# R1 adat-terv – a hajókatalógus adatháttére

**Verzió:** 1.0 (2026-11-14)
**Kapcsolódó dokumentumok:** [`funkcio-leiras.md`](funkcio-leiras.md) · [`release-terv.md`](release-terv.md) · [`../README.md`](../README.md) (adatbázis terv)

---

## 1. Mi az R1 adata, és mi nem

Az R1 a **katalógus** release. Az adatháttere ezért **leíró (referencia) adat**, nem eseményadat.

| Az R1 adatháttérébe **bekerül** | Az R1 adatháttérébe **nem kerül** (és mikor) |
|---|---|
| `vessel` + `vessel_identifier` + `vessel_i18n` | `position` – élő pozíció (R2) |
| `vessel_type` (+ i18n) | `voyage`, `voyage_stop` (R4) |
| `vessel_alias`, `vessel_cert` | `eta_prediction` (R4) |
| `vessel_service_period` – szezon (Balaton) | `lock_passage` (R4) |
| `operator` (+ i18n) | `water_level` (R4) |
| `port` + `port_i18n` (Duna + Balaton kikötők) | `convoy` – élő konvoj (R2) |
| `marina` (balatoni kikötő-kiegészítők) | `notice`, `event` (R3) |
| `lock` + `lock_i18n` | `vessel_schedule` – menetrend (R3) |
| `river_section` + i18n, `basin` + i18n | |
| `waterway` + i18n | |
| `cargo_type` (+ i18n) | |
| `content_key` + `content_text` – UI- és típusfordítások | |
| `data_source` – minden forrás nyilvántartása | |

**A lényeg:** az R1 adata az, amit **nem lehet élő adatból előállítani** — a hajók hivatalos azonossága, mérete, tulajdonosi köre, engedélye. Ezt kell egyszer, jól, és forrással bevinni. Ami élő adat (pozíció, ETA, zsilipvárakozás), az R2–R4 terméke, és nem lehet előre „letölteni".

---

## 2. Alapelv: minden mezőnek van forrása

> **Nincs olyan mező a katalógusban, aminek nincs megnevezett forrása.** Ha nem tudjuk, honnan származik egy adat, akkor az nem kerül be — üresen marad, és a hiánylista mutatja.

**Forráshierarchia (magasabb = erősebb):**

| Prioritás | Forrás típusa | Használata | Kötelező jelölés |
|:--:|---|---|---|
| 1 | **Hatósági nyilvántartás** (lajstrom, hajóokmány-nyilvántartás) | ENI, hajószám, méretek, tulajdonos, engedély | forrás + dátum |
| 2 | **Üzemeltető saját közlése** (honlap, menetrend, közlemény) | szolgáltatások, kapacitás, szezon, menetrend | forrás + dátum |
| 3 | **AIS statikus adat** (5. típusú üzenet) | hívójel, MMSI, méretek kereszt-ellenőrzése | forrás = feed |
| 4 | **Aggregátor / másodlagos adatbázis** | kiegészítő adatként, ellenőrzéshez | forrás + licenc |
| 5 | **Szerkesztői kiegészítés** | ha nincs más forrás, de a szerkesztő tudja | forrás = „szerkesztői" + indoklás |

**A `data_source` tábla ezt kötelezően rögzíti:** minden hajórekordhoz van `source_id`, minden mezőváltozás az `audit_log`-ban. A hajóoldalon a felhasználó látja: *"Forrás: Közlekedési Hatóság hajólajstrom, 2026. 03. 12."*

---

## 3. Adatforrás-mátrix – Duna

