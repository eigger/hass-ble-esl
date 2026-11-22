#!/usr/bin/env python3
"""Regenerate the built-in home presence template across every supported size."""

from pathlib import Path
import sys

import yaml

DESTINATION = (
    Path(__file__).resolve().parents[1]
    / "custom_components/ble_esl/designer/templates/home_presence.yaml"
)

TITLE = "${title}"
PEOPLE = ("${person_1}", "${person_2}", "${person_3}", "${person_4}")
DOOR = "${door_sensor}"
ACCENT = "${accent}"
FONT = "${font}"

ENTITY_RE = r"^[a-z][a-z0-9_]*[.][a-z0-9_]+$"
BADGE_INK_EXPR = f"('black' if '{ACCENT}' == 'white' else '{ACCENT}')"
BADGE_FG_EXPR = "('black' if _ink == 'yellow' else 'white')"
TEXT_INK_EXPR = f"('black' if '{ACCENT}' in ('yellow', 'white') else '{ACCENT}')"

COUNT_PRELUDE = (
    "{% set _ns = namespace(tot=0, home=0) %}"
    f"{{% for _pe in {PEOPLE!r} %}}"
    f"{{% if _pe is match('{ENTITY_RE}') %}}"
    "{% set _po = states[_pe] %}"
    "{% if _po is not none %}"
    "{% set _ns.tot = _ns.tot + 1 %}"
    "{% if (_po.state | string) == 'home' %}{% set _ns.home = _ns.home + 1 %}{% endif %}"
    "{% endif %}"
    "{% endif %}"
    "{% endfor %}"
    f"{{% set _ink = {BADGE_INK_EXPR} %}}{{% set _fg = {BADGE_FG_EXPR} %}}"
)

BADGE_TEXT = (
    COUNT_PRELUDE
    + "{{ '연결 대기' if _ns.tot == 0 else (('재실 ' ~ _ns.home ~ '/' ~ _ns.tot) if _ns.home > 0 else '전원 외출') }}"
)
HOME_SUMMARY = (
    "{% set _ns = namespace(tot=0, home=0, names=[]) %}"
    f"{{% for _pe in {PEOPLE!r} %}}"
    f"{{% if _pe is match('{ENTITY_RE}') %}}"
    "{% set _po = states[_pe] %}"
    "{% if _po is not none %}"
    "{% set _ns.tot = _ns.tot + 1 %}"
    "{% if (_po.state | string) == 'home' %}"
    "{% set _ns.home = _ns.home + 1 %}"
    "{% set _ns.names = _ns.names + [(_po.name[:8] if _po.name else _pe.split('.')[-1][:8])] %}"
    "{% endif %}"
    "{% endif %}"
    "{% endif %}"
    "{% endfor %}"
    "{{ '구성원 센서 연결 대기' if _ns.tot == 0 else ("
    "('재실: ' ~ ((_ns.names[:3] | join(', ')) ~ (' 외 ' ~ (_ns.home - 3) ~ '명' if _ns.home > 3 else ''))) if _ns.home > 0 else ("
    "'등록 ' ~ _ns.tot ~ '명 모두 외출')) }}"
)
BADGE_FILL = COUNT_PRELUDE + "{{ _ink if _ns.home > 0 else 'white' }}"
BADGE_OUTLINE = COUNT_PRELUDE + "{{ _ink if _ns.home > 0 else 'black' }}"
BADGE_COLOR = COUNT_PRELUDE + "{{ _fg if _ns.home > 0 else 'black' }}"

DOOR_PRELUDE = (
    f"{{% set _de = '{DOOR}' %}}"
    f"{{% set _has_d = _de is match('{ENTITY_RE}') %}}"
    "{% set _do = states[_de] if _has_d else none %}"
    "{% set _ds = (_do.state | string) if _do is not none else '' %}"
    "{% set _dopen = _has_d and _ds == 'on' %}"
    f"{{% set _ink = {BADGE_INK_EXPR} %}}{{% set _fg = {BADGE_FG_EXPR} %}}{{% set _tink = {TEXT_INK_EXPR} %}}"
)

