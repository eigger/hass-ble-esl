#!/usr/bin/env python3
"""Regenerate the built-in outdoor weather template at every supported size."""

from itertools import pairwise
from pathlib import Path
import sys

import yaml

DESTINATION = (
    Path(__file__).resolve().parents[1]
    / "custom_components/ble_esl/designer/templates/weather_outdoor.yaml"
)
WEATHER = "'${weather}'"
ACCENT = "${accent}"
BOLD = "NotoSansKR-Bold.ttf"
REGULAR = "NotoSansKR-Medium.ttf"
DAYS = ("월", "화", "수", "목", "금", "토", "일")
HOURS = (7, 10, 13, 16, 19, 22)
RAIN = ("rainy", "pouring", "lightning-rainy", "hail")
SNOW = ("snowy", "snowy-rainy")
WET = (*RAIN, *SNOW)
ICONS = {
    "clear-night": "night",
    "exceptional": "sunny-alert",
    "partlycloudy": "partly-cloudy",
    **{
        condition: condition
        for condition in (
            "cloudy",
            "fog",
            "hail",
            "lightning",
            "lightning-rainy",
            "pouring",
            "rainy",
            "snowy",
            "snowy-rainy",
            "sunny",
            "windy",
            "windy-variant",
        )
    },
}
CONDITIONS = {
    "clear-night": "맑음",
    "cloudy": "흐림",
    "exceptional": "특이 기상",
    "fog": "안개",
    "hail": "우박",
    "lightning": "번개",
    "lightning-rainy": "뇌우",
    "partlycloudy": "구름 많음",
    "pouring": "강한 비",
    "rainy": "비",
    "snowy": "눈",
    "snowy-rainy": "진눈깨비",
    "sunny": "맑음",
    "windy": "강풍",
    "windy-variant": "바람",
}


def tag(body):
    return "{% " + body + " %}"


def expression(body):
    return "{{ " + body + " }}"


def weather_attribute(key):
    return f"state_attr({WEATHER}, {key!r})"


def number(name, unit, precision=0):
    value = f"({name} | float | round({precision})"
    value += " | int)" if precision == 0 else ")"
    return f"{value} ~ ({unit}) if is_number({name}) and {name} is not boolean else '—'"


def current(key):
    if key == "name":
        return expression(
            f"({weather_attribute('friendly_name')} or '날씨') | truncate(13, true, '…')"
        )
    if key == "date":
        return expression(
            f"now().strftime('%m.%d') ~ ' ' ~ {DAYS!r}[now().weekday()] ~ now().strftime('  ·  %H:%M 갱신')"
        )
    if key == "condition":
        return expression(f"'현재 · ' ~ {CONDITIONS!r}.get(states({WEATHER}), '—')")
    field = {"temperature": "temperature", "feels": "apparent_temperature", "wind": "wind_speed"}[
        key
    ]
    unit = "wind_speed_unit" if key == "wind" else "temperature_unit"
    suffix = (
        f"' ' ~ ({weather_attribute(unit)} or '')"
        if key == "wind"
        else f"{weather_attribute(unit)} or '°'"
    )
    return tag(f"set v = {weather_attribute(field)}") + expression(number("v", suffix))


def rows(variable):
    return (
        f"{variable}[{WEATHER}].forecast | default([], true)"
        f" if {variable} is defined and {variable}[{WEATHER}] is defined else []"
    )


def select_forecast(variable, date, hour=None):
    slot = f" and t.hour == {hour}" if hour is not None else ""
    return (
        tag("set result = namespace(row={})")
        + tag(f"for i in ({rows(variable)})")
        + tag("set dt = as_datetime(i.datetime | default(none), none)")
        + tag("if dt is not none")
        + tag("set t = as_local(dt)")
        + tag(f"if t.date() == {date}{slot}")
        + tag("set result.row = i")
        + tag("break")
        + tag("endif")
        + tag("endif")
        + tag("endfor")
        + tag("set row = result.row")
    )


