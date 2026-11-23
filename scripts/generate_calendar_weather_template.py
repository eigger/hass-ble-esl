#!/usr/bin/env python3
"""Regenerate the built-in calendar + weather template across every supported size."""

from pathlib import Path
import sys

import yaml

DESTINATION = (
    Path(__file__).resolve().parents[1]
    / "custom_components/ble_esl/designer/templates/calendar_weather.yaml"
)

CALENDAR = "${calendar}"
WEATHER = "${weather}"
ACCENT = "${accent}"
FONT = "${font}"
TIME_FMT = "${time_format}"

TEXT_INK_EXPR = f"('black' if '{ACCENT}' in ('yellow', 'white') else '{ACCENT}')"
TEXT_INK = f"{{{{ {TEXT_INK_EXPR} }}}}"

DAYS_TUPLE = "('월','화','수','목','금','토','일')"

CONDITIONS_MAP = (
    "{'clear-night': '맑음', 'cloudy': '흐림', 'exceptional': '특이 기상', "
    "'fog': '안개', 'hail': '우박', 'lightning': '번개', 'lightning-rainy': '뇌우', "
    "'partlycloudy': '구름 많음', 'pouring': '강한 비', 'rainy': '비', 'snowy': '눈', "
    "'snowy-rainy': '진눈깨비', 'sunny': '맑음', 'windy': '강풍', 'windy-variant': '바람'}"
)

ICONS_MAP = (
    "{'clear-night': 'weather-night', 'cloudy': 'weather-cloudy', "
    "'exceptional': 'weather-sunny-alert', 'fog': 'weather-fog', 'hail': 'weather-hail', "
    "'lightning': 'weather-lightning', 'lightning-rainy': 'weather-lightning-rainy', "
    "'partlycloudy': 'weather-partly-cloudy', 'pouring': 'weather-pouring', "
    "'rainy': 'weather-rainy', 'snowy': 'weather-snowy', 'snowy-rainy': 'weather-snowy-rainy', "
    "'sunny': 'weather-sunny', 'windy': 'weather-windy', 'windy-variant': 'weather-windy-variant'}"
)

WET_SET = "('rainy', 'pouring', 'lightning-rainy', 'hail', 'snowy', 'snowy-rainy')"
TF_EXPR = f"(('{TIME_FMT}' | trim) or '%H:%M')"


def _finite_temp(raw_expr: str, var: str = "_v") -> str:
    return (
        f"{{% set _r = {raw_expr} %}}"
        "{% set _n = _r | float(none) if is_number(_r) and _r is not boolean else none %}"
        "{% set _f = _n if _n is not none and _n == _n and (_n | abs) < 10000 else none %}"
        "{% set _r1 = ((_f | round(1)) + 0) if _f is not none else none %}"
        f"{{% set {var} = ((0 if _r1 == 0 else _r1) | string | replace('.0', '')) if _r1 is not none else '--' %}}"
    )


def _finite_int(raw_expr: str, var: str = "_vi") -> str:
    return (
        f"{{% set _r = {raw_expr} %}}"
        "{% set _n = _r | float(none) if is_number(_r) and _r is not boolean else none %}"
        "{% set _f = _n if _n is not none and _n == _n and (_n | abs) < 10000 else none %}"
        f"{{% set {var} = ((0 if _f == 0 else (_f | round(0) | int)) | string) if _f is not none else '--' %}}"
    )


FC_PRELUDE = (
    "{% set _td = now().strftime('%Y-%m-%d') %}"
    f"{{% set _fco = fc['{WEATHER}'] if (fc is defined and fc is mapping and '{WEATHER}' in fc and fc['{WEATHER}'] is mapping) else {{}} %}}"
    "{% set _fcw = _fco.get('forecast') %}"
    "{% set _fcr = (_fcw | select('mapping') | list) if (_fcw is sequence and _fcw is not string) else [] %}"
    "{% set _ns = namespace(fc=[]) %}"
    "{% for _it in _fcr %}"
    "{% set _dt = as_datetime((_it.get('datetime') | default('')) | string, none) %}"
    "{% if _dt is not none %}"
    "{% set _dl = as_local(_dt) if _dt.tzinfo is not none else _dt %}"
    "{% if _dl.strftime('%Y-%m-%d') >= _td %}{% set _ns.fc = _ns.fc + [_it] %}{% endif %}"
    "{% endif %}"
    "{% endfor %}"
    "{% set _fc = _ns.fc %}"
)

