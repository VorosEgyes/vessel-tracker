# A Budapesti AIS-vevő — az első lépések

> A `vessel-tracker` projekt R1-0 előkészítő fázisának **első lépése**.
> A háttér: a [`docs/ais-vevo-terv.md`](../docs/ais-vevo-terv.md)
> (a vevőhálózat terve) és a
> [`docs/pi-eloallitas.md`](../docs/pi-eloallitas.md) (a Pi előállítása).

---

## Mi a helyzet

| Van | Nincs (még) |
|---|---|
| ✅ Raspberry Pi | ⬜ 162 MHz-es **SAW szűrő** (a jel/zaj arányt javítja — később) |
| ✅ SD-kártya | ⬜ **5V/2,5A** táp (a Pi 3B+ ezt igényli) |
| ✅ RTL2832U USB dongle | ⬜ a Pi hálózati elérése (a statikus IP) |
| ✅ antenna | ⬜ a hosszú távú hálózati út (a NAS-ig) |

**A szűrő nélkül is mérhetünk** — csak gyengébb jel/zaj aránnyal. A
szűrő **a mérés minőségét** javítja, nem a működőképességet.

---

## A sorrend

```
[1] OS + hálózat a Pi-n        ← 20 perc
[2] rtl-sdr telepítés         ← 5 perc
[3] DVB-T driver letiltása    ← 5 perc (+ reboot)
[4] a dongle felismerése      ← 2 perc  ← ELDÖNTŐ PONT
[5] PPM-kalibráció             ← 10 perc ← ELDÖNTŐ PONT
[6] a helyi AIS-teszt          ← 5 perc  ← ELDÖNTŐ PONT
[7] a mérés indítása (30 nap)  ← 2 perc
[8] a tetőn/vízparton a döntő teszt (a FI 10) ← ELDÖNTŐ PONT
```

**A [4], [5], [6] és [8] pontok döntőek** — ha ezek nem működnek,
a mérés nem ad használható adatot.

---

## [1] Az OS és a hálózat

Ha az SD-kártyán **már van** Raspberry Pi OS, ugorjunk a [2]-re.

Ha nincs:
1. a **Raspberry Pi Imager** letöltése (a számítógépedre)
2. az OS kiválasztása: **Raspberry Pi OS Lite (64-bit)** — a Full
   feleslegesen fogyaszt RAM-ot, és mi nem kell grafikus felület
3. a **beállítások az Imagerben** (ez a legfontosabb lépés):
   - hostname: `bud01`
   - felhasználó + jelszó (a **sudo**-hoz)
   - **SSH bekapcsolva** (a "Services" fülön)
   - időzóna: `Europe/Budapest`
   - hálózat: a Wi-Fi vagy az Ethernet
4. a beállítás a MicroSD-re

**Utána, a Pi-on:**
```bash
sudo apt update && sudo apt full-upgrade -y
timedatectl          # az NTP-nek működnie kell
```

**A statikus IP:** a routeren foglalj le egy DHCP-foglalást a Pi
MAC-címére (a `ip link show` kiírja). A Pi IP-jét **neked kell
megadnod** — innen nem látom.

---

## [2]–[3] Az SDR telepítése és a driver letiltása

```bash
sudo apt install -y rtl-sdr
```

> **Ha a `rtl-sdr` nem található a Raspberry Pi OS repójában:** a
> `rtl-sdr` külön repository-ból jön (a `pi.raspberrypi.com` /
> `raspberrypi.org` repója). A hibaüzenet a telepítéskor elmondja,
> mit kell hozzáadni.

**A DVB-T driver letiltása** — különben a kernel lefoglalja a
donglet, és a `rtl_test` nem látja:

```bash
sudo tee /etc/modprobe.d/rtl-sdr-blacklist.conf <<'EOF'
blacklist dvb_usb_rtl28xxu
blacklist rtl2832
blacklist e4000
EOF
sudo reboot
```

---

## [4] A dongle felismerése — a döntő pont

```bash
rtl_test -t
```

**A várt kimenet:**
```
Found Rafael Micro R820T tuner
Supported gain values: ...
```

**Ha nem látja a donglet:**

| A tünet | A valószínű ok |
|---|---|
| `lsusb` sem látja | **USB-kábel vagy tápellátás** — az RTL stick-nek 2 USB port kell (egy az adatnak, egy a tápnek) |
| `lsusb` látja, `rtl_test` nem | a **DVB-T driver** még aktív (a blacklista nem működött) |
| `rtl_test` hibát dob a tunerre | az **R820T tuner chip** nem található (a dongle más típusú) |

```bash
lsusb | grep -i realtek
dmesg | tail -20
```

---

## [5] A PPM-kalibráció — a legfontosabb lépés

**A frekvenciapontatlanság a legnagyobb korlát:** a generikus dongle
frekvenciája több tíz ppm-rel elcsúszhat, és **±3 ppm már rontja a
dekódolást**.

```bash
rtl_test -p
```

**10 percig futnia kell, nyugodtan** (a melegedés miatt a ppm
értéke változik — ez a drift, amit kalibrálunk). A végén:

```
ppm correction: 3.4 ppm
```

**Ezt az értéket JEGYZD FEL** — ez kerül az `AIS-catcher` konfigurációba.

