# Deployment-Anleitung – DaF Sprachdiagnostik v2

**Subdomain:** `daf-plattform-2.mikehoyer.de`  
**Port:** `8002` (läuft neben der alten Plattform auf Port 8001)  
**Datenbank:** SQLite (keine PostgreSQL-Abhängigkeit)

---

## Schritt 1: DNS bei Artfiles einrichten

Loggen Sie sich in Ihren Artfiles-Account ein und erstellen Sie einen neuen DNS-Eintrag:

| Typ | Name | Wert | TTL |
|-----|------|------|-----|
| A | `daf-plattform-2` | `<IHRE-DROPLET-IP>` | 300 |

Die Droplet-IP finden Sie im DigitalOcean Dashboard.

---

## Schritt 2: Dateien auf den Server übertragen

Verbinden Sie sich per SSH mit Ihrem Droplet:

```bash
ssh root@<IHRE-DROPLET-IP>
```

Laden Sie das ZIP-Archiv hoch und entpacken Sie es:

```bash
# Archiv hochladen (von Ihrem lokalen Rechner)
scp daf-plattform-2.zip root@<IHRE-DROPLET-IP>:/tmp/

# Auf dem Server: entpacken
unzip /tmp/daf-plattform-2.zip -d /var/www/
```

---

## Schritt 3: Deployment-Skript ausführen

```bash
cd /var/www/daf-plattform-2
chmod +x scripts/deploy.sh
bash scripts/deploy.sh
```

Das Skript installiert automatisch:
- Python Virtual Environment mit allen Abhängigkeiten
- Systemd-Service `daf-plattform-2` (Port 8002)
- Nginx-Konfiguration für die Subdomain

---

## Schritt 4: .env konfigurieren

```bash
nano /var/www/daf-plattform-2/.env
```

Mindestens diese Werte eintragen:

```env
OPENAI_API_KEY=sk-...
SECRET_KEY=langer-zufaelliger-string-min-32-zeichen
ADMIN_PASSWORD=sicheres-passwort
BASE_URL=https://daf-plattform-2.mikehoyer.de
```

Service neu starten:
```bash
systemctl restart daf-plattform-2
```

---

## Schritt 5: HTTPS mit Certbot einrichten

```bash
certbot --nginx -d daf-plattform-2.mikehoyer.de
```

Certbot ergänzt die Nginx-Konfiguration automatisch.

---

## Schritt 6: Test

```bash
# Service-Status prüfen
systemctl status daf-plattform-2

# Logs anzeigen
journalctl -u daf-plattform-2 --no-pager | tail -20

# Direkter Test
curl http://127.0.0.1:8002/
```

Die Plattform ist dann erreichbar unter: **https://daf-plattform-2.mikehoyer.de**

---

## Updates einspielen

```bash
cd /var/www/daf-plattform-2
# Neue Dateien hochladen, dann:
bash scripts/update.sh
```

---

## Admin-Bereich

- URL: `https://daf-plattform-2.mikehoyer.de/admin/login`
- Passwort: das in `.env` gesetzte `ADMIN_PASSWORD`

Im Admin-Bereich können Sie:
- Alle Test-Sessions einsehen
- Zugangscodes für Testgruppen erstellen
- Ergebnisse einzelner Kandidaten abrufen

---

## Troubleshooting

```bash
# Service-Status
systemctl status daf-plattform-2

# Logs
journalctl -u daf-plattform-2 -f

# Nginx-Fehler
nginx -t
journalctl -u nginx --no-pager | tail -20

# Port prüfen (beide Plattformen)
ss -tlnp | grep -E "8001|8002"
```

---

## Unterschiede zur alten Plattform (v1)

| Merkmal | v1 (Port 8001) | v2 (Port 8002) |
|---------|---------------|---------------|
| Datenbank | PostgreSQL | SQLite |
| M1 | Multiple-Choice | Progressiver Lückentext |
| Scoring | Gesamt-Score | Skill-Profil (12 Module) |
| Empfehlungen | Niveaustufe | Konkrete Schritte-Module |
| Subdomain | bestehend | daf-plattform-2.mikehoyer.de |
