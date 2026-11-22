#!/usr/bin/env python3
"""Regenerate the built-in home appliance status & alert template across all sizes."""

from pathlib import Path
import sys

import yaml

DESTINATION = (
    Path(__file__).resolve().parents[1]
    / "custom_components/ble_esl/designer/templates/appliance_status.yaml"
)

TITLE = "${title}"
APPLIANCES = (
    ("${appliance_1}", "${remaining_1}", "washing-machine", "세탁기"),
    ("${appliance_2}", "${remaining_2}", "tumble-dryer", "건조기"),
    ("${appliance_3}", "${remaining_3}", "dishwasher", "식기세척기"),
)
ACCENT = "${accent}"
FONT = "${font}"

ENTITY_RE = r"^[a-z][a-z0-9_]*[.][a-z0-9_]+$"
BADGE_INK_EXPR = f"('black' if '{ACCENT}' == 'white' else '{ACCENT}')"
BADGE_FG_EXPR = "('black' if _ink == 'yellow' else 'white')"
TEXT_INK_EXPR = f"('black' if '{ACCENT}' in ('yellow', 'white') else '{ACCENT}')"

_ERR_STATES = "('error', 'fault', 'failed', 'alert', 'warning', 'problem', 'jammed')"
_DONE_STATES = (
    "('complete', 'completed', 'done', 'finished', 'finish', 'end', 'ended', 'ready_to_unload')"
)
_RUN_STATES = (
    "('run', 'running', 'washing', 'drying', 'rinsing', 'spinning', 'active', "
    "'on', 'true', 'cleaning', 'brewing', 'cooking', 'heating', 'cooling', 'sensing', 'prewash')"
)
_PAUSE_STATES = (
    "('pause', 'paused', 'hold', 'delayed', 'delay_start', 'delayed_start', 'wait', 'waiting')"
)
_IDLE_STATES = "('idle', 'standby', 'off', 'false', 'power_off', 'powered_off', 'sleep', 'ready', 'stop', 'stopped')"


def _fmt_num(var: str, decimals: int, out_var: str) -> str:
    """Format float cleanly into `out_var` without '-0' or trailing '.0'."""
    return (
        f"{{% set _f1 = (({var} | round({decimals})) + 0) %}}"
        "{% set _f2 = 0 if _f1 == 0 else _f1 %}"
        "{% set _fi = _f2 | int %}"
        f"{{% set {out_var} = ((_fi if _f2 == _fi else _f2) | string) %}}"
    )


def _rem_snippet(rem_expr: str) -> str:
    """Emit Jinja computing `_rem_str` (or empty string) from optional remaining sensor."""
    return (
        f"{{% set _rm = '{rem_expr}' %}}"
        f"{{% set _has_r = _rm is match('{ENTITY_RE}') %}}"
        "{% set _rr = (states(_rm) | string | trim) if _has_r else '' %}"
        "{% set _rrl = _rr | lower %}"
        "{% set _r_valid = _has_r and _rrl not in ('', 'unknown', 'unavailable', 'none') %}"
        "{% if _r_valid and is_number(_rr) and _rr is not boolean %}"
        "{% set _rn = _rr | float(none) %}"
        "{% if _rn is not none and _rn == _rn and (_rn | abs) < 1000000 %}"
        "{% set _rnv = [0, _rn] | max %}"
        "{% set _ru = state_attr(_rm, 'unit_of_measurement') or '분' %}"
        "{% if _ru in ('h', 'hr', 'hrs', 'hour', 'hours') %}"
        + _fmt_num("_rnv", 1, "_rf")
        + "{% set _rem_str = _rf ~ '시간' %}"
        "{% elif _ru in ('s', 'sec', 'secs', 'second', 'seconds') %}"
        + _fmt_num("(_rnv / 60)", 0, "_rf")
        + "{% set _rem_str = _rf ~ '분' %}"
        "{% elif _ru in ('m', 'min', 'mins', 'minute', 'minutes', '분') %}"
        + _fmt_num("_rnv", 0, "_rf")
        + "{% set _rem_str = _rf ~ '분' %}"
        "{% else %}" + _fmt_num("_rnv", 1, "_rf") + "{% set _rem_str = _rf ~ ' ' ~ _ru[:6] %}"
        "{% endif %}"
        "{% else %}{% set _rem_str = '' %}{% endif %}"
        "{% elif _r_valid %}"
        "{% if 'T' in _rr and ':' in _rr %}"
        "{% set _dt = as_datetime(_rr, none) %}"
        "{% set _rem_str = as_local(_dt).strftime('%H:%M') if _dt is not none else _rr[:12] %}"
        "{% else %}{% set _rem_str = _rr[:12] %}{% endif %}"
        "{% else %}{% set _rem_str = '' %}{% endif %}"
    )