| Adatkör | Elsődleges forrás | Hozzáférés | Formátum | Frissítés | Kockázat |
|---|---|---|---|---|---|
| **ENI + magyar hajóadatok** (szám-jel, jelleg, rendeltetés, működési terület, méretek, vízkiszorítás, hajtóberendezés, tulajdonos) | Közlekedési Hatóság **hajólajstrom** + **hajóokmány-nyilvántartás** (a lajstromba bejegyzett adatkör jogszabályban rögzített) | **Adatszolgáltatási kérelem** a Hajózási Hatósági Főosztálynak (`hhf@tim.gov.hu` – a hatóság közzétett adatszolgáltatási csatornája) | XLSX / PDF, kézi bevitel | negyedévente + eseményvezérelt | **közepes** – a hatóság nem publikál nyílt adatkészletet, ezért az írásos megkeresés a kulcs |
| **ENI – nemzetközi hajók** | Az illetékes állami ENI-kiosztó hatóságok; az EU-s belvízi elektronikus hajójelentés referenciaadatbázisa (ERDMS) | nehéz, országenként eltérő | – | ritka | **magas** – teljes lefedettség nem biztosítható R1-ben |
| **MMSI + hívójel + AIS-méretek** | AIS feed statikus üzenetei (R2-től); R1-ben: gyűjtött statikus snapshot | előfizetéses feed | NMEA / JSON | hetente | közepes – a feed a licenc kötöttsége miatt R2 feladat |
| **Nemzetközi hajószám** | Nemzeti nyilvántartások (pl. DE: WSV hajószám-nyilvántartás, AT, SRB, RO, BG) | hatóságonként eltérő | | ritka | közepes |
| **Hajótípus (UN E-rek. 28)** | hajószám-adatbázis + AIS `type` mező | nyilvános | kódtábla | ritka | alacsony |
| **Flotta-összetétel (ellenőrzés)** | Danube Commission éves navigációs statisztika | nyilvános, PDF | PDF/Excel | évente | alacsony – rekordonkénti adat nincs benne, csak ellenőrzésre jó |
| **Kikötők** | KH kikötő-nyilvántartás + OSM `industrial=port` + terminál-operátörök | nyilvános | API/CSV | félévente | közepes |
| **Zsilipek** | KH + ERDMS hajózási referenciaadatok | nyilvános | táblázat | ritka | alacsony |
| **Üzemeltetők** | Nemzeti cégnyilvántartás + üzemeltetői honlapok | nyilvános | API / kézi | negyedévente | alacsony |
| **Folyószakaszok, vízút** | Duna-közlöny, VTS, hatósági tájékoztatók | nyilvános | kézi | évente | alacsony |

**Következtetés:** a Duna-katalógus **nagyrészt magyar hatósági adaton** és a nemzeti nyilvántartásokon áll. Ez az R1 legfontosabb kockázata, és a 2. sprint első hetében meg kell indítani az írásos adatkérést — a válaszidő határozza meg a R1 ütemezését.

---

## 4. Adatforrás-mátrix – Balaton

| Adatkör | Elsődleges forrás | Hozzáférés | Formátum | Frissítés | Kockázat |
|---|---|---|---|---|---|
| **Balatoni hajólajstrom** (nagyhajó, komp, úszómű, úszómunkagép, kishajó) | Közlekedési Hatóság | **Adatszolgáltatási kérelem** | XLSX / PDF | szezon előtt | **magas** – a Balatoni flotta töredékesen dokumentált, és nem ENI-vel azonosított |
| **Kikötők + kikötőrendek** | Közlekedési Hatóság **„Hajósoknak szóló hirdetmény"** és a Balatoni Hajózási Zrt. kikötőrendjei | nyilvános, PDF | PDF | évente + szezon előtt | közepes |
| **Hajók szolgáltatásai, kapacitás, fedélzet** | Üzemeltetők flottaoldalai (BAHART, Balatonmáriafürdő, Siófok, Tihany, Füred, Veszprém és további szolgáltatók) | nyilvános | kézi bevitel a szerkesztői felületen | szezon előtt | **magas** – nincs központi lista, minden üzemeltető másképp közöl |
| **Menetrend** | Üzemeltetők heti menetrendje | nyilvános | PDF / táblázat | szezon előtt | közepes – R3-adat, de a szezonlogikához már R1-ben kell a szezon határai |
| **Üzemeltetők** | Üzemeltetői honlapok + cégnyilvántartás | nyilvános | kézi | évente | alacsony |
| **Vitorlások, kishajók** | Magyar vitorlásszövetségi nyilvántartás | korlátozott | – | – | **magas** – nyitott kérdés, nem döntöttük el |
| **Balatoni közlekedési rend, meteorológiai tájékoztató** | KH hirdetmények | nyilvános, PDF | PDF | hetente a szezonban | közepes – R3-adat |

