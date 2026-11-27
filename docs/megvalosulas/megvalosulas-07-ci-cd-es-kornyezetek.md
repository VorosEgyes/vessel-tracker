# Implementációs terv – 07: CI/CD és környezetek

**Verzió:** 0.4 (2026-11-26 — **a CI/CD él** — a `justfile` a kanonikus
belépési pont, az Alembic-migráció fut, a PostgreSQL custom image
(PostGIS + `pg_cron`) épül, a deploy workflow-k a környezet-ellenőrzéssel
kihagyják a hiányzó VPS-t; **+ a rétegenkénti coverage-kapuk**, **a
`just models-check`** (a modellek–séma drift), **a `just test-integration`
a CI-ben** (a valódi PostgreSQL service-en), **a `just test-app`**
(release-kapu))
**Dátum:** 2026-11-23 (a verzó: 2026-11-26)
**Kapcsolódó dokumentumok:**
[`../README.md`](../README.md) (adatbázis-terv) ·
[`megvalosulas-01-stack-es-struktura.md`](megvalosulas-01-stack-es-struktura.md) (a stack, a struktúra, a környezetek — **ez a terv abból épül**) ·
[`megvalosulas-02-adatbazis-ddl.md`](megvalosulas-02-adatbazis-ddl.md) (a séma, a migrációk) ·
[`megvalosulas-03-api-specifikacio.md`](megvalosulas-03-api-specifikacio.md) (az API-szerződés) ·
[`megvalosulas-04-ais-parser.md`](megvalosulas-04-ais-parser.md) (a parser, a mérési protokoll) ·
[`../ingest-terv.md`](../ingest-terv.md) (az adatút — **v1.1, a méréshez igazítva**) ·
[`../ais-vevo-terv.md`](../ais-vevo-terv.md) (a vevőhálózat) ·
[`../pi-eloallitas.md`](../pi-eloallitas.md) (a Pi előkészítése) ·
[`../release-terv.md`](../release-terv.md) (a kiadási folyamat) ·
[`README.md`](README.md) (a terv-sorozat tagjai)

**Projekt:** `vessel-tracker` — a hajókövető a Dunán és a Balatonon.

> A dokumentum a repóban a `docs/megvalosulas/megvalosulas-07-ci-cd-es-kornyezetek.md`
> útvonalon van — a relatív linkek ehhez képest számolnak.

---

## 1. Mit fed le ez a terv

**A CI/CD és a környezetek** — vagyis:

| | |
|---|---|
| **§2** | a környezetek (local / CI / staging / production) és a **környezeti változók** |
| **§3** | a **build** (a monorepo, a `justfile`, a Docker image-ek) |
| **§4** | a **CI pipeline** (a GitHub Actions workflow-ok) |
| **§5** | a **migrációk** (az Alembic, a `pg_cron`, a seed) |
| **§6** | a **deploy** (a staging → production, a rollback) |
| **§7** | a **titkok** (a secret-kezelés) |
| **§8** | a **verifikáció** (a pipeline kötelező lépései) |
| **§9** | a **megfigyelhetőség** a CI-ből (a deploy utáni ellenőrzés) |
| **§10** | a **nyitott kérdések** |

**Amit ez a terv NEM fed le:**
- a **teszt-stratégia** (a `08` – teszt-stratégia terv) — itt csak a
  **CI-ban futó** teszteket említjük;
- az **üzemeltetést** (a `09` – üzemeltetés és observability terv) —
  itt a **deploy** a tárgy;
- a **kód** bármely részletét — ez a tervezés, nem az implementáció.

---

## 2. A környezetek

### 2.1 A négy környezet

| | **local** | **CI** | **staging** | **production** |
|---|---|---|---|---|
| **A DB** | a compose `postgres` (a custom image) | a **testcontainers** PostgreSQL (a PostGIS-sel) | a VPS `postgres` | a VPS `postgres` |
| **A `pg_cron`** | igen (a custom image) | **nem** (a teszt a `DROP PARTITION` SQL-t futtatja közvetlenül) | igen | igen |
| **A MQTT** | a compose `mqtt` (Mosquitto) | **nem** (a parser unit-tesztben) | igen | igen (R2-től) |
| **A fájlok** | `./data/` | a tmp | `/srv/app/data` | `/srv/app/data` |
| **A `ingest`** | a compose `api` | nem | a compose `api` | a compose `api` |
| **A kiadás** | `just up` | a `docker compose build` | a `deploy` script | a `deploy` script |

### 2.2 A környezeti változók

**A `pydantic-settings`** (`apps/api/src/duna/config.py`) olvassa — és
**a `Settings` osztály validálja** (a hiányzó kötelező változó →
**az app induláskor elhal**, nem futás közben).

| A változó | A local | A production | A titok? |
|---|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@postgres:5432/duna` | a VPS hostja + a jelszó | **igen** (a jelszó) |
| `SECRET_KEY` | `dev-not-secret` | 32+ karakteres random | **igen** |
| `DEBUG` | `true` | `false` | nem |
| `ALLOWED_HOSTS` | `localhost,web` | a domainek | nem |
| `CORS_ORIGINS` | `http://localhost:4321` | a `web` originje | nem |
| `INGEST_ENABLED` | `true` | `true` | nem |
| `INGEST_WORKER` | `true` | `true` (R2-től `false`) | nem |
| `STATION_ID` | `1` | a site-hoz tartozó | nem |
| `LOG_LEVEL` | `INFO` | `INFO` | nem |
| `SENTRY_DSN` | üres | a Sentry DSN | **igen** |
| `BACKUP_BUCKET` | üres | az S3/MinIO bucket | **igen** (a kulcs) |

> **A `DATABASE_URL` a `public_api` és az `app_user` szerepkörrel
> kapcsolódik** (a `02` – DDL-terv §9) → **a production jelszó
> külön szerepkörönként** (a `02` §9 szerint a `public_api` csak
> `SELECT`-et kap, az `editor` az író).

### 2.3 A `.env.example`

**A repóban csak a `.env.example`** (a nevekkel, érték nélkül) — **soha
egy valódi `.env`**:
```
# a másolás: cp .env.example .env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/duna
SECRET_KEY=dev-not-secret
DEBUG=true
ALLOWED_HOSTS=localhost,web
CORS_ORIGINS=http://localhost:4321
INGEST_ENABLED=true
INGEST_WORKER=true
STATION_ID=1
LOG_LEVEL=INFO
SENTRY_DSN=
BACKUP_BUCKET=

# a riasztasi watchdog (a 09 §5.1 — a preshaz P-H-10 findingje:
# ezek nelkul a watchdog os.environ[]-en KeyError-rel elhal, es a
# riasztas soha nem megy ki)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
# a vevoheartbeat hatara: R1 = 10 nap, R2 (elo MQTT) = 30 perc
STALE_RECEIVER_INTERVAL=10 days
```

> **A `.gitignore` tartalmazza a `.env`-et** — és **a pre-commit hook
> ellenőrzi**, hogy a `.env` fájl ne kerüljön be (a `02` – DDL-terv
> 4.1a: a `password_hash` és a `session_token_hash` **nem publikus**).
>
> **A `preshaz` reviewer P-H-10 findingje (a 2. kör):** a Telegram-titok
> **hiányoztak** a `.env.example`-ből → **a watchdog a cronból indítva
> az első `os.environ[...]`-nél `KeyError`-rel elhalt** → **a riasztás
> soha nem ment ki** (még a crontábal sem — lásd a P-C-5).
> **A javítás:** a fenti három változó (érték nélkül) a `.env.example`-ben
> → **a `07` §7.2 a VPS-en a `.env`-ből olvassa** → **a `09` §5.1
> `notify()`-ja hiányzó értéknél warninget ad, nem hal meg**.

