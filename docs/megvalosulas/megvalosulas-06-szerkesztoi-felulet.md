# Implementációs terv – 06: szerkesztői felület

**Verzió:** 0.1 (terv-draft, swarm review előtt)
**Dátum:** 2026-11-19
**Kapcsolódó dokumentumok:**
[`../../README.md`](../../README.md) (adatbázis-terv v1.3) ·
[`megvalosulas-01-stack-es-struktura.md`](megvalosulas-01-stack-es-struktura.md) (stack + struktúra) ·
[`megvalosulas-02-adatbazis-ddl.md`](megvalosulas-02-adatbazis-ddl.md) (a séma) ·
[`megvalosulas-03-api-specifikacio.md`](megvalosulas-03-api-specifikacio.md) (a `/api/admin/v1/` határ) ·
[`megvalosulas-05-frontend-arkitektura.md`](megvalosulas-05-frontend-arkitektura.md) (a frontend alapok) ·
[`../../docs/funkcio-leiras.md`](../../docs/funkcio-leiras.md) (a F-ADM igények) ·
[`README.md`](README.md) (a terv-sorozat tagjai)

**Projekt:** `vessel-tracker` — a hajókövető a Dunán és a Balatonon.

> A dokumentum a repóban a `docs/megvalosulas/06-szerkesztoi-felulet.md`
> útvonalon van — a relatív linkek ehhez képest számolnak.

---

## 1. Mi a szerkesztői felület

**A szerkesztői felület a `web` alkalmazás egyik területe**, nem
külön alkalmazás. Az útvonal-prefix `/szerkeszto/` (a publikus
oldalak `/[lang]/` prefixszel járnak).

| | A publikus oldal | A szerkesztői felület |
|---|---|---|
| Az útvonal | `/[lang]/...` | `/szerkeszto/...` |
| A hitelesítés | nincs | **session cookie** (a `app_user`) |
| A nyelv | a URL prefix | **nem nyelvfüggő** — a szerkesztő a saját `locale` beállítását használja, de **egyszerre két nyelvet lát** (a forrás és a fordítás) |
| A renderelés | SSR | **React-sziget** (a dinamikus űrlapok miatt) |
| A közreműködő | `editor` | az `editor` és az `admin` |

**A `/api/admin/v1/` prefix** (a 03-as terv §3.6) — a `web` proxyzza,
és a proxy ellenőrzi a sessiont.

**Az R1-ben a szerkesztői felület a legfontosabb felhasználói felület**
a publikus oldalak mellett — a katalógus minősége a szerkesztői
munka minőségétől függ.

---

## 2. A hitelesítés (a 03-as terv §3.2.2)

### 2.1 A session

**A session a `app_user` táblában** (a 02-es terv §4.1a):

| Oszlop | A szerepe |
|---|---|
| `session_token_hash` | a cookieban a token **SHA-256**-a (a nyers token soha nem tárolódik) |
| `session_expires_at` | a lejárati idő |
| `role` | `editor` vagy `admin` — a `guard_role_change` trigger védi (a V-N-7 finding) |
| `locale` | a szerkesztő preferált nyelve |

**A belépés:** email + jelszó → az `Argon2id` hash ellenőrzése →
egy **32 bájtos véletlen token** → a token SHA-256-ja a DB-be →
a token a `HttpOnly`, `Secure`, `SameSite=Lax` sütiben.

```python
# apps/api/services/auth_service.py
def create_session(user_id: int) -> str:
    raw = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode()).digest()
    expires = datetime.now(UTC) + timedelta(days=7)
    db.execute(
        "UPDATE app_user SET session_token_hash = :h, "
        "session_expires_at = :e WHERE id = :u",
        {"h": token_hash, "e": expires, "u": user_id},
    )
    return raw
```

**A session ellenőrzése** minden `/api/admin/v1/` kérésnél:

```python
def current_user(request) -> AppUser | None:
    token = request.cookies.get("vt_session")
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode()).digest()
    row = db.fetchone(
        "SELECT id, email, role, locale, unit_system FROM app_user "
        "WHERE session_token_hash = :h AND session_expires_at > now() "
        "AND status = 'active'",
        {"h": token_hash},
    )
    return AppUser(**row) if row else None
```

### 2.1a A DB-szerepkör (a `prof` reviewer C-4 findingje)

**A `02` – DDL-terv §9 szerint** a `session_token_hash` **nem** a
`public_api` GRANT listáján — *„az `app_user` password_hash-e és
session-hash-e … így nem publikus"*.

