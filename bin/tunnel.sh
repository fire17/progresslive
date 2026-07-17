#!/bin/sh
# ProgressLive tunnel wrapper (launchd-kept-alive). Writes the live URL to
# ~/.progresslive/tunnel_url so the local board always shows working values.
LOG=/tmp/pl-tunnel-launchd.log
: > "$LOG"
/opt/homebrew/bin/cloudflared tunnel --url http://localhost:8180 >"$LOG" 2>&1 &
CF=$!
for i in $(seq 1 30); do
  sleep 2
  URL=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$LOG" | head -1)
  [ -n "$URL" ] && { printf '%s' "$URL" > "$HOME/.progresslive/tunnel_url"; break; }
done
wait $CF
