# Payloads

[README](../README.md) | **English** | [한국어](payload.ko.md)

## Common payload guide

See the [imagespec payload guide](https://github.com/eigger/imagespec/blob/main/docs/payload.md) for shared syntax, elements, properties, colors, rotation and dithering.

## Using payloads in this integration

Call `ble_esl.write` or `ble_esl.write_guarded` from Developer Tools → Actions, a script or an automation. Select a loaded BLE ESL device or one of its entities with the normal HA target selector. The element list belongs in `data.payload`; a YAML string is not accepted. `write_guarded` also respects duplicate suppression, the write lock and configured debounce. See [actions and responses](actions.md) for their complete behavior.

HA evaluates Jinja in action data before the registered action schema validates the list, rotation and background. The write pipeline repairs YAML 1.1 boolean keys before passing the elements to the production imagespec renderer. Element values should use the imagespec guide's documented properties. The visual designer can also compile its own design documents into this same pipeline; those documents are separate from a plain payload list.

## Minimal working example

Open the complete [minimal action YAML](../examples/payload/minimal.yaml). It renders black and red rectangles on a white 296 × 128 canvas for a WOLINK 2.9-inch `290` BWRY tag. Replace `target.entity_id` with an entity of your loaded BLE ESL device; the sample entity identifies the test device and is not auto-discovered on your installation. The [template action YAML](../examples/payload/template.yaml) additionally demonstrates HA template evaluation and 90° canvas rotation with a yellow rectangle.

Both examples set `dry_run: true`: the preview image updates without a BLE transfer. Inspect the device's preview image, then set `dry_run: false` when you want to write the tag. Pick a matching model first; the target's configured preset supplies the resolution and palette. Existing [device examples](../examples/) cover additional layouts and panels.

## Device output settings

The sample WOLINK `290` preset renders 296 × 128 pixels in black, white, red and yellow. Other presets have their own dimensions and BW, BWR or BWRY palette. Choose the actual panel/protocol in integration options; an incorrect resolution or color mode can corrupt the physical result. Protocol encoding and physical display behavior remain device-specific.

Action fields `rotate` (0, 90, 180 or 270) and `background` control rendering. The integration uses imagespec `rotate_mode="canvas"`, so output dimensions remain fixed even at 90°/270°. Global dithering is disabled; use supported element-level dithering for image/chart elements when needed. There is no global action `dither` field.

The default font is bundled `NotoSansKR-Regular.ttf`. Font lookup first checks the integration's bundled fonts, then `/config/www/fonts` (the HA configuration directory's `www/fonts`), using the filename only. See [font and action details](actions.md).

## Supported features and limitations

The manifest declares `imagespec[datamatrix]>=1.1.0`; available elements follow the installed library version and its documented API. HA handles action-data templates; imagespec receives their prepared values. The integration supplies a font resolver, permits local image files, and provides recorder history for supported history elements. History requires the HA recorder and runs through its executor; a query that exceeds 60 seconds raises an error. Remote images require network access from the HA host. Paths, fonts, URLs and entities must exist in that installation.

The examples use only rectangles, so they require no downloaded images, history or external font files. Their executable contract loads the real HA integration, normalizes the registered action schema and compares the real production renderer with the installed imagespec public renderer; it never dispatches a BLE command. This checks software output, not actual hardware compatibility or panel quality. The write actions are admin-only because payload images can access local files and URLs. The device palette limits final color output; rendering cannot add colors or resolution that the panel lacks.

## Troubleshooting

First use `dry_run: true` to isolate payload/rendering problems from BLE transport. Check the selected model, loaded target, rendered templates, palette, font filename and local/remote image access. For history errors, verify recorder is enabled and the requested entities have history. Follow the local [troubleshooting guide](troubleshooting.md) for device and Bluetooth failures. Report remaining problems through the existing [Issues](https://github.com/eigger/hass-ble-esl/issues), including the model, firmware, redacted action YAML and diagnostics.
