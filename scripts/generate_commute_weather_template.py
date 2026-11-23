#!/usr/bin/env python3
"""Regenerate the built-in outing weather template at every supported size."""

from pathlib import Path
import sys

import yaml

DESTINATION = (
    Path(__file__).resolve().parents[1]
    / "custom_components/ble_esl/designer/templates/weather_commute.yaml"
)
WEATHER = "'${weather}'"
ACCENT = "${accent}"
ACCENT_INK = "{{ 'black' if '${accent}' == 'white' else '${accent}' }}"
FONT = "${font}"
DAYS = ("월", "화", "수", "목", "금", "토", "일")
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


def select_forecast(day_offset):
    """Select daily forecast row for ``day_offset``, matching dated rows or falling back by index."""
    return (
        tag(f"set _d = now().date() + timedelta(days={day_offset})")
        + tag(
            f"set _f = fc[{WEATHER}].forecast | default([], true) "
            f"if fc is defined and fc[{WEATHER}] is defined else []"
        )
        + tag("set _ns = namespace(r={}, dt=false)")
        + tag("for i in _f")
        + tag("set t = as_datetime(i.datetime | default(none), none)")
        + tag("if t is not none")
        + tag("set _ns.dt = true")
        + tag("if as_local(t).date() == _d")
        + tag("set _ns.r = i")
        + tag("break")
        + tag("endif")
        + tag("endif")
        + tag("endfor")
        + tag(f"if not _ns.dt and _f | length > {day_offset}")
        + tag(f"set _ns.r = _f[{day_offset}]")
        + tag("endif")
        + tag("set row = _ns.r")
    )


def _int_deg_expr(var_name):
    return f"((({var_name} | float | round(0) | int) ~ '°') if is_number({var_name}) and {var_name} is not boolean else '—')"


def _int_pct_expr(var_name):
    return f"((({var_name} | float | round(0) | int) ~ '%') if is_number({var_name}) and {var_name} is not boolean else '—')"


def _precip_amount_setup(var_name):
    """Build Jinja statements formatting a positive precipitation amount cleanly."""
    return (
        tag(f"set _pu = ({weather_attribute('precipitation_unit')} or 'mm') | trim")
        + tag("set _pul = _pu | lower")
        + tag(f"set _dec = 2 if (_pul in ('in', 'inch', 'inches') or {var_name} < 0.1) else 1")
        + tag(f"set _ar = {var_name} | round(_dec)")
        + tag(
            f"set _amt_str = ('<0.1' ~ _pu) if ({var_name} > 0 and _dec == 1 and _ar == 0) "
            f"else (('<0.01' ~ _pu) if ({var_name} > 0 and _dec == 2 and _ar == 0) "
            f"else (((_ar | int if _ar == _ar | int else _ar) ~ _pu) if {var_name} > 0 else ''))"
        )
    )


def _accent_ink_expr():
    return f"('black' if {ACCENT!r} == 'white' else {ACCENT!r})"


def _text_ink_expr():
    return f"('black' if {ACCENT!r} in ('yellow', 'white') else {ACCENT!r})"


def _accent_fg_expr():
    return f"('black' if {ACCENT!r} == 'yellow' else 'white')"


def _wind_expr(var_name, *, space=True):
    sep = "' ' ~ " if space else ""
    return (
        f"(((({var_name} | float | round(1)) if ({var_name} | float) < 10 and "
        f"({var_name} | float) != ({var_name} | float | round(0)) "
        f"else ({var_name} | float | round(0) | int)) ~ {sep}"
        f"({weather_attribute('wind_speed_unit')} or 'm/s')) if is_number({var_name}) and {var_name} is not boolean else '—')"
    )


def current(key, *, prefix=""):
    if key == "date":
        return expression(f"now().strftime('%m/%d') ~ ' (' ~ {DAYS!r}[now().weekday()] ~ ')'")
    if key == "short_date":
        return expression(f"now().strftime('%m/%d ') ~ {DAYS!r}[now().weekday()]")
    if key == "full_date":
        return expression(f"now().strftime('%Y.%m.%d') ~ ' (' ~ {DAYS!r}[now().weekday()] ~ ')'")
    if key == "icon":
        return expression(f"'weather-' ~ {ICONS!r}.get(states({WEATHER}), 'cloudy-alert')")
    if key == "condition":
        return expression(f"{CONDITIONS!r}.get(states({WEATHER}), '—')")
    if key == "temperature":
        return (
            tag(f"set _t = {weather_attribute('temperature')}")
            + tag(
                "set _r = (_t | float | round(1)) if is_number(_t) and _t is not boolean "
                "and (_t | float | abs) < 100000 else none"
            )
            + expression(
                f"'—' if _r is none else ((_r | int if _r == _r | int else _r) ~ "
                f"({weather_attribute('temperature_unit')} or '°'))"
            )
        )
    if key == "feels":
        return tag(f"set _v = {weather_attribute('apparent_temperature')}") + expression(
            f"{prefix!r} ~ {_int_deg_expr('_v')}" if prefix else _int_deg_expr("_v")
        )
    if key == "humidity":
        return tag(f"set _v = {weather_attribute('humidity')}") + expression(
            f"{prefix!r} ~ {_int_pct_expr('_v')}" if prefix else _int_pct_expr("_v")
        )
    if key == "wind":
        return tag(f"set _v = {weather_attribute('wind_speed')}") + expression(
            f"{prefix!r} ~ {_wind_expr('_v')}" if prefix else _wind_expr("_v")
        )
    raise KeyError(key)


