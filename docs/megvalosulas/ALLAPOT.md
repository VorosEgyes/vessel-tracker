# Állapot – Vessel Tracker (Duna és Balaton)

**Frissítve:** 2026-11-19
**Repo:** https://github.com/VorosEgyes/vessel-tracker
**Aktuális munkaterület:** a **Pi + rádió megépítése** (a Budapesti AIS-vevő)

> Ez a dokumentum a **„hol állunk"** hivatkozási pont: mi kész, mi fut,
> mi a következő lépés, és hol van minden. Frissítése a munkafolyamat
> minden fontos állapotváltásakor.

---

## 1. A projekt egy mondatban

**Hajókövető a Dunán és a Balatonon** — az R1 release egy **statikus
hajókatalógus** (térkép és élő adat nélkül), három nyelven (hu/de/en).

**Az R1-0 előkészítő fázis** (3–6 hónap, a `release-terv` 3.4.1)
még **nincs elkezdve** — ez a mostani munkaterület.

---

## 2. Mi a kész

### 2.1 A tervezési dokumentáció (a repóban, 17 fájl)

| Dokumentum | Tartalom | Státusz |
|---|---|---|
| `README.md` | az adatbázis-terv v1.3 — a séma, a jogszabályi háttér, a forrásmátrix | kész |
| `docs/funkcio-leiras.md` | a funkcióleírás (a F-xxx követelmények) | kész |
| `docs/release-terv.md` | a release-terv (R1–R5) | kész |
| `docs/r1-adat-terv.md` | az R1 adat-terv (a forrásmátrix, a validációs szabályok) | kész |
| `docs/ais-vevo-terv.md` | a saját AIS-vevőhálózat terve (a lefedettség, a hardver, a mérési protokoll) | kész |
| `docs/ingest-terv.md` | az adatút (a Pi → MQTT → ingest → Postgres) | kész |
| `docs/pi-eloallitas.md` | **a Pi előállítása lépésről lépésre** (28 lépés) | kész |
| `docs/measurement_2026-11-22.md` | **a bud01 vevő első mérési órája** (44 000 üzenet, 199 hajó, 106 lámpa, a go/no-go 69,8%) | kész |
| `docs/sema-core.mmd`, `docs/sema-irodalom.mmd` | a Mermaid séma-ábrák | kész |

### 2.2 Az implementációs terv-sorozat (`docs/megvalosulas/`)

| # | Terv | Státusz |
|---|---|---|
| 01 | technológiai stack és projektstruktúra | **v1.3** — 2 körű swarm review, a 2. kör 17 findingje javítva |
| 02 | adatbázis-séma (DDL v1.1) | **v1.5** — 113 finding, a 10 blokkoló javítva, **futtatva és tesztelve** (17/17 zöld) |
| 03 | API-specifikáció | **v0.3** — 96 finding (3 reviewer + verifier), **mind javítva** |
| 04 | AIS-parser specifikáció | **v1.0** — 64 finding, **mind javítva** (a mérés alapján) |
| 05 | frontend-arkitektúra | v0.1 — draft |
| 06 | szerkesztői felület | v0.1 — draft |
| 07 | CI/CD és környezetek | **v0.1** — draft (új) |
| 08 | teszt-stratégia | **v0.1** — draft (új, a mérési adatból) |
| 09 | üzemeltetés és observability | **v0.1** — draft (új, a watchdog) |

**A sorozat teljes (01–09).** A 02–04 terv swarm review-zott; az 05–09
draft, a review-juk a következő kör.

### 2.3 A 02-es DDL — a legjobban validált rész

**A séma futtatva van valódi PostgreSQL 17-en:**

| Objektum | Darabszám |
|---|---|
| Tábla | 71 |
| Index | **157** |
| FK constraint | **124** |
| CHECK constraint | **372** |
| Particionált tábla | 3 (`ais_message_raw`, `water_level`, `position`) |
| Trigger-definíció | 28 |
| **A referenciaadat-seed** | **89 hajótípus** (a magyar nevekkel), 3 nyelv, 24 ország, 11 folyószakasz, 4 medence, 8 teherfajta, 5 üzemeltető |

