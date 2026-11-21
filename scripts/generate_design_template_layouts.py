#!/usr/bin/env python3
"""Regenerate size-specific layouts in the built-in gallery template YAML files."""

from dataclasses import dataclass
from pathlib import Path
import sys

import yaml

DIRECTORY = Path(__file__).resolve().parents[1] / "custom_components/ble_esl/designer/templates"
START = "  # BEGIN GENERATED SIZE LAYOUTS"
END = "  # END GENERATED SIZE LAYOUTS"
FONT = "${font}"
BLACK = "black"
DASH = "—"


def template(expression):
    return "{{ " + expression + " }}"


def tag(statement):
    return "{% " + statement + " %}"


@dataclass
class Layout:
    """Editable ImageSpec elements positioned on a normalized 100 by 100 canvas."""

    width: int
    height: int

    def __post_init__(self):
        self.items = []

    @property
    def square(self):
        return self.width < self.height * 1.25

    @property
    def portrait(self):
        return self.height > self.width * 1.2

    @property
    def detail(self):
        return min(self.width, self.height) >= 480

    @property
    def large(self):
        return max(self.width, self.height) >= 800

    def x(self, value):
        return round(value * self.width / 100)

    def y(self, value):
        return round(value * self.height / 100)

    def size(self, value):
        return max(7, round(value * min(self.width, self.height) / 100))

    def text(self, box, value, size, *, color=BLACK, align="center", lines=1):
        left, top, right, bottom = box
        self.items.append(
            {
                "type": "text_fit",
                "value": value,
                "font": FONT,
                "x": self.x(left),
                "y": self.y(top),
                "width": self.x(right) - self.x(left),
                "height": self.y(bottom) - self.y(top),
                "size": min(self.size(size), self.y(bottom) - self.y(top)),
                "min_size": 7,
                "max_lines": lines,
                "align": align,
                "valign": "middle",
                "fit": "shrink",
                "color": color,
            }
        )

    def icon(self, x, y, value, size, color=BLACK):
        self.items.append(
            {
                "type": "icon",
                "value": value,
                "x": self.x(x),
                "y": self.y(y),
                "size": self.size(size),
                "anchor": "mm",
                "color": color,
            }
        )

    def rule(self, x1, y1, x2, y2, *, width=None, color=BLACK):
        self.items.append(
            {
                "type": "line",
                "x_start": self.x(x1),
                "y_start": self.y(y1),
                "x_end": self.x(x2),
                "y_end": self.y(y2),
                "width": width or max(1, round(min(self.width, self.height) / 320)),
                "fill": color,
            }
        )

    def rectangle(self, box, element_type="rectangle", **fields):
        left, top, right, bottom = box
        self.items.append(
            {
                "type": element_type,
                "x_start": self.x(left),
                "y_start": self.y(top),
                "x_end": self.x(right) - 1,
                "y_end": self.y(bottom) - 1,
                **fields,
            }
        )

    def header(self, value, color=BLACK):
        self.text((5, 3, 95, 17), value, 15, align="left", color=color)
        self.rule(5, 19, 95, 19)

    def row(self, top, bottom, fields):
        """Even-width cells with a divider and optional icon above each value."""
        cell = 90 / len(fields)
        for index, (label, value, glyph) in enumerate(fields):
            left = 5 + cell * index
            right = left + cell
            mid = (left + right) / 2
            if index:
                self.rule(left, top + 2, left, bottom - 2)
            span = bottom - top
            if glyph:
                self.icon(mid, top + span * 0.20, glyph, min(5, span * 0.2))
            self.text((left + 1, top + span * 0.35, right - 1, top + span * 0.63), label, 4.6)
            self.text((left + 1, top + span * 0.66, right - 1, bottom), value, 8)


def values(items, kind="text_fit"):
    return [item["value"] for item in items if item["type"] == kind]


def attribute(entity, name):
    return f"state_attr('${{{entity}}}', {name!r})"


