#!/bin/bash
# A Pi-on futo elemzes: milyen jeleket fogott az antenna, milyen hajokat lat.
set -u
DB=/var/lib/ais/ais.db

q() { sudo sqlite3 -header -column "$DB" "$1"; }

echo "===================================================================="
echo "A BUD01 VEVÓ — a fogott jelek és a látott hajók"
echo "===================================================================="
echo "idő: $(date '+%F %T')   adatbázis: $DB"
echo "üzenetek: $(sudo sqlite3 "$DB" 'SELECT count(*) FROM ais_message;')"
echo "hajók:    $(sudo sqlite3 "$DB" 'SELECT count(*) FROM ais_state;')"
echo

echo "--- 1. AZ ÜZENETTÍPUSOK ---"
q "
SELECT type,
  CASE type
    WHEN 1  THEN 'pozíció (Class A, 1-2 mp)'
    WHEN 2  THEN 'pozíció (Class A, 10 mp)'
    WHEN 3  THEN 'pozíció (küldés-kérés)'
    WHEN 4  THEN 'bázisállomás'
    WHEN 5  THEN 'statikus hajódatok'
    WHEN 6  THEN 'belső forg. adat (FI 10) — ENI'
    WHEN 8  THEN 'belső forg. adat (FI 10) — ENI'
    WHEN 18 THEN 'pozíció (Class B, 10 mp)'
    WHEN 19 THEN 'pozíció (Class B, extend)'
    WHEN 20 THEN 'belső forgalmi adat (MSK, Duna)'
    WHEN 21 THEN 'belső forgalmi adat (Class B)'
    WHEN 23 THEN 'belső forgalmi adat (MSK, Duna, új)'
    WHEN 24 THEN 'statikus hajódatok (részleges)'
    ELSE 'egyéb'
  END AS tipus,
  count(*) AS db,
  round(100.0*count(*)/(SELECT count(*) FROM ais_message),1) AS szazalék
FROM ais_message GROUP BY type ORDER BY db DESC;"

echo
echo "--- 2. A CSATORNÁK (A = 161.975 MHz, B = 162.025 MHz) ---"
q "SELECT channel, count(*) AS db FROM ais_message
   WHERE channel IS NOT NULL GROUP BY channel ORDER BY db DESC;"

echo
echo "--- 3. A JELERŐSSÉG (dB, a ais_state-ből — a legutóbbi érték hajónként) ---"
q "
SELECT
  CASE
    WHEN signalpower >= -20 THEN 'kiváló   (>= -20 dB)'
    WHEN signalpower >= -30 THEN 'jó       (-30..-20 dB)'
    WHEN signalpower >= -40 THEN 'gyenge   (-40..-30 dB)'
    WHEN signalpower >= -50 THEN 'nagyon gyenge (-50..-40 dB)'
    ELSE 'alig hallható (< -50 dB)'
  END AS jel_minoseg,
  count(*) AS hajok,
  round(100.0*count(*)/(SELECT count(*) FROM ais_state WHERE signalpower IS NOT NULL),1) AS szazalék
FROM ais_state WHERE signalpower IS NOT NULL GROUP BY 1 ORDER BY 2 DESC;"

echo
echo "--- 4. A JELERŐSSÉG ÖSSZEFOGLALÓ (a hajók legutóbbi értéke) ---"
q "
SELECT round(avg(signalpower),1) AS atlag_dB,
       round(min(signalpower),1)  AS min_dB,
       round(max(signalpower),1)  AS max_dB,
       count(signalpower)          AS hajok
FROM ais_state WHERE signalpower IS NOT NULL;"

echo
echo "--- 5. A PPM (a kristály pontossága) ---"
q "
SELECT round(avg(ppm),1) AS atlag_ppm, round(min(ppm),1) AS min_ppm,
       round(max(ppm),1) AS max_ppm, count(ppm) AS meres
FROM ais_state WHERE ppm IS NOT NULL;"

echo
echo "--- 6. A LÁTT HAJÓK ---"
q "
SELECT
  mmsi AS MMSI,
  COALESCE(NULLIF(shipname,''),'(névtelen)') AS nev,
  CASE WHEN imo IS NOT NULL AND imo!=0 THEN imo ELSE NULL END AS ENI,
  CASE shiptype
    WHEN 0 THEN 'nincs megadva'
    WHEN 20 THEN 'bárka (WIG)'
    WHEN 30 THEN 'halászhajó'
    WHEN 31 THEN 'halászhajó (túzhalog)'
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
    ELSE 'ismeretlen ('||shiptype||')'
  END AS tipus,
  round(speed,1) AS seb_kn,
  round(course,0) AS irany,
  round(COALESCE(draught,0),1) AS mer_ug,
  COALESCE(NULLIF(callsign,''),'-') AS hivoszam,
  round(signalpower,0) AS jel_dB
FROM ais_state
ORDER BY (imo IS NOT NULL AND imo!=0) DESC, (shipname!='') DESC, shipname
LIMIT 60;"

echo
echo "--- 7. A HAJÓK ÖSSZESÍTETT STATISZTIKÁJA ---"
q "
SELECT
  count(*) AS hajok,
  sum(CASE WHEN imo IS NOT NULL AND imo!=0 THEN 1 ELSE 0 END) AS ENI_vel,
  sum(CASE WHEN shipname IS NOT NULL AND shipname!='' THEN 1 ELSE 0 END) AS nev_vel,
  sum(CASE WHEN draught IS NOT NULL AND draught>0 THEN 1 ELSE 0 END) AS meret_adat,
  sum(CASE WHEN callsign IS NOT NULL AND callsign!='' THEN 1 ELSE 0 END) AS hivoszam,
  sum(CASE WHEN speed>0.5 THEN 1 ELSE 0 END) AS mozgaban,
  sum(CASE WHEN shiptype IS NOT NULL AND shiptype!=0 THEN 1 ELSE 0 END) AS tipus_adat
FROM ais_state;"

echo
echo "--- 8. A BELSŐ FORGALMI (FI 10) ÜZENETEK — az ENI-k forrása ---"
q "
SELECT count(*) AS fi10_db,
       count(DISTINCT mmsi) AS kulonb_so_forras,
       count(DISTINCT station_id) AS allomas
FROM ais_message WHERE type IN (6,8);"

echo
echo "--- 9. A FOGADÁS IDŐBELI ALAKJA (a ais_state first_seen alapján) ---"
q "
SELECT substr(first_seen,1,16) AS idopont, count(*) AS uj_hajo
FROM ais_state WHERE first_seen IS NOT NULL
GROUP BY 1 ORDER BY 1 DESC LIMIT 12;"

echo
echo "--- 10. A LEGAKTÍVABB HAJÓK (a legtöbb üzenet) ---"
q "
SELECT mmsi AS MMSI,
       COALESCE(NULLIF(shipname,''),'(névtelen)') AS nev,
       count AS uzenetek,
       round(speed,1) AS seb_kn,
       round(signalpower,0) AS jel_dB,
       first_seen AS elso,
       received_at AS utolso
FROM ais_state ORDER BY count DESC LIMIT 15;"
