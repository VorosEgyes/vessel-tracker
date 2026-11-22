# A Budapesti AIS-vevő — telepítési útmutató (a gyakorlatból)

> A `vessel-tracker` projekt R1-0 előkészítő fázisának első lépése.
> **Ez a dokumentum a 2026-11-22-i tényleges telepítésből származik** —
> a benne lévő tanulságok mind valós hibák voltak.

---

## A hardver

| Elem | Specifikáció | Állapot |
|---|---|---|
| **Raspberry Pi** | **Pi 4** (a 3B+ helyett: gyorsabb processzor, 2× USB 3.0 külön buszon, 5 GHz-es Wi-Fi) | ✅ |
| **Táp** | **USB-C, 5V/3A** (a Pi 4 hivatalos tápegysége) — 2,5A **brownoutot** okoz | ✅ |
| **SD-kártya** | 32 GB | ✅ |
| **RTL2832U dongle** | `0bda:2838` Realtek RTL2838UHIDIR + R820T tuner | ✅ |
| **Antenna** | AIS-re hangolt, 162 MHz | ✅ |
| **162 MHz SAW szűrő** | a túlterhelés és a LO-szivárgás ellen | ⬜ később |
| **Hálózat** | Wi-Fi `Pres-iot` | ✅ |

**A telephely:** Budapest, 3. emelet, a parttól ~2 km-re.

---

## Az öt döntő tanulság

### 1. Az `ssh` fájl a boot partíción KÖTELEZŐ

**A cloud-init a `users:` modult csak a `ssh` service elindítása UTÁN futja.**
Ha nincs `ssh` fájl a boot partíció gyökerében, akkor:
- a hálózati beállítás működik (a `bud01` hostname, a Wi-Fi rendben),
- **de az `sshd` soha nem indul el** → `Connection refused` a 22. porton.

**A megoldás (a kártya írása után):**
```bash
diskutil unmountDisk /dev/disk6
diskutil mount /dev/disk6s1
touch /Volumes/bootfs/ssh
diskutil unmountDisk /dev/disk6
```

### 2. A cloud-init `network-config` a `network:` gyökéren kell

A Raspberry Pi OS Trixie a cloud-init-et használja. **A hivatalos példa:**

```yaml
network:                    # ← NEM "version: 2" a legfelső szinten!
  version: 2
  wifis:
    renderer: NetworkManager    # ← KÖTELEZŐ (a cloud-init alapértelmezése a networkd)
    wlan0:
      dhcp4: true
      regulatory-domain: "HU"  # ← KÖTELEZŐ, enélkül a Wi-Fi NEM csatlakozik
      access-points:
        "Pres-iot":
          password: "..."
```

**A három elhagyott kulcs együtt: „a Wi-Fi nem csatlakozott".**
A `regulatory-domain` nélkül a kernel nem tudja, mely csatornát
használhatja a 5 GHz-es sávban.

### 3. Az SSH-kulcs a felhasználó blokkjában van

```yaml
users:
  - name: miklos
    groups: users,adm,dialout,...,sudo
    shell: /bin/bash
    lock_passwd: false
    plain_text_passwd: AIS01     # a cloud-init a boot után maga hasheli
    ssh_authorized_keys:          # ← a felhasználó BLOKKJÁBAN, nem top-level!
      - ssh-ed25519 AAAA...
    sudo: ALL=(ALL) NOPASSWD:ALL
```

**A top-level `ssh_authorized_keys` a Trixie-ben NEM működött** — a
kulcs nem került a felhasználó `~/.ssh/authorized_keys`-be. A javítás:
`mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys` a felhasználóval.

### 4. A dongle a KÉK (USB 3.0) portba

A `usb 1-1-port2: Cannot enable. Maybe the USB cable is bad?` hiba
(`error -71`, EPROTO) a **fehér/fekete USB 2.0 portban** jelentkezett.

**A kék USB 3.0 portba dugva azonnal felismerte:**
```
Bus 001 Device 024: ID 0bda:2838 Realtek Semiconductor Corp. RTL2838 DVB-T
Found Rafael Micro R820T tuner
```

*(A Pi 4-en a kék portok a belső USB hub mögött vannak — nagyobb
áramot adnak, és a külső SDR-dongle-ok itt működnek megbízhatóan.)*

### 5. A PPM-kalibráció kötelező

A kalibrálatlan dongle-nél: `[R82XX] PLL not locked!` — **a dekódolás
rossz lesz**. A `rtl_test -p` 10 percig fut (a melegedés miatt a ppm
driftel), és a végeredményt a `config.json` `ppm_error` mezőjébe kell
írni.

**A kalibrációt háttérben érdemes futtatni**, hogy az SSH-kapcsolat
megszakadása ne számítson:
```bash
sudo rtl_test -p > /tmp/ppm.txt 2>&1
```

---

## A telepítés lépései (a jelenlegi, működő sorrend)

### A) Az SD-kártya előkészítése (a Macen)

```bash
# a cloud-init fájlok (a Wi-Fi + a felhasználó + a kulcs)
bash ~/dev/make_cloudinit.sh bud01 miklos 'AIS01' 'Pres-iot' '<wifi-jelszo>' \
     "$(cat ~/.ssh/hermes_nas_ed25519.pub)" HU

# az OS képének letöltése + kiírása a kártyára
sudo bash ~/dev/install_pi_os.sh

# AZ SSH FÁJL (a kártya újra bedugása után!)
diskutil unmountDisk /dev/disk6
diskutil mount /dev/disk6s1
touch /Volumes/bootfs/ssh
diskutil unmountDisk /dev/disk6
```

### B) Az első boot

```bash
# a kártya a Pi-ba, a táp, a dongle (a KÉK portba!), az antenna
ssh miklos@bud01.local
```

