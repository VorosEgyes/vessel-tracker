# Implementációs terv – 03: API-specifikáció (OpenAPI v1)

**Verzió:** 0.1 (terv-draft, swarm review előtt)
**Dátum:** 2026-11-16
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
| **Nincs belső adat-kiszivárgás** | a `ais_message_raw`, a `job_run`, a `data_quality_event`, a `audit_log`, a `source_url` **nem** jelenik meg a válaszban |
| **Visszafelé kompatibilitás** | egy mező eltávolítása a `/v1/`-ben **tiltott**; a mező elavul → `deprecated: true` a OpenAPI-ban, és egy évig működik |
| **A hibakódok stabilak** | a `type` URI és a hibakódok változatlanok |
| **A válaszidő** | a katalógus-lekérdezés p95 < 300 ms (a README 9. fejezete) |

---

## 3. A belső API végpontjai (R1)

### 3.1 A katalógus

| Method | Path | Leírás | Funkció |
|---|---|---|---|
| GET | `/api/v1/vessels` | a katalógus listája, szűréssel és lapozással | F-CAT-02, F-CAT-08, F-CAT-10, F-CAT-14 |
| GET | `/api/v1/vessels/{id}` | egy hajó adatlapja | F-CAT-06, F-DET-01…16 |
| GET | `/api/v1/vessels/{id}/aliases` | a hajó történeti nevei | F-DET-05 |
| GET | `/api/v1/vessels/{id}/certificates` | a hajó engedélyei | F-DET-02 |
| GET | `/api/v1/vessels/{id}/identifiers` | az összes azonosító + eredet | F-DET-02, F-DET-15 |
| GET | `/api/v1/vessels/{id}/data-origin` | a mezőnkénti eredet | F-DET-15 |

**A `GET /api/v1/vessels` szűrői (mind a query stringben):**

| Paraméter | Típus | F-CAT / F-SRCH | Példa |
|---|---|---|---|
| `area` | `duna` \| `balaton` | F-CAT-01, F-SRCH-07 | `duna` |
| `q` | string | F-CAT-09, F-SRCH-01…03 | `HU-DA` |
| `type` | string (a `vessel_type.code`) | F-CAT-08 | `INLAND_CARGO` |
| `operator` | integer (a `operator.id`) | F-CAT-08, F-CAT-11 | `7` |
| `status` | `active` \| `excluded` \| `inactive` \| `scrapped` | F-CAT-08 | `active` |
| `verification` | `ais_identified` \| `ais_partial` \| `operator_claimed` \| `name_only` | F-CAT-14 | `ais_identified` |
| `section` | integer (a `river_section.id`) | F-CAT-08 | `3` |
| `basin` | integer (a `basin.id`) | F-CAT-08 | `1` |
| `moving` | boolean | F-CAT-04 | `true` |
| `season` | `in_season` \| `out_of_season` | F-CAT-05 (Balaton) | `in_season` |
| `sort` | `name` \| `type` \| `operator` \| `length` \| `updated_at` | F-CAT-02 | `name` |
| `order` | `asc` \| `desc` | F-CAT-02 | `asc` |
| `page` | integer ≥ 1 | F-CAT-02 | `1` |
| `per_page` | integer 1…200 | F-CAT-02 | `50` |

> **A `moving` és a `season` szűrő a statikus kivonatból számít.**
> Az R1-ben nincs élő pozíció, ezért a „közlekedő / nem közlekedő"
> megkülönböztetés (F-CAT-04) a **friss identitási adatkörből**
> (a `vessel.status` + az utolsó AIS-aktivitás) jön. A pontos
> mechanizmus — a fantom-szűrő kimenete — a `04` – AIS-parser
> specifikáció tárgyalja.

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
| GET | `/api/v1/content/{key}` | egy tartalmi kulcs fordítása | F-NF-01…15 |
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

### 3.6 A szerkesztői API határvonala

**Az R1-ben a szerkesztői végpontok vannak, de külön prefixszel:**

| Prefix | Auth | Ki használja |
|---|---|---|
| `/api/v1/` | nincs (belső) | a `web` SSR |
| `/api/admin/v1/` | **session cookie** (a `app_user`) | a szerkesztői felület |

