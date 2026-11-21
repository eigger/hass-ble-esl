#!/usr/bin/env python3
"""Regenerate the built-in indoor climate template across every supported size."""

from pathlib import Path
import sys

import yaml

DESTINATION = (
    Path(__file__).resolve().parents[1]
    / "custom_components/ble_esl/designer/templates/indoor_climate.yaml"
)

TITLE = "${title}"
TEMP = "${temp_sensor}"
HUM = "${humidity_sensor}"
CO2 = "${co2_sensor}"
PM25 = "${pm25_sensor}"
ACCENT = "${accent}"
FONT = "${font}"

INK_EXPR = f"('black' if '{ACCENT}' == 'white' else '{ACCENT}')"
FG_EXPR = f"('black' if '{ACCENT}' in ('yellow', 'white') else 'white')"


def _finite(entity_expr: str, var: str) -> str:
    """Emit Jinja parsing a finite sensor float into `var` (or `none`)."""
    return (
        f"{{% set _r = states({entity_expr}) if '.' in ({entity_expr}) else '' %}}"
        f"{{% set _n = _r | float(none) if is_number(_r) and _r is not boolean else none %}}"
        f"{{% set {var} = _n if _n is not none and _n == _n and (_n | abs) < 100000 else none %}}"
    )


TEMP_PRELUDE = _finite(f"'{TEMP}'", "_t")
HUM_PRELUDE = _finite(f"'{HUM}'", "_h")
CO2_PRELUDE = _finite(f"'{CO2}'", "_c")
PM25_PRELUDE = _finite(f"'{PM25}'", "_p")

STATUS_PRELUDE = (
    TEMP_PRELUDE
    + HUM_PRELUDE
    + CO2_PRELUDE
    + PM25_PRELUDE
    + f"{{% set _ink = {INK_EXPR} %}}"
    + f"{{% set _fg = {FG_EXPR} %}}"
    + "{% set _alert = "
    "(_c is not none and _c >= 1000) or "
    "(_p is not none and _p >= 36) or "
    "(_h is not none and (_h < 30 or _h > 65)) or "
    "(_t is not none and (_t > 28 or _t < 15)) %}"
    "{% set _badge = "
    "'환기 필수' if (_c is not none and _c >= 1500) else ("
    "'환기 권장' if (_c is not none and _c >= 1000) else ("
    "'먼지 나쁨' if (_p is not none and _p >= 36) else ("
    "'건조 주의' if (_h is not none and _h < 30) else ("
    "'다습 주의' if (_h is not none and _h > 65) else ("
    "'고온 주의' if (_t is not none and _t > 28) else ("
    "'저온 주의' if (_t is not none and _t < 15) else ("
    "'센서 대기' if (_t is none and _h is none) else ("
    "'쾌적' if (_t is not none and 20 <= _t <= 26 and (_h is none or 40 <= _h <= 60)) else ("
    "'적정' if (_h is not none and 40 <= _h <= 60 and _t is none) else '보통'))))))))) %}"
)

TEMP_VAL = (
    TEMP_PRELUDE + "{% set _u = state_attr('" + TEMP + "', 'unit_of_measurement') or '°C' %}"
    "{{ ((_t | round(1) | string | replace('.0', '')) ~ _u) if _t is not none else '--' ~ _u }}"
)
TEMP_CHIP = (
    TEMP_PRELUDE
    + "{{ '대기' if _t is none else ('과열' if _t > 28 else ('적정' if _t >= 20 else ('서늘' if _t >= 16 else '추움'))) }}"
)
TEMP_COLOR = (
    TEMP_PRELUDE + f"{{{{ {INK_EXPR} if _t is not none and (_t > 28 or _t < 15) else 'black' }}}}"
)
TEMP_PCT = (
    TEMP_PRELUDE
    + "{{ [0, [100, ((_t - 10) / 25 * 100) | round(0) | int] | min] | max if _t is not none else 0 }}"
)

HUM_VAL = HUM_PRELUDE + "{{ ((_h | round(0) | int | string) ~ '%') if _h is not none else '--%' }}"
HUM_CHIP = (
    HUM_PRELUDE
    + "{{ '대기' if _h is none else ('습함' if _h > 65 else ('적정' if _h >= 40 else ('주의' if _h >= 30 else '건조'))) }}"
)
HUM_COLOR = (
    HUM_PRELUDE + f"{{{{ {INK_EXPR} if _h is not none and (_h < 30 or _h > 65) else 'black' }}}}"
)
HUM_PCT = HUM_PRELUDE + "{{ [0, [100, _h | round(0) | int] | min] | max if _h is not none else 0 }}"

