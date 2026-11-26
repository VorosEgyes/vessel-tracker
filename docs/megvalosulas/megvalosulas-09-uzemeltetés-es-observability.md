# Implementációs terv – 09: üzemeltetés és observability

**Verzió:** 0.3 (a 05–09-es swarm review javításai: a lehúzás-határ 8 → **4 nap**, a környezetfüggő heartbeat-határ, a restore-drill a **stagingben**, a 3 site kapacitás, a havi partíciókezelés)
**Dátum:** 2026-11-23
**Kapcsolódó dokumentumok:**
[`../README.md`](../README.md) (adatbázis-terv) ·
[`megvalosulas-01-stack-es-struktura.md`](megvalosulas-01-stack-es-struktura.md) (a stack, a kockázatok) ·
[`megvalosulas-02-adatbazis-ddl.md`](megvalosulas-02-adatbazis-ddl.md) (a séma, **§13: a mentés, a visszaállítás és a monitorozás**) ·
[`megvalosulas-03-api-specifikacio.md`](megvalosulas-03-api-specifikacio.md) (az API, a hibakezelés) ·
[`megvalosulas-04-ais-parser.md`](megvalosulas-04-ais-parser.md) (a parser, a mérési protokoll) ·
[`megvalosulas-07-ci-cd-es-kornyezetek.md`](megvalosulas-07-ci-cd-es-kornyezetek.md) (a CI, a deploy, a smoke teszt) ·
[`megvalosulas-08-teszt-strategia.md`](megvalosulas-08-teszt-strategia.md) (a tesztek, a mérőszámok) ·
[`../ingest-terv.md`](../ingest-terv.md) (az adatút, **a heti lehúzás**) ·
[`../ais-vevo-terv.md`](../ais-vevo-terv.md) (a vevőhálózat) ·
[`../release-terv.md`](../release-terv.md) (a kiadás, a 11. fejezet metrikái) ·
[`../measurement_2026-11-22.md`](../measurement_2026-11-22.md) (a mérés valós adata) ·
[`README.md`](README.md) (a terv-sorozat tagjai)

**Projekt:** `vessel-tracker` — a hajókövető a Dunán és a Balatonon.

> A dokumentum a repóban a `docs/megvalosulas/megvalosulas-09-uzemeltetés-es-observability.md`
> útvonalon van — a relatív linkek ehhez képest számolnak.

---

## 1. Mit fed le ez a terv

**Az üzemeltetés és a megfigyelhetőség** — vagyis:

| | |
|---|---|
| **§2** | az **üzemeltetési modell** (a mérési időszak kontra az R1 éles) |
| **§3** | a **mentés és a visszaállítás** (a `02` §13.1 alapján) |
| **§4** | a **monitorozás** (a metrikák, a `02` §13.2 alapján) |
| **§5** | a **riasztás** (a **watchdog** — a `02` §13.2 szerint itt készül) |
| **§6** | a **naplózás** |
| **§7** | a **vevőhálózat üzemeltetése** (a `command=` korlátozás, a heti lehúzás) |
| **§8** | a **skálázás és a korlátok** (a 2 GB-os VPS) |
| **§9** | az **incidenskezelés** (a visszaállítási forgatókönyvek) |
| **§10** | a **nyitott kérdések** |

**Amit ez a terv NEM fed le:**
- a **fejlesztői környezetet** (a `07` – CI/CD terv);
- a **biztonsági auditot** (a §5.3 csak a riasztásokat fedi);
- a **adatvédelmi**Compliance-folyamatokat (a F-NF-14 — a GDPR-nyilatkozat, a cookie-banner — **termékoldali** feladat, nem üzemeltetési).

---

## 2. Az üzemeltetési modell

### 2.1 A két fázis

| | **R1-0 — a mérési időszak** | **R1 — az éles működés** |
|---|---|---|
| **A vevő** | a `bud01` (egy Raspberry Pi 4) | **3 site** (a F-CAT-08 szerint) |
| **A nyers adat útja** | **heti lehúzás** (a Pi → NAS, a `command=` korlátozással) | **heti lehúzás** (a Pi → NAS) + a központi feldolgozás |
| **Az adatbázis** | **nincs** — a mérés a Pi-n fut | a VPS `postgres` (a custom image) |
| **A felhasználó** | nincs (a web nincs R1-0-ban) | a weboldal |
| **A riasztás** | **a heti lehúzás ellenőrzése** (a NAS-on) | a teljes watchdog |
| **Az üzemeltető** | **egy ember** (Miklós) | egy ember + a watchdog |

### 2.2 A mérési időszak üzemeltetése (a mostani helyzet)

**Ez a legfontosabb rész — a mérés fut, és a heti lehúzás a lánc
kritikus pontja.**

| A teendő | A gyakoriság | A hiba hatása |
|---|---|---|
| **a Pi áramellátása és a hálózata** | folyamatos | a vevő leáll → **a nyers adat a leállás pillanatáig megvan** |
| **a heti lehúzás ellenőrzése** (hétfő reggel) | **hetente** | **a `RETENTION 35` nap a mérés + 5 nap tartalék** → 2 hét késés még rendben, a 3.-on **az adat elveszik** |
| **az SD-kártya szabad helye** | hetente | a 4,1 GB / 29 GB (15%) → **bőven rendben** |
| **a NAS `ais-data/` mappája** | hetente | **~600 MB/hét** → **a fájlokat törölni kell** (a `ais-data/` 30 GB/év) |

