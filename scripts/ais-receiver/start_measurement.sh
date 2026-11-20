#!/bin/bash
# =====================================================================
# A 30 napos meres indítása a budapesti AIS-vevon
# =====================================================================
# Ez a script a MERESI ÜZEMMÓDOT állítja be:
#   - a helyi SQLite archivalat (a mérési adathalmaz)
#   - a nyers NMEA + üzenet + pozíció táblákat
#   - a heti lemezhuzást (a 14 napos retention miatt!)
#
# FONTOS: az AIS-catcher v0.71-ben a -D kimenet ÚJRAÍRÓDOTT.
# A regi forma ("station_id 1 position on static on nmea on
# unique on position_interval 60 retention 14") NEM MUKODIK.
# Az uj forma egy kimeneti konfiguracio:
#
#   -D sqlite:/var/lib/ais/ais.db STATION_ID 1 V ON MSGS ON NMEA ON VP ON VS ON
#
# A tabla-nevek (a v0.71 szerint):
#   V    -> ais_vessel        (az utolso adatok hajonkent)
#   MSGS -> ais_message       (a fogadott uzenetek a metaadatokkal)
#   NMEA -> ais_nmea          (a nyers NMEA mondatok)
#   VP   -> ais_vessel_pos    (a pozicio uzenetek)
#   VS   -> ais_vessel_static (a statikus uzenetek)
#
# Hasznalat:  sudo bash start_measurement.sh
# =====================================================================

set -euo pipefail

SITE_CODE="${SITE_CODE:-bud01}"
DB_DIR="${DB_DIR:-/var/lib/ais}"
CONFIG_DIR="${CONFIG_DIR:-/etc/ais-receiver}"
DB_FILE="${DB_FILE:-${DB_DIR}/ais.db}"
USER_NAME="${USER_NAME:-ais}"

log() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }

# ---------------------------------------------------------------------
log "1/4 — a PPM-ertek beolvasasa a konfiguracioból"
PPM=$(grep -oP '"ppm_error"\s*:\s*\K-?[0-9.]+' "${CONFIG_DIR}/config.json" || echo "")
if [ -z "$PPM" ] || [ "$PPM" = "0" ]; then
    warn "a ppm_error 0 vagy nincs beallitva."
    warn "Ha nem kalibraltad meg a donglet, a dekodolas gyenge lesz."
    warn "A kalibracio: rtl_test -p  (10 perc, nyugodtan futnia kell)"
    read -rp "  A ppm-ertek (vagy 0, ha meg nem kalibralt): " PPM
    [ -z "$PPM" ] && PPM=0
    # beirjuk a konfiguracioba
    sed -i "s/\"ppm_error\":\s*-*[0-9.]*/\"ppm_error\": ${PPM}/" "${CONFIG_DIR}/config.json"
    log "    a ppm_error beallitva: ${PPM}"
else
    log "    a ppm_error: ${PPM}"
fi

# ---------------------------------------------------------------------
log "2/4 — a meresi konfiguracio"
cat > "${CONFIG_DIR}/config.json" <<EOF
{
  "_comment": "A 30 napos MERES — a helyi SQLite a mérési adathalmaz.",
  "_ppm": "A ppm_error a rtl_test -p kalibrációból (${PPM})",
  "_retention": "A heti lemezhuzas miatt a fenti retention 35 nap — a 30 napos meres teljes adathalmaza megmaradjon.",
  "rtl": {
    "sdr": "RTLSDR",
    "device": 0,
    "centerfreq": 162000000,
    "ppm_error": ${PPM},
    "gain": 20,
    "agc": true
  },
  "ais": {
    "output": true,
    "output_nmea": true,
    "output_json": true,
    "gnz": 4,
    "filters": "161.975M,162.025M"
  },
  "network": {
    "_comment": "A meres idejere KIKAPCSOLVA — a kozponti ingest a 30 nap UTAN indul.",
    "enabled": false
  },
  "server": {
    "port": 8080
  }
}
EOF
chown "${USER_NAME}:${USER_NAME}" "${CONFIG_DIR}/config.json"
chmod 640 "${CONFIG_DIR}/config.json"

