# Implementációs tervek – Vessel Tracker (Duna és Balaton)

Ez a mappa a **megvalósítási tervek** sorozata: a [`../README.md`](../README.md)
(adatbázis-terv), a [`../docs/funkcio-leiras.md`](../docs/funkcio-leiras.md)
(funkcióleírás) és a [`../docs/release-terv.md`](../docs/release-terv.md)
(release-terv) **hogyan** oldását adják.

> **A funkciók → tervek megfeleltetés:**
> [`../docs/funkcio-elemzes.md`](../docs/funkcio-elemzes.md) —
> **minden F-kód (103 funkció + 20 NFR) felsorolva, ahol van a
> tervben és mi a státusza.** **A scope ellenőrzéséhez ez a
> dokumentum** (a `03`–`09` tervek nem hivatkoznak minden F-kódra).

| # | Terv | Tartalom | Státusz |
|---|---|---|---|
| 01 | [stack és projektstruktúra](megvalosulas-01-stack-es-struktura.md) | Technológiai stack, monorepo-struktúra, környezetek, az AIS-adatút, az R1-scope | **v1.4** — swarm review 2 körön átesett, a 2. kör 17 új findingje javítva; **+ a `just check` pontosítása** (a `07` §3.1 definiálja) |
| 02 | [adatbázis-DDL v1.1 + migrációk](megvalosulas-02-adatbazis-ddl.md) | A teljes R1-séma (71 tábla), a partíciós terv, az indexek, a nézetek, a trigger-ek, a DB-szerepkörök, a mentés és a monitorozás | **v1.6 — futtatva és tesztelve** valódi PostgreSQL 17-en (**157 index, 124 FK, 372 CHECK, 85 trigger; 17/17 funkcionális teszt zöld**); 1. körű swarm review: **113 finding**, **10 blokkoló** — mind javítva és újra validálva; **a teljes referenciaadat-seed** (89 hajótípus a magyar nevekkel, a `language`, a `country`, a `waterway`, a `river_section`, a `basin`, a `cargo_type`, az `operator` — a `bud01` mérésből); **a `position.msg_type`/`msg_subtype` és a `nav_status` CHECK** (a `04` – parser-terv 1. körű swarm review-jának 64 findingje); **+ az `admin_api` szűk szerepkör** (a `06` §2.1a — a `public_api` nem olvashatja az `app_user`-t); **+ a `destination`/`destination_eta` oszlop** (a bori B-C-3); **+ a `position` TTL-job** (a blackboard X-3) |
| 03 | [API-specifikáció](megvalosulas-03-api-specifikacio.md) | A belső R1 API és az R5 B2B API határvonala, a hibakódok, a lokalizáció, a DB-szerepkör, a kivétel-kezelés | **v0.4** — 1. körű swarm review: **96 finding** (3 reviewer: `bori` 34, `preshaz` 24, `prof` 27 + a szintézis) — **mind javítva**; a `type` URI domainfüggetlen URN, a `moving` szűrő R1-ben meghatározva, a `meta.total` specifikálva, a `Page[T]`/`Data[T]` burkolók; a pinelt séma: a `02` **v1.6**; **+ a `?lang=` prioritás** (a `03` §6.1: a `?lang=` → a `session` → az `Accept-Language` → `hu`); **+ az ENI-korlát kommunikációja** (a `meta.hint`); **+ a `destination` a `VesselDetail`-ben** |
| 04 | [AIS-parser specifikáció](megvalosulas-04-ais-parser.md) | A NMEA frame-validáció, a 6 bites dekódolás, az üzenettípus-dispatch, a normalizált rekord (a `02` és a `04` közötti közös szerződés), a dedup, a mérési protokoll | **v1.0 — a mérés után**; 1. körű swarm review: **64 finding** (3 reviewer: `prof` 27 · `bori` 18 · `preshaz` 19), a verifier audit szerint **61 valós, 11 blokkoló** — **mind javítva**; a terv **a `bud01` mérés valós adataihoz** igazítva (a nem hajó üzenettípusok = a forgalom 27,3%-a, a SQLite architektúra, a mért ~900 000 üzenet/nap, a nem mérhető hibás arány) |
| 05 | [frontend-arkitektúra](megvalosulas-05-frontend-arkitektura.md) | Az Astro SSR, az i18n routing (a F-INTL-01…08), a SEO (a `hreflang`, a JSON-LD, a sitemap), a komponensmodell, a hajóadatlap blokkjai | **v0.3** — a 05–09-es swarm review javításai (a nyelvválasztó süti/prefix, a rendezés, a bizonyossági badge, a `river_km` 3 forrás, a súgó) **+ a 2. kör: a `output: 'static'` + a rebuild-mechanizmus** (a C-9 blokkoló) |
| 06 | [szerkesztői felület](megvalosulas-06-szerkesztoi-felulet.md) | A session-alapú hitelesítés, a `/api/admin/v1/` végpontok, a mezőnkénti eredet szerkesztése, a konfliktuskezelés (a F-ADM-09), az üzemeltetői önbevallás (a F-ADM-08), a tömeges import (a F-ADM-07), a fordítási hiánylista | **v0.2** — a 05–09-es swarm review javításai (a `admin_api` DB-szerepkör, az egy-session korlát, az AIS-import, a célállomás mező, az import limit) |
| 07 | [CI/CD és környezetek](megvalosulas-07-ci-cd-es-kornyezetek.md) | A pipeline (a `ci.yml`/`build.yml`/a deploy-workflow-ok), a build (a `justfile`, a Docker image-ek), a környezet-változók, a migrációk, a deploy és a rollback, a titkok, a smoke teszt | **v0.3** — a 05–09-es swarm review javításai (a `justfile` a szintenkénti célokkal és a `check`/`check-release` kapukkal, a coverage-küszöb a `just test`-ben, a `pg_stat_statements` a Dockerfile-ban, a host cron telepítése a deployban) **+ a 2. kör: a `ddl-diff` séma-drift lépés, a heti cron-ütem, a Telegram-titok, a branch protection javítása** |
| 08 | [teszt-stratégia](megvalosulas-08-teszt-strategia.md) | A teszt-piramis (7 szint), a 20 NFR → a mérőszám, a szintenkénti tesztek, a mérésből jövő fixture-ök, a kilépési feltételek | **v0.2** — a 05–09-es swarm review javításai (a fixture-méretkorlát, a replay a NAS-ról, a szintenkénti `just` célok, a flake-gate) |
| 09 | [üzemeltetés és observability](megvalosulas-09-uzemeltetés-es-observability.md) | A mentés és a visszaállítás (a PITR, a heti restore-drill), a monitorozás, a **watchdog** (a riasztás), a naplózás, a vevőhálózat üzemeltetése, az incidenskezelés | **v0.3** — a 05–09-es swarm review javításai (a lehúzás-határ 8 → **4 nap**, a környezetfüggő heartbeat-határ, a restore-drill a **stagingben**, a 3 site kapacitás, a havi partícióméret, a `COPY` batchelés) **+ a 2. kör: a PPM 7, a watchdog mind a 10 riasztása, a `job_run`-ba író drill, a katalógusméret-metrika** |

