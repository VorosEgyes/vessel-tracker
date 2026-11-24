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
    if [ -f pnpm-workspace.yaml ]; then pnpm install; else echo "a frontend meg nincs a repoban -> a pnpm install kihagyva"; fi
    @echo "a venv kesz"
    @echo "  a DDL-validacio: just ddl-validate"
    @echo "  a teljes minosegi kapu: just check"

# a compose indítása a build nélkül + a hot-reload
dev:
    if [ -f {{COMPOSE_LOCAL}} ]; then docker compose -f {{COMPOSE_LOCAL}} up; else echo "a compose fajl meg nincs a repoban -> a dev kihagyva"; fi

# a teljes compose (a DB migrációval)
up: db-migrate
    if [ -f {{COMPOSE_LOCAL}} ]; then docker compose -f {{COMPOSE_LOCAL}} up --build; else echo "a compose fajl meg nincs a repoban -> az up kihagyva"; fi

# a compose leállítása (a volume-okkal)
down:
    if [ -f {{COMPOSE_LOCAL}} ]; then docker compose -f {{COMPOSE_LOCAL}} down -v; else echo "a compose fajl meg nincs a repoban -> a down kihagyva"; fi


# az Alembic migrációk futtatása
db-migrate:
    # **Az alkalmazaskod meg nincs a repoban** (az `apps/api/` + az
    # `alembic.ini`) -> a lepes KIHAGYASA, nem hiba (a 07 §3.1)
    if [ -f alembic.ini ]; then {{UV}} alembic upgrade head; else echo "az alkalmazaskod meg nincs a repoban -> a db-migrate kihagyva"; fi

# a referenciaadat-seed (a 02 §12)
db-seed:
    if [ -d apps/api/src/duna/db ]; then {{UV}} python -m duna.db.seed; else echo "az alkalmazaskod meg nincs a repoban -> a db-seed kihagyva"; fi

# a DB újra (a down -v + up + migrate + seed)
# a DB ujra (a down -v + up + migrate + seed)
db-reset: down up
    if [ -d apps/api/src/duna/db ]; then {{UV}} python -m duna.db.seed; fi
    @echo "az adatbazis ujraindult (a migracio a `up` reszeben, a seed utana)"

#
# a DDL-validacio: a DDL futtatasa egy elo PostgreSQL-en + a fustteszt
ddl-validate:
    {{UV}} python db/tools/validate_ddl.py --no-gis
    # a fustteszt MINDIG fut (a `--keep` csak a schema megtartasa)

# a séma-drift ellenőrzése (a 02 §11): a generált DDLnek meg kell
ddl-diff:
    # **A `db/ddl/` a TERVBOL generálodik** (a 02 §11) -> a `--check`
    # a driftet ellenorzi, a `git diff --exit-code` a CI-ban a kapu.
    # A `pg_dump` a *rendeli* DB-vel mukodo masolat lenne (a CI-ban
    # nincs migrate-elt DB) -> a terv a kanonikus forras.
    # **A `--check` a kapu**: a generalt fajl == a tervbol szarmazo DDL
    # -> a drift (a terv valtozott, de a fajl nem) elbukik.
    {{UV}} python db/tools/gen_ddl.py --check
    # **A `git diff --exit-code` a CI-BAN, KULON LEPESKENT fut** (a
    # `ci.yml`-ben) -> ott a munkafa == a commit -> a fajlnek a
    # commitban kell lennie. **LOKALISAN nem futtatjuk**: a munkafaban
    # a friss generalt fajl mindig elter a commitolt verziotol ->
    # a `git diff` minden `just check`-et elbukna, pedig nincs drift.
    @echo "a sema-drift ellenorzes kesz (a --check); a CI-ban a git diff --exit-code is fut"

# a `db/ddl/` ujrageneralasa (a 02 §11) — **a terv modositasakor KOTELEZO**
ddl-generate:
    {{UV}} python db/tools/gen_ddl.py

# A MINŐSÉGI KAPU (a lint + a típusellenőrzés)

# a Python lint (a ruff)
lint:
    {{UV}} ruff check .
    # **A `ruff format` a MARKDOWN fajlok kodblokkjait is atirja** ->
    # a dokumentaciok kodmintai nem valtozhatnak -> **csak a Python
    # fajlokon** ellenorzzuk a formatot (a `apps/`, a `db/`, a
    # `scripts/`).
    {{UV}} ruff format --check .

# a frontend lint (az eslint + a prettier)
lint-frontend:
    # A frontend meg nem ltezik a repoban (a pnpm-workspace.yaml a
    # frontend-alkalmazas resze) -> a lepes KIHAGYASA, nem hiba
    # (a 07 §3.1: a frontend resze a 07 §3.2 szerinti image)
    if [ -f pnpm-workspace.yaml ]; then pnpm lint && pnpm format:check; else echo "a frontend meg nincs a repoban -> a lint-frontend kihagyva"; fi

