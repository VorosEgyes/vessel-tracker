#!/bin/bash
# A cloud-init fajlok eloallitasa a Macen (a Pi OS Lite telepiteshez).
#
# A Raspberry Pi OS Trixie a cloud-init-et hasznalja. A hivalatos pelda
# szerint a network-config a 'network:' gyokereken, 'renderer:
# NetworkManager'-rel es 'regulatory-domain'-nel (a 2026-11-22-es elso
# probalkozas ezek nelkul nem csatlakozott a Wi-Fi-re).
set -eu

HOSTNAME="${1:-bud01}"
USERNAME="${2:-miklos}"
PASSWORD="${3:?a jelszo kimaradt}"
SSID="${4:-}"
WIFI_PASS="${5:-}"
SSH_PUBKEY="${6:?az SSH kulcs kimaradt}"
COUNTRY="${7:-HU}"

# a Mac kulcsa (a NAS-hoz is ezt hasznaljuk)
KEY_FILE="${SSH_PUBKEY_FILE:-$HOME/.ssh/hermes_nas_ed25519.pub}"
if [ ! -f "$KEY_FILE" ]; then
    echo "HIBA: a kulcsfajl nem letezik: $KEY_FILE" >&2
    exit 1
fi
PUBKEY=$(cat "$KEY_FILE")

rm -rf /tmp/cloudinit
mkdir -p /tmp/cloudinit

python3 /tmp/make_cloudinit.py \
    "$HOSTNAME" "$USERNAME" "$PASSWORD" "$SSID" "$WIFI_PASS" "$PUBKEY" "$COUNTRY"

# --- a netplan-formatum ellenorzese (a 2026-11-22-i hiba okai) ---
if [ -n "$SSID" ]; then
    grep -q "^network:" /tmp/cloudinit/network-config \
        || { echo "HIBA: a network-config gyokereken nincs a 'network:'!" >&2; exit 1; }
    grep -q "renderer: NetworkManager" /tmp/cloudinit/network-config \
        || { echo "HIBA: a renderer: NetworkManager hianyzik!" >&2; exit 1; }
    grep -q "regulatory-domain" /tmp/cloudinit/network-config \
        || { echo "HIBA: a regulatory-domain hianyzik!" >&2; exit 1; }
    grep -q "access-points:" /tmp/cloudinit/network-config \
        || { echo "HIBA: az access-points blokk hianyzik!" >&2; exit 1; }
    echo "  a netplan-formatum ellenorzes OK (network:/renderer/regulatory-domain/access-points)"
    echo "  a Wi-Fi beallitas: $SSID ($COUNTRY)"
else
    echo "  Ethernet (a DHCP adja az IP-t)"
fi

# --- a user-data ellenorzese ---
grep -q "^#cloud-config" /tmp/cloudinit/user-data \
    || { echo "HIBA: a '#cloud-config' header hianyzik (kötelezo!)" >&2; exit 1; }
grep -q "ssh_authorized_keys:" /tmp/cloudinit/user-data \
    || { echo "HIBA: az ssh_authorized_keys hianyzik!" >&2; exit 1; }
grep -q "hostname: ${HOSTNAME}" /tmp/cloudinit/user-data \
    || { echo "HIBA: a hostname nem a megadott!" >&2; exit 1; }
echo "  a user-data ellenorzes OK (header/hostname/SSH-kulcs)"

# --- a hitelesito adat: a cloud-init sajat mechanizmusa ---
echo "  a jelszo a 'plain_text_passwd' mezoben van — a cloud-init a"
echo "  boot utan maga hasheli (a Raspberry Pi hivalatos peldaja szerint)"
echo "  A FOLYAMAT a /tmp/cloudinit/ alatt marad — a telepites UTAN"
echo "  torold: rm -rf /tmp/cloudinit"