EVS_PRELUDE = (
    f"{{% set _eco = events['{CALENDAR}'] if (events is defined and events is mapping and '{CALENDAR}' in events and events['{CALENDAR}'] is mapping) else {{}} %}}"
    "{% set _evw = _eco.get('events') %}"
    "{% set _evs = (_evw | select('mapping') | list) if (_evw is sequence and _evw is not string) else [] %}"
)

DATE_SHORT = f"{{{{ now().strftime('%m/%d') ~ ' (' ~ {DAYS_TUPLE}[now().weekday()] ~ ')' }}}}"
DATE_COLOR = f"{{{{ {TEXT_INK_EXPR} if now().weekday() >= 5 else 'black' }}}}"

TU_EXPR = f"(state_attr('{WEATHER}', 'temperature_unit') or '°C')"
CURR_TEMP = (
    _finite_temp(f"state_attr('{WEATHER}', 'temperature')", "_t") + f"{{{{ _t ~ {TU_EXPR} }}}}"
)
CURR_ICON = f"{{{{ {ICONS_MAP}.get(states('{WEATHER}'), 'weather-cloudy-alert') }}}}"


def _fc_day(idx: int) -> tuple[str, str, str, str, str]:
    sel = f"{FC_PRELUDE}{{% set _d = _fc[{idx}] if (_fc | length > {idx}) else {{}} %}}"
    day_label = (
        sel
        + "{% set _dt = as_datetime((_d.get('datetime') | default('')) | string, none) %}"
        + "{% set _dl = as_local(_dt) if (_dt is not none and _dt.tzinfo is not none) else _dt %}"
        + f"{{{{ '오늘' if {idx} == 0 else ({DAYS_TUPLE}[_dl.weekday()] if _dl is not none else '—') }}}}"
    )
    icon_val = sel + f"{{{{ {ICONS_MAP}.get(_d.get('condition', ''), 'weather-cloudy-alert') }}}}"
    chance_expr = (
        "{% set _pr = _d.get('precipitation_probability') %}"
        "{% set _pn = _pr | float(none) if is_number(_pr) and _pr is not boolean else none %}"
        "{% set _pf = (_pn | round(0) | int) if (_pn is not none and _pn == _pn and 0 <= _pn <= 100) else none %}"
    )
    day_color = (
        sel
        + chance_expr
        + f"{{{{ {TEXT_INK_EXPR} if (_d.get('condition', '') in {WET_SET} or (_pf is not none and _pf >= 50)) else 'black' }}}}"
    )
    hilo_val = (
        sel
        + _finite_int("_d.get('templow')", "_lo")
        + _finite_int("_d.get('temperature')", "_hi")
        + "{{ (_lo ~ '/' ~ _hi ~ '°') if _d else '—' }}"
    )
    chance_val = sel + chance_expr + "{{ (_pf | string ~ '%') if _pf is not none else '—' }}"
    return day_label, icon_val, day_color, hilo_val, chance_val


# Attribute-only calendar helpers for compact (<4") displays (no calendar.get_events required)
ATTR_TITLE = f"{{{{ state_attr('{CALENDAR}', 'message') or '예정된 일정 없음' }}}}"
ATTR_WHEN = (
    f"{{% set _st = as_datetime(state_attr('{CALENDAR}', 'start_time'), none) %}}"
    f"{{% set _ad = state_attr('{CALENDAR}', 'all_day') %}}"
    "{% if _st is not none and _st.tzinfo is not none %}{% set _st = as_local(_st) %}{% endif %}"
    f"{{{{ (_st.strftime('%m/%d') ~ (' 종일' if _ad else ' ' ~ _st.strftime({TF_EXPR}))) if _st is not none else '일정 대기' }}}}"
)