> **A dongle típusa számít:** ha nincs benne TCXO (a legtöbb
> RTL2832U-ban nincs), a ppm **a hőmérséklettel driftel** — nyáron
> más érték kell. A TCXO-s változat (a „RTL-SDR Blog V3", 0,5 ppm)
> stabilabb, de nem szükséges a mérés indításához.

---

## [6] A helyi AIS-teszt

```bash
rtl_ais -p 161975 -s 162025 -g 20
```

**Amit keresünk:** a `!AIVDM,...` sorokat.

> **A lakásban valószínűleg nem lesz jel** — a házak fala mögött
> nincs AIS. Ez **normális**. A valódi teszt a tetőn vagy a
> Duna-parton (a [8] pont).

**Ha a konyhában mégis van jel** (a szerencsés eset) — az azt jelenti,
hogy a ház közel van a folyóhoz vagy egy nagyon erős vevő van a
szomszédban.

---

## [7] A 30 napos mérés indítása

A `scriptek/` mappából:

```bash
scp install_ais_receiver.sh start_measurement.sh modmj@<pi-ip>:~/
ssh modmj@<pi-ip>
sudo bash install_ais_receiver.sh     # a telepítés (a build ~10-15 perc)
sudo bash start_measurement.sh        # a mérés indítása
```

**A mérés a helyi SQLite-ba ír** — a 30 napos próbaüzemhez **nem kell
semmilyen szerver**. A nyers adatot hetente lehúzzuk, és a 30 nap
után offline feldolgozzuk.

**A heti lehúzás** a `NAS_TARGET` env-ben állítható (alapértelmezés:
`modmj@192.168.1.205` — a NAS).

### A mérés ellenőrzése (napi szinten)

```bash
sqlite3 /var/lib/ais/ais.db "SELECT count(*) FROM ais_message;"
sqlite3 /var/lib/ais/ais.db "SELECT msg_type, count(*) FROM ais_message GROUP BY 1;"
journalctl -u ais-receiver -f
```

**Ha az üzenetszám 0:** a dongle nem lát jelet (a [8] pontra kell
menni), vagy a PPM nincs beállítva.

---

## [8] A döntő teszt — a belvízi FI 10

**Ez a projekt legfontosabb technikai kérdése.**

A Duna hajói a **szabványos AIS** üzeneteken kívül **Inland AIS
FI 10** üzeneteket is küldenek (DAC 200, FID 10) — ezek tartalmazzák
az **ENI-t**, a hajó nevét és a méreteit. **Ezen múlik a katalógus:**
az ENI a Duna-katalógus elsődleges azonosítója (a README 3.3/B).

**A teszt:**
```bash
# a web-térkép a szűrőkkel (a statisztikus nézet)
http://<pi-ip>:8080
```
**a tünetes státuszsorban keresd az „Inland" / „InlandAIS" szűrőt**
(az AIS-catcher külön jelöli a belvízi üzeneteket).

**Vagy a nyers kimenetben:**
```bash
sqlite3 /var/lib/ais/ais.db \
  "SELECT count(*) FROM ais_message WHERE msg_type = 8;"
```
**A Msg 8 a belvízi statikus üzenet** (a szabványos AIS-ben a Msg 8
a biztonsági üzenet — a különbséget a `nmea` tartalom és a
`DAC 200` jelzi).

### Ha nincs FI 10

| A valószínű ok | A megoldás |
|---|---|
| **a PPM nincs pontos** | újrakalibrálás, `ppm_error` beírása |
| **az antenna túl alacsonyan van** | a tetőre (a horizont +2-3 km) |
| **a helyszín rossz** | a Duna-partra kell menni (a lakás 2 km-re van a folyótól) |
| **túlterhelés** | **a szűrő kell** (a szűrő nélkül a városi zaj elnyomja a jelet) |
| **a frekvencia rossz** | a 161,975 + 162,025 MHz sávon belül kell lenni — az AIS-catcher `filters` beállítása |

> **Ha a szűrő nélkül nincs FI 10, de a szabványos AIS jön:** a
> vevő működik, de a **belvízi üzenetek** hiányoznak — ez a
> szűrő/erősítő/pozíció kérdése. **Ez a tipikus eredmény**, és a
> szűrő megvásárlása **indokolt**.

---

## A szerveroldal (később)

A mérés alatt **nem kell** a NAS-hoz semmi. A központi ingest (MQTT
broker + a Python ingest) a 30 nap **után** indul:

1. a **Mosquitto** a NAS-on (TLS, a `duna/ais/<site>/msg` témával)
2. a `data_source` és az `ais_receiver_site` seed a Postgresben
3. az ingest szolgáltatás (a `04` – AIS-parser terv alapján)

---

## A fájlok

| A fájl | A szerepe |
|---|---|
| `install_ais_receiver.sh` | a telepítés (rtl-sdr, a driver blacklista, az AIS-catcher build, a systemd unit) |
| `start_measurement.sh` | a mérési üzemmód (a SQLite kimenet, a heti lehúzás) |
| `analyze_measurement.py` | a mérés elemzése (a go/no-go metrikák) |
| `inspect_schema.py` | a SQLite séma felismerése (a mérés után, az oszlopnevekhez) |

---

## A kérdések, amikre szükség van

1. **Az OS már a kártyán van?** (és a hostname/SSH be van állítva?)
2. **A Pi hálózati IP-je?** (a statikus foglalás után)
3. **Az antenna pontos típusa?** (AIS-optimalizált 162 MHz / 3/4 hullámos / más)
4. **Az RTL stick típusa?** (a `rtl_test -t` kimenete — a TCXO megléte)
5. **A Pi tápellátása:** 5V/2,5A? (a régi telefon-töltő 1A-val **nem elég**)
