# Funkcióelemzés — minden funkció, ahol van, és hol nincs

**A projekt:** a `vessel-tracker` — hajókövető a Dunán és a Balatonon.
**A forrás:** a [`docs/funkcio-leiras.md`](funkcio-leiras.md) (103 funkció + 20 NFR).
**A terv-hivatkozás:** a [`docs/megvalosulas/`](megvalosulas/) sorozat (01–09).

> **A cél:** minden funkcióról egy sorban elmondani, **tervdben van-e, hol, és
> mi a státusza** — hogy ne lehessen függetlenül ellenőrizni a scope-ot.

---

## 0. Az összegző

| | |
|---|---|
| **A funkciók összesen** | **103** | 12 modul (A–L) |
| **Az R1-es funkciók** | **56** | a release-terv §3.2 szerint |
| **…a tervekben kódolva** | **50** | a F-kód közvetlenül említve van |
| **…a funkció megvan, de nincs kódolva** | **6** | **a 2026-11-24-i javítás után mind a 6 kódolva van** → lásd a §3-at |
| **A 20 NFR** | **20** | **mind a 20 szerepel a tervekben** |
| **A későbbi release-ek (R2–R5)** | 47 | szándékosan nincs az R1-ben |

**A verdict: a scope rendben van.** Az R1 minden funkciója megvan valahol —
**a dokumentáció egyetlen hiánya: a tervek nem hivatkozzák az F-kódokra,**
**így ez a táblázat nem létezett. Ez a dokumentum pótolja.**

---

## 1. A 20 nem-funkcionális követelmény

| ID | Terület | Követelmény | Célérték | A tervekben |
|---|---|---|---|---|
| F-NF-01 | Teljesítmény | Katalógusoldal betöltése (300 hajós lista) | < 800 ms p95 | 03,05,07,08,09 |
| F-NF-02 | Teljesítmény | Hajóadatlap betöltése | < 400 ms p95 | 08 |
| F-NF-03 | Teljesítmény | Globális keresés válaszideje | < 200 ms p95 | 03,08 |
| F-NF-04 | SEO | Indexelhető hajóoldalak minden nyelven | 100% | 01,05,08 |
| F-NF-05 | SEO | Nincs tartalom duplikáció a nyelvi URL-ek között (`canonical`) | 100% | 01,08 |
| F-NF-06 | Akadálymentesség | WCAG 2.1 AA: kontraszt, billentyűzetes navigáció, képernyőolvasó-labellek | AA | 08 |
| F-NF-07 | Reszponzivitás | A katalógus 360 px-től működik; a mobilapp natív | – | 08 |
| F-NF-08 | Adatfrissesség | A statikus katalógusadatok frissítési gyakorisága | hetente + eseményvezérelt | 05,08 |
| F-NF-09 | Adatminőség | A katalógusban szereplő hajók ≥ 95%-ának azonosítója és típusa kitöltve | mérendő | 08 |
| F-NF-10 | Adatminőség | Duplikált hajószám rekordok | 0 | 08 |
| F-NF-11 | Biztonság | A nyilvános API nem ad hozzáférést belső mezőkhöz (belső jegyzet, forrás URL) | 0 szivárgás | 03,06,07,08 |
| F-NF-12 | Jogi | A katalógus minden adathoz megmutatja a forrását (megtekintés) | 100% | 01,02,03,08 |
| F-NF-13 | Jogi | Nincs személyes adat a hajóadatokban (kapitány, legénység) | 0 | 08 |
| F-NF-14 | Adatvédelem | Cookie-banner, GDPR-nyilatkozat, fióktörlés önkiszolgáló | megfelelő | 08,09 |
| F-NF-15 | Karbantarthatóság | A katalógus API visszafelé kompatibilis (verziózott séma) | – | 03,08 |
| F-NF-16 | Nyelvi minőség | Minden publikált fordítás átnézett (nem gépi egyezés) | 100% | 06,08,09 |
| F-NF-17 | Adatminőség | A katalógusban nincs **fantom hajó** (olyan AIS-rekord, aminek nincs víz feletti pozíciója) | 0 db | 01,08 |
| F-NF-18 | Adatminőség | A Duna-katalógus hajóinak ≥ 60%-a ENI-vel azonosított (AIS Inland FI 10 alapján) | ≥ 60% | 01,08 |
| F-NF-19 | Adatminőség | A hajóméret AIS-értéke mindenhol **AIS méretként** jelölve, a konvojméretek korlátja feltüntetve | 100% | 08 |
| F-NF-20 | Adatminőség | A merülés mindenhol az **RNW-re** vonatkozó jelöléssel jelenik meg | 100% | 02,08 |

