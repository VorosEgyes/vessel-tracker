# Adatút: a Pi-től az adatbázisig

**Verzió:** 1.1 (2026-11-23 — **a `bud01` mérés alapján átírva**; a
v1.0 az MQTT-alapú architektúrát írta le, de a mérésben a Pi **helyi
SQLite-ot ír** és **hetente húz** — az MQTT-kimenet nincs bekapcsolva)
**Kapcsolódó dokumentumok:** [`pi-eloallitas.md`](pi-eloallitas.md) (a Pi előkészítése) · [`ais-vevo-terv.md`](ais-vevo-terv.md) (a vevőhálózat) · [`r1-adat-terv.md`](r1-adat-terv.md) (az AIS-adat és az ENI) · [`../README.md`](../README.md) (adatbázis terv, 6. fejezet: ingest)

---

## 0. A döntés egy mondatban

> **A Pi nem az adatbázisba ír.** A vevő **helyben, SQLite-ba ír**, és
> **hetente** (a cron, hétfő 04:17) a nyers SQLite-fájlt a NAS-ra húzza;
> a **központi feldolgozás** onnan olvassa, és írja a termékadatbázisba.
> A Pi soha nem kap megnyitási jogot az adatbázisra.

> **A v1.0 ezt másképp írta:** az AIS-catcher MQTT-kimenetét (`-Q`)
> egy brokernek publikálta, és a központi ingest onnan olvasta. **A
> mérésben ez nincs bekapcsolva** — a `bud01` vevő **csak** a
> `-D sqlite:` kimenetet használja (a `ais-receiver.service` unitja),
> és a nyers adat a **heti lehúzással** jut a NAS-ra.
>
> **Miért változott meg:**
> 1. **a mérési időszakban a heti lehúzás a praktikus út** — a 30 napos
>    mérés adathalmaza (~27 millió üzenet) nem Live MQTT-forgalomként
>    érkezik, hanem **fájlokban**;
> 2. **a Pi kiesése nem veszti el az adatot** — a heti lehúzás a NAS-ra
>    kerül, és a feldolgozás **újrajátszható** (a dedup miatt
>    idempotens — a `04` – parser-terv §6.1);
> 3. **a Mac kiesése nem számít** — a láncban nincs Mac (a `Pi → NAS`
>    közvetlen SSH, a `command=` korlátozással).
>
> **Az MQTT-út R2-ben jöhet** (az élő pozíció-streamhez, a `03` – API-terv
> R2-es része) — **de R1-ben a heti lehúzás a valós út**, és ezt a
> tervnek is dokumentálnia kell.

Ez a terv a gyakorlatban már megoldott elemekre épül: **az AIS-catchernek
beépített MQTT-kimenete (`-Q`) és beépített adatbázis-kimenete (`-D`,
PostgreSQL/SQLite/CSV) van**, tehát a Pi oldalán nem kell saját kódot
írni — **a `-D sqlite:` kimenet a mérésben bizonyítottan működik**
(a v0.71 sémájával: `ais_message`, `ais_position`, `ais_static`,
`ais_state`, `ais_stats_hourly`).

---

## 1. A teljes lánc

```
        ┌─────────────────── A PI (bud01) ───────────────────────┐
        │                                                        │
  RTL2832U ──► AIS-catcher v0.71                               │
  (162 MHz)      ├──► -D sqlite:/var/lib/ais/ais.db             │
                 │    (a nyers adat, RETENTION 35 nap)           │
                 │    + -N 8100 (a helyi web-térkép)             │
                 │                                              │
                 │  heti lehúzás (cron, hétfő 04:17)           │
                 └──► scp ──────────────────────────────┐        │
        └──────────────────────────────────────────────┼────────┘
                                                       │ SSH
                                                       ▼
        ┌─────────────────── A NAS (Artemis) ────────────────────┐
        │  /opt/data/martin/work/ais-data/ais-YYYYMMDD-HHMM.db  │
        └───────────────────────────────────────────────────────┘
                                                       │
                                                       │ (a feldolgozás
                                                       │  olvassa a *.db
                                                       │  fájlokat)
                                                       ▼
        ┌─────────────────── A KÖZPONT (VPS) ────────────────────┐
        │  ingest szolgáltatás (a saját dekóder)                 │
        │          ├─► ais_message_raw   (havi partíció, 14 nap) │
        │          ├─► position          (havi partíció, 90 nap) │
        │          ├─► position_archive / position_hourly       │
        │          ├─► vесel + vessel_identifier (ENI!)          │
        │          └─► a nyers *.db fájlok megmaradnak           │
        │                                                       │
        │  Postgres + PostGIS · Caddy (TLS)                     │
        └───────────────────────────────────────────────────────┘
```

