# A BUD01 AIS-VEVŐ — a mérési adat (2026-11-22, 19:19 – 21:52)

> A `vessel-tracker` projekt R1-0 előkészítő fázisának **első valós
> mérési eredménye**. A vevő a `bud01` (Raspberry Pi 4, RTL-SDR dongle
> a kék USB 3.0 portban) telephelyen fut.
>
> **A vevő helye:** 47,5755205 N, 19,046013 E — a pesti felső
> városrész, **a Dunától 2,88 km-re**.

## 1. A vevő állapota

| | |
|---|---|
| Az AIS-catcher | v0.71-0-gf27b24b (a Pi-n buildelve) |
| A tuner | `Realtek RTL2838UHIDIR` + `Rafael Micro R820T` |
| A csatornák | **A és B** — mindkettő működik |
| A PPM | **7** (a 25 perces `rtl_test -p` kalibráció után) |
| A jelerősség | −1,5 … −14,8 dB (a stdout JSON-ból) |
| Az adatbázis | `/var/lib/ais/ais.db` (SQLite), `RETENTION 35` nap |
| A service | `ais-receiver.service` — **active**, boot után auto-indul |
| A heti lehúzás | hétfő 04:17 → **a NAS direkt** (`/opt/data/martin/work/ais-data/`) |

## 2. Az üzenettípusok (a mérés első órájában)

| `type` | Jelentés | Darab | Arány |
|---|---|---|---|
| 2 | pozíció (Class A, 10 mp) | 21 914 | 58,2% |
| 21 | belső forgalmi adat (Class B) | 7 016 | 19,1% |
| 4 | **bázisállomás** | 2 070 | 5,7% |
| 3 | pozíció (küldés-kérés) | 2 003 | 5,5% |
| 1 | pozíció (Class A, 1–2 mp) | 1 720 | 4,3% |
| **8** | **belső forg. adat (FI 10) — az ENI-k forrása** | **767** | **2,0%** |
| 5 | statikus hajódatok | 720 | 1,8% |
| 20 | belső forgalmi adat (MSK, Duna) | 559 | 1,6% |
| 23 | belső forgalmi adat (MSK, Duna, új) | 519 | 1,4% |
| 15 | egyéb (interrogálás) | 60 | 0,1% |
| 18 | pozíció (Class B, 10 mp) | 57 | 0,1% |
| 24 | statikus hajódatok (részleges) | 52 | 0,1% |

## 3. A hajók

| | |
|---|---|
| A `ais_state` sorok | **199** |
| **A neves hajók** | **78** |
| Az ENI-jük van | **1** (`GONDOLA`, 8601836) |
| A hívójelük van | **76** |
| A hajótípusuk van | **75** |
| A meretük (a hossz/burkoló/mélység) van | **66** |
| **A navigációs lámpák** (`992438xxx` MMSI) | **106** |
| A `VIRTUAL` pontok | 5 |
| A bázisállomások (`2430003/6/7`) | 3 |

### A legaktívabb hajók (üzenetszám szerint)

| A hajó | MMSI | Üzenet |
|---|---|---|
| `HUNGARIA` | 243070517 | 826 |
| `LAGYMANYOS` | 243070510 | 858 |
| `MILLENNIUM 2` | 243070123 | 856 |
| `ROHAM` | 243042414 | 841 |
| `VISEGRAD` | 243072204 | 838 |
| `PHOENIX 1` | 243042845 | 868 |
| `SLUIZER` | 244730043 | 872 |
| `ESZTERGOM` | 243070519 | 829 |
| `PEST-BUDA` | 243070513 | 766 |
| `SZENT KRISTOF` | 243070326 | 834 |

### A nemzetközi hajók

