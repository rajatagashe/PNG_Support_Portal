#!/usr/bin/env bash
# Builds the png-support-desk image from apps.json (pulls the app from GitHub, not this checkout).
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
FRAPPE_DOCKER="$HOME/frappe_docker"

if [ ! -d "$FRAPPE_DOCKER" ]; then
  git clone --depth 1 https://github.com/frappe/frappe_docker "$FRAPPE_DOCKER"
else
  git -C "$FRAPPE_DOCKER" pull --ff-only
fi

echo "==> Building image (20-40 minutes on the free ARM VM)"
cd "$FRAPPE_DOCKER"
sudo docker build \
  --build-arg=FRAPPE_PATH=https://github.com/frappe/frappe \
  --build-arg=FRAPPE_BRANCH=version-16 \
  --build-arg=CACHE_BUST="$(date +%s)" \
  --secret=id=apps_json,src="$DIR/apps.json" \
  --tag=png-support-desk:latest \
  --file=images/layered/Containerfile .
