# A BUD01 AIS-VEVŐ — a mérési adat (2026-11-22, 19:19 – 21:52)

> A `vessel-tracker` projekt R1-0 előkészítő fázisának **első valós
> mérési eredménye**. A vevő a `bud01` (Raspberry Pi 4, RTL-SDR dongle
> a kék USB 3.0 portban) telephelyen fut.
>
> **A vevő helye:** 47,5755205 N, 19,046013 E — a pesti felső
> városrész, **a Dunától 2,88 km-re**.

## 0. A MÉRÉS 2. NAPJA (2026-11-22 18:32 → 2026-11-23 22:28, 28 óra)

> **A fenti táblázatok az első este (~1 óra) adatai.** A mérés azóta
> **28 órán át futott**, és a teljes adathalmaz lejött a NAS-ra:
> `ais-20261123-2328.db` (99,4 MB).
>
> | | Az első óra | **A 28 óra** | A változás |
> |---|---|---|---|
> | Az üzenetek | 37 494 | **382 968** | 10,2× |
> | A pozíciók | — | **354 740** | — |
> | A statikus üzenetek | 720 | **82 282** | — |
> | **A hajók** | 199 | **245** | +46 |
> | **A neves hajók** (a lámpák nélkül) | 78 | **91** | +13 |
> | **A hívójel** | 76 | **96** | +20 |
> | **Az ENI** | 1 | **1** | **nem változott** |
> | **A `destination`** | 0 | **90** | **megjelent!** |
> | **A mozgó hajók** (> 0,5 kn) | 26 | **34** | +8 |
> | Az üzenet/óra | 37 494 | **~13 700** | a csúcsok nappal jönnek |
>
> ### A három tanulság
>
> **1. A `destination` MEGJELENT.** Az első órában **egyetlen hajónak sem
> volt célállomása** — most **90-nek van** (`BUDAPEST`, `KOMARNO`,
> `HELYI SZOLGÁLAT`, `VISEGRÁD`, `DUNAKESZI-HORÁNY`, `LOBAU`,
> `KM 1658`…). **Ez cáfolja a bori B-C-3 findinget:** a célállomás
> **a FI 10 üzenetekből jön, és 1 óra alatt még nem érkezett el** —
> **a `02` v1.6 `destination` oszlopa és a `06` §4.2 mezője tehát
> megalapozott** (a kézi kitöltés csak a **nem** küldő hajóknál kell).
>
> **2. Az ENI-arány NEM javult** (1 hajó, 0,4%) → **a F-NF-09 (≥ 95%)
> a magyar Duna-szakaszon ezzel a vevővel NEM teljesíthető** → **a
> szűkvízi helyszín (a `04` K-4) továbbra is szükséges**.
>
> **3. A PPM két érték.** A `rtl_test -p` kalibráció **+7**, de a DB
> `ais_stats_hourly.ppm` **−6,12** körül van → **két különböző előjel!
> → a `09` §4.2 riasztási határ (`|ppm − 7| > 8`) **egyértelmű
> értelmezést igényel** → **a mérőszám definíciója nyitott** (lásd a
> §6.2-t).
>
> ### A 40 órás adat (2026-11-24 11:55) — a frissített mérés

**A `ais-20261124-1155.db` (125 MB) a NAS-on** — a Pi bootja utáni
lehúzás (a `09` §9.1 szerinti `ExecStartPost`) működik, **és a NAS-oldali
takarítás is** (a napi duplikátumok törölve → napi 1 fájl marad).

| Metrika | Az első óra | A 28 óra | **A 40 óra** |
| Az üzenetek | 37 494 | 382 968 | **482 036** |
| A pozíciók | — | 354 740 | **~445 000** |
| A hajók | 199 | 245 | **263** |
| A nevet viselő hajók | 78 | — | **213 (82,6%)** |
| Méretekkel | — | — | **109 (42,3%)** |
| ENI-vel | 1 | 1 | **1 (0,4%)** |
| **A `destination`-nel** | 0 | 90 | **~97** |
| A FI 10 (ENI) üzenetek | 767 | 7 894 | **~9 600** |
| **A fantom-jelöltek** | — | — | **16** |

**A lefedettség 69,8% → 64,59%** — az éjszakai órák kevesebb forgalmat
hoznak (a nappali 6–10 ezres csúcsok ~18 000 üzenet/óra, az éjszakai
~6 500) → **a mérőszám a teljes nap átlagja** (a F1 küszöb: 50%).

