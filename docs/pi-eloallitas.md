# Pi előállítás – AIS és ADS-B párhuzamosan

**Verzió:** 1.0 (2026-11-14)
**Hardver:** Raspberry Pi 3B+ · Budapest, 3. emelet
**Láncok:** AIS (162 MHz, hajós) + ADS-B (1090 MHz, légi)
**Kapcsolódó:** [`ais-vevo-terv.md`](ais-vevo-terv.md) (10. fejezet: a budapesti vevő) · [`ingest-terv.md`](ingest-terv.md) (hogyan jut el az adat a Pi-ről az adatbázisba) · [`r1-adat-terv.md`](r1-adat-terv.md)

---

## 0. A döntés és a fő korlát

> **Igen, lehet párhuzamosan futtatni a hajós AIS-t és a légi ADS-B-t egy Pi-on.** De **nem ugyanazzal a donglel**.

**A korlát:** az RTL2832U (és minden általános SDR-dongle) **egyetlen hangolható tunerrel** rendelkezik – egyszerre **egy frekvenciát** tud figyelni. Az AIS 161,975 / 162,025 MHz-en, az ADS-B 1090 MHz-en működik. **Két külön vevő kell, külön antennával.**

A Pi 3B+ 4 USB portja elég a kettőhöz, de a **portok egy USB 2.0 buszon osztoznak** (a Pi 3B+ mindegyike a VL805-ös vezérlőn). Az AIS forgalom szűk sávsávos módban könnyű (~0,2 Mbit/s), az ADS-B a nehéz (~16 Mbit/s USB-n, 2,048 MS/s mintarate). **Együtt épp belefér, de szűk – lásd 3. fejezet (a Pi 4/5 ajánlása).**

---

## 1. A két lánc

### 1.1 AIS-lánc (a hajós termékhez)

```
[162 MHz antenna, tető] → [162 MHz SAW szűrő] → [koax RG-58] → [AIS vevő] → [Pi: AIS-catcher] → [MQTT/VPN] → [szerver]
```

| Elem | Megjegyzés |
|---|---|
| Antenna | AIS-re hangolt, 3/4 hullámos (~1,2 m) vagy komplett AIS-antenna, **a tetőn, 3–5 m-rel a tető fölé** |
| Szűrő | 162 MHz sávszűrő (~20 EUR) – csökkenti a túlterhelést és a LO-szivárgást |
| Vevő | **Valódi AIS-vevő NMEA-kimenettel** (ajánlott) vagy az RTL2832U (prototípusra) |
| Szoftver | AIS-catcher (a belvízi FI 10 dekódolás is kell) |

### 1.2 ADS-B-lánc (a Flightradar24-feedhez)

```
[1090 MHz ADS-B antenna, ablak] → [1090 MHz szűrő] → [USB] → [Pi: dump1090-fa] → [fr24feed] → [FR24]
                                                                        └→ [ADSB.fi / ADS-B Exchange]
```

| Elem | Megjegyzés |
|---|---|
| Antenna | **1090 MHz ADS-B antenna** (pl. Nooelec/FlightAware) – az antenna a hatótáv meghatározója |
| Szűrő | **A 1090 MHz sávszűrő kötelező a generikus dongle-hoz** – enélkül a városi zaj elnyomja a jelet, az üzenetszám drámaian csökken |
| Vevő | **FlightAware Pro Stick Plus** (beépített 1090 szűrő + erősítő) a legjobb ár/érték; alternatíva: Nooelec NESDR SMArt v5 + külön 1090 szűrő |
| Szoftver | dump1090-fa → fr24feed → FR24 |

> **Ne a RTL-SDR Blog V4-et vegyél:** a tuner chipje (R828D) megszűnt, a maradék drága, és **hamisítványok** is vannak belőle. A **V3** jó, ha már van egy.
>
> **Fontos elhelyezési szabály:** a **hosszú koaxkábel tönkreteszi a jelet, a hosszú USB-kábel nem.** Ezért az ablakban legyen az antenna **és** a dongle (USB-hosszabbítóval), és a kábel fusson a falon belül. Ha csak hosszú koax lehetséges, akkor **szűrős LNA-t** (pl. SAWbird+) kell tenni az antenna közelébe.