## Olvasási sorrend

1. **01** (ez a sorozat alapja) → 02 → 03 → 05 → 06
2. **04** párhuzamosan a 02-vel (a mérési adatokra vár — az R1-0 alatt készülnek)
3. **07** a 01-re épül (a v0.1 draft kész), **08** és **09** a végső sprintre

## A terv-sorozat és a release-terv kapcsolata

A 9 terv **nem egyenlő a `release-terv` 3.7 sprintjeivel** — a tervek a
teljes R1-et fedik le (a 3.7 sprintjei + az R1-0 előkészítés). Az
01-es terv §3.4 tartalmazza a pontos leképezést.

## Státuszjelölés

- **v1.x** — swarm review-n átesett, a blokkolók javítva
- **v0.x** — draft, review alatt vagy utána
- **várakozik** — az előfeltételére vár

## A projekt

**GitHub:** https://github.com/VorosEgyes/vessel-tracker
(publikus, `main` branch védett — force push tilos).

**A jelenlegi állapot:** [`ALLAPOT.md`](ALLAPOT.md) — mi kész, mi fut,
mi a következő lépés (a mostani munkaterület: a Pi + rádió
megépítése).

## A 02-es terv validációja

A 02-es terv DDL-je **valódi PostgreSQL-en futott le** (nem csak szintaktikailag
ellenőrzött): a `db/tools/validate_ddl.py` a terv markdown-ból kicsomagolja a
DDL-t és lefuttatja egy élő példányon, majd funkcionális füstöt hajt végre
(partial unique index, CHECK constraint, upsert, partíció-TTL, audit-trigger,
mezőnkénti konfliktus, azonosító-szinkron, downgrade).

