#!/usr/bin/env python3
"""Regenerate the built-in EV battery & charging template across every supported size."""

from pathlib import Path
import sys

import yaml

DESTINATION = (
    Path(__file__).resolve().parents[1]
    / "custom_components/ble_esl/designer/templates/ev_charging.yaml"
)

TITLE = "${title}"
BATTERY = "${battery_sensor}"
RANGE = "${range_sensor}"
STATUS = "${status_sensor}"
POWER = "${power_sensor}"
LOW_THRESHOLD = "${low_threshold}"
ACCENT = "${accent}"
FONT = "${font}"

ENTITY_RE = r"^[a-z][a-z0-9_]*[.][a-z0-9_]+$"
BADGE_INK_EXPR = f"('black' if '{ACCENT}' == 'white' else '{ACCENT}')"
BADGE_FG_EXPR = "('black' if _ink == 'yellow' else 'white')"
TEXT_INK_EXPR = f"('black' if '{ACCENT}' in ('yellow', 'white') else '{ACCENT}')"


def _finite(entity_expr: str, var: str, set_flag: str | None = None) -> str:
    """Emit Jinja parsing a valid entity's finite numeric state into `var` (or `none`)."""
    valid = f"{entity_expr} is match('{ENTITY_RE}')"
    flag_stmt = f"{{% set {set_flag} = {valid} %}}" if set_flag else ""
    cond = set_flag if set_flag else valid
    return (
        f"{flag_stmt}"
        f"{{% set _r = states({entity_expr}) if {cond} else '' %}}"
        f"{{% set _n = _r | float(none) if is_number(_r) and _r is not boolean else none %}}"
        f"{{% set {var} = _n if _n is not none and _n == _n and (_n | abs) < 1000000 else none %}}"
    )


def _fmt_num(var: str, decimals: int, out_var: str) -> str:
    """Format float cleanly into `out_var` without '-0' or trailing '.0'."""
    return (
        f"{{% set _f1 = (({var} | round({decimals})) + 0) %}}"
        "{% set _f2 = 0 if _f1 == 0 else _f1 %}"
        "{% set _fi = _f2 | int %}"
        f"{{% set {out_var} = ((_fi if _f2 == _fi else _f2) | string) %}}"
    )


def _fmt_power(var: str, unit_var: str, out_var: str) -> str:
    """Format EV charging W/kW float cleanly into `out_var` without '-0' or trailing '.0'."""
    return (
        f"{{% set _dec = 0 if {unit_var} in ('W', 'w') else 2 %}}"
        f"{{% set _f1 = (({var} | round(_dec)) + 0) %}}"
        "{% set _f2 = 0 if _f1 == 0 else _f1 %}"
        "{% set _fi = _f2 | int %}"
        f"{{% set {out_var} = ((_fi if _f2 == _fi else _f2) | string) %}}"
    )


STATUS_PRELUDE = (
    f"{{% set _has_st = '{STATUS}' is match('{ENTITY_RE}') %}}"
    f"{{% set _st_raw = (states('{STATUS}') | string | trim) if _has_st else '' %}}"
    "{% set _stl = _st_raw | lower %}"
    "{% set _st_valid = _has_st and _stl not in ('', 'unknown', 'unavailable', 'none') %}"
    "{% set _sk = "
    "'fault' if _stl in ('error', 'fault', 'failed') else ("
    "'charging' if _stl in ('charging', 'fast_charging', 'rapid_charging', 'connected_charging', 'on', 'true') else ("
    "'complete' if _stl in ('complete', 'completed', 'charged', 'full', 'done') else ("
    "'connected' if _stl in ('connected', 'plugged_in', 'plugged', 'ready', 'standby', 'idle') else ("
    "'disconnected' if _stl in ('disconnected', 'unplugged', 'not_charging', 'off', 'false', 'away') else ("
    "'custom' if _st_valid else 'none'))))) %}"
)

POWER_PRELUDE = (
    _finite(f"'{POWER}'", "_pw", "_has_pw")
    + f"{{% set _pu = (state_attr('{POWER}', 'unit_of_measurement') or 'kW') if _has_pw else 'kW' %}}"
)

