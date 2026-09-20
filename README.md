# hass-ble-esl
[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?logo=home-assistant)](https://hacs.xyz/)
[![GitHub Release](https://img.shields.io/github/release/eigger/hass-ble-esl.svg)](https://github.com/eigger/hass-ble-esl/releases)
[![License](https://img.shields.io/github/license/eigger/hass-ble-esl)](https://github.com/eigger/hass-ble-esl/blob/main/LICENSE)
![integration usage](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=%24.ble_esl.total)

Generic BLE Electronic Shelf Label (ESL) Home Assistant Integration

## Gallery

| Size | Brand | Example |
|------|-------|---------|
| 2.1" (250×128) | Gicisky (PickSmart) | <img src="https://raw.githubusercontent.com/eigger/hass-ble-esl/main/docs/images/gicisky/21_1.png" alt="2.1 inch Gicisky" width="200" /> |
| 2.9" (296×128) | Gicisky (PickSmart) | <img src="https://raw.githubusercontent.com/eigger/hass-ble-esl/main/docs/images/gicisky/29_1.png" alt="2.9 inch Gicisky" width="200" /> |
| 4.2" (400×300) | Poshiji (XTE) PSJ-420 | <img src="https://raw.githubusercontent.com/eigger/hass-ble-esl/main/docs/images/poshiji/poshiji_psj420_4color.png" alt="4.2 inch Poshiji PSJ-420" width="200" /> |
| 10.2" (960×640) | Gicisky (PickSmart) | <img src="https://raw.githubusercontent.com/eigger/hass-ble-esl/main/docs/images/gicisky/102_1.jpg" alt="10.2 inch Gicisky" width="200" /> |

Photos are of real tags. See [Examples](#examples) for the full list with YAML, and [docs/poshiji-psj420.md](docs/poshiji-psj420.md) for the PSJ-420 setup guide.

---

## What is an electronic label?

An **electronic label** (electronic shelf label, ESL) is a low-power **e-paper** display that keeps showing content **without continuous power**.

This integration provides local BLE push communication with e-paper ESL tags across **WOLINK**, **easyTag (eLabel)**, **PickSmart (gicisky)**, and **Poshiji (XTE)** BLE protocol families.

They work well for information that should stay visible, changes infrequently, and lives where mains power is impractical — retail tags, home dashboard status displays, room calendars, sensors, and inventory monitors.

---

## Feedback & Support

- Found a bug? [Open an issue](https://github.com/eigger/hass-ble-esl/issues) and attach the tag's diagnostics: **Settings → Devices & services → BLE ESL → the device → ⋮ → Download diagnostics**. It contains the backend, preset, firmware versions, options, last advertisement and failure counters (the MAC address is redacted).
- Questions or ideas? [Join the discussion](https://github.com/eigger/hass-ble-esl/discussions)

## Related

- [hass-gicisky](https://github.com/eigger/hass-gicisky) — the original PickSmart-only integration, now archived. This repository is its successor; see [Migrating from `hass-gicisky`](#migrating-from-hass-gicisky).
- [Stash](https://github.com/eigger/stash) — self-hosted home inventory manager. Track and restock items with barcode scanning, and print labels to ESL tags via Home Assistant.

---

## Supported Models

> [!WARNING]
> **Hardware Testing Notice**: **PickSmart** (Gicisky) models are fully verified, inherited from hass-gicisky. **WOLINK** and **easyTag** models have **not** been physically tested yet — their implementations and presets are built from technical specifications.
> If you test a WOLINK or easyTag device, please share your results in [Discussions](https://github.com/eigger/hass-ble-esl/discussions) or [open an issue](https://github.com/eigger/hass-ble-esl/issues)!

Sorted by panel size. Colors: **BW** black/white · **BWR** + red · **BWRY** + red + yellow.

| Size | Resolution | Colors | Brand | Protocol | Model / Type | Status |
|------|------------|--------|-------|----------|--------------|--------|
| 1.54" | 200 × 200 | BWRY | Zhsunyco | WOLINK | — | ⚠️ untested |
| 1.54" | 200 × 200 | BWR | Zhsunyco | easyTag | ET0154-33B | ⚠️ untested |
| 2.1" | 250 × 132 | BW | Gicisky | PickSmart | TFT | ✅ verified |
| 2.1" | 212 × 104 | BWR | Gicisky | PickSmart | EPD | ✅ verified |
| 2.1" | 250 × 128 | BWR | Gicisky | PickSmart | EPD | ✅ verified |
| 2.13" | 250 × 122 | BWRY | Zhsunyco | WOLINK | — | ⚠️ untested |
| 2.13" | 250 × 122 | BWR | Zhsunyco | easyTag | ETR0213-36B | ⚠️ untested |
| 2.13" | 250 × 122 | BW | Zhsunyco | easyTag | ETR0213-39B | ⚠️ untested |
| 2.66" | 296 × 152 | BWRY | Zhsunyco | WOLINK | — | ⚠️ untested |
| 2.66" | 296 × 152 | BWR | Zhsunyco | easyTag | ET0266-3A | ⚠️ untested |
| 2.9" | 296 × 128 | BWRY | Zhsunyco | WOLINK | — | ⚠️ untested |
| 2.9" | 296 × 128 | BWR | Zhsunyco | easyTag | ET0290-3DB / ETR290-FF | ⚠️ untested |
| 2.9" | 296 × 128 | BW | Gicisky | PickSmart | EPD | ✅ verified |
| 2.9" | 296 × 128 | BWR | Gicisky | PickSmart | EPD | ✅ verified |
| 2.9" | 296 × 128 | BWRY | Gicisky | PickSmart | EPD | ✅ verified |
| 3.5" | 384 × 184 | BWRY | Zhsunyco | WOLINK | — | ⚠️ untested |
| 3.5" | 384 × 184 | BWR | Zhsunyco | easyTag | ET0350-55B | ⚠️ untested |
| 3.7" | 416 × 240 | BWRY | Zhsunyco | WOLINK | — | ⚠️ untested |
| 3.7" | 240 × 416 | BWR | Gicisky | PickSmart | EPD | ✅ verified |
| 4.2" | 400 × 300 | BWRY | Zhsunyco | WOLINK | — | ⚠️ untested |
| 4.2" | 400 × 300 | BWR | Zhsunyco | easyTag | ET0420-40B / 43B | ⚠️ untested |
| 4.2" | 400 × 300 | BWR | Gicisky | PickSmart | EPD | ✅ verified |
| 4.2" | 400 × 300 | BWRY | Gicisky | PickSmart | EPD | ✅ verified |
| 4.2" | 400 × 300 | BWRY | Poshiji | XTE | PSJ-420 | ✅ verified |
| 5.8" | 648 × 480 | BWRY | Zhsunyco | WOLINK | — | ⚠️ untested |
| 5.8" | 648 × 480 | BWR | Zhsunyco | easyTag | ETR0580-4FB | ⚠️ untested |
| 7.5" | 800 × 480 | BWRY | Zhsunyco | WOLINK | — | ⚠️ untested |
| 7.5" | 800 × 480 | BWR | Zhsunyco | easyTag | ET0750-44B | ⚠️ untested |
| 7.5" | 800 × 480 | BWR | Gicisky | PickSmart | EPD | ✅ verified |
| 10.2" | 960 × 640 | BWRY | Zhsunyco | WOLINK | — | ⚠️ untested |
| 10.2" | 960 × 640 | BWR | Zhsunyco | easyTag | ET1020-64 | ⚠️ untested |
| 10.2" | 960 × 640 | BWR | Gicisky | PickSmart | EPD | ✅ verified |
| 13.3" | 960 × 680 | BWRY | Zhsunyco | WOLINK | — | ⚠️ untested |

Protocol notes:
- **Poshiji (XTE)** — PSJ-420, 400×300 BWRY. Verified on hardware by the device owner; see [setup and protocol notes](docs/poshiji-psj420.md).
- **WOLINK** — Zhsunyco BWRY tags, 2 bpp. The 5.83" panel is listed as 5.8".
- **easyTag** — eLabel firmware sold under the Zhsunyco brand. Model code is printed on the tag.
- **PickSmart** — Gicisky tags; 2.1" TFT is an LCD (not e-paper). The 3.7" panel is portrait (240 × 416).

Have a tag that speaks another protocol? Each protocol is one self-contained package with an enforced contract — see [Adding a protocol backend](custom_components/ble_esl/esl_ble/README.md).

---

## Where to Buy

Availability varies by country. AliExpress listings by protocol family:

| Protocol | Brand | Listing |
|----------|-------|---------|
| WOLINK / easyTag | Zhsunyco | [Zhsunyco BLE Electronic Shelf Label](https://ko.aliexpress.com/item/1005009231276243.html) |
| XTE | Poshiji | [PSJ-420 4.2" BWRY](https://ko.aliexpress.com/item/1005012582138232.html) |
| PickSmart | Gicisky | [Gicisky store (item 1)](https://ko.aliexpress.com/item/1005002399342939.html) · [Gicisky store (item 2)](https://ko.aliexpress.com/item/1005002398744297.html) |

---

## Installation

1. Install via **HACS** (custom repository), or copy this repository into `custom_components/ble_esl`.
2. Restart Home Assistant.
3. Add the integration via **Settings** → **Devices & Services** → **Add Integration** → **BLE ESL** (or auto-discover via Bluetooth).

### Migrating from `hass-gicisky` or `hass-zhsunyco`

This repository supersedes two earlier integrations:

| Old repository | Old domain | Protocol here |
|----------------|------------|---------------|
| [`hass-gicisky`](https://github.com/eigger/hass-gicisky) (archived) | `gicisky` | PickSmart |
| `hass-zhsunyco` (renamed to this repo) | `zhsunyco` | WOLINK / easyTag |

The domain is now `ble_esl`. Home Assistant cannot move config entries between domains, so existing devices must be re-added:

1. Remove the existing **Gicisky** / **Zhsunyco** integration entries under **Settings** → **Devices & Services**.
2. Delete `custom_components/gicisky` / `custom_components/zhsunyco` (or uninstall the old repository in HACS) and install `hass-ble-esl`.
3. Restart Home Assistant and add your tags again. PickSmart tags are auto-discovered the same way as before.
4. Update automations and dashboards: service calls change from `gicisky.write` / `zhsunyco.write` (and `*_guarded`) to `ble_esl.write` / `ble_esl.write_guarded`, and entity IDs are regenerated. The payload format is unchanged.

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

Configure via **Settings** → **Devices & Services** → **BLE ESL** → **Configure**:

| Option | Default | Range | Description |
|--------|---------|-------|-------------|
| **Protocol Backend** | auto / wolink | wolink / easytag / picksmart / poshiji | Target BLE protocol family |
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

**Integration-specific behaviour:**

- **Resolution:** `width` and `height` come from the **device preset**, not the service call.
- **Palette:** auto-selected per tag profile — BW, BWR (`black`/`white`/`red`), or BWRY (+ `yellow`). Off-palette colors are quantized to the nearest supported color.
- **Rotation:** `rotate: 90/180/270` uses **canvas mode** — the fixed panel rotates; output size stays the device resolution.
- **Default font:** `NotoSansKR-Regular.ttf` in `custom_components/ble_esl/fonts/`. Custom fonts also work from `www/fonts/`.
- **`plot` element:** reads history from Home Assistant **Recorder**.
- **`dlimg`:** local file paths under `/config/...` are allowed (HTTP/HTTPS and data URIs too).
- **Dithering:** not a service option. Put `dither` on **photos and charts** in the payload — `dlimg`, `pie`, `diagram`, `plot`, `sparkline`, `progress_bar`, `gauge` — when they use off-palette colors. Leave text without `dither`. See [dithering.md](https://github.com/eigger/imagespec/blob/main/docs/dithering.md).
- **Layout:** prefer `row` / `column` / `stack` over hand-placed coordinates.
- **Image entities:** each tag exposes **Last Updated Content** (last image sent) and **Preview Content** (`dry_run` renders).
- **Write monitoring:** the **Write Duration** sensor's attributes describe the last write attempt — `attempt`, `success`, `error`, and the per-stage timings (`connect_s`, `session_s`; PickSmart also `start_probes`, `parts`, `resends`, `round_trip_ms`, `transfer_s`, `completed_by_tag`). Watch `start_probes` (should mostly be 1) and `round_trip_ms` (path quality) without turning on debug logging; the same data is in the diagnostics download.
- **Battery:** the tag voltage is mapped linearly to **Battery** (%) — PickSmart over 2.5–2.9 V, WOLINK / easyTag over 2.2–3.0 V — and a **Battery** binary sensor (low battery) turns on at the bottom of that range (PickSmart: 2.5 V or below, where e-paper refresh becomes unreliable even though BLE still works).

---

## Services

Both services take a standard `target:`: a BLE ESL device, any of its entities, or an area/floor/label containing one. Several tags can be targeted in one call; each is written in turn and failures are reported together at the end. The examples below use `device_id`.

### `ble_esl.write`

Renders the payload and sends it to the tag (unless `dry_run: true`).

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `payload` | yes | — | List of [imagespec elements](https://github.com/eigger/imagespec/blob/main/docs/elements.md) |
| `rotate` | no | `0` | `0`, `90`, `180`, or `270` |
| `background` | no | `white` | `white`, `black`, `red`, or `yellow` |
| `dry_run` | no | `false` | Render only; updates **Preview Content** image entity without BLE send |

Basic example:

```yaml
action: ble_esl.write
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
action: ble_esl.write
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
action: ble_esl.write
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
action: ble_esl.write
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
action: ble_esl.write
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

### `ble_esl.write_guarded`

Same rendering as `ble_esl.write`, with guards before BLE transmission:

- duplicate image skip (when **Prevent Duplicate Send** is enabled)
- write lock check
- debounce scheduling (**Debounce Delay** option, overridable per call)

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `payload` | yes | — | Same as `ble_esl.write` |
| `rotate`, `background`, `dry_run` | no | — | Same as `ble_esl.write` |
| `debounce_override_ms` | no | option value | Override debounce for this call (`0` = write immediately) |

```yaml
action: ble_esl.write_guarded
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
action: ble_esl.write_guarded
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
| `ble_esl.write` | Always send (except explicit `dry_run`) |
| `ble_esl.write_guarded` | Automations that fire often; skip duplicates and coalesce rapid updates |

### Response data

Both services can return what happened to each target. Ask for it with `response_variable`; the result is a map keyed by device id:

```yaml
- action: ble_esl.write
  target:
    device_id: <your device>
  data:
    payload: [...]
  response_variable: result
- if: "{{ result.values() | selectattr('status', 'eq', 'failed') | list }}"
  then:
    - action: notify.mobile_app_phone
      data:
        message: "ESL write failed: {{ result.values() | map(attribute='error') | join(', ') }}"
```

| `status` | Meaning | Extra fields |
|---|---|---|
| `written` | Image is on the tag | `attempts`, `duration_s`, `timing` (per-stage seconds, protocol-specific) |
| `failed` | Every attempt failed | `error`, `attempts`, `duration_s`, `timing` of the last attempt |
| `scheduled` | `write_guarded` debounced the write; it runs in the background after the quiet period (`delay_ms`). **Its result is not part of this response** — check the *Display In Sync* / *Failure Count* entities if you need it | `delay_ms` |
| `duplicate` | `write_guarded`: image unchanged, not sent (**Prevent Duplicate Send**) | |
| `locked` | Write lock switch is on; preview updated only | |
| `preview` | `dry_run`: rendered only | |

When a response is requested, a failed tag is **reported instead of raising**, so the automation continues and can branch on it. Without `response_variable` a failure still raises (and stops the automation) as before. Targeting no loaded tag at all always raises.

---

## Fonts

The default font is `fonts/NotoSansKR-Regular.ttf`. The integration checks `custom_components/ble_esl/fonts/` first, then `config/www/fonts/`.

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

## Examples

Payloads are resolution-specific, not tag-specific: any example below works on any supported tag with the same resolution, regardless of brand or protocol. All of them call `ble_esl.write` — replace `device_id` with your own device. Files live in [`examples/`](./examples) (`gicisky/` originally from [hass-gicisky](https://github.com/eigger/hass-gicisky); `poshiji/` contributed by a PSJ-420 owner, see its [README](./examples/poshiji/README.md)).

| Size | Brand | Example | Preview | YAML |
|------|-------|---------|---------|------|
| 2.1" (250×128) | Gicisky | Date | ![2.1-date.jpg](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/2.1-date.jpg) | [2.1-date.yaml](./examples/gicisky/2.1-date.yaml) |
| 2.1" (250×128) | Gicisky | Naver Weather | ![2.1-naver-weather.jpg](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/2.1-naver-weather.jpg) | [2.1-naver-weather.yaml](./examples/gicisky/2.1-naver-weather.yaml) |
| 2.1" (250×128) | Gicisky | Waste Collection | ![2.1-waste-collection.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/2.1-waste-collection.png) | [2.1-waste-collection.yaml](./examples/gicisky/2.1-waste-collection.yaml) |
| 2.1" (250×128) | Gicisky | Wifi | ![2.1-wifi.jpg](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/2.1-wifi.jpg) | [2.1-wifi.yaml](./examples/gicisky/2.1-wifi.yaml) |
| 2.1" (250×128) | Gicisky | TMap time | ![2.1-tmap-time.jpg](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/2.1-tmap-time.jpg) | [2.1-tmap-time.yaml](./examples/gicisky/2.1-tmap-time.yaml) |
| 2.9" (296×128) | Gicisky | Google Calendar | ![2.9-google-calendar.jpg](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/2.9-google-calendar.jpg) | [2.9-google-calendar.yaml](./examples/gicisky/2.9-google-calendar.yaml) |
| 2.9" (296×128) | Gicisky | Presence Display | ![2.9-presence-display.jpg](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/2.9-presence-display.jpg) | [2.9-presence-display.yaml](./examples/gicisky/2.9-presence-display.yaml) |
| 4.2" (400×300) | Gicisky | Image | ![4.2-image.jpg](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/4.2-image.jpg) | [4.2-image.yaml](./examples/gicisky/4.2-image.yaml) |
| 4.2" (400×300) | Gicisky | 기상청 Weather | ![4.2-kma-weather.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/4.2-kma-weather.png) | [4.2-kma-weather.yaml](./examples/gicisky/4.2-kma-weather.yaml) |
| 4.2" (400×300) | Gicisky | Naver Weather | ![4.2-naver-weather.jpg](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/4.2-naver-weather.jpg) | [4.2-naver-weather.yaml](./examples/gicisky/4.2-naver-weather.yaml) |
| 4.2" (400×300) | Gicisky | Date Weather | ![4.2-date-weather.jpg](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/4.2-date-weather.jpg) | [4.2-date-weather.yaml](./examples/gicisky/4.2-date-weather.yaml) |
| 4.2" (400×300) | Gicisky | Weather News | ![4.2-weather-news.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/4.2-weather-news.png) | [4.2-weather-news.yaml](./examples/gicisky/4.2-weather-news.yaml) |
| 4.2" (400×300) | Gicisky | 3D Print | ![4.2-3d-print.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/4.2-3d-print.png) | [4.2-3d-print.yaml](./examples/gicisky/4.2-3d-print.yaml) |
| 4.2" (400×300) | Poshiji | Four-color check | ![psj420-color-test.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/poshiji/psj420-color-test.png) | [psj420-color-test.yaml](./examples/poshiji/psj420-color-test.yaml) |
| 4.2" (400×300) | Poshiji | Naver Weather | ![poshiji_psj420_4color.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/docs/images/poshiji/poshiji_psj420_4color.png) | [psj420-weather-demo.yaml](./examples/poshiji/psj420-weather-demo.yaml) |
| 7.5" (800×480) | Gicisky | Google Calendar | ![7.5-google-calendar.jpg](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/7.5-google-calendar.jpg) | [7.5-google-calendar.yaml](./examples/gicisky/7.5-google-calendar.yaml) |
| 7.5" (800×480) | Gicisky | Google Calendar 2 | ![7.5-google-calender2.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/7.5-google-calender2.png) | [7.5-google-calender2.yaml](./examples/gicisky/7.5-google-calender2.yaml) |
| 7.5" (800×480) | Gicisky | Google Calendar 3 | ![7.5-google-calender3.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/7.5-google-calender3.png) | [7.5-google-calender3.yaml](./examples/gicisky/7.5-google-calender3.yaml) |
| 7.5" (800×480) | Gicisky | Date Weather | ![7.5-date-weather.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/7.5-date-weather.png) | [7.5-date-weather.yaml](./examples/gicisky/7.5-date-weather.yaml) |
| 7.5" (800×480) | Gicisky | Date Weather 2 | ![7.5-date-weather2.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/7.5-date-weather2.png) | [7.5-date-weather2.yaml](./examples/gicisky/7.5-date-weather2.yaml) |
| 7.5" (800×480) | Gicisky | Calendar Weather | ![7.5-calendar-weather.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/7.5-calendar-weather.png) | [7.5-calendar-weather.yaml](./examples/gicisky/7.5-calendar-weather.yaml) |
| 7.5" (800×480) | Gicisky | Image | ![7.5-image.jpg](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/7.5-image.jpg) | [7.5-image.yaml](./examples/gicisky/7.5-image.yaml) |
| 10.2" (960×640) | Gicisky | Calendar Weather | ![10.2-calendar-weather.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/10.2-calendar-weather.png) | [10.2-calendar-weather.yaml](./examples/gicisky/10.2-calendar-weather.yaml) |
| 10.2" (960×640) | Gicisky | Calendar Weather 2 | ![10.2-calendar-weather2.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/10.2-calendar-weather2.png) | [10.2-calendar-weather2.yaml](./examples/gicisky/10.2-calendar-weather2.yaml) |
| 10.2" (960×640) | Gicisky | Calendar | ![10.2-calendar.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/10.2-calendar.png) | [10.2-calendar.yaml](./examples/gicisky/10.2-calendar.yaml) |

---

## Tools

Web tools originally built for Gicisky tags. The payload format is shared, so they work for any protocol here — pick a matching resolution.

- **[Image Edit & Uploader](https://eigger.github.io/Gicisky_Image_Uploader.html)**
- **[Payload Editor](https://eigger.github.io/Gicisky_Payload_Editor.html)**

---

## Appendix

### T-Map integration

```yaml
# https://openapi.sk.com/products/detail?linkMenuSeq=46
rest_command:
  request_tmap_routes:
    url: https://apis.openapi.sk.com/tmap/routes?version=1
    method: POST
    headers:
      appKey: !secret tmap_api_key
      accept: "application/json, text/html"
    content_type: "application/json; charset=utf-8"
    payload: >-
      {
        "startX": {{ startX }},
        "startY": {{ startY }},
        "endX": {{ endX }},
        "endY": {{ endY }},
        "searchOption": {{ searchOption }},
        "totalValue": 2,
        "trafficInfo ": "Y",
        "mainRoadInfo": "Y"
      }
```

See [2.1-tmap-time.yaml](./examples/gicisky/2.1-tmap-time.yaml) for a full label example.

### Google Calendar

Add a remote calendar: **Settings** → **Devices & Services** → **Calendar** → add Google `*.ics` URL.

### Third-party custom components

- [기상청 APIhub (eigger)](https://github.com/eigger/hass-kma)
- [Naver Weather (minumida)](https://github.com/miumida/naver_weather)
- [ha-weathernews (dugurs)](https://github.com/dugurs/ha-weathernews)
- [Waste Collection Schedule (mampfes)](https://github.com/mampfes/hacs_waste_collection_schedule)

---

## Development

Tests run against a real Home Assistant core (`pytest-homeassistant-custom-component`), so they need the Python version current Home Assistant requires (3.14):

```bash
python3.14 -m venv .venv && source .venv/bin/activate
pip install -r requirements_test.txt
pip install -r <(python -c "import json; print('\n'.join(json.load(open('custom_components/ble_esl/manifest.json'))['requirements']))")
pip install -r <(python scripts/ha_component_requirements.py bluetooth usb recorder diagnostics)
pytest
```

CI tests against the Home Assistant release the test package pins (currently 2026.9); the declared minimum in `hacs.json` (2025.12) is supported but not exercised by the suite. `ruff check` and `ruff format --check` (version pinned in `requirements_lint.txt`) must pass; adding a protocol is described in [esl_ble/README.md](custom_components/ble_esl/esl_ble/README.md).

## References

- [imagespec](https://github.com/eigger/imagespec) — declarative rendering engine