→ **a `current_user` a `public_api` kapcsolattal NEM futhat.**

**A megoldás: egy szűk `admin_api` szerepkör** — a `02` v1.6
migrációja:

```sql
-- A 0009_admin_role.sql migrációban
CREATE ROLE admin_api LOGIN PASSWORD :'admin_password';

GRANT USAGE ON SCHEMA public TO admin_api;
GRANT SELECT ON app_user TO admin_api;         -- a session azonosítása
GRANT SELECT, UPDATE ON app_user TO admin_api; -- a session írása (a belépés)
```

**A `public_api` változatlan marad** → a hajóadatok továbbra sem
olvashatók közvetlenül a publikus kapcsolatból.

**A `current_user` az `admin_api` kapcsolatot használja** → a
`db.fetchone` a `db.admin` poolon fut:

```python
row = db.admin.fetchone(   # az admin_api szerepkör
    "SELECT id, email, role, locale, unit_system FROM app_user "
    "WHERE session_token_hash = :h AND session_expires_at > now() "
    "AND status = 'active'",
    {"h": token_hash},
)
```

> **A döntés:** a `06` a **szűk `admin_api` szerepkör** mellett dönt
> (a `public_api` kivételes bővítése helyett) → **a `02` v1.6
> migrációja ezt hozza létre**.

### 2.1b Az egy-session korlát (a `prof` reviewer H-3 findingje)

**A `02` v1.5 sémája egyetlen `session_token_hash` oszlopot tartalmaz**
→ **egy felhasználónak egyszerre csak egy sessione van** →
**a második belépés az elsőt kiléptezi**.

**Ez R1-ben elfogadható**, de **a szerkesztő ezt ne lássa meglepetésként**:

| A helyzet | A viselkedés |
|---|---|
| a szerkesztő a számítógépen dolgozik, majd **a telefonján** is bejelentkezik | **a számítógép sessionje kilép** |
| **egy másik szerkesztő** bejelentkezik | **érintetlen** (a `session` a felhasználónként van) |

**A több eszközös munka** a `session_token_hash` → **többsoros
`app_user_session` tábla** átalakítást igényelne (a `02` v1.7) →
**R1-ben nem** → **de a `06` §4.1 (a belépés) figyelmeztet**, ha a
session az elején már volt:

```
Már voltál bejelentve egy másik eszközön. Az új bejelentés
kiléptezi azt a sessiont. Folytatod?  [Igen] [Nem]
```

> **A `prof` reviewer H-11 findingje:** a `06` §8 (a nyitott
> kérdések) **ne tartalmazza** a DB-szerepkör-problémát → **a
> §2.1a lezárja** → **a nyitott kérdések listája a §2.1a-ra hivatkozik**.

### 2.2 A szerepek

| Szerep | A `role` | Amit tehet |
|---|---|---|
| **Szerkesztő** | `editor` | a hajóadatok, a fordítások, a referenciatáblák szerkesztése; a visszajelzések feldolgozása; az import |
| **Admin** | `admin` | minden, **plusz**: a felhasználók kezelése, a szerepváltás, az import jóváhagyása |

**A szerepváltás** a `guard_role_change` triggerrel védett (a
szerkesztő nem emelheti magát adminná).

**A `SET LOCAL app.user_role`** a tranzakció elején — a
`guard_role_change` trigger ezt olvassa.

**A `SET LOCAL app.user_id`** — az **audit** trigger ezt olvassa
(a `audit_log.actor_id`).

```python
@contextmanager
def as_user(user: AppUser):
    with db.transaction():
        db.execute("SET LOCAL app.user_id = :u", {"u": user.id})
        db.execute("SET LOCAL app.user_role = :r", {"r": user.role})
        yield
```

### 2.3 Az audit (a F-ADM-03)

**Minden kézzel módosított adat** az `audit_log`-ba kerül — a
`audit_row_change` triggerrel (a 02-es terv §8.2), **automatikusan**.

**A trigger** a `before`/`after` JSON-t rögzíti, az `actor_id`-t a
sessionből. **A szerkesztői felületnek nem kell külön auditot írnia** —
csak **a sessiont kell beállítania**.

