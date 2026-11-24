#!/usr/bin/env python3
"""A cloud-init fajlok elkeszitese a Pi OS Lite telepiteshez.

A Raspberry Pi OS (Bookworm, 2024+) a cloud-init-et hasznalja az
elso inditas elotti beallitasokra. Az Imager CLI ket fajlbol allitja
be a kartyat:
  --cloudinit-userdata      a hostname, a felhasznalo, a jelszo, az SSH
  --cloudinit-networkconfig a Wi-Fi (vagyEthernet)

A fajlok a /tmp/cloudinit/ alatt keszulnek el a Macen.
"""

import pathlib
import sys

OUT = pathlib.Path("/tmp/cloudinit")
OUT.mkdir(parents=True, exist_ok=True)

# --- a parameterek (a shellbol jonnek) ---
HOSTNAME = sys.argv[1] if len(sys.argv) > 1 else "bud01"
USERNAME = sys.argv[2] if len(sys.argv) > 2 else "miklos"
PASSWORD = sys.argv[3] if len(sys.argv) > 3 else ""
SSID = sys.argv[4] if len(sys.argv) > 4 else ""
WIFI_PASS = sys.argv[5] if len(sys.argv) > 5 else ""
SSH_PUBKEY = sys.argv[6] if len(sys.argv) > 6 else ""
COUNTRY = sys.argv[7] if len(sys.argv) > 7 else "HU"

if not PASSWORD:
    sys.exit("HIBA: a jelszo kimaradt")
if not SSH_PUBKEY:
    sys.exit("HIBA: az SSH kulcs kimaradt")

# --- a jelszo hashelése ---
# --- a user-data ---
# A Raspberry Pi hivatalos peldaja szerint a 'plain_text_passwd'
# mezot hasznaljuk — a cloud-init a boot utan maga hasheli.
# (A 'passwd: <hash>' is elfogadott, de a pelda egyszerubb.)
# A hitelesito adatak a kartyara writing kerulnek — ez a cloud-init
# sajat mechanizmusa, nem a mi fajlunk.
user_data = f"""#cloud-config
# A vessel-tracker projekt R1-0 AIS-vevo (a budapesti telephely).
hostname: {HOSTNAME}
manage_etc_hosts: true

timezone: Europe/Budapest
locale: hu_HU.UTF-8

# a felhasznalo — a Raspberry Pi hivatalos peldaja szerint
# (a 'plain_text_passwd' a cloud-init altal a boot utan hashelodik;
#  a 'passwd: <hash>' is elfogadott, de a pelda ezt hasznalja)
users:
  - name: {USERNAME}
    groups: users,adm,dialout,audio,netdev,video,plugdev,cdrom,games,input,gpio,spi,i2c,render,sudo
    shell: /bin/bash
    lock_passwd: false
    plain_text_passwd: {PASSWORD}
    ssh_authorized_keys:
      - {SSH_PUBKEY}
    sudo: ALL=(ALL) NOPASSWD:ALL

# a tufzfal: a LAN portok nyitva, a WAN nincs
ufw:
  enabled: true
  rules:
    - 22/tcp
    - 8080/tcp     # a helyi web-terkep (a AIS-catcher)
    - 8100/tcp     # a helyi NMEA kimenet (a AIS-catcher)
  logging: 'low'

# a rendszer naploinak korlatozasa (a 32 GB-os SD-karty miatt)
system_info:
  hostname: {HOSTNAME}

package_update: false

runcmd:
  # a raspi-config utan a soros konzol is mukodjon (a fejsuves telepitesnel)
  - [ sh, -c, "echo 'enable_uart=1' >> /boot/firmware/config.txt || true" ]
"""

# --- a network-config ---
# A Raspberry Pi OS Trixie a cloud-init-et hasznalja; a hivalatos
# pelda szerint a GYOKERKEKEN a 'network:' kulcs kell, a
# 'renderer: NetworkManager' pedig KOTELEZO (a cloud-init alaperttelmezese
# a 'networkd', ami a Pi OS-en nem fut). A 'regulatory-domain' pedig
# nelkul a Wi-Fi nem csatlakozik.
if SSID:
    network_config = f"""network:
  version: 2
  wifis:
    renderer: NetworkManager
    wlan0:
      dhcp4: true
      regulatory-domain: "{COUNTRY}"
      access-points:
        "{SSID}":
          password: "{WIFI_PASS}"
      optional: true
"""
else:
    network_config = """network:
  version: 2
  ethernets:
    eth0:
      dhcp4: true
      optional: true
"""

(OUT / "user-data").write_text(user_data, encoding="utf-8")
(OUT / "network-config").write_text(network_config, encoding="utf-8")

print(f"a cloud-init fajlok: {OUT}")
print(f"  user-data       ({len(user_data)} B)")
print(f"  network-config  ({len(network_config)} B)")
print(f"  hostname: {HOSTNAME} | user: {USERNAME} | wifi: {SSID or '(Ethernet)'}")
