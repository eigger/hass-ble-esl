# hass-ble-esl
<!-- hass-standards:badges:start -->
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5?style=flat-square)](#installation)
[![Release](https://img.shields.io/github/v/release/eigger/hass-ble-esl?style=flat-square)](https://github.com/eigger/hass-ble-esl/releases)
[![Home Assistant minimum](https://img.shields.io/badge/HA-%E2%89%A5%202025.12.0-41BDF5?style=flat-square)](hacs.json)
[![Tests](https://img.shields.io/github/actions/workflow/status/eigger/hass-ble-esl/tests.yml?branch=main&style=flat-square&label=Tests)](https://github.com/eigger/hass-ble-esl/actions/workflows/tests.yml)
[![Validate](https://img.shields.io/github/actions/workflow/status/eigger/hass-ble-esl/validate.yml?branch=main&style=flat-square&label=Validate)](https://github.com/eigger/hass-ble-esl/actions/workflows/validate.yml)
[![License](https://img.shields.io/github/license/eigger/hass-ble-esl?style=flat-square)](LICENSE)
[![Analytics reporting installs](https://img.shields.io/badge/dynamic/json?style=flat-square&color=41BDF5&label=Usage&query=%24.ble_esl.total&url=https%3A%2F%2Fanalytics.home-assistant.io%2Fcustom_integrations.json)](https://analytics.home-assistant.io/)
<!-- hass-standards:badges:end -->

English | **[한국어](README.ko.md)**

Generic BLE Electronic Shelf Label (ESL) Home Assistant Integration

**Battery-powered e-paper displays that show your Home Assistant data for months to years on one battery.** BLE ESL is a [HACS](https://hacs.xyz/) custom integration: one action call pushes a calendar, weather, sensor readings or a photo to the tag over Bluetooth — no gateway, no cloud, no wiring. It is not part of Home Assistant Core and claims no Core quality tier. [Why e-paper tags? →](docs/usage.md#why-e-paper-tags)

| 2.1" (250×128) | 2.9" (296×128) | 4.2" (400×300) | 10.2" (960×640) |
|---|---|---|---|
| <img src="https://raw.githubusercontent.com/eigger/hass-ble-esl/main/docs/images/gicisky/21_1.png" alt="2.1 inch Gicisky" width="200" /> | <img src="https://raw.githubusercontent.com/eigger/hass-ble-esl/main/docs/images/gicisky/29_1.png" alt="2.9 inch Gicisky" width="200" /> | <img src="https://raw.githubusercontent.com/eigger/hass-ble-esl/main/docs/images/poshiji/poshiji_psj420_4color.png" alt="4.2 inch Poshiji PSJ-420" width="200" /> | <img src="https://raw.githubusercontent.com/eigger/hass-ble-esl/main/docs/images/gicisky/102_1.jpg" alt="10.2 inch Gicisky" width="200" /> |
| Gicisky | Gicisky | Poshiji PSJ-420 | Gicisky |

Photos of real tags. [More examples with YAML →](examples/README.md)

## Supported tags

BLE protocol families, sold under these brands:

| Protocol | Brand | Sizes | Colors | Status | Buy |
|---|---|---|---|---|---|
| **ETAG** | Hipoink | 2.13" (250 × 122) | BWR | ✅ verified; [protocol notes](docs/etag.md) | [AliExpress](https://de.aliexpress.com/item/1005009110927073.html) |
| **PickSmart** | Gicisky | 2.1" – 10.2" | BW / BWR / BWRY | ✅ verified on hardware | [AliExpress](https://ko.aliexpress.com/item/1005002399342939.html) |
| **XTE** | Poshiji | 1.54" – 7.5" | BWRY | ✅ 2.13", 2.66", 2.9" and 4.2" verified on real tags by owner; other sizes size-only presets | [AliExpress](https://ko.aliexpress.com/item/1005012725381116.html) |
| **WOLINK** | Zhsunyco | 1.54" – 13.3" | BWR / BWRY | ✅ 1.54", 2.66", 3.5", 3.7" and 4.2" BWRY and 2.9" BWR verified on hardware; other sizes untested | [AliExpress](https://ko.aliexpress.com/item/1005009231276243.html) |
| **easyTag** | Zhsunyco | 1.54" – 10.2" | BW / BWR | ⚠️ from specifications, untested | — |

Full model list with resolutions and model codes: **[docs/models.md](docs/models.md)**. Have a tag that speaks another protocol? See [Adding a protocol](custom_components/ble_esl/esl_ble/README.md).

Key features:

- One Write action, `ble_esl.write` (skips unchanged images by default, honours a Write Lock switch, debounces bursts), with layouts written as [imagespec](https://github.com/eigger/imagespec) elements and Jinja templates.
- **ESL Manager**, a sidebar dashboard and visual designer that exports the same payload as YAML.
- Failure sensors and a diagnostics download that say at which stage a write failed and through which radio.

## Requirements

- Home Assistant **2025.12** or newer, with [HACS](https://hacs.xyz/) for the recommended install.
- A Bluetooth adapter or ESPHome Bluetooth proxy that supports **active connections** (see [Bluetooth](#bluetooth)).
- A supported tag (above).

## Installation

1. Install via **HACS** (custom repository `eigger/hass-ble-esl`), or copy `custom_components/ble_esl` into your config.
2. Restart Home Assistant.
3. Tags in range are discovered automatically — confirm them under **Settings → Devices & services**, or add one via **Add integration → BLE ESL**.

Options (Retry Count, Debounce Delay, and Model for WOLINK / easyTag) are under **Configure**; see [docs/usage.md](docs/usage.md#options).

Coming from `hass-gicisky` or `hass-zhsunyco`? Tags must be re-added under the new `ble_esl` domain and `gicisky.write` renamed to `ble_esl.write` — the payload stays the same. **[Migration guide →](docs/migration.md)**

### Bluetooth

Use a **Bluetooth proxy** rather than the host's built-in adapter whenever you can, and set it to **active** (`bluetooth_proxy: active: true`, plus `esp32_ble_tracker: scan_parameters: active: true` as the starting configuration) — most write problems trace back to a passive proxy or a weak adapter. Keep the scan interval at its default. A discovered tag is not yet a working connection: the first GATT connection happens on the first write. BLE ESL does not pair with tags; close the companion app (ETAG) and make sure no other integration writes to the same tag.

ESPHome snippet, hardware suggestions and BLE ESL specifics: [docs/bluetooth.md](docs/bluetooth.md). Shared proxy setup, recommended hardware and the connection troubleshooting order: [Bluetooth proxy guide](https://github.com/eigger/hass-repo-standards/blob/main/docs/bluetooth.md). Tag-specific conditions and the failure sensors are in [docs/troubleshooting.md](docs/troubleshooting.md).

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
      "y": 10
      size: 40
```

The tag refreshes in a few seconds. Add `dry_run: true` to render without sending — the result shows up in the tag's **Preview Content** image entity. More: [usage overview](docs/usage.md), ready-made layouts in [`examples/`](examples/README.md), the visual [Designer guide](docs/designer.md).

## Limits and warnings

> [!WARNING]
> Untested WOLINK and easyTag presets are built from technical specifications and have not been tested on physical tags. If you try one, please report the result in [Discussions](https://github.com/eigger/hass-ble-esl/discussions).

- XTE sizes other than 2.13", 2.66", 2.9" and 4.2" are size-only presets picked by hand; a preset that does not match the hardware can produce a successful write but a wrong-looking panel.
- **Preview Content** is what was rendered, not a readback of the panel.
- The designer does not transmit on sensor changes; schedule updates with automations. E-paper is not an LCD — avoid overly frequent redraws; `write` skips unchanged images by default; Debounce Delay can coalesce bursts. Disable the action’s **Skip unchanged image** option to resend an identical image.

## Documentation

| Topic | English | 한국어 |
|---|---|---|
| Usage overview: first layout, visual editor, actions, options, payload & rendering | [docs/usage.md](docs/usage.md) | [docs/ko/usage.md](docs/ko/usage.md) |
| Bluetooth setup | [docs/bluetooth.md](docs/bluetooth.md) | [docs/ko/bluetooth.md](docs/ko/bluetooth.md) |
| Troubleshooting and reporting | [docs/troubleshooting.md](docs/troubleshooting.md) | [docs/ko/troubleshooting.md](docs/ko/troubleshooting.md) |
| Actions, response data, entities, fonts | [docs/actions.md](docs/actions.md) | — |
| Supported models and where to buy | [docs/models.md](docs/models.md) | — |
| ESL Manager / Designer | [docs/designer.md](docs/designer.md) | [docs/ko/designer.md](docs/ko/designer.md) |
| Design templates | [docs/design-templates.md](docs/design-templates.md) | [docs/ko/design-templates.md](docs/ko/design-templates.md) |
| Migration from hass-gicisky / hass-zhsunyco | [docs/migration.md](docs/migration.md) | [docs/ko/migration.md](docs/ko/migration.md) |
| Protocol notes (ETAG, XTE) | [docs/etag.md](docs/etag.md), [docs/xte.md](docs/xte.md) | — |
| Examples | [examples/README.md](examples/README.md) | — |
| Development: tests, verified environments, lint, adding a protocol | [docs/development.md](docs/development.md) | — |

Related projects: [imagespec](https://github.com/eigger/imagespec) (the renderer behind `payload:`), [Stash](https://github.com/eigger/stash) (home inventory that prints labels to ESL tags), [hass-gicisky](https://github.com/eigger/hass-gicisky) (archived predecessor) — see [docs/usage.md](docs/usage.md#related-projects).

## Support

- A label not updating? **[docs/troubleshooting.md](docs/troubleshooting.md)** — the failure sensors say where a write died and why.
- Found a bug? [Open an issue](https://github.com/eigger/hass-ble-esl/issues) and attach the tag's diagnostics: **the device page → ⋮ → Download diagnostics**. It contains the protocol, preset, firmware, options, last advertisement and failure counters (tag MAC redacted; check the rest before posting — see [what to remove](docs/troubleshooting.md#remove-sensitive-information-before-posting)).
- Questions or ideas? [Discussions](https://github.com/eigger/hass-ble-esl/discussions)
- Tested a WOLINK or easyTag tag, or have a Poshiji size that asked for a manual model pick? Please share — that is how presets get verified.

## License

[MIT](LICENSE)
