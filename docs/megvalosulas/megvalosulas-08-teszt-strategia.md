# Implementációs terv – 08: teszt-stratégia

**Verzió:** 0.1 (terv-draft, swarm review előtt)
**Dátum:** 2026-11-23
**Kapcsolódó dokumentumok:**
[`../README.md`](../README.md) (adatbázis-terv) ·
[`megvalosulas-01-stack-es-struktura.md`](megvalosulas-01-stack-es-struktura.md) (a stack, a struktúra) ·
[`megvalosulas-02-adatbazis-ddl.md`](megvalosulas-02-adatbazis-ddl.md) (a séma, a constraint-ek) ·
[`megvalosulas-03-api-specifikacio.md`](megvalosulas-03-api-specifikacio.md) (az API-szerződés) ·
[`megvalosulas-04-ais-parser.md`](megvalosulas-04-ais-parser.md) (a parser, az elfogadási tesztje) ·
[`megvalosulas-05-frontend-arkitektura.md`](megvalosulas-05-frontend-arkitektura.md) (a frontend) ·
[`megvalosulas-06-szerkesztoi-felulet.md`](megvalosulas-06-szerkesztoi-felulet.md) (a szerkesztői felület) ·
[`megvalosulas-07-ci-cd-es-kornyezetek.md`](megvalosulas-07-ci-cd-es-kornyezetek.md) (a CI, a pipeline) ·
[`../funkcio-leiras.md`](../funkcio-leiras.md) (a 20 NFR) ·
[`../release-terv.md`](../release-terv.md) (a kiadási folyamat, a release-mátrix) ·
[`../ingest-terv.md`](../ingest-terv.md) (az adatút) ·
[`../measurement_2026-11-22.md`](../measurement_2026-11-22.md) (a mérés valós adata) ·
[`README.md`](README.md) (a terv-sorozat tagjai)

**Projekt:** `vessel-tracker` — a hajókövető a Dunán és a Balatonon.

> A dokumentum a repóban a `docs/megvalosulas/megvalosulas-08-teszt-strategia.md`
> útvonalon van — a relatív linkek ehhez képest számolnak.

---

## 1. Mit fed le ez a terv

**A teszt-stratégia** — vagyis:

| | |
|---|---|
| **§2** | a **teszt-piramis** (a szintek, a arányuk, a futásidejük) |
| **§3** | a **mérőszámok** (a 20 NFR → a teszt, a mérés helye) |
| **§4** | a **szintenkénti tesztek** (mi mit vizsgál, mi a példa) |
| **§5** | a **fixture-ök** (a mérési adatból) |
| **§6** | a **kilépési feltételek** (a release-terv 3.7 soraival) |
| **§7** | a **mérési adat** (a bud01 eredménye, a `docs/measurement_2026-11-22.md`) |
| **§8** | a **CI-integráció** (a `07` – CI/CD terv §8-cal) |
| **§9** | a **nyitott kérdések** |

**Amit ez a terv NEM fed le:**
- a **kód implementációja** — ez a tervezés;
- a **tervezési dokumentumok** tesztje (a swarm review) — az a
  `12` fejezete a terv-sorozatban;
- a **biztonsági audit** (a `09` – üzemeltetés terv).

---

## 2. A teszt-piramis

### 2.1 A szintek

| A szint | A tartalom | A darabszám | A futásidő | Hol fut |
|---|---|---|---|---|
| **unit** | a tiszta függvények (a 6 bites dekódolás, a keresési kulcs, a fallback-lánc) | **~400** | **< 30 s** | minden push |
| **property** | a **round-trip** tulajdonságok (a `hypothesis`) | **~40** | **< 20 s** | minden push |
| **komponens** | a service-ek a DB-vel (a testcontainers) | **~80** | **< 2 perc** | minden push |
| **integrációs** | a teljes API (a FastAPI `TestClient` + a DB) | **~60** | **< 3 perc** | minden push |
| **e2e** | a böngészőben (a Playwright) | **~25** | **< 8 perc** | a `main`-re, nem PR-re |
| **teljesítmény** | a betöltési idők (a `locust`/`k6`) | **~6** | **< 5 perc** | hetente |
| **regresszió (adat)** | a mérési adat teljes replayje | **1** | **~7,5 óra** | a mérési időszak végén |

### 2.2 A piramis aránya

