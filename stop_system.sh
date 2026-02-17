#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$BASE_DIR/.runtime/uvicorn.pid"

log() {
  printf '[%s] [%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" "$2"
}

if [[ ! -f "$PID_FILE" ]]; then
  log "WARN" "PID file not found: $PID_FILE"
  log "INFO" "Service may already be stopped."
  exit 0
fi

PID="$(cat "$PID_FILE" || true)"
if [[ -z "${PID:-}" ]]; then
  log "ERROR" "PID file is empty: $PID_FILE"
  exit 1
fi

if kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  for _ in {1..10}; do
    if ! kill -0 "$PID" 2>/dev/null; then
      break
    fi
    sleep 1
  done
  if kill -0 "$PID" 2>/dev/null; then
    kill -9 "$PID" || true
  fi
  log "OK" "Service stopped. PID=$PID"
else
  log "WARN" "Process not running. PID=$PID"
fi

rm -f "$PID_FILE"