CO2_VAL = (
    CO2_PRELUDE
    + f"{{% set _set = '.' in '{CO2}' %}}"
    + "{{ ((_c | round(0) | int | string) ~ ' ppm') if _c is not none else ('-- ppm' if _set else '미설정') }}"
)
CO2_CHIP = (
    CO2_PRELUDE
    + f"{{% set _set = '.' in '{CO2}' %}}"
    + "{{ '선택' if not _set else ('대기' if _c is none else ('환기 필수' if _c >= 1500 else ('환기 권장' if _c >= 1000 else ('보통' if _c >= 700 else '좋음')))) }}"
)
CO2_COLOR = CO2_PRELUDE + f"{{{{ {INK_EXPR} if _c is not none and _c >= 1000 else 'black' }}}}"
CO2_PCT = (
    CO2_PRELUDE
    + "{{ [0, [100, ((_c - 400) / 1600 * 100) | round(0) | int] | min] | max if _c is not none else 0 }}"
)

PM25_VAL = (
    PM25_PRELUDE
    + f"{{% set _set = '.' in '{PM25}' %}}"
    + "{{ ((_p | round(0) | int | string) ~ ' ug/m3') if _p is not none else ('-- ug/m3' if _set else '미설정') }}"
)
PM25_CHIP = (
    PM25_PRELUDE
    + f"{{% set _set = '.' in '{PM25}' %}}"
    + "{{ '선택' if not _set else ('대기' if _p is none else ('매우 나쁨' if _p >= 76 else ('나쁨' if _p >= 36 else ('보통' if _p >= 16 else '좋음')))) }}"
)
PM25_COLOR = PM25_PRELUDE + f"{{{{ {INK_EXPR} if _p is not none and _p >= 36 else 'black' }}}}"
PM25_PCT = (
    PM25_PRELUDE + "{{ [0, [100, _p | round(0) | int] | min] | max if _p is not none else 0 }}"
)

BADGE_TEXT = STATUS_PRELUDE + "{{ _badge }}"
BADGE_FILL = STATUS_PRELUDE + "{{ _ink if _alert else 'white' }}"
BADGE_OUTLINE = STATUS_PRELUDE + "{{ _ink if _alert else 'black' }}"
BADGE_COLOR = STATUS_PRELUDE + "{{ _fg if _alert else 'black' }}"

ADVICE_TEXT = (
    STATUS_PRELUDE + "{{ "
    "'CO2 농도가 높습니다 · 창문을 열어 10분간 환기하세요' if (_c is not none and _c >= 1000) else ("
    "'초미세먼지가 높습니다 · 공기청정기를 가동하세요' if (_p is not none and _p >= 36) else ("
    "'실내가 건조합니다 · 가습기 사용을 권장합니다' if (_h is not none and _h < 30) else ("
    "'습도가 높습니다 · 제습 또는 환기가 필요합니다' if (_h is not none and _h > 65) else ("
    "'실내 온도가 높습니다 · 냉방 또는 환기가 필요합니다' if (_t is not none and _t > 28) else ("
    "'실내 온도가 낮습니다 · 난방 확인이 필요합니다' if (_t is not none and _t < 15) else ("
    "'온도·습도 센서 연결을 확인해 주세요' if (_t is none and _h is none) else ("
    "'온도·습도·공기질 모두 쾌적한 상태입니다' if (_t is not none and 20 <= _t <= 26 and (_h is none or 40 <= _h <= 60)) else "
    "'무난한 실내 환경입니다 · 주기적인 환기를 유지하세요'))))))) }}"
)
ADVICE_ICON = (
    STATUS_PRELUDE
    + "{{ 'window-open-variant' if _alert else ('check-circle-outline' if _t is not none or _h is not none else 'alert-circle-outline') }}"
)
ADVICE_COLOR = STATUS_PRELUDE + "{{ _ink if _alert else 'black' }}"

