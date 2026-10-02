# ESL Designer

**English** | **[한국어](ko/designer.md)**

The designer is a visual way to make the **payload** of a [`ble_esl.write`](actions.md) action. What it shows, what it sends to the tag and the YAML it gives you are the same payload, drawn by the same [imagespec](https://github.com/eigger/imagespec) renderer, so a design you finish here is one you can paste into an automation and get the same picture.

Open **ESL Designer** in the Home Assistant sidebar (it appears once a tag is configured; admins only). Pick the tag at the top: the canvas has its size and colours.

- [Making a design](#making-a-design)
- [Payload YAML: using the design in an automation](#payload-yaml)
- [Import YAML: editing an existing payload](#import-yaml)
- [Convert to elements](#convert-to-elements)
- [Sensor templates and the older components](#sensor-templates-and-the-older-components)
- [Limits](#limits)

## Making a design

| To | Do |
|---|---|
| Add a text, shape, icon or image | The buttons under **Components** |
| Add a sensor | Pick it in **Entities**: its name, value and icon become elements |
| Add **any** imagespec element | **All elements** → choose one → **Add**. All thirty types are there: shapes, text, QR / bar / data-matrix codes, charts, tables, layout containers, widgets |
| Move, resize | Drag the element or its corner handle; arrow keys nudge, Shift for ten |
| Edit a value | The **Element properties** panel lists every field imagespec has for the type; required ones are marked `*`, defaults show as placeholders |
| Reorder, duplicate, delete | The **Layers** list, the context menu (right click), Ctrl+D, Delete |
| Undo | Ctrl+Z / Ctrl+Shift+Z; one step per edit |

Where an element sits comes from its **frame** (X, Y, Width, Height), not from keys you type. A rectangle fills its frame, a circle is centred in it, a QR code, barcode or icon takes its size from it, a polygon's corners are percentages of it. That is why every element moves and resizes the same way, and why the exported payload has ordinary absolute coordinates. Text, tables and similar elements are drawn from the frame's top left at their own size.

Any value can be a [Jinja template](https://www.home-assistant.io/docs/configuration/templating/): `{{ states('sensor.room') }} °C`, `{{ [1, 2, 3] }}` for a list. The preview renders it with the current state and redraws when an entity it reads changes. **Auto update sensor** sends the tag again when something the design reads changes (at most every *interval* seconds); **Send to tag** writes now.

> `plot` reads the recorder, so it needs a Home Assistant with one (every real installation has). Colours are limited to what the tag can show; others are rounded to the nearest.

## Payload YAML

**Payload YAML** shows the design as imagespec YAML, either the payload to paste under `payload:`, or a complete action (**Automation action** tab, with this tag's `device_id`) for a script or automation.

When an element has a template, **Keep templates** (on by default) leaves it as written. Home Assistant then renders it every time the automation runs, so the tag follows its sensors without the designer being involved. Turn it off to see today's values.

```yaml
action: ble_esl.write
target:
  device_id: 0a1b2c3d…
data:
  background: white
  payload:
    - type: text_fit
      value: '{% set v = states(''sensor.room'') %}{% set n = v|float(none) %}{{ v|capitalize if v in [''unavailable'', ''unknown''] else ((''%.1f''|format(n) if n is not none else v)) ~ '' °C'' }}'
      x: 8
      y: 8
      width: 120
      height: 40
```

What stays as of the moment: the older sensor components (see [Convert to elements](#convert-to-elements) for how to make them follow the sensor), field templates, and a polygon whose corners come from a template (its corners are percentages of the frame, which only the rendered text can give). The list under the text says so, and anything the renderer would reject, such as an unknown icon, or a string Home Assistant would take for a template.

## Import YAML

**Import YAML** takes the payload of an action you already have, as the list, as a mapping with `payload:`, or the whole action, and turns each element into an element to edit. **Add to display** keeps what is on the canvas, **Replace display** starts again.

- What cannot be placed in the designer is listed with the reason: a position that is a template or a script variable (`x: "{{ grid_x + 10 }}"`), an element with no position (it is laid out after the previous one), a diagonal line, a type imagespec does not have.
- The designer draws the pasted payload and what it builds from it and tells you **how many pixels differ**. `0` means it will write exactly what your automation did. A number above zero says the designer changed something: a QR code that had no size now has a frame, a corner was fractional.
- YAML anchors and aliases (`&a`, `*a`, `<<: *a`) are refused, and so are texts over 256 KB: write repeated values out.
- A display holds 100 elements; the rest are listed.

## Convert to elements

The older components (sensor, text, icon, image, shapes, progress bar, gauge) are drawn from settings the designer keeps. **Convert to elements** (in the properties panel) turns the selected one into the plain imagespec elements it is drawn with, in its place, one undo step. Each field is then editable, and the YAML is ordinary imagespec.

For a sensor shown as a plain value the value text becomes a template that follows the sensor, rounded as the component asked and with its unit; an unavailable state shows as it did before. A weather or binary sensor, a state that is not available, a bare number without a unit (Home Assistant would turn the template's result back into a number and lose its format), and a unit that is itself template syntax stay as they are, with the reason.

The status line says whether the result is drawn exactly as before (`0` pixels differ) or by how much it is not.

## Sensor templates and the older components

**Sensor templates** (the second tab) are reusable layouts for a kind of sensor: design one with `{{name}}`, `{{state}}`, `{{unit}}` and `{{icon}}` placeholders and every sensor component of that kind uses it, scaled to its frame. They belong to the older components and cannot hold imagespec elements; convert a sensor to take it out of the template system.

**Configure** opens the older component's own editor (entity, data field, icon rules, field templates).

## Limits

- 100 elements per display.
- Positions come from frames: elements laid out after each other (no `y`), diagonal lines and positions computed by a template cannot be placed.
- A layer you drag is what the element draws, cut out of the display; a half-transparent edge, such as a soft-edged PNG, can look slightly different while you drag. The picture on the canvas when you let go is the real one.
- Dithering is per element (`dither:`), never for the whole display; see [Per-element dither](actions.md#per-element-dither-photos--charts).
