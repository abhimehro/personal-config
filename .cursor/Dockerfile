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

# R 4.3.3 from Posit r-builds (matches Seatek_Analysis renv.lock).
RUN set -eux; \
  arch="$(dpkg --print-architecture)"; \
  r_version="4.3.3"; \
  r_deb="r-${r_version}_1_${arch}.deb"; \
  case "${arch}" in \
    amd64) r_sha="dde20cc255a1c5627ec5ed84c8d3b24f094b4b0459b363e96c137fb98220bae5" ;; \
    arm64) r_sha="5349604db30056bd8b40ab32518ea002bd748bcecff9e56b0ad4415981d3776e" ;; \
    *) echo "Unsupported architecture: ${arch}" >&2; exit 1 ;; \
  esac; \
  curl -fsSL -o "/tmp/${r_deb}" "https://cdn.posit.co/r/ubuntu-2204/pkgs/${r_deb}"; \
  printf "%s  /tmp/%s\n" "${r_sha}" "${r_deb}" | sha256sum -c -; \
  apt-get update \
  && apt-get install -y --no-install-recommends "/tmp/${r_deb}" \
  && rm -f "/tmp/${r_deb}" \
  && rm -rf /var/lib/apt/lists/*; \
  ln -sf "/opt/R/${r_version}/bin/R" /usr/local/bin/R; \
  ln -sf "/opt/R/${r_version}/bin/Rscript" /usr/local/bin/Rscript

# PlantUML (personal-config blueprint initialize).
RUN mkdir -p /opt/cloud-agent/bin \
  && curl -fsSL -o /opt/cloud-agent/bin/plantuml.jar \
    https://github.com/plantuml/plantuml/releases/download/v1.2024.5/plantuml-1.2024.5.jar \
  && printf '%s\n' '#!/usr/bin/env bash' 'exec java -jar /opt/cloud-agent/bin/plantuml.jar "$@"' \
    > /opt/cloud-agent/bin/plantuml \
  && chmod +x /opt/cloud-agent/bin/plantuml

RUN useradd -m -s /bin/bash -u 1000 ubuntu \
  && echo 'ubuntu ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/ubuntu \
  && chmod 0440 /etc/sudoers.d/ubuntu

ENV PATH="/opt/cloud-agent/bin:${PATH}"

USER ubuntu
WORKDIR /home/ubuntu