COMPACT_FOOTER = (
    STATUS_PRELUDE + "{{ "
    "('CO2 ' ~ (_c | round(0) | int) ~ 'ppm · PM2.5 ' ~ (_p | round(0) | int)) if (_c is not none and _p is not none) else ("
    "('CO2 ' ~ (_c | round(0) | int) ~ ' ppm · ' ~ _badge) if _c is not none else ("
    "('PM2.5 ' ~ (_p | round(0) | int) ~ ' ug/m3 · ' ~ _badge) if _p is not none else ("
    "'실내 온도 20~26°C · 습도 40~60% 권장' if (_t is not none and 20 <= _t <= 26 and (_h is none or 40 <= _h <= 60)) else _badge))) }}"
)
PORTRAIT_CO2_LINE = (
    CO2_PRELUDE
    + f"{{% set _set = '.' in '{CO2}' %}}"
    + "{{ ('CO2 ' ~ (_c | round(0) | int) ~ ' ppm') if _c is not none else ('CO2 -- ppm' if _set else '') }}"
)
PORTRAIT_PM25_LINE = (
    PM25_PRELUDE
    + f"{{% set _set = '.' in '{PM25}' %}}"
    + "{{ ('PM2.5 ' ~ (_p | round(0) | int)) if _p is not none else ('PM2.5 --' if _set else '') }}"
)
PORTRAIT_AQ_OR_TIME = (
    CO2_PRELUDE
    + PM25_PRELUDE
    + f"{{% set _has_c = '.' in '{CO2}' %}}{{% set _has_p = '.' in '{PM25}' %}}"
    + "{{ ('PM2.5 ' ~ (_p | round(0) | int) ~ ' ug/m3') if _p is not none else (('CO2 ' ~ (_c | round(0) | int) ~ ' ppm') if (_c is not none and not _has_p) else (now().strftime('%H:%M 갱신') if not (_has_c or _has_p) else '공기질 대기')) }}"
)
PORTRAIT_SUMMARY_LINE = (
    STATUS_PRELUDE
    + "{{ ('CO2 ' ~ (_c | round(0) | int) ~ 'ppm') if _c is not none else ('적정 20~26°C' if (_t is none or 20 <= _t <= 26) else _badge) }}"
)
CLOCK = "{{ now().strftime('%H:%M 갱신') }}"
CO2_SHORT_LINE = (
    CO2_PRELUDE
    + f"{{% set _set = '.' in '{CO2}' %}}"
    + "{{ ('CO2: ' ~ (_c | round(0) | int) ~ ' ppm') if _c is not none else ('CO2: --' if _set else 'CO2: 미설정') }}"
)
PM25_SHORT_LINE = (
    PM25_PRELUDE
    + f"{{% set _set = '.' in '{PM25}' %}}"
    + "{{ ('PM2.5: ' ~ (_p | round(0) | int) ~ ' ug/m3') if _p is not none else ('PM2.5: --' if _set else 'PM2.5: 미설정') }}"
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
    ) -> None:
        item = {
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
            "align": align,
            "valign": valign,
            "color": color,
        }
        self.items.append(FlowElement(item))

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
    c.text_fit(TITLE, 10, 7, 114, 21, 16)
    c.rect(128, 6, 190, 29, fill=BADGE_FILL, outline=BADGE_OUTLINE, radius=5)
    c.text_fit(BADGE_TEXT, 131, 8, 56, 19, 12, align="center", color=BADGE_COLOR)
    c.line(10, 34, 190, 34)

    c.icon("thermometer", 24, 67, 28, color=TEMP_COLOR)
    c.text_fit("실내 온도", 44, 41, 86, 16, 12)
    c.text_fit(TEMP_CHIP, 134, 41, 56, 16, 12, align="right", color=TEMP_COLOR)
    c.text_fit(TEMP_VAL, 44, 58, 146, 38, 32, color=TEMP_COLOR)
    c.line(10, 100, 190, 100)

    c.icon("water-percent", 24, 130, 26, color=HUM_COLOR)
    c.text_fit("실내 습도", 44, 106, 86, 16, 12)
    c.text_fit(HUM_CHIP, 134, 106, 56, 16, 12, align="right", color=HUM_COLOR)
    c.text_fit(HUM_VAL, 44, 123, 146, 32, 26, color=HUM_COLOR)
    c.line(10, 160, 190, 160)

    c.text_fit(COMPACT_FOOTER, 10, 165, 180, 26, 12, align="center")
    return c.items


