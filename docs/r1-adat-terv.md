# R1 adat-terv – AIS-first hajókatalógus

**Verzió:** 2.1 (2026-11-14) — *az 1.0 teljesen újraírásra került, lásd 0. fejezet; a 2.1 a feed-döntést és a Balaton-hatókört rögzíti*
**Kapcsolódó dokumentumok:** [`funkcio-leiras.md`](funkcio-leiras.md) · [`release-terv.md`](release-terv.md) · [`../README.md`](../README.md) (adatbázis terv) · [`ais-vevo-terv.md`](ais-vevo-terv.md) (saját AIS vevőhálózat)

---

## 0. Miért kellett újraírni a tervet

Az 1.0 verzió a katalógust a **Közlekedési Hatóság hajólajstromjára** építette, adatszolgáltatási kérés formájában. Ez két okból nem volt jó alap:

1. **A lajstrom nem nyílt adatkészlet** – a hozzáférés nem garantált, és a formátum (XLSX/PDF) kézi bevitelre kényszerít.
2. **Végül is kellett a feed-részlet** – a katalógus statikus adatai is AIS-ból jönnek, tehát a választható kockázat nem volt valódi.

**Az új alapelv:**

> **A katalógus AIS-ból épül fel. Amit az AIS nem ad, azt az üzemeltető önbevallása pótolja. Amit sem az AIS, sem az üzemeltető nem ad, az nem jelenik meg – és nincs is rá igény.**

Ez a terv **nem függ hatósági adatkéréstől**. Az AIS-adatot **saját vevőhálózattal** gyűjtjük ([`ais-vevo-terv.md`](ais-vevo-terv.md)), és azt R1-ben *statikus adatgyűjtésre* használjuk, nem pozíciókra.

> **Rögzített döntések (2026-11-14):**
> 1. **Adatbeszerzés:** ha a legális feed-hozzáférés nem megoldható (és a scraping szolgáltatói feltételeket sért), **saját AIS vevőhálózat** épül. A részletes terv: [`ais-vevo-terv.md`](ais-vevo-terv.md).
> 2. **Balatoni hatókör:** a **vitorlások és kishajók nem kerülnek be** a katalógusba. A Balaton-katalógus a jelentős motoros hajókat tartalmazza (nagyhajók, kompok, szolgálati hajók, úszó munkagépek, uszályok) — kb. **80–100 rekord**.

### Mi változott a v1 → v2 összevetésben

| | v1.0 | v2.0 |
|---|---|---|
| Elsődleges forrás | Közlekedési Hatóság lajstromja | **AIS (Inland FI 10 + Message 5)** |
| ENI honnan | hatósági lajstrom | **AIS Inland FI 10 üzenetből** |
| Folyó-km honnan | geometriai illesztés | **AIS fairway hectometre – közvetlenül** |
| Kikötők honnan | hatósági lista + OSM | AIS cél-UN/LOCODE + Duna Bizottság port-km táblázat + OSM |
| Tulajdonos, kapacitás, építési év | hatósági lajstrom | **üzemeltetői önbevallás (claim)** |
| Balaton | hatósági lista | üzemeltetői flottaoldalak + AIS (nagyhajók) + publikált kikötőrendek |
| Feed igény | R2 | **R1 (statikus gyűjtés)** – lásd 8. fejezet |

---

## 1. Mit ad az AIS – és mi a Duna-specifikus rész

### 1.1 Tengeri AIS – Message 5 (Class A statikus és útvonaladat)

