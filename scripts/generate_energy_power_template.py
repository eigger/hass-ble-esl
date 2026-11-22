#!/usr/bin/env python3
"""Regenerate the built-in energy & power monitor template across every supported size."""

from pathlib import Path
import sys

import yaml

DESTINATION = (
    Path(__file__).resolve().parents[1]
    / "custom_components/ble_esl/designer/templates/energy_power.yaml"
)

TITLE = "${title}"
POWER = "${power_sensor}"
ENERGY = "${today_energy_sensor}"
SOLAR = "${solar_sensor}"
BUDGET = "${budget_watts}"
ACCENT = "${accent}"
FONT = "${font}"

ENTITY_RE = r"^[a-z][a-z0-9_]*[.][a-z0-9_]+$"
BADGE_INK_EXPR = f"('black' if '{ACCENT}' == 'white' else '{ACCENT}')"
BADGE_FG_EXPR = "('black' if _ink == 'yellow' else 'white')"
TEXT_INK_EXPR = f"('black' if '{ACCENT}' in ('yellow', 'white') else '{ACCENT}')"
TEXT_INK = f"{{{{ {TEXT_INK_EXPR} }}}}"


def _finite(entity_expr: str, var: str, set_flag: str | None = None) -> str:
    """Emit Jinja parsing a valid entity's finite sensor float into `var` (or `none`)."""
    valid = f"{entity_expr} is match('{ENTITY_RE}')"
    flag_stmt = f"{{% set {set_flag} = {valid} %}}" if set_flag else ""
    cond = set_flag if set_flag else valid
    return (
        f"{flag_stmt}"
        f"{{% set _r = states({entity_expr}) if {cond} else '' %}}"
        f"{{% set _n = _r | float(none) if is_number(_r) and _r is not boolean else none %}}"
        f"{{% set {var} = _n if _n is not none and _n == _n and (_n | abs) < 1000000 else none %}}"
    )


def _fmt_power_or_solar(var: str, unit_var: str, out_var: str) -> str:
    """Format W/kW float cleanly into `out_var` without '-0' or trailing '.0'."""
    return (
        f"{{% set _dec = 2 if {unit_var} in ('kW', 'kw', 'KW') else 0 %}}"
        f"{{% set _f1 = (({var} | round(_dec)) + 0) %}}"
        "{% set _f2 = 0 if _f1 == 0 else _f1 %}"
        "{% set _fi = _f2 | int %}"
        f"{{% set {out_var} = ((_fi if _f2 == _fi else _f2) | string) %}}"
    )


def _fmt_energy_str(var: str, out_var: str) -> str:
    """Format up to 2-decimal energy float cleanly into `out_var` without '-0' or trailing '.0'."""
    return (
        f"{{% set _f1 = (({var} | round(2)) + 0) %}}"
        "{% set _f2 = 0 if _f1 == 0 else _f1 %}"
        "{% set _fi = _f2 | int %}"
        f"{{% set {out_var} = ((_fi if _f2 == _fi else _f2) | string) %}}"
    )


PWR_PRELUDE = (
    _finite(f"'{POWER}'", "_p")
    + f"{{% set _pu = state_attr('{POWER}', 'unit_of_measurement') or 'W' %}}"
    "{% set _pw = (_p * 1000) if (_p is not none and _pu in ('kW', 'kw', 'KW')) else _p %}"
    f"{{% set _bg = ({BUDGET} | float(3000)) %}}"
    "{% set _bg = _bg if _bg > 0 else 3000 %}"
    "{% set _ratio = ((_pw / _bg * 100) | round(0) | int) if _pw is not none else 0 %}"
    "{% set _pct = [0, [100, _ratio] | min] | max %}"
    "{% set _alert = _pw is not none and _pw >= (_bg * 0.8) %}"
    f"{{% set _ink = {BADGE_INK_EXPR} %}}{{% set _fg = {BADGE_FG_EXPR} %}}{{% set _tink = {TEXT_INK_EXPR} %}}"
    "{% set _badge = "
    "'센서 대기' if _pw is none else ("
    "'과부하' if _pw >= _bg else ("
    "'주의' if _pw >= (_bg * 0.8) else ("
    "'발전 여유' if _pw < 0 else ("
    "'보통' if _pw >= (_bg * 0.5) else '여유')))) %}"
)
ENERGY_PRELUDE = (
    _finite(f"'{ENERGY}'", "_e", "_has_e")
    + f"{{% set _eu = (state_attr('{ENERGY}', 'unit_of_measurement') or 'kWh') if _has_e else 'kWh' %}}"
)
SOLAR_PRELUDE = (
    _finite(f"'{SOLAR}'", "_s", "_has_s")
    + f"{{% set _su = (state_attr('{SOLAR}', 'unit_of_measurement') or 'W') if _has_s else 'W' %}}"
)

