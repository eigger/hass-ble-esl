# Layout blueprints

These are Home Assistant automation blueprints. They are separate from the
pixel-placed examples in [`gicisky/`](../gicisky) and [`poshiji/`](../poshiji).

One blueprint is one layout (date, weather), not one resolution. It reads the
resolution from the tag model (`296x128`, `400x300`, …) and shows one of
three arrangements: a short strip (height under 200, such as 2.9"), a
square panel (200–449, such as 4.2"), or a large panel (450 and up, such
as 7.5"). **Text scale** only multiplies that size.

Copy this folder to `config/blueprints/automation/ble_esl/`, then
**Settings → Automations & scenes → Create automation → Blueprint**.

Weather condition text is Home Assistant's translated state. The date
blueprint has no language list: **Date line** and **Second line** are
templates you can replace. Redraw uses a **time pattern** (`0` matches that
value, `/1` matches every hour) with seconds kept at `0`. **Font** is a
file name resolved by the component from its fonts folder or
`config/www/fonts`.
