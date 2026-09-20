# XTE (Poshiji PSJ-420, PSJ-213)

BLE ESL supports the XTE protocol family sold under the Poshiji brand. The
reference device is the PSJ-420, a 400x300 black/white/red/yellow label;
the catalog under [Advertisement](#advertisement) lists the other models.
Manufacturer, model and colors of the PSJ-420 were confirmed by the device
owner, who verified working screen updates with this backend on the real
tag. Its preset uses `reported` confidence. The protocol codec and BLE
transaction are also covered by automated tests.

## Product photo

![Poshiji PSJ-420 showing a four-color weather dashboard](images/poshiji/poshiji_psj420_4color.png)

Original photograph supplied by the device owner. It shows black text and icons,
white background, red temperature and a yellow footer. The displayed date,
weather and temperature are the photographed screen contents, not live data.

## Purchase

[AliExpress — Poshiji PSJ-420 purchase listing](https://ko.aliexpress.com/item/1005012582138232.html)

This link was supplied by the device owner. The listing contents could not be
retrieved during documentation preparation. Select/check **PSJ-420, 4.2-inch,
400×300, BWRY, BLE** with the seller; do not assume every listing option uses
this protocol. Current price, availability, accessories and seller warranty
are not recorded here.

## Product specifications and evidence

| Item | Value | Basis |
|------|-------|-------|
| Brand | Poshiji | Owner identification |
| Model | PSJ-420 | Owner identification |
| Nominal panel class | 4.2-inch | Model/profile identification; not a physical measurement |
| Resolution | 400 × 300 pixels | Owner specification and decoded image header |
| Aspect ratio | 4:3 landscape | Resolution and photograph |
| Display | Four-color electronic shelf label / e-paper | Owner description and photograph |
| Colors | Black, white, red, yellow (BWRY) | Owner confirmation and visible photo contents |
| Connection | Bluetooth Low Energy, connected GATT | Radio capture |
| Integration backend | `xte` / XTE (Poshiji) | BLE ESL implementation |
| Preset key | `psj-420` | BLE ESL implementation |
| Image packing | 2 bits/pixel, 30,000 bytes before RLE | Capture reconstruction |
| Compression | Run-length encoding (count, byte) | Byte-for-byte capture verification |
| Discovery | Manufacturer ID `0x5258`, XTE record with device number 153 | Advertisement layout (see [Advertisement](#advertisement)) |
| Battery telemetry | Percentage from the advertisement | Advertisement layout; PSJ-420 read 100 % |
| Temperature telemetry | Not exposed | Last advertised byte is probably °C but unconfirmed |
| Hardware confidence | Owner-verified working updates | Device owner tested this backend; codec/transport covered by tests |

**Not established:** enclosure dimensions/weight, battery type/capacity/life,
operating temperature, IP rating, exact Bluetooth specification version,
maximum range and rated panel refresh time. LE 1M in the capture is a PHY,
not evidence of a particular Bluetooth version. The roughly 0.69-second image
transfer in one capture is not the panel's physical refresh time or a guarantee.

## Examples

All layouts are native 400×300; Home Assistant selects the size from the preset.
Use `black`, `white`, `red` and `yellow`; other colors are quantized to BWRY.

- [Four-color check](../examples/poshiji/psj420-color-test.yaml): a complete `ble_esl.write` action drawing four labeled swatches; replace `device_id` and add `dry_run: true` under `data` to preview only.
- [Naver weather automation](../examples/poshiji/psj420-weather-demo.yaml): weekday 08:00 / 11:00 / 14:00 / 17:00 updates, daily forecast low/high, fine-dust warnings and a two-line weather comment. Uses the owner-supplied actual device photo.
- [Example setup instructions](../examples/poshiji/README.md): placeholders, preview/send behavior and entity requirements.

## Installation and use

Install BLE ESL (HACS or copy `custom_components/ble_esl` to
`/config/custom_components/`), then restart Home Assistant. Add the tag through
Settings > Devices & Services > BLE ESL. Manufacturer is Poshiji; the PSJ-420
model is detected automatically. Protocol and model are saved and restored by
the standard BLE ESL config flow.

Write with `ble_esl.write` / `ble_esl.write_guarded` and select the BLE ESL
device. Use `dry_run: true` for a preview before writing. Make sure no other
integration writes to the same tag.

After enabling notifications the writer waits 0.5 s before the prepare
command, like the other backends. Writes use the smaller of 244 bytes and
the backend's reported write limit.
20-byte limits are accepted without changing logical XTE block contents.
Retry Count and Write Delay options apply to the Poshiji backend; the delay is
applied once per XTE command or block, not per ATT chunk.

## Advertisement

The tag advertises under manufacturer ID `0x5258` (ASCII `XR` on the wire;
not a registered company). The layout below is common to the XTE firmware
family. Home Assistant strips the two company-ID bytes; offsets are into
what remains.

| Offset | PSJ-420 | Field |
|---|---|---|
| 0 | `fd` | Record type; one of `fd`, `fe`, `fc`, `04` |
| 1 | `02` | Hardware revision |
| 2–3 | `40 02` | Firmware 4.0.2 (BCD major.minor, then patch) |
| 4–5 | `00 99` | **Device number 153** — the tag type; identifies the model |
| 6 | `64` | Battery, percent |
| 7 | `06` | Chip type (high nibble), transmit power (low nibble) |
| 8–12 | `01 02 ff ff 1e` | Not used. The last byte (`1e` → `1b` seen after an update) sits where a temperature would; not exposed |

The tag alternates this record with a two-byte `ff 01` payload under the same
company ID; the record-type check rejects it.

A model is identified by its device number, never by the full byte string:
battery and firmware bytes change over the tag's life. Every XTE record is
claimed; when the device number is one of the captured models the model is
set automatically, otherwise the config flow asks for it and offers the
size-only presets below (marked *unverified*). The integration also logs one
INFO line per tag with the device number, versions and raw manufacturer
data — please open an issue with that line, the tag's printed model and its
resolution, and the size preset becomes a captured one. Some tag types (97,
102, 106, 109, 119, 122) use a different pixel layout that is not
implemented; a wrong pick shows as garbage or a sheared image, never as
damage.

### Other models in the family

The same firmware ships across sizes. Model names printed on the tags are
`PSJ-<size>`; the same panels are also listed as `ESL-<size><colors>` (1.54"
ESL-15BWRY 200×200, 2.13" ESL-21BWRY 250×122, 2.66" ESL-26BWRY 296×152, 2.9"
ESL-29BWRY 296×128, 3.5" ESL-35BWRY 384×184, 3.7" ESL-37BWRY 416×240, and a
freezer variant ESL-21MBW; the 4.2" has no such listing).

Catalog (`esl_ble/xte/devices.py`):

| Preset | Device number | Viewed | Buffer | Confidence |
|---|---|---|---|---|
| PSJ-420 | 153 | 400×300 landscape | 400×300 | reported (owner-verified with this integration) |
| PSJ-213 | 140 | 250×122 landscape | 122×250 portrait (`rotation: 90`, rows padded to 124 px) | community (pushed successfully with the same transaction elsewhere; not re-tested here) |
| psj-154 | — | 200×200 | 200×200 portrait (`rotation: 90`) | estimated (size only, manual pick) |
| psj-266 | — | 296×152 | 152×296 portrait (`rotation: 90`) | estimated (size only, manual pick) |
| psj-290 | — | 296×128 | 128×296 portrait (`rotation: 90`) | estimated (size only, manual pick) |
| psj-350 | — | 384×184 | 384×184 landscape | estimated (size only, manual pick) |
| psj-370 | — | 416×240 | 416×240 landscape | estimated (size only, manual pick) |

Panels up to 2.9" are assumed to scan along their short edge like the
PSJ-213 (portrait buffer); the larger sizes are assumed landscape like the
PSJ-420. If a manually picked size displays as diagonal stripes (shear), the
orientation assumption is wrong for that panel; report it and the preset's
`rotation` is flipped.
Promoting a size-only entry is filling in its `device_number`; the key stays,
so existing config entries keep working.

## Protocol

- Service: `00002760-08c2-11e1-9073-0e8ac72e1001`
- Write without response: `00002760-08c2-11e1-9073-0e8ac72e0001`
- Notifications: `00002760-08c2-11e1-9073-0e8ac72e0002`
- Pixels: row-major, four pixels per byte, high bits first; 00 black, 01 white,
  10 yellow, 11 red. This mapping is consistent with the owner-supplied four-color photograph.
- RLE: `(count, byte)` pairs, runs up to 255, with a reset halfway through the
  30000-byte packed frame (observed at offset 15000).
- XTEK object: magic [0:4], sum of bytes [12:] as big-endian uint32 [4:8],
  total length [8:12], image count 1 [12], image record offset 17 [13:17],
  then the record: x 0 [17:21], y 0 [21:25], width [25:29], height [29:33],
  compression 01 = RLE [33], RLE length [34:38], RLE body [38:]. This backend
  always sends one full-screen record.
- Logical block: `XTE 02`, big-endian uint16 total length, one-byte sum of all
  following bytes, total block count, zero-based block index, up to 1211 bytes
  of object data. Each logical block is split into <=244-byte BLE writes.
- Preparation: `XTE 01`, one-byte total length, one-byte payload sum,
  `01` followed by big-endian uint32 object length.
- Finish: `58 54 45 01 08 04 04 00`.
- Replies: XTE 04 frames; the declared length excludes trailing padding.
  Checksum and payload are checked. Only captured positive payloads `01 ff bd`
  (prepare) and `04 ff` (finish) are accepted. Unknown statuses fail explicitly.

The reply values are preserved from a single successful capture. A finish
acknowledgment means the transaction was acknowledged, not that the e-paper
has completed its physical refresh. No pairing or encryption was observed.

## Validation

The original 10244-byte XTEK object was regenerated byte-for-byte from its
decoded pixels, including its checksum; all nine logical blocks also match
the capture after replacing two bad-CRC packets with their valid retransmits.
Object SHA-256:
`b8edd478d1a8482dd9bd4baa066eeedcfc609c308b36a002b409dc9af600ed1d`.

Automated tests cover RLE boundaries, pixel ordering, header checksums, block
sizes, observed commands, the BLE transaction using a fake client, invalid
replies, timeout, write failure and 20/182/244/514-byte backend write limits.
No raw radio capture or
nearby-device addresses are included in this repository.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Device not discovered | Bluetooth is enabled, device is in range, and the advertisement decodes as described above with a device number in the catalog. Do not match on a fixed MAC/name. |
| Tag stops being recognized | Discovery keys on the device number only, so battery and firmware changes are fine. If it still stops, capture the manufacturer data (`0x5258`) and open an issue. |
| "XTE tag … has an unknown device number" in the log | Pick the model by size in the config flow. Open an issue with the logged line plus the tag's printed model and resolution so the size becomes a captured model. |
| Response timeout or repeated failures | Verify that only one integration writes to the tag, check adapter/proxy reachability, and retain the underlying Poshiji error log. Smaller write limits are supported; do not force 244-byte writes. |
| Preview updates but panel does not | The preview is not a readback. Check `dry_run` under `data`; neither example sets it, so both send to the panel. |
| Weather automation does nothing | Check the target device ID, Naver weather/sensor entity IDs and daily forecast availability. Scheduled runs are on weekdays at 08:00, 11:00, 14:00 and 17:00. |

The Naver example calls `weather.get_forecasts` with `type: daily` and uses the
first returned forecast for low/high values. It expects a non-empty forecast
and valid weather/sensor data; it does not include an unavailable-data guard.
Avoid overly frequent redraws; this is an e-paper panel, not an LCD.