**A `/api/admin/v1/` nem publikálódik** — a `web` proxyzza, és a proxy
ellenőrzi a sessiont is (a `401`-et a proxy adja, nem a FastAPI).

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
apps/api/
├── main.py                 ← az alkalmazás gyökere
├── deps.py                 ← a függőségek (session, db, lang, pagination)
├── settings.py             ← a pydantic-settings (a 01-es terv §3.2)
├── i18n.py                 ← a nyelv kiválasztása (a header / a path / a query)
├── exceptions.py           ← az RFC 9457 hibakezelés
├── routers/
│   ├── v1/
│   │   ├── vessels.py      ← GET /vessels, /vessels/{id}, …
│   │   ├── search.py       ← GET /search
│   │   ├── reference.py    ← GET /ports, /locks, /waterways, …
│   │   ├── content.py      ← GET /content, /articles, /notices, …
│   │   └── feedback.py     ← POST /feedback
│   └── admin/
│       └── v1/
│           ├── vessels.py  ← a szerkesztői CRUD (a 06-os terv)
│           ├── translations.py
│           └── import.py  ← a tömeges import (a 06-os terv)
├── schemas/
│   ├── vessel.py           ← a pydantic modell (a DB → JSON)
│   ├── common.py           ← a Page[T], a ProblemDetail
│   └── enums.py            ← a str enum-ek (a CHECK constraint-ek tükrözése)
├── services/
│   ├── vessel_service.py   ← a lekérdezések (a SQL itt van, ne a routerben)
│   ├── search_service.py
│   ├── i18n_service.py
│   └── origin_service.py   ← a mezőnkénti eredet összeállítása (F-DET-15)
└── repositories/
    ├── vessel_repo.py      ← a SQLAlchemy query-k
    └── ...
```

### 5.1 A router-vagy-service szabály

**A router nem ír SQL-t.** A router:
1. validálja a query paramétereket (a `Query(...)` és a `Field`)
2. meghívja a service-t
3. visszaadja a `response_model`-t

**A service tartja a lekérdezést**, a repository pedig a SQLAlchemy
query-ket. **A `response_model` kötelező minden végponton** — ez
garantálja a F-NF-11-et (nincs belső mező-kiszivárgás).

### 5.2 A `response_model` és a mezőnkénti eredet (F-DET-15)

A `vessel` adatlap **mezőnkénti eredetet** mutat. Ez nem egy sima
oszlop — a `vessel_data_origin` táblából jön.

```python
class FieldOrigin(BaseModel):
    field_name: str
    origin: Literal["ais", "operator_claimed", "official", "editorial"]
    observed_at: datetime
    confidence: float | None = None
    source_name: str | None = None

class VesselDetail(BaseModel):
    id: int
    name: str
    slug: str
    mmsi: int | None
    eni: str | None
    verification_level: str
    status: str
    length_m: Decimal | None
    # …
    origins: list[FieldOrigin] = Field(
        default_factory=list,
        description="A mezőnkénti eredet (F-DET-15).",
    )
```

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

### 6.3 A hiányzó fordítás (F-DET-13)

**Ha egy szöveg nincs lefordítva a kért nyelvre, a válasz tartalmazza:**

```json
{
  "data": { "name": "TESZTHAJO", "description": null },
  "meta": {
    "translation_fallback": {
      "description": { "requested": "de", "available": "hu" }
    }
  }
}
```

**A `translation_fallback` a `meta`-ban van**, nem a `data`-ban — így a
kliens nem keveri a „nincs adat" és a „nincs fordítás" esetet. A
`null` + a fallback-meta együtt jelzi: *a lefordított szöveg hiányzik, de
van másik nyelven*.

---

## 7. A hibakódok katalógusa

| `type` utolsó szegmense | HTTP | Mikor |
|---|---|---|
| `not-found` | 404 | a hajó/kikötő nem létezik |
| `validation-error` | 422 | a query paraméter hibás |
| `invalid-query` | 400 | a `per_page` > 200, a `sort` nem whitelistelt |
| `too-short-query` | 422 | a `q` 1 karakter |
| `not-found-in-area` | 404 | a keresés a másik területen lenne |
| `unauthorized` | 401 | a `/api/admin/v1/`-en nincs session |
| `forbidden` | 403 | a szerep nem jogosult |
| `conflict` | 409 | a szerkesztői módosítás ütközik |
| `rate-limited` | 429 | a kvóta exceeded (R5) |
| `internal-error` | 500 | a váratlan hiba |

**A `not-found-in-area` külön kód** — a F-SRCH-04 szerint a Balaton-keresés
nem talál Duna-hajót, és a kliens ezt **másként kezeli**, mint a
teljesen ismeretlen azonosítót (a felajánlott lépések mások).

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
| A `?per_page=200`上限 teszt | a limit nem működik → a teszt elbukik |

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
| `GET /vessels` (szűréssel, lapozva) | **< 300 ms** | `vessel` composite index a szűrőkre + a `vessel_i18n` trigram |
| `GET /vessels/{id}` | **< 100 ms** | PK |
| `GET /search?q=` (pontos azonosító) | **< 100 ms** | `vessel_identifier` unique index |
| `GET /search?q=` (név, trigram) | **< 400 ms** | `vessel_i18n_name_trgm` GIN |
| `GET /content/{key}` | **< 50 ms** | PK |

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