RANGE_PRELUDE = (
    _finite(f"'{RANGE}'", "_rn", "_has_rng")
    + "{% set _rng = ([0, _rn] | max) if _rn is not none else none %}"
    + f"{{% set _ru = (state_attr('{RANGE}', 'unit_of_measurement') or 'km') if _has_rng else 'km' %}}"
)

EV_PRELUDE = (
    _finite(f"'{BATTERY}'", "_sr")
    + "{% set _soc = ([0, [100, _sr] | min] | max) if _sr is not none else none %}"
    "{% set _pct = (_soc | round(0) | int) if _soc is not none else 0 %}"
    f"{{% set _low_cfg = ({LOW_THRESHOLD} | float(20)) %}}"
    "{% set _low = _low_cfg if (5 <= _low_cfg <= 50) else 20 %}"
    "{% set _is_low = _soc is not none and _soc <= _low %}"
    + STATUS_PRELUDE
    + POWER_PRELUDE
    + "{% set _pw_kw = (_pw / 1000) if (_pw is not none and _pu in ('W', 'w')) else _pw %}"
    "{% set _inferred_chg = (_sk == 'none') and (_pw_kw is not none and _pw_kw > 0.1) %}"
    "{% set _eff_sk = 'charging' if (_sk == 'charging' or _inferred_chg) else _sk %}"
    "{% set _alert = _eff_sk == 'fault' or _is_low %}"
    "{% set _charging = _eff_sk == 'charging' %}"
    "{% set _hl = _alert or _charging %}"
    f"{{% set _ink = {BADGE_INK_EXPR} %}}{{% set _fg = {BADGE_FG_EXPR} %}}{{% set _tink = {TEXT_INK_EXPR} %}}"
    "{% set _badge = "
    "'충전 오류' if _eff_sk == 'fault' else ("
    "'충전 필요' if _is_low else ("
    "'충전 중' if _charging else ("
    "'완충' if (_eff_sk == 'complete' or (_soc is not none and _soc >= 95 and _eff_sk in ('none', 'connected'))) else ("
    "'대기 중' if _eff_sk == 'connected' else ("
    "'미연결' if _eff_sk == 'disconnected' else ("
    "_st_raw[:10] if _eff_sk == 'custom' else ("
    "'센서 대기' if _soc is none else ("
    "'충분' if _soc >= 60 else '보통')))))))) %}"
)

SOC_VAL = (
    EV_PRELUDE
    + "{% if _soc is not none %}"
    + _fmt_num("_soc", 1, "_sf")
    + "{{ _sf ~ '%' }}{% else %}--%{% endif %}"
)
SOC_COLOR = EV_PRELUDE + "{{ _tink if _alert else 'black' }}"
BAR_COLOR = EV_PRELUDE + "{{ _ink if _hl else 'black' }}"
SOC_PCT = EV_PRELUDE + "{{ _pct }}"
BAT_ICON = (
    EV_PRELUDE
    + "{{ 'battery-alert' if _alert else ('battery-charging' if _charging else 'battery') }}"
)

SOC_HINT = (
    EV_PRELUDE
    + "{{ ('경고 기준 ' ~ (_low | round(0) | int) ~ '% 이하') if _is_low else ('저잔량 기준 ' ~ (_low | round(0) | int) ~ '%') }}"
)
SOC_HINT_COMPACT = EV_PRELUDE + "{{ '기준 ' ~ (_low | round(0) | int) ~ '%' }}"

BADGE_TEXT = EV_PRELUDE + "{{ _badge }}"
BADGE_FILL = EV_PRELUDE + "{{ _ink if _hl else 'white' }}"
BADGE_OUTLINE = EV_PRELUDE + "{{ _ink if _hl else 'black' }}"
BADGE_COLOR = EV_PRELUDE + "{{ _fg if _hl else 'black' }}"

RANGE_VAL = (
    RANGE_PRELUDE
    + "{% if _rng is not none %}"
    + _fmt_num("_rng", 0, "_rf")
    + "{{ _rf ~ ' ' ~ _ru }}{% else %}{{ ('-- ' ~ _ru) if _has_rng else '미설정' }}{% endif %}"
)
RANGE_SHORT = (
    RANGE_PRELUDE
    + "{% if _rng is not none %}"
    + _fmt_num("_rng", 0, "_rf")
    + "{{ '주행 ' ~ _rf ~ _ru }}{% else %}{{ '주행 --' if _has_rng else '주행 미설정' }}{% endif %}"
)

