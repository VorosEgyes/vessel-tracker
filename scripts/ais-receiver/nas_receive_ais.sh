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
#
# --- A 2026-11-23-i valtozas: a Pi NYILVANOS KULCSA is kiir ---
# A cel: a NAS-on levo kulcs (hermes_nas_ed25519) a Pi-ra keruljon,
# hogy a NAS-rol (a hermes userrel) be lehessen lepni a Pi-ra.
# A Pi kulcsa mar a Pi-n van (a ~/.ssh/ais_pull_key) — a Pi a
# standard inputon kuldi a DB-t, a stdout pedig a fogado uzenete.
# A stdout-on a kulcs is mehet, a Pi cronja pedig feldolgozza.
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

# --- a Pi nyilvanos kulcsa a stdout-on (a NAS kulcs atvitele a Pi-ra) ---
# A Pi a sajat ~/.ssh/ais_pull_key parancsaban kuldi a kulcsot is,
# a fogado pedig ezzel a markerrel adja vissza.
if [ -n "${AIS_PULL_PUBKEY:-}" ]; then
    echo "AIS_PULL_PUBKEY_BEGIN"
    echo "$AIS_PULL_PUBKEY"
    echo "AIS_PULL_PUBKEY_END"
fi
