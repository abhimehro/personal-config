#!/usr/bin/env bash
set -Eeuo pipefail

source /usr/local/bin/dns-common.sh

CHECK_INTERVAL=60
FAIL_THRESHOLD=1

main() {
  local failures=0
  
  # Quick check: service running and port bound
  if ! is_service_running || ! check_port_53; then
    ((failures++))
  fi

  # DNS test via 127.0.0.1
  if ! validate_dns_resolution "127.0.0.1"; then
    ((failures++))
  fi

  if (( failures >= FAIL_THRESHOLD )); then
    logger -t ctrld-health "ctrld health check failed ($failures). Initiating fallback to system DNS."
    emergency_rollback "Health check failure"
    exit 1
  fi

  exit 0
}

main "$@"