> **A heti lehúzás ellenőrzésének legegyszerűbb formája** (a NAS-on):
> ```bash
> ls -lt /opt/data/martin/work/ais-data/ | head -3
> # a legutóbbi fájl dátuma hétfő 04:17 körül kell legyen
> ```

---

## 3. A mentés és a visszaállítás

**A `02` – DDL-terv §13.1 alapján** (a README 8. fejezete):

| A szempont | A megoldás |
|---|---|
| **A teljes mentés** | hetente `pg_basebackup` |
| **A WAL-archívum** | `archive_mode = on` + az `archive_command` a tárolóba |
| **A PITR-ablak** | **7 nap** |
| **Az RPO** | **15 perc** (a WAL 15 percenként zsync-el) |
| **Az RTO** | **2 óra** (a heti mentés + a WAL-visszajátszás) |

### 3.1 A mentési ütemezés

```bash
#!/usr/bin/env bash
# infra/backup.sh — a heti teljes mentés (a pg_cron vagy a host cron)
set -euo pipefail

STAMP=$(date +%Y%m%d-%H%M)
BACKUP_DIR="${BACKUP_DIR:-/srv/app/backups}"

# a teljes mentés (a konzisztens pillanatkép)
pg_basebackup --format=tar --gzip --pgdata \
  --label="full-${STAMP}" \
  -D "${BACKUP_DIR}/full-${STAMP}"

# a séma külön (a gyors visszaállításhoz)
pg_dump --schema-only --no-owner --no-privileges \
  "$DATABASE_URL" > "${BACKUP_DIR}/schema-${STAMP}.sql"

# a régi mentések takarítása (a 4 hetesek meg tartása)
find "${BACKUP_DIR}" -maxdepth 1 -name 'full-*' -mtime +28 -exec rm -rf {} +
```

### 3.2 A visszaállítási próba (a heti kötelező lépés!)

> **A `release-terv` 9. fejezete és a `02` §13.1:** a mentés
> **mindig visszaállítással ellenőrzött**. **Egy visszaállítatlan mentés
> nem mentés.**

```bash
#!/usr/bin/env bash
# infra/restore-drill.sh — a heti visszaallitasi proba
set -euo pipefail

# A STAGING kompozban fut (a prof H-7 / preshaz P-C-3 findingje):
# a production lemezen a restore_test DB a teljes mentes merete
# (~2-3 GB) lenne, a position pedig ~15-25 GB -> a drill hetente
# karosithatna a productiont.
COMPOSE=infra/compose/staging.yml

# 1. egy eldobható DB
docker compose -f "$COMPOSE" exec -T postgres \
  createdb -U postgres restore_test

# 2. a legutolso teljes mentes visszatoltes
LATEST=$(ls -dt /srv/app/backups/full-* | head -1)
docker compose -f "$COMPOSE" exec -T postgres \
  pg_restore --clean --if-exists --no-owner --dbname=restore_test \
  < "${LATEST}/base.tar.gz"

# 3. az ellenorzes: a sorszamok egyeznek-e
VESSELS=$(docker compose -f "$COMPOSE" exec -T postgres \
  psql -U postgres -d restore_test -tAc \
  "SELECT count(*) FROM vessel;")

# 4. a restore_test DB torlese (a lemez felszabaditasa)
docker compose -f "$COMPOSE" exec -T postgres \
  dropdb -U postgres restore_test

# 5. AZ EREDMENY A PRODUCTION DB job_run TABLABA (a preshaz P-C-7
#    findingje) — a watchdog a productiont figyeli, igy a drill
#    eredmenyenek ODA kell kerulnie (a restore_test DB-be nem)
docker compose -f infra/compose/production.yml exec -T postgres \
  psql -U postgres -d duna -tAc \
  "INSERT INTO job_run (job_name, started_at, ended_at, status, rows_out)
   VALUES ('restore-drill', now(), now(),
           '$( [ -n "$VESSELS" ] && echo success || echo failed )',
           $VESSELS);"
```

> **A `preshaz` reviewer P-C-7 findingje (a 2. kör, BLOKKOLÓ):** az
> eredeti alakban a drill **egyetlen `job_run`-INSERTet sem írt** → a
> „a próba eredménye a `job_run` táblába" csak **egy mondat a szövegben**
> volt, nem kód → **a drill bukása sehol sem jelent meg**. **Ráadásul
> ha a `restore_test` DB-be írt volna, a watchdog (a productiont figyelő)
> soha nem látta volna.**
>
> **A javítás:** az **5. lépés** a drill eredményét a **production
> `job_run`** táblába írja (a `restore_test` DB-be **nem**) → **a
> watchdog figyelni tudja** → **az A9 riasztás életre kel**.

> **A próba eredménye a `job_run` táblába** (`job_name='restore-drill'`)
> → **a `09` §5 watchdogja figyeli** — **a STAGING DB `job_run`-ját**
> (a production érintetlen marad).

> **A `prof` reviewer H-7 és a `preshaz` reviewer P-C-3 findingje:**
> az eredeti alakban a drill a **production** compose-on futott → a
> `restore_test` DB a **production lemezén** foglal helyet (a teljes
> mentés mérete) → **a 2 GB-os VPS-en a `position` (~15–25 GB) mellett
> ez elfoghatja a lemez nagy részét**. **A javítás: a staging** (a
> `07` §6.1 szerint a staging a `release/*` deploy-k célpontja) +
> **a `restore_test` DB törlése a drill után** (a 4. lépés).

