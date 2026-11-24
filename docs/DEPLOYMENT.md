# Deployment (https://t.aryan.cfd/indiamacro)

## Topology

```
browser ─► Cloudflare (DNS + proxy, HTTPS) ─► this machine: nginx :443
            server block "t.aryan.cfd" in /etc/nginx/sites-available/t.aryan.cfd
              /indiamacro              → 301 /indiamacro/
              /indiamacro/             → basic auth → static files from /var/www/indiamacro
                                         try_files $uri $uri.html /indiamacro/index.html
                                         (so /indiamacro/terminal serves terminal.html)
              /indiamacro/api/         → basic auth → proxy http://127.0.0.1:8765/api/ (read timeout 300 s)
              other locations          → other apps (/p, /admin, /cytogame, /agentcyto): don't touch
          ─► systemd unit indiamacro-web (User=ubuntu, WorkingDirectory=/home/ubuntu/cyto/indiamacro)
              ExecStart: uv run --quiet indiamacro-web --host 127.0.0.1 --port 8765 --no-browser
              Environment: INDIAMACRO_CACHE=/home/ubuntu/.cache/indiamacro
              reads /home/ubuntu/cyto/indiamacro/.env (LLM + password variables)
```

Published files:

```
/var/www/indiamacro/index.html          dashboard
/var/www/indiamacro/terminal.html       terminal
/var/www/indiamacro/static/*.js, *.css  app.js, style.css, terminal.js, terminal.css
```

## Secrets (`.env`, gitignored)

| Variable | Used by |
|---|---|
| `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL` (or `LLM_*`) | the analyst (server process) |
| `INDIAMACRO_USERNAME`, `INDIAMACRO_KEY` | `deploy.sh` → `/etc/nginx/.htpasswd-indiamacro` (bcrypt, root:www-data 640) |
| `INDIAMACRO_ASK_PER_HOUR` (optional) | questions per IP per hour, default 30, 0 = unlimited |

Never print these values or pass them as command-line arguments. `.env.example` documents the names.

## Deploy

```bash
./deploy.sh
```

It: runs offline tests → rewrites the password file from `.env` and reloads nginx → copies static files
→ `sudo systemctl restart indiamacro-web` → waits for `/api/ask/status` → smoke test: expects **401**
without a password and **200** with it for `/`, `/terminal`, `/terminal.html`, `/static/terminal.js`,
`/api/ask/status`, `/api/live/quakes`. Exit code non-zero if any check fails.

Then check the UI: `uv run --no-project --with playwright==1.57.0 python scripts/screenshots.py --prod`.

Code runs from the working tree, so deploy from a clean, committed `main`: `git status` first.

## Changing nginx

```bash
sudo cp /etc/nginx/sites-available/t.aryan.cfd /etc/nginx/sites-available/t.aryan.cfd.bak-$(date +%Y%m%d%H%M%S)
sudoedit /etc/nginx/sites-available/t.aryan.cfd      # or write a new file and diff it first
sudo nginx -t && sudo systemctl reload nginx
```

The file is shared with other apps and partly managed by Certbot (the `listen 443 ssl` and certificate
lines); edit only the indiamacro blocks. Backups sit next to it as `t.aryan.cfd.bak-*`.

## Rollback

```bash
git log --oneline -5 && git checkout <good-commit> -- src/   # or git revert
./deploy.sh
# nginx: copy the latest backup back, nginx -t, reload
```

## Password

Change `INDIAMACRO_KEY` (and/or `INDIAMACRO_USERNAME`) in `.env`, then run `./deploy.sh`. It replaces the
file with exactly one user. To remove protection, delete the two `auth_basic*` lines from both indiamacro
locations in nginx (not recommended: the analyst spends LLM credits).

## Pushing to GitHub

Remote: `https://github.com/silverstone-git/indiamacro`. This machine has no GitHub credentials (no `gh`,
no SSH key registered), so `git push` fails non-interactively. The owner pushes with
`! git -C ~/cyto/indiamacro push origin main` from their session.
