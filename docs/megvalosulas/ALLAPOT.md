# Állapot – Vessel Tracker (Duna és Balaton)

**Frissítve:** 2026-11-26
**Repo:** https://github.com/VorosEgyes/vessel-tracker
**A fejlesztések alapcommitja:** `7fb5c26`; az alább jelzett fejlesztéseket
a dokumentum frissítésekor a GitHub CI még nem ellenőrizte.
**Aktuális munkaterület:** **az alkalmazás rétegeinek megépítése**
(a `03` – API-specifikáció alapján) — **a Pi + rádió mérésével
párhuzamosan**

> Ez a dokumentum a **„hol állunk"** hivatkozási pont: mi kész, mi fut,
> mi a következő lépés, és hol van minden. Frissítése a munkafolyamat
> minden fontos állapotváltásakor.

---

## 1. A projekt egy mondatban

**Hajókövető a Dunán és a Balatonon** — az R1 release egy **statikus
hajókatalógus** (térkép és élő adat nélkül), három nyelven (hu/de/en).

**A mérési fázis korábban elindult** (a `bud01` AIS-vevő, 2026-11-22) —
**és párhuzamosan az alkalmazás rétegei készülnek** (a `03`
alapján): a séma, a migráció, a hajós és referenciakatalógus-API,
a generált TypeScript-kliens és a statikus katalógus első változata
valós kód. A mérés jelenlegi üzemállapotát ebben a körben nem ellenőriztük.

**A két munkaág összefüggése:** a mérés **a fixture-öket adja**
(a `04` – parser-terv) → **a mérésből jönnek az AIS-tesztadatok**,
amikre a parser épül; **az alkalmazás rétegeire a mérés nem
vár** → **ezért lehetett párhuzamosan dolgozni.**

---

## 2. Mi a kész

### 2.1 A tervezési dokumentáció (a repóban, 17 fájl)

| Dokumentum | Tartalom | Státusz |
|---|---|---|
| `README.md` | az adatbázis-terv v1.3 — a séma, a jogszabályi háttér, a forrásmátrix | kész |
| `docs/funkcio-leiras.md` | a funkcióleírás (a F-xxx követelmények) | kész |
| `docs/release-terv.md` | a release-terv (R1–R5) | kész |
| `docs/r1-adat-terv.md` | az R1 adat-terv (a forrásmátrix, a validációs szabályok) | kész |
| `docs/ais-vevo-terv.md` | a saját AIS-vevőhálózat terve (a lefedettség, a hardver, a mérési protokoll) | kész |
| `docs/ingest-terv.md` | az adatút (a Pi → MQTT → ingest → Postgres) | kész |
| `docs/pi-eloallitas.md` | **a Pi előállítása lépésről lépésre** (28 lépés) | kész |
| `docs/measurement_2026-11-22.md` | **a bud01 vevő első mérési órája** (44 000 üzenet, 199 hajó, 106 lámpa, a go/no-go 69,8%) | kész |
| `docs/sema-core.mmd`, `docs/sema-irodalom.mmd` | a Mermaid séma-ábrák | kész |

### 2.2 Az implementációs terv-sorozat (`docs/megvalosulas/`)

| # | Terv | Státusz |
|---|---|---|
| 01 | technológiai stack és projektstruktúra | **v1.4** — 2 körű swarm review |
| 02 | adatbázis-séma (DDL v1.1) | **v1.12** — korábbi PostgreSQL-validáció és review |
| 03 | API-specifikáció | **v0.7** — review és implementációs pontosítások |
| 04 | AIS-parser specifikáció | **v1.0** — 64 finding, **mind javítva** (a mérés alapján) |
| 05 | frontend-arkitektúra | **v0.3** — review után, részleges megvalósítással |
| 06 | szerkesztői felület | **v0.2** — review után, megvalósítás előtt |
| 07 | CI/CD és környezetek | **v0.4** — review után |
| 08 | teszt-stratégia | **v0.3** — review után |
| 09 | üzemeltetés és observability | **v0.3** — review után |

**A tervsorozat teljes (01–09)**, de a tervek megléte és review-ja nem
jelenti az összes funkció megvalósítását.

### 2.3 A 02-es DDL — a legjobban validált rész

**A séma futtatva van valódi PostgreSQL 17-en:**

| Objektum | Darabszám |
|---|---|
| Tábla | 71 |
| Index | **157** |
| FK constraint | **124** |
| CHECK constraint | **372** |
| Particionált tábla | 3 (`ais_message_raw`, `water_level`, `position`) |
| Trigger-definíció | 28 |
| **A referenciaadat-seed** | **89 hajótípus** (a magyar nevekkel), 3 nyelv, 24 ország, 11 folyószakasz, 4 medence, 8 teherfajta, 5 üzemeltető |

**17 funkcionális teszt, mind zöld** — a `db/tools/validate_ddl.py`
a terv markdown-ból kicsomagolja a DDL-t, lefuttatja egy élő
PostgreSQL-en, majd füstöt hajt végre.

**A validáló maga indítja el a postgres-t** (a `pgserver`) és a
**`--plan` kapcsolóval bármely tervet validál** (a live helyett a
benyújtott fájlt olvassa).


---

## 2b. A kódoldali állapot (2026-11-26)

**Ez a fejezet a „melyik kódrész kész" rögzítése.** A fenti 2.1–2.2
a **tervezési** oldal; **ez az implementációs**.

### 2b.1 A repó szerkezete (a `01` §4.2 szerint)

```
apps/api/src/duna/
├── config.py              ← a pydantic-settings (a DATABASE_URL)
├── main.py                ← a FastAPI app + a CORS + a /health + a lifespan
├── db/
│   ├── models.py          ← 20 ORM modell (a 02 DDL ORM-reprezentációja)
│   ├── session.py         ← az async engine (a lifespanben!) + a session-gyár
│   └── views.py           ← a DB-nézetek (vessel_verification, vessel_last_position)
├── api/v1/
│   ├── vessel.py          ← GET /vessels, /vessels/{id} + 5 al-végpont
│   ├── search.py          ← GET /search
│   ├── content.py         ← GET /content/{key}
│   └── reference.py       ← referencialisták + kikötő/zsilip adatlap
├── api/export_openapi.py  ← OpenAPI export
├── schemas/               ← a Page[T]/Data[T], a VesselListItem, a VesselDetail
├── repositories/          ← a lekérdezések, köztük a referenciák
├── services/              ← a service réteg
├── domain/                ← a tiszta üzleti logika (verification, text, slug)
└── ingest/                ← az AIS parser (a 04)
```

**A rétegsorrend (a `03` §5.1):** `router → service → repository → DB`.
Az Astro alkalmazás az `apps/web/`, a generált kliens a
`packages/api-client/`, a generált séma a `docs/api/v1/openapi.json` alatt van.