**A szabály:** a Pi **helyben ír** (SQLite) és **hetente húz**; a
központi feldolgozás **ír** a termékadatbázisba. A Pi soha nem kap
megnyitási jogot az adatbázisra.

**A `VIRTUAL` pontok és a navigációs lámpák** (a mérés valós adata):
a `992438xxx` MMSI-k a **Duna navigációs infrastruktúrájának**
állomásai — **nem hajók** → a feldolgozás a fantom-szűrőben zárja ki
őket (a `04` – parser-terv §4.7.1).

> **Az MQTT-út R2-ben jöhet** (az élő pozíció-stream) → a diagram
> a `-Q mqtts://…` sort R2-re hagyja.

**A `Parquet → objektátár` a v1.0-ban a nyers archívumot jelentette —
a mérésben a nyers archívum a SQLite-fájl** (a heti lehúzás a
`*.db` fájlokat másolja a NAS-ra, ~4 MB/óra → ~600 MB/hét).

---

## 2. Miért MQTT és nem közvetlen Postgres-kapcsolat

| Szempont | Közvetlenül a Pi-ről a Postgresbe (`-D`) | MQTT + központi ingest |
|---|---|---|
| **Séma** | Az AIS-catcher saját sémája (`ais_position`, `ais_static`) – **nem** a termék sémája | A termék sémája: `river_km`, `river_section_id`, `geom`, `source_kind`, partíciók |
| **Dekódolás** | a Pi verziója dönt → 4 site-on 4 különböző dekóler | egyetlen központi dekóler (`aiscat`), verziófrissítés Pi-érintés nélkül |
| **ENI / FI 10** | a Pi adja át a `vin` mezőt, ha egyáltalán adja | a központi dekóler adja, a nyers NMEA-ból újra dekódolva |
| **Biztonság** | a DB (vagy WireGuard tunnel) közvetlenül elérhető | a Pi csak egy szűk ACL-lel korlátozott MQTT-témaírhat |
| **Kiesés** | AIS-catcher újracsatlakozik, de a sor a **félkész** sémába megy | a broker QoS 1-gyel sorba teszi; a termék-DB érintetlen |
| **Feldolgozás** | nincs konvoj-bontás, nincs aggregáció, nincs esemény-generálás | mindegyik a központban, egy helyen |
| **Kód a Pi-n** | nulla | nulla (a beépített `-Q` miatt) |
| **További fogyasztó** | nincs | lehet (archívum-writer, élő nézet, külső partner) |

> **Fontos:** az AIS-catcher adatbázis-kimenete **soha nem írhat a termékadatbázisba**. Legfeljebb egy **staging** adatbázisba – de a staging és a termék-DB szétválasztása is felesleges, ha a központi ingest 5–10 soros Python szolgáltatás.

**Amiért mégis van benne MQTT-ben a tudomány:** a Pi **push-only**. A budapesti lakás CGNAT mögött van, ezért a szerver nem érheti el a Pi-t – a Pi-nek kell kifelé küldenie. Az MQTT ezt natívan, QoS 1-gyel és perzisztens sessionnel megoldja, nem kell saját retry-queue.

---

## 3. A Pi oldal

### 3.1 Egy folyamat, három kimenet

| Kimenet | Flag | Cél | Kötelező? |
|---|---|---|---|
| MQTT (élő) | `-Q mqtts://…` | azonnali adat a központba | R1-ben igen |
| SQLite (helyi) | `-D sqlite:/var/lib/ais/ais.db` | helyi nyers archívum, 14 nap; kiesésnél a tartalék | **igen** |
| Web-térkép | `-N 8100` | helyi ellenőrzés, nem publikus | ajánlott |

### 3.2 A konkrét indítás (R1, budapesti site)

