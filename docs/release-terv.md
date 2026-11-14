# Release terv – Dunai hajókövető és Balatoni hajókatalógus

**Verzió:** 1.0 (2026-11-14)
**Kapcsolódó dokumentumok:** [`funkcio-leiras.md`](funkcio-leiras.md) · [`../README.md`](../README.md) (adatbázis terv)

---

## 1. Alapelvek

- **A release egy önállóan kiadható, értéket teremtő állapot.** Minden release a produkcióba kerül, nem csak a „fejlesztésben van" státuszban.
- **A release a felhasználó nézete, nem a moduloké.** Nem „Adatbázis-modul kész" a release, hanem „a hajókatalógus működik".
- **Az első release a kockázatot csökkenti, nem maximalizálja a funkciót.** Az R1 katalógus: nincs térkép, nincs élő adat, nincs ETA, nincs push. Cserébe a legnehezebb technikai kockázat (a hajóadatok megszerzése és háromnyelvűség) már ekkor megoldott.
- **Amit R1-ben megépítünk, az a későbbi release-ek alapja.** Az adatszerkezet, a fordítási mechanizmus, a SEO-minta és a szerkesztői felület R1-ben készül el és R2–R5 csak ráépül.
- **Sorrend, nem dátum.** A release-ek egymásra épülnek; a konkrét dátumot a release-ek lezárásakor rögzítjük.

**Munkamegosztás:** a becslések 1 teljes stack fejlesztőre (backend + frontend) és 0,5 tartalmi/szerkesztői szerepre vonatkoznak. Méretek: **S** = ~1 hét, **M** = ~2–3 hét, **L** = ~4–6 hét.

---

## 2. Release-áttekintés

| Release | Név | A felhasználó ezt kapja | Méret | Függőség |
|---|---|---|---|---|
| **R1** | **Hajókatalógus** | Teljes, kereshető, háromnyelvű hajókatalógus a Dunáról és a Balatonról — **térkép nélkül** | **L** | – |
| R2 | Térkép és élő adat | Élő térkép a Dunán, pozíciófrissítés, figyelőlista, első push | L | R1 |
| R3 | Balaton és tartalom | Balatoni térkép, kikötők, menetrend, tájékoztatók, események | M–L | R2 |
| R4 | Utazás és tervezés | Utazás/ETA, útvonal-tervező, zsilip- és vízállás-figyelmeztetés | L | R2 |
| R5 | B2B és közösség | Nyilvános API, webhooks, fuvar- és kapacitásérdeklődés | M–L | R3, R4 |

---

## 3. R1 – Hajókatalógus (első kiadás)

### 3.1 A release célja

> **A felhasználó böngészhet és kereshet a Dunán és a Balatonon közlekedő hajók között, minden haJORól megtalálhatja a hivatalos adatait, három nyelven, forrásjelöléssel — térkép nélkül.**

A release sikerkritériuma: **a hajóról szóló tények már elérhetők és ellenőrizhetők**, még akkor is, ha a hajó mozgását még nem látjuk. Ez egyben a későbbi élő funkciók adatbázis-alapja is.

### 3.2 Az R1-ben benne van

