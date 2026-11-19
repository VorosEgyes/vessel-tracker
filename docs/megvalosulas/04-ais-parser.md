# Implementációs terv – 04: AIS-parser specifikáció

**Verzió:** 0.1 (terv-draft, swarm review előtt)
**Dátum:** 2026-11-19
**Kapcsolódó dokumentumok:**
[`../../README.md`](../../README.md) (adatbázis-terv v1.3) ·
[`01-stack-es-struktura.md`](01-stack-es-struktura.md) (stack + struktúra) ·
[`02-adatbazis-ddl.md`](02-adatbazis-ddl.md) (a séma — a parser ide ír) ·
[`03-api-specifikacio.md`](03-api-specifikacio.md) (a normalizált rekord a kimenete) ·
[`../../docs/ais-vevo-terv.md`](../../docs/ais-vevo-terv.md) (a vevőhálózat) ·
[`../../docs/ingest-terv.md`](../../docs/ingest-terv.md) (az adatút) ·
[`../../docs/r1-adat-terv.md`](../../docs/r1-adat-terv.md) ·
[`README.md`](README.md) (a terv-sorozat tagjai)

**Projekt:** `vessel-tracker` — a hajókövető a Dunán és a Balatonon.

> A dokumentum a repóban a `docs/megvalosulas/04-ais-parser.md` útvonalon
> van — a relatív linkek ehhez képest számolnak.

---

## 1. Mi a parser feladata

A parser a **nyers NMEA 0183 üzenetekből** a **normalizált rekordot**
állítja elő — ez a 02-es terv szerinti **közös szerződés** a `04` és a
`02` között (a `02` §10.1).

```
nyers NMEA (UDP/5000 vagy MQTT)
   → [a] frame-szintű validáció (a szabályos NMEA-körvonal, a
      ellenőrzőösszeg, a mondatszám, a számozott sorok összefűzése)
   → [b] AIS-üzenet dekódolása (a 6 bites payload)
   → [c] üzenettípus-dispatch (Msg 1/3/5/18/24 + Inland FI 10)
   → [d] normalizálás (a közös rekord)
   → [e] dedup (a msg_hash)
   → [f] írás a DB-be (a position upsert, a vessel upsert)
```

**Amit a parser NEM csinál:**
- **nem** dönt a fantom-hajóról (a szűrő a 01-es terv §5.5 szerinti
  négy szabály — a parser csak a **geometriai** ellenőrzés adatait
  szolgáltatja);
- **nem** kezeli a forrásjogokat (a `data_source` a konfigurációból jön);
- **nem** ütemez (az APScheduler / `pg_cron` a felelőse).

---

## 2. A technológiai döntés

### 2.1 A saját dekóder

| | `aiscat` | `pyais` | **saját dekóder** |
|---|---|---|---|
| Licenc | **GPLv3** (az AIS-catcher C++ motorját örökli) | MIT | saját (MIT) |
| Nyelv | Python/C++ | Python | **Python** |
| Belvízi támogatás | teljes | részleges | teljes |
| Mezők nevei | **sematikus** (`msg_type`, `mmsi`, `lat`, `lon`) | **neves** (`MessageType8Dac200Fid10` → `vin`, `shiptype`, `length`, `beam`, `draught`) | **sematikus** (a 02-es séma oszlopneveivel egyezik) |
| Karbantartás | aktív | aktív | **a mink** |

**A döntés: saját dekóder** (a 01-es terv §5.3).

**Az okok (a `prof` reviewer 2. körű H-N-1 findingje után pontosítva):**

1. **A GPLv3 a projekt licencét meghatározza.** Az `aiscat` használata
   GPLv3-at tesz a teljes kódra — egy zártforrású API-kliens
   (R5) nem osztható GPLv3 alatt. **A saját dekóder ezt a problémát
   nem hozza létre.**
