# Implementációs terv – 01: technológiai stack és projektstruktúra

**Verzió:** 1.3 (2026-11-15) — **a swarm review 2 körön át futott
(3 reviewer × 2 kör); a 2. kör 3 új blokkolót talált, azok is javítva**;
a review eredménye a §12-ben
**Dátum:** 2026-11-15
**Kapcsolódó dokumentumok:**
[`../../README.md`](../../README.md) (adatbázis-terv v1.3) ·
[`../../docs/funkcio-leiras.md`](../../docs/funkcio-leiras.md) ·
[`../../docs/release-terv.md`](../../docs/release-terv.md) ·
[`../../docs/r1-adat-terv.md`](../../docs/r1-adat-terv.md) ·
[`../../docs/ais-vevo-terv.md`](../../docs/ais-vevo-terv.md) ·
[`../../docs/ingest-terv.md`](../../docs/ingest-terv.md)

> A dokumentum a repóban a `docs/megvalosulas/megvalosulas-01-stack-es-struktura.md`
> útvonalon van — a relatív linkek ehhez képest számolnak.

**Ez a dokumentum** a hiányzó implementációs terv első darabja: a
technológiai stack kiválasztását, a projektstruktúrát, és a fejlesztési
környezet kialakítását rögzíti. Az R1 (hajókatalógus) release-re
optimalizál, de a struktúra R2–R5-re is kitart.

> **Az 1.0 → 1.1 változás:** a terv az első swarm review után
> **módosult**. A legfontosabb javítás: a Pi oldali szoftver `rtl_ais`-ról
> **AIS-catcher**-re változott, mert a `rtl_ais` **megszüntette volna a
> belvízi FI 10 dekódolását**, és ezzel az R1 katalógus teljes adatútját
> (ENI, folyó-km, fairway section, cél-UN/LOCODE, ETA zsilipnél, merülés).
> A teljes blokkolólista és a javítások: **§12**.

---

## 1. Miért kell ez a dokumentum

A meglévő tervdokumentumok (7 fájl, ~160 KB) a **mit**-et rögzítik
kiváló minőségben: az adatmodellt, a jogszabályi hátteret, a
forrásmátrixot, a funkciókat, a release-fázisokat. A *hogyan* hiányzott.

| Hiányzó döntés | Hol rögzül | Státusz |
|---|---|---|
| Alkalmazás-stack (backend, frontend) | §3.2 | ✅ lezárva |
| Nyelvi/runtime-verziók | §3.2 | ✅ lezárva |
| Projektstruktúra (monorepo vs. külön repók) | §4.2 | ✅ lezárva |
| Adatbázis-DDL | §8.1 + a 02-es terv | ✅ a scope lezárva, a DDL a 02-ben |
| Migrációs eszköz és stratégia | §3.2 (Alembic) + §4.3 (a generálás mechanizmusa) | ✅ |
| API-specifikáció | §2.2 (a funkciók) + a 03-as terv | ✅ a scope lezárva, a spec a 03-ban |
| CI/CD | §4.2 (a fa) + a 07-es terv | ✅ a scope lezárva |
| **Authentikáció és jogosultság (RBAC)** | **§3.2.2** | ✅ lezárva |
| Teszt-stratégia | §11.6 + a 08-as terv | ✅ a scope lezárva |
| Kódstruktúra, könyvtárlayout | §4.2 | ✅ lezárva |
| Lokal fejlesztési környezet | §6 + §11.3 | ✅ lezárva |
| **Observability (naplózás, mérés, trace)** | **§3.2.3** | ✅ lezárva |

Ezek nélkül a fejlesztés nem indítható el: két fejlesztő ugyanazt a
stacket választaná, de öt ember öt különbözőt.

---

## 2. Területi határok – mi tartozik R1-be

### 2.1 Az R1 release célja (a release-terv 3.1-ből)

> A felhasználó böngészhet és kereshet a Dunán és a Balatonon közlekedő
> hajók között, minden haJORól megtalálhatja a hivatalos adatait, három
> nyelven, forrásjelöléssel — térkép nélkül.

### 2.2 R1-ben **van**

| # | Funkció | F-xx (funkcióleírás) | Hol |
|---|---|---|---|
| 1 | Két elkülönített katalógus: **Duna** / **Balaton** (külön URL, szűrő, rendezés) | F-CAT-01, F-CAT-08 | §2.2, §8.1 |
| 2 | Katalóguslista szűréssel, rendezéssel, lapozással (a szűrés URL-ben megőrződik) | F-CAT-02, F-CAT-04, F-CAT-05, F-CAT-03 | 05 |
| 3 | Hajóadatlap: azonosítók, műszaki adatok, üzemeltető, állapot, történet | F-DET-01…08, F-DET-13 | §8.1, 05 |
| 4 | Globális kereső: hajónév + területenkénti azonosítók | F-SRCH-01…07 | 03 |
| 5 | Területenkénti szűrők (típus, üzemeltető, állapot, **bizonyossági szint**) | F-CAT-08, F-CAT-14 | §5.8.2, 05 |
| 6 | Háromnyelvű felület (hu/de/en), URL-prefix, `hreflang`, hiánylista-jelölés | F-INTL-01…08 | §3.2, §5.8.1, §5.8.3 |
| 7 | Szerkesztői felület: hajóadatok, fordítások, észrevételek, tömeges import, **claim** | F-ADM-01…09 | §4.5, §5.8.2 |
| 8 | Felhasználói javító észrevétel a hajóoldalon (**anonim**) | F-DET-11 | §5.8.2, 06 |
| 9 | Forrás- és frissítésdátum-jelölés **mezőnkénti eredettel** | F-NF-12, F-DET-15 | §5.8.2, §8.1 |
| 10 | Statikus tartalomoldalak: kikötők (Duna + Balaton), zsilip, folyószakaszok, hajótípusok | F-CNT-01, F-CNT-02 | §8.1 |
| 11 | Statikus cikkek/blog (három nyelven) | F-CNT-05 | §8.1 |
| 12 | Nyilvános JSON API a katalógushoz (v1) | F-API-01 (részleges) | 03 |
| 13 | SEO: sitemap, kanonikus URL, strukturált adat, `hreflang` | F-NF-04, F-NF-05 | §5.8.1 |

### 2.3 R1-ben **nincs** (és ezek ne is kerüljenek a kódba)

Térkép · élő pozíció-megjelenítés · ETA · útvonal-tervező ·
push-értesítés · **fiókregisztráció** (a szerkesztői belépés igen, a
publikus fiók nem) · vízállás · zsilipvárakozás · B2B API · webhooks.

> **Pontosítás (a `bori` reviewer L-2 findingje):** a „fiókbejelentkezés"
> korábbi megfogalmazása félrevezető volt. Az R1-ben **nincs** publikus
> fiókregisztráció, de **van** szerkesztői belépés (`app_user`), mert a
> szerkesztői felületnek (F-ADM) hitelesítés kell. A nyilvános oldalakon
> **nincs** bejelentkezés.

**Architekturális szabály:** a kódban ne legyen olyan általános megoldás,
amelynek R1-ben nincs használata, *kivéve* ha az R2–R5 tervezett
funkcióhoz *előkészítő* (lásd §8).

### 2.4 Amit R1-ben **muszáj** érinteni, mert az infrastruktúra

> **A swarm review (C-3) után pontosítva.** Az eredeti változat a
> `position` írását és a partícionálást R1-be sorolta, egyetlen
> `release-terv` 3.3-ra hivatkozó mondatra építve — miközben a
> `release-terv` **4. fejezete és a 8-as release-mátrix** az
> ingestet/partícionálást/archívumot **R2-be** teszi.

- **AIS-adat bevitel, statikus kivonatra korlátozva** (R1-0 fázisban
  fut) — a parser, a `ais_message_raw` nyers tábla és a `vessel` +
  `vessel_data_origin` feltöltése R1-ben készül.