---

## 3. A build

### 3.1 A `justfile` — a kanonikus parancsok

**A `justfile` a `01` – stack-terv §4.2 szerint a kanonikus belépési
pont** — **a CI is ezt használja** (nem a `docker compose` parancsokat
szórva a workflow-ban).

> **A `justfile` a repo gyökerében van** (a `01` §4.2) — **a `07` §4.2
> CI-jében a `just` NINCS előre telepítve** a GitHub Actions-en →
> **a `extractions/setup-just@v1` action kell** (a 2026-11-24-i
> felfedezés).
>
> **A `pyproject.toml` a `01` §4.2 szerint a repo gyökerében van** →
> **ebből megy a `uv sync`** → **a dev-függőségek (`--extra dev`)
> tartalmazzák a `pgserver`-t** → **a `db/tools/validate_ddl.py` a
> venv-ből indul** → **a `find_psql()` megtalálja a `psql`-t** →
> **a `just ddl-validate` a CI-ban is működik**.

| A parancs | Mit csinál |
|---|---|
| `just setup` | a `.venv` + a `node_modules` létrehozása (`uv sync --extra dev` + `pnpm install`) — **a dev-eszközök is kellnek** (a pytest, a ruff, a mypy, **a `pgserver`** → a `just ddl-validate` a venv-ből indul) |
| `just dev` | a compose `up` a build nélkül + a hot-reload |
| `just up` | a teljes compose (a DB migrációval) |
| `just down` | a compose leállítása (a volume-okkal) |
| `just db-migrate` | az Alembic `upgrade head` (a `db/migrations/` a séma FORRÁSA — a 01 §4.3) |
| `just db-seed` | **a referenciaadat-seed a MIGRÁCIÓBAN van** (a 02 §12) → **a recept no-op** (a `duna.db.seed` modul nem létezik) |
| `just build-frontend` | **a statikus Astro build** → **a `scripts/ci/build_frontend.py`** elindítja a `pgserver`-t + a migrációt + az `uvicorn`-t → **a `getStaticPaths` a valódi API-t hívja** (a 05 §5.2) → **a `API_BASE_URL` a build környezeti változója** (a 05 §5.1) |
| `just db-migrate-down` | az Alembic `downgrade base` (a visszafordítás — a `07` §8.1 8. lépése) |
| `just db-seed` | a referenciaadat-seed (`02` – DDL-terv §12) |
| `just db-reset` | a DB újra (a `down -v` + `up` + migrate + seed) |
| `just test` | a `pytest` (a unit + a property + a komponens) **a coverage flaggel** — **a mérhető részre** (a `domain/` + az `ingest/`) → **a teljes `duna` 85% a `just test-app` (a release-kapu)** |
| `just test-api` | az API-tesztek (a `testcontainers` DB-vel) |
| `just test-frontend` | a `pnpm test` (a Vitest) |
| `just lint-frontend` | a frontend lint (az eslint + a prettier) |
| `just build-frontend` | a frontend statikus build (a `05` §1) |
| `just check-type-case` | a hajótípus-név lista ellenőrzése: a `report_vessels.sh` CASE listája egyezik a `02` seedjével (a `make_type_case.py --check`) |

**A szintenkénti teszt-célok (a `prof` reviewer H-9 findingje — a
`08` – teszt-stratégia-terv §2.1 hét szintet különböztet meg):**

| A parancs | A szint | A `08` §2.1 időigénye |
|---|---|---|
| `just test-unit` | a unit (a `pytest tests/unit`) | ~30 s |
| `just test-domain` | **a `domain/` 90%-os coverage-küszöbe** (a 08 §8.1: a kiemelt modulok szigorúbb határt kapnak, mint a teljes projekt 85%-a) — a `pytest --cov=duna.domain --cov-fail-under=90` | ~10 s |
| `just test-ingest` | **az `ingest/` 90%-os coverage-küszöbe** (a 08 §8.1: az AIS parser, a 04) — a `pytest --cov=duna.ingest --cov-fail-under=90` | ~10 s |
| `just test-property` | a property (a `hypothesis`) | ~20 s |
| `just test-component` | a komponens (a `pytest tests/component`) | ~2 perc |
| `just test-integration` | az integrációs (a **valódi PostgreSQL** — a `DATABASE_URL` a CI service-ből jön) → **a 70%-os alkalmazásréteg-coverage-kapu** (a 08 §8.1) | ~3 perc |
| `just test-e2e` | az e2e (a `playwright`) | ~8 perc |
| `just test-perf` | a teljesítmény (a `locust`) | ~5 perc |
| `just test-regression` | az adat-regresszió (a `08` §7) | ~1 perc |
| `just test-app` | **a TELJES `duna` 85%-os coverage-kapuja** (a 08 §8.1: a release-kapu) — a `just check-release` futtatja | ~4 perc |
| `just test-api` | az API-tesztek (a `testcontainers` DB-vel) | ~3 perc |
| `just test-frontend` | a frontend (a `pnpm test`, a Vitest) | ~1 perc |

**A `just check` — a teljes minőségi kapu egy parancsban** (a `01` –
stack-terv §11.3 és a `08` – teszt-stratégia-terv §6.1 szerint):

```make
# a teljes minőségi kapu (a 01 §11.3 és a 08 §6.1 szerint)
check: lint lint-frontend typecheck test-unit test-property test-component \
       test-domain test-ingest test-integration ddl-validate ddl-diff

# a release teljes kapuja (a 08 §6.1 — hetente)
check-release: check test-e2e test-perf test-regression

# a schema-drift ellenorzese (a 02 §11 — a prof H-12 findingje)
ddl-diff:
    pg_dump --schema-only --no-owner --no-privileges "$$DATABASE_URL" \
      > db/ddl/schema-v1.1.sql
    git diff --exit-code db/ddl/schema-v1.1.sql
```

> **A `prof` reviewer C-3 findingje (a 05–09-es swarm review-ból):**
> a `08` §6.1 a `just check`-et írja elő a kilépési feltételnek, **de a
> `justfile` nem definiálta** → **a kilépési feltétel nem teljesíthető**
> volt. **A fenti `check` cél ezt megoldja** → **és a `07` §8.1
> pipeline-lépései ebből származtatnak**.

**A coverage a `just test` része (a `prof` reviewer H-10 findingje):**

```make
test:
    pytest tests/unit tests/property tests/component --cov=duna       --cov-report=term-missing --cov-fail-under=85
```

> **A `08` §8.1 coverage-küszöböt ír elő (85%, a `domain/` és az
> `ingest/` 90%)** → **ha ez nincs a `just test`-ben, a küszöb soha
> nem ellenőrződik.**
| `just lint` | a `ruff check` + a `ruff format --check` + az `eslint` + a `prettier --check` |
| `just typecheck` | a `mypy` (a `duna` csomagra) + a `tsc --noEmit` |
| `just build` | a Docker image-ek buildje |
| `just openapi` | az OpenAPI export (`docs/api/v1/openapi.json`) |
| `just ddl-validate` | a `db/tools/validate_ddl.py` futtatása (a `02` – DDL-terv §12) |

### 3.1a A DB nélküli fejlesztői kapu (a `pgserver`)

