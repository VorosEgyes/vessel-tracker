# Adatút: a Pi-től az adatbázisig

**Verzió:** 1.0 (2026-11-14)
**Kapcsolódó dokumentumok:** [`pi-eloallitas.md`](pi-eloallitas.md) (a Pi előkészítése) · [`ais-vevo-terv.md`](ais-vevo-terv.md) (a vevőhálózat) · [`r1-adat-terv.md`](r1-adat-terv.md) (az AIS-adat és az ENI) · [`../README.md`](../README.md) (adatbázis terv, 6. fejezet: ingest)

---

## 0. A döntés egy mondatban

> **A Pi nem az adatbázisba ír.** Az AIS-catcher a beépített MQTT-kimenetével egy TLS-en futó brokernek publikál; a központi ingest szolgáltatás onnan olvassa, és az írja a termékadatbázisba. A Pi közben **helyi SQLite-ot tart** – ez a helyi archívum és egyben a kiesés-biztosítás.

Ez a terv a gyakorlatban már megoldott elemekre épül: **az AIS-catchernek beépített MQTT-kimenete (`-Q`) és beépített adatbázis-kimenete (`-D`, PostgreSQL/SQLite/CSV) van**, tehát a Pi oldalán nem kell saját kódot írni.

---

## 1. A teljes lánc

```
        ┌─────────────────── A PI (3. emelet) ───────────────────┐
        │                                                        │
  RTL2832U ──► AIS-catcher                                      │
  (162 MHz)      ├──► -Q mqtts://…  ──► [MQTT broker] ──┐       │
                 │    (élő út)                          │       │
                 ├──► -D sqlite:/var/lib/ais/ais.db     │       │
                 │    (helyi archívum, 14 nap)          │       │
                 └──► -N 8100 (helyi web-térkép)        │       │
        └────────────────────────────────────────────────┼───────┘
                                                         │ TLS 8883
                                                         ▼
        ┌─────────────────── A KÖZPONT (VPS) ────────────────────┐
        │  Mosquitto (broker)                                    │
        │    └─► ingest szolgáltatás (MQTT subscriber)           │
        │          ├─► ais_message_raw   (havi partíció, 14 nap) │
        │          ├─► position          (havi partíció)         │
        │          ├─► position_archive / position_hourly       │
        │          ├─► vесel + vessel_identifier (ENI!)          │
        │          └─► Parquet → objektátár (nyers archívum)     │
        │                                                       │
        │  Postgres + PostGIS · MinIO/S3 · Caddy (TLS)          │
        └───────────────────────────────────────────────────────┘
```

**A szabály:** a Pi kizárólag **publikál**; a központi ingest **ír**. A Pi soha nem kap megnyitási jogot az adatbázisra.

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

```bash
/usr/bin/AIS-catcher \
  -d:0 -s 1536K -a 192K -p <ppm> \
  -gr tuner auto rtlagc on \
  -Q mqtts://site_bud01:<jelszó>@ingest.example.hu:8883 \
       client_id bud01 \
       topic 'duna/ais/bud01/msg' \
       qos 1 \
       msgformat JSON_FULL \
       keep_alive on timeout 60 \
  -D sqlite:/var/lib/ais/ais.db \
       station_id 1 \
       position on static on nmea on \
       unique on position_interval 60 \
       retention 14 \
  -N 8100
```

**A flag-ek magyarázata:**

| Flag | Jelentés |
|---|---|
| `-d:0` | a 0. indexű SDR eszköz (`AIS-catcher -l` kilistázza) |
| `-s 1536K` | mintarate (RTL-SDR alapértéke) |
| `-a 192K` | tuner-sávszélesség |
| `-p <ppm>` | **frekvenciakorrekció** – a kalibrációból származó érték |
| `-gr tuner auto rtlagc on` | RTL-SDR tuner-beállítások (AGC be, erősítés automatikus) |
| `-Q … qos 1` | MQTT QoS 1 – a broker nyugtáz, a hálózat hibájánál újraküld |
| `-Q … msgformat JSON_FULL` | teljes dekódolás a payloadban (a `nmea` tömb is benne van) |
| `-D … station_id 1` | minden sorra ráíró site-azonosító – ez köti össze az `ais_receiver_site`-tal |
| `-D … unique on` | eldobja a 3 másodpercen belüli ismétlődéseket |
| `-D … position_interval 60` | hajónként legfeljebb 1 pozíció percenként (≈95%-os térfogatcsökkenés) |
| `-D … retention 14` | 14 napos helyi retention, napi automatikus tisztítással |

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

