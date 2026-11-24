# Implementációs terv – 08: teszt-stratégia

**Verzió:** 0.3 (2026-11-24 — **a mérhető rész élesedett**: az
`apps/api/src/duna/domain/verification.py` + a 20 unit teszt → **a
`just test-unit` zöld**, a `just test-domain` → **100% coverage** a
`domain/`-en (a 90%-os küszöbön), a `just test` → 98% (a 85%-os
küszöbön); **a `just ddl-validate` → a 22 füstteszt-pont zöld**; **a
`just check` (a teljes minőségi kapu) → EXIT 0**. A §2.1a a jelenlegi
állapotot mutatja. A korábbi v0.1 (terv-draft, swarm review előtt) a
törzse.)
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

**A szintek a `just` célokhoz rendelése (a `prof` reviewer H-9
findingje)** — **a `07` §3.1 `justfile`-ja a kanonikus**:

| A szint | A `just` cél | A `just check` része? |
|---|---|---|
| unit | `just test-unit` | ✅ |
| property | `just test-property` | ✅ |
| komponens | `just test-component` | ✅ |
| integrációs | `just test-integration` | ✅ |
| e2e | `just test-e2e` | ❌ (a `check-release`-ben) |
| teljesítmény | `just test-perf` | ❌ (a `check-release`-ben) |
| regresszió | `just test-regression` | ❌ (a `check-release`-ben) |

> **A `just check`** = a lint + a typecheck + az 5 gyors szint + a
> DDL-validáció (**~6 perc**, a `07` §8.1 szerint) → **ez a
> kilépési feltétel** (a §6.1).
> **A `just check-release`** = a `check` + az e2e + a teljesítmény + a
> regresszió.


### 2.1a A jelenlegi állapot (2026-11-24) — a mérhető rész

**A `~400` unit teszt egy TERVEZETI becslés — a valós állapot:**

| A szint | A terv becslése | **A valós (2026-11-24)** | A megjegyzés |
|---|---|---|---|
| **unit** | ~400 | **39** | a `duna/domain/verification.py` (a bizonyossági szint, 20 teszt) + a `duna/ingest/decoder.py` (a 6 bites kódolás, 19 teszt) → **a `domain/` réteg 100%-os coverage** |
| property | ~40 | **5** | a `hypothesis` a dev-függőségek között van → **a 6 bites round-trip teszt** (a GPSD armorra) + **a `pyais` referencia-összevetés** (a `04` §11 Q6) |
| komponens | ~80 | **0** | a service-ek még nincsenek |
| integrációs | ~60 | **0** | az API még nincs |
| e2e | ~25 | **0** | a frontend még nincs |
| teljesítmény | ~6 | **0** | a `locust` a dev-függőségek között van |
| regresszió | 1 | **0** | a mérési adat megvan, a replay még nincs |

**A mérhető rész működik:**
- a `just test-unit` → **39 teszt, zöld**;
- a `just test-domain` → **100% coverage** a `domain/`-en (a 90%-os
  küszöbön — a `08` §8.1);
- a `just test` → **98%** (a 85%-os küszöbön);
- a `just ddl-validate` → **a 22 füstteszt-pont zöld** (a `02` §12);
- a **`just check` → EXIT 0** (a teljes minőségi kapu).

> **A `~400` unit teszt a teljes R1-re vonatkozik** (a `domain/`,
> az `ingest/`, az `api/`, a `repositories/`, a `services/` együtt) →
> **a 20 a kezdet.** A sorrend: a `domain/` (a legtisztább, a
> legjobban tesztelhető) → az `ingest/` (a mérési adattal) → az
> `api/` (a `testcontainers`-szel).

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
from duna.ingest.decoder import decode_message


def test_a_gpsd_referencia_pelda():
    """**A GPSD/AIS referencia-példa** — a `pyais` referenciaértékei.

    A `!AIVDM,1,1,,A,15M67FC000G?ufbE`FepT@3n00Sa,0*5C` → a `type=1`,
    az **MMSI 366 053 209**.
    """
    msg = decode_message("15M67FC000G?ufbE`FepT@3n00Sa")
    assert msg.message_type == 1
    assert msg.mmsi == 366053209


