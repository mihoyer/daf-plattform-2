#!/bin/bash
# ============================================================
# DaF Sprachdiagnostik v2 – Deployment-Skript
# Läuft auf dem bestehenden DigitalOcean Droplet
# Subdomain: daf-plattform-2.mikehoyer.de  |  Port: 8002
# ============================================================
set -e

APP_DIR="/var/www/daf-plattform-2"
SERVICE="daf-plattform-2"
NGINX_CONF="/etc/nginx/sites-available/daf-plattform-2"
DOMAIN="daf-plattform-2.mikehoyer.de"

echo "=== DaF Plattform v2 Deployment ==="

# 1. Verzeichnis anlegen und Dateien kopieren
echo "[1/8] Anwendungsverzeichnis vorbereiten..."
mkdir -p "$APP_DIR"
cp -r . "$APP_DIR/"
chown -R www-data:www-data "$APP_DIR"

# 2. Python-Umgebung einrichten
echo "[2/8] Python-Umgebung einrichten..."
cd "$APP_DIR"
python3 -m venv venv
venv/bin/pip install --upgrade pip -q
venv/bin/pip install -r requirements.txt -q

# 3. .env prüfen
echo "[3/8] Konfiguration prüfen..."
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo "⚠️  WICHTIG: Bitte .env anpassen: nano $APP_DIR/.env"
fi

# 4. Upload-Verzeichnis
echo "[4/8] Upload-Verzeichnis anlegen..."
mkdir -p /tmp/daf_v2_uploads
chown www-data:www-data /tmp/daf_v2_uploads

# 5. Systemd-Service installieren
echo "[5/8] Systemd-Service installieren..."
cp "$APP_DIR/scripts/daf-plattform-2.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable "$SERVICE"

# 6. Nginx konfigurieren
echo "[6/8] Nginx konfigurieren..."
cp "$APP_DIR/scripts/nginx-daf-plattform-2.conf" "$NGINX_CONF"
ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/daf-plattform-2
nginx -t && systemctl reload nginx

# 7. Service starten
echo "[7/8] Service starten..."
systemctl restart "$SERVICE"
sleep 2
systemctl status "$SERVICE" --no-pager | head -10

# 8. HTTPS einrichten (interaktiv)
echo "[8/8] HTTPS mit Certbot einrichten..."
echo ""
echo "Führen Sie jetzt aus:"
echo "  certbot --nginx -d $DOMAIN"
echo ""
echo "=== Deployment abgeschlossen ==="
echo "Die Anwendung läuft auf: http://$DOMAIN"
echo "Nach Certbot: https://$DOMAIN"
echo ""
echo "Nächste Schritte:"
echo "  1. nano $APP_DIR/.env  (OPENAI_API_KEY und ADMIN_PASSWORD eintragen)"
echo "  2. systemctl restart $SERVICE"
echo "  3. certbot --nginx -d $DOMAIN"
