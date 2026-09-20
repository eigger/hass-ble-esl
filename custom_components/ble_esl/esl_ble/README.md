# Adding a protocol backend

Every ESL protocol is one package under `esl_ble/<id>/`. The contract below is
**enforced**: a backend or parser class that misses a required piece raises
`ProtocolContractError` when it is defined (import time), listing everything
that is missing, and `tests/test_protocol_contract.py` runs the same checks
plus the package-layout ones against every registered backend.

## Package layout

| File | Required | Contents |
|---|---|---|
| `const.py` | yes | `BRAND`, service/characteristic UUIDs or manufacturer id, timing constants |
| `devices.py` | yes | `PRESETS: dict[str, DevicePreset]` — key must equal `preset.key` |
| `protocol.py` | yes | Pure codecs: framing, CRC, quantization, compression. No BLE, no I/O — this is the part tested without hardware |
| `parser.py` | yes | `is_<id>_advertisement(service_info)` and `<Id>BluetoothDeviceData(BleParser)` |
| `writer.py` | yes | `prepare(preset, image, address)` and `write_session(client, address, preset, prepared, *, attempt, write_delay_ms)`; usually also a `Client` class holding the GATT session |
| `__init__.py` | yes | `<Id>BleBackend(BleBackend)` — declarative, see below |

## Parser (`BleParser`)

```python
class FooBluetoothDeviceData(BleParser):
    brand = BRAND  # required: HA device manufacturer
    fallback_name = "Foo"  # required: model name until a preset is known
    is_advertisement = staticmethod(is_foo_advertisement)  # required

    def _parse(self, service_info):  # optional: readings from the advertisement
        ...
        self.update_battery(volts, MIN_V, MAX_V)  # voltage / % / battery-low in one call
        self.set_device_sw_version(...)
```

Device naming, preset tracking (`set_preset`) and the update skeleton are
inherited; do not override `_start_update`.

## Backend (`BleBackend`)

```python
class FooBleBackend(BleBackend):
    id = "foo"  # registry / options key, lowercase, unique
    label = "FOO"  # short name shown as the HA model_id
    name = "Foo (vendor)"  # shown in the config UI
    capabilities = Capabilities(
        passive_battery=...,  # battery from advertisements
        session_battery=...,  # battery from the write session's reply
        session_temperature=...,
        model_detection=...,  # advertisement identifies the model -> no model step in the config flow
        palettes=("BW", "BWR"),  # every preset's `colors` must be listed here
    )
    PRESETS = PRESETS
    parser_cls = FooBluetoothDeviceData  # also supplies `brand`
    prepare_image = staticmethod(writer.prepare)
    write_session = staticmethod(writer.write_session)

    def parse_advertisement(self, service_info) -> AdvertisementInfo | None:  # required
        ...
```

| Member | Required | Notes |
|---|---|---|
| `id`, `label`, `name`, `capabilities`, `PRESETS`, `parser_cls` | yes | class attributes |
| `parse_advertisement()` | yes | battery / versions / `model_key` from the advertisement, or `None` |
| `prepare_image()` + `write_session()` | yes\* | \*or override `write_image()` wholesale |
| `refine_preset(preset, info)` | when `model_detection=True` identifies more than one model | e.g. PickSmart's firmware quirks |
| `write_prepared()` | rarely | to refuse before connecting (XTE) |
| `read_status()` | optional | status query without a write |

`presets()`, `preset_for()`, `supported()`, `create_parser()` and `brand` are
derived from the class attributes — do not override them.

## Write path (provided by the base)

```
BleBackend.write_image(ble_device, preset, image)
  └─ encode task: to_thread(prepare_image)          ┐ overlap
  └─ write_prepared(ble_device, preset, encode)      ┘
       └─ ble_session(ble_device)   connect … finally disconnect
            └─ write_session(client, address, preset, prepared)   ← your code
```

* `prepare_image` is CPU-bound and synchronous; the integration runs it once
  per write in the executor **before** taking the BLE lock and reuses the
  result across retries.
* `write_session` receives the encode as an awaitable. Await it only once the
  handshake that does not need it is done, so encoding overlaps connecting.
  Raise on any protocol error — `write_prepared` turns every exception
  (including connect failures) into a failed `WriteResult` with
  `str(exc) or type name`, which the retry loop and failure sensors use.
  Read replies through `base.Notifications`; its timeouts already carry the step
  (`asyncio.TimeoutError` alone has no message).
* Never catch exceptions to return `success=True`; never leave the link
  subscribed to notifications (unsubscribe in `finally`, suppressing errors on
  a dropped link).

## Registering

1. `esl_ble/__init__.py`: `register(FooBleBackend())` — ids must be unique and
   advertisement matchers must not overlap with other backends
   (`test_protocol_contract.py` checks both; add a sample advertisement there).
2. `manifest.json`: add the `bluetooth` matcher(s) so Home Assistant starts a
   discovery flow for the tags.
3. `README.md` (repo root): supported-models table and gallery entry.
4. Tests: `tests/test_<id>_protocol.py` for the codecs (no hardware),
   `tests/test_<id>_writer.py` for the session against a mocked BleakClient,
   and a sample advertisement in `tests/test_protocol_contract.py`. Integration
   behaviour (discovery, entities, services) is covered generically through a
   real Home Assistant; add a case to `tests/test_config_flow.py` if the
   protocol's discovery differs (e.g. model detection).