**Következtetés:** a Balatoni katalógus **szerkesztői munkával** készül el: hatósági alapadat + üzemeltetői információ kézi bevitel. Ez ~150–250 hajó, tehát kétszer-háromszor kisebb mint a Duna-katalógus, és emberi munkával megoldható. A kockázat itt nem a mennyiség, hanem a **hatósági lista elérhetősége** és az **üzemeteltetői együttműködés**.

---

## 5. Mezőenkénti kitöltési terv

### 5.1 Duna-hajó

| Mező | Forrás | Várható kitöltöttség | Megjegyzés |
|---|---|---|---|
| ENI | hatósági lajstrom | 95% | a nem magyar hajóknál hiányozhat |
| IMO-szám | hajószám-adatbázis | 40% | csak a nemzetközi forgalomban járóknál van |
| MMSI | AIS | 90% | a bárkáknál nincs – helyette a konvojt vezető hajója |
| Nemzetközi hajószám | hajószám-adatbázis | 85% | |
| Hajónév | lajstrom / AIS | 98% | latin betűs, egységes – **nem fordítandó** |
| UN E-rek. 28 típuskód | hajószám-adatbázis | 90% | |
| Szállítási kategória | származtatott a típuskódból | 95% | |
| Hossz / szélesség | lajstrom | 95% | |
| Max. merülés | lajstrom (vízkiszorítás) | 90% | |
| Bruttó tonnage | hajószám-adatbázis | 85% | |
| Teherkapacitás (DWT) | hajószám-adatbázis | 80% | csak teherhajnál értelmes |
| Motorteljesítmény | hajószám-adatbázis | 75% | |
| Építési év | hajószám-adatbázis | 80% | |
| Üzemeltető / tulajdonos | lajstrom (tulajdoni lap) | 90% | |
| Zászlóállapot | lajstrom | 95% | |
| Közlekedési engedély hatályossága | KH | 60% | a többi a lajstromból vagy a statuszból |
| Állapot (közlekedik / áll) | származtatott | 85% | AIS-alapú származtatás R2-ben, R1-ben kézi |
| Leggyakoribb szakasz | AIS-ből származtatott | R2 | R1-ben a lajstrom „működési terület" mezője |

### 5.2 Balatoni hajó

| Mező | Forrás | Várható kitöltöttség | Megjegyzés |
|---|---|---|---|
| Nemzetközi hajószám | KH lajstrom | 70% (a nagyhajóknál 100%) | kishajóknál nincs |
| Nemzeti nyilvántartási szám | KH lajstrom | 90% | |
| IMO-szám | lajstrom | 20% | csak a nemzetköti hajóknál |
| Hajónév | lajstrom / üzemeltető | 98% | latin betűs – **nem fordítandó** |
| Kategória (nagyhajó / komp / kishajó / munkagép / vitorlás) | KH lajstrom | 95% | |
| Befogadóképesség (fő) | KH lajstrom / üzemeltető | 85% | |
| Hossz / szélesség | lajstrom | 90% | |
| Szolgáltatások (WC, étterem, akadálymentes, védett hely) | üzemeltető | 70% | kézi, ellenőrizendő |
| Üzemeltető | KH / üzemeltető | 95% | |
| Szezon határai | üzemeltető | 80% | a szezononkénti változás miatt a `vessel_service_period` **időbeli** |
| Medence | szerkesztői meghatározás | 90% | a hajó fő járási területe |
| Kikötő | üzemeltető / KH | 70% | |

