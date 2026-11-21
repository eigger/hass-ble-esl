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

BADGE_INK_EXPR = f"('black' if '{ACCENT}' == 'white' else '{ACCENT}')"
BADGE_FG_EXPR = "('black' if _ink == 'yellow' else 'white')"
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
DATE_LONG = f"{{{{ now().strftime('%Y.%m.%d') ~ ' (' ~ {DAYS_TUPLE}[now().weekday()] ~ ')' }}}}"
DATE_COLOR = f"{{{{ {TEXT_INK_EXPR} if now().weekday() >= 5 else 'black' }}}}"
CLOCK = f"{{{{ now().strftime({TF_EXPR}) ~ ' 갱신' }}}}"

TU_EXPR = f"(state_attr('{WEATHER}', 'temperature_unit') or '°C')"
CURR_TEMP = (
    _finite_temp(f"state_attr('{WEATHER}', 'temperature')", "_t") + f"{{{{ _t ~ {TU_EXPR} }}}}"
)
CURR_COND = f"{{{{ {CONDITIONS_MAP}.get(states('{WEATHER}'), '—') }}}}"
CURR_ICON = f"{{{{ {ICONS_MAP}.get(states('{WEATHER}'), 'weather-cloudy-alert') }}}}"
CURR_ICON_COLOR = f"{{{{ {TEXT_INK_EXPR} if states('{WEATHER}') in {WET_SET} else 'black' }}}}"
CURR_HUM = (
    _finite_int(f"state_attr('{WEATHER}', 'humidity')", "_hm")
    + "{{ ('습도 ' ~ _hm ~ '%') if _hm != '--' else '습도 --' }}"
)

DAY0_PRELUDE = FC_PRELUDE + "{% set _day0 = _fc[0] if _fc else (_fcr[0] if _fcr else {}) %}"
TODAY_HILO_FULL = (
    DAY0_PRELUDE
    + _finite_int("_day0.get('templow')", "_lo")
    + _finite_int("_day0.get('temperature')", "_hi")
    + "{{ '최저 ' ~ _lo ~ '° / 최고 ' ~ _hi ~ '°' }}"
)
TODAY_HILO_COMPACT = (
    DAY0_PRELUDE
    + _finite_int("_day0.get('templow')", "_lo")
    + _finite_int("_day0.get('temperature')", "_hi")
    + "{{ _lo ~ '°/' ~ _hi ~ '°' }}"
)


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
ATTR_LOC = (
    f"{{% set _l = state_attr('{CALENDAR}', 'location') or '' %}}"
    f"{{{{ _l if _l else ('오늘 일정' if state_attr('{CALENDAR}', 'message') else '') }}}}"
)
ATTR_LOC_OR_CLOCK = (
    f"{{% set _l = state_attr('{CALENDAR}', 'location') or '' %}}"
    f"{{{{ _l if _l else (now().strftime({TF_EXPR}) ~ ' 갱신') }}}}"
)

# 4.2"+ Calendar helpers (reads `events` from calendar.get_events with entity-attribute fallback)
BADGE_PRELUDE = (
    EVS_PRELUDE
    + f"{{% set _ink = {BADGE_INK_EXPR} %}}{{% set _fg = {BADGE_FG_EXPR} %}}"
    + f"{{% set _cnt = (_evs | length) if _evs else (1 if state_attr('{CALENDAR}', 'message') else 0) %}}"
)
CAL_BADGE_TEXT = BADGE_PRELUDE + "{{ ('일정 ' ~ _cnt ~ '건') if _cnt > 0 else '일정 없음' }}"
CAL_BADGE_FILL = BADGE_PRELUDE + "{{ _ink if _cnt > 0 else 'white' }}"
CAL_BADGE_OUTLINE = BADGE_PRELUDE + "{{ _ink if _cnt > 0 else 'black' }}"
CAL_BADGE_COLOR = BADGE_PRELUDE + "{{ _fg if _cnt > 0 else 'black' }}"


