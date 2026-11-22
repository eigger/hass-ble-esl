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
    if key == "safe_color":
        return f"('black' if {ACCENT!r} in ('yellow', 'white') else {ACCENT!r}) if row.condition | default('') in {WET!r} else 'black'"
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


def precipitation(row):
    """Jinja fragment that derives the kind and validated probability for one row."""
    return (
        tag(f"set condition = {row}.condition | default('')")
        + tag(f"set p = {row}.precipitation_probability | default(none)")
        + tag(
            "set p = p | float if is_number(p) and p is not boolean and 0 <= p | float <= 100 else none"
        )
        + tag(f"set amount = {row}.precipitation | default(none)")
        + tag(
            f"set kind = 'snow' if condition in {SNOW!r} else ('rain' if condition in {RAIN!r} "
            "else ('wet' if (p is not none and p >= 50) or "
            "(is_number(amount) and amount is not boolean and amount | float > 0) else ''))"
        )
    )


def advice(key):
    # Select the first remaining contiguous event. A partial hourly response
    # cannot rule out a wet daily forecast.
    choose_event = (
        tag("set now_hour = now().replace(minute=0, second=0, microsecond=0)")
        + tag(
            "set e = namespace(kind='', start=none, end=none, chance=none, hours=[], covered=false, risk=0)"
        )
        + tag(f"for i in ({rows('fc_hourly')})")
        + tag("set dt = as_datetime(i.datetime | default(none), none)")
        + tag("if dt is not none")
        + tag("set t = as_local(dt)")
        + tag("if t.date() == now_hour.date() and t >= now_hour")
        + precipitation("i")
        + tag("if p is not none")
        + tag("set e.risk = [e.risk, p] | max")
        + tag("endif")
        + tag(f"if condition in {tuple(ICONS)!r} or p is not none or kind")
        + tag("set e.hours = e.hours + [t.hour]")
        + tag("endif")
        + tag("if e.start is not none and (kind != e.kind or (t - e.end).total_seconds() > 3600)")
        + tag("break")
        + tag("endif")
        + tag("if kind")
        + tag("set e.kind = kind")
        + tag("set e.start = e.start or t")
        + tag("set e.end = t")
        + tag("if p is not none")
        + tag("set e.chance = [e.chance | default(0, true), p] | max")
        + tag("endif")
        + tag("endif")
        + tag("endif")
        + tag("endif")
        + tag("endfor")
    )
    daily_fallback = (
        tag("if not e.kind")
        + tag("if e.hours | unique | list | count == 24 - now_hour.hour")
        + tag("set e.covered = true")
        + tag("else")
        + select_forecast("fc", "now().date()")
        + precipitation("row")
        + tag("set e.kind = kind")
        + tag("set e.chance = p")
        + tag("if p is not none")
        + tag("set e.risk = [e.risk, p] | max")
        + tag("endif")
        + tag(f"set e.covered = condition in {tuple(ICONS)!r} or p is not none")
        + tag("endif")
        + tag("endif")
    )
    output = {
        "icon": "'snowflake' if e.kind == 'snow' else ('umbrella-outline' if e.kind else ('weather-sunny' if e.covered or e.risk else 'weather-cloudy-alert'))",
        "label": "'미끄럼 주의' if e.kind == 'snow' else ('우산 챙기기' if e.kind else ('오늘 외출' if e.covered or e.risk else '예보 정보 없음'))",
        "color": f"{ACCENT!r} if e.kind else 'black'",
        "safe_color": f"('black' if {ACCENT!r} in ('yellow', 'white') else {ACCENT!r}) if e.kind else 'black'",
        "timing": (
            "(e.start.strftime('%H') ~ ('~' ~ e.end.strftime('%H') if e.end != e.start else '') ~ '시 ' if e.start else '오늘 ')"
            " ~ ('눈' if e.kind == 'snow' else ('비' if e.kind == 'rain' else '강수'))"
            " ~ (' ' ~ (e.chance | round | int) ~ '%' if e.chance is not none else '')"
            " if e.kind else ('강수 ' ~ (e.risk | round | int) ~ '%' if e.risk else ('비·눈 예보 없음' if e.covered else '—'))"
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


def fit_text(x, y, width, height, value, size, *, align="center", color="black", min_size=None):
    item = {
        "type": "text_fit",
        "value": value,
        "font": BOLD,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "size": size,
        "min_size": 7 if min_size is None else min_size,
        "fit": "shrink",
        "align": align,
        "valign": "middle",
        "max_lines": 1,
    }
    if color != "black":
        item["color"] = color
    return item


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
    ms = 10 if width >= 296 else 9
    small = width < 240
    mid_band = width >= 296
    mid = width // 2
    temp_sz = 34 if small else (42 if mid_band else 38)
    range_sz = 14 if small else 16
    label_sz = 16 if small else (20 if mid_band else 18)
    timing_sz = 13 if small else (16 if mid_band else 14)
    ic_sz = 24 if small else 28
    lbl_x = mid + (36 if small else 40)
    return [
        fit_text(
            6,
            8,
            mid - 12,
            temp_sz + 14,
            current("temperature"),
            temp_sz,
            align="center",
            min_size=ms,
        ),
        fit_text(
            6, height - 34, mid - 12, 26, temperature_range(), range_sz, align="center", min_size=ms
        ),
        line(mid, 8, mid, height - 8),
        icon(mid + 8, 12, advice("icon"), ic_sz, color=advice("safe_color")),
        fit_text(
            lbl_x,
            10,
            width - lbl_x - 6,
            30,
            advice("label"),
            label_sz,
            align="left",
            color=advice("safe_color"),
            min_size=ms,
        ),
        line(mid + 6, 46, width - 6, 46),
        fit_text(
            mid + 6,
            52,
            width - mid - 12,
            height - 60,
            advice("timing"),
            timing_sz,
            align="left",
            color=advice("safe_color"),
            min_size=ms,
        ),
    ]


def narrow_portrait(width, height):
    ms = 10 if height >= 296 or width >= 296 else 9
    compact_h = height < 240
    pad = 5
    inner = width - 2 * pad
    temp_sz = 34 if compact_h else 42
    sec_sz = 14 if compact_h else 16
    label_sz = 16 if compact_h else 19
    div_y = round(height * 0.46)
    return [
        fit_text(
            pad,
            10,
            inner,
            temp_sz + 14,
            current("temperature"),
            temp_sz,
            align="center",
            min_size=ms,
        ),
        fit_text(
            pad,
            62 if compact_h else 74,
            inner,
            28,
            temperature_range(),
            sec_sz,
            align="center",
            min_size=ms,
        ),
        line(8, div_y, width - 9, div_y),
        icon(
            width // 2,
            round(height * 0.50),
            advice("icon"),
            26 if compact_h else 32,
            "mt",
            advice("safe_color"),
        ),
        fit_text(
            pad,
            round(height * 0.65),
            inner,
            28,
            advice("label"),
            label_sz,
            align="center",
            color=advice("safe_color"),
            min_size=ms,
        ),
        fit_text(
            pad,
            round(height * 0.80),
            inner,
            height - round(height * 0.80) - 6,
            advice("timing"),
            sec_sz,
            align="center",
            min_size=ms,
        ),
    ]


def stacked(width, height):
    if width == 200 and height == 200:
        return [
            fit_text(10, 12, 180, 64, current("temperature"), 54, align="center", min_size=9),
            fit_text(10, 78, 180, 28, temperature_range(), 18, align="center", min_size=9),
            line(12, 112, 188, 112),
            icon(20, 122, advice("icon"), 30, color=advice("safe_color")),
            fit_text(
                56,
                122,
                134,
                30,
                advice("label"),
                22,
                align="left",
                color=advice("safe_color"),
                min_size=9,
            ),
            fit_text(12, 158, 176, 30, advice("timing"), 16, align="center", min_size=9),
        ]
    result = [
        fit_text(12, 8, width // 2 - 14, 24, "오늘 날씨", 18, align="left", min_size=10),
        fit_text(
            width // 2, 8, width // 2 - 12, 24, current("date"), 15, align="right", min_size=10
        ),
        line(12, 36, width - 13, 36),
        fit_text(12, 48, width - 24, 68, current("temperature"), 58, align="center", min_size=10),
        fit_text(12, 120, width - 24, 28, temperature_range(), 18, align="center", min_size=10),
        line(12, 156, width - 13, 156),
        icon(18, 166, advice("icon"), 26, color=advice("safe_color")),
        fit_text(
            50,
            164,
            width - 62,
            30,
            advice("label"),
            22,
            align="left",
            color=advice("safe_color"),
            min_size=10,
        ),
        fit_text(12, 198, width - 24, 28, advice("timing"), 16, align="center", min_size=10),
    ]
    for index, (hour, label) in enumerate(((7, "07시 출근"), (19, "19시 귀가"))):
        y = 240 + 68 * index
        result.extend(
            [
                line(12, y, width - 13, y),
                fit_text(12, y + 8, width - 24, 24, label, 16, align="left", min_size=10),
                icon(14, y + 36, hourly(hour, "icon"), 22, color=hourly(hour, "safe_color")),
                fit_text(
                    42, y + 34, 60, 26, hourly(hour, "temperature"), 18, align="left", min_size=10
                ),
                fit_text(
                    width - 70,
                    y + 34,
                    58,
                    26,
                    hourly(hour, "chance"),
                    16,
                    align="right",
                    min_size=10,
                ),
            ]
        )
    return result


def today(width, height):
    mid = width // 2
    sep = height - 62
    temp_sz = 48 if height < 210 else 56
    temp_h = 54 if height < 210 else 68
    range_y = 94 if height < 210 else 120
    range_sz = 16 if height < 210 else 18
    timing_y = 78 if height < 210 else 96
    result = [
        fit_text(12, 6, 160, 24, "오늘 날씨", 18, align="left", min_size=10),
        fit_text(width - 150, 6, 138, 24, current("date"), 16, align="right", min_size=10),
        line(12, 34, width - 13, 34),
        fit_text(
            12, 38, mid - 22, temp_h, current("temperature"), temp_sz, align="left", min_size=10
        ),
        fit_text(
            12, range_y, mid - 22, 24, temperature_range(), range_sz, align="left", min_size=10
        ),
        line(mid - 4, 40, mid - 4, sep - 6),
        icon(mid + 6, 44, advice("icon"), 26, color=advice("safe_color")),
        fit_text(
            mid + 38,
            42,
            width - mid - 50,
            30,
            advice("label"),
            21,
            align="left",
            color=advice("safe_color"),
            min_size=10,
        ),
        fit_text(
            mid + 6,
            timing_y,
            width - mid - 18,
            32,
            advice("timing"),
            16 if height < 210 else 18,
            align="left",
            min_size=10,
        ),
        line(12, sep, width - 13, sep),
    ]
    cell = (width - 24) / 2
    for index, (hour, label) in enumerate(((7, "07시 출근"), (19, "19시 귀가"))):
        x = round(12 + cell * index)
        end = round(x + cell)
        y = sep + 6
        if index:
            result.append(line(x, y, x, height - 8))
        result.extend(
            [
                fit_text(x + 6, y, 76, 22, label, 16, align="left", min_size=10),
                icon(x + 8, y + 26, hourly(hour, "icon"), 22, color=hourly(hour, "safe_color")),
                fit_text(
                    x + 34,
                    y + 26,
                    66,
                    22,
                    hourly(hour, "temperature"),
                    17,
                    align="left",
                    min_size=10,
                ),
                fit_text(
                    end - 64,
                    y + 26,
                    56,
                    22,
                    hourly(hour, "chance"),
                    16,
                    align="right",
                    color=hourly(hour, "safe_color"),
                    min_size=10,
                ),
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
    week_columns(
        result,
        t,
        i,
        rule,
        scale=(sx, sy),
        width=372,
        left=14,
        y=(174, 186, 208, 245, 271),
        sizes=(13, 26, 12),
    )
    return result


def week_columns(result, t, i, rule, *, scale, width, left, y, sizes):
    sx, sy = scale
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
        # Reserve the space between the dividers even for double-negative
        # ranges in Celsius and three-digit values in Fahrenheit.
        left_edge = round((x + 2) * sx)
        result.append(
            fit_text(
                left_edge,
                round((values - 2) * sy),
                round((x + cell - 2) * sx) - left_edge,
                round((chance - values) * sy),
                forecast(day, "range"),
                round(value_size * sx),
            )
        )
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
    week_columns(
        result,
        t,
        i,
        rule,
        scale=(sx, sy),
        width=752,
        left=24,
        y=(373, 384, 407, 435, 456),
        sizes=(17, 29, 16),
    )
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
