# Funkcióleírás – Dunai hajókövető és Balatoni hajókatalógus

**Verzió:** 1.0 (2026-11-14)
**Kapcsolódó dokumentumok:** [`../README.md`](../README.md) (adatbázis terv) · [`release-terv.md`](release-terv.md) (release terv) · [`sema-core.mmd`](sema-core.mmd) · [`sema-irodalom.mmd`](sema-irodalom.mmd)

---

## 1. A termék lényege

Két, egymástól **térben és adatmodellben is elkülönített** katalógus egy rendszerben:

| | **Duna-katalógus** | **Balatoni hajókatalógus** |
|---|---|---|
| Mi ez | A Duna (és mellékfolyói) nemzetközi és hazai hajóparkja | A Balaton-tó hajókatalógusa |
| Ki érdeklődik | Akit érdekelnek a hajók | Turista, Akit érdekelnek a hajók |
| Azonosítás | **ENI** (8 jegyű EU-s belvízi hajószám) | **Nemzetközi hajószám + nemzeti nyilvántartási szám** (nincs ENI) |
| Helyzethez kötött | Igen (folyó-km, szakasz, kikötő) | Igen, de **medence** (3 vízmedence) és **partkm** szerint |
| Éves ciklus | Egész év | **Szezonális** (tavasztól őszig) |
| Adatforrás | ENI-nyilvántartás, AIS, hajószám, Közlekedési Hatóság | Közlekedési Hatóság nyilvántartás, üzemeltetők, KH-hirdetmények |
| Katalógus mérete | ~3 500 regisztrált hajó | ~100 jelentős hajó + ~40–50 kishajó + több száz vitorlás |

**Elkülönítési alapelv:** a két katalógus *nem* egyetlen lista szűréssel. Külön navigáció, külön szűrőmezők, külön azonosítómezők, külön szezonlogika, külön adattáblák (a közös `vessel` tábla terület-diszcriminátorral és külön azonosító-táblával). A felhasználó sosem lát egységes „összes hajó" listát — a Duna és a Balaton más közlekedési valóság, más jogszabály, más szezon.

---

## 2. Célközönség és felhasználói szerepek

| Szerep | Igénye | Elsődleges felület |
|---|---|---|
| **Hajó érdeklődő** (hajótulajdonos, hajóügynök, turista, hobbista) | „Ki ez a hajó, milyen, ki üzemelteti, mekkora a kapacitása" | Web |
| **Szerkesztő (redakció)** | „Frissítsem a hajó adatait, a tájékoztatókat, a fordításokat" | Web (admin) |
| **Fejlesztő / B2B partner** | „Programozottan elérhető hajóadat" | API |

---

## 3. Amit a termék NEM tartalmaz

- Foglalási és fizetési rendszer (csak tájékoztató)
- Élő chat, értékelési rendszer (a visszajelzés R5-ben, korlátozottan)
- Hajóértékesítés / brokerage
- Személyzet-kezelés, HR, bérszámfejtés
- Navigációs berendezés vezérlése, rádióforgalom
- Verseny- és turisztikai programtervezés (R5 későbbi modul)

---

## 4. Funkcionális követelmények

Prioritás: **M** = kötelező (Must) · **S** = fontos (Should) · **L** = kívánatos (Could)

### 4.1 A. Katalógus modul (R1 — az első release gerince)

