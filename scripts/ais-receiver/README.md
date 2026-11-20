# Az AIS-vevő telepítő- és mérőscriptek

A `vessel-tracker` projekt R1-0 előkészítő fázisának **első lépése**:
a budapesti AIS-vevő megépítése és a 30 napos mérés elindítása.

**A részletes útmutató: [`PI-TELEPITES.md`](PI-TELEPITES.md)**

## A fájlok

| A fájl | A szerepe |
|---|---|
| `install_ais_receiver.sh` | a telepítés: az `rtl-sdr` csomag, a DVB-T driver blacklista, az AIS-catcher build (forrásból, ARM64), a systemd unit |
| `start_measurement.sh` | a mérési üzemmód: a helyi SQLite kimenet (a mérési adathalmaz), a heti lehúzás a NAS-ra |
| `analyze_measurement.py` | a mérés elemzése: a go/no-go metrikák (az üzenetszám, a hibás arány, a statikus adatok, a korridor, a belvízi FI 10) |
| `inspect_schema.py` | a SQLite séma felismerése (a mérés után, az oszlopnevek pontosításához) |

## A gyors indítás

```bash
# a Pi-n
sudo bash install_ais_receiver.sh     # a telepítés (a build ~10-15 perc)
sudo bash start_measurement.sh        # a mérés indítása
```

## A döntő pontok

1. **`rtl_test -t`** — látja-e a donglet? (a DVB-T driver letiltása után)
2. **`rtl_test -p`** — a PPM-kalibráció (10 perc) — **a legfontosabb lépés**
3. **`rtl_ais -p 161975 -s 162025 -g 20`** — jön-e jel? (a konyhában
   általában nem — ez normális)
4. **a belvízi FI 10** — ezen múlik az ENI, azaz a katalógus

**A részletek: [`PI-TELEPITES.md`](PI-TELEPITES.md)**
