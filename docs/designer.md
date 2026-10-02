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
| Add a text, shape, icon or image | The buttons under **Components**, one click each (**＋ Add component** opens the older components' own editor: a value from an entity, progress bar, gauge, conditional icon) |
| Add a sensor | Pick it in **Entities**: one sensor component that draws the icon, name and value. **Configure** edits it; [Convert to elements](#convert-to-elements) splits it into elements |
| Add **any** imagespec element | **All elements** → choose one → **Add**. All thirty types are there: shapes, text (tables and multi-line text too), codes (QR, bar, data matrix), charts, media (icon, image), layout containers, widgets |
| Move, resize | Drag the element or its corner handle; arrow keys nudge one pixel, Shift ten |
| Edit a value | The **Element properties** panel lists every field imagespec has for the type except the position (the frame sets that), plus `dither`; required fields are marked `*`, defaults show as placeholders |
| Reorder, duplicate, delete | Right click → **Send back** / **Bring front**; Ctrl+D or the menu to duplicate; Delete or Backspace, or the menu, to delete. The **Layers** list selects |
| Undo, redo | Ctrl+Z, Ctrl+Shift+Z (or Ctrl+Y); ⌘ instead of Ctrl on a Mac. One step per edit |

Where an element sits comes from its **frame** (X, Y, Width, Height), not from keys you type. A rectangle fills its frame, a circle is centred in it, a QR code, barcode or icon takes its size from it, a polygon's corners are percentages of it. That is why every element moves and resizes the same way, and why the exported payload has ordinary absolute coordinates. `text_fit` and `new_multiline` fit the frame, `rich_text` sits on the frame's middle line, and a line runs through the middle of the frame (vertical when the frame is taller than it is wide). Text, tables and the like are drawn from the frame's top left at their own size.

Any value can be a [Jinja template](https://www.home-assistant.io/docs/configuration/templating/): `{{ states('sensor.room') }} °C`, `{{ [1, 2, 3] }}` for a list. The preview renders it with the current state and redraws when an entity it reads changes. **Auto update sensor** sends the tag again when something the design reads changes: it works on the **saved** design and only on tags that can be written, and it waits at least *interval* seconds (10 at the least, 60 by default) between sends. **Send to tag** saves the design and writes now.

> `plot` reads the recorder, so it needs one that records the entity. A colour an imagespec element asks for that the tag cannot show is drawn as the nearest one it can; the older components only offer the tag's colours.

## Payload YAML

**Payload YAML** shows the design as imagespec YAML, either the payload to paste under `payload:`, or a complete action (**Automation action** tab, with this tag's `device_id`; only for tags that can be written) for a script or automation.

When an element has a template, **Keep templates** (on by default) leaves it as written. Home Assistant then renders it every time the automation runs, so the tag follows its sensors without the designer being involved. Turn it off to see today's values.

```yaml
action: ble_esl.write
target:
  device_id: 0a1b2c3d…
data:
  background: white
  payload:
    - type: text_fit
      # (other keys left out)
      value: '{% set v = states(''sensor.room'') %}{% set n = v|float(none) %}{{ v|capitalize if v in [''unavailable'', ''unknown''] else ((''%.1f''|format(n) if n is not none else v)) ~ '' °C'' }}'
      x: 8
      y: 8
      width: 120
      height: 40
```

What stays as of the moment: the older sensor components (see [Convert to elements](#convert-to-elements) for how to make them follow the sensor), field templates, and a polygon whose corners come from a template (its corners are percentages of the frame, which only the rendered text can give). The note under the tabs says what is as of the moment; the list below it names what the renderer would reject (an unknown icon, say), a polygon whose corners are as of now, and a string Home Assistant would take for a template.

## Import YAML

**Import YAML** takes the payload of an action you already have, as the list, as a mapping with `payload:`, or the whole action, and turns each element into an element to edit. **Add to display** keeps what is on the canvas, **Replace display** starts again.

- What cannot be placed in the designer is listed with the reason: a position that is a template or a script variable (`x: "{{ grid_x + 10 }}"`), an element with no position (it is laid out after the previous one), a diagonal line, a type imagespec does not have.
- The designer draws the pasted payload and what it builds from it and tells you **how many pixels differ**. `0` means it will write exactly what your automation did. A number above zero says the designer changed something: a QR code that had no size may now have a frame, or a corner was fractional.
- YAML anchors and aliases (`&a`, `*a`, `<<: *a`) are refused, and so are texts over 256 K characters: write repeated values out.
- A display holds 100 elements; the rest are listed.

## Convert to elements

The older components (sensor, text, icon, image, shapes, progress bar, gauge) are drawn from settings the designer keeps. **Convert to elements** (in the properties panel) turns the selected one into the plain imagespec elements it is drawn with, in its place, one undo step. Each field is then editable, and the YAML is ordinary imagespec.

The properties panel groups its fields: **Content** (what the element shows or is bound to), **Position & size** (px), **Style**, and a collapsed **Advanced**. With nothing selected it offers the display **Background**. In **Layers**, each row can be hidden (eye), moved forward or backward, or deleted. The toolbar says *Unsaved changes* until you save, and the browser asks before leaving a page with unsaved work. A message in red can be dismissed with ×.

Their properties panel also has the optional settings imagespec offers for what each draws: text and sensors (vertical align, fit, max lines, min font size, padding, line spacing, font file), shapes (filled or outline only, outline width, corner radius), icons (outline width and colour), images (rotate, crop to circle), progress bars (direction, corner radius, outline width, percentage), gauges (arc thickness, show value), and **Dither** for any of them. A setting left blank keeps imagespec's default, and **Visible** hides an element without deleting it.

For a sensor shown as a plain value the value text becomes a template that follows the sensor, rounded as the component asked and with its unit; an unavailable state shows as it did before.

These stay as text, as they were drawn: a weather or binary sensor, a sensor that is not available now, one with a data field or field templates, a bare number without a unit (Home Assistant reads a template whose result is only a number as a number, so 21.50 would become 21.5) and a unit with a quote, backslash or line break in it. The last two say why. Text that has template syntax in it (a unit or a name that contains `{{`) is **left out** instead, with the reason, because as an imagespec element Home Assistant would run it; the pixel count then shows what is missing.

The status line says whether the result is drawn exactly as before (`0` pixels differ) or by how much it is not.

## Sensor templates and the older components

**Sensor templates** (the second tab) are reusable layouts for a kind of sensor: design one with `{{name}}`, `{{state}}`, `{{unit}}` and `{{icon}}` placeholders and every sensor component of that kind uses it, scaled to its frame. They belong to the older components and cannot hold imagespec elements; convert a sensor to take it out of the template system.

**Configure** opens the older component's own editor (entity, data field, icon rules, field templates).

## Limits

- 100 elements per display.
- Positions come from frames. **Import** cannot place elements laid out after each other (no `y`), diagonal lines and positions computed by a template; inside the designer a field template can still move an element.
- A layer you drag is what the element draws, cut out of the display; a half-transparent edge, such as a soft-edged PNG, can look slightly different while you drag. The picture on the canvas when you let go is the real one.
- Dithering is per element (`dither:`), never for the whole display; see [Per-element dither](actions.md#per-element-dither-photos--charts).
