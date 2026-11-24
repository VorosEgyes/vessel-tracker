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

# --- a TAKARITAS (a 2026-11-24) ---
# A NAS lemezen a lehuzott fajlok gyulnek (~109 MB/lehuzas a
# 37 oras meresben) -> a fajlokat TOROLNI kell.
#
# A "command=" korlatozas miatt a Pi csak EZT a scriptet futtathatja ->
# a takaritas itt, a fogadon belul tortenik (nem kell kulon cron).
#
# KET szabaly:
#
# 1. a ${RETENTION_DAYS} naposnál régebbi fajlok torolése
#    (a Pi oldalon a DB RETENTION 35 napot tart -> a NAS-on is 35)
#    → a 09 §7.3
#
# 2. a NAPI lehuzasok: a boot utani lehuzas MINDEN boot utan megy
#    (a Pi naponta bekapcsol) -> azonos napon tobb fajl is lehet
#    -> **csak a legutolbi marad**, a regiek torlodnek (a fajlnev
#    a STAMP-et tartalmazza: ais-YYYYMMDD-HHMM.db)
#
# A 2. szabaly fontos: a heti lehuzas eleg (a Pi a heti cronban is
# futtatja a biztonsagi hatos), a napi fajlok csak a lemezet hogyak.
KEEP_PER_DAY="${KEEP_PER_DAY:-1}"
RETENTION_DAYS="${RETENTION_DAYS:-35}"

# --- 1. a regek torlese ---
DELETED=$(sudo -n find "$DEST_DIR" -maxdepth 1 -name 'ais-*.db' -type f \
  -mtime "+${RETENTION_DAYS}" -print -delete 2>/dev/null | wc -l)
if [ "${DELETED:-0}" -gt 0 ]; then
    echo "$(date '+%F %T') a ${RETENTION_DAYS} naposnál régebbi fajlok torlove: ${DELETED}"
fi

# --- 2. az azonos napon csak a legutolbi fajl marad ---
DUPS=$(sudo -n find "$DEST_DIR" -maxdepth 1 -name 'ais-*.db' -type f \
  -printf '%f\n' 2>/dev/null | sed -E 's/^ais-([0-9]{8})-.*/\1/' \
  | sort | uniq -c | awk '$1 > 1 {print $2}')
for DAY in $DUPS; do
    OLDER=$(sudo -n find "$DEST_DIR" -maxdepth 1 -name "ais-${DAY}-*.db" -type f \
      -printf '%T@ %p\n' 2>/dev/null | sort -rn | tail -n +$((KEEP_PER_DAY + 1)) | cut -d' ' -f2-)
    for F in $OLDER; do
        sudo -n rm -f "$F" 2>/dev/null && echo "$(date '+%F %T') a ${DAY} nap regi fajlja torolve: $(basename "$F")"
    done
done


# --- a fajl atvitele ---
#
# A 2026-11-24-es teszt: egy URES stdin (a hiba vagy a lehuzas hiany)
# egy 0 bajtos fajlt hozott letre a NAS-on -> ezt nem szabad elmenteni
# (a heti ellenorzo a 0 bajtos fajlt is "lehuzott"-nak venné).
FILE_SIZE=$(wc -c < "$TMP")
if [ "${FILE_SIZE}" -lt 1024 ]; then
    echo "HIBA: a befolyt adat ures vagy túl kicsi (${FILE_SIZE} B) — a fajl nem lett elmentve" >&2
    rm -f "$TMP"
    exit 1
fi

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
