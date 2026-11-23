#!/bin/bash
# =====================================================================
# A 30 napos AIS-merés indítása a budapesti AIS-vevőn
# =====================================================================
# Az AIS-catcher v0.71 CLI szintaxisa (a 2026-11-22-i próba alapján):
#
#   AIS-catcher -d:0 -s 1536K -a 192K -p <ppm> -o 3 \
#                -D sqlite:<fajl> [tabla-kapcsolok]
#
# FONTOS: a "-gr ..." opció a v0.71-ben NEM működik ("syntax error") —
# a tuner beállítások a config.json "rtl" blokkjában adhatók meg.
# A "-d:0" önmagában kiválasztja az eszközt, a gain automatikus.
#
# A "-D" utáni módosítók (a DB tábláinak kapcsolója):
#   STATION_ID 1  V ON  MSGS ON  NMEA ON  POSITION ON  STATIC ON
#
# A SQLite kimenet a mérési adathalmaz — a helyi fájl a kiesés
# elleni tartalek, a heti lehuzas utan offline feldolgozzuk.
#
# Hasznalat:  sudo bash start_measurement.sh
# =====================================================================

set -euo pipefail

SITE_CODE="${SITE_CODE:-bud01}"
DB_DIR="${DB_DIR:-/var/lib/ais}"
CONFIG_DIR="${CONFIG_DIR:-/etc/ais-receiver}"
DB_FILE="${DB_FILE:-${DB_DIR}/ais.db}"
USER_NAME="${USER_NAME:-ais}"
NAS_TARGET="${NAS_TARGET:-modmj@192.168.0.135}"
NAS_PATH="${NAS_PATH:-/opt/data/martin/work/ais-data}"

log()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }

# ---------------------------------------------------------------------
log "1/5 — a PPM-ertek"
# A sorrend: a PPM env-variablo > a config.json > a kerdes
PPM="${PPM:-}"
if [ -z "$PPM" ]; then
    PPM=$(grep -oP '"ppm_error"\s*:\s*\K-?[0-9.]+' "${CONFIG_DIR}/config.json" 2>/dev/null || echo "")
fi
if [ -z "$PPM" ] || [ "$PPM" = "0" ]; then
    if [ -t 0 ]; then
        warn "a ppm_error 0 vagy nincs beallitva."
        warn "Ha nem kalibraltad meg a donglet, a dekodolas gyenge lesz."
        warn "A kalibracio: sudo rtl_test -p > /tmp/ppm.txt  (10 perc)"
        read -rp "  A ppm-ertek (vagy 0, ha meg nem kalibralt): " PPM
    else
        warn "a ppm_error nincs beallitva es nincs interaktiv terminal."
        warn "A PPM env-variabbal lehet megadni:  PPM=8 sudo bash start_measurement.sh"
        PPM=0
    fi
    [ -z "$PPM" ] && PPM=0
fi
log "    a ppm_error: ${PPM}"

# ---------------------------------------------------------------------
log "2/5 — a felhasznalo és a konyvtarak"
if ! id "$USER_NAME" >/dev/null 2>&1; then
    sudo useradd --system --no-create-home --shell /usr/sbin/nologin "$USER_NAME"
    log "    a '$USER_NAME' rendszerfelhasznalo letrehozva"
fi
sudo mkdir -p "$DB_DIR"
sudo chown -R "$USER_NAME":"$USER_NAME" "$DB_DIR"
sudo chmod 750 "$DB_DIR"

# a sqlite3 CLI (a meres ellenorzesehez) — ha meg nincs
if ! command -v sqlite3 >/dev/null 2>&1; then
    log "    a sqlite3 CLI telepitese"
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq sqlite3 \
        >/dev/null 2>&1 || warn "a sqlite3 telepites nem sikerult"
fi

# **A DB SEMA betoltes** (a v0.71-ben a schema KULON SQL fajl —
# a "DBMS: cannot prepare statements, is the schema loaded?" hiba
# a hianyzo schema miatt van). A fajl az AIS-catcher forrasaban van.
SCHEMA_SQL=""
for c in /usr/local/share/ais-catcher/create_sqlite.sql \
         /usr/local/share/AIS-catcher/create_sqlite.sql \
         /usr/share/ais-catcher/create_sqlite.sql \
         /opt/ais-catcher/create_sqlite.sql; do
    [ -f "$c" ] && SCHEMA_SQL="$c" && break
done
if [ -z "$SCHEMA_SQL" ]; then
    # a build konyvtarabol (a forras a /tmp/AIS-catcher-build alatt van)
    SCHEMA_SQL=$(find /tmp/AIS-catcher-build /opt -name "create_sqlite.sql" 2>/dev/null | head -1)
