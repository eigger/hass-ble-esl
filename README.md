<!-- hass-standards:header:start -->
# BLE ESL

Bluetooth Low Energy electronic shelf labels for Home Assistant.

**English** | [한국어](README.ko.md)

<!-- hass-standards:badges:start -->
[![Release](https://img.shields.io/github/v/release/eigger/hass-ble-esl?style=flat)](https://github.com/eigger/hass-ble-esl/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5?style=flat)](#installation)
[![Home Assistant minimum](https://img.shields.io/badge/HA-%E2%89%A5%202025.12.0-41BDF5?style=flat)](hacs.json)
[![Tests](https://img.shields.io/github/actions/workflow/status/eigger/hass-ble-esl/tests.yml?branch=main&style=flat&label=Tests)](https://github.com/eigger/hass-ble-esl/actions/workflows/tests.yml)
[![Validate](https://img.shields.io/github/actions/workflow/status/eigger/hass-ble-esl/validate.yml?branch=main&style=flat&label=Validate)](https://github.com/eigger/hass-ble-esl/actions/workflows/validate.yml)
[![License](https://img.shields.io/github/license/eigger/hass-ble-esl?style=flat)](LICENSE)
[![Analytics reporting installs](https://img.shields.io/badge/dynamic/json?style=flat&color=41BDF5&label=Usage&query=%24.ble_esl.total&url=https%3A%2F%2Fanalytics.home-assistant.io%2Fcustom_integrations.json)](https://analytics.home-assistant.io/)
<!-- hass-standards:badges:end -->
<!-- hass-standards:header:end -->

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
| **PickSmart** | Gicisky | 2.1" – 10.2" | BW / BWR / BWRY | ✅ verified on hardware | [AliExpress](https://ko.aliexpress.com/item/100502399342939.html) |
| **XTE** | Poshiji | 1.54" – 7.5" | BWRY | ✅ 2.13", 2.66", 2.9" and 4.2" verified on real tags by owner; other sizes size-only presets | [AliExpress](https://ko.aliexpress.com/item/1005012725381116.html) |
| **WOLINK** | Zhsunyco | 1.54" – 13.3" | BWR / BWRY | ✅ 1.54", 2.66", 3.5", 3.7" and 4.2" BWRY and 2.9" BWR verified on hardware; other sizes untested | [AliExpress](https://ko.aliexpress.com/item/1005009231276243.html) |
| **easyTag** | Zhsunyco | 1.54" – 10.2" | BW / BWR | ⚠️ from specifications, untested | — |

Full model list with resolutions and model codes: **[docs/models.md](docs/models.md)**. Have a tag that speaks another protocol? See [Adding a protocol](custom_components/ble_esl/esl_ble/README.md).

## Key features

- **imagespec layouts**: Rich declarative payloads (text, lines, rectangles, icons, QR codes, images, and Jinja templates) powered by [imagespec](https://github.com/eigger/imagespec).
- **ESL Manager**: Integrated sidebar dashboard and visual designer to build layouts interactively and export ready-to-use YAML.
- **Guarded writes**: `ble_esl.write_guarded` skips unchanged content, respects a manual write-lock switch, and debounces rapid consecutive updates.
- **Diagnostic sensors**: Detailed failure stage sensors and diagnostics reporting RF signal strength and connection paths.

## Requirements

- Home Assistant **2025.12** or newer, with [HACS](https://hacs.xyz/) for recommended installation.
- A Bluetooth adapter or ESPHome Bluetooth proxy that supports **active connections** (see [Bluetooth](#bluetooth)).
- A supported tag (see [Supported tags](#supported-tags)).

## Installation

1. Install via **HACS** (custom repository `eigger/hass-ble-esl`), or copy `custom_components/ble_esl` into your config directory.
2. Restart Home Assistant.
3. Tags in range are discovered automatically — confirm them under **Settings → Devices & services**, or add manually via **Add integration → BLE ESL**.

Options (Retry Count, Prevent Duplicate Send, Debounce Delay, and Model for WOLINK / easyTag) can be tuned under **Configure**; see [docs/usage.md](docs/usage.md#options).

Upgrading from `hass-gicisky` or `hass-zhsunyco`? See the **[Migration guide →](docs/migration.md)**.

### Bluetooth

Transmitting images to ESL tags requires **active GATT connections** (passive advertisement scanning is not sufficient).

- An **active ESPHome Bluetooth proxy** (`bluetooth_proxy: active: true`) is strongly recommended over onboard host Bluetooth for reliable range and stability.
- **Shared proxy setup & hardware**: Follow the canonical [Bluetooth proxy guide](https://github.com/eigger/blesession/blob/main/docs/bluetooth.md) for recommended hardware, antenna advice, and ESPHome firmware configuration.
- **Integration-specific details**: Single-write concurrency locking, radio arbitration, and local settings are detailed in [docs/bluetooth.md](docs/bluetooth.md).
- **Troubleshooting & failure stages**: Check [docs/troubleshooting.md](docs/troubleshooting.md) for connection error codes and diagnostic sensors.

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

- **Payload syntax**: Layouts use [imagespec](https://github.com/eigger/imagespec) declarative syntax. See the shared [imagespec payload guide](https://github.com/eigger/imagespec/blob/main/docs/payload.md) for full syntax, element types (`text`, `line`, `rectangle`, `icon`, `qrcode`, `image`), styling, and color/dithering options.
- **Preview safely**: Add `dry_run: true` to render without transmitting — verify the output on the tag's **Preview Content** entity.
- **Visual designer**: Open **ESL Manager** in the Home Assistant sidebar to interactively design screens and export YAML.
- **More examples**: See [usage overview](docs/usage.md) and ready-made layouts in [`examples/`](examples/README.md).

## Limits and warnings

> [!WARNING]
> Untested WOLINK and easyTag presets are built from technical specifications and have not been tested on physical tags. If you try one, please report the result in [Discussions](https://github.com/eigger/hass-ble-esl/discussions).

- XTE sizes other than 2.13", 2.66", 2.9" and 4.2" are size-only presets picked by hand; a preset that does not match the hardware can produce a successful write but a wrong-looking panel.
- **Preview Content** is what was rendered, not a readback of the panel.
- The designer does not transmit on sensor changes; schedule updates with automations. E-paper is not an LCD — avoid overly frequent redraws; `write_guarded` and the Prevent Duplicate Send / Debounce Delay options help.

## Documentation

| Topic | English | 한국어 |
|---|---|---|
| Usage overview: first layout, visual editor, actions, options | [docs/usage.md](docs/usage.md) | [docs/ko/usage.md](docs/ko/usage.md) |
| Payload & layout syntax | [imagespec payload guide](https://github.com/eigger/imagespec/blob/main/docs/payload.md) | [imagespec payload 안내](https://github.com/eigger/imagespec/blob/main/docs/payload.ko.md) |
| Bluetooth setup & proxy | [docs/bluetooth.md](docs/bluetooth.md) ([Proxy guide](https://github.com/eigger/blesession/blob/main/docs/bluetooth.md)) | [docs/ko/bluetooth.md](docs/ko/bluetooth.md) ([프록시 안내](https://github.com/eigger/blesession/blob/main/docs/bluetooth.ko.md)) |
| Troubleshooting & failure stages | [docs/troubleshooting.md](docs/troubleshooting.md) ([blesession guide](https://github.com/eigger/blesession/blob/main/docs/troubleshooting.md)) | [docs/troubleshooting.ko.md](docs/troubleshooting.ko.md) ([blesession 안내](https://github.com/eigger/blesession/blob/main/docs/troubleshooting.ko.md)) |
| Actions, response data, entities, fonts | [docs/actions.md](docs/actions.md) | — |
| Supported models and where to buy | [docs/models.md](docs/models.md) | — |
| ESL Manager / Designer | [docs/designer.md](docs/designer.md) | [docs/ko/designer.md](docs/ko/designer.md) |
| Design templates | [docs/design-templates.md](docs/design-templates.md) | [docs/ko/design-templates.md](docs/ko/design-templates.md) |
| Migration from hass-gicisky / hass-zhsunyco | [docs/migration.md](docs/migration.md) | [docs/ko/migration.md](docs/ko/migration.md) |
| Protocol notes (ETAG, XTE) | [docs/etag.md](docs/etag.md), [docs/xte.md](docs/xte.md) | — |
| Examples | [examples/README.md](examples/README.md) | — |
| Development: tests, environments, lint | [docs/development.md](docs/development.md) | — |

<!-- hass-standards:support:start -->
## Support

- [Issues](https://github.com/eigger/hass-ble-esl/issues): Report bugs or request features.
<!-- hass-standards:support:end -->

<!-- hass-standards:related-projects:start -->
## Related Projects

- [imagespec](https://github.com/eigger/imagespec): The declarative layout and renderer behind ESL tag payloads.
- [Stash](https://github.com/eigger/stash): Home inventory system with direct printing to ESL tags.
- [hass-gicisky](https://github.com/eigger/hass-gicisky): Archived predecessor integration.
<!-- hass-standards:related-projects:end -->

<!-- hass-standards:license:start -->
## License

Released under the [MIT License](LICENSE).
<!-- hass-standards:license:end -->