def field_value(key):
    if key == "icon":
        return f"'weather-' ~ {ICONS!r}.get(row.condition | default(''), 'cloudy-alert')"
    if key == "color":
        return f"{ACCENT!r} if row.condition | default('') in {WET!r} else 'black'"
    if key == "chance":
        return number("row.precipitation_probability | default(none)", "'%'")
    if key == "range":
        return f"({field_value('low')}) ~ ' / ' ~ ({field_value('temperature')})"
    if key == "low":
        return number("row.templow | default(none)", "'°'")
    return number("row.temperature | default(none)", "'°'")


def forecast(day, key):
    date = f"(now().date() + timedelta(days={day}))"
    if key == "date":
        return "오늘" if day == 0 else expression(f"{DAYS!r}[{date}.weekday()]")
    return select_forecast("fc", date) + expression(field_value(key))


def hourly(hour, key):
    return select_forecast("fc_hourly", "now().date()", hour) + expression(field_value(key))


def hourly_trend():
    series = (
        tag("set series = namespace(values={})")
        + tag(f"for i in ({rows('fc_hourly')})")
        + tag("set dt = as_datetime(i.datetime | default(none), none)")
        + tag("set v = i.temperature | default(none)")
        + tag("if dt is not none and is_number(v) and v is not boolean")
        + tag("set t = as_local(dt)")
        + tag(f"if t.date() == now().date() and t.hour in {HOURS!r}")
        + tag("set series.values = dict(series.values, **{(t.hour | string): (v | float)})")
        + tag("endif")
        + tag("endif")
        + tag("endfor")
    )
    heights = "series.values.values() | list"
    for left, right in pairwise(HOURS):
        a, b = repr(str(left)), repr(str(right))
        yield (
            series
            + expression(
                f"[series.values[{a}], series.values[{b}]] if {a} in series.values and {b} in series.values else []"
            ),
            series + expression(f"({heights} | min) if series.values else 0"),
            series + expression(f"({heights} | max) if series.values else 1"),
        )


def temperature_range():
    return select_forecast("fc", "now().date()") + expression(
        f"'최저 ' ~ ({field_value('low')}) ~ ' / 최고 ' ~ ({field_value('temperature')})"
    )


def advice(key):
    # Use the first remaining contiguous event. The window ends at the last
    # forecast hour, and shows the first event's peak reported probability.
    choose_event = (
        tag("set now_hour = now().replace(minute=0, second=0, microsecond=0)")
        + tag("set e = namespace(kind='', start=none, end=none, chance=none, checked=false)")
        + tag(f"for i in ({rows('fc_hourly')})")
        + tag("set dt = as_datetime(i.datetime | default(none), none)")
        + tag("if dt is not none")
        + tag("set t = as_local(dt)")
        + tag("if t.date() == now_hour.date() and t >= now_hour")
        + tag("set condition = i.condition | default('')")
        + tag(
            f"set kind = 'snow' if condition in {SNOW!r} else ('rain' if condition in {RAIN!r} else '')"
        )
        + tag(f"set e.checked = e.checked or condition in {tuple(ICONS)!r}")
        + tag("if e.start is not none and (kind != e.kind or (t - e.end).total_seconds() > 3600)")
        + tag("break")
        + tag("endif")
        + tag("if kind")
        + tag("set e.kind = kind")
        + tag("set e.start = e.start or t")
        + tag("set e.end = t")
        + tag("set p = i.precipitation_probability | default(none)")
        + tag("if is_number(p) and p is not boolean")
        + tag("set e.chance = [e.chance | default(0, true), p | float] | max")
        + tag("endif")
        + tag("endif")
        + tag("endif")
        + tag("endif")
        + tag("endfor")
    )
    daily_fallback = (
        select_forecast("fc", "now().date()")
        + tag("set condition = row.condition | default('')")
        + tag("if not e.kind and not e.checked")
        + tag(
            f"set e.kind = 'snow' if condition in {SNOW!r} else ('rain' if condition in {RAIN!r} else '')"
        )
        + tag("set p = row.precipitation_probability | default(none)")
        + tag("set e.chance = p | float if e.kind and is_number(p) and p is not boolean else none")
        + tag(f"set e.checked = e.checked or (not e.kind and condition in {tuple(ICONS)!r})")
        + tag("endif")
    )
    output = {
        "icon": "'snowflake' if e.kind == 'snow' else ('umbrella-outline' if e.kind else ('weather-sunny' if e.checked else 'weather-cloudy-alert'))",
        "label": "'미끄럼 주의' if e.kind == 'snow' else ('우산 챙기기' if e.kind else ('오늘 외출' if e.checked else '예보 정보 없음'))",
        "color": f"{ACCENT!r} if e.kind else 'black'",
        "timing": (
            "(e.start.strftime('%H') ~ ('~' ~ e.end.strftime('%H') if e.end != e.start else '') ~ '시 ' if e.start else '오늘 ')"
            " ~ ('눈' if e.kind == 'snow' else '비') ~ (' ' ~ (e.chance | round | int) ~ '%' if e.chance is not none else '')"
            " if e.kind else ('비·눈 예보 없음' if e.checked else '—')"
        ),
    }
    return choose_event + daily_fallback + expression(output[key])


