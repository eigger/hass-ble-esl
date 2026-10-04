# Changelog

## Unreleased

### Changed

- Updated to `blesession 0.7.0`. The failure sentences take blesession's `Failure` (stage, error, radio facts) instead of positional arguments, and the protocol errors (`WolinkError`, `PickSmartError`, `EasyTagError`, `XteError`, `EtagError`, `WriteRefused`) derive from blesession's `DeviceError`: WOLINK's error code is read from `WolinkError.code` instead of the message text, and a retry stops at an error that says it is final (`retryable = False`: `WriteRefused`, and a tag that lacks the GATT profile) through `default_retry_if`. Behaviour changes: a missing service, characteristic or property is no longer retried (it was retried to the retry count before); a write that never returned now reads as blesession's `write_timeout` ("the adapter or proxy stopped taking data") instead of a silent tag, and each chunk write is bounded at 10 seconds.
- The ETAG and XTE GATT lookups use `characteristic_or_raise()`, so a missing service or characteristic (both), a missing property (XTE) or a too-small write size (ETAG) is reported as blesession's `GattMismatch` instead of the protocol error, with slightly different wording. Its failure sentence has its own `likely_cause_key`, `session.gatt_mismatch` (was `session.refused`). The failure sentences read the error's type (`NotificationTimeout`, `SessionDropped`) instead of matching its text.
- Request/reply exchanges (ETAG, PICKSMART) use `Notifications.request()`, and chunked uploads (WOLINK, XTE) use `write_chunks()`. On those exchanges, a link that has already dropped now fails as `SessionDropped` instead of a backend write error, and a request's write is bounded by the same timeout as its reply (the PICKSMART START probe gives its write a separate, longer limit).

## 1.0.0

First stable release of BLE ESL.

### Added

- A visual ESL Designer with alignment guides, improved selection and resizing, more responsive gestures, and better keyboard focus handling.
- BLE write diagnostics that retain the last known image state when an integration entry unloads during a write.

### Changed

- BLE writes are serialized in request order, and queued writes are discarded when their integration entry unloads. Duplicate guarded writes cancel stale debounce timers.
- `ble_esl.write` and `ble_esl.write_guarded` now require `payload` to be a list. Use `payload: []` to intentionally send a blank screen.
- Rendering uses `imagespec 1.0.0`; BLE session reporting uses `blesession 0.4.1`.

### Compatibility

- Existing valid payloads and stored designer layouts keep their format.
- Automations or scripts that call a write action without `payload` must add one before upgrading.
- Requires Home Assistant 2025.12 or newer.