def test_a_meresi_peldak():
    """A `bud01` mérési payloadjai (a `08` §4.1).

    **A `physical=True` a vevő oszlopát jelöli** → **a `type` a
    mérési `type` oszloppal egyezik** (a mérés 8000/8000).
    """
    assert decode_message("13HOI:0P0000VOHLCnHQKwvL05Ip", physical=True).message_type == 1
    assert decode_message("83Wj9l@j2dv=d<N=MhO@S@QU3L00", physical=True).message_type == 8


def test_fill_bits_are_stripped():
    """A kitöltő bitek nem kerülnek a kimenetbe (a 04 §3.3)."""
```

> **A `08` §4.1 eredeti példái (a 244 660 000 és a 243 042 769)
> FALSIFIKÁLTAK** (a 2026-11-24-i mérés): **a vevő `mmsi` oszlopa a
> NORMALIZÁLT azonosító, nem a payload-ból számítható** (a `04` §5) →
> **a mérési payloadokból a `type` olvasható ki, az MMSI nem.**
>
> **A GPSD referencia-példa a `pyais`-szal (a hivatalos
> referencia-dekoder, a `04` §11 Q6) ellenőrzött** → **a
> `apps/api/tests/property/test_decoder_roundtrip.py` két tesztje a
> `pyais` eredményével hasonlítja a `type`-ot és az MMSI-t.**

### 4.2 A property tesztek (a round-trip)

```python
# apps/api/tests/property/test_decoder_roundtrip.py
from hypothesis import given, settings, strategies as st
from duna.ingest.decoder import decode_standard_6bit, encode_standard_6bit


@settings(max_examples=100)  # a CI-ban (a HYPOTHESIS_MAX_EXAMPLES)
@given(st.text(alphabet="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz@",
               min_size=1, max_size=62))
def test_a_standard_armor_roundtrip(payload: str):
    """A dekódolás → visszaalakítás az eredetit adja (a 04 §10)."""
    assert encode_standard_6bit(decode_standard_6bit(payload)) == payload