def today_field(key, *, prefix=""):
    base = select_forecast(0)
    if key == "low":
        return base + tag("set _v = row.templow | default(none)") + expression(_int_deg_expr("_v"))
    if key == "high":
        return (
            base + tag("set _v = row.temperature | default(none)") + expression(_int_deg_expr("_v"))
        )
    if key == "range":
        return (
            base
            + tag("set _lo = row.templow | default(none)")
            + tag("set _hi = row.temperature | default(none)")
            + expression(f"({_int_deg_expr('_lo')}) ~ ' / ' ~ ({_int_deg_expr('_hi')})")
        )
    if key == "pop":
        return (
            base
            + tag("set _p = row.precipitation_probability | default(none)")
            + expression(f"{prefix!r} ~ {_int_pct_expr('_p')}" if prefix else _int_pct_expr("_p"))
        )
    if key == "pop_color":
        return (
            base
            + tag("set _p = row.precipitation_probability | default(none)")
            + expression(
                f"{_accent_ink_expr()} if is_number(_p) and _p is not boolean and (_p | float) >= 40 else 'black'"
            )
        )
    if key == "pop_safe_color":
        return (
            base
            + tag("set _p = row.precipitation_probability | default(none)")
            + expression(
                f"{_text_ink_expr()} if is_number(_p) and _p is not boolean and (_p | float) >= 40 else 'black'"
            )
        )
    raise KeyError(key)


def commute_alert(key):
    """Derive morning commute action badge, icon, colors, and checklist copy."""
    setup = (
        select_forecast(0)
        + tag(f"set _st = states({WEATHER})")
        + tag("set _cond = row.condition | default(_st, true)")
        + tag("set _p = row.precipitation_probability | default(none)")
        + tag(
            "set _pv = (_p | float | round(0) | int) if is_number(_p) and _p is not boolean else none"
        )
        + tag("set _amt = row.precipitation | default(none)")
        + tag("set _amtv = (_amt | float) if is_number(_amt) and _amt is not boolean else 0")
        + tag("set _hi = row.temperature | default(none)")
        + tag("set _lo = row.templow | default(none)")
        + tag(
            "set _gap = ((_hi | float) - (_lo | float)) | round(0) | int "
            "if is_number(_hi) and _hi is not boolean and is_number(_lo) and _lo is not boolean else 0"
        )
        + tag(f"set _tu = ({weather_attribute('temperature_unit')} or '') | lower")
        + tag("set _gap_lim = 18 if 'f' in _tu else 10")
        + tag(f"set _w = {weather_attribute('wind_speed')}")
        + tag(f"set _wu = ({weather_attribute('wind_speed_unit')} or 'm/s') | lower")
        + tag("set _wv = (_w | float) if is_number(_w) and _w is not boolean else none")
        + tag(
            "set _windy = (_st in ('windy', 'windy-variant')) or (_wv is not none and ("
            "(_wu == 'km/h' and _wv >= 25) or (_wu == 'mph' and _wv >= 16) "
            "or (_wu in ('kn', 'kt', 'knots') and _wv >= 14) or (_wu == 'ft/s' and _wv >= 23) "
            "or (_wu not in ('km/h', 'mph', 'kn', 'kt', 'knots', 'ft/s') and _wv >= 7)))"
        )
        + tag(f"set _is_snow = (_st in {SNOW!r}) or (_cond in {SNOW!r})")
        + tag(
            f"set _is_rain = (_st in {RAIN!r}) or (_cond in {RAIN!r}) "
            "or (_pv is not none and _pv >= 50) or (_amtv > 0)"
        )
        + tag(
            f"set _has_fc = (row | length > 0) and (_pv is not none or (row.condition | default('', true)) in {tuple(ICONS)!r})"
        )
        + tag(
            "set _kind = 'snow' if _is_snow else ('rain' if _is_rain else "
            "('gap' if _gap >= _gap_lim else ('wind' if _windy else ('ok' if _has_fc else 'none'))))"
        )
    )
    extra_comfort = tag(f"set _f = {weather_attribute('apparent_temperature')}") + tag(
        f"set _fstr = {_int_deg_expr('_f')}"
    )
    extra_sub = extra_comfort + _precip_amount_setup("_amtv")
    ink = _accent_ink_expr()
    fg = _accent_fg_expr()
    safe_text = _text_ink_expr()
    outputs = {
        "bg": (setup, f"{ink} if _kind in ('snow', 'rain') else 'white'"),
        "outline": (setup, f"{ink} if _kind in ('snow', 'rain') else 'black'"),
        "fg": (setup, f"{fg} if _kind in ('snow', 'rain') else 'black'"),
        "safe_text_color": (setup, f"{safe_text} if _kind in ('snow', 'rain') else 'black'"),
        "icon": (
            setup,
            "'snowflake' if _kind == 'snow' else ('umbrella' if _kind == 'rain' "
            "else ('thermometer' if _kind == 'gap' else ('weather-windy' if _kind == 'wind' "
            "else ('weather-sunny' if _kind == 'ok' else 'weather-cloudy-alert'))))",
        ),
        "label": (
            setup,
            "'눈길 주의' if _kind == 'snow' else ('우산 챙기기' if _kind == 'rain' "
            "else ('일교차 주의' if _kind == 'gap' else ('강풍 주의' if _kind == 'wind' "
            "else ('우산 불필요' if _kind == 'ok' else '예보 정보 없음'))))",
        ),
        "short": (
            setup,
            "(('눈 ' ~ _pv ~ '%') if _pv is not none else '눈 주의') if _kind == 'snow' "
            "else ((('우산 ' ~ _pv ~ '%') if _pv is not none else '우산 챙기기') if _kind == 'rain' "
            "else (('일교차 ' ~ _gap ~ '°') if _kind == 'gap' "
            "else ('강풍 주의' if _kind == 'wind' else ((('강수 ' ~ _pv ~ '%') if _pv is not none else '쾌적') if _kind == 'ok' else '예보 없음'))))",
        ),
        "sub": (
            setup + extra_sub,
            "(('강수 ' ~ _pv ~ '%' if _pv is not none else '눈 예보') ~ (' · ' ~ _amt_str if _amt_str else '')) if _kind == 'snow' "
            "else ((('강수 ' ~ _pv ~ '%' if _pv is not none else '비 예보') ~ (' · ' ~ _amt_str if _amt_str else '')) if _kind == 'rain' "
            "else (('일교차 ' ~ _gap ~ '° · 겉옷') if _kind == 'gap' "
            "else (('강풍 · 체감 ' ~ _fstr) if _kind == 'wind' "
            "else (('강수확률 ' ~ _pv ~ '%' if _pv is not none else '비·눈 없음') if _kind == 'ok' else '예보 대기 중'))))",
        ),
    }
    prefix, expr = outputs[key]
    return prefix + expression(expr)