| Helyzet | Mi történik |
|---|---|
| **Internetkiesés 1–2 óra** | a broker QoS 1 + perzisztens session miatt sorba teszi; a Pi újracsatlakozik, a sor kifogy |
| **Hosszabb kiesés** | a broker sorra kerül; a Pi közben a **helyi SQLite**-ba ír → a kiesés nem adatvesztés, csak késés |
| **A broker leáll** | a `persistence true` miatt az üzenetek a diszken vannak, újraindítás után kiszolgálva |
| **Későn érkező adat** | a `received_at` a **valódi** fogadási idő marad (a Pi ideje), az `ingested_at` a szerver ideje → a késés látható |
| **Duplikátum** | dedup kulcs `(vessel_id, ts)` + tartalom-hash; az újrajátszott feed nem duplikál |
| **A vevő kiesése** | a `last_seen_at` nem frissül → riasztás. **A kiesés soha nem néma adatveszteség.** |

**A dedup kulcs és az UPSERT** a README 6.2 fejezetében már rögzítve van (`ON CONFLICT (vessel_id, ts) DO UPDATE`).

---

## 7. Terhelés és sávszélesség

| Mutató | Becslés (budapesti vevő) |
|---|---|
| Üzenet | **~150–350 üzenet/mperc** átlagban (a teljes flotta ~2 millió üzenet/nap, a budapesti szakasz ennek 10–25%-a); csúcsidőben a duplája |
| Payload (JSON_FULL) | ~500–800 B |
| **Sávszélesség (átlag)** | **~15–35 kbit/s** – a házi internet bármilyen formájában elviseli |
| Sávszélesség (csúcs) | ~100 kbit/s |
| Napi adat | ~175–420 MB MQTT-forgalom |
| Broker terhelés | egy vCPU-s VPS-en is kisebb 1% |
| Központi ingest írás | ~0,3 millió pozíció/nap a `position`-be (havi partíció, BRIN index) |
| Pi írás a kártyára | **nulla** – minden a helyi SQLite-ba megy, az is USB-SSD-re |

> **A számítás forrása:** az adatbázis-terv 5.1 fejezete ~700 napi aktív hajót és ~30 s-os üzenetközt intervalumot feltételez, ami a teljes Dunán ~2,0 millió üzenet/nap. Egyetlen budapesti vevő ennek 10–25%-át látja.
>
> **A sávszélesség nem a szűk keresztmetszet.** A szűk keresztmetszet a **központi Postgres írási sebessége** és a **partíciózás** – ezt az R1 adat-terv és az adatbázis-terv 5. fejezete kezeli. A **valós** üzenetszámot a 30 napos mérés adja meg; addig ez becslés.

---

## 8. Kétlépcsős bevezetés

| Fázis | Időtartam | Mi fut | Szerver kell? |
|---|---|---|---|
| **F0 – próbaüzem** | 30 nap | **csak** `-D sqlite:` a Pi-n + `-N 8100` helyi térkép | **nem** |
| **F1 – első éles átvétel** | R1 | MQTT → központi ingest → Postgres + PostGIS | igen |
| **F2 – bővítés** | R1–R2 | további site-ok, S-AIS feed, aggregációk | igen |

**A F0 fázis előnye:** a go/no-go döntés **nulla infrastruktúra-kockázattal** hozható meg. Nem kell VPS-t, domaint, TLS-t, adatbázist állítani, mielőtt tudjuk, hogy a vevő egyáltalán működik-e. A 30 nap után a helyi SQLite fájlt bármikor visszafejthetjük az ingestbe.

> **A 30 napos mérés alatt még ne építs központi ingestet.** A mérés egyetlen kérdése: *mennyi AIS-adat jön, és megvan-e benne az ENI?* Ezt a helyi fájl adja meg. A központi ingestet **a mérés eredménye után** tervezzük meg, a valós üzenetszámmal és a valós FI 10-mezőkkel.

---

## 9. Az első éles fogadás ellenőrzőlistája

Ez a lista a mérési fázis végén futtatható, és **a projekt legkockázatosabb feltételezését** teszteli:

| # | Ellenőrzés | Miért kritikus |
|---|---|---|
| 1 | Az `nmea` tömb megvan-e a payloadban? | a központi újradekódolás ennek az alapján működik |
| 2 | **Megvan-e az Inland FI 10 üzenet a forgalomban?** | ha nincs, az ENI-terv összeomlik |
| 3 | **Van-e benne `fairway hectometre` mező?** | **a `river_km` innen jön** – ha hiányzik, vissza kell térni a geometriai km-illesztésre |
| 4 | A `vin` mező (ENI) a várt formátumban van-e? | `vessel.eni` a kulcs a katalógusban |
| 5 | A `draught` a RNW-re értendő-e? | a `draught_reference` mező indoka |
| 6 | Az `eri ship type` kódok a `vessel_type` típusokra fordíthatók-e? | a hajótípus-katalógus |
| 7 | Mennyi a `repeat` (ismétlődő üzenet) arány? | a dedup és a tárolási becslés pontossága |
| 8 | A `rxtime` pontossága (a Pi órája) | NTP-hiba → hibás pozícióidőbélyeg |
| 9 | Üzenetszám csúcsidőben | az ingest terhelésének tervezése |
| 10 | Van-e „ghost" hajó (a folyón kívüli pozíció)? | a pozíció-validáció szabályainak finomítása |

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