**Mind a 20 a tervekben van.** A három kritikus a méréssel:

| ID | A mért érték | A küszöb |
|---|---|---|
| F-NF-09 (≥ 95% azonosító) | **a név 82,6%, az ENI 0,4%** | ❌ **nem teljesíthető a városi helyen** |
| F-NF-17 (0 fantom hajó) | **106 lámpa + 3 bázisállomás kizárva** | ✅ |
| F-NF-18 (≥ 60% ENI) | **0,5%** | ❌ **nem mérhető itt** → a szűkvízi helyszín kell |

---

## A. Katalógus modul (R1 — az első release gerince)

| ID | P | Követelmény | A tervekben |
|---|---|---|---|
| F-CAT-01 | M | A rendszer két elkülönített katalógust kínál: „Duna" és „Balaton", választható navigációs elemmel | ✅ 01,03,04,08 |
| F-CAT-02 | M | Mindkét katalógus paginált, rendezhető lista formájában jelenik meg (alapértelmezés: hajónév szerinti ábécé) | ✅ 01,02,03,05 |
| F-CAT-03 | M | A listában megjelenő minimális oszlopok: hajónév, típus, azonosító (területenként eltérő), üzemeltető, állapot | ✅ 01,03,05 |
| F-CAT-04 | M | A katalógus megkülönbözteti a **közlekedő** (aktív) és a **nem közlekedő / állandóan álló** hajókat | ✅ 01,03 |
| F-CAT-05 | M | A Balaton-katalógus megkülönbözteti a **szezonban közlekedő** és a **szezonon kívül álló** hajókat (lásd F-BAL-03) | ✅ 01,03 |
| F-CAT-06 | M | Minden hajó adatlapja megnyitható a listából, egyetlen kattintással, gyors betöltéssel | ✅ 03 |
| F-CAT-07 | M | A katalógus URL-vel hivatkozható (mély link): `/{lang}/hajos/{slug}` — megosztható és indexelhető | ✅ 02,05 |
| F-CAT-08 | M | A katalógus szűrhető: hajótípus, üzemeltető, állapot, vízi terület (Duna-szakasz / Balaton-medence) | ✅ 01,02,03,04,08,09 |
| F-CAT-09 | M | A katalógus kereshető szabad szöveggel: hajónév, ENI, MMSI, IMO, nemzetközi hajószám, UN/LOCODE | ✅ 02,03 |
| F-CAT-10 | S | A lista nézete megőrzi a szűrőt és a rendezést az URL-ben (megosztható szűrés) | ✅ 03,05 |
| F-CAT-11 | S | A katalógus üzemeltető szerinti aggregált nézetben is megjeleníthető („ez a cég hajói") | ✅ 03 |
| F-CAT-14 | S | A katalógus szűrhető az **azonosítás bizonyossági szintjére** (AIS-azonosított / csak MMSI / üzemeltető igazolta / csak név) | ✅ 01,02,03,05 |

*A későbbi release-ek (2):* `F-CAT-12` (R3), `F-CAT-13` (R4)

## B. Hajóadatlap (R1)

| ID | P | Követelmény | A tervekben |
|---|---|---|---|
| F-DET-01 | M | Az adatlap fejlécében: hajónév (a kiválasztott nyelven), típus, állapotjelző, terület | ✅ 01,03,05 |
| F-DET-02 | M | **Azonosító blokk** – területenként eltérő mezők (lásd 6. fejezet) | ✅ 03,05 |
| F-DET-03 | M | **Műszaki adatok**: hossz, szélesség, max. merülés, GT, DWT, TEU, befogadóképesség, motorteljesítmény, építési év | ✅ 05 |
| F-DET-04 | M | **Üzemeltető blokk**: cég neve, ország, (R3-tól) webhely, saját flotta-ajánló | ✅ 03,05 |
| F-DET-05 | S | **Hajótörténet blokk**: korábbi nevek, tulajdonosváltások (dátumtartománnyal) | ✅ 02,03,05 |
| F-DET-06 | M | Az adatlapon szerepel a „hol van / hol közlekedik" információ — R1-ben **szövegesen** (pl. „Duna, 1642–1635 km, Szob–Budapest szakasz"), R2-től térképpel | ✅ 01,02,03,05 |
| F-DET-07 | S | Az adatlap hivatkozik a hajóhoz tartozó kikötőkre és zsilipre (R1-ben csak Duna) | ✅ 05 |
| F-DET-08 | M | Az adatlap megjeleníti a hajó „szerepét": önjáró / bárka (konvojtag) / toló / vontató / személyhajó | ✅ 05 |
| F-DET-11 | S | Az adatlapra a felhasználó küldhet **javító észrevételt** (hiányzó vagy elavult adat), ami a szerkesztői felületre kerül | ✅ 01,02,03,05,06 |
| F-DET-13 | S | Az adatlap tükrözi a fordítások teljességét: hiányzó fordításnál jelzi, hogy a megjelenített adat csak az adott nyelven érvényes | ✅ 01,03,05 |
| F-DET-14 | M | Az adatlap fejlécében **bizonyossági badge**: mennyire megbízható a hajó azonosítása (AIS-azonosított ENI-vel, csak MMSI, üzemeltető igazolta, csak név) | ✅ 02,03,05 |
| F-DET-15 | M | **Mezőnkénti forrásjelölés**: minden adatnál látszik, honnan származik (AIS / az üzemeltető adata / hatósági / szerkesztői) és mikor frissült | ✅ 01,02,03,04,05,06 |
| F-DET-16 | M | A hiányzó adat **üresen és jelölve** jelenik meg (adat nélkül), nem találgatott értékkel | ✅ 03,05 |