**A validáló script a `--plan` kapcsolóval bármely tervfájlt validálhat**
(nem csak a live verziót) — a swarm review ezt a hiányt mutatta ki
(V-N-1: a script a live fájlt olvasta, nem az auditáltat).

A terv §12 tartalmazza a futtatott eredményeket, a validáció során talált
hibákat és az **1. körű swarm review 113 findingjének** javítását.

**A legutóbbi validáció (2026-11-22, a v1.4 sémával — a `home_*`
oszlopokkal és a teljes referenciaadat-seeddel):**

| | |
|---|---|
| Táblák | **71** |
| Indexek | **157** |
| FK constraint | **124** |
| CHECK constraint | **372** |
| Particionált tábla | **3** |
| Trigger (definíció / information_schema) | 28 / **85** |
| **A funkcionális füstteszt** | **17/17 zöld** |
| **A referenciaadatok betöltve** | 3 nyelv, **89 hajótípus** (89 magyar névvel), 24 ország, 11 folyószakasz, 4 medence, 8 teherfajta, 5 üzemeltető, 5 forrás |

> **A validáló script önkállóan reprodukálható:**
> `db/tools/validate_ddl.py --no-gis --keep` — a postgres-t a
> `pgserver` indítja el (a korábbi változat egy külön indított
> szerverre számított → a „connection to server failed" hibával leállt).

### A 03-as terv (v0.3) — a 96 finding

| A reviewer | A findingek | A fő javítások |
|---|---|---|
| `bori` | 34 | a fallback-lánc, a `status`/`moving` szerződés, a `VesselListItem`, a kötelező `area`, a konfliktuskezelés |
| `preshaz` | 24 | a DB-szerepkörök, a `public_api` gronzálás, az observability, a health/readiness |
| `prof` | 27 | a `type` URI → URN, a `from_attributes`, a `moving` definíciója, a `meta.total`, a `Page[T]`/`Data[T]`, a `Decimal` → `string`, az `area` kötelező a `/search`-nél, a `sort=operator` → `operator_id` |
| **A szintézis** | 11 | a `?section=`/`?basin=` adatforrása (`home_*` oszlopok a `02` v1.3-ban) |

**Mind a 96 finding be van írva** — a `02` **v1.3** és a `03` **v0.3**
újra validálva.

---

## A sorozat állapota (2026-11-23)

| A terv | A verzió | A review |
|---|---|---|
| 01 – stack és struktúra | **v1.4** | ✅ 2 kör, 17 finding |
| 02 – adatbázis-DDL | **v1.6** | ✅ 113 finding + a 05–09-es kör, 17/17 validálva |
| 03 – API-specifikáció | **v0.4** | ✅ 96 finding + a 05–09-es kör |
| 04 – AIS-parser | **v1.0** | ✅ 64 finding (a mérés alapján) |
| 05 – frontend-arkitektúra | **v0.2** | ✅ a 05–09-es kör (31 prof / 19 bori / 17 preshaz finding) |
| 06 – szerkesztői felület | **v0.2** | ✅ ugyanaz |
| 07 – CI/CD és környezetek | **v0.2** | ✅ ugyanaz |
| 08 – teszt-stratégia | **v0.2** | ✅ ugyanaz |
| 09 – üzemeltetés és observability | **v0.2** | ✅ ugyanaz |

**A sorozat teljes (01–09) és mindegyik terv swarm review-zott.**

### A 05–09-es swarm review (2026-11-23) — 67 finding

| A reviewer | A findingek | A fő témájuk |
|---|---|---|
| `prof` | **31** (7 C · 11 H · 10 M · 3 L) | a technikai helyesség és **a tervek közötti konzisztencia** (a `?lang=` prioritás, a `just check`, a DB-szerepkör, a heartbeat, a fixture-ök) |
| `bori` | **19** (5 C · 7 H · 5 M · 2 L) | a felhasználói érték (az ENI-korlát, a „hol van", a célállomás, az AIS-import, a bizonyosság) |
| `preshaz` | **17** (5 C · 7 H · 4 M · 1 L) | az üzemeltethetőség (a lehúzás-határ, a 3 site, a drill, a cron, a partícióméret) |
| **a verifier** | audit | **66/67 igazolt**, 2 hamis (a worker javította), 8 duplikáció összevontva |

**A javítások a tervekben:** a `03` v0.4 · a `05` v0.3 · a `06` v0.2 ·
a `07` v0.3 · a `08` v0.2 · a `09` v0.3 · a `02` v1.6 · a `01` v1.4.

### A 2. kör (a worker-ek újraellenőrzése) — 3 új BLOKKOLÓ

**A worker-ek a saját kimenetüket újraellenőrizték**, és **három
blokkolót találtak, amit az első körben egyik sem látott**:

| A finding | Mi a hiba | A javítás |
|---|---|---|
| **C-9 / X-1** | a `05` §1 **kizárta** az `output: 'static'`-ot → **az `01` §3.2.1 rebuild-mechanizmusa (a hook, a `published` gating, a build-idő) levegőben maradt**, és a `07` §3.3 **egy nem létező kimenetre** épült | a `05` §1 → **`output: 'static'` + a Node adapter**; a §5.2 → **`getStaticPaths`**; a rebuild-mechanizmus táblázata |
| **C-8** | a `09` §4.2 a PPM-et **−6,1**-nek adta, **a mérési adat 7** → **a mérési adat ellentmondása** (és a `09` §9.2 maga 7-et írt) | a cella → **7**; a határ → `\|ppm − 7\| > 8` (a **drift** nagyságára, nem az abszolút értékre) |
| **H-12** | a `07` §8.1-ben **nem volt** a `db/ddl/` generálás + `git diff --exit-code`, amit a `02` §11 előír → **a séma-drift csendben benne maradt** | a **10b. lépés** (`just ddl-diff`) + a `justfile`-beli `ddl-diff` cél |

**További 2. körös javítások:** a `09` §5.1 watchdog SQL (`WHERE active` →
`WHERE status = 'active'` + a `NULL` ág) · a watchdog **mind a 10
riasztása** · a drill a production `job_run`-ba ír · a `07` §2.3
Telegram-titkok · a heti cron-ütem · a `02` §8.4 `position` TTL-job ·
a `02` `destination` oszlop + a `03` `VesselDetail` · a branch protection
javítása (a nem létező `ci / ddl-validate` job) · a `09` §8.2 a 3 site
adataival.

**A legfontosabb javítások:**

| A finding | A javítás |
|---|---|
| a `03` §6.1-ben a `?lang=` **nem** volt az első (a H-4 javítása kimaradt) | a sorrend: `?lang=` → `session` (adminon) → `Accept-Language` → `hu` |
| a `05` §3.2 **a sütivel felülírta** az útvonal-prefixet | a prefix erősebb a sütinél |
| a `just check` **nem létezett** (a `08` §6.1 erre épült) | a `07` §3.1 definiálja a `check`/`check-release` kapukat |
| a `06` nem mondta meg a DB-szerepkört | a **`admin_api`** szűk szerepkör (a `02` v1.6) |
| a 30 perces heartbeat **hetente frissülő** `last_seen_at`-tel | a határ **környezetfüggő**: R1-ben 10 nap, R2-ben 30 perc |
| a lehúzás-kimaradás **8 napos határa** sosem lépett túl | **4 nap** (a heti ritmus + 3 nap tartalék) |
| a restore-drill a **production** lemezén futott | a **stagingben** (+ a `restore_test` DB törlése) |
| a teljes replay **a repóban** lévő 3 GB-os `.db`-t hivatkozott | a **NAS-ról** jön, a repóban méretkorlát (100 KB / 5 MB) |