DOOR_BANNER_TEXT = (
    DOOR_PRELUDE
    + "{{ '현관 출입문 · 열림 주의' if _dopen else ('현관 출입문 · 닫힘 (안전)' if (_has_d and _ds == 'off') else ('현관 출입문 · 확인 필요' if _has_d else '현관 센서 · 미설정')) }}"
)
DOOR_STATUS_COMPACT = (
    DOOR_PRELUDE
    + "{{ '현관 · 열림 주의' if _dopen else ('현관 · 닫힘' if (_has_d and _ds == 'off') else ('현관 · 대기' if _has_d else '현관 · 미설정')) }}"
)
DOOR_ICON = (
    DOOR_PRELUDE + "{{ 'door-open' if _dopen else ('door-closed' if _has_d else 'shield-check') }}"
)
DOOR_BANNER_FILL = DOOR_PRELUDE + "{{ _ink if _dopen else 'white' }}"
DOOR_BANNER_OUTLINE = DOOR_PRELUDE + "{{ _ink if _dopen else 'black' }}"
DOOR_BANNER_FG = DOOR_PRELUDE + "{{ _fg if _dopen else 'black' }}"
DOOR_TEXT_COLOR = DOOR_PRELUDE + "{{ _tink if _dopen else 'black' }}"
CLOCK = "{{ now().strftime('%H:%M 갱신') }}"


def _person(idx: int, *, compact: bool) -> tuple[str, str, str, str, str]:
    """Return (name, status, icon, color, since) templates for member slot `idx`."""
    pe = PEOPLE[idx]
    sel = (
        f"{{% set _pe = '{pe}' %}}"
        f"{{% set _has = _pe is match('{ENTITY_RE}') %}}"
        "{% set _po = states[_pe] if _has else none %}"
        "{% set _st = (_po.state | string) if _po is not none else '' %}"
    )
    fallback_name = "" if compact else f"구성원 {idx + 1}"
    fallback_status = "" if compact else "미설정"
    name = sel + (
        f"{{{{ (_po.name or _pe) if _po is not none else (_pe if _has else '{fallback_name}') }}}}"
    )
    status = sel + (
        "{{ ('재실' if _st == 'home' else ('외출' if _st == 'not_home' else ('알 수 없음' if _st in ('unknown', 'unavailable') else _st))) "
        f"if _po is not none else ('엔티티 없음' if _has else '{fallback_status}') }}}}"
    )
    icon = sel + (
        "{{ ('home' if _st == 'home' else ('account-off-outline' if _st == 'not_home' else ('alert-circle-outline' if _st in ('unknown', 'unavailable') else 'account-outline'))) "
        "if _po is not none else 'account-outline' }}"
    )
    color = sel + f"{{{{ {TEXT_INK_EXPR} if (_po is not none and _st == 'home') else 'black' }}}}"
    icon_color = (
        sel
        + f"{{{{ 'white' if not _has else ({TEXT_INK_EXPR} if (_po is not none and _st == 'home') else 'black') }}}}"
        if compact
        else color
    )
    since = sel + (
        "{% set _lc = (_po.last_changed | default(none)) if _po is not none else none %}"
        "{{ ((as_local(_lc) if _lc.tzinfo is not none else _lc).strftime('%m/%d %H:%M')) "
        "if _lc is not none else ('선택 입력' if not _has else '') }}"
    )
    return name, status, icon, color, icon_color, since


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


def _square_200(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 200, 200)
    c.text_fit(BADGE_TEXT, 10, 16, 180, 94, 52, align="center", color="black", min_size=16)
    c.line(14, 122, 186, 122)
    c.text_fit(
        DOOR_STATUS_COMPACT,
        10,
        134,
        180,
        52,
        26,
        align="center",
        color=DOOR_TEXT_COLOR,
        min_size=16,
    )
    return c.items