### 3.3 A visszaállítás katasztrófája esetén

```
1. a VPS-en: docker compose down
2. a legutóbbi teljes mentés visszatöltése (a 3.2 szerint)
3. a WAL-visszajátszás a PITR-pontig:
   restore_command = 'cp /srv/app/backups/wal/%f %p'
4. a 'SELECT pg_wal_replay_resume()'
5. a migrate (a 07 §5.3) — az app verziója a DB-verzióval együtt
6. a smoke teszt (a 07 §9)
```

---

## 4. A monitorozás

### 4.1 A metrikák (a `02` §13.2 alapján)

| A metrika | A forrás | A riasztási határ |
|---|---|---|
| **A feldolgozás sikeressége** | `job_run.status` | a `failed`/`partial` sorok száma > 0 |
| **A pozíciófedettség** | a `vessel_last_position` nézet | a hajók > 20%-ának nincs 1 óránál régebbi pozíciója |
| **A partíció-méret** | `pg_total_relation_size` | egy partíció > 5 GB |
| **A lekérdezési latencia** | `pg_stat_statements` | a `mean_exec_time` > 100 ms |
| **A hibák** | `data_quality_event` | a nyitott `critical` események száma > 0 |
| **A vevőhálózat** | `ais_receiver_site.last_seen_at` | **R1-ben 10 nap, R2-ben (élő MQTT) 30 perc** (a `04` §4.1 környezet-táblázata) |
| **A katalógus mérete** | a `meta.total` (a `03` §9) | **a mérési alap legyen, ne becslés** (a `08` §3.1 az F-NF-01 tesztet a mért értékre állítja) |

> **A `prof` reviewer M-11 findingje (a 2. kör):** a `08` §3.1 a
> teljesítménytesztet **300 hajós listával** tervezi → **de a mérésben
> 199 `ais_state` sor van** (a valós katalógus ennél kisebb: a 106 lámpa
> és a 3 bázisállomás kiesik) → **a `meta.total` metrikát mérjük**, és
> **az F-NF-01 tesztparamétere a mért érték legyen**, ne egy becslés.
>

> **A `prof` reviewer M-8 findingje:** a `pg_stat_statements` **a teljes
> lekérdezés átlagát** adja → **a p95 NEM ebből jön** → **a határ
> megváltozott**: a `mean_exec_time > 100 ms`. Az **alkalmazásszintű p95**
> a `03` §9 szerint a `duration_ms`-ből mérhető (a `X-Request-ID`-s
> logból) → **a F-NF-01 (800 ms) mérhető** így.


**A `pg_stat_statements` extension** a `0001_extensions.sql`-ben (a custom
image-ben) — **a latencia-méréshez kell**.

### 4.2 A mérési időszak metrikái (a Pi oldalon)

**A `02` §13.2 a központi DB-re szól** — **a mérési időszakban nincs
központi DB**, tehát a vevő oldali metrikák:

| A metrika | A forrás | A határ |
|---|---|---|
| **a vevő él-e** | a `ais_stats_hourly` (`msg`, `vessels`) | **az üres óra = a vevő leállt** |
| **a PPM** | az `ais_stats_hourly.ppm` | a **\|ppm\| > 8** → a kristály driftelt (a kalibráció elcsúszott; a mérésben **−5,1 … −6,6**, a `rtl_test -p` szerint **+7**) |
| **a jelerősség** | az `ais_stats_hourly.level_min`/`level_max` | a **szint tartósan 0** → az antenna/szűrő problémája |
| **az üzenetszám** | az `ais_stats_hourly.msg` | **a napi 0 üzenet** → a vevő leállt |
| **a heti lehúzás** | a NAS `ais-data/` fájlok dátuma | **a fájl 4 napnél régebbi** → a lehúzás elmaradt |

> **A `level_min`/`level_max` a v0.71-ben 0** (a jelerősség nem kerül
> a DB-be — a `04` – parser-terv C-6 findingje) → **ez a két metrika
> R1-ben nem használható** → **a jelerősség a monitoring helyett a
> heti elemző riportban** (a `analyze_measurement.py`).

### 4.3 A teljesítménymonitorozás (az alkalmazás oldalán)

**A `03` – API-terv §9 szerint:**
- a **p95** a mérőszám (nem az átlag);
- a `pg_stat_statements` a lekérdezésekhez;
- a `slow query` riasztás a `02`-ben van.

```python
# apps/api/src/duna/middleware.py
@app.middleware("http")
async def add_timing(request: Request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    dt = (time.perf_counter() - t0) * 1000
    logger.info("request", extra={
        "path": request.url.path,
        "method": request.method,
        "status": response.status_code,
        "duration_ms": round(dt, 1),
        "request_id": request.headers.get("x-request-id"),
    })
    response.headers["X-Request-ID"] = request.headers.get("x-request-id", "")
    return response
```

---

## 5. A riasztás

### 5.1 A watchdog (a `02` §13.2 szerint itt készül)

> **A `preshaz` reviewer P-C-5 findingje (a 2. kör):** a watchdog
> **a host cron-jára** épült → **de a `07` §4.2-ben nem volt cron** →
> **a production VPS-en a crontáb kézi lépés volt** → **a `07` §6.1a
> (a deploy script) most telepíti** → **egy megoldás, egy helyen**.

