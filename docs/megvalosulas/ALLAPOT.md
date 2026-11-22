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
| `docs/sema-core.mmd`, `docs/sema-irodalom.mmd` | a Mermaid séma-ábrák | kész |

### 2.2 Az implementációs terv-sorozat (`docs/megvalosulas/`)

| # | Terv | Méret | Státusz |
|---|---|---|---|
| 01 | technológiai stack és projektstruktúra | 90,7 KB | **v1.3** — 2 körű swarm review, a 2. kör 17 findingje javítva |
| 02 | adatbázis-séma (DDL v1.1) | 109,6 KB | **v1.2** — 113 finding (3 reviewer + verifier), a 10 blokkoló javítva, **futtatva és tesztelve** |
| 03 | API-specifikáció | 19,0 KB | **v0.1** — 1. körű swarm review **fut** |
| 04 | AIS-parser specifikáció | 25,4 KB | **v0.1** — draft |
| 05 | frontend-arkitektúra | 24,8 KB | **v0.1** — draft |
| 06 | szerkesztői felület | 22,1 KB | **v0.1** — draft |
| 07 | CI/CD és környezetek | — | **nincs meg** |
| 08 | teszt-stratégia | — | **nincs meg** |
| 09 | üzemeltetés és observability | — | **nincs meg** |

### 2.3 A 02-es DDL — a legjobban validált rész

**A séma futtatva van valódi PostgreSQL 17-en:**

| Objektum | Darabszám |
|---|---|
| Tábla | 71 |
| Index | 150 |
| FK constraint | 121 |
| CHECK constraint | 370 |
| Particionált tábla | 3 (`ais_message_raw`, `water_level`, `position`) |
| Trigger-definíció | 28 |

**16 funkcionális teszt, mind zöld** — a `db/tools/validate_ddl.py`
a terv markdown-ból kicsomagolja a DDL-t, lefuttatja egy élő
PostgreSQL-en, majd füstöt hajt végre.

**A validáló a `--plan` kapcsolóval bármely tervet validál** (a
swarm review ezt a hiányt mutatta ki: a script a live fájlt olvasta
a benyújtott helyett).

---

## 3. Mi fut

| Mi | Hol | Állapot |
|---|---|---|
| **A 03-as API-terv 1. körű swarm review** | a `review-swarm` kanban boardon (`t_cecb1fc2` prof, `t_60ad07e9` bori, `t_369dcd42` preshaz) | a 3 worker fut, a kimenetek még nincsenek meg |
| A 03-as verifier + szintézis | `t_bb0c1a30`, `t_419ba291` | a worker-ek után indul |

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
| **Raspberry Pi** | **3B+** (a `pi-eloallitas.md` szerint a 4/5 ajánlott, de a 3B+ megfelel) | ~50 | **beszerzendő** |
| **SD-kártya** | 32 GB, A2 osztály (a wear levelling miatt) | ~10 | **beszerzendő** |
| **AIS USB dongle** | RTL2832U + **TCXO** (a V3, 0,5 ppm — a `pi-eloallitas.md` szerint a frekvenciapontatlanság a legnagyobb korlát) | ~25–35 | **beszerzendő** |
| **162 MHz antenna** | AIS-re hangolt, fix, függőleges polarizáció, ~3 dB | 80–250 | **beszerzendő** |
| **162 MHz SAW szűrő** | a túlterhelés és a LO-szivárgás csökkentésére | ~20 | **beszerzendő** |
| **Koax** | RG-58/U, **max. ~10 m** (a hosszú kábel tönkreteszi a jelet) | 20–60 | **beszerzendő** |
| **Táp** | a Pihoz + **UPS** (power bank) — a tápkiesés = adatlyuk | 30–60 | **beszerzendő** |
| **Hűtés** | a Pi és a dongle is melegszik | ~10 | **beszerzendő** |

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

### 4.1b A mérés állapota (2026-11-22 19:23)

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
┌─ TERVEZÉS (kész vagy készül) ──────────────────────────────┐
│ 01 stack  →  02 séma (VALIDÁLVA)  →  03 API (review fut)  │
│                                       ↓                    │
│ 04 parser  05 frontend  06 szerkesztő  07 CI  08 teszt     │
│ 09 üzemeltetés                                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─ MEGÉPÍTÉS (a mostani szakasz) ────────────────────────────┐
│ hardver → Pi előállítás → 30 napos mérés → fixture-ök       │
│                              ↓                               │
│              a saját parser → az ingest → az API             │
└─────────────────────────────────────────────────────────────┘
```

**A megépítés nem vár a tervekre** — a Pi + rádió **független** a
sémától és az API-tól. A mérés viszont **vár** a parserre (a
fixture-ök a mérésből jönnek) — tehát a sorrend:

**hardver → Pi előállítás → mérés (30 nap) → parser → ingest → API**

**A közben** elkészülnek a 07–09 tervek és a 03-as review-javítások.

---

*Ez a dokumentum a `docs/megvalosulas/ALLAPOT.md` útvonalon van a repóban.*
