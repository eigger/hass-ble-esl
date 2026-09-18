# Examples

Payloads are resolution-specific, not tag-specific: an example works on any
supported tag with the same resolution, regardless of brand or protocol. Folders
only record which tag family each example was originally written and
photographed on.

| Folder | Protocol | Origin |
|--------|----------|--------|
| [`gicisky/`](./gicisky) | PickSmart | Originally from [hass-gicisky](https://github.com/eigger/hass-gicisky) (archived); maintained here. Resolutions: 2.1" 250×128, 2.9" 296×128, 4.2" 400×300, 7.5" 800×480, 10.2" 960×640 |
| [`poshiji/`](./poshiji) | XTE | Poshiji PSJ-420: 400×300 BWRY; color check and weekday Naver weather automation |
| [`zhsunyco/`](./zhsunyco) | WOLINK / easyTag | Zhsunyco-branded tags. No examples yet — contributions welcome |

Examples call `ble_esl.write` or `ble_esl.write_guarded`; replace `device_id` with
your own device. A 4.2" (400×300) example runs unchanged on a Gicisky or Poshiji tag.
For a different resolution (e.g. 2.13" WOLINK is 250×122, not 250×128), adjust
the coordinates.