PWR_VAL = (
    POWER_PRELUDE
    + "{% if _pw is not none %}"
    + _fmt_power("_pw", "_pu", "_pf")
    + "{{ _pf ~ ' ' ~ _pu }}{% else %}{{ ('-- ' ~ _pu) if _has_pw else '미설정' }}{% endif %}"
)
PWR_SHORT = (
    POWER_PRELUDE
    + "{% if _pw is not none %}"
    + _fmt_power("_pw", "_pu", "_pf")
    + "{{ '충전 ' ~ _pf ~ _pu }}{% else %}{{ '충전 --' if _has_pw else '충전 미설정' }}{% endif %}"
)

STATUS_DETAIL = (
    EV_PRELUDE
    + RANGE_PRELUDE
    + "{% if _rng is not none %}"
    + _fmt_num("_rng", 0, "_rf")
    + "{% set _rs = _rf ~ _ru %}{% else %}{% set _rs = '' %}{% endif %}"
    + "{% if _pw is not none %}"
    + _fmt_power("_pw", "_pu", "_pf")
    + "{% set _ps = _pf ~ _pu %}{% else %}{% set _ps = '' %}{% endif %}"
    + "{{ "
    "'충전기 오류 상태입니다 · 케이블과 충전기를 확인하세요' if _eff_sk == 'fault' else ("
    "('배터리 잔량이 낮습니다 · 목표 충전(' ~ (_low | round(0) | int) ~ '%) 미만') if _is_low else ("
    "('충전 진행 중 · 출력 ' ~ _ps) if (_charging and _ps) else ("
    "'현재 차량 충전이 진행 중입니다' if _charging else ("
    "('충전이 완료되었습니다' ~ (' · 예상 주행 ' ~ _rs if _rs else '')) if _eff_sk == 'complete' else ("
    "('케이블 연결됨 · 대기 중' ~ (' (예상 ' ~ _rs ~ ')' if _rs else '')) if _eff_sk == 'connected' else ("
    "'충전 케이블이 분리되어 있습니다' if _eff_sk == 'disconnected' else ("
    "('현재 상태: ' ~ _st_raw[:16]) if _eff_sk == 'custom' else ("
    "'배터리 센서 연결을 확인해 주세요' if _soc is none else "
    "('운행 준비 완료' ~ (' · 예상 주행 ' ~ _rs if _rs else ' · 상태 양호')))))))))) }}"
)
STATUS_ICON = (
    EV_PRELUDE
    + "{{ 'alert-circle-outline' if _alert else ('battery-charging' if _charging else 'car-electric') }}"
)
STATUS_COLOR = EV_PRELUDE + "{{ _tink if _alert else 'black' }}"