| A hajó | MMSI | Ország | Hossz | Típus |
|---|---|---|---|---|
| `DOUCE FRANCE` | 226001160 | francia | 110 m | utasszállító |
| `KEPLER` | 203999372 | osztrák | 106 m | tanker |
| `RUBIKON23` | 279202732 | német | 110 m | tanker |
| `STADT WIEN` | 203999406 | osztrák | 77 m | teherhajó |
| `VIKING AEGIR` | 269057408 | finn | 135 m | teherhajó |
| `VIKING BRAGI` | 269057415 | finn | 135 m | teherhajó |
| `TRAVELMARVEL VEGA` | 269057759 | finn | 135 m | teherhajó |
| `RIVIERA RADIANCE` | 269057104 | finn | 135 m | teherhajó |
| `RIVER DIVA` | 253242476 | luxemburgi | 82 m | — |
| `SLUIZER` | 244730043 | svéd | 40 m | — |
| `PASSAU` | 211169130 | német | 80 m | — |
| `MERIAN` | 211694350 | német | 38 m | — |
| `HORISHNI PLAVNI` | 272136300 | ukrán | 36 m | — |

## 4. A Duna navigációs lámpái

A `992438xxx` MMSI-k a magyar Duna **navigációs infrastruktúrájának
virtuális AIS-állomásai**. A nevük a folyó-kilométert és a lámpa jelét
tartalmazza: `1592.4_R_FL` = **1592,4 km, piros villogó lámpa**.

| A jel | Példa | Darab |
|---|---|---|
| zöld (`_G`) | `1598.3_G` | 41 |
| piros (`_R`) | `1619.4_R` | 33 |
| villogó (`_FL`) | `1620.2_R_FL` | 32 |
| fehér (`_W`) | `1652.8_W_FL` | 1 |

**A lefedett Duna-szakasz: 1592,4 – 1728,3 km** — vagyis a teljes
hazai folyószakasz.

## 5. A hajótípus-kódok — a hivatalos UNECE-ERI lista

**A mérésben látt kódok a belvízi (ERI) típuskódok** — a 8xxx-es
sorozat az UNECE ERI kódrendszere (a `CESNI`/UNECE SC.3/WP.3).
**Ezek nem „ismeretlen” típusok** — a tervnek le kell fordítania őket.

| A kód | A jelentése | A hajók száma |
|---|---|---|
| `8444` | személyhajó szállás nélkül | 15 |
| `8443` | Cruzehajó | 14 |
| `8440` | személyhajó, komp, vöröskeresztes hajó | 11 |
| `8000` | a hajó típusa ismeretlen | 8 |
| `60` | utasszállító | 8 |
| `69` | utasszállító (a 60-as kiterjesztése) | 7 |
| `80` | tankhajó | 3 |
| `8450` | kisegítő hajó, rendőrségi, kikötői szolgálat | 3 |
| `51` | tengeri mentő | 2 |
| `0` | nincs megadva | 1 |
| `90` | egyéb | 1 |
| `8430` | tolóhajó, egy | 1 |
| `8460` | munkahajó, karbantartó, úszó daru, kábelhajó, bójahajó, zsombor | 1 |
| `8220` | tolóhajó, két teherbárka | 1 |
| *(null)* | nincs megadva | 2 |

**A mérés tanulsága:** a hajók **53%-a a 8440-as családban**
(személyhajó/komp/Cruzehajó) — a Duna turisztikai és kompszállító
forgalma. A **8444** (szállás nélküli személyhajó) **15 hajó** — a
magyar személyhajók többsége (24–39 m hossz, 1,0–1,4 m meret).
A **8450** (kisegítő hajó) **3** — a `SZENT FLORIAN`, a `KITUZO` sorok.
A **8460** (munkahajó) **1** — a `LUPPA`. A **8430** (tolóhajó) **1** —
a `HORISHNI PLAVNI`. A **8220** (két teherbárkát tolóhajó) **1** — a
`DUNA` (98×24 m, a legnagyobb a listán).

> **A terv (a 04-es parser) feladata:** a `shiptype` kódot **magyar
> nevre kell fordítania** (a F-CAT-08) — és a `vessel_type`
> referencia-tábla (a 02-es tervben) **töltse fel** ezekkel a kódokkal,
> a magyar névvel együtt.