**17 funkcionális teszt, mind zöld** — a `db/tools/validate_ddl.py`
a terv markdown-ból kicsomagolja a DDL-t, lefuttatja egy élő
PostgreSQL-en, majd füstöt hajt végre.

**A validáló maga indítja el a postgres-t** (a `pgserver`) és a
**`--plan` kapcsolóval bármely tervet validál** (a live helyett a
benyújtott fájlt olvassa).

---

## 3. Mi fut

| Mi | Hol | Állapot |
|---|---|---|
| **A bud01 AIS-vevő** | a Pi-n (`ais-receiver.service`) | ✅ **fut** 2026-11-22 19:19 óta — 38 000+ üzenet/óra, 199 hajó |
| **A heti lehúzás** | a Pi cron → a NAS (`/opt/data/martin/work/ais-data/`) | ✅ **működik** (a `command=` korlátozással) — hétfő 04:17-kor |
| **A mérési elemző** | a NAS-on (`analyze_measurement.py`) | ✅ fut — a read-only (`immutable=1`) nyitás nem hagy `-wal`/`-shm` fájlokat |
| **A 30 napos mérés** | a `bud01` telephelyen | **2026-12-22-ig** — a go/no-go küszöbön (69,8% ≥ 50%) |

**A mérés első órája:** 44 000 üzenet, 199 hajó (78 neves), 106
navigációs lámpa, 767 FI 10 (ENI) üzenet, **69,8% földrajzi lefedettség**
→ **a go/no-go küszöbön** (a `docs/measurement_2026-11-22.md`).

> **A 03-as és a 04-es swarm review lezárult** — a findingek mind
> be vannak írva (a 03 → v0.3, a 04 → v1.0).

---

## 4. A következő munkaterület: a Pi + rádió

### 4.1 Mi a cél

**A Budapesti AIS-vevő** (R1-0, a mérési fázis első lépése) — a
`docs/ais-vevo-terv.md` 10. fejezete és a `docs/pi-eloallitas.md`
alapján.

**A cél:** egy működő AIS-vevő, ami a NMEA üzeneteket a szerverre
küldi — és **30 napig mér** (a `ais-vevo-terv.md` 5. fejezete:
a go/no-go).

### 4.2 A hardver

| Elem | Specifikáció | Ár (EUR) | Állapot |
|---|---|---|---|
| **Raspberry Pi 4** | a gyorsabb processzor, a 2× USB 3.0 és az 5 GHz-es Wi-Fi miatt | ~50 | ✅ **van** |
| **SD-kártya** | 32 GB, A2 osztály (a wear levelling miatt) | ~10 | ✅ **van** (a DB 4,1 GB / 29 GB = 15%) |
| **AIS USB dongle** | RTL2832U (a mérésben **PPM 7–8** — TCXO nélkül) | ~25–35 | ✅ **van** — a **TCXO-s (0,5 ppm) verzió a következő méréshez** |
| **162 MHz antenna** | AIS-re hangolt, fix, függőleges polarizáció, ~3 dB | 80–250 | ✅ **van** |
| **162 MHz SAW szűrő** | a túlterhelés és a LO-szivárgás csökkentésére | ~20 | ⬜ **később** — a mérés szűrő nélkül is indulhat |
| **Koax** | RG-58/U, **max. ~10 m** (a hosszú kábel tönkreteszi a jelet) | 20–60 | ✅ **van** (a kék USB 3.0 portban működik) |
| **Táp** | a Pi 4 hivatalos 5V/3A | 30–60 | ✅ **van** |
| **UPS** (power bank) | a tápkiesés = adatlyuk | 30–60 | ⬜ **beszerzendő** |
| **Hűtés** | a Pi és a dongle is melegszik (a PPM driftel) | ~10 | ⬜ **beszerzendő** |

