# Docker Setup for personal-config

This repository is now containerized with Docker for reproducible development, testing, and CI/CD workflows.

## Files Generated

- **Dockerfile** - Multi-stage build with builder and runtime stages
- **docker-compose.yml** - Orchestrates dev, test, lint, and validation services  
- **.dockerignore** - Optimizes build context (excludes git, logs, caches, etc.)

## Quick Start

### Development Environment
```bash
# Start interactive development shell
docker compose run --rm dev

# Or use the service
docker compose up dev

# Run a specific script
docker compose run --rm dev bash -c "bash scripts/network-mode-manager.sh status"
```

### Run Tests
```bash
# Quick smoke tests (fast validation)
docker compose run --rm validate

# Full shell test suite
docker compose run --rm test

# Python tests only
docker compose run --rm test-python

# All tests
docker compose run --rm dev make test-all
```

### Code Quality
```bash
# Shellcheck linting (correctness checks)
docker compose run --rm lint

# Run benchmarks
docker compose run --rm benchmark

# SSH configuration tests
docker compose run --rm ssh-test
```

## Image Details

- **Base**: Ubuntu 24.04 (minimal security updates)
- **Tools Included**:
  - Shell: bash, zsh, fish
  - Python 3 with pytest
  - Network utilities: curl, wget, dnsutils, ssh
  - Build tools: git, jq, yq, sudo

- **Size**: ~371MB compressed
- **User**: `scriptuser` (non-root for security)

## Volume Mounts

- `/app` - Project source (read-write for development)
- `/app/scripts`, `/app/tests`, `/app/configs` - Optional read-only mounts
- `logs` - Persistent logs volume
- `reports` - Test/benchmark reports volume

## Environment Variables

Set in docker-compose.yml:
- `LOG_LEVEL=INFO` (dev), `DEBUG` (test)
- `PYTHONUNBUFFERED=1`

Override with:
```bash
docker compose run --rm -e LOG_LEVEL=DEBUG dev
```

## Build & Push

### Build locally
```bash
docker build -t personal-config:latest -f Dockerfile .
```

### Build for multiple platforms (requires buildx)
```bash
docker buildx build -t personal-config:latest --platform linux/amd64,linux/arm64 .
```

### Push to registry
```bash
docker tag personal-config:latest myregistry/personal-config:latest
docker push myregistry/personal-config:latest
```

## Best Practices Applied

✓ **Multi-stage builds** - Separate builder and runtime stages for minimal final image  
✓ **Non-root user** - Runs as `scriptuser` for security  
✓ **Layer caching** - Dependencies installed before source copy  
✓ **Health checks** - Container health verification  
✓ **Volume management** - Persistent logs and reports  
✓ **Read-only mounts** - Scripts/tests mounted as read-only where appropriate  
✓ **.dockerignore** - Reduces build context by ~80%  
✓ **Environment isolation** - Separate services for dev/test/lint workflows  

## Service Reference

| Service | Purpose | Command |
|---------|---------|---------|
| `dev` | Interactive development shell | `docker compose up dev` |
| `test` | Run all shell tests | `docker compose run --rm test` |
| `validate` | Quick validation checks | `docker compose run --rm validate` |
| `lint` | Shellcheck linting (SC2155/SC2145) | `docker compose run --rm lint` |
| `test-python` | Python unit tests | `docker compose run --rm test-python` |
| `benchmark` | Performance benchmarks | `docker compose run --rm benchmark` |
| `ssh-test` | SSH configuration tests | `docker compose run --rm ssh-test` |

## Tips

- Use `docker compose watch` for auto-rebuild on file changes (Docker v2.20+)
- Mount `.env.local` for environment overrides: `docker compose -f docker-compose.yml --env-file .env.local up dev`
- View logs: `docker compose logs -f dev`
- Stop all containers: `docker compose down`
- Clean up volumes: `docker compose down -v`
