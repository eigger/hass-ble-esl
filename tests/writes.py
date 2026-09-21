"""Scripted outcomes for the stubbed write path (see conftest.TagWriter).

A real backend times its stages on the SessionTrace it is handed and raises
on failure; the stub does the same from a script, so the pipeline above it
(retries, pacing, the report, the sensors) is exercised for real.

    tag_writer.write_result = ok(transfer=0.1)
    tag_writer.write_result = fail("boom", connect=0.5)        # died in `connect`
    tag_writer.write_result = fail("stalled", connect=0.1, handshake=0.2, transfer=1.5)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from blesession import LinkInfo, SessionTrace

from custom_components.ble_esl.esl_ble.base import WriteResult


@dataclass
class Scripted:
    """Record `stages` (name -> seconds) on the trace, then return or raise."""

    stages: dict[str, float] = field(default_factory=dict)
    error: str | None = None
    exc: type[Exception] = RuntimeError
    link: LinkInfo | None = None
    battery_mv: int | None = None
    temperature_c: int | None = None

    def play(self, trace: SessionTrace) -> WriteResult:
        for name, seconds in self.stages.items():
            trace.record(name, seconds)
        if self.link is not None:
            trace.link = self.link
        if self.error is not None:
            if self.stages:
                trace.fail(next(reversed(self.stages)))
            raise self.exc(self.error)
        return WriteResult(
            success=True, battery_mv=self.battery_mv, temperature_c=self.temperature_c
        )


def ok(*, link: LinkInfo | None = None, **stages: float) -> Scripted:
    return Scripted(stages, link=link)


def fail(error: str = "boom", *, exc: type[Exception] = RuntimeError, **stages: float) -> Scripted:
    return Scripted(stages, error=error, exc=exc)


def play(outcome: Any, trace: SessionTrace) -> WriteResult:
    """What the stub does with a script or a plain WriteResult."""
    if isinstance(outcome, Scripted):
        return outcome.play(trace)
    if isinstance(outcome, WriteResult) and not outcome.success:
        raise RuntimeError(outcome.error or "failed")
    return outcome
