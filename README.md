# ESP8266 Dual Sensor IoT Node
### SHARP 2Y0A21 Range + Digital Switch → Laravel API

An ESP8266 D1 Mini WiFi microcontroller reads two sensors every 30 seconds and POSTs the data to a live Laravel web API:

- **Sensor 1:** SHARP 2Y0A21 infrared range sensor (10–80 cm)
- **Sensor 2:** Any digital switch or float sensor (on/off)

Data is viewable at: `https://livewire_test-wamacq4e.on-forge.com/sensor-data`  



## Files

| File | Description |
|---|---|
| `boot.py` | WiFi connect + NTP time sync (runs on power-on) |
| `main.py` | Sensor reading + API posting loop |
| `README.md` | This file |


## Hardware Required

- ESP8266 ESP-12E D1 Mini breakout board (with CH340 USB chip)
- SHARP 2Y0A21 F 61 IR range sensor (3-wire: red/black/yellow)
- Digital switch or float sensor (2-wire, any polarity)
- 5V regulated DC power supply, minimum 1A
- Micro USB cable — **must be a data cable, not a charge-only cable**
- Jumper wires for the switch


## Wiring

**SHARP 2Y0A21 sensor:**

| Wire | Connect to |
|---|---|
| Red (Vcc) | 5V pin on board — must be 5V, not 3.3V |
| Black (GND) | GND pin on board |
| Yellow (Vout) | A0 pin on board — board has built-in voltage divider |

**Switch / float sensor:**

| Terminal | Connect to |
|---|---|
| Terminal A | D2 pin on board — internal pull-up, no resistor needed |
| Terminal B | GND pin on board |

**External DC power (when not using USB):**

| Wire | Connect to |
|---|---|
| Positive (+) | 5V (VIN) pin on board |
| Negative (−) | GND pin on board |

> **WARNING:** Never connect USB and the 5V pin at the same time.


## WiFi and API Settings

| Setting | Value |
|---|---|
| WiFi Band | 2.4GHz only (ESP8266 cannot connect to 5GHz) |
| API endpoint | `https://livewire_test-wamacq4e.on-forge.com/api/sensor-data` |
| Timezone | UTC+8 |
| Post interval | Every 30 seconds |


## Windows 11 Setup

### Step 1 — Install CH340 USB Driver

The D1 Mini uses a CH340 chip to communicate with your PC over USB. Windows 11 sometimes installs this automatically, sometimes not.

1. Plug the board into your laptop via micro USB.
2. Open Device Manager: press `Windows + X` then click **Device Manager**.
3. Look under **Ports (COM & LPT)** for `USB-SERIAL CH340 (COMx)` — if present, the driver is already installed.  
   If you see `USB2.0-Serial` under **Other devices**, the driver is missing.

If driver is missing: download from `https://www.wch-ic.com/downloads/CH341SER_EXE.html`, run the installer, reboot, then plug the board back in.

Note the COM port number (e.g. COM3, COM4) — you will need it in every command below.

---

### Step 2 — Install Python

Check if Python is installed:
```
python --version
```

If not installed, download from `https://www.python.org/downloads/`.  
**Important:** tick **"Add Python to PATH"** on the first installer screen.

---

### Step 3 — Install esptool and mpremote

Using a virtual environment is recommended to keep dependencies isolated.

**Create and activate a venv:**
```
python -m venv venv
venv\Scripts\activate
```

**Install dependencies from requirements.txt:**
```
pip install -r requirements.txt
```

Or install manually without a venv:
```
pip install esptool mpremote
```

Verify:
```
esptool version
mpremote --version
```

---

### Step 4 — Confirm Board is Detected

```
esptool --port COM3 flash-id
```

Expected output:
```
Chip type: ESP8266EX
Detected flash size: 4MB
```

If it hangs, hold the **FLASH/BOOT** button on the board while running the command. Release once you see `Connecting...`. If still failing, try a different USB cable (charge-only cables have no data wires).

---

### Step 5 — Download MicroPython Firmware

Go to `https://micropython.org/download/ESP8266_GENERIC/` and download the latest stable `.bin` file, e.g. `ESP8266_GENERIC-v1.27.0.bin`. Save it to your Downloads folder.

---

### Step 6 — Flash MicroPython onto the Board

Erase the chip first:
```
esptool --port COM3 erase_flash
```

Flash MicroPython:
```
esptool --port COM3 --baud 460800 write_flash --flash_size=detect 0x0 C:\Users\YOURNAME\Downloads\ESP8266_GENERIC-v1.27.0.bin
```

If baud 460800 fails, try `--baud 115200`.

Expected success message:
```
Hash of data verified.
Hard resetting via RTS pin...
```

---

### Step 7 — Verify MicroPython is Running

```
mpremote connect COM3
```

Press Enter. You should see `>>>`. Type `print("hello")` and expect `hello` back. Press `Ctrl+]` to exit.