class FlowElement(dict):
    """Write each generated layout item as compact single-line YAML flow mapping."""


class TemplateDumper(yaml.SafeDumper):
    """Share repeated Jinja strings as YAML scalar aliases across layouts."""

    def ignore_aliases(self, data):
        return not (isinstance(data, str) and len(data) > 40 and "{" in data)

    def represent_flow(self, element):
        return self.represent_mapping("tag:yaml.org,2002:map", element, flow_style=True)


TemplateDumper.add_representer(FlowElement, TemplateDumper.represent_flow)


class Canvas:
    """Accumulate scaled elements for one display resolution."""

    def __init__(self, width: int, height: int, vw: int, vh: int):
        self.width = width
        self.height = height
        self.sx = width / vw
        self.sy = height / vh
        self.scale = min(self.sx, self.sy)
        self.items: list[FlowElement] = []

    def rx(self, x: float) -> int:
        return min(self.width - 1, max(0, round(x * self.sx)))

    def ry(self, y: float) -> int:
        return min(self.height - 1, max(0, round(y * self.sy)))

    def rw(self, x: float, w: float) -> int:
        x0 = self.rx(x)
        x1 = min(self.width, round((x + w) * self.sx))
        return max(1, x1 - x0)

    def rh(self, y: float, h: float) -> int:
        y0 = self.ry(y)
        y1 = min(self.height, round((y + h) * self.sy))
        return max(1, y1 - y0)

    def text_fit(
        self,
        value: str,
        x: float,
        y: float,
        w: float,
        h: float,
        size: float,
        *,
        align: str = "left",
        valign: str = "middle",
        color: str = "black",
        min_size: int = 7,
        max_lines: int = 1,
    ) -> None:
        self.items.append(
            FlowElement(
                {
                    "type": "text_fit",
                    "value": value,
                    "font": FONT,
                    "x": self.rx(x),
                    "y": self.ry(y),
                    "width": self.rw(x, w),
                    "height": self.rh(y, h),
                    "size": max(min_size, round(size * self.sy)),
                    "min_size": min_size,
                    "max_lines": max_lines,
                    "fit": "shrink_ellipsis",
                    "align": align,
                    "valign": valign,
                    "color": color,
                }
            )
        )

    def icon(
        self,
        value: str,
        x: float,
        y: float,
        size: float,
        *,
        color: str = "black",
        anchor: str = "mm",
    ) -> None:
        self.items.append(
            FlowElement(
                {
                    "type": "icon",
                    "value": value,
                    "x": self.rx(x),
                    "y": self.ry(y),
                    "size": max(10, round(size * self.scale)),
                    "anchor": anchor,
                    "color": color,
                }
            )
        )

    def line(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        width: float = 1,
        color: str = "black",
    ) -> None:
        self.items.append(
            FlowElement(
                {
                    "type": "line",
                    "x_start": self.rx(x0),
                    "y_start": self.ry(y0),
                    "x_end": self.rx(x1),
                    "y_end": self.ry(y1),
                    "width": max(1, round(width * self.scale)),
                    "fill": color,
                }
            )
        )

    def rect(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        *,
        fill: str = "white",
        outline: str = "black",
        width: float = 1,
        radius: float = 0,
    ) -> None:
        item = {
            "type": "rectangle",
            "x_start": self.rx(x0),
            "y_start": self.ry(y0),
            "x_end": self.rx(x1),
            "y_end": self.ry(y1),
            "fill": fill,
            "outline": outline,
            "width": max(1, round(width * self.scale)),
        }
        if radius:
            item["radius"] = max(2, round(radius * self.scale))
        self.items.append(FlowElement(item))


def _square_200(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 200, 200)
    c.text_fit(CURR_TEMP, 8, 10, 184, 68, 54, align="center", min_size=16)
    c.line(12, 82, 188, 82)
    c.text_fit(ATTR_WHEN, 8, 88, 184, 34, 24, align="center", color=TEXT_INK, min_size=16)
    c.text_fit(ATTR_TITLE, 8, 126, 184, 64, 26, align="center", max_lines=2, min_size=16)
    return c.items


