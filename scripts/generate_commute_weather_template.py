#!/usr/bin/env python3
"""Regenerate the built-in morning commute & weekly weather template at every supported size."""

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
    return f"('black' if {ACCENT!r} in ('yellow', 'white') else 'white')"


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
    extra_check3 = (
        extra_sub
        + tag(f"set _h = {weather_attribute('humidity')}")
        + tag(f"set _hstr = {_int_pct_expr('_h')}")
    )
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
        "check1": (
            setup,
            "('• 눈 예보 · 미끄럼 주의' ~ (' (' ~ _pv ~ '%)' if _pv is not none else '')) if _kind == 'snow' "
            "else (('• 우산 필수' ~ (' (' ~ _pv ~ '%)' if _pv is not none else '')) if _kind == 'rain' "
            "else (('• 우산 불필요' ~ (' (강수 ' ~ _pv ~ '%)' if _pv is not none else '')) if _kind == 'ok' else '• 예보 정보 없음'))",
        ),
        "check2": (
            setup,
            "'• 두꺼운 방한 외투 · 장갑' if _kind == 'snow' "
            "else ('• 방수 겉옷 추천' if _kind == 'rain' "
            "else (('• 일교차 ' ~ _gap ~ '° · 겉옷 챙기기') if _kind == 'gap' "
            "else ('• 방풍 재킷 추천' if _kind == 'wind' "
            "else ('• 가벼운 외출복 추천' if _kind == 'ok' else '• 날씨 예보를 기다리는 중'))))",
        ),
        "check3": (
            setup + extra_check3,
            "('• 강수량 ' ~ _amt_str ~ ' · ' if _amt_str else '• ') ~ '체감 ' ~ _fstr ~ ' · 습도 ' ~ _hstr",
        ),
    }
    prefix, expr = outputs[key]
    return prefix + expression(expr)


def forecast_day(day_offset, key):
    date_expr = f"(now().date() + timedelta(days={day_offset}))"
    ink = _accent_ink_expr()
    fg = _accent_fg_expr()
    if key == "weekday":
        return expression(f"{DAYS!r}[{date_expr}.weekday()]")
    if key == "date":
        return expression(f"{date_expr}.strftime('%m/%d')")
    if key == "day_color":
        return expression(f"{ink} if {date_expr}.weekday() >= 5 else 'black'")
    prefix = select_forecast(day_offset)
    if key == "icon":
        return prefix + expression(
            f"'weather-' ~ {ICONS!r}.get(row.condition | default('', true), 'cloudy-alert')"
        )
    if key == "cond_text":
        return prefix + expression(f"{CONDITIONS!r}.get(row.condition | default('', true), '—')")
    if key == "high":
        return (
            prefix
            + tag("set _v = row.temperature | default(none)")
            + expression(_int_deg_expr("_v"))
        )
    if key == "low":
        return (
            prefix + tag("set _v = row.templow | default(none)") + expression(_int_deg_expr("_v"))
        )
    if key == "pop":
        return (
            prefix
            + tag("set _p = row.precipitation_probability | default(none)")
            + expression(_int_pct_expr("_p"))
        )
    if key == "wet_color":
        return (
            prefix
            + tag("set _c = row.condition | default('')")
            + tag("set _p = row.precipitation_probability | default(none)")
            + expression(
                f"{ink} if (_c in {WET!r}) or (is_number(_p) and _p is not boolean and (_p | float) >= 40) else 'black'"
            )
        )
    if key == "pop_bg":
        return (
            prefix
            + tag("set _p = row.precipitation_probability | default(none)")
            + expression(
                f"{ink} if is_number(_p) and _p is not boolean and (_p | float) >= 40 else 'white'"
            )
        )
    if key == "pop_fg":
        return (
            prefix
            + tag("set _p = row.precipitation_probability | default(none)")
            + expression(
                f"{fg} if is_number(_p) and _p is not boolean and (_p | float) >= 40 else 'black'"
            )
        )
    raise KeyError(key)


