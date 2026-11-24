# A PostgreSQL custom image (a 07 – CI/CD-terv §3.2)
#
# **Miért kell custom image:** a stock `postgis/postgis:16-3.4` image-ben
# **nincs `pg_cron`** → a `02` §12 szerinti `cron.schedule(...)` hívások
# `schema "cron" does not exist` hibával elhalnának. A
# `pg_stat_statements` is kell (a `09` §4.1 latencia-metrika).
#
# **A `strip_cron` preprocesszor** (a `db/tools/validate_ddl.py`) a
# validáció során kihagyja a `cron.schedule(...)` hívásokat → **a CI-ban
# a custom image a mérőszám** (a 07 §3.2).
#
# A build: `just build-postgres` vagy a `build.yml` workflow
FROM postgis/postgis:16-3.4

# **A PGDG repo KELL a `postgresql-16-cron`-hoz** — a Debian stable
# repo-jaban NINCS benne (a 2026-11-24-i CI-futas hiba: az apt-get
# update 404-et dobott, a csomag nem lelheto a forrasban).
# A `postgresql-contrib` a PGDG-ben is benne van -> onnan telepitjuk
# mindkettoet, hogy a verziok egyezzenek (a `postgresql-16-cron` a
# 16-os major-verziot igorli).
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends curl ca-certificates gnupg; \
    install -d /usr/share/postgresql-common/pgdg; \
    curl -fsSL -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
      https://www.postgresql.org/media/keys/ACCC4CF8.asc; \
    . /etc/os-release; \
    echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] \
https://apt.postgresql.org/pub/repos/apt ${VERSION_CODENAME}-pgdg main" \
      > /etc/apt/sources.list.d/pgdg.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      postgresql-16-cron \
      postgresql-contrib; \
    rm -rf /var/lib/apt/lists/*

# **A `shared_preload_libraries` a CMD-ben, nem a CMD-felülirással:**
# a postgis image `docker-entrypoint.sh` scriptje kezeli a CMD-t →
# a `command` mezőt kell felülírni (a compose-ban) vagy a CMD-et
# módosítani (a Dockerfile-ben, a `ENTRYPOINT` megtartásával).
#
# **A `pg_cron` a `cron.database_name`-t a `postgresql.conf`-ban is
# beállítja** -> a conf módosítása a beindítás előtt történik, ezért
# a `shared_preload_libraries` a CMD argumentuma.
CMD ["postgres", "-c", "shared_preload_libraries=pg_cron,pg_stat_statements"]