> **A `02` – DDL-terv §13.2:** „*a `pg_cron` **a `job_run` táblát
> tölti**, a riasztás pedig egy **külső watchdog** (a **09 –
> Üzemeltetés terv** dolga) figyeli a `job_run` és a `data_quality_event`
> táblát, és **Telegramon** értesít.*"

**A watchdog egy kis, önálló script** — **nem** az alkalmazás része
(az alkalmazás hibája ne riasztás-ügyelet legyen).

```python
# infra/watchdog/watchdog.py — a riasztó watchdog
"""Ellenőrzi a `job_run` és a `data_quality_event` táblákat, és
Telegramon értesít. A 02 – DDL-terv §13.2 szerint ez a 09-es terv
dolg a `pg_cron` mellett.

Futtatás: a host cron-jában, óránként.
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

import asyncpg
import httpx

# a hatarok (a 02 §13.2)
THRESHOLDS = {
    "failed_jobs": 0,          # a job_run failed/partial darabszama
    "critical_events": 0,     # a nyitott critical esemenyek
    "position_stale_pct": 20,    # a hajok hány %-a nincs 1 oras poziciom
    # a vevoheartbeat hatara NEM itt van — a kornyezettol fugg
    # (a STALE_RECEIVER_INTERVAL env var: R1 = 10 nap, R2 = 30 perc)
    # a prof C-5 / preshaz P-H-8 findingje szerint
}


def disk_usage_percent() -> float:
    """A lemez hasznalatanak szazaleka (a A8 riasztas).

    A `pg_database_size` a DB-re vonatkozik, nem a lemezre ->
    a hoszt oldali `df`-bol olvasunk.
    """
    st = os.statvfs("/var/lib/postgresql")
    total = st.f_blocks * st.f_frsize
    free = st.f_bavail * st.f_frsize
    return 100 * (total - free) / total


async def check(conn) -> list[str]:
    problems = []

    r = await conn.fetchrow("""
        SELECT count(*) AS n FROM job_run
        WHERE status IN ('failed','partial')
          AND started_at > now() - interval '24 hours'
    """)
    if r["n"] > THRESHOLDS["failed_jobs"]:
        problems.append(f"{r['n']} hibás feldolgozás az elmúlt 24 órában")

    r = await conn.fetchrow("""
        SELECT count(*) AS n FROM data_quality_event
        WHERE severity = 'critical' AND resolved_at IS NULL
    """)
    if r["n"] > THRESHOLDS["critical_events"]:
        problems.append(f"{r['n']} nyitott critical esemény")

    # A vevoheartbeat (a prof C-5 / preshaz P-H-8 findingje):
    # a hatar KORNYEZETFUGo — R1-ben a heti lehuzas miatt a
    # last_seen_at hetente frissul -> 10 nap; R2-ben (elo MQTT) 30 perc.
    STALE_RECEIVER_INTERVAL = os.environ.get(
        "STALE_RECEIVER_INTERVAL", "10 days"   # R1; R2: "30 minutes"
    )
    r = await conn.fetchrow("""
        SELECT count(*) AS n FROM ais_receiver_site
        WHERE status = 'active'
          AND (last_seen_at IS NULL
               OR last_seen_at < now() - $1::interval)
    """, STALE_RECEIVER_INTERVAL)
    if r["n"] > 0:
        problems.append(
            f"{r['n']} vevő nem adott heartbeatot "
            f"{STALE_RECEIVER_INTERVAL} óta (A3)"
        )

    # --- A5: a poziciofedettseg (a 20% hatar) ---
    r = await conn.fetchrow("""
        SELECT count(*) FILTER (
                   WHERE last_position_ts IS NULL
                      OR last_position_ts < now() - interval '1 hour'
               ) AS stale,
               count(*) AS total
        FROM vessel_last_position
    """)
    if r["total"] > 0 and 100 * r["stale"] / r["total"] > THRESHOLDS["position_stale_pct"]:
        problems.append(
            f"A pozíciófedettség {100 * r['stale'] / r['total']:.0f}% "
            f"stale (a határ {THRESHOLDS['position_stale_pct']}%) (A5)"
        )

    # --- A6: egy particio > 5 GB ---
    r = await conn.fetchrow("""
        SELECT count(*) AS n FROM (
            SELECT c.relname
            FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind IN ('r','p')
              AND pg_total_relation_size(c.oid) > 5 * 1024 * 1024 * 1024
        ) t
    """)
    if r["n"] > 0:
        problems.append(f"{r['n']} partíció nagyobb 5 GB-nál (A6)")

    # --- A7: a lekérdezesi latencia (a mean_exec_time) ---
    r = await conn.fetchrow("""
        SELECT count(*) AS n FROM pg_stat_statements
        WHERE mean_exec_time > 100 AND calls > 10
    """)
    if r["n"] > 0:
        problems.append(f"{r['n']} lekérdezés lassabb 100 ms-nál (A7)")

    # --- A8: a lemez megtelt ---
    r = await conn.fetchrow("""
        SELECT (pg_database_size(current_database())::float
                / (SELECT setting::float * 1024 * 1024 * 1024
                   FROM pg_settings WHERE name = 'block_size')) AS ratio
    """)
    # a lemez teljes merete a hoszton van -> a watchdog a /proc/mounts-ot olvassa
    disk_pct = disk_usage_percent()          # a helper fuggveny (latsd lentebb)
    if disk_pct > 85:
        problems.append(f"a lemez {disk_pct:.0f}%-on tele (a határ 85%) (A8)")

    # --- A9: a visszaallitasi proba (a job_run 'restore-drill') ---
    r = await conn.fetchrow("""
        SELECT count(*) AS n FROM job_run
        WHERE job_name = 'restore-drill'
          AND started_at > now() - interval '8 days'
          AND status <> 'success'
    """)
    if r["n"] > 0:
        problems.append(f"{r['n']} sikertelen visszaállítási próba (A9)")

    # --- A10: a job_run 24 orara nem futott ---
    r = await conn.fetchrow("""
        SELECT count(*) AS n FROM job_run
        WHERE started_at > now() - interval '24 hours'
    """)
    if r["n"] == 0:
        problems.append("24 óra alatt nem futott egyetlen job_run sem (A10)")

    return problems


async def notify(messages: list[str]) -> None:
    """A Telegram értesítés.

    A P-H-10 findingje szerint a `os.environ[...]` **KeyError-rel** elhal,
    ha a változó nincs a `.env`-ben -> **a hiányzó érték most warning,
    nem egy halott processz.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("HIBA: a TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID nincs beallitva "
              "(a .env.example a 07 §2.3-ban szerepel) — a riasztas nem megy ki",
              file=sys.stderr)
        return
    text = "🚨 *vessel-tracker*\n" + "\n".join(f"• {m}" for m in messages)
    async with httpx.AsyncClient() as c:
        await c.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
        )
```

