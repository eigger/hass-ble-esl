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
| [`blueprints/`](./blueprints) | any | Date, weather, and presence layouts. Each file branches on the tag height. Copy into `config/blueprints/automation/ble_esl/`. |

Examples call `ble_esl.write` or `ble_esl.write_guarded`; replace `device_id` with
your own device. A 4.2" (400×300) example runs unchanged on a Gicisky or Poshiji tag.
For a different resolution (e.g. 2.13" WOLINK is 250×122, not 250×128), adjust
the coordinates.

## All examples

| Size | Brand | Example | Preview | YAML |
|------|-------|---------|---------|------|
| 2.1" (250×128) | Gicisky | Date | ![2.1-date.jpg](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/2.1-date.jpg) | [2.1-date.yaml](./gicisky/2.1-date.yaml) |
| 2.1" (250×128) | Gicisky | Naver Weather | ![2.1-naver-weather.jpg](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/2.1-naver-weather.jpg) | [2.1-naver-weather.yaml](./gicisky/2.1-naver-weather.yaml) |
| 2.1" (250×128) | Gicisky | Waste Collection | ![2.1-waste-collection.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/2.1-waste-collection.png) | [2.1-waste-collection.yaml](./gicisky/2.1-waste-collection.yaml) |
| 2.1" (250×128) | Gicisky | Wifi | ![2.1-wifi.jpg](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/2.1-wifi.jpg) | [2.1-wifi.yaml](./gicisky/2.1-wifi.yaml) |
| 2.1" (250×128) | Gicisky | TMap time | ![2.1-tmap-time.jpg](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/2.1-tmap-time.jpg) | [2.1-tmap-time.yaml](./gicisky/2.1-tmap-time.yaml) |
| 2.9" (296×128) | Gicisky | Google Calendar | ![2.9-google-calendar.jpg](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/2.9-google-calendar.jpg) | [2.9-google-calendar.yaml](./gicisky/2.9-google-calendar.yaml) |
| 2.9" (296×128) | Gicisky | Presence Display | ![2.9-presence-display.jpg](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/2.9-presence-display.jpg) | [2.9-presence-display.yaml](./gicisky/2.9-presence-display.yaml) |
| 4.2" (400×300) | Gicisky | Image | ![4.2-image.jpg](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/4.2-image.jpg) | [4.2-image.yaml](./gicisky/4.2-image.yaml) |
| 4.2" (400×300) | Gicisky | 기상청 Weather | ![4.2-kma-weather.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/4.2-kma-weather.png) | [4.2-kma-weather.yaml](./gicisky/4.2-kma-weather.yaml) |
| 4.2" (400×300) | Gicisky | Naver Weather | ![4.2-naver-weather.jpg](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/4.2-naver-weather.jpg) | [4.2-naver-weather.yaml](./gicisky/4.2-naver-weather.yaml) |
| 4.2" (400×300) | Gicisky | Date Weather | ![4.2-date-weather.jpg](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/4.2-date-weather.jpg) | [4.2-date-weather.yaml](./gicisky/4.2-date-weather.yaml) |
| 4.2" (400×300) | Gicisky | Weather News | ![4.2-weather-news.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/4.2-weather-news.png) | [4.2-weather-news.yaml](./gicisky/4.2-weather-news.yaml) |
| 4.2" (400×300) | Gicisky | 3D Print | ![4.2-3d-print.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/4.2-3d-print.png) | [4.2-3d-print.yaml](./gicisky/4.2-3d-print.yaml) |
| 4.2" (400×300) | Poshiji | Four-color check | ![psj420-color-test.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/poshiji/psj420-color-test.png) | [psj420-color-test.yaml](./poshiji/psj420-color-test.yaml) |
| 4.2" (400×300) | Poshiji | Naver Weather | ![poshiji_psj420_4color.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/docs/images/poshiji/poshiji_psj420_4color.png) | [psj420-weather-demo.yaml](./poshiji/psj420-weather-demo.yaml) |
| 7.5" (800×480) | Gicisky | Google Calendar | ![7.5-google-calendar.jpg](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/7.5-google-calendar.jpg) | [7.5-google-calendar.yaml](./gicisky/7.5-google-calendar.yaml) |
| 7.5" (800×480) | Gicisky | Google Calendar 2 | ![7.5-google-calender2.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/7.5-google-calender2.png) | [7.5-google-calender2.yaml](./gicisky/7.5-google-calender2.yaml) |
| 7.5" (800×480) | Gicisky | Google Calendar 3 | ![7.5-google-calender3.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/7.5-google-calender3.png) | [7.5-google-calender3.yaml](./gicisky/7.5-google-calender3.yaml) |
| 7.5" (800×480) | Gicisky | Date Weather | ![7.5-date-weather.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/7.5-date-weather.png) | [7.5-date-weather.yaml](./gicisky/7.5-date-weather.yaml) |
| 7.5" (800×480) | Gicisky | Date Weather 2 | ![7.5-date-weather2.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/7.5-date-weather2.png) | [7.5-date-weather2.yaml](./gicisky/7.5-date-weather2.yaml) |
| 7.5" (800×480) | Gicisky | Calendar Weather | ![7.5-calendar-weather.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/7.5-calendar-weather.png) | [7.5-calendar-weather.yaml](./gicisky/7.5-calendar-weather.yaml) |
| 7.5" (800×480) | Gicisky | Image | ![7.5-image.jpg](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/7.5-image.jpg) | [7.5-image.yaml](./gicisky/7.5-image.yaml) |
| 10.2" (960×640) | Gicisky | Calendar Weather | ![10.2-calendar-weather.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/10.2-calendar-weather.png) | [10.2-calendar-weather.yaml](./gicisky/10.2-calendar-weather.yaml) |
| 10.2" (960×640) | Gicisky | Calendar Weather 2 | ![10.2-calendar-weather2.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/10.2-calendar-weather2.png) | [10.2-calendar-weather2.yaml](./gicisky/10.2-calendar-weather2.yaml) |
| 10.2" (960×640) | Gicisky | Calendar | ![10.2-calendar.png](https://raw.githubusercontent.com/eigger/hass-ble-esl/main/examples/gicisky/10.2-calendar.png) | [10.2-calendar.yaml](./gicisky/10.2-calendar.yaml) |

## Recipes

### T-Map integration

```yaml
# https://openapi.sk.com/products/detail?linkMenuSeq=46
rest_command:
  request_tmap_routes:
    url: https://apis.openapi.sk.com/tmap/routes?version=1
    method: POST
    headers:
      appKey: !secret tmap_api_key
      accept: "application/json, text/html"
    content_type: "application/json; charset=utf-8"
    payload: >-
      {
        "startX": {{ startX }},
        "startY": {{ startY }},
        "endX": {{ endX }},
        "endY": {{ endY }},
        "searchOption": {{ searchOption }},
        "totalValue": 2,
        "trafficInfo ": "Y",
        "mainRoadInfo": "Y"
      }
```

See [2.1-tmap-time.yaml](./gicisky/2.1-tmap-time.yaml) for a full label example.

### Google Calendar

Add a remote calendar: **Settings** → **Devices & Services** → **Calendar** → add Google `*.ics` URL.

### Third-party custom components

- [기상청 APIhub (eigger)](https://github.com/eigger/hass-kma)
- [Naver Weather (minumida)](https://github.com/miumida/naver_weather)
- [ha-weathernews (dugurs)](https://github.com/dugurs/ha-weathernews)
- [Waste Collection Schedule (mampfes)](https://github.com/mampfes/hacs_waste_collection_schedule)
