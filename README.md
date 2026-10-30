<!-- hass-standards:header:start -->
# hass-ble-esl

Generic BLE Electronic Shelf Label (ESL) Home Assistant Integration

**English** | [한국어](README.ko.md)

<!-- hass-standards:badges:start -->
[![Release](https://img.shields.io/github/v/release/eigger/hass-ble-esl?style=flat)](https://github.com/eigger/hass-ble-esl/releases)
[![HACS Default](https://img.shields.io/badge/HACS-Default-41BDF5?style=flat)](#installation)
[![Home Assistant minimum](https://img.shields.io/badge/HA-%E2%89%A5%202025.12.0-41BDF5?style=flat)](hacs.json)
[![Tests](https://img.shields.io/github/actions/workflow/status/eigger/hass-ble-esl/tests.yml?branch=main&style=flat&label=Tests)](https://github.com/eigger/hass-ble-esl/actions/workflows/tests.yml)
[![Validate](https://img.shields.io/github/actions/workflow/status/eigger/hass-ble-esl/validate.yml?branch=main&style=flat&label=Validate)](https://github.com/eigger/hass-ble-esl/actions/workflows/validate.yml)
[![License](https://img.shields.io/github/license/eigger/hass-ble-esl?style=flat)](LICENSE)
[![Downloads](https://img.shields.io/github/downloads/eigger/hass-ble-esl/latest/total?style=flat&color=41BDF5&label=Downloads)](https://github.com/eigger/hass-ble-esl/releases)
<!-- hass-standards:badges:end -->
<!-- hass-standards:header:end -->

The Downloads badge counts GitHub release asset downloads of the current release, not active installations.

**Battery-powered e-paper displays that show your Home Assistant data for months to years on one battery.**

BLE ESL is a [HACS](https://hacs.xyz/) custom integration: one action call pushes a calendar, weather, sensor readings or a photo to the tag over Bluetooth — no gateway, no cloud, no wiring.

It is not part of Home Assistant Core and claims no Core quality tier. [Why e-paper tags? →](docs/usage.md#why-e-paper-tags)

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

Full model list with resolutions and model codes: **[docs/models.md](docs/models.md)**.

Have a tag that speaks another protocol? See [Adding a protocol](custom_components/ble_esl/esl_ble/README.md).

Key features:

- Two actions, `ble_esl.write` and `ble_esl.write_guarded` (skips unchanged images, honours a Write Lock switch, debounces bursts), with layouts written as [imagespec](https://github.com/eigger/imagespec) elements and Jinja templates.
- **ESL Manager**, a sidebar dashboard and visual designer that exports the same payload as YAML.
- Failure sensors and a diagnostics download that say at which stage a write failed and through which radio.

## Requirements

- Home Assistant **2025.12** or newer, with [HACS](https://hacs.xyz/) for the recommended install.
- A Bluetooth adapter or ESPHome Bluetooth proxy that supports **active connections** (see [Bluetooth](#bluetooth)).
- A supported tag (above).

## Installation

<!-- hass-standards:installation:start -->
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=eigger&repository=hass-ble-esl)
<!-- hass-standards:installation:end -->

1. Install **BLE ESL** from the default **HACS** integration catalog, or copy `custom_components/ble_esl` into your config.
2. Restart Home Assistant.
3. Tags in range are discovered automatically — confirm them under **Settings → Devices & services**, or add one via **Add integration → BLE ESL**.

Options (Retry Count, Prevent Duplicate Send, Debounce Delay, and Model for WOLINK / easyTag) are under **Configure**; see [docs/usage.md](docs/usage.md#options).

Coming from `hass-gicisky` or `hass-zhsunyco`? Tags must be re-added under the new `ble_esl` domain and `gicisky.write` renamed to `ble_esl.write` — the payload stays the same. **[Migration guide →](docs/migration.md)**

### Bluetooth

For remote Bluetooth, use a **Bluetooth proxy** with **active connections** (`bluetooth_proxy: active: true`; `esp32_ble_tracker: scan_parameters: active: true` is the documented starting scan configuration). A local adapter that works reliably can also be used.

Passive scanning can still support GATT connections; connection capability is controlled separately by `bluetooth_proxy.active`. Keep the scan interval at its default.

A discovered tag is not yet a working connection: the first GATT connection happens on the first write. BLE ESL does not pair with tags; close the companion app (ETAG) and make sure no other integration writes to the same tag.

- [BLE ESL Bluetooth setup](docs/bluetooth.md): ESPHome snippet and integration-specific guidance.
- [Bluetooth proxy guide](https://github.com/eigger/blesession/blob/main/docs/bluetooth.md): shared setup, hardware recommendations and connection troubleshooting.
- [Troubleshooting](docs/troubleshooting.md): tag-specific conditions and failure sensors.

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

The tag refreshes in a few seconds.

Add `dry_run: true` to render without sending — the result shows up in the tag's **Preview Content** image entity.

See the [payload guide](docs/payload.md) for rendering options and complete action examples, and the [documentation index](#documentation) for layouts, usage and the visual designer.

## Limits and warnings

> [!WARNING]
> Untested WOLINK and easyTag presets are built from technical specifications and have not been tested on physical tags. If you try one, please report the result in [Discussions](https://github.com/eigger/hass-ble-esl/discussions).

- XTE sizes other than 2.13", 2.66", 2.9" and 4.2" are size-only presets picked by hand; a preset that does not match the hardware can produce a successful write but a wrong-looking panel.
- **Preview Content** is what was rendered, not a readback of the panel.
- The designer does not transmit on sensor changes; schedule updates with automations. E-paper is not an LCD — avoid overly frequent redraws; `write_guarded` and the Prevent Duplicate Send / Debounce Delay options help.

## Documentation

| Topic | English | 한국어 |
|---|---|---|
| Usage overview: first layout, visual editor, actions, options, payload & rendering | [docs/usage.md](docs/usage.md) | [docs/ko/usage.md](docs/ko/usage.md) |
| Bluetooth setup | [docs/bluetooth.md](docs/bluetooth.md) | [docs/ko/bluetooth.md](docs/ko/bluetooth.md) |
| Troubleshooting and reporting | [docs/troubleshooting.md](docs/troubleshooting.md) | [docs/troubleshooting.ko.md](docs/troubleshooting.ko.md) |
| Actions, response data, entities, fonts | [docs/actions.md](docs/actions.md) | — |
| Supported models and where to buy | [docs/models.md](docs/models.md) | — |
| ESL Manager / Designer | [docs/designer.md](docs/designer.md) | [docs/ko/designer.md](docs/ko/designer.md) |
| Design templates | [docs/design-templates.md](docs/design-templates.md) | [docs/ko/design-templates.md](docs/ko/design-templates.md) |
| Migration from hass-gicisky / hass-zhsunyco | [docs/migration.md](docs/migration.md) | [docs/ko/migration.md](docs/ko/migration.md) |
| Protocol notes (ETAG, XTE) | [docs/etag.md](docs/etag.md), [docs/xte.md](docs/xte.md) | — |
| Examples | [examples/README.md](examples/README.md) | — |
| Development: tests, verified environments, lint, adding a protocol | [docs/development.md](docs/development.md) | — |

## Troubleshooting and diagnostics

- A label not updating? **[docs/troubleshooting.md](docs/troubleshooting.md)** — the failure sensors say where a write died and why.
- When reporting a bug, attach the tag's diagnostics: **the device page → ⋮ → Download diagnostics**. It contains the protocol, preset, firmware, options, last advertisement and failure counters.
- The tag MAC is redacted, but check the remaining data before posting — see [what to remove](docs/troubleshooting.md#remove-sensitive-information-before-posting).
- Tested a WOLINK or easyTag tag, or have a Poshiji size that asked for a manual model pick? Share the result through the support links below to help verify presets.

<!-- hass-standards:support:start -->
## Support

- [Issues](https://github.com/eigger/hass-ble-esl/issues): Report bugs or request features.
- [Discussions](https://github.com/eigger/hass-ble-esl/discussions): Ask questions and share your experience.
<!-- hass-standards:support:end -->

<!-- hass-standards:related-projects:start -->
## Related Projects

- [imagespec](https://github.com/eigger/imagespec): The renderer behind `payload:`.
- [Stash](https://github.com/eigger/stash): Home inventory that prints labels to ESL tags.
- [hass-gicisky](https://github.com/eigger/hass-gicisky): Archived predecessor of BLE ESL.
<!-- hass-standards:related-projects:end -->

<!-- hass-standards:license:start -->
## License

Released under the [MIT License](LICENSE).
<!-- hass-standards:license:end -->
