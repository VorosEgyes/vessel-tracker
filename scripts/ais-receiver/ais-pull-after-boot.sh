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
LOG="${LOG:-$HOME/.ais-pull.log}"
DB_FILE="${DB_FILE:-/var/lib/ais/ais.db}"
export DB_FILE

# a service keszen all-e? (a vevonek meg kell indulnia elotte)
for i in $(seq 1 12); do
    if [ -f "$DB_FILE" ] && [ -s "$DB_FILE" ]; then break; fi
    sleep 10
done

{
    echo "--- $(date '+%F %T') a boot utani lehuzas indul ---"
    /usr/local/bin/ais-fetch-weekly.sh
    echo "--- $(date '+%F %T') a boot utani lehuzas vege (a stausz: $?) ---"
} >> "$LOG" 2>&1