def _tiny_landscape(w: int, h: int) -> list[FlowElement]:
    large = w >= 296
    vw = 296 if large else 250
    ms = 18 if large else 16
    mid = 122 if large else 108
    c = Canvas(w, h, vw, 128)
    c.text_fit(
        CURR_TEMP,
        6,
        6,
        mid - 12,
        56,
        52 if large else 50,
        align="center",
        min_size=ms,
    )
    c.line(mid, 10, mid, 60)
    c.text_fit(
        ATTR_WHEN,
        mid + 6,
        6,
        vw - mid - 12,
        56,
        26,
        align="center",
        color=TEXT_INK,
        min_size=ms,
    )
    c.line(6, 66, vw - 6, 66)
    c.text_fit(
        ATTR_TITLE,
        6,
        72,
        vw - 12,
        50,
        28 if large else 26,
        align="center",
        max_lines=1,
        min_size=ms,
    )
    return c.items


def _tiny_portrait(w: int, h: int) -> list[FlowElement]:
    tall = h >= 296
    vh = 296 if tall else 250
    ms = 15 if tall else 14
    c = Canvas(w, h, 128, vh)
    c.text_fit(CURR_TEMP, 6, 12, 116, vh * 0.30, 44, align="center", min_size=ms)
    c.line(10, vh * 0.36, 118, vh * 0.36)
    c.text_fit(
        ATTR_WHEN,
        6,
        vh * 0.40,
        116,
        40,
        22,
        align="center",
        color=TEXT_INK,
        min_size=ms,
    )
    c.text_fit(
        ATTR_TITLE,
        6,
        vh * 0.56,
        116,
        vh * 0.38,
        22,
        align="center",
        max_lines=2,
        min_size=ms,
    )
    return c.items


def _medium_compact_landscape(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 384, 184)
    c.text_fit(DATE_SHORT, 10, 12, 166, 70, 28, align="center", color=DATE_COLOR, min_size=18)
    c.line(182, 14, 182, 82)
    c.text_fit(CURR_TEMP, 190, 8, 184, 76, 64, align="center", min_size=18)
    c.line(10, 88, 374, 88)
    c.text_fit(ATTR_WHEN, 10, 94, 364, 36, 26, align="center", color=TEXT_INK, min_size=18)
    c.text_fit(ATTR_TITLE, 10, 132, 364, 46, 30, align="center", max_lines=1, min_size=18)
    return c.items


def _medium_compact_portrait(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 184, 384)
    c.text_fit(DATE_SHORT, 10, 14, 164, 40, 26, align="center", color=DATE_COLOR, min_size=16)
    c.text_fit(CURR_TEMP, 10, 62, 164, 90, 58, align="center", min_size=16)
    c.line(12, 168, 172, 168)
    c.text_fit(ATTR_WHEN, 10, 184, 164, 44, 24, align="center", color=TEXT_INK, min_size=16)
    c.text_fit(ATTR_TITLE, 10, 240, 164, 126, 28, align="center", max_lines=2, min_size=16)
    return c.items


DATE_KR = (
    "{{ now().month ~ '월 ' ~ now().day ~ '일 ' ~ ('월화수목금토일'[now().weekday()]) ~ '요일' }}"
)
TEMP_WHOLE = (
    _finite_int(f"state_attr('{WEATHER}', 'temperature')", "_tw")
    + "{{ '--' if _tw == '--' else _tw ~ '°' }}"
)
DAYS_KR = "'월화수목금토일'"


