# Implementációs terv – 03: API-specifikáció (OpenAPI v1)

**Verzió:** 0.2 (az 1. körű swarm review után — 58 finding, 8 blokkoló javítva)
**Dátum:** 2026-11-19
**A pinnelt séma:** `02-adatbazis-ddl.md` **v1.2** (71 tábla, 150 index,
121 FK, 28 trigger) — **a `03` ezen áll**
**Kapcsolódó dokumentumok:**
[`../../README.md`](../../README.md) (adatbázis-terv v1.3) ·
[`01-stack-es-struktura.md`](01-stack-es-struktura.md) (stack + struktúra) ·
[`02-adatbazis-ddl.md`](02-adatbazis-ddl.md) (a séma — ez a szerződés alapja) ·
[`../../docs/funkcio-leiras.md`](../../docs/funkcio-leiras.md) ·
[`../../docs/release-terv.md`](../../docs/release-terv.md) ·
[`README.md`](README.md) (a terv-sorozat tagjai)

**Projekt:** `vessel-tracker` — a hajókövető a Dunán és a Balatonon.

> A dokumentum a repóban a `docs/megvalosulas/03-api-specifikacio.md`
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

### 2.2 A hibák — RFC 9457 (`application/problem+json`)

```json
{
  "type": "https://vessel-tracker.example/probs/not-found",
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

**A `type` URI-privát** (nem a domainre mutat), hogy a példadomain
változása ne törje el a kliensoldali logikát.

### 2.2a A kivétel-kezelés (a `preshaz` reviewer C-3 findingje után)

**A FastAPI globális kivétel-kezelője** (`exceptions.py`) alakítja
**minden** hibát az RFC 9457 formátumra:

```python
# apps/api/src/duna/exceptions.py
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from psycopg import errors as pg_errors


PROBLEM_BASE = "https://vessel-tracker.example/probs/"


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
`per_page` nagyobb értékre hívás → **400**, nem csendes levágás.

**A rendezés:** `?sort=name&order=asc` — a rendezési mezők **whitelistelt**
(több rendezési mező kombinációja R1-ben nem kell).

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

| Method | Path | Leírás | Funkció |
|---|---|---|---|
| GET | `/api/v1/vessels` | a katalógus listája, szűréssel és lapozással | F-CAT-02, F-CAT-08, F-CAT-10, F-CAT-14 |
| GET | `/api/v1/vessels/{id}` | egy hajó adatlapja | F-CAT-06, F-DET-01…16 |
| GET | `/api/v1/vessels/{id}/aliases` | a hajó történeti nevei | F-DET-05 |
| GET | `/api/v1/vessels/{id}/ownership` | a **tulajdonosváltások** (a dátumtartománnyal) | F-DET-05 |
| GET | `/api/v1/vessels/{id}/certificates` | a hajó engedélyei | F-DET-02 |
| GET | `/api/v1/vessels/{id}/identifiers` | az összes azonosító + eredet | F-DET-02, F-DET-15 |
| GET | `/api/v1/vessels/{id}/data-origin` | a mezőnkénti eredet | F-DET-15 |

**A `GET /api/v1/vessels` szűrői (mind a query stringben):**

| Paraméter | Típus | F-CAT / F-SRCH | Példa |
|---|---|---|---|
| `area` | `duna` \| `balaton` — **KÖTELEZŐ** | F-CAT-01, F-SRCH-07 | `duna` |
| `q` | string | F-CAT-09, F-SRCH-01…03 | `HU-DA` |
| `type` | string (a `vessel_type.code`) | F-CAT-08 | `INLAND_CARGO` |
| `operator` | integer (a `operator.id`) | F-CAT-08, F-CAT-11 | `7` |
| `status` | `active` \| `excluded` \| `inactive` \| `scrapped` | F-CAT-08 | `active` |
| `verification` | `ais_identified` \| `ais_partial` \| `operator_claimed` \| `name_only` — a **SZÁMÍTT** érték | F-CAT-14 | `ais_identified` |
| `section` | integer (a `river_section.id`) | F-CAT-08 | `3` |
| `basin` | integer (a `basin.id`) | F-CAT-08 | `1` |
| `season` | `in_season` \| `out_of_season` | F-CAT-05 (Balaton) | `in_season` |
| `sort` | `name` \| `type` \| `operator` \| `length` \| `updated_at` | F-CAT-02 | `name` |
| `order` | `asc` \| `desc` | F-CAT-02 | `asc` |
| `page` | integer ≥ 1 | F-CAT-02 | `1` |
| `per_page` | integer 1…200 | F-CAT-02 | `50` |