---

## 2. Az FR24 bekötése – a fontos részletek

### 2.1 A lánc

```
dump1090-fa  --net  →  fr24feed  →  Flightradar24
   (port 30002: AVR raw)   (a fr24key a fiókból)
```

A `fr24feed` telepítése és regisztrációja:
1. `fr24feed --signup` – megadod az e-mailt; a FR24 létrehoz egy **fr24key**-t, amit a fiókban találsz
2. A receiver típusa: **„AVR or Beast Raw Feed"**, host `127.0.0.1`, port **30002** (a dump1090 nyers kimenete)
3. A **térkép a `http://<pi-ip>:8754/`** címen érhető el – innen ellenőrizhető, hogy az adat folyik

### 2.2 A szabály, amit könnyű elrontani

> **Ha egynél több hálózathoz is feedelsz (pl. FR24 + ADSB.fi + ADS-B Exchange), az FR24 feeden a MLAT-et KI kell kapcsolni.** Különben az FR24 **kitilthatja a feedet**.
>
> Az ADS-B Exchange a MLAT-et saját kezelésében végzi, így a többi hálózaton keresztül is megkapod a MLAT-lefedettséget.

Ez a leggyakoribb hiba a „több aggregátor" setupoknál – a feed csendben leállhat.

### 2.3 Több aggregátor egyszerre

| Hálózat | Forrás |
|---|---|
| Flightradar24 | fr24feed (vagy közvetlenül a dump1090 nyers kimenete) |
| ADS-B Exchange | a dump1090 Beast portjáról (30005) – a telepítő felismeri a meglévő dump1090-t |
| adsb.fi | a dump1090 Beast portjáról |
| FlightAware | külön feed, a saját fiókjával |
| RadarBox | külön feed |

A `dump1090-fa --net` egyszerre több célnak is tud küldeni – a kiindulási pont ugyanaz a nyers stream.

### 2.4 Jogi megjegyzés

Az ADS-B **titkosítatlan** sugárzás – bárki fogadhatja, nincs rá engedély. Amit a FR24 megköt, az a **saját pozíciód és a vevőd adataid** megosztása a hálózatukkal, a FR24 felhasználási feltételei szerint. A vállalati (B2B) felhasználásra mindig ellenőrizd a feltételeket.

> **A hajós termék szempontjából az ADS-B-lánc független projekt** – csak a Pi, az internetkapcsolat és a ház közös. A FR24-nek semmi köze a hajókatalógushoz.

---

## 3. A Pi 3B+ elbírja-e mindkettőt?

**Igen, de a USB a szűk keresztmetszet.** A Pi 3B+ mind a 4 USB-portja egy USB 2.0 (480 Mbit/s) buszon osztozik, a VL805-ös vezérlőn.

| Terhelés | USB-s forgalom |
|---|---|
| AIS (széles sávos mód, 0,25–2 MS/s) | ~2–16 Mbit/s |
| ADS-B (dump1090, 2,048 MS/s) | ~16–33 Mbit/s |
| **Összesen** | **~20–50 Mbit/s** – ez a 480 Mbit/s-en belül van, de a megosztott busz miatt időszakosan „USB bandwidth exceeded" hibák előfordulhatnak |

**Ajánlások:**
1. **A Pi 4/5 jobb választás, ha még vásárolhatsz** – a Pi 4-nek külön USB 3.0 vezérlője van (a 3.0-as portok nem a 2.0-as buszon osztoznak), és a processzor is gyorsabb. **A Pi 3B+ működik, de ne várj tőle hibátlan USB-t.**
2. Az **ADS-B mintarate csökkentése** (2,048 → 1,2 MS/s) csökkenti a terhelést, ha látod a hibákat.
3. A **dongle-kat távol egymástól** (≥ 0,5 m), mert az ADS-B dongle LO-szivárgása beleeshet az AIS vevő előerősítőjének (front-end) a bemenetére.

