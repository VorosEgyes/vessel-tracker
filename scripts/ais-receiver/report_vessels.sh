#!/bin/bash
# A Pi-on: a neveket hordozo "hajok" (a tenyleges hajok) vs a belső
# AIS-staciok (a Duna kilometerjelolesei), es a FI 10 (ENI) tartalma.
#
# A `shiptype` CASE lista **a 02-es DDL-terv seedjeből keszult**
# (a `make_type_case.py` generalja) -> a magyar hajotipus-nevek
# mindig a DB-vel egyeznek (a 88 tipus, a `vessel_type` + a
# `vessel_type_i18n` tabla alapjan).
set -u
DB=/var/lib/ais/ais.db
q() { sudo sqlite3 -header -column "$DB" "$1"; }

echo "--- A. A NÉVVEL ÉS ENI-VEL RENDELKEZŐ HAJÓK (a valódi járművek) ---"
q "
SELECT mmsi AS MMSI, shipname AS nev, imo AS ENI,
  CASE shiptype
    WHEN 30 THEN 'halászhajó'
    WHEN 31 THEN 'halászhajó (túzhalog)'
    WHEN 33 THEN 'sócsaró'
    WHEN 35 THEN 'katonai hajó'
    WHEN 36 THEN 'sétáló'
    WHEN 37 THEN 'kis vitorlázó'
    WHEN 40 THEN 'nagyhajó'
    WHEN 41 THEN 'konténerhajó'
    WHEN 42 THEN 'tanker'
    WHEN 43 THEN 'konténer/ro-ro'
    WHEN 44 THEN 'ro-ro (konténer)'
    WHEN 45 THEN 'ro-ro'
    WHEN 50 THEN 'pilótahajó'
    WHEN 51 THEN 'tengeri mentő'
    WHEN 52 THEN 'hulladékszállító'
    WHEN 53 THEN 'kórházhajó'
    WHEN 55 THEN 'joghajó'
    WHEN 58 THEN 'személyszállító hajó'
    WHEN 60 THEN 'utasszállító hajó'
    WHEN 70 THEN 'teherhajó'
    WHEN 79 THEN 'teherhajó (további információ nélkül)'
    WHEN 80 THEN 'tankhajó'
    WHEN 89 THEN 'tanker (további információ nélkül)'
    WHEN 90 THEN 'egyéb hajó'
    WHEN 99 THEN 'egyéb hajó (további információ nélkül)'
    WHEN 8000 THEN 'a hajó típusa ismeretlen (belvízi)'
    WHEN 8010 THEN 'motoros teherhajó'
    WHEN 8020 THEN 'motoros tanker'
    WHEN 8021 THEN 'motoros tanker, folyadék, N-típus'
    WHEN 8022 THEN 'motoros tanker, folyadék, C-típus'
    WHEN 8023 THEN 'motoros tanker, száraz teher, folyadékként'
    WHEN 8030 THEN 'konténerhajó'
    WHEN 8040 THEN 'gáztanker'
    WHEN 8050 THEN 'motoros teherhajó, vontató'
    WHEN 8060 THEN 'motoros tanker, vontató'
    WHEN 8070 THEN 'motoros teherhajó, egy vagy több mellette'
    WHEN 8080 THEN 'motoros teherhajó tankhajóval'
    WHEN 8090 THEN 'motoros teherhajó, egy vagy több teherhajót tol'
    WHEN 8100 THEN 'motoros teherhajó, legalább egy tankhajót tol'
    WHEN 8110 THEN 'vontató teherhajó'
    WHEN 8120 THEN 'vontató tanker'
    WHEN 8130 THEN 'vontató teherhajó, csatolt'
    WHEN 8140 THEN 'vontató teherhajó/tanker, csatolt'
    WHEN 8150 THEN 'teherbárka'
    WHEN 8160 THEN 'tankbárka'
    WHEN 8161 THEN 'tankbárka, folyadék, N-típus'
    WHEN 8162 THEN 'tankbárka, folyadék, C-típus'
    WHEN 8163 THEN 'tankbárka, száraz teher, folyadékként'
    WHEN 8170 THEN 'teherbárka konténerekkel'
    WHEN 8180 THEN 'gáztankbárka'
    WHEN 8210 THEN 'tolóhajó, egy teherbárka'
    WHEN 8220 THEN 'tolóhajó, két teherbárka'
    WHEN 8230 THEN 'tolóhajó, három teherbárka'
    WHEN 8240 THEN 'tolóhajó, négy teherbárka'
    WHEN 8250 THEN 'tolóhajó, öt teherbárka'
    WHEN 8260 THEN 'tolóhajó, hat teherbárka'
    WHEN 8270 THEN 'tolóhajó, hét teherbárka'
    WHEN 8280 THEN 'tolóhajó, nyolc teherbárka'
    WHEN 8290 THEN 'tolóhajó, kilenc vagy több bárka'
    WHEN 8310 THEN 'tolóhajó, egy tank-/gázbárka'
    WHEN 8320 THEN 'tolóhajó, legalább két tank-/gázbárka'
    WHEN 8330 THEN 'tolóhajó, legalább három tank-/gázbárka'
    WHEN 8340 THEN 'tolóhajó, legalább négy tank-/gázbárka'
    WHEN 8350 THEN 'tolóhajó, legalább öt tank-/gázbárka'
    WHEN 8360 THEN 'tolóhajó, legalább hat tank-/gázbárka'
    WHEN 8370 THEN 'tolóhajó, legalább hét tank-/gázbárka'
    WHEN 8380 THEN 'tolóhajó, legalább nyolc tank-/gázbárka'
    WHEN 8390 THEN 'tolóhajó, legalább kilenc tank-/gázbárka'
    WHEN 8400 THEN 'vontató, egy'
    WHEN 8410 THEN 'vontató, egy vagy több vontatás'
    WHEN 8420 THEN 'vontató, segéd'
    WHEN 8430 THEN 'tolóhajó, egy'
    WHEN 8440 THEN 'személyhajó, komp, vöröskeresztes hajó'
    WHEN 8441 THEN 'komp'
    WHEN 8442 THEN 'vöröskeresztes hajó'
    WHEN 8443 THEN 'Cruzehajó'
    WHEN 8444 THEN 'személyhajó szállás nélkül'
    WHEN 8445 THEN 'egynapos gyorsjáratú hajó'
    WHEN 8446 THEN 'egynapos hidrofoil'
    WHEN 8447 THEN 'vitorlázó Cruzehajó'
    WHEN 8448 THEN 'vitorlázó személyhajó szállás nélkül'
    WHEN 8450 THEN 'kisegítő hajó, rendőrségi, kikötői szolgálat'
    WHEN 8451 THEN 'kisegítő hajó'
    WHEN 8452 THEN 'rendőrségi járőrhajó'
    WHEN 8453 THEN 'kikötői szolgálati hajó'
    WHEN 8454 THEN 'navigációs felügyeleti hajó'
    WHEN 8460 THEN 'munkahajó, karbantartó, úszó daru, kábelhajó, bójahajó, zsombor'
    WHEN 8470 THEN 'vontatott tárgy, egyéb'
    WHEN 8480 THEN 'halászhajó'
    WHEN 8490 THEN 'bunkerhajó'
    WHEN 8500 THEN 'bárka, tanker, vegyi'
    WHEN 8510 THEN 'tárgy, egyéb'
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
