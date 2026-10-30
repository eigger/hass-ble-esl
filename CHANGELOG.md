# Changelog

## Unreleased

### Fixed

- Designer: leaving an automation design (browser Back to another ESL, or navigating elsewhere in Home Assistant) no longer drops unsaved changes silently; Back asks first and an unsaved design is offered back when the automation is opened again.
- Designer: *Create automation* is disabled while the design has validation errors, the YAML export works for automation designs that use preview parameters, and a failed save names the validation errors.
- Designer: the background of an opened automation design can be changed and is saved; disabled `ble_esl.write` steps are no longer offered; an unsupported `rotate` value is reported instead of being treated as 0; an unimportable payload no longer prevents opening the design.
- Designer: undoing back to the loaded or saved design no longer leaves the editor marked as having unsaved changes.
- Designer: accent, error and warning colours follow the Home Assistant theme, touch targets reach 44 px on touch screens, and animations stop with the "reduce motion" setting.
- Designer: restoring a kept automation draft says that Cancel discards it, the draft badge explains where the design is kept, the tips mention multi-select, zoom buttons have tooltips, and an empty search result offers to clear the search and filter.


## 1.7.0

### Added

- ETAG tags now report battery percentage and a low-battery indicator (≤10%) from the raw advertisement; requires a scanner and Home Assistant version that expose raw advertisements.
- Designer elements can be rotated to any angle with a slider or numeric entry; free-angle groups are exported as portable imagespec images.
- Rectangular tags can be switched between portrait and landscape from the editor toolbar.
- Home Assistant Material icons are used throughout the manager and editor, and hidden or null icons show a selectable preview-only ghost.
- The selected tag is kept in the URL, so reload and browser back/forward restore the open editor.
- Multiple elements can be selected with a marquee or Shift/Ctrl/Cmd-click, moved together by drag or keyboard, edited through shared properties, and duplicated or deleted as a group with undo.
- The designer can save the current design into an existing automation of the tag: *Save to existing automation…* from a blank start, or *Save to another automation…* while editing a loaded automation. Only automations with a `ble_esl.write` action targeting this tag are offered; when one has several, the action to replace is chosen. Only that action's `payload`, `design`, `design_specs`, `rotate` (and a non-default background) change.

### Changed

- The designer opens a tag with a blank design (or the unsaved browser draft) instead of a design stored on the server for the tag; designs are loaded from and saved to automations.
- **Send to tag** only sends; it no longer stores the design first, so a sent design stays marked as unsaved (kept as the browser draft) until it is saved into an automation.

### Removed

- Stored per-tag designs are no longer used; open the automation that uses a design, or recreate it. The designer's per-tag **Save** and **Restore** buttons, the `save` websocket action and the `document` field of the tag list are gone; outside an automation, keep a design with **Create automation** or **Save to existing automation…**. Sensor tile styles keep their own **Save**. The old `.storage/ble_esl.designer` file is no longer read or written and is left untouched.

## 1.5.1

### Fixed

- XTE (Poshiji) writes that fail through an ESP32 Bluetooth proxy with *No response from device within 5s after command 0x04* are retried with ATT writes of at most 182 bytes, 30 ms apart; the first attempt keeps full-size writes. The proxy reports the dropped writes only in its own log (`status=143`, GATT congested), so the slower writes start after a failed attempt.

### Changed

- Refresh the shared repository standards, README templates, Bluetooth troubleshooting, and reusable CI at the reviewed 2026-10-21 standards commit.
- Show the verified HACS Default status, official HACS Downloads badge, and direct HACS repository installation link in both README languages.
- Document executable payload examples and validate them through Home Assistant and the installed imagespec renderer in current and minimum dependency environments.
- Classify the electronic shelf label displays as `productivity_information` in the integration manifest.

## 1.5.0

### Added

- Designer elements can be rotated (0/90/180/270°) without converting them to imagespec; the rotated element keeps its live entity bindings and conditional rules.

### Changed

- Automations made in the designer keep component rules live: the write action carries the original design (`design`) and re-renders it with current entity states on every run. Templated imagespec elements are passed as `design_specs`, which Home Assistant renders with the automation's own variables such as `trigger`.
- New designer automations trigger on state changes only: attribute-only updates and a change to `unavailable`/`unknown` no longer rewrite the tag, and overflow runs are dropped silently.
- Invalid `design` or `design_specs` input is reported as a service validation error.

## 1.4.1

### Security

- `ble_esl.write` and `ble_esl.write_guarded` are now admin-only services. Their payload can make `dlimg` open any local image file Home Assistant can read and fetch any HTTP(S) URL, and the rendered image is shown in the Preview Content and Last Updated Content image entities, which every logged-in user can view. A non-admin user could therefore read image files or make Home Assistant request internal URLs.

### Changed

- Behavior change: calls from non-admin users, including a dashboard button or a script run by a non-admin user, now fail with `Unauthorized`. Automations and scripts started without a user (time or state triggers, designer-made automations) are unaffected. To let non-admins refresh a tag, trigger an automation that calls `ble_esl.write`.

## 1.4.0

### Changed