> **Az `area` KÖTELEZŐ** (a `bori` reviewer C-7 findingje után). A
> funkcióleírás 7.1 **kategorikusan tiltja** az egységes listát: „*Nincs
> egyetlen `/hajok` lista, amely mindkettőt mutatja*". A hiányzó `area`
> → **400 `invalid-query`** (nem 422 — a `area` nem opcionális, hanem
> hiányzik; a 400 a *malformed* kérésre, a 422 a *szemantikailag
> hibás* értékre vonatkozik). A `/search`-nél ugyanígy.
>
> **A `moving` szűrő NINCS az R1-es szerződésben** (a `bori`
> reviewer C-3 findingje után). A „közlekedő / nem közlekedő"
> megkülönböztetés (a F-CAT-04) R1-ben a **`vessel.status` értékével**
> történik:
>
> | A `status` | A jelentése a katalógusban |
> |---|---|
> | `active` | **közlekedő** — a hajó a rendszerben aktív |
> | `inactive` | **nem közlekedő / állandóan álló** (a kiürített vagy a raktáron álló hajó) |
> | `excluded` | **kizárva** — a fantom-szűrő vagy a kézi kizárás miatt (a `status` nem jelenik meg a katalógusban) |
> | `scrapped` | **kivezetve** |
>
> **A `status=excluded` a szűrőeredménye, nem egy mozgásjelző.** A
> `04` – AIS-parser terv a fantom-szűrő négy szabályát rögzíti (a
> pozíció, a sebesség, az 5+ napos állóhelyzet, a kézi kizáró lista) —
> ezek **a `vessel.status`-ba** írnak, nem külön flagbe.
>
> **A `moving` név félreérthető lenne:** a hajó éppen kikötőben lehet, de
> közlekedő — a mozgás nem a `status` tulajdonsága. Az R2-ben, az élő
> pozícióval, lesz valódi mozgásszűrő (a `vessel_last_position` alapján,
> `sog_mps > 0.5`).
>
> **A `season` szűrő** a `vessel_service_period` táblából számít: a
> `season_start`/`season_end` és a `service_status` alapján a
> `service_status='seasonal'` hajók esetén.

### 3.2 A kereső

| Method | Path | Leírás | Funkció |
|---|---|---|---|
| GET | `/api/v1/search` | a globális kereső | F-SRCH-01…07 |
| GET | `/api/v1/search/suggest` | a gyorskereső javaslatai (R3) | F-SRCH-08 |

**A `GET /api/v1/search` viselkedése:**

```
GET /api/v1/search?q=12345678&area=duna
```

1. **először pontos azonosító-egyezés** (F-SRCH-02): az `eni`, a `mmsi`,
   az `imo`, a `callsign` a `vessel_identifier`-ben
2. **aztán név-egyezés** (F-SRCH-03): prefix/szubsztring, trigram index,
   ékezet- és kis-nagybetű-független (`unaccent` + `lower`)
3. **a terület szűkít** (F-SRCH-04, F-SRCH-07): a `duna` keresés **soha**
   nem talál Balaton-hajót

**A `q` minimális hossza 2 karakter** — 1 karakterre **422**.

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

### 3.4 A tartalom

| Method | Path | Leírás | Funkció |
|---|---|---|---|
| GET | `/api/v1/content/{key}` | egy tartalmi kulcs fordítása — **csak `status='published'`** | F-NF-01…15 |
| GET | `/api/v1/articles` | a blog cikkei (lapozva, `status=published` csak) | F-H-01… |
| GET | `/api/v1/articles/{slug}` | egy cikk | |
| GET | `/api/v1/notices` | a hivatalos ertesitések | |
| GET | `/api/v1/events` | az események | |
| GET | `/api/v1/gauges` | a vízállás-mérő pontok | |

### 3.5 A visszajelzés (F-DET-11)

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
    field_name: str
    origin: Literal["ais", "operator_claimed", "official", "editorial"]
    observed_at: datetime
    confidence: float | None = None
    source_name: str | None = None

class OwnershipPeriod(BaseModel):
    """Egy tulajdonos periódus (a F-DET-05 hajtörténet blokkja)."""

    operator_name: str = Field(description="az üzemeltető neve (fordul)")
    valid_from: date
    valid_to: date | None = Field(
        default=None, description="None = jelenleg is aktuális")


class VesselDetail(BaseModel):
    id: int
    name: str
    slug: str
    mmsi: int | None
    eni: str | None
    verification_level: str = Field(
        description="a bizonyossagi badge — a SZAMITOTT ertek")
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
    last_river_km: Decimal | None = Field(
        default=None, description="az utolsó folyó-kilométer")

    # **A hajótörténet** (a F-DET-05): a korábbi nevek külön
    # végponton, a tulajdonosváltások itt.
    ownership: list[OwnershipPeriod] = Field(
        default_factory=list,
        description="a tulajdonosváltások (a dátumtartománnyal)",
    )
```

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

1. a path prefix (`/api/v1/hu/...`)? — **R1-ben nincs**, a `web` adja át
2. az `Accept-Language` header (`hu-DE,hu;q=0.9,de;q=0.8`)
3. a `?lang=` query paraméter
4. az alapértelmezés: **`hu`**

**A `?lang=` csak a belső API-n érvényes** — a B2B-nél (R5) a
hivatkozó rögzíti.

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

**A `missing: true` a F-DET-16 „adat nélkül" jelölése** — a UI üres
helyett ezt mutatja.

**A megvalósítás** a `content_service.py`-ben — a `content_text`
táblából a kért nyelven, majd az `en`, majd a `hu` sorrendben:

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
| `invalid-query` | 400 | a `per_page` > 200, a `sort` nem whitelistelt |
| `too-short-query` | 422 | a `q` 1 karakter |
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
| Q3 | A `moving` szűrő pontosan mi alapján működik R1-ben? | a fantom-szűrő kimenete (a `04` – AIS-parser terv); **a `04`-ig nyitott** |
| Q4 | A `GET /content/{key}` 404-ot ad, ha a kulcs nincs lefordítva a kért nyelvre, vagy a fallback-metaival 200-at? | **200 + fallback-meta** (a F-DET-13 szerint) |
| Q5 | A B2B API a `/api/v1/`-en osztozik a belsővel, vagy külön `/api/public/v1/`? | ** külön `/api/public/v1/`** (R5) — a belső útvonalak nem kerülnek a publikus szerződésbe |

---

*Ez a terv a `docs/megvalósulas/` sorozat harmadik darabja. Következik: 04 –
AIS-parser specifikáció (a 04 a mérési adatokra vár — az R1-0 alatt készül).*
