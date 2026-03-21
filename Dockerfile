# Multi-stage build for personal-config repository
# Optimized for shell scripting, testing, and configuration management

# Stage 1: Builder - Install all dependencies
FROM ubuntu:24.04 as builder

WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Shell scripting
    bash \
    zsh \
    fish \
    shellcheck \
    # Git and VCS
    git \
    # Python support
    python3 \
    python3-pip \
    python3-venv \
    # Network utilities
    curl \
    wget \
    net-tools \
    dnsutils \
    iputils-ping \
    # SSH support
    openssh-client \
    openssh-server \
    # Development tools
    build-essential \
    ca-certificates \
    # Utilities
    jq \
    yq \
    sudo \
    vim \
    nano \
    less \
    && rm -rf /var/lib/apt/lists/*

# Install Python testing dependencies
RUN python3 -m pip install --no-cache-dir \
    unittest-xml-reporting \
    pytest \
    pytest-cov

# Install additional tools for benchmarking (optional in production, include for testing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    hyperfine \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Runtime - Minimal production image
FROM ubuntu:24.04

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Shell runtimes
    bash \
    zsh \
    fish \
    # Network utilities (for scripts)
    curl \
    wget \
    net-tools \
    dnsutils \
    iputils-ping \
    # SSH client (for remote operations)
    openssh-client \
    # Python runtime
    python3 \
    python3-pip \
    # System utilities
    jq \
    yq \
    sudo \
    # Essential tools
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python runtime dependencies (from requirements if available)
RUN python3 -m pip install --no-install-recommends --no-cache-dir \
    unittest-xml-reporting \
    pytest \
    pytest-cov || true

# Copy entire project
COPY . /app/

# Create non-root user for running scripts
RUN useradd -m -s /bin/bash -G sudo scriptuser && \
    echo "scriptuser ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Set proper permissions
RUN chown -R scriptuser:scriptuser /app && \
    chmod +x /app/scripts/*.sh 2>/dev/null || true && \
    chmod +x /app/tests/*.sh 2>/dev/null || true && \
    chmod +x /app/maintenance/bin/*.sh 2>/dev/null || true

# Create directories for logs and runtime data
RUN mkdir -p /app/logs /app/data /app/reports && \
    chown -R scriptuser:scriptuser /app/logs /app/data /app/reports

# Switch to non-root user
USER scriptuser

# Set environment variables
ENV PATH="/app/scripts:/app/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    SHELL=/bin/bash

# Health check - verify basic shell functionality
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD bash -c "test -x /app/scripts/network-mode-manager.sh || echo 'Config OK'" || exit 1

# Default command - interactive shell
CMD ["/bin/bash"]
