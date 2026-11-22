#!/bin/bash
set -u
DB=/var/lib/ais/ais.db
q() { sudo sqlite3 -header -column "$DB" "$1"; }

echo "--- A. A VIRTUAL JELOLESEK (a szintetikus navigacios pontok) ---"
q "SELECT shipname AS jel, mmsi AS MMSI, round(lat,4) AS lat, round(lon,4) AS lon,
          count AS uzen
   FROM ais_state WHERE shipname LIKE 'VIRTUAL%'
   ORDER BY count DESC LIMIT 12;"

echo
echo "--- B. A MMSI ELOLAGOK SZERINTI MEGOSZLAS ---"
q "
SELECT
  CASE
    WHEN mmsi BETWEEN 992000000 AND 992999999 THEN 'belső (dunai navigáció, 992xxxxxx)'
    WHEN mmsi BETWEEN 243000000 AND 243999999 THEN 'magyar hajó (243xxxxxx)'
    WHEN mmsi BETWEEN 244000000 AND 244999999 THEN 'svéd hajó (244xxxxxx)'
    WHEN mmsi BETWEEN 269000000 AND 269999999 THEN 'finn hajó (269xxxxxx)'
    WHEN mmsi BETWEEN 279000000 AND 279999999 THEN 'német hajó (279xxxxxx)'
    WHEN mmsi BETWEEN 226000000 AND 226999999 THEN 'francia hajó (226xxxxxx)'
    WHEN mmsi BETWEEN 272000000 AND 272999999 THEN 'ukrán hajó (272xxxxxx)'
    WHEN mmsi BETWEEN 253000000 AND 253999999 THEN 'luxemburgi hajó (253xxxxxx)'
    WHEN mmsi BETWEEN 203000000 AND 203999999 THEN 'osztrák hajó (203xxxxxx)'
    WHEN mmsi BETWEEN 200000000 AND 200999999 THEN 'brit hajó (2xxxxxxxx)'
    ELSE 'egyéb'
  END AS csoport,
  count(*) AS hajok,
  sum(count) AS uzenetek
FROM ais_state GROUP BY 1 ORDER BY uzenetek DESC;"

echo
echo "--- C. A HOL A VEVÖ (a BUDAPEST jelölés) ---"
q "SELECT shipname AS jel, round(lat,4) AS lat, round(lon,4) AS lon, round(speed,1) AS seb
   FROM ais_state WHERE shipname LIKE '%BUDAPEST%';"

echo
echo "--- D. A TÁVOLSÁG a BUDAPEST-től (a hajok, a km) ---"
q "
WITH vevo AS (SELECT lat AS vlat, lon AS vlon FROM ais_state WHERE shipname LIKE '%BUDAPEST%' LIMIT 1)
SELECT
  COALESCE(NULLIF(s.shipname,''),'(névtelen)') AS nev,
  round(6371 * acos( MIN(1.0,
    cos(radians(s.lat))*cos(radians(v.vlat))*cos(radians(s.lon)-radians(v.vlon))
    + sin(radians(s.lat))*sin(radians(v.vlat)))),1) AS km,
  round(s.speed,1) AS seb_kn,
  s.count AS uzenetek
FROM ais_state s, vevo v
WHERE s.lat IS NOT NULL AND s.lat != 0 AND s.shipname NOT LIKE '%\_%' ESCAPE '\'
ORDER BY km LIMIT 30;"

echo
echo "--- E. A LEGTÁVOLABBI HAJÓK ---"
q "
WITH vevo AS (SELECT lat AS vlat, lon AS vlon FROM ais_state WHERE shipname LIKE '%BUDAPEST%' LIMIT 1)
SELECT
  COALESCE(NULLIF(s.shipname,''),'(névtelen)') AS nev,
  round(6371 * acos( MIN(1.0,
    cos(radians(s.lat))*cos(radians(v.vlat))*cos(radians(s.lon)-radians(v.vlon))
    + sin(radians(s.lat))*sin(radians(v.vlat)))),1) AS km,
  s.count AS uzenetek
FROM ais_state s, vevo v
WHERE s.lat IS NOT NULL AND s.lat != 0 AND s.shipname NOT LIKE '%\_%' ESCAPE '\'
ORDER BY km DESC LIMIT 15;"