COMPACT_FOOTER = (
    EV_PRELUDE
    + RANGE_PRELUDE
    + "{% if _rng is not none %}"
    + _fmt_num("_rng", 0, "_rf")
    + "{% set _rs = _rf ~ _ru %}{% else %}{% set _rs = '' %}{% endif %}"
    + "{% if _pw is not none %}"
    + _fmt_power("_pw", "_pu", "_pf")
    + "{% set _ps = _pf ~ _pu %}{% else %}{% set _ps = '' %}{% endif %}"
    + "{{ "
    "('주행 ' ~ _rs ~ ' · 충전 ' ~ _ps) if (_rs and _ps) else ("
    "('예상 주행 ' ~ _rs ~ ' · 기준 ' ~ (_low | round(0) | int) ~ '%') if _rs else ("
    "('충전 출력 ' ~ _ps ~ ' · 기준 ' ~ (_low | round(0) | int) ~ '%') if _ps else ("
    "('저잔량 기준 ' ~ (_low | round(0) | int) ~ '% · ' ~ now().strftime('%H:%M')) if _soc is not none else '배터리 센서 확인'))) }}"
)
PORTRAIT_SUMMARY = (
    EV_PRELUDE
    + RANGE_PRELUDE
    + "{% if _rng is not none %}"
    + _fmt_num("_rng", 0, "_rf")
    + "{% set _rs = _rf ~ _ru %}{% else %}{% set _rs = '' %}{% endif %}"
    + "{% if _pw is not none %}"
    + _fmt_power("_pw", "_pu", "_pf")
    + "{% set _ps = _pf ~ _pu %}{% else %}{% set _ps = '' %}{% endif %}"
    + "{{ "
    "('주행 ' ~ _rs ~ ' · 충전 ' ~ _ps) if (_rs and _ps) else ("
    "('예상 주행 ' ~ _rs) if _rs else ("
    "('충전 출력 ' ~ _ps) if _ps else ("
    "('기준 ' ~ (_low | round(0) | int) ~ '% · ' ~ _badge) if _soc is not none else '센서 연결 확인'))) }}"
)
RANGE_PWR_COMPACT = (
    EV_PRELUDE
    + RANGE_PRELUDE
    + "{% if _rng is not none %}"
    + _fmt_num("_rng", 0, "_rf")
    + "{% set _rs = _rf ~ ' ' ~ _ru %}{% else %}{% set _rs = '' %}{% endif %}"
    + "{% if _pw is not none %}"
    + _fmt_power("_pw", "_pu", "_pf")
    + "{% set _ps = _pf ~ ' ' ~ _pu %}{% else %}{% set _ps = '' %}{% endif %}"
    + "{{ (_rs ~ ' · ' ~ _ps) if (_rs and _ps) else (_rs if _rs else (_ps if _ps else _badge)) }}"
)
CLOCK = "{{ now().strftime('%H:%M 갱신') }}"


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
                    "max_lines": 1,
                    "line_spacing": 0,
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

    def progress_bar(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        progress: str,
        *,
        fill: str = "black",
    ) -> None:
        self.items.append(
            FlowElement(
                {
                    "type": "progress_bar",
                    "x_start": self.rx(x0),
                    "y_start": self.ry(y0),
                    "x_end": self.rx(x1),
                    "y_end": self.ry(y1),
                    "progress": progress,
                    "fill": fill,
                    "outline": "black",
                    "background": "white",
                    "show_percentage": False,
                }
            )
        )


def _square_200(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 200, 200)
    c.text_fit(SOC_VAL, 8, 12, 108, 92, 54, align="center", color=SOC_COLOR, min_size=16)
    c.rect(120, 22, 192, 88, fill=BADGE_FILL, outline=BADGE_OUTLINE, radius=6)
    c.text_fit(BADGE_TEXT, 124, 28, 64, 54, 24, align="center", color=BADGE_COLOR, min_size=16)
    c.line(10, 114, 190, 114)
    c.text_fit(RANGE_VAL, 10, 126, 180, 60, 28, align="center", min_size=16)
    return c.items


def _tiny_landscape(w: int, h: int) -> list[FlowElement]:
    large = w >= 296
    vw = 296 if large else 250
    ms = 18 if large else 16
    split = 152 if large else 128
    c = Canvas(w, h, vw, 128)
    c.text_fit(
        SOC_VAL,
        6,
        6,
        split - 10,
        66,
        54 if large else 52,
        align="center",
        color=SOC_COLOR,
        min_size=ms,
    )
    c.rect(split + 2, 10, vw - 6, 68, fill=BADGE_FILL, outline=BADGE_OUTLINE, radius=5)
    c.text_fit(
        BADGE_TEXT,
        split + 6,
        14,
        vw - split - 16,
        50,
        26,
        align="center",
        color=BADGE_COLOR,
        min_size=ms,
    )
    c.line(8, 76, vw - 8, 76)
    c.text_fit(
        RANGE_VAL,
        8,
        82,
        vw - 16,
        40,
        28 if large else 26,
        align="center",
        min_size=ms,
    )
    return c.items


def _tiny_portrait(w: int, h: int) -> list[FlowElement]:
    tall = h >= 296
    vh = 296 if tall else 250
    ms = 15 if tall else 14
    c = Canvas(w, h, 128, vh)
    c.text_fit(SOC_VAL, 6, 12, 116, vh * 0.30, 44, align="center", color=SOC_COLOR, min_size=ms)
    c.rect(6, vh * 0.36, 122, vh * 0.62, fill=BADGE_FILL, outline=BADGE_OUTLINE, radius=5)
    c.text_fit(
        BADGE_TEXT,
        10,
        vh * 0.39,
        108,
        vh * 0.20,
        22,
        align="center",
        color=BADGE_COLOR,
        min_size=ms,
    )
    c.text_fit(RANGE_VAL, 6, vh * 0.66, 116, vh * 0.28, 22, align="center", min_size=ms)
    return c.items