**A telephely:** Budapest, 3. emelet, a parttól ~2 km-re (a
`ais-vevo-terv.md` 10.1: a rádióhorizont ~14,3 km, a **hasznos
folyólefedettség ~15–20 km**).

**A legfontosabb elhelyezési kérdés:** a **tető fölé 3–5 m-rel** kerül
az antenna → a horizont 14,3 km-ről ~17 km-re nő (**+2–3 km mindkét
irányban**).

### 4.1a A megépítés állapota (2026-11-22)

| A hardver | Állapot |
|---|---|
| **Raspberry Pi 4** | ✅ van (a 3B+ helyett — a gyorsabb processzor, a 2× USB 3.0 és az **5 GHz-es Wi-Fi** miatt) |
| SD-kártya (32 GB) | ✅ van |
| RTL2832U USB dongle | ✅ van |
| Antenna | ✅ van |
| **162 MHz SAW szűrő** | ⬜ **később** — a mérés szűrő nélkül is indulhat |
| **5V/3A táp** | ✅ van (a Pi 4 hivatalos tápegysége) |

**Az OS telepítve** (2026-11-22): a Raspberry Pi OS Lite (64-bit),
Debian trixie, a **2026-10-06** build. A kártyára a `cloud-init` írta be
a beállításokat:
- a hostname: **`bud01`**
- a felhasználó: **`miklos`** (a `sudo` csoportban, jelszó nélkül)
- az **SSH-kulcs** (a Mac kulcsa) → ssh-val belépek
- a **Wi-Fi**: `Pres-iot` (a hálózat a `network-config`-ban)
- a tűzfal: a 22 (SSH), a 8080 (a helyi web-térkép) és a 8100 (a helyi
  NMEA) nyitva a LAN-on

**A telepítő scriptek** a repóban (`scripts/ais-receiver/`):
`install_pi_os.sh` (az OS-telepítés), `make_cloudinit.sh` (a
cloud-init fájlok), `install_ais_receiver.sh` (az SDR), a mérés- és
elemzőscriptek.

**A tanulságok a telepítésből (a teljes lista a
`scripts/ais-receiver/PI-TELEPITES.md`-ben):**
- a hivatalos `.sha256` a **tömörített** képre vonatkozik (a `.img.xz`),
  nem a kitömörített `.img`-re
- a `sudo` a Macen **megoldja a macOS „removable volumes"
  engedélykérdését** is (az Imager CLI `sudo` alatt közvetlenül nyitja
  a lemezt)
- a cloud-init `network-config`-nek a **`network:`** gyökéren kell lennie,
  `renderer: NetworkManager`-rel és `regulatory-domain`-nel
- az **`ssh` fájl a boot partíción** kötelező (különben az `sshd` nem
  indul el)
- az SSH-kulcs a felhasználó **`users:` blokkjában** kell (nem top-level)
- a dongle a **kék USB 3.0 portban** (a fekete 2.0-ban `error -71`)
- az AIS-catcher v0.71-ben a `-D` paraméterei megváltoztak:
  `V ON MSGS ON` → **`state ON position ON static ON nmea ON`**,
  és a DB-sémát a **`create_sqlite.sql`** betöltéssel kell létrehozni

### 4.1b A mérés állapota (2026-11-22 21:35)

**A 30 napos mérés ELINDULT** a `bud01` telephelyen:

| | |
|---|---|
| A vevő | `ais-receiver.service` — **active**, boot után auto-indul |
| A nyers adat | `/var/lib/ais/ais.db` (SQLite), `RETENTION 35` nap |
| Az üzenetek | ~300 az első percekben (Msg 1/2/5/20/23) |
| A hajók | 91 különböző MMSI az első 10 percben |
| A PPM | **8** (a kalibráció 25 percet futott; a 13–15 az átmeneti szakasz volt) |
| A heti lehúzás | hétfő 04:17-kor → **a NAS közvetlenül** (`/opt/data/martin/work/ais-data/`) — **a Mac kimarad a láncból** (nem mindig van bekapcsolva; a NAS a Pi-ról 4,5 ms alatt elérhető) |
| A web-térkép | `http://192.168.0.2:8080` |