PWR_VAL = (
    PWR_PRELUDE
    + "{% if _p is not none %}"
    + _fmt_power_or_solar("_p", "_pu", "_pf")
    + "{{ _pf ~ ' ' ~ _pu }}{% else %}{{ '-- ' ~ _pu }}{% endif %}"
)
PWR_COLOR = PWR_PRELUDE + "{{ _tink if _alert else 'black' }}"
PWR_BAR_COLOR = PWR_PRELUDE + "{{ _ink if _alert else 'black' }}"
PWR_PCT = PWR_PRELUDE + "{{ _pct }}"
PWR_HINT = (
    PWR_PRELUDE
    + "{{ ('목표 ' ~ (_bg | round(0) | int) ~ 'W 대비 ' ~ _ratio ~ '%') if _pw is not none else ('목표 최대 ' ~ (_bg | round(0) | int) ~ 'W') }}"
)
PWR_HINT_COMPACT = (
    PWR_PRELUDE
    + "{{ ('부하 ' ~ _ratio ~ '%') if _pw is not none else ('목표 ' ~ (_bg | round(0) | int) ~ 'W') }}"
)

BADGE_TEXT = PWR_PRELUDE + "{{ _badge }}"
BADGE_FILL = PWR_PRELUDE + "{{ _ink if _alert else 'white' }}"
BADGE_OUTLINE = PWR_PRELUDE + "{{ _ink if _alert else 'black' }}"
BADGE_COLOR = PWR_PRELUDE + "{{ _fg if _alert else 'black' }}"

ENERGY_VAL = (
    ENERGY_PRELUDE
    + "{% if _e is not none %}"
    + _fmt_energy_str("_e", "_ef")
    + "{{ _ef ~ ' ' ~ _eu }}{% else %}{{ ('-- ' ~ _eu) if _has_e else '미설정' }}{% endif %}"
)
ENERGY_SHORT = (
    ENERGY_PRELUDE
    + "{% if _e is not none %}"
    + _fmt_energy_str("_e", "_ef")
    + "{{ '오늘 ' ~ _ef ~ _eu }}{% else %}{{ '오늘 --' if _has_e else '오늘 미설정' }}{% endif %}"
)

SOLAR_VAL = (
    SOLAR_PRELUDE
    + "{% if _s is not none %}"
    + _fmt_power_or_solar("_s", "_su", "_sf")
    + "{{ _sf ~ ' ' ~ _su }}{% else %}{{ ('-- ' ~ _su) if _has_s else '미설정' }}{% endif %}"
)
SOLAR_SHORT = (
    SOLAR_PRELUDE
    + "{% if _s is not none %}"
    + _fmt_power_or_solar("_s", "_su", "_sf")
    + "{{ '태양광 ' ~ _sf ~ _su }}{% else %}{{ '태양광 --' if _has_s else '태양광 미설정' }}{% endif %}"
)