**A `just check` a DB nélkül is zöld kell legyen** (a 07 §3.1: a
fejlesztői kapu) → **a DB-függő lépések a `pgserver`-t indítják** →
**a `DATABASE_URL` megadva** (a CI-ben a PostgreSQL service) → **azt
használják**.

| A recept | A helper | Mit indít |
|---|---|---|
| `just test-integration` | `scripts/ci/run_integration.py` | a `pgserver` + a migráció (`alembic upgrade head`) |
| `just build-frontend` | `scripts/ci/build_frontend.py` | a `pgserver` + a migráció + az `uvicorn duna.main:app` |

**A `run_integration.py` miért kellett:** a 70%-os alkalmazásréteg-
coverage-kapu (a 08 §8.1) **a DB-s integrációs tesztekből mérhető** →
**a `skipif` miatt DB nélkül a tesztek kihúzódtak** → **a gate
69,25%-ra esett** → **a helper a DB-t mindig biztosítja** → **a gate
mindig mérhető** (a CI-ben 88,92%).

**A `build_frontend.py` miért kellett:** a `hajok.astro` a
`getStaticPaths`-ben tölti a katalógust (a 05 §5.2) → **a buildhez
futnia kell egy API-nak** → **a helper elindítja az `uvicorn`-t egy
szabad porton**, megvárja a `/health`-et, majd a `pnpm build`-et
futtatja az `API_BASE_URL`-lel.

**A `pnpm` a NAS konténerben** (a Node 26-ból eltűnt a `corepack`)
→ **`npm install -g --prefix ~/.local pnpm@10.33.0`** →
**a `/opt/data/bin/pnpm` symlinkkel** → **a PATH-on** (a `just` is
ott van).

### 3.1b A fejlesztői előnézet (a `scripts/dev/`)

**A `scripts/dev/` a helyi fejlesztői eszközöket tartalmazza** (nem
a CI-t — a CI a `scripts/ci/`).

| A script | A feladata |
|---|---|
| **`load_measurement.py`** | **a mérési SQLite → a PostgreSQL** → a haj neveket a `decoder.py`-vel dekódolja (a fizikai 6 bites formából) → a `vessel`/`vessel_i18n`/`vessel_identifier` táblákba → **a `sort_name` normalizáltan** (a `02` v1.12) |
| **`preview.py`** | **a `pgserver` + a migráció + a betöltés + az API + a frontend build (a NAS-IP-vel) + a statikus kiszolgálás** → **egy parancs az egész előnézethez** |

```sh
# a NAS-on
cd /opt/data/martin/work/vt-clone
uv run python scripts/dev/preview.py --public-url http://192.168.0.207:8000
```

| A címek | |
|---|---|
| a frontend | `http://192.168.0.207:8931/hu/duna/hajok` |
| az API | `http://192.168.0.207:8000/api/v1/vessels?area=duna` |

> **A portok:** a **8080 a Zigbee2MQTT**, a **8090 a Pi-hole** (a
> NAS-on) → **a `preview.py` a 8931-et használja** → **a port
> ütközésével **egy világos hibát** ad (a `--api-port` /
> `--web-port` opcióval) → **a migráció előtt** (gyors a hiba).

### 3.2 A Docker image-ek

**Három image** (a `01` – stack-terv §6.1):

| A Dockerfile | A base image | A méret |
|---|---|---|
| `infra/docker/postgres/Dockerfile` | `postgis/postgis:16-3.4` + a `postgresql-16-cron` apt csomag | ~450 MB |
| `apps/api/Dockerfile` | `python:3.14-slim` | ~180 MB |
| `apps/web/Dockerfile` | `node:22-alpine` (a build) → `nginx:alpine` (a futás) | ~60 MB |

**A `postgres` custom image** (a `01` – stack-terv §3.2 szerint):
```dockerfile
# **A BASE IMAGE: `postgis/postgis:16-3.7`** (a 2026-11-24-i javítás)
#
# **A korábbi `16-3.4` Debian `bullseye` (11) alapú volt** → a PGDG
# repóban **NINCS `bullseye-pgdg`** (a PGDG megszüntette a Debian 11
# támogatását) → az `apt-get update` **404 Not Found** hibával elbukott
# ("E: The repository 'http://apt.postgresql.org/pub/repos/apt
# bullseye-pgdg Release' does not have a Release file").
#
# **A `16-3.7` a `postgres:16-trixie` (Debian 13) alapú** → a PGDG
# `trixie-pgdg` repója létezik, **ÉS a base image már beállítja**
# (a `/usr/local/share/keyrings/postgres.gpg.asc` kulcs + a
# `/etc/apt/sources.list.d/pgdg.list` forrás) → **a PGDG repo
# beállítása NEM kell külön lépésként.**
FROM postgis/postgis:16-3.7

# A `postgresql-16-cron` (a 02 §12) — **a PGDG repoban van**
# (a 1.6.8-1.pgdg13+3) -> a base image PGDG-forrasa miatt nincs
# szukseg kulon repo-beallitasra.
#
# **A `postgresql-contrib` NEM KELL és NEM LÉTEZIK a PGDG-ben**:
# a PostgreSQL 10+ ota a contrib modulok (a `pg_stat_statements`,
# a 09 §4.1 latencia-metrikahoz) a **fő `postgresql-16` csomagban**
# vannak -> a base image (a `postgres:16-trixie`) MAR tartalmazza oket.
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      postgresql-16-cron; \
    rm -rf /var/lib/apt/lists/*
# a shared_preload_libraries a postgresql.conf-ban:
#   shared_preload_libraries = 'pg_cron,pg_stat_statements'
```

> **A `07` §3.2 eredeti előírása HIBÁS volt** (a 2026-11-24-i
> CI-futas igazolta, három hibával):
> 1. **a `postgis/postgis:16-3.4` Debian bullseye alapú** → a PGDG
>    repóban nincs `bullseye-pgdg` → **a 404**;
> 2. **a `postgresql-contrib` nem létező csomagnév a PGDG-ben** (a
>    Debian bullseye meta-csomagja volt) → a contrib modulok a fő
>    `postgresql-16` csomagban vannak → **a base image már tartalmazza
>    őket**;
> 3. **a PGDG repo beállítása nem kell külön lépésként**, ha a base
>    image trixie (a `postgres:16-trixie` beállítja).
>
> A javított Dockerfile a repóban: `infra/docker/postgres/Dockerfile`.

> **A `pg_cron` a custom imageben kell** — a stock PostGIS image-ben
> **nincs** → a `cron.schedule(...)` hívások `schema "cron" does not
> exist` hibával elhalnának. **A `02` – DDL-terv validátor preprocesszora
> kezeli** (`strip_cron`) → a CI-ban a **custom image** a mérőszám.

