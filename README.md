## Overview

Temperature Hub records temperature, humidity, dew point, and battery readings
from Zigbee2MQTT and serves a local browser dashboard.

The runtime is managed with Docker Compose:

- `mosquitto`: MQTT broker using the mounted `mosquitto.conf`.
- `ingester`: Python MQTT subscriber that writes daily TSV segments under
  `data/shared/segments` and maintains `data/shared/index.json`.
- `webserver`: nginx static server for `web/index.html`, with `data/shared`
  mounted read-only for the dashboard.
- `zigbee2mqtt`: Zigbee2MQTT frontend and device bridge.
- `watchdog`: MQTT subscriber that restarts Zigbee2MQTT if dewpoint sensor
  readings stop arriving while the broker is still reachable.

Zigbee2MQTT should publish to `mqtt://mosquitto:1883` inside the Compose
network. If `data/zigbee2mqtt/configuration.yaml` is restored from a backup,
check that it uses that broker name rather than the old `python-mqtt` service.

The watchdog is intended to recover from cases where Zigbee2MQTT remains
running but stops receiving sensor updates after a coordinator or network
connection fault. It watches `zigbee2mqtt/dewpoint/+` and restarts only the
`temperature-hub-zigbee2mqtt` container after two hours without readings. The
timeout can be tuned with `STALE_AFTER_SECONDS` in `docker-compose.yml`.

## How to deploy

See the README in the parent repository.

### Router DHCP reservation

Temperature Hub should use a router-managed DHCP reservation rather than a
static IP override in `/etc/dhcpcd.conf`.

On a TalkTalk Wi-Fi Hub 2:

1. Log in to `http://192.168.1.1`.
2. Open `http://192.168.1.1/2.0/gui/#/mybox/DHCP`.
3. Click **Add reserved address**.
4. Enter the Pi Wi-Fi MAC address and the reserved IP address.
5. Click **Apply**.

For the current Pi:

```text
MAC: 2C:CF:67:FA:02:F7
IP: 192.168.1.10
```

Keep the reserved IP inside the router's DHCP pool. Do not set `STATIC_IP` in
`config.env`; if it is unset, `flash.sh` leaves the image configured for DHCP.

On an existing Pi, remove any old static override from `/etc/dhcpcd.conf` by
commenting out the `interface wlan0`, `static ip_address`, `static routers`, and
`static domain_name_servers` lines that were added for Temperature Hub, then
reboot.

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
