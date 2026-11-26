# Implementációs terv – 04: AIS-parser specifikáció

**Verzió:** 1.0 (a 1. körű swarm review után — **64 finding**
(3 reviewer: `prof` 27 · `bori` 18 · `preshaz` 19), a verifier audit
szerint **61 valós, 11 blokkoló** — **mind javítva**)
**Dátum:** 2026-11-23

> **Ez a terv a MÉRÉS UTÁN készült.** A bud01 vevő 2026-11-22 19:19
> óta fut, és a mérés első órája **öt ponton ellentmondott** a
> v0.1-es draftnak (a `docs/measurement_2026-11-22.md`):
>
> | A v0.1 állítása | A mérés |
> |---|---|
> | a nyers adat Parquet + gzip archívumban | **SQLite** (a v0.71 sémája) + heti lehúzás |
> | ~2 millió üzenet/nap | **~900 000/nap** (átlag ~10,4/mp, csúcs ~100–300/mp) |
> | a hibás üzenetek aránya mérhető | **nem mérhető** (a vevő csak a sikeres dekódolásokat tárolja) |
> | a `river_km` a fairway-mezőből jön | **a fairway-mező a magyar szakaszon üres** |
> | a Msg 4/9/11 eldobandó | **a Msg 4/20/23 a NAVTEX/MSK-forrás** (a mért forgalom 27,3%-a) |
>
> **A javítások a tervet a méréshez igazítják — nem fordítva.**
**Kapcsolódó dokumentumok:**
[`../../README.md`](../../README.md) (adatbázis-terv v1.3) ·
[`megvalosulas-01-stack-es-struktura.md`](megvalosulas-01-stack-es-struktura.md) (stack + struktúra) ·
[`megvalosulas-02-adatbazis-ddl.md`](megvalosulas-02-adatbazis-ddl.md) (a séma **v1.5** — a parser ide ír) ·
[`megvalosulas-03-api-specifikacio.md`](megvalosulas-03-api-specifikacio.md) (a normalizált rekord a kimenete, **v0.4**) ·
[`../../docs/ais-vevo-terv.md`](../../docs/ais-vevo-terv.md) (a vevőhálózat) ·
[`../../docs/ingest-terv.md`](../../docs/ingest-terv.md) (az adatút) ·
[`../../docs/r1-adat-terv.md`](../../docs/r1-adat-terv.md) ·
[`README.md`](README.md) (a terv-sorozat tagjai)

**Projekt:** `vessel-tracker` — a hajókövető a Dunán és a Balatonon.

> A dokumentum a repóban a `docs/megvalosulas/04-ais-parser.md` útvonalon
> van — a relatív linkek ehhez képest számolnak.

---

## 1. Mi a parser feladata

A parser a **nyers NMEA 0183 üzenetekből** a **normalizált rekordot**
állítja elő — ez a 02-es terv szerinti **közös szerződés** a `04` és a
`02` között (a `02` §10.1).

```
nyers NMEA (UDP/5000 vagy MQTT)
   → [a] frame-szintű validáció (a szabályos NMEA-körvonal, a
      ellenőrzőösszeg, a mondatszám, a számozott sorok összefűzése)
   → [b] AIS-üzenet dekódolása (a 6 bites payload)
   → [c] üzenettípus-dispatch:
        a HAJÓ-üzenetek (Msg 1/2/3/5/18/24 + Inland FI 10)
        ÉS a NEM-HAJÓ üzenetek (Msg 4/20/21/23) külön kategóriaként
        (a §4.7 — a bud01 mérés: a mért forgalom 27,3%-a a nem hajó
        üzenettípusok)
   → [d] normalizálás (a közös rekord)
   → [e] dedup (a msg_hash)
   → [f] írás a DB-be (a position upsert, a vessel upsert)
   → [g] mezőnkénti eredet (a vessel_data_origin — a F-DET-15)
```

