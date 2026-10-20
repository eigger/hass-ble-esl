# Usage overview

**English** | **[한국어](ko/usage.md)**

This page collects the usage details that used to live in the README: why e-paper tags, writing a first layout, the visual editor, the two actions, the integration options and what the integration adds on top of the imagespec renderer. The full action, response and entity reference is in [actions.md](actions.md); Bluetooth setup is in [bluetooth.md](bluetooth.md).

## Why e-paper tags?

An **electronic shelf label (ESL)** is the display retailers use for shelf prices: an **e-paper** (e-ink) screen with its own battery and a Bluetooth radio. E-paper only draws power while the picture *changes* — holding a static image costs nothing, so a tag runs for months to years on its battery, is readable in daylight like printed paper, and emits no light.

That makes them ideal for information that should just *be there*, in places with no power outlet: a room calendar on the door, today's weather by the coat rack, the bin-collection day on the fridge, a "who is home" board, the print progress on the 3D printer, an inventory label on a storage box. Stick one anywhere and forget about charging it.

This integration talks to those tags directly from Home Assistant over BLE. You describe the layout in YAML (text, icons, QR codes, charts, images — anything from your entities), and the tag shows it.

## First layout

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

The tag refreshes in a few seconds. Add `dry_run: true` to render without sending — the result shows up in the tag's **Preview Content** image entity, so you can iterate on a layout without wearing the panel.

A layout is a list of [imagespec](https://github.com/eigger/imagespec) elements — text, icons, lines, QR codes, progress bars, gauges, pie/bar charts, history plots, downloaded images — and any value can be a Jinja template over your entities. Ready-made layouts for every supported resolution are in [`examples/`](../examples/README.md); the [Payload Editor](https://eigger.github.io/BLE_ESL_Payload_Editor.html) and [Image Uploader](https://eigger.github.io/Gicisky_Image_Uploader.html) web tools let you draft one in the browser.

## Visual editor

![ESL Manager dashboard](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/docs/images/manager/dashboard.png)

**ESL Manager** is the dashboard of every tag: its alias, battery, last successfully sent image, whether the display is in sync, the latest transmission result and duration, and its automations — with search, filters and sorting. From a card you open the designer or the automation that draws the tag.

Open **ESL Manager** in the HA sidebar to build the payload visually: drag, resize and layer elements, add any of the thirty [imagespec elements](https://github.com/eigger/imagespec/blob/v1.0.0/docs/elements.md) (shapes, text, QR / bar codes, charts, tables, …) and edit every field of each, with Jinja templates allowed. The preview, the image sent to the tag and the **Payload YAML** it gives you (the payload, or a complete `ble_esl.write` action with templates kept as written, so an automation follows your sensors) are the same payload drawn by the same renderer. **Import YAML** brings the payload of an action you already have into the designer, and **Convert to elements** turns a sensor or any older component into plain elements. Bluetooth Send saves the design first and sends only when requested. The designer does not automatically transmit on sensor changes; schedule updates with Home Assistant automations using the exported action.

From the connected-automations list, **Edit automation design** opens an existing `ble_esl.write` payload in a separate editing session and **Save to automation** stores it. The save rereads the latest automation configuration and replaces only the selected action's `data.payload`. It is blocked when the selected action changed or is ambiguous, or the design is invalid, and saving does not send anything over Bluetooth. Leaving the session restores the original design and undo history.

Existing YAML actions remain available. Full walkthrough: **[Designer guide](designer.md)**.

## Actions

The Write action takes a standard `target:` (a tag device, one of its entities, or an area/floor/label containing tags) and writes each target in turn.

| Action | Use it for |
|---|---|
| `ble_esl.write` | Skip unchanged images by default, honour the **Write Lock**, and debounce bursts |
| `ble_esl.write_guarded` | Compatibility alias for `ble_esl.write` |

| Parameter | Default | Description |
|---|---|---|
| `skip_unchanged` | `true` | Compare the final image with the last successful write; set `false` to resend |
| `use_saved_design` | `false` | Render the target tag’s current saved design; no payload is needed |
| `payload` | — | List of [imagespec elements](https://github.com/eigger/imagespec/blob/v1.0.0/docs/elements.md) (required unless `use_saved_design: true`); use `[]` for an intentional blank screen |
| `rotate` | `0` | `0`, `90`, `180`, `270` |
| `background` | `white` | `white`, `black`, `red`, `yellow` |
| `dry_run` | `false` | Render to **Preview Content** only |
| `debounce_override_ms` | option value | Override the debounce for this call (`0` = now) |

Both actions can return a per-tag result via `response_variable`. Full reference — dithering photos and charts, rotation, response data, the entities each tag exposes, fonts: **[actions.md](actions.md)**.

## Options

**Settings → Devices & services → BLE ESL → Configure**:

| Option | Default | Range | Description |
|--------|---------|-------|-------------|
| **Model** | — | model list | Shown only for protocols that cannot report their model (WOLINK, easyTag) |
| **Retry Count** | 3 | 1–10 | Retries when a BLE write fails |
| **Debounce Delay (ms)** | 0 | 0–120000 | Wait before writing; new requests cancel pending ones |

> [!TIP]
> Frequent automations: leave the action’s **Skip unchanged image** enabled and optionally configure **Debounce Delay** to save tag battery and BLE airtime. A write that fails mid-transfer is retried with slower packet pacing; if writes keep failing, the **Write Duration** sensor's attributes say whether it is the link or the placement — see [actions.md](actions.md#write-breakdown) and [troubleshooting.md](troubleshooting.md).

These options are specific to BLE ESL; they are not Bluetooth proxy firmware settings.

## Payload & rendering

Layouts are rendered by **[imagespec](https://github.com/eigger/imagespec)**; its docs are the reference for elements and fields:

| Topic | Link |
|-------|------|
| Element examples with preview images | [imagespec/docs/elements.md](https://github.com/eigger/imagespec/blob/v1.0.0/docs/elements.md) |
| All element fields & defaults | [imagespec README — Element Reference](https://github.com/eigger/imagespec#elements-reference) |
| Layout, palette, LLM authoring guide | [imagespec/docs/authoring.md](https://github.com/eigger/imagespec/blob/main/docs/authoring.md) |
| Dithering (per-element only) | [imagespec/docs/dithering.md](https://github.com/eigger/imagespec/blob/main/docs/dithering.md) |

What this integration adds on top:

- **Resolution and palette** come from the tag's preset, not the call. Off-palette colors are quantized to the nearest supported one (BW, BWR or BWRY).
- **Rotation** (`rotate: 90/180/270`) rotates the canvas; the output stays the panel size.
- **Dithering** is per element: put `dither` on photos and charts (`dlimg`, `pie`, `diagram`, `plot`, `sparkline`, `progress_bar`, `gauge`), not on text.
- **`plot`** reads history from the Recorder; **`dlimg`** accepts `/config/...` paths, HTTP(S) URLs and data URIs, read with Home Assistant's own access, which is why `write` and `write_guarded` are admin-only (automations are unaffected).
- **Fonts:** `NotoSansKR-Regular.ttf` is the default; drop your own `.ttf` into `config/www/fonts/` and reference it by name. See [fonts](actions.md#fonts).
- Prefer `row` / `column` / `stack` layout over hand-placed coordinates.

## Related projects

- [imagespec](https://github.com/eigger/imagespec) — the rendering engine behind `payload:`
- [Stash](https://github.com/eigger/stash) — self-hosted home inventory manager that prints labels to ESL tags via Home Assistant
- [hass-gicisky](https://github.com/eigger/hass-gicisky) — the archived PickSmart-only predecessor ([migration guide](migration.md))