def _slot(idx: int, *, compact: bool) -> tuple[str, str, str, str, str, str]:
    """Return (name, status_text, subtext, icon, color, icon_color) Jinja strings for slot `idx`."""
    ent_expr, rem_expr, base_icon, default_name = APPLIANCES[idx]
    sel = (
        f"{{% set _ae = '{ent_expr}' %}}"
        f"{{% set _has = _ae is match('{ENTITY_RE}') %}}"
        "{% set _ao = states[_ae] if _has else none %}"
        "{% set _st = (_ao.state | string | trim) if _ao is not none else '' %}"
        "{% set _stl = _st | lower %}"
        "{% set _sk = "
        "'unavail' if (_has and (_ao is none or _stl in ('', 'unknown', 'unavailable', 'none'))) else ("
        f"'error' if _stl in {_ERR_STATES} else ("
        f"'done' if _stl in {_DONE_STATES} else ("
        f"'run' if _stl in {_RUN_STATES} else ("
        f"'pause' if _stl in {_PAUSE_STATES} else ("
        f"'idle' if _stl in {_IDLE_STATES} else ("
        "'custom' if _has else 'unset')))))) %}"
        "{% set _sl = "
        "'오류 확인' if _sk == 'error' else ("
        "'완료됨' if _sk == 'done' else ("
        "'동작 중' if _sk == 'run' else ("
        "'일시정지' if _sk == 'pause' else ("
        "'대기 중' if _sk == 'idle' else ("
        "'응답 없음' if _sk == 'unavail' else ("
        "_st[:10] if _sk == 'custom' else '미설정')))))) %}"
        "{% set _alert = _sk in ('error', 'done') %}"
    ) + _rem_snippet(rem_expr)

    fallback_name = "" if compact else default_name
    fallback_status = "" if compact else "미설정"
    name = sel + (
        f"{{{{ ((_ao.name[:12] if (_ao is not none and _ao.name) else '{default_name}')) "
        f"if _has else '{fallback_name}' }}}}"
    )
    compact_status = sel + (
        "{% if not _has %}"
        + f"'{fallback_status}'"
        + "{% elif _rem_str and _sk in ('run', 'pause') %}"
        + "{{ ('일시정지 ' ~ _rem_str) if _sk == 'pause' else ('동작 · ' ~ _rem_str) }}"
        + "{% else %}{{ _sl }}{% endif %}"
    )
    panel_status = sel + "{{ _sl if _has else '미설정' }}"
    subtext = sel + (
        "{% set _lc = (_ao.last_changed | default(none)) if _ao is not none else none %}"
        "{% if not _has %}{{ '' if " + ("True" if compact else "False") + " else '선택 입력' }}"
        "{% elif _rem_str and _sk in ('run', 'pause', 'custom') %}"
        "{{ '남은 ' ~ _rem_str }}"
        "{% elif _lc is not none %}"
        "{{ (as_local(_lc) if _lc.tzinfo is not none else _lc).strftime('%m/%d %H:%M') }}"
        "{% elif _sk == 'unavail' %}엔티티 확인"
        "{% else %}{% endif %}"
    )
    icon = sel + (
        f"{{{{ 'alert-circle-outline' if _sk == 'error' else ('check-circle-outline' if _sk == 'done' else '{base_icon}') }}}}"
    )
    color = sel + f"{{{{ {TEXT_INK_EXPR} if _alert else 'black' }}}}"
    icon_color = (
        sel + f"{{{{ 'white' if not _has else ({TEXT_INK_EXPR} if _alert else 'black') }}}}"
        if compact
        else color
    )
    return name, (compact_status if compact else panel_status), subtext, icon, color, icon_color


