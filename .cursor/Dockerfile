# Use Ubuntu 22.04 as the base image for stability and compatibility
FROM ubuntu:22.04-slim

# Install essential system updates and tools
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Install Python and pip for scripting and automation
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js and npm for JavaScript-based tools (optional, remove if not needed)
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Set a non-root user and working directory for security
RUN useradd -m -s /bin/bash ubuntu
USER ubuntu
WORKDIR /home/ubuntu

# Optional: Set environment variables for better development experience
ENV PATH="/home/ubuntu/.local/bin:${PATH}"

# Optional: Add timezone for consistent timestamps
ENV TZ=America/Chicago

# Optional: Pre-install common Python packages your agents might need
RUN pip3 install --user requests aiohttp

# Optional: Add Rust toolchain if you work with Rust projects
# RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Expose any necessary ports if your background tasks require networking (customize as needed)
EXPOSE 3128

# Default command to keep the container running for background tasks
CMD ["bash"]