```
        e2e          ██                       25 teszt
    teljesítmény      ██                       6
  integrációs          █████                   60
komponens              ████████████████         80
       property        ██████████████████       40
            unit       ████████████████████████████████████   ~400
```
**Az e2e a legdrágább és a legtörékenyebb** → **a minimumra** (a
`05` – frontend-terv szerint a katalógusoldal a fő felület → **3
kritikus forgatókönyv** elég).

### 2.3 A „ne tedd a tesztet a táblázatba" szabály

| A teszt | Hol van |
|---|---|
| a 6 bites dekódolás | **unit** (a `04` – parser-terv §10) |
| a `msg_hash` | unit |
| a fallback-lánc (a `03` §6.3) | unit |
| a constraint-ek | **a DB-ben** (a `02` – DDL-terv §12) — **nem** Python-teszt |
| a `nav_status` CHECK | **a DB-ben** |
| a migrációk visszafordíthatósága | **integrációs** (a `07` §5.1) |
| az OpenAPI-szerződés | integrációs (a `03` §5.1a linter) |

---

## 3. A mérőszámok (a 20 NFR → a teszt)

### 3.1 A táblázat

| Az NFR | A követelmény | **Hogyan mérjük** | A szint |
|---|---|---|---|
| **F-NF-01** | a katalógusoldal < 800 ms p95 | a `locust` 300 hajós listával | teljesítmény |
| **F-NF-02** | a hajóadatlap < 400 ms p95 | a `locust` | teljesítmény |
| **F-NF-03** | a keresés < 200 ms p95 | a `locust` | teljesítmény |
| **F-NF-04** | 100% indexelhető hajóoldalak | az e2e sitemap-ellenőrzés | e2e |
| **F-NF-05** | nincs duplikáció a `canonical` miatt | az e2e | e2e |
| **F-NF-06** | WCAG 2.1 AA | az **axe-core** (a Playwright-be) | e2e |
| **F-NF-07** | 360 px-től működik | a Playwright viewport | e2e |
| **F-NF-08** | heti frissítés | a `job_run` `rows_in`/`rows_out` (a `09` terv) | operációs |
| **F-NF-09** | ≥ 95% azonosító és típus kitöltve | **a mérési adatból** (a `04` §8.1 4. célpont) | **adat** |
| **F-NF-10** | 0 duplikált hajószám | **a DB unique index** (a `02` §5.3) + a mérési query | **adat** |
| **F-NF-11** | 0 belső mező-szivárgás | **a CI linter** (a `03` §8.3) | integrációs |
| **F-NF-12** | 100% forrásjelölés | a séma-ellenőrzés (minden válasz `source`) | integrációs |
| **F-NF-13** | 0 személyes adat | a séma-ellenőrzés (nincs `crew`/`captain` mező) | integrációs |
| **F-NF-14** | GDPR | az e2e (a banner, a fióktörlés) | e2e |
| **F-NF-15** | a verziózott séma | **a `openapi-diff`** a CI-ban (a `03` §8.1) | integrációs |
| **F-NF-16** | 100% átnézett fordítás | **a `content_text` státusz** (a `published`) | adat |
| **F-NF-17** | **0 fantom hajó** | **a fantom-szűrő** (a `01` §5.5) + a mérési adat | **adat** |
| **F-NF-18** | ≥ 60% ENI-vel azonosított | **a mérési adat** | **adat** |
| **F-NF-19** | a méret AIS-méretként jelölve | az e2e (a hajóadatlap szövege) | e2e |
| **F-NF-20** | a merülés RNW-jelöléssel | az e2e | e2e |

### 3.2 A három „nem automatable" mérőszám

**Az F-NF-09, az F-NF-17 és az F-NF-18** a **mérési adathalmazból**
jönnek — **nem** a kódból. → **ezek a `04` – parser-terv §8 mérési
protokolljának a kimenetei**, és a `docs/measurement_2026-11-22.md`
a formájuk.

> **A mérési eredmény (2026-11-22, az első óra):**
>
> | Az NFR | A mért érték | **A küszöb** | Az állapot |
> |---|---|---|---|
> | F-NF-17 (0 fantom hajó) | a **106 lámpa + a 3 bázisállomás** kizárásra kerül → **0** | 0 | ✅ (a szűrő megvan) |
> | F-NF-18 (≥ 60% ENI) | **0,5%** (1 hajó a 199-ből) | ≥ 60% | ❌ **a városi helyen nem mérhető** |
> | F-NF-09 (≥ 95% azonosító) | **a név 91,5%**, az ENI 0,5%, a típus 100% | ≥ 95% | ⚠️ **a névre teljesül** |
> | a lefedettség | **69,8%** | ≥ 50% | ✅ |