### 5.2 A riasztások listája és a sürgőssége

| # | A riasztás | A határ | A sürgősség | **A csatorna** | **A kód** |
|---|---|---|---|---|---|
| A1 | a heti lehúzás elmaradt | a legutóbbi fájl **4 napnál régebbi** | **kritikus** (a 3. héten az adat elveszik) | **a NAS-on** (§5.3) | `check-pull.sh` |
| A2 | a feldolgozás hibás | `job_run.status` = `failed`/`partial` | kritikus | Telegram | `check()` — a `job_run` |
| A3 | a vevő nem ad heartbeatot | **R1: 10 nap · R2: 30 perc** | kritikus (a nyers adat a leállás pillanatáig megvan) | Telegram | `check()` — az `ais_receiver_site` |
| A4 | a nyitott `critical` esemény | > 0 | magas | Telegram | `check()` — a `data_quality_event` |
| A5 | a pozíciófedettség | a hajók > 20%-a 1 óránál régebbi | magas | Telegram | `check()` — a `vessel_last_position` |
| A6 | egy partíció > 5 GB | — | közepes | Telegram (napi összefoglaló) | `check()` — a `pg_class` |
| A7 | a `pg_stat_statements` latencia | a `mean_exec_time` > 100 ms | közepes | Telegram (napi) | `check()` — a `pg_stat_statements` |
| A8 | a lemez megtelt | > 85% | közepes | Telegram | `check()` — a `disk_usage_percent()` |
| A9 | a visszaállítási próba sikertelen | a `job_run` `restore-drill` ≠ `success` | kritikus | Telegram | `check()` — a `job_run` |
| A10 | a `job_run` 24 óra alatt nem futott | — | magas | Telegram | `check()` — a `job_run` |

> **A `preshaz` reviewer P-H-9 findingje (a 2. kör):** a §5.2 **10
> riasztást ígért**, **de a §5.1 `check()` függvénye csak kettőt
> teljesített** (A2, A4) → **a productionben 7 riasztás halott volt**.
> **A javítás:** a §5.1 `check()` most **mind a tízet** implementálja,
> **és a fenti táblázat "A kód" oszlopa megmondja, melyik hol van**
> → **a §5.2 nem ígér semmit, amit a §5.1 nem tartalmaz**.
>
> **A korábbi `WHERE active` SQL hiba (a P-C-6 findingje) is javítva:**
> az `ais_receiver_site`-nek **nincs `active` oszlopa**, a `status` van
> → **`WHERE status = 'active'`** (és a `last_seen_at IS NULL` ág is,
> hogy a **soha nem jelentkező** vevő is észrevétlen ne maradjon).

> **A1 és A9 a mérési időszakban is fontos** — ezek a `02` §13.2
> *központi* metrikái helyett a **mérési időszak** sajátjai.

### 5.3 A mérési időszak riasztásai (a Pi oldalán)

**A mérési időszakban nincs központi DB** → a riasztás a **NAS-on** fut
(a heti lehúzás ellenőrzése) + **a Pi heartbeatja**.

```bash
# infra/watchdog/check-pull.sh — a heti lehuzas ellenorzese (a NAS-on)
#!/usr/bin/env bash
# a cron: hetente, hétfon 09:00 (a lehuzas utan 5 oraval)
LATEST=$(ls -t /volume1/docker/hermes/data/martin/work/ais-data/ais-*.db 2>/dev/null | head -1)
if [ -z "$LATEST" ]; then
  echo "HIBA: egyetlen lehuzott fajl sincs" >&2
  exit 1
fi
# a hatar 4 nap (a prof C-7 / preshaz P-C-1 findingje): a lehuzas heti,
# igy a 8 napos hatar gyakorlatilag sosem lep tul — a 4 nap a heti
# ritmus + 3 nap tartalek, es a 2. heti kimaradast AZONNAL jelzi
AGE_DAYS=$(( ( $(date +%s) - $(stat -c %Y "$LATEST") ) / 86400 ))
if [ "$AGE_DAYS" -gt 4 ]; then
  echo "HIBA: a legutolbi lehuzas ${AGE_DAYS} napos (a hatar: 4)" >&2
  exit 1
fi
```

