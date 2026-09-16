# hass-zhsunyco
[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?logo=home-assistant)](https://hacs.xyz/)
[![GitHub Release](https://img.shields.io/github/release/eigger/hass-zhsunyco.svg)](https://github.com/eigger/hass-zhsunyco/releases)
[![License](https://img.shields.io/github/license/eigger/hass-zhsunyco)](https://github.com/eigger/hass-zhsunyco/blob/main/LICENSE)
![integration usage](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=%24.zhsunyco.total)

Zhsunyco BLE Electronic Shelf Label (ESL) Home Assistant Integration

---

## What is an electronic label?

An **electronic label** (electronic shelf label, ESL) is a low-power **e-paper** display that keeps showing content **without continuous power**.

This integration provides local BLE push communication with **Zhsunyco** ESL tags across **WOLINK**, **easyTag (eLabel)**, and **PickSmart (gicisky)** BLE protocol families.

They work well for information that should stay visible, changes infrequently, and lives where mains power is impractical — retail tags, home dashboard status displays, room calendars, sensors, and inventory monitors.

---

## Feedback & Support

- Found a bug? [Open an issue](https://github.com/eigger/hass-zhsunyco/issues)
- Questions or ideas? [Join the discussion](https://github.com/eigger/hass-zhsunyco/discussions)

---

## Supported Models

> [!WARNING]
> **Hardware Testing Notice**: None of the models listed below have been physically tested on actual hardware yet.
> Implementations and model presets are built according to technical specifications. If you test any of these devices, please share your results in [Discussions](https://github.com/eigger/hass-zhsunyco/discussions) or [open an issue](https://github.com/eigger/hass-zhsunyco/issues)!

### 1. WOLINK Protocol (BWRY / 2bpp)

| Size | Resolution | Colors |
|------|------------|--------|
| 1.54" | 200 × 200 | BWRY |
| 2.13" | 250 × 122 | BWRY |
| 2.66" | 296 × 152 | BWRY |
| 2.90" | 296 × 128 | BWRY |
| 3.50" | 384 × 184 | BWRY |
| 3.70" | 416 × 240 | BWRY |
| 4.20" | 400 × 300 | BWRY |
| 5.83" | 648 × 480 | BWRY |
| 7.50" | 800 × 480 | BWRY |
| 10.2" | 960 × 640 | BWRY |
| 13.3" | 960 × 680 | BWRY |

### 2. easyTag Protocol (eLabel)

| Model | Size | Resolution | Colors |
|-------|------|------------|--------|
| ET0154-33B | 1.54" | 200 × 200 | BWR |
| ETR0213-36B | 2.13" | 250 × 122 | BWR |
| ETR0213-39B | 2.13" | 250 × 122 | BW |
| ET0266-3A | 2.66" | 296 × 152 | BWR |
| ET0290-3DB | 2.90" | 296 × 128 | BWR |
| ETR290-FF | 2.90" | 296 × 128 | BWR |
| ET0350-55B | 3.50" | 384 × 184 | BWR |
| ET0420-40B / 43B | 4.20" | 400 × 300 | BWR |
| ETR0580-4FB | 5.80" | 648 × 480 | BWR |
| ET0750-44B | 7.50" | 800 × 480 | BWR |
| ET1020-64 | 10.2" | 960 × 640 | BWR |

### 3. PickSmart Protocol (gicisky)

| Type | Size | Resolution | Colors |
|------|------|------------|--------|
| TFT | 2.1" | 250 × 132 | BW |
| EPD | 2.1" | 212 × 104 | BWR |
| EPD | 2.1" | 250 × 128 | BWR |
| EPD | 2.9" | 296 × 128 | BW |
| EPD | 2.9" | 296 × 128 | BWR |
| EPD | 2.9" | 296 × 128 | BWRY |
| EPD | 3.7" | 240 × 416 | BWR |
| EPD | 4.2" | 400 × 300 | BWR |
| EPD | 4.2" | 400 × 300 | BWRY |
| EPD | 7.5" | 800 × 480 | BWR |
| EPD | 10.2" | 960 × 640 | BWR |

---

## Where to Buy

- [AliExpress - Zhsunyco BLE Electronic Shelf Label](https://ko.aliexpress.com/item/1005009231276243.html)

---

## Installation

1. Install via **HACS** (custom repository), or copy this repository into `custom_components/zhsunyco`.
2. Restart Home Assistant.
3. Add the integration via **Settings** → **Devices & Services** → **Add Integration** → **Zhsunyco** (or auto-discover via Bluetooth).

---

## Important Notice

Use a **Bluetooth proxy** instead of a built-in adapter when possible — especially with multiple BLE devices nearby.

> [!TIP]
> Hardware recommendations: [Great ESP32 Board for an ESPHome Bluetooth Proxy](https://community.home-assistant.io/t/great-esp32-board-for-an-esphome-bluetooth-proxy/916767/31)

Keep the proxy scan interval at its default. **`bluetooth_proxy` must have `active: true`.**

```yaml
esp32_ble_tracker:
  scan_parameters:
    active: true

bluetooth_proxy:
  active: true
```

---

## Options

Configure via **Settings** → **Devices & Services** → **Zhsunyco** → **Configure**:

| Option | Default | Range | Description |
|--------|---------|-------|-------------|
| **Protocol Backend** | auto / wolink | wolink / easytag / picksmart | Target BLE protocol family |
| **Model** | 2.9" (296×128) | model list | Hardware resolution profile |
| **Retry Count** | 3 | 1–10 | Retries when a BLE write fails |
| **Write Delay (ms)** | 0 | 0–1000 | Extra pause between BLE write packets |
| **Prevent Duplicate Send** | false | on/off | Skip sending when image data is unchanged |
| **Debounce Delay (ms)** | 0 | 0–120000 | Wait before writing; new requests cancel pending ones (`0` = immediate) |

> [!TIP]
> Unstable writes: try **Write Delay** 50–100 ms. Frequent automations: enable **Prevent Duplicate Send** and/or **Debounce Delay** to save tag battery and reduce BLE airtime.

---

## Payload & rendering (`imagespec`)

Labels are rendered with **[imagespec](https://github.com/eigger/imagespec)** — a declarative YAML/JSON list of drawing elements packed and sent to the e-paper panel.

**Documentation (maintained in imagespec, not duplicated here):**

| Topic | Link |
|-------|------|
| Element examples with preview images | [imagespec/docs/elements.md](https://github.com/eigger/imagespec/blob/main/docs/elements.md) |
| All element fields & defaults | [imagespec README — Element Reference](https://github.com/eigger/imagespec#elements-reference) |
| Layout, palette, LLM authoring guide | [imagespec/docs/authoring.md](https://github.com/eigger/imagespec/blob/main/docs/authoring.md) |
| Dithering (per-element only) | [imagespec/docs/dithering.md](https://github.com/eigger/imagespec/blob/main/docs/dithering.md) |

**Zhsunyco-specific behaviour:**

- **Resolution:** `width` and `height` come from the **device preset**, not the service call.
- **Palette:** auto-selected per tag profile — BW, BWR (`black`/`white`/`red`), or BWRY (+ `yellow`). Off-palette colors are quantized to the nearest supported color.
- **Rotation:** `rotate: 90/180/270` uses **canvas mode** — the fixed panel rotates; output size stays the device resolution.
- **Default font:** `NotoSansKR-Regular.ttf` in `custom_components/zhsunyco/fonts/`. Custom fonts also work from `www/fonts/`.
- **`plot` element:** reads history from Home Assistant **Recorder**.
- **`dlimg`:** local file paths under `/config/...` are allowed (HTTP/HTTPS and data URIs too).
- **Dithering:** not a service option. Put `dither` on **photos and charts** in the payload — `dlimg`, `pie`, `diagram`, `plot`, `sparkline`, `progress_bar`, `gauge` — when they use off-palette colors. Leave text without `dither`. See [dithering.md](https://github.com/eigger/imagespec/blob/main/docs/dithering.md).
- **Layout:** prefer `row` / `column` / `stack` over hand-placed coordinates.
- **Image entities:** each tag exposes **Last Updated Content** (last image sent) and **Preview Content** (`dry_run` renders).

---

## Services

### `zhsunyco.write`

Renders the payload and sends it to the tag (unless `dry_run: true`).

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `payload` | yes | — | List of [imagespec elements](https://github.com/eigger/imagespec/blob/main/docs/elements.md) |
| `rotate` | no | `0` | `0`, `90`, `180`, or `270` |
| `background` | no | `white` | `white`, `black`, `red`, or `yellow` |
| `dry_run` | no | `false` | Render only; updates **Preview Content** image entity without BLE send |

Basic example:

```yaml
action: zhsunyco.write
target:
  device_id: <your device>
data:
  payload:
    - type: text
      value: Hello World!
      x: 10
      y: 10
      size: 40
```

### Per-element dither (photos / charts)

Do **not** dither the whole panel. Add `dither` on chart/media elements that use off-palette colors (`dlimg`, `pie`, `diagram`, `plot`, `sparkline`, `progress_bar`, `gauge`):

```yaml
action: zhsunyco.write
target:
  device_id: <your device>
data:
  payload:
    - type: text
      value: Living room
      x: 10
      y: 8
      size: 28
    - type: dlimg
      url: "/config/www/photo.jpg"
      x: 10
      y: 40
      xsize: 120
      ysize: 90
      dither: floyd
    - type: pie
      x: 150
      y: 40
      radius: 40
      values: "A,40,orange;B,60,blue"
      dither: atkinson
    - type: diagram
      x: 250
      y: 40
      width: 130
      height: 90
      bars:
        values: "Mon,10;Tue,25;Wed,15;Thu,30"
        color: orange
      dither: bayer8
```

Rotation and background:

```yaml
action: zhsunyco.write
target:
  device_id: <your device>
data:
  rotate: 90
  background: black
  payload:
    - type: text
      value: Rotated!
      x: 10
      y: 10
      size: 30
      color: white
```

Preview without sending (`dry_run` updates the tag's **Preview Content** image entity):

```yaml
action: zhsunyco.write
target:
  device_id: <your device>
data:
  dry_run: true
  payload:
    - type: text
      value: Preview Test
      x: 10
      y: 10
      size: 30
```

Combined dashboard-style example:

```yaml
action: zhsunyco.write
target:
  device_id: <your device>
data:
  background: white
  payload:
    - type: text
      value: "Home Status"
      x: 10
      y: 5
      size: 24
      font: "fonts/NotoSansKR-Bold.ttf"
    - type: line
      x_start: 0
      x_end: 250
      y_start: 35
      y_end: 35
      fill: black
      width: 1
    - type: icon
      value: thermometer
      x: 10
      y: 45
      size: 24
    - type: text
      value: "{{ states('sensor.temperature') }}°C"
      x: 40
      y: 48
      size: 20
    - type: progress_bar
      x_start: 10
      y_start: 80
      x_end: 240
      y_end: 95
      progress: "{{ states('sensor.humidity') | int }}"
      fill: black
      show_percentage: true
    - type: qrcode
      data: "https://www.home-assistant.io"
      x: 180
      y: 40
      width: 60
      height: 60
```

### `zhsunyco.write_guarded`

Same rendering as `zhsunyco.write`, with guards before BLE transmission:

- duplicate image skip (when **Prevent Duplicate Send** is enabled)
- write lock check
- debounce scheduling (**Debounce Delay** option, overridable per call)

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `payload` | yes | — | Same as `zhsunyco.write` |
| `rotate`, `background`, `dry_run` | no | — | Same as `zhsunyco.write` |
| `debounce_override_ms` | no | option value | Override debounce for this call (`0` = write immediately) |

```yaml
action: zhsunyco.write_guarded
target:
  device_id: <your device>
data:
  payload:
    - type: text
      value: Guarded Write
      x: 10
      y: 10
      size: 36
```

Immediate write (skip debounce once):

```yaml
action: zhsunyco.write_guarded
target:
  device_id: <your device>
data:
  debounce_override_ms: 0
  payload:
    - type: text
      value: Immediate
      x: 10
      y: 10
      size: 36
```

| Service | When to use |
|---------|-------------|
| `zhsunyco.write` | Always send (except explicit `dry_run`) |
| `zhsunyco.write_guarded` | Automations that fire often; skip duplicates and coalesce rapid updates |

---

## Fonts

The default font is `fonts/NotoSansKR-Regular.ttf`. The integration checks `custom_components/zhsunyco/fonts/` first, then `config/www/fonts/`.

### Built-in fonts

| Family | Files |
|--------|-------|
| **CookieRun** | `CookieRunRegular.ttf`, `CookieRunBold.ttf`, `CookieRunBlack.ttf` |
| **Gmarket Sans** | `GmarketSansTTFLight.ttf`, `GmarketSansTTFMedium.ttf`, `GmarketSansTTFBold.ttf` |
| **Noto Sans KR** | Thin through Black weights (`NotoSansKR-*.ttf`) |
| **OwnglyphParkDaHyun** | `OwnglyphParkDaHyun.ttf` |

Custom font example:

```yaml
- type: text
  value: "Custom Font"
  x: 10
  y: 10
  size: 30
  font: "MyCustomFont.ttf"
```

Place `MyCustomFont.ttf` in `config/www/fonts/`.

---

## References

- [imagespec](https://github.com/eigger/imagespec) — declarative rendering engine