def _when_compact(idx: int) -> tuple[str, str]:
    """Compact time label ('09:30', '내일 09:30', '수 종일') and its colour for event ``idx``."""
    pick = (
        EVS_PRELUDE
        + "{% set _sd = none %}{% set _ad = false %}"
        + f"{{% if _evs | length > {idx} %}}"
        + f"{{% set _sr = (_evs[{idx}].get('start') | default('')) | string %}}"
        + "{% set _ad = _sr | length == 10 %}{% set _sd = as_datetime(_sr, none) %}"
        + (
            f"{{% elif state_attr('{CALENDAR}', 'start_time') %}}"
            f"{{% set _sd = as_datetime(state_attr('{CALENDAR}', 'start_time'), none) %}}"
            f"{{% set _ad = state_attr('{CALENDAR}', 'all_day') %}}"
            if idx == 0
            else ""
        )
        + "{% endif %}"
        + "{% if _sd is not none and _sd.tzinfo is not none %}{% set _sd = as_local(_sd) %}{% endif %}"
        + "{% set _dd = (_sd.date() - now().date()).days if _sd is not none else none %}"
    )
    clock = f"('종일' if _ad else _sd.strftime({TF_EXPR}))"
    label = (
        pick
        + f"{{{{ '' if _sd is none else ({clock} if _dd <= 0 else "
        + f"(('내일' if _dd == 1 else {DAYS_KR}[_sd.weekday()]) ~ ' ' ~ {clock})) }}}}"
    )
    color = (
        pick
        + f"{{{{ {TEXT_INK_EXPR} if _sd is not none and (_dd <= 0 or {idx} == 0) else 'black' }}}}"
    )
    return label, color


def _hilo_spaced(idx: int, compact: bool = False) -> str:
    sel = f"{FC_PRELUDE}{{% set _d = _fc[{idx}] if (_fc | length > {idx}) else {{}} %}}"
    sep = "/" if compact else "° / "
    return (
        sel
        + _finite_int("_d.get('templow')", "_lo")
        + _finite_int("_d.get('temperature')", "_hi")
        + f"{{{{ (_lo ~ '{sep}' ~ _hi ~ '°') if _d else '—' }}}}"
    )


def _put(
    c: Canvas,
    value: str,
    x: float,
    cy: float,
    w: float,
    size: float,
    *,
    align: str = "left",
    color: str = "black",
    floor: float = 14,
    ratio: float = 0.7,
) -> None:
    px = max(size * c.scale, floor) if size >= floor else size * c.scale
    height = px * 1.6
    width = c.sx * w
    edge = c.sx * x
    left = edge if align == "left" else edge - width if align == "right" else edge - width / 2
    top = c.sy * cy - height / 2
    c.items.append(
        FlowElement(
            {
                "type": "text_fit",
                "value": value,
                "font": FONT,
                "x": max(0, round(left)),
                "y": max(0, round(top)),
                "width": max(1, round(width)),
                "height": max(1, round(height)),
                "size": max(7, round(px)),
                "min_size": max(7, round(min(px, max(floor, px * ratio)))),
                "max_lines": 1,
                "fit": "shrink_ellipsis",
                "align": align,
                "valign": "middle",
                "color": color,
            }
        )
    )


def _glyph(c: Canvas, value: str, x: float, cy: float, size: float, color: str = "black") -> None:
    c.icon(value, x, cy, size, color=color)


def _bar(c: Canvas, height: float, date: str, size: float, *, icon: float = 28) -> None:
    """Black header: the date on the left, the current weather icon and temperature on the right."""
    c.rect(0, 0, c.width / c.sx, height, fill="black", outline="black", width=1)
    width = c.width / c.sx
    _put(c, date, 14, height / 2, width - 132, size, color="white")
    _put(c, TEMP_WHOLE, width - 12, height / 2, 56, size, align="right", color="white")
    _glyph(c, CURR_ICON, width - 12 - 56 - icon / 2 - 6, height / 2, icon, "white")


def _event_rows(
    c: Canvas,
    first: float,
    pitch: float,
    count: int,
    *,
    time_w: float,
    size: float,
    x: float,
    tx: float,
    tw: float,
) -> None:
    for slot in range(count):
        cy = first + slot * pitch
        label, color = _when_compact(slot)
        if slot:
            c.line(14, cy - pitch / 2, c.width / c.sx - 14, cy - pitch / 2)
        _put(c, label, x, cy, time_w, size, color=color, ratio=0.8)
        _put(c, _event_title(slot), tx, cy, tw, size + 2)