```

> **A GPSD armor a round-trip tesztelhető** (a `pyais` szerint: a
> 0–39 érték -> `chr(v+48)`, a 40–63 -> `chr(v+56)`) → **a property
> teszt a standard armorra vonatkozik.**
>
> **A `pyais` a hivatalos referencia-dekoder** (a `04` §11 Q6) → **a
> `test_decoder_roundtrip.py` két tesztje a `pyais` eredményével
> hasonlítja a `type`-ot és az MMSI-t** → **ez a legbiztosabb
> ellenőrzés, hogy a saját dekódolásunk helyes-e.**

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

### 5.2a A statikus adatok hiányának tesztje (a 2026-11-24-i mérési adat)

**A statikus adatok 6 percenként jönnek** (a `04` §4.4 szerint, a
mérés igazolva) → **a parsernek a „pozíció érkezett, statikus még nem"
állapotot is kezelnie kell.**

| A teszt | Mit vizsgál |
|---|---|
| **a pozíció statikus nélkül** | a `vessel` upsert **az `UNKNOWN` típussal** megy-e végig (a `02` §5.3 `NOT NULL`!) |
| **a statikus megérkezése később** | a `vessel_type_code` **frissül-e** a `UNKNOWN`-ról a valósra |
| **a név későbbi megjelenése** | a `vessel_i18n` upsert a `name_only` bizonyossági szintről valósra vált-e |
| **a `verification_level`** | a `name_only` → `ais_identified` átmenet (a `02` §6.3 `vessel_verification` nézet) |
| **az idempotencia** | a statikus adat **kétszer** érkezik → nincs duplikáció (a `msg_hash`) |

**A fixture-ök ezt fedik:** a `manifest.json`-ben a `received_at` a
fajlonkénti időpont → **a „statikus nélküli" állapot előállítható**
(a pozíció fixture-ökkel, a statikus nélkül).

### 5.3 A mérési adat a repóban

**A `docs/measurement_2026-11-22.md`** a mérés eredménye — **a
fixture-ök forrása**. **A nyers `ais.db` fájl nem kerül a repóba**
(~600 MB/hét) → **a NAS-on marad** (`/opt/data/martin/work/ais-data/`).

**A `manifest.json` tartalma (a `prof` reviewer C-6 findingje):**

```json
{
  "version": 1,
  "created_at": "2026-11-22T19:50:00Z",
  "source": "bud01 (a 47.5755205, 19.046013 pontban)",
  "total_messages": 43425,
  "fixtures": [
    {"file": "msg_01_position.json", "type": 1, "count": 10,
     "mmsi": "243043014", "received_at": "2026-11-22T19:44:12Z"},
    {"file": "msg_08_fi10.json", "type": 8, "count": 5,
     "mmsi": "243043014", "received_at": "2026-11-22T19:46:03Z"}
  ],
  "coverage": {
    "types_present": [1, 2, 3, 4, 5, 8, 15, 18, 20, 21, 23, 24],
    "missing_types": [6, 7, 9, 10, 11, 12, 13, 14, 16, 17, 19, 22],
    "note": "a hianyzó tipusok nem fordultak elo a merésben — a 04 §5.1 szerint ez nem hiba"
  }
}
```

**A méretkorlát (a `preshaz` reviewer P-C-4 findingje)** — **a repó
mérete korlátlanul ne nőjön**:

| A határ | Az érték | Ellenőrzés |
|---|---|---|
| a `manifest.json` mérete | **legfeljebb 100 KB** | a `08` §8.1 coverage-lépés |
| a JSON fixture-ök összesen | **legfeljebb 5 MB** | ugyanott |
| **a teljes `.db` a repóban** | **tilos** | a pre-commit hook |

> **A `prof` reviewer C-6 findingje:** a §7.2 egy **teljes
> `full-2026-12-22.db` SQLite-fájlt** hivatkozott a repóban
> (~3 GB) → **ellentmondott a §5.3-nak**. **A javítás: a teljes
> replay a NAS-ról jön** (lásd a §7.2).

---

## 6. A kilépési feltételek

### 6.1 A release-terv 3.7 soraival

| A sprint | A kilépési feltétel | **Hogyan mérjük** |
|---|---|---|
| **1 — a projekt alapja** | a `just check` zöld | a CI `lint`+`test` job (a `07` §3.1 definiálja a `check` célt) |
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

### 7.1a A minőségi metrikák (a MarineTraffic módszere)

> **A MarineTraffic support-dokumentációja** (a „Data Quality" és az
> „Understanding AIS & GNSS Spoofing" cikkek) **a pozíció-minőség
> ellenőrzését** is dokumentálja → **a mérési protokollunk (a `04` §8)
> ezt felveheti**:
>
> | A metrika | A módszer | A mi mérésünkben |
> |---|---|---|
> | **a pozícióugrás** | a két pozíció között a lehetségesnél nagyobb a távolság (a hajó nem ugorthat át) | **a `04` §8 szerinti mérésben** |
> | **a természetellenes sebesség** | a pozíciók közti sebesség > a hajó maximális sebessége | **a `ais_position.sog_mps` ellenőrzése** |
> | **a duplikált azonosító** | ugyanaz a MMSI/név több helyen | **a `vessel_identifier_active_uniq`** (a `02` §5.3) |
> | **a hosszú kikötő nélküli állás** | a pozíció változatlan, a `status` mégis mozgást mutat | **a `vessel_last_position.age`** |

> **A F-NF-17 (0 fantom hajó) a mérésben teljesül** (a 106 lámpa + a 3
> bázisállomás kizárva) → **de ezek a metrikák a szándékos hamisítás
> (a spoofing) és a mérési hibák (a több vevő) ellen is védik a
> katalógust** → **a `08` §4.5 szerinti regressziós tesztekbe felvehetők.**
>
> **A fontos korlát:** a MarineTraffic szerint **a hamisított jeleket
> a térképen MEGJELZIK, csak az analitikából zárják ki** → **a mi
> katalógusunkban is: a hamis gyanús jelölést kapjon, ne tűnjön el.**

### 7.2 A mérési protokoll mint regressziós teszt

**A 30 napos mérés végén** a teljes adathalmaz **replay**-elhető:
```bash
# a teljes adathalmaz a NAS-on van (a 08 §5.3) — NEM a repóban
just replay /opt/data/martin/work/ais-data/ais-20261222-1950.db
```
→ **a teljesítmény mérhető** (a `preshaz` P-H-3 findingje: a
`job_run` `started_at`/`ended_at` → a feldolgozási sebesség).

> **A `prof` reviewer C-6 findingje:** az eredeti alakban a replay a
> **repóban lévő** `db/fixtures/ais/full-2026-12-22.db` fájlt
> hivatkozta (~3 GB) → **ellentmondott a §5.3-nak** (a nyers DB nem
> kerül a repóba) → **a javítás: a NAS-ról jön** (a fenti útvonal).
>
> **A teljes replay a CI-ban NEM fut** (7,5 óra) → **a mérési
> időszak végén, egyszer** → a regressziós baseline.
>
> **A `justfile`-ban (a `07` §3.1):**
> ```make
> # a teljes meresi adat replay (a NAS-rol — a 08 §7.2)
> replay FILE:
>     python -m duna.ingest.replay --file {{FILE}} --batch-size 2000
> ```

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
→ **`@pytest.mark.flaky`** a `pytest-rerunfailures`-szal.

| A szint | A retry | Miért |
|---|---|---|
| unit + property + komponens | **0** | determinisztikusak → **a retry elrejtené a valódi hibát** |
| integrációs + e2e | **1** | a DB és a böngésző flake-el |

> **A „flake" a release-gate-et gyengíti** → **a havi release-ben a
> flake-ek számát nézzük**.

**A flake-szám a `09` – üzemeltetés-terv §10 metrikája (a `prof`
reviewer M-9 findingje — a lánc eddig nem zárult):**

| A metrika | A mérés | A küszöb |
|---|---|---|
| **a flake-ek száma a havi release-ben** | a CI összesítője a `@pytest.mark.flaky` jelölésből | **a release előtt: 0 új flake** (a meglévő is lista) |

**A `09` §10 metrikatáblázata ezt tartalmazza** → **a lánc zárva.**

---

## 9. A nyitott kérdések

| # | Kérdés | Az alapértelmezés | Az állapot |
|---|---|---|---|
| Q1 | **A coverage küszöb** | **85%** (a `domain/` és az `ingest/` 90%) | nyitva — **Miklós döntése** |
| Q2 | **A teljesítményteszt hetente fut-e a CI-ban?** | **igen** (a `main`-en, a PR-en nem) — **a `07` §8.1 a 11–13. lépéseket hetente futtatja** | **lezárva** (a `prof` reviewer P-H-1 findingje) |
| Q3 | **Az e2e a `main`-en fut-e vagy csak a release-ben?** | **a `main`-en** (a PR-en túl lassú) — **a `07` §8.1 szerint hetente** | **lezárva** |
| Q4 | **A regressziós replay (7,5 óra) a CI-ba kerül-e?** | **nem** — a mérési időszak végén, egyszer, a baseline-ra | nyitva |
| Q5 | **Az F-NF-18 (≥ 60% ENI) mérhető-e a városi helyen?** | **nem** → **a szűkvízi helyszín kell** (a `04` K-4 finding) | **nyitva — Miklós döntése** |
| Q6 | **Mekkora a `hypothesis` példaszám a CI-ban?** | **100** (a nightlyban 10 000) | nyitva |
| Q7 | **A vizuális regresszió** (a Playwright screenshot) | **nem** R1-ben — a design még alakul | **lezárva** |

---

*Ez a terv a `docs/megvalosulas/` sorozat **nyolcadik** darabja. A `01` –
stack-terv §4.2 a `08-teszt-strategia.md` fájlnevet írja elő. Következik:
09 – üzemeltetés és observability.*
