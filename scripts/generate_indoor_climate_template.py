#!/usr/bin/env python3
"""Regenerate the built-in indoor climate template across every supported size."""

from pathlib import Path
import sys

from _panel_blocks import PanelBlocks
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

ENTITY_RE = r"^[a-z][a-z0-9_]*[.][a-z0-9_]+$"
BADGE_INK_EXPR = f"('black' if '{ACCENT}' == 'white' else '{ACCENT}')"
BADGE_FG_EXPR = "('black' if _ink == 'yellow' else 'white')"
# Text/icons directly on white must stay high-contrast when accent is yellow or white.
TEXT_INK_EXPR = f"('black' if '{ACCENT}' in ('yellow', 'white') else '{ACCENT}')"


def _finite(entity_expr: str, var: str, set_flag: str | None = None) -> str:
    """Emit Jinja parsing a valid entity's finite sensor float into `var` (or `none`)."""
    valid = f"{entity_expr} is match('{ENTITY_RE}')"
    flag_stmt = f"{{% set {set_flag} = {valid} %}}" if set_flag else ""
    cond = set_flag if set_flag else valid
    return (
        f"{flag_stmt}"
        f"{{% set _r = states({entity_expr}) if {cond} else '' %}}"
        f"{{% set _n = _r | float(none) if is_number(_r) and _r is not boolean else none %}}"
        f"{{% set {var} = _n if _n is not none and _n == _n and (_n | abs) < 100000 else none %}}"
    )


TEMP_PRELUDE = (
    _finite(f"'{TEMP}'", "_t")
    + f"{{% set _tu = state_attr('{TEMP}', 'unit_of_measurement') or '°C' %}}"
    + "{% set _is_f = _tu in ('°F', 'F') %}"
    + "{% set _tc = ((_t - 32) * 5 / 9) if (_t is not none and _is_f) else _t %}"
)
HUM_PRELUDE = _finite(f"'{HUM}'", "_h")
CO2_PRELUDE = _finite(f"'{CO2}'", "_c", "_has_c")
PM25_PRELUDE = _finite(f"'{PM25}'", "_p", "_has_p")

STATUS_PRELUDE = (
    TEMP_PRELUDE
    + HUM_PRELUDE
    + CO2_PRELUDE
    + PM25_PRELUDE
    + f"{{% set _ink = {BADGE_INK_EXPR} %}}"
    + f"{{% set _fg = {BADGE_FG_EXPR} %}}"
    + f"{{% set _tink = {TEXT_INK_EXPR} %}}"
    + "{% set _alert = "
    "(_c is not none and _c >= 1000) or "
    "(_p is not none and _p >= 36) or "
    "(_h is not none and (_h < 30 or _h > 65)) or "
    "(_tc is not none and (_tc > 28 or _tc < 16)) %}"
    "{% set _badge = "
    "'환기 필수' if (_c is not none and _c >= 1500) else ("
    "'환기 권장' if (_c is not none and _c >= 1000) else ("
    "'먼지 나쁨' if (_p is not none and _p >= 36) else ("
    "'건조 주의' if (_h is not none and _h < 30) else ("
    "'다습 주의' if (_h is not none and _h > 65) else ("
    "'고온 주의' if (_tc is not none and _tc > 28) else ("
    "'저온 주의' if (_tc is not none and _tc < 16) else ("
    "'센서 대기' if (_t is none and _h is none) else ("
    "'쾌적' if (_tc is not none and 20 <= _tc <= 26 and (_h is none or 40 <= _h <= 60)) else ("
    "'적정' if (_h is not none and 40 <= _h <= 60 and _tc is none) else '보통'))))))))) %}"
)

TEMP_VAL = (
    TEMP_PRELUDE
    + "{% set _t1 = ((_t | round(1)) + 0) if _t is not none else none %}"
    + "{{ ((((0 if _t1 == 0 else _t1) | string) | replace('.0', '')) ~ _tu) if _t1 is not none else ('--' ~ _tu) }}"
)
TEMP_CHIP = (
    TEMP_PRELUDE
    + "{{ '대기' if _tc is none else ('과열' if _tc > 28 else ('따뜻' if _tc > 26 else ('적정' if _tc >= 20 else ('서늘' if _tc >= 16 else '저온')))) }}"
)
TEMP_COLOR = (
    TEMP_PRELUDE
    + f"{{{{ {TEXT_INK_EXPR} if _tc is not none and (_tc > 28 or _tc < 16) else 'black' }}}}"
)
TEMP_BAR_COLOR = (
    TEMP_PRELUDE
    + f"{{{{ {BADGE_INK_EXPR} if _tc is not none and (_tc > 28 or _tc < 16) else 'black' }}}}"
)
TEMP_PCT = (
    TEMP_PRELUDE
    + "{{ [0, [100, ((_tc - 10) / 25 * 100) | round(0) | int] | min] | max if _tc is not none else 0 }}"
)
TEMP_HINT = TEMP_PRELUDE + "{{ '적정 68 ~ 79°F' if _is_f else '적정 20 ~ 26°C' }}"