def number_metric(key, unit=None):
    field = attribute("weather", key)
    suffix = f" ~ ' ' ~ ({attribute('weather', unit)} or '')" if unit else " ~ '%'"
    return tag(f"set v = {field}") + template(
        f"(v | float | round(1) | string | regex_replace('[.]0$', '')){suffix}"
        f" if is_number(v) and v is not boolean else '{DASH}'"
    )


def date_layout(layout, base):
    date, weekday = values(base, "text")
    weekend = next(item["color"] for item in base if item.get("value") == weekday)
    if layout.detail:
        layout.text(
            (5, 5, 95, 17),
            template(
                "now().strftime('%Y  ·  ISO W%V' if now().strftime('%G') == now().strftime('%Y') else '%Y  ·  ISO %G-W%V')"
            ),
            9,
        )
        layout.text((5, 20, 95, 48), date, 35)
        layout.text((8, 49, 92, 65), weekday, 19, color=weekend)
        layout.rule(5, 69, 95, 69)
        for index in range(7):
            left = 5 + index * 90 / 7
            right = 5 + (index + 1) * 90 / 7
            prefix = tag(f"set d = now().date() + timedelta(days={index} - now().weekday())")
            color = "${weekend_color}" if index >= 5 else BLACK
            day = (
                tag("set names = '${weekdays}'.split(',')")
                + tag(f"set name = names[{index}] if names | length > {index} else ''")
                + template("name[:-2] if name.endswith('요일') else name[:3]")
            )
            layout.text((left, 72, right, 82), day, 5.5, color=color)
            layout.text((left, 82, right, 94), prefix + template("d.day"), 8, color=color)
            marker = template(f"{color!r} if now().weekday() == {index} else 'white'")
            layout.rule(left + 1.5, 95, right - 1.5, 95, color=marker)
    elif layout.portrait or layout.square:
        layout.text((5, 10, 95, 48), date, 32, lines=2)
        layout.rule(16, 53, 84, 53)
        layout.text((5, 57, 95, 89), weekday, 25, color=weekend)
    else:
        layout.text((5, 5, 95, 53), date, 40)
        layout.text((5, 54, 95, 94), weekday, 35, color=weekend)


def wifi_layout(layout, base):
    title, hint = values(base)
    qr = next(item for item in base if item["type"] == "qrcode")
    if layout.square:
        # A square QR region leaves room above and below for the title and hint.
        size = min(layout.x(82), layout.y(50 if layout.detail else 58))
        x, y = (layout.width - size) // 2, layout.y(18)
        title_box = (5, 2, 95, 17)
        hint_box = (5, 69, 95, 79) if layout.detail else (5, 79, 95, 94)
    else:
        size = min(layout.x(44), layout.y(88))
        x, y = (layout.x(48) - size) // 2, (layout.height - size) // 2
        title_box = (48, 9, 96, 39)
        hint_box = (49, 43, 95, 63 if layout.detail else 88)
    layout.text(title_box, title, 27)
    layout.text(hint_box, hint, 11, lines=2)
    if layout.detail:
        network = template("'${ssid}' if '${hidden}' == 'false' else ''")
        security = template(
            "'Open' if '${security}' == 'nopass' else ('WPA3' if '${security}' == 'SAE' else '${security}')"
        )
        left = 5 if layout.square else 49
        layout.text(
            (left, 79 if layout.square else 69, 95, 89 if layout.square else 86), network, 12
        )
        layout.text((left, 90 if layout.square else 87, 95, 97), security, 7)
    layout.items.append({**qr, "x": x, "y": y, "width": size, "height": size, "border": 4})


def message_layout(layout, base):
    item = base[0]
    limit = 76 if layout.detail else 95
    layout.text((5, 5, 95, limit), item["value"], 100, color=item["color"], lines=item["max_lines"])
    if layout.detail:
        layout.text((7, 80, 93, 94), "${subtitle}", 11, color=item["color"])