> **Az F-NF-18 a városi helyen nem mérhető** — a Duna szűkvízi
> szakaszain kell mérni (a `04` – parser-terv K-4 findingje) → **a
> mérési helyszín kiegészítése a feladat**, nem a teszt.

---

## 4. A szintenkénti tesztek

### 4.1 A unit tesztek (a 6 bites dekódolás)

**A `04` – parser-terv §10 szerint a `property` (round-trip) teszt a
legfontosabb** — a kézi implementálás legkisebb hibája is egy
bitben elcsúszik.

```python
# apps/api/tests/unit/test_decoder.py
import pytest
from duna.ingest.decoder import decode_6bit, decode_message


@pytest.mark.parametrize("payload,expected_mmsi", [
    ("13HOI:0P0000VOHLCnHQKwvL05Ip", 244660000),
    ("83Wj9l@j2dv=d<N=MhO@S@QU3L00", 243042769),
])
def test_decode_known_messages(payload, expected_mmsi):
    msg = decode_message(payload)
    assert msg.mmsi == expected_mmsi


def test_fill_bits_are_stripped():
    """A kitöltő bitek nem kerülnek a kimenetbe (a 04 §3.3)."""
```

### 4.2 A property tesztek (a round-trip)

```python
# apps/api/tests/property/test_decoder_roundtrip.py
from hypothesis import given, strategies as st
from duna.ingest.decoder import decode_6bit, encode_6bit


@given(st.binary(min_size=1, max_size=62))
def test_6bit_roundtrip(payload: bytes):
    """A dekódolás → visszaalakítás az eredetit adja (a 04 §10)."""
    assert encode_6bit(decode_6bit(payload)) == payload
```

> **A `property` tesztek a CI-ban a `hypothesis` példákkal futnak** —
> a `HYPOTHESIS_MAX_EXAMPLES` env-variabilissal korlátozva (a
> CI-ban **100**, a nightlyban **10 000**).

### 4.3 A komponens tesztek (a service-ek)

**A `testcontainers` valódi PostgreSQL-t ad** (a PostGIS-sel) →
a constraint-ek és a trigger-ek **valódi** viselkedését vizsgáljuk.

```python
# apps/api/tests/component/test_vessel_service.py
async def test_vessel_identifier_trigger_syncs_vessel(db):
    """A `sync_vessel_identifiers` trigger a `vessel.eni`-t feltölti."""
    # a `02` §8.1a trigger — a mérési adat szerint 1 ENI jött le,
    # szóval a trigger útvola működik
```

### 4.4 Az integrációs tesztek (az API)

**A FastAPI `TestClient` + a DB** → a teljes útvonal.

```python
# apps/api/tests/integration/test_api_contract.py
async def test_no_internal_fields_in_response(client):
    """A F-NF-11: a válasz nem tartalmaz belső mezőt."""
    r = await client.get("/api/v1/vessels?area=duna&per_page=1")
    body = r.json()
    for forbidden in ("ais_message_raw", "source_url", "audit_log"):
        assert forbidden not in str(body)


async def test_problem_detail_is_rfc9457(client):
    """A hibaformátum (a 03 §2.2) — a `type` URN (a H-6 finding)."""
    r = await client.get("/api/v1/vessels/999999999")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["type"] == "urn:vessel-tracker:problem:not-found"
```

### 4.5 Az e2e tesztek (a böngésző)

**A Playwright** — a `05` – frontend-terv szerint.

| A forgatókönyv | A NFR |
|---|---|
| a Duna-katalógus megnyílik, a szűrők működnek | F-CAT-01, F-CAT-08 |
| a hajóadatlap a német nyelven is | F-INTL, F-NF-04 |
| a kereső ENI-re | F-SRCH-01 (a US-02) |
| a **axe-core** a WCAG-ellenőrzés | F-NF-06 |
| a 360 px-es viewport | F-NF-07 |
| a `canonical` és a `hreflang` | F-NF-04, F-NF-05 |
| a méret „AIS méret" jelöléssel | F-NF-19 |
| a merülés RNW-jelöléssel | F-NF-20 |

### 4.6 A teljesítménytesztek