- Minimum Home Assistant stays at 2025.12; it is now tested in CI against exactly 2025.12.0 as well as the current release.
- Tests moved to `tests/components/ble_esl/`; CI now uses the shared hass-repo-standards workflows (see `STANDARDS.md`).
- The `write` and `write_guarded` services now validate their known options: `rotate` must be 0, 90, 180 or 270, `background` a color name or `#RGB`/`#RRGGBB`, `dry_run` a boolean and `debounce_override_ms` a non-negative integer. Invalid values are rejected before rendering instead of failing mid-render or silently falling back to white. Other keys are still accepted. Behavior changes for existing automations: `dry_run: "false"`/`"off"` is now read as false (it used to count as true and only preview), while `dry_run` null/empty, a negative `debounce_override_ms`, and an empty, `null` or unknown `background` are now rejected instead of being tolerated.
- The Failure Count sensor's state class is now `total_increasing`, since the count restarts at 0 when the entry reloads.
- `bluetooth-sensor-state-data` and `sensor-state-data`, which the integration imports directly, are now declared in the manifest requirements, and the manifest declares `integration_type: device`.
- A failed write attempt that will be retried is logged at debug level; only the final failure is a warning.
- Tag entities are no longer polled every 30 seconds; the Alias text entity writes its state itself.
- Manual setup lists only tags a connectable Bluetooth radio sees.

### Fixed

- Diagnostics no longer include the tag's MAC address inside write error messages.
- A designer panel registration failure no longer leaves the entry's platforms loaded behind a failed setup.
- Home Assistant's YAML editor reads a bare `y` as a boolean and saved `y: 22` as `'true': 22`, so `write` failed with a missing `y`. Designer exports now quote `"y"` (and `y`/`n`/`yes`/`no`/`on`/`off` values), a `true` element key is repaired back to `y` with a warning, and the docs and examples write `"y":`.

## 1.3.0

### Added

- Expose imagespec element rotation in the ESL Manager designer.

### Fixed

- Sensor device info is no longer mutated in the cache.

## 1.2.3

### Added

- Restore saved ESL designs from the Designer.

### Changed

- Improved automation design editing, including clearer save and restore behavior and focus handling.

### Fixed

- Designer toast messages no longer resize the hidden status line or shift the canvas, including on narrow screens.
- The Designer shows all missing automation preview variables together.

## 1.2.3b2

### Fixed

- Designer toast messages no longer resize the hidden status line and shift the canvas, including on narrow screens.

## 1.2.3b1

### Added

- Designer element action bar for duplicating, deleting, reordering and centering selected elements; improved touch controls and phone layout.
- ESL Manager and Designer show the integration version, and the Manager adapts better to narrow screens.

### Changed

- Updated Designer labels and toolbar wording, added an action picker dialog, and made save/send feedback stay visible while working.
- Unsaved designs now have clearer discard prompts and can be restored after navigating away from the panel.

### Fixed

- Translated the remaining Designer text and the device discovery troubleshooting hint across supported locales.
- Deleting an ESL config entry now removes its saved automation associations.

## 1.2.2

### Fixed

- **Designer: sensor & anchored element boundary clamp**: Element movement (drag and arrow keys) and direct coordinate inputs now clamp against actual rendered content bounds rather than bounding frames, allowing sensors and anchored elements (`mm`, `rb`, etc.) to naturally reach label edges (#166).
- **Designer: multi-move & resize containment**: Maintained active label boundary containment across consecutive drags and element resize operations even when frames partially extend beyond label edges (#166).

## 1.2.1

### Fixed

- **Designer: imagespec selection and hit area**: `imagespec` elements (shapes, diagrams, plots, circles, and anchored automation elements) now align their selection box and clickable hit area over their rendered content bounds, fixing selection displacement on anchored text and server-rendered elements (#161, #164).
- **Designer: imagespec preview on save**: Preserved `layerRecords` for `imagespec` elements in `adoptDocument` so saving or sending does not revert rendered elements to the "Preview updating…" placeholder (#162).
- **Designer: spec input validation**: Passed Home Assistant context to `applySpecInput` when changing select dropdown options in the properties panel (#162).

## 1.2.0

The first stable release of the 1.2 series (betas 1.2.0b1 to 1.2.0b4 are listed below).

### Added

- **Design templates**: pick a ready-made design under **Browse templates** in the Designer, adjust its parameters and add it as ordinary, editable elements, optionally with the automation that keeps it up to date (see [Design templates](docs/design-templates.md)). Bundled: Date label, Wi-Fi QR code, Message, Color check and Weather now. Save your own, or add files to `<config>/ble_esl/templates/`.
- Create a Home Assistant automation from the current ESL design, and edit an existing automation's `ble_esl.write` payload directly from ESL Manager.
- ESL Manager dashboard improvements: direct automation design editing, battery-warning filters, sorting, read-only badges and a README screenshot.

### Fixed

- Drop-downs in the Designer toolbar and left panel and in ESL Manager now match the buttons' height in Safari and other WebKit browsers (including the Home Assistant macOS app), which ignored the height of native drop-downs; they draw their own arrow.
- ESL Manager's search box and filter/sort drop-downs share one height; the drop-downs are as wide as their longest option (at least 12rem), so nothing is cut off and nothing moves when the selection changes.
- On a phone the editor bar (Dashboard, context, Connected automations) wraps instead of squeezing the context text into a one-character-wide column.
- The Manager's sort and filter labels, the "Last successful image" caption, the automation-design buttons and headings, and the messages for importing from and saving to an automation are translated in the 11 languages that still showed them in English; "design" is used consistently in French, Italian and Brazilian Portuguese. The preview-parameter dialog strings are still partly English.

## 1.2.0b4

### Changed

- README shows the ESL Manager dashboard.
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
