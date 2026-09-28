"""easyTag model catalog; the model code is printed on the tag."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base import DevicePreset

if TYPE_CHECKING:
    from home_assistant_bluetooth import BluetoothServiceInfoBleak


def _preset(
    key: str,
    name: str,
    width: int,
    height: int,
    colors: str,
) -> DevicePreset:
    return DevicePreset(
        key=key,
        display_name=name,
        width=width,
        height=height,
        colors=colors,
        extra={"dither": True},
    )


PRESETS: dict[str, DevicePreset] = {
    preset.key: preset
    for preset in (
        _preset("33", '1.54" BWR (ET0154-33B)', 200, 200, "BWR"),
        _preset("36", '2.13" BWR (ETR0213-36B)', 250, 122, "BWR"),
        _preset("39", '2.13" BW (ETR0213-39B)', 250, 122, "BW"),
        _preset("3A", '2.66" BWR (ET0266-3A)', 296, 152, "BWR"),
        _preset("3D", '2.9" BWR (ET0290-3DB)', 296, 128, "BWR"),
        _preset("FF", '2.9" BWR Gen1 (ETR290-FF)', 296, 128, "BWR"),
        _preset("55", '3.5" BWR (ET0350-55B)', 384, 184, "BWR"),
        _preset("40", '4.2" BWR (ET0420-40B)', 400, 300, "BWR"),
        _preset("43", '4.2" BWR (ET0420-43B)', 400, 300, "BWR"),
        _preset("4F", '5.8" BWR (ETR0580-4FB)', 648, 480, "BWR"),
        _preset("44", '7.5" BWR (ET0750-44B)', 800, 480, "BWR"),
        _preset("64", '10.2" BWR (ET1020-64)', 960, 640, "BWR"),
    )
}


def preset_for_advertisement(service_info: BluetoothServiceInfoBleak | None) -> DevicePreset | None:
    """The preset the advertisement names; no advertisement field is known to, yet."""
    return None