def _medium_compact_landscape(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 384, 184)
    c.text_fit(SOC_VAL, 10, 12, 200, 92, 68, align="center", color=SOC_COLOR, min_size=18)
    c.rect(218, 18, 374, 92, fill=BADGE_FILL, outline=BADGE_OUTLINE, radius=6)
    c.text_fit(BADGE_TEXT, 226, 26, 140, 58, 30, align="center", color=BADGE_COLOR, min_size=18)
    c.line(10, 108, 374, 108)
    c.text_fit(RANGE_PWR_COMPACT, 10, 118, 364, 54, 30, align="center", min_size=18)
    return c.items


def _medium_compact_portrait(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 184, 384)
    c.text_fit(SOC_VAL, 10, 18, 164, 106, 60, align="center", color=SOC_COLOR, min_size=16)
    c.rect(10, 138, 174, 214, fill=BADGE_FILL, outline=BADGE_OUTLINE, radius=6)
    c.text_fit(BADGE_TEXT, 16, 148, 152, 56, 30, align="center", color=BADGE_COLOR, min_size=16)
    c.line(12, 234, 172, 234)
    c.text_fit(RANGE_PWR_COMPACT, 10, 254, 164, 110, 28, align="center", min_size=16)
    return c.items


def _panel_landscape(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 800, 480)
    c.icon("car-electric", 38, 36, 28, color=SOC_COLOR)
    c.text_fit(TITLE, 60, 17, 360, 38, 28)
    c.text_fit(CLOCK, 430, 22, 144, 28, 16, align="right")
    c.rect(588, 15, 776, 55, fill=BADGE_FILL, outline=BADGE_OUTLINE, width=2, radius=10)
    c.text_fit(BADGE_TEXT, 596, 19, 172, 32, 20, align="center", color=BADGE_COLOR)
    c.line(24, 65, 776, 65, width=2)

    c.rect(24, 78, 776, 244, width=1.5, radius=10)
    c.icon(BAT_ICON, 54, 108, 30, color=SOC_COLOR)
    c.text_fit("배터리 충전 잔량", 76, 90, 260, 34, 22)
    c.text_fit(SOC_HINT, 356, 92, 400, 30, 18, align="right")
    c.text_fit(SOC_VAL, 42, 126, 714, 72, 60, color=SOC_COLOR)
    c.progress_bar(42, 204, 758, 226, SOC_PCT, fill=BAR_COLOR)

    c.rect(24, 256, 392, 402, width=1.5, radius=10)
    c.icon("map-marker-distance", 52, 284, 26)
    c.text_fit("주행 가능 거리", 72, 267, 298, 32, 20)
    c.text_fit(RANGE_VAL, 42, 310, 332, 68, 48)

    c.rect(408, 256, 776, 402, width=1.5, radius=10)
    c.icon("ev-station", 436, 284, 26)
    c.text_fit("현재 충전 전력", 456, 267, 298, 32, 20)
    c.text_fit(PWR_VAL, 426, 310, 332, 68, 48)

    c.rect(24, 414, 776, 466, width=1.5, radius=8)
    c.icon(STATUS_ICON, 48, 440, 22, color=STATUS_COLOR)
    c.text_fit(STATUS_DETAIL, 68, 422, 692, 36, 18)
    return c.items


