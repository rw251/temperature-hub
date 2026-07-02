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
IP: 192.168.1.96
```

Keep the reserved IP inside the router's DHCP pool. Do not set `STATIC_IP` in
`config.env`; if it is unset, `flash.sh` leaves the image configured for DHCP.

On an existing Pi, remove any old static override from `/etc/dhcpcd.conf` by
commenting out the `interface wlan0`, `static ip_address`, `static routers`, and
`static domain_name_servers` lines that were added for Temperature Hub, then
reboot.

### LAN HTTPS at `temp.rw251.com`

The Pi can serve the dashboard at `https://temp.rw251.com` without exposing the
service to the public internet. The setup uses:

- Cloudflare DNS API access for Let's Encrypt DNS-01 validation.
- `certbot` with the Cloudflare DNS plugin for certificate issuance and renewal.
- Host-level `nginx` as the HTTPS reverse proxy to the existing Docker webserver
  at `127.0.0.1:8000`.
- `dnsmasq` on the Pi for the LAN DNS override:
  `temp.rw251.com -> 192.168.1.96`.

The host setup is automated by `scripts/configure-host.sh`. The common
`update.sh` script runs that hook after `git pull` when the hook exists, then
rebuilds the Docker containers as usual.

#### Cloudflare setup for `rw251.com`

1. Log in to the Cloudflare dashboard.
2. Add `rw251.com` to Cloudflare if it is not already there.
3. At the domain registrar for `rw251.com`, change the authoritative
   nameservers to the two Cloudflare nameservers shown for the zone.
4. Wait until Cloudflare shows the zone as active.
5. Do not add a public `A` record for `temp.rw251.com` unless you later want the
   dashboard reachable from outside the LAN. Certbot only needs permission to
   create temporary `_acme-challenge.temp.rw251.com` TXT records.
6. In Cloudflare, open **My Profile > API Tokens**.
7. Select **Create Token**.
8. Use the **Edit zone DNS** template, or create a custom token with:
   - Permissions: `Zone / DNS / Edit`
   - Zone Resources: `Include / Specific zone / rw251.com`
9. Continue to summary, create the token, and copy the token secret immediately.
   Cloudflare only shows it once.
10. On the Pi, create `/etc/letsencrypt/cloudflare.ini`:

   ```bash
   sudo install -d -m 0700 /etc/letsencrypt
   sudo nano /etc/letsencrypt/cloudflare.ini
   ```

   Put this in the file:

   ```ini
   dns_cloudflare_api_token = paste-cloudflare-token-here
   ```

   Then lock down the file:

   ```bash
   sudo chmod 600 /etc/letsencrypt/cloudflare.ini
   ```

The example file at `data/secrets/cloudflare.ini.example` documents the expected
format, but the real token must not be committed to git.

#### Pi setup and update

On a running Pi:

```bash
cd ~/temperature-hub
./update.sh
```

The first run installs `nginx`, `dnsmasq`, `certbot`, and
`python3-certbot-dns-cloudflare`; configures local DNS; obtains the certificate
if `/etc/letsencrypt/cloudflare.ini` exists; writes the nginx reverse proxy; and
adds a Certbot renewal deploy hook that reloads nginx.

If the Cloudflare credentials file does not exist yet, the script configures
HTTP reverse proxying and local DNS, skips certificate issuance, and prints the
credential path to create. Create the file, then rerun `./update.sh`.

Set LAN clients to use the Pi as their DNS server (`192.168.1.96`) so
`temp.rw251.com` resolves locally. If the TalkTalk router cannot advertise a
custom DNS server via DHCP, configure DNS manually on the devices that should use
the dashboard, or move DHCP/DNS to Pi-hole/dnsmasq.

Useful checks:

```bash
nslookup temp.rw251.com 192.168.1.96
curl -I http://192.168.1.96:8000
curl -I https://temp.rw251.com
sudo certbot renew --dry-run
```

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
