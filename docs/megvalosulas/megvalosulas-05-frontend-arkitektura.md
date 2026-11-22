# Implementációs terv – 05: frontend-arkitektúra

**Verzió:** 0.1 (terv-draft, swarm review előtt)
**Dátum:** 2026-11-19
**Kapcsolódó dokumentumok:**
[`../../README.md`](../../README.md) (adatbázis-terv v1.3) ·
[`megvalosulas-01-stack-es-struktura.md`](megvalosulas-01-stack-es-struktura.md) (stack + struktúra) ·
[`megvalosulas-02-adatbazis-ddl.md`](megvalosulas-02-adatbazis-ddl.md) (a séma) ·
[`megvalosulas-03-api-specifikacio.md`](megvalosulas-03-api-specifikacio.md) (az API, amit ez hív) ·
[`../../docs/funkcio-leiras.md`](../../docs/funkcio-leiras.md) ·
[`../../docs/release-terv.md`](../../docs/release-terv.md) ·
[`README.md`](README.md) (a terv-sorozat tagjai)

**Projekt:** `vessel-tracker` — a hajókövető a Dunán és a Balatonon.

> A dokumentum a repóban a `docs/megvalosulas/05-frontend-arkitektura.md`
> útvonalon van — a relatív linkek ehhez képest számolnak.

---

## 1. Az alapelv: a SEO megköveteli a szerveroldali renderelést