def weekly_summary(days_count):
    return (
        tag(
            f"set _list = fc[{WEATHER}].forecast | default([], true) "
            f"if fc is defined and fc[{WEATHER}] is defined else []"
        )
        + tag("set _ns = namespace(items=[], has_dt=false)")
        + tag("for _i in _list")
        + tag("if as_datetime(_i.datetime | default(none), none) is not none")
        + tag("set _ns.has_dt = true")
        + tag("break")
        + tag("endif")
        + tag("endfor")
        + tag(f"for _off in range(1, {days_count + 1})")
        + tag("set _target = now().date() + timedelta(days=_off)")
        + tag("set _row = namespace(v={})")
        + tag("if _ns.has_dt")
        + tag("for _i in _list")
        + tag("set _dt = as_datetime(_i.datetime | default(none), none)")
        + tag("if _dt is not none and as_local(_dt).date() == _target")
        + tag("set _row.v = _i")
        + tag("break")
        + tag("endif")
        + tag("endfor")
        + tag("elif _list | length > _off")
        + tag("set _row.v = _list[_off]")
        + tag("endif")
        + tag("set _r = _row.v")
        + tag("set _p = _r.precipitation_probability | default(none)")
        + tag(
            "set _pv = (_p | float | round(0) | int) if is_number(_p) and _p is not boolean else none"
        )
        + tag("set _c = _r.condition | default('')")
        + tag(f"if (_c in {WET!r}) or (_pv is not none and _pv >= 40)")
        + tag(
            f"set _lbl = {DAYS!r}[_target.weekday()] ~ ('(' ~ _pv ~ '%)' if _pv is not none else '')"
        )
        + tag("set _ns.items = _ns.items + [_lbl]")
        + tag("endif")
        + tag("endfor")
        + expression(
            "'주간 비·눈: ' ~ (_ns.items[:3] | join(' · ')) if _ns.items else '주간 비·눈 예보 없음'"
        )
    )


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