| # | Funkció | Forrás |
|---|---|---|
| 1 | Két elkülönített katalógus: **Duna** / **Balaton** (külön URL, szűrő, rendezés) | F-CAT-01 |
| 2 | Katalóguslista szűréssel, rendezéssel, lapozással | F-CAT-02, F-CAT-04, F-CAT-05 |
| 3 | Hajóadatlap: azonosítók, műszaki adatok, üzemeltető, állapot, történet | F-DET-01…08, F-DET-13 |
| 4 | Globális kereső: hajónév + területenkénti azonosítók | F-SRCH-01…07 |
| 5 | Területenkénti szűrők (típus, üzemeltető, állapot, terület) | F-CAT-08 |
| 6 | Háromnyelvű felület (hu/de/en), URL-prefix, `hreflang`, hiánylista-jelölés | F-INTL-01…08 |
| 7 | Szerkesztői felület: hajóadatok, fordítások, észrevételek, tömeges import | F-ADM-01…07 |
| 8 | Felhasználói javító észrevétel a hajóoldalon | F-DET-11 |
| 9 | Forrás- és frissítésdátum-jelölés minden adathoz | F-NF-12 |
| 10 | Statikus tartalomoldalak: kikötők (Duna + Balaton), zsilip, folyószakaszok, hajótípusok | F-CNT-01, F-CNT-02 |
| 11 | Statikus cikkek/blog (három nyelven) | F-CNT-05 |
| 12 | Nyilvános JSON API a katalógushoz (v1) | F-API-01 részleges |
| 13 | SEO: sitemap, kanonikus URL, strukturált adat (`Vessel` / `Boat` séma) | F-NF-04, F-NF-05 |

### 3.3 Az R1-ben **nincs** benne (szándékosan)

| Nincs | Miért | Mikor |
|---|---|---|
| **Térkép** | A felhasználó kérése; a katalógus önmagában is értékes | R2 |
| Élő pozíció **megjelenítése** | Az AIS-adatvétel már R1-ben fut (statikus gyűjtés), csak a felület hiányzik | R2 |
| ETA, útvonal-tervező | Élő adatot igényel | R4 |
| Push-értesítések | Élő adatot igényel | R2 (figyelőlista), R4 (érkezés) |
| Fiókbejelentkezés, regisztráció | R1-ben a katalógus fiók nélkül is teljes értékű | R2 |
| Vízállás, zsilipvárakozás | Élő/hatósági adatforrás | R4 |
| B2B API, webhooks | Az R1 API belső célra készül | R5 |

### 3.4 Adathátter (milyen adat kell az R1-hez)

> **A részletes adat-terv: [`r1-adat-terv.md`](r1-adat-terv.md) · [`ais-vevo-terv.md`](ais-vevo-terv.md)** – forrásmátrix, mezőnkénti kitöltöttség, validációs szabályok, pipeline, átvételi küszöbök. Az alábbi táblázat az összefoglaló.

| Adat | Honnan | Mennyi | Kockázat |
|---|---|---|---|
| Duna-hajók: ENI, MMSI, hívójel, név, típus, méretek, merülés, zászló | **AIS** – Inland FI 10 + Message 5 | a Duna teljes AIS-flotta | **közepes** – a feed lefedettsége és a „fantom" hajók szűrése a kulcs |
| Duna-hajók: folyó-km, szakasz, célkikötő, ETA zsilipnél, rakomány-jelölés | **AIS** – Inland FI 10 útvonaladat | folyamatos | alacsony |
| Duna-hajók: üzemeltető, kapacitás, építési év | **üzemeltetői önbevallás (claim)** | a hajók egy része | **közepes** – a kitöltési hajlandóság függ a vállalattól |
| Balatoni hajók (név, típus, befogadóképesség, üzemeltető, szezon) | Üzemeltetők flottaoldalai + AIS (nagyhajók) | ~150–250 bejegyzés | **magas** – nincs központi lista, minden üzemeltető másképp közöl |
| Balatoni kikötők + kikötőrendek | Publikált KH- és Balatoni Hajózási Zrt. tájékoztatók | 70–80 kikötő | alacsony – publikált, nem igényel adatkérést |
| Duna-kikötők km-értékei | Duna Bizottság port-távolság-táblázata | ~400 kikötő | alacsony |
| Zsilipek, folyószakaszok | Publikált tájékoztatók + AIS fairway section kódok | ~30 zsilip | alacsony |
| UI- és típusfordítások | Saját szerkesztés | ~300 kulcs × 3 nyelv | **közepes** – a német terminológia szakértői ellenőrzést igényel |