SUMMARY_PRELUDE = (
    "{% set _ns = namespace(tot=0, err=0, done=0, run=0, pause=0, idle=0, err_name='', done_name='', run_name='') %}"
    + "".join(
        f"{{% set _ae = '{ent_expr}' %}}"
        f"{{% if _ae is match('{ENTITY_RE}') %}}"
        "{% set _ns.tot = _ns.tot + 1 %}"
        "{% set _ao = states[_ae] %}"
        "{% set _st = (_ao.state | string | trim) if _ao is not none else '' %}"
        "{% set _stl = _st | lower %}"
        f"{{% set _nm = (_ao.name[:10] if (_ao is not none and _ao.name) else '{default_name}') %}}"
        f"{{% if _stl in {_ERR_STATES} %}}"
        "{% set _ns.err = _ns.err + 1 %}"
        "{% if not _ns.err_name %}{% set _ns.err_name = _nm %}{% endif %}"
        f"{{% elif _stl in {_DONE_STATES} %}}"
        "{% set _ns.done = _ns.done + 1 %}"
        "{% if not _ns.done_name %}{% set _ns.done_name = _nm %}{% endif %}"
        f"{{% elif _stl in {_RUN_STATES} %}}"
        "{% set _ns.run = _ns.run + 1 %}"
        "{% if not _ns.run_name %}{% set _ns.run_name = _nm %}{% endif %}"
        f"{{% elif _stl in {_PAUSE_STATES} %}}"
        "{% set _ns.pause = _ns.pause + 1 %}"
        f"{{% elif _stl in {_IDLE_STATES} %}}"
        "{% set _ns.idle = _ns.idle + 1 %}"
        "{% endif %}"
        "{% endif %}"
        for ent_expr, _, _, default_name in APPLIANCES
    )
    + f"{{% set _ink = {BADGE_INK_EXPR} %}}{{% set _fg = {BADGE_FG_EXPR} %}}{{% set _tink = {TEXT_INK_EXPR} %}}"
    "{% set _has_alert = (_ns.err > 0 or _ns.done > 0) %}"
)

BADGE_TEXT = (
    SUMMARY_PRELUDE + "{{ "
    "'센서 대기' if _ns.tot == 0 else ("
    "(('오류 ' ~ _ns.err) if _ns.err > 1 else '오류 확인') if _ns.err > 0 else ("
    "(('완료 ' ~ _ns.done) if _ns.done > 1 else '완료 알림') if _ns.done > 0 else ("
    "('동작 ' ~ _ns.run) if _ns.run > 0 else ("
    "'일시정지' if _ns.pause > 0 else ("
    "'모두 대기' if _ns.idle > 0 else '상태 대기'))))) }}"
)
BADGE_FILL = SUMMARY_PRELUDE + "{{ _ink if _has_alert else 'white' }}"
BADGE_OUTLINE = SUMMARY_PRELUDE + "{{ _ink if _has_alert else 'black' }}"
BADGE_COLOR = SUMMARY_PRELUDE + "{{ _fg if _has_alert else 'black' }}"

BANNER_FILL = BADGE_FILL
BANNER_OUTLINE = BADGE_OUTLINE
BANNER_FG = BADGE_COLOR
BANNER_ICON = (
    SUMMARY_PRELUDE
    + "{{ 'alert-circle-outline' if _ns.err > 0 else ('check-circle-outline' if _ns.done > 0 else ('timer-sand' if _ns.run > 0 else 'washing-machine')) }}"
)
BANNER_TEXT = (
    SUMMARY_PRELUDE + "{{ "
    "'연결된 가전 센서가 없습니다' if _ns.tot == 0 else ("
    "(_ns.err_name ~ ' 오류 확인 필요' ~ (' (외 ' ~ (_ns.err - 1) ~ '건)' if _ns.err > 1 else '')) if _ns.err > 0 else ("
    "(_ns.done_name ~ ' 작동 완료 · 확인해 주세요' ~ (' (외 ' ~ (_ns.done - 1) ~ '건)' if _ns.done > 1 else '')) if _ns.done > 0 else ("
    "(_ns.run_name ~ ' 동작 중' ~ (' · 총 ' ~ _ns.run ~ '대 가동' if _ns.run > 1 else '')) if _ns.run > 0 else ("
    "'일시정지 중인 가전이 있습니다' if _ns.pause > 0 else '모든 가전이 대기 중입니다')))) }}"
)
BANNER_COMPACT = (
    SUMMARY_PRELUDE + "{{ "
    "'센서 연결 확인' if _ns.tot == 0 else ("
    "(_ns.err_name ~ ' 오류') if _ns.err > 0 else ("
    "(_ns.done_name ~ ' 완료!') if _ns.done > 0 else ("
    "(_ns.run_name ~ ' 동작 중') if _ns.run > 0 else ("
    "'일시정지 중' if _ns.pause > 0 else ('모두 대기 · ' ~ now().strftime('%H:%M')))))) }}"
)
BANNER_COMPACT_STATIC = (
    SUMMARY_PRELUDE + "{{ "
    "'센서 연결 확인' if _ns.tot == 0 else ("
    "(_ns.err_name ~ ' 오류') if _ns.err > 0 else ("
    "(_ns.done_name ~ ' 완료!') if _ns.done > 0 else ("
    "(_ns.run_name ~ ' 동작 중') if _ns.run > 0 else ("
    "'일시정지 중' if _ns.pause > 0 else '모든 가전 대기 중')))) }}"
)
BANNER_TEXT_COLOR = SUMMARY_PRELUDE + "{{ _tink if _has_alert else 'black' }}"
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


