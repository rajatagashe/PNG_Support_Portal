#!/usr/bin/env bash
# Deploys the latest commit on GitHub main: rebuild image, restart, migrate.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
# shellcheck disable=SC1091
source .env

echo "==> Backing up the site first"
sudo docker compose exec backend bench --site "$SITE_NAME" backup --with-files

"$DIR/build.sh"

echo "==> Restarting with the new image"
sudo docker compose up -d --force-recreate

echo "==> Running migrations"
sudo docker compose exec backend bench --site "$SITE_NAME" migrate

echo "Update complete."
