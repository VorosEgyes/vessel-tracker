#!/bin/bash
# A Pi-on: a neveket hordozo "hajok" (a tenyleges hajok) vs a belső
# AIS-staciok (a Duna kilometerjelolesei), es a FI 10 (ENI) tartalma.
set -u
DB=/var/lib/ais/ais.db
q() { sudo sqlite3 -header -column "$DB" "$1"; }

echo "--- A. A NÉVVEL ÉS ENI-VEL RENDELKEZŐ HAJÓK (a valódi járművek) ---"
q "
SELECT mmsi AS MMSI, shipname AS nev, imo AS ENI,
  CASE shiptype
    WHEN 20 THEN 'bárka (WIG)'
    WHEN 30 THEN 'halászhajó'
    WHEN 35 THEN 'katonai'
    WHEN 36 THEN 'sétáló'
    WHEN 37 THEN 'kis vitorlázó'
    WHEN 40 THEN 'nagyhajó'
    WHEN 41 THEN 'kontejnerhajó'
    WHEN 42 THEN 'tanker'
    WHEN 43 THEN 'konténer/ro-ro'
    WHEN 45 THEN 'ro-ro'
    WHEN 50 THEN 'pilóta'
    WHEN 51 THEN 'tengeri mentő'
    WHEN 52 THEN 'hulladékszállító'
    WHEN 53 THEN 'kórház'
    WHEN 55 THEN 'joghajó'
    WHEN 58 THEN 'személyszállító'
    WHEN 60 THEN 'utasszállító'
    WHEN 70 THEN 'teherhajó'
    WHEN 80 THEN 'tankhajó'
    WHEN 90 THEN 'egyéb'
    ELSE 'ismeretlen ('||COALESCE(shiptype,0)||')'
  END AS tipus,
  round(speed,1) AS seb_kn, round(course,0) AS irany,
  round(COALESCE(draught,0),2) AS mer_ug,
  COALESCE(NULLIF(callsign,''),'-') AS hivoszam,
  (to_bow+to_stern) AS hossz_m,
  (to_port+to_starboard) AS szelesseg_m,
  count AS uzenetek
FROM ais_state
WHERE (imo IS NOT NULL AND imo!=0) OR (callsign IS NOT NULL AND callsign!='')
ORDER BY (imo IS NOT NULL AND imo!=0) DESC, shipname;"

echo
echo "--- B. A NÉVVEL RENDELKEZŐ HAJÓK (a teljes lista, ENI nélkül is) ---"
q "
SELECT mmsi AS MMSI, shipname AS nev,
  CASE WHEN imo IS NOT NULL AND imo!=0 THEN imo ELSE '-' END AS ENI,
  round(speed,1) AS seb_kn,
  round(COALESCE(draught,0),2) AS mer_ug,
  count AS uzenetek
FROM ais_state WHERE shipname IS NOT NULL AND shipname!=''
ORDER BY (imo IS NOT NULL AND imo!=0) DESC, count DESC;"

echo
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
  END AS jel_-tipus,
  count(*) AS stacio,
  round(min(CAST(substr(shipname,1,instr(shipname,'_')-1) AS REAL)),1) AS km_tol,
  round(max(CAST(substr(shipname,1,instr(shipname,'_')-1) AS REAL)),1) AS km_ig
FROM ais_state
WHERE shipname LIKE '%\\_%' ESCAPE '\\'
GROUP BY 1 ORDER BY 2 DESC;"

echo
echo "--- D. A KILOMÉTERJELÖLÉSEK A DUNA MENTÉN (a sorrend) ---"
q "
SELECT shipname AS jeloles,
  CAST(substr(shipname,1,instr(shipname,'_')-1) AS REAL) AS km,
  count AS uzenetek
FROM ais_state WHERE shipname LIKE '%\\_%' ESCAPE '\\'
ORDER BY km;" | head -40

echo
echo "--- E. A FI 10 (ENI) ÜZENETEK NÉHÁNY SORBAN (a nyers tartalom) ---"
q "SELECT id, mmsi, type, channel, substr(nmea,1,80) AS nmea FROM ais_message
   WHERE type IN (6,8) ORDER BY id DESC LIMIT 8;"

echo
echo "--- F. A FI 10 FORRÁSOK (a belső AIS-staciok, amik kozvetlenul uldik a NAVTEX-et) ---"
q "
SELECT mmsi AS forras_mmsi, count(*) AS fi10_db,
       count(DISTINCT station_id) AS allomas
FROM ais_message WHERE type IN (6,8) GROUP BY 1 ORDER BY 2 DESC LIMIT 10;"

echo
echo "--- G. A STATIKUS ADATOK (Msg 5/24) — a hajonevek es a meretek ---"
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