**A döntő teszt még hátra van:** a **belvízi FI 10** üzenetek (ezen múlik az
ENI, azaz a katalógus) — a lakástól 2 km-re nem várható. **A tetőn vagy a
Duna-parton kell megmérni** (a `ais-vevo-terv.md` 10.1: a tető 3–5 m-rel
magasabban +2–3 km rádióhorizont).

**A szűrő nélkül a mérés használható**, de a jel/zaj arány gyengébb —
a szűrő megvásárlása a mérés után dönthető el (a `docs/ais-vevo-terv.md`
szerint a szűrő a túlterhelést és a LO-szivárgást csökkenti).

### 4.1c Az első óra eredménye (2026-11-22 21:30)

**A vevő helye: 47,5755205 N, 19,046013 E** (a pesti felső városrész,
**a Dunától 2,88 km-re**).

| Metrika | Érték |
|---|---|
| Az üzenetek | **37 457** (egy óra alatt) |
| A csatornák | A: 12 031 + B: 7 862 — **mindkettő működik** |
| A PPM | −6,1 átlag |
| A jelerősség (stdout JSON) | −1,5 … −14,8 dB — **kiváló** |
| A hajók | **199** |
| **A magyar hajók** | **63** (21 771 üzenet), 2,8–14,7 km |
| A nemzetközi hajók | 11 (3 343 üzenet), 2,9–13,0 km |
| A Duna navigációs lámpái | **108 „belső" AIS-állomás** (1592–1728 km) |
| **A FI 10 üzenetek** | **767** — **az ENI-k elérhetők!** |
| **A földrajzi lefedettség** | **69,8%** a Duna-korridorban |

**A go/no-go kritérium** (a `docs/ais-vevo-terv.md` 5.3): a lefedettség
≥ 50% → **a saját vevőhálózat (F1, 3 site) azonnal építhető**. A mérés
**69,8%-ot** ad — **a küszöbön felül**.

**A látott hajók között:** `GONDOLA` (ENI 8601836 — az egyetlen, aminek
ENI-je van), `AQUINCUM`, `ATTILA`, `BAKONY`, `BOGDANY`, `BUDAPEST`,
`CITADELLA`, `DUNA` (98×24 m), `ESZTERGOM`, `EUROPA`, `GROF SZECHENYI`,
`ISTER`, `LAGYMANYOS`, `MILLENNIUM 2`, `PRIMUS`, `RAKOCZI`, `SIRONA`,
`VISEGRAD`, `WIKING`, `ZIN URU` — és a nemzetközi forgalom:
`DOUCE FRANCE` (francia), `KEPLER` + `RUBIKON23` (tankhajók),
`STADT WIEN` (osztrák), `VIKING AEGIR`/`VIKING BRAGI`/
`TRAVELMARVEL VEGA` (horvát-osztrák), `SLUIZER` (holland),
`HORISHNI PLAVNI` (ukrán), `RIVER DIVA` (luxemburgi).

**A tudatos döntés (2026-11-22): a jelerősség kimarad a DB-ből.**
A v0.71-es AIS-catcher a `-M TD` flaggal számolja a jelerősséget (a
stdout JSON-ban megvan), **de a DB-be nem írja** — a `DatabaseOutput`
a `TAG.level`-t a JSON-stream útvonalon nem kapja meg. A mérés szempontjából
ez nem kritikus: a go/no-go a lefedettségen alapul, a szűrő kiválasztása
a `msg/hajó` arányból dönt. A részletek a
`scripts/ais-receiver/PI-TELEPITES.md`-ben.