def fit_text(
    x, y, width, height, value, size, *, align="center", color="black", lines=1, min_size=None
):
    item = {
        "type": "text_fit",
        "value": value,
        "font": FONT,
        "x": int(x),
        "y": int(y),
        "width": max(1, int(width)),
        "height": max(1, int(height)),
        "size": max(7, min(int(size), max(7, int(height)))),
        "valign": "middle",
    }
    if min_size is not None:
        item["min_size"] = int(min_size)
    if align != "left":
        item["align"] = align
    if color != "black":
        item["color"] = color
    if lines != 1:
        item["max_lines"] = lines
    return item


def icon(x, y, value, size, *, anchor="lt", color="black"):
    item = {
        "type": "icon",
        "value": value,
        "x": int(x),
        "y": int(y),
        "size": max(8, int(size)),
        "anchor": anchor,
    }
    if color != "black":
        item["color"] = color
    return item


def rect(x1, y1, x2, y2, *, fill="white", outline="black", width=1, radius=0):
    item = {
        "type": "rectangle",
        "x_start": int(x1),
        "y_start": int(y1),
        "x_end": int(x2),
        "y_end": int(y2),
        "fill": fill,
    }
    if outline != "black":
        item["outline"] = outline
    if width != 1:
        item["width"] = max(1, int(width))
    if radius:
        item["radius"] = int(radius)
    return item


def line(x1, y1, x2, y2, *, width=1, color="black"):
    item = {
        "type": "line",
        "x_start": int(x1),
        "y_start": int(y1),
        "x_end": int(x2),
        "y_end": int(y2),
    }
    if width != 1:
        item["width"] = max(1, int(width))
    if color != "black":
        item["fill"] = color
    return item


def alert_pill(x1, y1, x2, y2, text_value, *, radius=4, icon_pad=4):
    w = x2 - x1
    h = y2 - y1
    ic_size = max(10, min(18, h - 6))
    return [
        rect(
            x1,
            y1,
            x2,
            y2,
            fill=commute_alert("bg"),
            outline=commute_alert("outline"),
            width=1,
            radius=radius,
        ),
        icon(
            x1 + icon_pad,
            y1 + (h - ic_size) // 2,
            commute_alert("icon"),
            ic_size,
            color=commute_alert("fg"),
        ),
        fit_text(
            x1 + icon_pad + ic_size + 2,
            y1 + 1,
            w - icon_pad - ic_size - 5,
            h - 2,
            text_value,
            max(9, h - 8),
            align="center",
            color=commute_alert("fg"),
        ),
    ]


# ---------------------------------------------------------------------------
# Under 4" Layouts (Today's Morning Commute Focus)
# ---------------------------------------------------------------------------


def square_200(width, height):
    """1.54" 200x200 minimalist commute briefing."""
    return [
        fit_text(8, 10, 184, 68, current("temperature"), 54, align="center", min_size=16),
        fit_text(8, 84, 88, 36, today_field("low"), 24, align="center", min_size=16),
        fit_text(104, 84, 88, 36, today_field("high"), 24, align="center", min_size=16),
        line(12, 128, 188, 128, width=1),
        fit_text(
            8,
            136,
            184,
            54,
            commute_alert("short"),
            28,
            align="center",
            color=commute_alert("safe_text_color"),
            min_size=16,
        ),
    ]


