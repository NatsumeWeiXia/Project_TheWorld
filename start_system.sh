#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="$BASE_DIR/.runtime"
PID_FILE="$RUNTIME_DIR/uvicorn.pid"
LOG_FILE="$RUNTIME_DIR/uvicorn.log"

mkdir -p "$RUNTIME_DIR"

if [[ -f "$PID_FILE" ]]; then
  OLD_PID="$(cat "$PID_FILE" || true)"
  if [[ -n "${OLD_PID:-}" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "[WARN] Service already running. PID=$OLD_PID"
    echo "[INFO] URL: http://127.0.0.1:8000"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

cd "$BASE_DIR"
nohup python3 -m uvicorn src.app.main:app --host 0.0.0.0 --port 8000 >"$LOG_FILE" 2>&1 &
NEW_PID=$!
echo "$NEW_PID" >"$PID_FILE"

sleep 1
if kill -0 "$NEW_PID" 2>/dev/null; then
  echo "[OK] Service started. PID=$NEW_PID"
  echo "[INFO] URL: http://127.0.0.1:8000"
  echo "[INFO] Log: $LOG_FILE"
else
  echo "[ERROR] Service failed to start. Check log: $LOG_FILE"
  rm -f "$PID_FILE"
  exit 1
fi
