# BLE ESL brand assets

An original geometric electronic shelf label (e-paper display tag) and Bluetooth
badge icon drawn by `scripts/generate_brand.py` on a dark navy rounded square,
with a matching sky blue `BLE ESL` wordmark for the landscape logo. No
third-party artwork is used.

| File | Size | Purpose |
| --- | --- | --- |
| `icon.png` | 256 × 256 | Home Assistant and HACS icon |
| `icon@2x.png` | 512 × 512 | High-resolution icon |
| `logo.png` | 915 × 256 | Landscape integration logo; README artwork |
| `logo@2x.png` | 1830 × 512 | High-resolution landscape logo |

All images are RGBA PNGs with transparent outer corners and backgrounds. These
sizes follow the [HA brand image guidelines](https://contributors.home-assistant.io/core/integrations/brands/).
Home Assistant 2026.3 and later serves these assets from the integration's local
`brand/` directory. The sky blue wordmark works against light and dark
backgrounds, so separate dark variants are not required.

## Source and permission

The icon is drawn from geometric primitives in this repository's
`scripts/generate_brand.py` and is covered by the repository's MIT license
(Copyright (c) 2026 eigger). The wordmark is rendered with Pillow's bundled
Aileron Regular via
[`ImageFont.load_default`](https://pillow.readthedocs.io/en/stable/reference/ImageFont.html#PIL.ImageFont.load_default).
[Aileron](https://dotcolon.net/font/aileron/) permits commercial use and is
released with no rights reserved. No font file is redistributed or loaded from
the system.

## Reproduce

Use Python 3.10 or newer and Pillow 12.3.0 (also supplied by HA 2026.10.2):

```sh
python -m pip install Pillow==12.3.0
python scripts/generate_brand.py
```

The script needs no network access and produces the same PNG bytes on every
run with that Pillow version.

SHA256 (Pillow 12.3.0):

- `icon@2x.png`: `51f5f80ae261d6d4353f892381074682c1a4b07b3d97a42f296e714fc4a59793`
- `icon.png`: `7d8c80b5050c974433ba4c72b93fdf770f9a9506acf0a9d2eb4cffc46dee3860`
- `logo@2x.png`: `b66d8af69c35b29a74bd24f83dfb4dc2f20d7c01a877ec4ec814a4a5632051a6`
- `logo.png`: `c9006d714f2f2c6f47c4b97989de26443c4e705d6c6d7745be2472c2b5a16cb5`

The local `brand/icon.png` is used by the
[HACS brands check](https://hacs.xyz/docs/publish/include/#check-brands).
These files do not imply inclusion in the HA brands repository. README pages
use `custom_components/ble_esl/brand/logo.png`.
