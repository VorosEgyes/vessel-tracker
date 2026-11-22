#!/bin/bash
set -u
DB=/var/lib/ais/ais.db
q() { sudo sqlite3 -header -column "$DB" "$1"; }

echo "--- C. A DUNA KILOMÉTERJELÖLÉSEI (a belső AIS-staciok) ---"
q "
SELECT
  CASE
    WHEN shipname LIKE '%_G'    THEN 'zöld lámpa'
    WHEN shipname LIKE '%_R'    THEN 'piros lámpa'
    WHEN shipname LIKE '%_W'    THEN 'fehér lámpa'
    WHEN shipname LIKE '%_FL'   THEN 'villogó lámpa'
    WHEN shipname LIKE '%_F'    THEN 'fix lámpa'
    ELSE 'egyéb'
  END AS jel_tipus,
  count(*) AS stacio,
  round(min(CAST(substr(shipname,1,instr(shipname,'_')-1) AS REAL)),1) AS km_tol,
  round(max(CAST(substr(shipname,1,instr(shipname,'_')-1) AS REAL)),1) AS km_ig
FROM ais_state
WHERE shipname GLOB '*_*'
GROUP BY 1 ORDER BY 2 DESC;"

echo
echo "--- D. A JELÖLÉSEK A DUNA MENTÉN (a km szerint) ---"
q "
SELECT shipname AS jeloles,
  CAST(substr(shipname,1,instr(shipname,'_')-1) AS REAL) AS km,
  count AS uzenetek
FROM ais_state WHERE shipname GLOB '*_*'
ORDER BY km;"

echo
echo "--- E. A FI 10 (ENI) ÜZENETEK ---"
q "SELECT id, mmsi, type, channel, substr(nmea,1,90) AS nmea FROM ais_message
   WHERE type IN (6,8) ORDER BY id DESC LIMIT 8;"

echo
echo "--- F. A FI 10 FORRÁSOK ---"
q "
SELECT mmsi AS forras_mmsi, count(*) AS fi10_db
FROM ais_message WHERE type IN (6,8) GROUP BY 1 ORDER BY 2 DESC LIMIT 10;"

echo
echo "--- G. A STATIKUS ADATOK (Msg 5/24) ---"
q "
SELECT mmsi AS MMSI, shipname AS nev,
  CASE WHEN imo IS NOT NULL AND imo!=0 THEN imo ELSE '-' END AS ENI,
  (to_bow+to_stern) AS hossz_m,
  (to_port+to_starboard) AS szelesseg_m,
  round(COALESCE(draught,0),2) AS mer_ug,
  COALESCE(NULLIF(callsign,''),'-') AS hivoszam,
  COALESCE(NULLIF(destination,''),'-') AS cel
FROM ais_static
WHERE shipname IS NOT NULL AND shipname!=''
ORDER BY (imo IS NOT NULL AND imo!=0) DESC, shipname LIMIT 40;"