---

## 6. Azonosítók és formátum-ellenőrzés

### 6.1 Szerkezeti szabályok

| Azonosító | Szabály | Ellenőrzés |
|---|---|---|
| **ENI** | 8 számjegy. Az **első 3 számjegy az ENI-kiosztó hatóság kódja**, az utolsó 5 a sorozatszám. **Nem azonos a MID-del** (Magyarország MID-je 243, az ENI-hatósági kód más tartomány) | 8 számjegy; a 3 számjegyes hatóságkód létezik az ENI-kiosztók listáján |
| **MMSI** | 9 számjegy, az első 3 a **MID**. Belvízi hajónál a 4. számjegy `0` (ITU-R M.585) | 9 számjegy; MID létezik; a 4. számjegy `0` **figyelmeztető**, nem elutasító szabály (kivételek vannak) |
| **MID-ellenőrzőlista** (Duna-országok) | AT 203 · BG 207 · HR 238 · HU 243 · DE 211 és 218 · MD 214 · RO 264 · RS 279 · SK 267 · UA 272 | MMSI első 3 számjegye a listában van |
| **IMO-szám** | 7 számjegy, az utolsó **ellenőrző számjegy** (a számjegyek súlyozása 7-től 2-ig, maradék 10 → 0, különben 10 − maradék) | teljes ellenőrzőszám-algoritmus |
| **Nemzetközi hajószám** | legfeljebb 7 karakter, nagybetűk és számjegyek | regex + karakterkészlet |
| **UN/LOCODE** | 5 karakter: 2 karakteres országkód + 3 karakteres helykód | forma + létezés a hivatalos listában |
| **ENI-duplikátum** | egy ENI-hez egy hajó | **elutasító** |

### 6.2 Cross-field konzisztencia-szabályok

| Szabály | Szint |
|---|---|
| `length_m > beam_m` | elutasító |
| `draught_max_m < 0,35 × length_m` | figyelmeztető (a Duna 12 m-es hajóinál a merülés ~4 m, de a széles hátú bárkáknál a 0,35 alacsony – pontosítás a valós adatok alapján) |
| `passenger_capacity > 0` ⇔ hajótípus = személyhajó | figyelmeztető |
| `deadweight_t > 0` ⇔ szállítási kategória = teher | figyelmeztető |
| Személyhajó → `passenger_capacity` kötelező | elutasító |
| `operating_area = 'balaton'` ⇔ nincs ENI | elutasító |
| `operating_area = 'duna'` → legalább egy ENI vagy MMSI | elutasító |
| Duplikált hajónév | **figyelmeztető** – ugyanaz a név több hajón is lehet (átnevezés, új hajó ugyanazzal a névvel) |
| Üzemeltető nevéből a `operator` rekord | fuzzy illesztés, kézi megerősítés |

### 6.3 Illesztési (entity resolution) sorrend az új forrás beemelésekor

1. **ENI pontos egyezés** – azonnali, automatikus
2. **IMO pontos egyezés** – azonnali, automatikus
3. **MMSI pontos egyezés** – azonnali, automatikus
4. **Nemzetközi hajószám pontos egyezés** – azonnali, automatikus
5. **Név + hossz (±10%) egyezés** – automatikus, de **naplózva**; a mezőket nem írja felül
6. **Név fuzzy egyezés (trigram hasonlóság > 0,8)** – **emberi jóváhagyás**; a szerkesztő a felületen összeveti a két rekordot
7. **Nincs illesztés** → **új hajó**, emberi jóváhagyással jön létre