> **Az R1 adata nem hatósági adatkéréstől függ.** A katalógus AIS-ból épül fel; amit az AIS nem ad (üzemeltető, kapacitás, építési év), azt az üzemeltető önbevallása pótolja; a kikötő- és szakaszadatokhoz publikált hatósági anyag kell, nem adatbázis-hozzáférés. **Az egyetlen külső függőség az AIS feed** – és az a statikus adatot is ad.

**A legfontosabb felismerés a háromnyelvűséghez:** a hajók hivatalos neve latin betűs, egységes (a Dunán és a Balatonon egyaránt), tehát **a hajónevek nem igényelnek fordítást**. A háromnyelvűség terhe a UI-szövegeken, a hajótípus-neveken, a helységneveken és a jogi szövegeken van — ez lényegesen kisebb feladat, mint elsőre látszik. A magyar szerkesztői alapnyelv, az angol technikai másodlagos nyelv, a német piaci nyelv.

### 3.4.1 Az R1 előkészítő fázisa (R1-0)

> **A feed csak a szerződés kezdete után ad statikus adatot**, és a hajók a statikus üzenetet ritkán küldik el. Ezért az R1 **nem indulhat azonnal** a feed megkötése után.

| Fázis | Időtartam | Tartalom |
|---|---|---|
| **R1-0** | **3–6 hónap a formalis R1 előtt** | **Saját AIS vevőhálózat építése** (próbavevő → 30 napos mérés → F1 site-ek), parser, statikus adatok gyűjtése, „fantom"-szűrő kidolgozása – részletek: [`ais-vevo-terv.md`](ais-vevo-terv.md) |
| **R1** | – | A katalógus a gyűjtött statikus adatból épül fel |

Az R1-0 nem nyilvános release, de **a projekt legfontosabb időablaka**: ha itt csúszik, az R1 is csúszik. A feed kiválasztása ezért az **első döntés**, nem a fejlesztés második hete.

### 3.5 Kilépési feltételek (Definition of Done)

**Tartalom**
- [ ] Minden bejegyzett hajónak van neve, típusa, azonosítója (területenként a megfelelő) és bizonyossági szintje
- [ ] A Duna-katalógusban ≥ 60% a hajók ENI-vel azonosítható (AIS Inland FI 10-ből)
- [ ] A Balaton-katalógusban ≥ 90% a hajók hajószámmal vagy IMO-val azonosítható
- [ ] A katalógusban nincs „fantom" hajó (vízfeletti pozíció nélkül nincs bejegyzés)
- [ ] Minden hajóoldalon látható a forrás és a frissítés dátuma, mezőnkénti eredettel
- [ ] Az üzemeltetői önbevallás (claim) működik, és a konfliktusok láthatók
- [ ] Minden hajótípus lefordítva három nyelvre
- [ ] Minden kikötő és zsilip lefordítva három nyelvre

**Funkció**
- [ ] A katalógus szűrhető és rendezhető, a szűrés URL-ben megőrződik
- [ ] A kereső pontos egyezéssel azonosítóra és szubsztringre névre működik
- [ ] A Duna- és a Balaton-keresés nem szivárog át a másik területre
- [ ] Minden nyilvános oldal három nyelven elérhető, `hreflang` és kanonikus URL helyes
- [ ] Hiányzó fordítás esetén jelölés jelenik meg, üres mező nincs

**Technikai**
- [ ] A séma migrációként, visszafordíthatóan telepíthető
- [ ] A katalógus API verziózott (`/api/v1/…`), a dokumentáció mellette van
- [ ] A teljes katalógus importálható CSV-ből a szerkesztői felületen
- [ ] Alap SEO-ellenőrzés: sitemap, robots, strukturált adat valid
- [ ] Automatizált teszt: ENI/egyértelműség, terület-szivárgás, nyelvi hiánylista

**Üzemeltetés**
- [ ] Napi mentés és visszaállítás kipróbálva
- [ ] Adatminőségi riport (kitöltetlen mezők, duplikátumok) működik
- [ ] A hibajegyzet a szerkesztői felületen bekötve