def _tiny_landscape(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 250, 128)
    c.text_fit(TITLE, 6, 3, 130, 19, 13)
    c.rect(140, 2, 244, 22, fill=BADGE_FILL, outline=BADGE_OUTLINE, radius=4)
    c.text_fit(BADGE_TEXT, 143, 3, 98, 19, 11, align="center", color=BADGE_COLOR)
    c.line(6, 24, 244, 24)
    c.line(128, 28, 128, 97)

    c.icon("thermometer", 20, 62, 22, color=TEMP_COLOR)
    c.text_fit("온도", 34, 29, 88, 19, 12)
    c.text_fit(TEMP_VAL, 34, 49, 88, 44, 28, color=TEMP_COLOR)

    c.icon("water-percent", 143, 62, 20, color=HUM_COLOR)
    c.text_fit("습도", 156, 29, 86, 19, 12)
    c.text_fit(HUM_VAL, 156, 49, 86, 44, 28, color=HUM_COLOR)

    c.line(6, 100, 244, 100)
    c.text_fit(COMPACT_FOOTER, 6, 103, 238, 22, 11, align="center")
    return c.items


def _tiny_portrait(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 128, 250)
    c.text_fit(TITLE, 6, 5, 116, 21, 14, align="center")
    c.rect(8, 29, 120, 51, fill=BADGE_FILL, outline=BADGE_OUTLINE, radius=4)
    c.text_fit(BADGE_TEXT, 11, 30, 106, 20, 12, align="center", color=BADGE_COLOR)
    c.line(6, 56, 122, 56)

    c.icon("thermometer", 18, 71, 18, color=TEMP_COLOR)
    c.text_fit("실내 온도", 30, 61, 92, 20, 12)
    c.text_fit(TEMP_VAL, 6, 83, 116, 35, 26, align="center", color=TEMP_COLOR)
    c.line(6, 122, 122, 122)

    c.icon("water-percent", 18, 137, 18, color=HUM_COLOR)
    c.text_fit("실내 습도", 30, 127, 92, 20, 12)
    c.text_fit(HUM_VAL, 6, 149, 116, 34, 24, align="center", color=HUM_COLOR)
    c.line(6, 188, 122, 188)

    c.text_fit(PORTRAIT_SUMMARY_LINE, 6, 193, 116, 23, 12, align="center")
    c.text_fit(PORTRAIT_AQ_OR_TIME, 6, 219, 116, 23, 11, align="center")
    return c.items


def _medium_compact_landscape(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 384, 184)
    c.icon("home-outline", 18, 18, 18)
    c.text_fit(TITLE, 32, 7, 152, 22, 16)
    c.rect(190, 6, 302, 29, fill=BADGE_FILL, outline=BADGE_OUTLINE, radius=5)
    c.text_fit(BADGE_TEXT, 194, 7, 104, 20, 13, align="center", color=BADGE_COLOR)
    c.text_fit(CLOCK, 308, 7, 68, 22, 12, align="right")
    c.line(8, 34, 376, 34)
    c.line(192, 39, 192, 141)

    c.icon("thermometer", 22, 53, 20, color=TEMP_COLOR)
    c.text_fit("실내 온도", 36, 42, 76, 21, 14)
    c.text_fit(TEMP_CHIP, 116, 42, 68, 21, 13, align="right", color=TEMP_COLOR)
    c.text_fit(TEMP_VAL, 10, 68, 174, 50, 42, color=TEMP_COLOR)
    c.text_fit("적정 20 ~ 26°C", 10, 121, 174, 19, 12)

    c.icon("water-percent", 214, 53, 20, color=HUM_COLOR)
    c.text_fit("실내 습도", 228, 42, 76, 21, 14)
    c.text_fit(HUM_CHIP, 308, 42, 66, 21, 13, align="right", color=HUM_COLOR)
    c.text_fit(HUM_VAL, 200, 68, 174, 50, 42, color=HUM_COLOR)
    c.text_fit("적정 40 ~ 60%", 200, 121, 174, 19, 12)

    c.line(8, 146, 376, 146)
    c.icon(ADVICE_ICON, 20, 165, 18, color=ADVICE_COLOR)
    c.text_fit(COMPACT_FOOTER, 34, 152, 342, 24, 13)
    return c.items


