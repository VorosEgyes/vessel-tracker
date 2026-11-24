#!/bin/bash
# A heti lehuzas a service indulasa utan (a Pi ejszaka ki van kapcsolva).
#
# A Pi este kikapcsol es reggel 8-kor indul -> a fix 04:17-es cron
# SOHA nem futna -> a lehuzas a BOOT UTAN megy (a systemd
# ExecStartPost-jaban, a 07 §9.1 szerint).
#
# A "miklos" user futtatja (a lehuzas kulcsa a sajat home-jaban van):
# a systemd unit "User=ais"-szal indul -> ezert a unit a
# sudo -n -u miklos formaban hívja (a sudoers: /etc/sudoers.d/ais-pull).
set -u
# A log a "miklos" SAJAT home-jaba megy — a sudo -u miklos NEM tartja meg
# a HOME env-et (a /root-ra allitja) -> a "$HOME" itt a ROSSZ hely lenne.
# A 2026-11-24-i teszt: a "$HOME/.ais-pull.log" nem jott letre, a
# script csendben elbukott.
MIKLOS_HOME="/home/miklos"
LOG="${LOG:-$MIKLOS_HOME/.ais-pull.log}"
DB_FILE="${DB_FILE:-/var/lib/ais/ais.db}"
export DB_FILE

# a service keszen all-e? (a vevonek meg kell indulnia elotte)
#
# A DB fajl a /var/lib/ais alatt van (0750 ais:ais) -> a "miklos" user
# NEM latja -> a "test -f" a sudo-val mukodik (a 2026-11-24-i teszt:
# a sima "[ -f ]" mindig hamis volt -> a ciklus 12x10 masodpercet vart).
for i in $(seq 1 12); do
    if sudo -n test -f "$DB_FILE" && sudo -n test -s "$DB_FILE"; then break; fi
    sleep 10
done

{
    echo "--- $(date '+%F %T') a boot utani lehuzas indul ---"
    /usr/local/bin/ais-fetch-weekly.sh
    echo "--- $(date '+%F %T') a boot utani lehuzas vege (a stausz: $?) ---"
} >> "$LOG" 2>&1 || true

# a kesz jelzes a kulcs fajlban (hogy a NAS-on is latszik)
touch "$MIKLOS_HOME/.ais-pull.last" 2>/dev/null || true