**Amit a felület mutat** (a „ki, mikor, honnan"):

| A `before`/`after` különbsége | A megjelenítés |
|---|---|
| egy mező értéke változott | „Hossz: 110,0 m → 112,5 m" |
| új rekord | „Létrehozva" |
| törölt rekord | „Törölve" (a `before` tartalma) |

**Az `origin` mező** — a szerkesztői módosítás `origin='editorial'`
(F-DET-15).

---

## 3. A szerkesztői végpontok (a `/api/admin/v1/`)

### 3.1 A hajók

| Method | Path | Leírás |
|---|---|---|
| GET | `/api/admin/v1/vessels` | a hajók listája (a szűrők + a lapozás) |
| GET | `/api/admin/v1/vessels/{id}` | egy hajó **szerkesztési** nézete (minden mező, minden nyelven, az eredettel) |
| PATCH | `/api/admin/v1/vessels/{id}` | a hajó mezőinek módosítása |
| PATCH | `/api/admin/v1/vessels/{id}/i18n` | a fordítható mezők módosítása (nyelvenként) |
| POST | `/api/admin/v1/vessels/{id}/certificates` | egy engedély hozzáadása |
| DELETE | `/api/admin/v1/vessels/{id}/certificates/{cert_id}` | egy engedély törlése |
| GET | `/api/admin/v1/vessels/{id}/origins` | a mezőnkénti eredet + a konfliktusok |
| POST | `/api/admin/v1/vessels/{id}/origins` | egy új eredet rögzítése (kézi adat) |

**A `PATCH` részleges módosítás** (a JSON Merge Patch szemantika) —
csak a megadott mezők változnak.

**A `PATCH` a `vessel_data_origin`-t is írja** — a `origin='editorial'`
sor az új értékkel, az `is_current=true`.

### 3.2 A fordítások

| Method | Path | Leírás |
|---|---|---|
| GET | `/api/admin/v1/translations` | a **fordítási hiánylista** (a F-ADM-05) |
| GET | `/api/admin/v1/translations/{key}` | egy kulcs minden nyelven |
| PATCH | `/api/admin/v1/translations/{key}/{lang}` | egy fordítás módosítása (a `status` váltással) |
| POST | `/api/admin/v1/translations/{key}/{lang}/review` | a fordítás jóváhagyása (`status='published'`) |

**A hiánylista lekérdezése** — a `content_key` × `language` mátrix
hiányzó cellái:

```sql
SELECT ck.key, ck.domain,
       array_agg(l.code ORDER BY l.code) FILTER (WHERE ct.content_key IS NULL)
           AS missing_langs
FROM content_key ck
CROSS JOIN language l
LEFT JOIN content_text ct
       ON ct.content_key = ck.key AND ct.lang = l.code
WHERE ct.content_key IS NULL OR ct.status <> 'published'
GROUP BY ck.key, ck.domain;
```

**A `status`** a publikálási munkafolyamat: `draft` → `review` →
`published`.

### 3.3 A visszajelzések (a F-ADM-04)

| Method | Path | Leírás |
|---|---|---|
| GET | `/api/admin/v1/feedback` | a visszajelzések listája (a `status` szűrővel) |
| GET | `/api/admin/v1/feedback/{id}` | egy visszajelzés (a kapcsolódó hajóval) |
| PATCH | `/api/admin/v1/feedback/{id}` | a státusz váltása (`accepted`/`rejected`) + a kezelő |

**A `handled_by` és a `handled_at`** a `PATCH`-ben töltődik ki — a
`feedback.status` CHECK-je megköveteli (a P1-16 finding).

**A visszajelzésből egy hajóadat-módosítás** — a „kérek egy
korrekciót" link a hajóoldalon → a visszajelzés **egy konkrét hajóra**
mutat. **A `feedback` sémában nincs `vessel_id` oszlop!** — a 03-as
terv Q-je, ez a terv megoldja:

**A megoldás:** a `feedback.body` szabad szöveg, de a **hajó azonosítója
a `body` elején**, egy kulcs-érték formában:

```
vessel: 12345678 (ENI)
A hajó neve "TESZTHAJO" helyett "TESZTHÁJÓ" legyen.
```

**A `POST /api/v1/feedback` a `vessel_id`-t nem tudja** — a publikus
API nem ad hozzáférést a belső azonosítókhoz (a F-NF-11).

**A javasolt séma-módosítás** a 02-es tervhez:

```sql
ALTER TABLE feedback ADD COLUMN vessel_id bigint
    REFERENCES vessel(id) ON DELETE SET NULL;
ALTER TABLE feedback ADD COLUMN subject text
    CHECK (subject IN ('data_correction','translation','map','source',
                       'feature','other'));
```

**A `subject` a kategóriát,** a `vessel_id` a **hivatkozott hajót**
tartja. A publikus API a `vessel_id`-t a `slug` alapján kitölti
(a kliens a hajóoldalon kattint).

### 3.4 Az üzemeltetői önbevallás (a F-ADM-08)

| Method | Path | Leírás |
|---|---|---|
| GET | `/api/admin/v1/claims` | a beérkezett kérelmek listája |
| GET | `/api/admin/v1/claims/{id}` | egy kérelem (az AIS-rekorddal együtt) |
| POST | `/api/admin/v1/claims/{id}/approve` | a jóváhagyás (a `vessel_data_origin` írása) |
| POST | `/api/admin/v1/claims/{id}/reject` | az elutasítás (indoklással) |

**A kérelem** a `feedback` táblában van (`category='data_correction'`,
`status='new'`) — **külön `claims` tábla nincs** a 02-es sémában.

**A jóváhagyás mechanizmusa:**

```python
def approve_claim(claim_id: int, user: AppUser, values: dict) -> None:
    """A kérelm elfogadása: a `vessel_data_origin` új sora
    `origin='operator_claimed'` értékkel, a `vessel` oszlopok
    frissítésével."""
    claim = db.fetchone("SELECT * FROM feedback WHERE id = :i", {"i": claim_id})
    vessel_id = claim["vessel_id"]
    for field_name, value in values.items():
        # a kanonikus értek a vessel-en
        db.execute(
            f"UPDATE vessel SET {field_name} = :v WHERE id = :id",
            {"v": value, "id": vessel_id},
        )
        # az eredet nyilvántartása (a konfliktus megőrzésével)
        db.execute(
            "INSERT INTO vessel_data_origin "
            "(vessel_id, field_name, origin, value_snapshot, source_id, "
            " observed_at, confidence, is_current) "
            "VALUES (:vid, :f, 'operator_claimed', :v, :src, now(), 0.8, true) "
            "ON CONFLICT (vessel_id, field_name, origin) "
            "WHERE is_current DO UPDATE SET value_snapshot = :v, "
            "observed_at = now(), confidence = 0.8",
            {"vid": vessel_id, "f": field_name, "v": str(value),
             "src": claim.get("source_id")},
        )
```

**A `ON CONFLICT` a partial unique indexre mutat** (a 02-es terv
§5.3: `vessel_data_origin_active_uniq`) — ez a `WHERE is_current`
predikátummal definiált index, és a Postgres támogatja az ilyen
`ON CONFLICT ... WHERE` klauzulát.

**A konfliktus megmarad**: az AIS `origin='ais'` sora **érintetlen**,
az üzemeltetői állítás `origin='operator_claimed'` új sor. A
`vessel_data_origin_conflicts` nézet mindkettőt mutatja (a
F-ADM-09).

### 3.5 A konfliktuskezelés (a F-ADM-09)

| Method | Path | Leírás |
|---|---|---|
| GET | `/api/admin/v1/conflicts` | az összes konfliktus (a mezőnkénti eredet alapján) |
| POST | `/api/admin/v1/conflicts/{vessel_id}/{field}` | a **szerkesztő döntése** |

**A döntés három lehetősége:**

| A döntés | A hatás |
|---|---|
| **Az AIS értéke az igaz** | az `operator_claimed` sor `is_current=false` |
| **Az üzemeltetői állítás az igaz** | a `vessel` oszlop az üzemeltetői érték; az AIS sor is `is_current=false` (de a `value_snapshot` megmarad) |
| **Mindkettő igaz** (eltérő, de egyaránt érvényes) | mindkettő `is_current=true`; a UI **mindkettőt mutatja** |

**A `value_snapshot` megmarad** — a történet nem vész el (a 02-es
terv §5.3).

### 3.6 A tömeges import (a F-ADM-07)

| Method | Path | Leírás |
|---|---|---|
| POST | `/api/admin/v1/imports` | egy CSV feltöltése (a validáció előnézete) |
| GET | `/api/admin/v1/imports/{id}` | az import állapota (a hibák sorával) |
| POST | `/api/admin/v1/imports/{id}/commit` | az import véglegesítése |
| DELETE | `/api/admin/v1/imports/{id}` | az import eldobása (a validáció előnézete) |

**Az import két lépéses** — a **validálás** (a hibák listája, a
félbehagyás nélkül) és a **commit** (a tényleges írás).

**A CSV formátum (a minimum):**

```csv
eni,name,hajotipus_code,operator_legal_name,length_m,beam_m,draught_max_m
12345678,TESZTHAJO,INLAND_CARGO,Example Kft,110.0,11.5,6.2
```

**A validáció során:**
- az ENI **duplikált** a DB-ben → hiba
- az ENI **hiányzik** → hiba (a hajószám önmagában nem elég az
  azonosításhoz — a Duna-katalógusban az ENI kötelező)
- a `hajotipus_code` **nem létezik** a `vessel_type`-ban → hiba
- a `length_m` **nem szám** vagy negatív → hiba
- a `vessel` **már létezik** az ENI-vel → **frissítés** (nem hiba)

**Az import a `vessel_service_period`/`vessel_ownership` érintése nélkül**
— az import a statikus adatokat tölti be, a történetet nem módosítja.

**A CSV feldolgozása a `job_run` táblába ír** (a `job_name =
'import-csv'`) — a hosszú importok nyomon követhetők.

**A 10 000 soros limit** — a memória és a futásidő korlátja. Felette
a felhasználó fel kell bontja a fájlt.

---

## 4. A felület képernyői

### 4.1 A képernyők

| Képernyő | Útvonal | A F-ADM |
|---|---|---|
| **A hajólista** | `/szerkeszto/hajok` | F-ADM-01 |
| **A hajó szerkesztése** | `/szerkeszto/hajok/{id}` | F-ADM-01, F-ADM-02, F-ADM-03 |
| **A konfliktusok** | `/szerkeszto/konfliktusok` | F-ADM-09 |
| **A kérelmek** | `/szerkeszto/keresek` | F-ADM-08 |
| **A visszajelzések** | `/szerkeszto/visszajelzesek` | F-ADM-04 |
| **A fordítások** | `/szerkeszto/forditasok` | F-ADM-05 |
| Képernyő | Útvonal | A F-ADM |
|---|---|---|
| **A hajólista** | `/szerkeszto/hajok` | F-ADM-01 |
| **A hajó szerkesztése** | `/szerkeszto/hajok/{id}` | F-ADM-01, F-ADM-02, F-ADM-03 |
| **A konfliktusok** | `/szerkeszto/konfliktusok` | F-ADM-09 |
| **A kérelmek** | `/szerkeszto/keresek` | F-ADM-08 |
| **A visszajelzések** | `/szerkeszto/visszajelzesek` | F-ADM-04 |
| **A fordítások** | `/szerkeszto/forditasok` | F-ADM-05 |
| **Az import** | `/szerkeszto/import` | F-ADM-07 |
| **Az AIS-import** | `/szerkeszto/import/ais` | F-ADM-07 |
| **A fordítási hiánylista** | `/szerkeszto/forditasok/hianyok` | F-NF-16 |
| **Az előnézet** | `/szerkeszto/elonezet/hajok/{id}` | F-ADM-06 |

**Az AIS-import (a `bori` reviewer B-C-4 findingje)** — **a szerkesztő
nem üres lappal indul**:

**A mérési adat** (a `bud01` vevő) SQLite-ban van
(`ais_message`, `ais_position`, `ais_static`, `ais_state`) → **a
szerkesztő közvetlenül olvassa**:

```
/szerkeszto/import/ais
  Forrás:  db/fixtures/ais/manifest.json   (vagy a Pi ais.db)
  Talált hajók: 78  (a MMSI-k alapján)
  Névvel azonosított: 76
  ENI-vel azonosított: 1
  Importálható: 78        [Importálás]
```

**A leképezés** (a `02` – DDL-terv §5.3 alapján):

| Az AIS-adat | A `vessel` / `vessel_i18n` / `vessel_identifier` |
|---|---|
| a `mmsi` | a `vessel_identifier` (`identifier_type='mmsi'`) |
| a `callsign` (a `ais_static`-ból) | a `vessel_identifier` (`identifier_type='callsign'`) |
| a `name` (a `ais_static`-ból) | a `vessel_i18n.name` (`lang='en'`, a hivatalos latin név) |
| a `ship_type` (a `ais_static`-ból) | a `vessel_type` (az UNECE-kód → a `vessel_type` seed) |
| a `length`/`width`/`draught` | a `vessel.length_m` / `width_m` / `draught_max_m` (`origin='ais'`) |
| a `imo` | a `vessel_identifier` (`identifier_type='imo'`) |
| a `destination` (a `ais_static`-ból) | a `vessel.destination` |
| a `eta` (a `ais_static`-ból) | a `vessel.eta` |

**Az `origin` mindig `'ais'`** → a F-ADM-03 szerint a forrás **rögzített**,
a `vessel_data_origin` pedig az AIS-szal → **a konfliktus a kézzel
módosításkor keletkezik** (lásd a B-H-4 blokk).

**A fordítási hiánylista (a `prof` reviewer M-5 findingje)** — a
`/szerkeszto/forditasok/hianyok` képernyő **a `content_key` × a
hiányzó `lang` szerint** listázza a `published` státuszú, de **lefordítatlan**
szövegeket → **ez méri a F-NF-16-ot (a 100% átnézett fordítás)**.

**A konfliktusok képernyő — a valós forrás (a `bori` reviewer B-H-4
findingje):**

> **R1-ben a képernyő üres** — a hajóadatok **egyetlen forrásból**
> (az AIS-ből) jönnek → **nincs konfliktus**.
>
> **A konfliktus akkor keletkezik, amikor a szerkesztő kézzel
> felülírja az AIS-adatot** → a `vessel_data_origin.value_snapshot`
> az AIS értékét tartja meg, az `is_current` az új, szerkesztett értéket
> jelöli → **a konfliktus képernyő az ilyen eltéréseket mutatja**
> (a `02` – DDL-terv §6.3 `vessel_data_origin_conflicts` nézete).
>
> **Ez a F-ADM-09 valós értelmezése** — nem a két forrás közötti
> eredeti ellentérés, hanem **a szerkesztői felülírás**.

| **Az előnézet** | `/szerkeszto/elonezet/hajok/{id}` | F-ADM-06 |

### 4.2 A hajó szerkesztő képernyője

**A képernyő három hasábra oszlik:**

```
┌─────────────────────────────────────────────────────────────────┐
│ ← Vissza  TESZTHAJO (ENI 12345678)     [Előnézet] [Mentés]     │
├──────────────────┬────────────────────────┬─────────────────────┤
│ A MEZŐK          │ A FORDÍTÁSOK           │ AZ EREDET           │
│                  │                        │                     │
│ Típus  [INLAND…]│ 🇭🇺 Név    [TESZTHAJO ] │ Hossz               │
│ Hossz  [110,0 ] │ 🇩🇪 Name    [TESTFRACH…] │  AIS · 11-15        │
│ Szélesség [11,5]│ 🇬🇧 Name    [TEST CARG…] │  Üzemeltető · 11-02 │
│ Merülés  [6,2 ] │                        │  ⚠ ellentérés        │
│ Üzemeltető [Kft]│ Leírás                  │                     │
│ Célállomás [—]  │ [szövegszerkesztő]     │ Bizonyosság:         │
│                  │                        │  AIS-azonosított    │
└──────────────────┴────────────────────────┴─────────────────────┘
```


**A „Célállomás" mező (a `bori` reviewer B-C-3 findingje)** — a
`vessel.destination` oszlopba ír:

| A mező | A forrás | A megjegyzés |
|---|---|---|
| **a célállomás** | a `vessel.destination` | a mérésben **100%-ban üres** (a `04` – parser-terv szerint a FI 10-ből jönne) → **a szerkesztő kézzel adja meg** |

> **Miért kell:** a fuvarozók legfontosabb kérdése a célállomás
> (a funkcióleírás US-04-je: *„a folyamatban lévő útját és várható
> érkezését akarom látni"*). **Ha nincs a mező, a felhasználó soha nem
> látja.**
>
> **A `03` – API-terv `VesselDetail`-je** a `destination` mezőt
> tartalmazza → **a `05` – frontend-terv §8.1 blokk-listájában a
> „Üzemeltető blokk" mellett új blokk: „Utazási adatok"** (a
> célállomás, az indulási idő, az `eta` — ha van).

**A „Mentés" gomb** a `PATCH`-et küldi — **csak a módosított mezőkkel**
(a diff alapján).

**A „Mentés" a módosítás előtt megmutatja, mi fog változni** — egy
megerősítő dialógus:

```
Módosítások (2):
  Hossz: 110,0 m → 112,5 m
  Üzemeltető: Example Kft → Example Shipping Zrt.
  Forrás: editorial (a szerkesztő)
```

**Ez a F-ADM-03 követelménye** („*forrás- és bizonyítékmező minden
kézzel módosított adathoz*") — a felület a bizonyítékot **a
módosításkor** rögzíti, nem utólag.

### 4.3 Az előnézet (a F-ADM-06)

**Az előnézet a valódi hajóoldalt mutatja** — mindhárom nyelven.

**A megoldás: az `?preview=1` query paraméter** a publikus oldalon:

```
/hu/hajos/test-hajo?preview=1&token=<egyszeri token>
```

**A token** a szerkesztő sessionjéből származó **egyszeri, rövid
életű** érték (a `preview_token` a `job_run`-nál? — nem: egy külön
tábla kellene). **A legegyszerűbb: a session cookie maga** — a
`web` a `?preview=1`-lel a szerkesztői sessionnel rendelkező látogató
nek mutatja az **el nem mentett** változásokat.

**Az el nem mentett változások átadása:** a `web` a szerkesztői
képernyő state-jét a sessionben tárolja (egy `preview_state` a
`job_run`-ban? — a `app_user` táblához egy `jsonb` oszlop kellene).

**A javasolt megoldás:** a `preview_state` **a `web` szerver
memóriájában** (a session cookie azonosítójához kötve) — a 2 GB-os
VPS-en ez néhány MB, és a state **nincs perzisztens** (ez rendben
van: az előnézet átmeneti).

**Az előnézet a mentett állapotot mutatja** (a DB-ből), **plusz** az
el nem mentett mezőket (a memóriából) — a kettő összevonva.

### 4.4 A fordítási hiánylista (a F-ADM-05)

**A hiánylista nézete:**

| Kulcs | Domain | hu | de | en | Állapot |
|---|---|---|---|---|---|
| `vessel.type.dry_cargo` | vessel | ✅ | ✅ | ❌ | 1 hiányzik |
| `map.legend.locks` | ui | ✅ | ❌ | ✅ | 1 hiányzik |
| `notice.water_level.restriction` | content | ✅ | ✅ | ✅ | **elavult** (a hu 2026-06-01 óta) |

**Az „elavult" jelölés:** a `content_text.updated_at` a
`content_key.source_lang` fordításához képest — ha a forrásnyelv
újabb, a fordítás **elavult**.

**A szűrés:** a hiányzó / az elavult / a `status='draft'` /
a `status='review'` — mindegyikre külön fül.

---

## 5. A kliensoldali architektúra

### 5.1 A React-sziget

**A szerkesztői felület **egyetlen nagy React-sziget** — a formok
állapota, a diff, az előnézet.

```
/szerkeszto/hajok/[id].astro
  └── <VesselEditor client:load vesselId={id} />
        ├── <FieldPanel />         ← a mezők (a diff kiemeléssel)
        ├── <TranslationPanel />   ← a fordítások
        ├── <OriginPanel />        ← az eredet + a konfliktusok
        └── <SaveBar />            ← a mentés + a megerősítés
```

**A `client:load`** — a szerkesztői felületnek **azonnal** működnie
kell (a `client:idle` itt túl lassú lenne).

### 5.2 Az állapotkezelés

**Nincs külső state-könyvtár** (a Redux/Zustand overkill) — a React
beépített `useState`/`useReducer` + egy `useReducer` a formhoz.

```tsx
type EditorState = {
  // az eredeti értekek (a diff alapja)
  original: VesselEditorData;
  // a módosítások (a mezőnkénti)
  changes: Record<string, { value: unknown; lang?: string }>;
  // az el nem mentett fordítások
  translations: Record<string, Partial<Record<Lang, string>>>;
};
```

**A diff** a `changes` kulcsokból — nincs külön diff-könyvtár.

### 5.3 A mentés

```tsx
async function save() {
  // a diff -> a PATCH payload
  const patch = buildPatch(state.changes);
  const res = await fetch(`/api/admin/v1/vessels/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  });
  if (!res.ok) { showError(res); return; }
  // a friss adat vissza a state-be
  setState({ original: await res.json(), changes: {} });
}
```

**A `buildPatch`** a `changes` kulcsokat csoportosítja:
- a nem nyelvfüggő mezők → `/vessels/{id}`
- a nyelvfüggő mezők → `/vessels/{id}/i18n` (a `lang` szerint)

---

## 6. A hibakezelés és a jogosultság

| A hiba | A felület válasza |
|---|---|
| A session lejárt (401) | átirányítás a `/szerkeszto/bejelentkezes`-re |
| Nincs jogosultság (403) | „Nincs jogosultságod ehhez a művelethez" — a gomb letiltva |
| A `validation-error` (422) | a mező alatt, a hiba szövegével |
| Az `optimistic locking` konfliktus (409) | „Valaki közben módosította ezt a hajót" + az új adatok betöltése + a diff újra |
| A hálózati hiba | a mentés gomb újrapróbálható, a változások megmaradnak |

**Az optimista zárolás:** a `PATCH` a `updated_at`-et is elküldi —
ha a DB-ben más, `409`-et kap. A `vessel.updated_at` a 02-es terv
triggerével karbantartott.

---

## 7. A teljesítmény

| Művelet | Cél |
|---|---|
| A hajólista betöltése (100 hajó) | < 800 ms |
| Egy hajó betöltése (minden nyelvvel, az eredettel) | < 500 ms |
| A mentés | < 800 ms |
| Az import validálása (1000 sor) | < 10 s |
| Az import commitja (1000 sor) | < 30 s |

**Az import** a leglassabb — **a batch beszúrás** kötelező (a
soronkénti `INSERT` 1000 sorra > 10 másodperc). A `psycopg` +
`executemany` vagy a `COPY` a megoldás.

**A tömeges import limitje (a `bori` reviewer B-H-3 és a `prof`
reviewer M-10 findingje):**

| A limit | Az érték | Miért |
|---|---|---|
| **a sorok száma** | **50 000 sor** | a mérési adat 30 napja ~3 500 hajó → a teljes mérés importálható |
| **a fájlméret** | **20 MB** | a 2 GB-os VPS (a `09` – üzemeltetés-terv §8.1) |
| **a feldolgozás** | **a szerveroldalon, batchenként** (2 000 sor/batch) | **nem** a böngésző memóriájában |

**A böngésző csak a fájlt küldi el** (`multipart/form-data`) → **a
validáció és a beszúrás a szerveren történik** → **a `09` §8.3
szerint a `statement_timeout` (5 s) **batchre** vonatkozik, nem a
teljes importra.

**Az AIS-import (a `04` – parser-terv §9 alapján)** a `COPY`-t használja
→ **egy külön út**, a JSON-formátum limitje nem érvényes rá.

---

## 8. A nyitott kérdések

| # | Kérdés | Alapértelmezés | Állapot |
|---|---|---|---|
| Q1 | A `feedback` kapjon `vessel_id` oszlopot? | **igen** — a F-DET-11 a konkrét hajó hibájára vonatkozik; a módosítás a 02-es tervhez | **a 02-es tervben javítandó** |
| Q2 | A `feedback` kapjon `subject` oszlopot (a `category` helyett)? | **igen** — a `category` a visszajelzés *típusa* (a F-ADM-08 a claim), a `subject` a *tárgya* | nyitva |
| Q3 | Az előnézet hogyan adja át az el nem mentett változásokat? | **a `web` memóriájában**, a sessionhöz kötve (nem perzisztens) | **lezárva** |
| Q4 | A tömeges import a `vessel_alias`-t is kezelje? | **nem** — az import a statikus adatokat tölti be | nyitva |
| Q5 | A kérelmek (`claims`) külön táblát kapjanak? | **nem** — a `feedback` táblában van (`category='data_correction'`) | nyitva |
| Q6 | A szerkesztői felület a saját nyelvén működjön, vagy mindhármon egyszerre? | **mindhármon egyszerre** (a forrás + a fordítás) | **lezárva** |
| Q7 | A CSV import a `position`/`vessel_identifier` adatait is kezelje? | **nem** — az import a statikus vessel-adatokra vonatkozik | nyitva |
| Q8 | **Milyen DB-szerepkörrel olvassa a `session`-t?** | **a szűk `admin_api` szerepkör** (a `02` – DDL-terv v1.6) — a `public_api` nem olvashatja az `app_user`-t | **lezárva** (a `prof` reviewer C-4 findingje — a §2.1a) |
| Q9 | **A több eszközös munkát hogyan?** | **R1-ben egy session** (a `02` v1.5 sémája egy `session_token_hash` oszlop) → a második belépés kiléptezi az elsőt | **lezárva** (a `prof` reviewer H-3 findingje — a §2.1b; a több eszközös munka a `session_token_hash` → `app_user_session` átalakítás, **R2**) |
| Q10 | **A célállomás mező a szerkesztőben?** | **igen** — a `vessel.destination` (a mérésben 100%-ban üres) | **lezárva** (a `bori` reviewer B-C-3 findingje — a §4.2) |

**A sorozat állapota** — a terv-sorozat táblázata a
[`README.md`](README.md)-ben (a `docs/megvalosulas/README.md`) → **a
státusz egy helyen legyen** (a `prof` reviewer L-3 findingje).

---

*Ez a terv a `docs/megvalósulas/` sorozat hatodik darabja. Következik: 07 –
CI/CD és környezetek.*