- **A `position` sima, particionálatlan táblaként R1-ben** — az ingest
  buffer, amit a fantom-szűrő olvas (§5.5); **semmilyen felületi
  funkciót nem szolgál** (nincs térkép R1-ben). **A particionálás, az
  aggregáció és az archívum R2-be megy** (`release-terv` 4. fejezet:
  „Adatbeszerzés — AIS-feedintegráció, ingest, partícionálás, archívum").
  A részletes indoklás: §8.3.
- A **folyó-korridor geometria** — R1-adatkör, mert a fantom-szűrő
  (F-NF-17) R1-ben működnie kell (§5.5). Forrása: a `port` pontok
  (a `port.geom` Point) + a szakaszhatár-pontok; a `river_section` a
  szakasz **középvonalát** adja (a README 3.3 `river_section` oszloplistájában
  nincs `geom` oszlop → a 02-es DDL-terv dönt róla).
  **Az F-DET-06 („hol van", szövegesen, R1) forrása:** a hajó
  `river_section_id`-hez tartozó szakasz neve (`river_section_i18n.name`,
  három nyelven) + a `port` neve (`port_i18n.name`) — a szöveges hely
  ebből áll össze, a `vessel` nem külön tárolja.
- Az `app_user` séma — a szerkesztői felület (F-ADM) belépésre van szükség,
  tehát van szerkesztői felhasználó, de a *publikus* fiókregisztráció nincs.
- A `data_source`, `ais_receiver_site`, `job_run`, `data_quality_event` —
  a forrásjelölés (F-NF-12) és az ingest-napló alapja, R1-ben kötelező (§8.1).

---

## 3. Technológiai stack

### 3.1 Döntési szempontok

| # | Szempont | Súly | Miért |
|---|---|---|---|
| S1 | SEO (server-side rendering, hreflang, canonical, sitemap) | kritikus | A termék egyik fő értékajánlata a keresőpozíció; a README 1.1 ezt „SEO-kritikus"-nak nevezi |
| S2 | Háromnyelvűség URL-prefixszel (`/hu/…`, `/de/…`, `/en/…`) | kritikus | Nem query-paraméter, hanem útvonal — a nyelv a URL része |
| S3 | PostGIS + partícionálás + BRIN | kritikus | Az adatbázis-terv ezt rögzíti (5.3, 5.6) |
| S4 | Önálló fejlesztés 1 teljes stack fejlesztővel | magas | A release-terv 1. fejezete: „a becslések 1 teljes stack fejlesztőre vonatkoznak" |
| S5 | Kis csapat (1–2 fő), hosszú időhorizont, nem indulásra optimalizál | magas | A release-terv 10. fejezete: a tempót külső tényezők határozzák meg |
| S6 | Nyílt licencű, önállóan üzemeltethető | magas | A README 8. fejezete: „Minden séma-változás migrációs fájlban", heti `pg_basebackup` |
| S7 | Adatvédelem és jogi megfelelés (GDPR, általános adatvédelmi rendelet) | magas | A README 7.2 |
| S8 | Önkiszolgáló üzemeltetés (a NAS-on) | közepes | A projekt a Miklós saját infrastruktúráján fut |
| S9 | Kód-újrahasznosíthatóság, ha később mobilapp készül | közepes | A funkcióleírás 1.1 mobilappot ír le |

### 3.2 A stack

> **A swarm review (H-9, H-10, H-11, M-1, M-2, M-3, M-14) után
> pontosítva.** Az eredeti változat több technikai tévedést tartalmazott
> (`pg_cron` a stock PostGIS image-ben, nem létező Astro-direktíva,
> egy nem létező `docs/_config.yml` hivatkozás, a README 0. fejezetének
> „javaslattá" minősítése indoklásként).

**Backend: Python 3.14 + FastAPI + SQLAlchemy 2.0 (async) + Alembic**

| Elem | Választás | Indoklás |
|---|---|---|
| Nyelv | **Python 3.14** | Az AIS-parser (NMEA/AIS 6 bites dekódolás) Pythonban a leggyorsabban írható és a legjobban tesztelhető; a `pi-eloallitas.md` is Pythont ír elő a Pi-oldalra. A 3.13 **2026-10-01-től security-fázisban van**, ezért a baseline 3.14. Az async I/O a ~2 M üzenet/nap ingesthez kell. |
| Web-framework | FastAPI | Natív async, automatikus OpenAPI-generálás (S1/S2: a specifikáció kód-ból jön), Pydantic-alapú validáció a 8. § i18n-mechanizmusához |
| ORM | SQLAlchemy 2.0 async | `AsyncSession`; a PostgreSQL-specifikus részek (partíció, BRIN, GiST, `COPY`) nyers SQL-ben mehetnek át ahol kell |
| Migráció | Alembic | Az industry standard; a README 8. „számozott, visszafordítható" migrációkat kér — ez Alembic default |
| Validáció | Pydantic v2 | A `r1-adat-terv.md` 7. fejezete validációs szabályokat ír le → ezek Pydantic modellekbe mehetnek |
| AIS-dekódolás | **saját dekóder** (`apps/api/src/duna/ingest/`) | A teljes indoklás és a verifikált `aiscat`/`pyais`/saját összehasonlítás: **§5.3** |
| Időzítés | **APScheduler** (a Celery elutasítva) | Az ingest-feldolgozás ütemezett (a statikus kivonat, a fantom-szűrő, a heti frissítés). Az APScheduler a FastAPI-processzen belül fut, nincs külön broker; a Celery overkill egy 1 csapatos projekthez. **A havi partíció-létrehozás NEM itt történik** — azt a `pg_cron` végzi (lásd a következő sor). **Q9 lezárva.** |
| Háttérfeladat | Uvicorn worker + **`pg_cron` custom image-ben** | A havi partíció-létrehozás a DB-be job, nem az appba. **A `postgis/postgis:16-3.4` stock image-ben NINCS `pg_cron`** → custom Dockerfile kell: a `postgis/postgis:16-3.4` image **arra a `postgres:16` image-re épül**, amiben a `pg_cron` extension már szemcsomagolva van → a Dockerfile a `postgresql-16-cron` **apt csomagját** telepíti a PostGIS image fölé, és a `shared_preload_libraries = 'pg_cron'` beállítással indít. A részletek: 07 – CI/CD. |
| Teszt | pytest + pytest-asyncio + testcontainers | A DB-integrációs tesztek valódi PostgreSQL-t használjanak (a PostGIS-specifikus rész miatt) |

**Frontend: Astro + TypeScript + React (szigetek) + Tailwind**

| Elem | Választás | Indoklás |
|---|---|---|
| Framework | **Astro 5** | A katalógusoldal **90% statikus SEO-tartalom** (hajóadatlap, kikötőoldal, cikk) — az Astro zero-JS alapértelmezése pontosan erre való |
| Kimenet | `output: 'static'` + **`@astrojs/node` adapter** | A statikus oldalok build-kor generálódnak; a szerveroldali szigetekhez (a figyelőlista R2-ben) kell az adapter. A `read: "Forward"` **nem létező Astro-direktíva** — a helyes megoldás a `server:defer` Server Island. |
| Interaktivitás | React szigetek (`client:load` / `client:visible`) | A szűrés, lapozás és a kereső élő — de csak ott, ahol kell |
| Stílus | Tailwind CSS v4 | Halott kód nélküli utility-first; a design system a `content_key`/`content_text` UI-szövegekkel kombinálva |
| Nemzetköziség | `astro:i18n` — **a konfiguráció rögzítve** | Lásd alább. |
| Tartalom | **A cikkek a DB-ben vannak** (`article_i18n.body_md`) | A README 3.3 E) ezt írja elő. Az MDX **csak a fejlesztői dokumentációra** való (`docs/`) — nem a felhasználói cikkekhez. **A DB-ből épülő cikkek miatt a weboldalnak újraépülnie kell** — lásd §3.2.1 |
| Kliensoldali állapot | Nanostores | Astro-natív, framework-független |

#### 3.2.1 A DB-ből épülő tartalom és az újraépítés mechanizmusa

> **A `prof` reviewer 2. körös C-N2 findingje után.** A cikkek a DB-ben
> vannak (a README 3.3 E) szerint), a web Astro `output: 'static'`-ban
> épül → **a szerkesztés után újraépítés kell**, különben az oldal
> elavul. A tervben ez korábban nem volt megnevezve.

| Elem | Megoldás |
|---|---|
| **Ki indítja az újraépítést?** | a `article`/`content_text` mentése (a 06-os terv) egy **`rebuild`  végpontot** hív a `web` build-pipeline-re |
| **Hogyan?** | a `web` build egy **hookot** kap (`WEBHOOK_URL` env → a build kiszolgáló), amit a szerkesztői mentés hív; a hook `POST /rebuild` → a CI/CD egy `web-build` jobot indít, ami az Astro buildet futtatja és a kimenetet a statikus hosztra tolja |
| **Ha a build elbukik?** | a `content_text.status` **nem** vált `published`-re, hanem `review`-ban marad → a hibás cikk nem kerül ki; a hiba a szerkesztői felületen látszik |
| **Mennyi ideig?** | a build célszerűen **1–3 perc**; a szerkesztő a mentés után ezt látja: „a cikk 2 perc múlva jelenik meg" |
| **Statikus vs. szerver** | **statikus marad** (a `output: 'static'` a SEO-hoz kell) — az újraépítés a tartalom változására triggerelődő deploy, nem per-request SSR |
| **R1-ben ez fut?** | **igen** — a cikkek R1-ben is DB-ben vannak (§8.1), tehát az újraépítés R1-kötelező |

**A `webhooks` (F-API-04, R5) és a rebuild-hook nem ugyanaz!** A
`webhooks` a külső felhasználóknak értesítő kiszolgáltatás (R5); a
rebuild-hook a **belső** tartalom-deploy mechanizmus (R1). A §2.3
„webhooks"-ot az R1-en kívüli funkciók közé sorolja — ez **a publikus
webhook API-ra** igaz, a belső rebuild-hookra nem.

**A `07 – CI/CD` terv feladata:** a rebuild-hook végpontja, a build
trigger, a `content_text.status` → `published` gating, és a build-idő
monitorozás.

#### 3.2.2 Hitelesítés és jogosultság (RBAC)

> **A `prof` reviewer 2. körös H-7 findingje után.** A README 7.3 hat
> DB-szerepkört ír le, de a **HTTP-szintű** mechanizmus nem volt
> megnevezve — és a szerkesztői belépés R1-kötelező (a `app_user`
> a §2.4 szerint).

| Szerep | Ki | Hitelesítés | R1-ben? |
|---|---|---|---|
| `anon` | a publikus látogató | nincs | ✅ |
| `app_user` | a felhasználó (saját figyelőlista) | **R2** — a figyelőlista R2 | ❌ R1-ben nincs ilyen szerep |
| `editor` | a szerkesztő | **session cookie + jelszó** | ✅ |
| `admin` | az admin | **session cookie + jelszó** | ✅ |
| `etl` | az ingest folyamat | **service token** (a `mqtt` oldali) | ✅ |
| `api_client` | a B2B kliens | API-kulcs (hashelve) | **R5** |
| `viewer` / `reporter` | a visszajelző | nincs (anonim) | ✅ |

**A mechanizmus R1-ben:**

| Elem | Megoldás |
|---|---|
| **Session** | szerveroldali session (`session_id` a `app_user` táblában), a jelszó **Argon2id** hashként (`password_hash`), a cookie `HttpOnly` + `SameSite=Lax` + `Secure` |
| **A `app_user` séma bővül** | `password_hash`, `role` (`editor` \| `admin`), `session_expires_at`, `last_login_at` — a 02-es DDL-terv rögzíti |
| **A middleware** | FastAPI dependency, ami a `role`-t ellenőrzi a route-onként; a `templates/admin/` minden oldala ezen megy át |
| **A `/admin` belépés** | a login-forma a `templates/admin/login.html`; a sikeres belépés után a `session_id` a cookie-ba |
| **A jelszócsere** | az első belépéskor kényszerített (a seed `app_user` jelszó nélkül jön létre) |
| **A `etl` service token** | a MQTT-ből érkező ingest a `X-Ingest-Token` headerrel; a token a `data_source`-hoz kötött, nem felhasználóhoz |
| **Az anonim visszajelzés** | a `POST /feedback` route **nem** igényel hitelesítést (F-DET-11) |
| **A DB-szerepkörök** | a README 7.3 szerinti hat szerep a DB-grant szinten (a 02 + 07-es terv) |

**Miért nincs fiókregisztráció R1-ben:** a funkcióleírás szerint a
figyelőlista R2; a szerkesztői felületet belső felhasználók használják.

#### 3.2.3 Observability

> **A `prof` reviewer 2. körös H-7 findingje után.** A README 8.
> fejezete a figyelést felsorolja, de a mechanizmus nem volt megnevezve.

| Elem | Megoldás | Hol |
|---|---|---|
| **Naplózás** | strukturált JSON log (`python-json-logger`), a `request_id` a `X-Request-ID` headerben és minden log-sorban | §9 |
| **A `job_run` tábla** | az ingest futásnaplója: `job_name`, `started_at`, `ended_at`, `status`, `rows_in`, `rows_out`, `error_text` — ez a README 3.3 G)-ben már szerepel | §8.1 |
| **A `data_quality_event`** | a dead-letter és az adatminőségi események | §8.1 |
| **Mérés** | a `/metrics` endpoint (Prometheus-formátum): a kérések száma, a p95 latency, a DB-kapcsolatok, az ingest ütemezettsége | §9 |
| **A vevő heartbeat** | az `ais_receiver_site.last_seen_at` — a kiesés = adatlyuk → riasztás | §8.1 |
| **Trace** | **R2** — a teljes elérési lánc nyomkövetése (OTel) a R1-ben nem indokolt | — |
| **Alerting** | a NAS-on futó health-check cron (a `nas-openhab-mqtt` skill mintája) ellenőrzi a `job_run` státuszokat és a `last_seen_at`-et | §9 |

**Amit a `09 – Üzemeltetés` terv rögzít:** a mérőpontok listája, a
riasztási szabályok, a napló-retention, és a health-check ütemezése.

**Az Astro i18n-konfiguráció (rögzítve):**

```js
// apps/web/astro.config.mjs
export default defineConfig({
  site: 'https://vessel-tracker.example.hu',   // a valós domain a deploynal
  output: 'static',
  adapter: node({ mode: 'standalone' }),
  i18n: {
    locales: ['hu', 'de', 'en'],
    defaultLocale: 'hu',
    routing: {
      // F-NF-05: minden nyelv kapjon prefixet, különben a /hu/... és a
      // /... duplikátum lenne (canonical-sérülés).
      prefixDefaultLocale: true,
    },
  },
});
```

