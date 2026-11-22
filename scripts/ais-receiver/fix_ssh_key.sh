#!/bin/bash
# =====================================================================
# Az SSH-kulcs elhelyezése a bud01-re (a cloud-init nem tette oda)
# =====================================================================
# A cloud-init a 'users:' modulban a 'ssh_authorized_keys' kulcsot a
# felhasznalo '~/.ssh/authorized_keys' fajlba kellene tennie, de a
# Trixie-ben ez nem tortent meg. A javitas: a kulcsot mi helyezzuk el.
#
# A parancs a Mac termináljabol fut:
#   bash ~/dev/fix_ssh_key.sh
# =====================================================================

set -eu

PI="${PI:-bud01.local}"
USER_NAME="${USER_NAME:-miklos}"
KEY_FILE="${KEY_FILE:-$HOME/.ssh/hermes_nas_ed25519.pub}"

if [ ! -f "$KEY_FILE" ]; then
    echo "HIBA: a kulcsfajl nem letezik: $KEY_FILE" >&2
    exit 1
fi

echo "==> a kulcs masolasa a $PI-re ($USER_NAME)"
echo "    (a jelszot a terminalon kered — a cloud-init utani allapot)"
echo

# --- a kulcs beillesztese (a standard inputon megy át) ---
cat "$KEY_FILE" | ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 \
    "${USER_NAME}@${PI}" \
    'mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo "    a kulcs beillesztve: $(wc -l < ~/.ssh/authorized_keys) sor"'

echo
echo "==> a belepes ellenorzese (a sudo, a cloud-init allapot):"
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 "${USER_NAME}@${PI}" \
    'if sudo -n true 2>/dev/null; then echo "    a sudo jelszo nelkul muxik"; else echo "    FIGYELEM: a sudo jelszot ker"; fi
     echo "    a cloud-init:"; cloud-init status 2>/dev/null | head -2
     echo "    a Wi-Fi:"; nmcli -t -f ACTIVE,SSID dev show wlan0 2>/dev/null | head -2
     echo "    a rendszer:"; hostname; uname -m' 2>/dev/null

echo
echo "==> kesz. A teszt:"
echo "    ssh ${USER_NAME}@${PI} 'echo SSH_KEY_OK'"
