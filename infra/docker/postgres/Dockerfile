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

# a pg_cron (a 02 §12) es a pg_stat_statements (a 09 §4.1)
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      postgresql-16-cron \
      postgresql-contrib \
 && rm -rf /var/lib/apt/lists/*

# **A `shared_preload_libraries` a CMD-ben, nem a CMD-felülirással:**
# a postgis image `docker-entrypoint.sh` scriptje kezeli a CMD-t →
# a `command` mezőt kell felülírni (a compose-ban) vagy a CMD-et
# módosítani (a Dockerfile-ben, a `ENTRYPOINT` megtartásával).
#
# **A `pg_cron` a `cron.database_name`-t a `postgresql.conf`-ban is
# beállítja** -> a conf módosítása a beindítás előtt történik, ezért
# a `shared_preload_libraries` a CMD argumentuma.
CMD ["postgres", "-c", "shared_preload_libraries=pg_cron,pg_stat_statements"]
