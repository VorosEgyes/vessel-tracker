#!/bin/bash
# =====================================================================
# A nyers AIS-adat heti lehuzasa a NAS-ra (bud01 -> Artemis).
#
# A lanc KEZDETBEN ugy nezett ki, hogy "Pi -> Mac -> NAS", de a Mac
# nem mindig van bekapcsolva, es a NAS amugy is elerheto a Pirol
# (a 192.168.0.207-es cim, 4,5 ms). Ezert a lanc most:
#
#     Pi --> NAS (direkt, SSH)
#
# A NAS-on a "command=" korlatozas miatt csak a
# /usr/local/bin/nas-receive-ais.sh futhat (a DB masolat a standard
# inputon erkezik).
# =====================================================================
set -u

NAS_HOST="192.168.0.207"
NAS_USER="hermesadmin"
NAS_PATH="/opt/data/martin/work/ais-data"
DB_FILE="${DB_FILE:-/var/lib/ais/ais.db}"
KEY="${KEY:-$HOME/.ssh/ais_pull_key}"
STAMP=$(date +%Y%m%d-%H%M)

if [ ! -f "$KEY" ]; then
    echo "HIBA: a lehuzas kulcs nem ltezik: $KEY" >&2
    exit 1
fi

# --- a Pi DB konzisztens masolata ---
#
# A DB fajl a "ais" felhasznalo tulajdona (0644), de a /var/lib/ais
# konyvtar 0750 (ais:ais) — ezert a "miklos" NEM latja. A megoldas:
# a masolatot a SAJAT, "miklos" altal irhato konyvtarba keszitjuk,
# a DB-t pedig sudo-val olvassuk.
#
# A "sudo" altatt futo sqlite3 a celfajlt a "miklos" tulajdonak
# allitja be (a -cmd "chown" utan), hogy a "miklos" is törölhesse.
WORK_DIR="$HOME/.ais-pull"
mkdir -p "$WORK_DIR"
TMP="${WORK_DIR}/ais-${STAMP}.db"
rm -f "$TMP" 2>/dev/null

if ! sudo -n sqlite3 "$DB_FILE" ".backup '${TMP}'"; then
    echo "HIBA: a DB masolasa nem sikerult" >&2
    sudo -n rm -f "$TMP" 2>/dev/null
    exit 1
fi

# a fajl a "miklos" tulajdona legyen (a masolas utan)
sudo -n chown "$(id -u):$(id -g)" "$TMP" 2>/dev/null || true
chmod 644 "$TMP" 2>/dev/null || true

# --- a NAS elerese: a fajl a standard inputon megy ---
if ! ssh -i "$KEY" -o BatchMode=yes -o StrictHostKeyChecking=no \
        -o ConnectTimeout=20 -o ServerAliveInterval=30 \
        "${NAS_USER}@${NAS_HOST}" < "$TMP"; then
    echo "HIBA: a NAS elerese nem sikerult" >&2
    rm -f "$TMP" 2>/dev/null || sudo -n rm -f "$TMP"
    exit 1
fi

rm -f "$TMP" 2>/dev/null || sudo -n rm -f "$TMP"
echo "$(date '+%F %T') a heti lemezhuzas kesz: ${NAS_PATH}/ais-${STAMP}.db"