### 3.6 Az R1 kockázatai

| Kockázat | Valószínűség | Hatás | Mitigáció |
|---|---|---|---|
| **A saját vevő lefedettsége nem elég** a teljes magyar Duna-szakaszra | közepes | a katalógusban hiányzó hajók | A **30 napos próbavevős mérés** (Budapest) a go/no-go: ha nem éri el a magyar flotta 50%-át, F1 helyett S-AIS feed + vevő hibrid; a telephelyek számát a mérésből méretezjük |
| **A telephelyek engedélyezése elakad** | közepes | egy site csúszik, a hálózat építése lassul | Minden site-hoz 2–3 tartalék telephely; a kikötők és vízügyi objektumok a legegyszerűbbek |
| **A statikus adatok csak hetek-hónapok alatt gyűlnek össze** | biztos | az R1 indulása csúszik | Az **R1-0 előkészítő fázis** (3–6 hónap) a terv része, nem egy plusz |
| A „fantom" hajók (szárazföldi pozíciók) bekerülnek a katalógusba | magas | hitelességi probléma | Pozícióalapú szűrő kötelező a pipeline-ban, a folyó geometriáján belül |
| A Balatoni hajólista nem áll össze egyetlen forrásból | magas | gyenge Balaton-katalógus | Két megközelítés együtt: üzemeltetői oldalak kézi begyűjtése (~15 üzemeltető) + AIS a nagyhajókra |
| Az üzemeltetők nem élnek a claimmel (a kapacitás/év hiányzik) | közepes | a katalógus „félkész" | A hiányzó mező a felületen **„adat nélkül"** jelenik meg, nem elrejtve; a claim előnye a keresésben és a szűrésben |
| A német fordítások szakértelmetlenek | közepes | márkanév-érintettség, visszavonás | Német nyelvi reviewer bevonása; a nem átnézett fordítás státusza látszik a belső felületen |
| A katalógus „üresnek" tűnik térkép nélkül | közepes | a felhasználó nem érti, miért érdemes visszatérni | A katalógust **tartalmi termékként** pozicionálni (kereshető hajólista, szűrés, adatlap), és a terepviszonyokat szövegesen közölni (pl. „Szigetvár–Szekszárd szakasz") |
| A felhasználó élő pozíciót vár | magas | türelmetlenség | A felületen egyértelműen jelezni: „ez a katalógus; az élő követés a következő kiadásban" + értesítéslista a megjegyzésre |

### 3.7 Az R1 becslése

| Sprint | Tartalom | Kimenetel |
|---|---|---|
| 0. (R1-0) | **Saját AIS vevő: próbavevő + 30 napos mérés + F1 site-ek**, parser (Msg 5 + Inland FI 10), „fantom"-szűrő, statikus gyűjtés – részletek: [`ais-vevo-terv.md`](ais-vevo-terv.md) | Folyamatosan bővülő AIS-adatbázis |
| 1. | Séma, fordítási infrastruktúra, projekt-alapozás (CI, környezetek, migrációk) | Adatbázis váz, nyelvi kulcsok |
| 2. | **Adatfeldolgozás és -bevitel** (AIS-ból), „fantom"-szűrés, üzemeltetői claim, szerkesztői felület v1 | Valós adat a DB-ben |
| 3. | Katalóguslista, szűrés, rendezés, kereső, hajóadatlap | Működő katalógus (belső) |
| 4. | i18n véglegesítés, SEO, statikus tartalomoldalak, API v1, dokumentáció, hibajegyzet | **R1 kiadás** |

> **A sprint-sorrend nem véletlen:** a 2. sprint azért megy a 3. elé, mert a 3. sprint felülete a 2. sprintben behozott adat nélkül nem lenne megmutatható. **Az R1 legnagyobb ütemezési kockázata az adatbeszerzés:** a statikus hajóadat hetek-hónapok alatt gyűl össze, ezért a 0. sprint (előkészítő, saját vevő építése) a formális R1 **eleje**, nem utólagos teendő.