**A `locust`** — a `09` – üzemeltetés terv szerint a **p95** a
mérőszám (nem az átlag).

```python
# apps/api/tests/performance/catalog.py (a locust file)
from locust import HttpUser, task, between

class CatalogUser(HttpUser):
    @task
    def list_vessels(self):
        self.client.get("/api/v1/vessels?area=duna&per_page=50")

    @task
    def vessel_detail(self):
        self.client.get("/api/v1/vessels/42")

    @task
    def search(self):
        self.client.get("/api/v1/search?q=duna&area=duna")
```

> **A teljesítményteszt a CI-ban hetente fut** (a PR-en nem — a 8
> perc túl hosszú minden pushra) → a `07` – CI/CD terv Q6 nyitott
> kérdéséhez.

---

## 5. A fixture-ök (a mérési adatból)

### 5.1 A hol?

```
db/fixtures/ais/
├── manifest.json          ← a metaadatok (a típus, a darabszám, a dátum)
├── msg_01_position.json   ← a Msg 1/2/3 (a pozíció)
├── msg_04_basestation.json
├── msg_05_static.json
├── msg_08_fi10.json       ← a belvízi FI 10 (az ENI)
├── msg_18_19_classb.json
├── msg_20_23_msk.json     ← a NAVTEX/MSK
└── msg_21_classb_pos.json
```

### 5.2 A stratifikálás (a `04` – parser-terv H-8 findingje)

**Nem 50 „reprezentatív" üzenet** — **minden a mérésben előforduló
típusból legalább egy**, és a gyakori típusokból több:

| A típus | A darabszám a mérésben | A fixture darabszáma |
|---|---|---|
| 1, 2, 3 (pozíció) | 25 637 | **10** |
| **21** (Class B) | **7 016** | **5** |
| 4 (bázisállomás) | 2 070 | **2** |
| 5 (statikus) | 720 | **3** |
| **8** (FI 10) | **767** | **5** |
| **20, 23** (MSK) | **1 078** | **3** |
| 18, 24 (Class B statikus) | 82 | **2** |
| 15 (interrogálás) | 60 | **1** |

> **A `manifest.json`** a `received_at`-et, az `station_id`-t és a
> forrás-`mmsi`-t is tartalmazza → **a fixture-ök újrajátszhatók**
> (a dedup idempotenciája is tesztelhető).

### 5.3 A mérési adat a repóban

**A `docs/measurement_2026-11-22.md`** a mérés eredménye — **a
fixture-ök forrása**. **A nyers `ais.db` fájl nem kerül a repóba**
(~600 MB/hét) → **a NAS-on marad** (`/opt/data/martin/work/ais-data/`).

---

## 6. A kilépési feltételek

### 6.1 A release-terv 3.7 soraival

| A sprint | A kilépési feltétel | **Hogyan mérjük** |
|---|---|---|
| **1 — a projekt alapja** | a `just check` zöld | a CI `lint`+`test` job |
| **2 — a séma** | a migrációk visszafordíthatók, a constraint-ek élnek | a `just ddl-validate` + a `reversible` teszt |
| **3 — az API** | a 20 NFR-ből a **nem vizuális**ak teljesülnek | az integrációs tesztek |
| **4 — a frontend** | a **3 kritikus e2e** zöld | a Playwright |
| **5 — a tartalom** | a fordítási hiánylista ismert és dokumentált | a `content_key` riport |
| **6 — a kiadás** | **a mérési adatok rendben** | a `04` §8 mérési riport |

### 6.2 A release-gate (a `release-terv` 9. fejezete)

| A feltétel | A teszt |
|---|---|
| a fordítási check (a hiánylista üres vagy ismert) | a `content_text` riport |
| az adatminőségi check (ENI-duplikátumok, azonosító nélküli hajók, terület-ellentmondások) | **a mérési riport** (a `04` §8.3) |
| a visszacsatolás (mely hajóoldalak nézik) | **a `web` analitika** (a `09` terv) |

> **A „nincs ENI-duplikátum"** → a `vessel_identifier_active_uniq`
> index (a `02` §5.3) **a DB-ben** → **a mérési query ellenőrzi**.

---

## 7. A mérési adat (a bud01 eredménye)

**A `docs/measurement_2026-11-22.md`** — a mérés első órája. **Ez a
terv 3.2 táblázatának forrása**, és **a regressziós tesztek alapja**.

