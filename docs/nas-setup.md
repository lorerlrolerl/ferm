# NAS Setup Guide

## GitHub Actions Secrets

Go to: GitHub repo → Settings → Secrets and variables → Actions → New repository secret

| Secret | Value |
|--------|-------|
| `NAS_HOST` | Your NAS Tailscale IP e.g. `100.x.x.x` |
| `NAS_USER` | Your NAS SSH username e.g. `admin` |
| `NAS_SSH_KEY` | Your SSH private key (see below) |
| `NAS_SSH_PORT` | SSH port on your NAS, usually `22` or `22022` |

## Generating an SSH key for GitHub Actions

On your laptop:
```bash
ssh-keygen -t ed25519 -C "github-actions-fermlog" -f ~/.ssh/fermlog_deploy
```

Copy public key to NAS:
```bash
ssh-copy-id -i ~/.ssh/fermlog_deploy.pub admin@NAS-IP
```

Copy private key content into `NAS_SSH_KEY` secret:
```bash
cat ~/.ssh/fermlog_deploy
```

## Backup cron job on NAS

SSH into NAS and run:
```bash
mkdir -p /volume1/docker/fermlog/logs
crontab -e
```

Add this line (runs 2am nightly):
```
0 2 * * * /volume1/docker/fermlog/backup.sh >> /volume1/docker/fermlog/logs/backup.log 2>&1
```

Test manually:
```bash
/volume1/docker/fermlog/backup.sh
```

## How it works

**Push to main:**
1. Tests run — if any fail, deploy is blocked
2. Tests pass → SSH to NAS → git pull → docker compose up --build
3. Old images pruned automatically

**Every night 2am:**
1. ferm.db copied to backups/ferm_TIMESTAMP.db
2. Backups older than 30 days deleted
3. Logged to logs/backup.log