# Implementációs tervek – Vessel Tracker (Duna és Balaton)

Ez a mappa a **megvalósítási tervek** sorozata: a [`../README.md`](../README.md)
(adatbázis-terv), a [`../docs/funkcio-leiras.md`](../docs/funkcio-leiras.md)
(funkcióleírás) és a [`../docs/release-terv.md`](../docs/release-terv.md)
(release-terv) **hogyan** oldását adják.

| # | Terv | Tartalom | Státusz |
|---|---|---|---|
| 01 | [stack és projektstruktúra](megvalosulas-01-stack-es-struktura.md) | Technológiai stack, monorepo-struktúra, környezetek, az AIS-adatút, az R1-scope | **v1.3** — swarm review 2 körön átesett, a 2. kör 17 új findingje javítva |
| 02 | [adatbázis-DDL v1.1 + migrációk](megvalosulas-02-adatbazis-ddl.md) | A teljes R1-séma (71 tábla), a partíciós terv, az indexek, a nézetek, a trigger-ek, a DB-szerepkörök, a mentés és a monitorozás | **v1.4 — futtatva és tesztelve** valódi PostgreSQL 17-en (**157 index, 124 FK, 372 CHECK, 85 trigger; 17/17 funkcionális teszt zöld**); 1. körű swarm review: **113 finding**, **10 blokkoló** — mind javítva és újra validálva; **a `home_river_section_id` + `home_basin_id` oszlopokkal** (a `?section=`/`?basin=` katalógus-szűrő adatforrása — a `03` prof review C-1 findingje); **a teljes referenciaadat-seeddel** (89 hajótípus a magyar nevekkel, a `language`, a `country`, a `waterway`, a `river_section`, a `basin`, a `cargo_type`, az `operator` — a `bud01` mérésből) |
| 03 | [API-specifikáció](megvalosulas-03-api-specifikacio.md) | A belső R1 API és az R5 B2B API határvonala, a hibakódok, a lokalizáció, a DB-szerepkör, a kivétel-kezelés | **v0.3** — 1. körű swarm review: **96 finding** (3 reviewer: `bori` 34, `preshaz` 24, `prof` 27 + a szintézis) — **mind javítva**; a `type` URI domainfüggetlen URN, a `moving` szűrő R1-ben meghatározva, a `meta.total` specifikálva, a `Page[T]`/`Data[T]` burkolók; a pinelt séma: a `02` **v1.3** |
| 04 | [AIS-parser specifikáció](megvalosulas-04-ais-parser.md) | A NMEA frame-validáció, a 6 bites dekódolás, az üzenettípus-dispatch, a normalizált rekord (a `02` és a `04` közötti közös szerződés), a dedup, a mérési protokoll | **v0.1 — draft** |
| 05 | [frontend-arkitektúra](megvalosulas-05-frontend-arkitektura.md) | Az Astro SSR, az i18n routing (a F-INTL-01…08), a SEO (a `hreflang`, a JSON-LD, a sitemap), a komponensmodell, a hajóadatlap blokkjai | **v0.1 — draft** |
| 06 | [szerkesztői felület](megvalosulas-06-szerkesztoi-felulet.md) | A session-alapú hitelesítés, a `/api/admin/v1/` végpontok, a mezőnkénti eredet szerkesztése, a konfliktuskezelés (a F-ADM-09), az üzemeltetői önbevallás (a F-ADM-08), a tömeges import (a F-ADM-07), a fordítási hiánylista | **v0.1 — draft** |
| 07 | CI/CD és környezetek | A pipeline, a deploy, a környezet-változók | **nincs meg** |
| 08 | teszt-stratégia | A teszt-piramis, a kilépési feltételek mechanizmusa | **nincs meg** |
| 09 | üzemeltetés és observability | A mentés, a monitor, a naplózás | **nincs meg** |

## Olvasási sorrend

1. **01** (ez a sorozat alapja) → 02 → 03 → 05 → 06
2. **04** párhuzamosan a 02-vel (a mérési adatokra vár — az R1-0 alatt készülnek)
3. **07** a 01-re épül, **08** és **09** a végső sprintre

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
