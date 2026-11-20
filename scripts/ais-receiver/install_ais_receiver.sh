#!/bin/bash
# =====================================================================
# A Budapesti AIS-vevo telepítese — a Raspberry Pi 3B+-on
# =====================================================================
# A "vessel-tracker" projekt R1-0 elokeszito fazisanak elso lepese.
#
# Ez a script:
#   1. telepiti a rtl-sdr csomagot (rtl_test, rtl_ais, rtl_tcp)
#   2. letiltja a DVB-T drivert (kulonben a kernel lefoglalja a donglet)
#   3. telepiti a Rust-alapú AIS-catcher-t (forrasbol, ARM64-re)
#   4. leterkepezi a systemd unitot (boot után auto-indul)
#   5. beallitja a helyi SQLite archivalat (14 napos retention)
#
# A SCRIPT NEM inditja el a vevot — az utan kulon ellenorzodik a
# donglet, kalibralodik a ppm, es csak UTANA inditod el.
#
# Hasznalat:  sudo bash install_ais_receiver.sh
# =====================================================================

set -euo pipefail

# --- a konfiguracio ---
SITE_CODE="${SITE_CODE:-bud01}"          # a telephely kodo
DB_DIR="${DB_DIR:-/var/lib/ais}"
CONFIG_DIR="${CONFIG_DIR:-/etc/ais-receiver}"
USER_NAME="${USER_NAME:-ais}"
BUILD_DIR="${BUILD_DIR:-/tmp/AIS-catcher-build}"

log() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------------
log "1/6 — a rtl-sdr telepitese"
if ! dpkg -s rtl-sdr >/dev/null 2>&1; then
    apt-get update
    apt-get install -y --no-install-recommends \
        rtl-sdr git make gcc g++ cmake pkg-config \
        libsqlite3-dev libssl-dev zlib1g-dev librtlsdr-dev
else
    log "    a rtl-sdr mar telepitve"
fi

# A rtl-sdr a Raspberry Pi OS-en kulon repository-bol jon —
# ha nem sikerul, a felhasznalo hozza adja a forrasot.
if ! command -v rtl_test >/dev/null 2>&1; then
    warn "a rtl_test nem található."
    warn "Ha a 'sudo apt install rtl-sdr' nem mukodott (a Pi OS-en a"
    warn "rtl-sdr külön repository-ból jön):"
    warn "  1. a /etc/apt/sources.list.d/ -ba addd a rtl-sdr forrasot,"
    warn "  2. sudo apt install rtl-sdr"
    warn "  3. a 'rtl_ais' probahoz anélkül is mehet: apt install ais-catcher"
fi

# ---------------------------------------------------------------------
log "2/6 — a DVB-T driver letiltasa (a kernel lefoglalja a donglet!)"
mkdir -p /etc/modprobe.d
cat > /etc/modprobe.d/rtl-sdr-blacklist.conf <<'EOF'
# A Raspberry Pi OS-ben a DVB-T driver lefoglalja az RTL2832U-t.
# A blacklisztel masoldja mar van a /etc/modprobe.d/ -ben.
blacklist dvb_usb_rtl28xxu
blacklist rtl2832
blacklist e4000
EOF