### 2b.2 A megvalósított API-végpontok

Összesen **21 végpont**: az alábbi 10 (a `/health`-szel együtt), 9
referencialista és 2 referencia-adatlap; a FastAPI dokumentációs útvonalai
nem számítanak bele.

| A végpont | A funkció | A státusz |
|---|---|---|
| `GET /health` | a DB elérhetősége (a 09 §4.1) | ✅ |
| `GET /api/v1/vessels` | a katalóguslista (a F-CAT-02) | ✅ |
| `GET /api/v1/vessels/{id}` | a hajóadatlap (a F-DET-01…16) | ✅ |
| `GET /api/v1/vessels/{id}/aliases` | a történeti nevek (a F-DET-05) | ✅ |
| `GET /api/v1/vessels/{id}/ownership` | a tulajdonosváltások (a F-DET-05) | ✅ |
| `GET /api/v1/vessels/{id}/certificates` | az engedélyek (a F-DET-02) | ✅ |
| `GET /api/v1/vessels/{id}/identifiers` | az azonosítók (a F-DET-02, -15) | ✅ |
| `GET /api/v1/vessels/{id}/data-origin` | a mezőnkénti eredet (a F-DET-15) | ✅ |
| `GET /api/v1/search` | a globális kereső (a F-SRCH-01…07) | ✅ |
| `GET /api/v1/content/{key}` | a fordítás-fallback-lánc (a F-NF-01…15) | ✅ |

**Korlátok:** a katalógus egyes tervezett szűrői (`moving`, `section`,
`basin`, `home_section`, `home_basin`, `season`) még nem készültek el;
ezekre az API 422-es választ ad. A hajóadatlap és a listák a hiányzó
nyelv esetén visszaeső nevet használnak, de a mezőnkénti
`translation_fallback` metaadat ezeknél a végpontoknál még nem kész.

**A `GET /api/v1/search/suggest`** (a F-SRCH-08) ⏳ **R3** — nem R1.

**Referenciakatalógus:** elkészült a `ports`, `locks`, `waterways`,
`river-sections`, `basins`, `vessel-types`, `operators`, `routes` és
`cargo-types` lista, továbbá a kikötő- és zsilipadatlap. A listák
lapozhatók; a kikötőlista vízút-, típus-, ország- és szövegszűrést is
támogat. A fordított nevekhez `name_language` és `name_fallback` jelzés
tartozik; a kért nyelv után angol, majd magyar szöveg következik.

### 2b.3 A kész infrastruktúra