### C) Az SDR telepítése

```bash
sudo apt install -y rtl-sdr
sudo tee /etc/modprobe.d/rtl-sdr-blacklist.conf <<'EOF'
blacklist dvb_usb_rtl28xxu
blacklist rtl2832
blacklist e4000
EOF
sudo modprobe -r dvb_usb_rtl28xxu   # a reboot nem kell

# az AIS-catcher build (a Pi 4-en ~8 perc)
sudo apt install -y git make gcc g++ cmake pkg-config \
     libsqlite3-dev libssl-dev zlib1g-dev librtlsdr-dev
git clone --depth 1 https://github.com/jvde-github/AIS-catcher.git
cd AIS-catcher && mkdir build && cd build && cmake .. -DCMAKE_BUILD_TYPE=Release
make -j4 && sudo make install
```

### D) A kulcs elhelyezése (ha a cloud-init nem tette)

```bash
cat ~/.ssh/hermes_nas_ed25519.pub | ssh miklos@bud01.local \
  'mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
```

### E) A kalibráció és a mérés

```bash
ssh miklos@bud01.local
sudo rtl_test -p > /tmp/ppm.txt 2>&1   # 10 perc
tail -3 /tmp/ppm.txt                   # a ppm correction értéke

sudo bash ~/ais-scripts/start_measurement.sh
```

---

## A fájlok

| A fájl | A szerepe |
|---|---|
| `install_pi_os.sh` | az OS-telepítés (a kép letöltése, a SHA-256, a cloud-init, a lemez írása) |
| `make_cloudinit.sh` / `.py` | a cloud-init `user-data` + `network-config` generálása (a netplan-formátum ellenőrzéssel) |
| `fix_ssh_key.sh` | az SSH-kulcs elhelyezése, ha a cloud-init nem tette |
| `install_ais_receiver.sh` | az `rtl-sdr` telepítése, a driver blacklista, az AIS-catcher build, a systemd unit |
| `start_measurement.sh` | a mérési üzemmód (a helyi SQLite + a heti lehúzás) |
| `ais-fetch-weekly.sh` | a heti lehúzás a NAS-ra (a Pi-ről, direkt SSH-vel) |
| `ais-fetch.cron` | a cron-vonal (hétfő 04:17) |
| `nas_receive_ais.sh` | **a NAS oldalon** — ez fogadja a lehúzást (`/usr/local/bin/nas-receive-ais.sh`) |
| `analyze_measurement.py` | a go/no-go metrikák |
| `inspect_schema.py` | a SQLite séma felismerése |

---

## A heti lehúzás: Pi → NAS (a Mac nélkül)

**A lánc a Mac megkerülésével működik** — a Mac nem mindig van
bekapcsolva, és a NAS (`192.168.0.207`) a Pi-ról közvetlenül elérhető
(4,5 ms RTT).

```
Pi (bud01)  ──SSH──>  NAS (Artemis, 192.168.0.207)
 ~/.ssh/ais_pull_key      authorized_keys:
                           command="sudo -n /usr/local/bin/nas-receive-ais.sh"
```

### A Pi oldalon

```bash
# a kulcs (ha még nincs)
ssh-keygen -t ed25519 -N "" -C "ais-pull@bud01" -f ~/.ssh/ais_pull_key

# a heti lehuzas script
sudo install -m 755 ais-fetch-weekly.sh /usr/local/bin/ais-fetch-weekly.sh

# a cron-vonal
sudo install -m 644 ais-fetch.cron /etc/cron.d/ais-fetch
```

### A NAS oldalon (egyszer, a `hermesadmin` userrel)

```bash
# a fogado script
sudo install -m 755 nas_receive_ais.sh /usr/local/bin/nas-receive-ais.sh

# a Pi kulcs hozzaadasa a "command=" korlatozassal
# (a kulccsal CSAK a lehuzas futhat!)
echo 'command="sudo -n /usr/local/bin/nas-receive-ais.sh",no-agent-forwarding,no-port-forwarding,no-pty,no-X11-forwarding ssh-ed25519 AAAA... ais-pull@bud01' \
  | sudo tee -a ~/.ssh/authorized_keys > /dev/null
sudo chmod 600 ~/.ssh/authorized_keys
```

### A teszt

```bash
# a Pi-ről
/usr/local/bin/ais-fetch-weekly.sh
# -> "a heti lemezhuzas kesz: /opt/data/martin/work/ais-data/ais-YYYYMMDD-HHMM.db"

# a NAS-on (a konténerben)
/opt/data/martin/work/ais-data/ais-YYYYMMDD-HHMM.db
```

### A gyakorlati hibák

| A hiba | A megoldás |
|---|---|
| `attempt to write a readonly database` | a `sudo`-val készített másolat root-tulajdonú lett; a cél a `~/.ais-pull/` mappa legyen, és utána `chown` a `miklos`-ra |
| `unable to open database` | a `/var/lib/ais` könyvtár `0750 ais:ais` — a `sqlite3`-ot `sudo`-val kell futtatni |
| `Pseudo-terminal will not be allocated` | ez **nem hiba**, csak a távoli SSH üzenete (a stdin nem terminál) |

## A megépítés utáni teendők (a mérés mellett)

| # | Teendő | A terv |
|---|---|---|
| 1 | a **fixture-ök** a repóba (50 üzenet a mérésből) | 04 – AIS-parser |
| 2 | a **saját dekóder** megírása (a `pyais`-szal és az `aiscat`-tel referencia) | 04 – AIS-parser |
| 3 | a **heti lehúzás** a NAS-ra | a `start_measurement.sh` (a cron-vonalat is beírja) |
| 4 | a **szűrő** megvásárlása, ha a FI 10 nem érkezik | az `ais-vevo-terv.md` |
