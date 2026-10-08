# Design templates

**English** | **[한국어](ko/design-templates.md)**

## Using a template

In the Designer, choose **Templates** (under the component buttons). The gallery lists the designs and shows whether a layout was *adjusted* to the tag's display size. Pick one, change its parameters if you like (every one has a default), then:

- **Add to display** keeps what is on the canvas; **Replace display** starts again. The result is ordinary, editable elements.
- **Replace and create automation** (templates with an `automation` block, writable tags) also opens **Create automation**, with the template's triggers, for example *every day at 12:00*, already filled in. Choose **Create automation** in that dialog to save it.

After choosing **Add to display** you can still use the toolbar's **Create automation**: it uses the triggers of the template you applied last, as long as that design's elements are still on the canvas (undo, replace, import or deleting them drops the triggers).

A design template is a YAML file that describes a ready-made ESL design: the imagespec elements, the few values a user may change (font, colors, time…), and optionally the automation that keeps it up to date. Applying one in the Designer produces ordinary, fully editable elements; nothing in the saved result refers back to the template.

Bundled templates live in [`custom_components/ble_esl/designer/templates/`](../custom_components/ble_esl/designer/templates). Every `*.yaml` file in that folder is loaded when Home Assistant starts. A file that is invalid is skipped and the reason is logged as a warning (`Ignoring design template …`).

> The [`examples/`](../examples) folder is documentation and is not installed with the integration, so a template must be placed in the folder above.

## Bundled templates

| Template | What it makes | Layouts | Automation |
|---|---|---|---|
| `date` | Month/day with the weekday below (weekend color) | 250×128, 400×300 | Daily at 12:00 |
| `wifi` | Wi-Fi QR code (WPA, WPA3/SAE, WEP, open; hidden networks) with a title and hint | 250×128, 400×300 | none |
| `message` | Large centred text that shrinks to fit (one line by default) | 250×128 (scaled) | none |
| `color_check` | Black, white, red and yellow swatches | 250×128, 400×300 | none |
| `weather_now` | Icon, temperature, condition and humidity of a chosen `weather` entity (missing values show `--` or nothing) | 250×128, 400×300 | Every 10, 15 or 30 minutes |

Examples that need a service response (forecasts, calendars) or build their elements with a loop (presence) are not templates: a template carries a fixed payload. A single entity can be a parameter, as `weather_now` does.

## Your own templates

Put template files in `<config>/ble_esl/templates/*.yaml`; they are listed (marked *My template*) the next time the gallery opens, with no restart. A file that is invalid is skipped with a warning in the log, and a file cannot reuse the `id` of a bundled template.

To make one from a design, build it in the Designer, open **Templates**, type a name under **Save current design as a template** and choose **Save as template**. The file is written to the folder above with the design's current display size as its only layout. Unsaved edits are included and templates in elements are kept as written. A second save under the same name (or a name that matches a bundled template or a file already in the folder, even one that does not load) gets a new id (`name_2`) instead of overwriting; only an explicit `template_id` with `overwrite` replaces a file, and only the one named after that id. The gallery re-reads the folder every time it opens. Edit the file afterwards to add `parameters` (replace values with `${name}`), more layouts or an `automation` block.

A design whose text contains `${…}` cannot be saved this way, because that would read as a parameter.

## File format

```yaml
template: 1                  # format version, always 1
id: date                     # lowercase letters, digits, underscore; unique
name: { en: Date label, ko: 날짜 라벨 }   # text, or a map of language -> text
description: { en: …, ko: … }
background: white            # black | white | red | yellow (white if the tag cannot show it)

parameters:                  # values the user may change
  font:
    type: font
    default: GmarketSansTTFBold.ttf
    label: { en: Font, ko: 글꼴 }
  time:
    type: time
    group: automation        # used only by the automation block
    default: "12:00:00"

layouts:                     # one payload per display size
  "250x128":
    - type: text
      value: "{{ now().strftime('%m/%d') }}"
      font: ${font}
      anchor: mt
      x: 125
      y: 10
      size: 45

automation:                  # optional
  alias: Date label
  triggers:
    - trigger: time
      at: ${time}
  mode: single
```

### Layouts

Each key under `layouts` is `WIDTHxHEIGHT` and holds the same list of elements you would put under `payload:` in `ble_esl.write` (see [actions](actions.md)): absolute coordinates, at most 100 elements. Jinja is allowed and is kept as written, so `{{ now() }}` is evaluated each time the automation runs.

For a display whose size has no layout, the nearest layout is used. It is scaled evenly and centred: every number is a length in pixels and is multiplied (a positive length such as an outline width never drops below 1), except counts, angles, data and limits such as `x_repeat`, `y_repeat`, `rotation`, `start_angle`, `end_angle`, `max_lines`, `min`, `max`, `min_value`, `max_value`, `progress`, `values`, `rows`, `grow`, `border`, `data`, `dither`, and barcode millimetre keys such as `module_width`. The result reports `scaled: true`. A layout containing a polygon `points` string, even nested in a group, cannot be scaled and needs its own layout for each size. Write a dedicated layout for any size you care about. Values that are templates (not numbers) are not scaled.

### Parameters

`${name}` inside a layout or the automation is replaced before the elements are imported. Jinja `{{ }}` is not touched. A string that is only a reference, such as `size: ${size}`, keeps the value's type; a reference inside longer text becomes text. Every `${…}` must name a declared parameter.

| `type` | Value | Notes |
|---|---|---|
| `font` | file name | Must exist in the integration's `fonts/` folder or `www/fonts` |
| `color` | `black`, `white`, `red`, `yellow` | A color the tag cannot show becomes `black` |
| `select` | one of `options` | `options: [a, b]` is required |
| `string` | text | No braces, quotes, backslashes or line breaks, because it may be placed inside a Jinja string. Optional `forbidden: ";:,"` lists further characters to refuse and `min_length` requires a minimum length |
| `number` | number | Optional `min` / `max` |
| `time` | `HH:MM` or `HH:MM:SS` | Stored as `HH:MM:SS` |
| `boolean` | true / false | |
| `entity` | entity id such as `weather.home` | Optional `domain: weather` limits the choice (the gallery offers matching entities); the gallery offers matching entities only when `domain` is set, and if the default does not exist on this system it prefills the first matching one. Applying fails if the entity does not exist, so set the integration up first |

Every parameter needs a `default`, so a template can be applied without asking anything. `label` is optional text or a language map. `group: automation` marks a parameter that only the automation uses; the design may not reference it.

### Automation

`automation` provides the defaults for a new automation (the alias if given, otherwise the tag title): its alias, `triggers` (at least one), `conditions`, `mode` and `description`. The `ble_esl.write` action is added from the current design as usual, so it is not part of the template. Home Assistant validates the automation when it is saved.

A daily update at noon:

```yaml
automation:
  alias: Date label
  triggers:
    - trigger: time
      at: ${time}
```

## Checking a template

Run the test-suite: `tests/test_design_templates.py` loads every bundled template and, for several display sizes and color sets, imports its payload, renders it, and checks the designer reproduces it with `0` pixels different. It also validates the automation with Home Assistant.

## API

The Designer's websocket command `ble_esl/designer` offers `design_templates` (the list for a tag), `save_design_template` (`name`, optional `template_id`, `overwrite`; saves a design to the user folder), and `apply_design_template` (`template_id`, `parameters`, `existing`, `preview_variables`), which returns the same result as an import plus a `template` block with the chosen layout, the final parameter values and the automation defaults. Pass those defaults as `automation_defaults` to the `automation` action to prefill the new automation.