| A rész | A státusz |
|---|---|
| **a `justfile`** (a kanonikus belépési pont) | ✅ **~36 recept** |
| **az Alembic-migráció** (a `db/migrations/`) | ✅ **a `0001` a teljes sémát hozza létre** — a `just db-migrate` fut, a `just test-reversible` igazolja a visszafordíthatóságot |
| **a `db/ddl/schema-v1.1.sql`** | ✅ **GENERÁLT** a `02` tervből (a `just ddl-generate`) — **a `just ddl-diff` ellenőrzi a driftet** |
| **a CI** (a `.github/workflows/ci.yml`) | a `46b3dd5` CI-futása elbukott két SQLite-teszten; a helyi javítás távoli CI-n még nem futott |
| **a Build** (a `build.yml`) | a PostgreSQL image épül; az API és a web Dockerfile hiányzik, image-buildjük kimarad |
| **a deploy workflow-k** | léteznek, de a környezetek és a telepítés működését most nem ellenőriztük |
| **a `scripts/ci/pytest_or_skip.py`** | ✅ **nem maszkolja a hibákat** (csak a „nincs gyűjtött teszt" esetet nyeli el) |
| **a `scripts/ci/check_models.py`** (a `just models-check`) | ✅ **kétirányú modell–séma drift-ellenőrzés** |
| **a `scripts/ci/check_reversible.py`** | ✅ **a valódi migráció-visszafordítás teszt** |

### 2b.4 A tesztek és a minőségi kapuk

| Ellenőrzés | Legutóbbi helyi eredmény a jelenlegi fejlesztés során |
|---|---|
| Python `pytest` | **144 sikeres** frissen migrált, izolált PostgreSQL 16.2-vel, 2026-11-27-én |
| API-kliens | 2 Vitest-teszt sikeres; TypeScript típusellenőrzés és generált séma driftellenőrzés sikeres |
| Frontend | 4 Vitest-teszt sikeres; ebből egy ellenőrzi a hat statikus oldal buildjét és az elérhetetlen API miatti buildhibát |
| Böngésző | a keresés, az üres eredmény és az API-hiba helyi teszt-API-val ellenőrizve |
| Statikus ellenőrzés | Python Ruff és mypy, Astro/TypeScript típusellenőrzés és Prettier sikeres |

A helyi PostgreSQL-példányban nem volt PostGIS, unaccent és pg_cron,
ezért az első migráció ezek nélküli fejlesztői változata futott; az éles
extensionökkel és az időzített jobbal külön ellenőrzés szükséges. A
teljes `just check` és a jelenlegi munkafa GitHub CI-je nem futott le.

### 2b.4a Az új frontend és kliens

- **API-kliens:** `packages/api-client/`; az OpenAPI-export és a generált
  típusok együtt frissülnek (`pnpm api:generate`), eltérésük ellenőrizhető
  (`pnpm api:check`).
- **Katalógus:** `apps/web/`; hat statikus oldal (`hu`/`en`/`de` ×
  Duna/Balaton), buildkori API-adatokkal és élő API-s kereséssel,
  rendezéssel, lapozással. A build hibával leáll, ha az API nem érhető el.
- **Korlátok:** JavaScript nélkül csak a buildkori lista látható; nincs még
  hajóadatlap, automatikus rebuild-hook vagy webes/API Dockerfile.
  A build- és böngészős API-cím beállítását az
  [apps/web/README.md](../../apps/web/README.md) írja le.

### 2b.4b Ebben a munkamenetben javított hibák

Az AIS sebesség- és iránymértékegységei; az ismétlődő hajósorok;
a hiányzó és téves nyelvű fordítások; a keresési lapozás és a másik
terület azonosítós jelzése; a nem támogatott szűrők csendes figyelmen
kívül hagyása; valamint az adatlap szöveges pozíciója. A hibákhoz
regressziós tesztek kerültek; a PostgreSQL-specifikus igazolás még nyitott.

### 2b.4c Adatmodell-felülvizsgálat (2026-11-27)

**Keret:** a jelenlegi API és a későbbi funkciók megtartása a cél; a
felhasználó szerint nincs megőrzendő éles adatbázis. A vizsgálat a
sémára, az R1-adatigényre és az alkalmazás jelenlegi adatfelhasználására
épült, nem egy feltöltött adatbázis mérésére. A táblák kihasználtsága,
az adatok kitöltöttsége és az indexek valódi költsége ezért nem mért.

| Adatkör | Célszerűség és státusz |
|---|---|
| Hajó, azonosító, név, típus, terület, státusz | a kereshető R1-katalógus alapja; az ismeretlen típus és zászlóország kezelését az ingest tervezésekor tisztázni kell, mert a jelenlegi séma kötelezővé teszi őket |
| Üzemeltető, méretek, kapacitás, építési év, forrás és megfigyelési idő | hasznos katalógusadatok, de nem garantált az AIS-ból való kitöltésük; az ismeretlen érték nem azonos a nullával vagy a hamissal |
| Fordítások, korábbi nevek, forrástörténet | a többnyelvűséghez, hajótörténethez és ellenőrizhetőséghez indokolt; a név több helyen való tárolásának következetességét biztosítani kell |
| Kikötők, zsilipek, vízterületek, útvonalak, rakománytípusok | a jelenlegi referencia-API használja őket; nem tekinthetők egyszerűen törölhető, kihasználatlan tábláknak |
| Pozíció, nyers AIS és vízállás idősor | R1-ben a részletes, tartós mozgástörténet nem alapkövetelmény, későbbi funkciókhoz hasznos lehet; a tényleges gyűjtés előtt megőrzési időt, tárolási költséget és adatminimalizálást kell eldönteni |
| Menetrend, esemény, vízállás, pénznem és árfolyam | többnyire későbbi igényeket szolgálnak; a jelenlegi Python-kódban nincs teljes feldolgozási folyamatuk. Megőrzésük tudatos kompatibilitási döntés, nem bizonyíték arra, hogy most adatot is kell gyűjteni |
| Szerkesztő, audit, visszajelzés, üzemeltetés | a tervezett szerkesztési és üzemi működéshez tartoznak; a teljes munkafolyamat még nem készült el |

**Prioritásos megállapítások és további javaslatok:**

1. **Megőrzési hiba javítva, helyi PostgreSQL-teszttel:** a régi
   `drop_expired_partitions` a partíció
   nevét napi tartománynak feltételezi, miközben a `position_p20261101`
   havi partíció. Emiatt egy havi partíció a teljes időtartama lejárta
   előtt törölhető. A default partíciókat a függvény nem törli, és a
   sémában látható `position_default`-törlés csak a séma létrehozásakor
   fut. A nyers AIS és vízállás default partíciójára sincs itt ütemezett
   sortörlés. A `20261127_0002` migráció a tényleges partícióhatár alapján
   töröl, a default partíciót takarítja, és a hibát nem nyeli el.
   A részben lejárt partícióban az adatok a teljes partíció lejártáig
   megmaradnak; nagy default partíció takarítása blokkolhatja az írásokat.
2. **Azonosítók két helyen:** a kanonikus `vessel_identifier` mellett a
   `vessel.mmsi`, `eni`, `imo` oszlopokat triggerek szinkronizálják.
   Ez egyszerűbb olvasást ad, de plusz inkonzisztencia- és migrációs
   kockázat; a `vessel` bármely UPDATE-je újraolvassa az aktív primer
   azonosítókat. Egységes forrásra váltás előtt a detail API-t, indexeket,
   importot és történeti adatokat együtt kell átállítani.
3. **Bizonyossági szint kétféleképp:** a szűrő a tárolt, a megjelenítés
   a számított értéket használja, ezért eltéréskor egy elem nem a látható
   badge szerint szűrődik. Ezt a jelenlegi szerződés és teszt szándékosan
   rögzíti; egységesítéséhez API-viselkedési döntés és regressziós teszt
   szükséges, nem pusztán egy oszlop eltávolítása.
4. **Források és történet:** a `vessel_data_origin` aktív egyedisége
   eredettípusra, nem `source_id`-ra vonatkozik, így ugyanazon típus
   több egyidejű forrása nem tárolható. A konfliktusnézet több eredetet
   számol, nem feltétlenül eltérő értékeket. A `vessel_ownership`
   üzemeltetőre hivatkozik, ami nem bizonyít tulajdonjogot.
5. **Migrációs reprodukálhatóság:** a `0001` korábban a változtatható
   generált DDL-t olvasta. Most a revízióhoz tartozó rögzített SQL-másolatot
   és saját, rögzített transzformációkat használ; a hash-t teszt védi.
   A terv–generált DDL ellenőrzés nem igazolja az Alembic `head` sémáját,
   és a terv megváltoztatása nem migrálja a meglévő adatbázist. A `0001`
   külön `psql` folyamatot használ, így hibánál részleges séma maradhat;
   az extensionök elérhetősége is befolyásolja az eredményt. A helyi
   ellenőrzéskor felfedezett socketes
   kapcsolathiba és `PGPGBIN`-útvonalkezelés javítva: a `psql` a
   `DATABASE_URL` szerinti adatbázist használja.
6. **Adatforrás-ellentmondás:** a parserterv korábban ugyanazon oldalon
   állította, hogy az AIS Msg 5 tartalmaz és nem tartalmaz nevet.
   A bitmezők és a dekóder alapján az állítást javítottuk; az
   [R1 adatterv](../r1-adat-terv.md) FI 10-hez rendelt egyéb mezőit
   forrásonként külön ellenőrizni kell az ingest megépítése előtt.

A kódban a katalógus és a keresés közös sorkonverziót, a hajó és a
történeti üzemeltető pedig közös nyelvi sorrendet használ. A felülvizsgálat
nem törölt táblát, mezőt vagy API-t. A nagyobb sémaegyszerűsítés továbbra is
összehangolt migrációt és integrációs ellenőrzést igényel.
Az integrációs tesztek újrafuttatása azonos tesztadatbázison jelenleg
nem megbízható: a hajóteszt fixture egyes forrásrekordokat nem takarít
és újból beszúr. A fenti teljes futás ezért friss tesztadatbázison történt.

**Megőrzési ütemezés:** a `0001` a `pg_cron`-hívásokat továbbra is
eltávolítja, ezért a `0003` migráció állítja be a három heti feladatot.
A nyers AIS 14, a vízállás és a pozíció 90 napos megőrzését a felhasználó
jóváhagyta. A migráció pg_cron nélküli környezetben figyelmeztet, elérhető,
de az adatbázisba nem telepített kiterjesztésnél hibázik. Utólagos
telepítéskor az SQL külön futtatandó; a konfigurációt, a futtató
szerepkört és a tényleges futások ellenőrzését a
[migrációk leírása](../../db/migrations/README) részletezi.

Helyi PostgreSQL 16.2 és pg_cron 1.6 környezetben a migrációt, az
idempotenciát, az ütközéskezelést, a visszaléptetést és egy ténylegesen
futó, tesztadatot törlő cron-jobot is ellenőriztük: a teljes Python-suite
150 sikeres és 1 kihagyott teszttel zárult. PostGIS ebben a környezetben
nem volt; a pg_cron nélküli teljes futás 146 sikeres és 2 kihagyott
tesztet adott a cron-specifikus tesztek további bővítése előtt.

A `90013f7` commit CI- és Build-workflow-ja sikeres volt, de az utána
induló staging workflow a hiányzó `pnpm` miatt elbukott. A staging és
production workflow ezért a CI-hez hasonlóan telepíti a csomagkezelőt;
a staging új futásának eredményét a GitHub Actions mutatja.

### 2b.5 A mérési oldal (a 2026-11-24-i állapot)

| A mérés | Az eredmény |
|---|---|
| **a mérés időtartama** | **40 óra** (2026-11-22 → 11-24) |
| **az üzenetek száma** | **482 036** |
| **a hajók száma** | **263** |
| **a statikus ütem mediánja** | **361 mp** |
| **a lefedettség** | **64,59%** (a 37 órás mérésben) |
| **a névlefedettség** | **82,6%** |
| **az ENI-arány** | **0,4%** (a városi helyen — a szűvízben mérni kell) |

> A korabeli feljegyzés szerint a 30 napos mérés 2026-12-22-ig tartott
> volna, heti Pi → NAS lehúzással; aktuális állapota nem ellenőrzött.

### 2b.6 Korábbi, commitolt munka

Az alábbiak korábbi commitok; a dokumentált új fejlesztések alapja
`7fb5c26`.

| A lépés | A commit |
|---|---|
| az Alembic-migráció (a séma a forrás) | `5d1c9e4c3e` |
| a TCP-csatlakozás javítása (a CI-hiba) | `6eb0af64ce` |
| az extensionök telepítése (a CI-hiba) | `dd0fb35823` |
| a trigram-index javítása (a CI-hiba) | `7b5934b4e7` |
| **az `api/` réteg** (a katalóguslista) | `0f5ecf29db` |
| **a hajóadatlap + 5 al-végpont** | `bb9cc0cc2e` |
| **a globális kereső** | `57912356e6` |
| **a service réteg + a content végpont** | `0062220fcd` |

**A talált és javított valódi hibák (mind a tesztek és a `mypy` kapták el):**

| # | A hiba | A javítás |
|---|---|---|
| 1 | a `psql` a socketet kereste (a CI service TCP-n fut) | a `PGHOST`/`PGPORT`/`PGPASSWORD` a teljes URL-ből |
| 2 | `unaccent(text) does not exist` | a migráció telepíti a szükséges extensionöket |
| 3 | „index expression must be marked IMMUTABLE" (az `unaccent` nem IMMUTABLE) | a `02` v1.10: az index-kifejezés `lower(x)` |
| 4 | a globális `lru_cache`-elt engine → „Event loop is closed" | az engine a FastAPI lifespanben (architekturális hiba) |
| 5 | a `verification_level` label-ütközés (a tárolt érték jött) | egyedi label → a SZÁMÍTOTT érték |
| 6 | 4 hibás ORM modell (`country.name`, `operator.legal_name`, a `port` neve, a `waterway`) | javítva + **a `just models-check` elkapja a driftet** |
| 7 | a trigger felülírta az alkalmazás normalizált `sort_name`-jét | a `02` v1.12: csak az üres `sort_name`-t állítja |
| 8 | a `pgserver` egyetlen extensiont sem tartalmaz | a kereső a `sort_name` mellett a `vessel_i18n.name`-re is keres |
| 9 | a router közvetlenül a repository-t hívta (a `03` §5.1 eltérés) | a service réteg (4 modul) |
| 10 | az `UPDATE` `rowcount`-ja nem megbízható | a `RETURNING`-es upsert |
| 11 | a `vessel_identifier.source_id` hiányzott a `models.py`-ből | javítva (a `mypy` kapta el) |

## 3. Korábban jelentett üzemállapot

Az alábbi Pi/NAS-állapot történeti feljegyzés; most nem történt élő ellenőrzés.

| Mi | Hol | Állapot |
|---|---|---|
| **A bud01 AIS-vevő** | a Pi-n (`ais-receiver.service`) | ✅ **fut** 2026-11-22 19:19 óta — 38 000+ üzenet/óra, 199 hajó |
| **A heti lehúzás** | a Pi bootja után (`ExecStartPost`) → a NAS (`/opt/data/martin/work/ais-data/`) | ✅ **működik** (a legutóbbi: `ais-20261124-1155.db`, **125 MB**, **482 036 üzenet**, 263 hajó) (a `command=` korlátozással) — hétfő 04:17-kor |
| **A mérési elemző** | a NAS-on (`analyze_measurement.py`) | ✅ fut — a read-only (`immutable=1`) nyitás nem hagy `-wal`/`-shm` fájlokat |
| **A 30 napos mérés** | a `bud01` telephelyen | **2026-12-22-ig** — a go/no-go küszöbön (69,8% ≥ 50%) |

**A mérés első órája:** 44 000 üzenet, 199 hajó (78 neves), 106
navigációs lámpa, 767 FI 10 (ENI) üzenet, **69,8% földrajzi lefedettség**
→ **a go/no-go küszöbön** (a `docs/measurement_2026-11-22.md`).

**A 40 órás mérés (2026-11-24):** **482 036 üzenet**, **263 hajó**,
**a statikus ütem mediánja 361 mp** — a részletek a
`docs/measurement_2026-11-22.md`-ben.

### 3.1 A kódoldal (2026-11-26)

| Mi | Hol | Állapot |
|---|---|---|
| **a FastAPI app** | `apps/api/src/duna/` | hajós és referencia-végpontok; az új PostgreSQL-tesztek még nem futottak helyben |
| **a séma + a migráció** | `db/migrations/` + `db/ddl/` | korábban ellenőrzött; a jelenlegi munkafával nem futott újra |
| **a CI és Build** | `.github/workflows/` | a helyi módosítások GitHubon még nem futottak; API/web image nincs |
| **a minőségi kapu** | `just check` | a jelenlegi munkafán nem futott teljes egészében |
| **a fejlesztések alapcommitja** | Git | `7fb5c26` |

**A részletek:** a [2b. fejezet](#2b-a-kódoldali-állapot-2026-11-26).

> **A 03-as és a 04-es swarm review lezárult** — a findingek mind
> be vannak írva (a 03 → v0.3, a 04 → v1.0).

---

## 4. A következő munkaterület: a Pi + rádió

### 4.1 Mi a cél

**A Budapesti AIS-vevő** (R1-0, a mérési fázis első lépése) — a
`docs/ais-vevo-terv.md` 10. fejezete és a `docs/pi-eloallitas.md`
alapján.

**A cél:** egy működő AIS-vevő, ami a NMEA üzeneteket a szerverre
küldi — és **30 napig mér** (a `ais-vevo-terv.md` 5. fejezete:
a go/no-go).

### 4.2 A hardver

| Elem | Specifikáció | Ár (EUR) | Állapot |
|---|---|---|---|
| **Raspberry Pi 4** | a gyorsabb processzor, a 2× USB 3.0 és az 5 GHz-es Wi-Fi miatt | ~50 | ✅ **van** |
| **SD-kártya** | 32 GB, A2 osztály (a wear levelling miatt) | ~10 | ✅ **van** (a DB 4,1 GB / 29 GB = 15%) |
| **AIS USB dongle** | RTL2832U (a mérésben **PPM 7–8** — TCXO nélkül) | ~25–35 | ✅ **van** — a **TCXO-s (0,5 ppm) verzió a következő méréshez** |
| **162 MHz antenna** | AIS-re hangolt, fix, függőleges polarizáció, ~3 dB | 80–250 | ✅ **van** |
| **162 MHz SAW szűrő** | a túlterhelés és a LO-szivárgás csökkentésére | ~20 | ⬜ **később** — a mérés szűrő nélkül is indulhat |
| **Koax** | RG-58/U, **max. ~10 m** (a hosszú kábel tönkreteszi a jelet) | 20–60 | ✅ **van** (a kék USB 3.0 portban működik) |
| **Táp** | a Pi 4 hivatalos 5V/3A | 30–60 | ✅ **van** |
| **UPS** (power bank) | a tápkiesés = adatlyuk | 30–60 | ⬜ **beszerzendő** |
| **Hűtés** | a Pi és a dongle is melegszik (a PPM driftel) | ~10 | ⬜ **beszerzendő** |

**A telephely:** Budapest, 3. emelet, a parttól ~2 km-re (a
`ais-vevo-terv.md` 10.1: a rádióhorizont ~14,3 km, a **hasznos
folyólefedettség ~15–20 km**).

**A legfontosabb elhelyezési kérdés:** a **tető fölé 3–5 m-rel** kerül
az antenna → a horizont 14,3 km-ről ~17 km-re nő (**+2–3 km mindkét
irányban**).

### 4.1a A megépítés állapota (2026-11-22)

| A hardver | Állapot |
|---|---|
| **Raspberry Pi 4** | ✅ van (a 3B+ helyett — a gyorsabb processzor, a 2× USB 3.0 és az **5 GHz-es Wi-Fi** miatt) |
| SD-kártya (32 GB) | ✅ van |
| RTL2832U USB dongle | ✅ van |
| Antenna | ✅ van |
| **162 MHz SAW szűrő** | ⬜ **később** — a mérés szűrő nélkül is indulhat |
| **5V/3A táp** | ✅ van (a Pi 4 hivatalos tápegysége) |

**Az OS telepítve** (2026-11-22): a Raspberry Pi OS Lite (64-bit),
Debian trixie, a **2026-10-06** build. A kártyára a `cloud-init` írta be
a beállításokat:
- a hostname: **`bud01`**
- a felhasználó: **`miklos`** (a `sudo` csoportban, jelszó nélkül)
- az **SSH-kulcs** (a Mac kulcsa) → ssh-val belépek
- a **Wi-Fi**: `Pres-iot` (a hálózat a `network-config`-ban)
- a tűzfal: a 22 (SSH), a 8080 (a helyi web-térkép) és a 8100 (a helyi
  NMEA) nyitva a LAN-on

**A telepítő scriptek** a repóban (`scripts/ais-receiver/`):
`install_pi_os.sh` (az OS-telepítés), `make_cloudinit.sh` (a
cloud-init fájlok), `install_ais_receiver.sh` (az SDR), a mérés- és
elemzőscriptek.

**A tanulságok a telepítésből (a teljes lista a
`scripts/ais-receiver/PI-TELEPITES.md`-ben):**
- a hivatalos `.sha256` a **tömörített** képre vonatkozik (a `.img.xz`),
  nem a kitömörített `.img`-re
- a `sudo` a Macen **megoldja a macOS „removable volumes"
  engedélykérdését** is (az Imager CLI `sudo` alatt közvetlenül nyitja
  a lemezt)
- a cloud-init `network-config`-nek a **`network:`** gyökéren kell lennie,
  `renderer: NetworkManager`-rel és `regulatory-domain`-nel
- az **`ssh` fájl a boot partíción** kötelező (különben az `sshd` nem
  indul el)
- az SSH-kulcs a felhasználó **`users:` blokkjában** kell (nem top-level)
- a dongle a **kék USB 3.0 portban** (a fekete 2.0-ban `error -71`)
- az AIS-catcher v0.71-ben a `-D` paraméterei megváltoztak:
  `V ON MSGS ON` → **`state ON position ON static ON nmea ON`**,
  és a DB-sémát a **`create_sqlite.sql`** betöltéssel kell létrehozni

### 4.1b A mérés állapota (2026-11-22 21:35)

**A 30 napos mérés ELINDULT** a `bud01` telephelyen:

| | |
|---|---|
| A vevő | `ais-receiver.service` — **active**, boot után auto-indul |
| A nyers adat | `/var/lib/ais/ais.db` (SQLite), `RETENTION 35` nap |
| Az üzenetek | ~300 az első percekben (Msg 1/2/5/20/23) |
| A hajók | 91 különböző MMSI az első 10 percben |
| A PPM | **8** (a kalibráció 25 percet futott; a 13–15 az átmeneti szakasz volt) |
| A heti lehúzás | **a Pi bootja után** (`ExecStartPost`) + a biztonsági cron hétfő 04:17-kor → **a NAS közvetlenül** (`/opt/data/martin/work/ais-data/`) — **a Mac kimarad a láncból** (nem mindig van bekapcsolva; a NAS a Pi-ról 4,5 ms alatt elérhető) |
| A web-térkép | `http://192.168.0.2:8080` |

**A döntő teszt még hátra van:** a **belvízi FI 10** üzenetek (ezen múlik az
ENI, azaz a katalógus) — a lakástól 2 km-re nem várható. **A tetőn vagy a
Duna-parton kell megmérni** (a `ais-vevo-terv.md` 10.1: a tető 3–5 m-rel
magasabban +2–3 km rádióhorizont).

**A szűrő nélkül a mérés használható**, de a jel/zaj arány gyengébb —
a szűrő megvásárlása a mérés után dönthető el (a `docs/ais-vevo-terv.md`
szerint a szűrő a túlterhelést és a LO-szivárgást csökkenti).

### 4.1c Az első óra eredménye (2026-11-22 21:30)

**A vevő helye: 47,5755205 N, 19,046013 E** (a pesti felső városrész,
**a Dunától 2,88 km-re**).

| Metrika | Érték |
|---|---|
| Az üzenetek | **37 457** (egy óra alatt) |
| A csatornák | A: 12 031 + B: 7 862 — **mindkettő működik** |
| A PPM | −6,1 átlag |
| A jelerősség (stdout JSON) | −1,5 … −14,8 dB — **kiváló** |
| A hajók | **199** |
| **A magyar hajók** | **63** (21 771 üzenet), 2,8–14,7 km |
| A nemzetközi hajók | 11 (3 343 üzenet), 2,9–13,0 km |
| A Duna navigációs lámpái | **108 „belső" AIS-állomás** (1592–1728 km) |
| **A FI 10 üzenetek** | **767** — **az ENI-k elérhetők!** |
| **A földrajzi lefedettség** | **69,8%** a Duna-korridorban |

**A go/no-go kritérium** (a `docs/ais-vevo-terv.md` 5.3): a lefedettség
≥ 50% → **a saját vevőhálózat (F1, 3 site) azonnal építhető**. A mérés
**69,8%-ot** ad — **a küszöbön felül**.

**A látott hajók között:** `GONDOLA` (ENI 8601836 — az egyetlen, aminek
ENI-je van), `AQUINCUM`, `ATTILA`, `BAKONY`, `BOGDANY`, `BUDAPEST`,
`CITADELLA`, `DUNA` (98×24 m), `ESZTERGOM`, `EUROPA`, `GROF SZECHENYI`,
`ISTER`, `LAGYMANYOS`, `MILLENNIUM 2`, `PRIMUS`, `RAKOCZI`, `SIRONA`,
`VISEGRAD`, `WIKING`, `ZIN URU` — és a nemzetközi forgalom:
`DOUCE FRANCE` (francia), `KEPLER` + `RUBIKON23` (tankhajók),
`STADT WIEN` (osztrák), `VIKING AEGIR`/`VIKING BRAGI`/
`TRAVELMARVEL VEGA` (horvát-osztrák), `SLUIZER` (holland),
`HORISHNI PLAVNI` (ukrán), `RIVER DIVA` (luxemburgi).

**A tudatos döntés (2026-11-22): a jelerősség kimarad a DB-ből.**
A v0.71-es AIS-catcher a `-M TD` flaggal számolja a jelerősséget (a
stdout JSON-ban megvan), **de a DB-be nem írja** — a `DatabaseOutput`
a `TAG.level`-t a JSON-stream útvonalon nem kapja meg. A mérés szempontjából
ez nem kritikus: a go/no-go a lefedettségen alapul, a szűrő kiválasztása
a `msg/hajó` arányból dönt. A részletek a
`scripts/ais-receiver/PI-TELEPITES.md`-ben.

**Az elkészült telepítő- és mérőscriptek** (`scripts/ais-receiver/`):

| A fájl | A szerepe |
|---|---|
| `install_ais_receiver.sh` | a telepítés: az `rtl-sdr`, a DVB-T driver blacklista, az AIS-catcher build (forrásból, ARM64), a systemd unit |
| `start_measurement.sh` | a mérési üzemmód: a helyi SQLite kimenet + a heti lehúzás a NAS-ra |
| `analyze_measurement.py` | a go/no-go metrikák (a mérés elemzése) |
| `inspect_schema.py` | a SQLite séma felismerése (az oszlopnevek pontosításához) |
| `PI-TELEPITES.md` | **a lépésről lépésre útmutató** — a döntő pontokkal |

**A 8 lépés (a `PI-TELEPITES.md` szerint):** OS+hálózat → `rtl-sdr` →
a driver blacklista → **a dongle felismerése** → **a PPM-kalibráció** →
**a helyi AIS-teszt** → a mérés indítása → **a belvízi FI 10 teszt**
(a tetőn/vízparton).

**A négy döntő pont:** a dongle látszik-e · a PPM kalibrálva ·
jön-e jel · **jön-e belvízi FI 10** (ezen múlik az ENI, azaz a
katalógus).

**A méréshez nem kell szerver** — a Pi a helyi SQLite-ba ír, és a
heti lehúzás után offline feldolgozzuk. A központi ingest (MQTT +
a `04` – parser terv) **a 30 nap után** indul.

> **Az AIS-catcher v0.71-ben a `-D` kimenet ÚJRAÍRÓDOTT** — a
> `ingest-terv.md` 3.2-es fejezetének flag-formátuma (`station_id 1
> position on static on nmea on unique on position_interval 60
> retention 14`) **elavult**. Az új forma: `-D sqlite:fájl STATION_ID 1
> V ON MSGS ON NMEA ON VP ON VS ON RETENTION 35`. **Az
> `ingest-terv.md`-t javítani kell** a mérés után.

**Az elhelyezés ellenőrzése helyszínen:** ha a lakás a **budai
oldalon** van, a **Gellért-hegy (210 m)** és a nyugati budai dombok
takarhatják a kilátást — ez az első dolog, amit telepítéskor nézni kell.

### 4.3 A 28 lépcs (a `docs/pi-eloallitas.md` 4. fejezete)

| # | Lépés | Hol |
|---|---|---|
| 1–5 | a Raspberry Pi OS Lite, a hostname, az SSH, a statikus IP, az NTP | §4.1 |
| 6–9 | a `rtl-sdr` telepítése, a **DVB-T driver letiltása** (`blacklist dvb_usb_rtl28xxu` → reboot), a dongle felismerése, a **ppm-kalibráció** (`rtl_test -p`, 10 perc) | §4.2 |
| 10–13 | az **AIS-catcher** telepítése (bináris, systemd unit), a konfiguráció (a ppm, a JSON kimenet, a stat port, a gnz), a **belvízi FI 10 ellenőrzése** (ezen múlik az ENI!), a heartbeat | §4.3 |
| 14–20 | az **ADS-B lánc** (a dump1090-fa, a fr24feed, a FR24) — **külön dongle**, külön antenna (a 1090 MHz szűrő kötelező!) | §4.4 |
| 21–28 | a chrony, a GPS+PPS (opcionális), a **UPS**, a hűtés, az **USB-SSD** (a kártya kopása a leggyakoribb hibaforrás), a `ufw` biztonság, a monitorozás | §4.5 |

**A 12. lépés a legfontosabb a projekt szempontjából:** ha a
dekóder nem adja az Inland AIS (FI 10) üzeneteket, **nincs ENI** —
és az ENI nélkül nincs katalógus (a README 3.3/B: az ENI a
Duna-katalógus elsődleges azonosítója).

### 4.4 A mérési protokoll (a `ais-vevo-terv.md` 5. fejezete)

**30 nap, 1 próbavevő, a legforgalmasabb szakaszon.** A go/no-go
metrikák:

| # | Metrika | Küszöb |
|---|---|---|
| 1 | az üzenetek száma | a README 5. fejezetének becslését igazolja-e? |
| 2 | az üzenettípusok megoszlása | a Msg 1/3/5/18/24 + FI 10 aránya |
| 3 | a hibás üzenetek aránya | **< 0,1%** (a parser megbízhatósága) |
| 4 | a dekódolható statikus adatok aránya | hány hajóból van ENI/név/méret |
| 5 | a pozíciók minősége | a `river_km` a folyó-korridoron belül van-e? |
| 6 | a ghost hajók aránya | a négy szűrőszabály után hány marad |

**A mérés kimenete:** az 50 reprezentatív üzenet → a
`db/fixtures/ais/` — ezek a parser **elfogadási tesztjei** (a 04-es
terv §8.3).

### 4.5 A mérés utáni teendők (a sorban)

| # | Teendő | A terv |
|---|---|---|
| 1 | a **fixture-ök** a repóba (50 üzenet) | 04 – AIS-parser |
| 2 | a **saját dekóder** megírása és a tesztelése (a `pyais`-szal és az `aiscat`-tel referencia-implementációként) | 04 – AIS-parser |
| 3 | a **Q8 futtatott összehasonlítás** (a `pyais` vs. `aiscat` vs. saját) | 01 – terv §5.3 |
| 4 | a **szerveroldali ingest** (az MQTT → a dekódolás → a Postgres) | 04 – terv |
| 5 | a **03-as API-terv** javításai a swarm review alapján | 03 – API |
| 6 | a **07–09** terv (a CI/CD, a teszt-stratégia, az üzemeltetés) | — |

---

## 5. Hol van minden (a munkaterületek)

| Hol | Mi | Hogyan érem el |
|---|---|---|
| **A fejlesztői munkakönyvtár** | `/opt/data/martin/work/vt-clone/` — **a kód és a tervek élő változata** | a NAS konténerben |
| **A tervek forrása** | `/opt/data/martin/work/duna-plan/` — a tervek master másolata | a `vt-clone/docs/megvalosulas/` ide szinkronizál |
| **A GitHub** | `VorosEgyes/vessel-tracker` — **a kanonikus forrás** | a `main` branch védett (a force-push tiltva) |
| **A push-segéd** | `/opt/data/martin/work/gh_commit.py` — **a GitHub API-val pushol** | a fine-grained PAT-tal (a `.git-credentials`-ből) |
| **A Pi vevő** | `bud01` (`192.168.1.172`) — a fizikai AIS-vevő | a NAS-ról a `mac_to_pi_ed25519` kulccsal |
| **A NAS fogadó** | `/opt/data/martin/work/ais-data/` — a heti AIS-adatbázisok | a fogadó script a `command=` korlátozással |
| **A DDL-validáló** | a `pgserver` (a `pgdata` mappában) — az élő PostgreSQL | a `just ddl-validate` |
| **A swarm board** | `/opt/data/kanban/boards/review-swarm/` — a review-k | a `hermes kanban` parancs |

### 5.1 Korábbi NAS-os kód → GitHub munkafolyamat

Ez a rész a korábbi NAS-os munkakörnyezetet írja le, nem a jelenlegi
Mac-munkafát. A jelenlegi checkout a `/Users/modmj/dev/vessel-tracker`;
a helyi változtatások a szokásos `git status` paranccsal láthatók.

**A Mac offline** (a `192.168.0.135` és a `192.168.1.172` nem
elérhető a NAS-ról) → **a teljes fejlesztés a NAS konténerben
folyik** → **a push a GitHub API-n keresztül** (a `gh_commit.py`),
**nem** a `git`-en keresztül.

```bash
# a NAS-on, a vt-clone-ból
cd /opt/data/martin/work/vt-clone
MSG=$(cat /opt/data/martin/work/_commit_msgNN.txt)
python3 /opt/data/martin/work/gh_commit.py "$MSG" --root /opt/data/martin/work/vt-clone \
  <fájl1> <fájl2> ...
```

**A `gh_commit.py` a GitHub API `git/trees` + `git/commits` +
`git/refs` végpontjait használja** → **a `base_tree` a távoli HEAD-ből
származik** → **a lokális git repo nincs szinkronban** → **a `git
status` itt nem a valós diffet mutatja!**

**A valós diff** (a távoli HEAD fa vs. a munkafa, a `.gitignore`-ot
betartva) → **a `gh_commit.py` előtt** → **ez a jóváhagyás alapja.**

**A PAT:** a fine-grained PAT a `VorosEgyes/*` repókra korlátozott
(code/contents/issues/pull_requests) → **a workflow YAML-ok push-a
NEM megy** → **azokat Alfred pusholja** (a klasszikus workflow PAT-tal).

> **A `git` a lokális repóban a formázás/teszt futtatáshoz kell**
> (a `ruff`, a `pytest`, a `just`) — **de a PUSH-hoz a
> `gh_commit.py` a kanonikus út.**

---

## 6. A döntési nyitott pontok

| # | Kérdés | Ki dönt | Hol |
|---|---|---|---|
| 1 | A GitHub-repo létrejött és a `main` védett | ✅ **lezárva** (2026-11-19) | — |
| 2 | A projekt neve `vessel-tracker` (magyarul: Hajókövető — Duna és Balaton) | ✅ **lezárva** | — |
| 2b | **A `slug` a hajónévből legyen vagy az MMSI-ből?** (a `02` §8.1a: az alkalmazás generálja) | ✅ **lezárva** — **a név az elsőbbség, az MMSI a tartalék** (a hajót átnevezik, a MMSI nem) | a `duna/domain/slug.py` |
| 2c | **A `sort_name`-t a DB trigger vagy az alkalmazás töltse be?** | ✅ **lezárva** — **az alkalmazás** (a `02` §8.1a: "a `sort_name`-t az ingest tölti be") → **a trigger csak az üres `sort_name`-t állítja** | a `02` v1.12 |
| 2d | **A `verification` szűrő a tárolt vagy a számított értékre épüljön?** | ✅ **lezárva** — **a szűrő a TÁROLT értékre** (indexelt), **a megjelenített érték a SZÁMÍTOTT** (a `verification_source` jelzi az eltérést) | a `03` §3.1 |
| 2e | **A `datamodel-code-generator` bevezetése** (a `03` §5.1a: a modellek generáltak) — **egyelőre kézzel vannak, a `just models-check` ellenőrzi a driftet** | **Miklós** (a generátor a `datamodel-code-generator` dev-függőség) | a `03` §5.1a |
| 3 | A `position` TTL 90 nap, de a README 5.4 „60 nap"-ot ír | **Miklós** | a 02-es terv §14 Q9 |
| 4 | A `water_level` TTL 90 nap (a README-ből nem vezethető le) | **Miklós** | a 02-es terv §14 Q10 |
| 5 | A `release-terv` 3.3 mondatának pontosítása (a `position` R1/R2 helye) | **Miklós** | a 01-es terv §12 |
| 6 | Az R1 sprint-szám (4 vagy 5) | **Miklós** | a `release-terv` 3.7 |
| 7 | A projekt saját licence (Q12, a GPL-kompatibilitás) | **Miklós** | a 01-es terv §5.3 |
| 8 | A **hardver-beszerzés** (a fenti táblázat) | **Miklós** | a mostani munkaterület |

---

## 7. A terv-sorozat és a megépítés kapcsolata

```
┌─ TERVEZÉS — a sorozat TELJES (01–09) ─────────────────────┐
│ 01 stack  →  02 séma (v1.12, VALIDÁLVA)  →  03 API (v0.7)  │
│                                       ↓                    │
│ 04 parser (v1.0)  05 frontend  06 szerkesztő  07 CI (v0.2) │
│ 08 teszt (v0.2)  09 üzemeltetés                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─ ALKALMAZÁS ───────────────────────────────────────────────┐
│ séma + migráció; CI-konfiguráció; service réteg             │
│ hajós és referencia API; generált TypeScript-kliens          │
│ részleges frontend; szerkesztő és deploy hátravan           │
│ PostgreSQL-tesztek és teljes kapu: újra futtatandó          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─ A MÉRÉS (a másik munkaág, párhuzamosan) ──────────────────┐
│ korábbi mérés: 2026-11-22-től; jelenleg nem ellenőrzött     │
│                              ↓                               │
│              a saját parser → az ingest → a statikus adat    │
└─────────────────────────────────────────────────────────────┘
```

**A két munkaág FÜGGETLEN:** a Pi + rádió **nem vár** a sémától
vagy az API-tól; **az alkalmazás rétegei nem várnak** a mérésre
(kivéve az `ingest`-et, a `04` – parser-terv szerint).

**A mérésből jövő fixture-ök** (az AIS-tesztadatok) **az `ingest`
réteghez kell** → **a mérés lezárása után** (2026-12-22).

**A tervek rendelkezésre állnak**, de nem minden tervezett funkció
készült el; az aktuális implementációt a 2b. fejezet írja le.

### 7.1 A következő lépések (2026-11-26)

**Két párhuzamos munkaág:** **a mérés** (a hardver, határidő: 2026-12-22)
és **az alkalmazás rétegei** (a `03` alapján).

#### A) Az alkalmazás rétegei (a `03` szerint)

| # | A lépés | A méret | A függőség |
|---|---|---|---|
| A1 | **a referenciatáblák végpontjai** (a `03` §3.3): `/api/v1/ports`, `/locks`, `/waterways`, `/river-sections`, `/basins`, `/vessel-types`, `/operators`, `/routes`, `/cargo-types` | 9 lista + 2 adatlap | **elkészült** — a `reference.py` router |
| A2 | **a `vessel_service` write-oldalának használatba vétele** (a `sort_name` + a `slug` betöltése) | kicsi | az A1 után (a szerkesztői felülethez kell) |
| A3 | **az `ingest` réteg** (a `04`): a parser → a `position`/`vessel_static` írása | nagy | **a mérésből jövő fixture-ök** |
| A4 | **a `apps/web`** (a `05`): az Astro frontend, a katalógusoldal | nagy | **első változat:** statikus katalógus, élő API-s keresés, rendezés és lapozás; az adatlap és a rebuild-hook még hátravan |
| A5 | **a szerkesztői felület** (a `06`): az `/api/admin/v1/` | nagy | az A2 + az A4 után |
| A6 | **a `packages/api-client`** (a generált TS kliens az OpenAPI-ból) | kicsi | **elkészült** — generálás, típusellenőrzés és CI driftkapu |

**Következő javasolt sorrend:** a PostgreSQL-es integrációs tesztek és
teljes minőségi kapu futtatása → a frontend hajóadatlapja és a build-hook →
A2 és A5. Az A3 a mérési fixture-ökkel párhuzamosan folytatható.

#### B) A mérés és a hardver

| # | A lépés | A mikor |
|---|---|---|
| B1 | a mérés és a heti lehúzás aktuális állapotának ellenőrzése | nyitott |
| B2 | **a TCXO-s dongle** (a PPM ≤ 2) — a mérés lezárása után | a mérés után |
| B3 | **a 162 MHz SAW szűrő** — a döntés a mérés végén | a mérés után |
| B4 | **a 2. site a szűvízen** (az ENI-arány 0,4% → kell) | a mérés után |

#### C) A tervezési oldal (a háttérben)

| # | A lépés | A mikor |
|---|---|---|
| C1 | a tervek további összehangolása az implementációval | folyamatos |
| C2 | **a `release-terv` frissítése** (a kész R1-es végpontok listájával) | az A1 után |

#### D) A nyitott kérdések (Miklós döntése)

| A kérdés | A határ |
|---|---|
| a `position` TTL 90 nap, de a README 5.4 „60 nap"-ot ír | a 02-es terv §14 Q9 |
| a `water_level` TTL 90 nap | a 02-es terv §14 Q10 |
| a `release-terv` 3.3 mondatának pontosítása (a `position` R1/R2 helye) | a 01-es terv §12 |
| az R1 sprint-szám (4 vagy 5) | a `release-terv` 3.7 |
| a projekt saját licence (Q12) | a 01-es terv §5.3 |

### 7.2 A mérésből jövő döntések

| A döntés | A határ | A jelenlegi állapot |
|---|---|---|
| **a go/no-go** (a lefedettség) | ≥ 50% | **69,8%** ✅ |
| **a szűvíz helyszín** (az ENI-k) | a szűkvízi szakaszokon kell mérni | **a városi helyen az ENI-arány 0,5%** → **egy 2. site kell** |
| **a TCXO-s dongle** | a PPM ≤ 2 | **a mérésben PPM 7–8** (a TCXO nélküli dongle) |
| **a 162 MHz szűrő** | a túlterhelés csökkentésére | **a mérés szűrő nélkül is fut** → a döntés a mérés végén |

> **A Q7 (melyik telephelyen mérünk) a legfontosabb nyitott kérdés** —
> a `04` – parser-terv K-4 findingje és a `08` – teszt-stratégia Q5-e.

---

*Ez a dokumentum a `docs/megvalosulas/ALLAPOT.md` útvonalon van a repóban.*