HUM_VAL = HUM_PRELUDE + "{{ ((_h | round(0) | int | string) ~ '%') if _h is not none else '--%' }}"
HUM_CHIP = (
    HUM_PRELUDE
    + "{{ '대기' if _h is none else ('습함' if _h > 65 else ('약간 습함' if _h > 60 else ('적정' if _h >= 40 else ('약간 건조' if _h >= 30 else '건조')))) }}"
)
HUM_COLOR = (
    HUM_PRELUDE
    + f"{{{{ {TEXT_INK_EXPR} if _h is not none and (_h < 30 or _h > 65) else 'black' }}}}"
)
HUM_BAR_COLOR = (
    HUM_PRELUDE
    + f"{{{{ {BADGE_INK_EXPR} if _h is not none and (_h < 30 or _h > 65) else 'black' }}}}"
)
HUM_PCT = HUM_PRELUDE + "{{ [0, [100, _h | round(0) | int] | min] | max if _h is not none else 0 }}"

CO2_VAL = (
    CO2_PRELUDE
    + "{{ ((_c | round(0) | int | string) ~ ' ppm') if _c is not none else ('-- ppm' if _has_c else '미설정') }}"
)
CO2_CHIP = (
    CO2_PRELUDE
    + "{{ '선택' if not _has_c else ('대기' if _c is none else ('환기 필수' if _c >= 1500 else ('환기 권장' if _c >= 1000 else ('보통' if _c >= 700 else '좋음')))) }}"
)
CO2_COLOR = CO2_PRELUDE + f"{{{{ {TEXT_INK_EXPR} if _c is not none and _c >= 1000 else 'black' }}}}"
CO2_BAR_COLOR = (
    CO2_PRELUDE + f"{{{{ {BADGE_INK_EXPR} if _c is not none and _c >= 1000 else 'black' }}}}"
)
CO2_PCT = (
    CO2_PRELUDE
    + "{{ [0, [100, ((_c - 400) / 1600 * 100) | round(0) | int] | min] | max if _c is not none else 0 }}"
)

PM25_VAL = (
    PM25_PRELUDE
    + "{{ ((_p | round(0) | int | string) ~ ' ug/m3') if _p is not none else ('-- ug/m3' if _has_p else '미설정') }}"
)
PM25_CHIP = (
    PM25_PRELUDE
    + "{{ '선택' if not _has_p else ('대기' if _p is none else ('매우 나쁨' if _p >= 76 else ('나쁨' if _p >= 36 else ('보통' if _p >= 16 else '좋음')))) }}"
)
PM25_COLOR = PM25_PRELUDE + f"{{{{ {TEXT_INK_EXPR} if _p is not none and _p >= 36 else 'black' }}}}"
PM25_BAR_COLOR = (
    PM25_PRELUDE + f"{{{{ {BADGE_INK_EXPR} if _p is not none and _p >= 36 else 'black' }}}}"
)
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
    "'실내 온도가 높습니다 · 냉방 또는 환기가 필요합니다' if (_tc is not none and _tc > 28) else ("
    "'실내 온도가 낮습니다 · 난방 확인이 필요합니다' if (_tc is not none and _tc < 16) else ("
    "'온도·습도 센서 연결을 확인해 주세요' if (_t is none and _h is none) else ("
    "'온도·습도·공기질 모두 쾌적한 상태입니다' if (_tc is not none and 20 <= _tc <= 26 and (_h is none or 40 <= _h <= 60)) else "
    "'무난한 실내 환경입니다 · 주기적인 환기를 유지하세요'))))))) }}"
)
ADVICE_ICON = (
    STATUS_PRELUDE
    + "{{ 'window-open-variant' if _alert else ('check-circle-outline' if _t is not none or _h is not none else 'alert-circle-outline') }}"
)
ADVICE_COLOR = STATUS_PRELUDE + "{{ _tink if _alert else 'black' }}"


TEMP_RANGE = TEMP_PRELUDE + "{{ '68–79°F' if _is_f else '20–26°C' }}"  # noqa: RUF001
HUM_RANGE = "40–60%"  # noqa: RUF001
BADGE = (BADGE_TEXT, BADGE_FILL, BADGE_OUTLINE, BADGE_COLOR)
# icon, label, value, value colour, chip, range, bar percent, bar colour
METRICS = [
    ("thermometer", "온도", TEMP_VAL, TEMP_COLOR, TEMP_CHIP, TEMP_RANGE, TEMP_PCT, TEMP_BAR_COLOR),
    ("water-percent", "습도", HUM_VAL, HUM_COLOR, HUM_CHIP, HUM_RANGE, HUM_PCT, HUM_BAR_COLOR),
    ("molecule-co2", "CO2", CO2_VAL, CO2_COLOR, CO2_CHIP, "", CO2_PCT, CO2_BAR_COLOR),
    ("blur", "PM2.5", PM25_VAL, PM25_COLOR, PM25_CHIP, "", PM25_PCT, PM25_BAR_COLOR),
]

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


