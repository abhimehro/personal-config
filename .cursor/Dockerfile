# Use Ubuntu 22.04 as the base image for stability and compatibility
FROM ubuntu:22.04-slim

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install all system dependencies in a single layer to reduce image size
# This includes essential dev tools, Python, and timezone data
RUN apt-get update && apt-get install -y \
    # Essential development tools
    git \
    curl \
    wget \
    build-essential \
    software-properties-common \
    ca-certificates \
    # Python and pip for scripting and automation
    python3 \
    python3-pip \
    python3-venv \
    # Basic utilities agents might need
    vim \
    less \
    jq \
    # Timezone support (required when TZ env var is set)
    tzdata \
    # Cleanup in same layer to reduce image size
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Node.js and npm (optional - remove if not needed for your project)
# Using NodeSource for consistent version management
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user and set up home directory
# This is a security best practice for cloud agents
RUN useradd -m -s /bin/bash ubuntu

# Switch to non-root user before installing user-level packages
# This ensures proper permissions and security
USER ubuntu
WORKDIR /home/ubuntu

# Set environment variables for better development experience
ENV PATH="/home/ubuntu/.local/bin:${PATH}" \
    # Set timezone for consistent timestamps in logs and outputs
    TZ=America/Chicago \
    # Prevent Python from writing .pyc files (optional, reduces clutter)
    PYTHONDONTWRITEBYTECODE=1 \
    # Force Python to use UTF-8 encoding
    PYTHONUNBUFFERED=1

# Pre-install common Python packages your agents might need
# Using --user flag ensures packages are installed in user's home directory
# This avoids permission issues and follows best practices
RUN pip3 install --user --no-cache-dir \
    requests \
    aiohttp

# Optional: Add Rust toolchain if you work with Rust projects
# Uncomment if needed:
# RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
#     && echo 'source $HOME/.cargo/env' >> ~/.bashrc

# Note: Do NOT copy code or COPY commands here
# The agent will clone the repository into the working directory

# Default command to keep the container running for background tasks
# Using bash with -l flag to ensure proper environment loading
CMD ["/bin/bash", "-l"]