fi
if [ -n "$SCHEMA_SQL" ] && [ -f "$SCHEMA_SQL" ]; then
    log "    a DB schema betoltese: $SCHEMA_SQL"
    sudo sqlite3 "$DB_FILE" < "$SCHEMA_SQL"
else
    warn "a create_sqlite.sql nem talalhato — a DB semaja manualis"
fi

# ---------------------------------------------------------------------
log "3/5 — a config.json"
sudo mkdir -p "$CONFIG_DIR"
sudo tee "${CONFIG_DIR}/config.json" > /dev/null <<EOF
{
  "_comment": "A 30 napos MERES — a helyi SQLite a mérési adathalmaz.",
  "_ppm": "A ppm_error a rtl_test -p kalibrációból (${PPM})",
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
sudo chown "$USER_NAME":"$USER_NAME" "${CONFIG_DIR}/config.json"
sudo chmod 640 "${CONFIG_DIR}/config.json"

# ---------------------------------------------------------------------
log "4/5 — a systemd unit"
sudo tee /etc/systemd/system/ais-receiver.service > /dev/null <<EOF
[Unit]
Description=AIS-vevo (${SITE_CODE}) — vessel-tracker R1-0 MERES
After=network-online.target
Wants=network-online.target
# a systemd a [Unit] szakaszban fogadja ezeket (a [Service]-ben
# figyelmeztetve eldobja) — a prof finding alapjan javitva
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
User=${USER_NAME}
Group=${USER_NAME}
WorkingDirectory=${DB_DIR}

# A -D sqlite: a helyi archival (a mérési adathalmaz).
#
# A v0.71-es SEMA (a Source/DBMS/DatabaseOutput.cpp szerint):
#   state     = a hajoallapot (a legutobb ismert adat hajonkent)
#   position  = a pozicio uzenetek (Msg 1/3/18/19/27)
#   static    = a statikus uzenetek (Msg 5/24 + az inland FI 10)
#   nmea      = a nyers NMEA mondatok
#   stats     = a fogadasi statisztikak
#
# A REGI nevek (V, MSGS, VP, VS, BS, SAR, ATON) ELTUNTEK — a
# program hibával leall, ha ezeket kapja:
#   "DBMS: this setting was removed with the new schema, use ... instead"
#
# A DB-kimenet a CLI "-D" parametereivel (a v0.71-es UJ nevek:
# a regi "V ON MSGS ON" helyett "state ON position ON static ON
# nmea ON" — a program elall a regi nevekkel).
#
# A "-o 0" (quiet) — a naplo nem irja ki minden uzenetet (a nyers
# NMEA a DB-be megy).
# A "-M TD" a fogadasi timestampet (T) ES a decoder-metaadatot (D:
# signalpower, ppm) kapcsolja be — a v0.71 a "-M" opcio EGY
# argumentumban varja a ket betut ("-M TD"), nem ket kulonben.
#
# MEGJEGYZES (2026-11-22): a v0.71-ben a DBMS a TAG.level-t a
# JSON-stream utvonalon nem kapja meg, ezert a "signal_level" es a
# "signalpower" oszlop 0 marad a DB-ben (a jelerosseg a stdout JSON-
# ban van, a "-o 3" mellett). A meres szempontjabol ez nem kritikus:
# a szuro kivalasztasa a 30 napos adathalmazbol, a msg/hajo aranybol
# dontendő el.
ExecStart=/usr/local/bin/AIS-catcher -d:0 -s 1536K -a 192K -p ${PPM} \
  -o 0 -M TD \
  -D sqlite:${DB_FILE} STATION_ID 1 RETENTION 35 \
  NMEA ON POSITION ON STATIC ON STATE ON STATS ON

Restart=always
RestartSec=10
SupplementaryGroups=plugdev
Nice=-5

# A BOOT UTANI LEHUZAS (a 2026-11-23-i valtozas)
# A Pi este kikapcsol es reggel 8-kor indul -> a fix 04:17-es cron
# SOHA nem futna -> a lehuzas a service indulasa UTAN megy.
# Az ExecStartPost nem blokkolja a service-t (a "-" prefix: a hiba
# nem allitja le a unitot).
ExecStartPost=-/usr/local/bin/ais-pull-after-boot.sh

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload

# ---------------------------------------------------------------------
log "5/5 — a heti lemezhuzas"
# A heti lehuzas: Pi --> NAS DIREKT (a Mac nem lehet a lancban, mert
# nem mindig van bekapcsolva; a NAS amugy is elerheto a Pirol, 4,5 ms).
#
# A NAS-on a Pi kulcs "command=" korlatozassal fut: csak a
# /usr/local/bin/nas-receive-ais.sh hajthato, a DB masolat a standard
# inputon erkezik.
#
# A script maga a NAS-on van (nem innen masoljuk) — a helye:
#   NAS: /usr/local/bin/nas-receive-ais.sh
#   Pi:  /usr/local/bin/ais-fetch-weekly.sh
#
# A Pi oldali kulcs: ~/.ssh/ais_pull_key (a NAS authorized_keys-en
# a command= korlatozassal).
if [ ! -f "$HOME/.ssh/ais_pull_key" ]; then
    warn "a lehuzas kulcs hianyzik ($HOME/.ssh/ais_pull_key)"
    warn "generalj egy kulcsot: ssh-keygen -t ed25519 -N '' -C 'ais-pull@bud01' -f ~/.ssh/ais_pull_key"
    warn "es add hozza a NAS-on (hermesadmin) a command= korlatozassal:"
    warn "  command=\"sudo -n /usr/local/bin/nas-receive-ais.sh\" ... $(cat "$HOME/.ssh/ais_pull_key.pub" 2>/dev/null || echo '<a publikus kulcs>')"
fi

sudo tee /etc/cron.d/ais-fetch > /dev/null <<EOF
# a nyers AIS-adat heti lehuzasa a meres idejere (Pi -> NAS direkt)
#
# A UTEM: **a boot UTAN** (nem egy fix oraban) — a Pi este kikapcsol
# es reggel 8-kor indul -> a fix 04:17-es cron soha nem futna.
# A cron a heti *biztonsagi* lehuzast adja (a service indulasa kozben
# is mehet), a Fo lehuzas a systemd unit ExecStartPost-jaban van.
17 4 * * 1 ${USER_NAME} DB_FILE=/var/lib/ais/ais.db /usr/local/bin/ais-fetch-weekly.sh
EOF
sudo chmod 644 /etc/cron.d/ais-fetch

# --- a boot UTANI lehuzas (a systemd ExecStartPost) ---
# A Pi ejszaka ki van kapcsolva -> a fix oras cron nem mukodik.
# A lehuzas a SERVICE indulasa UTAN fut (a vevo elindulasa nem
# var a lehuzasra, es a lehuzas nem var a vevore -> a sorrend jo).
sudo tee /usr/local/bin/ais-pull-after-boot.sh > /dev/null <<'BOOTEOF'
#!/bin/bash
# A heti lehuzas a service indulasa utan (a Pi ejszaka ki van kapcsolva).
set -u
# A log a sajat home-jaba megy — a "miklos" user nem tud irni a
# /var/log-ba (a 2026-11-23-i teszt: a /var/log/ais-pull.log nem jott
# letre, a sudo nelkul nem is irhato)
LOG="${LOG:-$HOME/.ais-pull.log}"
DB_FILE="${DB_FILE:-/var/lib/ais/ais.db}"
export DB_FILE

# a service keszen all-e? (a vevonek mar be kell indulnia)
for i in $(seq 1 12); do
    if [ -f "$DB_FILE" ] && [ -s "$DB_FILE" ]; then break; fi
    sleep 10
done

{
    echo "--- $(date '+%F %T') a boot utani lehuzas indul ---"
    /usr/local/bin/ais-fetch-weekly.sh
    echo "--- $(date '+%F %T') a boot utani lehuzas vege (a stausz: $?) ---"
} >> "$LOG" 2>&1
BOOTEOF
sudo chmod 755 /usr/local/bin/ais-pull-after-boot.sh

# ---------------------------------------------------------------------
sudo systemctl enable ais-receiver
sudo systemctl restart ais-receiver
sleep 6

if systemctl is-active --quiet ais-receiver; then
    log "KESZ — a vevo fut."
else
    warn "A vevo NEM indult el. A naplo:"
    sudo journalctl -u ais-receiver -n 30 --no-pager
    exit 1
fi

IP=$(hostname -I | awk '{print $1}')
echo
log "KESZ."
echo
echo "A helyi ellenorzodes:"
echo "  http://${IP}:8080          — a web-terkep es a szurok"
echo "  sudo sqlite3 ${DB_FILE} 'SELECT count(*) FROM ais_message;'"
echo "  sudo journalctl -u ais-receiver -f"
echo
echo "A 30 NAPOS MERES ELINDULT: $(date '+%Y-%m-%d %H:%M')"
echo "A heti lemezhuzas: minden hetfon 04:17-kor -> ${NAS_TARGET}:${NAS_PATH}"