def _panel_portrait(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 480, 800)
    c.icon("car-electric", 34, 34, 24, color=SOC_COLOR)
    c.text_fit(TITLE, 54, 17, 256, 34, 24)
    c.text_fit(CLOCK, 316, 18, 144, 32, 16, align="right")
    c.rect(20, 58, 460, 98, fill=BADGE_FILL, outline=BADGE_OUTLINE, width=2, radius=8)
    c.text_fit(BADGE_TEXT, 28, 62, 424, 32, 19, align="center", color=BADGE_COLOR)

    c.rect(20, 110, 460, 334, width=1.5, radius=10)
    c.icon(BAT_ICON, 46, 138, 28, color=SOC_COLOR)
    c.text_fit("배터리 충전 잔량", 68, 120, 376, 34, 21)
    c.text_fit(SOC_VAL, 36, 162, 408, 84, 62, color=SOC_COLOR)
    c.progress_bar(36, 256, 444, 276, SOC_PCT, fill=BAR_COLOR)
    c.text_fit(SOC_HINT, 36, 286, 408, 34, 17)

    c.rect(20, 348, 460, 524, width=1.5, radius=10)
    c.icon("map-marker-distance", 46, 376, 26)
    c.text_fit("주행 가능 거리", 68, 358, 376, 34, 21)
    c.text_fit(RANGE_VAL, 36, 404, 408, 92, 52)

    c.rect(20, 538, 460, 714, width=1.5, radius=10)
    c.icon("ev-station", 46, 566, 26)
    c.text_fit("현재 충전 전력", 68, 548, 376, 34, 21)
    c.text_fit(PWR_VAL, 36, 594, 408, 92, 52)

    c.rect(20, 728, 460, 784, width=1.5, radius=8)
    c.icon(STATUS_ICON, 46, 756, 22, color=STATUS_COLOR)
    c.text_fit(STATUS_DETAIL, 66, 738, 380, 36, 17)
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
        "id": "ev_charging",
        "name": {"en": "EV & battery charging", "ko": "전기차 · 배터리 충전"},
        "description": {
            "en": "EV battery level with low-charge alert, charging status badge, and optional range and power sensors.",
            "ko": "전기차 배터리 잔량과 저잔량 경고, 충전 상태 배지, 선택 주행 거리·충전 전력을 표시합니다.",
        },
        "background": "white",
        "parameters": {
            "title": {
                "type": "string",
                "default": "EV 충전 상태",
                "min_length": 1,
                "label": {"en": "Title", "ko": "제목"},
            },
            "battery_sensor": {
                "type": "entity",
                "domain": "sensor",
                "default": "sensor.ev_battery",
                "label": {"en": "Battery SOC sensor", "ko": "배터리 잔량 센서"},
            },
            "range_sensor": {
                "type": "string",
                "default": "",
                "label": {
                    "en": "Estimated range sensor ID (optional)",
                    "ko": "주행 가능 거리 센서 ID (선택)",
                },
            },
            "status_sensor": {
                "type": "string",
                "default": "",
                "label": {
                    "en": "Charging status sensor ID (optional)",
                    "ko": "충전 상태 센서 ID (선택)",
                },
            },
            "power_sensor": {
                "type": "string",
                "default": "",
                "label": {
                    "en": "Charging power sensor ID (optional)",
                    "ko": "충전 전력 센서 ID (선택)",
                },
            },
            "low_threshold": {
                "type": "number",
                "default": 20,
                "min": 5,
                "max": 50,
                "label": {"en": "Low battery alert (%)", "ko": "저잔량 경고 기준 (%)"},
            },
            "accent": {
                "type": "color",
                "default": "red",
                "label": {"en": "Highlight & alert color", "ko": "강조 · 경고 색상"},
            },
            "font": {
                "type": "font",
                "default": "NotoSansKR-Bold.ttf",
                "label": {"en": "Font", "ko": "글꼴"},
            },
            "interval": {
                "type": "select",
                "group": "automation",
                "options": ["5", "10", "15", "30"],
                "default": "10",
                "label": {"en": "Update every (minutes)", "ko": "갱신 주기 (분)"},
            },
        },
        "layouts": layouts,
        "automation": {
            "triggers": [{"trigger": "time_pattern", "minutes": "/${interval}"}],
            "mode": "single",
        },
    }
    output = "# Generated by scripts/generate_ev_charging_template.py\n" + yaml.dump(
        data, Dumper=TemplateDumper, allow_unicode=True, sort_keys=False, width=4096
    )
    if len(output.encode("utf-8")) >= 256 * 1024:
        raise ValueError("ev_charging.yaml exceeds 256 KB template limit")
    return output


if __name__ == "__main__":
    DESTINATION.write_text(generate(), encoding="utf-8")
