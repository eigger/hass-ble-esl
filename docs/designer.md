# Visual display editor

After installing the integration and restarting Home Assistant, open **Label designer** in the sidebar. The editor uses the existing BLE ESL devices and write pipeline; it does not require a separate tag protocol or cloud service. Administrator access is required.

## Design a display

Choose a tag, then add text, images, shapes or sensor components. Drag elements freely, resize from any corner, and use arrow keys for precise positioning (Shift moves ten pixels). Elements may extend beyond the display; the sent image clips to the tag dimensions. Clicking empty canvas space deselects the current element.

The preview fits the available window by default. Use the zoom controls to inspect pixels. The editing view uses the same rendered layers as the final image, so fonts, wrapping and icons agree with the sent image. Components have transparent backgrounds by default.

The side panels collapse independently. The right panel contains selected-element properties and a separate layer list. Right-click an element to duplicate, delete, change its layer order or center it. Delete/Backspace removes the selected component; shortcuts do not apply while typing in a picker or field.

**Configure** opens the component editor. Choose a component (text/value, icon, conditional icon, image, shape, progress bar or gauge), then independently bind an entity and select its state, name, unit, icon or attribute. Native HA entity and icon pickers provide search. Conditional icons map exact states or ordered numeric ranges to icons; ranges include their lower bound and exclude their upper bound, and the first matching rule wins.

Sensor components default to a tile-style arrangement with HA names, units and icons. Label overrides update while typing; unit and decimal controls appear when applicable. Weather components offer current conditions or a forecast selection with a condition icon and selectable value.

## Reusable sensor templates

Open **Sensor templates** or choose **Create template…** from a sensor's template picker. Pick a concrete sample entity, then arrange the template components. Save a template to reuse it with comparable binary, numeric, text or weather output. Parts may inherit the sample entity or bind a separate entity.

A sensor template is saved as a reusable design; it is not sent directly to a tag. Switch back to **Display** to apply it to a sensor component and send the complete display.

## Dynamic fields

In Configure, open **Dynamic fields…** to drive colour, icon, text, image, background, position, dimensions, formatting or visibility with HA Jinja templates. The modal provides insertable examples, the resolved field value and a pixel preview. Templates have `value`, `entity`, `entity_id` and `attributes` in addition to standard HA helpers such as `states()`, `is_state()` and `state_attr()`.

For example, a conditional colour can be `{{ 'red' if value | float(0) > 25 else 'black' }}`. Colours must fit the selected tag's palette; a background may resolve to `transparent`.

## Save and send

Save stores the design in HA. Bluetooth Send saves it before transferring; a save failure prevents the transfer. **Auto update sensor**, beside Send, updates the tag when bound entities or template dependencies change. The interval coalesces changes and limits repeated writes. Preview rendering is serialized to avoid overlapping CPU work on small hosts.

Tags whose protocol does not support writes may be previewed but cannot be sent or automatically updated. Existing YAML services continue to work.

## Development checks

Use the repository's Python test environment, then run:

```sh
python -m pytest tests/ -q --timeout=120
npm ci
npx playwright install chromium
DESIGNER_PYTHON=python npm test
```

The browser tests start a local demo using the actual renderer and sample HA states. No real Bluetooth writes are performed.