**A `destination` most már a hajók 60%-ánál megvan** → **a bori B-C-3
findingje (a „célállomás sosem jön") a mérési adat alapján cáfolódik**:
a `02` v1.6 `destination` oszlopa és a `06` §4.2 mezője **megalapozott**.

### 🆕 A `shiptype` kérdése (a `04` – parser-tervhez)

**A mérés 7 olyan `shiptype` kódot talált, ami NINCS a `02` v1.6
seedjében (89 típus):**

| A kód | A hajó | A jelentése |
|---|---|---|
| `37` | THETIS | **SOLAS hajóosztály 3** (teherhajó) |
| `35` | AM31 DUNAUJVAROS | SOLAS hajóosztály 3 |
| `33` | LUPPA | SOLAS hajóosztály 3 |
| `79` | TEKOV | SOLAS hajóosztály 7 |
| `89` | AQUA TEAM | SOLAS hajóosztály 8 |
| `99` | MARGITSZIGET, MONARCH QUEEN | SOLAS hajóosztály 9 |
| `156` | PRIMUV | **az ERI 14 bites kódja a hajóosztállyal keverve** |

**A `04` – parser-terv §4.5 szerint** a `shiptype` **14 bites ERI-kód**,
**de a mérésben a SOLAS-osztályok (30–99) is megjelennek** →
**a `shiptype` → `vessel_type` lookupnak két kódtervet kell kezelnie:**
a **8000–8519-es ERI**-t **és** az **1–99-es SOLAS-osztályt** →
**a hiányzó → az `UNKNOWN`** (a `04` §626-630 szabálya) → **ez a
lookup helyes, de a `02` seedből a SOLAS-osztályok hiányoznak**.

**A hatás: kicsi** (a 258 hajóból 8 érintett, mind 1–2 hajó) →
**a seed bővítése a `02` v1.7-ben** (SOLAS-osztályok a magyar nevekkel).

---

### 🆕 A statikus adatok ütemezése (a 2026-11-24-i mérés)

**Az AIS nem egyetlen csomag:** a **pozícióadatok** (a sebesség, az
irány, a koordináták) **másodpercenként** sugároznak, **a statikus
adatok** (a hajónév, a méretek, az ENI) **6 percenként**.

**A mérés igazolja:**

| A mérőszám | Az érték |
|---|---|
| a statikus (Msg 5/24) üzenetek közötti rés | **a medián 361 mp (6,0 perc)** · a 75% 590 mp |
| a FI 10 (a belvízi ENI) üzenetek közötti rés | **a medián 364 mp (6,1 perc)** |
| **a statikus adat elérése a pozíció után** | **a medián 8,8 perc** · a 75% 33,8 perc · **a maximum 795 perc (13 óra)** |
| 10 percen belül megvan | **51%** |
| 20 percen belül megvan | **63%** |

**A nyers NMEA bizonyítja** (a `type 5` / `type 8` / `type 2`):

| Az üzenet | A tartalom | Az ENI benne? |
|---|---|---|
| `type 2` → `23WkpQ0P00QGD\`RK=ckf4?wN20Sl` | a pozíció | **nem** |
| `type 5` → `53Wktk400000PMH@001HU<DM84@000000000000t0hQ16vim02hUA0D1` | a nemzetközi hajószám, a méretek, a NAV-nevek | **nem** |
| `type 8` → `83Wklbhj2P00000000gPS?\`53L00` | **a belvízi FI 10: az ENI (`2P000000`), a hossz, a szélesség, a `shiptype`, a merülés** | **igen** |

**A két fontos következmény:**

**1. Az ENI-arány nem az időzavartól függ.** A mérés első órájában
**0,5%** volt, 37 óra alatt **0,4%** → **nem azért alacsony, mert
„még nem jött be" a statikus adat** → **a hajók 76%-a küld FI 10-et,
a többi sosem fog ENI-t küldeni ezen a vevőn.** A mérés: a 135
pozíciót küldő hajóból **102 küld FI 10-et**, és a **34-ből 30
navigációs lámpa**, a **4 valódi hajó pedig NEM küld FI 10-et**
(a `LEGENDA`, a `KEPLER`, a `LAGUNA`, a `GONDOLA`).

**2. A katalógus „érési" ideje 8,8 perc** (a medián) → **a mérés
elején a katalógus hiányos** → **a felületnek jeleznie kell, hogy egy
hajó adatai még frissülnek** (a `vessel_data_origin.observed_at`).

### A tipusok a 28 órában
>
> | `type` | Jelentés | Darab | Arány |
> |---|---|---|---|
> | 2 | pozíció (Class A, 10 mp) | 216 934 | 56,7% |
> | 21 | belső forgalmi adat (Class B) | 74 025 | 19,3% |
> | **4** | **bázisállomás** | 21 990 | 5,7% |
> | 1 | pozíció (Class A, 1–2 mp) | 21 047 | 5,5% |
> | 3 | pozíció (küldés-kérés) | 19 940 | 5,2% |
> | **8** | **belső forg. adat (FI 10)** | **7 894** | **2,1%** |
> | 5 | statikus hajódatok | 7 450 | 1,9% |
> | 20 | belső forgalmi adat (MSK, Duna) | 6 060 | 1,6% |
> | 23 | belső forgalmi adat (MSK, Duna, új) | 5 396 | 1,4% |
> | 24 | statikus (Class B, részleges) | 807 | 0,2% |
> | 18 | pozíció (Class B, 10 mp) | 804 | 0,2% |
> | 15 | egyéb (interrogálás) | 620 | 0,2% |
>
> **A type 4/20/23 együtt 8,7%** → **a navigációs infrastruktúra forgalma
> nem hajó** → **a fantom-szűrőnek ki kell zárnia** (a `04` §5.2).

---

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
| A heti lehúzás | **a Pi bootja után** (a `ExecStartPost`) + a biztonsági cron hétfő 04:17 → **a NAS direkt** (`/opt/data/martin/work/ais-data/`) |

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