def color_layout(layout, _base):
    top = 21 if layout.detail else 7
    bottom = 74 if layout.detail else 94
    columns = 2 if layout.square else 4
    rows = 4 // columns
    if layout.detail:
        layout.header(f"{layout.width} x {layout.height} px")
    for index, (label, ink) in enumerate(
        (("BLACK", BLACK), ("WHITE", "white"), ("RED", "red"), ("YELLOW", "yellow"))
    ):
        column, row = index % columns, index // columns
        left = 4 + column * 92 / columns
        start = top + row * (bottom - top) / rows
        right = left + 92 / columns
        end = start + (bottom - top) / rows
        layout.rectangle((left, start, right - 2, end - 2), fill=ink, outline=BLACK)
        layout.text(
            (left + 1, start, right - 3, end - 2),
            label,
            8,
            color="white" if ink in {BLACK, "red"} else BLACK,
        )
    if layout.detail:
        for index, width in enumerate((1, 2, 4)):
            left = 5 + index * 30
            layout.rule(left, 81, left + 25, 81, width=width)
            layout.text((left, 85, left + 25, 95), f"{width} px", 5)


def calendar_layout(layout, base):
    heading, title, start, location = values(base)
    if layout.detail:
        layout.header(heading, "${accent}")
        layout.text((5, 21, 95, 46), title, 22, align="left", lines=2)
        period = (
            tag(f"set start = as_datetime({attribute('calendar', 'start_time')}, none)")
            + tag(f"set end = as_datetime({attribute('calendar', 'end_time')}, none)")
            + tag(f"set all_day = {attribute('calendar', 'all_day')}")
            + template(
                "start.strftime('${date_format}') ~ ('' if all_day else "
                "' ' ~ start.strftime('${time_format}') ~ "
                "(' - ' ~ end.strftime('${time_format}' if end.date() == start.date() else '${date_format} ${time_format}') "
                "if end and (end.tzinfo is none) == (start.tzinfo is none) and end >= start else '')) if start else ''"
            )
        )
        layout.icon(8, 53, "clock-outline", 6)
        layout.text((14, 48, 95, 58), period, 8, align="left")
        layout.icon(8, 65, "map-marker-outline", 6)
        layout.text((14, 60, 95, 70), location, 8, align="left")
        note = template(f"{attribute('calendar', 'description')} or ''")
        layout.rule(5, 74, 95, 74)
        layout.text((5, 77, 95, 95), note, 6, align="left", lines=3)
    else:
        layout.header(heading, "${accent}")
        layout.text((5, 23, 95, 60), title, 24, align="left", lines=2)
        for top, glyph, value in (
            (64, "clock-outline", start),
            (81, "map-marker-outline", location),
        ):
            layout.icon(9, top + 7, glyph, 10)
            layout.text((17, top, 95, top + 15), value, 11, align="left")


def sensor_layout(layout, base):
    title, value, unit = values(base)
    layout.header(title)
    if layout.square:
        layout.icon(50, 30, "${icon}", 14)
        layout.text((5, 39, 95, 62 if layout.detail else 77), value, 35, color="${color}")
        layout.text((5, 62 if layout.detail else 78, 95, 71 if layout.detail else 95), unit, 12)
    else:
        limit = 70 if layout.detail else 95
        layout.icon(19, (19 + limit) / 2, "${icon}", 27)
        layout.text((33, 22, 76, limit), value, 45, color="${color}", align="right")
        layout.text((78, 22, 95, limit), unit, 14, align="left")
    if layout.detail:
        last = tag("set s = states['${sensor}']") + template(
            "as_local(s.last_updated).strftime('%m/%d %H:%M') if s is not none else ''"
        )
        secondary = tag("set e = '${secondary_sensor}'") + tag(
            "set s = states[e] if e.startswith('sensor.') else none"
        )
        second_name = secondary + template("s.name if s is not none else ''")
        second_value = secondary + template(
            "s.state ~ (' ' ~ s.attributes.unit_of_measurement if s.attributes.unit_of_measurement is defined else '') if s is not none else ''"
        )
        layout.rule(5, 73, 95, 73)
        layout.row(75, 95, (("Updated", last, None), (second_name, second_value, None)))


