# hass-ble-esl
[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?logo=home-assistant)](https://hacs.xyz/)
[![GitHub Release](https://img.shields.io/github/release/eigger/hass-ble-esl.svg)](https://github.com/eigger/hass-ble-esl/releases)
[![License](https://img.shields.io/github/license/eigger/hass-ble-esl)](https://github.com/eigger/hass-ble-esl/blob/main/LICENSE)
![integration usage](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=%24.ble_esl.total)

English | **[한국어](README.ko.md)**

Generic BLE Electronic Shelf Label (ESL) Home Assistant Integration

**Battery-powered e-paper displays that show your Home Assistant data for months to years on one battery.** One action call pushes a calendar, weather, sensor readings or a photo to the tag over Bluetooth — no gateway, no cloud, no wiring.

| 2.1" (250×128) | 2.9" (296×128) | 4.2" (400×300) | 10.2" (960×640) |
|---|---|---|---|
| <img src="https://raw.githubusercontent.com/eigger/hass-ble-esl/main/docs/images/gicisky/21_1.png" alt="2.1 inch Gicisky" width="200" /> | <img src="https://raw.githubusercontent.com/eigger/hass-ble-esl/main/docs/images/gicisky/29_1.png" alt="2.9 inch Gicisky" width="200" /> | <img src="https://raw.githubusercontent.com/eigger/hass-ble-esl/main/docs/images/poshiji/poshiji_psj420_4color.png" alt="4.2 inch Poshiji PSJ-420" width="200" /> | <img src="https://raw.githubusercontent.com/eigger/hass-ble-esl/main/docs/images/gicisky/102_1.jpg" alt="10.2 inch Gicisky" width="200" /> |
| Gicisky | Gicisky | Poshiji PSJ-420 | Gicisky |

Photos of real tags. [More examples with YAML →](examples/README.md)

## Why e-paper tags?

An **electronic shelf label (ESL)** is the display retailers use for shelf prices: an **e-paper** (e-ink) screen with its own battery and a Bluetooth radio. E-paper only draws power while the picture *changes* — holding a static image costs nothing, so a tag runs for months to years on its battery, is readable in daylight like printed paper, and emits no light.

That makes them ideal for information that should just *be there*, in places with no power outlet: a room calendar on the door, today's weather by the coat rack, the bin-collection day on the fridge, a "who is home" board, the print progress on the 3D printer, an inventory label on a storage box. Stick one anywhere and forget about charging it.

This integration talks to those tags directly from Home Assistant over BLE. You describe the layout in YAML (text, icons, QR codes, charts, images — anything from your entities), and the tag shows it.

## Supported tags

Four BLE protocol families, sold under these brands:

| Protocol | Brand | Sizes | Colors | Status | Buy |
|---|---|---|---|---|---|
| **PickSmart** | Gicisky | 2.1" – 10.2" | BW / BWR / BWRY | ✅ verified on hardware | [AliExpress](https://ko.aliexpress.com/item/1005002399342939.html) |
| **XTE** | Poshiji | 1.54" – 7.5" | BWRY | ✅ PSJ-420 verified by owner; other sizes size-only presets | [AliExpress](https://ko.aliexpress.com/item/1005012725381116.html) |
| **WOLINK** | Zhsunyco | 1.54" – 13.3" | BWRY | ⚠️ from specifications, untested | [AliExpress](https://ko.aliexpress.com/item/1005009231276243.html) |
| **easyTag** (eLabel) | Zhsunyco | 1.54" – 10.2" | BW / BWR | ⚠️ from specifications, untested | — |

Full model list with resolutions and model codes: **[docs/models.md](docs/models.md)**. Have a tag that speaks another protocol? See [Adding a protocol backend](custom_components/ble_esl/esl_ble/README.md).

> [!WARNING]
> WOLINK and easyTag presets are built from technical specifications and have not been tested on physical tags. If you try one, please report the result in [Discussions](https://github.com/eigger/hass-ble-esl/discussions).

## Installation

Requires Home Assistant **2025.12** or newer.

1. Install via **HACS** (custom repository `eigger/hass-ble-esl`), or copy `custom_components/ble_esl` into your config.
2. Restart Home Assistant.
3. Tags in range are discovered automatically — confirm them under **Settings → Devices & services**, or add one via **Add integration → BLE ESL**.

Use a **Bluetooth proxy** rather than the host's built-in adapter whenever you can, and set it to **active** — most write problems trace back to a passive proxy or a weak adapter. Keep the scan interval at its default.

```yaml
esp32_ble_tracker:
  scan_parameters:
    active: true

bluetooth_proxy:
  active: true
```

> [!TIP]
> Hardware suggestions: the [Seeed Studio XIAO W5500](https://ko.aliexpress.com/item/1005009310322353.html) (XIAO ESP32 with wired Ethernet) is a good proxy — Ethernet keeps the radio free for BLE, and the community thread [Great ESP32 board for an ESPHome Bluetooth proxy](https://community.home-assistant.io/t/great-esp32-board-for-an-esphome-bluetooth-proxy/916767/31) covers other boards.

Coming from `hass-gicisky` or `hass-zhsunyco`? Tags must be re-added under the new `ble_esl` domain and `gicisky.write` renamed to `ble_esl.write` — the payload stays the same. **[Migration guide →](docs/migration.md)**

## Quick start

From **Developer tools → Actions**:

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

The tag refreshes in a few seconds. Add `dry_run: true` to render without sending — the result shows up in the tag's **Preview Content** image entity, so you can iterate on a layout without wearing the panel.

A layout is a list of [imagespec](https://github.com/eigger/imagespec) elements — text, icons, lines, QR codes, progress bars, gauges, pie/bar charts, history plots, downloaded images — and any value can be a Jinja template over your entities. Ready-made layouts for every supported resolution are in [`examples/`](examples/README.md); the [Payload Editor](https://eigger.github.io/Gicisky_Payload_Editor.html) and [Image Uploader](https://eigger.github.io/Gicisky_Image_Uploader.html) web tools let you draft one in the browser.

## Actions

Both actions take a standard `target:` (a tag device, one of its entities, or an area/floor/label containing tags) and write each target in turn.

| Action | Use it for |
|---|---|
| `ble_esl.write` | Always send (unless `dry_run`) |
| `ble_esl.write_guarded` | Automations that fire often: skips unchanged images, honours the **Write Lock** switch, and debounces bursts |

| Parameter | Default | Description |
|---|---|---|
| `payload` | — | List of [imagespec elements](https://github.com/eigger/imagespec/blob/main/docs/elements.md) (required) |
| `rotate` | `0` | `0`, `90`, `180`, `270` |
| `background` | `white` | `white`, `black`, `red`, `yellow` |
| `dry_run` | `false` | Render to **Preview Content** only |
| `debounce_override_ms` | option value | `write_guarded` only: override the debounce for this call (`0` = now) |

Both actions can return a per-tag result via `response_variable`. Full reference — dithering photos and charts, rotation, response data, the entities each tag exposes, fonts: **[docs/actions.md](docs/actions.md)**.

## Options

**Settings → Devices & services → BLE ESL → Configure**:

| Option | Default | Range | Description |
|--------|---------|-------|-------------|
| **Model** | — | model list | Shown only for protocols that cannot report their model (WOLINK, easyTag) |
| **Retry Count** | 3 | 1–10 | Retries when a BLE write fails |
| **Prevent Duplicate Send** | off | on/off | Skip sending when the image is unchanged |
| **Debounce Delay (ms)** | 0 | 0–120000 | Wait before writing; new requests cancel pending ones |

> [!TIP]
> Frequent automations: enable **Prevent Duplicate Send** and/or **Debounce Delay** to save tag battery and BLE airtime. A write that fails mid-transfer is retried with slower packet pacing; if writes keep failing, the **Write Duration** sensor's attributes say whether it is the link or the placement — see [docs/actions.md](docs/actions.md#write-breakdown).

## Payload & rendering

Layouts are rendered by **[imagespec](https://github.com/eigger/imagespec)**; its docs are the reference for elements and fields:

| Topic | Link |
|-------|------|
| Element examples with preview images | [imagespec/docs/elements.md](https://github.com/eigger/imagespec/blob/main/docs/elements.md) |
| All element fields & defaults | [imagespec README — Element Reference](https://github.com/eigger/imagespec#elements-reference) |
| Layout, palette, LLM authoring guide | [imagespec/docs/authoring.md](https://github.com/eigger/imagespec/blob/main/docs/authoring.md) |
| Dithering (per-element only) | [imagespec/docs/dithering.md](https://github.com/eigger/imagespec/blob/main/docs/dithering.md) |

What this integration adds on top:

- **Resolution and palette** come from the tag's preset, not the call. Off-palette colors are quantized to the nearest supported one (BW, BWR or BWRY).
- **Rotation** (`rotate: 90/180/270`) rotates the canvas; the output stays the panel size.
- **Dithering** is per element: put `dither` on photos and charts (`dlimg`, `pie`, `diagram`, `plot`, `sparkline`, `progress_bar`, `gauge`), not on text.
- **`plot`** reads history from the Recorder; **`dlimg`** accepts `/config/...` paths, HTTP(S) URLs and data URIs.
- **Fonts:** `NotoSansKR-Regular.ttf` is the default; drop your own `.ttf` into `config/www/fonts/` and reference it by name. See [fonts](docs/actions.md#fonts).
- Prefer `row` / `column` / `stack` layout over hand-placed coordinates.

## Feedback & support

- A label not updating? **[docs/troubleshooting.md](docs/troubleshooting.md)** — the failure sensors say where a write died and why.
- Found a bug? [Open an issue](https://github.com/eigger/hass-ble-esl/issues) and attach the tag's diagnostics: **the device page → ⋮ → Download diagnostics**. It contains the backend, preset, firmware, options, last advertisement and failure counters (MAC redacted).
- Questions or ideas? [Discussions](https://github.com/eigger/hass-ble-esl/discussions)
- Tested a WOLINK or easyTag tag, or have a Poshiji size that asked for a manual model pick? Please share — that is how presets get verified.

## Related

- [imagespec](https://github.com/eigger/imagespec) — the rendering engine behind `payload:`
- [Stash](https://github.com/eigger/stash) — self-hosted home inventory manager that prints labels to ESL tags via Home Assistant
- [hass-gicisky](https://github.com/eigger/hass-gicisky) — the archived PickSmart-only predecessor ([migration guide](docs/migration.md))
- [Development](docs/development.md) — running the test suite, lint, adding a protocol
