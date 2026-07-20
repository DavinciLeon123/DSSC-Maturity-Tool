# Operations Guide

Day-to-day administration of the MAMI Compliance Checker.

---

## Starting and stopping the application

```bash
# Start all services in the background
docker compose -f docker-compose.prod.yml up -d

# Stop all services (data is preserved)
docker compose -f docker-compose.prod.yml down

# Restart a single service (e.g. after a config change)
docker compose -f docker-compose.prod.yml restart backend
```

---

## Viewing logs

```bash
# All services, last 100 lines, follow new output
docker compose -f docker-compose.prod.yml logs -f --tail=100

# Single service
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f nginx
```

---

## Database backups

### Creating a backup

Run this command on the server. It dumps the database to a compressed file named with the current date and time.

```bash
docker compose -f docker-compose.prod.yml exec db \
  pg_dump -U mami_user mami_db | gzip \
  > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

Replace `mami_user` with the value of `POSTGRES_USER` in your `.env` file.

### Restoring a backup

```bash
# Stop the backend first to prevent writes during restore
docker compose -f docker-compose.prod.yml stop backend

# Restore
gunzip -c backup_20260101_120000.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T db \
  psql -U mami_user mami_db

# Restart the backend
docker compose -f docker-compose.prod.yml start backend
```

### Recommended backup schedule

Set up a daily backup cron job:

```bash
sudo crontab -e
```

```
0 2 * * * cd /path/to/MaMi-Compliance-Checker && \
  docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U mami_user mami_db | gzip \
  > /backups/mami_$(date +\%Y\%m\%d).sql.gz
```

Keep at least 30 days of backups and copy them off-server (e.g. to cloud storage or a NAS).

---

## Updating the application

When a new version is available on GitHub:

```bash
# Pull the latest code
git pull

# Rebuild and restart services (backend + frontend images are rebuilt)
docker compose -f docker-compose.prod.yml up -d --build

# Database migrations run automatically on backend startup
```

Check the logs after updating to confirm the backend started cleanly:

```bash
docker compose -f docker-compose.prod.yml logs backend | tail -30
```

---

## Managing admin accounts

### Changing the admin password

Log in to the application as admin and use the "Change password" option in the profile menu. Alternatively, use the "Forgot password" flow from the login page.

### Adding a second admin account

Currently, admin accounts can only be created directly in the database. Connect to the running database container:

```bash
docker compose -f docker-compose.prod.yml exec db psql -U mami_user mami_db
```

Then run:

```sql
-- First check what roles exist
SELECT email, role FROM "user";

-- Promote an existing user to admin
UPDATE "user" SET role = 'ADMIN' WHERE email = 'user@example.com';

-- Exit
\q
```

### Changing the admin email address

If the admin account email needs to change (for example, to transfer ownership):

```bash
docker compose -f docker-compose.prod.yml exec db psql -U mami_user mami_db
```

```sql
UPDATE "user" SET email = 'newadmin@yourdomain.com' WHERE role = 'ADMIN' AND email = 'oldadmin@example.com';
\q
```

Also update `ADMIN_EMAIL` in your `.env` file so the startup script stays consistent. Restart the backend after editing `.env`:

```bash
docker compose -f docker-compose.prod.yml restart backend
```

---

## Updating questionnaire or scoring configuration

The questionnaire questions, scoring rules, and MAMI structure are all JSON files in the `config/` directory. They are mounted into the backend container at `/config` — changes take effect without rebuilding the image, only a backend restart is needed.

After editing a config file:

```bash
docker compose -f docker-compose.prod.yml restart backend
```

| File | What it controls |
|---|---|
| `config/dsi-questionnaire-v2.json` | DSI questions, answer options, follow-ups |
| `config/sp-questionnaire-v2.json` | SP questions, answer options, follow-ups |
| `config/mami-framework.json` | MAMI categories and dimensions |
| `config/scoring/mami-scoring.json` | GoRules ZEN scoring rules (CRITICAL/NON_CRITICAL) |

---

## Checking application health

```bash
curl https://your-domain.com/health
# Expected: {"status":"ok"}
```

---

## Disk space

Docker images and the database volume are the main consumers. Check available space:

```bash
df -h
docker system df
```

To remove unused Docker images (old build layers after updates):

```bash
docker image prune -f
```

---

## SSL certificate renewal

Certificates are renewed automatically by the cron job set up during deployment (see [DEPLOYMENT.md](DEPLOYMENT.md)). To check when the current certificate expires:

```bash
sudo certbot certificates
```

To trigger a manual renewal:

```bash
sudo certbot renew --webroot --webroot-path /var/www/certbot
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

---

## Demo reset

The admin panel includes a "Demo reset" function that clears all user accounts and questionnaire data while preserving the admin account. Use this before public events or demonstrations.

Access it from: Admin panel → Demo Reset (bottom of the page).
