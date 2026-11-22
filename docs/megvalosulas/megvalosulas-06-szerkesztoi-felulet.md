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

> A dokumentum a repóban a `docs/megvalosulas/megvalosulas-06-szerkesztoi-felulet.md`
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
| **Az import** | `/szerkeszto/import` | F-ADM-07 |
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
│ …               │ [szövegszerkesztő]     │ Bizonyosság:         │
│                  │                        │  AIS-azonosított    │
└──────────────────┴────────────────────────┴─────────────────────┘
```

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

---

*Ez a terv a `docs/megvalósulas/` sorozat hatodik darabja. Következik: 07 –
CI/CD és környezetek.*