def metadata(key):
    if key == "sunset":
        return tag("set t = as_datetime(state_attr('sun.sun', 'next_setting'), none)") + expression(
            "as_local(t).strftime('%H:%M') if t is not none and as_local(t).date() == now().date() else '—'"
        )
    snow_sensor = "'${snowfall_sensor}'"
    snow = (
        tag(f"set sensor = {snow_sensor}")
        + tag("set snow = states(sensor) if sensor.startswith('sensor.') else none")
        + tag("set use_snow = is_number(snow) and (snow | float) > 0")
    )
    if key == "amount_label":
        return snow + expression("'예상 적설' if use_snow else '예상 강수량'")
    return (
        snow
        + select_forecast("fc", "now().date()")
        + expression(
            "("
            + number("snow", "' ' ~ (state_attr(sensor, 'unit_of_measurement') or '')", 1)
            + ") if use_snow else ("
            + number(
                "row.precipitation | default(none)",
                f"' ' ~ ({weather_attribute('precipitation_unit')} or '')",
                1,
            )
            + ")"
        )
    )


def text(x, y, value, size, bold=False, anchor="lt", color="black"):
    return {
        "type": "text",
        "value": value,
        "font": BOLD if bold else REGULAR,
        "x": x,
        "y": y,
        "size": size,
        "anchor": anchor,
        "color": color,
    }


def icon(x, y, value, size, anchor="lt", color="black"):
    return {
        "type": "icon",
        "value": value,
        "x": x,
        "y": y,
        "size": size,
        "anchor": anchor,
        "color": color,
    }


def line(x1, y1, x2, y2, width=1, color="black"):
    return {
        "type": "line",
        "x_start": x1,
        "y_start": y1,
        "x_end": x2,
        "y_end": y2,
        "width": width,
        "fill": color,
    }


def compact(width, height):
    small = width < 240
    mid = width // 2 + 2
    y = 29 + (height - 104) // 3
    return [
        text(8, 6, "오늘 날씨", 13, True),
        text(width - 8, 7, expression("now().strftime('%H:%M 갱신')"), 11, anchor="rt"),
        line(8, 24, width - 9, 24),
        line(mid, y, mid, height - 10),
        text(8, y, current("condition"), 11),
        text(8, y + 15, current("temperature"), 28 if small else 35, True),
        text(8, height - 19, temperature_range(), 10 if small else 12, True),
        icon(mid + 8, y, advice("icon"), 17, color=advice("color")),
        text(mid + 8, y + 21, advice("label"), 14 if small else 17, True, color=advice("color")),
        text(mid + 8, y + 44, advice("timing"), 11 if small else 13, True),
    ]