ADVICE_TEXT = (
    PWR_PRELUDE
    + SOLAR_PRELUDE
    + "{% if _s is not none %}"
    + _fmt_power_or_solar("_s", "_su", "_sf")
    + "{% else %}{% set _sf = '' %}{% endif %}"
    + "{{ "
    "('목표 전력(' ~ (_bg | round(0) | int) ~ 'W)을 초과했습니다 · 대기전력 차단을 권장합니다') if (_pw is not none and _pw >= _bg) else ("
    "'전력 사용량이 높습니다 · 고전력 가전 동시 사용에 유의하세요' if _alert else ("
    "'태양광 잉여 전력이 송전 중입니다' if (_pw is not none and _pw < 0) else ("
    "('태양광 ' ~ _sf ~ _su ~ ' 발전 중 · 현재 부하 ' ~ _ratio ~ '%') if (_s is not none and _s > 0) else ("
    "('안정적인 전력 사용 중입니다 (목표 ' ~ (_bg | round(0) | int) ~ 'W 기준 ' ~ _ratio ~ '%)') if _pw is not none else "
    "'전력 센서 연결을 확인해 주세요')))) }}"
)
ADVICE_ICON = (
    PWR_PRELUDE
    + "{{ 'alert-circle-outline' if _alert else ('check-circle-outline' if _pw is not none else 'power-plug') }}"
)
ADVICE_COLOR = PWR_PRELUDE + "{{ _tink if _alert else 'black' }}"