---

### Step 8 — Create your config.py

Copy the example config and fill in your WiFi and API credentials:
```
copy config.example.py config.py
```

Edit `config.py` with your actual values before uploading.

---

### Step 9 — Upload boot.py, main.py, and config.py

Navigate to the folder containing the files, then:
```
mpremote connect COM3 resume fs cp boot.py :boot.py
mpremote connect COM3 resume fs cp main.py :main.py
mpremote connect COM3 resume fs cp config.py :config.py
```

> **Tip:** Use `resume` to skip the soft-reset — connect right after WiFi fails and the board shows `>>>`. See [Serial Console Debugging](#serial-console-debugging) if you have trouble.

Verify they landed on the board:
```
mpremote connect COM3 resume fs ls
```

Expected output:
```
boot.py
main.py
config.py
```


## Serial Console Debugging

### Live output via mpremote (recommended)

```
mpremote connect COM3
```

Press `Ctrl+D` to soft-reset and watch the full startup sequence.

Expected output every 30 seconds:
```
[boot] Starting in 3s - press Ctrl+C to abort
[WiFi] Connecting to Pixel8aHiro ...
[WiFi] Connected!
  IP      : 192.168.x.x
  Gateway : 192.168.x.1
[NTP] Synced! Local time (UTC+8): 2026-03-21 14:32:07
[MAIN] Starting. Interval=30s
[SENSOR1] distance=42.3cm
[POST] OK  distance=42.3cm HTTP 201
[SENSOR2] switch=0  (open)
[POST] OK  digital_input=0binary HTTP 201
[MAIN] Next in 28s | free RAM: 30000b
```

| Key | Action |
|---|---|
| `Ctrl+D` | Soft reset (restarts Python, WiFi stays connected) |
| `Ctrl+C` | Interrupt and stop the running loop |
| `Ctrl+]` | Disconnect mpremote (board keeps running on its own) |

### Alternative: PuTTY serial console

Download PuTTY from `https://www.putty.org/`.

Settings: Connection type **Serial**, Serial line `COM3`, Speed `115200`, then click Open. Press the physical **RESET** button on the board to see output from boot.

> Note: PuTTY is read-only — use mpremote for all file uploads.

### Useful debug commands

Run these in the mpremote REPL after connecting:

```python
# Check WiFi connection and IP address
import network; w=network.WLAN(network.STA_IF); print(w.isconnected(), w.ifconfig())

# Check free RAM
import gc; gc.collect(); print(gc.mem_free(), "bytes free")

# Read raw ADC value (0–15 = disconnected, 80–900 = sensor connected)
from machine import ADC; print("ADC raw:", ADC(0).read())

# Read D2 switch pin (1 = open, 0 = closed)
from machine import Pin; p=Pin(4,Pin.IN,Pin.PULL_UP); print("D2:", p.value())

# Send a test POST immediately
import main; main.post_sensor(1, 55.5, "cm", "distance")

# Read files off the board
# mpremote connect COM3 fs cat main.py
# mpremote connect COM3 fs cat boot.py
```


## Standalone Deployment (No USB)

Once `boot.py` and `main.py` are uploaded, the USB cable is no longer needed.

1. Upload both files via USB (Step 8 above)
2. Unplug the USB cable
3. Connect your 5V 1A DC supply: positive → 5V (VIN) pin, negative → GND pin
4. Board boots automatically within 5 seconds
5. Blue LED flickers during WiFi connect then settles
6. Data posts every 30 seconds with no PC needed

> **WARNING:** Do not connect USB and the 5V pin at the same time — they will fight each other through the onboard voltage regulator.


## Troubleshooting

| Symptom | Fix |
|---|---|
| Board not showing in Device Manager | Try a different USB cable; install CH340 driver (Step 1); try a different USB port |
| `esptool: Failed to connect` | Hold FLASH/BOOT button while running command, release on `Connecting...`; try baud 115200 |
| `mpremote: could not enter raw repl` | Press RESET then immediately run mpremote — the 3s countdown in boot.py will catch the interrupt |
| WiFi stuck on `waiting 1, 2, 3...` | ESP8266 is 2.4GHz only; check SSID/password case; move board closer to router |
| SENSOR1 always skipped | Check red wire is on 5V (not 3.3V); yellow wire on A0; object must be 10–80 cm away; ADC debug should read 80+ |
| Switch always reads 0 (open) | Confirm wire is on D2 not D0; confirm other terminal is on a GND pin |
| HTTP 401 Unauthorised | API key has changed — contact Hiro for the updated key, edit `API_KEY` in `main.py` and re-upload |
| HTTP 422 Validation Error | A payload field doesn't match server expectations — contact Hiro to check API validation rules |
| Device reboots every 10 seconds | Power supply too weak — must be 5V at 1A minimum; avoid shared USB chargers |