def print_layout(layout, base):
    title, percentage, status, finish = values(base)
    bar = next(item for item in base if item["type"] == "progress_bar")
    layout.header(title)
    layout.text((5, 22, 95, 56 if layout.detail else 57), percentage, 38, color="${color}")
    layout.rectangle(
        (6, 59, 94, 67),
        "progress_bar",
        **{
            key: bar[key]
            for key in ("progress", "fill", "outline", "background", "show_percentage")
        },
    )
    if layout.detail:
        remaining = (
            tag("set d = as_datetime(states('${end_time}'), none)")
            + tag(
                "set minutes = ((as_timestamp(d) - as_timestamp(now())) / 60) | round(0, 'ceil') | int if d else -1"
            )
            + template(
                "((minutes // 60) ~ 'h ' if minutes >= 60 else '') ~ (minutes % 60) ~ 'm' if minutes >= 0 else '—'"
            )
        )
        layout.row(
            71,
            95,
            (("Status", status, None), ("ETA", finish, None), ("Remaining", remaining, None)),
        )
    elif layout.square:
        layout.text((6, 69, 94, 82), status, 14)
        layout.text((6, 83, 94, 97), finish, 12)
    else:
        layout.text((6, 71, 45, 96), status, 15, align="left")
        layout.text((47, 71, 94, 96), finish, 15, align="right")


def countdown_layout(layout, base):
    title, count, target = values(base)
    color = next(item["color"] for item in base if item.get("value") == count)
    layout.header(title)
    layout.text((5, 22, 95, 66 if layout.detail else 75), count, 46, color=color)
    layout.rule(5, 70 if layout.detail else 77, 95, 70 if layout.detail else 77)
    if layout.detail:
        prefix = tag("set t = strptime('${target}', '%Y-%m-%d', none)")
        weekday = prefix + template("t.strftime('%A') if t else ''")
        span = (
            prefix
            + tag("set n = (t.date() - now().date()).days if t else 0")
            + template(
                "((n | abs) // 7) ~ 'w ' ~ ((n | abs) % 7) ~ 'd' if t and (n | abs) >= 7 else ''"
            )
        )
        layout.row(
            73, 96, (("Target", target, None), ("Weekday", weekday, None), ("Interval", span, None))
        )
    else:
        layout.text((5, 79, 95, 96), target, 15)


def conditions(layout, *, bottom=96):
    layout.row(
        bottom - 27,
        bottom,
        (
            (
                "Feels like",
                number_metric("apparent_temperature", "temperature_unit"),
                "thermometer",
            ),
            ("Humidity", number_metric("humidity"), "water-percent"),
            ("Wind", number_metric("wind_speed", "wind_speed_unit"), "weather-windy"),
        ),
    )


def current_weather_layout(layout, base):
    date, name, temperature, unit, state, humidity, updated = values(base, "text")
    weather_icon = values(base, "icon")[0]
    header_date = date + "  " + updated if layout.detail else date
    if layout.square:
        layout.text((4, 3, 96, 15), name, 12)
        layout.text((4, 16, 96, 25), header_date, 8)
        if layout.detail:
            layout.icon(23, 45, weather_icon, 26)
            layout.text((38, 28, 94, 53), temperature + unit, 29)
            layout.text((38, 54, 94, 66), state, 11)
        else:
            layout.icon(50, 37, weather_icon, 22)
            layout.text((5, 50, 95, 71), temperature + unit, 30)
            layout.text((5, 72, 95, 83), state, 11)
    else:
        layout.text((5, 3, 49, 18), header_date, 12, align="left")
        layout.text((50, 3, 95, 18), name, 13, align="right")
        layout.rule(5, 19, 95, 19)
        layout.icon(21, 48 if layout.detail else 49, weather_icon, 38)
        layout.text((38, 22, 95, 53 if layout.detail else 59), temperature + unit, 41)
        layout.text((38, 54 if layout.detail else 60, 95, 66 if layout.detail else 81), state, 15)
    if layout.detail:
        layout.rule(5, 68, 95, 68)
        conditions(layout)
    else:
        layout.rule(5, 84, 95, 84)
        layout.text((5, 86, 48, 98), humidity, 10, align="left")
        layout.text((51, 86, 95, 98), updated, 10, align="right")