| ID | Követelmény | P | Release |
|---|---|---|---|
| F-CAT-01 | A rendszer két elkülönített katalógust kínál: „Duna" és „Balaton", választható navigációs elemmel | M | R1 |
| F-CAT-02 | Mindkét katalógus paginált, rendezhető lista formájában jelenik meg (alapértelmezés: hajónév szerinti ábécé) | M | R1 |
| F-CAT-03 | A listában megjelenő minimális oszlopok: hajónév, típus, azonosító (területenként eltérő), üzemeltető, állapot | M | R1 |
| F-CAT-04 | A katalógus megkülönbözteti a **közlekedő** (aktív) és a **nem közlekedő / állandóan álló** hajókat | M | R1 |
| F-CAT-05 | A Balaton-katalógus megkülönbözteti a **szezonban közlekedő** és a **szezonon kívül álló** hajókat (lásd F-BAL-03) | M | R1 |
| F-CAT-06 | Minden hajó adatlapja megnyitható a listából, egyetlen kattintással, gyors betöltéssel | M | R1 |
| F-CAT-07 | A katalógus URL-vel hivatkozható (mély link): `/{lang}/hajos/{slug}` — megosztható és indexelhető | M | R1 |
| F-CAT-08 | A katalógus szűrhető: hajótípus, üzemeltető, állapot, vízi terület (Duna-szakasz / Balaton-medence) | M | R1 |
| F-CAT-09 | A katalógus kereshető szabad szöveggel: hajónév, ENI, MMSI, IMO, nemzetközi hajószám, UN/LOCODE | M | R1 |
| F-CAT-10 | A lista nézete megőrzi a szűrőt és a rendezést az URL-ben (megosztható szűrés) | S | R1 |
| F-CAT-11 | A katalógus üzemeltető szerinti aggregált nézetben is megjeleníthető („ez a cég hajói") | S | R1 |
| F-CAT-12 | A katalógus exportálható (CSV) kiválasztott szűréssel | L | R3 |
| F-CAT-13 | A katalógus összehasonlító nézet: legfeljebb 3 hajó adatlapja egymás mellett | L | R4 |
| F-CAT-14 | A katalógus szűrhető az **azonosítás bizonyossági szintjére** (AIS-azonosított / csak MMSI / üzemeltető igazolta / csak név) | S | R1 |

### 4.2 B. Hajóadatlap (R1)

| ID | Követelmény | P | Release |
|---|---|---|---|
| F-DET-01 | Az adatlap fejlécében: hajónév (a kiválasztott nyelven), típus, állapotjelző, terület | M | R1 |
| F-DET-02 | **Azonosító blokk** – területenként eltérő mezők (lásd 6. fejezet) | M | R1 |
| F-DET-03 | **Műszaki adatok**: hossz, szélesség, max. merülés, GT, DWT, TEU, befogadóképesség, motorteljesítmény, építési év | M | R1 |
| F-DET-04 | **Üzemeltető blokk**: cég neve, ország, (R3-tól) webhely, saját flotta-ajánló | M | R1 |
| F-DET-05 | **Hajótörténet blokk**: korábbi nevek, tulajdonosváltások (dátumtartománnyal) | S | R1 |
| F-DET-06 | Az adatlapon szerepel a „hol van / hol közlekedik" információ — R1-ben **szövegesen** (pl. „Duna, 1642–1635 km, Szob–Budapest szakasz"), R2-től térképpel | M | R1 |
| F-DET-07 | Az adatlap hivatkozik a hajóhoz tartozó kikötőkre és zsilipre (R1-ben csak Duna) | S | R1 |
| F-DET-08 | Az adatlap megjeleníti a hajó „szerepét": önjáró / bárka (konvojtag) / toló / vontató / személyhajó | M | R1 |
| F-DET-09 | Ha a hajó bárka, az adatlap jelzi, hogy pozíciója a vezető hajótól származtatott (R2-től) | M | R2 |
| F-DET-10 | Az adatlap mutatja a közleményeket és eseményeket, amelyek a hajóhoz kapcsolódnak | S | R3 |
| F-DET-11 | Az adatlapra a felhasználó küldhet **javító észrevételt** (hiányzó vagy elavult adat), ami a szerkesztői felületre kerül | S | R1 |
| F-DET-12 | Az adatlap nyomtatható / PDF-ként menthető (szerkesztői felhasználás) | L | R4 |
| F-DET-13 | Az adatlap tükrözi a fordítások teljességét: hiányzó fordításnál jelzi, hogy a megjelenített adat csak az adott nyelven érvényes | S | R1 |
| F-DET-14 | Az adatlap fejlécében **bizonyossági badge**: mennyire megbízható a hajó azonosítása (AIS-azonosított ENI-vel, csak MMSI, üzemeltető igazolta, csak név) | M | R1 |
| F-DET-15 | **Mezőnkénti forrásjelölés**: minden adatnál látszik, honnan származik (AIS / az üzemeltető adata / hatósági / szerkesztői) és mikor frissült | M | R1 |
| F-DET-16 | A hiányzó adat **üresen és jelölve** jelenik meg (adat nélkül), nem találgatott értékkel | M | R1 |