2. **A `pyais` NEM ad mezőszintű belvízi szemantikát** — a korábbi
   állítás („a pyais mezőszinten nem strukturált") **HAMIS** volt: a
   `MessageType8Dac200Fid10` **neves mezőket ad** (`vin`, `shiptype`,
   `length`, `beam`, `draught`). A valódi ok: a `pyais` **nem ad
   `river_km`-t** (a fairway hectometre mezőt) és a mezőnevek nem
   illeszkednek a 02-es sémához — tehát **az átalakítás költsége
   nagyobb, mint a saját dekóderé**.
3. **A saját dekóder 300–400 sor** — az AIS payload 6 bites karakterkódolás
   (a nemzetközi specifikáció), a formátum **dokumentált és stabil**.

### 2.2 Mit jelent a „sematikus" mezőnév

A parser kimenete **közvetlenül a 02-es séma oszlopneveivel** egyezik:

| AIS mező | A parser kimenete | A séma oszlopa |
|---|---|---|
| `mmsi` | `mmsi` | `vessel.mmsi` |
| `lat` / `lon` | `lat_e7` / `lon_e7` | `position.lat_e7` / `lon_e7` |
| `sog` | `sog_mps` | `position.sog_mps` |
| `cog` | `cog_deg` | `position.cog_deg` |
| `true_heading` | `heading_deg` | `position.heading_deg` |
| `rot` | `rot_deg` | `position.rot_deg` |
| `pos_accuracy` | `ais_accuracy_m` | `position.ais_accuracy_m` |
| `nav_status` | `nav_status` | `position.nav_status` |
| `mmsi` (statikus) | `mmsi` | `vessel.mmsi` |
| `imo` | `imo` | `vessel.imo` |
| `callsign` | `callsign` | `vessel.callsign` |
| `name` (Msg 5) | `name` | `vessel_i18n.name` |
| `shiptype` (FI 10) | `vessel_type_code` | `vessel.vessel_type_code` |
| `length` / `beam` / `draught` (FI 10) | `length_m` / `beam_m` / `draught_max_m` | `vessel.*` |
| `fairway_distance` (FI 10) | `river_km` | `position.river_km` |
| `en` (FI 10) | `eni` | `vessel.eni` |

**Az `mmsi` az összekötő kulcs** — az AIS-ből mindig jön, a `vessel`
tábla elsődleges azonosítója.

---

## 3. A frame-szintű validáció (a NMEA 0183 körvonal)

### 3.1 A formátum

```
!AIVDM,1,1,,A,13HOI:0P0000VOHLCnHQKwvL05Ip,0*23
│     │  ││ │ │                                │ │
│     │  ││ │ │                                │ └─ a checksum (hex, 2 karakter)
│     │  ││ │ │                                └─── a payload (max. 82 karakter)
│     │  ││ │ └──────────────────────────────────── a talker+type ("AIVDM")
│     │  ││ └────────────────────────────────────── a rádió (a hosszú 'A')
│     │  │└──────────────────────────────────────── a számozott sorok száma
│     │  └───────────────────────────────────────── a sor sorszáma (1-ből)
│     └──────────────────────────────────────────── a formátum ("!")
└────────────────────────────────────────────────── a sentence azonosító
```

**A szabályok (a szabványból):**

| Szabály | Ellenőrzés |
|---|---|
| A mondat `$` (vagy `!`) karakterrel kezdődik | a szabályos karakterkészlet |
| A mezők vesszővel elválasztottak | a mezőszám ellenőrzése |
| A `*` után 2 hex karakter a checksum | az **XOR** a `$`/`!` és a `*` közötti karaktereken |
| Az `n` (sorok száma) 1–9 | a 0 érték érvénytelen |
| Az `r` (sorszám) 1..n | a `r` nem lehet nagyobb, mint `n` |

### 3.2 A számozott sorok összefűzése

**Az AIS üzenetek 82 karakter fölé nem férnek egy NMEA sorba** → a
formátum több sort használ (`1/3`, `2/3`, `3/3`).

**A szabály:**
1. az `1/n` sor kezdi az üzenetet;
2. az `r/n` sorok **rendben** jönnek (`r` növekvő);
3. a `payload` részeket **összefűzzük** (a `,` és az `*` nélkül);
4. az utolsó sor `fill_bits` mezője a payload **kitöltő bitjeinek száma**
   (0–5).

**Hiba esetén** (a `r` nem folytonos, a `payload` > 82 karakter, a
checksum hibás): **az üzenet eldobandó, és egy `data_quality_event`
íródik** (a `reason = 'parser_error'`).

### 3.3 A `fill_bits` kezelése

A `fill_bits` a payload **utolsó** bitjeinek száma, amik kitöltő
nullák. **A 6 bites karakterkódolásban** a kitöltő bitek a karakter
legalsó bitjeiben vannak → a `fill_bits` szám **a teljes payload
bitjeinek számával** számolódik (a karakterenkénti 6-tól).

**A dekódolás előtt** a `fill_bits` biteket el kell távolítani:
```python
bits = payload_bits[: len(payload_bits) - fill_bits]
```

---

## 4. Az AIS payload dekódolása

### 4.1 A 6 bites karakterkódolás

| Karakter | Bináris (MSB first) |
|---|---|
| `0`–`9` | `000000`–`001001` |
| `A`–`Z` | `001010`–`011001` |
| `a`–`z` | `011010`–`101001` |
| `0`–`W` (számok) | `101010`–`111111` |

**A 6 bites érték → bit-sor:** a karakter indexe a fenti táblából,
**6 bit, MSB first** (a legmagasabb bit a karakter 5. bitje).

**A megfordítás (a karakterek visszafelé):** a NMEA-ben a bitek
**bajt-sorrendben, a karaktereken belül fordítottak** vannak — a
dekódoláskor **a karakter 6 bitjét meg kell fordítani**.

### 4.2 Az üzenet fejléce

A dekódolt bitsor első **168 bitje** (22 karakter) az üzenet fejléce:

| Bit | Méret | Jelentés |
|---|---|---|
| 0–5 | 6 | üzenettípus (1, 3, 4, 5, 18, 19, 24) |
| 6–7 | 2 | ismétlődés (a számozott üzenetek sorszáma) |
| 8–37 | 30 | **MMSI** |
| 38–39 | 2 | navigációs állapot |
| 40–69 | 30 | nemzetközi szám (a 8-as üzenet) |
| 70–115 | 46 | hajógép-állapot (a 18-as üzenet) |

### 4.3 A dinamikus üzenetek (Msg 1, 2, 3)

| Bit | Hossz | Mező | Típus |
|---|---|---|---|
| 38–55 | 18 | `lon_e7` | egész, **1/10000 fok**, előjel a 17. bit |
| 56–73 | 18 | `lat_e7` | egész, **1/10000 fok**, előjel a 17. bit |
| 74–83 | 10 | `cog_deg` | egész, **1/10 fok** |
| 84–91 | 8 | `heading_deg` | egész, **1/10 fok** |
| 92–99 | 8 | `sog_mps` | egész, **1/10 m/s** |
| 100 | 1 | pozíció pontosság | 0 = 10 m, 1 = < 10 m |
| 101–103 | 3 | navigációs állapot | 0–15 |
| 104 | 1 |/manöverjelzés` | 0 = nincs, 1 = van |
| 105–107 | 3 | tartalék | |
| 108–115 | 8 | rádióállapot | |
| 116–127 | 12 | rate of turn | |
| 128–136 | 9 | nav status (a 2. üzenetben) | |
| ... | | pozíció (a 2. üzenetben) | |
| 148–167 | 20 | **GNSS antenna helye** | a `position` `geom`-jének **referenciapontja**! |

**A GNSS antenna helye (a 148–167. bit):** a pozíció **nem** a hajó
középpontjában van, hanem egy antennaszerelésben. Ez a Duna szűk
szakaszain (a keskeny vízállásnál) **fontos**: a hajó „mélysége" és
a „szélessége" a pozíció pontosságát is befolyásolja.

**A 02-es séma `position` táblájában nincs antennaszerelés-mező** — a
F-DET-15 mezőnkénti eredete alapján ez egy **saját mezőnkényi
eredet** lenne, nem külön oszlop. **A parser eldobja** (a `position`
tábla nem tartalmazza), de a `vessel_data_origin` **nem** kap ilyet
(az a statikus adatokra vonatkozik).

> **A `position` `geom` pont a GNSS-antenna helye, nem a hajó
> középpontja.** A UI-n (R2) ez megjegyzendő.

### 4.4 A statikus üzenetek (Msg 5)

| Bit | Hossz | Mező |
|---|---|---|
| 40–69 | 30 | `imo` |
| 70–89 | 20 | hívójel (`callsign`), 6 karakter, `trim` + `@` kitöltés |
| 90–91 | 2 | hajó- és kargótípus |
| 92–93 | 2 | a pozíció pontossága (a hajó mérete) |
| 94–97 | 4 | a GNSS-antenna helye (a hajó orrától, méterben) |
| 98–107 | 10 | hossz (méter) — **csak a GNSS-antenna elöl** |
| 108–115 | 8 | szélesség (méter) |
| 116–127 | 12 | a hajótípus kódja |
| 128–139 | 12 | ETA (perc) — **a szállító hajóknál** |
| 140–143 | 4 | a draft (méter, 1/10) |
| 144–147 | 4 | aDestination |
| 148–167 | 20 | ETA (perc) |

**A nev és a hívójel (a `vessel_i18n.name`):** a Msg 5 **nem tartalmaz
nevet**! A nevet az **Inland FI 10 (DAC 200, FID 10)** üzenet hordozza
(`name`, `callsign`) — ez a belvízi statikus üzenet.

**A hívójel a Msg 5-ben van** — és az FI 10-ban is. **A `vessel_identifier`
a kanonikus** (a 02-es terv §8.2a szinkron).

### 4.5 A belvízi statikus üzenet (Inland FI 10)

**A formátum:** a 6 bites karakterkódolás **egy karakterrel eltér**:
a **számok** (`0`–`9`) és a betűk **a 6 bites index helyett 7 bites
kódolással** vannak a payload **végén** (a `?` ASCII = 63 = a
kitöltő karakter).

> **A `?` a kitöltő karakter** — a `0x3F`. Az Inland FI 10 a
> hosszanti mezők végén `?`-ekkel kitöltött.

**A mezők (a 6 bites karakterkódolás után, a 7 bites kódolás előtt):**

| Mező | Hossz | Jelentés |
|---|---|---|
| `vin` | 8×7 bit | **ENI** (a 2016/1629/EU szerinti európai hajóazonosító) |
| `length` | 13 bit | a hajó hossza (0,1 m) |
| `beam` | 10 bit | a hajó szélessége (0,1 m) |
| `shiptype` | 14 bit | a hajótípus kódja (UN/CEFACT ERI) |
| `draught` | 11 bit | a merülés (0,1 m) |
| `hazard` | 3 bit | a veszélyes áru jelölés |
| `category` | 3 bit | a kategória |
| `dist_to_starboard` | 13 bit | a parttól mért távolság jobbra (m) |
| `dist_to_port` | 13 bit | a parttól mért távolság balra (m) |
| `speed_qp` | 1 bit | a sebesség pontossága |
| `heading_qp` | 1 bit | a haladási irány pontossága |
| `callsign` | 7×8 bit | a hívójel (7 karakter) |
| `name` | 20×6 bit | a hajó neve (20 karakter) |
| `draught_qp` | 1 bit | a merülés pontossága |
| `eta` | 4×5 bit | az ETA (óra:perc) |
| `draught_reference` | 2 bit | a merülés referencia (0 = nincs, 1 = **RNW**) |

**A `river_km` (a fairway hectometre) — a pozícióból jön, nem a
statikus üzenetből!** Az AIS **pozíció** üzenet (Msg 1/3) tartalmazza
a `distance_to_shore` és a `fairway_distance` mezőket a **szokásos
pozícióüzenet** 60–87. bitjén (a `lon`/`lat` után).

> **Ez a `position.river_km` forrása** — a 02-es terv szerint
> „*a `river_km` **közvetlenül az AIS fairway hectometre mezőből** jön
> (Inland FI 10)*". **Pontosítás:** a FI 10 a **statikus** üzenet, a
> `river_km` a **pozíció** üzenetben van (a szokásos pozíció
> kiterjesztése, a 60–87. bit). A terv megfogalmazása pontosítandó.

**A `draught_reference = 1` → `'RNW'`** — a 02-es terv
`CHECK (draught_reference IN ('RNW','lake_operator','unknown'))`
értékei. A **Balatoni** hajóknál nincs RNW → `NULL` (a `position`-ben
a `draught_reference` nem szerepel, a `vessel`-ben igen).

### 4.6 A Class B üzenetek (Msg 18, 24)

**A Msg 18** (a Class B pozíció) a 168 bites fejléc után **38 bites
Class B pozíciófejlécet** tartalmaz:

| Bit | Hossz | Mező |
|---|---|---|
| 0–7 | 8 | a fedélzeti berendezés fajtája |
| 8–37 | 30 | **MMSI** |
| 38–39 | 2 | navigációs állapot |
| 40–69 | 30 | nemzetközi szám |
| 70–105 | 36 | a Class B pozíció (a 8 bites pozíció + a navigációs adatok) |
| 106 | 1 | a pozíció pontossága |
| 107–109 | 3 | a SOG/COG pontossága |
| 110–141 | 32 | **a GNSS antenna helye** (a hajó orrától, méterben) |
| 142–143 | 2 | a hajótípus (a Class B kód) |
| 144–149 | 6 | a hajótípus altípusa |
| 150–151 | 2 | a hajótípus altípusának javítója |
| 152–157 | 6 | a hajótípus kódja |
| 158–167 | 10 | a **bevég/zárt hossz** |
| 168–187 | 20 | a **szélesség** (m) |
| 188–193 | 6 | a port oldali fedélzeti állapot |
| 194–199 | 6 | a jobb oldali fedélzeti állapot |
| 200–203 | 4 | a pozíciójelző eszköz típusa |
| 204–207 | 4 | a rádióállapot |
| 208–235 | 28 | a gyorsítóműszak-hiba (SOG) |
| 236–237 | 2 | a gyorsítóműszak-jelző |
| 238–245 | 8 | a navigációs állapot |
| 246–248 | 3 | a fedélzeti munkaállapot |
| 249–253 | 5 | a hajó belső berendezéseinek állapota |
| 254–255 | 2 | a hajó irányítása |
| 256–263 | 8 | a **GNSS antenna helye** (ismét) |

**A Msg 24** (a Class B statikus) a hajótípust, a hívójelet, a nevet,
a hosszt és a szélességet tartalmazza.

**A Balaton miatt fontos:** a Msg 18 és 24 a **Class B** (a kishajók)
üzenetei — **a Balatoni katalógus** ezekből épül (a README 2.10
szerint a kishajók és vitorlások nincsenek a katalógusban, de a
személyhajók és a kompok igen).

---

## 5. A normalizált rekord (a közös szerződés)

A `02` és a `04` közötti **egyetlen definíció** — a `04` ezt Pydantic
modellként rögzíti, a `02` ebből generálja az oszlopokat.

```python
# apps/ingest/pydantic_models.py
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


class NormalizedAisMessage(BaseModel):
    """A parser kimenete — a 02-es terv sémaoszlopaival egyezik."""

    # a forras
    source_code: str = Field(description="a data_source.code")
    received_at: datetime = Field(description="a fogadas idopontja (UTC)")
    msg_hash: bytes = Field(description="a dedup-kulcs (sha256)")

    # a hajo
    mmsi: int
    eni: Optional[str] = Field(default=None, description="a FI 10 vin-je")
    imo: Optional[str] = None
    callsign: Optional[str] = None
    name: Optional[str] = Field(default=None, description="a FI 10 neve")

    # a pozicio
    ts: Optional[datetime] = Field(default=None, description="a hajo GNSS-idobelyege")
    lat_e7: Optional[int] = None
    lon_e7: Optional[int] = None
    sog_mps: Optional[float] = None
    cog_deg: Optional[float] = None
    heading_deg: Optional[float] = None
    rot_deg: Optional[float] = None
    nav_status: Optional[int] = None
    ais_accuracy_m: Optional[float] = None
    river_km: Optional[float] = Field(default=None, description="a fairway hectometre")
    fairway_code: Optional[str] = None

    # a statikus meretek
    vessel_type_code: Optional[str] = None
    length_m: Optional[float] = None
    beam_m: Optional[float] = None
    draught_max_m: Optional[float] = None
    draught_reference: Optional[Literal["RNW"]] = Field(
        default=None, description="a merules referenciaja (a FI 10 flag-je)")

    # a diszpoziciok
    msg_type: int
    msg_subtype: Optional[int] = None
    repeat: Optional[int] = None
    is_static: bool = Field(description="True a statikus uzenetekre (Msg 5, 18, 24, FI 10)")
```

**A `source_kind`:** a `position.source_kind` a 02-es terv szerint
`'ais' | 'derived' | 'manual'` — a parser mindig `'ais'`-t ír; a
`'derived'` a **bárka** pozíciója (a konvoj vezetőjéből származtatva —
az a 01-es terv §5.5 3. pontja).

---

## 6. A dedup

### 6.1 A kulcs

A 02-es terv szerint a `msg_hash` a `raw_nmea` + `received_at` +
`source_id` elemekből jön — **a Python `hashlib.sha256`-a számolja**
(a DB-beli generálás nem lehetséges: a `timestamptz::text` nem
immutable — a V-N-5 finding).

```python
import hashlib

def compute_msg_hash(raw_nmea: str, received_at: datetime,
                     source_code: str) -> bytes:
    """A nyers uzenet dedup-kulcsa.

    A `received_at` epoch-milliSzekundumban megy (a timezone
    függetlenség miatt) — a `datetime.timestamp()` a local time
    felhasznalja, ezert a `timestamp()` helyett a `tz-aware`
    konverzio kell.
    """
    epoch_ms = int(received_at.timestamp() * 1000)
    payload = f"{raw_nmea}|{epoch_ms}|{source_code}"
    return hashlib.sha256(payload.encode("utf-8")).digest()
```

**A `received_at` a fogadás ideje** (a szerver ideje, UTC) — **nem** a
hajó GNSS-időbélyege. Ez fontos: a dedup a **hálózati** duplikációt
szűri (a vevő újraküldi, az MQTT retry), nem a fizikait.

### 6.2 A duplikáció forrásai

| Forrás | Leírás | Kezelés |
|---|---|---|
| **Az MQTT retry** | a broker újraküldi az üzenetet | a `msg_hash` eldobja |
| **A vevő buffer** | a helyi buffer újra küldi a blokkot | a `msg_hash` eldobja |
| **Két vevő, ugyanaz a hajó** | a Duna egy szakaszon belül 2 vevőt is lát | **NEM** eldobandó — a `position` upsert a `(vessel_id, ts)`-en, a későbbi írás győz |
| **A fizikai „ismétlődés"** | ugyanaz a pozíció kétszer | a `position` upsert eldobja (a `ts` azonos) |

---

## 7. A hibakezelés

| Hiba | Hatás | Jelzés |
|---|---|---|
| A checksum nem egyezik | az üzenet **eldobandó** | `data_quality_event` (`reason='parser_error'`) |
| A számozott sorok nem folytonosak | az üzenet **eldobandó** | `data_quality_event` |
| A payload > 82 karakter (több sor nélkül) | az üzenet **eldobandó** | `data_quality_event` |
| Ismeretlen karakter a payloadban | az üzenet **eldobandó** | `data_quality_event` |
| Ismeretlen üzenettípus | az üzenet **eldobandó** (a debug logban) | `data_quality_event` (`severity='info'`) |
| A `position` upsert ütközik | az **upsert** győz (a legfrissebb) | — |
| A `vessel` upsert ütközik (az ENI már létezik) | a `vessel_identifier` szinkron kezeli | — |

**A `data_quality_event` írása** az `ingest` folyamatban történik — a
02-es terv szerint a `job_run_id`-vel köthető (a P1-26 finding).

**A hibák aránya a mérés során** (a `ais-vevo-terv.md` 5. fejezete):
a go/no-go feltétel. A hibás üzenetek aránya **< 0,1%** kell legyen.

---

## 8. A mérési protokoll (a go/no-go)

A `ais-vevo-terv.md` 5. fejezete: **30 nap, 1 próbavevő, a
legforgalmasabb szakaszon.**

### 8.1 A mérés célpontjai

| # | Célpont | A mérés kérdése |
|---|---|---|
| 1 | **Az üzenetek száma** | a README 5. fejezetének becslését igazolja-e? |
| 2 | **Az üzenettípusok megoszlása** | a Msg 1/3/5/18/24 + FI 10 aránya |
| 3 | **A hibás üzenetek aránya** | < 0,1% (a parser megbízhatósága) |
| 4 | **A dekódolható statikus adatok aránya** | hány hajóból van ENI/név/méret |
| 5 | **A pozíciók minősége** | a `river_km` a folyó-korridoron belül van-e? |
| 6 | **A ghost hajók aránya** | a négy szűrőszabály után hány marad |

### 8.2 A mérés kimenete

A mérési időszak alatt a nyers üzenetek **egy fájlba** kerülnek
(a `raw archive` a `ais-vevo-terv.md` szerint Parquet + gzip), és a
**replay** a parser teljesítményét is méri.

**A fixture-ök:** a mérési időszakból **50 reprezentatív üzenet**
(részletenként 10) — ezek a `db/fixtures/ais/` mappába kerülnek, és
a parser **elfogadási tesztje** ez (a 01-es terv §5.7).

### 8.3 A parser elfogadási tesztje

| # | Teszt | Elvárt |
|---|---|---|
| 1 | A `!AIVDM,1,1,,A,...` egysoros üzenet dekódolása | a `mmsi` és a `lat_e7`/`lon_e7` helyes |
| 2 | A 3 soros üzenet összefűzése | ugyanaz az eredmény, mint az 1. tesztnél |
| 3 | A hibás checksum | eldobva + `data_quality_event` |
| 4 | A `fill_bits` levágása | a kitöltő bitek nincsenek a kimenetben |
| 5 | A FI 10 `vin` → `eni` | a 8 karakteres ENI helyes |
| 6 | A FI 10 `name` (20 karakter) | a név a `?` kitöltők nélkül |
| 7 | A Msg 5 `callsign` | a `@` kitöltő levágva, a szóköz-trimmelés után |
| 8 | A Msg 18 `length`/`beam` | a méretek helyesek |
| 9 | A negatív szélesség (`lon_e7 < 0`) | a előjel helyes |
| 10 | Az `mmsi = 0` | eldobva (a hibás üzenet) |

**A fixture-ök a mérés után jönnek** — a tesztek addig **szintetikus
üzenetekkel** futnak (a nemzetközi specifikáció példái).

---

## 9. A teljesítmény

| Művelet | Cél | Megjegyzés |
|---|---|---|
| Egy üzenet dekódolása | **< 1 ms** | a 6 bites dekódolás Pythonban |
| Egy üzenet feldolgozása (dekódolás + írás) | **< 5 ms** | a DB-írás dominál |
| Az üzenetfolyam feldolgozása | **> 1000 üzenet/másodperc** | a vevőnkénti 100–200 üzenet/mp sokszorosa |
| A memória | **a stream-enkénti 1 üzenet** | nincs pufferelés |

**A mérési adat (a README 5. fejezete alapján):** a Duna Budapest
szakaszán **~2 millió üzenet/nap** → **~23 üzenet/másodperc átlagban**,
de csúcsidőben (a reggeli átkelés) **tízszeres**.

**A 23 üzenet/mp nem igényel semmilyen optimalizálást** — a
`asyncio` + egy `psycopg` connection pool elegendő. A **parser nem a
szűk keresztmetszet** — a szűk keresztmetszet az **adatbázis írás**
(upsert).

---

## 10. A tesztelési stratégia

| Szint | Tartalom | Eszköz |
|---|---|---|
| **Unit** | a 6 bites dekódolás, a frame-validáció, az `fill_bits` | `pytest` |
| **Fixture** | az 50 reprezentatív üzenet a mérésből | `pytest` (paraméterezve) |
| **Property** | a dekódolás **round-trip**: a bitekből a karakterek visszaállíthatók | `hypothesis` |
| **Integráció** | a parser → a DB → a `vessel_last_position` nézet | a `validate_ddl.py` mintájára |
| **Regresszió** | a mérési időszak teljes replayje | a mérési fájl + a teljesítmény-mérés |

**A `property` teszt a legfontosabb** — a 6 bites kódolás kézi
implementálásánál a legkisebb hiba is elcsúszik egy bittel. A
`hypothesis` generálja a véletlen biteket és ellenőrzi, hogy a
dekódolás → visszaalakítás az eredetit adja.

---

## 11. A nyitott kérdések

| # | Kérdés | Alapértelmezés | Állapot |
|---|---|---|---|
| Q1 | A `river_km` a **pozíció** üzenetből jön (a szokásos pozíció kiterjesztése), nem a FI 10-ből — a 02-es terv megfogalmazása pontosítandó | **a pozíció üzenetből** | **lezárva** (§4.5) |
| Q2 | A `fairway_code` a pozíció üzenetben van-e? | a 02-es `position` séma **nem** tartalmaz `fairway_code` oszlopot — a `river_section.fairway_code` a szakaszhoz tartozik, nem a pozícióhoz | nyitva |
| Q3 | A **GNSS antenna helye** (a pozícióüzenet 148–167. bitje és a statikus üzenetek antennahelye) a `position` sémában nincs | **eldobva** — a `vessel_data_origin` a statikus adatokra vonatkozik | nyitva (a 02-es tervben) |
| Q4 | A `draught_reference` a `vessel`-ben van (a statikus FI 10-ből) — a `position`-ben nincs | **így** — a `position` a pillanatnyi merülés, a hivatkozás a statikus adathoz tartozik | **lezárva** |
| Q5 | A Msg 4 (bázisállomás) és a Msg 9/11 (SAR) kezelése | **eldobva** — a belső AIS-átvitelben nem relevánsak | **lezárva** |
| Q6 | A `pyais` használható-e **teszt-összehasonlításra** (a saját dekóder helyett)? | **igen** — a MIT licenc és a `pyais` a mezőneveket másképp adja, de a **számértékek** összehasonlíthatók | nyitva (a mérés után) |

---

*Ez a terv a `docs/megvalósulas/` sorozat negyedik darabja. Következik: 05 –
frontend-arkitektúra.*
