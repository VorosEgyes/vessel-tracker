# A vessel-tracker kanonikus parancsai
#
# A `justfile` az `01` – stack-terv §4.2 szerint a belépési pont: a CI
#
# A parancsok a `07` – CI/CD-terv §3.1 szerint, a `08` – teszt-stratégia
#

set shell := ["bash", "-euo", "pipefail", "-c"]

# a Python interpreter (a venv-ből) — a `uv run` biztosítja, hogy a
UV := "uv run"

# a compose fájlok (a 07 §4.2)
COMPOSE_LOCAL := "infra/compose/local.yml"
COMPOSE_STAGING := "infra/compose/staging.yml"
COMPOSE_PRODUCTION := "infra/compose/production.yml"

# a DDL referencia fájl (a 02 §11)
DDL_REF := "db/ddl/schema-v1.1.sql"

# a coverage küszöb (a 08 §8.1)
COVERAGE_MIN := "85"

# a teszt-útvonalak (a 08 §2.1)
TESTS := "apps/api/tests"

# A KÖRNYEZET

# a helyi fejlesztői környezet előkészítése
setup:
    uv sync --extra dev
    # a `uv sync --extra dev` a dev-eszkozoket is telepiti (a pytest, a
    # ruff, a mypy, a pgserver) -> a `just ddl-validate` is fut
    pnpm install
    @echo "a venv és a node_modules kesz"
    @echo "  a DDL-validacio: just ddl-validate"
    @echo "  a teljes minosegi kapu: just check"

# a compose indítása a build nélkül + a hot-reload
dev:
    docker compose -f {{COMPOSE_LOCAL}} up

# a teljes compose (a DB migrációval)
up: db-migrate
    docker compose -f {{COMPOSE_LOCAL}} up --build

# a compose leállítása (a volume-okkal)
down:
    docker compose -f {{COMPOSE_LOCAL}} down -v


# az Alembic migrációk futtatása
db-migrate:
    {{UV}} alembic upgrade head

# a referenciaadat-seed (a 02 §12)
db-seed:
    {{UV}} python -m duna.db.seed

# a DB újra (a down -v + up + migrate + seed)
# a DB ujra (a down -v + up + migrate + seed)
db-reset: down up
    {{UV}} python -m duna.db.seed
    @echo "az adatbazis ujraindult (a migracio a `up` reszeben, a seed utana)"

#
# a DDL-validacio: a DDL futtatasa egy elo PostgreSQL-en + a fustteszt
ddl-validate:
    {{UV}} python db/tools/validate_ddl.py --no-gis
    # a fustteszt MINDIG fut (a `--keep` csak a schema megtartasa)

# a séma-drift ellenőrzése (a 02 §11): a generált DDLnek meg kell
ddl-diff:
    pg_dump --schema-only --no-owner --no-privileges "$$DATABASE_URL" \
      > {{DDL_REF}}
    git diff --exit-code {{DDL_REF}}

# A MINŐSÉGI KAPU (a lint + a típusellenőrzés)

# a Python lint (a ruff)
lint:
    {{UV}} ruff check .
    {{UV}} ruff format --check .

# a frontend lint (az eslint + a prettier)
lint-frontend:
    pnpm lint
    pnpm format:check

# a típusellenőrzés (a mypy + a tsc)
typecheck:
    {{UV}} mypy apps/api/src/duna
    pnpm typecheck

# A TESZTEK (a 08 §2.1 hét szintje)

# a unit tesztek (a tiszta függvények)
test-unit:
    {{UV}} pytest {{TESTS}}/unit

# a property tesztek (a hypothesis round-trip)
test-property:
    {{UV}} pytest {{TESTS}}/property

# a komponens tesztek (a service-ek a DB-vel)
test-component:
    {{UV}} pytest {{TESTS}}/component

# az integrációs tesztek (a testcontainers + a PostGIS)
test-integration:
    {{UV}} pytest {{TESTS}}/integration

# az e2e tesztek (a playwright)
test-e2e:
    pnpm test:e2e

# a teljesítményteszt (a locust; a F-NF-01: a p95 < 800 ms)
test-perf:
    {{UV}} locust -f tests/perf/locustfile.py --headless

# az adat-regresszió (a mérési adat a baseline, a 08 §7)
test-regression:
    {{UV}} pytest {{TESTS}}/regression

# az API-tesztek (a testcontainers DB-vel)
test-api:
    {{UV}} pytest {{TESTS}}/api

# a frontend tesztek (a Vitest)
test-frontend:
    pnpm test

# a teljes tesztkészlet a coverage flaggel (a 08 §8.1 küszöb: 85%)
test:
    {{UV}} pytest {{TESTS}}/unit {{TESTS}}/property {{TESTS}}/component \
      --cov=duna --cov-report=term-missing --cov-fail-under={{COVERAGE_MIN}}

# a migráció-visszafordíthatóság (a 07 §8.1 8. lépése)
test-reversible:
    {{UV}} pytest -k reversible

# A KAPUK

# a teljes minőségi kapu egy parancsban (a 01 §11.3 és a 08 §6.1)
check: lint lint-frontend typecheck test-unit test-property test-component \
       test-integration ddl-validate ddl-diff

# a release teljes kapuja (a 08 §6.1 — hetente)
check-release: check test-e2e test-perf test-regression

# A BUILD

# a Docker image-ek buildje
build:
    docker build -f apps/api/Dockerfile -t duna-api:local .
    docker build -f apps/web/Dockerfile -t duna-web:local .

# a frontend statikus build (a 05 §1)
build-frontend:
    pnpm build

# az OpenAPI export (a 03 §5.1a)
openapi:
    {{UV}} python -m duna.api.export_openapi > docs/api/v1/openapi.json

# A SZINTENKÉNTI MINŐSÉGI KAPUK (a 08 §8.1)

# a hajótípus-név lista ellenőrzése: a report_vessels.sh CASE listája
check-type-case:
    {{UV}} python scripts/ais-receiver/make_type_case.py --check