COMPACT_FOOTER = (
    PWR_PRELUDE
    + ENERGY_PRELUDE
    + SOLAR_PRELUDE
    + "{% if _e is not none %}"
    + _fmt_energy_str("_e", "_ef")
    + "{% set _es = _ef ~ _eu %}{% else %}{% set _es = '' %}{% endif %}"
    + "{% if _s is not none %}"
    + _fmt_power_or_solar("_s", "_su", "_sf")
    + "{% set _ss = _sf ~ _su %}{% else %}{% set _ss = '' %}{% endif %}"
    + "{{ "
    "('오늘 ' ~ _es ~ ' · 태양광 ' ~ _ss) if (_es and _ss) else ("
    "('오늘 ' ~ _es ~ ' · 부하 ' ~ _ratio ~ '%') if _es else ("
    "('태양광 ' ~ _ss ~ ' · 부하 ' ~ _ratio ~ '%') if _ss else ("
    "('목표 ' ~ (_bg | round(0) | int) ~ 'W 대비 ' ~ _ratio ~ '% · ' ~ now().strftime('%H:%M')) if _pw is not none else '센서 연결 확인'))) }}"
)
PORTRAIT_SUMMARY = (
    PWR_PRELUDE
    + ENERGY_PRELUDE
    + SOLAR_PRELUDE
    + "{% if _e is not none %}"
    + _fmt_energy_str("_e", "_ef")
    + "{% set _es = _ef ~ _eu %}{% else %}{% set _es = '' %}{% endif %}"
    + "{% if _s is not none %}"
    + _fmt_power_or_solar("_s", "_su", "_sf")
    + "{% set _ss = _sf ~ _su %}{% else %}{% set _ss = '' %}{% endif %}"
    + "{{ "
    "('오늘 ' ~ _es ~ ' · 태양광 ' ~ _ss) if (_es and _ss) else ("
    "('오늘 ' ~ _es) if _es else ("
    "('태양광 ' ~ _ss) if _ss else ("
    "('부하 ' ~ _ratio ~ '% · 목표 ' ~ (_bg | round(0) | int) ~ 'W') if _pw is not none else '센서 연결 확인'))) }}"
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
    c.text_fit(PWR_VAL, 10, 14, 180, 96, 56, align="center", color=PWR_COLOR, min_size=16)
    c.line(12, 120, 188, 120)
    c.text_fit(ENERGY_SHORT, 10, 132, 180, 56, 26, align="center", min_size=16)
    return c.items


def _tiny_landscape(w: int, h: int) -> list[FlowElement]:
    large = w >= 296
    vw = 296 if large else 250
    ms = 18 if large else 16
    c = Canvas(w, h, vw, 128)
    c.text_fit(
        PWR_VAL,
        8,
        6,
        vw - 16,
        68,
        54 if large else 52,
        align="center",
        color=PWR_COLOR,
        min_size=ms,
    )
    c.line(8, 78, vw - 8, 78)
    c.text_fit(
        ENERGY_SHORT,
        8,
        84,
        vw - 16,
        38,
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
    c.text_fit(PWR_VAL, 6, 20, 116, vh * 0.44, 44, align="center", color=PWR_COLOR, min_size=ms)
    c.line(10, vh * 0.56, 118, vh * 0.56)
    c.text_fit(ENERGY_SHORT, 6, vh * 0.62, 116, vh * 0.30, 22, align="center", min_size=ms)
    return c.items


def _medium_compact_landscape(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 384, 184)
    c.text_fit(PWR_VAL, 10, 12, 232, 92, 66, align="center", color=PWR_COLOR, min_size=18)
    c.rect(250, 20, 374, 88, fill=BADGE_FILL, outline=BADGE_OUTLINE, radius=6)
    c.text_fit(BADGE_TEXT, 256, 26, 112, 56, 30, align="center", color=BADGE_COLOR, min_size=18)
    c.line(10, 108, 374, 108)
    c.text_fit(ENERGY_SHORT, 10, 118, 364, 54, 30, align="center", min_size=18)
    return c.items


def _medium_compact_portrait(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 184, 384)
    c.text_fit(PWR_VAL, 10, 20, 164, 106, 58, align="center", color=PWR_COLOR, min_size=16)
    c.rect(10, 138, 174, 214, fill=BADGE_FILL, outline=BADGE_OUTLINE, radius=6)
    c.text_fit(BADGE_TEXT, 16, 148, 152, 56, 30, align="center", color=BADGE_COLOR, min_size=16)
    c.line(12, 234, 172, 234)
    c.text_fit(ENERGY_SHORT, 10, 254, 164, 110, 28, align="center", min_size=16)
    return c.items


def _panel_landscape(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 800, 480)
    c.icon("flash", 38, 36, 28, color=PWR_COLOR)
    c.text_fit(TITLE, 60, 17, 360, 38, 28)
    c.text_fit(CLOCK, 430, 22, 144, 28, 16, align="right")
    c.rect(588, 15, 776, 55, fill=BADGE_FILL, outline=BADGE_OUTLINE, width=2, radius=10)
    c.text_fit(BADGE_TEXT, 596, 19, 172, 32, 20, align="center", color=BADGE_COLOR)
    c.line(24, 65, 776, 65, width=2)

    # Top full-width current power & load bar card
    c.rect(24, 78, 776, 244, width=1.5, radius=10)
    c.icon("lightning-bolt", 54, 108, 30, color=PWR_COLOR)
    c.text_fit("현재 실시간 전력", 76, 90, 260, 34, 22)
    c.text_fit(PWR_HINT, 356, 92, 400, 30, 18, align="right")
    c.text_fit(PWR_VAL, 42, 126, 714, 72, 60, color=PWR_COLOR)
    c.progress_bar(42, 204, 758, 226, PWR_PCT, fill=PWR_BAR_COLOR)

    # Bottom 2 cards: Today energy + Solar generation
    c.rect(24, 256, 392, 402, width=1.5, radius=10)
    c.icon("meter-electric", 52, 284, 26)
    c.text_fit("오늘 누적 사용량", 72, 267, 298, 32, 20)
    c.text_fit(ENERGY_VAL, 42, 310, 332, 68, 48)

    c.rect(408, 256, 776, 402, width=1.5, radius=10)
    c.icon("solar-power", 436, 284, 26)
    c.text_fit("태양광 발전 전력", 456, 267, 298, 32, 20)
    c.text_fit(SOLAR_VAL, 426, 310, 332, 68, 48)

    c.rect(24, 414, 776, 466, width=1.5, radius=8)
    c.icon(ADVICE_ICON, 48, 440, 22, color=ADVICE_COLOR)
    c.text_fit(ADVICE_TEXT, 68, 422, 692, 36, 18)
    return c.items


def _panel_portrait(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 480, 800)
    c.icon("flash", 34, 34, 24, color=PWR_COLOR)
    c.text_fit(TITLE, 54, 17, 256, 34, 24)
    c.text_fit(CLOCK, 316, 18, 144, 32, 16, align="right")
    c.rect(20, 58, 460, 98, fill=BADGE_FILL, outline=BADGE_OUTLINE, width=2, radius=8)
    c.text_fit(BADGE_TEXT, 28, 62, 424, 32, 19, align="center", color=BADGE_COLOR)

    c.rect(20, 110, 460, 334, width=1.5, radius=10)
    c.icon("lightning-bolt", 46, 138, 28, color=PWR_COLOR)
    c.text_fit("현재 실시간 전력", 68, 120, 376, 34, 21)
    c.text_fit(PWR_VAL, 36, 162, 408, 84, 62, color=PWR_COLOR)
    c.progress_bar(36, 256, 444, 276, PWR_PCT, fill=PWR_BAR_COLOR)
    c.text_fit(PWR_HINT, 36, 286, 408, 34, 17)

    c.rect(20, 348, 460, 524, width=1.5, radius=10)
    c.icon("meter-electric", 46, 376, 26)
    c.text_fit("오늘 누적 사용량", 68, 358, 376, 34, 21)
    c.text_fit(ENERGY_VAL, 36, 404, 408, 92, 52)

    c.rect(20, 538, 460, 714, width=1.5, radius=10)
    c.icon("solar-power", 46, 566, 26)
    c.text_fit("태양광 발전 전력", 68, 548, 376, 34, 21)
    c.text_fit(SOLAR_VAL, 36, 594, 408, 92, 52)

    c.rect(20, 728, 460, 784, width=1.5, radius=8)
    c.icon(ADVICE_ICON, 46, 756, 22, color=ADVICE_COLOR)
    c.text_fit(ADVICE_TEXT, 66, 738, 380, 36, 17)
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
        "id": "energy_power",
        "name": {"en": "Energy & power", "ko": "에너지 · 전력 모니터"},
        "description": {
            "en": "Live home power load against a target budget, plus optional daily energy and solar generation.",
            "ko": "실시간 소비 전력과 목표 전력 대비 부하 상태, 선택 일일 사용량·태양광 발전량을 표시합니다.",
        },
        "background": "white",
        "parameters": {
            "title": {
                "type": "string",
                "default": "전력 모니터",
                "min_length": 1,
                "label": {"en": "Title", "ko": "제목"},
            },
            "power_sensor": {
                "type": "entity",
                "domain": "sensor",
                "default": "sensor.power",
                "label": {"en": "Current power sensor", "ko": "현재 전력 센서"},
            },
            "today_energy_sensor": {
                "type": "string",
                "default": "",
                "label": {
                    "en": "Today energy sensor ID (optional)",
                    "ko": "오늘 사용량 센서 ID (선택)",
                },
            },
            "solar_sensor": {
                "type": "string",
                "default": "",
                "label": {
                    "en": "Solar generation sensor ID (optional)",
                    "ko": "태양광 발전 센서 ID (선택)",
                },
            },
            "budget_watts": {
                "type": "number",
                "default": 3000,
                "min": 100,
                "max": 50000,
                "label": {"en": "Target peak budget (W)", "ko": "목표 최대 전력 (W)"},
            },
            "accent": {
                "type": "color",
                "default": "red",
                "label": {"en": "Alert color", "ko": "경고 강조 색상"},
            },
            "font": {
                "type": "font",
                "default": "NotoSansKR-Bold.ttf",
                "label": {"en": "Font", "ko": "글꼴"},
            },
            "interval": {
                "type": "select",
                "group": "automation",
                "options": ["1", "5", "10", "15"],
                "default": "5",
                "label": {"en": "Update every (minutes)", "ko": "갱신 주기 (분)"},
            },
        },
        "layouts": layouts,
        "automation": {
            "triggers": [{"trigger": "time_pattern", "minutes": "/${interval}"}],
            "mode": "single",
        },
    }
    output = "# Generated by scripts/generate_energy_power_template.py\n" + yaml.dump(
        data, Dumper=TemplateDumper, allow_unicode=True, sort_keys=False, width=4096
    )
    if len(output.encode("utf-8")) >= 256 * 1024:
        raise ValueError("energy_power.yaml exceeds 256 KB template limit")
    return output


if __name__ == "__main__":
    DESTINATION.write_text(generate(), encoding="utf-8")
