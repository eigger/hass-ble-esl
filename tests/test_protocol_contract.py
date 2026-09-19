"""Contract checks that run against every registered protocol backend.

A new protocol package is covered automatically once it is registered in
esl_ble/__init__.py; see esl_ble/README.md for what is required.
"""

from __future__ import annotations

import importlib
from unittest.mock import MagicMock

from PIL import Image
import pytest

from custom_components.ble_esl import esl_ble
from custom_components.ble_esl.esl_ble.base import BleParser

REQUIRED_MODULES = ("const", "devices", "parser", "protocol", "writer")

BACKENDS = esl_ble.all_backends()
IDS = [b.id for b in BACKENDS]


@pytest.mark.parametrize("backend", BACKENDS, ids=IDS)
def test_package_layout(backend):
    """Each protocol lives in esl_ble/<id>/ with the required modules."""
    package = f"custom_components.ble_esl.esl_ble.{backend.id}"
    assert type(backend).__module__ == package, "backend class must be defined in the package __init__"
    for module in REQUIRED_MODULES:
        importlib.import_module(f"{package}.{module}")

    const = importlib.import_module(f"{package}.const")
    assert isinstance(getattr(const, "BRAND", None), str) and const.BRAND
    devices = importlib.import_module(f"{package}.devices")
    assert devices.PRESETS is backend.PRESETS
    writer = importlib.import_module(f"{package}.writer")
    assert callable(getattr(writer, "prepare", None)), "writer.prepare(preset, image, address)"
    assert callable(getattr(writer, "write_session", None)), "writer.write_session(client, address, preset, prepared, ...)"


@pytest.mark.parametrize("backend", BACKENDS, ids=IDS)
def test_identity_attributes(backend):
    assert backend.id == backend.id.lower() and backend.id.isidentifier()
    assert backend.label and backend.name and backend.brand
    assert issubclass(backend.parser_cls, BleParser)
    assert backend.parser_cls.brand == backend.brand


@pytest.mark.parametrize("backend", BACKENDS, ids=IDS)
def test_presets_are_well_formed(backend):
    assert backend.presets(), "at least one preset"
    for key, preset in backend.presets().items():
        assert key == preset.key
        assert preset.width > 0 and preset.height > 0
        assert preset.colors in backend.capabilities.palettes
        assert preset.display_name


@pytest.mark.parametrize("backend", BACKENDS, ids=IDS)
def test_parser_ignores_foreign_advertisement(backend):
    """A blank advertisement is not claimed, and parse_advertisement copes with it."""
    info = MagicMock()
    info.name = "Something Else"
    info.address = "00:11:22:33:44:55"
    info.manufacturer_data = {}
    info.service_uuids = []
    assert backend.supported(info) is False
    assert backend.parse_advertisement(info) is None
    parser = backend.create_parser()
    parser.update(info)
    assert parser.last_service_info is None


@pytest.mark.parametrize("backend", BACKENDS, ids=IDS)
def test_prepare_image_runs_for_the_smallest_preset(backend):
    """The encode hook accepts a preset-sized image (the renderer's output)."""
    preset = min(backend.presets().values(), key=lambda p: p.width * p.height)
    image = Image.new("RGB", (preset.width, preset.height), "white")
    prepared = backend.prepare_image(preset, image, "00:11:22:33:44:55")
    assert prepared is not None and prepared is not image


def test_backend_ids_are_unique_and_matchers_disjoint_on_each_others_samples():
    """Registration order resolves detect(); matchers must not overlap."""
    assert len(IDS) == len(set(IDS))
    samples = {
        "wolink": {"manufacturer_data": {0xBBAA: bytes(10)}, "service_uuids": []},
        "easytag": {"manufacturer_data": {}, "service_uuids": ["00001523-1212-efde-1523-785feabcd123"]},
        "picksmart": {"manufacturer_data": {0x5053: bytes(5)}, "service_uuids": []},
        "poshiji": {
            "manufacturer_data": {0x5258: bytes.fromhex("fd024002009964060102ffff1e")},
            "service_uuids": [],
        },
    }
    assert set(samples) == set(IDS), "add a sample advertisement for every registered backend"
    for owner, fields in samples.items():
        info = MagicMock(name="x", address="00:11:22:33:44:55", **fields)
        info.name = "x"
        claimed = [b.id for b in BACKENDS if b.supported(info)]
        assert claimed == [owner], f"{owner} sample claimed by {claimed}"