def narrow_portrait(width, height):
    mid = width // 2
    return [
        text(mid, 7, "오늘 날씨", 14, True, "mt"),
        text(mid, 25, expression("now().strftime('%H:%M 갱신')"), 10, anchor="mt"),
        line(8, 41, width - 9, 41),
        text(mid, round(height * 0.24), current("condition"), 10, anchor="mt"),
        text(mid, round(height * 0.32), current("temperature"), min(34, width // 3), True, "mt"),
        text(mid, round(height * 0.50), temperature_range(), 10, True, "mt"),
        line(8, round(height * 0.61), width - 9, round(height * 0.61)),
        icon(mid, round(height * 0.66), advice("icon"), 20, "mt", advice("color")),
        text(mid, round(height * 0.78), advice("label"), 14, True, "mt", advice("color")),
        text(mid, round(height * 0.89), advice("timing"), 10, True, "mt"),
    ]


def stacked(width, height):
    portrait = height > width
    mid = width // 2
    hero = 66 if portrait else 43
    action = 196 if portrait else 131
    result = [
        text(12, 10, "오늘 날씨", 16, True),
        text(width - 12, 12, expression("now().strftime('%H:%M 갱신')"), 12, anchor="rt"),
        line(12, 32, width - 13, 32),
        text(mid, hero, current("condition"), 15 if portrait else 12, anchor="mt"),
        text(mid, hero + 20, current("temperature"), 58 if portrait else 42, True, "mt"),
        text(
            mid,
            hero + (86 if portrait else 65),
            temperature_range(),
            17 if portrait else 14,
            True,
            "mt",
        ),
        line(12, action - 4, width - 13, action - 4),
        icon(18, action + 10, advice("icon"), 25, color=advice("color")),
        text(53, action + 8, advice("label"), 22 if portrait else 18, True, color=advice("color")),
        text(53, action + 38, advice("timing"), 16 if portrait else 14, True),
    ]
    if portrait:
        for index, (hour, label) in enumerate(
            ((7, "07시 출근"), (16, "16시 오후"), (19, "19시 귀가"))
        ):
            y = 275 + 41 * index
            result.extend(
                [
                    line(12, y, width - 13, y),
                    text(13, y + 10, label, 13 if width < 220 else 15, True),
                    icon(
                        round(width * 0.45),
                        y + 8,
                        hourly(hour, "icon"),
                        18 if width < 220 else 23,
                        color=hourly(hour, "color"),
                    ),
                    text(
                        width - (48 if width < 220 else 71),
                        y + 12,
                        hourly(hour, "temperature"),
                        15,
                        True,
                        "rt",
                    ),
                    text(width - 12, y + 12, hourly(hour, "chance"), 14, anchor="rt"),
                ]
            )
    return result


def today(width, height):
    mid = width // 2
    separation = height - (80 if height > 200 else 58)
    result = [
        text(14, 9, "오늘 날씨", 16, True),
        text(width - 14, 11, current("date"), 12, anchor="rt"),
        line(14, 33, width - 15, 33),
        text(14, 42, current("condition"), 13, True),
        text(14, 61, current("temperature"), 40, True),
        text(14, 105, temperature_range(), 14, True),
        line(mid - 10, 44, mid - 10, separation - 10),
        icon(mid + 2, 49, advice("icon"), 25, color=advice("color")),
        text(mid + 36, 48, advice("label"), 21, True, color=advice("color")),
        text(mid + 3, 83, advice("timing"), 17, True),
        line(14, separation, width - 15, separation),
    ]
    cell = (width - 28) / 3
    for index, (hour, label) in enumerate(((7, "07시 출근"), (16, "16시 오후"), (19, "19시 귀가"))):
        x = round(14 + cell * index)
        end = round(x + cell)
        y = separation + (19 if height > 200 else 8)
        if index:
            result.append(line(x, y, x, height - 12))
        result.extend(
            [
                text(x + 6, y, label, 12, True),
                icon(x + 5, y + 18, hourly(hour, "icon"), 22, color=hourly(hour, "color")),
                text(x + 35, y + 21, hourly(hour, "chance"), 12),
                text(end - 7, y + 19, hourly(hour, "temperature"), 15, True, "rt"),
            ]
        )
    return result


def weekly(width, height):
    sx, sy = width / 400, height / 300
    result = []

    def t(x, y, value, size, bold=False, anchor="lt", color="black"):
        result.append(
            text(round(x * sx), round(y * sy), value, round(size * sx), bold, anchor, color)
        )

    def i(x, y, value, size, anchor="lt", color="black"):
        result.append(icon(round(x * sx), round(y * sy), value, round(size * sx), anchor, color))

    def rule(x1, y1, x2, y2, weight=1, color="black"):
        result.append(
            line(
                round(x1 * sx),
                round(y1 * sy),
                round(x2 * sx),
                round(y2 * sy),
                round(weight * sx),
                color,
            )
        )

    t(14, 11, current("name"), 18, True)
    t(386, 13, current("date"), 12, anchor="rt")
    rule(14, 36, 386, 36)
    t(14, 48, current("condition"), 12, True)
    t(14, 66, current("temperature"), 42, True)
    t(14, 111, temperature_range(), 13, True)
    rule(170, 48, 170, 122)
    i(189, 50, advice("icon"), 23, color=advice("color"))
    t(218, 48, advice("label"), 19, True, color=advice("color"))
    t(189, 79, advice("timing"), 21, True)
    rule(14, 135, 386, 135, 2)
    t(14, 146, "7일 예보", 16, True)
    t(386, 151, "최저 / 최고 · 강수확률", 11, anchor="rt")
    week_columns(t, i, rule, width=372, left=14, y=(174, 186, 208, 245, 271), sizes=(13, 26, 12))
    return result


def week_columns(t, i, rule, *, width, left, y, sizes):
    cell = width / 7
    heading, icon_size, value_size = sizes
    mark, date, icon_y, values, chance = y
    for day in range(7):
        x = left + cell * day
        mid = x + cell / 2
        color = forecast(day, "color")
        if day == 0:
            rule(x + 5, mark, x + cell - 5, mark, 2, color)
        else:
            rule(x, date - 3, x, chance + value_size + 2)
        t(mid, date, forecast(day, "date"), heading, True, "mt")
        i(mid, icon_y, forecast(day, "icon"), icon_size, "mt", color)
        t(mid, values, forecast(day, "range"), value_size, True, "mt")
        t(mid, chance, forecast(day, "chance"), value_size, True, "mt", color)


def large_layout(width, height):
    """Large Korean weather dashboard, built from editable ImageSpec primitives.

    Coordinate system follows the 800 x 480 design; vertical space expands on
    taller displays. Forecast indices start at zero (today), while hourly slots
    use local clock hours 7, 10, 13, 16, 19, and 22.
    """
    sx, sy = width / 800, height / 480
    result = []

    def t(x, y, value, size, bold=False, anchor="lt", color="black"):
        result.append(
            text(
                round(x * sx),
                round(y * sy),
                value,
                round(size * sx),
                bold=bold,
                anchor=anchor,
                color=color,
            )
        )

    def i(x, y, value, size, anchor="lt", color="black"):
        result.append(
            icon(round(x * sx), round(y * sy), value, round(size * sx), anchor=anchor, color=color)
        )

    def rule(x1, y1, x2, y2, weight=1, color="black"):
        result.append(
            line(
                round(x1 * sx),
                round(y1 * sy),
                round(x2 * sx),
                round(y2 * sy),
                width=max(1, round(weight * sx)),
                color=color,
            )
        )

    t(24, 17, current("name"), 26, True)
    t(776, 23, current("date"), 16, anchor="rt")
    rule(24, 52, 776, 52)
    t(24, 67, current("condition"), 16, True)
    t(24, 91, current("temperature"), 58, True)
    t(24, 143, temperature_range(), 17, True)
    rule(230, 67, 230, 154)
    i(254, 70, advice("icon"), 30, color=advice("color"))
    t(293, 69, advice("label"), 27, True, color=advice("color"))
    t(254, 116, advice("timing"), 25, True)
    rule(539, 67, 539, 154)
    t(562, 72, "체감", 14, True)
    t(562, 90, current("feels"), 19, True)
    t(562, 119, "바람", 14, True)
    t(562, 137, current("wind"), 19, True)
    if max(width, height) >= 960:
        t(672, 72, metadata("amount_label"), 14, True)
        t(672, 90, metadata("amount"), 19, True)
        t(672, 119, "일몰", 14, True)
        t(672, 137, metadata("sunset"), 19, True)

    rule(24, 168, 776, 168, 2)
    t(24, 182, "오늘 시간대별 예보", 21, True)
    t(776, 187, "기온 · 강수확률", 15, anchor="rt")
    labels = ("07시 출근", "10시", "13시", "16시", "19시 귀가", "22시")
    for n, (hour, label) in enumerate(zip(HOURS, labels, strict=True)):
        x = 24 + (n + 0.5) * 752 / 6
        t(x, 216, label, 16, True, anchor="mt")
        t(x, 239, hourly(hour, "temperature"), 21, True, anchor="mt")
        i(x - 28, 291, hourly(hour, "icon"), 27, color=hourly(hour, "color"))
        t(x + 5, 296, hourly(hour, "chance"), 17, True, color=hourly(hour, "color"))

    for index, (values, minimum, maximum) in enumerate(hourly_trend()):
        left = round((24 + (index + 0.5) * 752 / 6) * sx)
        right = round((24 + (index + 1.5) * 752 / 6) * sx)
        result.append(
            {
                "type": "sparkline",
                "x": left,
                "y": round(266 * sy),
                "width": right - left + 1,
                "height": round(18 * sy),
                "width_line": max(1, round(2 * sx)),
                "values": values,
                "min": minimum,
                "max": maximum,
            }
        )
    rule(24, 329, 776, 329, 2)
    t(24, 342, "7일 예보", 21, True)
    t(776, 346, "최저 / 최고 · 강수확률", 15, anchor="rt")
    week_columns(t, i, rule, width=752, left=24, y=(373, 384, 407, 435, 456), sizes=(17, 29, 16))
    return result


class TemplateDumper(yaml.SafeDumper):
    """Share repeated Jinja strings across bundled layouts."""

    def ignore_aliases(self, data):
        return not (isinstance(data, str) and len(data) > 200 and data.startswith("{%"))


def generate():
    layouts = {}
    profiles = (
        (stacked, ((200, 200), (240, 416))),
        (compact, ((212, 104), (250, 122), (250, 128), (250, 132), (296, 128), (296, 152))),
        (today, ((384, 184), (416, 240))),
        (weekly, ((400, 300), (648, 480))),
        (large_layout, ((800, 480), (960, 640), (960, 680), (1600, 1200))),
    )
    portrait_layouts = {compact: narrow_portrait, today: stacked}
    for layout, resolutions in profiles:
        for width, height in resolutions:
            layouts[f"{width}x{height}"] = layout(width, height)
            portrait_size = f"{height}x{width}"
            if width > height and portrait_size not in layouts:
                layouts[portrait_size] = portrait_layouts.get(layout, layout)(height, width)
    for items in layouts.values():
        for item in items:
            for key, value in item.items():
                if isinstance(value, str) and value.startswith("{%"):
                    item[key] = sys.intern(value)
    data = {
        "template": 1,
        "id": "weather_outdoor",
        "name": {"en": "Outdoor weather", "ko": "외출 날씨"},
        "description": {
            "en": "Korean weather dashboard with precipitation timing, today's temperatures, and a weekly outlook on larger tags.",
            "ko": "비·눈 시간과 오늘 기온을 표시하며, 큰 태그에는 주간 및 시간대별 예보를 더합니다.",
        },
        "background": "white",
        "parameters": {
            "weather": {
                "type": "entity",
                "domain": "weather",
                "default": "weather.home",
                "label": {"en": "Weather entity", "ko": "날씨 엔티티"},
            },
            "snowfall_sensor": {
                "type": "string",
                "default": "",
                "label": {
                    "en": "Today's snowfall sensor (10.2 and 13.3 inches, optional)",
                    "ko": "오늘 예상 적설 센서 ID (10.2·13.3인치, 선택)",
                },
            },
            "accent": {
                "type": "color",
                "default": "red",
                "label": {"en": "Precipitation color", "ko": "비·눈 강조 색상"},
            },
        },
        "layouts": layouts,
        "automation": {
            "triggers": [{"trigger": "time_pattern", "minutes": "0"}],
            "actions": [
                {
                    "action": "weather.get_forecasts",
                    "target": {"entity_id": "${weather}"},
                    "data": {"type": kind},
                    "response_variable": variable,
                    "continue_on_error": True,
                }
                for kind, variable in (("daily", "fc"), ("hourly", "fc_hourly"))
            ],
            "mode": "single",
        },
    }
    return "# Generated by scripts/generate_outdoor_weather_template.py\n" + yaml.dump(
        data, Dumper=TemplateDumper, allow_unicode=True, sort_keys=False, width=4096
    )


if __name__ == "__main__":
    DESTINATION.write_text(generate(), encoding="utf-8")