def _medium_compact_portrait(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 184, 384)
    c.text_fit(TITLE, 10, 8, 164, 24, 18)
    c.rect(10, 35, 174, 59, fill=BADGE_FILL, outline=BADGE_OUTLINE, radius=5)
    c.text_fit(BADGE_TEXT, 14, 36, 156, 22, 13, align="center", color=BADGE_COLOR)

    c.rect(10, 66, 174, 158, radius=6)
    c.icon("thermometer", 25, 82, 18, color=TEMP_COLOR)
    c.text_fit("실내 온도", 38, 72, 72, 20, 13)
    c.text_fit(TEMP_CHIP, 114, 72, 54, 20, 12, align="right", color=TEMP_COLOR)
    c.text_fit(TEMP_VAL, 16, 95, 152, 42, 34, color=TEMP_COLOR)
    c.progress_bar(16, 141, 168, 151, TEMP_PCT, fill=TEMP_COLOR)

    c.rect(10, 166, 174, 258, radius=6)
    c.icon("water-percent", 25, 182, 18, color=HUM_COLOR)
    c.text_fit("실내 습도", 38, 172, 72, 20, 13)
    c.text_fit(HUM_CHIP, 114, 172, 54, 20, 12, align="right", color=HUM_COLOR)
    c.text_fit(HUM_VAL, 16, 195, 152, 42, 34, color=HUM_COLOR)
    c.progress_bar(16, 241, 168, 251, HUM_PCT, fill=HUM_COLOR)

    c.rect(10, 266, 174, 376, radius=6)
    c.icon("air-filter", 25, 282, 17)
    c.text_fit("공기질 · 상태", 38, 272, 130, 20, 13)
    c.text_fit(CO2_SHORT_LINE, 16, 297, 152, 22, 13, color=CO2_COLOR)
    c.text_fit(PM25_SHORT_LINE, 16, 322, 152, 22, 13, color=PM25_COLOR)
    c.text_fit(CLOCK, 16, 349, 152, 21, 12, align="right")
    return c.items


def _panel_landscape(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 800, 480)
    c.icon("home-outline", 38, 38, 30)
    c.text_fit(TITLE, 60, 18, 330, 40, 30)
    c.text_fit(CLOCK, 404, 24, 146, 28, 17, align="right")
    c.rect(564, 16, 776, 58, fill=BADGE_FILL, outline=BADGE_OUTLINE, width=2, radius=10)
    c.text_fit(BADGE_TEXT, 572, 20, 196, 34, 21, align="center", color=BADGE_COLOR)
    c.line(24, 68, 776, 68, width=2)

    cards = (
        (
            "thermometer",
            "실내 온도",
            TEMP_CHIP,
            TEMP_VAL,
            TEMP_PCT,
            TEMP_COLOR,
            "적정 20 ~ 26°C",
            24,
        ),
        ("water-percent", "실내 습도", HUM_CHIP, HUM_VAL, HUM_PCT, HUM_COLOR, "적정 40 ~ 60%", 408),
    )
    for icon_name, label, chip, val, pct, color, hint, left in cards:
        right = left + 368
        c.rect(left, 80, right, 256, width=1.5, radius=10)
        c.icon(icon_name, left + 28, 106, 26, color=color)
        c.text_fit(label, left + 48, 89, 156, 32, 21)
        c.text_fit(chip, left + 212, 91, 138, 28, 17, align="right", color=color)
        c.text_fit(val, left + 18, 125, 332, 76, 64, color=color)
        c.progress_bar(left + 18, 209, right - 18, 224, pct, fill=color)
        c.text_fit(hint, left + 18, 228, 332, 24, 13)

    aq_cards = (
        (
            "molecule-co2",
            "이산화탄소 (CO2)",
            CO2_CHIP,
            CO2_VAL,
            CO2_PCT,
            CO2_COLOR,
            "좋음 <700 · 보통 <1000 · 환기 권장 1000+ ppm",
            24,
        ),
        (
            "air-filter",
            "초미세먼지 (PM2.5)",
            PM25_CHIP,
            PM25_VAL,
            PM25_PCT,
            PM25_COLOR,
            "좋음 0~15 · 보통 16~35 · 나쁨 36+ ug/m3",
            408,
        ),
    )
    for icon_name, label, chip, val, pct, color, hint, left in aq_cards:
        right = left + 368
        c.rect(left, 268, right, 406, width=1.5, radius=10)
        c.icon(icon_name, left + 28, 294, 24, color=color)
        c.text_fit(label, left + 48, 277, 192, 30, 18)
        c.text_fit(chip, left + 244, 279, 106, 26, 15, align="right", color=color)
        c.text_fit(val, left + 18, 311, 332, 48, 36, color=color)
        c.progress_bar(left + 18, 365, right - 18, 379, pct, fill=color)
        c.text_fit(hint, left + 18, 381, 332, 22, 12)

    c.rect(24, 418, 776, 466, width=1.5, radius=8)
    c.icon(ADVICE_ICON, 48, 442, 22, color=ADVICE_COLOR)
    c.text_fit(ADVICE_TEXT, 68, 424, 692, 36, 19)
    return c.items


