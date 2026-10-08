# Changelog

## Unreleased

### Changed

- ESL Manager no longer shifts its search box and drop-downs sideways when the filter or search changes the number of cards (the scrollbar space is reserved), and the filter and sort drop-downs keep a fixed width.
- The Designer's template entry point is now the first block of the left panel (**Browse templates**, with a short explanation), and the toolbar and left-panel buttons and drop-downs share one height.

## 1.2.0b3

### Added

- **Design templates.** Pick a ready-made design under **Templates** in the Designer, adjust its parameters (font, colors, entity, time…) and add it as ordinary, editable elements. The gallery shows a thumbnail of each template and the chosen one redraws as you edit its parameters, both drawn by the real renderer for the tag. See [Design templates](docs/design-templates.md), which also explains how to write one.
- Templates can come with an automation: **Replace and create automation** opens Create automation with the template's triggers already filled in (the Date label updates daily at 12:00).
- Bundled templates: Date label, Wi-Fi QR code, Message, Color check and Weather now (any `weather` entity).
- Your own templates: files in `<config>/ble_esl/templates/` appear in the gallery, and **Save as template** keeps the current design there. Template parameters can be text, numbers, colors, fonts, times, choices or entities.

### Changed

- Manager cards offer direct automation design editing, labelled last-successful images with surrounding margins, read-only badges, battery-warning filters, and sorting by attention, battery, or name. Editor headers identify the tag and automation; normal notices and save confirmations use distinct status styles.
- Preview parameters use a typed form with field validation and optional advanced JSON editing. Automation save buttons retain their text on narrow screens, imported designs start without pending edits, and less common element properties are grouped under Advanced settings.

### Fixed

- Automation design imports and previews use separate preview parameters for action-local variables. Missing parameters block rendering instead of logging undefined-variable warnings or substituting empty values. Saving preserves the original Jinja expressions and excludes preview parameters.
- Separated the 3D Print example's Python helper from its YAML so the entire example can be parsed.

## 1.2.0b2

### Added

- Create a Home Assistant automation from the current ESL design, including unsaved edits. Configure its triggers and conditions in Home Assistant after creation.
- Open an existing automation's `ble_esl.write` payload directly from ESL Manager, edit the design, and save to the same automation without copying YAML. Saving rereads the latest configuration and changes only the uniquely matched action's payload, preserving triggers, conditions, other actions, and other service data. Saving does not send over Bluetooth.

### Fixed

- Automation editing uses an isolated session and restores the ordinary design, drafts, and undo history on exit. Delayed imports, conversions, image uploads, and cancelled YAML imports cannot modify another session.
- Invalid payloads, non-finite numbers, changed or ambiguous actions, unsupported targets, and background changes block automation saves. Action matching follows Home Assistant's target precedence and does not infer targets from payload content.
- Corrected Designer panel layout and updated the English and Korean guides for direct automation editing.

### Known limitation

- Home Assistant's configuration API has no conditional write: an external change between the latest configuration read and save cannot be protected atomically.

## 1.2.0b1

### Added

- ESL Manager card dashboard with each tag's alias, battery, display size, last successful image and send time, transmission duration, and error status. The sidebar uses `mdi:label-multiple`.
- Existing Home Assistant automations can be viewed and associated with tags, including multiple automations per tag.
- Manager and Designer now follow Home Assistant's selected language, supporting English, Korean, German, Spanish, French, Italian, Japanese, Dutch, Polish, Brazilian Portuguese, Russian, Simplified Chinese, and Traditional Chinese. Switching languages preserves the current design and unsaved edits.

### Changed

- Designer sends are manual only. The Auto update sensor option and Designer's automatic send scheduler have been removed; use Home Assistant automations for scheduled or event-triggered sends. Associating an automation in Manager does not create or change its actions.
- Requires `imagespec[datamatrix]>=1.0.1` (was `>=1.0.0`).

### Fixed

- Manager and Designer headers stay visible while dashboard cards and editor content scroll, including short desktop windows and mobile layouts.

## 1.1.3

### Changed

- The ESL Designer now shows loading progress (fonts, icons, templates, component specs, devices) under its header and reveals the editor once they are loaded, instead of a blank toolbar. These requests now run in parallel, and a failed first load shows the error with a Retry button. Refresh tags keeps the editor on screen and only disables its button while it reloads.
- Requires `blesession>=0.9.0` (was `>=0.8.0`). The Failure Count and Last Failure Time sensors now come from blesession's `SessionReports` (`failures`, `last_failure_at`); their values are unchanged: one failure per write that failed with every retry exhausted, none for an attempt a retry recovered from or a write a guard declined.
- While a write waits to retry a failed attempt, the Write Duration sensor's attributes carry `retrying: true` for that attempt (blesession's report key). The attempt that ends a write never has it.
- The diagnostics download's `sensors.last_failure` is now in UTC (`+00:00`) instead of Home Assistant's local time zone. It is the same moment; the sensor's state is unaffected.
- A bug while building a write's breakdown no longer stops the write: it is logged as an error with its traceback and a minimal report (outcome, error, failed stage, attempt) is recorded in its place, still counted as a failure only when the write fails.

## 1.1.2

### Changed

- Requires `blesession>=0.8.0` (was pinned to `0.7.0`) and `imagespec>=1.0.0` (was pinned to `1.0.0`). The only behaviour change is in the library's own log: a failed unsubscribe is now logged by the `blesession.subscribe` logger instead of `blesession.notifications`. The integration's write paths are unchanged.

## 1.1.1

### Fixed

- `plot` elements read their history on the recorder's executor, so Home Assistant no longer logs "accesses the database without the database executor". The render itself still runs on the generic executor; only the query is handed to the recorder.

## 1.1.0

### Changed

- Updated to `blesession 0.7.0`. The failure sentences take blesession's `Failure` (stage, error, radio facts) instead of positional arguments, and the protocol errors (`WolinkError`, `PickSmartError`, `EasyTagError`, `XteError`, `EtagError`, `WriteRefused`) derive from blesession's `DeviceError`: WOLINK's error code is read from `WolinkError.code` instead of the message text, and a retry stops at an error that says it is final (`retryable = False`: `WriteRefused`, and a tag that lacks the GATT profile) through `default_retry_if`. Behaviour changes: a missing service, characteristic or property is no longer retried (it was retried to the retry count before); a write that never returned now reads as blesession's `write_timeout` ("the adapter or proxy stopped taking data") instead of a silent tag. The PICKSMART START probe no longer re-probes a hung write: it fails as that `WriteTimeout` at once. Each WOLINK/XTE chunk write is bounded at 10 seconds: a chunk write that hung used to run to the 10-minute attempt bound and was then not retried; it now fails after 10 seconds, is retried like any transfer failure (up to the retry count, with the extra packet pacing a failed transfer earns). A hung ETAG/PICKSMART command write (already bounded by the reply timeout) is now a `WriteTimeout` too. PICKSMART's "insufficient characteristics" is a `GattMismatch` now, so it is no longer retried.
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
