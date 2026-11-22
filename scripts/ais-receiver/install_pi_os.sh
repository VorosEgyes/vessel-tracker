#!/bin/bash
# =====================================================================
# A Pi OS Lite (64-bit) telepitese a 32 GB-os SD-kartyara
# =====================================================================
# Az Imager CLI-vel (a letoltott app a /tmp/rpi-imager-mnt alatt).
#
# A hibrid OSlista nem elerheto a raspberrypi.com-on (a 404-es
# images.list), ezert a kepet KEZDOLAGOSAN toltjuk le a
# downloads.raspberrypi.com images/ alkonyvtarabol, a SHA-256
# ellenorzesével.
#
# Hasznalat:  bash install_pi_os.sh
# =====================================================================

set -euo pipefail

BASE="https://downloads.raspberrypi.com/raspios_lite_arm64/images"
# a legutobbi build — a script maga keresi meg a legfrissebbet
BUILD="${BUILD:-raspios_lite_arm64-2026-10-06}"
FILE="2026-10-06-raspios-trixie-arm64-lite.img.xz"
DEVICE="${DEVICE:-/dev/disk6}"
IMG_MOUNT="/tmp/rpi-imager-mnt"
IMG_BIN="${IMG_MOUNT}/Raspberry Pi Imager.app/Contents/MacOS/rpi-imager"
CACHE="/tmp/pi-os-cache"
LOG="/tmp/pi-imager.log"

# A 'sudo' alatt a PATH keskenyebb — a curl/diskutil/hdiutil is kell
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

log()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
err()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------------
log "1/6 — a build ellenorzese (a legfrissebb a listabol)"
ALL_BUILDS=$(curl -s "${BASE%/images}/images/" \
  | grep -oE 'href="raspios_lite_arm64-[0-9-]+/"' \
  | sed 's/href="//; s/"//' | sort)
LATEST=$(printf '%s\n' "$ALL_BUILDS" | tail -1)
log "    a legfrissebb build: $LATEST"
if [ -n "${BUILD:-}" ]; then
    log "    a keresett build: $BUILD"
    if ! printf '%s\n' "$ALL_BUILDS" | grep -q "^${BUILD}/$"; then
        warn "a '$BUILD' nem az utolso build — de hasznalhato"
    fi
fi

# a fajlnev a buildbol jon (a datum a build neveben van)
FILE=$(curl -s "${BASE}/${LATEST}/" \
  | grep -oE 'href="[0-9]{4}-[0-9]{2}-[0-9]{2}-raspios-[a-z]+-arm64-lite\.img\.xz"' \
  | head -1 | sed 's/href="//; s/"//')
[ -n "$FILE" ] || err "nem talaltam a kepet a $LATEST buildben"
URL="${BASE}/${LATEST}/${FILE}"
log "    a kep: $FILE"

# ---------------------------------------------------------------------
log "2/6 — a letoltes"
mkdir -p "$CACHE"
IMG="${CACHE}/${FILE%.xz}"
if [ ! -f "$IMG" ]; then
    if [ ! -f "${IMG}.xz" ]; then
        log "    a letoltes (~550 MB, a hálózattol fugg)"
        curl -L --progress-bar -o "${IMG}.xz" "$URL"
    fi
    log "    a kitomorolas"
    # A macOS-en nincs 'xz' — a Python standard 'lzma' moduljat
    # hasznaljuk (a shell scriptben hivas helyett egy kis helper).
    python3 - "$IMG.xz" "$IMG" <<'PYXZ'
import lzma, shutil, sys
src, dst = sys.argv[1], sys.argv[2]
print(f"    a kitomorolas: {src} -> {dst}")
with lzma.open(src) as f_in, open(dst, "wb") as f_out:
    shutil.copyfileobj(f_in, f_out, length=16 * 1024 * 1024)
PYXZ
fi
ls -la "$IMG" | awk '{print "    a kep:", $5, "byte"}'

# ---------------------------------------------------------------------
log "3/6 — a SHA-256 ellenorzes"
#
# FONTOS: a hivatalos .sha256 fajl a **TOMORITETT** kepre
# (img.xz) vonatkozik, nem a kitomorott img-re. Ezert a hash
# ellenorzest a .xz fajlon kell elvegezni.
SHA_URL="${URL}.sha256"
EXPECTED=$(curl -s "$SHA_URL" | awk '{print $1}')
XZ_FILE="${CACHE}/${FILE}"
if [ ! -f "$XZ_FILE" ]; then
    err "a tomoritet kep nem talalhato: $XZ_FILE"