def _square_200(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 200, 200)
    c.text_fit(TITLE, 10, 7, 104, 21, 15)
    c.rect(118, 6, 190, 29, fill=BADGE_FILL, outline=BADGE_OUTLINE, radius=5)
    c.text_fit(BADGE_TEXT, 121, 8, 66, 19, 12, align="center", color=BADGE_COLOR)
    c.line(10, 34, 190, 34)

    for idx in range(3):
        top = 40 + idx * 40
        if idx:
            c.line(10, top - 2, 190, top - 2)
        name, status, _, icon, color, icon_color = _slot(idx, compact=True)
        c.icon(icon, 23, top + 18, 22, color=icon_color)
        c.text_fit(name, 40, top + 2, 148, 16, 13)
        c.text_fit(status, 40, top + 19, 148, 17, 13, color=color)

    c.line(10, 162, 190, 162)
    c.icon(BANNER_ICON, 21, 178, 17, color=BANNER_TEXT_COLOR)
    c.text_fit(BANNER_COMPACT, 36, 167, 154, 22, 12, color=BANNER_TEXT_COLOR)
    return c.items


def _tiny_landscape(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 250, 128)
    c.text_fit(TITLE, 6, 3, 120, 19, 13)
    c.rect(130, 1, 244, 23, fill=BADGE_FILL, outline=BADGE_OUTLINE, radius=4)
    c.text_fit(BADGE_TEXT, 134, 3, 106, 17, 11, align="center", color=BADGE_COLOR)
    c.line(6, 25, 244, 25)

    for idx in range(3):
        top = 27 + idx * 24
        if idx:
            c.line(6, top - 1, 244, top - 1)
        name, status, _, icon, color, icon_color = _slot(idx, compact=True)
        c.icon(icon, 16, top + 11, 15, color=icon_color)
        c.text_fit(name, 29, top + 2, 95, 18, 12)
        c.text_fit(status, 128, top + 2, 114, 18, 12, align="right", color=color)

    c.line(6, 100, 244, 100)
    c.icon(BANNER_ICON, 17, 114, 15, color=BANNER_TEXT_COLOR)
    c.text_fit(BANNER_COMPACT, 29, 103, 215, 22, 11, color=BANNER_TEXT_COLOR)
    return c.items


def _tiny_portrait(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 128, 250)
    c.text_fit(TITLE, 6, 4, 116, 20, 14, align="center")
    c.rect(8, 27, 120, 52, fill=BADGE_FILL, outline=BADGE_OUTLINE, radius=4)
    c.text_fit(BADGE_TEXT, 12, 30, 104, 18, 12, align="center", color=BADGE_COLOR)
    c.line(6, 56, 122, 56)

    for idx in range(3):
        top = 60 + idx * 46
        if idx:
            c.line(6, top - 2, 122, top - 2)
        name, status, _, _, color, _ = _slot(idx, compact=True)
        c.text_fit(name, 6, top + 2, 116, 17, 12, align="center")
        c.text_fit(status, 6, top + 21, 116, 18, 12, align="center", color=color)

    c.line(6, 198, 122, 198)
    c.text_fit(BANNER_COMPACT_STATIC, 6, 203, 116, 20, 11, align="center", color=BANNER_TEXT_COLOR)
    c.text_fit(CLOCK, 6, 226, 116, 20, 10, align="center")
    return c.items


