# Implementációs terv – 03: API-specifikáció (OpenAPI v1)

**Verzió:** 0.6 (a **katalóguslista + a hajóadatlap + az 5 al-végpont
+ a globális kereső végrehajtva**: **8 R1-es végpont** a valós kód, a
`just check` zöld, a 24 integrációs teszt valódi PostgreSQL-lel)
**Dátum:** 2026-11-22
**A pinnelt séma:** `megvalosulas-02-adatbazis-ddl.md` **v1.3** (71 tábla,
150 index, 121 FK, 28 trigger — **a `home_river_section_id` +
`home_basin_id` oszlopokkal**) — **a `03` ezen áll**
**Kapcsolódó dokumentumok:**
[`../../README.md`](../../README.md) (adatbázis-terv v1.3) ·
[`megvalosulas-01-stack-es-struktura.md`](megvalosulas-01-stack-es-struktura.md) (stack + struktúra) ·
[`megvalosulas-02-adatbazis-ddl.md`](megvalosulas-02-adatbazis-ddl.md) (a séma — ez a szerződés alapja) ·
[`../../docs/funkcio-leiras.md`](../../docs/funkcio-leiras.md) ·
[`../../docs/release-terv.md`](../../docs/release-terv.md) ·
[`README.md`](README.md) (a terv-sorozat tagjai)

**Projekt:** `vessel-tracker` — a hajókövető a Dunán és a Balatonon.

> A dokumentum a repóban a `docs/megvalosulas/megvalosulas-03-api-specifikacio.md`
> útvonalon van — a relatív linkek ehhez képest számolnak.

---

## 1. Mit fed le ez a terv

**Két API van, és ezeket NEM szabad összekeverni:**

| | **Az R1 belső API** | **Az R5 B2B API** |
|---|---|---|
| Kiknek | a saját weboldalnak (a `web` Astro SSR) | külső fejlesztőknek |
| Hitelesítés | **nincs** (a hálózaton belül) | kulcs + hatókör + kvóta |
| Verziózás | `/api/v1/` | `/api/v1/` (a saját verziózás, lásd §3) |
| Rate limit | nincs | **van** (kvótánként) |
| Stabilitási garancia | **nincs** — R2–R5 alatt szabad változni | **van** — a F-NF-15 szerint visszafelé kompatibilis |
| Publikálódás | **soha** (a `release-terv` 3.3: „Az R1 API belső célra készül") | a docsban, a `docs/api/` alatt |

**A kettő ugyanazt a kódot használja** (ugyanazok a routerek, ugyanazok a
service-ek) — **de a B2B réteg nem R1-ben jelenik meg**. Az R1-ben a
`/api/v1/` útvonalak a `web` szerveren belül vannak, és **a `web` nem
proxyzza ki őket a publikus internetre**.

**Amit ez a terv NEM fed le:**
- a **B2B API részletes specifikációja** (a kulcskezelés, a kvóták, a
  stream, a webhook) — az **R5**, a `release-terv` 5. fejezete;
  itt csak a **szerződés határa** rögzül, hogy R1-ben ne legyen
  feleslegesen kiépítve
- a **szerkesztői API** — az a `06` – Szerkesztői felület terv tárgyalja
  részletesen; itt a határvonal rögzül
- az **élő pozíció stream** (R2) és az **értesítések** (R2–R4)

---

## 2. A szerződés alapelvei

### 2.0a A tervverziók szinkronja (a `preshaz` reviewer H-1 findingje után)

**A `02` – DDL-terv és a `03` – API-terv szorosan kötött.**

| A szabály | |
|---|---|
| **A pin** | a `03` fejlécében rögzített séma-verzió — **a `02` minden módosítása a `03` felülvizsgálatát igényli** |
| **A CI-ellenőrzés** | a `03` fejlécének pinje egyezik a `02` fejlécének verziójával → különben a build elbukik |
| **A `03` nyitott kérdései** | a `02` verzióját rögzítik (melyik séma-verzióra vonatkoznak) |
| **A `04` – parser terv** | a `02` **v1.3**-ra épül (a `position` és a `vessel` mezők változásai) |

**A `docs/megvalosulas/README.md`** a sorozat állapotát mutatja — a
verziók ott is frissülnek.

### 2.1 A JSON-forma

**A válaszok `application/json; charset=utf-8`** — a `snake_case`
oszlopnevekkel, hogy a DB-vel való leképezés **egyértelmű és gépi**
legyen.

```json
{
  "data": [ { "id": 42, "name": "TEST HAJO", "mmsi": 244660000 } ],
  "meta": { "total": 137, "page": 1, "per_page": 50 }
}
```

**A `data` + `meta` burkoló** minden listaelválaszon, a `data` egyetlen
objektumon. Ez a séma egyformú, és a kliens (Astro + React-szigetek)
egy generikus hookkal kezeli.

**A `meta.total` definíciója** (a `prof` reviewer H-1 findingje után):

- a `total` a **szűrés UTÁNI teljes darabszám** (a lapozás nélkül) — ezt
  használja a kliens lapozója;
- a számítás **ugyanazzal a `WHERE`-tel** történik, mint a lekérdezés
  (`SELECT COUNT(*) FROM ... WHERE <ugyanaz>`);
- **kivétel: a `q` (trigram) keresés** → a `vessel_i18n`-re join-öl →
  a `COUNT(*)` **nem indexelhető** (a teljes szűkített halmazt kell
  megszámolni) → ilyenkor a `meta.total` **`null`**, és a kliens
  lapozója „lapozás nem elérhető" jelzést ad (a `has_more` viszont
  megmarad — a `per_page + 1` lekérdezésből jön);
- a `vessel` mérete a README 5.1 szerint ~3 300–3 500 (Duna) + ~250
  (Balaton) → a `vessel`-en a számlálás triviális; a `q` nélküli
  szűrők mind **indexelt** oszlopokra épülnek → a `COUNT(*)` az
  `EXPLAIN`-ban **index-only scan**.

**A `meta` két variánsa** (a `prof` reviewer L-4 findingje):

| A válasz | A `data` típusa | A `meta` modellje |
|---|---|---|
| lista | `list[T]` | `PageMeta` (`total`, `page`, `per_page`, `has_more`) |
| objektum | `T` | `ObjectMeta` (`total`) |

A két burkoló: `Page[T]` és `Data[T]` — a `response_model` a generikus
paraméterrel (`Page[VesselListItem]`, `Data[VesselDetail]`) — lásd §5.5.

### 2.2 A hibák — RFC 9457 (`application/problem+json`)

```json
{
  "type": "urn:vessel-tracker:problem:not-found",
  "title": "Hajó nem található",
  "status": 404,
  "detail": "A 'xyz' keresésre nincs hajó a duna katalógusban.",
  "instance": "/api/v1/vessels/xyz",
  "errors": [
    { "field": "operator_id", "code": "not_found",
      "message": "Az üzemeltető nem létezik." }
  ]
}
```

**A `type` egy domainfüggetlen URN** (`urn:vessel-tracker:problem:<kód>`)
— a `prof` reviewer **H-6** és **L-1** findingje szerint. A korábbi
`https://vessel-tracker.example/probs/not-found` forma **ellentmondott a
saját magyarázatának**: a domainre mutató URI-t a domain megváltoztatása
**megváltoztatja**, tehát a kliensoldali kulcs (az RFC 9457 szerint a
`type` a gépi fogyasztás kulcsa) **törne**.

A URN forma előnye:
- **domainfüggetlen** — a telepítési domain (a `01` – stack-terv szerint
  `vessel-tracker.example.hu`) **soha nem** kerül a `type`-ba;