# A MÉRÉSBEN MŰKÖDŐ PARANCS (a bud01, a 2026-11-22-i mérés)
#
# **A v1.0-s parancssor ELAVULT FLAG-eket használt** — a v0.71-ben
# a `-gr tuner auto rtlagc on` és a `position on static on nmea on`
# SZINTAKTIKAI hibát ad ("syntax error on command line"), és a
# `retention 14` a helyén `retention 35` kell (a 30 napos mérés +
# 5 nap tartalék).
/usr/local/bin/AIS-catcher \
  -d:0 -s 1536K -a 192K -p 8 \
  -o 0 -M TD \
  -D sqlite:/var/lib/ais/ais.db \
       STATION_ID 1 RETENTION 35 \
       NMEA ON POSITION ON STATIC ON STATE ON STATS ON \
  -N 8100
```

> **A `-gr` flag NEM MŰKÖDIK a v0.71-ben** — a syntax error elbukik
> rajta. **A gain automatikus**, nem kell megadni. Az `-M TD` a
> fogadási timestampet (T) és a dekóder-metaadatot (D) kapcsolja be
> — **a v0.71 a két betűt EGY argumentumban várja** (`-M TD`, nem
> `-M T D`).

**A flag-ek magyarázata:**

| Flag | Jelentés |
|---|---|
| `-d:0` | a 0. indexű SDR eszköz (`AIS-catcher -l` kilistázza) |
| `-s 1536K` | mintarate (RTL-SDR alapértéke) |
| `-a 192K` | tuner-sávszélesség |
| `-p 8` | **frekvenciakorrekció** – a kalibrációból (a `rtl_test -p`, 25 perc) |
| `-o 0` | **quiet** – a napló nem írja ki minden üzenetet (a nyers NMEA a DB-be megy) |
| `-M TD` | a fogadási timestamp (T) + a dekóder-meta (D: signalpower, ppm) a JSON-ba |
| `-D … STATION_ID 1` | minden sorra ráíró site-azonosító – ez köti össze az `ais_receiver_site`-tal |
| `-D … RETENTION 35` | **35 napos** helyi retention (a 30 napos mérés + 5 nap tartalék) |
| `-D … NMEA/POSITION/STATIC/STATE/STATS ON` | a v0.71-es **új** nevek — a régi `position on static on nmea on` **elavult** |
| `-N 8100` | a helyi web-térkép |

> **A `unique on` és a `position_interval 60` FLAG-EK ELHIVTAK** a
> v0.71-ben → **a dedupot a feldolgozás végzi** (a `msg_hash` alapján,
> a `04` – parser-terv §6.1) → **a nyers adat teljes** (a mérésben
> 37 494 üzenet/óra, ebből 199 hajó).

> **A topikus sablonok:** az AIS-catcher a témában placeholder-eket is támogat (`%mmsi%`, `%type%`, `%channel%`, `%station%`, `%rxtimeux%`). **Ne ezeket használd** a terméküzeneteknél – egy fix `duna/ais/<site>/msg` témát használj, hogy az ACL egyszerű legyen, és a site-ot a broker hitelesített felhasználónevéből lehessen megállapítani. A per-hajó témák a külső fogyasztóknak (térkép, értesítés) hasznosak.

### 3.3 A helyi SQLite – miért ez a legfontosabb kimenet a mérés idején

- **A 30 napos próbaüzemhez nincs szükség semmilyen szerverre.** A Pi ír a helyi SQLite-ba, a fájlt a végén WireGuarden (vagy `scp`-vel) lehúzzuk, és offline feldolgozzuk.
- Ez egyben **a mérési adathalmaz**: a go/no-go döntés (lefedettség, üzenetszám, ENI-kihúzás) ezen fut.
- A helyi fájl **a kiesési tartalék**: internetkieséskor is megvan minden, és a `retention 14` a Pi-n is fut.
- A `-D sqlite:` kimenet **hibás adatbázisnál sem állítja le a vevőt**: exponenciális backofftal újracsatlakozik (5 perces maximumig), és közben csak a saját legrégebbi sorait dobja el.

**Fontos:** a helyi SQLite **a termékadatbázis másolata, nem a termékadatbázis.** Az `ais_message_raw` 14 napos TTL-je és a `position` havi partíciója a központi Postgresben van.

---

## 4. A szerver oldal

### 4.1 A broker

Mosquitto a központi VPS-en, TLS-en a **8883-as porton**:

```conf
# /etc/mosquitto/conf.d/duna.conf
listener 8883
allow_anonymous false
password_file /etc/mosquitto/passwd
acl_file /etc/mosquitto/acl
cafile /etc/letsencrypt/live/ingest.example.hu/fullchain.pem
certfile /etc/letsencrypt/live/ingest.example.hu/fullchain.pem
keyfile /etc/letsencrypt/live/ingest.example.hu/privkey.pem
tls_version tlsv1.3
persistence true
persistence_location /var/lib/mosquitto/
max_queued_messages 100000
```

| Sor | Jelentés |
|---|---|
| `allow_anonymous false` | csak hitelesített kliens csatlakozhat |
| `password_file` | a site-ok felhasználói; a `mosquitto_passwd` utility generálja |
| `acl_file` | téma-szintű jogosultság (lásd 4.2) |
| `persistence true` | a broker újraindítás után is megtartja a sorba került üzeneteket |
| `max_queued_messages` | mennyi üzenet várhat egy kliens visszatérésekor |

### 4.2 Az ACL – egy site, egy téma

```conf
# /etc/mosquitto/acl
# a site-ok: csak a saját prefixükre írhatnak
user site_bud01
topic write duna/ais/bud01/msg
topic write duna/site/bud01/status

