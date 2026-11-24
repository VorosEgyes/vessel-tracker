# A PostgreSQL custom image (a 07 – CI/CD-terv §3.2)
#
# **Miért kell custom image:** a stock `postgis/postgis` image-ben
# **nincs `pg_cron`** → a `02` §12 szerinti `cron.schedule(...)` hívások
# `schema "cron" does not exist` hibával elhalnának. A
# `pg_stat_statements` is kell (a `09` §4.1 latencia-metrika).
#
# **A `strip_cron` preprocesszor** (a `db/tools/validate_ddl.py`) a
# validáció során kihagyja a `cron.schedule(...)` hívásokat → **a CI-ban
# a custom image a mérőszám** (a 07 §3.2).
#
# **A BASE IMAGE: `postgis/postgis:16-3.7`** (a 2026-11-24-i javítás)
#
# **A korábbi `16-3.4` Debian `bullseye` (11) alapú volt** → a PGDG
# repóban **NINCS `bullseye-pgdg`** (a PGDG megszüntette a Debian 11
# támogatását) → az `apt-get update` **404 Not Found** hibával elbukott
# (a 2026-11-24-i CI-futas igazolta: "E: The repository
# 'http://apt.postgresql.org/pub/repos/apt bullseye-pgdg Release' does
# not have a Release file").
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
# a `pg_stat_statements` a 09 §4.1 latencia-metrikahoz) a **fő
# `postgresql-16` csomagban** vannak -> a base image (a
# `postgres:16-trixie`) MAR tartalmazza oket.
# (A `postgresql-contrib` a Debian bullseye-ben volt egy
# meta-csomag — a PGDG-ben nincs ilyen.)
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      postgresql-16-cron; \
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