**Az elkészült telepítő- és mérőscriptek** (`scripts/ais-receiver/`):

| A fájl | A szerepe |
|---|---|
| `install_ais_receiver.sh` | a telepítés: az `rtl-sdr`, a DVB-T driver blacklista, az AIS-catcher build (forrásból, ARM64), a systemd unit |
| `start_measurement.sh` | a mérési üzemmód: a helyi SQLite kimenet + a heti lehúzás a NAS-ra |
| `analyze_measurement.py` | a go/no-go metrikák (a mérés elemzése) |
| `inspect_schema.py` | a SQLite séma felismerése (az oszlopnevek pontosításához) |
| `PI-TELEPITES.md` | **a lépésről lépésre útmutató** — a döntő pontokkal |

**A 8 lépés (a `PI-TELEPITES.md` szerint):** OS+hálózat → `rtl-sdr` →
a driver blacklista → **a dongle felismerése** → **a PPM-kalibráció** →
**a helyi AIS-teszt** → a mérés indítása → **a belvízi FI 10 teszt**
(a tetőn/vízparton).

**A négy döntő pont:** a dongle látszik-e · a PPM kalibrálva ·
jön-e jel · **jön-e belvízi FI 10** (ezen múlik az ENI, azaz a
katalógus).

**A méréshez nem kell szerver** — a Pi a helyi SQLite-ba ír, és a
heti lehúzás után offline feldolgozzuk. A központi ingest (MQTT +
a `04` – parser terv) **a 30 nap után** indul.

> **Az AIS-catcher v0.71-ben a `-D` kimenet ÚJRAÍRÓDOTT** — a
> `ingest-terv.md` 3.2-es fejezetének flag-formátuma (`station_id 1
> position on static on nmea on unique on position_interval 60
> retention 14`) **elavult**. Az új forma: `-D sqlite:fájl STATION_ID 1
> V ON MSGS ON NMEA ON VP ON VS ON RETENTION 35`. **Az
> `ingest-terv.md`-t javítani kell** a mérés után.

**Az elhelyezés ellenőrzése helyszínen:** ha a lakás a **budai
oldalon** van, a **Gellért-hegy (210 m)** és a nyugati budai dombok
takarhatják a kilátást — ez az első dolog, amit telepítéskor nézni kell.

### 4.3 A 28 lépcs (a `docs/pi-eloallitas.md` 4. fejezete)

| # | Lépés | Hol |
|---|---|---|
| 1–5 | a Raspberry Pi OS Lite, a hostname, az SSH, a statikus IP, az NTP | §4.1 |
| 6–9 | a `rtl-sdr` telepítése, a **DVB-T driver letiltása** (`blacklist dvb_usb_rtl28xxu` → reboot), a dongle felismerése, a **ppm-kalibráció** (`rtl_test -p`, 10 perc) | §4.2 |
| 10–13 | az **AIS-catcher** telepítése (bináris, systemd unit), a konfiguráció (a ppm, a JSON kimenet, a stat port, a gnz), a **belvízi FI 10 ellenőrzése** (ezen múlik az ENI!), a heartbeat | §4.3 |
| 14–20 | az **ADS-B lánc** (a dump1090-fa, a fr24feed, a FR24) — **külön dongle**, külön antenna (a 1090 MHz szűrő kötelező!) | §4.4 |
| 21–28 | a chrony, a GPS+PPS (opcionális), a **UPS**, a hűtés, az **USB-SSD** (a kártya kopása a leggyakoribb hibaforrás), a `ufw` biztonság, a monitorozás | §4.5 |

**A 12. lépés a legfontosabb a projekt szempontjából:** ha a
dekóder nem adja az Inland AIS (FI 10) üzeneteket, **nincs ENI** —
és az ENI nélkül nincs katalógus (a README 3.3/B: az ENI a
Duna-katalógus elsődleges azonosítója).

### 4.4 A mérési protokoll (a `ais-vevo-terv.md` 5. fejezete)