def _event_slot(idx: int) -> tuple[str, str, str, str]:
    """Return (when, summary, location, color) templates for upcoming slot `idx`."""
    when_ev = (
        f"{{% set _tf = {TF_EXPR} %}}"
        "{% set _sr = (_ev.get('start') | default('')) | string %}"
        "{% set _er = (_ev.get('end') | default('')) | string %}"
        "{% set _sd = as_datetime(_sr, none) %}"
        "{% set _ed = as_datetime(_er, none) %}"
        "{% if _sd is not none and _sd.tzinfo is not none %}{% set _sd = as_local(_sd) %}{% endif %}"
        "{% if _ed is not none and _ed.tzinfo is not none %}{% set _ed = as_local(_ed) %}{% endif %}"
        "{{ "
        "_sd.strftime('%m/%d' if _sr | length == 10 else '%m/%d ' ~ _tf) "
        "~ ((' - ' ~ (_ed - timedelta(days=1)).strftime('%m/%d')) "
        "if _sr | length == 10 and _er | length == 10 and _ed is not none and (_ed.tzinfo is none) == (_sd.tzinfo is none) and _ed.date() > _sd.date() + timedelta(days=1) "
        "else (' - ' ~ _ed.strftime(_tf if _ed.date() == _sd.date() else '%m/%d ' ~ _tf) "
        "if _ed is not none and (_ed.tzinfo is none) == (_sd.tzinfo is none) and _ed >= _sd and _sr | length > 10 else '')) "
        "if _sd is not none else '' }}"
    )
    if idx == 0:
        when_val = (
            EVS_PRELUDE
            + "{% if _evs %}{% set _ev = _evs[0] %}"
            + when_ev
            + "{% else %}"
            + ATTR_WHEN
            + "{% endif %}"
        )
        title_val = (
            EVS_PRELUDE
            + f"{{{{ (_evs[0].get('summary') | default('일정 없음', true)) if _evs else (state_attr('{CALENDAR}', 'message') or '예정된 일정 없음') }}}}"
        )
        loc_val = (
            EVS_PRELUDE
            + f"{{{{ (_evs[0].get('location') | default('', true)) if _evs else (state_attr('{CALENDAR}', 'location') or '') }}}}"
        )
        slot_color = (
            EVS_PRELUDE
            + f"{{{{ {TEXT_INK_EXPR} if (_evs or state_attr('{CALENDAR}', 'message')) else 'black' }}}}"
        )
    else:
        when_val = (
            EVS_PRELUDE
            + f"{{% if _evs | length > {idx} %}}{{% set _ev = _evs[{idx}] %}}"
            + when_ev
            + "{% endif %}"
        )
        title_val = (
            EVS_PRELUDE
            + f"{{{{ (_evs[{idx}].get('summary') | default('', true)) if _evs | length > {idx} else '' }}}}"
        )
        loc_val = (
            EVS_PRELUDE
            + f"{{{{ (_evs[{idx}].get('location') | default('', true)) if _evs | length > {idx} else '' }}}}"
        )
        slot_color = "black"
    return when_val, title_val, loc_val, slot_color


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
    c.text_fit(DATE_SHORT, 10, 6, 118, 22, 16, color=DATE_COLOR)
    c.text_fit(CLOCK, 130, 8, 60, 19, 11, align="right")
    c.line(10, 32, 190, 32)

    c.icon(CURR_ICON, 30, 62, 34, color=CURR_ICON_COLOR)
    c.text_fit(CURR_TEMP, 54, 38, 74, 36, 28)
    c.text_fit(CURR_COND, 132, 38, 58, 18, 13, align="right")
    c.text_fit(TODAY_HILO_COMPACT, 132, 58, 58, 18, 12, align="right")
    c.text_fit(CURR_HUM, 54, 78, 136, 18, 12)
    c.line(10, 99, 190, 99)

    c.icon("calendar-today", 20, 116, 16, color=TEXT_INK)
    c.text_fit("다음 일정", 32, 106, 56, 20, 12, color=TEXT_INK)
    c.text_fit(ATTR_WHEN, 90, 106, 100, 20, 12, align="right")
    c.text_fit(ATTR_TITLE, 10, 132, 180, 36, 20, max_lines=2)
    c.text_fit(ATTR_LOC, 10, 170, 180, 22, 12)
    return c.items


def _tiny_landscape(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 250, 128)
    c.text_fit(DATE_SHORT, 6, 3, 124, 20, 14, color=DATE_COLOR)
    c.text_fit(CLOCK, 136, 4, 108, 19, 11, align="right")
    c.line(6, 25, 244, 25)
    c.line(112, 29, 112, 124)

    c.icon(CURR_ICON, 25, 56, 30, color=CURR_ICON_COLOR)
    c.text_fit(CURR_TEMP, 46, 33, 62, 32, 24)
    c.text_fit(CURR_COND, 6, 74, 102, 21, 13, align="center")
    c.text_fit(TODAY_HILO_COMPACT, 6, 98, 102, 21, 12, align="center")

    c.text_fit("다음 일정", 118, 30, 56, 20, 12, color=TEXT_INK)
    c.text_fit(ATTR_WHEN, 176, 30, 68, 20, 11, align="right")
    c.text_fit(ATTR_TITLE, 118, 56, 126, 36, 19, max_lines=2)
    c.text_fit(ATTR_LOC, 118, 96, 126, 23, 12)
    return c.items