def weekly_columns(start_x, top_y, total_w, bottom_y, count, *, show_dates=False, show_cond=False):
    """Build equal-width daily forecast columns for 5, 6, or 7 days within exact vertical bounds."""
    items = []
    col_w = total_w / count
    avail_h = bottom_y - top_y
    day_h = max(14, round(avail_h * 0.11))
    date_h = max(12, round(avail_h * 0.08)) if show_dates else 0
    pop_h = max(16, round(avail_h * 0.12))
    hi_h = max(16, round(avail_h * 0.15))
    lo_h = max(14, round(avail_h * 0.12))
    cond_h = max(13, round(avail_h * 0.10)) if show_cond else 0
    gap = max(2, round(avail_h * 0.02))
    num_gaps = 6 if show_cond else 5
    if show_dates:
        num_gaps += 1
    fixed_h = day_h + date_h + pop_h + hi_h + lo_h + cond_h + num_gaps * gap + 4
    ic_sz = max(20, min(round(col_w * 0.65), avail_h - fixed_h))

    used_h = fixed_h + ic_sz
    extra_gap = max(0, (avail_h - used_h) // 4)
    y = top_y + 2
    day_y = y
    y += day_h + (gap if show_dates else 0)
    date_y = y
    y += (date_h + gap + extra_gap) if show_dates else (gap + extra_gap)
    ic_y = y
    y += ic_sz + gap + extra_gap
    pop_y = y
    y += pop_h + gap + extra_gap
    hi_y = y
    y += hi_h + gap
    lo_y = y
    y += lo_h + gap
    cond_y = y

    for idx in range(count):
        day_offset = idx + 1
        x0 = round(start_x + idx * col_w)
        x1 = round(start_x + (idx + 1) * col_w)
        w = x1 - x0
        cx = (x0 + x1) // 2
        if idx > 0:
            items.append(line(x0, top_y + 2, x0, bottom_y - 2, width=1))
        items.append(
            fit_text(
                x0 + 2,
                day_y,
                w - 4,
                day_h,
                forecast_day(day_offset, "weekday"),
                max(12, day_h - 2),
                color=forecast_day(day_offset, "day_color"),
            )
        )
        if show_dates:
            items.append(
                fit_text(
                    x0 + 2,
                    date_y,
                    w - 4,
                    date_h,
                    forecast_day(day_offset, "date"),
                    max(10, date_h - 2),
                )
            )
        items.append(
            icon(
                cx,
                ic_y,
                forecast_day(day_offset, "icon"),
                ic_sz,
                anchor="mt",
                color=forecast_day(day_offset, "wet_color"),
            )
        )
        pill_pad = max(4, round(w * 0.12))
        items.extend(
            [
                rect(
                    x0 + pill_pad,
                    pop_y,
                    x1 - pill_pad,
                    pop_y + pop_h,
                    fill=forecast_day(day_offset, "pop_bg"),
                    outline=forecast_day(day_offset, "wet_color"),
                    width=1,
                    radius=3,
                ),
                fit_text(
                    x0 + pill_pad + 2,
                    pop_y + 1,
                    w - 2 * pill_pad - 4,
                    pop_h - 2,
                    forecast_day(day_offset, "pop"),
                    max(10, pop_h - 4),
                    color=forecast_day(day_offset, "pop_fg"),
                ),
                fit_text(
                    x0 + 2, hi_y, w - 4, hi_h, forecast_day(day_offset, "high"), max(13, hi_h - 2)
                ),
                fit_text(
                    x0 + 2, lo_y, w - 4, lo_h, forecast_day(day_offset, "low"), max(11, lo_h - 2)
                ),
            ]
        )
        if show_cond:
            items.append(
                fit_text(
                    x0 + 2,
                    cond_y,
                    w - 4,
                    cond_h,
                    forecast_day(day_offset, "cond_text"),
                    max(10, cond_h - 3),
                )
            )
    return items


def weekly_5day_landscape(width, height):
    """4.2" & 5.8" landscape (400x300, 648x480): today commute summary + 5-day forecast."""
    sx, sy = width / 400, height / 300

    def rx(v):
        return round(v * sx)

    def ry(v):
        return round(v * sy)

    pad = rx(10)
    return [
        fit_text(pad, ry(8), rx(220), ry(26), current("date"), round(16 * sy), align="left"),
        *alert_pill(
            rx(238), ry(8), width - pad, ry(33), commute_alert("label"), radius=4, icon_pad=rx(4)
        ),
        icon(rx(14), ry(46), current("icon"), round(62 * min(sx, sy))),
        fit_text(
            rx(80), ry(44), rx(96), ry(54), current("temperature"), round(44 * sy), align="right"
        ),
        fit_text(
            rx(80), ry(98), rx(96), ry(22), current("condition"), round(14 * sy), align="right"
        ),
        line(rx(182), ry(44), rx(182), ry(124), width=1),
        fit_text(rx(190), ry(44), rx(92), ry(22), today_field("low"), round(15 * sy), align="left"),
        fit_text(
            rx(190),
            ry(67),
            rx(92),
            ry(22),
            today_field("high"),
            round(15 * sy),
            align="left",
            color=ACCENT_INK,
        ),
        fit_text(
            rx(190),
            ry(92),
            rx(92),
            ry(22),
            current("feels", prefix="체감 "),
            round(13 * sy),
            align="left",
        ),
        rect(
            rx(288), ry(44), width - pad, ry(124), fill="white", outline="black", width=1, radius=5
        ),
        fit_text(
            rx(294),
            ry(48),
            rx(92),
            ry(23),
            today_field("pop", prefix="강수 "),
            round(12 * sy),
            align="left",
            color=today_field("pop_color"),
        ),
        fit_text(
            rx(294),
            ry(73),
            rx(92),
            ry(23),
            current("humidity", prefix="습도 "),
            round(12 * sy),
            align="left",
        ),
        fit_text(
            rx(294),
            ry(98),
            rx(92),
            ry(23),
            current("wind", prefix="바람 "),
            round(12 * sy),
            align="left",
        ),
        line(pad, ry(136), width - pad, ry(136), width=max(1, round(2 * sy))),
        fit_text(
            pad, ry(141), rx(200), ry(20), "주간 날씨 예보 (5일)", round(13 * sy), align="left"
        ),
        fit_text(
            rx(210),
            ry(141),
            width - pad - rx(210),
            ry(20),
            "주말·강수 40%↑ 강조",
            round(11 * sy),
            align="right",
        ),
        *weekly_columns(pad, ry(164), width - 2 * pad, height - ry(8), 5, show_dates=width >= 600),
    ]


def weekly_5day_portrait(width, height):
    """4.2" & 5.8" portrait (300x400, 480x648): today commute summary + 5-day forecast."""
    sx, sy = width / 300, height / 400

    def rx(v):
        return round(v * sx)

    def ry(v):
        return round(v * sy)

    pad = rx(10)
    inner = width - 2 * pad
    return [
        fit_text(pad, ry(10), rx(140), ry(24), current("date"), round(16 * sy), align="left"),
        *alert_pill(
            rx(154), ry(10), width - pad, ry(35), commute_alert("label"), radius=4, icon_pad=rx(4)
        ),
        icon(rx(16), ry(48), current("icon"), round(64 * min(sx, sy))),
        fit_text(
            rx(88), ry(44), rx(196), ry(52), current("temperature"), round(44 * sy), align="right"
        ),
        fit_text(
            rx(88), ry(96), rx(196), ry(22), current("condition"), round(14 * sy), align="right"
        ),
        fit_text(
            pad, ry(124), inner // 2 - 4, ry(26), today_field("low"), round(16 * sy), align="left"
        ),
        fit_text(
            pad + inner // 2 + 4,
            ry(124),
            inner // 2 - 4,
            ry(26),
            today_field("high"),
            round(16 * sy),
            align="right",
            color=ACCENT_INK,
        ),
        rect(pad, ry(154), width - pad, ry(186), fill="white", outline="black", width=1, radius=4),
        fit_text(
            pad + 6,
            ry(158),
            inner // 3 - 8,
            ry(24),
            current("feels", prefix="체감 "),
            round(12 * sy),
            align="left",
        ),
        fit_text(
            pad + inner // 3 + 2,
            ry(158),
            inner // 3 - 4,
            ry(24),
            current("humidity", prefix="습도 "),
            round(12 * sy),
        ),
        fit_text(
            pad + 2 * (inner // 3) + 2,
            ry(158),
            inner // 3 - 8,
            ry(24),
            today_field("pop", prefix="강수 "),
            round(12 * sy),
            align="right",
            color=today_field("pop_color"),
        ),
        line(pad, ry(196), width - pad, ry(196), width=max(1, round(2 * sy))),
        fit_text(pad, ry(202), inner, ry(22), "주간 날씨 예보 (5일)", round(14 * sy), align="left"),
        *weekly_columns(pad, ry(226), inner, height - ry(10), 5, show_dates=height >= 600),
    ]


def dashboard_6day_landscape(width, height):
    """7.5" landscape (800x480): left today commute dashboard + right 6-day forecast."""
    left_w = 286
    div_x = 304
    right_x = 322
    pad = 16
    return [
        fit_text(pad, 14, 150, 28, current("date"), 20, align="left"),
        rect(176, 14, left_w, 40, fill="white", outline="black", width=1, radius=4),
        fit_text(180, 16, left_w - 184, 22, "오늘 출근 브리핑", 12),
        icon(pad + 4, 58, current("icon"), 84),
        fit_text(104, 54, left_w - 104, 68, current("temperature"), 60, align="right"),
        fit_text(104, 122, left_w - 104, 24, current("condition"), 18, align="right"),
        fit_text(pad, 154, 128, 26, today_field("low"), 17, align="left"),
        fit_text(146, 154, 140, 26, today_field("high"), 17, align="right", color=ACCENT_INK),
        rect(pad, 190, 146, 232, fill="white", outline="black", width=1, radius=5),
        fit_text(pad + 8, 194, 116, 34, current("feels", prefix="체감  "), 14, align="left"),
        rect(156, 190, left_w, 232, fill="white", outline="black", width=1, radius=5),
        fit_text(
            164,
            194,
            114,
            34,
            today_field("pop", prefix="강수  "),
            14,
            align="left",
            color=today_field("pop_color"),
        ),
        rect(pad, 240, 146, 282, fill="white", outline="black", width=1, radius=5),
        fit_text(pad + 8, 244, 116, 34, current("humidity", prefix="습도  "), 14, align="left"),
        rect(156, 240, left_w, 282, fill="white", outline="black", width=1, radius=5),
        fit_text(164, 244, 114, 34, current("wind", prefix="바람  "), 13, align="left"),
        rect(
            pad,
            298,
            left_w,
            height - 16,
            fill="white",
            outline=commute_alert("outline"),
            width=2,
            radius=6,
        ),
        rect(
            pad,
            298,
            left_w,
            334,
            fill=commute_alert("bg"),
            outline=commute_alert("outline"),
            width=1,
            radius=6,
        ),
        icon(pad + 10, 305, commute_alert("icon"), 22, color=commute_alert("fg")),
        fit_text(
            pad + 38,
            302,
            left_w - pad - 44,
            28,
            commute_alert("label"),
            16,
            align="left",
            color=commute_alert("fg"),
        ),
        fit_text(pad + 10, 346, left_w - pad - 18, 32, commute_alert("check1"), 14, align="left"),
        fit_text(pad + 10, 384, left_w - pad - 18, 32, commute_alert("check2"), 14, align="left"),
        fit_text(pad + 10, 422, left_w - pad - 18, 32, commute_alert("check3"), 13, align="left"),
        line(div_x, 16, div_x, height - 16, width=2),
        fit_text(right_x, 14, 190, 30, "주간 예보 (6일)", 20, align="left"),
        rect(522, 14, width - pad, 42, fill="white", outline=ACCENT_INK, width=1, radius=4),
        fit_text(528, 16, width - pad - 534, 24, weekly_summary(6), 13, color=ACCENT_INK),
        line(right_x, 54, width - pad, 54, width=1),
        *weekly_columns(
            right_x, 62, width - right_x - pad, height - 16, 6, show_dates=True, show_cond=True
        ),
    ]


def dashboard_6day_portrait(width, height):
    """7.5" portrait (480x800): top today commute dashboard + bottom 6-day forecast."""
    pad = 16
    inner = width - 2 * pad
    return [
        fit_text(pad, 14, 200, 30, current("date"), 22, align="left"),
        *alert_pill(240, 14, width - pad, 44, commute_alert("label"), radius=5, icon_pad=6),
        icon(pad + 6, 58, current("icon"), 92),
        fit_text(120, 54, 150, 74, current("temperature"), 64, align="right"),
        fit_text(120, 128, 150, 24, current("condition"), 18, align="right"),
        fit_text(286, 60, 178, 28, today_field("low"), 18, align="left"),
        fit_text(286, 90, 178, 28, today_field("high"), 18, align="left", color=ACCENT_INK),
        fit_text(286, 122, 178, 26, current("feels", prefix="체감  "), 15, align="left"),
        rect(pad, 166, 156, 206, fill="white", outline="black", width=1, radius=4),
        fit_text(
            pad + 8,
            170,
            126,
            32,
            today_field("pop", prefix="강수  "),
            14,
            align="left",
            color=today_field("pop_color"),
        ),
        rect(166, 166, 314, 206, fill="white", outline="black", width=1, radius=4),
        fit_text(174, 170, 132, 32, current("humidity", prefix="습도  "), 14, align="left"),
        rect(324, 166, width - pad, 206, fill="white", outline="black", width=1, radius=4),
        fit_text(332, 170, 124, 32, current("wind", prefix="바람  "), 13, align="left"),
        rect(
            pad,
            218,
            width - pad,
            342,
            fill="white",
            outline=commute_alert("outline"),
            width=1,
            radius=6,
        ),
        fit_text(pad + 12, 226, inner - 24, 30, commute_alert("check1"), 15, align="left"),
        fit_text(pad + 12, 264, inner - 24, 30, commute_alert("check2"), 15, align="left"),
        fit_text(pad + 12, 302, inner - 24, 30, commute_alert("check3"), 14, align="left"),
        line(pad, 360, width - pad, 360, width=2),
        fit_text(pad, 372, 180, 28, "주간 예보 (6일)", 20, align="left"),
        rect(206, 372, width - pad, 400, fill="white", outline=ACCENT_INK, width=1, radius=4),
        fit_text(212, 374, width - pad - 218, 24, weekly_summary(6), 13, color=ACCENT_INK),
        *weekly_columns(pad, 410, inner, height - 16, 6, show_dates=True, show_cond=True),
    ]


def dashboard_7day_landscape(width, height):
    """10.2"+ landscape (960x640, 960x680, 1600x1200): top hero + bottom 7-day forecast."""
    sx, sy = width / 960, height / 640

    def rx(v):
        return round(v * sx)

    def ry(v):
        return round(v * sy)

    pad = rx(20)
    return [
        fit_text(pad, ry(16), rx(320), ry(30), current("full_date"), round(22 * sy), align="left"),
        fit_text(
            pad,
            ry(46),
            rx(320),
            ry(22),
            "아침 출근 · 주간 날씨 브리핑",
            round(14 * sy),
            align="left",
        ),
        icon(pad + rx(4), ry(80), current("icon"), round(100 * min(sx, sy))),
        fit_text(
            rx(136), ry(76), rx(144), ry(82), current("temperature"), round(72 * sy), align="right"
        ),
        fit_text(
            rx(284), ry(110), rx(72), ry(36), current("condition"), round(22 * sy), align="left"
        ),
        line(rx(364), ry(20), rx(364), ry(204), width=max(1, round(2 * sx))),
        fit_text(
            rx(382), ry(18), rx(122), ry(30), today_field("low"), round(20 * sy), align="left"
        ),
        fit_text(
            rx(512),
            ry(18),
            rx(122),
            ry(30),
            today_field("high"),
            round(20 * sy),
            align="left",
            color=ACCENT_INK,
        ),
        fit_text(
            rx(382),
            ry(52),
            rx(252),
            ry(26),
            current("feels", prefix="체감온도  "),
            round(16 * sy),
            align="left",
        ),
        rect(rx(382), ry(88), rx(504), ry(140), fill="white", outline="black", width=1, radius=6),
        fit_text(
            rx(392),
            ry(92),
            rx(102),
            ry(44),
            today_field("pop", prefix="강수 "),
            round(16 * sy),
            align="left",
            color=today_field("pop_color"),
        ),
        rect(rx(514), ry(88), rx(636), ry(140), fill="white", outline="black", width=1, radius=6),
        fit_text(
            rx(524),
            ry(92),
            rx(102),
            ry(44),
            current("humidity", prefix="습도 "),
            round(16 * sy),
            align="left",
        ),
        rect(rx(382), ry(150), rx(636), ry(202), fill="white", outline="black", width=1, radius=6),
        fit_text(
            rx(392),
            ry(154),
            rx(234),
            ry(44),
            current("wind", prefix="바람  "),
            round(16 * sy),
            align="left",
        ),
        rect(
            rx(656),
            ry(18),
            width - pad,
            ry(204),
            fill="white",
            outline=commute_alert("outline"),
            width=max(1, round(2 * sx)),
            radius=8,
        ),
        rect(
            rx(656),
            ry(18),
            width - pad,
            ry(62),
            fill=commute_alert("bg"),
            outline=commute_alert("outline"),
            width=1,
            radius=8,
        ),
        icon(
            rx(670),
            ry(27),
            commute_alert("icon"),
            round(26 * min(sx, sy)),
            color=commute_alert("fg"),
        ),
        fit_text(
            rx(704),
            ry(22),
            width - pad - rx(712),
            ry(36),
            commute_alert("label"),
            round(18 * sy),
            align="left",
            color=commute_alert("fg"),
        ),
        fit_text(
            rx(670),
            ry(76),
            width - pad - rx(682),
            ry(34),
            commute_alert("check1"),
            round(15 * sy),
            align="left",
        ),
        fit_text(
            rx(670),
            ry(118),
            width - pad - rx(682),
            ry(34),
            commute_alert("check2"),
            round(15 * sy),
            align="left",
        ),
        fit_text(
            rx(670),
            ry(160),
            width - pad - rx(682),
            ry(34),
            commute_alert("check3"),
            round(14 * sy),
            align="left",
        ),
        line(pad, ry(220), width - pad, ry(220), width=max(1, round(2 * sy))),
        fit_text(pad, ry(232), rx(260), ry(32), "7일 주간 예보", round(22 * sy), align="left"),
        rect(
            rx(610),
            ry(230),
            width - pad,
            ry(264),
            fill="white",
            outline=ACCENT_INK,
            width=1,
            radius=5,
        ),
        fit_text(
            rx(618),
            ry(232),
            width - pad - rx(626),
            ry(30),
            weekly_summary(7),
            round(15 * sy),
            color=ACCENT_INK,
        ),
        line(pad, ry(274), width - pad, ry(274), width=1),
        *weekly_columns(
            pad, ry(284), width - 2 * pad, height - ry(16), 7, show_dates=True, show_cond=True
        ),
    ]


def dashboard_7day_portrait(width, height):
    """10.2"+ portrait (640x960, 680x960, 1200x1600): top hero + bottom 7-day forecast."""
    sx, sy = width / 640, height / 960

    def rx(v):
        return round(v * sx)

    def ry(v):
        return round(v * sy)

    pad = rx(20)
    inner = width - 2 * pad
    return [
        fit_text(pad, ry(18), rx(340), ry(32), current("full_date"), round(24 * sy), align="left"),
        fit_text(
            pad,
            ry(50),
            rx(340),
            ry(22),
            "아침 출근 · 주간 날씨 브리핑",
            round(15 * sy),
            align="left",
        ),
        icon(pad + rx(6), ry(88), current("icon"), round(106 * min(sx, sy))),
        fit_text(
            rx(142), ry(84), rx(174), ry(86), current("temperature"), round(74 * sy), align="right"
        ),
        fit_text(
            rx(142), ry(170), rx(174), ry(28), current("condition"), round(22 * sy), align="right"
        ),
        fit_text(
            rx(346), ry(90), rx(130), ry(32), today_field("low"), round(22 * sy), align="left"
        ),
        fit_text(
            rx(484),
            ry(90),
            rx(130),
            ry(32),
            today_field("high"),
            round(22 * sy),
            align="left",
            color=ACCENT_INK,
        ),
        fit_text(
            rx(346),
            ry(128),
            rx(268),
            ry(28),
            current("feels", prefix="체감온도  "),
            round(17 * sy),
            align="left",
        ),
        fit_text(
            rx(346),
            ry(158),
            rx(268),
            ry(28),
            current("humidity", prefix="습도  "),
            round(17 * sy),
            align="left",
        ),
        fit_text(
            rx(346),
            ry(188),
            rx(268),
            ry(28),
            current("wind", prefix="바람  "),
            round(16 * sy),
            align="left",
        ),
        rect(
            pad,
            ry(230),
            width - pad,
            ry(412),
            fill="white",
            outline=commute_alert("outline"),
            width=max(1, round(2 * sx)),
            radius=8,
        ),
        rect(
            pad,
            ry(230),
            width - pad,
            ry(278),
            fill=commute_alert("bg"),
            outline=commute_alert("outline"),
            width=1,
            radius=8,
        ),
        icon(
            pad + rx(14),
            ry(240),
            commute_alert("icon"),
            round(28 * min(sx, sy)),
            color=commute_alert("fg"),
        ),
        fit_text(
            pad + rx(50),
            ry(236),
            inner - rx(64),
            ry(36),
            commute_alert("label"),
            round(20 * sy),
            align="left",
            color=commute_alert("fg"),
        ),
        fit_text(
            pad + rx(14),
            ry(290),
            inner - rx(28),
            ry(34),
            commute_alert("check1"),
            round(17 * sy),
            align="left",
        ),
        fit_text(
            pad + rx(14),
            ry(330),
            inner - rx(28),
            ry(34),
            commute_alert("check2"),
            round(17 * sy),
            align="left",
        ),
        fit_text(
            pad + rx(14),
            ry(370),
            inner - rx(28),
            ry(34),
            commute_alert("check3"),
            round(16 * sy),
            align="left",
        ),
        line(pad, ry(432), width - pad, ry(432), width=max(1, round(2 * sy))),
        fit_text(pad, ry(446), rx(200), ry(32), "7일 주간 예보", round(22 * sy), align="left"),
        rect(
            rx(236),
            ry(444),
            width - pad,
            ry(480),
            fill="white",
            outline=ACCENT_INK,
            width=1,
            radius=5,
        ),
        fit_text(
            rx(244),
            ry(446),
            width - pad - rx(252),
            ry(32),
            weekly_summary(7),
            round(15 * sy),
            color=ACCENT_INK,
        ),
        line(pad, ry(492), width - pad, ry(492), width=1),
        *weekly_columns(pad, ry(504), inner, height - ry(18), 7, show_dates=True, show_cond=True),
    ]


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
        (wide_compact_landscape, ((296, 128), (296, 152))),
        (mid_compact_landscape, ((384, 184), (416, 240))),
        (weekly_5day_landscape, ((400, 300), (648, 480))),
        (weekly_5day_portrait, ((300, 400), (480, 648))),
        (dashboard_6day_landscape, ((800, 480),)),
        (dashboard_6day_portrait, ((480, 800),)),
        (dashboard_7day_landscape, ((960, 640), (960, 680), (1600, 1200))),
        (dashboard_7day_portrait, ((640, 960), (680, 960), (1200, 1600))),
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
        "name": {"en": "Commute weather", "ko": "출근 날씨 브리핑"},
        "description": {
            "en": (
                "Morning commute briefing with rain/snow alerts, min/max & feels-like "
                "temperatures on tags under 4 inches, plus 5-7 day weekly forecasts on 4 inches and above."
            ),
            "ko": (
                "4인치 미만은 비·눈 우산 알림, 최저·최고·체감온도 중심의 출근 브리핑을, "
                "4인치 이상은 오늘 요약과 5~7일 주간 예보를 표시합니다."
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
                    "data": {"type": "daily"},
                    "response_variable": "fc",
                    "continue_on_error": True,
                }
            ],
            "mode": "single",
        },
    }
    return "# Generated by scripts/generate_commute_weather_template.py\n" + yaml.dump(
        data, Dumper=TemplateDumper, allow_unicode=True, sort_keys=False, width=4096
    )


if __name__ == "__main__":
    DESTINATION.write_text(generate(), encoding="utf-8")