**30 nap, 1 próbavevő, a legforgalmasabb szakaszon.** A go/no-go
metrikák:

| # | Metrika | Küszöb |
|---|---|---|
| 1 | az üzenetek száma | a README 5. fejezetének becslését igazolja-e? |
| 2 | az üzenettípusok megoszlása | a Msg 1/3/5/18/24 + FI 10 aránya |
| 3 | a hibás üzenetek aránya | **< 0,1%** (a parser megbízhatósága) |
| 4 | a dekódolható statikus adatok aránya | hány hajóból van ENI/név/méret |
| 5 | a pozíciók minősége | a `river_km` a folyó-korridoron belül van-e? |
| 6 | a ghost hajók aránya | a négy szűrőszabály után hány marad |

**A mérés kimenete:** az 50 reprezentatív üzenet → a
`db/fixtures/ais/` — ezek a parser **elfogadási tesztjei** (a 04-es
terv §8.3).

### 4.5 A mérés utáni teendők (a sorban)

| # | Teendő | A terv |
|---|---|---|
| 1 | a **fixture-ök** a repóba (50 üzenet) | 04 – AIS-parser |
| 2 | a **saját dekóder** megírása és a tesztelése (a `pyais`-szal és az `aiscat`-tel referencia-implementációként) | 04 – AIS-parser |
| 3 | a **Q8 futtatott összehasonlítás** (a `pyais` vs. `aiscat` vs. saját) | 01 – terv §5.3 |
| 4 | a **szerveroldali ingest** (az MQTT → a dekódolás → a Postgres) | 04 – terv |
| 5 | a **03-as API-terv** javításai a swarm review alapján | 03 – API |
| 6 | a **07–09** terv (a CI/CD, a teszt-stratégia, az üzemeltetés) | — |

---

## 5. Hol van minden (a munkaterületek)

| Hol | Mi | Hogyan érem el |
|---|---|---|
| **A Mac repó** | `/Users/modmj/dev/duna-hajokoveto` — a forrás | SSH: `modmj@192.168.1.172` (a wifi-címen; a `192.168.0.135` a fix LAN) |
| **A GitHub** | `VorosEgyes/vessel-tracker` — a publikus forrás | a `main` branch védett |
| **A NAS munkakönyvtár** | `/opt/data/martin/work/duna-plan/` — a tervek élő változata | a `stage_for_mac.py` script másolja a Macre |
| **A swarm board** | `/opt/data/kanban/boards/review-swarm/` — a review-k | a `hermes kanban` parancs |
| **A review-kivonatok** | `/tmp/swarm/<run>/output/` — a findingek | HEREDOC-ral írták |
| **A DDL-validáló** | `/opt/data/martin/work/pgtest/` — az élő PostgreSQL | a `pgserver` (a `pgdata` mappában) |
| **A Mac mount** | `/opt/data/mnt/mac/` — **halott** (a konténerben nincs `SYS_ADMIN`) | **SSH/SCP helyett** — a `stage_for_mac.py` SSH-ágát használjuk |

### 5.1 A Mac repo és a GitHub kapcsolat

**A Macen nincs GitHub-hitelesítés** → a push a `git bundle`-en
keresztül történik:

```bash
# a Macen
git bundle create /tmp/vt.bundle --all
# a NAS-on
scp modmj@192.168.1.172:/tmp/vt.bundle .
cd /opt/data/martin/work/vessel-tracker
git fetch ../vt.bundle 'refs/heads/*:refs/remotes/bundle/*'
git reset --hard bundle/main
GIT_ASKPASS=/opt/data/martin/home/bin/askpass_gh.sh \
  git -c credential.helper= push origin main
```

**A `push_to_github.sh` script** (`/opt/data/martin/work/duna-plan/`)
az egyszerű útvonalat végzi (a remote beállítása + a push).

---

## 6. A döntési nyitott pontok