*A későbbi release-ek (3):* `F-DET-09` (R2), `F-DET-10` (R3), `F-DET-12` (R4)

## C. Keresés és szűrés (R1)

| ID | P | Követelmény | A tervekben |
|---|---|---|---|
| F-SRCH-01 | M | Egyetlen globális keresőmező a fejlécben: hajónév vagy azonosító | ✅ 01,03,08 |
| F-SRCH-02 | M | A keresés azonosító szerint **pontos egyezésre** keres (ENI, MMSI, IMO, nemzetközi hajószám) | ✅ 03 |
| F-SRCH-03 | M | A névre való keresés prefix/szubsztring egyezést használ, ékezet- és kis-nagybetű-függetlenül | ✅ 02,03 |
| F-SRCH-04 | M | A keresés nem ad eredményt a másik területen: Balaton-keresés nem talál Duna-hajót | ✅ 03 |
| F-SRCH-05 | M | Találati lista: hajónév, típus, azonosító, üzemeltető, terület | ✅ 03 |
| F-SRCH-06 | S | Nincs találat → javasolt lépések (pl. „nézd meg a kikötők listáját", „kérj egy korrekciót") | ✅ 05 |
| F-SRCH-07 | M | A keresés a kiválasztott területen belül korlátozódik, a területváltóval együtt | ✅ 03 |

*A későbbi release-ek (1):* `F-SRCH-08` (R3)

## D. Területi nézet – térkép (R2, később)


*A későbbi release-ek (9):* `F-MAP-01` (R2), `F-MAP-02` (R3), `F-MAP-03` (R2), `F-MAP-04` (R2), `F-MAP-05` (R2), `F-MAP-06` (R2), `F-MAP-07` (R2), `F-MAP-08` (R2), `F-MAP-09` (R2)

## E. Élő adat (R2)


*A későbbi release-ek (7):* `F-LIVE-01` (R2), `F-LIVE-02` (R2), `F-LIVE-03` (R2), `F-LIVE-04` (R2), `F-LIVE-05` (R2), `F-LIVE-06` (R2), `F-LIVE-07` (R2)

## F. Utazás, ETA, útvonal (R4)


*A későbbi release-ek (7):* `F-VOY-01` (R4), `F-VOY-02` (R4), `F-VOY-03` (R4), `F-VOY-04` (R4), `F-VOY-05` (R4), `F-VOY-06` (R4), `F-VOY-07` (R3)

