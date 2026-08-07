# Cursor Cloud Agent base image for the multi-repo Dev Cloud workspace.
# System packages mirror personal-config and Seatek_Analysis .devin/blueprint.yaml
# initialize sections. Repository dependencies are installed by install script.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    ca-certificates curl git gnupg sudo software-properties-common \
    python3.12 python3.12-venv python3-pip \
    graphviz rclone shellcheck openjdk-17-jre-headless \
    build-essential gfortran libcurl4-openssl-dev libxml2-dev libssl-dev \
    libfontconfig1-dev libharfbuzz-dev libfribidi-dev libuv1-dev \
    libzip-dev zlib1g-dev libgit2-dev pandoc cmake \
  && rm -rf /var/lib/apt/lists/*

# R 4.3.3 from Posit r-builds noble packages (matches Seatek_Analysis renv.lock).
RUN set -eux; \
  arch="$(dpkg --print-architecture)"; \
  r_version="4.3.3"; \
  r_deb="r-${r_version}_1_${arch}.deb"; \
  case "${arch}" in \
    amd64) r_sha="f1a4c4d4c36f7e8ddd67fd2abf2019f15e4c05e20ecc22d4c1890d64692b9ab5" ;; \
    arm64) r_sha="" ;; \
    *) echo "Unsupported architecture: ${arch}" >&2; exit 1 ;; \
  esac; \
  if [ -z "${r_sha}" ]; then echo "R noble package SHA not pinned for ${arch}" >&2; exit 1; fi; \
  curl -fsSL -o "/tmp/${r_deb}" "https://cdn.posit.co/r/ubuntu-2404/pkgs/${r_deb}"; \
  printf "%s  /tmp/%s\n" "${r_sha}" "${r_deb}" | sha256sum -c -; \
  apt-get update \
  && apt-get install -y --no-install-recommends "/tmp/${r_deb}" \
  && rm -f "/tmp/${r_deb}" \
  && rm -rf /var/lib/apt/lists/* \
  && ln -sf "/opt/R/${r_version}/bin/R" /usr/local/bin/R \
  && ln -sf "/opt/R/${r_version}/bin/Rscript" /usr/local/bin/Rscript

# PlantUML (personal-config blueprint initialize).
RUN mkdir -p /opt/cloud-agent/bin \
  && curl -fsSL -o /opt/cloud-agent/bin/plantuml.jar \
    https://github.com/plantuml/plantuml/releases/download/v1.2024.5/plantuml-1.2024.5.jar \
  && printf '%s\n' '#!/usr/bin/env bash' 'exec java -jar /opt/cloud-agent/bin/plantuml.jar "$@"' \
    > /opt/cloud-agent/bin/plantuml \
  && chmod +x /opt/cloud-agent/bin/plantuml

# ubuntu:24.04 ships the ubuntu user; only ensure sudo and home layout.
RUN if ! id ubuntu >/dev/null 2>&1; then useradd -m -s /bin/bash -u 1000 ubuntu; fi \
  && echo 'ubuntu ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/ubuntu \
  && chmod 0440 /etc/sudoers.d/ubuntu

ENV PATH="/opt/cloud-agent/bin:${PATH}"

USER ubuntu
WORKDIR /home/ubuntu