---

## 4. R2 – Térkép és élő adat

**Cél:** a felhasználó a térképen látja, hol vannak a hajók, és követheti a kedvencét.

| Tartalom | Funkciók |
|---|---|
| Térkép | F-MAP-01, 03, 04, 05, 06, 07, 08, 09 |
| Élő pozíció | F-LIVE-01…05, 07 |
| Figyelőlista + push | F-NOT-01, 05, 06; F-USR-03…05 |
| Adatbeszerzés | AIS-feedintegráció, ingest, partícionálás, archívum |

**Kilépési feltételek (kivonat):** pozíciófrissesség < 15 perc a mozgó hajóknál; a térkép első betöltése < 2 s; a figyelőlista push késése < 5 s; nincs ismétlődő pozíciósor; a bárkák konvojként jelennek meg.

**Kockázat:** az AIS-licenc és a feed minősége. **Mitigáció:** a feed legyen cserélhető (`data_source`), és legyen egy belső minőségi dashboard (pozíciófedettség, késés) az első naptól.

---

## 5. R3 – Balaton és tartalom

**Cél:** a Balaton ne csak katalógus legyen, hanem a turisztikai igényt is kiszolgálja.

| Tartalom | Funkciók |
|---|---|
| Balatoni térkép (3 medence) | F-MAP-02, 03 |
| Balatoni kikötőadatlapok + kikötőrendek | F-CNT-02 |
| Szezon- és menetrend-adatok | F-CNT-04, F-VOY-07; F-BAL-03 |
| Tájékoztatók és események | F-CNT-03, 04 |
| Kikötő–hajó kapcsolat valós forgalomból | F-CNT-07 |
| Duna-kikötő forgalmi adatai | F-CNT-07 |

**Különlegesség:** a Balatoni adatok nem ugyanazok a forrásokból jönnek, és a szezon miatt a „most nincs forgalom" állapot teljesen normális — ezt a felületnek egyértelműen kezelnie kell, különben a felhasználó hibásnak érzékeli.

---

## 6. R4 – Utazás, ETA és tervezés

**Cél:** a felhasználó meg tudja tervezni, mikor és melyik hajóval jut el A-ról B-re.

| Tartalom | Funkciók |
|---|---|
| Utazás felismerése, megállók | F-VOY-01 |
| Útvonal-tervező + ETA konfidenciával | F-VOY-02, 03, 06 |
| Zsilipvárakozás, sor | F-VOY-04 |
| Vízállás-korlát figyelmeztetés | F-VOY-05, F-NOT-04 |
| Érkezési/késési értesítések | F-NOT-02, 03 |
| Összehasonlító nézet, PDF | F-CAT-13, F-DET-12 |

**Kockázat:** az ETA pontosság. **Mitigáció:** a becslés verziózott, a konfidencia-intervallum mindig látszik, és az átlagos hibát (MAPE) mérni kell — a terv szerint < 6 óra.

---

## 7. R5 – B2B és közösség

| Tartalom | Funkciók |
|---|---|
| Nyilvános API v2, kulcsok, kvóták, használati statisztika | F-API-01, 02 |
| Élő pozíció stream, webhookok | F-API-03, 04 |
| Fuvar- és kapacitásérdeklődés (funkció nélküli érdeklődés) | – |
| Közösségi visszajelzés, javítások értékelése | F-DET-11 kibővítve |
| Összehasonlító és export funkciók | F-CAT-12, 13 |
| Nyilvános vizesblokk / hajószámla letöltés | – |

---

## 8. Release-mátrix