# a típusellenőrzés (a mypy + a tsc)
typecheck:
    if [ -d apps/api/src/duna ]; then {{UV}} mypy apps/api/src/duna; else echo "az alkalmazaskod meg nincs a repoban -> a mypy kihagyva"; fi
    if [ -f pnpm-workspace.yaml ]; then pnpm typecheck; else echo "a frontend meg nincs a repoban -> a pnpm typecheck kihagyva"; fi

# A TESZTEK (a 08 §2.1 hét szintje)

# a unit tesztek (a tiszta függvények)
test-unit:
    {{UV}} python scripts/ci/pytest_or_skip.py {{TESTS}}/unit

# a property tesztek (a hypothesis round-trip)
test-property:
    {{UV}} python scripts/ci/pytest_or_skip.py {{TESTS}}/property

# a komponens tesztek (a service-ek a DB-vel)
test-component:
    {{UV}} python scripts/ci/pytest_or_skip.py {{TESTS}}/component

# az integrációs tesztek (a testcontainers + a PostGIS)
test-integration:
    {{UV}} python scripts/ci/pytest_or_skip.py {{TESTS}}/integration

# az e2e tesztek (a playwright)
test-e2e:
    if [ -f pnpm-workspace.yaml ]; then pnpm test:e2e; else echo "a frontend meg nincs a repoban -> a test-e2e kihagyva"; fi

# a teljesítményteszt (a locust; a F-NF-01: a p95 < 800 ms)
test-perf:
    if [ -f tests/perf/locustfile.py ]; then {{UV}} locust -f tests/perf/locustfile.py --headless; else echo "a perf-locustfile meg nincs a repoban -> a test-perf kihagyva"; fi

# az adat-regresszió (a mérési adat a baseline, a 08 §7)
test-regression:
    {{UV}} python scripts/ci/pytest_or_skip.py {{TESTS}}/regression

# az API-tesztek (a testcontainers DB-vel)
test-api:
    {{UV}} python scripts/ci/pytest_or_skip.py {{TESTS}}/api

# a frontend tesztek (a Vitest)
test-frontend:
    if [ -f pnpm-workspace.yaml ]; then pnpm test; else echo "a frontend meg nincs a repoban -> a test-frontend kihagyva"; fi

# a teljes tesztkészlet a coverage flaggel (a 08 §8.1 küszöb: 85%)
test:
    # A pytest hibakodjai: a 5 (nem gyujtott teszt) a wrapperben
    # elnyelodik -> a 3 (belső hiba) ES az 1 (teszthiba) atmegy
    {{UV}} python scripts/ci/pytest_or_skip.py {{TESTS}}/unit {{TESTS}}/property {{TESTS}}/component --cov=duna --cov-report=term-missing --cov-fail-under={{COVERAGE_MIN}}

# a domain réteg 90%-os küszöbe (a 08 §8.1) — a kiemelt modulok
# (a domain/ es az ingest/) szigorubb hatart kapnak, mint a teljes
# projekt (85%)
test-domain:
    {{UV}} python scripts/ci/pytest_or_skip.py {{TESTS}}/unit --cov=duna.domain --cov-report=term-missing --cov-fail-under=90

# a migráció-visszafordíthatóság (a 07 §8.1 8. lépése)
test-reversible:
    {{UV}} python scripts/ci/pytest_or_skip.py -k reversible

# A KAPUK

# a teljes minőségi kapu egy parancsban (a 01 §11.3 és a 08 §6.1)
check: lint lint-frontend typecheck test-unit test-property test-component \
       test-domain test-integration ddl-validate ddl-diff

# a release teljes kapuja (a 08 §6.1 — hetente)
check-release: check test-e2e test-perf test-regression

# A BUILD

# a Docker image-ek buildje
build:
    if [ -f apps/api/Dockerfile ]; then docker build -f apps/api/Dockerfile -t duna-api:local .; else echo "az API Dockerfile meg nincs a repoban -> kihagyva"; fi
    if [ -f apps/web/Dockerfile ]; then docker build -f apps/web/Dockerfile -t duna-web:local .; else echo "a web Dockerfile meg nincs a repoban -> kihagyva"; fi

# a frontend statikus build (a 05 §1)
build-frontend:
    if [ -f pnpm-workspace.yaml ]; then pnpm build; else echo "a frontend meg nincs a repoban -> a build-frontend kihagyva"; fi

# az OpenAPI export (a 03 §5.1a)
openapi:
    if [ -d apps/api/src/duna/api ]; then mkdir -p docs/api/v1 && {{UV}} python -m duna.api.export_openapi > docs/api/v1/openapi.json; else echo "az alkalmazaskod meg nincs a repoban -> az openapi kihagyva"; fi

# A SZINTENKÉNTI MINŐSÉGI KAPUK (a 08 §8.1)

# a hajótípus-név lista ellenőrzése: a report_vessels.sh CASE listája
check-type-case:
    {{UV}} python scripts/ais-receiver/make_type_case.py --check
