## Overview

This ...

## How to deploy

See the README in the parent repository.

## Developer Workflow

This project is managed as a Git submodule within the main `pi-images` flasher repository.

### Making Changes

1.  Navigate into this project's directory: `cd projects/temperature-hub`
2.  Make your code changes (e.g., update `index.html`).
3.  Commit and push your changes _from within this directory_:
    ```bash
    git add .
    git commit -m "feat: Update the webserver index page"
    git push
    ```
4.  Navigate back to the parent `pi-images` repository: `cd ../..`
5.  The parent repository will now see that the `temperature-hub` submodule is pointing to a new commit. Add, commit, and push this change to finalize the update:
    ```bash
    git add projects/temperature-hub
    git commit -m "chore: Update temperature-hub to latest version"
    git push
    ```

## How to update

### On a running Pi

1. SSH into the Raspberry Pi.
2. Navigate to the project directory: `cd ~/temperature-hub`.
3. Run the update script: `./update.sh`

This will pull the latest code _for this project only_ and rebuild the Docker containers as needed.
