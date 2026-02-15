#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$BASE_DIR/.runtime/uvicorn.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "[WARN] PID file not found: $PID_FILE"
  echo "[INFO] Service may already be stopped."
  exit 0
fi

PID="$(cat "$PID_FILE" || true)"
if [[ -z "${PID:-}" ]]; then
  echo "[ERROR] PID file is empty: $PID_FILE"
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
  echo "[OK] Service stopped. PID=$PID"
else
  echo "[WARN] Process not running. PID=$PID"
fi

rm -f "$PID_FILE"
