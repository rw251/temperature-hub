#!/bin/bash
set -euo pipefail

DOMAIN="${TEMP_HUB_DOMAIN:-temp.rw251.com}"
LAN_IP="${TEMP_HUB_LAN_IP:-192.168.1.96}"
UPSTREAM="${TEMP_HUB_UPSTREAM:-http://127.0.0.1:8000}"
CERTBOT_EMAIL="${TEMP_HUB_CERTBOT_EMAIL:-}"
CLOUDFLARE_CREDENTIALS="${TEMP_HUB_CLOUDFLARE_CREDENTIALS:-/etc/letsencrypt/cloudflare.ini}"

if [ "$(id -u)" -ne 0 ]; then
    exec sudo env \
        TEMP_HUB_DOMAIN="$DOMAIN" \
        TEMP_HUB_LAN_IP="$LAN_IP" \
        TEMP_HUB_UPSTREAM="$UPSTREAM" \
        TEMP_HUB_CERTBOT_EMAIL="$CERTBOT_EMAIL" \
        TEMP_HUB_CLOUDFLARE_CREDENTIALS="$CLOUDFLARE_CREDENTIALS" \
        "$0" "$@"
fi

export DEBIAN_FRONTEND=noninteractive

install_packages() {
    local missing=0
    for package in nginx dnsmasq certbot python3-certbot-dns-cloudflare; do
        if ! dpkg -s "$package" >/dev/null 2>&1; then
            missing=1
        fi
    done

    if [ "$missing" -eq 1 ]; then
        apt-get update
        apt-get install -y nginx dnsmasq certbot python3-certbot-dns-cloudflare
    fi
}

configure_dnsmasq() {
    install -d -m 0755 /etc/dnsmasq.d
    cat > /etc/dnsmasq.d/temperature-hub.conf <<EOF
# Managed by temperature-hub/scripts/configure-host.sh
local-service
address=/${DOMAIN}/${LAN_IP}
EOF

    systemctl enable dnsmasq
    systemctl restart dnsmasq
}

issue_certificate_if_needed() {
    if [ -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ] && [ -f "/etc/letsencrypt/live/${DOMAIN}/privkey.pem" ]; then
        return
    fi

    if [ ! -f "$CLOUDFLARE_CREDENTIALS" ]; then
        echo "Cloudflare credentials not found at ${CLOUDFLARE_CREDENTIALS}; skipping certificate issuance."
        echo "Create that file from data/secrets/cloudflare.ini.example, chmod it 600, then rerun ./update.sh."
        return
    fi

    chmod 600 "$CLOUDFLARE_CREDENTIALS"

    local email_args=(--register-unsafely-without-email)
    if [ -n "$CERTBOT_EMAIL" ]; then
        email_args=(--email "$CERTBOT_EMAIL")
    fi

    certbot certonly \
        --non-interactive \
        --agree-tos \
        "${email_args[@]}" \
        --dns-cloudflare \
        --dns-cloudflare-credentials "$CLOUDFLARE_CREDENTIALS" \
        --dns-cloudflare-propagation-seconds 60 \
        -d "$DOMAIN"
}

configure_nginx() {
    install -d -m 0755 /etc/nginx/sites-available /etc/nginx/sites-enabled

    if [ -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ] && [ -f "/etc/letsencrypt/live/${DOMAIN}/privkey.pem" ]; then
        cat > /etc/nginx/sites-available/temperature-hub <<EOF
# Managed by temperature-hub/scripts/configure-host.sh
server {
    listen 80;
    server_name ${DOMAIN};

    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl;
    server_name ${DOMAIN};

    ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;

    location / {
        proxy_pass ${UPSTREAM};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
EOF
    else
        cat > /etc/nginx/sites-available/temperature-hub <<EOF
# Managed by temperature-hub/scripts/configure-host.sh
server {
    listen 80;
    server_name ${DOMAIN};

    location / {
        proxy_pass ${UPSTREAM};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto http;
    }
}
EOF
    fi

    ln -sf /etc/nginx/sites-available/temperature-hub /etc/nginx/sites-enabled/temperature-hub
    rm -f /etc/nginx/sites-enabled/default

    nginx -t
    systemctl enable nginx
    systemctl reload nginx || systemctl restart nginx
}

configure_certbot_renewal_hook() {
    install -d -m 0755 /etc/letsencrypt/renewal-hooks/deploy
    cat > /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh <<'EOF'
#!/bin/sh
systemctl reload nginx
EOF
    chmod 0755 /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
}

install_packages
configure_dnsmasq
issue_certificate_if_needed
configure_nginx
configure_certbot_renewal_hook

echo "Host configuration complete for ${DOMAIN} -> ${UPSTREAM} with local DNS ${DOMAIN} -> ${LAN_IP}."
