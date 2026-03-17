#!/bin/bash
# Aktualisierungs-Skript für DaF Plattform v2
set -e

APP_DIR="/var/www/daf-plattform-2"
SERVICE="daf-plattform-2"

echo "=== DaF Plattform v2 Update ==="

# Backup der Datenbank
echo "[1/4] Datenbank-Backup..."
cp "$APP_DIR/daf_plattform_v2.db" "/root/backup-daf-v2-$(date +%Y%m%d-%H%M).db" 2>/dev/null || true

# Dateien aktualisieren (ohne .env und Datenbank zu überschreiben)
echo "[2/4] Dateien aktualisieren..."
rsync -av --exclude='.env' --exclude='*.db' --exclude='venv/' . "$APP_DIR/"
chown -R www-data:www-data "$APP_DIR"

# Abhängigkeiten aktualisieren
echo "[3/4] Abhängigkeiten aktualisieren..."
cd "$APP_DIR"
venv/bin/pip install -r requirements.txt -q

# Service neu starten
echo "[4/4] Service neu starten..."
systemctl restart "$SERVICE"
sleep 2
systemctl status "$SERVICE" --no-pager | head -5

echo "=== Update abgeschlossen ==="
