# Examples

Automation examples are grouped by the tag family they were written for, because
the display resolution (and therefore every `x` / `y` coordinate in the payload)
depends on the device preset.

| Folder | Protocol | Origin |
|--------|----------|--------|
| [`gicisky/`](./gicisky) | PickSmart | Originally from [hass-gicisky](https://github.com/eigger/hass-gicisky) (archived); maintained here. Resolutions: 2.1" 250×128, 2.9" 296×128, 4.2" 400×300, 7.5" 800×480, 10.2" 960×640 |
| [`poshiji/`](./poshiji) | XTE | Poshiji PSJ-420: 400×300 BWRY; color check and weekday Naver weather automation |
| [`zhsunyco/`](./zhsunyco) | WOLINK / easyTag | Zhsunyco-branded tags. No examples yet — contributions welcome |

Examples call `ble_esl.write` or `ble_esl.write_guarded`. To reuse a `gicisky/` example on a Zhsunyco tag,
adjust coordinates for the different resolution (e.g. 2.13" WOLINK is 250×122, not
250×128) and replace `device_id` with your own device.
