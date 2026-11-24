# Az AIS-vevő telepítő- és mérőscriptek

A `vessel-tracker` projekt R1-0 előkészítő fázisának **első lépése**:
a budapesti AIS-vevő megépítése és a 30 napos mérés elindítása.

**A részletes útmutató: [`PI-TELEPITES.md`](PI-TELEPITES.md)**

## A fájlok

### A Pi-n fut

| A fájl | A szerepe |
|---|---|
| `install_ais_receiver.sh` | a telepítés: az `rtl-sdr` csomag, a DVB-T driver blacklista, az AIS-catcher build (forrásból, ARM64), a systemd unit |
| `start_measurement.sh` | a mérési üzemmód: a helyi SQLite kimenet, a **boot utáni lehúzás** (a systemd `ExecStartPost`), a heti biztonsági cron, a sudoers-szabály |
| `ais-pull-after-boot.sh` | a lehúzás a service indulása után (a Pi éjszaka ki, reggel 8-kor be → **a fix orás cron soha nem futna**) |
| `ais-fetch-weekly.sh` | a heti lehúzás a NAS-ra (a Pi → NAS direkt SSH-vel) |
| `ais-fetch.cron` | a cron-vonal (a **miklos crontabjába** kerül, **nem** a `/etc/cron.d`-be) |

### A NAS-on fut

| A fájl | A szerepe |
|---|---|
| `nas_receive_ais.sh` | a fogadó: elmenti a lehúzott DB-t, **törli a 35 naposnál régebbieket és az azonos napi duplikátumokat**, elutasítja az üres adatot |

### A mérés elemzése (a Pi-n vagy a NAS-on)

| A fájl | A szerepe |
|---|---|
| `analyze_measurement.py` | a go/no-go metrikák (az üzenetszám, a hibás arány, a statikus adatok, a **geográfiai korridor-lefedettség**, a belvízi FI 10) |
| `report_signals.sh` | a fogott jelek statisztikája (az üzenettípus, a csatorna, a PPM) |
| `report_range.py` | a vevő valódi helyzete, a korridor és a hajólista |
| `report_vessels.sh` | a hajók, a Duna kilométerjelölések és a FI 10 (ENI) tartalma |
| `inspect_schema.py` | a SQLite séma felismerése (a mérés után, az oszlopnevek pontosításához) |
| `make_type_case.py` | **a `shiptype` CASE lista generálása** a `02` – DDL-terv seedjéből (a `--check` a CI-ban: a riport és a DB egyezése) |

### A telepítéshez (a Mac-en, egyszer)

| A fájl | A szerepe |
|---|---|
| `make_cloudinit.sh` / `make_cloudinit.py` | a cloud-init fájlok (a Pi OS első indításához) |
| `install_pi_os.sh` | a Raspberry Pi Imager CLI hívása (a kártya előkészítése) |
| `fix_ssh_key.sh` | az SSH-kulcs betelepítése a Pi-ra (a cloud-init nem teszi oda) |

> **A `report_vessels.sh` a `shiptype` CASE listát a `make_type_case.py`
> generálja** → **a magyar hajótípus-nevek mindig a DB-vel egyeznek.**
> A seed változásakor: `python3 scripts/ais-receiver/make_type_case.py`
> (a repo gyökeréből), majd a CASE blokk cseréje.

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