def _tiny_portrait(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 128, 250)
    c.text_fit(DATE_SHORT, 6, 5, 116, 22, 14, align="center", color=DATE_COLOR)
    c.line(6, 31, 122, 31)

    c.icon(CURR_ICON, 27, 63, 28, color=CURR_ICON_COLOR)
    c.text_fit(CURR_TEMP, 46, 41, 76, 32, 24, align="right")
    c.text_fit(CURR_COND, 46, 74, 76, 19, 12, align="right")
    c.text_fit(TODAY_HILO_COMPACT, 6, 96, 116, 21, 12, align="center")
    c.line(6, 121, 122, 121)

    c.text_fit("다음 일정", 6, 126, 116, 20, 12, align="center", color=TEXT_INK)
    c.text_fit(ATTR_WHEN, 6, 150, 116, 22, 12, align="center")
    c.text_fit(ATTR_TITLE, 6, 177, 116, 38, 18, align="center", max_lines=2)
    c.text_fit(ATTR_LOC_OR_CLOCK, 6, 220, 116, 22, 11, align="center")
    return c.items


def _medium_compact_landscape(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 384, 184)
    c.icon("calendar-today", 18, 17, 18, color=DATE_COLOR)
    c.text_fit(DATE_LONG, 32, 6, 210, 22, 16, color=DATE_COLOR)
    c.text_fit(CLOCK, 252, 7, 124, 21, 12, align="right")
    c.line(8, 33, 376, 33)
    c.line(166, 38, 166, 178)

    c.icon(CURR_ICON, 34, 68, 38, color=CURR_ICON_COLOR)
    c.text_fit(CURR_TEMP, 60, 42, 100, 44, 34)
    c.text_fit(CURR_COND, 10, 94, 150, 24, 16)
    c.text_fit(TODAY_HILO_FULL, 10, 122, 150, 24, 14)
    c.text_fit(CURR_HUM, 10, 150, 150, 24, 13)

    c.text_fit("다음 일정", 176, 40, 80, 24, 14, color=TEXT_INK)
    c.text_fit(ATTR_WHEN, 260, 40, 116, 24, 13, align="right")
    c.text_fit(ATTR_TITLE, 176, 72, 200, 56, 26, max_lines=2)
    c.text_fit(ATTR_LOC, 176, 136, 200, 32, 14)
    return c.items


def _medium_compact_portrait(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 184, 384)
    c.text_fit(DATE_SHORT, 10, 7, 104, 24, 16, color=DATE_COLOR)
    c.text_fit(CLOCK, 116, 9, 58, 20, 11, align="right")
    c.line(10, 36, 174, 36)

    c.rect(10, 44, 174, 184, radius=6)
    c.icon(CURR_ICON, 40, 82, 38, color=CURR_ICON_COLOR)
    c.text_fit(CURR_TEMP, 68, 56, 98, 42, 32, align="right")
    c.text_fit(CURR_COND, 18, 108, 148, 22, 15)
    c.text_fit(TODAY_HILO_FULL, 18, 134, 148, 22, 14)
    c.text_fit(CURR_HUM, 18, 158, 148, 20, 13)

    c.rect(10, 194, 174, 374, radius=6)
    c.text_fit("다음 일정", 18, 204, 148, 22, 14, color=TEXT_INK)
    c.text_fit(ATTR_WHEN, 18, 232, 148, 24, 13)
    c.text_fit(ATTR_TITLE, 18, 264, 148, 60, 22, max_lines=2)
    c.text_fit(ATTR_LOC, 18, 332, 148, 30, 13)
    return c.items