user ingest
topic read duna/ais/+/msg
topic read duna/site/+/status
```

> **A `%u` minta használható** (`pattern write duna/ais/%u/#`), de akkor a felhasználónévnek pontosan a site-kóddal kell egyeznie – különben a séma nem bontja szét a telephelyeket. A **explicit `user` blokkok biztonságosabbak**: egy sor hozzáadása sem indít újra más site-ot.

### 4.3 Az ingest szolgáltatás

Kis Python szolgáltatás, ami a `duna/ais/+/msg` témára iratkozik fel:

| Lépés | művelet | cél |
|---|---|---|
| 1 | MQTT üzenet fogadás | a `nmea` tömb kicsomagolása |
| 2 | **újra dekódolás** `aiscat`-tel | a hitelesített mezők – **nem** a Pi JSON-ját használjuk |
| 3 | site-azonosítás | a broker **felhasználónevéből** → `ais_receiver_site.id` → `source_id` |
| 4 | validáció | MMSI-ellenőrzés, pozíció-értékek, „ghost" szűrés |
| 5 | dedup | `(vessel_id, ts)` + tartalom-hash → `ON CONFLICT DO UPDATE` |
| 6 | geo-enrichment | `river_km` az Inland FI 10 **fairway hectometre** mezőjéből, `river_section_id` |
| 7 | írás | `ais_message_raw` + `position` (UPSERT, a havi partícióba) |
| 8 | archívum | Parquet (zstd) → objektátár, napi fájl |
| 9 | `ais_receiver_site.last_seen_at` frissítés | heartbeat |
| 10 | hibakezelés | hibás sor → `data_quality_event` (dead-letter), nem csendben |

**Miért dekódolunk újra a központban?** Az AIS-catcher payloadja tartalmazza a **nyers NMEA-t**, így a központi oldal bármikor újra dekódolhatja. Ennek három előnye van: a dekóler verziója egy helyen van; a `river_km`-hez szükséges mező nem függ a Pi szoftververziójától; és a nyers NMEA megmarad akkor is, ha egy AIS-catcher-verzió bugos volt.

---

## 5. A site-azonosítás – a biztonság lényege

> **A `source_id`-t SOHA nem a payloadból vesszük.** A Pi küldheti, hogy „bud01 vagyok", de ezt nem hisszük el.

| Szempont | Szabály |
|---|---|
| Hitelesítés | MQTT username + password (vagy kliens-tanúsítvány + `use_identity_as_username`) |
| Mapping | `ais_receiver_site.code` ↔ MQTT username – a broker oldali ACL is ezt használja |
| `source_id` | a **szerver** állapítja meg a hitelesített usernévből |
| Payload `station_id` | csak **tájékoztató**, nem hiteles forrás |
| Site kikapcsolása | elég törölni a `password_file` bejegyzést – a token azonnal érvénytelen |
| `last_seen_at` | a szerver írja, az utolsó **tőle kapott** üzenet alapján |

A `station_id` mező egyébként is a `data_source`-hoz köti a site-ot (az `ais_receiver_site` a `data_source`-ra mutat), így a `position.source_id` lánc végigvezet a forrástól a termékig.

---