### 7.1 A mérésből jövő regressziós tesztek

| A teszt | A mérési alap |
|---|---|
| **a dekódolás a valós üzeneteken** | a 37 494 üzenet → **a fixture-ök** |
| **a `position` upsert** | a `(vessel_id, ts)` konfliktus → a mérésben is előfordul |
| **a dedup idempotencia** | a `msg_hash` → a backfill újrafuttatható |
| **a nem hajó üzenettípusok kizárása** | a 106 lámpa + a 3 bázisállomás → **a fantom-szűrő tesztje** |
| **a `shiptype` → `vessel_type.code` lookup** | a 14 mért kód → **mind a 89 seedben van** |
| **a `msg_hash` a valós `nmea` tömbökkel** | a `nmea` **tömb** (a v0.71) → a H-1 findingje |

### 7.2 A mérési protokoll mint regressziós teszt

**A 30 napos mérés végén** a teljes adathalmaz **replay**-elhető:
```bash
just replay db/fixtures/ais/full-2026-12-22.db
```
→ **a teljesítmény mérhető** (a `preshaz` P-H-3 findingje: a
`job_run` `started_at`/`ended_at` → a feldolgozási sebesség).

> **A teljes replay a CI-ban NEM fut** (7,5 óra) → **a mérési
> időszak végén, egyszer** → a regressziós baseline.

---

## 8. A CI-integráció

**A `07` – CI/CD terv §8.1 szerint a pipeline 8 kötelező lépése.**
**A tesztek ezekben futnak:**

| A CI lépés | A teszt |
|---|---|
| `just lint` | a `ruff` + az `eslint` |
| `just typecheck` | a `mypy` + a `tsc --noEmit` |
| `just test` | a unit + a property + a komponens + az integrációs |
| `just ddl-validate` | a `02` – DDL-terv §12 (a constraint-ek) |
| a `reversible` teszt | a migrációk visszafordíthatósága (a `07` §5.1) |
| az image build | a `docker build` |
| a frontend build | a `pnpm build` |
| **a smoke teszt** (a deploy után) | a `07` §9 |

### 8.1 A tesztlefedettség (a coverage)

**A `pytest-cov` a `duna` csomagra** — **a küszöb 85%** (a
`domain/` és az `ingest/` 90%-on felül).

> **A `domain/` (a tiszta üzleti logika) és az `ingest/` (a parser)
> a 95%-ot célozza** — ezek ahol a hibák a **legdrágábbak**.

### 8.2 A flake-ek

**A hálózati függő tesztek** (a külső AIS-forrás, az S3, a Sentry)
→ **`@pytest.mark.flaky`** a `pytest-rerunfailures`-szal, és
**a CI-ban 2 újrapróbálkozás**.

> **A „flake" a release-gate-et gyengíti** → **a havi release-ben a
> flake-ek számát nézzük** (a `09` terv metrikája).

---

## 9. A nyitott kérdések

| # | Kérdés | Az alapértelmezés | Az állapot |
|---|---|---|---|
| Q1 | **A coverage küszöb** | **85%** (a `domain/` és az `ingest/` 90%) | nyitva — **Miklós döntése** |
| Q2 | **A teljesítményteszt hetente fut-e a CI-ban?** | **igen** (a `main`-en, a PR-en nem) | nyitva (a `07` Q6-tól függ) |
| Q3 | **Az e2e a `main`-en fut-e vagy csak a release-ben?** | **a `main`-en** (a PR-en túl lassú) | nyitva |
| Q4 | **A regressziós replay (7,5 óra) a CI-ba kerül-e?** | **nem** — a mérési időszak végén, egyszer, a baseline-ra | nyitva |
| Q5 | **Az F-NF-18 (≥ 60% ENI) mérhető-e a városi helyen?** | **nem** → **a szűkvízi helyszín kell** (a `04` K-4 finding) | **nyitva — Miklós döntése** |
| Q6 | **Mekkora a `hypothesis` példaszám a CI-ban?** | **100** (a nightlyban 10 000) | nyitva |
| Q7 | **A vizuális regresszió** (a Playwright screenshot) | **nem** R1-ben — a design még alakul | **lezárva** |

---

*Ez a terv a `docs/megvalosulas/` sorozat **nyolcadik** darabja. A `01` –
stack-terv §4.2 a `08-teszt-strategia.md` fájlnevet írja elő. Következik:
09 – üzemeltetés és observability.*