---

## 4. A Pi előkészítése – lépésről lépésre

### 4.1 Rendszerkép és alapbeállítás

| # | Lépés | Parancs / megjegyzés |
|---|---|---|
| 1 | Raspberry Pi OS **Lite** (64-bit) képe – a Full feleslegesen fogyaszt RAM-ot | Raspberry Pi Imager |
| 2 | Telepítéskor: hostname, felhasználó + jelszó, **SSH bekapcsolva**, időzóna `Europe/Budapest`, Wi-Fi vagy Ethernet megadva | Imager beállítási ablak |
| 3 | Frissítés | `sudo apt update && sudo apt full-upgrade -y` |
| 4 | **Statikus IP** (DHCP foglalás a routeren) | a `8080` (dump1090 térkép) és `8754` (fr24feed) portok LAN-on belül maradnak |
| 5 | Időszinkron ellenőrzése | `timedatectl` – NTP-nek működnie kell |

### 4.2 SDR előkészítés

| # | Lépés | Parancs |
|---|---|---|
| 6 | rtl-sdr telepítése | `sudo apt install -y rtl-sdr` (rtl_test, rtl_ais, rtl_tcp) |
| 7 | **A DVB-T driver letiltása** – különben a kernel lefoglalja a donglet | `/etc/modprobe.d/rtl-sdr-blacklist.conf`: `blacklist dvb_usb_rtl28xxu`, `blacklist rtl2832`, `blacklist e4000` → **reboot** |
| 8 | Mindkét dongle felismerése | `rtl_test` – a `Found Rafael Micro R820T tuner` sort kell látni |
| 9 | **Kalibráció** az AIS dongle-re | `rtl_test -p` (10 perc) → a ppm-érték beállítása a configban |

### 4.3 AIS-lánc

| # | Lépés | Megjegyzés |
|---|---|---|
| 10 | AIS-catcher telepítése (bináris, GitHub release) | systemd unit, hogy induljon a boot után |
| 11 | Konfiguráció: PPM érték, JSON kimenet, stat port, gnz (zajcsökkentés) | |
| 12 | **Belvízi FI 10 ellenőrzése** | a dekódernek ki kell adnia az Inland AIS üzeneteket – ezen múlik az ENI! |
| 13 | Heartbeat a szerverre | a `ais_receiver_site.last_seen_at` frissüljön |

### 4.4 ADS-B-lánc

| # | Lépés | Megjegyzés |
|---|---|---|
| 14 | dump1090-fa telepítése | `apt` csomag vagy a hivatalos telepítőszkript; systemd unit |
| 15 | Futtatás | `dump1090-fa --net --net-beast --net-riport --gain <érték> --device <index>` |
| 16 | **Helyi ellenőrzés** | `http://<pi-ip>:8080` → a térkép repülőket mutat |
| 17 | fr24feed telepítése + `--signup` | a receiver: AVR/Beast raw feed, `127.0.0.1:30002` |
| 18 | FR24-feed ellenőrzés | `http://<pi-ip>:8754/` – a „feeder status" mutatja, hogy folyik az adat |
| 19 | **MLAT kikapcsolása** az FR24 feeden, **ha más hálózatnak is feedelsz** | különben az FR24 kitilthat |
| 20 | Opcionális: adsb.fi / ADS-B Exchange feed | a dump1090 30005 portjáról |

### 4.5 Idő, pontosság, üzemeltetés