def date_weather_layout(layout, base):
    date, weekday, temperature, state = values(base)
    weather_icon = values(base, "icon")[0]
    weekend = next(item["color"] for item in base if item.get("value") == weekday)
    if layout.square:
        layout.text((5, 6, 95, 22), date, 21, lines=2)
        layout.text((5, 23, 95, 39), weekday, 17, color=weekend)
        layout.rule(8, 40, 92, 40)
        if layout.detail:
            layout.icon(23, 53, weather_icon, 19)
            layout.text((40, 42, 95, 58), temperature, 16)
            layout.text((40, 58, 95, 67), state, 9)
            layout.rule(5, 68, 95, 68)
            conditions(layout)
        else:
            layout.icon(23, 63, weather_icon, 24)
            layout.text((40, 48, 95, 73), temperature, 26)
            layout.text((5, 76, 95, 95), state, 12)

    else:
        limit = 67 if layout.detail else 94
        layout.text((4, 8, 52, limit * 0.63), date, 29)
        layout.text((5, limit * 0.65, 51, limit), weekday, 24, color=weekend)
        layout.rule(53, 10, 53, limit)
        layout.icon(65, limit * 0.46, weather_icon, 26)
        layout.text((75, 9, 97, limit * 0.65), temperature, 27)
        layout.text((56, limit * 0.65, 99, limit), state, 13)
        if layout.detail:
            layout.rule(5, 68, 95, 68)
            conditions(layout)


def forecast_layout(layout, base):
    # Reuse the existing forecast parsing, condition mapping and fallbacks.
    day, high, low = values(base, "text")[:3]
    glyph = values(base, "icon")[0]
    indices = range(7) if layout.large else range(1, 6 if layout.detail else 4)
    if layout.detail:
        layout.text((5, 3, 48, 16), f"{len(indices)}-day forecast", 12, align="left")
        layout.text((49, 4, 95, 16), "Low / High  ·  Precip.", 7, align="right")
        layout.rule(5, 18, 95, 18)
    low_result = low.split("{{", 1)[1].split("}}", 1)[0].strip()
    high_result = high.split("{{", 1)[1].split("}}", 1)[0].strip()
    prefix = low.split("{{", 1)[0]
    temperature_pair = prefix + template(f"({low_result}) ~ '° / ' ~ ({high_result}) ~ '°'")
    chance = (
        prefix
        + tag("set probability = d.precipitation_probability | default(none)")
        + template(
            "'%d%%' | format(probability | round(0) | int) if is_number(probability) and probability is not boolean else '—'"
        )
    )
    for index, day_index in enumerate(indices):

        def field(value, slot=day_index):
            return value.replace("f[1]", f"f[{slot}]").replace("length > 1", f"length > {slot}")

        if layout.square:
            top = (21 if layout.detail else 5) + index * (72 if layout.detail else 90) / len(
                indices
            )
            bottom = top + (72 if layout.detail else 90) / len(indices)
            mid = (top + bottom) / 2
            if index:
                layout.rule(5, top, 95, top)
            layout.text((5, top, 24, bottom), field(day), 9)
            layout.icon(34, mid, field(glyph), min(17, 54 / len(indices)))
            if layout.detail:
                layout.text((43, top, 71, bottom), field(temperature_pair), 9)
                layout.text((72, top, 95, bottom), field(chance), 8)
            else:
                layout.text((43, top, 68, bottom), field(high), 12)
                layout.text((70, top, 95, bottom), field(low), 10)
        else:
            left = 5 + index * 90 / len(indices)
            right = 5 + (index + 1) * 90 / len(indices)
            top = 20 if layout.detail else 3
            if index:
                layout.rule(left, top + 2, left, 95)
            layout.text((left, top, right, top + 14), field(day), 9)
            glyph_size = min(
                20, (right - left) * layout.width / min(layout.width, layout.height) * 0.70
            )
            layout.icon((left + right) / 2, 46, field(glyph), glyph_size)
            if layout.detail:
                layout.text((left + 0.6, 62, right - 0.6, 78), field(temperature_pair), 10)
                layout.text((left, 80, right, 95), field(chance), 8)
            else:
                layout.text((left, 63, right, 82), field(high), 15)
                layout.text((left, 82, right, 96), field(low), 10)