**Az `api` image (a multi-stage build):**
```dockerfile
FROM python:3.14-slim AS builder
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
COPY apps/api ./apps/api
RUN uv sync --frozen

FROM python:3.14-slim
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "duna.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

> **A `uv.lock` a reprodukálhatóság kulcsa** — a `uv sync --frozen`
> **nem** frissíti a lockot → **a CI ugyanazt a függőségverziót kapja,
> mint a fejlesztő**.

### 3.3 Az Astro build

**A `web` image a `pnpm build` kimenetét szolgálja ki** — a statikus
fájlok a `nginx`ben, **a szerveroldali szigetek** az
`@astrojs/node` adapterrel (a `01` – stack-terv §3.2 szerint).

> **A `output: 'static'` + a node adapter** kombináció a `05` –
> frontend-terv döntése — a CI a `pnpm build` kimenetét ellenőrzi.

---

## 4. A CI pipeline

### 4.1 A workflow-ok

**Négy workflow**, mind a `.github/workflows/`-ban:

| A workflow | A trigger | A célja |
|---|---|---|
| **`ci.yml`** | `push` (a `main`-re és a PR-ekre), `workflow_dispatch` | a **minőségi kapu** — minden pushra |
| **`build.yml`** | `push` a `main`-re + `release/*` ágra, `workflow_dispatch` | a **Docker image-ek** buildje és pushja a registry-be |
| **`deploy-staging.yml`** | `workflow_run` (a `ci.yml` sikeres után a `main`-en) | a **staging** deploy |
| **`deploy-production.yml`** | `workflow_dispatch` (a `release/*` ágra, **manuális jóváhagyással**) | a **production** deploy |

> **A workflow-fájlok a repóban vannak** (a `.github/workflows/`):
> `ci.yml` · `build.yml` · `deploy-staging.yml` · `deploy-production.yml`
> (a 2026-11-24-i implementáció).
>
> **A `deploy-staging.yml` triggerének egy korlátja:** a GitHub a
> `workflow_run` triggerrel **nem engedi** a `branches:` szűkítést →
> **a branch-szűrés a job `if` feltételében van**
> (`github.event.workflow_run.head_branch == 'main'`).
>
> **A `deploy-production.yml` a `release-terv` 9. szerint:**
> - a trigger `workflow_dispatch` **kézzel** (a `release_branch` és az
>   `image_tag` inputokkal);
> - a **`production` GitHub environment** → **a jóváhagyás a deploy
>   előtt**;
> - **a release branch ellenőrzése** → a `main` nem a productionon
>   van → a release branchnek a `main`-ből kell erednie (a `git
>   merge-base --is-ancestor` ellenőrzés).

> **A production deploy MANUÁLIS** (`workflow_dispatch` +
> a környezet jóváhagyás) — a `release-terv` 9. fejezete szerint a
> release branch a `main`-ből indul, és **csak bugfix megy rá** → a
> deploy **nem** minden pushra megy.

### 4.1a A CI első futása (2026-11-24) — a feltárt hibák

**A négy workflow a repóba került, és a GitHub Actions-en lefutott →
3 valódi hiba → mind javítva (a `main` HEAD-en):**

| A hiba | A tünet | A javítás |
|---|---|---|
| **a `pnpm` hiányzik** | a `lint` job: `Unable to locate executable file: pnpm` | a **`pnpm/action-setup@v4`** action (a `actions/setup-node@v4` **nem** telepíti a `pnpm`-t) |
| **a `pgserver` nem telepíthető** | a `test` job: `Distribution pgserver==0.1.4 … doesn't have a source distribution or wheel for the current platform` → `You're using CPython 3.14 (cp314), but pgserver only has wheels with cp312` | a **`python-version: "3.12"`** a `setup-uv`-ban (a GitHub runner defaultja 3.14) |
| **a GHCR tag nagybetűs** | a `Build`: `invalid tag "ghcr.io/VorosEgyes/…": repository name must be lowercase` | a **`IMAGE_PREFIX: vorosegyes`** (a GHCR a repó nevét kisbetűsíti; a `github.repository_owner` nagybetűs) |

**Két további probléma (nem a workflowban, hanem a repóban):**

| A probléma | A hatás | A javítás |
|---|---|---|
| **a repóban nincs alkalmazáskód** (`apps/web/`, a Dockerfile-ok) — **a `apps/api/` már megvan** (a `03` §3.1) | a `just build` mind elbukna → **a CI a 3. lépésen túl** | **a `justfile` receptjei feltételesek** (`if [ -f … ]`) → **a hiányzó rész kihagyódik, nem bukik el** (a 07 §3.1 elve) |
| **a `db/ddl/schema-v1.1.sql` nem létezett** | a `just ddl-diff` (a 10b. lépés) nem tudta volna ellenőrizni a séma-driftet | **az új `db/tools/gen_ddl.py`** → a `db/ddl/` a **tervből** generálódik → a `--check` a driftet ellenőrzi |

> **A `db/ddl/` generálása a tervből, nem a `pg_dump`-ból:**
> a `02` §11 a `pg_dump`-ot írja elő, **de a CI-ban nincs
> migrate-elt DB** → a `pg_dump` a CI-ban nem futtatható. **A
> kanonikus forrás a `02` – DDL-terv SQL-blokkjaival** →
> a `db/tools/gen_ddl.py` ugyanazt a blokk-kivonást használja, mint
> a `db/tools/validate_ddl.py` → **a validált sémia és a verziózott
> `db/ddl/` garantáltan ugyanaz** → **a `just ddl-diff` valódi
> séma-drift-ellenőrzés.**
>
> **A `just ddl-generate` kötelező a terv módosításakor** — különben
> a `git diff --exit-code` elbukik a CI-ban.

#### A második CI-futás (2026-11-24, a `603c35e0f0` commit után)

**A `test` job SIKERES** (a `pgserver` + a Python 3.12 javítás
működik) → **két új hiba maradt:**

| A hiba | A tünet | A javítás |
|---|---|---|
| **a `pnpm` továbbra is hiányzik** | `Unable to locate executable file: pnpm` — **a `actions/setup-node@v4` a `cache: pnpm` opcióval a pnpm-et KÉRDEZI** a cache beállításakor → a `pnpm/action-setup` **ELŐTT** bukik el | a **`cache: pnpm` kivéve** a `setup-node`-ből (a frontend még nincs a repóban → a cache felesleges) |
| **a `pg_cron` csomag nem telepíthető** | az `apt-get update` → **404 Not Found** → a `postgresql-16-cron` **a PGDG repóban van**, nem a Debian stable-ban | a **PGDG repo** beállítása a Dockerfile-ban (a kulcs + a `apt.postgresql.org` forrás) |
| **a `pytest` INTERNALERROR** | `pytest.PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset` → a `filterwarnings = ["error::DeprecationWarning"]` miatt **hibává** válik | az **`asyncio_default_fixture_loop_scope = "function"`** a `pyproject.toml`-ban |

> **A `07` §3.2 terv hibás volt:** a `postgresql-16-cron` telepítéséhez
> a **PGDG repo kell** → **a terv a Debian stable repóját feltételezte,
> ahol a csomag nincs benne.**

#### A maszkolás megszüntetése (a `pytest_or_skip.py`)

**A korábbi `|| echo "..."` a `justfile`-ban MASZKOLTA a valódi
hibákat:** a pytest exit 3 (belső hiba, a coverage config-hiba) és
exit 4 (a nem létező útvonal) is „sikernek" számított → **a CI zöld
volt, miközben a tesztek egyáltalán nem futottak.**

**Az új `scripts/ci/pytest_or_skip.py`:**
1. a nem létező útvonalakat kiszűri (→ a 4-es exit nem fordul elő);
2. ha nem maradt útvonal → **a lépés kihagyva** (exit 0);
3. a pytest futtatása → **csak az 5-öt (nem gyűjtött teszt) nyeli el**,
   **a 1-est (teszthiba), a 3-asat (belső hiba) és a 4-est átengedi**.

**Az igazolt viselkedés (a kesztyeben):** a valódi teszthiba →
**exit 1** (a CI bukik); a sikeres teszt → exit 0; a nem létező
útvonal → exit 0 (kihagyva).

#### A harmadik CI-futás (2026-11-24, a `cce17c6811` commit után)

**A `test` job ismét SIKERES** → **két új hiba maradt:**

| A hiba | A tünet | A javítás |
|---|---|---|
| **a `ruff` nem telepítve** | a `lint` job: `error: Failed to spawn: 'ruff'` → **a `lint` jobban NEM volt `uv sync`** (csak a `setup-uv`) → a `ruff` a dev-függőségek között van → a venv kell | a **`uv sync --frozen --extra dev`** a `lint` jobba is |
| **a postgres image build** | `E: The repository 'http://apt.postgresql.org/pub/repos/apt bullseye-pgdg Release' does not have a Release file` → **a `16-3.4` Debian bullseye alapú, és a PGDG-ben NINCS `bullseye-pgdg`** (a PGDG megszüntette a Debian 11 támogatását) | a **base image `postgis/postgis:16-3.7`** (a `postgres:16-trixie` alapú) → a PGDG `trixie-pgdg` repója létezik **ÉS a base image már beállítja** |

> **A `postgresql-contrib` NEM LÉTEZIK a PGDG-ben** (a Debian
> bullseye meta-csomagja volt) → a PostgreSQL 10+ óta a contrib
> modulok (a `pg_stat_statements`) a **fő `postgresql-16` csomagban**
> vannak → **a base image már tartalmazza őket** → **a
> `postgresql-contrib` csomagnevet ki kell venni** (különben az
> `apt-get install` elbukna).

**A `pnpm`-hiba javítása működött** (a `pnpm/action-setup` lefutott,
a `cache: pnpm` kivétele megoldotta) → **a `lint` job a `ruff`
telepítése után a lintig jutott.**

#### A negyedik CI-futás (2026-11-24, a `06f1ce4cc0` commit után)

**A postgres image BUILD MŰKÖDIK** (a base image + a csomagnév
javítások) → **a push a registry-be bukott el**:

| A hiba | A tünet | A javítás |
|---|---|---|
| **a registry push** | `failed to authorize: failed to fetch anonymous token ... 403 Forbidden` → **a `postgres` jobban NEM volt `docker/login-action`** (csak az `api`/`web` jobban) | a **`docker/login-action@v3`** a `postgres` jobba is |
| **a `ruff` 6 hibája** | a `lint` job: a `report_range.py` 6 hibája (a `E401`, az `I001`, az `F401`, az `N806`, az `F541`, a `SIM108`) → **a helyi másolat 16 fájlban elmaradt a repótól** → a `ruff` a repóban lévő fájlokat nézi | a javítások a `report_range.py`-ben + **a tiszta klónból dolgozás** |

> **A `ruff format` a MARKDOWN fájlok kódblokkjait is átírja** →
> **a dokumentációk kódmintái nem változhatnak** → a
> `pyproject.toml`-ban az **`extend-exclude = ["*.md", "docs/"]`**.

> **A `build.yml` `api` és `web` jobja** a hiányzó
> `apps/api/Dockerfile`-ra / `apps/web/Dockerfile`-ra hivatkozott →
> **a build feltételes** (a `just build` szabálya szerint) → **a
> Dockerfile-ok megjelenésekor a feltétel automatikusan megszűnik.**

#### Az ötödik CI-futás (2026-11-24, a `a4e5522daf` commit után)

# ✅ A CI TELJESEN ZÖLD

| A job | Az eredmény |
|---|---|
| a `lint` | ✅ **success** (a `ruff check` + a `ruff format --check`) |
| a `test` | ✅ **success** (a `check-type-case`, a `db-migrate`, a `test-reversible`, a `test`, a `ddl-validate`, a `ddl-diff`) |
| a `build` | ✅ **success** (a PostgreSQL custom image) |

# ✅ A BUILD TELJESEN ZÖLD

| A job | Az eredmény |
|---|---|
| a `postgres` | ✅ **success** (a build + a GHCR push) |
| a `api` | ✅ **success** (kihagyva — a Dockerfile még nincs) |
| a `web` | ✅ **success** (kihagyva — a Dockerfile még nincs) |

**A `Deploy staging` két hibát talált:**

| A hiba | A javítás |
|---|---|
| a `pgserver` a deployban is elbukott (a `setup-uv` a Python-verziót nem pinelte) | a **`python-version: "3.12"`** mindkét deploy workflowban |
| a staging/production VPS nincs beállítva (a `STAGING_HOST` var és a `DEPLOY_SSH_KEY` secret hiányzik) → **a deploy minden main-push-nal elbukott** | a **környezet-ellenőrzés** → **a deploy kihagyva** (exit 0), nem hiba |

> **A tanulság:** **a CI és a Build kapu ZÖLD, de a `Deploy staging`
> minden main-pushra indult** → **a hiányzó környezet miatt a
> deploy-nek KIHAGYANDÓ, nem buknia kell.** A `07` §9 szerint a
> staging a release után áll be.

### 4.2 A `ci.yml` — a minőségi kapu

**A `01` – stack-terv §3.2 és a `02` – DDL-terv §12 alapján:**

```yaml
name: CI
on:
  push:
    branches: [main, "release/*"]
  pull_request:
  workflow_dispatch:

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with: {version: "0.5"}
      - uses: actions/setup-node@v4
        with: {node-version: "22", cache: pnpm}
      # **A `just` NINCS elore telepitve a GitHub Actions-en** (a 2026-11-24-i
      # felfedezes) -> a kanonikus parancsokat nem lehet futtatni ->
      # **a workflow-nak telepitenie kell** (a `extractions/setup-just` action
      # vagy a `cargo install`).
      - uses: extractions/setup-just@v1
      - run: pnpm install --frozen-lockfile
      - run: just lint
      - run: just typecheck

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: ghcr.io/baosystems/postgis:16-3.4
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: duna_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with: {version: "0.5"}
      - uses: extractions/setup-just@v1
      - run: uv sync --frozen --extra dev
      # **A hajotipus-nev lista ellenorzese (a 2026-11-24):** a
      # `report_vessels.sh` CASE listaja a 02-es DDL-terv seedjebol
      # generalodik -> **a CI ellenorizze, hogy a riport es a DB
      # egyezzen** (a `make_type_case.py --check`).
      - run: just check-type-case
      - run: just db-migrate
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/duna_test
      # **Az alkalmazasreteg integracios tesztjei** (a 08 §2.1a) ->
      # **a `just db-migrate` MINT letrehozta a semat** ->
      # **a 70%-os alkalmazasreteg-coverage-kapu** (a 08 §8.1)
      - run: just test-integration
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/duna_test
      - run: just test
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/duna_test
      - run: just ddl-validate
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/duna_test
      - run: just ddl-diff
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/duna_test

  build:
    runs-on: ubuntu-latest
    needs: [lint, test]
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v6
        with:
          context: .
          file: apps/api/Dockerfile
          push: false
          tags: duna-api:ci
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

> **A `pg_cron` a CI service-ben NINCS** (a stock PostGIS image) → a
> `just ddl-validate` a `strip_cron` preprocesszort használja (a `02` –
> DDL-terv §12) → **a cron-függvények a CI-ban nem futnak**. **A
> `pg_cron` a custom image-ben fut** → **a production/staging
> smoke tesztje** az (a §9).

### 4.3 A kötelező ellenőrzések (a `branch protection`)

**A `main` védelme** (a GitHub beállításban):
```
✓ ci / lint   — kötelező
✓ ci / test   — kötelező
✓ ci / build  — kötelező
```

> **A blackboard X-5 findingje (a 05–09-es swarm review-ból):** a
> `ci / ddl-validate` **nem létező job** volt a listában → **a
> branch protection egy nem futó ellenőrzést követelt** (a GitHub
> ilyenkor **örökké pending** marad a PR-en → **a `main` merge-je
> lehetetlen**).
>
> **A javítás:** **a `ddl-validate` (és a `ddl-diff`) a `test` job
> része** (a §4.2) → **nincs külön job** → **a három felsorolt
> ellenőrzés mind fut** → **a `main` védelme működik**.

**A `test` job tartalma (a §4.2):** a lint nem, de a tesztek, a
`ddl-validate` **és** a `ddl-diff` mind a `test` jobban fut → **egy
kötelező ellenőrzés, mindent lefed.**

**A `main` védett** — a **force push tiltva** (a GitHub API-n
ellenőrizve: `allow_force_pushes: false`, `allow_deletions: false`).

> **A workflow YAML push a `main`-re a `workflows` scope-ot igényli** —
> a fine-grained PAT-tal **NEM** megy (a GitHub 2023-as védelme) →
> **a workflow-módosításokat a klasszikus PAT-tal kell pusholni**
> (a `docs/workflow_pat` a NAS-on, `workflow` scope-pal).

---

## 5. A migrációk

### 5.1 Az Alembic

| | |
|---|---|
| A belépési pont | `alembic.ini` (a repo-gyökérben) |
| A migrációk | `db/migrations/versions/` |
| A seed | `db/seeds/` (a `02` – DDL-terv §12: a referenciaadatok) |
| **A referencia DDL** | `db/ddl/` (a teljes DDL, olvasható — **nem** a migráció forrása) |

**A `release-terv` 9. fejezete:** „*minden séma-változás
visszafordítható migráció*". → **a `downgrade()` minden migrációban
kötelező** — a CI ezt ellenőrzi:

```python
# apps/api/tests/test_migrations.py
def test_every_migration_is_reversible():
    """Minden migrációnak van a downgrade-je — a release-terv 9. szerint."""
    # a `down_revision` lánc végigkövetése, és a `downgrade()` hívása
    # egy üres DB-n, fordított irányban
```

### 5.2 A `pg_cron` és a partíciók

**A havi partíció-létrehozás a `pg_cron`-nal** történik (a `01` –
stack-terv §3.2) — **a DB-be job, nem az appba**:

```sql
-- a 02-es tervben a partition maintenance
-- A HETI utem a helyes (a 02 §13.3 heti jobot ir, es a 09 §8.1
-- szerint is heti a drop_expired_partitions) → a preshaz P-H-11
-- findingje a 07 §5.2 havi utemet javitotta
SELECT cron.schedule(
  'create-position-partitions',
  '0 3 * * 0',                              -- vasarnap hajnal 3
  $$SELECT duna.create_future_partitions(2);
    SELECT duna.drop_expired_partitions(); $$
);
```

| A heti job két dolgot csinál | Miért heti |
|---|---|
| `create_future_partitions(2)` — a következő **2 hónap** partícióit létrehozza | **soha nem fogyhat el** a partíció (a `02` §13.3) |
| `drop_expired_partitions()` — a **90 napos TTL** lejárt partícióit eldobja | a `09` §8.1 szerint a heti ütem **~1,3 GB/partíció** méretet tart (a havi ütem ~5 GB-ot érne el — a `02` §13.2 5 GB-os riasztási határát azonnal elérné) |

> **A `pg_cron` a `shared_preload_libraries`-ben** (a custom image) →
> **újraindítás nélkül nem érhető el** → a CI a `strip_cron`
> preprocesszort használja.
>
> **A `preshaz` reviewer P-H-11 findingje (a 2. kör):** a `07` §5.2
> **havi** cron-t írt (`0 3 1 * *`) → **a `02` §13.3 heti jobot ír**
> → **a két terv ellentmondott**. **A javítás: a heti ütem** (a fenti
> táblázat szerint) → **a `02`-vel és a `09` §8.1-gyel egyezik**.

### 5.3 A migráció a deploy során

**A migráció a `deploy` script elején fut** — **a kód és az adat
verziója együtt** (a `release-terv` 9.):

```bash
#!/usr/bin/env bash
# infra/deploy.sh — a staging és a production deploy
set -euo pipefail

ENVIRONMENT="${1:?staging|production}"
cd "$(dirname "$0")/.."

echo "==> a compose leállítása (a migráció előtt)"
docker compose -f infra/compose/${ENVIRONMENT}.yml stop api

echo "==> a migráció"
docker compose -f infra/compose/${ENVIRONMENT}.yml run --rm api \
  alembic upgrade head

echo "==> a compose indítása"
docker compose -f infra/compose/${ENVIRONMENT}.yml up -d

echo "==> a health check"
./infra/smoke.sh "${ENVIRONMENT}"
```

> **A `stop` a migráció előtt** — a `pg_cron` és a `pg_dump` miatt
> **a DB ne legyen írás alatt** a migráció alatt.

---

## 6. A deploy

### 6.1 A staging → production lépcső

| A lépés | A staging | A production |
|---|---|---|
| **A trigger** | a `main`-en a `ci.yml` sikere után | **manuális** (`workflow_dispatch` a `release/*` ágon) |
| **A migráció** | igen (a `alembic upgrade head`) | igen |
| **A smoke teszt** | igen | igen (§9) |
| **A rollback** | a `git revert` + a `alembic downgrade` | **a `git revert` + a `alembic downgrade`** — a `release-terv` 9. szerint |
| **a host cron telepítése** | igen (a §6.1a) | igen (a §6.1a) |

### 6.1a A host cron telepítése (a `preshaz` reviewer P-C-5 findingje)

**A `09` – üzemeltetés-terv §5.1 (a watchdog) és §3.1 (a heti mentés)
a **host cron-jára** épül** → **a deploy script telepíti** →
**nem kézi lépés** (különben elcsúszhat).

```bash
# infra/deploy.sh — a cron telepítése (a production VPS-en)
install_crontab() {
  local CRON_FILE=/etc/cron.d/duna-ops
  cat > "$CRON_FILE" <<'CRON'
# a Duna hajokoveto uzemeltetesi feladatai (a 09 — uzemeteles terv)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# a heti teljes mentes (a 09 §3.1) — vasarnap 03:00 (a hétfői lehuzas ELOTT)
17 3 * * 0 root /opt/duna/infra/backup.sh >> /var/log/duna-backup.log 2>&1

# a riasztasi watchdog (a 09 §5.1) — orankent
23 * * * * root /opt/duna/infra/watchdog.py >> /var/log/duna-watchdog.log 2>&1
CRON
  chmod 0644 "$CRON_FILE"
  chown root:root "$CRON_FILE"
}
```

> **A `09` §3.1 szerint a heti mentésnek a deploy ELŐTT kell lennie**
> (a `preshaz` P-M-4 findingje) → **a vasárnapi 03:00** a hétfői
> 04:17-es Pi-lehúzás előtt van → **a mentés friss adatot tartalmaz**.
>
> **A `09` §5.2 A9 (a drill riasztása)** a staging DB `job_run`-ját
> figyeli → **a drill a stagingben fut** (a `09` §3.2 szerint).

### 6.2 A rollback

**A migráció visszafordítható** (a §5.1) → a rollback:
```bash
docker compose -f infra/compose/production.yml stop api
docker compose -f infra/compose/production.yml run --rm api alembic downgrade -1
docker compose -f infra/compose/production.yml up -d
```

> **A `release-terv` 9. fejezete:** a release branch a `main`-ből
> indul, **csak bugfix megy rá** → **a production-on a `main` nincs
> közvetlenül** → a rollback a `release/*` branch újraindításával
> történik.

### 6.3 A feature flag-ek

**A `02` – DDL-terv §6.5 `feature_flag` táblája** — az új funkciók
flaggel kapcsolhatók ki (a `release-terv` 9.).

> **A flag a DB-ben van, nem a kódban** → **a flag átállítása nem
> igényel deploy-t** → a `09` – üzemeltetés terv feladata a kezelése.

---

## 7. A titkok

### 7.1 A GitHub Actions secrets

| A secret | A mire | A megjegyzés |
|---|---|---|
| `PROD_DATABASE_URL` | a production DB (a `public_api` vagy az `editor` szerepkörrel) | **a jelszó a secretben, nem a `settings`-ben** |
| `STAGING_DATABASE_URL` | a staging DB | ugyanaz |
| `PROD_SECRET_KEY` | a FastAPI `SECRET_KEY` | 32+ karakter |
| `SENTRY_DSN` | a Sentry | opcionális |
| `BACKUP_ACCESS_KEY_ID` / `BACKUP_SECRET_ACCESS_KEY` | az S3/MinIO backup | |
| `DOCKERHUB_TOKEN` / `GHCR_TOKEN` | a registry push | |
| `DEPLOY_SSH_KEY` | a deploy a VPS-re | a `ssh-keygen` nyilvános része a `known_hosts`-ba |

> **A `settings` (`DATABASE_URL` stb.) a környezeti változókból jön** —
> **a `pydantic-settings` a hiányzó kötelező változónál elhal az induláskor**.

### 7.2 A VPS-en

**A production compose a titkokat a fájlrendszerből olvassa**:
```
/srv/app/
├── compose.production.yml
├── .env                  ← 0600, a root tulajdona
└── data/
```
**A `.env` a repóból NEM kerül a VPS-re** — a deploy script a
`secrets manager`ből tölti be (a `ansible-vault` vagy a
`SOPS` — a nyitott kérdés, §10).

### 7.3 A local fejlesztés

**A `.env` a `.gitignore`-ban** — és a **pre-commit hook** ellenőrzi:
```bash
# .pre-commit-config.yaml egyik hook-ja
- repo: local
  hooks:
    - id: forbid-env
      name: a .env ne kerüljön be
      entry: bash -c 'if git diff --cached --name-only | grep -q "^\.env$"; then echo "A .env titkot tartalmaz!"; exit 1; fi'
      language: system
      files: ^\.env$
```

### 7.4 A Pi oldali telepítés (a mérési út)

**A Pi-t nem a CI deployolja** — a **mérés** alatt a vevő kézzel
telepített. **A repóban a telepítő scriptek vannak:**
`scripts/ais-receiver/{install_pi_os.sh, make_cloudinit.sh,
install_ais_receiver.sh, start_measurement.sh, ais-fetch-weekly.sh}`.

**A Pi telepítésének lépései (a `pi-eloallitas.md` szerint):**
```bash
# 1. az SD-kártya (a Macről)
sudo bash ~/dev/install_pi_os.sh        # a cloud-init a beállításokat is beírja

# 2. a vevő (a Pi-n)
ssh -X -t miklos@bud01.local 'sudo bash -s' < scripts/ais-receiver/install_ais_receiver.sh

# 3. a mérés indítása
ssh miklos@bud01.local 'PPM=7 sudo -E bash ~/ais-scripts/start_measurement.sh'
```

> **A `PPM` a `rtl_test -p` kalibráció eredménye** — a mérésben **7**
> (a `-M TD` flaggel együtt a jelerősség a stdout JSON-ba kerül).
>
> **A `sudo` jelszó nélkül** a cloud-init miatt → a `PPM=8 sudo -E
> bash …` a **nem interaktív** shellben is működik (a `read` helyett
> az env-variabiló).

### 7.5 A heti lehúzás telepítése (a NAS-on)

**A lehúzás kulcsa a Pi-n van, a fogadó script a NAS-on:**

```bash
# a NAS-on (a hermesadmin userrel)
sudo install -m 755 scripts/ais-receiver/nas_receive_ais.sh \
  /usr/local/bin/nas-receive-ais.sh
sudo mkdir -p /volume1/docker/hermes/data/martin/work/ais-data

# a Pi kulcsának hozzáadása a NAS-on (a command= korlátozással)
echo 'command="sudo -n /usr/local/bin/nas-receive-ais.sh",no-agent-forwarding,no-port-forwarding,no-pty,no-X11-forwarding ssh-ed25519 AAAA... ais-pull@bud01' \
  | sudo tee -a ~/.ssh/authorized_keys > /dev/null
```

> **A `command=` korlátozás a lánc biztonságának kulcsa:** a Pi
> kulcsával a NAS-on **kizárólag a lehúzás futtatható** — minden más
> parancsot a szerver elutasít. **A mérésben ez így van beállítva.**
>
> **A lehúzás a NAS konténerének bind mountjára ír** → a fájl a
> `marton` munkamappájában jelenik meg (`/opt/data/martin/work/ais-data/`).

---

## 8. A verifikáció

### 8.1 A pipeline kötelező lépései (a sorrend)

| A lépés | A parancs | A bukás feltétele | A gyakoriság |
|---|---|---|---|
| **1. a lint** | `just lint` | bármelyik warning | **minden push** |
| **2. a típusellenőrzés** | `just typecheck` | bármelyik hiba | **minden push** |
| **3. az unit tesztek** | `just test-unit` | bármelyik bukás | **minden push** |
| **4. a property tesztek** | `just test-property` | bármelyik bukás | **minden push** |
| **5. a komponens tesztek** | `just test-component` | bármelyik bukás | **minden push** |
| **5b. a domain 90%-os küszöbe** | `just test-domain` | **a coverage < 90%** (a 08 §8.1: a `domain/` szigorúbb határt kap, mint a teljes projekt 85%-a) | **minden push** |
| **5c. az ingest 90%-os küszöbe** | `just test-ingest` | **a coverage < 90%** (a 08 §8.1: az `ingest/` — az AIS parser, a 04 — a legbitebb kód) | **minden push** |
| **6. az integrációs tesztek** | `just test-integration` | bármelyik bukás | **minden push** |
| **7. a DDL-validáció** | `just ddl-validate` | bármelyik constraint-hiba | **minden push** |
| **8. a migráció-visszafordíthatóság** | `just test-reversible` (a `db-migrate` → a `db-migrate-down` → a `db-migrate` ciklus, a táblák számának ellenőrzésével — a `scripts/ci/check_reversible.py`) | bármelyik bukás | **minden push** |

> **A `pg_cron` a CI `test` jobban NINCS** (a stock
> `ghcr.io/baosystems/postgis` image) → **a migráció a `pg_cron`
> hívások nélkül fut** → **a séma a TTL-partíciók cron-jobjaival együtt
> jön létre, de a `cron.schedule` hívások kimaradnak** → **a
> `drop_expired_partitions` a CI-ben nem fut** (a productionben a
> custom image-ben van → a `07` §3.2) → **a `test-reversible` a
> `pg_cron` nélkül is működik** (a `scripts/ci/check_reversible.py` a
> táblák számát ellenőrzi, nem a cron-jobokat).
| **9. az image build** | `docker build` | bármelyik hiba | **minden push** |
| **10. a frontend build** | `pnpm build` | bármelyik hiba | **minden push** |
| **10b. a séma-drift ellenőrzése** | `just ddl-diff` | **bármelyik eltérés** | **minden push** |
| **10c. a hajótípus-lista ellenőrzése** | `just check-type-case` | **a riport és a seed eltérése** | **minden push** |
| **11. az e2e tesztek** | `just test-e2e` | bármelyik bukás | **hetente** |
| **12. a teljesítményteszt** | `just test-perf` | a p95 > 800 ms (a F-NF-01) | **hetente** |
| **13. az adat-regresszió** | `just test-regression` | bármelyik eltérés | **hetente** |

> **A `prof` reviewer H-12 findingje (a 2. kör, BLOKKOLÓ):** a `02` §11
> előírja, hogy a CI a `db/ddl/schema-v1.1.sql`-t **újragenerálja és
> `git diff --exit-code`-tel ellenőrizze** (*„ha eltérés van, a build
> elbukik"*) → **de a pipeline-ban eddig nem volt ilyen lépés** → **a
> séma-drift csendben benne maradt**, és a `db/ddl/` **verziózott
> fájlként** hamissá válhatott (a `03` OpenAPI sémája is a DB-ből
> generálódik).
>
> **A javítás:** a **10b. lépés** (`just ddl-diff`) — a `justfile`-ban
> a `ddl-diff` cél (a `check` cél is hívja) → **a `02` §11 szerinti
> ellenőrzés a `07`-ben is létezik**.

> **A `preshaz` reviewer P-H-1 findingje (a 05–09-es swarm review-ból):**
> a `08` – teszt-stratégia-terv §2.1 **~17 percet** számol a teljes
> szintre → **minden pushra ennyi túlzás** → **a gyors lépések
> (1–10) mindig, a lassúak (11–13) hetente.**
>
> **A gyors lépések (1–10) ideje: ~6 perc** → **elfogadható minden
> pushra**.

**A flake-ek és a gate (a `preshaz` reviewer P-H-7 findingje):**

| A teszt | A retry | A bukás feltétele |
|---|---|---|
| a unit + a property + a komponens | **nincs retry** | bármelyik bukás |
| az integrációs + az e2e | **1 retry** (`pytest-rerunfailures`) | **a retry után is bukik** |

**A flake-ek külön jelölve** (a `pytest` `--reruns` + a CI egy külön
számlálója) → **a havi release a flake-ek számát is nézze**
(a `09` – üzemeltetés-terv §10) → **egy flake nem gyengíti a gate-et,
de látható**.

> **A `08` §8.2 szerint** a CI 2 újrapróbálkozást csinál → **a
> fenti táblázat szűkíti**: **a gyors szintek retry nélkül** (a
> determinisztikusak), **a lassúak 1 retry-val**.

### 8.2 A tesztek CI-ban futása

**A `pytest` a `testcontainers`-szal** (a `01` – stack-terv §3.2) →
**valódi PostgreSQL** a PostGIS-sel → a PostGIS-specifikus rész
(geometria, GiST) is tesztelve van.

> **A `testcontainers` a CI-ban Docker-in-Docker-t igényel** → a
> GitHub Actions ubuntu runneren **működik** (a Docker be van
> építve) → **a service-konténer helyett a `testcontainers` a
> tisztább**.

### 8.3 Az OpenAPI linter

**A `03` – API-terv §5.1a szerint a CI linter ellenőrzi**, hogy a
`response_model`-ek **a generált sémából** jönnek és **nem tartalmaznak
belső mezőt** (`ais_message_raw`, `source_url`, `audit_log`).

```python
# apps/api/tests/test_openapi_contract.py
def test_no_internal_fields_in_responses():
    """A válaszok nem tartalmazhatnak belső mezőt (a 03 F-NF-11)."""
```

---

## 9. A deploy utáni ellenőrzés (a smoke teszt)

**A `infra/smoke.sh`** — a `deploy` script hívja, **a deploy** után:

```bash
#!/usr/bin/env bash
# infra/smoke.sh — a deploy utáni ellenőrzés
set -euo pipefail
BASE="${1:?a base URL}"

echo "==> a health check"
curl -fsS "${BASE}/healthz" | jq -e '.status == "ok"'

echo "==> a katalógus (a Duna)"
curl -fsS "${BASE}/api/v1/vessels?area=duna&per_page=1" \
  | jq -e '.data | length >= 1'

echo "==> a kereső"
curl -fsS "${BASE}/api/v1/search?q=duna&area=duna" | jq -e '.data'

echo "==> a 404 formátuma (a RFC 9457)"
curl -fsS -o /dev/null -w '%{http_code}' "${BASE}/api/v1/vessels/999999" | grep -q 404

echo "==> a DB elérhetőség"
docker compose -f "infra/compose/${BASE}.yml" exec -T postgres \
  pg_isready -U postgres -d duna

echo "==> a pg_cron (a custom image — a CI-ban nem fut)"
docker compose -f "infra/compose/${BASE}.yml" exec -T postgres \
  psql -U postgres -d duna -tAc \
  "SELECT count(*) FROM cron.job WHERE jobname = 'create-position-partitions'"
```

> **A `pg_cron` ellenőrzés a smoke tesztben** — **a CI service-ben
> nincs `pg_cron`** (a stock PostGIS image) → **ez a lépés a
> staging/production custom image-et ellenőrzi**, nem a CI-t.

---

## 10. A nyitott kérdések

| # | Kérdés | Az alapértelmezés | Az állapot |
|---|---|---|---|
| Q1 | **Hol a registry?** (GHCR vagy Docker Hub) | **GHCR** (a GitHub mellett, a `packages` jogosultság a `GITHUB_TOKEN`-nel) | nyitva |
| Q2 | **A `pg_cron` custom image hol épül?** (a CI-ban vagy a release-ben) | **a CI-ban** (`build.yml`) → a registry-be → a compose onnan húzza | nyitva |
| Q3 | **A VPS-en hogyan érkeznek a titkok?** | a **deploy** a CI-ból másolja (a `DEPLOY_SSH_KEY`-vel) → a `.env` a VPS-en 0600 | nyitva — **Miklós döntése** (a `SOPS`/`ansible-vault` alternatíva) |
| Q4 | **A `main` védelem a PR-k review-ját is megköveteli-e?** | **igen** (1 approval) — a `release-terv` 9. szerint a release branch a `main`-ből indul | nyitva |
| Q5 | **Az `ingest` a `api` konténerben fut** (a `01` §6.1) vagy külön? | **az `api` konténerben** (a `01` – stack-terv §6.1) | **lezárva** (a `01` szerint) |
| Q6 | **A nightly build kell?** (a `main`-en a pipeline minden éjjel) | **nem** — a `main` pushra megy; a `release/*` a kiadáskor | nyitva |
| Q7 | **A `docs/api/v1/openapi.json` a repóban van-e?** | **igen, generálva** — a CI a `main`-en frissíti (a `03` – API-terv §8.1) | nyitva — **Miklós döntése** (a generált fájl a repóban vagy a release artifact) |

---

*Ez a terv a `docs/megvalosulas/` sorozat **hetedik** darabja. A `01` –
stack-terv §4.2 már előírta a `07-ci-cd-es-kornyezetek.md` fájl nevét.
Következik: 08 – teszt-stratégia, 09 – üzemeltetés és observability.*