| AIS mező | Tartalom | Pontosság | Használható a katalógusban? |
|---|---|---|---|
| MMSI | 9 számjegy | – | ✅ **elsődleges kulcs** |
| IMO-szám | 7 számjegy | – | ⚠️ **belvízi hajóknál a szabály szerint nem érvényes** („not available for Inland vessels") |
| Hívójel | max. 7 karakter | – | ✅ azonosító |
| Hajónév | max. 20 karakter | – | ✅ |
| Hajótípus | 1–99 (AIS-kód) | – | ✅ (de nem azonos az UN E-rek. 28 kóddal) |
| Méretek | antenna-horgonyponttól számolva | 1 m | ⚠️ lásd 1.4 |
| Merülés | 0,1 m | 0,1 m | ✅ |
| Célállomás | 20 karakter, szabad szöveg | – | ⚠️ nem strukturált |
| ETA | MMDDHHMM UTC | – | ✅ |

### 1.2 Belvízi AIS – Inland FI 10 (ez a Duna-specifikus kincs)

Az EU belvízi AIS technikai specifikációja (2019/838/EU melléklet, 3. szakasz) külön **Inland FI 10** üzenetet definiál a belvízi hajók számára. **Ez tartalmazza az ENI-t.**

| FI 10 mező | Tartalom | Formátum |
|---|---|---|
| **1** | **ENI (Egyedi Európai Hajóazonosító)** | `cccccccc` – 8 karakter |
| 2 | Belvízi hajótípus (ERI, APPENDIX C) | 14 bit |
| 3 | Hajó hossza | `x.x` méter, 0–800,0 m |
| 4 | Hajó szélessége | `x.x` méter, 0–100,0 m |
| 5–7 | Sebesség / út / irány minőségi jelzés | 1 bit |
| 8–11 | B/C értékek (belső és külső referenciapont) | `x.x` méter |
| **Útvonaladat (szintén FI 10)** | | |
| – | **Zászlóállapot** | UN country code (2 karakter) |
| – | **Célállomás** | UN location code (3 karakter) = UN/LOCODE |
| – | **Terminál** | Terminal code (5 karakter) |
| – | **Zsóldemér szakasz** | Fairway section number (5 karakter) |
| – | **Folyó-km** | Fairway hectometre (5 karakter) |
| – | **ETA zsilipnél / hídnál / terminálnál** | MMDDHHMM UTC |
| – | **Vontató hajók száma** | 3 bit (0–6, 7 = ismeretlen) |
| – | **Légmagasság** | 12 bit, 1/100 m |
| – | **Veszélyes áru jelölés** | 3 bit (0–3 kék kúp, 4 = B-Flag) |
| – | **Rakott / üres** | 2 bit |
| – | **Merülés** | 11 bit, 1/100 m |

> **Ez a válasz a kérdésre: az ENI igenis AIS-ból szerezhető meg** – Inland AIS felszerelés esetén, az FI 10 üzenet első mezőjeként. Nem kell hozzá hatósági lajstrom.
>
> A 2019/838/EU az Inland AIS-t a Duna hajózási szakaszán kötelezővé teszi (a „Standard Vessel Tracking and Tracing for Inland Navigation" melléklet), tehát a gyakorlatban a hajók FI 10-et küldenek.

### 1.3 Amit az AIS **nem** ad (teljes lista)

| Hiányzó adat | Miért fontos | Honnan pótolható |
|---|---|---|
| **Üzemeltető / tulajdonos** | a katalógus egyik legkeresettebb mezője | **üzemeltetői önbevallás (claim)** |
| **Építési év** | korsorbecslés | claim |
| **Bruttó tonnage / DWT** | kapacitás | claim |
| **Utasbefogadóképesség** | Balatoni turisztikai döntéshez kritikus | claim |
| **IMO-szám** | belvízi hajóknál nincs | – (a szabály szerint sem) |
| **Hajótörténet** (átnevezés, tulajdonosváltás) | | claim + szerkesztői |
| **Hajó szolgáltatásai** (WC, étterem, akadálymentesség) | | claim (Balaton) |
| **Szezon** (mikor közlekedik) | | claim (Balaton) |
| **Fotó** | SEO, vizuális | claim / szerkesztői |

### 1.4 Amit az AIS **korlátozottan** ad – ahol vigyázni kell

| Korlát | Részlet | Következmény a katalógusban |
|---|---|---|
| **A méretek a konvoj méretei lehetnek** | A szabály szerint a konvoj méretét a legnagyobb téglalap alakú burkolólap méretre kell állítani | A hossz/szélesség **nem feltétlenül a hajóé**; a `length_m`/`beam_m` mezőt „AIS méretként" kell jelölni, nem hivatalos hajóméretként |
| **A méret a horgonyreferenciapontból számolódik** | `L = A + B`, `W = C + D` (a közlés irányához igazítva) | Az érték a hajó teljes hosszát adja meg, de a *referenciapont* eltolás miatt a hossz- és szélesség-arány nem pontos |
| **A merülés RNW-re vonatkozik** | A Duna szabályos alacsony vízállása (Regulierungsniederwasserstand) a Kelheim (km 2411,60) – Sulina (km 0) szakaszon, 1961–1990 megfigyelésekből | A merüléshez **mindig hozzá kell mondani az RNW-t** – a felületen: „merülés: 3,2 m (RNW)". Az `RNW` referencia a sémában kötelező |
| **Az ENI csak Inland AIS esetén van** | Csak Class A (tengeri) felszerelésnél nincs FI 10 | Az ENI nélküli hajókat MMSI + hívójel alapján azonosítjuk, és ezt a felületen jelöljük |
| **Az AIS hajótípus-kódja nem az UN E-rek. 28 kód** | Az AIS 1–99 kódja műszaki kategória | Külön leképezés kell: `ais_type_code` → `vessel_type_code` (ERI-kód). A katalógus a **normált** típust mutatja |
| **A hívójel a rádióengedély szerinti név** | Nem feltétlenül egyezik a hajó „kereskedelmi" nevével | Két névmező: `callsign` és `vessel_name` (a kereső mindkettőre keres) |
| **A célállomás szabad szöveg** | Kivéve az FI 10-ban, ahol UN/LOCODE | Az elsődleges kikötő-feloldás az FI 10 UN location code-ja; a Message 5 szövege csak tartalék |

### 1.5 A folyó-km: **nincs átváltás**

Ez a legkevésbé várt, de leghasznosabb megkönnyítés.

- A Duna km-számlálása **egyetlen, nemzetközileg használt skálán** történik: **0 km a Sulinánál (a Fekete-tenger torkolatánál), és felfelé nő** (Duna Bizottság; a WSV Streckenatlas Donau: „Die Kilometrierung beginnt an der Donaumündung (Hafen von Sulina) und steigt stromaufwärts").
- Fontosabbrázok: **Sulina 0** · **Kelheim 2414,72** · **Regensburg 2379** · **Passau 2226** · **Bécs 1929** · **Pozsony 1868** · **Budapest 1758** · **Mohács 1447** · **Belgrád 1167** · **Turnu Severin 931** · **Brăila 300** · **Galați 71**.
- A hivatalos szakaszhatárok: **Felső Duna** (2414,72–1791) · **Középső Duna** (1791–931) · **Alsó Duna** (931–0).
- Az AIS **fairway hectometre** mezője **ugyanebben a skálában** értendő.

> **Következmény:** a `river_km` denormalizált mező **közvetlenül az AIS-ból jön**. Nem kell geometriai illesztést csinálnunk (GPS-pont → legközelebbi km-tábla), és nem kell PostGIS-alapú river-km-indexet építenünk. A `river_section` meghatározása is AIS-ból történik (fairway section number), a mi szakaszainkra leképezve.

---

## 2. A négy forrásréteg

| Réteg | Tartalom | Forrás | Megbízhatóság | Felhasználói jelölés |
|---|---|---|---|---|
| **A – AIS statikus** | ENI, MMSI, hívójel, név, típus, méretek, merülés, zászló | Inland FI 10 + Message 5 – **saját vevőhálózatból** | nagy (a hajó önkényes adata) | „AIS alapján" |
| **B – AIS útvonal** | folyó-km, szakasz, célkikötő, terminál, ETA zsilipnél, rakomány-jelölés, vontatók száma | Inland FI 10 | nagy, idővel változó | „AIS alapján" |
| **C – Üzemeltetői önbevallás** | üzemeltető, kapacitás, építési év, szolgáltatások, szezon, fotó | claim űrlap (4. fejezet) | közepes – de ellenőrizhető | „Az üzemeltető adata" |
| **D – Publikált hatósági anyag** | kikötőrendek, tájékoztatók, Duna Bizottság port-km táblázat, Danube Commission flotta-statisztika | nyilvános PDF | nagy | „Hatósági adat" |

**A lényeg a D rétegben:** a v1 terv a hatósági *adatbázist* kérte – ez hozzáférési probléma. A **publikált dokumentumok** (kikötőrendek, tájékoztatók, a Duna Bizottság távolságtáblázata) viszont szabadon elérhetők, és pont a kikötők/szakaszok adatait tartalmazzák. **A Duna-katalógus kikötő- és szakasz-adatait ezekből lehet felépíteni – adatkérés nélkül.**

---

## 3. A Duna-katalógus felépítése AIS-ből

### 3.1 A folyamat

```
AIS feed (Inland FI 10 + Msg 5)
   ↓
① statikus üzenetek gyűjtése, kulcs: ENI (ha van) egyébként MMSI
   ↓
② vessel entitás létrehozás/upsert, státusz: 'ais_identified'
   ↓
③ FI 10 → river_km, river_section, célkikötő (UN/LOCODE), terminál
   ↓
④ hiányzó mezők → üres, 'is_missing' jelölés (nem kitalálunk!)
   ↓
⑤ üzemeltetői claim → a hiányzó mezők kitöltése, 'operator_claimed'
   ↓
⑥ publikálás a katalógusban; a bizonyosság szintje látható
```

### 3.2 A hajó „bizonyossági szintje" – ez az R1 legfontosabb új fogalma

Mivel az adatok forrása és minősége hajónként eltér, **a katalógusnak ezt láthatóvá kell tennie**, különben a felhasználó nem tudja, mit érdemes elhinnie.

| Szint | Jelölés | Mit jelent | Hány hajó várható |
|---|---|---|---|
| `ais_identified` | ✅ zöld | Van ENI-ja **és** hívójele – a rádióengedély szerinti azonosítás, AIS-ből | ~55–65% |
| `ais_partial` | 🟡 sárga | Van MMSI-je, de nincs ENI-je (nem Inland AIS felszerelés) | ~25–35% |
| `operator_claimed` | 🔵 kék | Nincs AIS-azonosítás, de az üzemeltető igazolta a hajót | a többi |
| `name_only` | ⚪ szürke | Csak a neve ismert (Balaton, kishajók) | a Balaton-vitorlásoknál |

**A felületen ez egy badge**, a hajóoldalon pedig mezőnkénti forrásjelölés. Ez nem gyengeség, hanem **hitelesítési előny** – a versenytársak nem mutatják meg, honnan van az adat.

---

## 4. Az üzemeltetői önbevallás (claim) – a hiányzó mezők pótlása

### 4.1 Miért ez a megoldás

Az AIS nem ad üzemeltetőt, kapacitást, építési évet. Ezek nélkül a katalógus „félkész": a hajóról tudjuk, hogy létezik, de nem tudjuk, ki birtokolja és mit szállít. A v1 terv ezt hatósági adattal oldotta meg – mostantól a termék maga szerzi be.

### 4.2 Hogyan működik

| Lépés | Leírás |
|---|---|
| 1. A hajó adatlapján a „Jelentem a hajót" gomb (vagy az üzemeltető saját oldala) | Az űrlap a hajó MMSI-jéhez kötődik, így nem kell új hajót létrehozni |
| 2. Az üzemeltető megadja a hajó azonosítóját: **MMSI vagy ENI** (vagy hívójel + név) | Az ENI a belvízi AIS-ből érkező hivatalos azonosító, az MMSI a rádióállomás azonosítója |
| 3. Az ellenőrzés: az azonosító egyezik a rendszerben lévő AIS-rekorddal **ÉS** a megadott cég adatai illeszkednek a hajószámhoz vagy az üzemeltető nevéhez | Ha nincs egyezés, a claim elutasítható vagy kézi egyeztetésre vár |
| 4. Az üzemeltető kitölti a hiányzó mezőket (kapacitás, év, szolgáltatások, szezon, fotó) | Csak az AIS-ből hiányzó mezők jelennek meg az űrlapon – a meglévő AIS-adatot nem lehet átírni |
| 5. A mezők `origin = 'operator_claimed'` eredettel kerülnek be, **a hajót nem írjuk felül automatikusan** – ha az AIS-ben van adat, azt megőrizzük, és a kettő konfliktusa látható | A konfliktus nem oldódik fel automatikusan: a szerkesztő dönt, a felületen mindkét érték látszik |
| 6. A szerkesztő ellenőrzi, és publikálja | A jóváhagyás után a mezők a hajóoldalon „az üzemeltető adata" jelöléssel jelennek meg |

### 4.3 Jogi és adatvédelmi keretek

- Az önbevallás **nem hatósági adat**, és ezt a felületen **explicit jelölni kell** („Az üzemeltető által megadott, ellenőrzésre váró adat").
- Az üzemeltető csak **a saját hajójához** férhet hozzá – a claim kötődik egy `operator` rekordhoz, amit ellenőrizni kell.
- A `vessel` entitásban **továbbra sem** lehet személyes adat (kapitány, magánszemély tulajdonos neve) – a claim űrlap ezt tiltja, és a validáció elutasítja.
- GDPR: az üzemeltető kapcsolattartója a cég jogi képviselője – természetes személy adatai nem kerülnek a `vessel` rekordba, hanem az `operator` entitásba (ott kezelhető).

### 4.4 Séma-követelmény: `vessel_data_origin`

A mezőnkénti eredet nyilvántartása új táblát igényel, mert egy mezőnek több eredete is lehet (AIS + üzemeltető), és a konfliktust meg kell tudni mutatni.

| Tábla | Oszlopok |
|---|---|
| `vessel_data_origin` | `id` PK, `vessel_id` FK, `field_name`, `origin` (ais/operator_claimed/official/editorial), `value_snapshot`, `source_id` FK, `observed_at`, `confidence`, `is_current` bool |

A `vessel` rekord tárolja az **aktuális** értéket (a gyors olvasás kedvéért), a `vessel_data_origin` pedig a **történetet és az eredetet**. A UI így tudja: „Merülés: 3,2 m — AIS (2026-11-14)"; „Kapacitás: 850 t — az üzemeltető adata (2026-11-02)".

---

## 5. A Balaton: miért kell más megoldás

| Tény | Következmény |
|---|---|
| A Balatonon ~40–50 kishajó és több száz vitorlás van, ezek **nincsenek AIS-felszereléssel** – és **a döntés alapján nem is kerülnek be** a katalógusba | Az AIS itt **nem fedi le** a katalógust, de a kizárt hajók miatt ez nem probléma: a maradék ~80–100 jelentős motoros hajó nagy része AIS-elhető |
| A nagyhajók (Szent György, Jókai, Csongor, Balaton katamarán…) **vannak AIS-en** | A nagyhajók AIS-ből kiegészíthetők |
| A kikötőrendek és tájékoztatók **publikáltak** (KH, Balatoni Hajózási Zrt.) | A kikötő-adatokhoz **nem kell adatkérés** |
| A hajók listája az **üzemeltetők saját oldalain** van (~15 üzemeltető) | Ez a legkisebb ráfordítású és legfrissebb forrás; a kizárt kishajók miatt a lista kezelhető méretű |
| A közlekedés **szezonális** | A szezon az üzemeltetőtől jön (claim), nem a hatóságtól |

**A Balaton-katalógus tehát: üzemeltetői flottaoldalak (a gerinc) + AIS (a nagyhajók kiegészítése) + publikált kikötőrendek (a kikötők).** Nincs szükség hatósági adatkérésre.

**A katalógusba kerülő Balatoni hajók (döntés szerint):** nagyhajók (több mint 100 fő), személyhajók, kompok, szolgálati hajók, úszó munkagépek, uszályok. **Nem kerülnek be:** a kishajók és a vitorlások. A teljes katalógus így ~80–100 hajó – **kézzel tartható**, és minden bejegyzéshez van ellenőrizhető forrás.

> **Kockázat:** az üzemeltetői oldalak nem stabilak (a flottaoldal URL-je és tartalma évente változik). **Mitigáció:** a bevitel éves, kézi, ellenőrzött – és a `data_source` rekordban minden forráshoz mentjük a *beolvasás dátumát és a mentett URL-t*. Ha egy üzemeltető megszűnik, a rekordja nem tűnik el, csak „megerősítésre vár" státuszba kerül.

---

## 6. Mező-mátrix (v2.0)

| Mező | Duna – AIS | Duna – claim | Balaton | Jelölés a UI-ban |
|---|---|---|---|---|
| ENI | ✅ Inland FI 10 | – | ❌ nincs | „ENI (AIS)" |
| MMSI | ✅ | – | ✅ nagyhajóknál | „MMSI (AIS)" |
| Nemzetközi hajószám | ✅ | ✅ | ✅ | „Hajószám (AIS)" / „(üzemeltető)" |
| Hajónév | ✅ | ✅ | ✅ | latin betűs, nem fordítandó |
| Típus | ✅ ERI-kód | – | ✅ (kategória) | „típus (AIS)" |
| Hossz / szélesség | ✅ (AIS méret, figyelem: konvoj) | ✅ pontosabb | ✅ | „AIS méret" vs. „műszaki adat" |
| Merülés | ✅ (RNW-re) | – | – | „merülés (RNW)" |
| Zászlóállapot | ✅ UN country code | – | ✅ | |
| Üzemeltető | ❌ | ✅ | ✅ (nyilvános oldalról) | „Az üzemeltető adata" |
| Kapacitás (DWT/TEU/utas) | ❌ | ✅ | ✅ | „Az üzemeltető adata" |
| Építési év | ❌ | ✅ | ✅ | „Az üzemeltető adata" |
| Folyó-km | ✅ | – | – (helyette partkm) | „AIS pozíció" |
| Folyószakasz | ✅ fairway section | – | – medence | |
| Célkikötő | ✅ UN/LOCODE | – | – | |
| ETA zsilipnél | ✅ | – | – | R4-ben válik hasznos |
| Veszélyes áru jelölés | ✅ | – | – | |
| Rakott/üres | ✅ | – | – | |
| Szezon | – | ✅ | ✅ | „Szezonban közlekedik" |
| Kikötő | ✅ (célállomásból) | – | ✅ kikötőrendből | |

---

## 7. Validációs szabályok (v2.0)

### 7.1 Azonosítók

| Szabály | Szint |
|---|---|
| ENI: 8 karakter, az első 3 a hatósági kód (nem a MID!) | elutasító |
| MMSI: 9 számjegy, az első 3 a MID (Duna-országok: AT 203, BG 207, HR 238, HU 243, DE 211/218, MD 214, RO 264, RS 279, SK 267, UA 272) | elutasító |
| Az IMO-mező belvízi hajónál 0 → „nem érvényes", **nem hiba** | figyelmeztető |
| Hívójel: max. 7 karakter, nagybetű + szám | elutasító |
| Azonos ENI-vel két hajó | **elutasító** |
| Azonos MMSI-vel két hajó | **elutasító** |
| Duplikált hajónév | figyelmeztető (átnevezés miatt lehet) |

### 7.2 AIS-specifikus mezőértékek

| Szabály | Szint |
|---|---|
| `length_m` > 0 és `beam_m` > 0, ha AIS-ből jött | figyelmeztető, ha 0 (a 0 = „not available") |
| A méret 0,1 m-es pontosságú, a referenciapont a közlés irányához igazított | **dokumentálva**, nem hiba |
| `draught` > 0 és a hajó merülése RNW-re értendő | kötelező jelölés a UI-on |
| A zászló-ország nem egyezik a hajó hazai kikötőjének országával | figyelmeztető |
| `fairway hectometre` a 0–2414,72 tartományon kívül | figyelmeztető |
| A `fairway section` kód nem létezik a `river_section` táblánkban | figyelmeztető → a szakasz-leképezés bővítése |
| Az UN location code nem létezik a `port` táblánkban | figyelmeztető → új kikötő-jelölt |
| A `destination` szöveg és az UN/LOCODE eltér egymástól | figyelmeztető |
| Az ERI-típuskód 0 (nem elérhető) | figyelmeztető |

### 7.3 Claim-validáció

| Szabály | Szint |
|---|---|
| A claim MMSI/ENI-je létező AIS-rekordra mutat | elutasító |
| A claimben szereplő üzemeltető már létezik az `operator` táblában | figyelmeztető (új operator → jóváhagyás) |
| Személyes adatot tartalmazó mező (kapitány, magánszemély) | **elutasító** |
| A kapacitás nem negatív, és a típushoz illik (DWT csak teherhajnál) | figyelmeztető |
| A claimben szereplő mező nem írhatja felül az AIS-értéket konfliktus nélkül | **kötelező**: a konfliktus feloldandó vagy a felületen mindkettő látszik |

---

## 8. Az AIS adat beszerzése – a saját vevőhálózat

> **A döntés (2026-11-14):** ha a legális feed-hozzáférés nem megoldható, **saját AIS vevőket építünk**. A vevőhálózat teljes terve: [`ais-vevo-terv.md`](ais-vevo-terv.md).

Az alábbiak a vevőterv összefoglalója; a részletek (hardver, lefedettség-számítás, jogi keret, mérési protokoll) ott vannak.

### 8.1 Miért kell már R1-ben

A statikus hajóadat **ugyanabból a feedből** jön, mint a pozíció. Nem külön beszerzendő dolog – de **időbeli problémát okoz**:

> **A feed csak a szerződés kezdete után ad statikus adatot.** Az AIS statikus üzenet (Message 5, FI 10) csak ritkán küldi el a hajó – hetente-hónaponta, az aktivitásától függően. **Egy frissen indított feeddel tehát az R1-ben még nem lesz teljes katalógus.**

**Következmény – az R1 előkészítő fázisa:**

| Fázis | Időtartam | Tartalom |
|---|---|---|
| **R1-0 (előkészítő)** | **3–6 hónap a formális R1 előtt** | **A vevőhálózat építése és a statikus adatok gyűjtése** – ha saját vevőt építünk, a statikus adat a vevő üzembe helyezése pillanatától rendelkezésre áll, tehát nincs „várakozás a feedre" |
| R1 | – | A gyűjtött statikus adatból felépül a katalógus |

Ez az ütemezésben **a legfontosabb változás** a v1-hez képest, és a release-tervet is módosítja.

> **A saját vevő itt előny:** egy fizetős feedet csak a szerződés kezdetétől tudunk gyűjteni (2–3 hónap várakozás, és közben nem tudunk mérni), a saját vevő viszont **már a próbaüzem első napjától** adatot termel – ezért a mérés és a gyűjtés ugyanaz a tevékenység.

### 8.2 A feed lehetőségek

| Lehetőség | Státusz | Előny | Hátrány |
|---|---|---|---|
| **Fizetős aggregátor** (AIS-hub, Kpler/Spire, MarineTraffic) | **tartalék opció** | globális lefedettség, S-AIS is, nincs hardvermunka | költség, licencfeltételek, a statikus adat csak a szerződés kezdetétől |
| Fejlesztői feed (valós idejű WebSocket) | **csak prototípushoz** | olcsó, azonnal elérhető | nincs historikus adat, korlátozott lekérdezés |
| **Saját vevőhálózat a Dunán** | **a fő út** | teljes kontroll, korlátlan historikus nyers NMEA, nincs vendor-lock, a cég saját adatbázisa | hardver + hálózat + üzemeltetés, és a folyó mentén sok site kell a teljes lefedettséghez |
| Nemzetközi szervezeti adatok (Duna Bizottság, RIS-rendszerek) | **megkeresendő, nem a terv alapja** | a hivatalos forgalmi statisztika | általában aggregált vagy korlátozott tartalom, kutatási célra |

### 8.3 Amit a feed kiválasztásakor **döntően** vizsgálni kell

| Szempont | Miért kritikus itt |
|---|---|
| **A Duna menti lefedettség** | A VHF-alapú AIS a part felé terjed; a szárazföldi (terrestrial) lefedettség a folyó mentén korlátozott. Ha a feed csak S-AIS-t ad, a köztes vízi állapotok kimaradnak |
| **Statikus üzenetek (Msg 5, FI 10) elérhetősége** | Nem minden feed ad statikus adatot, és nem minden hajó küldi el |
| **Historikus visszamenőleg** | Az R1-nek a gyűjtés alatt keletkezett statikus adatot kell kapnia |
| **Terjesztési jog** | A nyilvános AIS-adat és a szolgáltatói licenc nem ugyanaz |
| **Adatminőség** | Duplikált MMSI-k, hibás nevek, „ghost" hajók (a szárazföldi pozíciók) – a szárazföldi AIS-fantomok kiszűrése a katalógus minőségét közvetlenül meghatározza |
| **A lefedettség mérése** | Egyetlen vevő nem mutatja meg a teljes lefedettséget – **30 napos próbaüzem kell**, a számok pedig csak a tervezéshez valók, ha a végleges lefedettség több site-ot igényel |

> **Fontos gyakorlati részlet:** a szárazföldi (terrestrial) AIS-források **fantompozíciókat** is adnak – olyan hajókat, amelyek valójában nem a vízen vannak. A katalógusba beépülő hajók listáját ezért **pozíció-alapú szűréssel kell tisztítani** (víz felett, a folyó geometriáján belül), nem pusztán a statikus üzenet alapján. Ez egy külön szabály a pipeline-ban, és a nyers AIS-„flotta" mérete jóval nagyobb a valós flottánál.

---

## 9. Mit nem csinálunk R1-ben (és miért)

| Nincs | Miért |
|---|---|
| Térkép | a kérés szerint; R2 |
| Élő pozíció megjelenítése | R2 – de az adat **már R1-ben gyűjtődik** |
| ETA-modell | R4 – de az AIS-ból származó **ETA zsilipnél/terminálnál már R1-ben megvan** |
| Tulajdonjog, érték, ár | nem az adatbázis feladata |
| Személyzet, kapitány | GDPR – nem tároljuk |
| Bérlet, foglalás | nem az R1 célja |
| A bárkák önálló katalógusbejegyzése | a bárka nem AIS-entity; a konvoj tagjaként kezeljük |

---

## 10. A pipeline szabályai (v2.0)

| Szabály | |
|---|---|
| **A kulcs MMSI**, nem ENI | Az ENI hiányozhat; az MMSI soha. Az ENI elsődleges azonosító *ha van* |
| **Üres értéket soha nem töltünk ki találgatással** | Hiányzó mező = üres + `is_missing` jelölés |
| **Értéket soha nem törölünk felül üresre** | Az `origin` történet megőrzi az előző értéket |
| **A „ghost" hajók kiszűrése** | Pozícióalapú validáció (a folyó geometriáján belül) a statikus listában |
| **Idempotencia** | Az azonosító a kulcs; a feldolgozás újrafuttatható |
| **Nyers adat megőrzése** | A nyers AIS-üzenetek 14 napig, a statikus kivonatok korlátlan ideig a `data_source`-hoz kötve |
| **Minden mező eredete nyilvántartva** | `vessel_data_origin` |

---

## 11. Akciólista

| # | Feladat | Ki | Mikor |
|---|---|---|---|
| 1 | **AIS feed kiválasztása és megkötése** – 3 ajánlat bekérése (lefedettség, statikus adat, historikus, licenc, ár) | törzs | 1. hét |
| 2 | A feed próba-üzemeltetése a magyar Duna-szakaszon, lefedettség-mérés (milyen gyakran látszunk magyar hajót) | fejlesztés | 1–2. hét |
| 3 | AIS parser (Msg 5 + Inland FI 10) – prototípus | fejlesztés | 2. hét |
| 4 | Statikus gyűjtő indítása (a teljes R1-0 időszak alatt fut) | fejlesztés | 2. hét |
| 5 | **„Ghost"-szűrő** kialakítása és validálása a magyar szakaszon | fejlesztés | 3. hét |
| 6 | ENI → hajó, MMSI → hajó, hívójel → hajó illesztési logika + ütközéskezelés | fejlesztés | 3. hét |
| 7 | `vessel_data_origin` séma és a claim-űrlap (R1 végére) | fejlesztés | 4. hét |
| 8 | Port-km táblázat bevitele (Duna Bizottság) + kikötőrendek feldolgozása (Balaton) | tartalom | 2–3. hét |
| 9 | `river_section` kódok leképezése a fairway section kódokra | fejlesztés + tartalom | 3–4. hét |
| 10 | UN/LOCODE kikötőlista bevitele + ellenőrzés | tartalom | 3. hét |

---

## 12. Forráshivatkozások

- Commission Implementing Regulation (EU) 2019/838 – belvízi AIS technikai specifikáció, **Inland FI 10 (ENI, ERI-típus, fairway km, UN/LOCODE, ETA zsilipnél)** – [EUR-Lex](https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32019R0838&rid=5) · [legislation.gov.uk melléklet](https://www.legislation.gov.uk/eur/2019/838/annex/division/3/data.xht)
- Commission Regulation (EC) No 415/2007 – belvízi elektronikus hajójelentés, az Inland FI 10 és az ERI-hajótípus kódok – [EUR-Lex](https://eur-lex.europa.eu/eli/reg/2007/415/2012-08-17/eng)
- AIS Message 5 mezőleírás – [USCG NAVCEN](https://navcen.uscg.gov/ais-class-a-static-voyage-message-5)
- ITU-R M.585 – MMSI szerkezet és MID-értékek – [ITU](https://www.itu.int/en/ITU-R/terrestrial/Pages/by-categories-faq.aspx?categorizedby=17)
- Danube Commission – a Duna km-számlálása (Sulina 0), szakaszhatárok (2414,72 / 1791 / 931), **RNW** definíciója, kikötőtávolság-táblázat – [Danube Commission](http://www.danubecommission.org/extranet/e-library/publication/KM_ANZEIGER/HTML/ALLGEMEINES1.htm)
- WSV Streckenatlas Donau – „Die Kilometrierung beginnt an der Donaumündung (Hafen von Sulina) und steigt stromaufwärts" – [WSV](https://www.gdws.wsv.bund.de/SharedDocs/Downloads/DE/Karten/Streckenatlas/Streckenatlas_Donau.pdf)
- Közlekedési Hatóság – Balatoni tájékoztatók és kikötőrendek (publikált) – [KH](https://www.kozlekedesihatosag.kormany.hu/hu/dokumentumtar?delta=60&start=22&category=66908&modified=past-year)
- BAHART hajóflotta, Balatonmáriafürdő menetrend – [bahart.hu](https://bahart.hu/hu/bahart-hajoflotta) · [menetrend](https://www.balatonmariafurdo.hu/wp-content/uploads/2025/03/BH_Menetrend_kiadvany_2024.pdf)
