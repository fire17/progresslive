#!/bin/sh
# ProgressLive tunnel wrapper (launchd-kept-alive). Continuously mirrors the live
# quick-tunnel URL into ~/.progresslive/tunnel_url (binary-safe extraction) so the
# local board card + /api/remote-info always show working values — even when
# registration is slow or the edge re-registers mid-life.
LOG=/tmp/pl-tunnel-launchd.log
: > "$LOG"
/opt/homebrew/bin/cloudflared tunnel --url http://localhost:8180 >"$LOG" 2>&1 &
CF=$!
while kill -0 $CF 2>/dev/null; do
  URL=$(strings "$LOG" | grep -ao 'https://[a-z0-9-]*\.trycloudflare\.com' | tail -1)
  if [ -n "$URL" ] && [ "$URL" != "$(cat "$HOME/.progresslive/tunnel_url" 2>/dev/null)" ]; then
    printf '%s' "$URL" > "$HOME/.progresslive/tunnel_url"
  fi
  sleep 5
done