def _medium_compact_landscape(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 384, 184)
    c.icon("washing-machine", 18, 17, 18)
    c.text_fit(TITLE, 32, 6, 144, 22, 16)
    c.rect(182, 5, 294, 30, fill=BADGE_FILL, outline=BADGE_OUTLINE, radius=5)
    c.text_fit(BADGE_TEXT, 186, 7, 104, 21, 13, align="center", color=BADGE_COLOR)
    c.text_fit(CLOCK, 300, 7, 76, 22, 12, align="right")
    c.line(8, 34, 376, 34)

    xs = (10, 134, 258)
    for idx, left in enumerate(xs):
        c.rect(left, 41, left + 116, 141, radius=6)
        name, status, subtext, icon, color, icon_color = _slot(idx, compact=True)
        c.icon(icon, left + 58, 60, 24, color=icon_color)
        c.text_fit(name, left + 7, 77, 102, 18, 13, align="center")
        c.text_fit(status, left + 7, 97, 102, 20, 14, align="center", color=color)
        c.text_fit(subtext, left + 7, 119, 102, 16, 11, align="center")

    c.line(8, 147, 376, 147)
    c.icon(BANNER_ICON, 20, 165, 18, color=BANNER_TEXT_COLOR)
    c.text_fit(BANNER_TEXT, 34, 152, 342, 24, 13, color=BANNER_TEXT_COLOR)
    return c.items


def _medium_compact_portrait(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 184, 384)
    c.text_fit(TITLE, 10, 8, 164, 24, 18)
    c.rect(10, 35, 174, 59, fill=BADGE_FILL, outline=BADGE_OUTLINE, radius=5)
    c.text_fit(BADGE_TEXT, 14, 37, 156, 20, 13, align="center", color=BADGE_COLOR)

    for idx in range(3):
        top = 66 + idx * 82
        c.rect(10, top, 174, top + 74, radius=6)
        name, status, subtext, icon, color, icon_color = _slot(idx, compact=True)
        c.icon(icon, 28, top + 27, 22, color=icon_color)
        c.text_fit(name, 44, top + 6, 122, 19, 14)
        c.text_fit(status, 44, top + 27, 122, 22, 15, color=color)
        c.text_fit(subtext, 16, top + 51, 152, 17, 11)

    c.rect(10, 314, 174, 376, fill=BANNER_FILL, outline=BANNER_OUTLINE, radius=6)
    c.icon(BANNER_ICON, 26, 336, 18, color=BANNER_FG)
    c.text_fit(BANNER_COMPACT_STATIC, 40, 324, 126, 24, 13, color=BANNER_FG)
    c.text_fit(CLOCK, 18, 351, 148, 19, 11, align="right", color=BANNER_FG)
    return c.items


def _panel_landscape(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 800, 480)
    c.icon("washing-machine", 38, 36, 28)
    c.text_fit(TITLE, 60, 17, 360, 38, 28)
    c.text_fit(CLOCK, 430, 22, 144, 28, 16, align="right")
    c.rect(588, 15, 776, 55, fill=BADGE_FILL, outline=BADGE_OUTLINE, width=2, radius=10)
    c.text_fit(BADGE_TEXT, 596, 19, 172, 32, 20, align="center", color=BADGE_COLOR)
    c.line(24, 65, 776, 65, width=2)

    xs = (24, 280, 536)
    for idx, left in enumerate(xs):
        right = left + 240
        c.rect(left, 78, right, 398, width=1.5, radius=10)
        name, status, subtext, icon, color, _ = _slot(idx, compact=False)
        c.icon(icon, left + 30, 112, 30, color=color)
        c.text_fit(name, left + 52, 95, 172, 34, 21)
        c.line(left + 16, 146, right - 16, 146)
        c.text_fit(status, left + 16, 178, 208, 72, 42, align="center", color=color)
        c.line(left + 16, 282, right - 16, 282)
        c.text_fit("세부 정보", left + 16, 298, 208, 26, 15, align="center")
        c.text_fit(subtext, left + 16, 330, 208, 42, 22, align="center")

    c.rect(
        24,
        412,
        776,
        466,
        fill=BANNER_FILL,
        outline=BANNER_OUTLINE,
        width=1.5,
        radius=8,
    )
    c.icon(BANNER_ICON, 50, 439, 24, color=BANNER_FG)
    c.text_fit(BANNER_TEXT, 72, 421, 686, 36, 20, color=BANNER_FG)
    return c.items