> **Fontos:** az R1-ben **nincs automatikus rekord-összevonás**. Két hajót nem szabad automatikusan egyesíteni, mert a téves egyesítés rosszabb, mint a duplikátum — a duplikátum jelezhető, az összevonás nem.

---

## 7. A bevitel folyamata

```
nyers forrásfájl          →  0. megőrzés (source_id-hoz kötve, újrafuttatható)
        ↓
parse                     →  1. staging (minden mező stringként, nyersen)
        ↓
normalizálás              →  2. vezető nullák, whitespace, kis/nagybetű, egység, dátum
        ↓
validáció                 →  3. hibanapló (sor- és mezőszinten, nem dobódik el)
        ↓
illesztés                  →  4. az ENI→IMO→MMSI→hívójel→név sorrend szerint
        ↓
upsert                    →  5. temporális zárás (valid_to) + új sor
        ↓
QA + emberi jóváhagyás    →  6. az új hajók és a kétséges illesztések jóváhagyása
        ↓
publikálás                →  7. a jóváhagyott rekord válik „published" állapotúvá
```

**Fájlok és eszközök:**
- A nyers forrásfájl (XLSX/PDF/CSV) **a `data_source` rekordhoz kötve megőrzendő** – a feldolgozás bármikor újrafuttatható, és a licenc/audit miatt is kell.
- A bevitel **CSV-en keresztül** történik a szerkesztői felületre (F-ADM-07) – ez a kézi források miatt a reális út, nem a nagy betöltő.
- Minden futás a `job_run` táblába ír: bemenő sorok, elutasított sorok, létrehozott/frissített rekordok.

**Idempotencia:** a feldolgozás újrafuttatható anélkül, hogy duplikálna. A kulcs az azonosító (`vessel_identifier`), nem a sorszám.

---

## 8. Adatminőségi mérőszámok (R1 átvételi küszöbök)

| Metrika | Küszöb |
|---|---|
| ENI-duplikátum a Duna-katalógusban | **0** |
| MMSI-duplikátum | **0** (üres kivételével) |
| ENI-vel azonosítható Duna-hajók aránya | ≥ 95% |
| Hajószámmal vagy IMO-val azonosítható Balatoni hajók aránya | ≥ 90% |
| Hajó nevének kitöltöttsége | ≥ 98% |
| Típus kitöltöttsége | ≥ 90% |
| Méret (hossz + szélesség) kitöltöttsége | ≥ 95% |
| Üzemeltető kitöltöttsége | ≥ 90% |
| Forrásjelölés a kézzel módosított mezőknél | **100%** |
| Nyelvi hiánylista: UI-szövegek | **0** |
| Nyelvi hiánylista: hajótípus-nevek | **0** |
| Nyelvi hiánylista: kikötő- és zsilipnevek | ≤ 5% (a többi a forrásnyelven marad, jelöléssel) |
| Elutasított sorok aránya egy beviteli futásban | ≤ 2% (a többi emberi javításra vár, nem dobódik el) |
| Felhasználói észrevételek feldolgozása | a beérkezéstől 5 munkanapon belül |

---

## 9. Mi kerül be automatikusan, mi emberi jóváhagyással

| Automatikus (jóváhagyás nélkül) | Emberi jóváhagyással |
|---|---|
| Hatósági adatsor beemelése azonosító mezőkkel | **Új hajó létrehozása** |
| Mezőfrissítés, ha az azonosító egyértelmű és az érték nem üres | **Rekord-összevonás** (7. pont, illesztés) |
| Típuskód-változás (UN E-rek. 28 alapján) | Minden kézzel írt mező első betöltése |
| Fordítások gátolt státuszba (publikálás külön lépés) | Fordítás publikálása |

**Elv:** *az automatizmus soha nem töröl és nem ír felül nem üres értéket üresre, és soha nem von össze rekordokat.* Az üres → érték irány automatikus, az érték → más érték irány naplózott, az érték → üres irány soha.

---

## 10. Az R1 adatkészlet elfogadási checklist