| # | Lépés | Megjegyzés |
|---|---|---|
| 21 | **chrony** telepítése | az NTP rendben van; a rendszeróra a dekódolás időbélyegeit adja |
| 22 | GPS + PPS (opcionális) | `gpsd` + chrony – **csak ha jó MLAT-kontributor akarsz lenni**; a házi, hálózatra kötött állomásnál az NTP is elég (1–10 ms) |
| 23 | **A Pi-nek nincs RTC-ja** | tápkiesés után a rendszeróra rossz, amíg NTP-hez nem csatlakozik – az ADS-B időbélyegek addig értelmezhetetlenek |
| 24 | **UPS** (power bank vagy akkumulátor) | hosszú áramkiesés = adatlyuk, és a `last_seen_at` heartbeat kiesik |
| 25 | Hűtés | `vcgencmd get_throttled` – a Pi és a dongle is melegszik; zárt szekrényben szellőzés kell |
| 26 | Tárolás | az OS az SD-kártyán, az **adatot USB-SSD-re** (vagy hálózatra) – a kártya kopása a leggyakoribb hibaforrás |
| 27 | **Biztonság** | `ufw` (csak a LAN portok), kulcsalapú SSH, **nincs port forwarding** a 8080/8754-re |
| 28 | Monitorozás | a szerveroldali ingest heartbeat alapján riaszt, ha a vevő kiesik |

---

## 5. A telepítés helyszíni kérdései (3. emelet)

| Kérdés | Hogyan ellenőrizhető |
|---|---|
| Takarja-e a Gellért-hegy a folyót? | a tetőről nézni a folyó irányában; a pesti oldalon nincs ilyen akadály |
| Van-e 3–5 m-rel magasabb antenna helye? | a tetőn, oszloppal – ez a legnagyobb egyszeri nyereség a lefedettségben |
| Zavar-e valami az ADS-B-t? | a 1090 MHz szűrő nélkül a városi zaj (DAB, FM) elnyomja a jelet; szűrővel a repülőszám drámaian megugrik |
| Merődik-e a villámvédelem? | a tetőn lévő antenna kötelező |

---

## 6. Várható eredmény a Budapesti helyszínen

| Mutató | Várható |
|---|---|
| ADS-B repülők | **sok** – a Budapesti reptér (BUD) kb. 15 km-re van, Európa egyik legforgalmasabb reptere; a háztól több repülő látható, és **van MLAT-potenciál** |
| AIS hajók | a Duna budapesti szakasza – **a legforgalmasabb szakasz**, ideális a katalógus első méréséhez |
| Tárolás | ~2 000 AIS-üzenet/perc + ~10 000 ADS-B üzenet/perc → **a nyers adatot tömörítve írd Parquetbe, ne a Postgresbe** |

---

## 7. Forráshivatkozások

- FR24 T Feed manual – a receiver-típusok, a portok (30002 AVR / 30005 Beast / 30334 RAW) és a `fr24feed --signup` – [FR24](https://www.flightradar24.com/blog/wp-content/uploads/2023/02/fr24feed-manual.pdf)
- ADS-B Exchange – „Already Feeding?": **több aggregátor egyszerre**, és **az FR24 megköveteli az MLAT kikapcsolását, ha más hálózatnak is feedelsz** – [adsbexchange](https://www.adsbexchange.com/already-feeding/)
- openskynetwork/raspberry-pi-adsb – a **1090 MHz sávszűrő ajánlása**, a kábel/adaptor részletek, a dump1090 telepítése – [GitHub](https://github.com/openskynetwork/raspberry-pi-adsb/blob/master/README.md)
- „Choosing an ADS-B Receiver" – a vevőválasztás (Pro Stick Plus, NESDR, **a V4 nevét kerülni**), az antenna elhelyezése (dongle az ablaknál, USB-hosszabbítóval) – [GitHub wiki](https://github.com/Valar-Systems/valar-scopes/wiki/Choosing-an-ADS-B-Receiver)
- readsb/dump1090 build – **gpsd + chrony** az időzítéshez, a Pi RTC hiánya, az antenna/koax vs. USB hossz – [GitHub](https://github.com/Wezdenko-L-L-C/adsb-receiver/blob/main/docs/BUILD.md)
- MarineTraffic – DVB-T stick AIS-vevőként, frekvenciakorrekció, egycsatornás korlát – [MT](https://support.marinetraffic.com/en/articles/9552960-how-to-build-an-ais-station-with-sdr-dvb-t)