| Funkciócsoport | R1 | R2 | R3 | R4 | R5 |
|---|:--:|:--:|:--:|:--:|:--:|
| Katalóguslista, szűrés, rendezés | ✅ | | | | |
| Hajóadatlap | ✅ | ✅ | | ✅ | |
| Globális keresés | ✅ | | | | |
| Háromnyelvűség | ✅ | ✅ | ✅ | ✅ | ✅ |
| Szerkesztői felület, import, észrevételek | ✅ | | ✅ | | |
| Statikus tartalom (kikötő, zsilip, cikk) | ✅ | | ✅ | | |
| **Térkép (Duna)** | | ✅ | | | |
| **Térkép (Balaton)** | | | ✅ | | |
| Élő pozíció, figyelőlista, push | | ✅ | ✅ | ✅ | |
| Fiók, bejelentkezés, adatvédelem | | ✅ | | | ✅ |
| Menetrend (Balaton) | | | ✅ | | |
| Tájékoztatók, események | | | ✅ | | |
| Utazás, megállók | | | | ✅ | |
| ETA, útvonal-tervező | | | | ✅ | |
| Zsilipvárakozás, vízállás | | | | ✅ | |
| Nyilvános API, B2B | v1 | | | | ✅ |

---

## 9. Kiadási folyamat

| Lépés | Tartalom |
|---|---|
| **Release branch** | `release/1`, `release/2`… a `main`-ből indul, csak bugfix megy rá |
| **V feature flag** | Az új funkciók flaggel kapcsolhatók ki (a katalógus R2-ben már flag mögött él, hogy a betöltési út másodrendű legyen) |
| **Adat-migráció** | Minden séma-változás visszafordítható migráció; az éles adat és a kód verziója együtt kezelendő |
| **Fordítási check** | Release előtt: a hiánylista üres, vagy a maradék ismert és dokumentált |
| **Adatminőségi check** | ENI-duplikátumok, azonosító nélküli hajók, terület-ellentmondások |
| **Visszacsatolás** | Az R1 lezárása után: mely hajóoldalak nézik, mely keresési kifejezések nem adnak találatot → ez az R2 keresési és szűrési finomhangolását adja |

---

## 10. A tempót meghatározó külső tényezők

| Tényező | Hatás | Felelős |
|---|---|---|
| AIS-/hajószám-adatforrás szerződése | Az R2 indulását gátolja, ha késik | Törzs / üzlet |
| Közlekedési Hatósági adatszolgáltatás (Balaton) | Az R1 katalógusminőségét határozza meg | Törzs / üzlet |
| Fordítási kapacitás (német) | Az R1 hiánylista méretét | Tartalom |
| Karteusz-térképszolgáltató kiválasztása | Az R2 indulását | Fejlesztés |
| Balatoni menetrend-adatforrás (üzemeltetők) | Az R3 menetrend- és szezonfunkcióit | Tartalom |
| Szerkesztői csapat rendelkezésre állása | Az R1 adattöltésének üteme | Törzs |

---

## 11. Mit mérünk release-enként

| Metrika | R1 cél | R2 cél | R4 cél |
|---|---|---|---|
| Havóoldalak indexelve a Google-ban | 100% | – | – |
| Katalógusoldal betöltési idő (p95) | < 800 ms | < 1,2 s (térkép) | – |
| Keresés használata / meghiúsulási arány | < 20% | – | – |
| Ismétlődő látogatók aránya | – | > 25% | > 40% |
| Push-értesítés megnyitási arány | – | > 20% | > 30% |
| ETA hibája (MAPE) | – | – | < 6 óra |
| Helyesbítő észrevételek száma / hajó | mérés alatt | – | csökkenő |

---

## 12. Az R1 „kész” definíciója egy mondatban

> **Mindenki megnyithatja a weboldalt, magyarul, németül vagy angolul, rábökhet a „Hajók" menüpontra, és két külön katalógusban — Duna, Balaton — végigböngészheti a hajókat; minden hajóról megvan a hivatalos azonosítója, típusa, mérete, üzemeltetője, állapota és az adatai forrása; és egyik hajóhoz sincs szükség térképhez, hogy értelmes információt kapjunk róla.**