def _tiny_landscape(w: int, h: int) -> list[FlowElement]:
    large = w >= 296
    vw = 296 if large else 250
    ms = 18 if large else 16
    c = Canvas(w, h, vw, 128)
    c.text_fit(
        BADGE_TEXT,
        8,
        8,
        vw - 16,
        66,
        54 if large else 52,
        align="center",
        color="black",
        min_size=ms,
    )
    c.line(10, 78, vw - 10, 78)
    c.text_fit(
        DOOR_STATUS_COMPACT,
        8,
        84,
        vw - 16,
        38,
        28 if large else 26,
        align="center",
        color=DOOR_TEXT_COLOR,
        min_size=ms,
    )
    return c.items


def _tiny_portrait(w: int, h: int) -> list[FlowElement]:
    tall = h >= 296
    vh = 296 if tall else 250
    ms = 15 if tall else 14
    c = Canvas(w, h, 128, vh)
    c.text_fit(BADGE_TEXT, 6, 20, 116, vh * 0.44, 44, align="center", color="black", min_size=ms)
    c.line(10, vh * 0.56, 118, vh * 0.56)
    c.text_fit(
        DOOR_STATUS_COMPACT,
        6,
        vh * 0.62,
        116,
        vh * 0.30,
        22,
        align="center",
        color=DOOR_TEXT_COLOR,
        min_size=ms,
    )
    return c.items


def _medium_compact_landscape(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 384, 184)
    c.text_fit(BADGE_TEXT, 10, 10, 364, 78, 64, align="center", color="black", min_size=18)
    c.text_fit(HOME_SUMMARY, 10, 94, 364, 38, 28, align="center", color="black", min_size=18)
    c.line(12, 138, 372, 138)
    c.text_fit(
        DOOR_STATUS_COMPACT,
        10,
        144,
        364,
        34,
        26,
        align="center",
        color=DOOR_TEXT_COLOR,
        min_size=18,
    )
    return c.items


def _medium_compact_portrait(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 184, 384)
    c.text_fit(BADGE_TEXT, 10, 24, 164, 110, 58, align="center", color="black", min_size=16)
    c.line(16, 154, 168, 154)
    c.text_fit(HOME_SUMMARY, 10, 174, 164, 88, 26, align="center", color="black", min_size=16)
    c.line(16, 282, 168, 282)
    c.text_fit(
        DOOR_STATUS_COMPACT,
        10,
        300,
        164,
        60,
        26,
        align="center",
        color=DOOR_TEXT_COLOR,
        min_size=16,
    )
    return c.items


def _panel_landscape(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 800, 480)
    c.icon("home-outline", 38, 36, 28)
    c.text_fit(TITLE, 60, 17, 360, 38, 28)
    c.text_fit(CLOCK, 430, 22, 144, 28, 16, align="right")
    c.rect(588, 15, 776, 55, fill=BADGE_FILL, outline=BADGE_OUTLINE, width=2, radius=10)
    c.text_fit(BADGE_TEXT, 596, 19, 172, 32, 20, align="center", color=BADGE_COLOR)
    c.line(24, 65, 776, 65, width=2)

    cards = ((24, 78), (408, 78), (24, 244), (408, 244))
    for idx, (left, top) in enumerate(cards):
        right = left + 368
        c.rect(left, top, right, top + 154, width=1.5, radius=10)
        name, status, icon, color, _, since = _person(idx, compact=False)
        c.icon(icon, left + 28, top + 28, 28, color=color)
        c.text_fit(name, left + 50, top + 11, 184, 34, 21)
        c.text_fit(since, left + 238, top + 13, 114, 30, 14, align="right")
        c.line(left + 16, top + 52, right - 16, top + 52)
        c.text_fit(status, left + 18, top + 64, 332, 76, 48, align="center", color=color)

    c.rect(
        24,
        412,
        776,
        466,
        fill=DOOR_BANNER_FILL,
        outline=DOOR_BANNER_OUTLINE,
        width=1.5,
        radius=8,
    )
    c.icon(DOOR_ICON, 50, 439, 24, color=DOOR_BANNER_FG)
    c.text_fit(DOOR_BANNER_TEXT, 72, 421, 686, 36, 20, color=DOOR_BANNER_FG)
    return c.items


