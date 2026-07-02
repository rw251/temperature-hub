#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

echo "--- Pulling latest changes from git... ---"
stash_created=false
if ! git diff --quiet || ! git diff --cached --quiet || [ -n "$(git ls-files --others --exclude-standard)" ]; then
    # Stash local changes to avoid conflicts, then pull.
    # This is useful if config files or logs have been modified.
    git stash push --include-untracked -m "update.sh auto-stash"
    stash_created=true
fi

git pull --ff-only origin main

if [ "$stash_created" = true ]; then
    git stash pop || true # Try to re-apply stashed changes; keep stash if conflicts need manual handling.
fi

if [ -x "./scripts/configure-host.sh" ]; then
    echo "--- Configuring host services... ---"
    ./scripts/configure-host.sh
fi

echo "--- Rebuilding and restarting Docker containers... ---"
docker compose up -d --build --remove-orphans

echo "--- Pruning old Docker images to save space... ---"
docker image prune -f

echo "--- Update complete! ---"
