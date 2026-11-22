# Design templates

The gallery filters templates by Weather, Schedule, Smart home, and Labels. A template may appear in more than one category; uncategorized templates remain in All. In YAML, `categories` is optional, for example `categories: [weather, schedule]`. Allowed values are `weather`, `schedule`, `smart_home`, and `labels`.


**English** | **[한국어](ko/design-templates.md)**

## Using a template

In the Designer, choose **Browse design gallery** (the first block of the left panel). The gallery lists the designs with a thumbnail drawn by the real renderer for this tag (a default entity that does not exist is replaced by the first one of its domain), and shows whether a layout was *adjusted* to the tag's display size. Pick one, change its parameters if you like (every one has a default; the preview above the fields redraws as you type), then:

- **Add to display** keeps what is on the canvas; **Replace display** starts again. The result is ordinary, editable elements.
- **Replace and create automation** (templates with an `automation` block, writable tags) also opens **Create automation**, with the template's triggers, for example *every day at 12:00*, already filled in. Choose **Create automation** in that dialog to save it.

After choosing **Add to display** you can still use the toolbar's **Create automation**: it uses the triggers of the template you applied last, as long as that design's elements are still on the canvas (undo, replace, import or deleting them drops the triggers).

A design template is a YAML file that describes a ready-made ESL design: the imagespec elements, the few values a user may change (font, colors, time…), and optionally the automation that keeps it up to date. Applying one in the Designer produces ordinary, fully editable elements; nothing in the saved result refers back to the template.

Bundled templates live in [`custom_components/ble_esl/designer/templates/`](../custom_components/ble_esl/designer/templates). Every `*.yaml` file in that folder is loaded when Home Assistant starts. A file that is invalid is skipped and the reason is logged as a warning (`Ignoring design template …`).

> The [`examples/`](../examples) folder is documentation and is not installed with the integration, so a template must be placed in the folder above.

## Bundled templates

The gallery selects an exact layout by tag resolution for the 1.54- to 13.3-inch presets, including portrait and landscape orientations. Compact screens keep the key values prominent. From 4.2 inches (`date`, `weather_forecast`) and 5.8 inches, the existing templates use the added space for details supported by the same entities in both orientations. Templates keep their existing update schedules.

| Template | Main content | Added on larger screens | Automation |
|---|---|---|---|
| `date` | Month/day with the weekday below (weekend color) | Year, ISO week and the current week's dates (from 4.2 inches) | Daily at 12:00 |
| `wifi` | Wi-Fi QR code (WPA, WPA3/SAE, WEP, open; hidden networks) with a title and hint | Network name for visible networks and security type | none |
| `message` | Large centred text that shrinks to fit (one line by default) | Optional second line | none |
| `color_check` | Black, white, red and yellow swatches | Resolution and 1, 2 and 4 px line samples | none |
| `weather_now` | Icon, temperature, condition and humidity of a chosen `weather` entity (missing values show `--` or nothing) | Feels-like temperature, humidity and wind | Every 10, 15 or 30 minutes |
| `weather_forecast` | The next three days of a `weather` entity's daily forecast: weekday, icon, high and low (`--` until the forecast is fetched) | Five (from 4.2 inches) or seven forecast days with precipitation probability | Every 1, 3 or 6 hours |
| `weather_outdoor` | Korean outdoor weather: large current temperature, rain or snow alert/timing (`3.5"`+ adds low/high) | 7-day outlook from 4.2 inches and hourly slots from 7.5 inches | Hourly |
| `weather_commute` | Morning commute briefing: large temperature, min/max and rain/snow umbrella alert on tags under 4 inches | Today's commute metrics plus 5-, 6- or 7-day weekly forecasts with precipitation probability | Every 1, 3 or 6 hours |
| `sensor_card` | Icon, title and value with unit of any `sensor` entity (title empty = the entity's name; numbers rounded to one decimal, optional alert threshold) | Last update and an optional second sensor reading | Every 5, 10, 15 or 30 minutes |
| `calendar_next` | The current or next event of a `calendar` entity: title, date and time, location (falls back to entity attributes) | Up to three upcoming events via `calendar.get_events`, or end time and description | When the event changes and every 10, 15 or 30 minutes |
| `print_progress` | A 3D printer's progress bar and percentage, status and finish time from three `sensor` entities (progress is kept between 0 and 100) | Estimated time remaining and optional nozzle/bed temperature sensors | Every 1, 5, 10 or 15 minutes and when the status changes |
| `date_weather` | Today's date and weekday beside the icon, temperature and condition of a `weather` entity | Feels-like temperature, humidity and wind | Every 10, 15 or 30 minutes |
| `countdown` | Days left until a date (`D-12`, `D-Day`, `D+3`) with a title; the number turns to the alert color from a chosen number of days before the date and stays in it after the date (`--` for an invalid date) | Target weekday and interval in weeks and days | Daily at 00:05 |
| `indoor_climate` | Large indoor temperature, humidity and comfort/ventilation status accent | Metric cards with progress bars for temperature, humidity, optional CO2 & PM2.5 and ventilation advice | Every 5, 10, 15 or 30 minutes |
| `calendar_weather` | Large current temperature and next calendar event from entity attributes (`3.5"`+ adds date) | Today's low/high, 4-day weather forecast with precipitation chance and up to 4 upcoming calendar events | Every 10, 15 or 30 minutes |
| `home_presence` | Large home-presence count and entryway door status accent (`3.5"`+ adds home-member summary) | 4 member cards with status/last-changed timestamp and entryway door alert banner | Every 5, 10, 15 or 30 minutes |
| `energy_power` | Large live power reading, load status accent and today's energy | Budget load bar, dedicated today's energy & solar generation cards and saving advice banner | Every 1, 5, 10 or 15 minutes |
| `ev_charging` | Large battery SOC percentage, charging status accent and estimated range (`3.5"`+ adds charging power) | SOC progress bar, threshold hints, range/power cards and status detail banner | Every 5, 10, 15 or 30 minutes |
| `appliance_status` | Priority appliance name (`error` > `done` > `running`) and large status text/icon on tags under 4 inches | Up to 3 dedicated appliance cards with remaining time or last-changed timestamp and full alert banner | Every 1, 5, 10 or 15 minutes |

The designer saves a plain payload, so a service response is read by the payload's own templates: `weather_forecast` and `calendar_weather` read `fc`, the `response_variable` of the `weather.get_forecasts` step, while 5.8"+ `calendar_next` and 4.2"+ `calendar_weather` layouts read `events`, the `response_variable` of `calendar.get_events` (falling back to the calendar entity's own attributes when `events` is unavailable or on smaller tags). The Designer previews such designs with the real daily forecast or calendar events of the entities they name (fetched for the preview only), and adds those steps when creating or updating an automation. Examples that build an open-ended list of elements with a Jinja loop are not templates: a template carries a fixed payload (so `home_presence` provides 4 fixed member slots). A single entity can be a parameter, as `weather_now` does.