Tartalom:
- [ ] A Duna-katalógusban minden hajótípus (teher száraz, teher folyadék, vegyes, bárka, toló, vontató, személy, munkahajó, kishajó, uszály) legalább 3 példánnyal szerepel
- [ ] A Balaton-katalógusban a nagyhajók, kompok, kishajók és munkagépek mind jelen vannak
- [ ] Minden hajótípusnak van háromnyelvű neve
- [ ] Minden kikötőnek és zsilipnek van háromnyelvű neve
- [ ] A `vessel_service_period` a Balatoni hajóknál kitöltött (szezon), a Duna-hajóknál `year_round`
- [ ] Az `operator` rekordok nem duplikáltak (név + ország szinten)
- [ ] A `marina` rekordok hivatkoznak a kikötőrend-re

Megkötés:
- [ ] A nyers forrásfájlok megőrzöttek és visszatöltésre alkalmasak
- [ ] A bevitel újrafuttatható duplikátum nélkül
- [ ] Minden `data_source` rekord tartalmaz jogalapot, licencet és frissítési gyakoriságot
- [ ] A `content_text` státuszok: a hu és en minden kulcsnál `published`, a de-nél a hiányzó elemek jelölve

Felület:
- [ ] A kereső ENI-re, IMO-ra, MMSI-re, hajószámra, névre talál (a Duna- és a Balaton-keresés nem szivárog át)
- [ ] Minden hajóoldalon látható a forrás és a frissítés dátuma
- [ ] A hiányzó fordítás jelölést kap, nem üres mezőt

---

## 11. Kockázatok és a konkrét mitigációs lépés

| Kockázat | Hatás | Konkrét lépés (a 2. sprint első hete) |
|---|---|---|
| A KH nem ad adatot, vagy lassan | az R1 késik | Írásos megkeresés a `hhf@tim.gov.hu` csatornán, a lajstrom és a hajóokmány-nyilvántartás **részleges** (Egy adatkészlet) adatkérésével – a részleges is elindíthatja a katalógust |
| A nemzetközi ENI-lista nem elérhető | a Duna-katalógus 60–70%-a ENI nélkül | A magyar ENI-vel rendelkező hajók + AIS-azonosítható hajók adják a teljes lefedettséget; a hiányzókat a nemzeti hajószám-adatbázisokból pótoljuk |
| A Balatoni lista hiányos | gyenge Balaton-katalógus | Két megközelítés együtt: hatósági lista **+** üzemeltetői oldalak kézi begyűjtése (~15 üzemeltető) |
| A forrásfájlok formátuma változik | a bevitel elbukik | A bevitel a `data_source` + fájlverzió alapján fut; a formátumváltozás új `source_file` bejegyzés, nem kódmódosítás |
| A kézi bevitel hibás | bizalomvesztés | Kötelező forrás- és dátummező; mezőnkénti hibajegyzet a UI-on; a felhasználói észrevétel visszacsatol |
| A fordítás nem készül el | a 3 nyelv ígéret sérül | A német fordítási kapacitás **az R1 2. sprintjében** eldöntendő; a hiánylista nyilvános belső dashboard |
| A jogszabályi háttér változik | mezők értelmezése elcsúszik | A `data_source` és a `vessel` mezők dokumentálva, a jogszabály-hivatkozás a rekord mellett |

---

## 12. A konkrét következő 10 munkanap