| # | Kérdés | Ki dönt | Hol |
|---|---|---|---|
| 1 | A GitHub-repo létrejött és a `main` védett | ✅ **lezárva** (2026-11-19) | — |
| 2 | A projekt neve `vessel-tracker` (magyarul: Hajókövető — Duna és Balaton) | ✅ **lezárva** | — |
| 3 | A `position` TTL 90 nap, de a README 5.4 „60 nap"-ot ír | **Miklós** | a 02-es terv §14 Q9 |
| 4 | A `water_level` TTL 90 nap (a README-ből nem vezethető le) | **Miklós** | a 02-es terv §14 Q10 |
| 5 | A `release-terv` 3.3 mondatának pontosítása (a `position` R1/R2 helye) | **Miklós** | a 01-es terv §12 |
| 6 | Az R1 sprint-szám (4 vagy 5) | **Miklós** | a `release-terv` 3.7 |
| 7 | A projekt saját licence (Q12, a GPL-kompatibilitás) | **Miklós** | a 01-es terv §5.3 |
| 8 | A **hardver-beszerzés** (a fenti táblázat) | **Miklós** | a mostani munkaterület |

---

## 7. A terv-sorozat és a megépítés kapcsolata

```
┌─ TERVEZÉS — a sorozat TELJES (01–09) ─────────────────────┐
│ 01 stack  →  02 séma (VALIDÁLVA, v1.5)  →  03 API (v0.3)  │
│                                       ↓                    │
│ 04 parser (v1.0)  05 frontend  06 szerkesztő  07 CI        │
│ 08 teszt  09 üzemeltetés                                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─ MEGÉPÍTÉS (a mostani szakasz) ────────────────────────────┐
│ hardver ✅ → Pi előállítás ✅ → 30 NAPOS MÉRÉS ⏳ FUT        │
│ (2026-11-22 óta, a go/no-go 69,8%-on)                       │
│                              ↓                               │
│              a saját parser → az ingest → az API             │
└─────────────────────────────────────────────────────────────┘
```

**A megépítés nem vár a tervekre** — a Pi + rádió **független** a
sémától és az API-tól. A mérés viszont **vár** a parserre (a
fixture-ök a mérésből jönnek) — tehát a sorrend:

**hardver → Pi előállítás → mérés (30 nap) → parser → ingest → API**

**A közben** elkészültek a 07–09 tervek és a 03-as/04-es
review-javítások — **a tervezés gyakorlatilag kész**.

### 7.1 A következő három lépés

| # | A lépés | A mikor |
|---|---|---|
| 1 | **a mérés fut** — a heti lehúzás ellenőrzése hétfőnként | **2026-12-22-ig** |
| 2 | **a 05–09 terv swarm review-ja** (a draftok) | a mérés alatt, párhuzamosan |
| 3 | **a saját parser implementálása** (a 04-es terv v1.0 szerint) | a mérés után (a fixture-ök készen állnak) |

### 7.2 A mérésből jövő döntések

| A döntés | A határ | A jelenlegi állapot |
|---|---|---|
| **a go/no-go** (a lefedettség) | ≥ 50% | **69,8%** ✅ |
| **a szűvíz helyszín** (az ENI-k) | a szűkvízi szakaszokon kell mérni | **a városi helyen az ENI-arány 0,5%** → **egy 2. site kell** |
| **a TCXO-s dongle** | a PPM ≤ 2 | **a mérésben PPM 7–8** (a TCXO nélküli dongle) |
| **a 162 MHz szűrő** | a túlterhelés csökkentésére | **a mérés szűrő nélkül is fut** → a döntés a mérés végén |

> **A Q7 (melyik telephelyen mérünk) a legfontosabb nyitott kérdés** —
> a `04` – parser-terv K-4 findingje és a `08` – teszt-stratégia Q5-e.

---

*Ez a dokumentum a `docs/megvalosulas/ALLAPOT.md` útvonalon van a repóban.*