def _panel_landscape(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 800, 480)
    c.icon("calendar-today", 38, 36, 28, color=DATE_COLOR)
    c.text_fit(DATE_LONG, 60, 17, 360, 38, 28, color=DATE_COLOR)
    c.text_fit(CLOCK, 430, 22, 144, 28, 16, align="right")
    c.rect(588, 15, 776, 55, fill=CAL_BADGE_FILL, outline=CAL_BADGE_OUTLINE, width=2, radius=10)
    c.text_fit(CAL_BADGE_TEXT, 596, 19, 172, 32, 19, align="center", color=CAL_BADGE_COLOR)
    c.line(24, 64, 776, 64, width=2)

    c.rect(24, 76, 468, 464, width=1.5, radius=10)
    c.icon("calendar", 48, 100, 24, color=TEXT_INK)
    c.text_fit("다가오는 일정", 68, 84, 240, 32, 20)
    for slot in range(4):
        top = 122 + slot * 84
        if slot:
            c.line(38, top - 3, 454, top - 3)
        when_val, title_val, loc_val, slot_color = _event_slot(slot)
        c.text_fit(when_val, 40, top + 2, 232, 28, 15, color=slot_color)
        c.text_fit(loc_val, 276, top + 2, 176, 28, 14, align="right")
        c.text_fit(title_val, 40, top + 34, 412, 42, 23)

    c.rect(484, 76, 776, 234, width=1.5, radius=10)
    c.icon(CURR_ICON, 534, 130, 56, color=CURR_ICON_COLOR)
    c.text_fit(CURR_TEMP, 574, 88, 186, 64, 52)
    c.text_fit(CURR_COND, 500, 160, 138, 30, 19)
    c.text_fit(CURR_HUM, 642, 160, 118, 30, 17, align="right")
    c.text_fit(TODAY_HILO_FULL, 500, 196, 260, 30, 18)

    c.rect(484, 246, 776, 464, width=1.5, radius=10)
    c.text_fit("4일 예보", 500, 254, 260, 28, 18)
    for idx in range(4):
        col_x = 496 + idx * 67
        day_label, icon_val, day_color, hilo_val, chance_val = _fc_day(idx)
        c.text_fit(day_label, col_x, 288, 63, 28, 15, align="center")
        c.icon(icon_val, col_x + 31, 344, 28, color=day_color)
        c.text_fit(hilo_val, col_x, 372, 63, 32, 14, align="center")
        c.text_fit(chance_val, col_x, 410, 63, 32, 14, align="center", color=day_color)
    return c.items


def _panel_portrait(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 480, 800)
    c.icon("calendar-today", 34, 34, 24, color=DATE_COLOR)
    c.text_fit(DATE_LONG, 54, 17, 256, 34, 24, color=DATE_COLOR)
    c.text_fit(CLOCK, 316, 18, 144, 32, 16, align="right")
    c.rect(20, 58, 460, 96, fill=CAL_BADGE_FILL, outline=CAL_BADGE_OUTLINE, width=2, radius=8)
    c.text_fit(CAL_BADGE_TEXT, 28, 61, 424, 32, 19, align="center", color=CAL_BADGE_COLOR)

    c.rect(20, 108, 460, 384, width=1.5, radius=10)
    c.icon(CURR_ICON, 64, 158, 50, color=CURR_ICON_COLOR)
    c.text_fit(CURR_TEMP, 102, 116, 162, 64, 46)
    c.text_fit(CURR_COND, 270, 114, 174, 32, 20, align="right")
    c.text_fit(CURR_HUM, 270, 148, 174, 32, 17, align="right")
    c.text_fit(TODAY_HILO_FULL, 102, 184, 342, 32, 18)
    c.line(34, 220, 446, 220)

    for idx in range(4):
        col_x = 34 + idx * 104
        day_label, icon_val, day_color, hilo_val, chance_val = _fc_day(idx)
        c.text_fit(day_label, col_x, 226, 98, 32, 17, align="center")
        c.icon(icon_val, col_x + 49, 282, 28, color=day_color)
        c.text_fit(hilo_val, col_x, 306, 98, 34, 16, align="center")
        c.text_fit(chance_val, col_x, 342, 98, 32, 16, align="center", color=day_color)

    c.rect(20, 396, 460, 784, width=1.5, radius=10)
    c.icon("calendar", 44, 420, 22, color=TEXT_INK)
    c.text_fit("다가오는 일정", 64, 404, 380, 34, 20)
    for slot in range(4):
        top = 446 + slot * 84
        if slot:
            c.line(34, top - 3, 446, top - 3)
        when_val, title_val, loc_val, slot_color = _event_slot(slot)
        c.text_fit(when_val, 36, top + 2, 232, 32, 16, color=slot_color)
        c.text_fit(loc_val, 274, top + 2, 170, 32, 15, align="right")
        c.text_fit(title_val, 36, top + 36, 408, 42, 23)
    return c.items


def generate() -> str:
    layouts: dict[str, list[FlowElement]] = {}
    profiles = (
        (_square_200, ((200, 200),)),
        (_tiny_landscape, ((212, 104), (250, 122), (250, 128), (250, 132), (296, 128), (296, 152))),
        (_medium_compact_landscape, ((384, 184), (416, 240))),
        (
            _panel_landscape,
            ((400, 300), (648, 480), (800, 480), (960, 640), (960, 680), (1600, 1200)),
        ),
    )
    portrait_map = {
        _tiny_landscape: _tiny_portrait,
        _medium_compact_landscape: _medium_compact_portrait,
        _panel_landscape: _panel_portrait,
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