fi
ACTUAL=$(shasum -a 256 "$XZ_FILE" | awk '{print $1}')
if [ -z "$EXPECTED" ]; then
    warn "a sha256 fajl nem elerheto — az ellenorzes kimarad"
elif [ "$EXPECTED" = "$ACTUAL" ]; then
    log "    a hash rendben (a tomoritet kep): $ACTUAL"
else
    err "a hash NEM egyezik!
  a varhato: $EXPECTED
  a tenyleges: $ACTUAL
  (a letoltes serult vagy modosult)"
fi

# ---------------------------------------------------------------------
log "4/6 — a cloud-init fajlok ellenorzese"
[ -f /tmp/cloudinit/user-data ] || err "nincs /tmp/cloudinit/user-data"
[ -f /tmp/cloudinit/network-config ] || err "nincs /tmp/cloudinit/network-config"
log "    a cloud-init fajlok keszen"

# ---------------------------------------------------------------------
log "5/6 — a lemez ellenorzese"
if [ ! -b "$DEVICE" ]; then
    err "a $DEVICE nem letezik (a kartyolvaso bedugva?)"
fi
# A "Disk Size: 31.9 GB (31914983424 Bytes)" sorbol a BAJTSZAM kell
# (a grep -oE '[0-9]+' a "31"-et hozna a tizedesvesszo elott)
DISK_SIZE=$(diskutil info "$DEVICE" \
  | grep "Disk Size" \
  | grep -oE '\([0-9]+ Bytes\)' \
  | grep -oE '[0-9]+' | head -1)
[ -z "$DISK_SIZE" ] && DISK_SIZE=$(diskutil info "$DEVICE" \
  | awk -F'[()]' '/Disk Size/ {split($2,a," "); print a[1]}')
log "    a lemez: $DEVICE ($DISK_SIZE byte)"
if [ -z "$DISK_SIZE" ] || [ "$DISK_SIZE" -lt 8000000000 ]; then
    err "a $DEVICE tulsag kicsi (${DISK_SIZE:-ismeretlen} byte) — nem ez a SD-karta?"
fi
CURRENT=$(diskutil info "$DEVICE" | grep "Volume Name" | sed 's/.*: *//' | tr -d ' ')
log "    a jelenlegi rendszer: ${CURRENT:-ismeretlen} — EZT FELULIRJUK"

# ---------------------------------------------------------------------
log "6/6 — a telepites (a rpi-imager CLI-vel)"
warn "A $DEVICE LE SZEM LEMEZRE IRASA — a meglevo rendszer TORLODIK."

cat <<EOF

  ┌──────────────────────────────────────────────────────────┐
  │  A telepites megindul:                                   │
  │    • a $DEVICE lemez teljes tartalma TORLODIK             │
  │    • a cloud-init beallitja a hostname/user/SSH/Wi-Fi-t  │
  │    • kesz: a kartyara egy uj, tiszta Raspberry Pi OS     │
  │                                                          │
  │  A jóváhagyás a 'sudo' hívással volt meg.                │
  └──────────────────────────────────────────────────────────┘

EOF

# az Imager a lemezre ir, a cloud-init fajlokkal
"$IMG_BIN" --cli \
    --cloudinit-userdata /tmp/cloudinit/user-data \
    --cloudinit-networkconfig /tmp/cloudinit/network-config \
    "$IMG" "$DEVICE" 2>&1 | tee "$LOG" | \
    grep -vE 'locale|Qt depends|reconfigure|locale\(1\)|Text scale|Font engine|libcurl|CacheManager|Optimal async|FileOperations|Starting background|Restricted permissions'

echo
if grep -qE 'Writing|Verifying|Successful|complete' "$LOG"; then
    log "KESZ — a telepites befejezodott."
else
    warn "a telepites vegeredmenye nem egyertelmu — a naplo:"
    tail -25 "$LOG"
    exit 1
fi

echo
log "A KOVETKEZO LEPESEK:"
echo "  1. A kartyat kiveve es a Pi-ba (a hdmi, a tap, a dongle, az antenna)"
echo "  2. A Pi bootol — a LED villog (~1 perc)"
echo "  3. A router DHCP listaja alapjan keresd meg a 'bud01' IP-jet"
echo "  4. ssh miklos@<pi-ip>   (a jelszo: a beallitott)"
echo "  5. ssh -X -t miclos@<pi-ip> 'sudo bash -s' < scripts/ais-receiver/install_ais_receiver.sh"
echo "  6. A PPM-kalibracio (10 perc): rtl_test -p > /tmp/ppm.txt"
