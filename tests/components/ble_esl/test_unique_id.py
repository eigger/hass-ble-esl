"""Entity unique ids: legacy entries keep the short id, new entries use the full address."""

from homeassistant.helpers import entity_registry as er
import pytest

from custom_components.ble_esl.const import CONF_FULL_ID, DOMAIN
from custom_components.ble_esl.data import tag_identifier

from .conftest import ADDRESS, IDENT, setup_entry

pytestmark = pytest.mark.usefixtures("enable_bluetooth")

# Same last four bytes, different first two: they collide on the legacy id.
TAG_A = "B9:B9:00:18:39:37"
TAG_B = "F3:83:00:18:39:37"


def test_tag_identifier():
    assert tag_identifier(TAG_A, full=False) == tag_identifier(TAG_B, full=False) == "00183937"
    assert tag_identifier(TAG_A, full=True) == "B9B900183937"
    assert tag_identifier(TAG_A, full=True) != tag_identifier(TAG_B, full=True)


async def test_entry_without_flag_keeps_legacy_unique_ids(hass):
    entry = await setup_entry(hass)
    assert entry.runtime_data.identifier == IDENT
    registry = er.async_get(hass)
    ids = {e.unique_id for e in er.async_entries_for_config_entry(registry, entry.entry_id)}
    assert f"ble_esl_{IDENT}_alias" in ids
    assert not any(i.startswith(f"ble_esl_{ADDRESS.replace(':', '')}") for i in ids)


async def test_new_entries_with_colliding_short_ids_do_not_collide(hass):
    entries = [
        await setup_entry(hass, address=address, data={CONF_FULL_ID: True})
        for address in (TAG_A, TAG_B)
    ]
    registry = er.async_get(hass)
    for entry, address in zip(entries, (TAG_A, TAG_B), strict=True):
        full = address.replace(":", "")
        owned = er.async_entries_for_config_entry(registry, entry.entry_id)
        assert any(e.unique_id == f"{DOMAIN}_{full}_alias" for e in owned), full