Outdoor weather uses daily and hourly forecasts from the selected weather entity. Missing fields display an em dash. On 10.2- and 13.3-inch tags, the optional snowfall sensor should report total expected new snow for today. When supplied with a positive value, it appears in place of the forecast precipitation total. Sunset comes from `sun.sun`.

## Your own templates

Put template files in `<config>/ble_esl/templates/*.yaml`; they are listed (marked *My template*) the next time the gallery opens, with no restart. A file that is invalid is skipped with a warning in the log, and a file cannot reuse the `id` of a bundled template.

To make one from a design, build it in the Designer, open **Browse design gallery**, type a name under **Save current design as a template** and choose **Save as template**. The file is written to the folder above with the design's current display size as its only layout. Unsaved edits are included and templates in elements are kept as written. A second save under the same name (or a name that matches a bundled template or a file already in the folder, even one that does not load) gets a new id (`name_2`) instead of overwriting; only an explicit `template_id` with `overwrite` replaces a file, and only the one named after that id. The gallery re-reads the folder every time it opens. Edit the file afterwards to add `parameters` (replace values with `${name}`), more layouts or an `automation` block.

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
      "y": 10
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

`automation` provides the defaults for a new automation (the alias if given, otherwise the tag title): its alias, `triggers` (at least one), `conditions`, `mode` and `description`, and optionally `actions`: steps that run before the write, for example one that fetches a forecast into a `response_variable` the payload reads. The `ble_esl.write` action is added from the current design after them, so it is not part of the template. Home Assistant validates the automation when it is saved.

A daily update at noon:

```yaml
automation:
  alias: Date label
  triggers:
    - trigger: time
      at: ${time}
```

## Checking a template

Run the test-suite: `tests/components/ble_esl/test_design_templates.py` loads every bundled template and, for several display sizes and color sets, imports its payload, renders it, and checks the designer reproduces it with `0` pixels different. It also validates the automation with Home Assistant.

## API

The Designer's websocket command `ble_esl/designer` offers `design_templates` (the list for a tag), `save_design_template` (`name`, optional `template_id`, `overwrite`; saves a design to the user folder), `preview_design_template` (`template_id`, `parameters`; a PNG drawn for the tag, nothing imported), and `apply_design_template` (`template_id`, `parameters`, `existing`, `preview_variables`), which returns the same result as an import plus a `template` block with the chosen layout, the final parameter values and the automation defaults. Pass those defaults as `automation_defaults` to the `automation` action to prefill the new automation.
