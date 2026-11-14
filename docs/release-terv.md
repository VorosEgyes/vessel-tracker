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
| Élő pozíció, AIS-adatvétel | Adatlicenc + infrastruktúra; nem kell a katalógushoz | R2 |
| ETA, útvonal-tervező | Élő adatot igényel | R4 |
| Push-értesítések | Élő adatot igényel | R2 (figyelőlista), R4 (érkezés) |
| Fiókbejelentkezés, regisztráció | R1-ben a katalógus fiók nélkül is teljes értékű | R2 |
| Vízállás, zsilipvárakozás | Élő/hatósági adatforrás | R4 |
| B2B API, webhooks | Az R1 API belső célra készül | R5 |

### 3.4 Adathátter (milyen adat kell az R1-hez)

| Adat | Honnan | Mennyi | Kockázat |
|---|---|---|---|
| Duna-hajók (ENI, IMO, MMSI, méretek, típus, üzemeltető) | ENI- és hajószám-nyilvántartás, KH | ~3 500 hajó | **közepes** – a nyilvántartás részletessége változó |
| Duna hajótípus-kódok | UN E-rek. 28 alapján, hajószám-adatbázis | ~40 kód | alacsony |
| Balatoni hajók (hajószám, típus, befogadóképesség, üzemeltető) | Közlekedési Hatóság nyilvántartás, üzemeltetők | ~150–250 bejegyzés | **magas** – a Balaton-hajók nem ENI-vel, hanem hajószámmal és névvel azonosítottak, a lista több forrásból áll |
| Balatoni kikötők + kikötőrendek | KH-hirdetmények, üzemeltetők | 70–80 kikötő | közepes |
| Üzemeltetők | Nyilvántartás, cégnyilvántartás | ~300 cég | alacsony |
| Kikötők (Duna), zsilipek, folyószakaszok | Nyilvántartás, Közlekedési Hatóság, Duna-közlöny | ~400 kikötő, ~30 zsilip | közepes |
| UI- és típusfordítások | Saját szerkesztés | ~300 kulcs × 3 nyelv | **közepes** – a német terminológia szakértői ellenőrzést igényel |

**A legfontosabb felismerés a háromnyelvűséghez:** a hajók hivatalos neve latin betűs, egységes (a Dunán és a Balatonon egyaránt), tehát **a hajónevek nem igényelnek fordítást**. A háromnyelvűség terhe a UI-szövegeken, a hajótípus-neveken, a helységneveken és a jogi szövegeken van — ez lényegesen kisebb feladat, mint elsőre látszik. A magyar szerkesztői alapnyelv, az angol technikai másodlagos nyelv, a német piaci nyelv.

### 3.5 Kilépési feltételek (Definition of Done)

**Tartalom**
- [ ] Minden bejegyzett hajónak van neve, típusa, azonosítója (területenként a megfelelő), üzemeltetője és állapota
- [ ] A Duna-katalógusban ≥ 95% a hajók ENI-vel azonosítható
- [ ] A Balaton-katalógusban ≥ 90% a hajók hajószámmal vagy IMO-val azonosítható
- [ ] Minden hajóoldalon látható a forrás és a frissítés dátuma
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

| Kockázat | Valószínűség | Hatás | Mitáció |
|---|---|---|---|
| A Balatoni hajólista nem áll össze egyetlen forrásból | magas | az R1 legnagyobb ismeretlene | Már az R1 elején (2. sprint) a lista forrásait egyeztetni; a hajókat kézzel is be lehet tölteni a szerkesztői felületen |
| A hajószám-adatbázisok licencelése korlátozza a közzétételt | közepes | a katalógus nem indítható | Az adatforrás szerződését az R1 **előtt** rendezni; a `data_source.license_type` mező a sémában erre van |
| A német fordítások szakértelmetlenek | közepes | márkanév-érintettség, visszavonás | Német nyelvi reviewer bevonása; a nem átnézett fordítás státusza látszik a belső felületen |
| A katalógus „üresnek" tűnik térkép nélkül | közepes | a felhasználó nem érti, miért érdemes visszatérni | A katalógust **tartalmi termékként** pozicionálni (kereshető hajólista, szűrés, adatlap), és a terepviszonyokat szövegesen közölni (pl. „Szigetvár–Szekszárd szakasz") |
| A felhasználó élő pozíciót vár | magas | türelmetlenség | A felületen egyértelműen jelezni: „ez a katalógus; az élő követés a következő kiadásban" + értesítéslista a megjegyzésre |
| Túl sok hajó (3 500) gyenge adattal rossz minőséget ad | közepes | hitelességi probléma | Prioritás: a **gyakran közlekedő és AIS-azonosítható** ~1 300 hajó legyen teljes; a többi „korlátozott adattal" jelölést kapjon |

### 3.7 Az R1 becslése

| Sprint | Tartalom | Kimenetel |
|---|---|---|
| 1. | Séma, fordítási infrastruktúra, projekt-alapozás (CI, környezetek, migrációk) | Adatbázis váz, nyelvi kulcsok |
| 2. | **Adatbeszerzés** (Duna + Balaton), szerkesztői felület v1, CSV-import | Valós adat a DB-ben |
| 3. | Katalóguslista, szűrés, rendezés, kereső, hajóadatlap | Működő katalógus (belső) |
| 4. | i18n véglegesítés, SEO, statikus tartalomoldalak, API v1, dokumentáció, hibajegyzet | **R1 kiadás** |

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
