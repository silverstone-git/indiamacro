#!/usr/bin/env bash
# Publish the dashboard + terminal to https://t.aryan.cfd/indiamacro/ on this server.
#
# nginx (sites-available/t.aryan.cfd) serves /var/www/indiamacro/ as static files and proxies
# /indiamacro/api/ to the indiamacro-web systemd service on 127.0.0.1:8765, which runs from this
# checkout (so it reads this directory's .env for the LLM). The front end uses relative URLs, so the
# same files work at / locally and under /indiamacro/ here.
#
#   ./deploy.sh            copy static files, restart the API service, smoke-test the public URLs
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

WWW=/var/www/indiamacro
SRC=src/indiamacro/web/static
URL=${INDIAMACRO_PUBLIC_URL:-https://t.aryan.cfd/indiamacro}

uv run --quiet pytest -q

mkdir -p "$WWW/static"
cp "$SRC/index.html" "$SRC/terminal.html" "$WWW/"
cp "$SRC"/*.js "$SRC"/*.css "$WWW/static/"
rm -f "$WWW/app.js" "$WWW/style.css"        # pre-terminal layout kept these at the root

sudo systemctl restart indiamacro-web
for _ in $(seq 1 30); do
  curl -sf -o /dev/null http://127.0.0.1:8765/api/ask/status && break
  sleep 1
done

fail=0
for path in / /terminal.html /static/terminal.js /api/ask/status /api/live/quakes; do
  code=$(curl -s -o /dev/null -w '%{http_code}' "$URL$path")
  printf '%s  %s\n' "$code" "$URL$path"
  [ "$code" = 200 ] || fail=1
done
exit $fail
