#!/bin/bash
# =====================================================================
# A Pi nyers AIS-adatanak fogadasa a NAS-on (Artemis).
#
# A Pi a ~/.ssh/authorized_keys "command=" korlatozas miatt CSAK ezt
# a scriptet futtathatja ezzel a kulccsal. A DB masolat a standard
# inputon erkezik (a Pi igy kuldi: ssh ... < db).
#
# A "/volume1/docker/hermes/data" a hermes kontener "/opt/data"
# bind mountja — a fajl a martin mappajaban lesz elerheto.
# =====================================================================
set -u

DEST_DIR="/volume1/docker/hermes/data/martin/work/ais-data"
STAMP=$(date +%Y%m%d-%H%M)
TMP="/tmp/ais-${STAMP}.db"
DEST="${DEST_DIR}/ais-${STAMP}.db"

# --- a celmappa ---
if ! sudo -n mkdir -p "$DEST_DIR"; then
    echo "HIBA: a celmappa nem hozhato letre: $DEST_DIR" >&2
    exit 1
fi

# --- a befolyt adat ---
if ! cat > "$TMP"; then
    echo "HIBA: a befolyt adat olvasasa nem sikerult" >&2
    rm -f "$TMP"
    exit 1
fi

# --- a fajl atvitele ---
if ! sudo -n cp "$TMP" "$DEST"; then
    echo "HIBA: a masolas nem sikerult: $DEST" >&2
    rm -f "$TMP"
    exit 1
fi

# --- a jogosultsagok: a hermes felhasznalo olvashassa ---
sudo -n chown 10000:10000 "$DEST" 2>/dev/null || true
sudo -n chmod 644 "$DEST" 2>/dev/null || true

rm -f "$TMP"
echo "$(date '+%F %T') a heti lemezhuzas kesz: ${DEST}"