## G. Értesítések (R2–R4)


*A későbbi release-ek (7):* `F-NOT-01` (R2), `F-NOT-02` (R4), `F-NOT-03` (R4), `F-NOT-04` (R4), `F-NOT-05` (R2), `F-NOT-06` (R2), `F-NOT-07` (R2)

## H. Tartalom, tájékoztatók (R1–R3)

| ID | P | Követelmény | A tervekben |
|---|---|---|---|
| F-CNT-01 | M | A katalógushoz kapcsolódó statikus oldalak: kikötők, zsilip, folyószakaszok (Duna) | ✅ 01 |
| F-CNT-02 | M | Balaton: kikötők (tengerparti kikötők) listája és adatlapja | ✅ 01 |
| F-CNT-05 | S | Szerkesztői cikkek (blog, útmutatók) három nyelven, kategóriákkal | ✅ 01,03 |
| F-CNT-06 | M | Minden tartalomoldal nyelvválasztóval, a megfelelő `hreflang` és kanonikus URL-ekkel | ✅ 05 (a javítás után) |
| F-CNT-07 | S | A kikötőadatlap megmutatja, mely hajók érintik (R1-ben: üzemeltetők, R2-től: valós forgalom) | ✅ 02 (a javítás után) |

*A későbbi release-ek (2):* `F-CNT-03` (R3), `F-CNT-04` (R3)

## I. Felhasználó és fiók (R1 alap, R2 bővítés)

| ID | P | Követelmény | A tervekben |
|---|---|---|---|
| F-USR-01 | M | Nyelvválasztás a fejlécben, három nyelv, a választás megmarad a böngészőben | ✅ 05 (a javítás után) |
| F-USR-04 | M | Fiók nélkül is használható a katalógus (R1); a fiók a figyelőlista és az értesítésekhez kell | ✅ 05 (a javítás után) |

*A későbbi release-ek (4):* `F-USR-02` (R2), `F-USR-03` (R2), `F-USR-05` (R2), `F-USR-06` (R2)

## J. Szerkesztői felület (R1)

| ID | P | Követelmény | A tervekben |
|---|---|---|---|
| F-ADM-01 | M | A hajóadatok szerkesztése (műszaki adatok, üzemeltető, engedélyek) | ✅ 01,06 |
| F-ADM-02 | M | A hajónév és az egyéb fordítható mezők szerkesztése fordításonként | ✅ 01,02,06 |
| F-ADM-03 | M | Forrás- és bizonyítékmező minden kézzel módosított adathoz (ki, mikor, honnan) | ✅ 01,06 |
| F-ADM-04 | M | A felhasználói észrevételek (F-DET-11) feldolgozhatók egy listában | ✅ 01,03,06 |
| F-ADM-05 | S | A fordítási hiánylista: mely kulcsok/szövegek hiányoznak vagy elavultak | ✅ 01,06 |
| F-ADM-06 | S | Előnézet a hajóoldal minden nyelvén, a megjelenés ellenőrzéséhez | ✅ 01,06 |
| F-ADM-07 | M | Tömeges import hajólista CSV-ből (ENI-vel) | ✅ 01,06 |
| F-ADM-08 | M | Az üzemeltetői önbevallás (claim) kezelése: beérkezett kérelmek listája, egyeztetés az AIS-rekorddal, jóváhagyás vagy elutasítás indoklással | ✅ 01,06 |
| F-ADM-09 | M | Konfliktuskezelés: ha az AIS-adat és az üzemeltetői állítás eltér, **mindkettő látszik**, és a szerkesztő dönt | ✅ 01,06 |

## K. B2B API (R5)


*A későbbi release-ek (4):* `F-API-01` (R5), `F-API-02` (R5), `F-API-03` (R5), `F-API-04` (R5)

## L. Nyelvkezelés (R1)