A `src/pages/` alatt `hu/`, `de/`, `en/` könyvtárak vannak (a
`prefixDefaultLocale: true` azt jelenti, hogy **a default nyelv (a magyar) is prefixet kap** — tehát a magyar a `/hu/...` útvonalon érhető el, nem prefix nélkül. (Prefix nélkül csak akkor lenne elérhető, ha `prefixDefaultLocale: false` lenne — de akkor F-NF-05 sérülne, mert a `/...` és a `/hu/...` ugyanazt az oldalt szolgálná ki.)
**A DB-szintű fordítás-fallback (a README 4.3: kérés → `en` → `hu` → kód)
külön réteg**, az Astro route-fallbacktől függetlenül.

**Adatbázis: PostgreSQL 16 + PostGIS 3.4** — a README 0. fejezete ezt
*rögzíti* (nem „javaslat"), ezért a terv nem vitatkozik vele.

**Verziókezelés: Git + GitHub (VorosEgyes szervezet)**

**CI/CD: GitHub Actions** — a Miklós másik projektjeinél (`espRadar`, `ArcDice`) már van ilyen workflow, és a `nas-openhab-mqtt` skill is GitHub Actions-t használ.

**Konténerizálás: Docker Compose** — a NAS-on fut, a `nas-openhab-mqtt` skill topológiája alapján.

### 3.3 Elutasított alternatívák

| Alternatíva | Miért nem |
|---|---|
| **Node.js / Next.js** | A teljes SSR-t a Next adja, de a katalógusoldal szinte teljesen statikus — az Astro ugyanazt a SEO-t adja kevesebb JS-sel és kisebb csomagmérettel. A Python amúgy is kell az AIS-parserhez, így egy nyelv a backenden (a pipeline) kevesebb kontextusváltást jelent. |
| **Django** | Beépített admin panel előny, de a 30+ modellre a „saját kód" admin nem elég; a REST API és a szerkesztői felület más igény. A Django ORM a PostGIS-specifikus részeknél (partíció, BRIN) korlátos. |
| **Rails / Laravel** | Ugyanaz a leképezés: a séma erősen SQL-specifikus (partial unique index, BRIN, partition), ezek ORM-független migrációkban jobban kezelhetők. |
| **FastAPI + Jinja SSR (Astro nélkül)** | Astro a statikus + sziget hibridet adja ingyen; a kétszeri template-egyeztetés (Astro + Jinja) hibák forrása. |
| **GraphQL** | A funkcióleírás nem ír elő rugalmas kliens-queries-t; a REST + OpenAPI egyszerűbb, és a B2B API (R5) nyilvános, verziózott RESTként van tervezve. |
| **TimescaleDB** | A README 5.5 explicit döntése: „induljunk csak PostgreSQL-rel", a séma legyen TimescaleDB-kompatibilis. |
| **ClickHouse / dedikált time-series DB** | A `position` tábla ~120 M sor, de a lekérdezési minták (katalógus, kereső) relációsak; a PostGIS+PostgreSQL egy rendszerben kezeli a geo- és az i18n-adatokat is. |
| **Prisma / Drizzle (ORM)** | A partícionálás, a BRIN, a partial unique index és a PostGIS operátorok kézi SQL-t igényelnek; ezek ORM-független migrációban tisztább. |
| **Celery** | Az APScheduler ugyanazt megadja a havi/­ heti ütemezéshez, külön broker és külön processz nélkül. |
| **`aiscat` (a referencia által előírt)** | GPLv3-at örököl az AIS-catcher C++ motorjától; a mezőszintű inland-szemantika mellett is a licenc a döntő ok. A teljes összehasonlítás: §5.3, Q12. |


### 3.4 A döntés hatása a becslésre

> **A swarm review (preshaz C-1) után átírva.** Az eredeti mondat
> („a stack-választás a becslést nem változtatja meg") **igaz a
> stackre, de hamis volt a scope-ra**: a §8 eredeti táblázata R1-be
> vitt elemeket, amelyeknek nincs finanszírozó sprintje.

A release-terv 1. fejezete: „Méretek: S = ~1 hét, M = ~2–3 hét,
L = ~4–6 hét" — **1 teljes stack fejlesztőre**. Az R1 sprint-becslése
(3.7) 4 sprint × M/L.

**A stack-választás önmagában nem változtatja meg a becslést** — a
technológiai kockázat (S3/S4: ismeretlen territory) csökken, mert a
stack a fejlesztő mindennapi eszközkészlete.

**DE a tanulási és integrációs költséget a becslés nem tartalmazza:**
a §3.2 stack **21 döntési sort** és a §4.2 struktúra **24 kódhelyet**
hoz, és a release-terv 1. fejezete *egy* fejlesztővel és *nulla*
tanulási puffertel számol. A tanulási költség becslése:

| Stack-elem | Tanulási költség (saját becslés) |
|---|---|
| Astro + Tailwind v4 + a Server Island modell | ~1 hét (az első Astro-projekt) |
| FastAPI + async SQLAlchemy 2.0 + Alembic | ~1 hét (a szokásos Python-stack, minimális) |
| PostGIS + partícionálás + BRIN/GiST | ~3–5 nap |
| A saját AIS-dekóder (töredékes mondat, checksum, tag-block, DAC/FID) | ~2 hét (a mérési adatok nélkül nem kezdhető) |
| **Összesen** | **~4–5 hét = 1 sprint M-része** |

**Ez a tanulási költség a `release-terv` 3.7 sprint-táblázatából
hiányzik.** A döntés: a tanulási idő **az R1-0 fázisban** (a vevőépítés
3–6 hónapja alatt) keletkezik — nem az R1 fejlesztési sprintjeiben. Erre
a §7 függőségi táblázat utal, de a becslésben **nincs benne**.

**Amit ez a fejezet rögzít:** a terv-sorozat 9 terve **nem egyenlő a
4 fejlesztői sprinttel** — a tervek a teljes R1-et (a release-terv 3.7
sprintjei + az R1-0 előkészítés) fedik le, és a 02–09 terv mindegyike
egy-egy sprint **részének** felel meg:

| Implementációs terv | release-terv 3.7 sprint | Becslés (1 fejlesztő) |
|---|---|---|
| 01 (ez) — stack + struktúra | sprint 1 (projekt-alapozás) része | S |
| 02 — DDL + migrációk | sprint 1 | M |
| 03 — API-specifikáció | sprint 1–2 | M |
| 04 — AIS-parser | **sprint 0 (R1-0)** + sprint 2 | L (a mérési adatokkal együtt) |
| 05 — frontend-arkitektúra | sprint 3 | M |
| 06 — szerkesztői felület | sprint 2 | M |
| 07 — CI/CD + környezetek | sprint 1 | S |
| 08 — teszt-stratégia | a sprint-eken át | M |
| 09 — üzemeltetés | sprint 1 + 4 | S |

**Amit a terv NEM dönt el** (a `release-terv` 3.7 módosítása kell hozzá):
az R1 **4 sprint** marad, vagy **5**? A `preshaz` C-1 findingje szerint
a négy R1-be hozott elem (partícionálás, materializált nézet, konvoj-séma)
a 3.7 sprint-tartalmában nincs megnevezve → nincs finanszírozó sprintje.

**A prof review (C-3) után a terv állapota:** a `position` írása,
a partícionálás, az aggregáció és a `convoy` séma **R2-be** került
(§8.2) → **a scope-többlet megszűnt**, és a 4 sprint finanszírozható.
A `release-terv` 3.3 mondatának pontosítása és a 8-as mátrix R1/R2
jelölése a **§8.3** szerinti teendő — de a becslés nem sérül.

**A tanulási puffer:** a fenti ~4–5 hét az R1-0 alatt (a vevőépítés
3–6 hónapja) elhasználódik, mert a parser fejlesztése (04-es terv)
**a mérési adatokra vár** — és azok az R1-0 alatt keletkeznek. Így
a tanulás nem a fejlesztési sprintből jön, hanem **előre fizetett
R1-0-idő**. Ez a `release-terv` 3.4.1 üzenetének megfelel: „a 0. sprint
(előkészítő, saját vevő építése) a formális R1 **eleje**, nem utólagos
teendő."

---

## 4. Projektstruktúra

### 4.1 Egy repo, nem több

**Döntés: egy monorepo** (`vessel-tracker`), a dokumentumokkal együtt.

> **A repo neve 2026-11-15-én változott:** `duna-hajokoveto` →
> **`vessel-tracker`**. Az eredeti név a Duna-t hangsúlyozta, but a
> projekt hatóterülete a Duna **és** a Balaton (a katalógus mindkettőt
> kezeli, a séma területfüggetlen), és a „követő" az R1 statikus
> katalógusra nem pontos.
>
> **A GitHub-repo létrejött 2026-11-18-án:**
> **https://github.com/VorosEgyes/vessel-tracker** (publikus, `main`).
> A repó a tervezési dokumentumokat és az implementációs terv-sorozatot
> tartalmazza; a `main` branch védett (force push tilos).

| Alternatíva | Miért nem |
|---|---|
| Külön repo a backendre, a frontendre, a dokumentumokra | 1 csapat, 1 release-terv, közös séma-változások. A séma-migráció és a kliens API-kliens generálás szinkronban kell legyen — külön repóban ez fájlok másolása, ami elcsúszik. |
| Külön repo a dokumentumoknak | A terv és a kód ugyanaz a projekt. A dokumentum a kód mellé kerül, és a CI ellenőrzi a linkeket (S6 §10.1). |

### 4.2 A struktúra

```
├── justfile                     ← a kanonikus parancsok (dev, test, lint, db-migrate, seed, up)
├── .env.example                 ← minden környezet változóinak neve, érték nélkül
├── .pre-commit-config.yaml      ← ruff, prettier, egy közös hook
├── .gitignore                   ← node_modules/, .venv/, *.db, .env
├── alembic.ini                  ← a migrációk belépési pontja
├── ruff.toml / .eslintrc / .prettierrc
├── uv.lock / pnpm-lock.yaml     ← a reprodukálható build
├── LICENSE                      ← a projekt licence (Q12)
├── pyproject.toml
├── package.json                 ← workspace root
├── pnpm-workspace.yaml
├── README.md                    ← a projekt bemutatása
├── docs/                        ← a meglévő 7 tervdokumentum + az implementációs tervek
│   ├── funkcio-leiras.md
│   ├── release-terv.md
│   ├── r1-adat-terv.md
│   ├── ais-vevo-terv.md
│   ├── ingest-terv.md
│   ├── pi-eloallitas.md
│   ├── sema-core.mmd
│   ├── sema-irodalom.mmd
│   └── megvalosulas/            ← ÚJ: a részletes implementációs tervek
│       ├── README.md            ← a 9 terv státusszal és olvasási sorrenddel
│       ├── 01-stack-es-struktura.md      ← ez a dokumentum
│       ├── megvalosulas-02-adatbazis-ddl.md
│       ├── megvalosulas-03-api-specifikacio.md
│       ├── 04-ais-parser.md
│       ├── 05-frontend-architektura.md
│       ├── 06-szerkesztoi-felulet.md
│       ├── 07-ci-cd-es-kornyezetek.md
│       ├── 08-teszt-strategia.md
│       └── 09-uzemeltetés-es-observability.md
├── db/                          ← Alembic migrációk + seed
│   ├── migrations/versions/
│   ├── seeds/                   ← referenciaadat seed (kikötők, zsilip, típusok)
│   └── ddl/                     ← a teljes DDL referencia (olvasható, nem a migráció forrása)
├── apps/
│   ├── api/                     ← FastAPI alkalmazás
│   │   ├── Dockerfile
│   │   ├── src/duna/
│   │   │   ├── main.py
│   │   │   ├── config.py        ← pydantic-settings
│   │   │   ├── db/              ← session, modellek, unit-of-work
│   │   │   ├── api/v1/          ← routerek (vessel, port, search, content, feedback, admin)
│   │   │   ├── schemas/         ← Pydantic request/response
│   │   │   ├── domain/          ← üzleti logika, tiszta függvények
│   │   │   ├── repositories/    ← SQLAlchemy query-k
│   │   │   ├── services/        ← use-case-ek (catalog_search, i18n_resolve)
│   │   │   ├── i18n/            ← nyelv-feloldás, fallback-lánc (a TÁROLÁS a DB-ben: content_text + *_i18n)
│   │   │   └── ingest/          ← AIS parser + pipeline (R1-0)
│   │   ├── templates/admin/     ← a szerkesztői felület Jinja2 sablonjai (§4.5)
│   │   └── tests/
│   ├── web/                     ← Astro
│   │   ├── Dockerfile
│   │   ├── src/
│   │   │   ├── pages/{hu,de,en}/  ← /hu/duna/hajok, /hu/balaton/hajok …
│   │   │   ├── components/
│   │   │   ├── i18n/              ← a routing + a DB-fallback hívó
│   │   │   └── content/           ← MDX: CSAK a fejlesztői dokumentáció
│   │   └── astro.config.mjs
│   └── pi/                      ← a Pi oldali kód (AIS-catcher indítás, MQTT publisher)
├── packages/
│   ├── api-client/              ← generált TS kliens az OpenAPI-ból
│   └── shared/                  ← a generált típusok + a kézi formázó-segédfüggvények
├── infra/
│   ├── docker/
│   │   ├── docker-compose.yml   ← lokális fejlesztés
│   │   ├── docker-compose.prod.yml
│   │   └── postgres/Dockerfile  ← a pg_cron-t tartalmazó custom image (§3.2)
│   ├── mosquitto/               ← az ingest-terv 4.1/4.2 konfigurációja
│   │   ├── mosquitto.conf
│   │   └── acl
│   └── nginx/                   ← reverse proxy, rate limit
├── scripts/
│   ├── seed/                    ← seed-generátorok
│   └── checks/                  ← adatminőségi riportok
└── .github/workflows/
    ├── ci.yml
    └── release.yml
```

### 4.3 A könyvtárak miért különválnak

| Döntés | Indoklás |
|---|---|
| `api/`, `web/`, `pi/` külön alkalmazás | A web Astro (build-time static), az API hosszú életű szerver, a Pi oldali kód egy másik gépen fut. Külön processz, külön skálázás, külön deploy-ciklus. |
| Az admin **nem** külön alkalmazás R1-ben | Az R1 szerkesztői felülete adatszerkesztés (táblázat + űrlap), nem vizuálisan gazdag alkalmazás. A FastAPI + Jinja2 admin jobb arány. A tömeges CSV-import **offline pipeline** (nem HTTP-feltöltés) — §4.5. Az R2+ push-értesítésekhez lehet saját frontend, de R1-ben nem kell. |
| `db/ddl/` **generált** fájl, nem kézi forrás | A `db/migrations/` (Alembic) a séma **forrása**; a `db/ddl/` a teljes sémát egy olvasható fájlban mutatja (a `psql` bootstraphoz és a review-hoz). **A CI diff-ellenőrzést futtat** a kettő között — különben elcsúsznak (H-8). |
| `packages/shared` **generált** típusokat tartalmaz | A Zod sémák és a TS típusok az OpenAPI-ból jönnek; a `packages/shared` a kézi képlőhelyettesítőket (formázás, dátum, pénznem) tartalmazza — nem a duplikált sémákat (H-8). |
| `packages/api-client` generált | Az OpenAPI-ból generált TS kliens: a kliens és a szerver nem divergálhat. |
| `docs/megvalósulas/` a `docs/` alatt | A meglévő 7 dokumentum a *terv*, az új 9 az *implementáció*. A README 8. fejezete utal a migrationökre, tehát a kód a dokumentumok mellé kerül, nem helyettük. |

### 4.4 Monorepo eszköz

**pnpm workspaces** (frontend) + **uv** (Python, egy `pyproject.toml` a
teljes backendhez).

Az `uv` a Miklós környezetében már használt (a Hermes konténerben
`/usr/local/bin/uv` van) és a Python projekt toolchain-ajánlása.

### 4.5 Az `apps/admin` döntés felülvizsgálata

> **A swarm review (H-6) után átírva.** Az eredeti döntés (az admin az
> Astro `web` app egy route-ja) **nem fedte le** a funkcióleírás
> F-ADM-01…07 követelményeit: a tömeges CSV-import (fájl-feltöltés,
> előnézet, hibajelentés) és a konfliktuskezelés nem Astro-route-ban
> megvalósítható.

Az R1 szerkesztői felületének követelményei (funkcióleírás 4.10 — **a
sorszámok a referencia szerinti eredeti számozás**):

| ID | Követelmény (a funkcióleírás szerint) | Hol valósul meg R1-ben? |
|---|---|---|
| F-ADM-01 | A hajóadatok szerkesztése (műszaki adatok, üzemeltető, engedélyek) | ✅ a FastAPI/Jinja admin — űrlap + táblázat |
| F-ADM-02 | A hajónév és az egyéb fordítható mezők szerkesztése fordításonként | ✅ a `*_i18n` táblák szerkesztője (§5.8.4: a hajónév nem fordul, a leírás igen) |
| F-ADM-03 | Forrás- és bizonyítékmező minden kézzel módosított adathoz (ki, mikor, honnan) | ✅ a `vessel_data_origin` mezőnkénti eredete + az `audit_log` before/after (§5.8.2) |
| F-ADM-04 | A felhasználói észrevételek (F-DET-11) feldolgozhatók egy listában | ✅ a `feedback` tábla + státusz-lista |
| F-ADM-05 | **A fordítási hiánylista**: mely kulcsok/szövegek hiányoznak vagy elavultak | ✅ a `content_text.status` (draft/review/published) + a hiányosság-lekérdezés a dashboardon (§4.5.1) |
| F-ADM-06 | **Előnézet a hajóoldal minden nyelvén**, a megjelenés ellenőrzéséhez | ✅ az admin oldalon nyelvenkénti előnézet (a 06-os terv) |
| F-ADM-07 | Tömeges import hajólista CSV-ből (ENI-vel) | ✅ **offline pipeline** (§4.5.2) — nem Astro-route |
| F-ADM-08 | **Az üzemeltetői önbevallás (claim) kezelése**: beérkezett kérelmek listája, egyeztetés az AIS-rekorddal, jóváhagyás vagy elutasítás indoklással | ✅ a `vessel_data_origin` `origin='operator_claimed'` soraival + a jóváhagyás/elutasítás `audit_log`-ban (§5.8.2) |
| F-ADM-09 | **Konfliktuskezelés**: ha az AIS-adat és az üzemeltetői állítás eltér, **mindkettő látszik**, és a szerkesztő dönt | ✅ a mezőnkénti kétértékű megjelenítés (§5.8.2) |

#### 4.5.1 A fordítási hiánylista (F-ADM-05)

A hiánylista **lekérdezés**, nem tárolt adat: a `content_text` és a
`*_i18n` táblák állapotából számítandó.

| Mérce | Definíció |
|---|---|
| **Kulcs-hiány** | a `content_key` létezik, de a kért nyelven nincs `content_text` sor |
| **Elavult fordítás** | a `content_text.status = 'draft'` vagy `status = 'review'` (a `published` a kész) |
| **Hiánypontszám** | a kulcsok és a szövegek aránya a `content_key` és a `*_i18n` táblákban, nyelvenként |

A dashboard ezt nyelvenként mutatja (a README 4.4: „minden entitáshoz
lekérdezhető a fordítások teljessége (százalék), ez a szerkesztői
felület dashboardja").

#### 4.5.2 A tömeges import (F-ADM-07) — az offline pipeline

A `release-terv` 3.5 kilépési feltétele: „a teljes katalógus
importálható CSV-ből a szerkesztői felületen". A megvalósítás:

| Lépés | Mi történik | Hol |
|---|---|---|
| 1. **Fájl feltöltése** | a CSV a `scripts/seed/` pipeline-ba kerül (nem HTTP-feltöltés) | 06 |
| 2. **Validáció** | a `r1-adat-terv.md` 7.1 szabályai: az ENI-formátum, a kötelező mezők, a **duplikált ENI/MMSI elutasítása** | 06 |
| 3. **Dry-run** | nincs írás — csak az előnézeti jelentés: új / módosított / ütköző / hibás sorok száma, és egy minta-diff | 06 |
| 4. **Ütközés-jelzés** | a meglévő `vessel` rekorddal ütköző sorok **külön listázva** — a felhasználó dönt | 06 |
| 5. **Jóváhagyás** | a jóváhagyott sorok bekerülnek; minden mező a `vessel_data_origin`-ba kerül `origin='editorial'` (vagy `'operator_claimed'`) jelöléssel | 06 |
| 6. **Audit** | az `audit_log` rögzíti, ki, mikor, mit importált | 06 |

**A `release-terv` mondat pontosítása:** a „szerkesztői felületen" itt
azt jelenti, hogy a **szerkesztő dönti el** a jóváhagyást — a feldolgozás
offline pipeline, nem egy böngészőben futó űrlap.

**Döntés: az admin R1-ben a FastAPI által kiszolgált
szerver-renderelt oldal** (Jinja2 sablonok a `templates/admin/` alatt,
a `web` Astro app **nem** tartalmaz admin route-ot). Az indok:

1. a szerkesztői felület **adat-grid**, nem SEO-tartalom — az Astro
   zero-JS modellje itt nem ad előnyt;
2. a tömeges CSV-import **offline pipeline** (a fenti 6 lépés);
3. a konfliktuskezelés a `vessel_data_origin` kétértékű megjelenítésével
   történik (AIS-érték vs. üzemeltetői állítás), nem külön konfliktus-
   feloldó UI-val.

**Amit ez nem érint:** a `web` Astro app a **publikus** felület
(katalógus, hajóadatlap, kikötők, cikkek, SEO). Az admin külön réteg.

---

## 4.6 Az `apps/admin` — a döntés eltolódása az eredeti §4.2 struktúrától

Az eredeti §4.2 struktúra `apps/admin/` alatt külön alkalmazást jelölt.
A fenti döntés szerint **R1-ben nincs külön `apps/admin` alkalmazás** —
a szerkesztői felület a `apps/api/` FastAPI alkalmazás része
(`templates/admin/` + statikus assetek). Az `apps/admin/` hely a későbbi
(R2+) önálló admin alkalmazás számára fenntartott hely.

---

## 5. Az AIS-adatút: a Pi, a dekóder és az ingest

> **Ez a fejezet a swarm review (C-1, C-2, H-1, H-2, H-3) után íródott át.**
> Az eredeti változat `rtl_ais`-t írt elő a Pi-re és teljesen mellőzte a
> referencia által előírt `AIS-catcher`-t — ami **megszüntette volna a
> belvízi FI 10 dekódolását**, és ezzel az R1 katalógus teljes
> adatútját (ENI, folyó-km, fairway section, cél-UN/LOCODE, ETA zsilipnél,
> merülés RNW).

### 5.1 Mi az, amit a referencia rögzít

| Referencia | Tartalom |
|---|---|
| `ais-vevo-terv.md` 10.5 | A szoftver **AIS-catcher**: „Statisztikai felület, JSON kimenet, **belvízi (FI 10) dekódolás**, webes felület". Az `rtl_ais` melléje: „működik, de **nincs belvízi FI 10 dekódolás** és nincs ilyen diagnosztika". |
| `ingest-terv.md` 3.2 | A konkrét indítás: `/usr/bin/AIS-catcher … -Q mqtts://… topic 'duna/ais/bud01/msg' qos 1 msgformat JSON_FULL -D sqlite:/var/lib/ais/ais.db …` → a MQTT-kimenet **JSON_FULL**, nem nyers NMEA. |
| `ingest-terv.md` 4.3 | A szerver oldalon **újradekódolás**: a hitelesített mezők **nem** a Pi JSON-ját használják. |
| `ingest-terv.md` (forráshiv.) | `aiscat` Python csomag — „a központi újradekódoláshoz, `Decoder`, `from_tcp`/`from_udp`/`from_stdin`". |
| `pi-eloallitas.md` | „[AIS vevő] → [Pi: AIS-catcher] → [MQTT/WireGuard] → [szerver]"; „Szoftver | AIS-catcher (**a belvízi FI 10 dekódolás is kell**)". |
| `r1-adat-terv.md` 0–1 | Az R1 katalógus **kizárólag** az AIS-ból épül; a `river_km` a **FI 10 fairway hectometre** mezőből jön. |

### 5.2 A lánc — három réteg, egy forrás az igazságra

| Réteg | Szoftver | Kimenet | Felelős |
|---|---|---|---|
| **Pi (vevő)** | **AIS-catcher** (`-Q mqtts://… topic 'duna/ais/<site>/msg' qos 1 msgformat JSON_FULL`, `-D sqlite:/var/lib/ais/ais.db retention 14`) | MQTT `JSON_FULL` üzenet, amiben a `nmea` mező a **nyers NMEA** | A vevő + a helyi diagnosztika |
| **Szerver (ingest)** | **saját dekóder** (`apps/api/src/duna/ingest/`) | A `nmea` mező **újradekódolása** → normalizált rekord | Az egyetlen hiteles forrás |
| **Szerver (adatbázis)** | — | `ais_message_raw`, `vessel`, `position`, `job_run`, `data_quality_event` | A pipeline írási céljai |

**Miért van az újradekódolás?** Mert a Pi JSON-ja nem tekinthető
forrásnak: a `ingest-terv.md` 4.3 fejezete explicit módon ezt mondja ki
(„a hitelesített mezők – **nem** a Pi JSON-ját használjuk"). Az AIS-catcher
a belvízi dekódolást elvégzi (ezért kell a Pi-oldali szoftver), de a
szerver a **nyers NMEA-t** dekódolja újra — így a szerveroldali dekóder
verziója kontrollálja a mezőértelmezést, nem a Pi firmware-e.

**Miért kell a Pi JSON-ja, ha a nyers NMEA is benne van?** Az AIS-catcher
JSON-ja tartalmazza a **vevőállapotot** (jelerősség, üzenetszám,
időbélyeg, hibaszám) — ez a `data_quality_event` és az
`ais_receiver_site.last_seen_at` heartbeat forrása. A `nmea` mező viszont
a dekódoláshoz használt nyers adat.

> **A `nmea` mező TÖMB, nem skalár** (az AIS-catcher a töredékes
> üzeneteket külön sorokban adja át) → a szerveroldali parser a
> `nmea` tömböt **összefűzi** a 2. pont szerinti sorrendben. A `04` –
> AIS-parser terv rögzíti a pontos formátumot.

### 5.3 A dekóder-döntés — összehasonlítás (a futtatás a Q8 feladata)

> **A `prof` reviewer 2. körös H-N1 findingje után.** Az eredeti
> változat a táblázatot „verifikált összehasonlítás"-nak nevezte és a
> `pyais`-ról azt állította, hogy „mezőszinten nem strukturált" — ez
> **hamis volt**: a `pyais` `MessageType8Dac200Fid10` osztálya neves
> mezőket ad (`vin` 48 bit = ENI, `shiptype` 14 bit = ERI-kód, `length`,
> `beam`, `draught` 11 bit, `loaded`, `hazard`). **A összehasonlítás még
> nem futott** — a Q8 nyitott kérdés ezt rögzíti.

| | `aiscat` | `pyais` | saját dekóder |
|---|---|---|---|
| Licenc | **GPLv3** (az AIS-catcher C++ motorját örökli) | MIT | saját |
| Nyelv | Python wrapper + C++ motor | tiszta Python | tiszta Python |
| **Inland FI 10** (DAC 200 / FID 10) | igen | **igen** — `MessageType8Dac200Fid10` (a 3.3.1-es PyPI-kiadásban) | igen |
| ENI (FI 10) | igen | **igen, mezőszinten** (`vin`, 48 bit) | igen |
| ERI-típuskód | igen | **igen, mezőszinten** (`shiptype`, 14 bit) | igen |
| Méretek, merülés | igen | **igen, mezőszinten** (`length`, `beam`, `draught`) | igen |
| **fairway km (folyó-km)** | igen | **mezőszinten** (a `shiptype`/pozíció blokkban) | igen |
| Cél-UN/LOCODE, ETA zsilipnél | igen | részben mezőszinten | igen |
| Verziófrissítés Pi-érintés nélkül | igen | igen | igen |
| Függőség az ingest-kritikus útvonalon | GPL-korlát | tiszta Python | nincs |

**Döntés: saját dekóder.** Az indok **nem** a `pyais` mezőszintű
hiányossága — a `pyais` a belvízi mezők egy részét **adja**:

1. **licenc** — az `aiscat` GPLv3-at örököl az AIS-catcher C++ motorjától;
   a projekt nyílt licencű terméket épít → a származékos munkák
   terjesztési korlátját külön ellenőrizni kell (Q12);
2. **kontroll** — az ingest-kritikus útvonalon nem akarunk futásidejű
   külső függőséget;
3. **teljes mezőlefedés** — a projektnek a fairway km, az UN/LOCODE és a
   zsilip-ETA **saját** mezőszintű reprezentációj kell (a `river_km`
   denormalizálva, `source_kind`-del), nem egy könyvtár nyers mezőit kell
   átalakítani minden fogyasztónak.

**Amit ez NEM állít:** hogy a `pyais` mezőszinten nem tudja a FI 10
mezőket. **Amit állít:** hogy a projektnek több mező kell, mint amit a
`pyais` tiszta Pythonban strukturáltan ad — és ez a **Q8 futtatott
összehasonlítással igazolandó**, nem feltételezés.

**A becslés valós komplexitása (≈400 sor helyett ≈700 sor):** a
töredékes mondat összefűzése, az NMEA checksum-ellenőrzés, a tag-block
(`\s:…,c:…`) kezelése, a 6 bites ASCII kódolás hibakezelése, a DAC/FID
dispatch, és a `toa`/`rxuxtime` időbélyeg-szétválasztás — ezek adják a
munka nagy részét.

### 5.4 A szerveroldali dekóder feladata

1. **NMEA szétesztése és összefűzése** — a töredékes mondatok
   (`$!AIVDM,1,2,…` / `$!AIVDM,2,2,…`) összefűzése, checksum-ellenőrzés
2. **6 bites AIS karakterkódolás** dekódolása hibakezeléssel
3. **Üzenettípus-dispatch** — négy oszlop:

   | Üzenet | Tartalom | R1-ben |
   |---|---|---|
   | **Msg 8 / DAC 200 / FID 10** (Inland Ship Static & Voyage) | ENI, ERI-típuskód, méretek, **fairway hectometre**, merülés (RNW), cél-UN/LOCODE, ETA zsilipnél | **igen — ez a katalógus gerince** |
   | **Msg 5** (Static & Voyage) | hívójel, név, méretek, cél-UN/LOCODE | igen (a nem-belvízi hajók statikus adatai) |
   | **Msg 18** (Class B Position Report) | pozíció, SOG, COG — a **kisebb hajók** (motorcsónak, vitorlás) | a pozíció írása R2 (§8.3), de a **statikus kivonat** (a hívójel/név, ha van) R1-ben |
   | **Msg 24** (Class B Static Data Report) | hívójel, név, méretek — a Class B hajók statikus adatai | **igen — a Balaton-katalógushoz kell** (F-CAT-01) |
   | Msg 1/2/3 (Position Report, Class A) | pozíció, SOG, COG | a `position` tábla (R1-ben sima buffer, §8.3) |
   | Msg 4 / 9 / 21 / 22 | bázisállomás, SAR, segédnavigáció | **eldobandó** (nem hajók) |

   **A `ais-vevo-terv.md` 4. diagramja a parser bemenetét felsorolja:
   „parser (Msg 1/3/5/18/24 + Inland FI 10)" — a terv most ezt követi.**

4. **Időbélyeg-kezelés** — a `received_at` (ingest idő) és a `ts` (üzenet
   időbélyege) külön; a `position` PK-ja **(`vessel_id`, `ts`)** — ez a
   dedup-kulcs is (`ON CONFLICT (vessel_id, ts) DO UPDATE`, a README 6.2
   és az `ingest-terv.md` 4.3/5. lépése)
5. **A folyó-km két forrásból** — elsődlegesen a **FI 10 fairway
   hectometre** mezőből; **tartalék eljárásként** (a nem-FI-10 hajóknál)
   geometriai illesztéssel a folyó-korridorra, `source_kind = 'derived'`
   jelöléssel (H-5)

### 5.5 A fantom-szűrő — területenként, R1-ben megvalósítható

A `release-terv` 3.6 kockázata („magas" valószínűség) és az `F-NF-17`
(„0 db fantom hajó") a katalógus hitelességének kulcsa. A szűrőnek
**R1-ben** működnie kell, tehát nem építhet a R2-ben bevezetett élő
térképre.

**A szűrő három szabálya (a `bori` reviewer C-1 findingje után — az
első verzió túl szigorú volt, és kizárta a Balaton-katalógust és a
bárkákat):**

1. **A pozíció-alapú szűrő CSAK az AIS-ből érkező Duna-hajókat
   érinti.** A Balatoni katalógus kézi/üzemeltetői forrásból épül
   (funkcióleírás 6.2) → **nem esik alá a szűrőnek**. A szárazföldön
   álló balatoni motorcsónak az R1-ben a katalógusban van, a
   `vessel.status` mezővel jelezve.
2. **A szűrő kizáró szűrő, nem eldobó szűrő.** Az AIS-static-listában
   a pozíció nélküli hajó **`excluded` státuszba** kerül
   (`data_quality_event`-tel), nem törlődik. A pipeline **újrafuttatható**
   a szűrő finomhangolása után — így a 30 napos mérés alatt kiderülő
   túl szigorú szűrő nem okoz adatvesztést, mert a kizárt hajók
   nyomon követhetők.
3. **A bárkák a konvoj tagjaként kerülnek be**, a vezető pozíciójából
   származtatva (`source_kind='derived'`, README 2.2). A bárka nem
   AIS-entity (r1-adat-terv 10.), de **az R1 katalógusban szerepel** —
   a konvoj megjelöléssel, nem önálló pozícióval.

| Lépés | Szűrő | Mire vonatkozik | Miért |
|---|---|---|---|
| 1. **Pozíció-ellenőrzés** | a pozíció a folyó-korridor **polygonján belül** van, **ÉS** a hajó nem áll 5+ napig ugyanott | **csak az AIS-ből érkező Duna-hajók** | a `position` ingest bufferből (R1-ben sima tábla, §8.3) + a folyó-korridor geometriája (R1-adatkör: a `port` pontokból + a szakaszhatár-pontokból épül — a 02-es DDL-terv rögzíti) |
| 2. **Sebesség-ellenőrzés** | a `sog` **0 és 12 csomó között** van | ugyanaz | a Duna legnagyobb hajói is lassabbak — a `ais-vevo-terv.md` 4.2 |
| 3. **Kézi kizáró lista** | a legismertebb „szárazföldi" MMSI-k (hajógáyak kikötői, munkahajók) | ugyanaz | az `ais-vevo-terv.md` 4.2; a lista a `db/seeds/`-ben, szerkeszthető |
| 4. **Frissességi ellenőrzés** | a pozíció az utolsó 90 napban keletkezett | ugyanaz | az elhagyott hajók kiesnek — **`excluded` státusszal**, nem törléssel |

**A szárazállási korlátozás nem fantom:** ha egy hajó a vízen áll
(kikötőben, zsiliptől várakozva), az pozíciója van → bent marad. A
F-NF-17 a **szárazföldi** pozíciókat zárja ki, nem a kikötőben állókat.

**A szűrő eredménye három helyre kerül:**
1. a `vessel.status` (`active` / `excluded` / …) — a katalóguslista
   szűrője;
2. a `data_quality_event` — a kizárás nyomon követhető;
3. az ingest futásnapló (`job_run`) — a szűrő futása újrafuttatható
   a paraméterek finomhangolása után (**a kizált hajók nem vesznek el**,
   csak kiszűrésre kerülnek).

**A saját vevő előnye itt is látszik:** minden üzenetet mi tárolunk, így
a szűrőután is visszakereshető, és a későbbi elemzések nem torzulnak
(`ais-vevo-terv.md` 4.2).

### 5.6 Az ingest írási céljai

| # | Írási cél | Tartalom | R1-ben |
|---|---|---|---|
| 1 | `ais_message_raw` | a nyers NMEA, 14 nap TTL, havi partíció | **igen** |
| 2 | `vessel` + `vessel_i18n` | a statikus kivonat (ENI, hívójel, név, típus, méretek) | **igen** |
| 3 | `position` | **sima, particionálatlan tábla** — az ingest buffer, amit a fantom-szűrő olvas (§5.5); a UI nem olvassa | **igen** (a particionálás, az aggregáció és a `position_archive`/`position_hourly` **R2**) |
| 4 | `job_run` | az ingest futásnaplója | **igen** |
| 5 | `data_quality_event` | a dead-letter és az adatminőségi események (a kizárt hajók is ide kerülnek) | **igen** |
| 6 | `convoy` / `convoy_member` | a konvoj-séma és a bárka-tagok (a származtatott pozíció írása R2) | **séma: igen**, felbontás: R2 |
| 7 | Parquet-objektátár | a nyers NMEA hosszú távú archívuma | **R2** (H-13 — a terv 01 nem tartalmaz tárhelyet; a 02-es DDL-terv a `db/ddl/`-ben rögzíti a sémát) |

### 5.8 A felhasználói felület rétegei, amiket a 05/06-os terv örököl

> **A `bori` reviewer 2. körös H-3, H-4, H-5 és M-1 findingjei után.**
> Ezek a mechanizmusok a 01-es tervben **névvel és felelősséggel**
> rögzítendők, mert a 02/03/05/06-os tervek öröklik őket — ha itt
> nincsenek megnevezve, a hézagok nem szűrhetők és a későbbi tervek
> kimaradnak velük.

| Réteg | Hol rögzül | A felelős terv | Miért itt |
|---|---|---|---|
| **SEO-mechanizmusok** — `hreflang` + `x-default`, kanonikus URL, `robots.txt`, a hajóadatlap-URL-minta (`/{lang}/duna/hajok/{slug}`), a strukturált adat-séma (`Vessel`), a sitemap | §5.8.1 | 05 – frontend-arkitektúra | A tervnek meg kell neveznie, hogy **melyik mechanizmus** hol van; a 05 megvalósítja |
| **Claim-kezelés** (F-ADM-08/09) — az üzemeltetői önbevallás, a konfliktus megjelenítése | §5.8.2 | 06 – szerkesztői felület | A `vessel_data_origin` séma R1 (§8.1), de a **működés** a szerkesztői felületben van |
| **Nyelvfüggő formázás** (README 4.6–4.7) — `Intl.NumberFormat`, `Intl.DateTimeFormat`, az SI-alapú tárolás, az ICU MessageFormat a paraméterezett szövegekhez | §5.8.3 | 05 – frontend-arkitektúra | A tárolt érték **mindig SI-alapú**; a formázás soha nem a DB-ben |
| **A hajónév fordítása** (M-1) | §5.8.4 | 05 – frontend-arkitektúra | A `release-terv` 3.4 és a funkcióleírás 6.1/F-DET-01 ellentmond egymásnak — a döntést itt kell meghozni |

#### 5.8.1 A SEO-mechanizmusok (a 05-ös terv örökli)

| Mechanizmus | Követelmény | Megjegyzés |
|---|---|---|
| **URL-minta** | `/{lang}/{terület}/hajok/{slug}` és `/{lang}/{terület}/kikotok/{code}` | A `terület` = `duna` \| `balaton` (F-CAT-01: külön URL-tér) |
| **`hreflang`** | minden nyelv + `x-default` → a `hu` | A `prefixDefaultLocale: true` miatt a magyar is prefixet kap (§3.2) |
| **Kanonikus URL** | a saját nyelvi URL-re mutat | F-NF-05: nincs duplikáció a nyelvi URL-ek között |
| **`robots.txt`** | a keresőknek; a `?` query-szűrők `noindex` | A szűrés URL-ben marad → a szűrős oldalak ne indexelődjenek |
| **Strukturált adat** | `schema.org/Vessel` a hajóadatlapon, `schema.org/Article` a cikkeken | F-NF-05 |
| **Sitemap** | a sitemap-index a nyelvek szerint, `hreflang` hivatkozásokkal | |
| **Open Graph / Twitter Card** | a hajóadatlaphoz | nem kötelező, de a linkmegosztáshoz kell |

#### 5.8.2 A claim-kezelés (a 06-os terv örökli)

- A `vessel_data_origin` mezőnkénti eredetet tárol (`origin`:
  `ais` | `operator_claimed` | `official` | `editorial`) — a séma R1-ben
  (§8.1).
- A konfliktus **látható**: ahol az AIS-érték és az üzemeltetői állítás
  eltér, a felület **mindkettőt megjeleníti**, jelölve, hogy melyik a
  hiteles (a `confidence` és az `observed_at` alapján).
- A `verification_level` (`ais_identified` | `ais_partial` |
  `operator_claimed` | `name_only`) a katalógus **szűrője** (F-CAT-14)
  — a Balatoni bejegyzések jellemzően `operator_claimed` szinten vannak.
- A `claim` űrlap a szerkesztői felületen (a 06-os terv), anonim
  bejelentés nem — a claim hiteles üzemeltetői adat.

#### 5.8.3 A nyelvfüggő formázás (a 05-ös terv örökli)

| Elem | Szabály |
|---|---|
| **A tárolt érték mindig SI-alapú** | m/s, m, t, m³, °C — a DB-ben nincs „km/h" vagy „lb" |
| **A formázás kliensoldalon** | `Intl.NumberFormat(locale)`, `Intl.DateTimeFormat(locale)` — soha nem a DB-ben |
| **Mértékegység-rendszer** | a `app_user.unit_system` (`metric` \| `imperial` \| `nautical`) alapján, a kliens konvertál |
| **Paraméterezett szövegek** | ICU MessageFormat szintaxis a `content_text`-ben: `A(z) {vessel} hajó {delay} perc késéssel érkezik a(z) {port} kikötőbe.` — így a magyar, német és angol mondatsorrend is helyes marad |
| **A `language` katalógus** | `code` (char2), `name_native`, `name_en`, `is_rtl` — a UI a `lang` cookie/header alapján választ |

#### 5.8.4 A hajónév fordítása — a döntés

**Döntés: a hajónév NEM fordul.** A hajó hivatalos neve latin betűs és
egységes (a `release-terv` 3.4: „a hajónevek hivatalos neve latin betűs,
egységes, tehát **a hajónevek nem igényelnek fordítást**").

Ez **felülírja** a funkcióleírás 6.1/F-DET-01 („a kiválasztott nyelven")
és F-ADM-02 („fordításonként") szövegét a **hajnév** mezőnél.

**A `vessel_i18n` tábla ettől még létezik** — nem a hajnév miatt, hanem
a **leírás** miatt (a `description` mező: „Ez a hajó a Duna legmélyebb
pontján …" — ez valóban nyelvenként eltér). A `name` mező a `vessel_i18n`-ben
a **hivatalos latin nevet** tárolja (minden nyelven azonos), a
`description` a nyelvenkénti szöveg.

**Amit ez a döntés érint:** a katalógus keresője a hajónévre **minden
nyelven azonos értékkel** talál (a `vessel_i18n.name` + a `vessel_alias`
+ az azonosítók együtt) → a `packages/shared` kereső-kliensnek **nem
kell** nyelvenkénti hajónév-változatot kezelnie.

### 5.9 A parser elfogadási tesztje

Az `ingest-terv.md` 9. fejezetének ellenőrzőlistája a mérce:
az első éles fogadáskor a teljes lánc (AIS-catcher → MQTT → szerver →
adatbázis) együtt fut, és a parser csak akkor tekinthető késznek, ha a
lista minden pontja zöld.

**A parser fejlesztése nem kezdhető meg a vevő előtt:** a tesztfixture-ök
valódi rögzített NMEA sorok, amik a mérés során keletkeznek
(`ais-vevo-terv.md` 10. fejezete). A fixture-ök generálhatók a `pyais`
vagy az `aiscat` referencia-implementációval (**tesztadat-generálásra**,
nem futásidejű függőség), de a **goldenset** a valós rögzítések adják.

---

## 6. Környezetek

> **A swarm review (C-5) után pontosítva.** Az eredeti változat a
> staginget „a local seed + éles sémával frissítve"-ként definiálta,
> ami ellentmond a README 8. fejezetének: „Staging | Éles adatmásolat
> maszkolt felhasználói adatokkal; a teljes éles séma **és
> adatmennyiség** reprodukálható egy lépésben". A seed kis
> adathalmaz → a p95 SLO-k (README 5.7) a stagingen **nem mérhetők**.

| Környezet | Cél | Adatbázis | AIS-feed |
|---|---|---|---|
| **local** | Fejlesztői gép, `docker compose up` | seedelt Postgres+PostGIS | nincs (fixture-ök) |
| **staging** | Integrációs teszt, a NAS-on | **éles adatmásolat** maszkolt felhasználói adatokkal (README 8.) — a séma **és az adatmennyiség** reprodukálható egy lépésben; a `pg_dump`/`pg_basebackup` + maszkolás a `scripts/`-ben | a saját vevő élő feedje (read-only) |
| **production** | A NAS-on | éles | a saját vevő + később a hub feed |

**Nincs külön „dev DB a fejlesztő gépén" és „staging"** — a developer
Docker Compose a local-hoz tartozik, a staging a NAS-on fut a
production mellett.

**A seed a LOCAL környezet seedje, nem a staging adathalmaza.** A
`db/seeds/` referenciaadatok (kikötők, zsilip, hajótípusok) a local
környezetet töltik fel; a staging az éles példányról készül
`pg_basebackup`-kal, a felhasználói adatok maszkolásával.

**A p95 SLO-k (README 5.7: katalógusoldal < 800 ms, hajóadatlap
< 300 ms, kereső < 150 ms) a STAGING adatmennyiségén mérendők**, nem a
local seeden — különben a mérés nem reprezentatív.

### 6.1 Docker Compose (local)

Szolgáltatások:

| Szolgáltatás | Kép | Feladat |
|---|---|---|
| `postgres` | **custom image** (`infra/docker/postgres/Dockerfile`) a `pg_cron`-nal, mert a `postgis/postgis:16-3.4` stock image-ben **nincs** (§3.2) | a DB |
| `api` | a repóból buildelt (`apps/api/Dockerfile`) | a REST API + a szerkesztői felület + **az ingest MQTT-fogyasztó** |
| `web` | a repóból buildelt (`apps/web/Dockerfile`) | az Astro build kimenete (statikus) |
| `nginx` | a repóból buildelt (`infra/nginx/`) | a 8080-as reverse proxy, a rate limit |
| `mqtt` | Mosquitto, a `infra/mosquitto/{mosquitto.conf,acl}` konfigurációval | az ingest-terv 4.1/4.2 szerinti broker |

**Az ingest-processz futtatóegysége (a `prof` reviewer 2. körös H-N5
findingje után):** az MQTT-fogyasztó **az `api` konténeren belül fut**, egy
külön processzként (`python -m duna.ingest.worker`), nem külön
compose-szolgáltatásként. A `docker-compose.yml`-ben a `api` szolgáltatás
`command:`-je indítja mindkettőt (`uvicorn` + az ingest worker), vagy
a `docker-compose.override.yml` definiál egy `ingest` szolgáltatást
ugyanazzal a `build:`-del.

**R1-ben az ingest a statikus kivonatot végzi** (a `position` bufferbe
ír, amit a fantom-szűrő olvas — §5.5); a `position` partícionálása és
az aggregáció R2 (§8.3).

**A `mqtt` szolgáltatás R1-ben is kell**, mert az ingest-terv a
„Pi → MQTT → központi ingest" láncot rögzíti, és a pipeline-t a
fejlesztés során is tesztelni kell.

---

## 7. A projekt ütemezésének hatása a tervre

A `release-terv.md` 3.4.1 alapján az **R1-0 fázis (3–6 hónap)** a
saját AIS vevőhálózat építése, és ez a projekt legfontosabb
időablaka. Ez az implementációs terv-sorozat **nem** várja meg az
R1-0 végét: a kódfejlesztés és a vevőépítés **párhuzamosan** futhat.

**Amit ez a terv-sorozat ütemez** (a `preshaz` C-1 és H-6 findingje után
a `release-terv` 3.7 sprint-táblázatához igazítva):

| Megvalósítási terv | Tartalom | release-terv 3.7 sprint | Függőség |
|---|---|---|---|
| 01 (ez) | Stack, struktúra, környezetek | sprint 1 (projekt-alapozás) része | – |
| 02 | Adatbázis-DDL v1.1 + migrációk (**a folyó-korridor geometria definíciójával** — a `port` pontokból + a szakaszhatár-pontokból, a `river_section` középvonalával; a `river_section.geom` oszlop a README 3.3-ban nem létezik → itt döntünk róla) | sprint 1 | 01 |
| 03 | API-specifikáció (OpenAPI) | sprint 1–2 | 01, 02 |
| **04** | **AIS-parser specifikáció és implementáció** | **sprint 0 (R1-0)** + sprint 2 | 01, **a mérési adatok** |
| 05 | Frontend-arkitektúra (SEO, i18n routing) | sprint 3 | 01, 03 |
| 06 | Szerkesztői felület | sprint 2 | 03, 05 |
| 07 | CI/CD, környezetek, deploy | sprint 1 | 01 |
| 08 | Teszt-stratégia | a sprint-eken át | 02, 03, 04 |
| 09 | Üzemeltetés, observability | sprint 1 + 4 | 02, 07 |

**A 04-es terv (a parser) az R1-0-ba tartozik** — a `release-terv` 3.7
sprint-0 sora a „saját AIS-vevő, 30 napos mérés, **parser (Msg 5 +
Inland FI 10)**, **fantom-szűrő**" elemeit tartalmazza. A parser
fejlesztése **a mérési adatokra vár**, amik az R1-0 alatt keletkeznek
(§5.7) — ezért nem lehet a fejlesztési sprintek egyikébe sem
belehelezni, és ezért nem is finanszírozható a 4 sprintből.

**Amit ez a terv-sorozat NEM tartalmaz, és a `release-terv` 3.7
kiegészítése igényli:** a **10. terv — a Pi-vevő üzemeltetése**
(antenna, AIS-catcher indítás, WireGuard, MQTT publisher, a
telephelyek üzemeltetése). Ez a `ais-vevo-terv.md` 2. és 10. fejezetének
operatív része, nem implementációs terv — **a 10. terv csak akkor
szükséges, ha a vevőüzemeltetés is a szoftveres csapat feladata**.

**A függőségi sorrend konzisztenciája:** a 02 → 03 → 05 → 06 lánc
soros; a 04 párhuzamosan futhat a 02-vel (a tiszta dekódolás nem függ a
sémától, csak az ingest *írása* függ); a 07 a 01-re épül; a 08 és a 09
a végső sprintre.

---

## 8. Az R1 adatmodellje — mi kerül be R1-be, mi nem

> **A swarm review (C-3, C-4) után íródott át.** Az eredeti táblázat
> tíz R1-kötelező adatköröt nem tartalmazott, és az `position`-írás
> R1-be sorolása ellentmondott a `release-terv` R2-es scope-jának.
> A táblázat most **a README 3.3 táblajegyzékének teljes lefedését**
> adja — ez a terv-sorozat scoping-alapja.

### 8.1 Az R1-be **beleszülő** adatkörök (teljes lista)

| Adatkör | Táblák | Miért R1-kötelező |
|---|---|---|
| **Vízút és szakaszok** | `waterway`, `waterway_i18n`, `river_section`, `river_section_i18n`, `gauge`, `gauge_i18n` | A katalógus szűrője a folyószakasz; a szakaszok adják a folyó-korridor **középvonalát** — a fantom-szűrő referenciája (§5.5). A `river_section.geom` oszlop nincs a README 3.3 oszloplistájában → a 02-es DDL-terv dönt róla |
| **Kikötők, kötődömök, terminálok, zsilipek** | `port`, `port_i18n`, `berth`, `terminal`, `lock`, `lock_i18n` | A statikus tartalomoldalak (R1 10. pont); az `unlocode` a kereséshez |
| **Hajótípusok** | `vessel_type`, `vessel_type_i18n` | Minden hajótípus lefordítva három nyelvre (R1 DoD) |
| **Üzemeltetők** | `operator`, `operator_i18n` | A `vessel.operator_id`, a `terminal.operator_id`, a `lock.operator_id` és a `marina.operator_id` mind R1-táblák FK-ja, és az **F-CAT-08** (R1) üzemeltető-szűrőt kér |
| **Hajók** | `vessel`, `vessel_i18n`, `vessel_alias` | A katalógus magja |
| **Azonosítók** | `vessel_identifier` | Területenként eltérő azonosítók (Duna: ENI/MMSI/…, Balaton: hajószám/nemzeti szám) — README 2.10b |
| **Mezőnkénti eredet** | `vessel_data_origin` | F-DET-15 (M, R1); R1 DoD: „mezőnkénti eredettel" — a konfliktus látható |
| **Forrás-nyilvántartás** | `data_source` | A forrásjelölés és a licenc-nyilvántartás alapja (F-NF-12) |
| **Saját vevőhálózat** | `ais_receiver_site` | A forrásjelölés telephelyszinten; a `last_seen_at` heartbeat a kiesés-riasztáshoz |
| **Nyers AIS-üzenetek** | `ais_message_raw` | A statikus kivonat nyers alapja; 14 nap TTL; havi partíció |
| **Ingest-napló és dead-letter** | `job_run`, `data_quality_event` | A hibák nem esnek el csendben (README 6.2) |
| **Háromnyelvűség (adat)** | `content_key`, `content_text`, `translation_task`, `language` + **minden `*_i18n`** (`vessel_i18n`, `port_i18n`, `lock_i18n`, `vessel_type_i18n`, `waterway_i18n`, `river_section_i18n`, `cargo_type_i18n`, `route_i18n`) | **Az Astro `i18n` csak a routingot adja — a fordítás a DB-ben van** (README 4.1–4.5) |
| **Balaton** | `basin`, `basin_i18n`, `marina`, `vessel_service_period` | A Balaton-katalógus R1-ben van: külön URL, külön szűrők, szezonlogika (README 2.10) |
| **Tartalom** | `notice`, `notice_i18n`, `notice_type`, `event`, `event_i18n`, `event_type`, `article`, `article_i18n`, `article_category` | Statikus tartalomoldalak + blog (R1 11. pont). A `notice_type` és az `event_type` FK-val hivatkozott kódkatalógus (a README 3.3 E) a `notice.notice_type` FK-ját említi); az `article_category` az `article.category_id` FK-ja |
| **Engedélyek és útvonalak** | `vessel_cert`, `route`, `route_stop`, `route_i18n`, `cargo_type`, `cargo_type_i18n` | Az adatlap műszaki adatai; a kereső a UN/LOCODE-ra |
| **Rendszer** | `country`, `unit`, `currency`, `fx_rate`, `feature_flag` | A referenciatáblák |
| **Szerkesztői és audit** | `app_user` (szerkesztői belépés), `audit_log`, `feedback` | F-ADM-03 (audit), F-ADM-04 (visszajelzés) — a szerkesztői felület és a forrásbizonyíték |
| **Rendszer-meta** | `job_run` (fent), `data_quality_event` (fent), `ais_gap` | A hajó „néma" periódusának nyilvántartása |

### 8.2 Az R2-be **halasztott** adatkörök

| Adatkör | Mikor | Miért nem R1-ben |
|---|---|---|
| `position` **sima, particionálatlan** tábla (R1-ben) | **R1** | **A fantom-szűrőnek pozíció kell** (§5.5) — a szűrő R1-ben fut, tehát a pozíciónak is léteznie kell. Az R1-ben a `position` az ingest buffer: a nyers pozíciókat írja, a szűrő olvassa, a UI **nem** olvassa (nincs térkép R1-ben). **A particionálás, az 5 perces/1 órás aggregáció és az archívum R2** (`position_archive`, `position_hourly`, a havi/éves partíciók) — a `release-terv` 4. fejezete szerint |
| `convoy` / `convoy_member` **séma** | **R1** | A bárkák R1-ben is konvoj-tagként szerepelnek a katalógusban (§5.5), a vezető pozíciójából származtatva — a séma kell, a **felbontás** (a származtatott pozíció írása) R2. A `convoy.vessel_id` FK-ja a `vessel`-re mutat; az `voyage_id` FK-ja a `voyage`-ra **R2-ben** lép be (a `voyage` a §8.2 R2-listájában) |
| `voyage`, `voyage_stop`, `voyage_cargo` | **R2** | A README 3.3 D) szerint az utazás-adatkör: a `release-terv` 6. fejezete (R4) az „Utazás/ETA" release-re teszi. Az R1-ben a **cél-UN/LOCODE** az AIS statikus kivonatból jön (a `vessel`-hez kötve), nem külön `voyage` rekordban |
| `position_archive`, `position_hourly`, `vessel_last_position` materializált nézet, a `position` partícionálása | **R2** | A `release-terv` 4. fejezete: „**Adatbeszerzés** — AIS-feedintegráció, ingest, partícionálás, archívum" → R2. Az R1-ben a `position` sima tábla (a szűrő bufferé) |
| `ais_message_raw` Parquet-objektátár-archívum | **R2** | A hosszú távú nyers archívum (ingest-terv 4.3/8. lépés) |
| `watchlist`, `alert_rule`, `alert_event`, `device_token` | **R2** | Élő adatot igényel |
| `eta_prediction` | **R4** | Élő adatot igényel |
| `water_level`, `lock_passage`, `lock_status` | **R4** | Élő/hatósági adatforrás |
| `trip_plan`, `position_report` | **R4** / **R2** | Fiókalapú, élő funkciók |
| `api_client`, `api_key` | **R5** | B2B |
| `vessel_schedule` (Balatoni menetrend) | **R3** | A release-terv 3.2 szerint R3-től |

### 8.3 Az eltérés a release-tervtől — explicit blokk

A `release-terv` 3.3 fejezete egyetlen mondattal („Az AIS-adatvétel már
R1-ben fut (statikus gyűjtés), csak a felület hiányzik") sugallja, hogy
az ingest R1-ben van, míg a 4. fejezet és a 8-as release-mátrix az
ingestet/partícionálást/archívumot **R2-be** sorolja.

**Döntés: az R1-ben a `position` egy sima, particionálatlan tábla** — az
ingest buffer, amit a fantom-szűrő olvas (§5.5). **A particionálás, az
5 perces/1 órás aggregáció és az archívum (`position_archive`,
`position_hourly`) R2-be megy** — a `release-terv` 4. fejezete és a 8-as
mátrix szerint. Az R1-ben a `position` **semmilyen felületi funkciót nem
szolgál** (nincs térkép R1-ben) — kizárólag a szűrő adata.

**Ez a döntés a `bori` reviewer 2. körös H-7 findingjét oldja:** a
fantom-szűrő R1-ben fut (az F-NF-17 „0 db fantom hajó" R1 kilépési
feltétel), tehát a pozíció-adatnak is R1-ben kell léteznie. Az
alternatíva — a szűrő R2-be tolása — elfogadhatatlan lett volna, mert
akkor az R1 katalógus **fantom hajókkal** szállna (a DoD sérülne).

**Amit ez a terv a `release-terv`-től eltér:** a `release-terv` 3.3
mondata pontosítást kap: „az AIS-adatvétel már R1-ben fut (statikus
gyűjtés **és a fantom-szűrőhöz szükséges pozíció-buffer**), a
pozíció-írás partícionálással, az aggregáció és az archívum R2". A
`release-terv` 4. fejezete és a 8-as mátrix **változatlanul R2-t mond** —
azok most már nincsenek ellentmondásban a 3.3-cal.

### 8.4 Amit a §8 nem fed le (és a 02-es DDL-terv feladata)

| Elem | Hol rögzül |
|---|---|
| A `position` / `position_archive` / `position_hourly` **partíciós sémája** (havi vs. éves, BRIN, GiST) | 02 – Adatbázis-DDL |
| A `DROP PARTITION` TTL-mechanizmus és a havi partíció-létrehozás | 02 + 07 – CI/CD |
| A `pg_cron` konténerbe építése (a `postgis/postgis:16-3.4` stock image-ben **nincs**) | 07 – CI/CD |
| Az indexek pontos definíciója | 02 – Adatbázis-DDL |
| A DB-szerepkörök és jogosultságok (a README 7.3 hat szerepe) | 02 + 07 |

---

## 9. Kockázatok

| # | Kockázat | Valószínűség | Hatás | Mitigáció |
|---|---|---|---|---|
| K1 | **Az Astro skill-szinten ismeretlen** — a projekt első Astro-ja | közepes | Az első 2 hét lassabb | A `web/` a legkisebb kockázatú komponens (statikus oldalak); az Astro tanulási görbe kisebb, mint a Django/Next átállásé |
| K2 | **A partícionált `position`-upsert és a materializált nézet** hibás teljesítményt ad | közepes | A p95 SLO-k sérülnek | **Megjegyzés:** a swarm review (M-11) helyesen jelezte, hogy az eredeti K2 az „async SQLAlchemy + PostGIS" párosra mutatott, ami **nem** a valós kockázat — a geo-lekérdezések R1-ben minimálisak. A valós kockázat a partícionált írás és a nézet-frissítés. A mitigáció: a `COPY`/bulk-insert R2-ben, a BRIN index a partíciós sémával együtt (02 – DDL), a nézet `REFRESH CONCURRENTLY`-tel (1–2 perces frissítés) |
| K3 | **A saját AIS-dekóder hibás** → rossz ENI-k a katalógusban | magas | A katalógus hitelessége (F-NF-17, F-NF-18) | A dekóder a `pyais`-szal **és** az `aiscat`-tel referencia-implementációként **tesztelve** (nem csak egyik); a valódi rögzítésekkel goldenset; a `r1-adat-terv.md` 7. validációs szabályai a pipeline-ban; az `ingest-terv.md` 9. fejezetének ellenőrzőlistája a mérce |
| K4 | **A 3 hónapos R1-0 csúszik** → a kód készen áll, de nincs adat | biztos | Az R1 nem indítható | A terv ezt explicit kezeli (release-terv 3.4.1). A kódfejlesztés párhuzamos, a katalógus a gyűjtött adatból épül. **A fantom-szűrő és a parser a legkisebb kockázatú elem** — ezek a mérés során csiszolódnak |
| K5 | **A háromnyelvűség alul becsült** | közepes | Az R1 csúszik | A `release-terv` 3.4 már kimondja: „a hajónevek nem igényelnek fordítást", a teher a UI-szövegeken és a jogi szövegeken van. A `content_key`/`content_text` mechanizmus a 300 kulcs × 3 nyelvet kezeli — a fordítási *munkamenet* a kockázat, nem a mechanizmus |
| K6 | **A monorepo a 3 nyelvet egy repóba szorítja** (Python + TS) | alacsony | Eszközlánc-conflict | A `pnpm` és az `uv` függetlenek; a CI két jobban fut (a Python és a TS), a `paths`-szűrés a cache-t nem töri |
| K7 | **A GPL-kompatibilitás az `aiscat` használatával** | alacsony (a saját dekóder mellett) | Jogi | A saját dekóder ezt eleve kizárja; a Q12 nyitott kérdés marad, ha az `aiscat` mellett döntenének |
| K8 | **A telephelyek engedélyezése elakad** (a release-terv 3.6 kockázata) | magas | Az R1-0 csúszik, a hálózat nem épül | Minden site-hoz 2–3 tartalék telephely; a kikötők és vízügyi objektumok a legegyszerűbbek. **A terv 01 nem fedi le** — a `ais-vevo-terv.md` 2. fejezete a mérce |
| K9 | **A német fordítások szakértelmetlenek** (a release-terv 3.6 kockázata) | közepes | Márkanév-érintettség, visszavonás | Német nyelvi reviewer bevonása; a nem átnézett fordítás státusza látszik a belső felületen. **A terv 01 nem fedi le** — a 06 – Szerkesztői felület terv |
| K10 | **A staging nem a NAS-on fut a production mellett** (erőforrás, portütközés) | közepes | A SLO-mérés nem működik | A NAS-on a `hermes` konténer + a PostgreSQL + az OpenHAB fut; egy második PostgreSQL-példány 500 MB–1 GB RAM. A `docker-compose.prod.yml` külön porttartományt kap (5433), és a staging leállítható, ha nincs rá szükség. A részletek: 09 – Üzemeltetés |

---

## 10. Nyitott kérdések

> **A swarm review után bővült (Q8–Q12).** A Q1–Q7 mellett a
> technikai reviewer öt új pontot emelt ki, amelyek nélkül a terv
> nem implementálható egyértelműen.

| # | Kérdés | Opciók | Alapértelmezés (ha nincs válasz) |
|---|---|---|---|
| Q1 | **A nyelvi routing a weboldal URL-je legyen-e, vagy a domain?** (`/hu/…` vs `hu.domain/…`) | (a) path prefix, (b) subdomain, (c) domain | **(a) path prefix** — a funkcióleírás 7. fejezete ezt írja elő (`/hu/duna/hajok`), és az Astro `prefixDefaultLocale: true` ezt adja |
| Q2 | **A `position` írása R1-ben: `COPY` bulk vagy normál upsert?** | (a) COPY + staging tábla, (b) `INSERT ... ON CONFLICT` | **(b)** — és a kérdés **R2-re kerül**, mert a `position` írása R2 (§8.2). R1-ben a `vessel` upsert térfogata minimális |
| Q3 | **Az admin felület R1-ben: Astro oldal vagy külön app?** | (a) Astro route, (b) külön Svelte app, (c) FastAPI/Jinja | **(c) FastAPI/Jinja** — a §4.5 döntés (H-6): a tömeges CSV-import offline pipeline, nem Astro-route |
| Q4 | **Az OpenAPI generálás a build-ből vagy commit-ból?** | (a) CI-ban generált, (b) commitolt | **(b) commitolt**, CI diff-ellenőrzéssel — a kliens offline is tudja használni |
| Q5 | **Az i18n fallback a DB-ben vagy az alkalmazásban?** | (a) DB view, (b) app-logika | **(b) app-logika** — a README 4.3 ezt mutatja |
| Q6 | **A seedadatok (kikötők, zsilip, hajótípusok) forrása és formátuma?** | (a) kézi CSV, (b) GeoJSON, (c) OSM-import, (d) forrásonként eltérő | **(d) forrásonként eltérő** — a preshaz H-5 findingje szerint öt különböző beszerzési folyamatot nem szabad egy „kézi CSV"-be olvasztani. A konkrét táblázat: kikötők a Duna Bizottság port-távolság-táblázatából (CSV, river_km-mal) · zsilipek a `ais-vevo-terv.md` 10. fejezetéből + a zsilip-üzemeltetők adataiból · hajótípusok az UN E-rek. 28 kódrendszerből (kódtábla, nem példányadat) · folyószakaszok a Duna Bizottság km-táblázatából · Balaton-kikötők a KH + Balatoni Hajózási Zrt. tájékoztatóiból (CSV, forrás-URL-lel). Minden seed-fájl a `data_source.code`-ra hivatkozik (F-NF-12) |
| Q7 | **A Pi oldali kód (AIS-catcher indítás, MQTT publisher) ebben a repo-ban van-e?** | (a) igen, `apps/pi/`, (b) külön repo, (c) csak a docs | **(a)** — a `apps/pi/` a §4.2 fában benne van; az `ingest-terv.md` a Pi oldalt is részletesen specifikálja; egy helyen kezelve |
| **Q8** | **Melyik `pyais`/`aiscat` verziót vizsgáltuk, és futtattunk-e Inland FI 10 NMEA-sort rajta?** | (a) csak a docs alapján, (b) futtatva, valós fixture-rel | **(b) kell** — a §5.3 döntés csak így verifikálható; a 04 – AIS-parser specifikáció terv első feladata egy futtatott összehasonlítás (a `pyais` `MessageType8Dac200Fid10` és az `aiscat` `Decoder` ugyanarra a fixture-re) |
| **Q9** | **Az ütemező mechanizmus: APScheduler vagy Celery?** | (a) APScheduler, (b) Celery | **(a) APScheduler** — lezárva a §3.2-ben |
| **Q10** | **A nem-FI-10 hajók `river_km` forrása?** | (a) geometriai illesztés a folyó-korridorra, (b) nincs km, (c) más | **(a)** — a §5.4 szerinti tartalék eljárás, `source_kind = 'derived'` jelöléssel |
| **Q11** | **A `position` írásának R1/R2 helye — a release-terv módosítandó?** | (a) a terv írja át a release-tervet, (b) a release-terv marad és az R1 bővül | **(a)** — a §8.3 blokk: a `release-terv` 3.3 mondata pontosítást kap, a 4. fejezet és a 8-as mátrix változatlanul R2-t mond |
| **Q12** | **A projekt saját licence és a GPL-kompatibilitás hatása az `aiscat` használatára** | (a) MIT/Apache → az `aiscat` kizárva, (b) GPL-kompatibilis → használható | **(a)** — a saját dekóder mellett a licenc nem döntő, de a Q nyitva marad, ha az `aiscat` mellett döntenének |

---

## 11. Elfogadási kritériumok

Ez a terv akkor kész, ha:

1. A stack-döntés indokolt (minden elemre van indoklás, az elutasított
   alternatívák is).
2. A projektstruktúra a teljes R1-et leképezi, és a §8.1 táblázata
   **minden R1-kötelező adatkörre** (a README 3.3 táblajegyzéke alapján)
   sort tartalmaz — és a §8.2 táblázata alapján demonstrálhatóan nem
   tartalmaz R2+ funkciót.
3. A környezetek (local/staging/prod) a `docker compose` one-command
   indítással felállítható, és a `postgres` image **tartalmazza a
   `pg_cron`-t** (custom image, nem a stock PostGIS).
   **Konkrétan:** a `just dev` felállítja a local környezetet a
   `docker compose` egyszeri hívásával; a `just check`
   (lint + typecheck + unit + integration) zöld; a `just db-reset` tiszta
   sémát állít elő seedelt adatokkal. A §6.1 öt szolgáltatása
   **mindegyike** a repóból buildelt vagy a repóban definiált
   konfigurációval indul (a `Dockerfile`-ok, a `mosquitto.conf`/`acl`,
   a `.env.example` a repóban van).
4. A nyitott kérdések (Q1–Q12) megválaszolva vagy alapértelmezéssel
   rögzítve.
5. A swarm review (3 reviewer + verifier) nem talál Critical/High
   blokkolót.
6. A `docs/megvalósulas/` sorozat többi terve (02–09) a 01-re épül,
   és a függőségi sorrend konzisztens.
7. **A `release-terv` 3.3 fejezete és a 8-as release-mátrix
   összhangba kerül a §8.3-mal** (a `position` írása R2), vagy a
   `release-terv` eltérését a §8.3 blokk rögzíti.

---

## 12. A swarm review eredménye és a javítások

A terv 1.0 verzióját **3 reviewer** vizsgálta (a `swarm-review-orchestrator`
protokoll szerint, párhuzamosan, izolált workdir-ben):

| Kör | Reviewer | Fókusz | Findingek | Verdikt |
|---|---|---|---|---|
| 1 | `prof` | technikai mélység | 41 (5C / 15H / 14M / 7L) | „módosítandó, nem újraírandó" |
| 1 | `preshaz` fókusz (a `prof` profil) | üzemeltethetőség + átadhatóság | 32 (4C / 9H / 13M / 6L) | „módosítandó" |
| 1 | `bori` | felhasználói érték + hatókör | 18 (1C / 6H / 8M / 3L) | „módosítandó" |
| **1. kör összesen** | | | **91** | **3/3 „módosítandó"** |
| 2 | `prof` | a technikai javítások ellenőrzése | új blokkolók: **2 Critical + 5 High + 7 Medium + 3 Low** | „módosítandó — a sorozat még nem léphet a 02-re" |
| 2 | `bori` | a felhasználói javítások ellenőrzése | **1 Critical + 6 High** (a 18-ból 4 teljesen, 4 részben, 10 változatlan) | „módosítandó" |

**A 2. kör tanulsága:** az 1. kör javításai **új hibákat** hoztak be (a `position` R2-be tolása ütközött a fantom-szűrő R1-es igényével; a F-ADM-táblázat saját számozást használt; a cikkek DB-be költözése rebuild-mechanizmus nélkül). Ezek mind javítva vannak a v1.3-ban — a részletek lent.

**A 2. kör javított blokkolói:**

| ID | Reviewer | A blokkoló | A javítás |
|---|---|---|---|
| **C-N1** | prof | A §4.5 F-ADM-táblázata **saját számozást** használt, és a **F-ADM-08 (claim)** / **F-ADM-09 (konfliktus)** hiányzott — pedig az F-ADM-08 az R1 kilépési feltétele | §4.5: a táblázat a referencia **eredeti számozását** követi (mind a 9 F-ADM), plusz §4.5.1 (fordítási hiánylista) és §4.5.2 (a tömeges import 6 lépésben) |
| **C-N2** | prof | A cikkek DB-be költözése + `output: 'static'` = **nincs rebuild-mechanizmus** | §3.2.1: a rebuild-hook, a `content_text.status` gating, a build-idő; a „webhooks" (R5) és a belső rebuild-hook (R1) megkülönböztetve |
| **H-N1** | prof | A §5.3 „verifikált összehasonlítás" **hamis** volt: a `pyais` `MessageType8Dac200Fid10` neves mezőket ad (`vin`, `shiptype`, `length`, `beam`, `draught`) | §5.3: a táblázat pontos, a „verifikált" jelző removed, a döntés indoka **átírva** (licenc + kontroll + teljes mezőlefedés, nem a `pyais` hiányossága); a Q8 nyitott marad |
| **H-N2** | prof | A §5.5 3. szabálya újra behúzza a `convoy` sémát R1-be | §8.2: a `convoy` **séma R1-ben**, a felbontás R2-ben; a `voyage`/`voyage_stop`/`voyage_cargo` R2 |
| **H-N3** | prof | A fantom-szűrőből hiányzik a **sebesség-ellenőrzés** és a **kézi kizáró lista** | §5.5: a négy szabály az `ais-vevo-terv.md` 4.2 szerint (polygon + 5 nap ugyanott, SOG 0–12 csomó, kézi MMSI-lista, 90 nap frissesség) |
| **H-N4** | prof | A **Msg 18 és Msg 24 (Class B)** hiányzik az üzenettípus-listából — pedig a Balaton-katalógus R1 | §5.4: a négy oszlopos lista a `ais-vevo-terv.md` 4. diagramját követi (Msg 1/3/5/18/24 + Inland FI 10) |
| **H-N5** | prof | Az ingest-processznek **nincs futtatóegysége** (se a fában, se a compose-ban) | §6.1: az MQTT-fogyasztó az `api` konténeren belül fut (`python -m duna.ingest.worker`) |
| **H-7** | prof | A §1 hiánylista **változatlan**: auth/RBAC és observability nincs | §3.2.2 (hitelesítés + a hat szerep + a mechanizmus) és §3.2.3 (naplózás, mérés, heartbeat, alerting) |
| **M-5** | prof | A `position` PK-ja tévesen csak `ts` | §5.4: PK(`vessel_id`, `ts`) — a dedup-kulcs |
| **M-9** | prof | A `feedback` router hiányzik az `api/v1/` listából | §4.2 fa: `feedback` a routerek között |
| **M-10** | prof | A fejléc relatív linkjei **mind elbuknak** | a fejléc `../../`-s linkeket használ (a `docs/megvalosulas/` alá kerülve) |
| **M-N1** | prof | A §8.1 a `operator`/`operator_i18n`-t kihagyta, és két nem létező táblát sorolt fel | §8.1: az `operator`/`operator_i18n` bekerült; az `event_type` hozzáadva |
| **M-N2** | prof | A `prefixDefaultLocale` magyarázat **fordított** | §3.2: a magyar **is** prefixet kap |
| **M-N4** | prof | A `postgresql-16-cron` alapképlet **nem létezik** | §3.2: a PostGIS image fölé telepített `postgresql-16-cron` apt csomag + `shared_preload_libraries` |

### A Critical blokkolók és a javításuk

| ID | Reviewer | A blokkoló | A javítás |
|---|---|---|---|
| **C-1** | prof | A Pi oldali `rtl_ais` **megszüntette volna a belvízi FI 10 dekódolását** → az egész R1 adatút (ENI, folyó-km, fairway section, cél-UN/LOCODE, ETA, merülés) törött | §5.1–5.2: a Pi-re **AIS-catcher** (`msgformat JSON_FULL`), a szerver a `nmea` mezőt **újradekódolja** |
| **C-2** | prof | A terv kihagyta a referencia által előírt `aiscat`-et, és a `pyais`-indok **téves** volt (a `pyais` ismeri a `MessageType8Dac200Fid10`-et) | §5.3: verifikált háromoszlopos összehasonlítás (`aiscat` / `pyais` / saját) **a GPLv3-licenc-korlattal együtt** |
| **C-3** | prof | Az R1 scope **bővítette az R2-scope-ot**, miközben a terv maga állította, hogy nem | §2.4 + §8.2 + §8.3: a `position` írása R2-be; a `release-terv` 3.3 pontosítást kap |
| **C-4** | prof | A §8 táblázat **nem tartalmazta az R1 adatmodelljének nagy részét** (az i18n-táblák, `vessel_data_origin`, `vessel_identifier`, `basin`/`marina`, `audit_log`, `feedback`, …) | §8.1: a teljes R1-adatkör-lista, a README 3.3 táblajegyzéke alapján |
| **C-5** | prof | A staging a **local seedből** épült → a p95 SLO-k nem mérhetők | §6: a staging az **éles adatmásolat** (README 8. szerint); a SLO-mérés helye rögzítve |
| **C-1** | bori | A fantom-szűrő **katalógusba-lépési feltétellé** vált → kizárta a Balaton-katalógust és a bárkákat | §5.5: területenkénti alkalmazás + **kizáró** szűrő (`excluded` státusz, nem törlés) + a bárkák konvoj-tagként |
| **C-1** | preshaz | A §3.4 becslés-védelem állítása **hamis** volt: a scope-többletnek nincs finanszírozó sprintje | §3.4: a tanulási puffer (~4–5 hét) az R1-0 alatt teljesül; a terv–sprint leképezés táblázat; a 9 terv a 4 sprint **része** |
| **C-2** | preshaz | A terv nem foglalkozik a **tartalmi oldallal** — a becslés fejlesztői FTE, a kilépési feltételek tartalmat kérnek | a tartalmi oldal a 06-os terv és a `release-terv` 3.7 0,5 tartalmi szerepe |
| **C-3** | preshaz | A §4.2 struktúra **nem indítható el**: nincs Dockerfile, `justfile`, `.env.example`, `alembic.ini`, lockfile, lint-konfig, `LICENSE` | §4.2: a fa 78+ bejegyzésre bővült; §11.3 konkrét (`just dev` / `just check` / `just db-reset`) |
| **C-4** | preshaz | Az **R1-0 (a 3–6 hónapos vevőépítés) nincs elhelyezve** a tervben; a Q7 alapértelmezés nem létező helyre mutatott | §7: a 04-es terv (parser) az R1-0-ba tartozik; a 10. terv (Pi-vevő üzemeltetése) opcionális; Q7 javítva |

### A további javítások

| Terület | Finding | Javítás |
|---|---|---|
| §3.2 | `pg_cron` nincs a stock PostGIS image-ben (H-9, prof) | custom image (`infra/docker/postgres/Dockerfile`) |
| §3.2 | `read: "Forward"` nem létező Astro-direktíva (H-11, prof) | `server:defer` Server Island + `@astrojs/node` adapter |
| §3.2 | Az MDX a felhasználói cikkekhez ütközött a DB-modellel (H-10, prof) | a cikkek a DB-ben vannak, az MDX csak a fejlesztői dokre |
| §3.2 | Python 3.12 → **3.14** (a 3.13 security-fázisban van) (M-2, prof) | frissítve |
| §3.2 | Nem létező `docs/_config.yml` hivatkozás (M-1, prof) | törölve; az Astro-konfiguráció rögzítve |
| §3.2 | Celery → APScheduler (Q9) | lezárva |
| §3.2 | Az `astro:i18n` `defaultLocale`/`prefixDefaultLocale` nincs eldöntve (H-14, prof) | rögzítve: `prefixDefaultLocale: true` (F-NF-05) |
| §4.3 | A `db/ddl/` és a `packages/shared` duplikál egy forrást (H-8, prof) | mechanizmus: generált fájl + CI diff-ellenőrzés |
| §4.5 | Az admin Astro route-ja **nem fedte le** az F-ADM-01…07-et (H-6, prof) | FastAPI/Jinja + offline tömeges-import pipeline |
| §5.3 | A `pyais`-indok téves (C-2, prof) | lásd fent |
| §5.5 | A fantom-szűrő R1-ben **nem volt megvalósítható** (H-1, prof) + **túl szigorú volt** (C-1, bori) | háromlépéses, területenkénti, kizáró szűrő |
| §5.6 | Az ingest írási céljai nem voltak felsorolva (H-3, prof) | hat írási cél, R1/R2 bontásban |
| §6 | A staging erőforrás/port/izoláció (H-8, preshaz) | a staging külön porttartomány, leállítható |
| §7 | A függőségi táblázat nem konzisztens (H-6, preshaz) | a release-terv 3.7 sprintjeivel leképezve + a 10. terv |
| §8 | A `position`/`convoy`/Parquet archívum (H-12, H-13, prof) | R2-be halasztva, indoklással |
| §9 | K2 a nem valós kockázatra mutatott (M-11, prof) | átírva; K8–K10 új (telephely-engedély, német fordítás, staging erőforrás) |
| §10 | Q8–Q12 hiányzott (prof) | hozzáadva, alapértelmezésekkel; Q6 pontosítva (H-5, preshaz) |
| §11 | A „demonstrálhatóan nincs R2+ funkció" kritérium hamis volt | a §8.1 teljes lefedéséhez kötve; a „one-command" konkrét (C-3, preshaz) |
| §4.2 | A struktúra-fából hiányzott a futtathatóság (C-3, preshaz) | Dockerfile-ok, `justfile`, `.env.example`, lockfile-ok, lint-konfig, `LICENSE` |

### Ami nyitva maradt (a reviewer-ek szerint)

| # | Pont | Felelős | Állapot |
|---|---|---|---|
| 1 | **A tartalmi oldal** (a háromnyelvű cikkek, a kikötő-leírások, a hajótípus-nevek) — a becslés fejlesztői FTE, a kilépési feltételek tartalmat kérnek | a 06 – Szerkesztői felület terv + a `release-terv` 3.7 0,5 tartalmi szerepe | nyitva |
| 2 | **A kilépési feltételek mechanizmusa** — a `release-terv` 3.5 kilépési feltételeiből hogyan lesz egy futtatható ellenőrző lista | a 08 – Teszt-stratégia terv | nyitva |
| 3 | **A tulajdonosi felelősség kerete** — ki írja a tervet, ki kódol, ki hagyja jóvá | Miklós döntése | nyitva |
| 4 | **Az R1 sprint-szám** (4 vagy 5) — a `release-terv` 3.7 módosítása | Miklós döntése | nyitva |
| 5 | **A `release-terv` 3.3 mondatának pontosítása** (a `position` R1/R2 helye — §8.3) | Miklós döntése (a `release-terv` az övé) | nyitva |
| 6 | **A Q8 futtatott összehasonlítás** — a `pyais` vs. `aiscat` vs. saját dekóder ugyanarra a fixture-re (§5.3) | a 04 – AIS-parser terv első feladata | nyitva |
| 7 | **A projekt saját licence** (Q12) — a GPL-kompatibilitás hatása az `aiscat` használatára | Miklós döntése | nyitva |
| 8 | **A `river_section` kap-e `geometry(LineString)` oszlopot**, vagy a korridor külön adatkör (a README 3.3-ban nincs ilyen oszlop) | a 02 – DDL terv | nyitva |

**A 2. kör összegzése (a `prof` reviewer verdiktje):** az 1. kör
41 findingjából **18 teljesen és 15 részben** zárult le, 8 változatlan; a
javítások **17 új hibát** hoztak be (2 Critical, 5 High, 7 Medium, 3 Low) —
**mind javítva a v1.3-ban**. A `bori` reviewer szerint a 18 saját
findingjéből 4 teljesen, 4 részben zárult le; a maradék 10 a
felhasználói felület rétegeire vonatkozik, és ezek most a §5.8-ban
névvel és felelősséggel rögzítve vannak.

---

*Ez a terv a `docs/megvalósulas/` sorozat első darabja. Következik: 02 –
Adatbázis-DDL v1.1, 03 – API-specifikáció, 04 – AIS-parser.*
