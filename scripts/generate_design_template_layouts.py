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
    def medium(self):
        return min(self.width, self.height) >= 300

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

    def fit(self, x, y, width, height, value, size, *, align="center", color=BLACK, min_size=None):
        """A one-line text box in pixels that shrinks to fit instead of clipping."""
        self.items.append(
            {
                "type": "text_fit",
                "value": value,
                "font": FONT,
                "x": round(x),
                "y": round(y),
                "width": max(1, round(width)),
                "height": max(1, round(height)),
                "size": max(7, round(size)),
                "min_size": max(7, round(min_size if min_size is not None else size * 0.6)),
                "max_lines": 1,
                "align": align,
                "valign": "middle",
                "fit": "shrink",
                "color": color,
            }
        )

    def glyph(self, x, y, value, size, *, color=BLACK):
        """An icon centred on a pixel position."""
        self.items.append(
            {
                "type": "icon",
                "value": value,
                "x": round(x),
                "y": round(y),
                "size": max(8, round(size)),
                "anchor": "mm",
                "color": color,
            }
        )

    def stroke(self, x1, y1, x2, y2, width=1, color=BLACK):
        self.items.append(
            {
                "type": "line",
                "x_start": round(x1),
                "y_start": round(y1),
                "x_end": round(x2),
                "y_end": round(y2),
                "width": max(1, round(width)),
                "fill": color,
            }
        )

    def block(self, x1, y1, x2, y2, *, fill, outline=None, radius=0):
        item = {
            "type": "rectangle",
            "x_start": round(x1),
            "y_start": round(y1),
            "x_end": round(x2),
            "y_end": round(y2),
            "fill": fill,
            "outline": outline or fill,
        }
        if radius:
            item["radius"] = round(radius)
        self.items.append(item)

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
    if layout.detail or layout.medium:
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
        ev_prefix = tag(
            "set _evs = events['${calendar}'].events | default([], true) "
            "if events is defined and events['${calendar}'] is defined else []"
        )
        title_expr = title.split("{{", 1)[1].rsplit("}}", 1)[0].strip()
        loc_expr = location.split("{{", 1)[1].rsplit("}}", 1)[0].strip()
        layout.text(
            (5, 21, 95, 46),
            ev_prefix
            + template(
                f"(_evs[0].summary | default('${{empty_text}}', true)) if _evs else ({title_expr})"
            ),
            22,
            align="left",
            lines=2,
        )
        ev_period = (
            tag("set _sr = (_evs[0].start | default('')) | string")
            + tag("set _er = (_evs[0].end | default('')) | string")
            + tag("set _sd = as_datetime(_sr, none)")
            + tag("set _ed = as_datetime(_er, none)")
            + tag(
                "if _sd is not none and _sd.tzinfo is not none %}{% set _sd = as_local(_sd) %}{% endif"
            )
            + tag(
                "if _ed is not none and _ed.tzinfo is not none %}{% set _ed = as_local(_ed) %}{% endif"
            )
        )
        period = (
            ev_prefix
            + tag("if _evs")
            + ev_period
            + template(
                "_sd.strftime('${date_format}' if _sr | length == 10 else '${date_format} ${time_format}') "
                "~ ((' - ' ~ (_ed - timedelta(days=1)).strftime('${date_format}')) "
                "if _sr | length == 10 and _er | length == 10 and _ed is not none and (_ed.tzinfo is none) == (_sd.tzinfo is none) and _ed.date() > _sd.date() + timedelta(days=1) "
                "else (' - ' ~ _ed.strftime('${time_format}' if _ed.date() == _sd.date() else '${date_format} ${time_format}') "
                "if _ed is not none and (_ed.tzinfo is none) == (_sd.tzinfo is none) and _ed >= _sd and _sr | length > 10 else '')) "
                "if _sd is not none else ''"
            )
            + tag("else")
            + tag(f"set start = as_datetime({attribute('calendar', 'start_time')}, none)")
            + tag(f"set end = as_datetime({attribute('calendar', 'end_time')}, none)")
            + tag(f"set all_day = {attribute('calendar', 'all_day')}")
            + template(
                "start.strftime('${date_format}') ~ ('' if all_day else "
                "' ' ~ start.strftime('${time_format}') ~ "
                "(' - ' ~ end.strftime('${time_format}' if end.date() == start.date() else '${date_format} ${time_format}') "
                "if end and (end.tzinfo is none) == (start.tzinfo is none) and end >= start else '')) if start else ''"
            )
            + tag("endif")
        )
        layout.icon(8, 53, "clock-outline", 6)
        layout.text((14, 48, 95, 58), period, 8, align="left")
        layout.icon(8, 65, "map-marker-outline", 6)
        layout.text(
            (14, 60, 95, 70),
            ev_prefix
            + template(f"(_evs[0].location | default('', true)) if _evs else ({loc_expr})"),
            8,
            align="left",
        )

        def upcoming_slot(index):
            return (
                ev_prefix
                + tag(f"if _evs | length > {index}")
                + tag(f"set _ev = _evs[{index}]")
                + tag("set _sr = (_ev.start | default('')) | string")
                + tag("set _dt = as_datetime(_sr, none)")
                + tag(
                    "if _dt is not none and _dt.tzinfo is not none %}{% set _dt = as_local(_dt) %}{% endif"
                )
                + tag(
                    "set _when = _dt.strftime('${date_format}' if _sr | length == 10 else '${date_format} ${time_format}') "
                    "if _dt is not none else ''"
                )
                + template("(_when ~ '  ' if _when else '') ~ (_ev.summary | default('', true))")
                + tag("endif")
            )

        slot_one = (
            ev_prefix
            + tag("if _evs | length > 1")
            + upcoming_slot(1).removeprefix(ev_prefix)
            + tag("elif _evs")
            + template("_evs[0].description | default('', true)")
            + tag("else")
            + template(f"{attribute('calendar', 'description')} or ''")
            + tag("endif")
        )
        layout.rule(5, 74, 95, 74)
        layout.text((5, 76, 95, 85), slot_one, 6.5, align="left", lines=1)
        layout.text((5, 87, 95, 96), upcoming_slot(2), 6.5, align="left", lines=1)
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
    value_color = next(item["color"] for item in base if item.get("value") == value)
    layout.header(title)
    if layout.square:
        layout.icon(50, 30, "${icon}", 14)
        layout.text((5, 39, 95, 62 if layout.detail else 77), value, 35, color=value_color)
        layout.text((5, 62 if layout.detail else 78, 95, 71 if layout.detail else 95), unit, 12)
    else:
        limit = 70 if layout.detail else 95
        layout.icon(19, (19 + limit) / 2, "${icon}", 27)
        layout.text((33, 22, 76, limit), value, 45, color=value_color, align="right")
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
        temps = (
            tag("set _ns = '${nozzle_sensor}'")
            + tag("set _bs = '${bed_sensor}'")
            + tag("set _nr = states(_ns) if _ns.startswith('sensor.') else ''")
            + tag("set _br = states(_bs) if _bs.startswith('sensor.') else ''")
            + tag("set _nt = (_nr | float | round(0) | int ~ '°') if is_number(_nr) else '—'")
            + tag("set _bt = (_br | float | round(0) | int ~ '°') if is_number(_br) else '—'")
            + template(
                "_nt ~ ' / ' ~ _bt if (_ns.startswith('sensor.') or _bs.startswith('sensor.')) else '—'"
            )
        )
        layout.row(
            71,
            95,
            (
                ("Status", status, None),
                ("ETA", finish, None),
                ("Remaining", remaining, None),
                ("Nozzle / Bed", temps, None),
            ),
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


ACCENT_INK = "{{ 'black' if '${accent}' in ('yellow', 'white') else '${accent}' }}"
CONDITION_ICON = (
    "weather-{{ {'clear-night': 'night', 'exceptional': 'sunny-alert', 'partlycloudy': "
    "'partly-cloudy', 'unknown': 'cloudy-alert', 'unavailable': 'cloudy-alert'}"
    ".get(states('${weather}'), states('${weather}')) }}"
)


def whole_degrees(variable):
    return (
        f"((({variable} | float | round(0) | int) ~ '°') "
        f"if is_number({variable}) and {variable} is not boolean else '{DASH}')"
    )


def current_value(name):
    """Jinja for one weather entity attribute, as it reads on the tag."""
    if name == "temperature":
        return (
            tag(f"set t = {attribute('weather', 'temperature')}")
            + tag(
                "set r = t | round(0) | int if t is number and t is not boolean "
                "and t == t and t | abs < 100000 else none"
            )
            + template(f"'{DASH}' if r is none else r ~ '°'")
        )
    if name == "feels":
        return tag(f"set v = {attribute('weather', 'apparent_temperature')}") + template(
            whole_degrees("v")
        )
    if name == "humidity":
        return number_metric("humidity")
    if name == "wind":
        unit = f"({attribute('weather', 'wind_speed_unit')} or '')"
        return tag(f"set v = {attribute('weather', 'wind_speed')}") + template(
            f"((v | float | round(1) | string | regex_replace('[.]0$', '')) ~ {unit}) "
            f"if is_number(v) and v is not boolean else '{DASH}'"
        )
    if name == "location":
        return template(f"{attribute('weather', 'friendly_name')} or ''")
    if name == "date":
        return template("now().strftime('${date_format}')")
    if name == "time":
        return template("now().strftime('%H:%M')")
    if name == "footer":
        return tag(f"set n = {attribute('weather', 'friendly_name')} or ''") + template(
            "(n ~ ' · ' if n else '') ~ now().strftime('${date_format}')"
        )
    if name == "state":
        return template("state_translated('${weather}')")
    raise KeyError(name)


def today_value(name):
    """Today's forecast for the weather entity, or a dash while no forecast was fetched."""
    entity = "'${weather}'"
    row = (
        tag(
            f"set f = fc[{entity}].forecast | default([], true) "
            f"if fc is defined and fc[{entity}] is defined else []"
        )
        + tag("set n = namespace(r={}, dated=false)")
        + tag("for i in f")
        + tag("set t = as_datetime(i.datetime | default(none), none)")
        + tag("if t is not none")
        + tag("set n.dated = true")
        + tag("if as_local(t).date() == now().date()")
        + tag("set n.r = i")
        + tag("break")
        + tag("endif")
        + tag("endif")
        + tag("endfor")
        + tag("if not n.dated and f | length > 0")
        + tag("set n.r = f[0]")
        + tag("endif")
        + tag("set row = n.r")
    )
    field = {
        "high": "temperature",
        "low": "templow",
        "chance": "precipitation_probability",
    }[name]
    unit = "%" if name == "chance" else "°"
    return (
        row
        + tag(f"set v = row.{field} | default(none)")
        + template(
            f"((v | float | round(0) | int) ~ '{unit}') "
            f"if is_number(v) and v is not boolean else '{DASH}'"
        )
    )


READINGS = (
    ("thermometer", "feels", "Feels like"),
    ("water-percent", "humidity", "Humidity"),
    ("weather-windy", "wind", "Wind"),
)


def landscape_now(layout):
    """Header bar, big temperature next to the condition icon and three readings."""
    width, height = layout.width, layout.height
    sx, sy = width / 400, height / 300
    s = min(sx, sy)

    def X(value):
        return value * sx

    def Y(value):
        return value * sy

    def S(value):
        return value * s

    value = current_value
    layout.block(0, 0, width - 1, Y(38) - 1, fill=BLACK)
    layout.glyph(S(20), Y(19), "map-marker", S(20), color="white")
    layout.fit(
        S(34),
        Y(19) - S(15),
        X(250) - S(34),
        S(30),
        value("location"),
        S(18),
        align="left",
        color="white",
    )
    layout.fit(
        X(256),
        Y(19) - S(15),
        width - S(14) - X(256),
        S(30),
        value("date"),
        S(17),
        align="right",
        color="white",
    )
    layout.glyph(X(90), Y(124), CONDITION_ICON, S(120))
    layout.fit(
        X(172),
        Y(90) - S(64),
        width - S(12) - X(172),
        S(128),
        value("temperature"),
        S(88),
        align="right",
    )
    layout.fit(
        X(172),
        Y(161) - S(17),
        width - S(14) - X(172),
        S(34),
        value("state"),
        S(22),
        align="right",
        min_size=S(16),
    )
    layout.glyph(X(286), Y(191), "arrow-up-thin", S(20), color=ACCENT_INK)
    layout.fit(
        X(298),
        Y(191) - S(14),
        X(40),
        S(28),
        today_value("high"),
        S(19),
        align="left",
        color=ACCENT_INK,
        min_size=S(16),
    )
    layout.glyph(X(348), Y(191), "arrow-down-thin", S(20))
    layout.fit(
        X(360),
        Y(191) - S(14),
        width - S(10) - X(360),
        S(28),
        today_value("low"),
        S(19),
        align="left",
        min_size=S(16),
    )
    layout.stroke(S(14), Y(212), width - S(14), Y(212), S(2))
    cell = (width - 2 * S(14)) / 3
    for index, (glyph, key, label) in enumerate(READINGS):
        left = S(14) + index * cell
        if index:
            layout.stroke(left, Y(226), left, Y(288))
        layout.glyph(left + S(26), Y(248), glyph, S(26))
        layout.fit(
            left + S(46),
            Y(248) - S(16),
            cell - S(52),
            S(32),
            value(key),
            S(26),
            align="left",
            min_size=S(17),
        )
        layout.fit(left + S(46), Y(279) - S(11), cell - S(52), S(22), label, S(16), align="left")


def portrait_now(layout):
    """The same design stacked for tall tags."""
    width, height = layout.width, layout.height
    sx, sy = width / 300, height / 400
    s = max(1, min(sx, sy))

    def X(value):
        return value * sx

    def Y(value):
        return value * sy

    def S(value):
        return value * s

    value = current_value
    layout.block(0, 0, width - 1, Y(36) - 1, fill=BLACK)
    layout.glyph(S(18), Y(18), "map-marker", S(20), color="white")
    layout.fit(
        S(32),
        Y(18) - S(15),
        X(160) - S(32),
        S(30),
        value("location"),
        S(17),
        align="left",
        color="white",
    )
    layout.fit(
        X(166),
        Y(18) - S(15),
        width - S(12) - X(166),
        S(30),
        value("date"),
        S(16),
        align="right",
        color="white",
    )
    layout.glyph(X(150), Y(100), CONDITION_ICON, S(112))
    layout.fit(S(12), Y(184) - S(46), width - 2 * S(12), S(92), value("temperature"), S(80))
    layout.fit(
        S(12), Y(238) - S(16), width - 2 * S(12), S(32), value("state"), S(22), min_size=S(16)
    )
    layout.glyph(X(96), Y(270), "arrow-up-thin", S(20), color=ACCENT_INK)
    layout.fit(
        X(108),
        Y(270) - S(14),
        X(48),
        S(28),
        today_value("high"),
        S(19),
        align="left",
        color=ACCENT_INK,
        min_size=S(16),
    )
    layout.glyph(X(176), Y(270), "arrow-down-thin", S(20))
    layout.fit(
        X(188),
        Y(270) - S(14),
        X(48),
        S(28),
        today_value("low"),
        S(19),
        align="left",
        min_size=S(16),
    )
    layout.stroke(S(14), Y(296), width - S(14), Y(296), S(2))
    cell = (width - 2 * S(8)) / 3
    for index, (glyph, key, label) in enumerate(READINGS):
        left = S(8) + index * cell
        if index:
            layout.stroke(left, Y(310), left, Y(388))
        layout.glyph(left + cell / 2, Y(330), glyph, S(26))
        layout.fit(
            left + S(4), Y(356) - S(14), cell - S(8), S(28), value(key), S(20), min_size=S(16)
        )
        layout.fit(left + S(4), Y(380) - S(11), cell - S(8), S(22), label, S(16))


def compact_now(layout):
    """Wide, short tags: icon, big temperature, condition, high/low and a footer bar."""
    width, height = layout.width, layout.height
    s = min(width / 296, height / 128)
    footer = round(26 * s)
    sx = width / 296
    sy = (height - footer) / 102

    def X(value):
        return value * sx

    def Y(value):
        return value * sy

    def S(value):
        return value * s

    value = current_value
    top = height - footer
    layout.block(0, top, width - 1, height - 1, fill=BLACK)
    layout.fit(
        S(10),
        top,
        X(206),
        footer,
        value("footer"),
        S(15),
        align="left",
        color="white",
        min_size=14,
    )
    layout.fit(
        X(222),
        top,
        width - S(10) - X(222),
        footer,
        value("time"),
        S(14),
        align="right",
        color="white",
    )
    layout.glyph(X(44), Y(60), CONDITION_ICON, S(72))
    layout.fit(X(84), Y(42) - S(40), X(108), S(80), value("temperature"), S(64))
    layout.fit(
        X(194),
        Y(25) - S(15),
        width - S(10) - X(194),
        S(30),
        value("state"),
        S(20),
        align="right",
        min_size=14,
    )
    layout.glyph(X(203), Y(56), "arrow-up-thin", S(18), color=ACCENT_INK)
    layout.fit(
        X(213),
        Y(56) - S(13),
        X(33),
        S(26),
        today_value("high"),
        S(17),
        align="left",
        color=ACCENT_INK,
        min_size=14,
    )
    layout.glyph(X(257), Y(56), "arrow-down-thin", S(18))
    layout.fit(
        X(267),
        Y(56) - S(13),
        width - S(6) - X(267),
        S(26),
        today_value("low"),
        S(17),
        align="left",
        min_size=14,
    )
    layout.glyph(X(226), Y(86), "umbrella", S(16))
    layout.fit(
        X(236),
        Y(86) - S(12),
        width - S(10) - X(236),
        S(24),
        today_value("chance"),
        S(16),
        align="left",
        min_size=14,
    )


def small_wide_now(layout):
    """Under 296 wide: icon and temperature, with condition and high/low stacked beside them."""
    width, height = layout.width, layout.height
    value = current_value
    footer = 26
    body = height - footer
    layout.block(0, body, width - 1, height - 1, fill=BLACK)
    layout.fit(
        6,
        body,
        width * 0.62,
        footer,
        value("footer"),
        15,
        align="left",
        color="white",
        min_size=14,
    )
    layout.fit(
        width * 0.62 + 8,
        body,
        width - width * 0.62 - 14,
        footer,
        value("time"),
        14,
        align="right",
        color="white",
    )
    icon = min(body * 0.62, width * 0.27)
    layout.glyph(6 + icon / 2, body / 2, CONDITION_ICON, icon)
    split = 6 + icon + 2
    column = width * 0.60
    layout.fit(
        split,
        body / 2 - body * 0.36,
        column - split,
        body * 0.72,
        value("temperature"),
        min(body * 0.58, 56),
    )
    rows = (body * 0.22, body * 0.5, body * 0.78)
    layout.fit(
        column + 2,
        rows[0] - 11,
        width - column - 8,
        22,
        value("state"),
        16,
        align="left",
        min_size=14,
    )
    for centre, glyph, key, color in (
        (rows[1], "arrow-up-thin", "high", ACCENT_INK),
        (rows[2], "arrow-down-thin", "low", BLACK),
    ):
        layout.glyph(column + 12, centre, glyph, 20, color=color)
        layout.fit(
            column + 26,
            centre - 11,
            width - column - 32,
            22,
            today_value(key),
            18,
            align="left",
            color=color,
            min_size=14,
        )


def tiny_now(layout):
    """The smallest portrait tags: icon, temperature and today's high and low."""
    width, height = layout.width, layout.height
    value = current_value
    icon = min(width * 0.62, height * 0.27)
    layout.glyph(width / 2, height * 0.17, CONDITION_ICON, icon)
    layout.fit(
        2,
        height * 0.33,
        width - 4,
        height * 0.2,
        value("temperature"),
        min(height * 0.17, width * 0.4),
    )
    for centre, glyph, key, color in (
        (height * 0.67, "arrow-up-thin", "high", ACCENT_INK),
        (height * 0.83, "arrow-down-thin", "low", BLACK),
    ):
        layout.glyph(width * 0.24, centre, glyph, 20, color=color)
        layout.fit(
            width * 0.24 + 12,
            centre - 14,
            width * 0.76 - 16,
            28,
            today_value(key),
            20,
            align="left",
            color=color,
            min_size=14,
        )


def square_now(layout):
    """200x200: icon beside the temperature, condition, high/low and a footer bar."""
    width, height = layout.width, layout.height
    value = current_value
    footer = 28
    top = height - footer
    layout.block(0, top, width - 1, height - 1, fill=BLACK)
    layout.fit(
        8, top, width * 0.62, footer, value("footer"), 15, align="left", color="white", min_size=14
    )
    layout.fit(
        width * 0.62 + 10,
        top,
        width * 0.38 - 18,
        footer,
        value("time"),
        14,
        align="right",
        color="white",
    )
    layout.glyph(width * 0.23, height * 0.27, CONDITION_ICON, width * 0.34)
    layout.fit(width * 0.42, height * 0.07, width * 0.55, height * 0.4, value("temperature"), 60)
    layout.fit(8, height * 0.5, width - 16, 30, value("state"), 22, min_size=16)
    centre = height * 0.74
    layout.glyph(width * 0.2, centre, "arrow-up-thin", 24, color=ACCENT_INK)
    layout.fit(
        width * 0.2 + 14,
        centre - 16,
        width * 0.3 - 8,
        32,
        today_value("high"),
        24,
        align="left",
        color=ACCENT_INK,
        min_size=16,
    )
    layout.glyph(width * 0.6, centre, "arrow-down-thin", 24)
    layout.fit(
        width * 0.6 + 14,
        centre - 16,
        width * 0.4 - 22,
        32,
        today_value("low"),
        24,
        align="left",
        min_size=16,
    )


def narrow_portrait_now(layout):
    """Narrow tall tags: hero on top, then the readings as a short list."""
    width, height = layout.width, layout.height
    value = current_value
    layout.glyph(width / 2, height * 0.115, CONDITION_ICON, min(width * 0.62, height * 0.18))
    layout.fit(
        4,
        height * 0.21,
        width - 8,
        height * 0.13,
        value("temperature"),
        min(height * 0.12, width * 0.36),
    )
    layout.fit(4, height * 0.37, width - 8, 26, value("state"), 18, min_size=16)
    half = width / 2
    centre = height * 0.52
    for left, glyph, key, color in (
        (0, "arrow-up-thin", "high", ACCENT_INK),
        (half, "arrow-down-thin", "low", BLACK),
    ):
        layout.glyph(left + 14, centre, glyph, 20, color=color)
        layout.fit(
            left + 26,
            centre - 14,
            half - 30,
            28,
            today_value(key),
            19,
            align="left",
            color=color,
            min_size=16,
        )
    layout.stroke(10, height * 0.585, width - 10, height * 0.585, 2)
    rows = [(glyph, key) for glyph, key, _ in READINGS]
    for index, (glyph, key) in enumerate(rows):
        centre = height * (0.68 + 0.11 * index)
        layout.glyph(24, centre, glyph, 26)
        layout.fit(44, centre - 16, width - 50, 32, value(key), 22, align="left", min_size=16)


STEP_HOURS = 3


def hourly_value(slot, key):
    """One three-hourly slot from the hourly forecast, or a dash while none was fetched."""
    entity = "'${weather}'"
    row = (
        tag(
            f"set t0 = now().replace(minute=0, second=0, microsecond=0) + timedelta(hours={slot * STEP_HOURS})"
        )
        + tag(
            f"set f = fc_hourly[{entity}].forecast | default([], true) "
            f"if fc_hourly is defined and fc_hourly[{entity}] is defined else []"
        )
        + tag("set n = namespace(r={})")
        + tag("for i in f")
        + tag("set t = as_datetime(i.datetime | default(none), none)")
        + tag("if t is not none and as_local(t).replace(minute=0, second=0, microsecond=0) == t0")
        + tag("set n.r = i")
        + tag("break")
        + tag("endif")
        + tag("endfor")
        + tag("set row = n.r")
    )
    if key == "label":
        return row + template("t0.strftime('%H:00')")
    if key == "icon":
        return row + template(
            "'weather-' ~ {'clear-night': 'night', 'exceptional': 'sunny-alert', "
            "'partlycloudy': 'partly-cloudy'}.get(row.condition | default('', true), "
            "row.condition | default('', true)) if row.condition | default('', true) else 'weather-cloudy-alert'"
        )
    if key == "temp":
        return (
            row
            + tag("set v = row.temperature | default(none)")
            + template(
                f"((v | float | round(0) | int) ~ '°') if is_number(v) and v is not boolean else '{DASH}'"
            )
        )
    if key == "chance":
        return (
            row
            + tag("set v = row.precipitation_probability | default(none)")
            + template(
                f"((v | float | round(0) | int) ~ '%') if is_number(v) and v is not boolean else '{DASH}'"
            )
        )
    return (
        row
        + tag("set v = row.precipitation_probability | default(none)")
        + template(
            f"{ACCENT_INK[3:-3]} if is_number(v) and v is not boolean and (v | float) >= 50 else 'black'"
        )
    )


STATS = (
    ("thermometer", "feels", "Feels like"),
    ("water-percent", "humidity", "Humidity"),
    ("weather-windy", "wind", "Wind"),
    ("umbrella-outline", "chance", "Precip."),
)


def stat_value(key):
    return today_value("chance") if key == "chance" else current_value(key)


def hour_strip(layout, slots, centres, top, sizes, s):
    """Hour, icon, temperature and chance of rain for each slot at the given x centres."""
    hour, glyph, temp, chance = sizes
    for slot, centre in zip(range(slots), centres, strict=True):
        pitch = centres[1] - centres[0]
        left = centre - pitch / 2 + 2
        width = pitch - 4
        layout.fit(
            left, top, width, hour * 1.35, hourly_value(slot, "label"), hour, min_size=hour * 0.7
        )
        y = top + hour * 1.35 + glyph * 0.5
        layout.glyph(centre, y, hourly_value(slot, "icon"), glyph)
        y += glyph * 0.5
        layout.fit(
            left, y, width, temp * 1.35, hourly_value(slot, "temp"), temp, min_size=temp * 0.7
        )
        y += temp * 1.35
        layout.fit(
            left,
            y,
            width,
            chance * 1.35,
            hourly_value(slot, "chance"),
            chance,
            color=hourly_value(slot, "color"),
            min_size=chance * 0.7,
        )


def large_landscape_now(layout):
    """7.5 inch and up: header, hero with a stat list, then eight three-hourly slots."""
    width, height = layout.width, layout.height
    sx, sy = width / 800, height / 480
    s = min(sx, sy)

    def X(value):
        return value * sx

    def Y(value):
        return value * sy

    def S(value):
        return value * s

    value = current_value
    layout.block(0, 0, width - 1, Y(56) - 1, fill=BLACK)
    layout.glyph(S(30), Y(28), "map-marker", S(30), color="white")
    layout.fit(
        S(50),
        Y(28) - S(22),
        X(400) - S(50),
        S(44),
        value("location"),
        S(28),
        align="left",
        color="white",
    )
    layout.fit(
        X(410),
        Y(28) - S(20),
        width - S(24) - X(410),
        S(40),
        tag("set d = now().strftime('${date_format}')")
        + template("d ~ '  ' ~ now().strftime('%H:%M')"),
        S(26),
        align="right",
        color="white",
        min_size=S(20),
    )
    layout.glyph(X(130), Y(176), CONDITION_ICON, S(190))
    layout.fit(X(236), Y(130) - S(115), X(280), S(230), value("temperature"), S(156), align="left")
    layout.fit(
        X(244), Y(268) - S(24), X(270), S(48), value("state"), S(36), align="left", min_size=S(24)
    )
    layout.glyph(X(262), Y(310), "arrow-up-thin", S(34), color=ACCENT_INK)
    layout.fit(
        X(282),
        Y(310) - S(24),
        X(90),
        S(48),
        today_value("high"),
        S(30),
        align="left",
        color=ACCENT_INK,
        min_size=S(22),
    )
    layout.glyph(X(392), Y(310), "arrow-down-thin", S(34))
    layout.fit(
        X(412),
        Y(310) - S(24),
        X(100),
        S(48),
        today_value("low"),
        S(30),
        align="left",
        min_size=S(22),
    )
    layout.stroke(X(520), Y(78), X(520), Y(322), S(2))
    for index, (glyph, key, label) in enumerate(STATS):
        centre = Y(104 + index * 62)
        if index:
            layout.stroke(X(544), centre - Y(31), width - S(24), centre - Y(31), 1)
        layout.glyph(X(560), centre, glyph, S(32))
        layout.fit(
            X(584), centre - S(18), X(104), S(36), label, S(22), align="left", min_size=S(18)
        )
        layout.fit(
            X(694),
            centre - S(20),
            width - S(24) - X(694),
            S(40),
            stat_value(key),
            S(30),
            align="right",
            min_size=S(22),
        )
    layout.block(0, Y(336), width - 1, Y(336) + max(1, S(2)), fill=BLACK)
    centres = [X(50 + 100 * index) for index in range(8)]
    hour_strip(layout, 8, centres, Y(342), (S(22), S(36), S(28), S(22)), s)


def large_portrait_now(layout):
    """The same blocks stacked: header, hero, a 2x2 stat grid and two rows of four hours."""
    width, height = layout.width, layout.height
    sx, sy = width / 480, height / 800
    s = min(sx, sy)

    def X(value):
        return value * sx

    def Y(value):
        return value * sy

    def S(value):
        return value * s

    value = current_value
    layout.block(0, 0, width - 1, Y(52) - 1, fill=BLACK)
    layout.glyph(S(26), Y(26), "map-marker", S(26), color="white")
    layout.fit(
        S(44),
        Y(26) - S(20),
        X(230) - S(44),
        S(40),
        value("location"),
        S(24),
        align="left",
        color="white",
    )
    layout.fit(
        X(236),
        Y(26) - S(18),
        width - S(16) - X(236),
        S(36),
        tag("set d = now().strftime('${date_format}')")
        + template("d ~ '  ' ~ now().strftime('%H:%M')"),
        S(22),
        align="right",
        color="white",
        min_size=S(18),
    )
    layout.glyph(X(110), Y(150), CONDITION_ICON, S(150))
    layout.fit(X(200), Y(130) - S(80), X(260), S(160), value("temperature"), S(120), align="left")
    layout.fit(
        X(206), Y(212) - S(22), X(250), S(44), value("state"), S(30), align="left", min_size=S(22)
    )
    layout.glyph(X(222), Y(256), "arrow-up-thin", S(30), color=ACCENT_INK)
    layout.fit(
        X(240),
        Y(256) - S(22),
        X(90),
        S(44),
        today_value("high"),
        S(28),
        align="left",
        color=ACCENT_INK,
        min_size=S(22),
    )
    layout.glyph(X(344), Y(256), "arrow-down-thin", S(30))
    layout.fit(
        X(362),
        Y(256) - S(22),
        X(100),
        S(44),
        today_value("low"),
        S(28),
        align="left",
        min_size=S(22),
    )
    layout.stroke(S(16), Y(296), width - S(16), Y(296), S(2))
    for index, (glyph, key, label) in enumerate(STATS):
        left = (index % 2) * width / 2
        top = Y(304) + (index // 2) * Y(76)
        if index % 2:
            layout.stroke(left, top + Y(6), left, top + Y(70))
        layout.glyph(left + S(34), top + Y(38), glyph, S(34))
        layout.fit(
            left + S(62),
            top + Y(4),
            width / 2 - S(72),
            S(32),
            label,
            S(20),
            align="left",
            min_size=S(18),
        )
        layout.fit(
            left + S(62),
            top + Y(36),
            width / 2 - S(72),
            S(40),
            stat_value(key),
            S(28),
            align="left",
            min_size=S(20),
        )
    layout.stroke(S(16), Y(456), width - S(16), Y(456), S(2))
    centres = [width * (0.125 + 0.25 * index) for index in range(4)]
    hour_strip_rows = ((Y(470), 0), (Y(630), 4))
    for top, offset in hour_strip_rows:
        for index, centre in enumerate(centres):
            slot = offset + index
            left = centre - width * 0.125 + 2
            wide = width * 0.25 - 4
            layout.fit(left, top, wide, S(32), hourly_value(slot, "label"), S(22), min_size=S(18))
            layout.glyph(centre, top + S(52), hourly_value(slot, "icon"), S(40))
            layout.fit(
                left, top + S(72), wide, S(40), hourly_value(slot, "temp"), S(28), min_size=S(22)
            )
            layout.fit(
                left,
                top + S(112),
                wide,
                S(30),
                hourly_value(slot, "chance"),
                S(20),
                color=hourly_value(slot, "color"),
                min_size=S(18),
            )


def current_weather_layout(layout, _base):
    width, height = layout.width, layout.height
    if min(width, height) >= 480:
        (large_portrait_now if height > width else large_landscape_now)(layout)
        return
    if height > width:
        if width <= 132 and height <= 250:
            tiny_now(layout)
        elif width < 240:
            narrow_portrait_now(layout)
        else:
            portrait_now(layout)
    elif width / height >= 1.7:
        (compact_now if width >= 296 else small_wide_now)(layout)
    elif width / height >= 1.2:
        landscape_now(layout)
    else:
        square_now(layout)


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


def legacy_forecast_layout(layout, base):
    # Reuse the existing forecast parsing, condition mapping and fallbacks.
    day, high, low = values(base, "text")[:3]
    glyph = values(base, "icon")[0]

    show_chance = layout.detail or layout.medium
    indices = range(7) if layout.large else range(1, 6 if show_chance else 4)
    if show_chance:
        layout.text((5, 3, 48, 16), f"{len(indices)}-day forecast", 12, align="left")
        right_label = "Low / High  ·  Precip." if layout.detail else "High · Low · Precip."
        layout.text((49, 4, 95, 16), right_label, 7, align="right")
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
            top = (21 if show_chance else 5) + index * (72 if show_chance else 90) / len(indices)
            bottom = top + (72 if show_chance else 90) / len(indices)
            mid = (top + bottom) / 2
            if index:
                layout.rule(5, top, 95, top)
            layout.text((5, top, 24, bottom), field(day), 9)
            layout.icon(34, mid, field(glyph), min(17, 54 / len(indices)))
            if layout.detail:
                layout.text((43, top, 71, bottom), field(temperature_pair), 9)
                layout.text((72, top, 95, bottom), field(chance), 8)
            elif layout.medium:
                layout.text((42, top, 59, bottom), field(high), 10)
                layout.text((59, top, 76, bottom), field(low), 9)
                layout.text((77, top, 95, bottom), field(chance), 8)
            else:
                layout.text((43, top, 68, bottom), field(high), 12)
                layout.text((70, top, 95, bottom), field(low), 10)
        else:
            left = 5 + index * 90 / len(indices)
            right = 5 + (index + 1) * 90 / len(indices)
            top = 20 if show_chance else 3
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
            elif layout.medium:
                layout.text((left, 61, right, 74), field(high), 12)
                layout.text((left, 74, right, 85), field(low), 9)
                layout.text((left, 85, right, 96), field(chance), 8)
            else:
                layout.text((left, 63, right, 82), field(high), 15)
                layout.text((left, 82, right, 96), field(low), 10)


BAR_POINTS = 40


def forecast_pieces(base):
    """Jinja building blocks over the base layout's forecast parsing."""
    day, _high, low = values(base, "text")[:3]
    glyph = values(base, "icon")[0]
    prefix = low.split("{{", 1)[0]

    def at(text, slot):
        return text.replace("f[1]", f"f[{slot}]").replace("length > 1", f"length > {slot}")

    def row(slot):
        return at(prefix, slot)

    def number(slot, field, suffix):
        return row(slot) + template(
            f"((d.{field} | round(0) | int) ~ '{suffix}') "
            f"if is_number(d.{field} | default(none)) and d.{field} is not boolean else '{DASH}'"
        )

    def chance_color(slot):
        return row(slot) + template(
            "(" + ACCENT_INK[3:-3] + ") if is_number(d.precipitation_probability | default(none)) "
            "and d.precipitation_probability is not boolean and d.precipitation_probability >= 50 "
            "else 'black'"
        )

    def range_values(slot, days):
        scan = (
            tag("set ns = namespace(lo=none, hi=none)")
            + tag(f"for k in range(1, {days + 1})")
            + tag("set r = f[k] if f | length > k else {}")
            + tag("set a = r.templow | default(none)")
            + tag("set b = r.temperature | default(none)")
            + tag("if is_number(a) and a is not boolean")
            + tag("set ns.lo = a if ns.lo is none or a < ns.lo else ns.lo")
            + tag("endif")
            + tag("if is_number(b) and b is not boolean")
            + tag("set ns.hi = b if ns.hi is none or b > ns.hi else ns.hi")
            + tag("endif")
            + tag("endfor")
        )
        last = BAR_POINTS - 1
        return (
            row(slot)
            + scan
            + tag("set lo = d.templow | default(none)")
            + tag("set hi = d.temperature | default(none)")
            + tag(
                "set ok = ns.lo is not none and ns.hi is not none and is_number(lo) and is_number(hi) "
                "and lo is not boolean and hi is not boolean"
            )
            + tag("set span = [ns.hi - ns.lo, 1] | max if ok else 1")
            + tag(f"set a = ((lo - ns.lo) / span * {last}) | round(0) | int if ok else 0")
            + tag(f"set b = ((hi - ns.lo) / span * {last}) | round(0) | int if ok else 0")
            + template(
                f"[0] * a + [1] * (b - a + 1) + [0] * ({last} - b) if ok else [0] * {BAR_POINTS}"
            )
        )

    return {
        "row": row,
        "day": lambda slot: at(day, slot),
        "glyph": lambda slot: at(glyph, slot),
        "high": lambda slot: number(slot, "temperature", "°"),
        "low": lambda slot: number(slot, "templow", "°"),
        "chance": lambda slot: number(slot, "precipitation_probability", "%"),
        "chance_color": chance_color,
        "range": range_values,
    }


def sparkline_bar(layout, pieces, slot, days, x0, x1, centre, height):
    """A rounded track with a filled segment from the day's low to its high."""
    layout.block(
        x0,
        centre - height / 2,
        x1,
        centre + height / 2,
        fill="white",
        outline=BLACK,
        radius=height / 2,
    )
    layout.items.append(
        {
            "type": "sparkline",
            "x": round(x0 + 2),
            "y": round(centre - height / 2 + 2),
            "width": round(x1 - x0 - 3),
            "height": max(2, round(height - 4)),
            "values": pieces["range"](slot, days),
            "min": 0,
            "max": 1,
            "color": "white",
            "fill": BLACK,
            "width_line": 1,
        }
    )


def forecast_list(layout, base):
    """Today on top, then one row per coming day with a temperature range bar."""
    pieces = forecast_pieces(base)
    width, height = layout.width, layout.height
    portrait = height > width
    value = current_value
    accent = ACCENT_INK
    today = pieces["row"](0)
    condition = (
        today
        + tag("set p = d.precipitation_probability | default(none)")
        + template(
            "state_translated('${weather}') ~ ((' · ' ~ (p | round(0) | int) ~ '%') "
            "if is_number(p) and p is not boolean else '')"
        )
    )
    today_high = pieces["high"](0)
    today_low = pieces["low"](0)
    if portrait:
        sx, sy = width / 300, height / 400
        s = max(1, min(sx, sy))
        days = 6
        rows_top = 124 * sy
        rule_y = 118 * sy
        layout.fit(10 * sx, 4 * sy, 136 * sx, 28 * s, value("location"), 18 * s, align="left")
        layout.fit(
            150 * sx,
            4 * sy,
            140 * sx,
            28 * s,
            template("now().strftime('%m/%d %a')"),
            17 * s,
            align="right",
        )
        layout.glyph(44 * sx, 74 * sy, CONDITION_ICON, 72 * s)
        layout.fit(84 * sx, 36 * sy, 122 * sx, 66 * s, value("temperature"), 60 * s)
        layout.fit(84 * sx, 92 * sy, 210 * sx, 24 * s, condition, 17 * s, align="left", min_size=14)
        layout.glyph(218 * sx, 56 * sy, "arrow-up-thin", 20 * s, color=accent)
        layout.fit(
            230 * sx,
            42 * sy,
            64 * sx,
            28 * s,
            today_high,
            20 * s,
            align="left",
            color=accent,
            min_size=16,
        )
        layout.glyph(218 * sx, 84 * sy, "arrow-down-thin", 20 * s)
        layout.fit(230 * sx, 70 * sy, 64 * sx, 28 * s, today_low, 20 * s, align="left", min_size=16)
        columns = {
            "day": (0.073, 0.0),
            "icon": 0.2,
            "pop": 0.375,
            "low": 0.5,
            "bar": (0.527, 0.78),
            "high": 0.8,
        }
        show_pop = width >= 300
        if not show_pop:
            columns.update(day=(0.085, 0.0), icon=0.265, low=0.50, bar=(0.53, 0.785), high=0.80)
        font_day, font_value = 19 * s, 19 * s
    else:
        sx, sy = width / 400, height / 300
        s = max(1, min(sx, sy))
        days = 5
        rows_top = 118 * sy
        rule_y = 114 * sy
        layout.glyph(50 * sx, 56 * sy, CONDITION_ICON, 84 * s)
        layout.fit(98 * sx, 2 * sy, 150 * sx, 84 * s, value("temperature"), 70 * s, align="left")
        layout.fit(98 * sx, 87 * sy, 170 * sx, 26 * s, condition, 18 * s, align="left", min_size=16)
        layout.fit(250 * sx, 4 * sy, 140 * sx, 30 * s, value("location"), 20 * s, align="right")
        layout.fit(
            250 * sx,
            34 * sy,
            140 * sx,
            26 * s,
            template("now().strftime('%m/%d %a')"),
            17 * s,
            align="right",
        )
        layout.glyph(284 * sx, 95 * sy, "arrow-up-thin", 20 * s, color=accent)
        layout.fit(
            294 * sx,
            81 * sy,
            37 * sx,
            28 * s,
            today_high,
            20 * s,
            align="left",
            color=accent,
            min_size=16,
        )
        layout.glyph(342 * sx, 95 * sy, "arrow-down-thin", 20 * s)
        layout.fit(352 * sx, 81 * sy, 44 * sx, 28 * s, today_low, 20 * s, align="left", min_size=16)
        columns = {
            "day": (0.055, 0.0),
            "icon": 0.17,
            "pop": 0.335,
            "low": 0.465,
            "bar": (0.49, 0.815),
            "high": 0.835,
        }
        show_pop = True
        font_day, font_value = 22 * s, 19 * s
    layout.block(0, rule_y, width - 1, rule_y + max(2, 2 * s), fill=BLACK)
    pitch = (height - rows_top) / days
    for index in range(days):
        slot = index + 1
        centre = rows_top + (index + 0.5) * pitch
        if index:
            layout.stroke(width * 0.035, centre - pitch / 2, width * 0.965, centre - pitch / 2)
        box = min(pitch - 2, 32 * s)
        day_x = columns["day"][0] * width
        layout.fit(
            day_x - 20 * s,
            centre - box / 2,
            40 * s,
            box,
            pieces["day"](slot),
            font_day,
            min_size=14,
        )
        layout.glyph(columns["icon"] * width, centre, pieces["glyph"](slot), min(30 * s, pitch - 4))
        if show_pop:
            layout.fit(
                columns["pop"] * width - 38 * s,
                centre - box / 2,
                38 * s,
                box,
                pieces["chance"](slot),
                font_value * 0.95,
                align="right",
                color=pieces["chance_color"](slot),
                min_size=14,
            )
        layout.fit(
            columns["low"] * width - 38 * s,
            centre - box / 2,
            38 * s,
            box,
            pieces["low"](slot),
            font_value,
            align="right",
            min_size=14,
        )
        sparkline_bar(
            layout,
            pieces,
            slot,
            days,
            columns["bar"][0] * width,
            columns["bar"][1] * width,
            centre,
            12 * s,
        )
        layout.fit(
            columns["high"] * width,
            centre - box / 2,
            width * 0.985 - columns["high"] * width,
            box,
            pieces["high"](slot),
            font_value * 1.05,
            align="left",
            min_size=14,
        )


def forecast_columns(layout, base):
    """Wide, short tags: the coming days side by side."""
    pieces = forecast_pieces(base)
    width, height = layout.width, layout.height
    s = max(1, min(width / 296, height / 128))
    count = 3 if width < 330 else 4
    pad = 6
    column = (width - 2 * pad) / count
    bands = (0.0, 0.2, 0.5, 0.75, 0.98)
    top = lambda band: height * bands[band]  # noqa: E731
    for index in range(count):
        slot = index + 1
        left = pad + index * column
        if index:
            layout.stroke(left, height * 0.08, left, height * 0.92)
        for band, key, want, color in (
            (0, "day", 16 * s, BLACK),
            (2, "high", 22 * s, BLACK),
            (3, "low", 18 * s, BLACK),
        ):
            box = top(band + 1) - top(band)
            size = max(14, min(want, box / 1.45))
            layout.fit(
                left + 2,
                top(band),
                column - 4,
                box,
                pieces[key](slot),
                size,
                color=color,
                min_size=14,
            )
        glyph = min(column - 12, (top(2) - top(1)) - 2, 44 * s)
        layout.glyph(left + column / 2, (top(1) + top(2)) / 2, pieces["glyph"](slot), glyph)


def forecast_large(layout, base):
    """7.5 inch and up: a black panel for today beside (or above) one row per coming day."""
    pieces = forecast_pieces(base)
    width, height = layout.width, layout.height
    portrait = height > width
    value = current_value
    accent = ACCENT_INK
    condition = value("state")
    today_high = pieces["high"](0)
    today_low = pieces["low"](0)
    date_text = template("now().strftime('%m/%d %a')")
    days = 7
    if portrait:
        sx, sy = width / 480, height / 800
        s = min(sx, sy)
        panel = 282 * sy
        layout.block(0, 0, width - 1, panel, fill=BLACK)
        layout.fit(
            24 * sx,
            14 * sy,
            270 * sx,
            40 * s,
            value("location"),
            26 * s,
            align="left",
            color="white",
        )
        layout.fit(
            24 * sx,
            54 * sy,
            270 * sx,
            34 * s,
            date_text,
            22 * s,
            align="left",
            color="white",
            min_size=18 * s,
        )
        layout.glyph(110 * sx, 158 * sy, CONDITION_ICON, 120 * s, color="white")
        layout.fit(
            196 * sx,
            70 * sy,
            260 * sx,
            130 * s,
            value("temperature"),
            100 * s,
            align="left",
            color="white",
        )
        layout.fit(
            200 * sx,
            190 * sy,
            250 * sx,
            36 * s,
            condition,
            28 * s,
            align="left",
            color="white",
            min_size=22 * s,
        )
        layout.glyph(214 * sx, 252 * sy, "arrow-up-thin", 26 * s, color=accent)
        layout.fit(
            230 * sx,
            234 * sy,
            90 * sx,
            36 * s,
            today_high,
            26 * s,
            align="left",
            color=accent,
            min_size=22 * s,
        )
        layout.glyph(332 * sx, 252 * sy, "arrow-down-thin", 26 * s, color="white")
        layout.fit(
            348 * sx,
            234 * sy,
            100 * sx,
            36 * s,
            today_low,
            26 * s,
            align="left",
            color="white",
            min_size=22 * s,
        )
        top = panel + 4 * sy
        left, right = 12 * sx, width - 12 * sx
        columns = {
            "day": 0.061,
            "icon": 0.193,
            "pop": 0.452,
            "low": 0.583,
            "bar": (0.60, 0.80),
            "high": 0.83,
        }
        scale = s
    else:
        sx, sy = width / 800, height / 480
        s = min(sx, sy)
        layout.block(0, 0, 300 * sx, height - 1, fill=BLACK)
        layout.fit(
            24 * sx,
            14 * sy,
            260 * sx,
            44 * s,
            value("location"),
            30 * s,
            align="left",
            color="white",
        )
        layout.fit(
            24 * sx,
            60 * sy,
            260 * sx,
            36 * s,
            date_text,
            24 * s,
            align="left",
            color="white",
            min_size=20 * s,
        )
        layout.glyph(150 * sx, 180 * sy, CONDITION_ICON, 150 * s, color="white")
        layout.fit(
            10 * sx, 232 * sy, 280 * sx, 130 * s, value("temperature"), 110 * s, color="white"
        )
        layout.fit(
            10 * sx, 366 * sy, 280 * sx, 44 * s, condition, 32 * s, color="white", min_size=24 * s
        )
        layout.glyph(100 * sx, 438 * sy, "arrow-up-thin", 30 * s, color=accent)
        layout.fit(
            118 * sx,
            416 * sy,
            80 * sx,
            44 * s,
            today_high,
            28 * s,
            align="left",
            color=accent,
            min_size=22 * s,
        )
        layout.glyph(214 * sx, 438 * sy, "arrow-down-thin", 30 * s, color="white")
        layout.fit(
            232 * sx,
            416 * sy,
            66 * sx,
            44 * s,
            today_low,
            28 * s,
            align="left",
            color="white",
            min_size=22 * s,
        )
        top = 0
        left, right = 320 * sx, width - 16 * sx
        columns = {
            "day": 0.052,
            "icon": 0.172,
            "pop": 0.397,
            "low": 0.539,
            "bar": (0.565, 0.832),
            "high": 0.858,
        }
        scale = s
    area = right - left
    pitch = (height - top) / days
    for index in range(days):
        slot = index + 1
        centre = top + (index + 0.5) * pitch
        if index:
            layout.stroke(left, centre - pitch / 2, right, centre - pitch / 2)
        box = min(pitch - 4, 40 * scale)

        def at(key):
            return left + columns[key] * area

        layout.fit(
            at("day") - 26 * scale,
            centre - box / 2,
            52 * scale,
            box,
            pieces["day"](slot),
            30 * scale,
            min_size=18 * scale,
        )
        layout.glyph(at("icon"), centre, pieces["glyph"](slot), min(42 * scale, pitch - 6))
        layout.fit(
            at("pop") - 66 * scale,
            centre - box / 2,
            66 * scale,
            box,
            pieces["chance"](slot),
            26 * scale,
            align="right",
            color=pieces["chance_color"](slot),
            min_size=18 * scale,
        )
        layout.fit(
            at("low") - 58 * scale,
            centre - box / 2,
            58 * scale,
            box,
            pieces["low"](slot),
            28 * scale,
            align="right",
            min_size=18 * scale,
        )
        sparkline_bar(
            layout,
            pieces,
            slot,
            days,
            left + columns["bar"][0] * area,
            left + columns["bar"][1] * area,
            centre,
            16 * scale,
        )
        layout.fit(
            at("high"),
            centre - box / 2,
            right - at("high"),
            box,
            pieces["high"](slot),
            30 * scale,
            align="left",
            min_size=18 * scale,
        )


def forecast_stacked(layout, base):
    """Narrow tall tags: a few days, each with its weekday, icon, high and low."""
    pieces = forecast_pieces(base)
    width, height = layout.width, layout.height
    count = 4 if height >= 380 else 3
    pad = 6
    pitch = (height - 2 * pad) / count
    for index in range(count):
        slot = index + 1
        top = pad + index * pitch
        if index:
            layout.stroke(pad, top, width - pad, top)
        layout.fit(pad, top + 2, width - 2 * pad, 22, pieces["day"](slot), 16, min_size=14)
        icon_size = min(32, pitch - 30, (width - 2 * pad) * 0.4)
        layout.glyph(
            pad + icon_size / 2 + 2, top + 24 + (pitch - 24) / 2, pieces["glyph"](slot), icon_size
        )
        left = pad + icon_size + 6
        room = (pitch - 26) / 2
        layout.fit(
            left, top + 24, width - pad - left, room + 2, pieces["high"](slot), 20, min_size=14
        )
        layout.fit(
            left, top + 24 + room, width - pad - left, room, pieces["low"](slot), 16, min_size=14
        )


def forecast_layout(layout, base):
    width, height = layout.width, layout.height
    if height > width and width < 240:
        forecast_stacked(layout, base)
        return
    if min(width, height) >= 480:
        forecast_large(layout, base)
        return
    if height <= width and width / height >= 1.7:
        forecast_columns(layout, base)
        return
    stacked = height > width and width >= 240
    lists = height <= width and width / height < 1.7 and min(width, height) >= 300
    if stacked or lists:
        forecast_list(layout, base)
        return
    legacy_forecast_layout(layout, base)


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
    written = data["layouts"] or {}
    base = written.get("250x128")
    builder = BUILDERS[data["id"]]
    layouts = {}
    for size in sizes:
        if size in written:
            continue
        width, height = map(int, size.split("x"))
        layout = Layout(width, height)
        builder(layout, base)
        items = layout.items
        layouts[size] = [
            FlowElement(
                {
                    key: sys.intern(value) if isinstance(value, str) else value
                    for key, value in item.items()
                }
            )
            for item in items
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
        if yaml.safe_load(path.read_text(encoding="utf-8")).get("id") in BUILDERS:
            path.write_text(generate(path, sizes), encoding="utf-8")