class Canvas(PanelBlocks):
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
    c.text_fit(TEMP_VAL, 10, 12, 180, 68, 54, align="center", color="black", min_size=16)
    c.line(14, 84, 186, 84)
    c.text_fit(HUM_VAL, 10, 88, 180, 50, 44, align="center", color="black", min_size=16)
    c.line(14, 142, 186, 142)
    c.text_fit(BADGE_TEXT, 10, 148, 180, 42, 26, align="center", color=ADVICE_COLOR, min_size=16)
    return c.items


def _tiny_landscape(w: int, h: int) -> list[FlowElement]:
    large = w >= 296
    vw = 296 if large else 250
    ms = 18 if large else 16
    half = vw // 2
    c = Canvas(w, h, vw, 128)
    c.text_fit(TEMP_VAL, 6, 6, half - 10, 68, 52, align="center", color="black", min_size=ms)
    c.line(half, 10, half, 70)
    c.text_fit(
        HUM_VAL, half + 4, 6, vw - half - 10, 68, 52, align="center", color="black", min_size=ms
    )
    c.line(8, 76, vw - 8, 76)
    c.text_fit(
        BADGE_TEXT,
        8,
        82,
        vw - 16,
        40,
        28 if large else 26,
        align="center",
        color=ADVICE_COLOR,
        min_size=ms,
    )
    return c.items


def _tiny_portrait(w: int, h: int) -> list[FlowElement]:
    tall = h >= 296
    vh = 296 if tall else 250
    ms = 15 if tall else 14
    c = Canvas(w, h, 128, vh)
    c.text_fit(
        TEMP_VAL,
        6,
        12,
        116,
        vh * 0.30,
        46 if tall else 44,
        align="center",
        color="black",
        min_size=ms,
    )
    c.line(10, vh * 0.36, 118, vh * 0.36)
    c.text_fit(
        HUM_VAL,
        6,
        vh * 0.40,
        116,
        vh * 0.28,
        42 if tall else 38,
        align="center",
        color="black",
        min_size=ms,
    )
    c.line(10, vh - 60, 118, vh - 60)
    c.text_fit(BADGE_TEXT, 6, vh - 54, 116, 46, 22, align="center", color=ADVICE_COLOR, min_size=ms)
    return c.items


def _medium_compact_landscape(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 384, 184)
    c.text_fit(TEMP_VAL, 10, 12, 174, 96, 66, align="center", color="black", min_size=18)
    c.line(192, 14, 192, 108)
    c.text_fit(HUM_VAL, 202, 12, 172, 96, 66, align="center", color="black", min_size=18)
    c.line(12, 114, 372, 114)
    c.text_fit(BADGE_TEXT, 12, 122, 360, 52, 34, align="center", color=ADVICE_COLOR, min_size=18)
    return c.items


def _medium_compact_portrait(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 184, 384)
    c.text_fit(TEMP_VAL, 10, 24, 164, 100, 60, align="center", color="black", min_size=16)
    c.line(16, 144, 168, 144)
    c.text_fit(HUM_VAL, 10, 164, 164, 100, 56, align="center", color="black", min_size=16)
    c.line(16, 284, 168, 284)
    c.text_fit(BADGE_TEXT, 10, 300, 164, 62, 30, align="center", color=ADVICE_COLOR, min_size=16)
    return c.items