### 4.3 C. Keresés és szűrés (R1)

| ID | Követelmény | P | Release |
|---|---|---|---|
| F-SRCH-01 | Egyetlen globális keresőmező a fejlécben: hajónév vagy azonosító | M | R1 |
| F-SRCH-02 | A keresés azonosító szerint **pontos egyezésre** keres (ENI, MMSI, IMO, nemzetközi hajószám) | M | R1 |
| F-SRCH-03 | A névre való keresés prefix/szubsztring egyezést használ, ékezet- és kis-nagybetű-függetlenül | M | R1 |
| F-SRCH-04 | A keresés nem ad eredményt a másik területen: Balaton-keresés nem talál Duna-hajót | M | R1 |
| F-SRCH-05 | Találati lista: hajónév, típus, azonosító, üzemeltető, terület | M | R1 |
| F-SRCH-06 | Nincs találat → javasolt lépések (pl. „nézd meg a kikötők listáját", „kérj egy korrekciót") | S | R1 |
| F-SRCH-07 | A keresés a kiválasztott területen belül korlátozódik, a területváltóval együtt | M | R1 |
| F-SRCH-08 | Billentyűzetes gyorskereső (cmd+K), a legutóbbi keresések memóriája | S | R3 |

### 4.4 D. Területi nézet – térkép (R2, később)

| ID | Követelmény | P | Release |
|---|---|---|---|
| F-MAP-01 | Térkép a Dunán, hajók élő pozíciójával | M | R2 |
| F-MAP-02 | Térkép a Balatonon, hajók élő pozíciójával (medence szerinti szűréssel) | M | R3 |
| F-MAP-03 | Térkép rétegek: hajók, kikötők, zsilip, folyó-km jelölők, vízállás-mérőállomások, események | M | R2 |
| F-MAP-04 | Kattintás a hajószimbólumra → oldalpanel a hajó adataival (nem új oldalra navigálva) | M | R2 |
| F-MAP-05 | Szűrés a térképen: hajótípus, mozgás (álló/mozgó), terület, „figyelt hajóim" | M | R2 |
| F-MAP-06 | Klaszterezés nagyobb hajószám esetén, zoom-szinttől függően | S | R2 |
| F-MAP-07 | Térkép- URL megőrzi a nézetet (központ, zoom, szűrők) | S | R2 |
| F-MAP-08 | Alacsony sávszélességnél (mobil) automatikus kisebb adatmennyiség | M | R2 |
| F-MAP-09 | Térképen a bárkák konvojként, halvány jelöléssel jelennek meg | M | R2 |

### 4.5 E. Élő adat (R2)

| ID | Követelmény | P | Release |
|---|---|---|---|
| F-LIVE-01 | Élő pozíció frissül a térképen legalább 30 másodpercenként | M | R2 |
| F-LIVE-02 | Minden hajószimbólum mutatja az utolsó frissítés korát | M | R2 |
| F-LIVE-03 | Elavult adat (> 15 perc) esetén a szimbólum „elavult" jelölést kap | M | R2 |
| F-LIVE-04 | A hajó sebessége, iránya (szöveg + nyíl) | M | R2 |
| F-LIVE-05 | A „figyelt hajóim" listám azonnal mutatja a legutóbbi pozíciót és az állapotot | M | R2 |
| F-LIVE-06 | Push értesítés a figyelt hajó elindulásakor / megállásakor | S | R2 |
| F-LIVE-07 | Adatfrissesség státusz kiemelve a felületen (működik / nincs adat / üzemeltetői hiba) | S | R2 |

### 4.6 F. Utazás, ETA, útvonal (R4)

