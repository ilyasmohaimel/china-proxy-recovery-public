# Optional services (generic example)

This is a template for optional supporting services you might run alongside the proxy. Do not expose a detailed map of a live deployment. Adapt ports, paths, and service choices to your own setup.

All application data in this example lives on `/srv` (the OCI Block Volume), separate from the boot volume.

```text
/srv/
├── apps/
│   ├── <service-a>/
│   ├── <service-b>/
│   └── <service-c>/
├── data/
├── backups/
└── git/
```

## Reverse proxy pattern

TCP/443 remains dedicated to the proxy. If you expose additional services over HTTPS, use separate ports and a reverse proxy (e.g., Nginx) with distinct vhosts.

Example port mapping — replace with your own:

| Port | Example service |
|------|----------------|
| 80 | ACME HTTP-01 only |
| <SERVICE_A_PORT> | Example service A (e.g., media) |
| <SERVICE_B_PORT> | Example service B (e.g., file sharing) |
| <SERVICE_C_PORT> | Example service C (e.g., notifications) |

Use TLS certificates appropriate to your deployment (e.g., Let's Encrypt). Keep renewal automated and verify with:

```sh
sudo nginx -t
sudo systemctl reload nginx
```

The OCI Security List / NSG must allow only the ports you intentionally expose. Do not add public rules for private-only services.

## Storage

If you share a directory between services (e.g., `/srv/cloud`), mount it once and reference it read-only where appropriate. Do not make a second copy.

For private-only file sharing (e.g., Samba), restrict access to a private network (e.g., tailnet) and verify the public address is closed:

```sh
sudo ss -lntp | grep ':445'
sudo ufw status numbered
```

## Containers

If you run services via Docker Compose, keep each service's Compose project and state under `/srv/apps/<service>`:

```sh
sudo docker compose -f /srv/apps/<service>/compose.yaml ps
sudo docker ps
```

## Credentials

- **Change all default credentials before exposing any service.** Do not publish credentials in config files committed to Git.
- Use strong, unique administrator passwords for every service (e.g., file sharing, notifications, link shorteners).
- Store secrets in protected files outside Git (`chmod 600`) and never commit `.env`, tokens, or API keys.
- For file-sharing services (e.g., Gokapi), create a strong admin password on first setup and do not reuse example or default credentials.

## Backups

Take consistent application backups (e.g., database dumps) before pulling or syncing to another host. Never copy live database directories while the database is running.

Verify backups:

```sh
sudo systemctl list-timers
sudo journalctl -u <backup-service> -n 50 --no-pager
df -h /srv
```

After any storage, Docker, or reverse-proxy change, verify the mount, containers, listeners, and proxy services:

```sh
findmnt /srv
sudo docker ps
sudo ss -lntup
sudo systemctl status nginx xray hysteria-server adguardhome --no-pager
sudo ufw status verbose
systemctl --failed
```

## Notifications

If you use ntfy or similar for operational alerts, consider separate topics for different event classes (e.g., `security`, `updates`, `system`) and keep auth tokens in protected files (`chmod 600`). Routine successful jobs should be silent; only failures should alert.