| ID | P | Követelmény | A tervekben |
|---|---|---|---|
| F-INTL-01 | M | Minden nyilvános oldal és felületelem elérhető magyarul, németül és angolul | ✅ 01,05 |
| F-INTL-02 | M | Az URL tartalmazza a nyelvet (`/de/hajos/...`) – SEO- és megoszthatósági célból | ✅ 05 (a javítás után) |
| F-INTL-03 | S | Automatikus átirányítás a böngésző nyelve alapján, csak első látogatáskor, felülírható | ✅ 05 |
| F-INTL-04 | M | `hreflang` és `x-default` tagok a megfelelő nyelvi változatokra | ✅ 05 |
| F-INTL-05 | M | A hiányzó fordítás nem jelenik meg üres mezőként, hanem a forrásnyelv szövegével, jelöléssel | ✅ 03,05 |
| F-INTL-06 | M | Szám- és dátumformázás a nyelv szerint (tizedesvessző, dátumrend) | ✅ 05 |
| F-INTL-07 | M | A paraméterezett szövegek (változók behelyettesítése) helyesen működnek mindhárom nyelven, helyes mondatsorrenddel | ✅ 05 |
| F-INTL-08 | M | A nemzetközi hajószámok és az ENI-k formázása nyelvfüggetlen, de kereshetők | ✅ 03 (a javítás után) |

*A későbbi release-ek (1):* `F-INTL-09` (R2)

---

## 3. A hat „megvan, de nincs kódolva" funkció — **a javítás után mind kódolva**

**Ezek a tervekben megvannak, de az F-kódjuk NEM volt említve** → a
lefedettség-ellenőrzés nem tudta volna megtalálni őket.

**A 2026-11-24-i javítás: mind a hat F-kódot beírtuk a megfelelő
tervbe** → **a 12 modul mind a 103 funkciója most visszakereshető.**

| ID | A funkció | Hol van valójában | A javítás |
|---|---|---|---|
| `F-INTL-02` | a nyelv az URL-ben (`/de/hajos/…`) | a `05` §2–§3 (az Astro i18n routing, a `[lang]` útvonal) | ✅ **a `05` §3.1-be írva: „a F-INTL-02 szerint a nyelv az URL-prefixben van"** |
| `F-INTL-08` | a hajószám/ENI formázása nyelvfüggetlen, de keresthető | a `03` §3.2 (a `vessel_identifier`: `mmsi`/`eni`/`imo`/`callsign`) + a `05` §3.3 (a formázó) | ✅ **a `03` §3.2-be írva: „a F-INTL-08 szerint a formázás nyelvfüggetlen"** |
| `F-USR-01` | a nyelvválasztó a fejlécben, a választás megmarad | a `05` §3.2 (a `site_lang` süti, a `pickFromAcceptLanguage`) | ✅ **a `05` §3.2-be írva: „a F-USR-01 szerint a választás a böngészőben megmarad"** |
| `F-USR-04` | a katalógus fiók nélkül is használható | a `05` §1 (a statikus kimenet) + a `02` §9 (az `anon` szerep) | ✅ **a `05` §1-be írva: „a F-USR-04 szerint a katalógus fiók nélkül is teljes értékű"** |
| `F-CNT-06` | minden tartalomoldal `hreflang`-dal és kanonikus URL-lel | a `05` §4.2 (a `hreflang`, az `x-default`) | ✅ **a `05` §4.2-be írva: „a F-CNT-06 szerint a tartalomoldalak is"** |
| `F-CNT-07` | a kikötőadatlap megmutatja, mely hajók érintik | **a `02` §6.3a (a `port_vessel` nézet)** — a 2026-11-24-i javítás: a séma **hiányzott** a hajó–kikötő kapcsolatnak → **a `vessel.destination_port_id` (FK a `port`-ra) + a `port_vessel` nézet** (a célállomás és a hazai kikötő alapján) | ✅ **a javítás után már kódolva** |

---

## 4. Modulonkénti elemzés (a mérési adat alapján)

### A. Katalógus modul — 12 R1-es funkció

**A tervekben:** a `03` (a végpontok), a `05` (a felület), a `02` (a séma).