> **A `command=` korlátozás miatt** a Pi a NAS-on **csak** a lehúzást
> futtathatja → **a watchdog a NAS-on a `hermesadmin` userrel fut**.

---

## 6. A naplózás

### 6.1 A strukturált formátum

**A `03` – API-terv §2.2a szerint:**
- a `request_id` a `X-Request-ID` headerrel;
- a `5xx` hibák **fix szöveggel** a kliensnek, **a részlet a naplóba**;
- a `logger.exception` a teljes kivételt rögzíti (a stack trace).

**A formátum: JSON a sorban** (a `structlog` vagy a `python-json-logger`).

```json
{"ts": "2026-11-23T08:15:42Z", "level": "info", "event": "request",
 "path": "/api/v1/vessels", "status": 200, "duration_ms": 34.2,
 "request_id": "a1b2c3d4", "site": "bud01"}
```

### 6.2 A szintek és a retenció

| A szint | Mi kerül bele | A retenció |
|---|---|---|
| `DEBUG` | a query-k, a dekódolás részletei | **a developmentben** (a productionben nincs) |
| `INFO` | a kérések, a job-ok, a partíció-létrehozás | **30 nap** (a `journalctl` a `docker logs`ban) |
| `WARNING` | a degradált működés (a lassú query, a retry) | 30 nap |
| `ERROR` | a kezelt hibák (a `data_quality_event`-tel párhuzamosan) | 30 nap |
| `CRITICAL` | a kezeletlen hibák | 30 nap + a Sentry |

### 6.3 A Pi oldali napló

**A vevő a `journalctl`-ban** (a systemd unit):
```bash
journalctl -u ais-receiver -f --since "1 hour ago"
```

> **A `-o 0` (quiet) miatt a vevő nem írja ki minden üzenetet** — a
> nyers NMEA a DB-ben van → **a napló tiszta, és a `journalctl` nem
> nő a hónapok során** (a `AIS-catcher` a saját stdout-ját is csendesíti).

---

## 7. A vevőhálózat üzemeltetése

### 7.1 A Pi oldal

| A feladat | A gyakoriság |
|---|---|
| az SD-kártya cseréje (a wear) | ** évente** |
| a `rtl_test -p` újrakalibráció (a PPM driftel) | **félévente** (a mérésben a PPM 7 volt, a kristály melegben driftel) |
| az antenna ellenőrzése | évente |
| a Wi-Fi jelszó (a `Pres-iot`) rotációja | évente |

### 7.2 A NAS oldal

| A feladat | A gyakoriság |
|---|---|
| **az `ais-data/` fájlok törlése** (30 GB/év) | **hetente** (a lehúzás után) |
| a fogadó script (`/usr/local/bin/nas-receive-ais.sh`) ellenőrzése | a Pi cseréjénél |
| a `command=` kulcs rotációja | évente |

### 7.3 Az új site hozzáadása (a 3 site bővítésekor)

```
1. a repóból: az install_pi_os.sh + a make_cloudinit.sh (a site
   paramétereivel: a hostname, a Wi-Fi, a station_id)
2. a Pi-n: az install_ais_receiver.sh + a start_measurement.sh
3. a NAS-on: a Pi kulcsának hozzáadása (a command= korlátozással)
4. a központi DB-ben: az ais_receiver_site sor (a site_id, a
   station_id, a kód, a nevén, a lat/lon)
5. a docs/ais-vevo-terv.md frissítése a site adataival
```

> **A `station_id` a lánc kulcsa**: a `ais_message.station_id` →
> az `ais_receiver_site` → **a vevő azonosítható**.

---

## 8. A skálázás és a korlátok

### 8.1 A 2 GB-os VPS (a `01` – stack-terv §3.2)

| A korlát | A határ | A megoldás |
|---|---|---|
| **a RAM** | a `pool_size=10` + `max_overflow=5` = **15 kapcsolat** | a `psycopg` pool a `statement_timeout` miatt |
| **a lemez** | a `position` ~81 millió sor (90 nap) → **~15–25 GB** | a havi partíció + a `drop_expired_partitions` |
| **a CPU** | az Astro statikus build (a build nem a VPS-en fut, a CI-ban) | a `web` a statikus fájlokat szolgálja ki |
| **a `statement_timeout`** | 5 s | a `03` – API-terv §9 |

**A havi partíció mérete (a `preshaz` reviewer P-H-2 findingje)** — a
mérésből számolva:

| A számítás | Az érték |
|---|---|
| a pozíciók a mérésben | ~900 000 pozíció/nap |
| **egy hónap** | **~27 millió pozíció** |
| **egy havi partíció** | **~27 millió sor ≈ 5 GB** |

