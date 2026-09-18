#!/bin/bash
set -e

echo "[+] Starting Xvfb virtual display :99..."
Xvfb :99 -screen 0 1024x768x24 -ac +extension GLX +render -noreset &
export DISPLAY=:99

sleep 1
echo "[+] Virtual display ready on $DISPLAY. Launching ClashBot Host Engine..."

exec python /app/Host/run.py