| Nap | Feladat | Kimenet |
|---|---|---|
| 1–2 | Adat-hozzáférési megkeresések megírása és elküldése (KH: hajólajstrom + hajóokmány-nyilvántartás + Balatoni hajólajstrom; KH: kikötőrendek) | 3 levél, válaszhatáridő megkérve |
| 1–3 | A `data_source` tábla feltöltése a lehetséges forrásokkal (név, típus, jogalap, formátum, várható mennyiség) | 12–15 forrásrekord |
| 3–5 | A mezőlista véglegesítése a funkcióleírás 6. fejezete alapján | Mezőspecifikáció |
| 4–6 | A `vessel_type` kódkészlet véglegesítése (UN E-rek. 28 + Balatoni kategóriák) + a háromnyelvű nevek | ~45 típus × 3 nyelv |
| 5–8 | A `content_key` lista véglegesítése (UI-szövegek) és a hu + en szövegek megírása | ~300 kulcs × 2 nyelv |
| 6–9 | Az üzemeltetői lista összeállítása (Duna + Balaton) a honlapokról | ~300 üzemeltető |
| 7–10 | A validációs szabályok kódolása a séma-ellenőrzésekbe (CHECK constraint + betöltő szabályok) | Validátor |
| 8–10 | A Balatoni nagyhajók kézi lista (~50–70 hajó) üzemeltetői oldalakról | Első Balaton-adathalmaz |

---

## 13. Forráshivatkozások

- Közlekedési Hatóság, Hajózási Hatósági Főosztály – a hajólajstrom, a hajóokmány-nyilvántartás és az adatszolgáltatás (`hhf@tim.gov.hu`) – [KH](https://www.kozlekedesihatosag.kormany.hu/hu/haj%C3%B3z%C3%A1si-hat%C3%B3s%C3%A1gi-f%C5%91oszt%C3%A1ly-hhf-bemutatkoz%C3%A1s)
- Közlekedési Hatóság – „Hajósoknak szóló hirdetmény" és tájékoztatók (Balaton, kikötőrendek) – [dokumentumtár](https://www.kozlekedesihatosag.kormany.hu/hu/dokumentumtar?delta=60&start=22&category=66908&modified=past-year)
- 5/1974. (V. 21.) KPM rendelet a hajózásról – a hajójegyzékbe bejegyzett adatok köre (jelleg, méretek, vízkiszorítás, tulajdonos) – [FAOLEX](https://faolex.fao.org/docs/pdf/hun27974.pdf)
- ITU-R M.585 – MMSI szerkezet, MID-értékek – [ITU](https://www.itu.int/en/ITU-R/terrestrial/Pages/by-categories-faq.aspx?categorizedby=17)
- Közlekedési Hatóság – Balatoni meteorológiai megfigyelő rendszer hirdetmény (a 4 szigetüzemű állomás) – [KH](https://www.kozlekedesihatosag.kormany.hu/documents/66222/66315/016_Ba_2025.+sz%C3%A1m%C3%BA+Haj%C3%B3soknak+sz%C3%B3l%C3%B3+hirdetm%C3%A9ny+-+a+Balatonon,+t%C3%B3k%C3%B6z%C3%A9pen+m%C5%B1k%C3%B6d%C5%91+meteorol%C3%B3giai+megfigyel%C5%91+%C3%A9s+t%C3%A1j%C3%A9koztat%C3%B3+rendszer+%C3%A1llom%C3%A1sainak+n%C3%A1ri+id%C5%91szakra+t%C3%B6rt%C3%A9n%C5%91+%C3%A1llap%C3%ADt%C3%A1s%C3%A1r%C3%B3l.pdf/e2936517-2b3f-383d-d102-7d868eb6350e)
- Balatoni flotta összetétele (4 komp, 29 személyhajó, 17 szolgálati hajó, 17 uszály, 16 úszó munkagép, 70–80 kikötő) – [balatonihajok.hu](http://www.balatonihajok.hu/technika/hajozas)
- BAHART hajóflotta (nagyhajók, nosztalgiahajók, kapacitások) – [bahart.hu](https://bahart.hu/hu/bahart-hajoflotta)
- Balatonmáriafürdő – 19 személyhajó, 6 komp, 18 kikötő – [menetrend](https://www.balatonmariafurdo.hu/wp-content/uploads/2025/03/BH_Menetrend_kiadvany_2024.pdf)