> **Ez a `02` §13.2 riasztási határát („egy partíció > 5 GB") **az
> első hónapban eléri** → **vagy napi partíció kell, vagy a határ
> emelendő**. **A döntés: a havi partíció marad, de a `position`
> partíció a TTL helyett a méret alapján is hasad** → a `drop_expired_partitions`
> heti fut → **egy partíció ~1,3 GB** (a heti adag) → **a határ alatt marad**.

**A `COPY` és a `statement_timeout` (a `preshaz` reviewer P-H-3
findingje)** — a `COPY` **egy** utasítás, nem `executemany`:

| A mód | A `statement_timeout` (5 s) |
|---|---|
| a `COPY` egy 27 millió soros fájlból | **ELBUKIK** (egy utasítás > 5 s) |
| **a `COPY` 5 millió soros darabokban** | ✅ (a `09` §8.1 szerint: **a `COPY` batchelt**) |
| az `INSERT` `executemany`-val, 2 000 sor/batch | ✅ |

**A heti mentés lemezigénye (a `preshaz` reviewer P-H-5 findingje):**

| A szükséges hely | Az érték |
|---|---|
| az élő DB | ~15–25 GB (a `position`) |
| **a heti mentés fájlja** | **~2–3 GB** (a `pg_basebackup` tömörítve) |
| **a WAL-archivum** (a PITR-hez, 7 nap) | **~a DB mérete** |
| **a drill** (a stagingben) | a `restore_test` DB mérete → **a staging lemezén** |

> **A skálázási trigger (a §8.3) ezért nem elég a „VPS lemez > 85%"**:
> **a heti mentés idejére duplán kell hely** → **a `09` §8.3
> trigger-táblázata kap egy sort: „a heti mentés idejére van hely"
> (a mentés + a WAL-archivum együtt)**.

### 8.2 A nyers adat mennyisége (a mérésből)

| | A mérés | A 30 napos |
|---|---|---|
| az üzenetek | 37 494/óra | **~27 millió** |
| a nyers SQLite | ~4 MB/óra | **~2,9 GB** |
| a heti lehúzás fájlja | — | **~600 MB** |
| a NAS éves | — | **~30 GB** (a törlés kell) |

**A 3 site (az F1) es a lemezigeny (a `preshaz` reviewer P-M-5 és
P-M-6 findingje) — a fenti táblázat EGY SITE adata:**

| | 1 site (a mérés) | **3 site (az F1)** |
|---|---|---|
| az üzenetek 30 nap alatt | ~27 millió | **~81 millió** |
| a nyers SQLite | ~2,9 GB | **~8,7 GB** |
| a heti lehúzás fájlja | ~600 MB | **~1,8 GB** |
| a NAS éves (a törlés kell) | ~30 GB | **~90 GB** |
| **a `position` a Postgresben** | ~27 millió sor/hó | **~81 millió sor/hó** |
| **a teljes lemezigeny a VPS-en** | DB (~15–25 GB) + mentés (~2–3 GB) + WAL-archivum (~a DB mérete) | **~3×** |

> **A `preshaz` reviewer P-M-5 findingje (a 2. kör):** a §8.2 **egy
> site** adataival számolt, **a 3 site-os F1 konfiguráció nem volt benne**
> → **a skálázási döntés (a §8.3) a valósnál kisebb adattal készült**.
>
> **A `preshaz` reviewer P-M-6 findingje (a 2. kör):** a mentés, a drill
> és a WAL-archivum együttes lemezigényének **nem volt egyetlen száma**
> → most a fenti táblázatban **van**: **a teljes lemezigény = a DB + a
> heti mentés + a WAL-archivum** → **a VPS lemezének mérete nélkül a
> TTL nem tervezhető meg** (a §10 Q6 — a tervezés blokkolója).

### 8.3 A mikor kell skálázni

| A jel | A küszöb | A lépés |
|---|---|---|
| a `p95` a katalógusoldalon | > 800 ms (az F-NF-01) | a `pool_size` növelése **vagy** a Read-replica |
| a `position` partíciója | > 5 GB | a `drop_expired_partitions` gyakorisága |
| a `pool_size` kimerül | a `pool_timeout` | a `pgbouncer` |
| a VPS lemez | > 85% | a tárhely bővítése |
| **a heti mentés idejére van hely** | **a DB + a mentés + a WAL-archivum együtt** | a tárhely bővítése **vagy** a mentés idejének áthelyezése |

**A 3 site (az F1) kapacitása (a `preshaz` reviewer P-C-2 findingje):**

| A számítás | Az érték |
|---|---|
| 1 site, 30 nap (a mérés) | ~27 millió üzenet |
| **3 site, 30 nap** | **~81 millió üzenet** |
| a feldolgozás egy site-ra (a mérésből) | **~7,5 óra** |
| **3 site egyszerre** | **~22,5 óra** → **egy éjszakát sem bír** |
| **a `COPY`-vel** (a `04` §9 — ~10× gyorsabb) | **~2,2 óra** |
| **a site-ok szekvenciális indítása** (a `09` §7.3) | **hetente 1 site** → **~45 perc/hét** |

**A megoldás — mindkettő egyszerre:**

1. **a `COPY` a `position`-re** (a `04` – parser-terv §9) → a 22,5 óra
   → **~2,2 óra**;
2. **a site-ok szekvenciális indítása** (a `09` §7.3 lépései) →
   **a heti lehúzás nem egyszerre, hanem site-onként** → **a heti
   lehúzás a `bud01`-gyel kezdődik** (a mérési időszak folytatása).

> **A mérési protokoll (a `04` §8) **a 3 site-ra is érvényes** legyen**:
> a `msg/hajó` arány site-onként mérendő → **a F1 küszöb (a 3 site,
> az 50%-os lefedettség) a teljes hálózatra vonatkozik**.



---

## 9. Az incidenskezelés

### 9.1 A három gyakori forgatókönyv

| # | A forgatókönyv | A tünet | A teendő | A helyreállás |
|---|---|---|---|---|
| **I1** | **a vevő leállt** (a Pi áram/SD/Wi-Fi) | a `ais_stats_hourly` üres órái, a heti lehúzás régebbi fájllal | a Pi újraindítása, a Wi-Fi/SD ellenőrzése | **a nyers adat a leállás pillanatáig megvan** → nincs adatvesztés, csak késés |
| **I2** | **a feldolgozás megállt** (a `job_run` `failed`) | a `position` nem nő, a watchdog riaszt | a `job_run.error_text` megnézése → a `alembic downgrade -1` + a `upgrade head` → a feldolgozás újraindítása | **a dedup idempotens** → **a feldolgozás újrafuttatható** (a `04` §6.1) |
| **I3** | **a DB megsérült** | a `psql` nem csatlakozik | a `03.2` visszaállítási próba szerint | **a PITR** a 7 napos ablakban |

### 9.2 A „visszaállítás semleges állapotból" forgatókönyv

**A legrosszabb eset: a DB és a nyers adat is elveszett.**
```
1. a legutóbbi teljes mentés visszatöltése (a 3.2)
2. a WAL-visszajátszás a PITR-pontig
3. a migrate (a 07 §5.3)
4. a heti lehúzott nyers fájlok újrafeldolgozása (a dedup idempotens!)
5. a smoke teszt (a 07 §9)
```
> **A 4. lépés a dedup miatt lehetséges** — a feldolgozás újrafuttatható
> a nyers fájlokból. **Ez a teljes adatvesztés elleni védelem.**

### 9.3 A incidensnapló

**Minden incidens** a `job_run`-ba (a `job_name='incident'` sor) →
**a `status`**, az `error_text` és a `started_at`/`ended_at` → **a
hónap végén a `09` §10 metrikája**.

---

## 10. A nyitott kérdések

| # | Kérdés | Az alapértelmezés | Az állapot |
|---|---|---|---|
| Q1 | **A watchdog a VPS-en fut-e vagy a NAS-on?** | **a VPS-en** (a központi DB-hez kell) — **a mérési időszakban a NAS-on** (a heti lehúzás ellenőrzése) — **a `07` §6.1a a deployban telepíti a crontábot** | **lezárva** (a `preshaz` reviewer P-C-5 findingje) |
| Q2 | **A riasztások csatornája** | **Telegram** (a `02` §13.2 szerint) — de a `watchdog.py` **a projekt kulcsát** használja, nem a Hermesét | nyitva |
| Q3 | **A Sentry bevezetése R1-ben?** | **igen** (a `SENTRY_DSN` a `07` §2.2-ben) — a `CRITICAL` szintű hibák oda mennek | nyitva |
| Q4 | **A restore-drill heti kötelező-e vagy havi?** | **heti** (a `02` §13.1: „*a mentés mindig visszaállítással ellenőrzött*") | **lezárva** (a `02` szerint) |
| Q5 | **A vevő heartbeatja hogyan érkezik a DB-be?** | a `ais_receiver_site.last_seen_at` a **feldolgozás** során frissül (a heti lehúzásból) → **a határ környezetfüggő: R1-ben 10 nap, R2-ben (élő MQTT) 30 perc** (a §4.1) | **lezárva** (a `prof` reviewer C-5 findingje) |
| Q6 | **A `position` 90 napos TTL-e a VPS lemezén elég-e?** | **~15–25 GB** (a mérésből) — a VPS lemezének mérete **ismeretlen** → **ez a tervezés BLOKKOLÓJA** (a `preshaz` reviewer P-L-1 findingje: a TTL a lemez mérete nélkül nem tervezhető meg) | **nyitva — **Miklós döntése** (a blokkoló)** |
| Q7 | **A watchdog ütemezése** | **óránként** (a host cron — a `07` §6.1a telepíti) — a `job_run` 24 órás ellenőrzés napi szinten elég | **lezárva** (a `preshaz` reviewer P-C-5 findingje) |

**A release-enkénti metrikák (a `release-terv` 11. fejezete):**

| A metrika | A forrás | A küszöb |
|---|---|---|
| a fordítások átnézettsége | a `content_text` riport | 100% (a F-NF-16) |
| az ENI-azonosítás aránya | a mérési riport | a mérési időszakban a mérés adata; R1-ben a kézi import |
| a lefedettség | a geográfiai korridor-riport | ≥ 50% (a F1) |
| **a flake-ek száma** | a CI összesítője (a `@pytest.mark.flaky`) | **a release előtt: 0 új flake** (a `08` §8.2) |
| az ENI-duplikátumok száma | a mérési query | 0 (a `vessel_identifier_active_uniq`) |
| a p95 a katalógusoldalon | az alkalmazás-monitorozás | < 800 ms (a F-NF-01) |

---

*Ez a terv a `docs/megvalosulas/` sorozat **kilencedik és utolsó** darabja.
Ezzel a terv-sorozat teljes (01–09). A `02` – DDL-terv §13.2 szerint a
watchdog itt készül — ez a terv az utolsó hiányzó lépés.*