def _forecast_columns(
    c: Canvas,
    days: int,
    top: float,
    bottom: float,
    *,
    label: float,
    icon: float,
    hilo: float,
    chance: float | None = None,
) -> None:
    width = c.width / c.sx
    pitch = width / days
    for slot in range(days):
        cx = pitch * (slot + 0.5)
        day_label, icon_val, day_color, _, chance_val = _fc_day(slot + 1)
        if slot:
            c.line(pitch * slot, top + 8, pitch * slot, bottom - 4)
        span = bottom - top
        _put(
            c,
            day_label,
            cx,
            top + span * (0.14 if chance is None else 0.10),
            pitch - 6,
            label,
            align="center",
            color=day_color,
        )
        _glyph(c, icon_val, cx, top + span * (0.46 if chance is None else 0.35), icon)
        _put(
            c,
            _hilo_spaced(slot + 1, pitch < 90),
            cx,
            top + span * (0.82 if chance is None else 0.64),
            pitch - 4,
            hilo,
            align="center",
            ratio=0.8,
        )
        if chance is not None:
            _put(
                c,
                chance_val,
                cx,
                top + span * 0.88,
                pitch - 4,
                chance,
                align="center",
                color=day_color,
            )


def _forecast_rows(
    c: Canvas,
    days: int,
    top: float,
    bottom: float,
    *,
    label: float,
    icon: float,
    hilo: float,
    chance: float | None = None,
    compact: bool = False,
) -> None:
    width = c.width / c.sx
    pitch = (bottom - top) / days
    for slot in range(days):
        cy = top + pitch * (slot + 0.5)
        day_label, icon_val, day_color, _, chance_val = _fc_day(slot + 1)
        if slot:
            c.line(14, cy - pitch / 2, width - 14, cy - pitch / 2)
        _put(c, day_label, 16, cy, 44, label, color=day_color)
        _glyph(c, icon_val, 94, cy, icon)
        if chance is not None:
            _put(c, chance_val, width * 0.52, cy, 60, chance, color=day_color)
        _put(
            c,
            _hilo_spaced(slot + 1, compact),
            width - 12,
            cy,
            min(width * 0.46, 150),
            hilo,
            align="right",
            ratio=0.8,
        )


def _landscape(w: int, h: int) -> list[FlowElement]:
    big = max(w, h) >= 800
    c = Canvas(w, h, 800 if big else 400, 480 if big else 300)
    if big:
        _bar(c, 56, DATE_KR, 28, icon=36)
        _event_rows(c, 96, 50, 4, time_w=170, size=26, x=24, tx=210, tw=566)
        c.rect(0, 272, 800, 275, fill="black", outline="black", width=1)
        _forecast_columns(c, 5, 278, 478, label=24, icon=54, hilo=26, chance=22)
    else:
        _bar(c, 44, DATE_KR, 20)
        _event_rows(c, 70, 46, 3, time_w=104, size=21, x=16, tx=126, tw=262)
        c.rect(0, 196, 400, 199, fill="black", outline="black", width=1)
        _forecast_columns(c, 4, 200, 298, label=18, icon=30, hilo=18)
    return c.items


def _portrait(w: int, h: int) -> list[FlowElement]:
    big = max(w, h) >= 800
    c = Canvas(w, h, 480 if big else 300, 800 if big else 400)
    if big:
        _bar(c, 56, DATE_KR, 28, icon=36)
        _event_rows(c, 100, 56, 5, time_w=150, size=24, x=24, tx=176, tw=280)
        c.rect(0, 372, 480, 375, fill="black", outline="black", width=1)
        _forecast_rows(c, 5, 378, 796, label=28, icon=46, hilo=28, chance=24)
    else:
        _bar(c, 44, DATE_KR, 18, icon=26)
        _event_rows(c, 74, 44, 3, time_w=90, size=18, x=14, tx=108, tw=180)
        c.rect(0, 196, 300, 198, fill="black", outline="black", width=1)
        _forecast_rows(c, 4, 200, 398, label=20, icon=30, hilo=20)
    return c.items


