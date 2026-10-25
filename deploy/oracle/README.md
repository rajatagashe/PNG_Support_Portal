# Deploy PNG Support Desk on Oracle Cloud (Always Free)

Runs the full stack (Frappe v16 + Helpdesk + Telephony, MariaDB, Redis, workers,
scheduler, Socket.IO, Caddy for HTTPS) on one free Oracle VM with Docker Compose.

The image is built from **GitHub `main`** (`apps.json`), not from local files —
push your changes before deploying.

## 1. Create the VM (Oracle Console)

1. Sign up at <https://cloud.oracle.com> (card is for verification only on Always Free).
2. **Compute → Instances → Create instance**
   - Image: **Canonical Ubuntu 24.04** (or 22.04)
   - Shape: **Ampere → VM.Standard.A1.Flex**, **2 OCPU / 12 GB RAM** (free up to 4 / 24)
   - Boot volume: **100 GB** (free up to 200 GB total)
   - Add your SSH public key, then **Create**.
   - "Out of capacity"? Retry later or try another availability domain.
3. **Open ports 80/443:** instance → Subnet → Default Security List → **Add Ingress Rules**
   - Source `0.0.0.0/0`, TCP, destination port `80`
   - Source `0.0.0.0/0`, TCP, destination port `443`
4. Note the instance's **Public IP**.

## 2. (Optional) Free domain for HTTPS

Create a subdomain at <https://www.duckdns.org> (e.g. `pngsupport.duckdns.org`) and point
it to the VM's public IP. Without a domain the app runs on plain HTTP via the IP.

## 3. Install

```bash
ssh ubuntu@<public-ip>
git clone https://github.com/rajatagashe/PNG_Support_Portal.git
cd PNG_Support_Portal/deploy/oracle
DOMAIN=pngsupport.duckdns.org bash setup.sh   # or just: bash setup.sh
```

The first build takes 20–40 minutes. At the end the script prints the URL and the
`Administrator` password (also saved in `deploy/oracle/.env`, which is git-ignored).

## 4. Deploy new changes

Push to `main`, then on the VM:

```bash
cd ~/PNG_Support_Portal/deploy/oracle
bash update.sh    # backup → rebuild image → restart → migrate
```

## Useful commands (run in `deploy/oracle`)

| Task | Command |
|---|---|
| Status | `sudo docker compose ps` |
| Logs | `sudo docker compose logs -f backend` |
| Bench shell | `sudo docker compose exec backend bash` |
| Backup | `sudo docker compose exec backend bench --site <site> backup --with-files` |
| Stop / start | `sudo docker compose down` / `sudo docker compose up -d` |

Backups are stored in the `sites` volume under `<site>/private/backups`.

## Adding a domain later

Site data lives under `SITE_NAME` (default `png.local`), which only needs to match
internally. To switch to HTTPS, set `CADDY_ADDRESS=<your-domain>` in `.env`, then
`sudo docker compose up -d caddy`.

## Files

| File | Purpose |
|---|---|
| `apps.json` | Apps baked into the image (telephony `develop`, this repo `main`) |
| `build.sh` | Builds `png-support-desk:latest` with frappe_docker's layered Containerfile |
| `docker-compose.yml` | Production stack, adapted from frappe_docker `pwd.yml` |
| `Caddyfile` | Reverse proxy; automatic Let's Encrypt when `CADDY_ADDRESS` is a domain |
| `setup.sh` | First install: Docker, VM firewall, `.env` with random passwords, build, start |
| `update.sh` | Redeploy latest `main` |