BUILDERS = {
    "calendar_next": calendar_layout,
    "color_check": color_layout,
    "countdown": countdown_layout,
    "date": date_layout,
    "date_weather": date_weather_layout,
    "message": message_layout,
    "print_progress": print_layout,
    "sensor_card": sensor_layout,
    "weather_now": current_weather_layout,
    "weather_forecast": forecast_layout,
    "wifi": wifi_layout,
}


class FlowElement(dict):
    """Write each generated editable item in YAML flow style."""


class ElementDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return not (isinstance(data, str) and len(data) > 180 and "{{" in data)

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, indentless=False)

    def represent_element(self, element):
        return self.represent_mapping("tag:yaml.org,2002:map", element, flow_style=True)


ElementDumper.add_representer(FlowElement, ElementDumper.represent_element)


def generate(path, sizes):
    original = path.read_text(encoding="utf-8")
    head, marker, tail = original.partition(START)
    # Parameter blocks go before layouts and are regenerated independently.
    original = head.rstrip() + tail.partition(END)[2] if marker else original
    if "  # BEGIN SIZE PARAMETERS\n" in original:
        prefix, _, rest = original.partition("  # BEGIN SIZE PARAMETERS\n")
        original = prefix + rest.partition("  # END SIZE PARAMETERS\n")[2]
    data = yaml.safe_load(original)
    base_key = "400x300" if data["id"] == "weather_now" else "250x128"
    base = data["layouts"][base_key]
    builder = BUILDERS[data["id"]]
    layouts = {}
    for size in sizes:
        if size in data["layouts"]:
            continue
        width, height = map(int, size.split("x"))
        layout = Layout(width, height)
        builder(layout, base)
        layouts[size] = [
            FlowElement(
                {
                    key: sys.intern(value) if isinstance(value, str) else value
                    for key, value in item.items()
                }
            )
            for item in layout.items
        ]
    generated = yaml.dump(
        layouts, Dumper=ElementDumper, sort_keys=False, allow_unicode=True, width=6000
    )
    generated = "\n".join((START, *("  " + line for line in generated.splitlines()), END))

    before, separator, after = original.partition("\nautomation:")
    source = before.rstrip() + "\n" + generated + "\n"
    if separator:
        source += "\nautomation:" + after
    params = {
        "message": ("subtitle", "Second line on larger tags", "큰 화면의 보조 문구"),
        "sensor_card": (
            "secondary_sensor",
            "Secondary sensor ID on larger tags",
            "큰 화면의 보조 센서 ID",
        ),
    }
    if data["id"] in params:
        name, english, korean = params[data["id"]]
        parameter = (
            "  # BEGIN SIZE PARAMETERS\n"
            f"  {name}:\n"
            "    type: string\n"
            '    default: ""\n'
            f"    label: {{ en: {english}, ko: {korean} }}\n"
            "  # END SIZE PARAMETERS"
        )
        source = source.replace("\nlayouts:", parameter + "\n\nlayouts:", 1)
    if len(source.encode()) >= 256 * 1024:
        raise ValueError(f"{path.name} exceeds the gallery template size limit")
    return source


if __name__ == "__main__":
    sizes = yaml.safe_load((DIRECTORY / "weather_outdoor.yaml").read_text(encoding="utf-8"))[
        "layouts"
    ]
    for path in sorted(DIRECTORY.glob("*.yaml")):
        if path.name != "weather_outdoor.yaml":
            path.write_text(generate(path, sizes), encoding="utf-8")