def _panel_portrait(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 480, 800)
    c.icon("home-outline", 34, 34, 24)
    c.text_fit(TITLE, 54, 17, 256, 34, 24)
    c.text_fit(CLOCK, 316, 18, 144, 32, 16, align="right")
    c.rect(20, 58, 460, 98, fill=BADGE_FILL, outline=BADGE_OUTLINE, width=2, radius=8)
    c.text_fit(BADGE_TEXT, 28, 62, 424, 32, 19, align="center", color=BADGE_COLOR)

    for idx in range(4):
        top = 108 + idx * 148
        c.rect(20, top, 460, top + 136, width=1.5, radius=10)
        name, status, icon, color, _, since = _person(idx, compact=False)
        c.icon(icon, 48, top + 34, 30, color=color)
        c.text_fit(name, 74, top + 14, 214, 36, 21)
        c.text_fit(since, 294, top + 15, 150, 34, 15, align="right")
        c.line(36, top + 56, 444, top + 56)
        c.text_fit(status, 36, top + 66, 408, 60, 42, align="center", color=color)

    c.rect(
        20,
        710,
        460,
        784,
        fill=DOOR_BANNER_FILL,
        outline=DOOR_BANNER_OUTLINE,
        width=1.5,
        radius=8,
    )
    c.icon(DOOR_ICON, 48, 747, 24, color=DOOR_BANNER_FG)
    c.text_fit(DOOR_BANNER_TEXT, 72, 726, 372, 42, 19, color=DOOR_BANNER_FG)
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
        "id": "home_presence",
        "name": {"en": "Home presence", "ko": "가족 재실 · 현관"},
        "description": {
            "en": "Track up to 4 household members (home, away, custom zones) with an optional entryway door sensor.",
            "ko": "가족 구성원 최대 4명의 재실·외출·위치 상태와 선택 현관문 센서를 한눈에 표시합니다.",
        },
        "background": "white",
        "parameters": {
            "title": {
                "type": "string",
                "default": "가족 재실",
                "min_length": 1,
                "label": {"en": "Title", "ko": "제목"},
            },
            "person_1": {
                "type": "entity",
                "domain": "person",
                "default": "person.home",
                "label": {"en": "Person 1", "ko": "구성원 1"},
            },
            "person_2": {
                "type": "string",
                "default": "",
                "label": {"en": "Person 2 entity ID (optional)", "ko": "구성원 2 엔티티 ID (선택)"},
            },
            "person_3": {
                "type": "string",
                "default": "",
                "label": {"en": "Person 3 entity ID (optional)", "ko": "구성원 3 엔티티 ID (선택)"},
            },
            "person_4": {
                "type": "string",
                "default": "",
                "label": {"en": "Person 4 entity ID (optional)", "ko": "구성원 4 엔티티 ID (선택)"},
            },
            "door_sensor": {
                "type": "string",
                "default": "",
                "label": {
                    "en": "Entryway door sensor ID (optional)",
                    "ko": "현관문 센서 ID (선택)",
                },
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
            "interval": {
                "type": "select",
                "group": "automation",
                "options": ["5", "10", "15", "30"],
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
    output = "# Generated by scripts/generate_home_presence_template.py\n" + yaml.dump(
        data, Dumper=TemplateDumper, allow_unicode=True, sort_keys=False, width=4096
    )
    if len(output.encode("utf-8")) >= 256 * 1024:
        raise ValueError("home_presence.yaml exceeds 256 KB template limit")
    return output


if __name__ == "__main__":
    DESTINATION.write_text(generate(), encoding="utf-8")