def _panel_43(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 400, 300)
    c.header("home-thermometer", TITLE, BADGE)
    c.line(200, 52, 200, 292)
    c.line(14, 172, 386, 172)
    for index, (icon, caption, value, color, hint, rng, _, _) in enumerate(METRICS):
        x = 14 + (index % 2) * 192
        y = 52 + (index // 2) * 122
        c.icon(icon, x + 15, y + 19, 22)
        c.text_fit(caption, x + 32, y + 5, 140, 28, 18, min_size=c.ms(15))
        c.text_fit(value, x + 4, y + 36, 178, 56, 42, color=color, min_size=c.ms(24))
        c.text_fit(hint, x + 4, y + 94, 84, 24, 16, min_size=c.ms(14))
        if rng:
            c.text_fit(rng, x + 90, y + 94, 92, 24, 16, align="right", min_size=c.ms(14))
    return c.items


def _panel_34(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 300, 400)
    c.header("home-thermometer", TITLE, BADGE, pill_w=104)
    for index, (icon, caption, value, color, hint, rng, _, _) in enumerate(METRICS):
        top = 50 + index * 87
        if index:
            c.line(14, top - 2, 286, top - 2)
        c.icon(icon, 28, top + 24, 24)
        c.text_fit(caption, 46, top + 8, 96, 32, 18, min_size=c.ms(15))
        c.text_fit(value, 144, top + 4, 144, 50, 36, align="right", color=color, min_size=c.ms(20))
        c.text_fit(hint, 14, top + 54, 130, 24, 16, min_size=c.ms(14))
        if rng:
            c.text_fit(rng, 150, top + 54, 136, 24, 16, align="right", min_size=c.ms(14))
    return c.items


def _large_landscape(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 800, 480)
    c.header(
        "home-thermometer",
        TITLE,
        BADGE,
        bar=64,
        margin=24,
        pill_w=190,
        pill_h=40,
        size=28,
        pill_size=24,
        icon_size=34,
    )
    c.line(400, 76, 400, 408, 2)
    c.line(24, 242, 776, 242, 2)
    for index, (icon, caption, value, color, hint, rng, pct, bar) in enumerate(METRICS):
        x = 24 + (index % 2) * 388
        y = 74 + (index // 2) * 168
        c.icon(icon, x + 20, y + 22, 32)
        c.text_fit(caption, x + 46, y + 2, 200, 40, 26, min_size=c.ms(20))
        c.text_fit(value, x + 6, y + 44, 340, 66, 56, color=color, min_size=c.ms(28))
        c.progress_bar(x + 6, y + 116, x + 340, y + 132, pct, fill=bar)
        c.text_fit(hint, x + 6, y + 134, 160, 30, 22, min_size=c.ms(18))
        if rng:
            c.text_fit(rng, x + 170, y + 134, 170, 30, 22, align="right", min_size=c.ms(18))
    c.line(24, 420, 776, 420, 2)
    c.icon(ADVICE_ICON, 46, 448, 30, color=ADVICE_COLOR)
    c.text_fit(ADVICE_TEXT, 74, 430, 700, 38, 24, color=ADVICE_COLOR, min_size=c.ms(18))
    return c.items


def _large_portrait(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 480, 800)
    c.header(
        "home-thermometer",
        TITLE,
        BADGE,
        bar=64,
        margin=24,
        pill_w=170,
        pill_h=40,
        size=28,
        pill_size=24,
        icon_size=34,
    )
    for index, (icon, caption, value, color, hint, rng, pct, bar) in enumerate(METRICS):
        top = 74 + index * 150
        if index:
            c.line(24, top - 4, 456, top - 4, 2)
        c.icon(icon, 44, top + 28, 36)
        c.text_fit(caption, 74, top + 6, 150, 44, 28, min_size=c.ms(22))
        c.text_fit(value, 226, top + 2, 230, 64, 52, align="right", color=color, min_size=c.ms(26))
        c.progress_bar(24, top + 76, 456, top + 92, pct, fill=bar)
        c.text_fit(hint, 24, top + 100, 200, 36, 24, min_size=c.ms(18))
        if rng:
            c.text_fit(rng, 230, top + 100, 226, 36, 24, align="right", min_size=c.ms(18))
    c.line(24, 674, 456, 674, 2)
    c.icon(ADVICE_ICON, 44, 724, 34, color=ADVICE_COLOR)
    c.text_fit(ADVICE_TEXT, 72, 694, 384, 60, 26, color=ADVICE_COLOR, min_size=c.ms(20))
    return c.items


def generate() -> str:
    layouts: dict[str, list[FlowElement]] = {}
    profiles = (
        (_square_200, _square_200, ((200, 200),)),
        (
            _tiny_landscape,
            _tiny_portrait,
            ((212, 104), (250, 122), (250, 128), (250, 132), (296, 128), (296, 152)),
        ),
        (_medium_compact_landscape, _medium_compact_portrait, ((384, 184), (416, 240))),
        (_panel_43, _panel_34, ((400, 300), (648, 480), (1600, 1200))),
        (_large_landscape, _large_portrait, ((800, 480), (960, 640), (960, 680))),
    )
    for landscape, portrait_builder, sizes in profiles:
        for width, height in sizes:
            layouts[f"{width}x{height}"] = landscape(width, height)
            portrait = f"{height}x{width}"
            if width > height and portrait not in layouts:
                layouts[portrait] = portrait_builder(height, width)

    for items in layouts.values():
        for item in items:
            for key, value in item.items():
                if isinstance(value, str) and len(value) > 40 and "{" in value:
                    item[key] = sys.intern(value)

    data = {
        "template": 1,
        "id": "indoor_climate",
        "categories": ["smart_home"],
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