- **stabil** — a F-NF-15 („a hibakódok stabilak") a `type` URI-re is
  érvényes: a kódok nem változnak, tehát a URN sem;
- a kliens a `type` **utolsó szegmense** utáni kódot használja kulcsként
  (`not-found`, `validation-error`, …) — ez a §7 katalógusának kulcsa is.

**A `title` és a `detail` lokalizációja** (a `prof` reviewer M-6
findingje): a `title` a **`content_key`-ből** jön (egy kulcs a hibakódra,
pl. `error.vessel.not_found.title`) **a kiválasztott nyelven** (a
`content_key` + `content_text` mechanizmus, a README 4.2), a `detail`
pedig **paraméterezett szöveg** (a README 4.7: ICU MessageFormat) → a
publikálatlan fordításnál a §6.3 fallback-lánca szerint.

### 2.2a A kivétel-kezelés (a `preshaz` reviewer C-3 findingje után)

**A FastAPI globális kivétel-kezelője** (`exceptions.py`) alakítja
**minden** hibát az RFC 9457 formátumra:

```python
# apps/api/src/duna/exceptions.py
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from psycopg import errors as pg_errors


# A domainfuggetlen URN (a H-6/L-1 finding) — a "type" stabil kulcs,
# a telepitesi domain nem kerul bele.
PROBLEM_BASE = "urn:vessel-tracker:problem:"


def problem(status: int, slug: str, detail: str,
            errors: list[dict] | None = None,
            instance: str | None = None) -> JSONResponse:
    """Egy RFC 9457 problem+json válasz."""
    body = {
        "type": PROBLEM_BASE + slug,
        "title": TITLES[slug],
        "status": status,
        "detail": detail,
    }
    if instance:
        body["instance"] = instance
    if errors:
        body["errors"] = errors
    return JSONResponse(
        status_code=status,
        content=body,
        media_type="application/problem+json",
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def on_validation_error(request: Request, exc: RequestValidationError):
        return problem(
            422, "validation-error",
            "A kérés egy vagy több paramétere érvénytelen.",
            errors=[
                {"field": ".".join(str(p) for p in e["loc"][1:]),
                 "code": e["type"], "message": e["msg"]}
                for e in exc.errors()
            ],
            instance=str(request.url.path),
        )

    @app.exception_handler(pg_errors.OperationalError)
    async def on_db_error(request: Request, exc: pg_errors.OperationalError):
        # A belső hiba szövege NEM mehet a válaszba (a psycopg
        # üzenete SQL-részletet, fájlnevet, connection stringet
        # is tartalmazhat) — csak a naplóba.
        logger.exception("DB-hiba: %s", exc)
        return problem(
            503, "service-unavailable",
            "Az adatbázis nem érhető el. Kérjük, próbáld újra később.",
            instance=str(request.url.path),
        )

    @app.exception_handler(pg_errors.QueryCanceled)
    async def on_timeout(request: Request, exc: pg_errors.QueryCanceled):
        logger.warning("Query timeout: %s", request.url.path)
        return problem(
            504, "gateway-timeout",
            "A kérés feldolgozása túl hosszú időt vett igénybe.",
            instance=str(request.url.path),
        )
```

**A kivétel → HTTP → `type` leképezés:**

| A kivétel | HTTP | A `type` utolsó szegmense |
|---|---|---|
| `RequestValidationError` | 422 | `validation-error` |
| `HTTPException(404)` | 404 | `not-found` |
| `HTTPException(400)` | 400 | `invalid-query` |
| `HTTPException(401)` | 401 | `unauthorized` |
| `HTTPException(403)` | 403 | `forbidden` |
| `HTTPException(409)` | 409 | `conflict` |
| `OperationalError` / `InterfaceError` | **503** | `service-unavailable` |
| `QueryCanceled` (a `statement_timeout`) | **504** | `gateway-timeout` |
| bármi más | 500 | `internal-error` |

**A `detail` szabály:** a `4xx` válaszok `detail`-je **felhasználóknak
szóló szöveg** (magyarul, a kérésre vonatkozó). Az `5xx` válaszoké
**mindig fix szöveg** — a belső hiba **csak a naplóba** megy. A
`logger.exception` rögzíti a teljes kivételt (a stack trace-et), és a
`request_id` a `X-Request-ID` headerrel visszaadható.

**A pool és a timeoutok** (`db/session.py`):

```python
engine = create_async_engine(
    settings.database_url,
    pool_size=10,             # a 2 GB-os VPS-en 10 a maximum
    max_overflow=5,
    pool_pre_ping=True,       # a halott kapcsolatot azonnal dobja
    pool_recycle=1800,        # 30 perc — a NAT-ok lezáratják
    connect_args={
        "connect_timeout": 10,        # másodperc
        "options": "-c statement_timeout=5000",   # 5 másodperc
        "options": "-c lock_timeout=2000",         # 2 másodperc
    },
)
```

**A `statement_timeout=5000`** (5 s) — a katalógus-lekérdezés p95
300 ms, így az 5 s bőséges. **A `lock_timeout=2000`** — egy zárolt
tábla nem tartja a kapcsolatot percekig.

**A `pool_pre_ping`** — a VISMét (a VPS-en a DB és a app is ugyanazon
a gépen, de a restart után a connection elavulhat).

### 2.3 A verziózás

- a **URL-verziózás** (`/api/v1/`) — a README 7.3 és a F-NF-15
- **nincs** query-paraméteres verzió (`?v=2`) — az egyetlen forrás a URL
- a **verzió a `docs/api/` alatt** van, verziózva (`v1/index.html`)

### 2.4 A lapozálás

**Két mód, a használati esettől függően:**

| Mód | Paraméter | Használja |
|---|---|---|
| **Offset** (alapértelmezett) | `?page=1&per_page=50` | a katalógus lista, a kereső |
| **Cursor** | `?cursor=<opaque>` | a nagy, gyorsan változó listák (R2+ élő pozíció) |

**Az offset alapértelmezett, 50 elem/page, maximum 200.** A
`per_page` nagyobb értékre hívás → **422** (`validation-error`), nem
csendes levágás — a `Query(le=200)` ezt adja (a prof reviewer H-3
findingje után: a korábbi `400` a terven belül három helyen ellentmondott
magának).

**A rendezés:** `?sort=name&order=asc` — a rendezési mezők **whitelistelt**
(több rendezési mező kombinációja R1-ben nem kell).

**A lapozás DETERMINISZTIKUS** (a prof reviewer C-6 findingje után):
a `sort=name` **önmagában nem elég** — azonos nevű hajók közti sorrend
ingadozna, és a lapozáskor egy hajó kimaradna vagy megduplázódna.
**A rendezési kulcs mindig `(<mező>, <id>)`** — az `id` a másodlagos
kulcs, így a sorrend teljesen determinisztikus:

```sql
ORDER BY vessel.sort_name ASC, vessel.id ASC
```

**Minden rendezési módra** a másodlagos kulcs a `vessel.id` — a
`sort=length`, a `sort=updated_at` és a `sort=operator` esetén is.

**A `sort_name` index** (`vessel_area_sort_name_idx` a 02-es terv
§5.2) a `(operating_area, sort_name)` sorrendet fedi — az `id`-val
kiegészítve a PostgreSQL az indexet használja (az `id` a heap-ből
jön).

### 2.5 A nem-funkcionális garanciák (a F-NF-11, F-NF-15 alapján)

| Garancia | Szabály |
|---|---|
| **Nincs belső adat-kiszivárgás** | a `ais_message_raw`, a `job_run`, a `data_quality_event` és az `audit_log` **nem** jelenik meg a válaszban |
| **A forrás látható** (a F-NF-12) | a `data_source.code` és a `data_source.name` **látható** — a jogi forrásláthatóság (a F-NF-12) ezt kívánja. A **`source_url`** és a `data_source.license_ref` **belső** — a licenc- vagy szerződéshivatkozás üzleti titok lehet |
| **Visszafelé kompatibilitás** | egy mező eltávolítása a `/v1/`-ben **tiltott**; a mező elavul → `deprecated: true` a OpenAPI-ban, és egy évig működik |
| **A hibakódok stabilak** | a `type` URI és a hibakódok változatlanok |
| **A válaszidő** | a katalógus-lekérdezés p95 < 300 ms — **a valós forrás: a README 5.7 (SLO) és a F-NF-01…03**, nem a 9. fejezet (a `preshaz` reviewer H-3 findingje után — a README 9. fejezete a megvalósítási fázisokat tartalmazza) |

---

## 3. A belső API végpontjai (R1)

### 3.1 A katalógus

> **IMPLEMENTÁCIÓS ÁLLAPOT (2026-11-25):**
>
> | A rész | Az állapot |
> |---|---|
> | a `GET /api/v1/vessels` | ✅ **VALÓS KÓD** (`duna/api/v1/vessel.py`) |
> | a `duna/db/models.py` | ✅ **11 ORM modell** (a `vessel`, a `vessel_i18n`, a `vessel_type`(+`_i18n`), az `operator`(+`_i18n`), a `country`, a `port`, a `vessel_identifier`, a `language`) |
> | a `duna/repositories/vessel_repo.py` | ✅ **a JOIN-ek + a szűrők + a lapozás** |
> | a `duna/schemas/common.py` | ✅ **a `Page[T]`/`Data[T]`** (a §5.5 — két burkoló) |
> | a `duna/main.py` | ✅ **a FastAPI app + a CORS + a `/health` + a lifespan** |
> | az integrációs teszt | ✅ **13 teszt**, valódi PostgreSQL-lel |
> | az alkalmazásréteg-coverage | ✅ **91%** (a CI-ben, a `DATABASE_URL`-lel) |
> | **a `models-check`** (a `just models-check`) | ✅ **a modell–séma drift-ellenőrzés** (a §5.1a) — **a kézzel írt modellek elcsúszását a CI kapja el** |
> | a `GET /api/v1/vessels/{id}` (a hajóadatlap) | ✅ **VALÓS KÓD** (`duna/repositories/vessel_detail_repo.py`) |
> | a `GET /api/v1/vessels/{id}/aliases` | ✅ **VALÓS KÓD** (a `vessel_alias` — **a LEZÁRTak**, a 03 §3.1) |
> | a `GET /api/v1/vessels/{id}/ownership` | ✅ **VALÓS KÓD** (a `vessel_ownership` + a dátumtartomány) |
> | a `GET /api/v1/vessels/{id}/certificates` | ✅ **VALÓS KÓD** (a `vessel_cert` — **szűrés nélkül**) |
> | a `GET /api/v1/vessels/{id}/identifiers` | ✅ **VALÓS KÓD** (a `vessel_identifier` + a `data_source` — **szűrés nélkül**) |
> | a `GET /api/v1/vessels/{id}/data-origin` | ✅ **VALÓS KÓD** (a `vessel_data_origin` — **csak az aktuális források**) |
> | **a `scripts/ci/check_models.py`** (a `just models-check`) | ✅ **a modellek és a séma driftjét elkapja** (a §5.1a) — **kétirányú**: a modell oszlopa a DB-ben, a DB NOT NULL oszlopa a modellben |
> | a `GET /api/v1/search` | ✅ **VALÓS KÓD** (`duna/repositories/search_repo.py`) |
> | **a `duna/domain/text.py`** (a kereső normalizálás) | ✅ **a `lower(unaccent(name))` alakja** — **a `sort_name`-ével egyezik** |
> | **a `meta.area_hint`** | ✅ **a `bori` H-2 findingje: a másik területen van-e találat, a darabszám nélkül** |
> | a `GET /api/v1/search/suggest` (a F-SRCH-08) | ⏳ **NEM KÉSZ** (R3) |
>
> **A `verification_level` a SZÁMÍTOTT érték** (a `vessel_verification`
> nézetből) → **a `verification_source` jelzi, ha a tárolt érték
> eltér** (`stored_stale`) → **ez a `bori` reviewer C-8 findingje.**
>
> **A `verification` SZŰRŐ a TÁROLT értékre épül** (a §3.1 szerint
> indexelt) → **a szűrő és a megjelenített érték különbözhet** →
> **a `verification_source` ezt jelzi.**


| Method | Path | Leírás | Funkció |
|---|---|---|---|
| GET | `/api/v1/vessels` | a katalógus listája, szűréssel és lapozással | F-CAT-02, F-CAT-08, F-CAT-10, F-CAT-14 |
| GET | `/api/v1/vessels/{id}` | egy hajó adatlapja | F-CAT-06, F-DET-01…16 |
| GET | `/api/v1/vessels/{id}/aliases` | a hajó **történeti** nevei (a jelenlegi a `vessel`-ből jön) | F-DET-05 |
| GET | `/api/v1/vessels/{id}/ownership` | a **tulajdonosváltások** (a dátumtartománnyal) | F-DET-05 |
| GET | `/api/v1/vessels/{id}/certificates` | a hajó engedélyei | F-DET-02 |
| GET | `/api/v1/vessels/{id}/identifiers` | az összes azonosító + eredet | F-DET-02, F-DET-15 |
| GET | `/api/v1/vessels/{id}/data-origin` | a mezőnkénti eredet | F-DET-15 |

> **Az `/aliases` szűrője** (a `prof` reviewer M-8 findingje után): a
> végpont a **történeti** neveket adja → a szűrő
> **`valid_to IS NOT NULL`** (a lezárt időtartomány = a történet).
> A `name_type='official'` **és** `valid_to IS NULL` sor a **jelenlegi**
> név — az a `vessel`/`vessel_i18n`-ből jön, **nem** duplikálódik itt.
> A `name_type` (`former`/`official`/`shipyard`) a szemantika, a
> `valid_to` az idő — **mindkettő** megvan a `vessel_alias`-ban.
>
> A `/certificates` és az `/identifiers` viszont **szűrés nélkül**
> mindent adnak (az aktív + a lezárt azonosítók egyaránt).

**A `GET /api/v1/vessels` szűrői (mind a query stringben):**

| Paraméter | Típus | F-CAT / F-SRCH | Példa |
|---|---|---|---|
| `area` | `duna` \| `balaton` — **KÖTELEZŐ** | F-CAT-01, F-SRCH-07 | `duna` |
| `q` | string | F-CAT-09, F-SRCH-01…03 | `HU-DA` |
| `type` | string (a `vessel_type.code`) | F-CAT-08 | `INLAND_CARGO` |
| `operator` | integer (a `operator.id`) | F-CAT-08, F-CAT-11 | `7` |
| `status` | `active` \| `excluded` \| `inactive` \| `scrapped` | F-CAT-08 | `active` |
| `moving` | boolean — a **számított** mozgás (lásd a blokquote-ot) | F-CAT-04 | `true` |
| `verification` | `ais_identified` \| `ais_partial` \| `operator_claimed` \| `name_only` \| `unverified` — a **TÁROLT** érték (a `vessel.verification_level`) | F-CAT-14 | `ais_identified` |
| `section` | integer (a `river_section.id`) | F-CAT-08 | `3` |
| `basin` | integer (a `basin.id`) | F-CAT-08 | `1` |
| `home_section` | integer (a `river_section.id`) — a hajó **Hazai szakasz**-a | F-CAT-08 | `3` |
| `home_basin` | integer (a `basin.id`) — a hajó **medence**-je | F-CAT-08 | `1` |
| `season` | `in_season` \| `out_of_season` | F-CAT-05 (Balaton) | `in_season` |
| `sort` | `name` \| `type` \| `operator` \| `length` \| `updated_at` | F-CAT-02 | `name` |
| `order` | `asc` \| `desc` | F-CAT-02 | `asc` |
| `page` | integer ≥ 1, **default 1** | F-CAT-02 | `1` |
| `per_page` | integer 1…200, **default 50** | F-CAT-02 | `50` |

> **A `verification` szűrő a TÁROLT értékre épül** (a `vessel.verification_level`),
> **nem** a számítottra (a `vessel_verification.computed_verification_level`
> nézetből) — és ez **szándékos** (a `prof` reviewer H-8 findingje):
>
> - a tárolt érték **indexelt** (`vessel_area_status_verification_idx`),
>   a nézetből való szűrés **nem**;
> - a `02` – DDL-terv szerint a tárolt és a számított érték eltérését az
>   `is_stale` jelzi, és **a CI ellenőrzi** a konzisztenciát egy
>   minta-adaton → az elavultság a gyakorlatban 0;
> - az **adatlap** a `verification_level` mezőben a **SZÁMÍTT** értéket
>   adja, plusz a `verification_source` mező (`computed` | `stored_stale`)
>   jelzi, ha a tárolt érték elavult → **a kliens nem tud hamis
>   bizonyossági szintet mutatni** (a F-DET-14).
>
> **A szűrő és az adatlap különböző forrást használ** — ez a szándékos
> döntés: a szűrő gyors és indexelt, az adatlap pontos és számított.

> **A `sort=operator` a `vessel.operator_id`-re megy** (a `prof` reviewer
> M-3 findingje után) — **nem** az `operator.legal_name`-ra. A név szerinti
> rendezés JOIN-t igényelne → a `vessel`-en nem indexelhető → `filesort`
> a JOIN-olt halmazon. Az `operator_id` a **stabil, indexelt** út, és
> a rendezési sorrend a hajók listájában értelmezhető (a kezelő azonosítója
> szerint). A trigram-index az `operator_legal_name`-re **rendezésre nem
> használható**.
>
> **Ha később névre kell rendezni**, a `02`-be egy denormalizált
> `vessel.operator_sort_name` kell (a `vessel.sort_name` mintájára) — ez
> **egy 02-es terv-módosítás**, nem a 03-as API-kerdés.

> **Az `area` KÖTELEZŐ** (a `bori` reviewer C-7 findingje után). A
> funkcióleírás 7.1 **kategorikusan tiltja** az egységes listát: „*Nincs
> egyetlen `/hajok` lista, amely mindkettőt mutatja*". A hiányzó `area`
> → **400 `invalid-query`** (nem 422 — a `area` nem opcionális, hanem
> hiányzik; a 400 a *malformed* kérésre, a 422 a *szemantikailag
> hibás* értékre vonatkozik). A `/search`-nél ugyanígy.
>
> **A `section` és a `basin` szűrő adatforrása** (a `prof` reviewer
> **C-1** findingje után) — ez volt a legkomolyabb hiányosság:
>
> **A korábbi terv a `position` táblára hivatkozott** (`position.river_section_id`)
> — de a `position` **90 napos TTL-lel partícionált** (a `02` – DDL-terv
> §6.2), és a `?section=` szűrő a **katalógust** szűri, nem a pozíciót.
> A `vessel`-en pedig **nem volt** szakasz-hivatkozás → a szűrő **R1-ben
> nem volt implementálható**.
>
> **A megoldás: két új denormalizált oszlop a `vessel`-en** (a
> `last_river_km` mintájára) — a `02` – DDL-terv **v1.3**-ban:
>
> | Az oszlop | A jelentése | A null érték |
> |---|---|---|
> | `vessel.home_river_section_id` | a hajó **Hazai szakasz**-a (a `river_section.id`) | nincs meghatározva |
> | `vessel.home_basin_id` | a hajó **medence**-je (a `basin.id`) | nincs meghatározva |
>
> Ezek az **ingest** során töltődnek (a pozícióból kiszámított
> folyó-kilométerből → a `river_section` és a `basin` lookup) → **a
> szűrő indexelhető** (a `vessel_home_idx` composite index a
> `home_river_section_id`-re).
>
> **A `section` és a `basin` szűrő mostantól a `home_*` oszlopokra
> épül** — a `position`-ön alapuló szűrés helyett. (A `position`
> TTL-je miatt a katalógus-szűrés nem épülhetett volna a pozíciókra.)
>
> A `home_*` oszlopok a **`02` v1.3** részei → a `03` fejlécének
> séma-pinje a `02` **v1.3**-ra mutat (a §2.0a szerint).

> **A `moving` szűrő az R1-es szerződésben VAN** — a `bori` reviewer
> C-3 findingje kivette, de a **`prof` reviewer C-5 findingje szerint
> R1-ben is megadható**, mert a `vessel.status` **és** a
> `vessel.last_position_ts` **együtt** elegendő.
>
> **A definíció (két érték):**
>
> ```
> moving=true  ⇔  status = 'active'
>              ∧  last_position_ts IS NOT NULL
>              ∧  last_position_ts > now() - interval '24 hours'
>              ∧  sog_mps > 0        (a vessel_last_position nézetből)
>
> moving=false ⇔  a fenti feltételek bármelyike nem teljesül
> ```
>
> **A `status` értékei és a jelentésük:**
>
> | A `status` | A jelentése a katalógusban |
> |---|---|
> | `active` | **közlekedő** — a hajó a rendszerben aktív |
> | `inactive` | **nem közlekedő / állandóan álló** (a kiürített vagy a raktáron álló hajó) |
> | `excluded` | **kizárva** — a fantom-szűrő vagy a kézi kizárás miatt (a `status` nem jelenik meg a katalógusban) |
> | `scrapped` | **kivezetve** |
>
> **A 24 órás frissességi küszöb** egy **dokumentált konstans**
> (`MOVING_FRESHNESS_HOURS = 24`) — a 90 nap a pozíciók **TTL-e**
> (a `02` – DDL-terv §6.3a), a mozgás frissessége ennél sokkal
> szigorúbb; **két külön konstans, nem ugyanaz**.
>
> **Miért kell a `status` ÉS a pozíció is?** (a F-CAT-04 két oldala)
> A `status='active'` önmagában a *rendszerben való jelenlétet* jelenti —
> egy hónapja nem látott hajó is `active` marad. Az „éppen mozog"
> jelentéshez **friss pozíció kell**; a `status` pedig kizárja a
> fantom-szűrő által `excluded`-dé tett hajókat.
>
> **A `status=excluded` a szűrőeredménye, nem egy mozgásjelző.** A
> `04` – AIS-parser terv a fantom-szűrő négy szabályát rögzíti (a
> pozíció, a sebesség, az 5+ napos állóhelyzet, a kézi kizáró lista) —
> ezek **a `vessel.status`-ba** írnak, nem külön flagbe.
>
> **Az indexelhetőség:** a `moving` a `vessel.last_position_ts`-re
> épül (a `02` §6.3a denormalizált mező) → **indexelhető**; a
> `sog_mps` a `vessel_last_position` nézetből jön (a nézet a
> `vessel`-re néz → a `sog_mps` szűrés **nem** indexelhető, de a
> 24 órás `last_position_ts` szűrés igen → a `sog_mps` csak a már
> szűkített halmazon fut).
>
> **A `season` szűrő** a `vessel_service_period` táblából számít: a
> `season_start`/`season_end` és a `service_status` alapján a
> `service_status='seasonal'` hajók esetén.

### 3.2 A kereső

| Method | Path | Leírás | Funkció |
|---|---|---|---|
| GET | `/api/v1/search` | a globális kereső | F-SRCH-01…07 |
| GET | `/api/v1/search/suggest` | a gyorskereső javaslatai (R3) | F-SRCH-08 |

> **Az `area` a `/search`-nél is KÖTELEZŐ** (a `prof` reviewer M-5
> findingje után). A `not-found-in-area` (404) hibakód **csak
> területhez kötött kérésnél értelmes** — különben a „másik területen
> lenne" diagnózis nem állítható. A funkcióleírás F-SRCH-07 („a
> keresés a kiválasztott területen belül korlátozódik, a területváltóval
> együtt") és 7.1 (a két katalógus külön navigáció) ezt kikötelezi.
>
> **A hiányzó `area` → 400 `invalid-query`** (ugyanaz, mint a
> `/vessels`-nél).

**A `GET /api/v1/search` viselkedése:**

```
GET /api/v1/search?q=12345678&area=duna
```

1. **először pontos azonosító-egyezés** (F-SRCH-02): az `eni`, a `mmsi`,
   az `imo`, a `callsign` a `vessel_identifier`-ben
   (**a `F-INTL-08` szerint** a hajószámok és az ENI-k **formázása
   nyelvfüggetlen**, de **kereshetők** → a keresés a **nyelvfüggetlen
   nyers értékre** támaszkodik, nem a megjelenített formára)
2. **aztán név-egyezés** (F-SRCH-03): prefix/szubsztring, trigram index,
   ékezet- és kis-nagybetű-független (`unaccent` + `lower`)
3. **a terület szűkít** (F-SRCH-04, F-SRCH-07): a `duna` keresés **soha**
   nem talál Balaton-hajót

**A `q` minimális hossza 2 karakter** — 1 karakterre **422**.

> **Az azonosítók elérhetősége — a mérési adat korlátja**
> (a `bori` reviewer B-C-1 findingje, a 05–09-es swarm review-ból).
>
> A `docs/measurement_2026-11-22.md` szerint a mérésben (a `bud01`
> vevő, 199 hajó) **az ENI-vel azonosított hajók aránya 0,5%** (1 hajó),
> miközben a **hívójellel 76/78 hajó azonosítható**.
>
> **Ez nem API-hiba, hanem adatforrás-hiány** — de a felhasználónak
> tudnia kell. Ezért:
>
> | Az azonosító | A mérésben | A kereső viselkedése |
> |---|---|---|
> | az `mmsi` | 100% | mindig talál (minden AIS-üzenetben van) |
> | a `callsign` | ~97% | talál (a `vessel_identifier`-ben) |
> | az `imo` | ritka | nem talál → **üres eredmény** |
> | az `eni` | **0,5%** | nem talál → **üres eredmény** |
>
> **A `GET /search` üres eredményre** (pontos azonosító, de nincs találat)
> → **404 `not-found-in-area`** a szokásos válasszal, **de a
> `meta.hint` mezővel** (a `03` §5.4a szerint):
>
> ```json
> {
>   "error": {
>     "code": "not-found-in-area",
>     "message": "Nincs ENI-vel azonosított hajó a Duna-katalógusban.",
>     "hint": "Az ENI-k a magyar Duna-szakaszon ritkák (a mérésben a hajók 0,5%-ának van). Próbáld a hívójellel vagy a MMSI-vel."
>   }
> }
> ```
>
> **A `hint` a `search` végpont kizárólagos mezője** — a többi
> végpont nem ad `hint`-et (a `03` §5.4a).

### 3.3 A referenciatáblák

| Method | Path | Leírás |
|---|---|---|
| GET | `/api/v1/ports` | a kikötők listája (szűrés: `waterway_id`, `port_type`, `country_code`, `q`) |
| GET | `/api/v1/ports/{id}` | egy kikötő (a `berth`, a `terminal`, a `lock` együtt) |
| GET | `/api/v1/locks` | a zsilipek listája |
| GET | `/api/v1/locks/{id}` | egy zsilip (a `lock_status` idősorral) |
| GET | `/api/v1/waterways` | a vízutak |
| GET | `/api/v1/river-sections` | a folyószakaszok |
| GET | `/api/v1/basins` | a balatoni medencék |
| GET | `/api/v1/vessel-types` | a hajótípusok (fordítással) |
| GET | `/api/v1/operators` | az üzemeltetők (a saját flotta-ajánlóval, R3) |
| GET | `/api/v1/routes` | az útvonalak (a `route_stop`-okkal) |
| GET | `/api/v1/cargo-types` | a rakománytípusok |

> **Az R3-as végpontok az R1-es fejezetben** (a `prof` reviewer H-7
> findingje után) — a fejezetcím „R1", de a felsorolt végpontok között
> van, ami a funkcióleírás/release-terv szerint **R3**:
>
> | A végpont | A funkció | A prioritás / release |
> |---|---|---|
> | `/api/v1/search/suggest` | F-SRCH-08 | **S, R3** |
> | `/api/v1/notices` | F-CNT-03 | **S, R3** |
> | `/api/v1/events` | F-CNT-04 | **S, R3** |
> | `/api/v1/gauges` | a mérőpontok | nem az R1-es funkciólista része |
> | `/api/v1/operators` — a „saját flotta-ajánló" | F-DET-04 | **R3-től** |
>
> **A `/api/v1/operators` R1-es része MARAD** (a F-CAT-11 „a katalógus
> üzemeltető szerinti aggregált nézetben is megjeleníthető" — S, R1) —
> csak a „saját flotta-ajánló" funkció R3-es.
>
> **Az `/api/v1/articles` R1-ben van** (a F-CNT-05, a release-terv §3.2
> 11. sora: „Statikus cikkek/blog (három nyelven)") — ez rendben.
>
> **A `release-terv` §3.2 R1-es listája:** kikötők (Duna + Balaton),
> zsilip, folyószakaszok, hajótípusok, statikus cikkek/blog.

> **A `/notices` és az `/events` időszűrése** (a `prof` reviewer M-2
> findingje után) — a séma alapján:
>
> | A végpont | A szűrő | Az index |
> |---|---|---|
> | `/api/v1/notices` | `valid_from <= now() AND (valid_to IS NULL OR valid_to > now())` | `notice_valid_idx` |
> | `/api/v1/events` | `starts_at >= now() - interval '30 days'` (a közelmúlt + a jövő) | `event_starts_idx` |
>
> **A `notice`-nek NINCS `status` oszlopa** (a `notice_i18n`/`notice_type`
> igen, a `notice` maga nem) → a szűrő **kizárólag az időablak**;
> a `/articles`-nél van a `status='published'` szűrő (az `article`-nek van
> `status` oszlopa: `draft`/`review`/`published`/`archived`).
>
> **A jövőbeli események** a `/events`-nél benne vannak (a `starts_at`
> a szűrő alsó határa) → a kliens a `starts_at` alapján rendez.

### 3.4 A tartalom

| Method | Path | Leírás | Funkció |
|---|---|---|---|
| GET | `/api/v1/content/{key}` | egy tartalmi kulcs fordítása — **csak `status='published'`** | F-NF-01…15 |
| GET | `/api/v1/articles` | a blog cikkei (lapozva, `status=published` csak) | F-H-01… |
| GET | `/api/v1/articles/{slug}` | egy cikk | |
| GET | `/api/v1/notices` | a hivatalos ertesitések — **R3** (a F-CNT-03 prioritása S) | |
| GET | `/api/v1/events` | az események — **R3** (a F-CNT-04 prioritása S) | |
| GET | `/api/v1/gauges` | a vízállás-mérő pontok — **R3** (a mérőpontok nem az R1-es funkciólista része) | |

### 3.5 A visszajelzés (F-DET-11)

> **A `POST /feedback` teljes szerződése** (a `prof` reviewer M-7
> findingje után):
>
> | A szempont | A döntés |
> |---|---|
> | A válasz | **`201 Created`**, a `Location: /api/v1/feedback/{id}` headerrel, a body: `{"id": <uuid>, "status": "new"}` |
> | A `body` méretkorlátja | **2 000 karakter** (a FastAPI `Field(max_length=2000)`) + az `nginx` `client_max_body_size 16k` a `/api/v1/feedback` útvonalon |
> | A `category` | a `feedback.category` CHECK tükröze: `data_correction` \| `translation` \| `map` \| `source` \| `feature` \| `other` (a `schemas/enums.py` a CHECK-ből generálva) |
> | A `status` | az alapérték **`new`** (a `02` §6.3 alapértéke) → a F-ADM-04 szerkesztői listája erre szűr |
> | Az `user_id` | `NULL` (a bejelentkezés nélküli `POST`-nál) → a `user_id` oszlop nullable |
> | A kvóta | a 5/óra rate limit (a `01` – stack-terv §4.5) — a `POST /feedback` mellett, a `403`/`429` a §7 szerint |


| Method | Path | Leírás | Auth |
|---|---|---|---|
| POST | `/api/v1/feedback` | a felhasználói észrevétel | **anonim is lehet** |

**A `POST /api/v1/feedback` a nyilvános API egyetlen író végpontja.**
A `user_id` nullable (a séma szerint) — ha nincs session, a `user_id` NULL,
és a `feedback` a későbbi feldolgozáshoz a `category` és a `body` alapján
rendezhető.

**A rate limit:** 5 kérés/óra per IP — a visszajelzés spambarlang.

**A rate limit tulajdonosa a FastAPI** (a `preshaz` reviewer C-4
findingje után) — **nem** az `nginx`.

**Miért nem az nginx?** Az nginx a rate limitet **HTML** hibaoldallal
adja (a default `error_page`), ami **megszérti az RFC 9457
szerződést** — a kliens `application/problem+json`-t várna, és HTML-t
kapna. A FastAPI middleware viszont a `problem+json` formátumban adja
a `429`-et.

**A megvalósítás:** egy **middleware** (a `web` nem érintett):

```python
# apps/api/src/duna/api/v1/feedback.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address, default_limits=[])


@app.post("/api/v1/feedback", status_code=202)
@limiter.limit("5/hour")
async def create_feedback(request: Request, ...):
    ...


@app.exception_handler(RateLimitExceeded)
async def on_rate_limit(request: Request, exc: RateLimitExceeded):
    return problem(
        429, "rate-limited",
        "Túl sok visszajelzés érkezett. Kérjük, próbáld újra később.",
        instance=str(request.url.path),
    )
```

**A `slowapi` a `redis`-es tárolót használja** — de **a 2 GB-os
VPS-en nincs Redis**! A `memory://` tároló **egyetlen worker** esetén
működik, több worker között **nem oszlik meg** → a limit ugyanaz a
processzen belül érvényes, de több worker között nem.

**A megoldás a VPS-en:** a `memory://` tároló **elfogadható**, mert a
`web` és az `api` **egy processzen** fut (a `compose` egy konténerben),
így egy worker. **Ha a skálázás később több workert igényel**, a
tároló Redis-re vált (a `slowapi` támogatja, a `RATE_LIMIT_STORAGE_URL`
env-vel).

**A `Retry-After` header** kötelező a 429-en — a kliens tudja, mikor
próbálhatja újra.

### 3.6 A DB-szerepkör (a `public_api`)

> **A `preshaz` reviewer C-2 findingje után.** A terv eddig nem
> mondta meg, **melyik DB-szerepkörrel** kapcsolódik a belső API a
> adatbázishoz — és a `02`-es terv gronzásai **nem fedték le** a terv
> végpontjait.

**A belső R1 API a `public_api` szerepkörrel kapcsolódik** — ez a
`02`-es terv §9-ben definiált „*a weboldal DB-kapcsolata*".

**A `public_api` által elérhető objektumok** (a `02`-es terv §9):

| Kategória | Objektumok |
|---|---|
| A flotta | `vessel`, `vessel_i18n`, `vessel_alias`, `vessel_identifier`, `vessel_data_origin`, `vessel_ownership`, `vessel_cert`, `vessel_service_period`, `vessel_type`, `vessel_type_i18n` |
| A referenciák | `port`, `port_i18n`, `berth`, `terminal`, `lock`, `lock_i18n`, `lock_status`, `operator`, `operator_i18n`, `basin`, `basin_i18n`, `marina`, `route`, `route_i18n`, `route_stop`, `cargo_type`, `cargo_type_i18n` |
| A tartalom | `content_key`, `content_text`, `notice`, `notice_i18n`, `notice_type`, `event`, `event_i18n`, `event_type`, `article`, `article_i18n`, `article_category` |
| A földrajz | `country`, `waterway`, `waterway_i18n`, `river_section`, `river_section_i18n`, `gauge`, `gauge_i18n`, `water_level`, `data_source` |
| A pozíció | `position` (a `vessel_last_position` nézet alaptáblája) |
| **A nézetek** | `vessel_verification`, `vessel_last_position`, `vessel_data_origin_current`, `vessel_data_origin_conflicts` |

**A `public_api` csak `SELECT`-et kap** — az egyetlen író végpont a
`POST /api/v1/feedback`, és azt az **`anon`** szerepkör írja (a
`02`-es terv §9: `GRANT INSERT ON feedback TO anon` + a
`feedback_id_seq` USAGE).

**A prof reviewer C-7 findingje után — minden végpont a gronzáson
belül van:** a `public_api` a teljes listát megkapja, **de** a
`content_key`/`content_text` és a `vessel_data_origin` **írás** a
`public_api` útján **nem** történhet (az a szerkesztői réteg):

| A végpont | A `public_api` jog | Megjegyzés |
|---|---|---|
| `GET /api/v1/*` | `SELECT` | a teljes olvasó lista |
| `POST /api/v1/feedback` | `INSERT` (az `anon`role) | az egyetlen író |
| `GET /api/admin/v1/*` | **`nincs`** | a `editor`/`admin` szerepkör |

**A `content_text` írása** (a fordítások szerkesztése) a
`/api/admin/v1/` alatt van — a `02`-es terv §9 szerint az `editor`
szerepkör `INSERT, UPDATE, DELETE` jogot kap a `content_text`-re.
**A `public_api` nem.**

**Az `ais_message_raw` és a `job_run`** — sem a `public_api`, sem az
`anon` nem éri el (a 02-es terv §9).

**A `public_api` NEM éri el:** az `ais_message_raw`-ot, az `audit_log`-ot,
a `job_run`-t, a `data_quality_event`-et, az `app_user`-t (a
jelszó-hash!) és a `translation_task`-ot.

**A `role` megadása a kapcsolatban** (`DATABASE_URL`-ben):
`postgresql://public_api:<jelszó>@db:5432/vessel_tracker`

**A jelszó** a `docker-compose` env-ből jön (`DB_PASSWORD_PUBLIC_API`),
**nem** a repóban.

### 3.7 A szerkesztői API határvonala

**Az R1-ben a szerkesztői végpontok vannak, de külön prefixszel:**

| Prefix | Auth | Ki használja |
|---|---|---|
| `/api/v1/` | nincs (belső) | a `web` SSR |
| `/api/admin/v1/` | **session cookie** (a `app_user`) | a szerkesztői felület |

**A `/api/admin/v1/` a FastAPI alkalmazás része** (a `bori` reviewer
H-6 findingje után) — **nem** a `web` proxyzza.

**A döntés a `01` – stack tervben rögzített** (a v1.3 §4.5/§4.6): a
szerkesztői felület **a FastAPI-on belül** van (a Jinja2 sablonok a
`templates/admin/` alatt), és *„a `web` Astro app **nem** tartalmaz
admin route-ot"*.

**A session-ellenőrzést a FastAPI dependency** végzi — a `401`/`403` a
FastAPI válasza, a `problem+json` formátumban (a §7 szerint). A hálózati
belépést az **`nginx`** zárja (a `01`-es terv §4.2).

**A `web` semmilyen admin útvonalhoz nem nyúl.**

### 3.8 A health, readiness és metrics végpontok

> **A `preshaz` reviewer H-5 findingje után.** Az API-nak **nincs**
> health/readiness végpontja — így a konténer-orchestrator (a
> `compose` healthcheck, a `restart: unless-stopped`) nem tudja
> ellenőrizni, hogy a szolgáltatás valóban kész-e.

| Végpont | Path | A válasz | A célja |
|---|---|---|---|
| **Health** | `GET /health` | `{"status": "ok"}` | a process életben van |
| **Readiness** | `GET /ready` | `{"status": "ok", "checks": {...}}` | a DB elérhető, a pool nem üres |
| **Metrics** | `GET /metrics` | a Prometheus text formátum | a monitoring |

**A readiness a DB-t is ellenőrzi:**

```python
@app.get("/ready", include_in_schema=False)
async def ready(request: Request):
    checks = {}
    try:
        async with db_session() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        logger.warning("readiness: a DB nem elérhető: %s", exc)
        checks["database"] = "unavailable"
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "checks": checks},
        )
    return {"status": "ok", "checks": checks}
```

**A `health` NEM nyúl a DB-hez** — a liveness (a process életben van) és
a readiness (a DB elérhető) **más szempont**. Ha a `health` is
ellenőrizné a DB-t, egy DB-kiesés **restartot** okozna, ami nem
segít (a DB ugyanaz a gép).

**A `compose` healthcheck:**

```yaml
healthcheck:
  test: ["CMD", "curl", "-fsS", "http://localhost:8000/health"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 10s
```

**A `/metrics` a `prometheus-client`** — a `http_request_duration_seconds`
histogrammal (a H-6 findingje), plusz a `process_*` és a
`python_gc_*` metrikákkal.

**A `/metrics` és a `/health` NEM publikálódik** — a `nginx` a
`/health`-et a `127.0.0.1`-re korlátozza, a `/metrics`-et a
monitorozó rendszer olvassa (a 09 – Üzemeltetés terv).

---

## 4. A B2B API (R5) — a szerződés határa

**Az R1-ben a B2B API nem épül ki**, de a **séma és a kód** nem zárja ki:

| Elem | R1 állapot | R5 igény |
|---|---|---|
| `api_client` DB-szerepkor | **létezik** (a 02-es terv §9) | kulcsokhoz kötve |
| `api_key` tábla | **nincs** | R5 |
| `api_quota` / `api_usage` | **nincs** | R5 |
| `Rate-Limit` fejlécek | **nincs** | R5 |
| `OpenAPI` dokumentáció | **belső** (`/internal/openapi.json`) | R5: publikus, a `docs/api/` alatt |

**Amit az R1-ben mindenképp meg kell tenni, hogy az R5 ne törje a
szerződést:**
1. a `/api/v1/` útvonalak **verziózottak** (később `/api/v2/` jöhet)
2. a válaszforma **stabil** (a `data`/`meta` burkoló)
3. **nincs** belső mező a válaszban (F-NF-11) — a `response_model`-ek
   ezt kényszerítik ki, nem a kézi szűrés

---

## 5. A FastAPI struktúra

```
apps/api/src/duna/
├── main.py                 ← az alkalmazás gyökere (a FastAPI app)
├── config.py               ← a pydantic-settings (a 01-es terv §3.2)
├── exceptions.py           ← az RFC 9457 hibakezelés
├── db/
│   ├── session.py          ← a SQLAlchemy engine + a session (a Unit of Work)
│   ├── models.py           ← az ORM modellek (a 02-es sémából generálva)
│   └── uow.py              ← a Unit of Work (a tranzakció-határ)
├── api/v1/
│   ├── vessels.py          ← GET /vessels, /vessels/{id}, …
│   ├── search.py           ← GET /search
│   ├── reference.py        ← GET /ports, /locks, /waterways, …
│   ├── content.py          ← GET /content, /articles, /notices, …
│   └── feedback.py         ← POST /feedback
├── admin/                  ← a szerkesztői végpontok (a 06-os terv)
│   ├── vessels.py
│   ├── translations.py
│   └── imports.py
├── schemas/
│   ├── vessel.py           ← a pydantic modell (a DB → JSON)
│   ├── common.py           ← a Page[T], a ProblemDetail
│   └── enums.py            ← a str enum-ek (a CHECK constraint-ek tükrözése)
├── domain/
│   ├── vessel.py           ← a tiszta üzleti logika (a domain-szabályok)
│   ├── verification.py     ← a bizonyossági szint számítása
│   └── location.py         ← a szöveges „hol van" összeállítása
├── repositories/
│   ├── vessel_repo.py      ← a SQLAlchemy query-k
│   ├── port_repo.py
│   └── content_repo.py
├── services/
│   ├── vessel_service.py   ← a lekérdezések (a SQL itt van, ne a routerben)
│   ├── search_service.py
│   ├── content_service.py  ← a fallback-lánc (a §6.3)
│   └── origin_service.py   ← a mezőnkénti eredet összeállítása (F-DET-15)
├── i18n/
│   ├── __init__.py
│   ├── resolver.py         ← a nyelv kiválasztása (a §6.1)
│   └── fallback.py         ← a fallback-lánc (a §6.3)
├── ingest/                ← az AIS-parser (a 04-es terv)
│   ├── decoder.py          ← a 6 bites dekódolás
│   ├── frames.py           ← a NMEA frame-validáció
│   └── models.py           ← a normalizált rekord (a 02 ↔ 04 szerződés)
└── templates/admin/        ← a szerkesztői felület (a Jinja2 sablonok)
```

> **A `bori` reviewer H-7 findingje után.** Az eredeti terv **saját
> könyvtárszerkezetet** rajzolt fel, ami **nem egyezett** az `01` –
> stack terv §4.2-ben rögzített struktúrával (a sorozat első tagja a
> **mérce**). Most a fenti ábra **az `01`-es tervet követi**:
> a `src/duna/` gyökér, a `config.py` (nem `settings.py`), a `db/`
> (session, modellek, Unit of Work), a `domain/` (a tiszta üzleti
> logika), az `i18n/` (a könyvtár, nem a fájl) és az `ingest/` (a
> `04`-es terv parserének helye).
>
> **A `deps.py` a `main.py` mellett van** — a FastAPI függőségei
> (`Depends`) ott vannak.

### 5.1 A router-vagy-service szabály

**A router nem ír SQL-t.** A router:
1. validálja a query paramétereket (a `Query(...)` és a `Field`)
2. meghívja a service-t
3. visszaadja a `response_model`-t

**A service tartja a lekérdezést**, a repository pedig a SQLAlchemy
query-ket. **A `response_model` kötelező minden végponton** — ez
garantálja a F-NF-11-et (nincs belső mező-kiszivárgás).

### 5.1a A séma → `response_model` lánc (a `preshaz` reviewer C-1 findingje után)

**A `response_model` NEM kézzel írt másolat** — a DB-sémából
**generálódik**, különben a séma és az API között csendben csúszás
lenne.

**A lánc:**

```
Alembic migráció → DB (a séma az egyetlen igazság)
   → datamodel-code-generator → db/models.py (az ORM modellek)
   → a pydantic response_model-ek (a db/models.py-ből generálva)
   → OpenAPI (a kódból) → a TypeScript kliens (az OpenAPI-ból)
```

**A codegen:** a `datamodel-code-generator` (`pydantic` → SQLAlchemy 2.0
ORM modelleket generál a `db/ddl/schema-v1.1.sql`-ből), és a
`pydantic-model-generator` (a SQLAlchemy modellekből pydantic
`BaseModel`-eket).

**A generált fájlok** (`db/models.py`, `schemas/generated.py`)
**a repóban vannak** — a CI a `codegen` után `git diff --exit-code`-tel
ellenőrzi. Ha a séma és a generált modellek eltérnek, **a build
elbukik**.

**A kézzel írt rész** (`schemas/vessel.py`) **csak a kézi mezőket**
tartalmazza (a `VesselListItem`, a `VesselDetail` összeállítás, a
`FieldOrigin`) — a DB-oszlopok a generált modellből jönnek.

**A `db/models.py` a `02`-es terv ORM-reprezentációja** — a séma
migrációkból generálódik, tehát **nincs kézi másolat**.

**A `pydantic` `from_attributes=True`** kötelező a generált modelleken
(a DB-sor → a pydantic objektum konverziója):

```python
# a generált modell tetején
class VesselBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
```

**Egy kézzel írt `response_model` a `db/models.py` mezőit nem
tartalmazza** → a FastAPI `response_model`-ként használható, de a
CI **linter** ellenőrzi, hogy a `response_model` **a generált
oszlopokat tartalmazza-e** (a `model_fields` összevetése a
`db/models.py`-vel).

### 5.2 A katalóguslista eleme (a F-CAT-03)

> **A `bori` reviewer C-1 findingje után.** A terv megmondta, milyen
> szűrőket fogad a `GET /api/v1/vessels`, de **nem mondta meg, mit
> tartalmaz egy listaelem** — a F-CAT-03 (M, R1) öt minimális oszlopot
> ír elő: *hajónév, típus, azonosító, üzemeltető, állapot*.

```python
class VesselListItem(BaseModel):
    """A katalóguslista egy eleme (a F-CAT-03 oszlopai).

    A `GET /api/v1/vessels` és a `GET /api/v1/search` ELEMENTJE is
    ez a modell (a F-SRCH-05 ugyanezeket az oszlopokat kéri).
    """

    id: int
    slug: str
    name: str = Field(description="a hajonév (nem fordul, a latin hivatalos ne)")
    vessel_type_name: str = Field(description="a tipus neve (fordul)")
    identifier: str | None = Field(
        default=None,
        description="""a teruletenkenti azonosito: a Dunan az ENI,
        a Balatonon a hajoszam vagy a nemzeti hajoszam""",
    )
    identifier_type: str | None = Field(
        default=None, description="'eni' | 'national_reg_no' | 'callsign' | …")
    operator_name: str | None = Field(default=None, description="az uzemelteto neve (fordul)")
    operating_area: str = Field(description="'duna' | 'balaton'")
    status: str = Field(description="'active' | 'excluded' | 'inactive' | 'scrapped'")
    verification_level: str = Field(
        description="a bizonyossagi szint (a badge) — a SZAMITOTT ertek")
    verification_source: Literal["computed", "stored_stale"] = Field(
        default="computed",
        description="a badge forrasa; a 'stored_stale' az elterest jelzi")
```

**A mezők forrása (a JOIN-ek):**

| Mező | Forrás | A JOIN |
|---|---|---|
| `id`, `slug`, `status`, `operating_area` | `vessel` | — |
| `name` | `vessel_i18n.name` | `LEFT JOIN vessel_i18n ON (vessel_id, lang)` |
| `vessel_type_name` | `vessel_type_i18n.name` | `JOIN vessel_type` → `LEFT JOIN vessel_type_i18n` |
| `operator_name` | `operator_i18n.display_name` | `LEFT JOIN operator` → `LEFT JOIN operator_i18n` |
| `identifier`, `identifier_type` | `vessel_identifier` | `LEFT JOIN` a területnek megfelelő típusra (`Duna` → `eni`, `Balaton` → `national_reg_no` \| `callsign`) |
| `verification_level` | `vessel.verification_level` | — (a tárolt érték, a §3.1 megjegyzésével) |

**A `meta.total` a szűrés utáni teljes darabszám** — nem a teljes
tábláé.

**A `verification_level` a SZÁMÍTT érték** (a `bori` reviewer C-8
findingje után) — a `vessel_verification.computed_verification_level`
(a 02-es terv §6.2b), **nem** a tárolt `vessel.verification_level`.

**Miért:** a tárolt érték **szabadon beírható** volt → a badge
**hazudhatott** (pl. `ais_identified`, miközben nincs AIS-eredetű
azonosító) — pontosan az a hiba, amit a H-10 finding a sémában
már javított, de a terv újra behozta volna.

**A tárolt érték** csak a **szerkesztői felületen** olvasható (a 06-os
terv) — az elavulás-ellenőrzésre (`is_stale`).

**A `verification_source` mező** megmondja, honnan jött az érték:

| Érték | Jelentés |
|---|---|
| `computed` | a számított érték (a normál eset) |
| `stored_stale` | a tárolt érték **eltér** a számítottól (a szerkesztői felület jelzi) |

### 5.4 A `response_model` és a mezőnkénti eredet (F-DET-15)

A `vessel` adatlap **mezőnkénti eredetet** mutat. Ez nem egy sima
oszlop — a `vessel_data_origin` táblából jön.

```python
class FieldOrigin(BaseModel):
    """A mezőnkénti eredet (a F-DET-15 mezőnkénti eredete).

    A `value_snapshot` az aktualis ertek **ebben az eredetben** — a
    konfliktus (a `prof` reviewer C-3 findingje szerint) csak ezzel
    lathato: ket forras, ket kulonbozo ertek.
    """

    # A FastAPI a `response_model`-t a handler **visszatérési értékéből**
    # építi (§5.1) — ez a service/repo rétegből jön, tehát egy
    # SQLAlchemy ORM-objektum. A Pydantic v2-ben ezért KÖTELEZŐ a
    # `from_attributes=True`, különben a validáció
    # "model_type"-attribute-hibával elhasal.
    # (A `prof` reviewer C-4 findingje.)
    model_config = ConfigDict(from_attributes=True)

    field_name: str
    origin: Literal["ais", "operator_claimed", "official", "editorial"]
    value_snapshot: str | None = Field(
        default=None,
        description="az adott forrastol szarmazo ertek (a konfliktus latatasahoz)")
    observed_at: datetime
    confidence: float | None = None
    source_name: str | None = None
    is_current: bool = Field(
        default=True,
        description="False, ha a forras mar nem aktualis (a tortenet)")

    model_config = ConfigDict(from_attributes=True)

class OwnershipPeriod(BaseModel):
    """Egy tulajdonos periódus (a F-DET-05 hajtörténet blokkja)."""

    operator_name: str = Field(description="az üzemeltető neve (fordul)")
    valid_from: date
    valid_to: date | None = Field(
        default=None, description="None = jelenleg is aktuális")


class VesselDetail(BaseModel):
    # lásd a FieldOrigin kommentjét (a C-4 finding): a FastAPI a
    # handler visszatérési értékéből (ORM-objektum) építi a
    # response_model-t → a from_attributes=True kötelező.
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    mmsi: int | None
    eni: str | None
    verification_level: str = Field(
        description=(
            "a bizonyossagi badge — a SZAMITOTT ertek "
            "(ais_identified|ais_partial|operator_claimed|name_only|unverified; "
            "a 02 §6.2 vessel_verification nezet szamitja, a 05 §8.2 a badge)"
        ))
    verification_source: Literal["computed", "stored_stale"] = Field(
        default="computed",
        description="a badge forrasa; a 'stored_stale' az elterest jelzi")
    status: str
    length_m: Decimal | None
    # …
    origins: list[FieldOrigin] = Field(
        default_factory=list,
        description="A mezőnkénti eredet (F-DET-15).",
    )

    # **A szöveges „hol van"** (a F-DET-06, R1-ben szövegesen).
    # A `02` – DDL-terv §6.3a írja elő a mechanizmust: a
    # `vessel_last_position` nézetből + a `river_section_i18n.name`-ből
    # + a `waterway_i18n.name`-ből áll össze.
    location_text: str | None = Field(
        default=None,
        description="""pl. „Duna, 1642–1635 km, Szob–Budapest szakasz";
        None, ha nincs pozícióadat (a F-DET-16 jelölése)""",
    )
    last_position_ts: datetime | None = Field(
        default=None, description="az utolsó pozíció időbélyege")
    last_river_km: Decimal | None = Field

    # **A CELALLOMAS** (a bori reviewer B-C-3 findingje — a blackboard
    # szerint a 02 v1.6 / a 03 v0.4 / a 06 §4.2 feladata):
    # a funkcióleírás US-04-je („a folyamatban lévő útját és várható
    # érkezését akarom látni") → **a célállomás az egyik fő kérdés**.
    # A mérésben **100%-ban üres** (a `04` v1.0 szerint a FI 10-ből
    # jönne, de a magyar szakaszon a fairway-mező üres) → **a szerkesztő
    # adja meg kézzel** (a `06` §4.2).
    destination: str | None = Field(
        default=None,
        description="a hajó célállomása; None, ha még nincs megadva",
    )
    destination_eta: datetime | None = Field(
        default=None,
        description="a várható érkezés (a FI 10 `eta` mezője)",
    )(
        default=None, description="az utolsó folyó-kilométer")

    # **A hajótörténet** (a F-DET-05): a korábbi nevek külön
    # végponton, a tulajdonosváltások itt.
    ownership: list[OwnershipPeriod] = Field(
        default_factory=list,
        description="a tulajdonosváltások (a dátumtartománnyal)",
    )
```

### 5.5 A burkoló modellek (`schemas/common.py`)

**A `data` mezőnek két típusa van** — lista-válaszon `list[T]`,
objektum-válaszon `T` → **egyetlen `Page[T]` nem elég** (a `prof`
reviewer L-4 findingje). A generikus burkoló:

```python
# schemas/common.py
from pydantic import BaseModel, ConfigDict, Field
from typing import Generic, TypeVar

T = TypeVar("T")


class PageMeta(BaseModel):
    """A lapozás metaadatai."""

    model_config = ConfigDict(from_attributes=True)

    total: int | None = Field(
        default=None,
        description="a szűrés UTÁNI teljes darabszám (a lapozás nélkül); "
                    "a trigram-alapú q-keresésnél null (nem indexelhető)",
    )
    page: int = Field(default=1, description="az oldalszám (1-alapú)")
    per_page: int = Field(default=50, description="az oldal elemszáma")
    has_more: bool = Field(
        default=False, description="van-e a következő oldal")


class ObjectMeta(BaseModel):
    """Az objektum-válasz metaadatai (a lapozás nélkül)."""

    model_config = ConfigDict(from_attributes=True)

    total: int | None = Field(default=None)


class Page(BaseModel, Generic[T]):
    """A lista-válasz burkolója."""

    model_config = ConfigDict(from_attributes=True)

    data: list[T]
    meta: PageMeta


class Data(BaseModel, Generic[T]):
    """Az objektum-válasz burkolója."""

    model_config = ConfigDict(from_attributes=True)

    data: T
    meta: ObjectMeta
```

**A `response_model` a generikus paraméterrel** (`Page[VesselListItem]`,
`Data[VesselDetail]`) — a FastAPI támogatja a generikus
`response_model`-t, és a `data`/`meta` burkoló **nem generálható a
`response_model`-ből, ha nincs két modell** (a C-4 finding).

**A `Decimal` → JSON típus (a M-4 finding döntése):**

A `numeric(6,2)` / `numeric(10,2)` mezők a válaszban **`string`**
(`Decimal` helyett), **nem** `number`:

- a `jsonable_encoder` a `Decimal`-t `float`-ra alakítaná → a
  `deadweight_t` (a `numeric(10,2)`) 100 tonna felett **két tizedespontot
  veszít**;
- a README 4.6 szerint a formázás **kliensoldali**
  (`Intl.NumberFormat`) → a generált TS kliens `string`-et kap, és a
  `packages/shared` formázója formázza;
- a `snake_case` oszlopnevek „gépi leképezés" elve is ezt sugallja
  (a séma `decimal` → a kliens formázza).

A Pydantic modellben ezért:

```python
length_m: str | None = Field(
    default=None, description="a hajó hossza méterben (2 tizedes)")
deadweight_t: str | None = Field(
    default=None, description="a holteher tonnában (2 tizedes)")
```

*(a `db/models.py`-ban a `Decimal` marad — a **DB rétegben** pontos
 kell; a **JSON rétegben** a `str` a formázásra kész érték)*

**A `location_text` összeállítása** (a `02` – DDL-terv §6.3a
előírása szerint — **ez az API-terv feladata**):

```python
def build_location_text(row, section_name: str | None,
                        waterway_name: str) -> str | None:
    """A F-DET-06 szöveges helye: „Duna, 1642–1635 km, Szob–Budapest szakasz".

    A `river_km` a `vessel_last_position` nézetből jön, a szakasz
    neve a `river_section_i18n`-ből (a kért nyelven, a fallback-
    lánccal — a §6.3 szerint).
    """
    if row is None or row.last_river_km is None:
        return None          # nincs pozíció -> a F-DET-16 jelölése
    parts = [waterway_name]
    km = row.last_river_km
    parts.append(f"{km:.0f} km")
    if section_name:
        parts.append(section_name)
    return ", ".join(parts)
```

**A `river_section_i18n.name` a kért nyelven** — a fallback-lánccal
(§6.3), a hiányzó fordításnál az `en`, majd a `hu` szöveg jön
(fallback-lánc).

**A `confidence` nullable** — a séma szerint is.

---

## 6. A lokalizáció az API-ban

### 6.1 A nyelv kiválasztása

**A sorrend (az első nem-null győz):**

1. **a `?lang=` query paraméter** — a `web` **explicit döntése**; a
   README 4.3 szerint *„a weboldal nyelve explicit módon választott, a
   `?lang=` paraméterrel felülírható"* → **ez az elsőbbség**
2. **a `session` / `app_user.locale`** — **csak az `/api/admin/v1/`-en**
   (a bejelentkezett szerkesztő nyelve); a `public_api` nem olvashatja
   az `app_user`-t (a `02` – DDL-terv §9)
3. az `Accept-Language` header (`hu-DE,hu;q=0.9,de;q=0.8`) — **csak
   fallback**, ha nincs explicit kérés. A README 4.3 **ellenzi** a `q=`
   súlyozás használatát (*„nem releváns: a weboldal nyelve explicit
   módon választott"*) → **a header csak az első látogatáskor számít**
4. az alapértelmezés: **`hu`**

**A `?lang=` csak a belső API-n érvényes** — a B2B-nél (R5) a
hivatkozó rögzíti.

> **A `prof` reviewer H-4 findingje:** a korábbi sorrend
> (path prefix → `Accept-Language` → `?lang=`) **az `Accept-Language`
> fejlécet elsődlegessé tette**, ami (a) **mindig** jelen van (a
> böngészők küldik) → **a `?lang=` sosem érvényesülne**, és (b)
> **ellentmondott a README 4.3-nek**. A fenti sorrend a `?lang=`
> elsőbbségét adja — **és ezt a `05` – frontend-terv §3.2-nek is
> követnie kell** (a nyelvválasztó süti **ne** írhassa felül az
> explicit `?lang=`-ot).

### 6.2 Mi fordítódik, mi nem

| Mező | Fordul? | Miért |
|---|---|---|
| `vessel_i18n.name` | **nem** | a hivatalos latin név (a 01-es terv §5.8.4) |
| `vessel_i18n.description` | **igen** | |
| `vessel_type_i18n.name` | **igen** | |
| `port_i18n.name` | **igen** | |
| `river_section_i18n.name` | **igen** | |
| `notice_i18n.title` / `.body` | **igen** | |
| `article_i18n.title` / `.summary` / `.body_md` | **igen** | |
| `content_text.text` | **igen** | |
| `operator_i18n.display_name` | **igen** | |
| A `code` mezők (`vessel_type.code`, `port.code`) | **nem** | az azonosító, nem a megjelenített szöveg |

### 6.2a A publikálási szűrés (a C-5 finding)

**A `GET /api/v1/content/{key}` CSAK a `status='published'` sorokat
szolgálja ki** — a nem publikált (`draft`, `review`) fordítás **nem
látható** a publikus API-n.

**A nem publikált kulcs → 404 `not-found`** (nem 403 — a publikus API
nem árulja el, hogy a kulcs létezik-e csak a szerkesztőknek).

**A `status` a `content_text`-en van** (a PK `(content_key, lang)`),
tehát a szűrés egy `WHERE`-be megy:

```sql
SELECT text FROM content_text
WHERE content_key = :key AND lang = :lang AND status = 'published';
```

**A `Q4` (a 404 vs. a 200+fallback) külön kérdés:** a Q4 a *fordítás*
hiányáról szól (az adott nyelven nincs szöveg), a publikálási állapot
pedig **mindenképp** szűrendő.

### 6.3 A hiányzó fordítás (F-DET-13, F-INTL-05)

**A fallback-lánc** (a README 4.4 rögzíti):

```
a kért nyelv  →  en  →  hu  →  a kód / az eredeti érték
```

**Ha egy szöveg nincs lefordítva a kért nyelvre, a válasz a
fallback-lánc szerinti szöveget tartalmazza a mező helyén** — **nem
`null`-t** (a F-INTL-05: „*a hiányzó fordítás nem jelenik meg üres
mezőként, hanem a forrásnyelv szövegével, jelöléssel*"; a
`release-terv` 3.5 kilépési feltétele: „*Hiányzó fordítás esetén jelölés
jelenik meg, üres mező nincs*").

```json
{
  "data": {
    "name": "TESZTHAJO",
    "description": "Dry cargo vessel"
  },
  "meta": {
    "translation_fallback": {
      "description": { "requested": "de", "used": "en", "fallback": true }
    }
  }
}
```

**A lánc a README 4.4 szerint: `kérés → en → hu → a kód`** — a német
hiányzik, ezért az **angol** (`en`) jön, **nem** a magyar. (A `hu` csak
akkor következik, ha az `en` is hiányzik.)

**A `translation_fallback` a `meta`-ban van**, nem a `data`-ban — így a
kliens nem keveri a „nincs adat" és a „nincs fordítás" esetet. A
`data.description` a **fallback-szöveg**, a `meta` jelzi, hogy **nem a
kért nyelven** érkezett.

**A `null` csak akkor marad**, ha **nincs** fordítás és nincs
fallback-szöveg sem (a kulcs nem létezik egyetlen nyelven sem) — és
akkor a `meta.translation_fallback` **külön jelölést** kap:

```json
{
  "data": { "description": null },
  "meta": {
    "translation_fallback": {
      "description": { "requested": "de", "used": null, "fallback": false,
                       "missing": true }
    }
  }
}
```

**Ez az utolsó eset:** sem a kért nyelven, sem `en`-en, sem `hu`-n
nincs fordítás → a `null` a helyes (a F-DET-16 „adat nélkül" jelölése).

**A `missing: true` a F-DET-16 „adat nélkül" jelölése** — a UI üres
helyett ezt mutatja.

**A megvalósítás** a `content_service.py`-ben — a `content_text`
táblából a kért nyelven, majd az `en`, majd a `hu` sorrendben
(a README 4.4 lánca — az `en` a nemzetközi visszaesés, **a `hu` előtt**):

> **Az `en` a `hu` ELŐTT jön** — a prof reviewer C-2 findingje után
> pontosítva. A korábbi példa a `hu`-t mutatta, ami a README 4.4
> láncát sérti.

**A `*_i18n` tábláknál ugyanígy** — a `vessel_i18n.name` stb. a
`content_text`-hez hasonlóan fut a láncon (a `status='published'`
gating a `content_text`-re vonatkozik, az `*_i18n` tábláknál nincs
publikálási állapot):

```python
FALLBACK_CHAIN = ("en", "hu")

def resolve_text(key: str, lang: str) -> tuple[str | None, dict]:
    """A fallback-lanc: a ker nyelv -> en -> hu -> a kod."""
    for candidate in (lang, *FALLBACK_CHAIN):
        row = db.fetchone(
            "SELECT text FROM content_text WHERE content_key = :k ""
            "AND lang = :l AND status = 'published'",
            {"k": key, "l": candidate},
        )
        if row:
            if candidate == lang:
                return row["text"], {"requested": lang, "used": lang,
                                     "fallback": False}
            return row["text"], {"requested": lang, "used": candidate,
                                 "fallback": True}
    return None, {"requested": lang, "used": None, "fallback": False,
                  "missing": True}
```

**A `status = 'published'` szűrő** minden nyelvnél — a nem
publikált fordítás **nem** szolgálhat fallbacknek.

---

## 7. A hibakódok katalógusa

| `type` utolsó szegmense | HTTP | Mikor |
|---|---|---|
| `not-found` | 404 | a hajó/kikötő nem létezik |
| `validation-error` | 422 | a query paraméter hibás |
| `invalid-query` | 400 | **csak** a FastAPI-val nem validálható paraméterek (a kézzel ellenőrzött, nem whitelistelt `sort`/`order`) |
| ~~`too-short-query`~~ | — | **a katalógusból kikerült** (a H-2 finding) — a `Query(min_length=2)` a `validation-error` (422) formátumot adja |
| ~~`not-found-in-area`~~ | — | **a katalógusból kikerült** (a H-2 finding) |
| `unauthorized` | 401 | a `/api/admin/v1/`-en nincs session |
| `forbidden` | 403 | a szerep nem jogosult |
| `conflict` | 409 | a szerkesztői módosítás ütközik |
| `rate-limited` | 429 | a kvóta exceeded (R5) |
| `service-unavailable` | **503** | az adatbázis nem érhető el (a C-3 finding) |
| `gateway-timeout` | **504** | a query timeout (a `statement_timeout`, a C-3 finding) |
| `internal-error` | 500 | a váratlan hiba |

**A `not-found-in-area` kód KIKERÜLT** (a `bori` reviewer H-2
findingje után). Az eredeti terv szerint a másik területen lévő
találat **külön hibakóddal** jelzett volna — ez **terület-szivárgás**:
a felhasználó megtudta volna, hogy létezik egy ilyen hajó, csak más
vízen. A `release-terv` 3.5 kilépési feltétele ezt kifejezetten tiltja
(„*A Duna- és a Balaton-keresés nem szivárog át a másik területre*").

**A helyes viselkedés:** a keresés a kiválasztott területen fut, és a
válasz **üres lista** — a `meta`-ban egy **`area_hint`**, ami **szám
és azonosító nélkül** jelzi, hogy a másik területen van találat:

```json
{
  "data": [],
  "meta": {
    "area_hint": { "other_area": "duna", "has_matches": true }
  }
}
```

**A felhasználó így tudja, hogy területet kell váltania, de nem tudja
kiderülni, melyik hajóról van szó** — a Balatoni katalógus titka és a
Duna/Balaton elkülönítés egyaránt megmarad.

**A szám nélküli `has_matches`** azért elég: a UI-n a területváltó
gomb (a F-CAT-01) megvan, a felhasználó átválthat.

---

## 8. A specifikáció generálása és a CI

### 8.1 Az OpenAPI-fájl

```bash
# a spec generálása a kódbol (a CI-ban ez a ellenőrzés)
python -m apps.api.scripts.export_openapi docs/api/v1/openapi.json
```

**A spec a kódból generálódik** — nem kézzel írt. A kézzel írt spec
elavul, a kódban a `response_model` az igazság.

### 8.2 A CI-ellenőrzés

| Ellenőrzés | Mi bukik |
|---|---|
| `export_openapi` → `git diff --exit-code docs/api/v1/openapi.json` | a spec nem egyezik a kóddal |
| A `response_model` minden routeren | hiányzik → a linter elbukik |
| A `response_model` nem tartalmaz belső mezőt (`ais_message_raw`, `source_url`, `audit_log`) | szivárgás → a linter elbukik |
| **A codegen után a `db/models.py` és a `schemas/generated.py` egyezik** a `git diff --exit-code`-tel | a séma és a modellek elcsúsztak → a build elbukik |
| **A kézzel írt `response_model` tartalmazza a `db/models.py` minden mezőjét** | a modell elavult → a linter elbukik |
| A `?per_page=200` felső korlát teszt | a limit nem működik → a teszt elbukik |

### 8.3 A `per_page` limit mechanizmusa

```python
PerPage = Annotated[int, Query(ge=1, le=200)]
```

**A FastAPI maga validál** → a `RequestValidationError` → a kivétel-kezelő
a `validation-error` (422) formátumra alakítja. **A `422` a helyes
válasz**, nem a `400` — a FastAPI validációs hibái `422`-ek.

> **A korábbi terv §7.2 a `400`-at írja — itt a `422` a helyes.**
> A `400` a *malformed* kérésre (rossz JSON), a `422` a *szemantikailag
> hibás* paraméterre (a `per_page` 5000) való. A `?per_page=5000` a
> FastAPI `Query(le=200)`-val `422`-t ad.

---

## 9. A teljesítmény

| Végpont | Cél (p95) | Index-megoldás |
|---|---|---|
| `GET /vessels` (szűréssel, lapozva) | **< 300 ms** | a szűrésre: `vessel_area_status_verification_idx`, `vessel_area_operator_idx`, `vessel_area_type_idx`; **a rendezésre: `vessel_area_sort_name_idx`** (a `02`-es terv §5.2 — a `preshaz` H-4 findingje után hozzáadva) |
| `GET /vessels/{id}` | **< 100 ms** | PK |
| `GET /search?q=` (pontos azonosító) | **< 100 ms** | `vessel_identifier` unique index |
| `GET /search?q=` (név, trigram) | **< 200 ms** (a F-NF-03) | `vessel_i18n_name_trgm` GIN |
| `GET /content/{key}` | **< 50 ms** | PK |

**A `meta.total` definíciója:** a **szűrés utáni** teljes darabszám
(nem a teljes tábláé).

**A `q` (trigram) szűrőnél a `COUNT(*)` NEM indexelt** — a teljes
szűkített halmazt kell megszámolni. A flotta mérete (~3 300–3 500
hajó, a README 5.1) ezt elviselhető, **de a keresőnél a `total`
elhagyható** (a F-SRCH-05 találati listája nem kér `total`-t).

**A rendezési indexek** (a `02`-es terv §5.2):

| A `sort` értéke | Az index | Megjegyzés |
|---|---|---|
| `name` (alapértelmezett) | `vessel_area_sort_name_idx` | a `sort_name` oszlopon |
| `length` | `vessel_area_length_idx` | a `length_m` részleges indexe |
| `updated_at` | `vessel_area_updated_idx` | |
| `type` | `vessel_area_type_idx` | a szűrő indexe egyben |
| `operator` | `vessel_area_operator_idx` | a szűrő indexe egyben |

**Az elfogadási kritérium (a H-4 findingje után):**

> A `GET /vessels?area=duna&sort=name` lekérdezés
> `EXPLAIN (ANALYZE, BUFFERS)` kimenete **nem tartalmaz `Seq Scan`-t**
> a `vessel`-en, és a `Rows Removed by Filter` **0**.

**Az API-latencia mérése** (a H-6 findingje után): a
`pg_stat_statements` **DB-oldali** — az API teljes idejét (a
hálózati + a FastAPI + a DB) **nem** méri. A méréshez egy
**alkalmazásoldali metrika** kell — a `prometheus-client` (a
`/metrics` végpont, a H-5 findingje) histogramja a
`http_request_duration_seconds` metrikával (a `method`, a `path`, a
`status` címkékkel).

**A `job_run` az adatfeldolgozás naplója** — nem az API-napló.

**A `slow query`riasztás:** a 09 – Üzemeltetés tervben, `pg_stat_statements`
alapján, 1 s felett.

---

## 10. A nyitott kérdések

| # | Kérdés | Alapértelmezés |
|---|---|---|
| Q1 | A `vessel` lista a `vessel`-táblából olvas, vagy anyagolt nézetből (a `vessel_i18n` join)? | **a `vessel`-táblából** + egy `LEFT JOIN` a `vessel_i18n`-re; az anyagolt nézet R2 |
| Q2 | A `/api/v1/vessels` támogasson mezőválasztást (`?fields=`)? | **nem R1-ben** — a kliens (Astro) szerveroldali renderel, nem kell |
| Q3 | A `moving` szűrő pontosan mi alapján működik R1-ben? | **lezárva** (a `prof` reviewer C-5 findingje után): `status='active'` ∧ `last_position_ts > now() - 24 h` ∧ `sog_mps > 0` — a konstans: `MOVING_FRESHNESS_HOURS = 24` (lásd §3.1) |
| Q4 | A `GET /content/{key}` 404-ot ad, ha a kulcs nincs lefordítva a kért nyelvre, vagy a fallback-metaival 200-at? | **200 + fallback-meta** (a F-DET-13 szerint) |
| Q5 | A B2B API a `/api/v1/`-en osztozik a belsővel, vagy külön `/api/public/v1/`? | ** külön `/api/public/v1/`** (R5) — a belső útvonalak nem kerülnek a publikus szerződésbe |

---

*Ez a terv a `docs/megvalósulas/` sorozat harmadik darabja. Következik: 04 –
AIS-parser specifikáció (a 04 a mérési adatokra vár — az R1-0 alatt készül).*
