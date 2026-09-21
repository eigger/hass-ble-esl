# Actions, entities and fonts

Reference for the two actions this integration registers, the data they return, the entities each tag exposes, and font lookup. For what goes inside `payload:` see [imagespec](https://github.com/eigger/imagespec); for a first write see the [README](../README.md#quick-start).

## Actions

Both actions take a standard `target:`: a BLE ESL device, any of its entities, or an area/floor/label containing one. Several tags can be targeted in one call; each is written in turn and failures are reported together at the end. The examples below use `device_id`.

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

### More examples

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

| Action | When to use |
|---------|-------------|
| `ble_esl.write` | Always send (except explicit `dry_run`) |
| `ble_esl.write_guarded` | Automations that fire often; skip duplicates and coalesce rapid updates |

### Response data

Both actions can return what happened to each target. Ask for it with `response_variable`; the result is a map keyed by device id:

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
| `written` | Image is on the tag | `attempts`, `duration_s`, `timing` (the [write breakdown](#write-breakdown) of the attempt) |
| `failed` | Every attempt failed | `error`, `attempts`, `duration_s`, `timing` of the last attempt |
| `scheduled` | `write_guarded` debounced the write; it runs in the background after the quiet period (`delay_ms`). **Its result is not part of this response** — check the *Display In Sync* / *Failure Count* entities if you need it | `delay_ms` |
| `duplicate` | `write_guarded`: image unchanged, not sent (**Prevent Duplicate Send**) | |
| `locked` | Write lock switch is on; preview updated only | |
| `preview` | `dry_run`: rendered only | |

When a response is requested, a failed tag is **reported instead of raising**, so the automation continues and can branch on it. Without `response_variable` a failure still raises (and stops the automation) as before. Targeting no loaded tag at all always raises.

## Entities

Every tag is one device with these entities:

| Entity | Type | Meaning |
|---|---|---|
| Battery / Battery Voltage | sensor | See below; a **Battery** binary sensor turns on when low |
| Temperature | sensor | Only on protocols that report it in the write session (easyTag) |
| Signal Strength | sensor | RSSI of the last advertisement |
| Connectivity | binary sensor | Tag seen recently |
| Display In Sync | binary sensor | Last write reached the tag |
| Write Duration | sensor | Seconds of the last write; attributes describe the attempt |
| Failure Count / Last Failure Time | sensor | Consecutive failed writes |
| Last Updated Content | image | Last image sent |
| Preview Content | image | `dry_run` renders |
| Alias | text | Free-form label for the tag |
| Write Lock | switch | On: nothing is sent to the tag; both actions only update the preview |

- **Write monitoring:** the **Write Duration** sensor's attributes describe the last write attempt (see [Write breakdown](#write-breakdown)); the same data is in the diagnostics download.
- **Battery:** the tag voltage is mapped linearly to **Battery** (%) over 2.5–2.9 V for every backend that reports a voltage (PickSmart and WOLINK from the advertisement, easyTag from the write session), and a **Battery** binary sensor (low battery) turns on at 2.5 V or below, where e-paper refresh becomes unreliable even though BLE still works. XTE (Poshiji) tags advertise a percentage directly; the low-battery sensor turns on at 10 % or below.

## Write breakdown

Every write attempt is recorded on the **Write Duration** sensor's attributes and returned in the action's `timing` (with `response_variable`), so a slow or flaky tag can be diagnosed without debug logging.

| Attribute | Meaning |
|---|---|
| `attempt` / `success` / `error` | Which retry this was and how it ended |
| `via` / `via_type` / `via_source` | The radio the write went through: a Bluetooth **proxy** (its ESPHome name and MAC) or a local **adapter** (`hci0` and its MAC) |
| `rssi` | Signal strength of the tag's last advertisement as seen by that radio |
| `paths` | How many connectable radios currently see the tag (1 = no failover possible) |
| `connect_s` | Establishing the BLE link — includes any connection retries |
| `session_s` | Everything after the link was up (the stages below) |
| `settle_s` | Fixed pause after subscribing to notifications |
| `start_s` | Handshake before the image data: START/SIZE/IMAGE commands (PickSmart), AES authentication (WOLINK), the size command (XTE) |
| `parts` / `bytes` | Number of frames the image is sent as, and its encoded size. PickSmart and WOLINK also count `sends` — frames actually written, which on a failed attempt shows how far it got |
| `transfer_s` | Sending the image data |
| `finish_s` | From the last data frame until the tag confirms; for WOLINK and easyTag this is the e-paper refresh itself |

Protocol-specific extras: PickSmart adds `start_probes` (how many START commands were needed — should mostly be 1), `sends` / `resends` (chunks the tag asked for again), `round_trip_ms` (per-chunk round trip; the best measure of path quality) and `completed_by_tag`; XTE adds `chunk_size` (the ATT write size the backend allowed — 20 on some proxies, 244 on others, which dominates `transfer_s`).

Reading it: a large `connect_s` with a low `rssi` or `paths: 1` points at placement or a missing proxy; `resends` or `start_probes` above 1 point at a marginal link (try **Write Delay**); a large `finish_s` on WOLINK/easyTag is the panel refresh, which grows with panel size and cold temperature and is not a transport problem. `via` tells you which proxy the tag actually used, which is what to move or replace.

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