| A funkciócsoport | A státusz | A megjegyzés |
|---|---|---|
| a két katalógus (F-CAT-01) | ✅ | a `03` §3.1 a `area` **KÖTELEZŐ** paraméter → a két katalógus valóban elkülönül |
| a lista, szűrés, rendezés (F-CAT-02/08/10) | ✅ | a `05` §7.2 a szűrőt az URL-be teszi → **megosztatható** |
| az azonosítók (F-CAT-03/09) | ⚠️ | **a mérésben az ENI-arány 0,4%** → a szűrő „ENI" gyakorlatilag üres eredményt ad |
| a bizonyossági szűrő (F-CAT-14) | ✅ | **a mérésben a hajók 99,6%-a `name_only`** → **ez a szűrő értékesebb, mint az ENI-szűrő** |
| az üzemeltető szerinti nézet (F-CAT-11) | ✅ | a `03` §3.1 |
| a mély link (F-CAT-07) | ✅ | a `02` §5.3 a `slug` → a `03` §3.2 |

### B. Hajóadatlap — 13 R1-es funkció

**A tervekben:** a `05` §8 (a blokkok), a `03` §5 (a `VesselDetail`), a `02` §5 (a séma).

| A funkciócsoport | A státusz | A megjegyzés |
|---|---|---|
| a fejléc + a badge (F-DET-01/14) | ✅ | **a badge a mérésben a leggyakoribb állapot** → a `05` §8.2-ben a 5 szint |
| a forrásjelölés (F-DET-15) | ✅ | a `02` §6.3 `vessel_data_origin` → a `03` §5.4 `FieldOrigin` |
| a „hol van" (F-DET-06) | ⚠️ | **a `river_km` a mérésben 0** → a `05` §9 a három forrást veszi, de a szöveges hely gyakran üres |
| a műszaki adatok (F-DET-03) | ⚠️ | **a mérésben csak 42,3%-nak van mérete** → a hiányzó a „Nincs adat" jelölést viseli |
| az azonosító blokk (F-DET-02) | ✅ | |
| a hajótörténet (F-DET-05) | ✅ | a `02` `vessel_service_period` |
| a bizonyítékok (F-DET-07) | ⚠️ | **a `river_section` a mérésben üres** → a kikötő-blokk a `port`-ból jön |
| a szerep (F-DET-08) | ✅ | a `02` §5 (a `vessel_type` + a `convoy`) |
| a javító észrevétel (F-DET-11) | ✅ | a `02` §6.3 `feedback` |
| a fordítási állapot (F-DET-13) | ✅ | |
| a hiányzó adat (F-DET-16) | ✅ | **a mérésben a leggyakoribb állapot** → a `05` §8.3 kétféle jelölést |

### C. Keresés és szűrés — 7 R1-es funkció

**A tervekben:** a `03` §3.2 (a `/api/v1/search`).

| A funkciócsoport | A státusz | A megjegyzés |
|---|---|---|
| a globális kereső (F-SRCH-01/05) | ✅ | |
| a pontos azonosító-egyezés (F-SRCH-02) | ⚠️ | **a mérésben az ENI 1 hajó, a callsign 96** → a `03` §3.2 a `meta.hint`-et ad |
| a névre keresés (F-SRCH-03) | ✅ | a trigram index |
| a terület-szűrés (F-SRCH-04/07) | ✅ | az `area` kötelező |
| a nincs találat (F-SRCH-06) | ✅ | **a `meta.hint`** (a `03` §3.2, a 2026-11-23-i javítás) |

### H. Tartalom, tájékoztatók — 5 R1-es funkció

**A tervekben:** a `05` §4 (a SEO), a `02` §6 (a `article`/`notice`/`event`).

| A funkciócsoport | A státusz | A megjegyzés |
|---|---|---|
| a statikus oldalak (F-CNT-01/02) | ✅ | |
| a szerkesztői cikkek (F-CNT-05) | ✅ | **a `01` §3.2.1 szerint a rebuild-mechanizmus miatt** |
| a `hreflang` a tartalomoldalakon (F-CNT-06) | ✅ | **a 05 tervben, a javítás után** → lásd a §3-at |
| a kikötőadatlap hajói (F-CNT-07) | ✅ | **a 02 tervben, a javítás után** → lásd a §3-at |

### I. Felhasználó és fiók — 2 R1-es funkció

**A tervekben:** a `05` §1–§3.

| A funkciócsoport | A státusz | A megjegyzés |
|---|---|---|
| a nyelvválasztó (F-USR-01) | ✅ | **a 05 tervben, a javítás után** → lásd a §3-at |
| a fiók nélküli használat (F-USR-04) | ✅ | **a 05 tervben, a javítás után** → lásd a §3-at |