| ID | Követelmény | P | Release |
|---|---|---|---|
| F-VOY-01 | A hajó adatlapján a folyamatban lévő vagy legutóbbi út (kikötőtől kikötőig) megjelenik | M | R4 |
| F-VOY-02 | Útvonal-tervező: indulási és érkezési kikötő + dátum → lehetséges hajók és várható idő | M | R4 |
| F-VOY-03 | Az ETA-nak konfidenciája és tartománya (korábbi–későbbi) látható, nem csak egy pont | M | R4 |
| F-VOY-04 | Zsilipvárakozás: a hajó várakozási ideje és a sor pozíciója | M | R4 |
| F-VOY-05 | Vízállás-korlát figyelmeztetés a tervezett útvonalon (szárazállás) | M | R4 |
| F-VOY-06 | Az útvonal-terv menthető és megosztható (link) | S | R4 |
| F-VOY-07 | A Balatoni menetrend (szezonális hajómenetrend) mint „terv" jelenik meg – külön, egyszerűbb modellel | S | R3 |

### 4.7 G. Értesítések (R2–R4)

| ID | Követelmény | P | Release |
|---|---|---|---|
| F-NOT-01 | Felhasználó kiválaszthat hajót (figyelőlista) és megadhatja az értesítés típusát | M | R2 |
| F-NOT-02 | Értesítés a célkikötőbe érkezésről (tervezett vs. tényleges) | M | R4 |
| F-NOT-03 | Értesítés késésről (a becsléshez képest) | S | R4 |
| F-NOT-04 | Értesítés vízállás-korlát esetén az útvonalon | S | R4 |
| F-NOT-05 | Az értesítések a felhasználó nyelvén, a választott csatornán (push / e-mail) | M | R2 |
| F-NOT-06 | Az értesítések összevonhatók (ne 25 külön push menjen egy hajó miatt) | M | R2 |
| F-NOT-07 | Az értesítés a szolgáltatás aktuális állapotát is tartalmazza (pl. „a pozíció 8 perce frissült") | S | R2 |

### 4.8 H. Tartalom, tájékoztatók (R1–R3)

| ID | Követelmény | P | Release |
|---|---|---|---|
| F-CNT-01 | A katalógushoz kapcsolódó statikus oldalak: kikötők, zsilip, folyószakaszok (Duna) | M | R1 |
| F-CNT-02 | Balaton: kikötők (tengerparti kikötők) listája és adatlapja | M | R1 |
| F-CNT-03 | Közlemények (Hajósoknak Szóló Tájékoztató, KH-hirdetmények) listája és részletei | S | R3 |
| F-CNT-04 | Események (zárás, korlátozás, vihar) listája, területenként szűrhető | S | R3 |
| F-CNT-05 | Szerkesztői cikkek (blog, útmutatók) három nyelven, kategóriákkal | S | R1 |
| F-CNT-06 | Minden tartalomoldal nyelvválasztóval, a megfelelő `hreflang` és kanonikus URL-ekkel | M | R1 |
| F-CNT-07 | A kikötőadatlap megmutatja, mely hajók érintik (R1-ben: üzemeltetők, R2-től: valós forgalom) | S | R1 |

### 4.9 I. Felhasználó és fiók (R1 alap, R2 bővítés)

| ID | Követelmény | P | Release |
|---|---|---|---|
| F-USR-01 | Nyelvválasztás a fejlécben, három nyelv, a választás megmarad a böngészőben | M | R1 |
| F-USR-02 | A felhasználó beállíthatja a mértékegység-rendszert (metrikus / nemzetközi) | S | R2 |
| F-USR-03 | Regisztráció és bejelentkezés e-mail + jelszó, vagy OAuth (Google) | S | R2 |
| F-USR-04 | Fiók nélkül is használható a katalógus (R1); a fiók a figyelőlista és az értesítésekhez kell | M | R1 |
| F-USR-05 | Adatvédelmi beállítások: értesítések kikapcsolása, fiókexport, fióktörlés | M | R2 |
| F-USR-06 | A felhasználó nyelvi beállítása alapértelmezett, de egyedi oldalnyelvi felülírás lehetséges | S | R2 |

### 4.10 J. Szerkesztői felület (R1)

| ID | Követelmény | P | Release |
|---|---|---|---|
| F-ADM-01 | A hajóadatok szerkesztése (műszaki adatok, üzemeltető, engedélyek) | M | R1 |
| F-ADM-02 | A hajónév és az egyéb fordítható mezők szerkesztése fordításonként | M | R1 |
| F-ADM-03 | Forrás- és bizonyítékmező minden kézzel módosított adathoz (ki, mikor, honnan) | M | R1 |
| F-ADM-04 | A felhasználói észrevételek (F-DET-11) feldolgozhatók egy listában | M | R1 |
| F-ADM-05 | A fordítási hiánylista: mely kulcsok/szövegek hiányoznak vagy elavultak | S | R1 |
| F-ADM-06 | Előnézet a hajóoldal minden nyelvén, a megjelenés ellenőrzéséhez | S | R1 |
| F-ADM-07 | Tömeges import hajólista CSV-ből (ENI-vel) | M | R1 |
| F-ADM-08 | Az üzemeltetői önbevallás (claim) kezelése: beérkezett kérelmek listája, egyeztetés az AIS-rekorddal, jóváhagyás vagy elutasítás indoklással | M | R1 |
| F-ADM-09 | Konfliktuskezelés: ha az AIS-adat és az üzemeltetői állítás eltér, **mindkettő látszik**, és a szerkesztő dönt | M | R1 |

### 4.11 K. B2B API (R5)

| ID | Követelmény | P | Release |
|---|---|---|---|
| F-API-01 | Dokumentált REST API: hajólista, hajóadatlap, kikötők | M | R5 |
| F-API-02 | Kulcskezelés, hatókörök, kvóták, használati statisztika | M | R5 |
| F-API-03 | Élő pozíció stream (SSE vagy WebSocket) külön díjszabással | S | R5 |
| F-API-04 | Webhook-feliratkozás eseményekre (érkezés, késés, vízállás) | L | R5 |

### 4.12 L. Nyelvkezelés (R1)

| ID | Követelmény | P | Release |
|---|---|---|---|
| F-INTL-01 | Minden nyilvános oldal és felületelem elérhető magyarul, németül és angolul | M | R1 |
| F-INTL-02 | Az URL tartalmazza a nyelvet (`/de/hajos/...`) – SEO- és megoszthatósági célból | M | R1 |
| F-INTL-03 | Automatikus átirányítás a böngésző nyelve alapján, csak első látogatáskor, felülírható | S | R1 |
| F-INTL-04 | `hreflang` és `x-default` tagok a megfelelő nyelvi változatokra | M | R1 |
| F-INTL-05 | A hiányzó fordítás nem jelenik meg üres mezőként, hanem a forrásnyelv szövegével, jelöléssel | M | R1 |
| F-INTL-06 | Szám- és dátumformázás a nyelv szerint (tizedesvessző, dátumrend) | M | R1 |
| F-INTL-07 | A paraméterezett szövegek (változók behelyettesítése) helyesen működnek mindhárom nyelven, helyes mondatsorrenddel | M | R1 |
| F-INTL-08 | A nemzetközi hajószámok és az ENI-k formázása nyelvfüggetlen, de kereshetők | M | R1 |
| F-INTL-09 | A felhasználó beállíthatja a preferált nyelvet a fiókban (R2-től) | S | R2 |

---

## 5. Nem-funkcionális követelmények

| ID | Terület | Követelmény | Célérték |
|---|---|---|---|
| F-NF-01 | Teljesítmény | Katalógusoldal betöltése (300 hajós lista) | < 800 ms p95 |
| F-NF-02 | Teljesítmény | Hajóadatlap betöltése | < 400 ms p95 |
| F-NF-03 | Teljesítmény | Globális keresés válaszideje | < 200 ms p95 |
| F-NF-04 | SEO | Indexelhető hajóoldalak minden nyelven | 100% |
| F-NF-05 | SEO | Nincs tartalom duplikáció a nyelvi URL-ek között (`canonical`) | 100% |
| F-NF-06 | Akadálymentesség | WCAG 2.1 AA: kontraszt, billentyűzetes navigáció, képernyőolvasó-labellek | AA |
| F-NF-07 | Reszponzivitás | A katalógus 360 px-től működik; a mobilapp natív | – |
| F-NF-08 | Adatfrissesség | A statikus katalógusadatok frissítési gyakorisága | hetente + eseményvezérelt |
| F-NF-09 | Adatminőség | A katalógusban szereplő hajók ≥ 95%-ának azonosítója és típusa kitöltve | mérendő |
| F-NF-10 | Adatminőség | Duplikált hajószám rekordok | 0 |
| F-NF-11 | Biztonság | A nyilvános API nem ad hozzáférést belső mezőkhöz (belső jegyzet, forrás URL) | 0 szivárgás |
| F-NF-12 | Jogi | A katalógus minden adathoz megmutatja a forrását (megtekintés) | 100% |
| F-NF-13 | Jogi | Nincs személyes adat a hajóadatokban (kapitány, legénység) | 0 |
| F-NF-14 | Adatvédelem | Cookie-banner, GDPR-nyilatkozat, fióktörlés önkiszolgáló | megfelelő |
| F-NF-15 | Karbantarthatóság | A katalógus API visszafelé kompatibilis (verziózott séma) | – |
| F-NF-16 | Nyelvi minőség | Minden publikált fordítás átnézett (nem gépi egyezés) | 100% |
| F-NF-17 | Adatminőség | A katalógusban nincs **fantom hajó** (olyan AIS-rekord, aminek nincs víz feletti pozíciója) | 0 db |
| F-NF-18 | Adatminőség | A Duna-katalógus hajóinak ≥ 60%-a ENI-vel azonosított (AIS Inland FI 10 alapján) | ≥ 60% |
| F-NF-19 | Adatminőség | A hajóméret AIS-értéke mindenhol **AIS méretként** jelölve, a konvojméretek korlátja feltüntetve | 100% |
| F-NF-20 | Adatminőség | A merülés mindenhol az **RNW-re** vonatkozó jelöléssel jelenik meg | 100% |

---

## 6. A katalógus adatszükséglete (R1) – területenként

### 6.1 Duna-hajó adatlap mezői

| Csoport | Mező | Forrás | Kötelező |
|---|---|---|---|
| Azonosítás | ENI (8 jegy) | **AIS – Inland FI 10** | ha van |
| | IMO-szám | AIS (belvízi hajónál nem érvényes) | ha van |
| | MMSI | **AIS** | igen |
| | Hívójel (call sign) | **AIS – Message 5** | igen |
| | Korábbi nevek | üzemeltetői állítás / szerkesztői | opcionális |
| Osztályozás | ERI-típuskód (UN E-rek. 28 szerinti) | **AIS – Inland FI 10** | igen |
| | Szállítási kategória (száraz teher / folyadék / vegyes / személy / munkahajó / kishajó) | származtatott | igen |
| | Önjáró / nem önjáró (bárka) | származtatott | igen |
| Műszaki | Hossz, szélesség | **AIS méret** (figyelem: lehet konvojméret) | igen |
| | Max. merülés (RNW-re) | **AIS – Inland FI 10** | igen |
| | Bruttó tonnage, teherkapacitás (DWT), TEU | üzemeltetői állítás | opcionális |
| | Motorteljesítmény, építési év | üzemeltetői állítás | opcionális |
| Tulajdonos | Üzemeltető / tulajdonos | **üzemeltetői önbevallás** | opcionális |
| | Zászlóállapot | **AIS – Inland FI 10** (UN country code) | igen |
| | Hazai kikötő | üzemeltetői állítás / szerkesztői | opcionális |
| | Közlekedési engedély hatályossága | üzemeltetői állítás | opcionális |
| Állapot | Aktív / állandóan álló / nem közlekedik | származtatott | igen |
| Terület | Leggyakoribb vízi szakasz (szövegesen, R1) | **AIS – fairway section** | opcionális |
| | Érintett kikötők | **AIS – cél UN/LOCODE** | opcionális |
| Történet | Tulajdonosváltás, átalakítás (dátumtartomány) | üzemeltetői állítás | opcionális |
| Belső | Forrás, frissítés dátuma, megjegyzés | belső | igen |

### 6.2 Balatoni hajó adatlap mezői

| Csoport | Mező | Forrás | Kötelező |
|---|---|---|---|
| Azonosítás | Nemzetközi hajószám (call sign) | üzemeltetői lista / AIS | nagyhajónál igen |
| | Nemzeti hajónyilvántartási szám | üzemeltetői lista | igen |
| | IMO-szám (ha van) | AIS / üzemeltetői lista | ha van |
| | Hajónév | üzemeltetői lista / AIS | igen |
| Osztályozás | Kategória: nagyhajó (több mint 100 fő) / személyhajó / komp / szolgálati hajó / munkagép / kishajó / vitorlás | üzemeltetői lista | igen |
| | Ezen belül: „nosztalgia-hajó" / modern motoros hajó | üzemeltető | opcionális |
| Műszaki | Befogadóképesség (fő), hossz, szélesség | üzemeltetői lista | igen |
| | Szolgáltatások: fedélzet, étterem, WC, akadálymentesség, védett hely | üzemeltető | opcionális |
| Üzemeltető | Cég neve, webhely, elérhetőség | üzemeltető saját oldala | igen |
| Szezon | Szezonban közlekedik (dátumtartomány), heti menetrend hivatkozás | üzemeltető | igen |
| Terület | Medence (nyugati / középső / keleti), partkm | szerkesztői meghatározás | opcionális |
| Kikötő | Hozzáférhető kikötők, kikötőrend hivatkozás | **publikált kikötőrend** | opcionális |
| Belső | Forrás, frissítés dátuma | belső | igen |

**Különbség a két terület között, ami a sémát is meghatározza:** a Duna-hajónál az *azonosítás központi* (MMSI mindig van, ENI a belvízi AIS-ből jön, és mind kereshető), a Balaton-hajónál az *azonosítás gyenge* (a nagyhajóknál van nemzetközi hajószám, a kishajóknál és a vitorlásnál nincs) — ott a *szolgáltatás és a szezon* a keresési és döntési alap. Ezért a katalógus szűrői is területenként eltérnek.

**Adatforrás-táblázat:** a mezők forrásának részletes táblázata a [`r1-adat-terv.md`](r1-adat-terv.md) 6. fejezetében van (AIS / üzemeltetői állítás / publikált hatósági anyag szerinti bontásban).

### 6.3 Katalógusszűrők területenként

| Szűrő | Duna | Balaton |
|---|---|---|
| Típus | ✅ | ✅ (más kódkészlet) |
| Üzemeltető | ✅ | ✅ |
| Állapot / szezon | állapot | szezonban közlekedik |
| Vízterület | folyószakasz (szöveges) | medence |
| Befogadóképesség | – | ✅ |
| Szolgáltatás (WC/étterem/akadálymentes) | – | ✅ |
| Kikötő | ✅ (R3) | ✅ |
| Celzia / célkikötő | ✅ (R4) | – |
| Név / azonosító keresés | ✅ | ✅ (más azonosítók) |

---

## 7. A Balaton elkülönítésének szabályai

1. **Külön katalógus és URL-tér:** `/hu/duna/hajok`, `/hu/balaton/hajok`. Nincs egyetlen `/hajok` lista, amely mindkettőt mutatja.
2. **Külön szűrők és rendezés:** a Balaton-szűrők nem kínálnak folyószakaszt, a Duna-szűrők nem kínálnak medencét.
3. **Külön azonosító-értelmezés:** Duna = ENI-first; Balaton = hajószám-first. A kereső a Balatonon nem vár ENI-t, és a Duna-szűrő nem vár hajószámot.
4. **Külön szezonlogika:** a Duna-hajók egész évre vannak nyilvántartva; a Balatoni hajóknál a „szezonban közlekedik" elsődleges állapot, a szezonon kívüli állapotot külön jelöljük.
5. **Külön adattáblák a plusz adatokra:** `vessel_service_period` (szezon), `marina` (balatoni kikötő), `vessel_schedule` (menetrend) – a Duna oldalon ezek üresek.
6. **Külön tartalom:** a Balatoni tájékoztatók (KH-hirdetmények, kikötőrendek) nem jelennek meg a Duna-szűrőkben.
7. **Közös réteg csak ott, ahol tényleg közös:** a hajó alapadat-struktúrája, a fordítási mechanizmus, a kereső infrastruktúra, a felhasználói fiók, a figyelőlista.

---

## 8. Felhasználói forgatókönyvek (a legfontosabbak)

| # | Szerep | Forgatókönyv | Release |
|---|---|---|---|
| US-01 | Hajókereső | „Meg akarom nézni, ki üzemelteti a Balaton Csongor hajót és mekkora a befogadóképessége." | R1 |
| US-02 | Hajókereső | „Az ENI 12345678 alapján meg akarom nézni ezt a hajót a Duna-katalógusban." | R1 |
| US-03 | Hajókereső | „A német változatban is meg akarom nézni ugyanazt a hajót." | R1 |
| US-04 | Fuvarozó | „A folyamatban lévő útját és várható érkezését akarom látni." | R4 |
| US-05 | Balatoni utazó | „Meg akarom nézni, mely hajók járnak jövő szombaton, és hol indulnak." | R3 |
| US-06 | Hajóbérlő | „Azonosítani akarok egy 80–120 fő befogadóképességű, zárt fedélzetű hajót, WC-vel." | R1 |
| US-07 | Szkepticikus | „A honlapon látni akarom, honnan származnak az adatok, hogy elbírjam a hitelességüket." | R1 |
| US-08 | Szerkesztő | „Egy felhasználó jelezte, hogy a hajó neve elavult. Meg kell javítanom, és a három nyelven is." | R1 |
| US-09 | Adatminőség | „Látni akarom, mely hajóknál hiányzik az ENI vagy a kapacitás, és ki kell-e pótolni." | R1 |
| US-10 | Fejlesztő | „Programozottan le akarom kérni a száraz teherhajókat ENI-jükkel." | R5 |

---

## 9. A nyelv megjelenése a termékben

| Szempont | Megoldás |
|---|---|
| Nyelvválasztó | Fejlécben, mindig látható; a választás sütiben és a felhasználó fiókban is tárolódik |
| URL | `/hu/…`, `/de/…`, `/en/…` – a nyelv az URL első szegmense |
| Megosztás | A megosztott link mindig a felhasználó aktuális nyelvén nyílik meg |
| Tartalmi eltolás | Ha a magyar nyelvű szöveg nincs kész, a német és az angol változat külön-külön jelölést kap (nem egy közös „elavult" jelölés) |
| Számformátum | hu/de: `1 250` / `1.250`; en: `1,250`. Tizedes: `12,5` vs `12.5` |
| Dátum | hu: `2026. máj. 14.` · de: `14. Mai 2026` · en: `14 May 2026` |
| Mértékegység | tárolva SI-alapú; megjelenítés: km/h, t, m (nemzetközi felhasználóknál: kn, nm, ft) |
| Szöveges irány | Latin írás, RTL nem szükséges |
| UI-szöveg vs. adattartalom | a UI-szövegek (`content_key`) és a tartalmi mezők (`*_i18n`) külön kezelendők, de ugyanazt a hiánylistát követik |

---

## 10. Mit nem döntöttünk el (funkcionális szinten)

| # | Kérdés | Hol dől el |
|---|---|---|
| 1 | A Duna-katalógus mutassa-e a nem közlekedő (állandóan álló, eladásra váró) hajókat is? | Adatpolitika, R1 előtt |
| 2 | A Balatonon a vitorlásokat is katalógusba vesszük-e, vagy csak a motoros hajókat? | Adatpolitika, R1 előtt |
| 3 | A katalógus mutat-e árkategóriát vagy bérleti árat? (Nem funkció, de a felhasználói elvárás) | Üzleti döntés |
| 4 | A felhasználó javító észrevétele befolyásolja-e a nyilvános adatot automatikusan? | Adatminőségi politika |
| 5 | A katalógus mutat-e „utolsó frissítés" dátumot a hajóneveknél is? | UI-döntés |

Ezek a döntések nem blokkolják az R1 fejlesztését, de a katalógus tartalmi keretét befolyásolják.
