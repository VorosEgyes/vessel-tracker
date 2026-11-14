# Saját AIS vevőhálózat – tervezés

**Verzió:** 1.0 (2026-11-14)
**Kapcsolódó dokumentumok:** [`r1-adat-terv.md`](r1-adat-terv.md) (8. fejezet: a feed) · [`release-terv.md`](release-terv.md) (R1-0 fázis) · [`pi-eloallitas.md`](pi-eloallitas.md) (a Pi előkészítése lépésről lépésre) · [`../README.md`](../README.md) (adatbázis terv)

---

## 0. A döntés

> **Ha a legális feed-hozzáférés nem megoldható, saját AIS vevőket építünk.**

Ez a terv a saját vevőhálózatot mutatja be – **nem** egy szolgáltatói feedre épülő modellt.

### Miért a saját vevő a jobb alap

| Szempont | Fizetős aggregátor (S-AIS/földi mix) | Saját vevőhálózat |
|---|---|---|
| Statikus adat (ENI, típus, méret) | **csak a szerződés kezdetétől** – hetek-hónapok a teljes katalógusig | **a vevő üzembe helyezése pillanatától** – nincs várakozás |
| Historikus nyers NMEA | a szolgáltató birtokolja, korlátozott hozzáférés | **nálunk van, korlátlan**, visszakereshető |
| Terjesztési jog | külön megvásárolható, hajónkénti/területi korlátokkal | a fogadott adat közvetlenül nyilvános |
| Hosszú távú költség | hajószámonkénti/hónaponkénti díj, növekszik a flottával | fix hardverköltség + egy site ~30 €/hó |
| Vendor-lock | a szolgáltató megszűnése = adatvesztés | nincs |
| Adatminőség | a szolgáltató feldolgozása (dedup, „ghost" szűrés) – nem kontrollálható | **mi írjuk a szűrőt és a validációt** |
| Extrák | a legtöbb szolgáltató nem adja a belső FI 10 mezőket strukturálva | a nyers AIS-ből **minden** kinyerhető, ahogy a specifikáció mondja |

### Miért nem a scraping

A nyilvános hajóoldalak (MarineTraffic, VesselFinder, ShipSpotting stb.) **programozott kiolvasása a felhasználási feltételek megsértését jelenti**, és a hajószám-adatbázisok többségének licencfeltétele ezt tiltja. A scrapingre épülő termék **nem skálázódik és nem finanszírozható**, és egy jogi felszólítás az egész adatbázist fenyegeti. Az AIS-adat maga szabadon hozzáférhető – **a fogadását nem kell megvásárolni**, csak a vevőt kell felépíteni.

### Amit a saját vevő nem old meg

- **A teljes Duna lefedettségét** – a folyó ~2 850 km hosszú, és minden telephely csak ~30–45 km-t lát. A teljes lefedettség 15–20 site (és nemzetközi együttműködést) igényel. **Ez a projekt legnagyobb kockázata**, és a 9. fejezet mérési protokollja dönti el.
- **A Balaton kis hajóit** – de ezeket kizártuk a katalógusból, és a Balaton jelentős hajói 1–2 vevővel elérhetők.
- **A hajótörténetet** – az AIS-ből nincs.

---

## 1. Jogi keret

| Kérdés | Válasz | Alap |
|---|---|---|
| Kell-e rádióengedély a vevőre? | **Nem.** A vevő **nem adóállomás**, nem sugároz. Az EU rádióeszköz-jogszabály a vevők konformitását, az engedélyezési kötelezettséget a **adó** berendezésekhez köti | A vevő kizárólag fogad |
| Szabad-e az AIS-adat fogadása és felhasználása? | **Igen.** A hajófelügyeleti (VTMIS) adatok – köztük az AIS-adat – az EU-ban nyilvánosan hozzáférhetők | 2002/59/EK + 2014/100/EU |
| Korlátozza-e valami a **közzétételét**? | A nyers AIS-adat közvetlen közreadása szabad, de az IMO 2004-es (MSC.79) állásfoglalása a nyilvános internetes AIS-közzétételt **biztonsági és verseny-problémaként** jelölte | IMO MSC.79 |
| Mi a te gyakorlati következmete? | **Ne ingyenes, nyílt térképet építs.** A termék legyen fizetős, és adjon értéket (katalógus, ETA, útvonaltervezés, adatelemzés). Az ingyenes réteg legyen korlátozott | Stratégia, nem jogi kényszer |
| Telepítés az állami vízparton / kikötőben | **A hely tulajdonosának engedélye** (vízügyi igazgatóság, kikötő, önkormányzat, magánvállalkozás). Antenna-építési engedély 20 m felett | Helyi függőség, telepítésenként |
| Antenna zavarja a hajóforgalmat? | A szárazföldi vevő nem zavar (nincs adás). Közvetlenül a parton, nem a hajóút közepén | – |
| A fogadott adat újraközzététele | A gyűjtési mód és a forrás megjelölése kötelező: *„Forrás: saját AIS vevőhálózat, {telephely}, {időpont}"* | Az adatvédelmi és hitelességi alapelv |

> **A jogi kockázat nem a vevő, hanem a közzététel módja.** Ezért van a termékben forrásjelölés és a fizetős modell.

---

## 2. A lefedettség megtervezése

### 2.1 A fizikai alap

A VHF-jel horizontja rádióhorizont-törvénnyel közelíthető:

```
d_rádióhorizont (km) ≈ 4,12 · √h (h = antenna magassága méterben)
teljes látótávolság = d_vevő + d_hajó
```

| Eset | Vevő antenna | Hajó antenna | Rádióhorizont | Tényleges lefedettség a folyón (víz + visszaverés) |
|---|---|---|---|---|
| Kezdő site | 5 m (tető) | 5 m | ~18 km | **15–25 km** |
| Standard site | 12 m (oszlop) | 5 m | ~27 km | **25–35 km** |
| Emelt site | 20–25 m (parti magaslat) | 5 m | ~32 km | **30–45 km** |

A gyakorlati érték a rádióhorizontnál nagyobb a víz feletti visszaverés miatt, de a folyó **kanyarú szakaszain a geometria szűkít** – ott a horizont-limit közel van a tényleges távolsághoz. **Ez a legfontosabb tervezési korlát: a lefedettség a folyó alakjától függ, nem csak a számoktól.**

### 2.2 A magyar Duna szakaszai és a javasolt telephelyek

| Telephely | Duna-km | Jelentőség |
|---|---|---|
| Győr / Komárom | 1767–1809 | a Rába torkolata, a nemzetközi forgalom belépési pontja |
| Budapest | 1758 | **a legforgalmasabb szakasz**, a budai hídlők |
| Dunaújváros | 1447 | Szigetköz, Paks, a középső szakasz |
| Baja / Mohács | 1335–1370 | a legfontosabb magyar teherkikötők (MAHAP) |
| Szeged | ~1290 | a Tisza torkolata, a déli határ |

**A magyar Duna szakasza ~580 km**, tehát:

| Fázis | Site-ek | Várható lefedettség |
|---|---|---|
| **F1** | Budapest, Dunaújváros, Szeged | a forgalom ~60–70%-a |
| **F2** | F1 + Komárom/Győr, Baja/Mohács | a forgalom ~85–90%-a |
| **F3** | F2 + a maradék szakaszok (Esztergom, Szob, Tata, Sümeg…) | gyakorlatilag teljes |
| **B1** (Balaton) | Siófok, Keszthely/Balatonfüred | a Balaton jelentős hajói (~100) |

> **Megfontolandó:** a telephelyek helyét **nem térképen, hanem méréssel** kell kiválasztani. A „leggyorsabb forgalmi pont" nem feltétlenül a legjobb rádiópont (a part menti emelkedés, a kikötő épületei, a fák takarhatnak). A 9. fejezet mérési protokollja ezt kezeli.

### 2.3 A telephelyek kiválasztásának szempontjai

| Szempont | Követelmény |
|---|---|
| Antenna magassága | min. 10 m, ideális 20 m felett (parti magaslat, torony, kémény – de a zavarosság és a megfelelés miatt csak tulajdonosi engedéllyel) |
| Tiszta horizont | ne legyen nagy fa, épület vagy domb a víz felé; a 360°-os horizont átlátszó |
| Vízközelség | a parttól néhány száz méteren belül, de ne a hullámzó parton (a talaj minősége) |
| Elektromos | hálózati áram, stabil internet (vagy LTE), szünetmentesítés |
| Biztonság | zárt, IP65 doboz, megközelíthető szerelési hely (tető/technikai tér) |
| Tulajdonos | önkormányzat, kikötő, vízügyi objektum, magánpartner – **ki kell kérni az engedélyt** |

---

## 3. Hardver – telephelyenként

| Elem | Specifikáció | Közelítő ár (EUR) |
|---|---|---|
| AIS vevő | 2 csatornás (161,975 + 162,025 MHz), NMEA 0183 kimenet (UDP vagy USB-sorozat), folyamatos üzem | 150–400 |
| VHF antenna | AIS-re hangolt, fix, függőleges polarizáció, ~3 dB erősítés | 80–250 |
| Antennaoszlop + rögzítés | 6–12 m acéloszlop, alapozás, guajszalás | 150–400 |
| Koax | RG-58/U (max. ~10 m), hosszabb kábelhez RG-213 + alacsony veszteségű csatlakozók | 20–60 |
| Viharvédelem | Földelés, SPD (túlfeszültség-levezető), biztonsági kötés | 40–100 |
| Számítógép | ipari mini PC vagy Raspberry Pi 4/5, 2 GB RAM, 64 GB eMMC/SSD, Linux | 120–300 |
| Hálózat | 4G/5G modem + SIM (vagy DSL), VPN (WireGuard) a központba | 15–40/hó |
| Tároló | szekrény (IP65), 230 V tápegység, akkumulátor (UPS) | 80–200 |
| **Összesen / site** | | **~700–1 700 EUR** + telepítés |

**Telepítési költség:** kivitelező, út/állás megközelítés, antenna-szerelés (magasban) – **~500–1 500 EUR / site**. Az Antenna oszlopos, magasban történő szerelése a legdrágább tétel (daruklift, bontás nélkül).

**Karbantartás:** SIM (30 €/hó), éves ellenőrzés (antenna, kábel, táp, hőmérséklet), helyszíni hiba esetén csere. **~100–200 EUR / site / év.**

### 3.1 Alternatíva: „külső antenna, házban a vevő"

Ha a telephely nem ad magas antenna helyet, a vevő a házban van, és csak az antenna + koax kerül ki. A koax vesztesége miatt **a hosszú kábel rontja a hatótávot** – ezért a vevőt a lehető legközelebb kell tenni az antennához.

---

## 4. Szoftver és adatút

> **A konkrét átvitel, a broker-konfiguráció, az ACL-ek és a központi ingest lépései:** [`ingest-terv.md`](ingest-terv.md). Az alábbiak a nagyvonalú vázlat.

```
[vevő telephely]
  AIS vevő → NMEA 0183 (UDP/5000 vagy USB) → helyi buffer (60 perc)
      → TLS/MQTT vagy VPN tunnel → központi ingest
                    ↓
     raw archive (Parquet, gzip, objektátár)  ← 14 nap NMEA + korlátlan statikus kivonat
                    ↓
     parser (Msg 1/3/5/18/24 + Inland FI 10) → normalizálás → dedup
                    ↓
     Postgres: position (partícionált), vessel, vessel_data_origin
                    ↓
     AIS-static kivonat → vessel katalógus (R1)
```

### 4.1 Komponensek

| Komponens | Választás | Megjegyzés |
|---|---|---|
| NMEA-decoding | `gpsd` (AIVDM parser) vagy `pyais` / Rust `ais-parser` | Nyílt forráskód, nem kell fizetős könyvtár |
| Helyi buffer | `gpsd` beépített, vagy `ais-router` | Hálózat-kiesésnél ne vesszen el adatot |
| Forwarding | MQTT over TLS (vagy WireGuard + NMEA/UDP) | A VPN egyszerűbb, az MQTT jobban skálázódik |
| Időszinkron | NTP (a központ), GNSS-idő a hajópozícióban | A pozíció időbélyege a hajó GNSS-jéből jön – ezt nem kell szinkronizálni |
| Központi tárolás | Parquet (zstd) objektátárban + Postgres | A nyers NMEA Parquetben, a normalizált pozíció Postgresben |
| Dedup | `ais_message_raw` hash + `ON CONFLICT (vessel_id, ts)` | Azonos szabálykészlet, mint az adat-terv 7. fejezete |
| Monitorozás | site-heartbeat (5 percenként), riasztás kiesésre | A site kiesése = adatlyuk, ezt azonnal látni kell |

### 4.2 A „ghost" hajók kiszűrése – ami a saját vevővel egyszerűbb

A szárazföldi vevők a parton állva **a szárazföldön ülő hajók pozícióját is látják** (a belső GPS hibája, vagy a hajó valóban a parton van). Ezek szűrése:

1. **Pozíció-ellenőrzés:** a pozíció a folyó geometriáján belül van-e (a Duna/polygon buffer), és a hajó nem áll 5+ napig ugyanott.
2. **Sebesség-ellenőrzés:** a `sog` értéke 0 és 12 csomó között van-e (a Duna legnagyobb hajói is lassabbak).
3. **Kézi lista:** a legismertebb „szárazföldi" MMSI-k (pl. a hajógáyak kikötői, a munkahajók) kizárása.

> A saját vevő előnye itt is látszik: **minden üzenetet mi tárolunk**, így a szűrőután is visszakereshető, és a későbbi elemzések (pl. „melyik hajó hol tartózkodik a legtöbbet") nem torzulnak.

---

## 5. A mérési protokoll (go/no-go)

> **Mielőtt bármit építünk, mérünk.** 30 nap, 1 próbavevő, a legforgalmasabb szakaszon.

### 5.1 A mérés beállítása

| Elem | Beállítás |
|---|---|
| Helyszín | Budapest (a legforgalmasabb szakasz), magas antenna (parti magaslat vagy 15–20 m oszlop) |
| Időtartam | **30 nap** folyamatos rögzítés |
| Mentés | minden NMEA üzenet, plusz napi összesítés |

### 5.2 A mérésből számolt metrikák

| Metrika | Kérdés, amire választ ad | Küszöb |
|---|---|---|
| **Hétközapi látható MMSI-k száma** | Hány magyar (243-as MID) hajót látunk egy napon? | ≥ 120 |
| **A magyar flotta lefedettsége** | A napi látott magyar hajók aránya a teljes magyar AIS-flotta ~1 300-hoz képest | ≥ 50% |
| **A statikus üzenetek aránya** | Hány hajóról érkezik Msg 5 / FI 10? | a beépülési arány nő, ahogy gyűlik |
| **ENI-arány** | A látt hajók közül hány ad FI 10-et (tehát ENI-t)? | ≥ 50% |
| **Látótávolság** | A pozíciók km szerinti eloszlása a vevőtől | a 30 km-es határon belül a hajók többsége |
| **Adatveszteség** | Kiesett-e üzenet (hálózat, táp)? | < 1% |
| **Éjszakai lefedettség** | Van-e különbség nappal/éjjel? (zaj, interferencia) | nincs szignifikáns különbség |

### 5.3 A go/no-go döntés

| Eredmény | Döntés |
|---|---|
| A lefedettség ≥ 50%, és a statikus adatok elegendő mennyiségben érkeznek | **Saját vevőhálózat** – F1 (3 site) azonnal építhető |
| A lefedettség 25–50% | **Hibrid**: saját vevők + S-AIS feed kiegészítésként (a S-AIS a szárazföldi hézagokat tölti be) |
| A lefedettség < 25% | **S-AIS feed kell**, a saját vevő csak kiegészítés (a folyó menti VHF-lefedettség nem elég) |
| Bármely esetben | **A Duna teljes lefedettsége soha nem egyetlen vevővel** – a site-hálózat a cél, a mérés csak a méretezést szolgálja |

---

## 6. Költség és időtartam

### 6.1 Egyszeri beruházás

| Fázis | Site | Hardver + telepítés | Hálózat (első év) |
|---|---|---|---|
| **F0** (mérés) | 1 | ~2 000 EUR | ~40 EUR |
| **F1** | 3 (+1) | ~8 000 EUR | ~160 EUR |
| **F2** | 8 | ~20 000 EUR | ~400 EUR |
| **F3** | 15 | ~38 000 EUR | ~750 EUR |
| **B1** (Balaton) | 2 | ~5 000 EUR | ~100 EUR |

### 6.2 Folyó költség (F2, 8 site)

| Tétel | Éves költség |
|---|---|
| SIM és hálózat | ~500 EUR |
| Karbantartás, alkatrész | ~1 500 EUR |
| Akkumulátor/csere | ~300 EUR |
| **Összesen** | **~2 300 EUR/év** |

**Összehasonlítás:** egy kereskedelmi AIS-feed hajószámonkénti díja 8 site lefedettséggel (a magyar flotta nagyjából 1 300 hajó) **évi öt számjegyű összeget** jelenthet – a saját hálózat ugyanezt a lefedettséget évi ~2 300 EUR-ral adja, plusz korlátlan historikus nyers adattal és a cég saját adatbázisával.

### 6.3 Időtartam

| Hónap | Tevékenység |
|---|---|
| 1 | hardver beszerzés, 1 próbavevő telepítése (Budapest), NMEA-parser, nyers mentés |
| 2 | **mérés folytatódik**; közben a központi ingest és az adatbázis-váz elkészül |
| 3 | **go/no-go döntés**; F1 site-ek kiválasztása és telepítése (2–3 site/hónap) |
| 4–5 | F1/F2 bővítés; a statikus hajóadat gyűlik; a katalógus épül |
| 6 | **R1 katalógus** a begyűjtött adatból |

> **A vevőépítés az R1-0 fázis.** Aki ezt 3 hónappal a formális R1 előtt elindítja, az R1-et a begyűjtött statikus adattal tudja elindítani – ahogy az adat-terv 8. fejezete előrevette.

---

## 7. Kockázatok

| Kockázat | Valószínűség | Hatás | Mitigáció |
|---|---|---|---|
| A lefedettség a mérés alapján nem elég | közepes | a katalógus hiányos | A mérés a 2. hónap végére kész; a döntés ekkor van, nem az R1 elején |
| Telepítési engedély elakad | közepes | egy site csúszik | A site-ok listáján legyen 2–3 tartalék telephely; a kikötők és vízügyi objektumok a legegyszerűbbek |
| Antenna viharban megsérül | közepes | adatlyuk | Villámvédelem + biztonsági kötés; a site-ok redundánciája |
| Site kiesése (táp/hálózat) | magas | adatlyuk | Heartbeat-riasztás, UPS, távoli újraindítás; ha hosszabb kiesés, a szomszédos site átveszi |
| A szomszédos site-ok sem fedik le a kanyart | közepes | „lyuk" a folyón | A mérés kimutatja; a site-ok távolságát a kanyarus szakaszokon döntsük el, nem a km szerint |
| A szolgáltatói feedre való átállás kelleni kell | alacsony | a hálózat elpazarolja a ráfordítást | A vevőhálózat **önmagában is hasznos**: a statikus katalógus és a pozíciótörténet önmagában is a termék alapja |

---

## 8. Miért éri meg a vevő a saját adatbázis miatt

A vevő nem csak adatot ad – **adatarchívumot** épít, amit a termék később újra felhasználhat:

| Termékfunkció | A vevő adta előny |
|---|---|
| ETA-modell (R4) | a historikus pozíciósor a saját tréningadatunk – nem kell külső modellt fizetni |
| Zsilipvárakozási elemzés | a valós áthaladási idők historikus sorból |
| Útvonal-tervezés | a leggyakoribb útvonalak a saját forgalmunkból |
| Szezon- és trendelemzés | a hajók aktivitása, a flotta terhelése |
| B2B adatértékesítés | historikus forgalmi statisztika (a Duna Bizottság statisztikáinak valós idejű megfelelője) |

> **Ez az igazi üzleti indoklás:** a fizetős feedből *pillanatnyi* adatot kapnál; a saját vevőből **történet** lesz, és a történet értékesebb, mint a pillanat.

---

## 9. Akciólista

| # | Feladat | Ki | Mikor |
|---|---|---|---|
| 1 | Telephely-vizsgálat: Budapest (3–4 jelölt hely), tulajdonosi egyeztetés | fejlesztés | 1. hét |
| 2 | Hardver beszerzése (1 próbavevő + tartalék alkatrész) | törzs | 1–2. hét |
| 3 | NMEA-parser + nyers mentés + heartbeat a szerverre | fejlesztés | 2. hét |
| 4 | **30 napos mérés** indul | fejlesztés | 3. hét |
| 5 | Központi ingest + Postgres séma (raw archive + position partíciók) | fejlesztés | 2–3. hét |
| 6 | **Go/no-go elemzés** a mérési metrikákból | fejlesztés + törzs | 4. hét |
| 7 | F1 site-ek kiválasztása (a mérési eredmény alapján) | fejlesztés | 4. hét |
| 8 | F1 telepítése (2–3 site) | kivitelező | 5–7. hét |
| 9 | Statikus kivonat és `vessel` rekordok építése az összegyűlt adatból | fejlesztés | 6–8. hét |
| 10 | Balaton: 1–2 próbavevő (Siófok, Keszthely/Füred) a nagyhajókhoz | fejlesztés | 8. hét |

---

## 10. A Budapesti vevő – konkrét konfiguráció és értékelés

**Terv (2026-11-14):** egyetlen vevő, Budapest, a parttól ~2 km-re, egy lakóház 3. emeletén. Hardver: Raspberry Pi 3B+ + RTL2832U USB dongle.

> **A konkrét telepítési lépések** (OS, SDR-driver, AIS-catcher, systemd, hűtés, biztonság) külön dokumentumban vannak: [`pi-eloallitas.md`](pi-eloallitas.md) – és ugyanott az **ADS-B lánc** beállítása is, ha a Pi-t a Flightradar24-feedhez is használod.

### 10.1 A lefedettség – a konkrét számok

| Elem | Érték |
|---|---|
| Antenna magassága (3. emelet) | ~10–12 m a vízszint felett |
| Rádióhorizont a vevőtől | 4,12 × √12 ≈ **14,3 km** |
| Rádióhorizont a hajótól (5 m antennával) | 4,12 × √5 ≈ **9,2 km** |
| Teljes rádióhorizont | **~23,5 km** |
| A parttól mért távolság | **−2 km** (a legközelebbi folyószakasz is 2 km-re van!) |
| **Hasznos folyólefedettség** | **~15–20 km a folyó mentén, mindkét irányban** |

**Két dolog, amit ez jelent:**

1. **A 2 km távolság a látómező elejét „elvágja".** A vevő a hozzá legközelebbi 2 km folyószakaszt **nem látja** – pont azokat a hajókat, amelyek a kikötő közelében vannak. Ez a „luk" a katalógusban és a térképen is látszik majd.
2. **A 3. emelet nem elég.** Ha az antenna a tető fölé kerül (3–5 m-rel magasabbra), a horizont 14,3 km-ről ~17 km-re nő, ami **+2–3 km mindkét irányban**. Ez olcsó és gyors nyereség.

**Ellenőrizendő helyszínen:** ha a lakás a **budai oldalon** van, a **Gellért-hegy (210 m)** és a nyugati budai dombok takarhatják a kilátást bizonyos irányokban. A pesti oldal sík, ott nincs takarás. **Ez az első dolog, amit a telepítéskor nézni kell.**

### 10.2 A rádió: az RTL2832U megfelel-e?

**Igen, működik** – ez a szokásos DIY AIS-vevő, és az AIS mindkét csatornáját (161,975 / 162,025 MHz) fogja. **De négy konkrét korlát van, és mindegyik kezelhető:**

| Korlát | Részlet | Megoldás |
|---|---|---|
| **Frekvenciapontatlanság** | A generikus DVB-T dongle frekvenciája több tíz ppm-rel elcsúszhat; **±3 ppm már rontja a dekódolást**, és hőmérséklet-változással tovább driftel | `rtl_test -p` kalibráció + **TCXO-s dongle** (RTL-SDR Blog V3, 0,5 ppm) – a kalibrációt nem kell hetente ismételni |
| **Egycsatornás kényszer** | A szimpla, egy frekvenciára hangolt mód **csak egy AIS-csatornát** fogad | Használjunk **széles sávsávos (wideband) módot**: a két csatorna 50 kHz-re van egymástól, tehát egy 2,048 MS/s mintában **mindkettő benne van**, és digitálisan szétválasztható |
| **Érzékenység** | Az R820T/R820T2 tuner 162 MHz-en nem optimális; a hatótáv a számított horizontnál **rövidebb** lesz | Aktív antenna (beépített LNA) vagy külső LNA + 162 MHz-es SAW szűrő (~20 EUR) |
| **Túlterhelés és LO-leakage** | Erős közeli jel (pl. a parton álló hajó, egy közeli bázisállomás) leterítheti a dongle-t; a helyi oszcillátor szivárgása fantomcélokat okozhat | A dongle **távol az antennától**, kábel-szűrő a bemeneten, és **a gain ne legyen automatikus maximumon** |

> **A fontos ajánlás:** a **kiértékeléshez ez a konfiguráció tökéletes** (a pipeline-t, a parsert, az adatbázist ezzel validáljuk). **Az éles vevőbe viszont valódi AIS-vevőt tennék**, nem az RTL donglet – lásd 10.4.

### 10.3 A Raspberry Pi 3B+

**Bőséges.** Az AIS-dekódolás loadja nevesebb (néhány ezer üzenet/perc), mint egyetlen lapos weboldal betöltése. Három dologra figyelj:

| Téma | Megjegyzés |
|---|---|
| **SD-kártya kopás** | A folyamatos írás megyasztja. A Pi **ne írjon a kártyára**, hanem: nyers NMEA → hálózat (MQTT/VPN) a szerverre, helyben csak 1–2 óra buffer. Ha mégis helyi írás kell, USB-SSD |
| **Tápellátás** | Pi 3B+ + USB-dongle + Wi-Fi: **5,1 V / 3 A** tápegység kell, különben brownout |
| **Hő** | A dongle és a Pi is melegszik egy zárt szekrényben – szellőzés kell (a dongle túlmelegedhet) |

### 10.4 Az éles vevő ajánlott összeállítása

| Elem | Ajánlott | Ár (EUR) |
|---|---|---|
| **Vevő** | **Valódi AIS-vevő NMEA-kimenettel** – u-blox AIS modul (Class B transzponderből) vagy ethernetes/USB-s AIS-vevő | 70–150 |
| Antenna | AIS-re hangolt 3/4 hullámos, ~1,2 m, tetőn 3–5 m-es oszlopon | 40–90 |
| Szűrő | 162 MHz SAW sávszűrő (a LO-leakage és a túlterhelés ellen) | 15–25 |
| Koax | RG-58/U (rövid), RG-213 (hosszabb) – minden dB kábelveszteség a hatótávból jön | 20–50 |
| Számítógép | Pi 3B+ (megfelel) vagy Pi 4/5, ha helyben is fut valami | – |
| Hálózat | Ethernet ha lehet, különben 4G; WireGuard/MQTT a központba | 15–40/hó |

**Miért érdemes cserélni a donglet?**
- **két csatorna** egyidejűleg, gondolkodás nélkül
- **jóval nagyobb érzékenység** 162 MHz-en → a valós hatótáv közel a számított horizont
- **nincs kalibráció**, nincs ppm-drift, nincs fájdalmas hangolás
- **tiszta NMEA 0183 kimenet** → a szerveroldali parser nem függ az SDR-szoftvertől
- a **megbízhatóság** üzleti kritérium: egy kieső éjszaka adatlyuk

> **Kompromisszum:** a u-blox AIS modulok NMEA-t adnak ki, de **nem minden doboz adja ki a nyers belső (FI 10) üzeneteket** – ezt **vásárlás előtt ellenőrizni kell**: a vevőnek a teljes NMEA/AIVDM folyamot ki kell adnia, mert az ENI a belvízi FI 10 üzenetben van. A kérdés, amit a beszállítónak fel kell tenni: *„a kimenet tartalmazza-e az Inland AIS FI 10 (üzenet 8, FI=10) bináris üzeneteket?"*

### 10.5 Szoftver

| Szoftver | Értékelés |
|---|---|
| **AIS-catcher** | **Ajánlott.** Statisztikai felület (üzenet/óra, PPM-grafikon), JSON kimenet, **belvízi (FI 10) dekódolás**, webes felület a készüléken |
| rtl_ais | működik, de nincs belvízi FI 10 dekódolás és nincs ilyen diagnosztika |
| gpsd | a szerveroldali NMEA-fogadáshoz jó választás |

**Kalibrálási folyamat (ez kötelező lépés a dongles telepítésnél):**
1. `rtl_test -p` – 10 perc, a ppm-eltérés meghatározása
2. `rtl_test` – a jel erősségének ellenőrzése a 162 MHz-en
3. AIS-catcherben a `-p` érték beállítása, majd **a PPM-grafikon ellenőrzése 24 órán át** (a hőmérséklet-változás miatt)
4. A gain manuális beállítása, túlterhelés ellenőrzése

### 10.6 Amit egyetlen vevő jelent az R1-re

**Őszinte értékelés:** egy budapesti vevő a **budapesti szakaszt** fedi le (jegyük Csepel–Szob–Bajai, ~25–35 km folyó). Ez **a legforgalmasabb szakasz**, de a teljes magyar Duna-flottának csak egy részét.

| Lehetőség | Értékelés |
|---|---|
| **A. Egy saját vevő + S-AIS feed a többi szakaszra** | **Ajánlott.** A saját vevő adja a jó minőségű budapesti adatot + a **referenciát** (ground truth), amivel a feed ellenőrizhető. A feed a hiányzó szakaszokat hozza, ahol a S-AIS elég |
| B. Egy saját vevő + később 2–3 további site | A végállapot, de a ~2 500–5 000 EUR beruházás egy későbbi döntés |
| C. Csak egy saját vevő, nincs feed | A katalógus a **budapesti szakaszra** korlátozódik – ez egy **regionális szolgáltatás**, nem „a Dunáról szóló katalógus". Őszintén ezt kell kommunikálni, nem úgy mutatni, mintha az egész folyó lefedett |

**A lényeg, amit a vevőépítés hoz:** a saját vevő nem csak adat, hanem **mérőműszer**. Ha a Budapesti vevő működik, onnantól **minden további site egy másolás**, és a S-AIS feed minőségét is tudjuk validálni.

### 10.7 Működési rend a gyakorlatban

```
[antenna tetőn] → [162 MHz szűrő] → [koax] → [AIS vevő] → [Pi: AIS-catcher] → [MQTT/WireGuard] → [szerver]
                                                     ↓
                                              helyi buffer (1-2 óra, memóra)
```

| Elem | Felelősség |
|---|---|
| Antenna + szűrő | a ház tulajdonosa (tető) |
| Vevő + Pi | a projekt |
| Hálózat (4G/Ethernet) | a projekt |
| Szerver (ingest + Postgres) | a projekt |

**A vevő kiesése észlelhető:** a heartbeat 5 percenként megy, és a `last_seen_at` a `ais_receiver_site` táblában figyelt → a kiesés riasztás, nem néma adatveszteség.

---

## 11. Forráshivatkozások

- MarineTraffic – AIS vevőállomás telepítése (antenna magasság, hatótáv, „csak állandó áram és stabil internet kell") – [MT támogatás](https://support.marinetraffic.com/en/articles/9552957-how-to-install-an-ais-station)
- MarineTraffic – AIS vevőállomások: a vevő nem sugároz, bárki üzemeltetheti – [MT támogatás](https://support.marinetraffic.com/en/articles/9552994-ais-receiving-stations)
- CESNI/UNECE/CCNR – Inland AIS telepítési irányelvek (antenna, interferencia, műszaki teszt) – [CESNI](https://www.cesni.eu/wp-content/uploads/2022/11/L_dir_syst_auto_ident_en_1.pdf)
- Az AIS VHF-jel hatótávja (antennamagasság-függés, 20 m → ~25 nemzetközi tengeri mérföld) – [svb24](https://www.svb24.com/de/ratgeber/alles-was-sie-ueber-ais-wissen-sollten.html)
- Directive 2002/59/EK + 2014/100/EU – hajófelügyeleti rendszer (VTMIS) és az adatok hozzáférhetősége – [EUR-Lex](http://www.eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex:32014L0100)
- Bizottsági javaslat a River Information Services-irányelvhez (2004) – a RIS-alkalmazások áttekintése, **DoRIS** (osztrák Duna-risz), a forgalmi adatok központi tárolása és az XML-interfész külső logisztikai szerverekhez – [EUR-Lex](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex:52004PC0392)
- Commission Regulation (EC) No 415/2007 – belvízi AIS, a belső FI 10 üzenet tartalma – [EUR-Lex](https://www.legislation.gov.uk/eur/2007/415/adopted/data.xht)
- MarineTraffic – DVB-T stick használata AIS-vevőként: **egyszerre csak egy AIS-csatorna** a hangolt módban, frekvenciakorrekció szükséges, az antenna csatlakozója számít – [MT támogatás](https://support.marinetraffic.com/en/articles/9552960-how-to-build-an-ais-station-with-sdr-dvb-t)
- AIS-catcher – a PPM-eltérés mérésének és finomhangolásának gyakorlata, a ppm-drift hőmérsékletfüggése – [AIS-catcher](https://github.com/jvde-github/AIS-catcher/discussions/75)
- RTL-SDR Blog V3 – TCXO-s, 0,5 ppm stabilitású vevő (a frekvenciakorrekció elhagyható) – [rtl-sdr.com](https://www.rtl-sdr.com/rtl-sdr-v3/)