# a mar meglevo blacklisteket is kommenteljuk ki, hogy ne legyenek ellentmondasok
for f in /etc/modprobe.d/*blacklist*.conf /etc/modprobe.d/raspi-blacklist*.conf; do
    [ -f "$f" ] || continue
    [ "$f" = "/etc/modprobe.d/rtl-sdr-blacklist.conf" ] && continue
    if grep -q "dvb_usb_rtl28xxu" "$f" 2>/dev/null; then
        warn "a $f is blacklisztelja a donglet — rendben"
    fi
done

# a blacklista utan a modul ki- és visszatoltesre kell
modprobe -r dvb_usb_rtl28xxu 2>/dev/null || true
modprobe -r rtl2832 2>/dev/null || true
modprobe -r e4000 2>/dev/null || true

# ---------------------------------------------------------------------
log "3/6 — az AIS-catcher buildelése (forrasbol, ARM64)"
if command -v AIS-catcher >/dev/null 2>&1; then
    log "    az AIS-catcher mar telepitve: $(AIS-catcher -v 2>&1 | head -1)"
else
    [ -d "$BUILD_DIR" ] || git clone --depth 1 \
        https://github.com/jvde-github/AIS-catcher.git "$BUILD_DIR"
    cd "$BUILD_DIR"
    mkdir -p build && cd build
    # a WEBVIEWER ON: a helyi ellenorzodeshez kell a web-térkep (-N)
    cmake .. -DCMAKE_BUILD_TYPE=Release
    make -j"$(nproc)"
    make install
    ldconfig
    log "    a build kesz: $(AIS-catcher -v 2>&1 | head -1)"
fi

# ---------------------------------------------------------------------
log "4/6 — a felhasznalo es a konyvtarak"
if ! id "$USER_NAME" >/dev/null 2>&1; then
    useradd --system --no-create-home --shell /usr/sbin/nologin "$USER_NAME"
    log "    a '$USER_NAME' rendszerfelhasznalo letrehozva"
fi

mkdir -p "$DB_DIR" "$CONFIG_DIR"
chown -R "$USER_NAME":"$USER_NAME" "$DB_DIR" "$CONFIG_DIR"
chmod 750 "$DB_DIR"

# ---------------------------------------------------------------------
log "5/6 — a systemd unit"
cat > /etc/systemd/system/ais-receiver.service <<EOF
[Unit]
Description=AIS-vevo (${SITE_CODE}) — vessel-tracker R1-0
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${USER_NAME}
Group=${USER_NAME}
WorkingDirectory=${DB_DIR}
ExecStart=/usr/bin/AIS-catcher -E ${CONFIG_DIR}/config.json
Restart=always
RestartSec=10
# a hardveres hibat nem kell folytonosan ujrainditani
StartLimitIntervalSec=300
StartLimitBurst=5

# a hardver gyors elerhetesegere
SupplementaryGroups=plugdev
Nice=-5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
log "    a unit letolthetve (a systemctl enable a PPM beallitasa UTAN)"

# ---------------------------------------------------------------------
log "6/6 — a konfiguracio (a PPM placeholder)"
cat > "${CONFIG_DIR}/config.json" <<EOF
{
  "_comment": "A PPM_ERT 'PPM_HELYSETT' - a rtl_test -p utani erteket masold be, majd inditsd újra a servicet.",
  "rtl": {
    "sdr": "RTLSDR",
    "device": 0,
    "centerfreq": 162000000,
    "ppm_error": 0,
    "gain": 20,
    "agc": true,
    "antenna": "SMA"
  },
  "ais": {
    "output": true,
    "output_nmea": true,
    "output_json": true,
    "gnz": 4,
    "filters": "161.975M,162.025M"
  },
  "network": {
    "_comment": "A mQTT kimenet a 30 napos MERESHEZ nem kell — a helyi SQLite a meresi adat. Amikor elindul a kozponti ingest, ezt a blokkot kell kitolteni.",
    "enabled": false
  },
  "server": {
    "port": 8080
  }
}
EOF

chown -R "$USER_NAME":"$USER_NAME" "$CONFIG_DIR"
chmod 640 "${CONFIG_DIR}/config.json"

echo
log "KESZ."
echo
echo "A KOVETKEZO LEPESEK:"
echo "  1. Ellenorizd a donglet:      rtl_test -t"
echo "     (a várt: 'Found Rafael Micro R820T tuner')"
echo "  2. Kalibralj (10 perc):       rtl_test -p"
echo "     (a vegeredmény: 'ppm correction: X.Y ppm' — JEGYZD FEL)"
echo "  3. Ird be a PPM-ot:           sudo nano ${CONFIG_DIR}/config.json"
echo "     (a 'ppm_error' mezőbe)"
echo "  4. Inditsd el:                sudo systemctl start ais-receiver"
echo "  5. Ellenorizd a weben:        http://\$(hostname -I | awk '{print \$1}'):8080"
echo "  6. A belvizi FI 10 ellenorzese (a tetőn vagy a vizparton!)"
echo
echo "A UNIT AUTOMATIKUS INDITASA:"
echo "  sudo systemctl enable ais-receiver"