def narrow_portrait(width, height):
    """Narrow portrait tags under 4 inches (104x212 .. 152x296)."""
    tall = height >= 296
    ms = 15 if tall else 14
    pad = 4
    inner = width - 2 * pad
    temp_sz = (46 if width >= 145 else 42) if tall else (36 if width < 120 else 40)
    hilo_sz = 20 if tall else 18
    alert_sz = 22 if tall else 19
    hilo_y = round(height * 0.36)
    hilo_h = round(height * 0.18)
    box_y = round(height * 0.58)
    return [
        fit_text(
            pad,
            10,
            inner,
            hilo_y - 16,
            current("temperature"),
            temp_sz,
            min_size=ms,
        ),
        fit_text(pad, hilo_y, inner // 2 - 2, hilo_h, today_field("low"), hilo_sz, min_size=ms),
        fit_text(
            width // 2 + 2,
            hilo_y,
            inner // 2 - 2,
            hilo_h,
            today_field("high"),
            hilo_sz,
            min_size=ms,
        ),
        line(8, box_y - 2, width - 8, box_y - 2, width=1),
        fit_text(
            pad,
            box_y + 4,
            inner,
            height - box_y - 12,
            commute_alert("short"),
            alert_sz,
            color=commute_alert("safe_text_color"),
            min_size=ms,
        ),
    ]


def tall_portrait_under4(width, height):
    """Tall portrait tags under 4 inches (184x384, 240x416)."""
    tall = width >= 210
    pad = 10
    inner = width - 2 * pad
    temp_sz = 72 if tall else 62
    hilo_sz = 28 if tall else 24
    lbl_sz = 34 if tall else 28
    sub_sz = 26 if tall else 22
    ic_sz = 34 if tall else 28
    hilo_y = round(height * 0.34)
    card_top = height - 186
    div_y = card_top + 82
    return [
        fit_text(pad, 16, inner, hilo_y - 24, current("temperature"), temp_sz, min_size=16),
        fit_text(pad, hilo_y, inner // 2 - 4, 46, today_field("low"), hilo_sz, min_size=16),
        fit_text(
            width // 2 + 4,
            hilo_y,
            inner // 2 - 4,
            46,
            today_field("high"),
            hilo_sz,
            min_size=16,
        ),
        line(12, card_top, width - 12, card_top, width=1),
        icon(
            pad + 6,
            card_top + 12 + (60 - ic_sz) // 2,
            commute_alert("icon"),
            ic_sz,
            color=commute_alert("safe_text_color"),
        ),
        fit_text(
            pad + 10 + ic_sz + 4,
            card_top + 12,
            inner - ic_sz - 14,
            60,
            commute_alert("label"),
            lbl_sz,
            align="left",
            color="black",
            min_size=16,
        ),
        line(pad + 12, div_y, width - pad - 12, div_y, width=1),
        fit_text(
            pad + 8,
            div_y + 12,
            inner - 16,
            height - div_y - 30,
            commute_alert("sub"),
            sub_sz,
            min_size=16,
        ),
    ]


def compact_landscape(width, height):
    """2.1"/2.13" compact landscape (212x104, 250x122, 250x128, 250x132)."""
    small = width < 230
    mid = 114 if small else 136
    div_y = round(height * 0.54)
    temp_sz = 42 if small else 48
    hilo_sz = 22 if small else 24
    alert_sz = 24 if small else 26
    hilo_w = (width - mid - 12) // 2
    return [
        fit_text(
            6,
            4,
            mid - 12,
            div_y - 8,
            current("temperature"),
            temp_sz,
            align="center",
            min_size=16,
        ),
        fit_text(
            mid + 4,
            4,
            hilo_w,
            div_y - 8,
            today_field("low"),
            hilo_sz,
            align="center",
            min_size=16,
        ),
        fit_text(
            mid + 8 + hilo_w,
            4,
            width - mid - hilo_w - 14,
            div_y - 8,
            today_field("high"),
            hilo_sz,
            align="center",
            min_size=16,
        ),
        line(8, div_y, width - 8, div_y, width=1),
        fit_text(
            8,
            div_y + 6,
            width - 16,
            height - div_y - 12,
            commute_alert("short"),
            alert_sz,
            align="center",
            color=commute_alert("safe_text_color"),
            min_size=16,
        ),
    ]


def wide_compact_landscape(width, height):
    """2.66"/2.9" high-legibility 2-zone layout (296x128, 296x152)."""
    tall = height >= 145
    col1_end = 126
    div_y = round(height * 0.50)
    temp_sz = 56 if tall else 50
    rng_sz = 24
    lbl_sz = 28 if tall else 26
    short_sz = 24 if tall else 22
    ic_sz = 24
    return [
        fit_text(
            6,
            8,
            col1_end - 12,
            round(height * 0.54),
            current("temperature"),
            temp_sz,
            align="center",
            min_size=18,
        ),
        fit_text(
            6,
            height - 46,
            col1_end - 12,
            38,
            today_field("range"),
            rng_sz,
            align="center",
            min_size=18,
        ),
        line(col1_end, 10, col1_end, height - 10, width=1),
        icon(
            col1_end + 10,
            (div_y - ic_sz) // 2 + 2,
            commute_alert("icon"),
            ic_sz,
            color=commute_alert("safe_text_color"),
        ),
        fit_text(
            col1_end + 38,
            8,
            width - col1_end - 44,
            div_y - 14,
            commute_alert("label"),
            lbl_sz,
            align="left",
            color="black",
            min_size=18,
        ),
        line(col1_end + 8, div_y, width - 8, div_y, width=1),
        fit_text(
            col1_end + 8,
            div_y + 6,
            width - col1_end - 16,
            height - div_y - 14,
            commute_alert("short"),
            short_sz,
            align="center",
            min_size=18,
        ),
    ]


def mid_compact_landscape(width, height):
    """3.5"/3.7" minimalist split briefing (384x184, 416x240)."""
    tall = height >= 210
    mid = round(width * 0.44)
    pad = 10
    right_x = mid + pad
    right_w = width - right_x - pad
    temp_sz = 76 if tall else 64
    hilo_sz = 30 if tall else 26
    lbl_sz = 36 if tall else 30
    sub_sz = 28 if tall else 24
    ic_sz = 36 if tall else 30
    hilo_y = height - 56
    card_div_y = round(height * 0.50)
    hilo_w = (mid - 2 * pad) // 2 - 4
    return [
        fit_text(
            pad,
            12,
            mid - 2 * pad,
            hilo_y - 20,
            current("temperature"),
            temp_sz,
            align="center",
            min_size=18,
        ),
        fit_text(
            pad,
            hilo_y,
            hilo_w,
            44,
            today_field("low"),
            hilo_sz,
            align="center",
            min_size=18,
        ),
        fit_text(
            pad + hilo_w + 8,
            hilo_y,
            hilo_w,
            44,
            today_field("high"),
            hilo_sz,
            align="center",
            min_size=18,
        ),
        line(mid, 12, mid, height - 12, width=1),
        icon(
            right_x + 4,
            (card_div_y - ic_sz) // 2 + 4,
            commute_alert("icon"),
            ic_sz,
            color=commute_alert("safe_text_color"),
        ),
        fit_text(
            right_x + ic_sz + 10,
            10,
            right_w - ic_sz - 12,
            card_div_y - 16,
            commute_alert("label"),
            lbl_sz,
            align="left",
            color="black",
            min_size=18,
        ),
        line(right_x + 4, card_div_y, width - pad, card_div_y, width=1),
        fit_text(
            right_x + 4,
            card_div_y + 10,
            right_w - 8,
            height - card_div_y - 20,
            commute_alert("sub"),
            sub_sz,
            align="center",
            min_size=18,
        ),
    ]


# ---------------------------------------------------------------------------
# 4" and Above Layouts (Today Summary + 5-7 Day Weekly Forecast)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Outing briefing: verdict banner + hourly forecast (4" class and smaller wide tags)
# ---------------------------------------------------------------------------

HOUR_STEP = 3


def hourly_rows():
    return (
        f"fc_hourly[{WEATHER}].forecast | default([], true) "
        f"if fc_hourly is defined and fc_hourly[{WEATHER}] is defined else []"
    )


def hour_slot(slot):
    """Statements that set ``_t0`` (the slot's hour) and ``row`` (its hourly forecast, or empty)."""
    return (
        tag(
            f"set _t0 = now().replace(minute=0, second=0, microsecond=0) + timedelta(hours={slot * HOUR_STEP})"
        )
        + tag(f"set _hf = {hourly_rows()}")
        + tag("set _hn = namespace(r={})")
        + tag("for i in _hf")
        + tag("set t = as_datetime(i.datetime | default(none), none)")
        + tag("if t is not none and as_local(t).replace(minute=0, second=0, microsecond=0) == _t0")
        + tag("set _hn.r = i")
        + tag("break")
        + tag("endif")
        + tag("endfor")
        + tag("set row = _hn.r")
    )


def hourly(slot, key):
    prefix = hour_slot(slot)
    if key == "label":
        return prefix + expression("_t0.strftime('%H') ~ '시'")
    if key == "icon":
        return prefix + expression(
            f"'weather-' ~ {ICONS!r}.get(row.condition | default('', true), 'cloudy-alert')"
        )
    if key == "temp":
        return (
            prefix
            + tag("set _v = row.temperature | default(none)")
            + expression(_int_deg_expr("_v"))
        )
    if key == "pop":
        return (
            prefix
            + tag("set _p = row.precipitation_probability | default(none)")
            + expression(_int_pct_expr("_p"))
        )
    if key == "pop_color":
        return (
            prefix
            + tag("set _p = row.precipitation_probability | default(none)")
            + expression(
                f"{_text_ink_expr()} if is_number(_p) and _p is not boolean and (_p | float) >= 50 else 'black'"
            )
        )
    raise KeyError(key)


def hourly_series(count):
    """Statements that collect the slots' temperatures as ``_hs.vals`` (``none`` where missing)."""
    return (
        tag(f"set _hf = {hourly_rows()}")
        + tag("set _hs = namespace(vals=[])")
        + tag(f"for _k in range({count})")
        + tag(
            f"set _tt = now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=_k * {HOUR_STEP})"
        )
        + tag("set _hm = namespace(v=none)")
        + tag("for i in _hf")
        + tag("set t = as_datetime(i.datetime | default(none), none)")
        + tag("if t is not none and as_local(t).replace(minute=0, second=0, microsecond=0) == _tt")
        + tag("set _x = i.temperature | default(none)")
        + tag("if is_number(_x) and _x is not boolean")
        + tag("set _hm.v = _x | float")
        + tag("endif")
        + tag("break")
        + tag("endif")
        + tag("endfor")
        + tag("set _hs.vals = _hs.vals + [_hm.v]")
        + tag("endfor")
        + tag("set _nums = _hs.vals | reject('none') | list")
    )


def hourly_trend(count, key):
    prefix = hourly_series(count)
    if key == "values":
        return prefix + expression(f"_nums if _nums | length == {count} else []")
    if key == "min":
        return prefix + expression("(_nums | min) - 1 if _nums else 0")
    return prefix + expression("(_nums | max) + 1 if _nums else 1")


def hourly_level(count, slot):
    """How warm one slot is, 15 to 100 percent between the coldest and warmest slot."""
    return hourly_series(count) + expression(
        f"(15 + 85 * (_hs.vals[{slot}] - (_nums | min)) / ([(_nums | max) - (_nums | min), 1] | max)) "
        f"| round(0) | int if _hs.vals[{slot}] is not none else 0"
    )


def outing_sunset():
    return tag("set _s = as_datetime(state_attr('sun.sun', 'next_setting'), none)") + expression(
        "as_local(_s).strftime('%H:%M') if _s is not none and as_local(_s).date() == now().date() else '—'"
    )


def compact_wind():
    return tag(f"set _v = {weather_attribute('wind_speed')}") + expression(
        _wind_expr("_v", space=False)
    )


def banner(x1, y1, x2, y2, icon_size, label_size, *, radius, sub_size=0, sub_value=None):
    """The verdict banner: one big line, optionally a smaller line under it."""
    height = y2 - y1
    pad = 10
    text_x = x1 + pad + icon_size + 10
    items = [
        rect(
            x1,
            y1,
            x2,
            y2,
            fill=commute_alert("bg"),
            outline=commute_alert("outline"),
            radius=radius,
        ),
        icon(
            x1 + pad,
            y1 + (height - icon_size) // 2,
            commute_alert("icon"),
            icon_size,
            color=commute_alert("fg"),
        ),
    ]
    if sub_value is None:
        items.append(
            fit_text(
                text_x,
                y1 + 2,
                x2 - pad - text_x,
                height - 4,
                commute_alert("label"),
                label_size,
                align="left",
                color=commute_alert("fg"),
                min_size=14,
            )
        )
        return items
    top = y1 + (height - round(label_size * 1.3) - round(sub_size * 1.45)) // 2
    items += [
        fit_text(
            text_x,
            top,
            x2 - pad - text_x,
            round(label_size * 1.3),
            commute_alert("label"),
            label_size,
            align="left",
            color=commute_alert("fg"),
            min_size=14,
        ),
        fit_text(
            text_x,
            top + round(label_size * 1.3),
            x2 - pad - text_x,
            round(sub_size * 1.45),
            sub_value,
            sub_size,
            align="left",
            color=commute_alert("fg"),
            min_size=14,
        ),
    ]
    return items


def hourly_trend_line(x1, x2, y, height, count):
    return {
        "type": "sparkline",
        "x": int(x1),
        "y": int(y),
        "width": int(x2 - x1 + 1),
        "height": int(height),
        "values": hourly_trend(count, "values"),
        "min": hourly_trend(count, "min"),
        "max": hourly_trend(count, "max"),
        "width_line": 3,
        "dot_last": False,
    }


def outing_landscape(width, height):
    """4" landscape (400x300): title, verdict banner, six hours with a trend line, readings."""
    items = [
        fit_text(14, 4, 150, 34, "오늘 외출", 22, align="left"),
        fit_text(
            166,
            6,
            width - 14 - 166,
            30,
            tag(f"set _n = {weather_attribute('friendly_name')} or ''")
            + expression(
                "now().strftime('%m/%d') ~ ' ' ~ "
                + repr(DAYS)
                + "[now().weekday()] ~ (' · ' ~ _n if _n else '')"
            ),
            17,
            align="right",
            min_size=14,
        ),
        *banner(
            10, 42, width - 11, 106, 40, 28, radius=8, sub_size=17, sub_value=commute_alert("sub")
        ),
    ]
    centres = [40 + index * 64 for index in range(6)]
    for slot, centre in enumerate(centres):
        items += [
            fit_text(centre - 30, 112, 60, 24, hourly(slot, "label"), 16, min_size=14),
            icon(centre - 14, 138, hourly(slot, "icon"), 28),
            fit_text(centre - 30, 206, 60, 30, hourly(slot, "temp"), 20, min_size=16),
            fit_text(
                centre - 30,
                236,
                60,
                26,
                hourly(slot, "pop"),
                17,
                color=hourly(slot, "pop_color"),
                min_size=14,
            ),
        ]
    items.append(hourly_trend_line(centres[0], centres[-1], 174, 28, 6))
    items.append(line(10, 264, width - 10, 264, width=2))
    readings = (
        ("thermometer", current("feels", prefix="체감 ")),
        ("water-percent", current("humidity")),
        ("weather-windy", compact_wind()),
        ("weather-sunset-down", outing_sunset()),
    )
    for index, (glyph, value) in enumerate(readings):
        x = 12 + index * 96
        items += [
            icon(x, 274, glyph, 20),
            fit_text(x + 24, 270, 68, 28, value, 17, align="left", min_size=14),
        ]
    return items


def outing_portrait(width, height):
    """4" portrait (300x400): the same briefing stacked, hours as a list."""
    items = [
        fit_text(12, 4, 120, 34, "오늘 외출", 21, align="left"),
        fit_text(
            134,
            6,
            width - 12 - 134,
            30,
            tag(f"set _n = {weather_attribute('friendly_name')} or ''")
            + expression(
                "now().strftime('%m/%d') ~ ' ' ~ "
                + repr(DAYS)
                + "[now().weekday()] ~ (' · ' ~ _n if _n else '')"
            ),
            16,
            align="right",
            min_size=14,
        ),
        *banner(
            8, 42, width - 9, 110, 36, 26, radius=8, sub_size=16, sub_value=commute_alert("sub")
        ),
    ]
    top = 118
    pitch = 36
    for slot in range(6):
        y = top + slot * pitch
        items += [
            fit_text(10, y, 50, pitch - 2, hourly(slot, "label"), 18, align="left", min_size=14),
            icon(62, y + 4, hourly(slot, "icon"), 26),
            fit_text(94, y, 56, pitch - 2, hourly(slot, "temp"), 20, min_size=16),
            fit_text(
                152,
                y,
                52,
                pitch - 2,
                hourly(slot, "pop"),
                17,
                color=hourly(slot, "pop_color"),
                min_size=14,
            ),
            {
                "type": "progress_bar",
                "x_start": 212,
                "y_start": y + 10,
                "x_end": width - 12,
                "y_end": y + 22,
                "progress": hourly_level(6, slot),
                "fill": "black",
                "background": "white",
                "outline": "black",
                "radius": 4,
            },
        ]
    items.append(line(10, 336, width - 10, 336, width=2))
    readings = (
        ("thermometer", current("feels", prefix="체감 ")),
        ("water-percent", current("humidity")),
        ("weather-windy", compact_wind()),
        ("weather-sunset-down", outing_sunset()),
    )
    for index, (glyph, value) in enumerate(readings):
        x = 12 + (index % 2) * 144
        y = 342 + (index // 2) * 29
        items += [
            icon(x, y + 4, glyph, 20),
            fit_text(x + 24, y, 112, 28, value, 17, align="left", min_size=14),
        ]
    return items


def outing_wide(width, height):
    """Wide, short tags (296 wide and up): the verdict banner above four hours."""
    pad = 6
    banner_height = round(height * 0.4)
    ic = min(banner_height - 14, 36)
    items = banner(
        pad,
        pad,
        width - pad - 1,
        pad + banner_height,
        ic,
        min(banner_height - 16, 26),
        radius=6,
    )
    top = pad + banner_height + 4
    room = height - top - 2
    hour_height = 18 if room < 80 else (20 if room < 120 else 22)
    temp_height = 24 if room < 80 else (28 if room < 120 else 30)
    pop_height = 20 if room >= 96 else 0
    icon_size = min(room - hour_height - temp_height - pop_height, 40)
    column = (width - 2 * pad) / 4
    for slot in range(4):
        left = pad + slot * column
        centre = left + column / 2
        y = top
        items.append(
            fit_text(
                left,
                y,
                column,
                hour_height,
                hourly(slot, "label"),
                min(16, hour_height - 4),
                min_size=14,
            )
        )
        y += hour_height
        items.append(icon(centre - icon_size / 2, y, hourly(slot, "icon"), icon_size))
        y += icon_size
        items.append(
            fit_text(
                left,
                y,
                column,
                temp_height,
                hourly(slot, "temp"),
                min(20, temp_height - 4),
                min_size=14,
            )
        )
        if pop_height:
            items.append(
                fit_text(
                    left,
                    y + temp_height,
                    column,
                    pop_height,
                    hourly(slot, "pop"),
                    14,
                    color=hourly(slot, "pop_color"),
                    min_size=14,
                )
            )
    return items


def outing_header(width, sx, sy, s, *, stacked):
    place = tag(f"set _n = {weather_attribute('friendly_name')} or ''") + expression(
        "now().strftime('%m/%d') ~ ' ' ~ "
        + repr(DAYS)
        + "[now().weekday()] ~ (' · ' ~ _n if _n else '') ~ now().strftime('  %H:%M')"
    )
    if stacked:
        return [
            fit_text(20 * sx, 10 * sy, 440 * sx, 46 * s, "오늘 외출", 36 * s, align="left"),
            fit_text(
                20 * sx, 56 * sy, 440 * sx, 36 * s, place, 24 * s, align="left", min_size=18 * s
            ),
        ]
    return [
        fit_text(24 * sx, 10 * sy, 300 * sx, 50 * s, "오늘 외출", 34 * s, align="left"),
        fit_text(
            330 * sx,
            14 * sy,
            width - 24 * sx - 330 * sx,
            42 * s,
            place,
            26 * s,
            align="right",
            min_size=20 * s,
        ),
    ]


def outing_readings():
    return (
        ("thermometer", "체감", current("feels")),
        ("water-percent", "습도", current("humidity")),
        ("weather-windy", "바람", current("wind")),
        ("weather-sunset-down", "일몰", outing_sunset()),
    )


def outing_large_landscape(width, height):
    """7.5" and up landscape: banner, eight hours with a trend line and four readings."""
    sx, sy = width / 800, height / 480
    s = min(sx, sy)
    items = outing_header(width, sx, sy, s, stacked=False)
    items += banner(
        16 * sx,
        70 * sy,
        width - 17 * sx,
        164 * sy,
        round(64 * s),
        round(44 * s),
        radius=round(12 * s),
        sub_size=round(24 * s),
        sub_value=commute_alert("sub"),
    )
    centres = [(70 + 94 * index) * sx for index in range(8)]
    for slot, centre in enumerate(centres):
        half = 47 * sx - 2
        items += [
            fit_text(
                centre - half,
                174 * sy,
                2 * half,
                34 * s,
                hourly(slot, "label"),
                22 * s,
                min_size=18 * s,
            ),
            icon(centre - 20 * s, 212 * sy, hourly(slot, "icon"), 40 * s),
            fit_text(
                centre - half,
                316 * sy,
                2 * half,
                42 * s,
                hourly(slot, "temp"),
                28 * s,
                min_size=22 * s,
            ),
            fit_text(
                centre - half,
                358 * sy,
                2 * half,
                34 * s,
                hourly(slot, "pop"),
                22 * s,
                color=hourly(slot, "pop_color"),
                min_size=18 * s,
            ),
        ]
    trend = hourly_trend_line(centres[0], centres[-1], 262 * sy, 50 * sy, 8)
    trend["width_line"] = max(2, round(4 * s))
    items.append(trend)
    items.append(rect(16 * sx, 392 * sy, width - 17 * sx, 392 * sy + max(2, 2 * s), fill="black"))
    for index, (glyph, label, value) in enumerate(outing_readings()):
        x = (30 + 192 * index) * sx
        if index:
            items.append(line(x - 12 * sx, 408 * sy, x - 12 * sx, 466 * sy))
        items += [
            icon(x, 419 * sy, glyph, 34 * s),
            fit_text(
                x + 42 * s, 402 * sy, 134 * sx, 32 * s, label, 20 * s, align="left", min_size=18 * s
            ),
            fit_text(
                x + 42 * s, 436 * sy, 134 * sx, 42 * s, value, 28 * s, align="left", min_size=22 * s
            ),
        ]
    return items


def outing_large_portrait(width, height):
    """7.5" and up portrait: banner, eight hours as rows with a warmth bar, readings in a grid."""
    sx, sy = width / 480, height / 800
    s = min(sx, sy)
    items = outing_header(width, sx, sy, s, stacked=True)
    items += banner(
        16 * sx,
        100 * sy,
        width - 17 * sx,
        220 * sy,
        round(64 * s),
        round(40 * s),
        radius=round(12 * s),
        sub_size=round(22 * s),
        sub_value=commute_alert("sub"),
    )
    pitch = 48 * sy
    for slot in range(8):
        y = 234 * sy + slot * pitch
        items += [
            fit_text(
                20 * sx,
                y,
                80 * sx,
                pitch - 2,
                hourly(slot, "label"),
                24 * s,
                align="left",
                min_size=18 * s,
            ),
            icon(108 * sx, y + (pitch - 36 * s) / 2, hourly(slot, "icon"), 36 * s),
            fit_text(
                156 * sx, y, 76 * sx, pitch - 2, hourly(slot, "temp"), 28 * s, min_size=22 * s
            ),
            fit_text(
                236 * sx,
                y,
                72 * sx,
                pitch - 2,
                hourly(slot, "pop"),
                24 * s,
                color=hourly(slot, "pop_color"),
                min_size=18 * s,
            ),
            {
                "type": "progress_bar",
                "x_start": int(320 * sx),
                "y_start": int(y + pitch / 2 - 8 * s),
                "x_end": int(width - 20 * sx),
                "y_end": int(y + pitch / 2 + 8 * s),
                "progress": hourly_level(8, slot),
                "fill": "black",
                "background": "white",
                "outline": "black",
                "radius": int(6 * s),
            },
        ]
    items.append(rect(16 * sx, 626 * sy, width - 17 * sx, 626 * sy + max(2, 2 * s), fill="black"))
    for index, (glyph, label, value) in enumerate(outing_readings()):
        x = (20 + (index % 2) * 232) * sx
        y = (640 + (index // 2) * 80) * sy
        if index % 2:
            items.append(line(x - 14 * sx, y, x - 14 * sx, y + 64 * sy))
        items += [
            icon(x, y + 14 * sy, glyph, 34 * s),
            fit_text(x + 46 * s, y, 170 * sx, 30 * s, label, 20 * s, align="left", min_size=18 * s),
            fit_text(
                x + 46 * s,
                y + 30 * sy,
                170 * sx,
                42 * s,
                value,
                28 * s,
                align="left",
                min_size=22 * s,
            ),
        ]
    return items


class FlowElement(dict):
    """Write each layout item in compact YAML flow style."""


class TemplateDumper(yaml.SafeDumper):
    """Share repeated Jinja strings across bundled layouts as scalar aliases."""

    def ignore_aliases(self, data):
        return not (isinstance(data, str) and len(data) > 40 and "{" in data)

    def represent_element(self, element):
        return self.represent_mapping("tag:yaml.org,2002:map", element, flow_style=True)


TemplateDumper.add_representer(FlowElement, TemplateDumper.represent_element)


def generate():
    layouts = {}
    profiles = (
        (square_200, ((200, 200),)),
        (narrow_portrait, ((104, 212), (122, 250), (128, 250), (132, 250), (128, 296), (152, 296))),
        (tall_portrait_under4, ((184, 384), (240, 416))),
        (compact_landscape, ((212, 104), (250, 122), (250, 128), (250, 132))),
        (outing_wide, ((296, 128), (296, 152), (384, 184), (416, 240))),
        (outing_landscape, ((400, 300),)),
        (outing_portrait, ((300, 400),)),
        (outing_large_landscape, ((648, 480), (800, 480), (960, 640), (960, 680), (1600, 1200))),
        (outing_large_portrait, ((480, 648), (480, 800), (640, 960), (680, 960), (1200, 1600))),
    )
    for builder, resolutions in profiles:
        for width, height in resolutions:
            layouts[f"{width}x{height}"] = [
                FlowElement(
                    {
                        key: sys.intern(value) if isinstance(value, str) and "{" in value else value
                        for key, value in item.items()
                    }
                )
                for item in builder(width, height)
            ]

    data = {
        "template": 1,
        "id": "weather_commute",
        "categories": ["weather"],
        "name": {"en": "Outing weather", "ko": "외출 날씨 브리핑"},
        "description": {
            "en": (
                "Outing briefing with an umbrella, snow, temperature-gap or wind verdict and an "
                "hourly forecast on 4-inch tags, a compact version on smaller tags and the weekly "
                "forecast on the largest. The automation fetches the daily and hourly forecasts."
            ),
            "ko": (
                "4인치 태그에는 우산·눈·일교차·강풍 판정과 시간대별 예보를, 더 작은 태그에는 "
                "간단한 브리핑을, 가장 큰 태그에는 주간 예보를 표시합니다. "
                "자동화가 일별·시간별 예보를 가져옵니다."
            ),
        },
        "background": "white",
        "parameters": {
            "weather": {
                "type": "entity",
                "domain": "weather",
                "default": "weather.home",
                "label": {"en": "Weather entity", "ko": "날씨 엔티티"},
            },
            "accent": {
                "type": "color",
                "default": "red",
                "label": {"en": "Alert & weekend color", "ko": "비·눈 및 주말 강조 색상"},
            },
            "font": {
                "type": "font",
                "default": "NotoSansKR-Bold.ttf",
                "label": {"en": "Font", "ko": "글꼴"},
            },
            "interval": {
                "type": "select",
                "group": "automation",
                "options": ["1", "3", "6"],
                "default": "1",
                "label": {"en": "Update every (hours)", "ko": "갱신 주기 (시간)"},
            },
        },
        "layouts": layouts,
        "automation": {
            "triggers": [{"trigger": "time_pattern", "hours": "/${interval}", "minutes": "0"}],
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
    return "# Generated by scripts/generate_commute_weather_template.py\n" + yaml.dump(
        data, Dumper=TemplateDumper, allow_unicode=True, sort_keys=False, width=4096
    )


if __name__ == "__main__":
    DESTINATION.write_text(generate(), encoding="utf-8")
