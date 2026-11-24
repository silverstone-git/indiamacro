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

# Basic-auth password for the whole site (nginx reads /etc/nginx/.htpasswd-indiamacro), from .env:
#   INDIAMACRO_USERNAME=...   INDIAMACRO_KEY=...   (the password; piped via stdin, never on a command line)
HTPASSWD=/etc/nginx/.htpasswd-indiamacro
if user=$(uv run --quiet python -c 'from indiamacro.monitor import env; print(env.get("INDIAMACRO_USERNAME"))') && [ -n "$user" ]; then
  uv run --quiet python -c 'from indiamacro.monitor import env; print(env.get("INDIAMACRO_KEY"), end="")' \
    | sudo htpasswd -c -i -B "$HTPASSWD" "$user" 2>/dev/null
  sudo chown root:www-data "$HTPASSWD" && sudo chmod 640 "$HTPASSWD"
  sudo nginx -t -q && sudo systemctl reload nginx
  echo "password file updated for user $user"
else
  echo "INDIAMACRO_USERNAME not set in .env: leaving $HTPASSWD as it is" >&2
fi

mkdir -p "$WWW/static"
cp "$SRC/index.html" "$SRC/terminal.html" "$WWW/"
cp "$SRC"/*.js "$SRC"/*.css "$WWW/static/"
rm -f "$WWW/app.js" "$WWW/style.css"        # pre-terminal layout kept these at the root

sudo systemctl restart indiamacro-web
for _ in $(seq 1 30); do
  curl -sf -o /dev/null http://127.0.0.1:8765/api/ask/status && break
  sleep 1
done

netrc() {   # credentials for curl on stdin-like fd, so the password never appears in `ps`
  uv run --quiet python -c 'import sys; from urllib.parse import urlsplit; from indiamacro.monitor import env
print("machine", urlsplit(sys.argv[1]).hostname, "login", env.get("INDIAMACRO_USERNAME"), "password", env.get("INDIAMACRO_KEY"))' "$URL"
}
fail=0
code=$(curl -s -o /dev/null -w '%{http_code}' "$URL/terminal")
printf '%s  %s (no password: expect 401)\n' "$code" "$URL/terminal"
[ "$code" = 401 ] || fail=1
for path in / /terminal /terminal.html /static/terminal.js /api/ask/status /api/live/quakes; do
  code=$(curl -s -o /dev/null -w '%{http_code}' --netrc-file <(netrc) "$URL$path")
  printf '%s  %s\n' "$code" "$URL$path"
  [ "$code" = 200 ] || fail=1
done
exit $fail
