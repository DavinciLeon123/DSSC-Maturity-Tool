# Deployment Guide — Self-Hosting

This guide covers deploying the MAMI Compliance Checker on your own Linux server.

---

## Prerequisites

### Server requirements

- A Linux server (Ubuntu 22.04 LTS recommended), minimum 2 GB RAM
- A domain name with an A record pointing to the server's public IP address
- Ports 80 and 443 open in the server's firewall

### Software to install on the server

**Docker:**
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in for the group change to take effect
```

**Docker Compose (v2):**
```bash
sudo apt-get install docker-compose-plugin
docker compose version   # Should print v2.x.x
```

### External service: Resend (email)

The application uses [Resend](https://resend.com) to send PDF reports and password reset emails.

1. Create a free account at resend.com
2. Add and verify your domain in the Resend dashboard
3. Create an API key — you will need this during configuration
4. Add a sender address (e.g. `noreply@yourdomain.com`) and note it

If you skip this step, the app still works but email delivery (PDF reports and password resets) will be disabled.

---

## Step 1 — Get the code

On your server, clone the repository:

```bash
git clone https://github.com/DavinciLeon123/MaMi-Compliance-Checker.git
cd MaMi-Compliance-Checker
```

---

## Step 2 — Configure environment variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
nano .env
```

The file to fill in:

```env
POSTGRES_USER=mami_user
POSTGRES_PASSWORD=          # Strong password, no special shell characters

# Generate with: python3 -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=                 # 64-character hex string

ADMIN_EMAIL=                # Email address for the admin account
ADMIN_PASSWORD=             # Strong password for the admin account

DOMAIN=                     # Your domain, e.g. checker.yourdomain.com

RESEND_API_KEY=             # From the Resend dashboard (leave empty to disable email)
FRONTEND_URL=https://       # Full URL of your domain, e.g. https://checker.yourdomain.com
```

Generate a secure `SECRET_KEY`:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## Step 3 — Start the application (HTTP first)

Start all services. On first boot the backend runs database migrations and creates the admin account automatically.

```bash
docker compose -f docker-compose.prod.yml up -d
```

Verify all four services are running:

```bash
docker compose -f docker-compose.prod.yml ps
```

All four services (`db`, `backend`, `frontend`, `nginx`) should show status `Up`.

Check that the app responds on port 80:

```bash
curl http://your-domain/health
# Expected: {"status":"ok"}
```

---

## Step 4 — Obtain an SSL certificate (manual Certbot)

Install Certbot on the server (not inside Docker):

```bash
sudo apt-get install certbot
```

The nginx container already serves the Let's Encrypt HTTP-01 challenge from `/var/www/certbot`. Run Certbot in webroot mode, pointing at that same directory on the host:

```bash
sudo certbot certonly \
  --webroot \
  --webroot-path /var/www/certbot \
  -d your-domain.com \
  --email your-email@example.com \
  --agree-tos \
  --non-interactive
```

If successful, certificates are written to `/etc/letsencrypt/live/your-domain.com/`. The nginx container already mounts `/etc/letsencrypt` read-only, so it can read these files.

---

## Step 5 — Enable HTTPS in nginx

Open `nginx/nginx.conf` in a text editor:

```bash
nano nginx/nginx.conf
```

Make two edits:

**Edit 1** — In the existing HTTP `server` block, replace the `location /` block (which currently proxies to the frontend) with a redirect to HTTPS:

```nginx
location / {
    return 301 https://$host$request_uri;
}
```

**Edit 2** — Uncomment the entire HTTPS `server` block at the bottom of the file and replace both occurrences of `YOUR_DOMAIN_HERE` with your actual domain:

```nginx
server {
    listen 443 ssl;
    server_name checker.yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/checker.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/checker.yourdomain.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # ... (rest of the block, leave unchanged)
}
```

Reload nginx to apply the new config:

```bash
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

Verify HTTPS is working:

```bash
curl https://your-domain.com/health
```

---

## Step 6 — Set up automatic certificate renewal

Let's Encrypt certificates expire after 90 days. Add a cron job to renew automatically:

```bash
sudo crontab -e
```

Add this line (runs renewal check twice a day and reloads nginx if a certificate was renewed):

```
0 3,15 * * * certbot renew --webroot --webroot-path /var/www/certbot --quiet && docker exec $(docker ps -qf name=nginx) nginx -s reload
```

---

## Step 7 — Verify the deployment

1. Open `https://your-domain.com` in a browser — the login page should load
2. Log in with the `ADMIN_EMAIL` and `ADMIN_PASSWORD` you configured
3. Check the admin panel at the top-right menu
4. If you configured Resend, test email delivery via the "Forgot password" flow

---

## Environment variable reference

| Variable | Required | Description |
|---|---|---|
| `POSTGRES_USER` | Yes | PostgreSQL username |
| `POSTGRES_PASSWORD` | Yes | PostgreSQL password |
| `SECRET_KEY` | Yes | 64-char hex string for JWT signing |
| `ADMIN_EMAIL` | Yes | Email for the initial admin account |
| `ADMIN_PASSWORD` | Yes | Password for the initial admin account |
| `DOMAIN` | Yes | Your domain name (used for CORS) |
| `RESEND_API_KEY` | No | Resend API key — email is disabled if empty |
| `FRONTEND_URL` | No | Full HTTPS URL — used in password reset emails |

---

## Firewall checklist

| Port | Protocol | Purpose |
|---|---|---|
| 22 | TCP | SSH (management) |
| 80 | TCP | HTTP (redirect to HTTPS + Let's Encrypt challenge) |
| 443 | TCP | HTTPS (application traffic) |

All other ports should be closed. The database (5432), backend (8000), and frontend (80 internal) are not exposed to the public — nginx handles all traffic.

---

## Troubleshooting

**Services not starting:**
```bash
docker compose -f docker-compose.prod.yml logs backend
docker compose -f docker-compose.prod.yml logs db
```

**Database migration failed:**
```bash
docker compose -f docker-compose.prod.yml logs backend | grep -i alembic
```

**Nginx config error:**
```bash
docker compose -f docker-compose.prod.yml exec nginx nginx -t
```

**Certificate not found:**
Check the certificate exists on the host:
```bash
sudo ls /etc/letsencrypt/live/your-domain.com/
```

**CORS errors in browser:**
Make sure `DOMAIN` in `.env` exactly matches the domain you are accessing (no trailing slash, no `https://`).