**Amit a parser NEM csinál:**
- **nem** dönt a fantom-hajóról (a szűrő a 01-es terv §5.5 szerinti
  négy szabály — a parser csak a **geometriai** ellenőrzés adatait
  szolgáltatja); **a navigációs lámpákat és a bázisállomásokat is
  kizárja** (a MMSI-tartomány + a név-minta alapján — a `bori` B-C-4
  findingje: a felhasználó nem látja a 106 lámpát „hajóként");
- **nem** kezeli a forrásjogokat (a `data_source` a konfigurációból jön);
- **nem** hoz létre `content_key`-t (a súgók és a rendszerüzenetek
  szerkesztői tartalom — a `bori` B-M-5 findingje);
- **nem** számítja a bizonyossági badge-et (a `vessel_verification`
  nézet a service szintjén — a `bori` B-M-1 findingje);
- **nem** tölti ki a `destination`-t (a mérésben 100%-ban üres → **a
  szerkesztői felület adja**, a `06` terv — a `bori` B-C-2 findingje);
- **nem** ütemez (az APScheduler / `pg_cron` a felelőse).

**Amit a parser KÖTELESEN elvégez:**
- a **`vessel.operating_area`** kitöltése (a `duna`/`balaton`) — a pozíció
  földrajzi elhelyezkedéséből (a folyó-korridor vs. a Balaton-medence)
  → **ez a F-CAT-01 (a területválasztó) és a `03` – API-terv kötelező
  `area` paraméterének az alapja** (a `bori` B-H-7 findingje);
- a **`vessel.flag_country_code`** kitöltése — a MMSI-prefixből (a
  `country` tábla segítségével) → **a felhasználó megkülönbözteti a
  magyar és a nemzetközi hajót** (a `bori` B-H-5 findingje; a mérésben
  **67 magyar és 11 nemzetközi** hajó);
- a **`callsign` normalizálása** (a `@` kitöltés levágva, a trim, és a
  **kis/nagybetű egységesítése**) → a keresés **case-insensitive**
  (a `bori` B-H-2 findingje: a mérésben **76 hajónak van hívójele**
  — a hívójel a **másodlagos keresési kulcs** az ENI után).

---

## 2. A technológiai döntés

### 2.1 A saját dekóder

| | `aiscat` | `pyais` | **saját dekóder** |
|---|---|---|---|
| Licenc | **GPLv3** (az AIS-catcher C++ motorját örökli) | MIT | saját (MIT) |
| Nyelv | Python/C++ | Python | **Python** |
| Belvízi támogatás | teljes | részleges | teljes |
| Mezők nevei | **sematikus** (`msg_type`, `mmsi`, `lat`, `lon`) | **neves** (`MessageType8Dac200Fid10` → `vin`, `shiptype`, `length`, `beam`, `draught`) | **sematikus** (a 02-es séma oszlopneveivel egyezik) |
| Karbantartás | aktív | aktív | **a mink** |

**A licenc pontosítása** (a `prof` M-8 findingje): a fenti táblázat **a
dekóderek** licencéről szól, **nem a projektéről** — a projekt licencét a
README szabja meg. A **saját dekóder** MIT-licencű, **de a projekt
licenc-döntése független** a dekódertől (a GPLv3-as `aiscat` használata
terítette volna a teljes kódra).

**A döntés: saját dekóder** (a 01-es terv §5.3).

**Az okok (a `prof` reviewer 2. körű H-N-1 findingje után pontosítva):**

1. **A GPLv3 a projekt licencét meghatározza.** Az `aiscat` használata
   GPLv3-at tesz a teljes kódra — egy zártforrású API-kliens
   (R5) nem osztható GPLv3 alatt. **A saját dekóder ezt a problémát
   nem hozza létre.**
2. **A `pyais` NEM ad mezőszintű belvízi szemantikát** — a korábbi
   állítás („a pyais mezőszinten nem strukturált") **HAMIS** volt: a
   `MessageType8Dac200Fid10` **neves mezőket ad** (`vin`, `shiptype`,
   `length`, `beam`, `draught`). A valódi ok: a `pyais` **nem ad
   `river_km`-t** (a fairway hectometre mezőt) és a mezőnevek nem
   illeszkednek a 02-es sémához — tehát **az átalakítás költsége
   nagyobb, mint a saját dekóderé**.
3. **A saját dekóder 300–400 sor** — az AIS payload 6 bites karakterkódolás
   (a nemzetközi specifikáció), a formátum **dokumentált és stabil**.

### 2.2 Mit jelent a „sematikus" mezőnév

A parser kimenete **közvetlenül a 02-es séma oszlopneveivel** egyezik:

| AIS mező | A parser kimenete | A séma oszlopa |
|---|---|---|
| `mmsi` | `mmsi` | `vessel.mmsi` |
| `lat` / `lon` | `lat_e7` / `lon_e7` | `position.lat_e7` / `lon_e7` |
| `sog` | `sog_mps` | `position.sog_mps` |
| `cog` | `cog_deg` | `position.cog_deg` |
| `true_heading` | `heading_deg` | `position.heading_deg` |
| `rot` | `rot_deg` | `position.rot_deg` |
| `pos_accuracy` | `ais_accuracy_m` | `position.ais_accuracy_m` |
| `nav_status` | `nav_status` | `position.nav_status` |
| `mmsi` (statikus) | `mmsi` | `vessel.mmsi` |
| `imo` | `imo` | `vessel.imo` |
| `callsign` | `callsign` | `vessel.callsign` |
| `name` (Msg 5) | `name` | `vessel_i18n.name` |
| `shiptype` (FI 10) | `vessel_type_code` | `vessel.vessel_type_code` |
| `length` / `beam` / `draught` (FI 10) | `length_m` / `beam_m` / `draught_max_m` | `vessel.*` |
| `fairway_distance` (FI 10) | `river_km` | `position.river_km` |
| `en` (FI 10) | `eni` | `vessel.eni` |

**Az `mmsi` az összekötő kulcs** — az AIS-ből mindig jön, a `vessel`
tábla elsődleges azonosítója.

**A `nav_status` értékkészlete** (a `prof` L-2 findingje) — a 02-es
`position.nav_status` CHECK-ja (a v1.5):

| Kód | Jelentés |
|---|---|
| 0 | under way using engine |
| 1 | at anchor |
| 2 | not under command |
| 3 | restricted manoeuvrability |
| 4 | constrained by her draught |
| 5 | moored |
| 6 | aground |
| 7 | engaged in fishing |
| 8 | under way sailing |
| 9 | reserved (HSC) |
| 10 | reserved (WIG) |
| 11 | power-driven vessel towing astern |
| 12 | power-driven vessel pushing ahead |
| 13 | power-driven vessel towing alongside |
| 14 | reserved for future amendment of navigational status |
| 15 | undefined |

**A `msg_type` és a `msg_subtype`** (a `prof` L-3 findingje): a
`msg_type` az AIS `type` mezője (1–27); **a DAC/FID a `msg_subtype`-
ben van** (a 02-es v1.5 `position.msg_subtype smallint`) → **a FI 10
a 6-os/8-as `msg_type` + a `msg_subtype=10`** (a DAC 200), a Class B a
21-es + a `msg_subtype=21`.

---

## 3. A frame-szintű validáció (a NMEA 0183 körvonal)

### 3.1 A formátum

```
!AIVDM,1,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23
│     │  ││ │ │                                │ │
│     │  ││ │ │                                │ └─ a checksum (hex, 2 karakter)
│     │  ││ │ │                                └─── a payload (max. 82 karakter)
│     │  ││ │ └──────────────────────────────────── a talker+type ("AIVDM")
│     │  ││ └────────────────────────────────────── a rádió (a hosszú 'A')
│     │  │└──────────────────────────────────────── a számozott sorok száma
│     │  └───────────────────────────────────────── a sor sorszáma (1-ből)
│     └──────────────────────────────────────────── a formátum ("!")
└────────────────────────────────────────────────── a sentence azonosító
```

**A szabályok (a szabványból):**

| Szabály | Ellenőrzés |
|---|---|
| A mondat `$` (vagy `!`) karakterrel kezdődik | a szabályos karakterkészlet |
| A mezők vesszővel elválasztottak | a mezőszám ellenőrzése |
| A `*` után 2 hex karakter a checksum | az **XOR** a `$`/`!` és a `*` közötti karaktereken |
| Az `n` (sorok száma) 1–9 | a 0 érték érvénytelen |
| Az `r` (sorszám) 1..n | a `r` nem lehet nagyobb, mint `n` |

### 3.2 A számozott sorok összefűzése

**Az AIS üzenetek 82 karakter fölé nem férnek egy NMEA sorba** → a
formátum több sort használ (`1/3`, `2/3`, `3/3`).

**A szabály:**
1. az `1/n` sor kezdi az üzenetet;
2. az `r/n` sorok **rendben** jönnek (`r` növekvő);
3. a `payload` részeket **összefűzzük** (a `,` és az `*` nélkül);
4. az utolsó sor `fill_bits` mezője a payload **kitöltő bitjeinek száma**
   (0–5).

**Hiba esetén** (a `r` nem folytonos, a `payload` > 82 karakter, a
checksum hibás): **az üzenet eldobandó, és egy `data_quality_event`
íródik** (a `reason = 'parser_error'`).

### 3.3 A `fill_bits` kezelése

A `fill_bits` a payload **utolsó** bitjeinek száma, amik kitöltő
nullák. **A 6 bites karakterkódolásban** a kitöltő bitek a karakter
legalsó bitjeiben vannak → a `fill_bits` szám **a teljes payload
bitjeinek számával** számolódik (a karakterenkénti 6-tól).

**A dekódolás előtt** a `fill_bits` biteket el kell távolítani:
```python
bits = payload_bits[: len(payload_bits) - fill_bits]
```

---

## 4. Az AIS payload dekódolása

### 4.1 A 6 bites karakterkódolás

**A karakter -> a 6 bites érték (a GPSD szerint, az ITU-R M.1371
alapján):**

| A tartomány | A 6 bites érték |
|---|---|
| `0`–`W` (a 0x30–0x57) | **0–39** (az érték + 48) |
| `` ` ``–`w` (a 0x60–0x77) | **40–63** (az érték + 56) |

**A `0x58`–`0x5F` tartomány (a `X`–`_`) ÉRVÉNYETLEN.**

**A bitek a karaktereken belül NEM fordítottak** — a karakter 6 bitje
**MSB-first** sorrendben van.

> **⚠️ A 2026-11-24-i mérés három megállapítása:**
>
> **1. A `bud01` vevő (AIS-catcher v0.71) fizikai 6 bites értékeket
> tárol** a `nmea` oszlopban → **a mérés igazolja: a vevő `type`
> oszlopa 8000/8000 egyezik, ha a `payload[0]` karakter értékét a
> fenti táblázat szerint olvassuk** (a `B`→18, az `E`→21, a `G`→23,
> a `H`→24 → **mindegyik a 0–39 tartományban van**).
>
> **2. A vevő `lat`/`lon`/`mmsi` mezői NORMALIZÁLTAK** → **a `nmea`
> oszlopból csak a `type` olvasható ki megbízhatóan** (a `04` §5, a
> `04` §11 Q8) → **a mérési adatot nem szabad nyers payloadként
> kezelni.**
>
> **3. A GPSD hivatalos referencia-példán a `pyais` (a hivatalos
> referencia-dekoder, a `04` §11 Q6) és a mi dekódolásunk egyezik:**
> a `!AIVDM,1,1,,A,15M67FC000G?ufbE`FepT@3n00Sa,0*5C` → a `type=1`,
> az **MMSI 366 053 209**, a `lat=37.802118`, a `lon=-122.341618`.
> → **a fenti táblázat a helyes** (a `pyais` `_six_bit_to_ascii`
> implementációja).

**Az implementáció:** az `apps/api/src/duna/ingest/decoder.py`
(`decode_standard_6bit` + `decode_physical_6bit` — **a kettő ugyanaz
a kódolás**, a fizikai csak a szándék kifejezésére).

### 4.2 Az üzenet fejléce

A dekódolt bitsor első **168 bitje** (22 karakter) az üzenet fejléce:

| Bit | Méret | Jelentés |
|---|---|---|
| 0–5 | 6 | üzenettípus (1, 3, 4, 5, 18, 19, 24) |
| 6–7 | 2 | ismétlődés (a számozott üzenetek sorszáma) |
| 8–37 | 30 | **MMSI** |
| 38–39 | 2 | navigációs állapot |
| 40–69 | 30 | nemzetközi szám (a 8-as üzenet) |
| 70–115 | 46 | hajógép-állapot (a 18-as üzenet) |

### 4.3 A dinamikus üzenetek (Msg 1, 2, 3)

**A standard AIS bit-sorrend (a GPSD/`pyais` szerint — a `04` §4.1
kódolással):**

| Bit | Hossz | Mező | Típus |
|---|---|---|---|
| 0–5 | 6 | `message_type` (1, 2, 3) | egész |
| 6–7 | 2 | `repeat` | egész |
| 8–37 | 30 | `mmsi` | egész |
| 38–41 | 4 | `nav_status` | 0–15 |
| 42–49 | 8 | a manöverjelzés (a ROT) | előjeles |
| 50–59 | 10 | `sog_mps` | 1/10 csomó, m/s-ra átszámítva (1 csomó = 1852/3600 m/s) |
| 60 | 1 | a pozíció pontossága | 0 = 10 m, 1 = < 10 m |
| 61–88 | 28 | `lon` | előjeles, 1/10000 perc |
| 89–115 | 27 | `lat` | előjeles, 1/10000 perc |
| 116–127 | 12 | `cog_deg` | egész, 1/10 fok |
| 128–136 | 9 | `heading_deg` | egész fok (511: nincs adat) |
| 137–142 | 6 | az időbélyeg | egész |
| 143–144 | 2 | a manöver | 0–3 |
| 145–147 | 3 | a tartalék | |
| 148 | 1 | a RAIM | |
| 149–167 | 19 | a rádióállapot | egész |

> **A korábbi táblázat (a 18 bites LAT/LON a 38–55. bittől, a 10
> bites SOG a 92–99. bittől, a 4 bites rádió) NEM a standard AIS-t
> írta le** → **a 2026-11-24-i implementáció a `pyais` hivatalos
> referenciája alapján javította** (a `04` §11 Q6) → **a GPSD
> referencia-példán a `pyais`-szal és a saját dekódolásunkkal
> egyezik** (`lat=37.802118`, `lon=-122.341618`, `sog=0.0`,
> `cog=219.3`, `heading=1`, `status=3`, `second=59`, `radio=2281`).

**A GNSS antenna helye (a 148–167. bit):** a pozíció **nem** a hajó
középpontjában van, hanem egy antennaszerelésben. Ez a Duna szűk
szakaszain (a keskeny vízállásnál) **fontos**.

**A `02` – DDL-terv `position` táblájában nincs antennaszerelés-mező** —
a F-DET-15 mezőnkénti eredete alapján ez egy **saját mezőnkényi
eredet** lenne, nem külön oszlop. **A parser eldobja** (a `position`
tábla nem tartalmazza), de a `vessel_data_origin` **nem** kap ilyet
(az a statikus adatokra vonatkozik).

> **A `position` `geom` pont a GNSS-antenna helye, nem a hajó
> középpontja.** A UI-n (R2) ez megjegyzendő.

### 4.4 A statikus üzenetek (Msg 5)

> #### 🆕 A STATIKUS ADATOK ÜTEMEZÉSE (a 2026-11-24-i mérési adat)
>
> **Az AIS nem egyetlen csomag:** a **pozícióadatok** (a sebesség, az
> irány, a koordináták) **másodpercenként** sugároznak (a Msg 1/2/3),
> **a statikus adatok** (a hajónév, a méretek, az ENI) **ritkábban,
> általában 6 percenként** (a Msg 5, a belvízi FI 10).
>
> **A mérés igazolja (a `docs/measurement_2026-11-22.md`, a 37 órás adat):**
>
> | A mérőszám | Az érték |
> |---|---|
> | a statikus üzenetek közötti rés (a Msg 5/24) | **a medián 361 mp (6,0 perc)**, a 75% 590 mp (10 perc) |
> | a FI 10 (a belvízi ENI) üzenetek közötti rés | **a medián 364 mp (6,1 perc)** |
> | **a statikus adat elérése a pozíció után** | **a medián 8,8 perc**, a 75% 33,8 perc, **a maximum 795 perc (13 óra)** |
> | 10 percen belül megvan | **51%** |
> | 20 percen belül megvan | **63%** |
>
> **A tervezési következmény:**
>
> **1. Egy „éppen fogott pillanatnyi" AIS-üzenetben NEM feltétlenül van
> az ENI (vagy a név, vagy a méret)** → **a parsernek a statikus
> adatot külön kell kezelnie**, nem a pozícióból derivesztálnia.
>
> **2. A `vessel` rekord a statikus adat nélkül HIÁNYOS** → **a
> `02` §5.3 szerint a `vessel_type_code` NOT NULL** → **a fallback az
> `UNKNOWN` típus** (a `04` §4.5-ökkel) → **a hajó a `vessel`-ben
> létezik, de `name_only`/`UNKNOWN` típussal.**
>
> **3. A katalógus teljessége a mérés időtartamától függ** → **a
> mérési időszak elején (az első órában) az ENI-arány 0,5% volt, és
> 37 óra alatt is csak 0,4%** → **nem az időzavar, hanem az, hogy a
> hajók 76%-a küld FI 10-et, a többi sosem fog ENI-t küldeni ezen a
> vevőn** (a mérés: a 34 pozíciót küldő hajóból **30 navigációs
> lámpa**, és **a 4 valódi hajó NEM küld FI 10-et**).
>
> **4. A `03` – API-terv `meta.hint`-je és a `05` §8.3 „Nincs adat"
> jelölése a helyes megoldás** → **a felhasználónak tudnia kell, hogy
> egy hajó adatai még „érnek"** → **a `vessel_data_origin.observed_at`
> (a statikus adat érkezési ideje) ezt megadja.**

**A standard AIS bit-sorrend (a GPSD/`pyais` szerint):**

| Bit | Hossz | Mező |
|---|---|---|
| 0–5 | 6 | `message_type` (5) |
| 6–7 | 2 | `repeat` |
| 8–37 | 30 | `mmsi` |
| 38–39 | 2 | az AIS-verzió |
| 40–69 | 30 | `imo` |
| **70–111** | **42** | **a hívójel (`callsign`), 7 karakter** |
| **112–231** | **120** | **a hajónév (`shipname`), 20 karakter** |
| 232–239 | 8 | a hajótípus kódja |
| 240–248 | 9 | a GNSS-antenna a hajó orrától (méterben) |
| 249–257 | 9 | a GNSS-antenna a hajó fartól (méterben) |
| 258–263 | 6 | a bal oldali szélesség (méterben) |
| 264–269 | 6 | a jobb oldali szélesség (méterben) |
| 270–273 | 4 | az EPFD (a pozíciójavítás típusa) |
| 274–277 | 4 | a hónap |
| 278–282 | 5 | a nap |
| 283–287 | 5 | az óra |
| 288–293 | 6 | a perc |
| 294–301 | 8 | a merülés (méter, 1/10) |
| 302–421 | 120 | a célállomás (`destination`), 20 karakter |
| 422 | 1 | a DTE |
| 423 | 1 | a tartalék |

> **A korábbi táblázat (a 20 bites hívójel, a 10 bites hossz, a 8
> bites szélesség, a 12 bites ETA) NEM a standard AIS-t írta le** →
> **a 2026-11-24-i implementáció a `pyais` hivatalos referenciája
> alapján javította** (a `04` §11 Q6) → **a magyar hajó
> (`MAHAB ORSZAG`) minden mezője egyezik a `pyais`-szal** (a
> hívójel `HGXC`, a célállomás `BUDAFEST`, a hossz 100 m, a
> szélesség 10 m, a merülés 4,2 m).

**A szövegmezők (a hívójel, a név, a célállomás) kódolása KÜLÖNBÖZIK
a számszerű mezőktől:** a szöveg karaktere a `pyais`
`SIXBIT_ENCODING` szerint értendő (a `T` a 20-as érték), a
kitöltő az `@` (64) → **a `decode_text_field` külön függvény.**

**A nev és a hívójel (a `vessel_i18n.name`):** a Msg 5 **nem tartalmaz
nevet**! A nevet az **Inland FI 10 (DAC 200, FID 10)** üzenet hordozza
(`name`, `callsign`) — ez a belvízi statikus üzenet.

**A hívójel a Msg 5-ben van** — és az FI 10-ban is. **A `vessel_identifier`
a kanonikus** (a 02-es terv §8.2a szinkron).

### 4.4a A külső referencia: az AIS szabályok és a minőségi problémák

> **A MarineTraffic support-dokumentációja** (a `support.marinetraffic.com`
> „Data Quality & Methodology" és „Using MarineTraffic" gyűjteményei)
> **a nemzetközi gyakorlatot mutatja** — **a saját protokoll-specifikációnk
> (az IMO/UNECE/RI kódok) az irányadó**, ez a külső oldal a **gyakorlati
> háttér**. **A három releváns pont:**
>
> **1. Az üzenetek ütemezése — a Class A és a Class B eltér.**
>
> | A transzponder | A dinamikus (pozíció) üzenet | A statikus üzenet |
> |---|---|---|
> | **Class A** | **2–10 mp** (a sebességtől és az iránytól függően) | **6 perc** (mozgás nélkül is) |
> | **Class B** | **30 mp (minimum)** | a Class A-val azonos (6 perc) |
>
> **Ez a mérésben is látszik:** a statikus üzenetek közötti rés
> **a medián 361 mp (6,0 perc)**, **a 75. percentilis 590 mp (10 perc)** —
> **a 10 perces érték a Class B-k ritkább küldésével magyarázható**.
>
> **A Class B transzponder küldött adathalmaz is szűkebb:** **nincs
> IMO-szám, nincs merülés, nincs célállomás, nincs ETA, nincs
> kormányzási sebesség, nincs navigációs állapot.**
>
> **A tervezés következménye:** **a Class B hajóknál a `destination` és
> az `eta` sosem jön** → **a `06` §4.2 szerkesztői mezője ezeknél
> **üres** lesz, és **a kézi kitöltés a cél** → **a `05` §8.3 „Még nem
> tudjuk" jelölése** (a F-DET-16) **pontos ezt jelenti.**
>
> **2. A navigációs állapot (`nav_status`) 16 értéke** (0–15) —
> **a `02` DDL CHECK constraintje mind a 16-ot kezeli** (a szöveges
> névekkel). **A mérésben előforduló értékek:** `0` (under way using
> engine, 257 896 pozíció), `15` (undefined, 11 272), `8` (under way
> sailing, 7 774), `5` (moored, 6 245), `1` (at anchor, 13), `4`
> (constrained by draught, 3), `2` (not under command, 2), `10` (a
> tartalék kód, 2), `9` (a tartalék kód, 1), `6` (aground, 1).
>
> **3. A hamis pozíciók (spoofing) — a F-NF-17 fantom-szűrőnk
> kontextusa.** A MarineTraffic szerint:
> - a **GNSS-hamisítás** (a külső, katonai/gépolitikai actoroktól) a
>   hajó fedélzeti navigációját is megtéveszti;
> - az **AIS-hamisítás** (a hajó saját maga) hamis koordinátákat,
>   hamis azonosítókat és **duplikált üzeneteket** küld, hogy
>   „szellemhajókat" (ghost ships) szimuláljon.
> - **A felismerés:** a pozícióugrások, a természetellenes sebességek,
>   a **duplikált MMSI-k/névvel**, a hosszú ideig kikötő nélkül álló
>   hajók.
>
> **A mi fantom-szűrőnk (a `01` §5.5 és a `04` §4.7) a navigációs
> infrastruktúrát zárja ki** (a 106 lámpa + a 3 bázisállomás) → **a
> szándékos hamisítás ezen a Duna-szakaszon nem dokumentált** → **a
> F-NF-17 (0 fantom hajó) a mérésben teljesül** → **de a mérési
> protokoll (a `04` §8) rögzíthetné a pozícióugrás-ellenőrzést** mint
> **minőségi metrikát** (a MarineTraffic módszere).

### 4.5 A belvízi statikus üzenet (Inland FI 10)

> **⚠️ A 2026-11-24-i mérés tanulsága (a vevő nem dekódolja a
> belvízi FI 10-ot):**
>
> **A `bud01` vevő (AIS-catcher v0.71) a 21-es üzenetet az AtoN
> mezőkkel dekódolja** → **a mérési DB `ais_static` táblájában
> NINCS `vin` (ENI) oszlop**, és a 93 645 `type=21` üzenet
> `shipname`-je a **hívójel** (pl. a `1658.8_G`).
>
> **KÖVETKEZMÉNYEK:**
> 1. **a mérési ENI-arány (0,4%) nem a vevőből származik** → **a
>    belvízi FI 10 `vin` mezőjét (a 7 bites kódolás) a `duna`
>    parserének kell dekódolnia**, **saját** implementációval (a
>    `pyais` a DAC 200/FID 10-et nem ismeri);
> 2. **a 21-es üzenet dekódolása a `pyais` AtoN-szerű értelmezését
>    követi** (a hívójel a `name` mezőben) → **a `duna` ezt
>    implementálja** (`decode_aid_to_navigation`) → **a mérési
>    példán egyezik** (`1658.8_G`, a LAT/LON, az MMSI);
> 3. **a 7 bites `vin`-kódolás (a `04` §4.5) a következő
>    implementációs lépés** → **a mérési adat nem tudja validálni**
>    (a vevő nem tárolja) → **a nyitott kérdések egyike**.

**A formátum:** a 6 bites karakterkódolás **egy karakterrel eltér**:
a **számok** (`0`–`9`) és a betűk **a 6 bites index helyett 7 bites
kódolással** vannak a payload **végén** (a `?` ASCII = 63 = a
kitöltő karakter).

> **A `?` a kitöltő karakter** — a `0x3F`. Az Inland FI 10 a
> hosszanti mezők végén `?`-ekkel kitöltött.

**A mezők (a 6 bites karakterkódolás után, a 7 bites kódolás előtt):**

| Mező | Hossz | Jelentés |
|---|---|---|
| `vin` | 8×7 bit | **ENI** (a 2016/1629/EU szerinti európai hajóazonosító) — **a kitöltő érték `00000000`** (a kényelmes hajóknak nincs ENI-jük; a CESNI Inland AIS irányelv) → **a kitöltő érték `NULL`-ra cserélendő**, nem tárolandó |
| `length` | 13 bit | a hajó hossza (0,1 m) |
| `beam` | 10 bit | a hajó szélessége (0,1 m) |
| `shiptype` | 14 bit | a hajótípus kódja (UN/CEFACT ERI) |
| `draught` | 11 bit | a merülés (0,1 m) |
| `hazard` | 3 bit | a veszélyes áru jelölés |
| `category` | 3 bit | a kategória |
| `dist_to_starboard` | 13 bit | a parttól mért távolság jobbra (m) |
| `dist_to_port` | 13 bit | a parttól mért távolság balra (m) |
| `speed_qp` | 1 bit | a sebesség pontossága |
| `heading_qp` | 1 bit | a haladási irány pontossága |
| `callsign` | 7×8 bit | a hívójel (7 karakter) |
| `name` | 20×6 bit | a hajó neve (20 karakter) |
| `draught_qp` | 1 bit | a merülés pontossága |
| `eta` | 4×5 bit | az ETA (óra:perc) — a `vessel` statikus adata (a `position`-ben nincs ilyen oszlopa) |
| `draught_reference` | 2 bit | a merülés referencia (0 = nincs, 1 = **RNW**) |

**A `river_km` (a fairway hectometre) — a pozícióból jön, nem a
statikus üzenetből!** Az AIS **pozíció** üzenet (Msg 1/3) tartalmazza
a `distance_to_shore` és a `fairway_distance` mezőket a **szokásos
pozícióüzenet** 60–87. bitjén (a `lon`/`lat` után).

> **Ez a `position.river_km` forrása** — a 02-es terv szerint
> „*a `river_km` **közvetlenül az AIS fairway hectometre mezőből** jön
> (Inland FI 10)*". **Pontosítás:** a FI 10 a **statikus** üzenet, a
> `river_km` a **pozíció** üzenetben van (a szokásos pozíció
> kiterjesztése, a 60–87. bit). A terv megfogalmazása pontosítandó.

**A feldolgozatlan FI 10 mezők** (a `prof` M-3/M-4/M-5 findingjei) —
**a v1-ben feldolgozatlanok**, de **dokumentáltan**:

| A mező | A sorsa |
|---|---|
| `hazard` (3 bit, a veszélyes áru) | **eldobva** — a `vessel`-ben nincs ilyen oszlop; a `cargo_type`-ra utalhatna, de a mérésben **egyetlen hajó sincs veszélyes árujelöléssel** |
| `category` (3 bit) | **eldobva** — ugyanaz, mint a `hazard` |
| `dist_to_starboard` / `dist_to_port` (13 bit, a parttól mért távolság) | **eldobva** — a `position` sémában nincs ilyen oszlop; a korridor-ellenőrzés a `river_km`-ből / a geo-illesztésből jön |
| a **GNSS antenna helye** (a Msg 18 **két helyen**: a 110–141. és a 256–263. bit) | **eldobva** — a 02-es sémában nincs antennas hely oszlop → **a Q3 nyitva marad a 02-ben** |

**A `draught` (11 bit, 0,1 m) és a `draught_max_m`** (a `prof` M-5/M-6
findingjei):
- a FI 10 `draught` a **jelenlegi merülés** → a `vessel.draught_max_m`
  (a **legnagyobb** merülés — a hajó a legnagyobb merülésével a
  legmélyebb vízben jár);
- a **`draught = 0` → `NULL`** (a „nincs megadva") — a mérésben a
  `GONDOLA` 0,0;
- **a `position.draught_m`** (a pillanatnyi merülés) **mindig NULL**
  marad R1-ben (a parser nem tölti) → a terv ezt kimondja;
- **ellenőrző szabály:** a `draught > 6 m` **figyelmeztetés** (a Duna
  hajóinál a merülés ritkán > 4 m) → **ez a dekódolási hibák szűrője**
  (a mérésben a `CITADELLA` 7,0 m — ez gyanús).

**A `draught_reference = 1` → `'RNW'`** — a 02-es terv
`CHECK (draught_reference IN ('RNW','lake_operator','unknown'))`
értékei. A **Balatoni** hajóknál nincs RNW → `NULL` (a `position`-ben
a `draught_reference` nem szerepel, a `vessel`-ben igen).

**A `river_km` három forrása — a mérési adat alapján** (a `prof` C-5
findingje):

| A forrás | Honnan | A magyar szakaszon |
|---|---|---|
| **a pozíció `fairway_distance` mezője** | a Msg 1/3 60–87. bitje | **gyakorlatilag üres** — a bud01 vevő 37 494 üzenetében **egyetlen** pozícióüzenetben sem volt kitöltve |
| **a navigációs lámpák neveiből** | a `992438xxx` MMSI-k neve (`1592.4_R_FL` = 1592,4 km) | **ez működik** — a lámpák a folyó középvonalán vannak |
| **geometriai illesztés** a folyó középvonalára | a pozíció `lat`/`lon`-ja + a lámpák pozíciói | **ez is működik** — a mérési dokumentum így számolja a 69,8%-os lefedettséget |

> **A döntés:** a `river_km` **elsődleges forrása a geometriai
> illesztés** (a lámpák pozíciói + a pozíció `lat`/`lon`-ja) — ez a
> magyar szakaszon **mindig** elérhető, és a mérési adat szerint
> **a 69,8%-os lefedettséget** ebből számítjuk. A `fairway_distance`
> mező **másodlagos** (a nemzetközi hajóknál jelen van, ott pontosabb).
> A **Q1 státusza: „félig lezárva"** → a három forrás dokumentálva.

**A `fairway_code` kikerült** a normalizált rekordból (a `prof` M-1
findingje) — a `river_section.fairway_code` a **szakaszhoz** tartozik,
nem a pozícióhoz → **a Q2 lezárva**.

### 4.6 A Class B üzenetek (Msg 18, 24)

**A Msg 18** (a Class B pozíció) a 168 bites fejléc után **38 bites
Class B pozíciófejlécet** tartalmaz:

| Bit | Hossz | Mező |
|---|---|---|
| 0–7 | 8 | a fedélzeti berendezés fajtája |
| 8–37 | 30 | **MMSI** |
| 38–39 | 2 | navigációs állapot |
| 40–69 | 30 | nemzetközi szám |
| 70–105 | 36 | a Class B pozíció (a 8 bites pozíció + a navigációs adatok) |
| 106 | 1 | a pozíció pontossága |
| 107–109 | 3 | a SOG/COG pontossága |
| 110–141 | 32 | **a GNSS antenna helye** (a hajó orrától, méterben) |
| 142–143 | 2 | a hajótípus (a Class B kód) |
| 144–149 | 6 | a hajótípus altípusa |
| 150–151 | 2 | a hajótípus altípusának javítója |
| 152–157 | 6 | a hajótípus kódja |
| 158–167 | 10 | a **bevég/zárt hossz** |
| 168–187 | 20 | a **szélesség** (m) |
| 188–193 | 6 | a port oldali fedélzeti állapot |
| 194–199 | 6 | a jobb oldali fedélzeti állapot |
| 200–203 | 4 | a pozíciójelző eszköz típusa |
| 204–207 | 4 | a rádióállapot |
| 208–235 | 28 | a gyorsítóműszak-hiba (SOG) |
| 236–237 | 2 | a gyorsítóműszak-jelző |
| 238–245 | 8 | a navigációs állapot |
| 246–248 | 3 | a fedélzeti munkaállapot |
| 249–253 | 5 | a hajó belső berendezéseinek állapota |
| 254–255 | 2 | a hajó irányítása |
| 256–263 | 8 | a **GNSS antenna helye** (ismét) |

**A Msg 24** (a Class B statikus) a hajótípust, a hívójelet, a nevet,
a hosszt és a szélességet tartalmazza.

**A Balaton miatt fontos:** a Msg 18 és 24 a **Class B** (a kishajók)
üzenetei — **a Balatoni katalógus** ezekből épül (a README 2.10
szerint a kishajók és vitorlások nincsenek a katalógusban, de a
személyhajók és a kompok igen).

**A méretadatok kiemelése** (a `bori` B-H-6 findingje): a hossz, a
szélesség és a merülés a **legjobban kitöltött** statikus adatok (a
mérésben **66 a 78 neves hajóból**, 85%!) → a felhasználó számára a
**legfontosabb** statikus adatok (a komp mérete → befér-e a kikötőbe?).
A `length`/`beam` **0,1 m-es** pontossága a tároláshoz jó, a UI-on a
kerekített érték (39×7 m) a hasznos.

**A mentő- és kiszolgáló hajók** (a `bori` B-H-4/B-M-3 findingje): a
`vessel_type` referencia (a `02` v1.4 seed) a **8450** (kisegítő hajó,
kikötői szolgálat) és az **51** (tengeri mentő) típusokat is tartalmazza
→ **a UI megkülönbözteti** őket (a mérésben 3 + 2 hajó — a
`SZENT FLORIAN`, a `KITUZO III.`/`V.`, a `CSEPEL`, a `BALATONAKARATTYA`).

**A hivatalos név vs. a fordított név** (a `bori` B-H-3 findingje): a
`vessel_i18n.name` a **hivatalos latin név** (a mérésben 175 hajóból
van) → a **lefordított** név a `content_key`-ből jön
(`vessel.name.<mmsi>`) → **a szerkesztői felület fordítja**. A parser
**csak** a hivatalos nevet írja.

---

### 4.7 A nem hajó üzenettípusok (a bud01 mérés alapján)

> **A `prof` reviewer C-1 findingje után.** A terv a mérés előtti
> architektúrát írta le: a mérésben a **37 494** üzenet **27,3%-a**
> (a 21-es 18,7%, a 4-es 5,5%, a 20-as 1,5%, a 23-as 1,4%, a 15-ös 0,2%)
> **nem hajó üzenet** — és a terv **egyetlen szóval sem** említette őket.

| `type` | Jelentés | A mérésben | A kezelés |
|---|---|---|---|
| **21** | **belső forgalmi adat (Class B, DAC 200/FID 21)** | **7 016 (18,7%)** | **a `position`-be kerül** — a Class B pozíciók (`lat`/`lon`/`sog`) a **Balatoni katalógushoz** szükségesek (a README 2.10: a kishajók nincsenek a katalógusban, de a **személyhajók és a kompok igen**) |
| **4** | bázisállomás | 2 070 (5,5%) | **a NAVTEX/MSK-forrás** — a `data_quality_event`-be? **nem**: a §4.7.1 szerint |
| **20** | belső forgalmi adat (MSK) | 559 (1,5%) | a bázisállomásoktól jön → **a NAVTEX-adat** |
| **23** | belső forgalmi adat (MSK, új) | 519 (1,4%) | a bázisállomásoktól jön → **a NAVTEX-adat** |
| **15** | egyéb (interrogálás) | 60 (0,2%) | **eldobandó**, de **a számlálóba** kerül (a mérési protokoll metrikája) |

#### 4.7.1 A Msg 4 / 20 / 23: a NAVTEX-forrás (a korábbi „eldobandó" **hamis** volt)

**A terv korábbi Q5-je** a Msg 4-et „eldobandónak" jelölte („*a belső
AIS-átvitelben nem relevánsak*"). **Ez a méréssel ellentmond.**

**A mérés tényе:** a `2430003`, `2430006` és `2430007` MMSI-k
**kizárólag** a 4-es, 20-as és 23-as üzenettípust küldik — **pozíció-
(1/2/3) és statikus (5) üzenet nélkül**. Ezek **nem hajók**: a **Duna
navigációs infrastruktúrájának állomásai**, és a **NAVTEX/MSK
forgalmat** adják tovább.

**A döntés (a prof C-1 és a bori B-C-4 alapján):**
- a **Msg 4/20/23** → **a `data_quality_event`-be** kerülnek
  (`severity='info'`, `detail='basestation: NAVTEX/MSK relay'`) — **a
  `position`/`vessel` táblába NEM**;
- **a bázisállomások nem hajók** → a fantom-szűrő (a 01-es terv §5.5)
  kizárja őket (a `2430003/6/7` MMSI-tartomány + a **név-találgatás
  nélküli**, pozíció nélküli jelleg);
- **a 767 FI 10 üzenet (a 8-as típus) a hajóktól jön** → a §4.5 szerint
  kezelendő (az ENI-adatok útja) — **nem** a bázisállomásoktól.

> **A `bori` reviewer B-C-4 findingje:** a felhasználó **nem látja** a
> bázisállomásokat és a **106 navigációs lámpát** (`992438xxx`) a
> katalógusban — a lámpáknak **van nevük** (`1592.4_R_FL` = 1592,4 km,
> piros villogó lámpa), tehát **számokra hasonlítanak**, és a katalógus
> „hajóként" mutatná őket. A fantom-szűrő **MMSI-tartomány + név-minta**
> alapján zárja ki őket (`^\d+\.\d+_[GRW]`).

#### 4.7.2 A Msg 21 (a Class B) — a `position`-be megy

**A Class B pozícióüzenet** (`lat`/`lon`/`sog`/`cog` a 38–105. biten)
**a szokásos `position` upsert** flow-ba kerül, **a `vessel` upsert** pedig
a statikus adatokból (a Msg 24) — **a Class B hajók ugyanúgy a
katalógusba kerülnek**, mint a Class A-k.

**A Class B-re nincs külön dekódoló** — a pozíció-resz (a 70–105. bit)
**a szokásos 8 bites pozíció formátumú**, a navigációs adatok
(a 38–69. bit) kiegészítik a `nav_status`-t és a `heading`-et.

---

## 5. A normalizált rekord (a közös szerződés)

A `02` és a `04` közötti **egyetlen definíció** — a `04` ezt Pydantic
modellként rögzíti, a `02` ebből generálja az oszlopokat.

> **⚠️ A 2026-11-24-i mérés TANULSÁGA (a `bud01` vevő normalizálása):**
>
> **A vevő `ais_message.mmsi` oszlopa NEM a `nmea` payloadból
> számítható.** A mérés 300 pozíció- és 50 statikus üzeneten vizsgálta
> → **egyetlen bit-pozíció és bit-orientáció sem adja vissza a
> tárolt `mmsi`-t.**
>
> **A bizonyíték:**
> - a `type` oszlop **8000/8000** egyezik → a payload sértetlen és a
>   kódolásunk helyes;
> - a tárolt `mmsi` **egyetlen** variánsban sem egyezik;
> - a **MID egyezik** (a 243-as hajóknál a fizikai és a tárolt MMSI
>   is 243-as), **csak a 6 számjegyű suffix tér el** → **a vevő a
>   hajót azonosítja, nem a nyers MMSI-t adja tovább.**
>
> **A Class B (a `type=21`, FI 10) esetén** a mérésben **992-es
> synthetic MMSI**-k vannak (a 992 436 091, a 992 438 237, …) →
> **a Class B-nek nincs MMSI-je a payloadban** → **a vevő generál
> egyet** → **ez a `04` §5 szerinti normalizálás egyik esete.**
>
> **KÖVETKEZMÉNYEK:**
> 1. **a `duna` saját parserének a STANDARD AIS-t kell dekódolnia**
>    (a `pyais` a hivatalos referencia — a `04` §11 Q6);
> 2. **a mérési `mmsi` oszlop a NORMALIZÁLT azonosító** → **a
>    mérési adatot nem szabad nyers payloadként kezelni**;
> 3. **a normalizálás szabálya nyitott kérdés** (a `04` §11 Q8) → **a
>    hajót a MID + a fizikai MMSI suffix alapján kell azonosítani.**
>
> **Az implementáció:** a `decode_standard_6bit` (a GPSD armor) és
> a `decode_physical_6bit` (**ugyanaz a kódolás**, a mérési adat
> kényelmes olvasására) az `apps/api/src/duna/ingest/decoder.py`-ban.

```python
# apps/ingest/pydantic_models.py
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class NormalizedAisMessage(BaseModel):
    """A parser kimenete — a 02-es terv sémaoszlopaival egyezik."""

    # a forras
    source_code: str = Field(description="a data_source.code")
    received_at: datetime = Field(description="a fogadas idopontja (UTC)")
    msg_hash: bytes = Field(description="a dedup-kulcs (sha256)")

    # a hajo
    mmsi: int
    eni: Optional[str] = Field(default=None, description="a FI 10 vin-je")
    imo: Optional[str] = None
    callsign: Optional[str] = None
    name: Optional[str] = Field(default=None, description="a FI 10 neve")

    # a pozicio
    ts: Optional[datetime] = Field(default=None, description="a hajo GNSS-idobelyege")
    lat_e7: Optional[int] = None
    lon_e7: Optional[int] = None
    sog_mps: Optional[float] = None
    cog_deg: Optional[float] = None
    heading_deg: Optional[float] = None
    rot_deg: Optional[float] = None
    # **A `nav_status` a 02-es sémában `text`** (a prof C-2 findingje:
    # a korábbi `int` nem illeszkedett) → itt is `Optional[str]`, a
    # 02-es CHECK ertekkeszletevel.
    nav_status: Optional[str] = None
    ais_accuracy_m: Optional[float] = None
    river_km: Optional[float] = Field(default=None, description="a fairway hectometre")
    # **A `fairway_code` kikerult** (a prof M-1 findingje): a
    # `river_section.fairway_code` a SZAKASZHOZ tartozik, nem a
    # poziciohoz → a `position` tablanak nincs ilyen oszlopa.
    # A Q2 ezzel lezarva.

    # a statikus meretek
    vessel_type_code: Optional[str] = None
    length_m: Optional[float] = None
    beam_m: Optional[float] = None
    draught_max_m: Optional[float] = None
    draught_reference: Optional[Literal["RNW"]] = Field(
        default=None, description="a merules referenciaja (a FI 10 flag-je)")

    # a diszpoziciok
    msg_type: int = Field(description="az AIS type mezője (1-27)")
    # **A `msg_subtype` a DAC/FID** (a prof C-3 findingje) — a 02-es
    # `position.msg_subtype smallint` oszlopra megy (a `02` v1.5).
    # A FI 10 a 6-os/8-as `msg_type` (a DAC 200, FID 10), a Class B a
    # 21-es (a DAC 200, FID 21) → a `msg_type` ONMAGABAN nem eleg.
    msg_subtype: Optional[int] = None
    # **A `repeat` a normalizalt rekordban marad** (a dedup/ismetlodes
    # logikaja hasznalja) — **a `position` tablaba NEM kerul** (a 02-es
    # `position` nincs ilyen oszlopa) → a prof C-3 findingje.
    repeat: Optional[int] = None

    # **Az `is_static` NEM oszlop** (a 02-es semaban nincs) — a
    # statikus jelleg SZAMITOTT: `msg_type IN (5, 24)` vagy a FI 10
    # (a 6-os/8-as `msg_type` + a DAC 200) → a prof C-3 findingje.
    @property
    def is_static(self) -> bool:
        return self.msg_type in (5, 24) or (
            self.msg_type in (6, 8) and self.msg_subtype == 10)
```

**A `vessel_type_code` KÖTELEZŐ** (a `K-3` finding — a 02-es
`vessel.vessel_type_code text NOT NULL REFERENCES vessel_type(code)`):

```python
    # **KÖTELEZŐ** — a 02-es `vessel.vessel_type_code` NOT NULL + FK.
    # A Msg 1/2/3 (a pozicio) NEM tartalmaz `shiptype`-ot → a tipus
    # a `vessel` upsertkor a **statikus** uzenetbol (a Msg 5/24 vagy a
    # FI 10) jon, a poziciouzenetbol nem.
    # A fallback: az `UNKNOWN` tipus (a 02-es v1.4 seedje) — a
    # `shiptype = 0` es a `shiptype` hianya esetén is.
    vessel_type_code: str = Field(
        description="a vessel_type.code (a 89 tipus egyike; a "
                    "'UNKNOWN' a fallback)")
```

**A `shiptype` → `vessel_type.code` lookup** (a `prof` H-2 findingje):
az `ais_type_code` (a 8000–8519-es belvízi ERI, az 1–99-es SOLAS)
→ a `vessel_type.ais_type_code` → a `vessel_type.code`
(a `02` v1.6 seedje: **89 típus, a magyar nevekkel**). A **hiányzó**
kód → az `UNKNOWN` (`ais_type_code = NULL`).

> **A mérési tapasztalat (a `docs/measurement_2026-11-22.md`, a 37 órás
> adat):** a `shiptype` mező **NEM csak ERI-kódot** tartalmaz:
>
> | A `shiptype` | A hajó | A jelentése |
> |---|---|---|
> | `37` | THETIS | **SOLAS hajóosztály** (személyhajó/komp) |
> | `35` | AM31 DUNAUJVAROS | SOLAS (katonai hajó) |
> | `33` | LUPPA | SOLAS (sócsaró) |
> | `79` | TEKOV | SOLAS (teherhajó) |
> | `89` | AQUA TEAM | SOLAS (tanker) |
> | `99` | MARGITSZIGET | SOLAS (egyéb hajó) |
> | `156` | PRIMUV | **regionális kód** (az IMO 100–199 tartomány) — a belvízi uszály |
>
> **Két kódterv egy mezőben:**
> - a **SOLAS-osztályok** (1–99) → a `02` v1.6 seed `SOLAS_xx` soraival
>   egyeztethetők (`ais_type_code` = a saját számuk);
> - a **regionális kódok** (100–199) → **nincs seedbeli ellenőrlés** →
>   **az `UNKNOWN`** (a `02` v1.6 `ais_type_code = NULL`).
>
> **A `shiptype` sosem 14 bites ERI-kód itt** — a `04` §4.5 a FI 10
> mezőjéről beszél, **de a SOLAS-osztály (Msg 5/24) mezője 8 bites** →
> **a lookup mindkettőt kezelje**.

**A `02` v1.6 seed javítása (a mérés alapján):** a SOLAS-osztályok
(`SOLAS_30`…`SOLAS_90`) korábban `ais_type_code = NULL`-lel voltak
seedelve → **a lookup nem találta meg őket** → **most a saját
kódjukat kapják** (`SOLAS_37` → `ais_type_code = 37`) → **a 21 SOLAS
típus a mérési adatokból elérhető**.

**A `source_kind`:** a `position.source_kind` a 02-es terv szerint
`'ais' | 'derived' | 'manual'` — a parser mindig `'ais'`-t ír; a
`'derived'` a **bárka** pozíciója (a konvoj vezetőjéből származtatva —
az a 01-es terv §5.5 3. pontja).

**A mezőnkénti eredet** (a `prof` H-3 findingje, a F-DET-15): a
statikus AIS-adatok (a **név**, a **méret**, a **hívójel**, az **ENI**)
a `vessel_data_origin`-ba mennek, `origin='ais'`-szal, a
`value_snapshot` az eredeti értékkel. **A `confidence` a parser
művelete** (a mérésben a statikus adatok `confidence=1.0` →
a `vessel_data_origin_conflicts` nézet konfliktust jelez, ha egy másik
forrás más értéket ad).

**A `vessel_data_origin` a `vessel_data_origin_current` nézetből
olvasható** (a 02-es terv §6.3a) → **a felhasználó a badge-et a
service-től kapja** (a `bori` B-M-1 findingje: **a parser nem számít
badge-et**).

---

## 6. A dedup

### 6.1 A kulcs

A 02-es terv szerint a `msg_hash` a `raw_nmea` + `received_at` +
`source_id` elemekből jön — **a Python `hashlib.sha256`-a számolja**
(a DB-beli generálás nem lehetséges: a `timestamptz::text` nem
immutable — a V-N-5 finding).

**A törzsadatok a migráció seedjéből jönnek** (a `preshaz` P-M-4
findingje): a `vessel_type` (a 89 hajótípus, a magyar nevekkel), a
`language`, a `country`, a `waterway`, a `river_section`, a `basin`, a
`cargo_type` és az `operator` — **a `02` v1.4 DDL-jének végén** (a
`00014_seed_reference.sql`). → **a lookup erre a seedre támaszkodik**;
a **hiányzó** `ais_type_code` (nem seedelt kód) → az `UNKNOWN` típus
(`ais_type_code = NULL`).

**A `shiptype` → `vessel_type.code` lookup** (a `prof` H-2 findingje):
az `ais_type_code` (a **8000–8519-es belvízi ERI** sorozat, illetve az
**1–99-es SOLAS** kódok) → a `vessel_type.ais_type_code` →
a `vessel_type.code`. A mérésben előforduló kódok: **8444** (15 hajó),
**8443** (14), **8440** (11), **8000** (8), **60** (8), **69** (7),
**80** (3), **8450** (3), **51** (2), **0** (1), **90** (1), **8430** (1),
**8460** (1), **8220** (1) → **mind a 89 típus seedben van**.

```python
import hashlib

def compute_msg_hash(raw_nmea: list[str], received_at: datetime,
                     source_code: str) -> bytes:
    """A nyers uzenet dedup-kulcsa.

    A `raw_nmea` **LISTA** — a v0.71-es AIS-catcher a `nmea` mezot
    tombkent adja (a JSON-ben: `"nmea":["!AIVDM,1,1,,A,..."]`), a
    3 soros uzenetet pedig **3 elembol allo** (a `prof` H-1 findingje:
    a `str` tipus a `hashlib`-en elhasalna).

    A hash elemei a 02-es §6.1 szerint: `raw_nmea` + `received_at`
    (epoch) + `source_id` — a **sorokat sorrendben, `\n`-nel
    osszefuzve** (igy a 3 soros uzenet egyetlen hash-t ad).

    A `received_at` epoch-milliSzekundumban megy (a timezone
    függetlenség miatt) — a `datetime.timestamp()` a local time
    felhasznalja, ezert a `timestamp()` helyett a `tz-aware`
    konverzio kell.

    **A visszafuttathatosag kulcsa:** a `received_at` a **vevo ideje**
    (a `ais_message.received_at` oszlopból olvasva) → a backfill
    **ugyanazt a hash-t** allitja elo, mint a valos idejü
    feldolgozas → **a backfill idempotens** (a `preshaz` P-H-1
    findingje).
    """
    epoch_ms = int(received_at.timestamp() * 1000)
    payload = "\n".join(raw_nmea) + f"|{epoch_ms}|{source_code}"
    return hashlib.sha256(payload.encode("utf-8")).digest()
```

**A `received_at` a fogadás ideje** (a szerver ideje, UTC) — **nem** a
hajó GNSS-időbélyege. Ez fontos: a dedup a **hálózati** duplikációt
szűri (a vevő újraküldi, az MQTT retry), nem a fizikait.

### 6.2 A duplikáció forrásai

| Forrás | Leírás | Kezelés |
|---|---|---|
| **Az MQTT retry** | a broker újraküldi az üzenetet | a `msg_hash` eldobja |
| **A vevő buffer** | a helyi buffer újra küldi a blokkot | a `msg_hash` eldobja |
| **Két vevő, ugyanaz a hajó** | a Duna egy szakaszon belül 2 vevőt is lát | **NEM** eldobandó — a `position` upsert a `(vessel_id, ts)`-en, a későbbi írás győz |
| **A fizikai „ismétlődés"** | ugyanaz a pozíció kétszer | a `position` upsert eldobja (a `ts` azonos) |

**A `repeat` flag** (a `prof` H-5 findingje): a `repeat=1` azt jelenti,
hogy a vevő **már küldött egy ilyen üzenetet** → a parser **előnyben
részesíti a `repeat=0`-t** a dedupnál, és a `position` upsert a
`(vessel_id, ts)`-en **a `repeat=0` írás győz**. A `repeat` a
normalizált rekordban marad, **a `position` táblába nem kerül** (a 02-es
sémában nincs ilyen oszlopa).

**A dedup korlátja** (a `prof` L-1 findingje): a `msg_hash` a
`received_at` **millisecondszresolutionját** használja → **a hálózati
retry** (a vevő újraküldi az üzenetet **más** időbélyeggel) **NEM
szűrődik**. A második védvonal: a `position` upsert a `(vessel_id, ts)`-en
**az eleve eldobja** a fizikai ismétlődést.

---

## 7. A hibakezelés

| Hiba | Hatás | Jelzés |
|---|---|---|
| A checksum nem egyezik | az üzenet **eldobandó** | `data_quality_event` (`severity='warning'`, `detail='parser_error: checksum mismatch'`) |
| A számozott sorok nem folytonosak | az üzenet **eldobandó** | `data_quality_event` |
| A payload > 82 karakter (több sor nélkül) | az üzenet **eldobandó** | `data_quality_event` |
| Ismeretlen karakter a payloadban | az üzenet **eldobandó** | `data_quality_event` |
| Ismeretlen üzenettípus | az üzenet **eldobandó** (a debug logban) | `data_quality_event` (`severity='info'`) |
| A `position` upsert ütközik | az **upsert** győz (a legfrissebb) | — |
| A `vessel` upsert ütközik (az ENI már létezik) | a `vessel_identifier` szinkron kezeli | — |

**A `data_quality_event` írása** az `ingest` folyamatban történik — a
02-es terv szerint a `job_run_id`-vel köthető (a P1-26 finding).

**A `job_run` élettörtje** (a `prof` H-9 és a `preshaz` P-M-2 findingje):
a parser indulásakor egy `job_run` sor (`job_name='ingest'`,
`status='running'`, `started_at=now()`) → a végén `status='success'`
(illetve `'partial'`/`'failed'`), a `rows_in`/`rows_out` kitöltve, az
`ended_at=now()`-val. **A valós idejű feldolgozás és a backfill külön
`job_run`** (`job_name='ingest-realtime'` / `'ingest-backfill'`) → a
backfill **újrafuttatható**, és a `partial` státusz jelzi, hogy a
hónap nem teljes (a `preshaz` P-H-8 findingje: a hónap közepén
megszakadt backfill **a `ts` alapján** ír → a következő futás
kitölti; a félig üres partíció a **90 napos TTL** miatt megy el).

**A `detail` a technikai szöveg** (a parser logja); a **felhasználó** a
`03` – API-terv szerint a `content_key`-ből kapja a lokalizált
hibaüzenetet → **a parser nem lokalizál** (a `preshaz` P-M-3 findingje).

**A hibák aránya a mérés során** (a `ais-vevo-terv.md` 5. fejezete):
a go/no-go feltétel. A hibás üzenetek aránya **< 0,1%** kell legyen.

**A két hibafajta szétválasztása** (a `prof` H-4 és a `preshaz` P-C-2
findingje) — **ez a go/no-go kritérium értelmezhetősége**:

| A hibafajta | Hol mérhető | A határ |
|---|---|---|
| **a vevő oldali hibák** (a hibás checksum, a hibás NMEA) | **sehol** — a vevő eldobja, **a DB-be nem jut** | **nem mérhető** |
| **a parser oldali hibák** (a saját dekódolás hibája) | a `data_quality_event` / az összes feldolgozott üzenet | **< 0,1%** |

**A helyettesítő metrika** (a vevő érzékenysége): a **`msg/hajó` arány**
(a mérés: 37 494 üzenet / 199 hajó = **188 üzenet hajónként**).

**A futás szintjén** (a `preshaz` P-H-2 findingje): ha a DB megszakad
a backfill közben, a lemez betelik vagy a hálózat kiesik → a `job_run`
`status='failed'`/`'partial'` + az `error_text` → **a backfill
újrafuttatható** (a dedup miatt idempotens — a `preshaz` P-H-1
findingje: a `received_at` a **vevő ideje**, a `ais_message.received_at`
oszlopból olvasva → a backfill **ugyanazt a hash-t** állítja elő).

---

## 8. A mérési protokoll (a go/no-go)

> **A `preshaz` reviewer P-C-1/C-2/C-3 findingjei után — a terv a
> MÉRÉS ELŐTTI architektúrát írta le.** A bud01 vevő 2026-11-22
> 19:19-től fut, és a mérés első órájának adata (a
> `docs/measurement_2026-11-22.md`) **mindenben eltér** a tervtől.
> **Ez a fejezet a valós folyamatot írja le.**

### 8.0 A tényleges architektúra (a 8.1-es mérés előtt)

```
Pi (bud01, Raspberry Pi 4)
  └─ AIS-catcher v0.71  →  SQLite (/var/lib/ais/ais.db, RETENTION 35 nap)
       (a service: ais-receiver.service, boot után auto-indul)
  └─ heti lehúzás (cron, hétfő 04:17)
       └─ scp a NAS-ra → /opt/data/martin/work/ais-data/ais-YYYYMMDD-HHMM.db
NAS (Artemis)
  └─ a nyers *.db fájlok (a bind mounton)
Központi (a VPS)
  └─ a parser (a saját dekóder)  →  Postgres
       (a position havonta partícionált, 90 napos TTL)
```

**A Parquet + gzip archívum NEM létezik** (a régi terv ezt írta) —
a nyers adat **SQLite**, és a heti lehúzás **az SQLite fájlt** másolja.
A parser a **központi** oldalon fut, **a SQLite `ais_message.nmea`
oszlopából** olvas (a `nmea` **tömb** — a `prof` H-1 findingje).

### 8.1 A mérés célpontjai (a mérhető metrikákkal)

| # | Célpont | A mérhető metrika | A határ |
|---|---|---|---|
| 1 | **Az üzenetek száma** | a mért érték vs. a README 5.1 becslése | — |
| 2 | **Az üzenettípusok megoszlása** | a 12 típus aránya (a **nem hajó** üzenettípusok is) | — |
| 3 | **A hibás üzenetek aránya** | **a PARSER hibái** (`data_quality_event` / az összes feldolgozott üzenet) — **a vevő hibái nem mérhetők** (a v0.71 csak a sikeres dekódolásokat tárolja) | **< 0,1%** |
| 3b | **A vevő érzékenysége** (a helyettesítő metrika) | a **`msg/hajó` arány** (a mérés: 37 494 / 199 = **188 üzenet hajónként**) | — |
| 4 | **A dekódolható statikus adatok aránya** | a **névvel** rendelkező hajók aránya (a mérés: **78 a 199-ből = 39,2%**) **és külön** az ENI-arány (**1 a 199-ből = 0,5%**) | — |
| 5 | **A pozíciók minősége** | a pozíciók hány százaléka van a **folyó-korridoron** (a **földrajzi** becsléssel — a `fairway_distance` a magyar szakaszon üres, a C-5 finding) | — |
| 6 | **A ghost hajók aránya** | a négy szűrőszabály után hány marad | — |
| 7 | **A felhasználói lefedettség** (új, a `bori` B-M-2 findingje) | hány hajót találunk meg a **nevével/hívójelével** | — |
| 8 | **A frissesség** (új, a `bori` B-M-2 findingje) | a katalógus hány százaléka friss (a pozíció az utolsó 24 órában) | — |

> **A go/no-go ENI-kritérium** (az `ais-vevo-terv.md` 5.2: „*az
> **ENI-arány ≥ 50%*") **a jelenlegi, városi helyen nem értelmezhető**:
> a mérésben **0,5%**. A budapesti városi szakasz **nem a szűkvízi
> forgalmat** méri → **a szűkvízi szakaszokon kell mérni** (a
> `K-4` finding — a F-CAT-08 szerinti 3 site pontosan ezt a hármat
> jelenti).

### 8.2 A mérés kimenete és a feldolgozási lánc

A nyers adat a Pi-n SQLite-ban van (35 nap retention) → hetente a NAS-ra
kerül → a központi feldolgozás a `*.db` fájlokat olvassa.

**A feldolgozás három lépése (a `preshaz` P-C-5 findingje):**
1. a **vevő** fut folyamatosan a Pi-n (a v0.71) → SQLite;
2. a **heti lehúzás** (a cron, hétfő 04:17) → a NAS-ra;
3. a **feldolgozás** (a parser) → a központi Postgres-be.

**A backfill becslése (a mérési adatból):** a 30 napos adat **~27
millió üzenet** (a mérés: ~900 000/nap) → Pythonban, ~1 ms/üzenet →
**~7,5 óra egyprocesszben** → **egy éjszaka**. Az `asyncio` + a
`psycopg` pool párhuzamosítható.

**A fixture-ök:** a mérési időszakból **típus szerint stratifikált**
üzenetek — **minden a mérésben előforduló üzenettípusból legalább
egy** (a 12-ből), és a **21-es típusból legalább 5** (a 18,7%-os
gyakorisága miatt) → a `db/fixtures/ais/` mappába kerülnek, és a
parser **elfogadási tesztje** ez (a 01-es terv §5.7). **Nem kell a 30
napra várni**: a mérés első 48 órájából már készíthető (a `preshaz`
P-H-5 findingje).

**A `pyais` a teszt-referencia** (a `preshaz` P-H-7 findingje, a Q6
lezárása): a fixture-ök dekódolását a `pyais`-szal **ellenőrizzük**
(a MIT licenc → a tesztben használható) → **a számszerű mezők
egyezése** a mérőszám. A `pyais` **nem** fut a termelésben.

**A részleges partíció** (a `preshaz` P-H-8 findingje): a backfill a
`ts` alapján ír → **a hónap közepén megszakadt futás a következő
futással kitölti** (a dedup miatt) → **a félig üres partíció a 90 napos
TTL miatt megy el**; a `job_run.status='partial'` jelzi, hogy a hónap
nem teljes.

### 8.3 A parser elfogadási tesztje

| # | Teszt | Elvárt |
|---|---|---|
| 1 | A `!AIVDM,1,1,,A,...` egysoros üzenet dekódolása | a `mmsi` és a `lat_e7`/`lon_e7` helyes |
| 2 | A 3 soros üzenet összefűzése | ugyanaz az eredmény, mint az 1. tesztnél |
| 3 | A hibás checksum | eldobva + `data_quality_event` |
| 4 | A `fill_bits` levágása | a kitöltő bitek nincsenek a kimenetben |
| 5 | A FI 10 `vin` → `eni` | a 8 karakteres ENI helyes |
| 6 | A FI 10 `name` (20 karakter) | a név a `?` kitöltők nélkül |
| 7 | A Msg 5 `callsign` | a `@` kitöltő levágva, a szóköz-trimmelés után |
| 8 | A Msg 18 `length`/`beam` | a méretek helyesek |
| 9 | A negatív szélesség (`lon_e7 < 0`) | a előjel helyes |
| 10 | Az `mmsi = 0` | eldobva (a hibás üzenet) |
| 11 | A **21-es típus** (a Class B pozíció) | a `position`-be megy (a Class B hajók a katalógusban vannak — §4.7.2) |
| 12 | A **20-as/23-as** (a MSK/NAVTEX) | a `data_quality_event`-be (`severity='info'`), **nem** a `position`-be (§4.7.1) |

**A hibás checksum a fixture-ben kézzel kell** (a `prof` M-9 findingje):
a **vevő** eldobja a hibás checksumú üzenetet → **soha nem jut el a
parserhez** → a teszt a parser **saját** hibakezelését méri, nem a
vevőét.

**A fixture-ök a mérés után jönnek** — a tesztek addig **szintetikus
üzenetekkel** futnak (a nemzetközi specifikáció példái).

> **A 2026-11-24-i mérés után a fixture-ök MEGVANNak** — **de a
> `bud01` vevő FIZIKAI formátumban tárolja őket** (a §4.1) →
> **a mérési fixture-ök a `decode_physical_6bit`-tel olvashatók**
> (`physical=True`).
>
> **A GPSD/AIS referencia-példa** (`15M67FC000G?ufbE`FepT@3n00Sa`) a
> **legismertebb szintetikus fixture** → **a fizikai dekódolás az
> MMSI-jét hibátlanul adja: 366 053 209** → **a szintetikus
> tesztek is a fizikai formát használják.**
>
> **A `duna` éles parserének viszont a STANDARD AIS-t kell
> dekódolnia** (a `decode_standard_6bit`) → **a standard armor és a
> fizikai forma közötti konverzió a `duna` feladata** (a `04` §5
> szerinti normalizálás).

---

## 9. A teljesítmény

| Művelet | Cél | Megjegyzés |
|---|---|---|
| Egy üzenet dekódolása | **< 1 ms** | a 6 bites dekódolás Pythonban |
| Egy üzenet feldolgozása (dekódolás + írás) | **< 5 ms** | a DB-írás dominál |
| Az üzenetfolyam feldolgozása | **> 1000 üzenet/másodperc** | a vevőnkénti 100–200 üzenet/mp sokszorosa |
| A memória | **a stream-enkénti 1 üzenet** | nincs pufferelés |

**A mérési adat (a bud01 vevő, 2026-11-22 19:19–21:52) — a
`prof` C-6 és a `preshaz` P-C-3 findingje után.** A korábbi terv a
**README 5.1 becslését** használta; **a mérés a valóság**:

| Metrika | A README becslése | **A mérés** |
|---|---|---|
| Üzenet/nap | ~2 000 000 | **~900 000** (a teljes órával ~1 056 000) |
| Üzenet/mp (átlag) | ~23 | **~10,4** |
| Üzenet/mp (**csúcs**) | „tízszeres" | **~100–300** (a reggeli átkelés) |
| A 30 napos adat | ~60 millió | **~27 millió** |
| A nyers SQLite mérete | ? | **~4 MB/óra** → **~3,4 GB** (35 nap) |
| A `position` a Postgresben | ? | **~27 millió sor/hó** (90 napos TTL → ~81 millió) |

**A teljesítménycél:** a mérés **átlagban** 10,4/mp — a **csúcsot**
kell bírnia (**~300/mp**), és a mérés **a csúcsot** mérje (a
másodpercenkénti maximumot), **ne az átlagot** (a `prof` M-7 findingje).

**A 300 üzenet/mp nem igényel optimalizálást** — az `asyncio` + egy
`psycopg` connection pool elegendő. A **parser nem a szűk keresztmetszet**
— a szűk keresztmetszet az **adatbázis írás** (upsert).

**A `statement_timeout` és a batch mérete** (a `preshaz` P-M-1
findingje): a 03-as terv 5 s-os `statement_timeout`-t ad → a
`executemany` batch **egyben** 5 s alatt kell lefusson → **~2000
sor/batch** (a `psycopg` ~1000 sor/mp).

**A `position` upsert** a `(vessel_id, ts)`-en — a 02-es sémával
egyezik; a `msg_hash` **egyedi** indexe a `ais_message_raw`-on szűri a
duplikátumokat.

**A tárhely** (a `preshaz` P-H-4 findingje):

| Hely | Adat | Méret |
|---|---|---|
| Pi SD (35 nap) | a nyers SQLite | **~3,4 GB** (a mérés: 4 MB/óra) |
| NAS (a lehúzott fájlok) | heti ~600 MB × 52 | **~30 GB/év** — **a törlés kell** |
| Postgres (a központi) | a `position` (90 napos TTL) | **~81 millió sor** → **~15–25 GB** |

**A működési figyelő** (a `preshaz` P-C-4 findingje — a tervben nem
volt): a heti lehúzás sikerességét a NAS-on a `ais-data/` mappa dátumai
ellenőrzik; a vevő életjele az `ais_stats_hourly` táblából jön (a v0.71
kitölti: `msg`, `vessels`, `level_min`/`level_max`, `ppm`) → **az üres
óra = a vevő leállt**.

---

## 10. A tesztelési stratégia

| Szint | Tartalom | Eszköz |
|---|---|---|
| **Unit** | a 6 bites dekódolás, a frame-validáció, az `fill_bits` | `pytest` |
| **Fixture** | az 50 reprezentatív üzenet a mérésből | `pytest` (paraméterezve) |
| **Property** | a dekódolás **round-trip**: a bitekből a karakterek visszaállíthatók | `hypothesis` |
| **Integráció** | a parser → a DB → a `vessel_last_position` nézet | a `validate_ddl.py` mintájára |
| **Regresszió** | a mérési időszak teljes replayje | a mérési fájl + a teljesítmény-mérés |

**A futás közbeni mérés** (a `preshaz` P-H-3 findingje): a `job_run`
`started_at`/`ended_at` → a teljes feldolgozási sebesség (a ~27 millió
üzenet / az idő); a soronkénti mérés (a `rows_in`/`rows_out` különbsége
percenként) → **a 7,5 órás backfill figyelése**.

**A `property` teszt a legfontosabb** — a 6 bites kódolás kézi
implementálásánál a legkisebb hiba is elcsúszik egy bittel. A
`hypothesis` generálja a véletlen biteket és ellenőrzi, hogy a
dekódolás → visszaalakítás az eredetit adja.

---

## 11. A nyitott kérdések

| # | Kérdés | Alapértelmezés | Állapot |
|---|---|---|---|
| Q1 | A `river_km` a **pozíció** üzenetből jön (a szokásos pozíció kiterjesztése), nem a FI 10-ből — a 02-es terv megfogalmazása pontosítandó | **a pozíció üzenetből** | **lezárva** (§4.5) |
| Q2 | A `fairway_code` a pozíció üzenetben van-e? | **nincs hová írni** → **kikerült a normalizált rekordból** (a `prof` M-1 findingje) | **lezárva** |
| Q3 | A **GNSS antenna helye** (a pozícióüzenet 148–167. bitje és a statikus üzenetek antennahelye) a `position` sémában nincs | **eldobva** — a `vessel_data_origin` a statikus adatokra vonatkozik | nyitva (a 02-es tervben) |
| Q4 | A `draught_reference` a `vessel`-ben van (a statikus FI 10-ből) — a `position`-ben nincs | **így** — a `position` a pillanatnyi merülés, a hivatkozás a statikus adathoz tartozik | **lezárva** |
| Q5 | A Msg 4 (bázisállomás) és a Msg 9/11 (SAR) kezelése | **a Msg 4/20/23 a NAVTEX/MSK-forrás** (a mérés) → a `data_quality_event`-be (`severity='info'`), **nem** a `position`-be; a Msg 9/11 (SAR) **eldobandó** | **lezárva** (§4.7.1) — **a korábbi „eldobandó" indoklás hamis volt** |
| Q6 | A `pyais` használható-e **teszt-összehasonlításra** (a saját dekóder helyett)? | **igen** — a MIT licenc és a `pyais` a mezőneveket másképp adja, de a **számértékek** összehasonlíthatók → **a fixture-ök dekódolását a `pyais`-szal ellenőrizzük** | **lezárva** (a `preshaz` P-H-7 findingje) |
| Q9 | **Hogyan dekódolható a belvízi FI 10 `vin` (ENI) mezője?** (a 2026-11-24-i mérés: a vevő a 21-est AtoN-ként dekódolja → **a mérési DB-ben nincs ENI** → a mérés nem tudja validálni) | **a `04` §4.5 szerinti 7 bites kódolás** (a `vin` a `?` kitöltőkkel) — **a `pyais` a DAC 200/FID 10-et nem ismeri** → **saját implementáció kell**, **egy referencia-példával validálva** (a `04` §8.3 fixture-ök) | **nyitva** (a `04` §4.5) |
| Q8 | **Mi a `bud01` vevő `mmsi` oszlopának a normalizálási szabálya?** (a 2026-11-24-i mérés: a tárolt `mmsi` **nem** a `nmea` payloadból számítható → a MID egyezik, a suffix nem; a Class B-nél synthetic 992-es) | **a hajót a MID + a fizikai MMSI suffix alapján azonosítjuk** — a pontos szabály a vevő forrásából kell → **a `duna` saját parserének NEM kell reprodukálnia** (a mi vevőnk a standard AIS-t adja) | **nyitva** (a `04` §5) |
| Q7 | Melyik ** telephelyen** mérünk? | a bud01 a **városi** szakaszon (a Dunától 2,88 km) → a lefedettség itt mérhető, a **szűkvízi** forgalom nem → **a szűkvízi szakaszokon is kell mérni** (a F-CAT-08 szerinti 3 site) | **nyitva** (a `K-4` finding) — **Miklós döntése** |
| Q8 | A `destination` (a célállomás) honnan jön? | **a szerkesztői felületről** (a `06` terv) — az AIS-ből nem (a mérés: 100%-ban üres) | **lezárva** (a `bori` B-C-2 findingje) |
| Q9 | A `nav_status` a sémában `text` vagy `smallint`? | **`text`** (a 02-es sémában már az, és a UI-on olvashatóbb) | **lezárva** — **Miklós döntése** |
| Q10 | A `msg_subtype` (a DAC/FID) bekerüljön-e a sémába? | **igen**, `smallint` — a FI 10 és a Class B megkülönböztetéséhez | **lezárva** — **Miklós döntése** |

---

*Ez a terv a `docs/megvalósulas/` sorozat negyedik darabja. Következik: 05 –
frontend-arkitektúra.*