def _panel_portrait(w: int, h: int) -> list[FlowElement]:
    c = Canvas(w, h, 480, 800)
    c.icon("washing-machine", 34, 34, 24)
    c.text_fit(TITLE, 54, 17, 256, 34, 24)
    c.text_fit(CLOCK, 316, 18, 144, 32, 16, align="right")
    c.rect(20, 58, 460, 98, fill=BADGE_FILL, outline=BADGE_OUTLINE, width=2, radius=8)
    c.text_fit(BADGE_TEXT, 28, 62, 424, 32, 19, align="center", color=BADGE_COLOR)

    for idx in range(3):
        top = 110 + idx * 200
        c.rect(20, top, 460, top + 186, width=1.5, radius=10)
        name, status, subtext, icon, color, _ = _slot(idx, compact=False)
        c.icon(icon, 48, top + 36, 30, color=color)
        c.text_fit(name, 74, top + 16, 214, 36, 21)
        c.text_fit(subtext, 294, top + 18, 150, 32, 15, align="right")
        c.line(36, top + 62, 444, top + 62)
        c.text_fit(status, 36, top + 84, 408, 76, 46, align="center", color=color)

    c.rect(
        20,
        712,
        460,
        784,
        fill=BANNER_FILL,
        outline=BANNER_OUTLINE,
        width=1.5,
        radius=8,
    )
    c.icon(BANNER_ICON, 48, 748, 24, color=BANNER_FG)
    c.text_fit(BANNER_TEXT, 72, 728, 372, 40, 19, color=BANNER_FG)
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
        "id": "appliance_status",
        "name": {"en": "Appliance status & alerts", "ko": "가전 상태 · 완료 알림"},
        "description": {
            "en": "Track up to 3 home appliances with running, completion and error alerts plus optional remaining time.",
            "ko": "최대 3대의 가전 동작 상태와 완료·오류 알림, 선택 남은 시간·변경 시각을 한눈에 표시합니다.",
        },
        "background": "white",
        "parameters": {
            "title": {
                "type": "string",
                "default": "가전 동작 상태",
                "min_length": 1,
                "label": {"en": "Title", "ko": "제목"},
            },
            "appliance_1": {
                "type": "entity",
                "domain": "sensor",
                "default": "sensor.washer_state",
                "label": {"en": "Appliance 1 status sensor", "ko": "가전 1 상태 센서"},
            },
            "remaining_1": {
                "type": "string",
                "default": "",
                "label": {
                    "en": "Appliance 1 remaining sensor ID (optional)",
                    "ko": "가전 1 남은 시간 센서 ID (선택)",
                },
            },
            "appliance_2": {
                "type": "string",
                "default": "",
                "label": {
                    "en": "Appliance 2 status sensor ID (optional)",
                    "ko": "가전 2 상태 센서 ID (선택)",
                },
            },
            "remaining_2": {
                "type": "string",
                "default": "",
                "label": {
                    "en": "Appliance 2 remaining sensor ID (optional)",
                    "ko": "가전 2 남은 시간 센서 ID (선택)",
                },
            },
            "appliance_3": {
                "type": "string",
                "default": "",
                "label": {
                    "en": "Appliance 3 status sensor ID (optional)",
                    "ko": "가전 3 상태 센서 ID (선택)",
                },
            },
            "remaining_3": {
                "type": "string",
                "default": "",
                "label": {
                    "en": "Appliance 3 remaining sensor ID (optional)",
                    "ko": "가전 3 남은 시간 센서 ID (선택)",
                },
            },
            "accent": {
                "type": "color",
                "default": "red",
                "label": {"en": "Done & error alert color", "ko": "완료 · 오류 강조 색상"},
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
    output = "# Generated by scripts/generate_appliance_status_template.py\n" + yaml.dump(
        data, Dumper=TemplateDumper, allow_unicode=True, sort_keys=False, width=4096
    )
    if len(output.encode("utf-8")) >= 256 * 1024:
        raise ValueError("appliance_status.yaml exceeds 256 KB template limit")
    return output


if __name__ == "__main__":
    DESTINATION.write_text(generate(), encoding="utf-8")