def _event_title(idx: int) -> str:
    if idx == 0:
        return (
            EVS_PRELUDE
            + "{{ (_evs[0].get('summary') | default('일정 없음', true)) if _evs "
            + f"else (state_attr('{CALENDAR}', 'message') or '예정된 일정 없음') }}}}"
        )
    return (
        EVS_PRELUDE
        + f"{{{{ (_evs[{idx}].get('summary') | default('', true)) if _evs | length > {idx} else '' }}}}"
    )


def generate() -> str:
    layouts: dict[str, list[FlowElement]] = {}
    profiles = (
        (_square_200, ((200, 200),)),
        (_tiny_landscape, ((212, 104), (250, 122), (250, 128), (250, 132), (296, 128), (296, 152))),
        (_medium_compact_landscape, ((384, 184), (416, 240))),
        (
            _landscape,
            ((400, 300), (648, 480), (800, 480), (960, 640), (960, 680), (1600, 1200)),
        ),
    )
    portrait_map = {
        _tiny_landscape: _tiny_portrait,
        _medium_compact_landscape: _medium_compact_portrait,
        _landscape: _portrait,
    }
    for builder, sizes in profiles:
        for width, height in sizes:
            layouts[f"{width}x{height}"] = builder(width, height)
            portrait = f"{height}x{width}"
            if width > height and portrait not in layouts:
                layouts[portrait] = portrait_map[builder](height, width)

    for items in layouts.values():
        for item in items:
            for key, value in item.items():
                if isinstance(value, str) and len(value) > 40 and "{" in value:
                    item[key] = sys.intern(value)

    data = {
        "template": 1,
        "id": "calendar_weather",
        "categories": ["schedule", "weather"],
        "name": {"en": "Calendar & weather", "ko": "캘린더 · 날씨"},
        "description": {
            "en": "Combined schedule and weather dashboard: today's weather and next event on compact tags, and upcoming events with a 4-day forecast from 4.2 inches.",
            "ko": "오늘 일정과 날씨를 함께 보여줍니다. 작은 화면은 다음 일정 1건과 오늘 날씨를, 4.2인치 이상은 다가오는 일정 4건과 4일 예보를 표시합니다.",
        },
        "background": "white",
        "parameters": {
            "calendar": {
                "type": "entity",
                "domain": "calendar",
                "default": "calendar.home",
                "label": {"en": "Calendar entity", "ko": "캘린더 엔티티"},
            },
            "weather": {
                "type": "entity",
                "domain": "weather",
                "default": "weather.home",
                "label": {"en": "Weather entity", "ko": "날씨 엔티티"},
            },
            "accent": {
                "type": "color",
                "default": "red",
                "label": {"en": "Accent color", "ko": "강조 색상"},
            },
            "font": {
                "type": "font",
                "default": "NotoSansKR-Bold.ttf",
                "label": {"en": "Font", "ko": "글꼴"},
            },
            "time_format": {
                "type": "string",
                "default": "%H:%M",
                "min_length": 1,
                "label": {"en": "Time format (strftime)", "ko": "시간 형식 (strftime)"},
            },
            "interval": {
                "type": "select",
                "group": "automation",
                "options": ["10", "15", "30"],
                "default": "15",
                "label": {"en": "Update every (minutes)", "ko": "갱신 주기 (분)"},
            },
        },
        "layouts": layouts,
        "automation": {
            "triggers": [{"trigger": "time_pattern", "minutes": "/${interval}"}],
            "mode": "single",
        },
    }
    output = "# Generated by scripts/generate_calendar_weather_template.py\n" + yaml.dump(
        data, Dumper=TemplateDumper, allow_unicode=True, sort_keys=False, width=4096
    )
    if len(output.encode("utf-8")) >= 256 * 1024:
        raise ValueError("calendar_weather.yaml exceeds 256 KB template limit")
    return output


if __name__ == "__main__":
    DESTINATION.write_text(generate(), encoding="utf-8")
