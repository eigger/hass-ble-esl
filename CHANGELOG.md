# Changelog

## Unreleased

### Changed

- Updated to `blesession 0.5.0`. Request/reply exchanges (ETAG, PICKSMART) use `Notifications.request()`, and chunked uploads (WOLINK, XTE) use `write_chunks()`. A link that has already dropped now fails as `SessionDropped` instead of a backend write error, and a request's write is bounded by the same timeout as its reply (the PICKSMART START probe keeps its write unbounded).

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

