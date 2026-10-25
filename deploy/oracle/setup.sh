#!/usr/bin/env bash
# First-time install of PNG Support Desk on an Ubuntu VM (Oracle Cloud Always Free, ARM or x86).
# Usage: DOMAIN=support.example.com ./setup.sh   (omit DOMAIN to serve plain HTTP on the VM's IP)
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "==> Installing Docker"
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sudo sh
fi

echo "==> Opening ports 80/443 in the VM firewall (Oracle Ubuntu images block them by default)"
for port in 80 443; do
  sudo iptables -C INPUT -p tcp --dport "$port" -j ACCEPT 2>/dev/null ||
    sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport "$port" -j ACCEPT 2>/dev/null ||
    sudo iptables -I INPUT -m state --state NEW -p tcp --dport "$port" -j ACCEPT
done
if command -v netfilter-persistent >/dev/null; then
  sudo netfilter-persistent save
fi

echo "==> Writing .env"
if [ ! -f .env ]; then
  site_name="${DOMAIN:-png.local}"
  cat > .env <<EOF
SITE_NAME=${site_name}
CADDY_ADDRESS=${DOMAIN:-:80}
DB_ROOT_PASSWORD=$(openssl rand -hex 16)
ADMIN_PASSWORD=$(openssl rand -hex 8)
EOF
  chmod 600 .env
else
  echo ".env already exists, keeping it"
fi

"$DIR/build.sh"

echo "==> Starting the stack"
sudo docker compose up -d

echo "==> Waiting for the site to be created (first run takes a few minutes)"
sudo docker compose wait create-site || {
  echo "Site creation failed. Check: sudo docker compose logs create-site"
  exit 1
}

# shellcheck disable=SC1091
source .env
echo
echo "PNG Support Desk is up."
if [ -n "${DOMAIN:-}" ]; then
  echo "  URL:      https://${DOMAIN}/helpdesk"
else
  echo "  URL:      http://<your-vm-public-ip>/helpdesk"
fi
echo "  Login:    Administrator"
echo "  Password: ${ADMIN_PASSWORD}   (also stored in $DIR/.env)"