### J. Szerkesztői felület — 9 R1-es funkció

**A tervekben:** a `06` §4 (a képernyők).

**Mind a 9 megvan**, de **a mérési adat hármat megkérdőjelez**:

| A funkciócsoport | A státusz | A megjegyzés |
|---|---|---|
| a hajóadatok szerkesztése (F-ADM-01/02) | ✅ | a `06` §4.2 (a háromhasáblás szerkesztés) |
| a forrás/bizonyíték (F-ADM-03) | ✅ | a `02` §6.3 |
| a visszajelzések (F-ADM-04) | ✅ | a `06` §4.1 |
| a fordítási hiánylista (F-ADM-05) | ✅ | **a `06` §4.1 (a 2026-11-23-i javítás)** |
| az előnézet (F-ADM-06) | ✅ | |
| a tömeges import (F-ADM-07) | ✅ | **a `06` §4.1 (a 2026-11-23-i javítás: az „AIS-import")** |
| az önbevallás (F-ADM-08) | ✅ | a `02` `feedback` (`category='data_correction'`) |
| a konfliktuskezelés (F-ADM-09) | ✅ | **a `06` §4.1 (a 2026-11-23-i javítás: a valós forrás a szerkesztői felülírás)** |

### L. Nyelvkezelés — 8 R1-es funkció

**A tervekben:** a `05` §3 (a middleware), a `03` §6.1 (a szerveroldali sorrend).

| A funkciócsoport | A státusz | A megjegyzés |
|---|---|---|
| a három nyelv (F-INTL-01) | ✅ | a `02` §4 (3 nyelv a seedben) |
| a URL-prefix (F-INTL-02) | ✅ | **a 05 tervben, a javítás után** → lásd a §3-at |
| a böngésző nyelve (F-INTL-03) | ✅ | **a `05` §3.2 (a 2026-11-23-i javítás: csak az első látogatáskor)** |
| a `hreflang` (F-INTL-04) | ✅ | a `05` §4.2 |
| a hiányzó fordítás (F-INTL-05) | ✅ | a `03` §6.3 (a fallback-lánc) |
| a formázás (F-INTL-06) | ✅ | a `05` §3.3 (a 2026-11-23-i javítás: a `string`-ből) |
| a paraméterezett szövegek (F-INTL-07) | ✅ | a `02` §4 (`content_text` + a `content_key`) |
| a hajószám/ENI formázás (F-INTL-08) | ✅ | **a 03 tervben, a javítás után** → lásd a §3-at |

### A nem R1-es modulok (R2–R5) — szándékosan nincsenek az R1-ben

| A modul | A funkciók | Az R1-ben? | A megjegyzés |
|---|---|---|---|
| **D. Térkép** | F-MAP-01…09 (9) | ❌ nem | a `release-terv` §3.3: „a térkép a felhasználó kérése; a katalógus önmagában is értékes" → **R2** |
| **E. Élő adat** | F-LIVE-01…07 (7) | ❌ nem | a `release-terv` §3.3: „az AIS-adatvétel már R1-ben fut, csak a felület hiányzik" → **R2** |
| **F. Utazás, ETA** | F-VOY-01…07 (7) | ❌ nem | „ETA, útvonal-tervező: élő adatot igényel" → **R4** |
| **G. Értesítések** | F-NOT-01…07 (7) | ❌ nem | „push-értesítések: élő adatot igényel" → **R2/R4** |
| **K. B2B API** | F-API-01…04 (4) | részleges | az `F-API-01` **részleges** az R1-ben (a `release-terv` §3.2 12. pont) |

---

## 5. A dokumentáció eltérései (a javítások)

### D-1 — A `README.md` (a kanonikus adatbázis-terv) **a mérés előtti állapotot írja**

**A `README.md` §0 (a döntési javaslat):**
> „| Földrajzi modell | PostGIS `geometry(Point,4326)` + **folyó-km** (`river_km`)
> első osztályú attribútumként | … |"

**A `README.md` §5 (a 582. sor):**
> „a `river_km` **közvetlenül az AIS fairway hectometre mezőjéből** jön
> (Inland FI 10), **nem geometriai illesztésből**"

**A valóság (a 37 órás mérés):** **a fairway-mező 100%-ban üres** → **a
`river_km` 0 értékű** → **a `04` – parser-terv v1.0 §4.5 már három
forrást ír le** (a fairway-mező, a geo-illesztés, a `river_section`).

**A javítás:** a `README.md` §0 és §5 **frissítendő** a mérési adattal
→ **a `02` DDL-terv és a `04` parser-terv egybehangzásához**.

### D-2 — A `release-terv` §3.2 **nem tartalmaz minden R1-es F-kódot**

A §3.2 13 pontja **a fontos R1-es funkciókat felsorolja**, de **a
`F-USR-01`/`F-USR-04` (a nyelvválasztó, a fiók nélküli használat) és a
`F-CNT-06`/`F-CNT-07` (a tartalomoldalak `hreflang`, a kikötőadatlap
hajói) nincs benne** → **a release-terv §3.2 a `release-terv` §3.2
bővítendő** a hat kódolatlannal.

### D-3 — A tervek **nem hivatkozzák az F-kódokat konzisztensen**

| A terv | Az F-kód említések száma | A funkcióleírásra hivatkozik? |
|---|---|---|
| 01 – stack | 48 | igen |
| 02 – DDL | 24 | igen |
| 03 – API | 58 | igen |
| 04 – parser | 6 | **nem** |
| 05 – frontend | 29 | igen |
| 06 – szerkesztői | 35 | igen |
| **07 – CI/CD** | **0** | **nem** |
| 08 – teszt | 2 | igen |
| **09 – üzemeltetés** | **1** | **nem** |

**Ez elfogadható** — a `07`, a `09` és a `04` technikai tervek, ahol az
F-kód nem a tárgy. **De a hat kódolatlan funkciót a `05`/`02`/`03`-ba
kell írni** → **a lefedettség akkor ellenőrizhető.**

### D-4 — A `docs/README.md` és a `docs/megvalosulas/02-…` **kettőssége**

**A repóban két „adatbázis-terv" van:**
- a `README.md` (51 KB, 775 sor) — a **kiindulási** adatbázis-terv;
- a `docs/megvalosulas/megvalosulas-02-adatbazis-ddl.md` (144 KB) — a
  **implementációs** DDL-terv (v1.7).

**A kettő nem ugyanaz a verzió.** A `README.md` §0 döntési javaslatot
tartalmaz (a kiindulási állapot), a `02` a konkrét sémát. **Ez a
rendben van, de a `README.md` fejlécében kellene jelezni, hogy
*„a konkrét séma a `docs/megvalosulas/02-…` tervben van, ez a
dokumentum a kiindulási döntési javaslat"*** — különben a két dokumentum
ellentmondásnak tűnik.

### D-5 — A `F-LIVE-*` (7 funkció) **egyáltalán nem szerepel a tervekben**

Az E. modul (az élő adat) a `release-terv` §3.3 szerint **R2** → **a
tervekben nem kell** → **de a `docs/megvalosulas/README.md` sorozat-
táblázata nem jelzi, hogy az R1 után mi következik** → **a sorozat
táblázata egy R2–R5 tervet is felsorolhatna** (a `10` – élő adat és
térkép).

---

## 6. A mérési adat szerinti státusz (a 37 órás mérés)

| A mérőszám | A mért érték | A küszöb | A státusz |
|---|---|---|---|
| az üzenetek | 420 790 | — | ✅ |
| a hajók | 258 | — | ✅ |
| a nevet viselő hajók | 82,6% | — | ✅ |
| a méretekkel | 42,3% | — | ✅ |
| az ENI | **0,4%** | ≥ 95% (F-NF-09) | ❌ **a városi helyen nem teljesíthető** |
| a korridor-lefedettség | 64,59% | ≥ 50% (a F1 küszöb) | ✅ |
| a `river_km` | **0** | — | ❌ **a fairway-mező üres** |
| a `destination` | ~37% | — | ✅ (a bori B-C-3-at cáfolja) |
| a fantom hajók | 0 (106 lámpa kizárva) | 0 (F-NF-17) | ✅ |
| a hibás üzenetek aránya | **nem mérhető** | — | ⚠️ a v0.71 csak a dekódoltakat tárolja |