## 6. Kiesés, újrajátszás, dedup

> **A mérési időszakban NINCS MQTT** (a heti lehúzás a út) → **a
> broker-sor nem létezik**, és a kiesés kezelése **más**.

| Helyzet | Mi történik (a **heti lehúzásos** úton) |
|---|---|
| **A Pi internet-kiesése** | a vevő a **helyi SQLite-ba ír** (nem a brokernek) → **nincs adatvesztés**, csak a lehúzás késődik |
| **A Pi leáll (táp/SD/Wi-Fi)** | a `ais-receiver.service` nem indul újra → **a nyers adat a leállás pillanatáig megvan** a DB-ben; a heti lehúzás az utolsó mentett állapotot viszi el → **a kiesés NEM néma** (a fájl dátuma régebbi) |
| **A NAS elérhetetlen** | az `scp` nem sikerül → **a fájl a Pi-n marad** (`~/.ais-pull/`) → a következő lehúzás újrapróbálja (a `command=` korlátozás miatt más nem futhat) |
| **A lehúzás kimarad egy héten** | a `RETENTION 35` nap a mérés + 5 nap tartalék → **a 2. héten még megvan**, a 3.-on már **elveszik** → **riasztandó** |
| **Későn érkező adat** | a `received_at` a **valódi** fogadási idő marad (a Pi ideje, a `ais_message.received_at`), az `ingested_at` a feldolgozás ideje → a késés látható |
| **Duplikátum** | a dedup kulcs a `msg_hash` (`raw_nmea` + `received_at` + `source_id`) → **a visszajátszott fájl nem duplikál** → **a backfill idempotens** |
| **A vevő kiesése** | a `last_seen_at` nem frissül → riasztás. **A kiesés soha nem néma adatveszteség.** |

**A dedup kulcs és az UPSERT** a README 6.2 fejezetében már rögzítve van (`ON CONFLICT (vessel_id, ts) DO UPDATE`).

> **A dedup korlátja** (a `04` – parser-terv prof L-1 findingje): a
> `msg_hash` a `received_at` **millisecondszresolutionját** használja →
> **a hálózati retry** (a vevő újraküldi az üzenetet **más**
> időbélyeggel) **nem szűrődik** → a második védvonal a `position`
> upsert (a `(vessel_id, ts)`).

> **A MQTT-út (R2)** a fenti táblázat első három sorát kezeli helyesen
> (a broker QoS 1 + a perzisztens session) → **R2-ben a táblázat
> mindkét ágát használjuk**.

---

## 7. Terhelés és sávszélesség

> **A `04` – parser-terv prof C-6 és a preshaz P-C-3 findingje után:**
> a v1.0 **a README becslését** használta (2 millió üzenet/nap). **A
> mérés valós számai:**

| Mutató | A v1.0 becslése | **A mérés (2026-11-22)** |
|---|---|---|
| Üzenet/nap | ~2 000 000 (a teljes flotta) | **~900 000** (a budapesti vevő) |
| Üzenet/perc (átlag) | ~150–350 | **~10,4** (átlag), **~100–300** (csúcs) |
| A 30 napos adat | ~60 millió | **~27 millió** |
| A nyers SQLite mérete | ? | **~4 MB/óra** → **~3,4 GB** (35 nap) |
| A heti lehúzás fájl mérete | ? | **~600 MB** |
| A NAS éves terhelése | ? | **~30 GB** (a fájlokat **törölni kell**) |
| Központi `position` írás | ~0,3 millió pozíció/nap | **~900 000 pozíció/nap** (a `position` havonta partícionált, 90 napos TTL → ~81 millió sor) |
| Pi írás a kártyára | "nulla" | **~4 MB/óra** (a 32 GB-os SD: 4,1 GB a DB-vel = 15%) |

> **A mérési tények:**
> - a **37 494 üzenet/óra** a 199 hajóból → **188 üzenet hajónként**;
> - a **hétközapi MMSI-k száma** (a `ais-vevo-terv.md` 5.2 metrikája:
>   **≥ 120**) → **a mérésben 199** → **teljesül**;
> - a **lefedettség** (a Duna-korridorban lévő pozíciók aránya, a
>   földrajzi becsléssel) → **69,8%** → **a go/no-go küszöbön (50%)**.