# ---------------------------------------------------------------------
log "3/4 — a systemd unit a meresre (a SQLite kimenettel)"
cat > /etc/systemd/system/ais-receiver.service <<EOF
[Unit]
Description=AIS-vevo (${SITE_CODE}) — vessel-tracker R1-0 MERES
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${USER_NAME}
Group=${USER_NAME}
WorkingDirectory=${DB_DIR}

# A -D sqlite: a helyi archival (a mérési adathalmaz).
# V    = hajoallapot, MSGS = minden uzenet, NMEA = nyers mondatok,
# VP   = poziciok, VS = statikus adatok.
# A "retention 35" a 30 napos meres teljes adathalmazának megmaradasa.
ExecStart=/usr/bin/AIS-catcher -E ${CONFIG_DIR}/config.json \\
  -D sqlite:${DB_FILE} STATION_ID 1 V ON MSGS ON NMEA ON VP ON VS ON \\
  RETENTION 35

Restart=always
RestartSec=10
StartLimitIntervalSec=300
StartLimitBurst=5
SupplementaryGroups=plugdev
Nice=-5

# a lemezhuzas nem allitja le a vevot
ExecStopPost=/usr/local/bin/ais-fetch-weekly.sh

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
log "    a unit frissitve"

# ---------------------------------------------------------------------
log "4/4 — a heti lemezhuzas (a 14 napos retention miatt KELL)"
cat > /usr/local/bin/ais-fetch-weekly.sh <<'EOF'
#!/bin/bash
# A nyers adat hetente lehuzasa a Pi-rol (a 30 napos meres adathalmaza).
# A NAS-cim a REPO-BAN cserelendő (a hálózati ut a Mi hostunk).
NAS_TARGET="${NAS_TARGET:-modmj@192.168.1.205}"
NAS_PATH="${NAS_PATH:-/opt/data/martin/work/ais-data}"
DB_FILE="${DB_FILE:-/var/lib/ais/ais.db}"
STAMP=$(date +%Y%m%d-%H%M)

mkdir -p "$NAS_PATH"
# az sqlite konzisztens masolata (a WAL-ot is atvisszuk)
sqlite3 "$DB_FILE" ".backup '/tmp/ais-${STAMP}.db'" 2>/dev/null \
  || cp "$DB_FILE" "/tmp/ais-${STAMP}.db"
scp -q "/tmp/ais-${STAMP}.db" "${NAS_TARGET}:${NAS_PATH}/" \
  && echo "$(date '+%F %T') a heti lemezhuzas kesz: ais-${STAMP}.db" \
  && rm -f "/tmp/ais-${STAMP}.db"
EOF
chmod 755 /usr/local/bin/ais-fetch-weekly.sh

# a heti huzast cronbol is futtathatjuk (a ExecStopPost csak leallasnal fut)
cat > /etc/cron.d/ais-fetch <<EOF
# a nyers AIS-adat heti lehuzasa a meres idejere
17 4 * * 1 ${USER_NAME} NAS_TARGET=${NAS_TARGET:-modmj@192.168.1.205} /usr/local/bin/ais-fetch-weekly.sh
EOF
chmod 644 /etc/cron.d/ais-fetch

# ---------------------------------------------------------------------
systemctl enable ais-receiver
systemctl restart ais-receiver
sleep 5

if systemctl is-active --quiet ais-receiver; then
    log "KESZ — a vevo fut."
else
    warn "A vevo NEM indult el. A naplo:"
    journalctl -u ais-receiver -n 30 --no-pager
    exit 1
fi

IP=$(hostname -I | awk '{print $1}')
echo
log "KESZ."
echo
echo "A helyi ellenorzodes:"
echo "  http://${IP}:8080          — a web-terkep es a szurok"
echo "  sqlite3 ${DB_FILE}          — a nyers adat"
echo "  journalctl -u ais-receiver -f  — a naplo"
echo
echo "A 30 NAPOS MERES ELINDULT: $(date '+%Y-%m-%d %H:%M')"
echo "A heti lemezhuzas: minden hetfon 04:17-kor"
echo "A lehuzott fajlok: a NAS-on a NAS_PATH alatt"