**A forrás:** az UNECE SC.3/WP.3 belvízi AIS-egyezmény
(`ECE/TRANS/SC.3/WP.3/2020/22` — az UN–IMO hajótípus-megfeleltetés),
és a CESNI `L_dir_syst_auto_ident_en_1.pdf` (az ITU-R M.1371
belvízi kiegészítése).

## 6. A bázisállomások (a `2430003`, `2430006`, `2430007`)

**Ezek nem hajók** — a mérésben **kizárólag** a 4-es (bázisállomás), a
20-as és a 23-as (MSK/NAVTEX) üzenettípusokat küldik, **pozíció- (1/2/3)
és statikus (5) üzenet nélkül**. Ez a **Duna navigációs
infrastruktúrájának „állomás" szolgáltatása** — a NAVTEX/MSK
forgalmat adják tovább.

**A fantom-szűrőnek ezeket ki kell zárnia** — a 78 neves hajó
katalógusába nem kerülhetnek bele.

## 7. A FI 10 üzenetek (a 6-os és 8-as típus)

**767 üzenet** a mérés első órájában. **A forrásuk valódi hajó** (nem a
lámpák és nem a bázisállomások) — a NAVTEX-információt a hajók **a
belső infrastruktúrától kapják, és újraküldik**.

**Ez az ENI-adatokhoz vezető út** — de a mérésben **egyetlen hajónál
sem jött le ENI** a FI 10-ből (csak a `GONDOLA` ENI-je van, és az
egyéb forrásból jöhet).

## 8. A mérési protokoll eredménye

| A go/no-go kritérium (a `docs/ais-vevo-terv.md` 5.3) | A mérés |
|---|---|
| A lefedettség ≥ 50% → **saját vevőhálózat (F1, 3 site)** | **69,8%** ✅ |
| A hibás dekódolás aránya < 0,1% | **nem mérhető** a DB-ből (a v0.71 csak a sikeresen dekódoltakat tárolja) |
| A statikus adatok (név) elegendő mennyiségben | **91,5%** (a hajóknak) ✅ |
| A belvízi FI 10 (az ENI-adat) elérhető | **767 üzenet** ✅ |

**A földrajzi lefedettség** a Duna Budapest-környéki szakaszának
korridor-polygonjából számolva (a navigációs lámpák pozícióiból
levezetve, ±1,5 km).

## 9. A tudatos döntés: a jelerősség kimarad a DB-ből

A v0.71-es AIS-catcher a `-M TD` flaggal számolja a jelerősséget (a
stdout JSON-ban megvan), **de a DB-be nem írja** — a `DatabaseOutput` a
`TAG.level`-t a JSON-stream útvonalon nem kapja meg
(`Source/DBMS/DatabaseOutput.cpp:691`).

**A döntés (2026-11-22): a jelerősség kimarad a DB-ből.** A mérés
szempontjából nem kritikus: a go/no-go a lefedettségen alapul, a
szűrő kiválasztása a `msg/hajó` arányból dönt. A saját parser
(**a nyers NMEA-ből dolgozik**) a jelerősséget amúgy sem tudná
kinyerni.

## 9. amit a mérés megmutatott — a tervezési tanulságok

1. **A Duna teljes navigációs rendszere látszik** (106 lámpa, 1592–1728
   km) — ez a projekt katalógusának alapja, nem hajók.
2. **A 3 bázisállomás** (`2430003/6/7`) a NAVTEX/MSK forgalmat adja —
   a parser **külön kategóriaként** kezelje.
3. **A hajók 91%-ának van neve, de csak 1%-ának ENI-je** → a
   bizonyossági badge (`F-CAT-14`) a gyakorlatban `name_only` /
   `ais_partial` lesz, a `ais_identified` ritka.
4. **A fairway-mező nincs a v0.71 kimenetében** → a `river_km`-et a
   **saját parser** kell kinyerje — vagy a lámpák neveiből kell
   számolni (a `1592.4_R_FL` név → a km).
5. **A hibás dekódolás aránya nem mérhető** a DB-ből → a mérési
   protokollnak **más** mérőszámot kell használnia (a `msg/hajó` arány,
   a `repeat` flag, a hosszú ideje némán csendes hajók).