> **A sávszélesség nem a szűk keresztmetszet.** A szűk keresztmetszet a
> **központi Postgres írási sebessége** és a **partíciózás** – ezt az
> R1 adat-terv és az adatbázis-terv 5. fejezete kezeli.
>
> **Az MQTT-forgalom sávszélessége R1-ben nem érvényes** — a mérés
> időszakában **nincs MQTT-kimenet** (a heti lehúzás a fájlokat mozgatja,
> nem a hálózat). A sávszélesség-adatok **R2-re** érvényesek (az élő
> pozíció-stream).

---

## 6b. A heti lehúzás (a mérési időszak tényleges útja)

> **Ez a fejezet a v1.0-ból hiányzott** — a `preshaz` P-C-5 findingje.

**A lépés (a Pi-n, a `scripts/ais-receiver/ais-fetch-weekly.sh`):**
```
1. sqlite3 /var/lib/ais/ais.db ".backup '/home/miklos/.ais-pull/ais-<STAMP>.db'"
2. scp -i ~/.ssh/ais_pull_key <NAS_USER>@<NAS_HOST>:<NAS_PATH>/ais-<STAMP>.db
```
**a kulcs** (`~/.ssh/ais_pull_key`) **a NAS-on** a `command=` korlátozással
van regisztrálva → **a Pi a NAS-on kizárólag a lehúzást futtathatja**
(más parancsot a szerver elutasít).

**A NAS-on** a fogadó script (`/usr/local/bin/nas-receive-ais.sh`) a
bind mounton keresztül a martin munkamappájába ír:
`/opt/data/martin/work/ais-data/ais-<STAMP>.db`.

**A cron:** `17 4 * * 1 miklos` (hétfő 04:17) — a `miklos` userrel,
mert a lehúzási kulcs a saját home-jában van.

**A feldolgozás** a `*.db` fájlokat olvassa (a `04` – parser-terv
§8.0) → **a dedup a `msg_hash` alapján → a backfill idempotens** → a
félig feldolgozott fájl újrafuttatható.

> **A `RETENTION 35` nap a mérés + 5 nap tartalék** — ha a heti
> lehúzás kimarad, **a nyers adat elvész** (a preshaz P-L-2 findingje)
> → ezért a lehúzás sikeressége **riasztandó** (a NAS-on a fájlok
> dátumai).

---

## 8. Kétlépcsős bevezetés

| Fázis | Időtartam | Mi fut | Szerver kell? |
|---|---|---|---|
| **F0 – próbaüzem** | 30 nap | **csak** `-D sqlite:` a Pi-n + `-N 8100` helyi térkép | **nem** |
| **F1 – első éles átvétel** | R1 | **a heti lehúzás** (a NAS-ra) → központi feldolgozás → Postgres + PostGIS | igen |
| **F2 – bővítés** | R1–R2 | további site-ok, S-AIS feed, aggregációk | igen |

**A F0 fázis előnye:** a go/no-go döntés **nulla infrastruktúra-kockázattal** hozható meg. Nem kell VPS-t, domaint, TLS-t, adatbázist állítani, mielőtt tudjuk, hogy a vevő egyáltalán működik-e. A 30 nap után a helyi SQLite fájlt bármikor visszafejthetjük az ingestbe.

> **A 30 napos mérés alatt még ne építs központi ingestet.** A mérés egyetlen kérdése: *mennyi AIS-adat jön, és megvan-e benne az ENI?* Ezt a helyi fájl adja meg. A központi ingestet **a mérés eredménye után** tervezzük meg, a valós üzenetszámmal és a valós FI 10-mezőkkel.

---

## 9. Az első éles fogadás ellenőrzőlistája

Ez a lista a mérési fázis végén futtatható, és **a projekt legkockázatosabb feltételezését** teszteli:

| # | Ellenőrzés | Miért kritikus |
|---|---|---|
| 1 | Az `nmea` tömb megvan-e a payloadban? | **IGEN** — a v0.71 a `nmea`-t **tömbként** adja (a `04` – parser-terv prof H-1) |
| 2 | **Megvan-e az Inland FI 10 üzenet a forgalomban?** | **IGEN — 767 üzenet** (a 8-as típus, a mérés első órájában) → **az ENI-terv nem omlik el** |
| 3 | **Van-e benne `fairway hectometre` mező?** | **NEM** — a magyar szakaszon a pozíciók fairway-mezője **üres** → **a `river_km` a navigációs lámpák neveiből vagy geo-illesztésből jön** (a `04` – parser-terv C-5) |
| 4 | A `vin` mező (ENI) a várt formátumban van-e? | **egy hajónál jött le ENI** (a `GONDOLA`, 8601836) → **a `vessel.eni` a kulcs, de ritka** (a mérésben 0,5%) |
| 5 | A `draught` a RNW-re értendő-e? | **igen** — a magyar hajóknál értelmes (a Balatonnál nem) |
| 6 | Az `eri ship type` kódok a `vessel_type` típusokra fordíthatók-e? | **IGEN — a 02-es v1.4 seedje 89 típust tartalmaz** (a mérés 14 kódja mind benne van: 8444/8443/8440/8000/60/69/80/8450/51/0/90/8430/8460/8220) |
| 7 | Mennyi a `repeat` (ismétlődő üzenet) arány? | a mérésben a 15-ös típus (interrogálás) 60 üzenet (0,2%); a `repeat` a pozícióknál gyakori → **a dedup a feldolgozás dolga** (a `msg_hash`) |
| 8 | A `rxtime` pontossága (a Pi órája) | **a PPM kalibráció a 7–8 értékre állította be** (a `rtl_test -p`, 25 perc) |
| 9 | Üzenetszám csúcsidőben | **átlag ~10,4/mp, csúcs ~100–300/mp** (a reggeli átkelés) |
| 10 | Van-e „ghost" hajó (a folyón kívüli pozíció)? | **IGEN — a navigációs lámpák (106) és a bázisállomások (3) nem hajók** → a fantom-szűrő kizárja őket (a `04` – parser-terv §4.7.1) | a pozíció-validáció szabályainak finomítása |

> **A 3. pont a legfontosabb.** A teljes adatbázis-terv azon a feltételezésen áll, hogy a folyó-km **közvetlenül az AIS-ből jön**. Ez a feltételezés a 30 napos mérés végén **empirikusan igazolódik vagy megdől** – és ha megdől, az `r1-adat-terv.md` 1.5 fejezetét és az adatbázis-terv 5.2 fejezetét módosítani kell. **Ezért a mérés a legfontosabb következő lépés, nem az infrastruktúra.**

---

## 10. Forráshivatkozások

- AIS-catcher MQTT-kimenet – a `-Q` flag, a `mqtts://user:pass@host:port` URL, a `topic`/`qos`/`msgformat`/`client_id` beállítások, a témasablon-placeholder-ek – [AIS-catcher docs](https://jvde-github.github.io/AIS-catcher-docs/configuration/output/MQTT/)
- AIS-catcher adatbázis-kimenet – a `-D` flag, a PostgreSQL/SQLite/CSV backendok, a `station_id`/`unique`/`position_interval`/`retention` beállítások, **a hibás adatbázisnál való újracsatlakozás és soreldobás viselkedése** – [AIS-catcher docs](https://jvde-github.github.io/AIS-catcher-docs/configuration/output/PSQL/)
- AIS-catcher CLI – a `-gr` (RTL-SDR), `-d:`, `-s`, `-a`, `-p`, `-Q`, `-D`, `-N` flagok – [AIS-catcher docs](https://jvde-github.github.io/AIS-catcher-docs/usage/cli/)
- AIS-catcher JSON-dekódolás – az **Inland AIS (DAC 200, FID 10)**: `vin` (ENI), `length`, `beam`, `shiptype` (ERI), `hazard`, `draught`, `loaded`; a `msgformat` (`JSON_NMEA` / `JSON_FULL`) – [AIS-catcher docs](https://jvde-github.github.io/AIS-catcher-docs/references/JSON-decoding/)
- `aiscat` Python csomag – a központi újradekódoláshoz, `Decoder`, `from_tcp`/`from_udp`/`from_stdin`, a formátumok – [AIS-catcher docs](https://jvde-github.github.io/AIS-catcher-docs/tools/python/)
- Mosquitto konfiguráció – `password_file`, `acl_file`, a `user`/`topic`/`pattern` szintaxis, a TLS a 8883-on, `allow_anonymous false` – [mosquitto.conf(5)](https://mosquitto.org//man/mosquitto-conf-5.html)
- Az AIS protokoll és a belvízi kiterjesztés – [EUR-Lex 2019/838](https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32019R0838&rid=5)
