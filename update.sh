#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

echo "--- Pulling latest changes from git... ---"
# Stash any local changes to avoid conflicts, then pull.
# This is useful if config files or logs have been modified.
git stash --include-untracked
git pull origin main
git stash pop || true # Try to re-apply stashed changes, ignore if nothing was stashed

if [ -x "./scripts/configure-host.sh" ]; then
    echo "--- Configuring host services... ---"
    ./scripts/configure-host.sh
fi

echo "--- Rebuilding and restarting Docker containers... ---"
docker compose up -d --build --remove-orphans

echo "--- Pruning old Docker images to save space... ---"
docker image prune -f

echo "--- Update complete! ---"