def _panel_portrait(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 480, 800)
    c.icon("home-outline", 34, 36, 26)
    c.text_fit(TITLE, 54, 18, 256, 36, 26)
    c.text_fit(CLOCK, 316, 20, 144, 32, 16, align="right")
    c.rect(20, 60, 460, 98, fill=BADGE_FILL, outline=BADGE_OUTLINE, width=2, radius=8)
    c.text_fit(BADGE_TEXT, 28, 63, 424, 32, 19, align="center", color=BADGE_COLOR)

    primary = (
        (
            "thermometer",
            "실내 온도",
            TEMP_CHIP,
            TEMP_VAL,
            TEMP_PCT,
            TEMP_COLOR,
            "적정 20 ~ 26°C",
            110,
        ),
        ("water-percent", "실내 습도", HUM_CHIP, HUM_VAL, HUM_PCT, HUM_COLOR, "적정 40 ~ 60%", 288),
    )
    for icon_name, label, chip, val, pct, color, hint, top in primary:
        c.rect(20, top, 460, top + 168, width=1.5, radius=10)
        c.icon(icon_name, 44, top + 25, 24, color=color)
        c.text_fit(label, 64, top + 9, 180, 32, 19)
        c.text_fit(chip, 252, top + 9, 192, 32, 17, align="right", color=color)
        c.text_fit(val, 36, top + 45, 408, 68, 56, color=color)
        c.progress_bar(36, top + 116, 444, top + 130, pct, fill=color)
        c.text_fit(hint, 36, top + 132, 408, 32, 14)

    aq = (
        ("molecule-co2", "이산화탄소 (CO2)", CO2_CHIP, CO2_VAL, CO2_PCT, CO2_COLOR, 466),
        ("air-filter", "초미세먼지 (PM2.5)", PM25_CHIP, PM25_VAL, PM25_PCT, PM25_COLOR, 600),
    )
    for icon_name, label, chip, val, pct, color, top in aq:
        c.rect(20, top, 460, top + 124, width=1.5, radius=10)
        c.icon(icon_name, 44, top + 24, 22, color=color)
        c.text_fit(label, 64, top + 8, 224, 32, 18)
        c.text_fit(chip, 294, top + 8, 150, 32, 16, align="right", color=color)
        c.text_fit(val, 36, top + 42, 408, 46, 34, color=color)
        c.progress_bar(36, top + 92, 444, top + 106, pct, fill=color)

    c.rect(20, 734, 460, 784, width=1.5, radius=8)
    c.icon(ADVICE_ICON, 44, 759, 22, color=ADVICE_COLOR)
    c.text_fit(ADVICE_TEXT, 64, 741, 384, 36, 17)
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
        "id": "indoor_climate",
        "name": {"en": "Indoor climate", "ko": "실내 환경"},
        "description": {
            "en": "Indoor temperature, humidity, and comfort badge with optional CO2 and PM2.5 metrics and ventilation advice.",
            "ko": "실내 온도·습도와 쾌적 상태를 표시하며, 선택 CO2·초미세먼지(PM2.5) 센서로 환기 권장을 안내합니다.",
        },
        "background": "white",
        "parameters": {
            "title": {
                "type": "string",
                "default": "실내 환경",
                "min_length": 1,
                "label": {"en": "Title", "ko": "제목"},
            },
            "temp_sensor": {
                "type": "entity",
                "domain": "sensor",
                "default": "sensor.temperature",
                "label": {"en": "Temperature sensor", "ko": "온도 센서"},
            },
            "humidity_sensor": {
                "type": "entity",
                "domain": "sensor",
                "default": "sensor.humidity",
                "label": {"en": "Humidity sensor", "ko": "습도 센서"},
            },
            "co2_sensor": {
                "type": "string",
                "default": "",
                "label": {"en": "CO2 sensor ID (optional)", "ko": "CO2 센서 ID (선택)"},
            },
            "pm25_sensor": {
                "type": "string",
                "default": "",
                "label": {
                    "en": "PM2.5 sensor ID (optional)",
                    "ko": "초미세먼지(PM2.5) 센서 ID (선택)",
                },
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
    output = "# Generated by scripts/generate_indoor_climate_template.py\n" + yaml.dump(
        data, Dumper=TemplateDumper, allow_unicode=True, sort_keys=False, width=4096
    )
    if len(output.encode("utf-8")) >= 256 * 1024:
        raise ValueError("indoor_climate.yaml exceeds 256 KB template limit")
    return output


if __name__ == "__main__":
    DESTINATION.write_text(generate(), encoding="utf-8")
