# Supported models

> [!WARNING]
> **Hardware Testing Notice**: **PickSmart** (Gicisky) models are fully verified, inherited from hass-gicisky. **WOLINK** and **easyTag** models have **not** been physically tested yet — their implementations and presets are built from technical specifications.
> If you test a WOLINK or easyTag device, please share your results in [Discussions](https://github.com/eigger/hass-ble-esl/discussions) or [open an issue](https://github.com/eigger/hass-ble-esl/issues)!

Sorted by panel size. Colors: **BW** black/white · **BWR** + red · **BWRY** + red + yellow.

| Size | Resolution | Colors | Brand | Protocol | Model / Type | Status |
|------|------------|--------|-------|----------|--------------|--------|
| 1.54" | 200 × 200 | BWRY | Zhsunyco | WOLINK | — | ⚠️ untested |
| 1.54" | 200 × 200 | BWR | Zhsunyco | easyTag | ET0154-33B | ⚠️ untested |
| 1.54" | 200 × 200 | BWRY | Poshiji | XTE | — (size only) | ⚠️ untested |
| 2.1" | 250 × 132 | BW | Gicisky | PickSmart | TFT | ✅ verified |
| 2.1" | 212 × 104 | BWR | Gicisky | PickSmart | EPD | ✅ verified |
| 2.1" | 250 × 128 | BWR | Gicisky | PickSmart | EPD | ✅ verified |
| 2.13" | 250 × 122 | BWRY | Zhsunyco | WOLINK | — | ⚠️ untested |
| 2.13" | 250 × 122 | BWR | Zhsunyco | easyTag | ETR0213-36B | ⚠️ untested |
| 2.13" | 250 × 122 | BW | Zhsunyco | easyTag | ETR0213-39B | ⚠️ untested |
| 2.13" | 250 × 122 | BWRY | Poshiji | XTE | PSJ-213 | ⚠️ community report |
| 2.66" | 296 × 152 | BWRY | Zhsunyco | WOLINK | — | ⚠️ untested |
| 2.66" | 296 × 152 | BWR | Zhsunyco | easyTag | ET0266-3A | ⚠️ untested |
| 2.66" | 296 × 152 | BWRY | Poshiji | XTE | — (size only) | ⚠️ untested |
| 2.9" | 296 × 128 | BWRY | Zhsunyco | WOLINK | — | ⚠️ untested |
| 2.9" | 296 × 128 | BWR | Zhsunyco | WOLINK | `290-bwr` | ⚠️ community report |
| 2.9" | 296 × 128 | BWR | Zhsunyco | easyTag | ET0290-3DB / ETR290-FF | ⚠️ untested |
| 2.9" | 296 × 128 | BWRY | Poshiji | XTE | — (size only) | ⚠️ untested |
| 2.9" | 296 × 128 | BW | Gicisky | PickSmart | EPD | ✅ verified |
| 2.9" | 296 × 128 | BWR | Gicisky | PickSmart | EPD | ✅ verified |
| 2.9" | 296 × 128 | BWRY | Gicisky | PickSmart | EPD | ✅ verified |
| 3.5" | 384 × 184 | BWRY | Zhsunyco | WOLINK | — | ⚠️ untested |
| 3.5" | 384 × 184 | BWR | Zhsunyco | easyTag | ET0350-55B | ⚠️ untested |
| 3.5" | 384 × 184 | BWRY | Poshiji | XTE | — (size only) | ⚠️ untested |
| 3.7" | 416 × 240 | BWRY | Zhsunyco | WOLINK | — | ⚠️ untested |
| 3.7" | 240 × 416 | BWR | Gicisky | PickSmart | EPD | ✅ verified |
| 3.7" | 416 × 240 | BWRY | Poshiji | XTE | — (size only) | ⚠️ untested |
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
| 7.5" | 800 × 480 | BWRY | Poshiji | XTE | — (size only) | ⚠️ untested |
| 10.2" | 960 × 640 | BWRY | Zhsunyco | WOLINK | — | ⚠️ untested |
| 10.2" | 960 × 640 | BWR | Zhsunyco | easyTag | ET1020-64 | ⚠️ untested |
| 10.2" | 960 × 640 | BWR | Gicisky | PickSmart | EPD | ✅ verified |
| 13.3" | 960 × 680 | BWRY | Zhsunyco | WOLINK | — | ⚠️ untested |

Protocol notes:
- **XTE** — tags sold under the Poshiji brand. PSJ-420 (400×300 BWRY) verified on hardware by the device owner; PSJ-213 (250×122 BWRY, portrait buffer) from a community report. Other sizes are offered as size-only presets picked by hand until their device numbers are reported. See [setup and protocol notes](xte.md).
- **WOLINK** — Zhsunyco tags. Most presets are 4-color, 2 bits per pixel. The 2.9" BWR preset (`290-bwr`) sends two 1bpp planes (black/white, then red), 128 pixels per column. Colors and that scan were confirmed on a physical tag. The 5.83" panel is listed as 5.8".
- **easyTag** — eLabel firmware sold under the Zhsunyco brand. Model code is printed on the tag.
- **PickSmart** — Gicisky tags; 2.1" TFT is an LCD (not e-paper). The 3.7" panel is portrait (240 × 416).

Have a tag that speaks another protocol? Each protocol is one self-contained package with an enforced contract — see [Adding a protocol backend](../custom_components/ble_esl/esl_ble/README.md).

## Where to buy

Availability varies by country. AliExpress listings by protocol family:

| Protocol | Brand | Listing |
|----------|-------|---------|
| WOLINK | Zhsunyco | [Zhsunyco BLE Electronic Shelf Label (WOLINK)](https://ko.aliexpress.com/item/1005009231276243.html) |
| XTE | Poshiji | [Poshiji BWRY ESL, 2.13"–4.2"](https://ko.aliexpress.com/item/1005012725381116.html) |
| PickSmart | Gicisky | [Gicisky store (item 1)](https://ko.aliexpress.com/item/1005002399342939.html) · [Gicisky store (item 2)](https://ko.aliexpress.com/item/1005002398744297.html) |