**Az R1 termék lényege a kereshetőség** (a F-NF-04: „*Indexelhető
hajóoldalak minden nyelven — 100%*"), és ez **nem** megvalósítható
tiszta kliensoldali rendereléssel (a Google a JS-t renderszeli, de
a kezdeti HTML üres).

**Ezért: Astro SSR** — a `output: 'server'`, a `web` konténer a Node
adapterrel fut, és **minden nyilvános oldal szerveroldalon jön**.

| Renderelés | Hol | Mikor |
|---|---|---|
| **Szerveroldali (SSR)** | a nyilvános oldalak **mind** | R1-ben **nincs** kliensoldali renderelés |
| **Kliensoldali sziget** | a React-szigetek (a szűrő, a lapinyítás) | ahol a JavaScript valóban kell |
| **Statikus** | a `docs/`, a fejlécek | a build során |

**Amit ez kizár:**
- a `output: 'static'` (a 02-es terv §3.2.1-ben említett **rebuild-mechanizmus**
  a DB-ben lévő cikkek miatt kellett — a cikkek a DB-ben vannak, és a
  `status='published'` a publish gating; **nem** lehet minden
  szerkesztés után statikusan újraépíteni az egész oldalt, mert a
  hajóoldalak **folyamatosan változó** adatot mutatnak).

**Amit ez megenged:**
- a `docs/megvalosulas/` és a `README.md` **statikus** maradhat — a
  `docs/` a GitHub Pages-en (a `docs/_config.yml` a Jekyll configja —
  a projekt dokumentációja a GitHubon olvasható, nem a weboldalon).

---

## 2. A könyvtárstruktúra

```
apps/web/
├── astro.config.mjs         ← az i18n, az adapter, a middleware
├── src/
│   ├── middleware.ts         ← a nyelv kiválasztása, a canonical URL
│   ├── pages/
│   │   ├── [lang]/
│   │   │   ├── index.astro               ← a kezdőlap
│   │   │   ├── hajos/
│   │   │   │   ├── [slug].astro          ← a hajóadatlap (F-DET-01…16)
│   │   │   │   └── index.astro           ← a katalóguslista (F-CAT-02…14)
│   │   │   ├── kikotok/
│   │   │   │   ├── index.astro           ← a kikötők listája
│   │   │   │   └── [code].astro          ← a kikötőoldal
│   │   │   ├── zsilipek/index.astro      ← a zsilipek
│   │   │   ├── szakaszok/[code].astro    ← a folyószakaszok
│   │   │   ├── tankonyvak/[slug].astro   ← a blog (a DB-ből)
│   │   │   ├── hirek/[slug].astro        ← a hír (a notice)
│   │   │   ├── esemenyek/index.astro     ← az események
│   │   │   ├── vizallaszint/[code].astro ← a mérőállomás
│   │   │   ├── kereses/index.astro       ← a kereső eredménye
│   │   │   ├── informacio/[...slug].astro ← a statikus tartalom
│   │   │   └── 404.astro
│   │   └── api/                          ← a proxy a belső API-hoz
│   │       └── [...path].ts
│   ├── components/
│   │   ├── ui/                           ← a design system (Astro)
│   │   │   ├── Button.astro, Card.astro, Badge.astro, …
│   │   ├── catalog/                      ← a katalógus
│   │   │   ├── VesselList.astro, VesselFilters.tsx, VesselCard.astro
│   │   ├── vessel/                       ← a hajóadatlap
│   │   │   ├── VesselHeader.astro, VesselSpecs.astro,
│   │   │   ├── VesselOriginList.astro, VesselHistory.astro
│   │   ├── content/                      ← a tartalom
│   │   └── islands/                      ← a React-szigetek
│   │       ├── VesselFilters.tsx
│   │       ├── CompareTable.tsx          ← R4
│   │       └── SearchBox.tsx
│   ├── lib/
│   │   ├── api.ts                        ← a belső API kliens
│   │   ├── i18n.ts                       ← a nyelv, a formázás
│   │   ├── seo.ts                        ← a meta, a hreflang, a JSON-LD
│   │   └── format.ts                     ← a szám/dátum/mértékegység
│   ├── content/                          ← a UI-szövegek (a content_key-ből)
│   │   └── keys.ts                       ← a kulcsok állandója (TS)
│   └── styles/
│       └── global.css                    ← a Tailwind v4
└── public/
    ├── favicon.svg
    └── robots.txt
```

---

## 3. A nyelvkezelés (a F-INTL-01…08)

### 3.1 Az Astro i18n konfiguráció

```js
// astro.config.mjs
export default defineConfig({
  output: 'server',
  adapter: node({ mode: 'standalone' }),
  i18n: {
    defaultLocale: 'hu',
    locales: ['hu', 'de', 'en'],
    routing: {
      // A 'prefix-default-locale' a magyar URL-t is prefixeli
      // (/hu/hajos/...) — a funkcioleiras 7. fejezete ezt írja elő
      // ("/hu/duna/hajok"), TEHAT a magyar is prefixelt.
      prefixDefaultLocale: true,
      redirectToDefaultLocale: false,   // a F-INTL-03: a sajat
                                       // nyelvválasztó sütijének
                                       // felülirhatósaga miatt nem
                                       // automatikus atiranyitas
    },
  },
});
```

**A `prefixDefaultLocale: true` és a `redirectToDefaultLocale: false`**
kombináció a kulcs: a magyar URL `/hu/...` (a funkcióleírás szerint),
de **nincs automatikus átirányítás** — a látogató böngészőnyelve
alapján csak **első látogatáskor** ajánlunk nyelvet (a F-INTL-03).

### 3.2 A nyelv kiválasztása (a middleware)

```ts
// src/middleware.ts
import { defineMiddleware } from 'astro:middleware';

export const onRequest = defineMiddleware(async (context, next) => {
  const lang = context.params.lang ?? 'hu';
  context.locals.lang = lang;

  // A nyelvválasztó sütije (a felhasznalo valaszthato)
  const cookieLang = context.cookies.get('site_lang')?.value;
  if (cookieLang && ['hu', 'de', 'en'].includes(cookieLang)) {
    context.locals.lang = cookieLang;
  }

  // A F-INTL-03: a bongeszo nyelve alapjan csak elso latogataskor
  const isFirstVisit = !context.cookies.get('site_lang');
  if (isFirstVisit) {
    const browserLang = pickFromAcceptLanguage(
      context.request.headers.get('accept-language'),
      ['hu', 'de', 'en'],
    );
    if (browserLang) {
      context.cookies.set('site_lang', browserLang, {
        path: '/', maxAge: 60 * 60 * 24 * 365, sameSite: 'lax',
      });
      context.locals.lang = browserLang;
    }
  }

  return next();
});
```

**A `pickFromAcceptLanguage`** a `q` értékek szerinti rendezést végzi
(`de-DE,de;q=0.9,en;q=0.8` → `de`), és a **nyelv-prefixet** nézi
(`de-DE` → `de`).

**A `context.locals.lang` a `src/env.d.ts`-ben deklarálva** — a
TypeScript típusát a `App.Locals` interface adja.

### 3.3 A formázás (a F-INTL-06, a 09. fejezet)

**A `Intl` API beépített** — nem kell könyvtár:

```ts
// src/lib/format.ts
const LOCALE: Record<string, string> = {
  hu: 'hu-HU', de: 'de-DE', en: 'en-GB',
};

/** A szamformazas a nyelv szerint (a 09. fejezet). */
export function formatNumber(value: number, lang: string): string {
  return new Intl.NumberFormat(LOCALE[lang] ?? 'hu-HU').format(value);
}

/** A datumrend a nyelv szerint. */
export function formatDate(d: Date, lang: string): string {
  return new Intl.DateTimeFormat(LOCALE[lang] ?? 'hu-HU', {
    year: 'numeric', month: 'short', day: 'numeric',
  }).format(d);
}

/** A mertekegyseg: a 09. fejezet szerint a hajomerek SI-alapuan
 *  tarolva, a megjelenites a nyelvtol fugo (km/h, t, m; a nemzet-
 *  kozi felhasznaloknak kn, nm, ft). */
export function formatLength(meters: number, lang: string): string {
  const unit = lang === 'en' ? 'ft' : 'm';
  const value = lang === 'en' ? meters * 3.28084 : meters;
  return `${formatNumber(Math.round(value * 10) / 10, lang)} ${unit}`;
}
```

**A tárolás SI-alapú, a megjelenítés a kliensoldali.** A 02-es terv
sémája a hosszt `length_m`-ben, a merülést `draught_max_m`-ben tárolja
— **nincs mértékegység-konverzió a DB-ben**.

### 3.4 A paraméterezett szövegek (a F-INTL-07)

**A `content_text.text` mezője** a `content_key` szerint tartalmazhat
változókat. **A behelyettesítés ICU MessageFormat szerint** történik —
a `messageformat` npm csomag (a `FormatJS` család).

```ts
// src/lib/i18n.ts
import { MessageFormat } from 'messageformat';

export function renderContent(
  template: string, lang: string, params: Record<string, unknown> = {},
): string {
  const mf = new MessageFormat(template);
  return mf.format(params as never);
}
```

**Példa:** a `vessel.list.count` kulcs →

| Nyelv | Szöveg |
|---|---|
| hu | `{count} hajó a katalógusban` |
| de | `{count} Schiffe im Katalog` |
| en | `{count} vessels in the catalogue` |

**A `messageformat` a `de`-ben is a helyes mondatsorrendet adja**
(a német főnév után a szám a második helyen megy: „2 Schiffe").

### 3.5 A hiányzó fordítás (a F-INTL-05)

**A hiányzó fordítás nem üresen jelenik meg** — a **forrásnyelv
szövegével, jelöléssel**:

```astro
---
// A content_text-ből: a kért nyelv, vagy a forrásnyelv csere
const { text, isFallback, fallbackLang } = await getContent('vessel.type.dry_cargo', lang);
---
<span class:list={['content', { 'content--fallback': isFallback }]}>
  {text}
  {isFallback && <span class="content__badge" title={t('ui.translationMissing')}>
    {fallbackLang.toUpperCase()}
  </span>}
</span>
```

**A `getContent` a 03-as API `/api/v1/content/{key}` végpontját hívja**
— a válasz `meta.translation_fallback` mezője jelzi a csere tényleges
nyelvét.

**A jelölés nyelvenként különböző?** A funkcióleírás 9. fejezete: „*a
magyar nyelvű szöveg nincs kész, a német és az angol változat külön-
külön jelölést kap*". **Azaz: ha a német nincs kész, de az angol igen,
az angol jelenik meg** — nem a magyar.

**A `getContent` implementációja a szerveroldalon:**

```ts
export async function getContent(key: string, lang: string) {
  const res = await apiFetch(`/api/v1/content/${key}?lang=${lang}`);
  const body = await res.json();
  const fb = body.meta?.translation_fallback?.[key];
  return {
    text: body.data.text,
    isFallback: Boolean(fb),
    fallbackLang: fb?.available ?? lang,
  };
}
```

**A hiánylista:** a szerkesztői felület (a 06-os terv) a
`translation_task` táblából építi — a hiányzó fordítások listája
nem a frontend aggadata.

---

## 4. A SEO (a F-NF-04)

### 4.1 A meta

```ts
// src/lib/seo.ts
export function buildMeta(params: {
  title: string; description: string; lang: string;
  canonical: string; alternates: Record<string, string>;
}) {
  return {
    title: params.title,
    description: params.description,
    canonical: params.canonical,
    alternates: params.alternates,   // a hreflang
    openGraph: { ... },
    jsonLd: { ... },
  };
}
```

**A `canonical` URL** mindig a **teljes abszolút URL** a nyelvi
prefixszel — a `site` a `astro.config.mjs`-ből (`SITE_URL` env).

### 4.2 A `hreflang` (a F-INTL-04)

**Minden oldalon**, mindhárom nyelvre + `x-default`:

```astro
<link rel="alternate" hreflang="hu" href={alts.hu} />
<link rel="alternate" hreflang="de" href={alts.de} />
<link rel="alternate" hreflang="en" href={alts.en} />
<link rel="alternate" hreflang="x-default" href={alts.hu} />
```

**A `x-default` a magyar** — a nemzetközi felhasználóknak az angol
lenne a jobb, de a **célközönség magyar** (a README 1. fejezete) →
a magyar az alapértelmezett.

**A `hreflang` kötelező a megfelelő nyelvi változatokra** — ha egy
nyelvi változat **nem létezik** (a hajóról nincs angol adatlap), akkor
**arra nem kerül `hreflang`** (a keresőmotorok ezt büntetik).

### 4.3 A JSON-LD

**A hajóadatlapon** a `Vessel` séma (a schema.org):

```json
{
  "@context": "https://schema.org",
  "@type": "Vehicle",
  "name": "TEST HAJO",
  "identifier": [{"@type": "PropertyValue", "name": "ENI", "value": "12345678"}],
  "description": "...",
  "url": "https://vessel-tracker.example/hu/hajos/test-hajo"
}
```

**A `WebSite` + `SearchAction`** a kezdőlapra:

```json
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "Vessel Tracker",
  "url": "https://vessel-tracker.example",
  "potentialAction": {
    "@type": "SearchAction",
    "target": "https://vessel-tracker.example/{lang}/kereses?q={search_term_string}",
    "query-input": "required name=search_term_string"
  }
}
```

### 4.4 A sitemap

**Az `@astrojs/sitemap`** a `site` konfigurációból generálja — de
**csak a statikus oldalakat** látja. Az SSR oldalak (a hajóadatlapok)
**dinamikusan** kerülnek a sitemapbe → **egy `/sitemap.xml.ts` route**
kell, ami a `vessel` táblából generálja.

```ts
// src/pages/sitemap.xml.ts
export async function GET({ site }) {
  const vessels = await apiFetch('/api/v1/vessels?per_page=200');
  // ... a teljes lista paginggel
  return new Response(xml, { headers: { 'Content-Type': 'application/xml' } });
}
```

**A `robots.txt`** a `public/` mappában:

```
User-agent: *
Allow: /
Sitemap: https://vessel-tracker.example/sitemap.xml
```

---

## 5. Az adatlekérés (a szerveroldali renderelés)

### 5.1 A belső API kliens

```ts
// src/lib/api.ts
const API_BASE = import.meta.env.API_INTERNAL_URL;  // http://api:8000

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  });
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return res.json();
}
```

**Az `API_INTERNAL_URL` a compose-on belüli hálózat** (`http://api:8000`)
— **nem** a publikus URL. A belső API **nem** publikálódik (a
03-as terv §1).

### 5.2 A szerveroldali adatlekérés (a `getStaticPaths` helyett)

**Az SSR-ben nincs `getStaticPaths`** — minden kéréskor kell az adat:

```astro
---
// src/pages/[lang]/hajos/[slug].astro
const { lang } = Astro.params;
const { slug } = Astro.params;

const vessel = await apiFetch(`/api/v1/vessels/by-slug/${slug}?lang=${lang}`);
if (!vessel) return Astro.redirect(`/${lang}/404`);
---
```

**A `by-slug` végpont** — a 03-as tervben a `/vessels/{id}` van (a
`{id}` a numerikus azonosító). **A mély link a `slug`-ot használja**
(F-CAT-07) → **a `slug` alapján is kell keresni**.

**Ez a 03-as terv egy hiánya**: a `/api/v1/vessels/{id}` az `id`-t
veszi, de az URL a `slug`. **A megoldás: a `slug` alapján is kell
lookup** — vagy a 03-as tervben a `{id}` a `slug` is lehet.

### 5.3 A `no-store` és a gyorsítótár

**A hajóadatlap adatai** a `position`-ből származnak (a
`vessel_last_position` nézet) — **egy percnél frissebbek lehetnek**.

| Oldal | Cache-Control |
|---|---|
| A hajóadatlap | `public, max-age=60, s-maxage=60` |
| A katalóguslista | `public, max-age=300, s-maxage=300` |
| A kereső | `no-store` (a szűrő a URL-ben van) |
| A statikus tartalom | `public, max-age=3600` |

**A `s-maxage` a CDN-nek szól** — a böngésző a `max-age`-et használja.

---

## 6. A komponensmodell

### 6.1 Az Astro-komponensek (a legtöbb)

**A `layout` → `page` → `component` hierarchia:**

```
Layout.astro              ← a html, a head, a nav, a footer, a nyelvválasztó
├── CatalogLayout.astro    ← a katalógus: a szűrő + a lista
│   ├── VesselFilters.tsx  ← a React-sziget (a szűrő)
│   └── VesselList.astro   ← a lista (a szűrő szerint)
├── VesselLayout.astro     ← a hajóadatlap: a fejléc + a blokkok
│   ├── VesselHeader.astro
│   ├── VesselSpecs.astro
│   ├── VesselOriginList.astro
│   └── VesselHistory.astro
└── ContentLayout.astro    ← a cikk, a hír
```

**Az `astro:content`** a `docs/` mappához — a fejlesztői dokumentáció
a `docs/megvalosulas/` alatt van, és az Astro Markdown-ként kezeli.

### 6.2 A React-szigetek (ahol a JavaScript kell)

**Csak három ilyen van R1-ben:**

| Sziget | Miért kell a JS | A hydration |
|---|---|---|
| `VesselFilters.tsx` | a szűrő az URL-t módosítja (a `history.replaceState`) | `client:idle` |
| `SearchBox.tsx` | a `cmd+K` gyorskereső (R3) | `client:visible` |
| `CompareTable.tsx` | az összehasonlítás (R4) | `client:visible` |

**A `client:idle`** a szűrőnél: a lapgörgetés után töltődik be, így
az első festés nem vár JS-re.

**A szűrő a URL-t módosítja, nem a state-et** — ez a F-CAT-10
(„*a lista nézete megőrzi a szűrőt és a rendezést az URL-ben*").

### 6.3 A szűrő → URL → szerveroldali feldolgozás

```
A felhasznalo megvaltoztatja a szuret
   → a VesselFilters.tsx frissiti a URL-t (replaceState)
   → az Astro navigacio ujra-rendereli a page komponenst
   → a page komponens az API-val lekeri az uj adatot
   → a lista frissul
```

**A teljes oldal újrarenderelődik** — nincs kliensoldali adatkezelés.
**Ez a legegyszerűbb és a legbiztonságosabb** (a URL az egyetlen
állapottartó), és a SEO-t is garantálja.

---

## 7. A katalóguslista (a F-CAT-02…14)

### 7.1 A lista oszlopai (a F-CAT-03)

| Oszlop | Forrás | Megjegyzés |
|---|---|---|
| A hajónév | `vessel_i18n.name` (a kért nyelven) | **nem fordul** → a latin hivatalos név (a 02-es terv §5.8.4) |
| A típus | `vessel_type_i18n.name` | **fordul** |
| Az azonosító | `vessel_identifier` (területenként) | a Duna: ENI, a Balaton: hajószám |
| Az üzemeltető | `operator_i18n.display_name` | **fordul** |
| Az állapot | a `vessel.status` + a `verification_level` | a bizonyossági badge |

**A lista 50 hajót mutat laponként** — a F-NF-01: „*Katalógusoldal
betöltése (300 hajós lista) < 800 ms p95*".

### 7.2 A szűrő és a rendezés az URL-ben

```
/hu/hajos?area=duna&type=INLAND_CARGO&operator=7&sort=name&order=asc&page=2
```

**A `page` a lapozás** — a 03-as terv szerint.

### 7.3 Az üres állapot (a F-SRCH-06)

**Nincs találat → a javasolt lépések:**

```
Nincs találat a "xyz" keresésre.
- Nézd meg a kikötők listáját
- Küldj egy korrekciót
- Próbáld a másik területen (Balaton)
```

**A „küldj egy korrekciót" link** a `POST /api/v1/feedback` űrlapjára
megy (a F-DET-11).

---

## 8. A hajóadatlap (a F-DET-01…16)

### 8.1 A blokkok sorrendje

| # | Blokk | Tartalom | F |
|---|---|---|---|
| 1 | **Fejléc** | a név, a típus, az állapotjelző, a terület, a **bizonyossági badge** | F-DET-01, F-DET-14 |
| 2 | **Azonosító blokk** | az ENI/MMSI/IMO/hajószám + a **forrásjelölés** | F-DET-02, F-DET-15 |
| 3 | **„Hol van"** | a szöveges hely (R1-ben) | F-DET-06 |
| 4 | **Műszaki adatok** | a hossz, a szélesség, a merülés, a GT, a DWT, a TEU, a teljesítmény, az építési év | F-DET-03 |
| 5 | **Üzemeltető blokk** | a cég neve, az ország | F-DET-04 |
| 6 | **„A hajó szerepe"** | az önjáró / bárka / toló / vontató / személyhajó | F-DET-08 |
| 7 | **Hajótörténet** | a korábbi nevek, a tulajdonosváltások | F-DET-05 |
| 8 | **Bizonyítékok** | a hajóhoz kötött kikötők, zsilipek | F-DET-07 |
| 9 | **Javító észrevétel** | a visszajelzési űrlap | F-DET-11 |
| 10 | **Fordítási állapot** | a hiányzó fordítások jelölése | F-DET-13 |

### 8.2 A mezőnkénti forrásjelölés (a F-DET-15)

**Minden adatnál** látszik, honnan jött és mikor frissült:

```astro
<dd>
  {formatLength(vessel.length_m, lang)}
  <OriginBadge origin={originOf('length_m')} observedAt={...} />
</dd>
```

**Az `OriginBadge`** a `vessel_data_origin` alapján:

| `origin` | Jelölés | Magyar |
|---|---|---|
| `ais` | egy ikon | „AIS" |
| `operator_claimed` | egy ikon | „Üzemeltető állítása" |
| `official` | egy ikon | „Hatósági adat" |
| `editorial` | egy ikon | „Szerkesztői adat" |

**A konfliktus (a 02-es terv `vessel_data_origin_conflicts` nézete):**
ha egy mezőnek **több forrása** van, **mindkettő megjelenik**:

```
Hossz: 110,0 m
  AIS · 2026-11-15
  Üzemeltető állítása · 2026-11-02 · 105,0 m   ← ellentérés
```

**A `confidence`** a `vessel_data_origin.confidence` mezője — ha van,
egy sávgrafikon jelzi.

### 8.3 A hiányzó adat (a F-DET-16)

**A hiányzó adat üresen és jelölve** — nem találgatott értékkel:

```astro
<dd class="value--missing">
  — <span class="badge">Nincs adat</span>
</dd>
```

**A jelölés nyelvfüggő** — a `content_key` (`vessel.field.missing`).

---

## 9. A „hol van" (a F-DET-06) — R1-ben szövegesen

**A szöveges hely összeállítása** a `vessel_last_position` nézetből
(a 02-es terv §6.3a) + a `river_section_i18n.name`-ből:

```
Duna, 1642–1635 km, Szob–Budapest szakasz
```

**A részletek:**
1. a `waterway_i18n.name` (a folyó neve)
2. a `river_km` — a formázás **a nyelv szerint** (`1 642 km` / `1.642 km`)
3. a `river_section_i18n.name` (a szakasz neve)

**A `river_section` a `position.river_section_id`-ből jön** — a
`vessel_last_position` nézet tartalmazza.

**Ha nincs pozíció** (a hajó még nem küldött, vagy a szűrő kizárta):
**„Nincs pozícióadat"** — a F-DET-16 szerint.

---

## 10. A teljesítmény

| Oldal | Cél (p95) | Hogyan |
|---|---|---|
| A kezdőlap | **< 500 ms** | a `max-age=300` cache + a statikus részek |
| A katalóguslista | **< 800 ms** (a 300 hajós listára) | az API p95 < 300 ms + a renderelés |
| A hajóadatlap | **< 500 ms** | az egyetlen API-hívás + a `max-age=60` |
| A kereső | **< 600 ms** | a trigram index a DB-ben |

**A hajóadatlap a legkritikusabb** — a SEO-crawl egy millió oldalt
járhat be, és **a TTFB számít**.

**A `Web Vitals`:** az LCP < 2,5 s, a CLS < 0,1. A **CLS** a
veszély: a hiányzó fordítások betöltése után eltolhatja a layoutot →
**a betöltött tartalom helyére foglaló foglaló elem** (`min-height`).

---

## 11. A tesztelés

| Szint | Tartalom | Eszköz |
|---|---|---|
| **Unit** | a `format.ts`, az `i18n.ts`, a `seo.ts` | `vitest` |
| **Komponens** | az Astro komponensek (a `astro-container`) | `vitest` + `@astrojs/testing-library` |
| **E2E** | a fő felhasználói utak (a katalógus → a szűrés → a hajóadatlap) | `playwright` |
| **SEO** | a `hreflang`, a `canonical`, a sitemap, a JSON-LD | `playwright` + a séma-ellenőrző |
| **i18n** | mindhárom nyelven minden oldal | a `playwright` parametrizálva |
| **Vizuális** | a design system regressziója | a `playwright` screenshot |

**Az i18n-teszt** kritikus: **minden oldal** mindhárom nyelven
betöltődik-e, és a `hreflang` létezik-e?

**A linkellenőrzés** a CI-ben: minden belső link létező oldalra
mutat-e (a `docs/megvalosulas/` és a `docs/` között is).

---

## 12. A nyitott kérdések

| # | Kérdés | Alapértelmezés | Állapot |
|---|---|---|---|
| Q1 | A `hreflang` a **nem létező** nyelvi változatra | **nem kerül rá** (a keresőmotorok büntetik a hibás `hreflang`-et) | nyitva |
| Q2 | A `x-default` melyik nyelv legyen? | **a magyar** (a célközönség magyar, a README 1. fejezete) | nyitva |
| Q3 | A katalóguslista a `vessel_i18n.name`-re rendez (a latin névre) vagy a `sort_name`-re? | a `sort_name`-re — a 02-es terv denormalizálta a gyors olvasáshoz | **lezárva** |
| Q4 | A `/api/v1/vessels/{id}` a numerikus `id`-t vagy a `slug`-ot veszi? | **mindkettőt** — a mély link a `slug` (F-CAT-07), de az API a `slug` alapján is kereshet | **a 03-as tervben javítandó** |
| Q5 | A sötét mód (a dark mode) | **R1-ben nincs** — a világos téma a design alapja | nyitva (R3+) |
| Q6 | A „hasonló hajók" ajánlás (a katalógus oldalán) | **R4** (a F-CAT-13) | nyitva (R4) |
| Q7 | A React-szigetek hydration strategiája | `client:idle` a szűrőnél, `client:visible` a többinél | **lezárva** |

---

*Ez a terv a `docs/megvalósulas/` sorozat ötödik darabja. Következik: 06 –
szerkesztői felület.*
