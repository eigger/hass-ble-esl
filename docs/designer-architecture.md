# Designer frontend architecture baseline

This document records the current frontend boundaries and the behavior later
modularization must preserve. It is an implementation baseline, not a target
package design. The separate [shared designer plan](ko/shared-designer-plan.md)
covers extracting the editor for use by other integrations.

## Current shape

The frontend is native JavaScript modules and custom elements, without a
frontend framework or bundler. `panel.js` defines the `ble-esl-designer`
custom element and currently coordinates most editor state, rendering,
interaction handling, Home Assistant requests, and document actions. Its
responsibilities include:

| Current owner | Responsibilities |
|---|---|
| `panel.js` / `BleEslDesigner` | Editor lifecycle and loading; selected tag and document; selection, undo/redo, dirty state and drafts; display and sensor-tile modes; markup and stage rendering; property and layer UI; pointer/keyboard gestures; preview scheduling; import/export, save and send; Home Assistant API calls. |
| `model.js` | Shared document helpers: cloning, IDs, palette, empty document, element bounds/defaults, and JPEG orientation. These are mostly data-oriented helpers, although ID creation uses browser `crypto`. |
| `spec-editor.js`, `dynamic-fields.js` | Imagespec field definitions/input helpers and dynamic property controls used by the panel and dialogs. |
| `component-editor.js`, `yaml-dialog.js`, `import-dialog.js`, `template-dialog.js`, `preview-parameters-dialog.js` | Focused custom elements for component configuration and modal workflows. The panel supplies their editor context and handles their results. |
| `i18n.js`, `locales/` | Home Assistant language selection, translations, and localized rerender support. |
| `manager.js` | Dashboard, device discovery/status presentation, filtering/sorting, editor entry/exit, automation association and editing. It embeds `ble-esl-designer` and owns automation configuration matching and saving. |

`panel.js` is 3,937 lines and `manager.js` is 1,256 lines at this baseline.
Line count is context, not a success metric: boundaries should follow ownership
and change flow, not arbitrary file-size targets.

## State ownership and access today

The editor element is the live owner of the working display and sensor-tile
state. In particular, `document`, `selected`, `undoStack`, `redoStack`,
`dirty`, per-tag `drafts`, template drafts, mode, zoom and preview state are
stored directly on `BleEslDesigner`. Most editor handlers read and mutate those
fields directly. The manager does not own ordinary display editing state; it
asks the editor to load a tag and reads its draft indicator.

Automation editing is an intentional cross-component exception. `manager.js`
captures the editor's return state, owns the automation source/configuration
and session lifecycle, imports the selected action payload into the editor,
then receives an `automation-save-request` to perform guarded automation
configuration saving. The editor owns the temporary editing document; the
manager owns the external automation write. Tokens and run counters prevent
late responses from mutating a session that has since changed.

Draft persistence is also editor-owned: dirty display documents are stored in
`sessionStorage` under `ble_esl_designer_drafts`, keyed by entry ID and restored
only when the device dimensions still match. The `beforeunload` guard covers
dirty current and parked sessions. Switching between display and tile-style
editing parks one mode's state while the other is active.

These ownership notes describe current implementation, not an endorsement of
direct field access as a permanent module API. During extraction, preserve
behavior first; introduce narrower commands/snapshots only where they clarify
who may change a state value.

## Host and module contracts

The Home Assistant host creates the custom elements and supplies `hass` and
panel context. `ble-esl-designer` also accepts `tag`, `panel`, and `narrow`, and
the manager sets the `managed` attribute when embedding it. The editor sends
designer operations through `hass.callWS` with type
`ble_esl/designer` and an action plus action-specific data. Keep this transport
at the integration boundary; editor UI modules should not invent alternate
server protocols.

The editor emits bubbling, composed events consumed by the manager:

| Event | Current meaning |
|---|---|
| `designer-context-changed` | Current tag, mode, and whether automation-save mode is active; manager updates its context header. |
| `automation-save-request` | Snapshot for a requested automation payload save; manager validates and writes the automation configuration. |

`model.js` exports `clone`, `createId`, `palette`, `emptyDocument`,
`onLabel`, `clampBox`, `newElement`, and `jpegOrientation`. Keep document
helpers independent of HA state and DOM where practical; callers currently
depend on the document shape and defaults produced there.

### Manager-to-editor compatibility surface

`manager.js` currently imports `hasStoredDraft(entryId)` from `panel.js` and
uses the editor element as a cross-component API. Before narrowing that API,
preserve or deliberately migrate these call sites:

| Purpose | Current editor surface used by the manager |
|---|---|
| Readiness and host setup | `ready`, `readyPromise`, `hass`, `panel`, `narrow`, `tag`, `tags`, `mode`, `switchMode(mode)`, and the `managed` attribute. `readyPromise` lets automation import wait for the first boot attempt. |
| Ordinary editor navigation | `load(tag)`, `hasDraft(entryId)`, and `displaySession?.tag` when returning to the tag design parked during tile-style editing. |
| Automation session lifecycle | `captureEditorSession()`, `beginAutomationSession(token)`, `setAutomationReturnState(state, token)`, and `restoreEditorSession(state, token)`. The manager allocates the monotonically increasing session token and owns the automation session/source; the editor stores that token and checks it against asynchronous import/save requests. |
| Automation payload import and preview parameters | `prepareAutomationPayload(payload, background, entryId, previewVariables)`, `requestPreviewVariables(variables, missingName)`, `applyAutomationPayload(result, payload, background, allowEmpty, entryId, token, previewVariables)`, plus `document` to record the imported background. |
| Automation payload export and completion | `api("export", data)` produces the validated payload. The manager then writes HA automation config. On success it compares `editor.document` with the submitted snapshot; if unchanged, it directly sets `editor.dirty = false` and calls `editor.render()`. |

This inventory reflects real coupling, including direct state mutation. It is a
compatibility constraint for staged work, not a recommendation to keep these
members public forever. A session/API extraction should replace the manager's
direct `document`/`dirty` access with an explicit contract only when all
callers and stale-session checks move together.

## UX and correctness invariants

These are observable behavior and concurrency guarantees, not implementation
choices. Preserve them through each extraction and verify the relevant existing
frontend specs after runtime changes:

- **One document, one history:** successful edits update the active document
  and undo/redo history coherently. A cancelled pointer gesture rolls back and
  creates no undo step. Selection and dirty state remain consistent across
  mode switches and automation-session restore.
- **Draft safety:** switching tags or leaving the managed editor preserves
  dirty work; drafts survive panel teardown/re-entry in the same browser
  session when the device identity and dimensions match. Unsaved work prompts
  before a full page leave.
- **Responsive editing:** typing in properties does not require blur to apply;
  rerenders preserve focus, caret/selection, partially typed invalid values,
  open advanced sections, and modal drafts. Locale changes preserve editor
  history and authored payload text.
- **Direct manipulation:** clicks select without accidentally dragging;
  dragging and resizing respect frame bounds and alignment guides; pointer
  cancellation through `pointercancel`, window blur, or explicit gesture
  cancellation restores the pre-gesture frame. Text editing shortcuts and
  keyboard nudge/delete/undo remain available.
- **Preview freshness:** preview is debounced (currently 200 ms), requests do
  not pile up without bound, and only the newest relevant response updates the
  stage. A late response cannot overwrite a newer document/session or a live
  gesture. Preview-parameter changes invalidate the applicable preview cache
  without becoming document edits.
- **Exact and interactive canvas:** exact renderer output and editable element
  overlays stay aligned; editing remains usable while a fresh renderer result
  is pending. Fit/zoom, mobile layout, and manager-embedded layout remain
  usable.
- **Explicit side effects:** preview and editing do not transmit to a device.
  Save persists a design; Send to tag is the explicit transmission action.
  Automation save changes only the validated matching action payload and does
  not send over Bluetooth.
- **Recoverable failures:** loading and operation failures are surfaced with
  retry/recovery paths; cancelled or stale asynchronous work cannot mutate a
  newer session.

The primary existing browser coverage is in `tests/frontend/editor.spec.js`,
`manager.spec.js`, `manager-ux.spec.js`, `language.spec.js`, and
`parameters.spec.js`. Their cases cover editor operations, draft restoration,
automation-session safety, responsive layout, localization, focus retention,
and preview parameters. These specs are a regression map; this documentation
change does not run them.

## Incremental migration constraints

1. Keep the custom-element entry points and their host-facing properties/events
   stable while responsibility moves behind them.
2. Move pure document rules before moving view code. Do not merge legacy
   component defaults and imagespec defaults unless the resulting document
   behavior is proven equivalent.
3. Establish one editor-session owner for document mutations before extracting
   canvas, inspector, or library views. Views may request changes but should
   not maintain competing document copies or update history/dirty flags
   independently.
4. Keep HA transport, tag capabilities, and automation configuration writes
   outside reusable editor views. Preserve the manager's guarded automation
   matching and write boundary.
5. Extract preview scheduling with its sequence/session invalidation rules
   intact. Keep gesture-time rendering and exact preview behavior coordinated.
6. Split by cohesive responsibility and actual dependency direction. Do not
   create a file or custom element solely to meet a line-count target.
7. Keep each migration step reviewable and reversible; update this baseline
   when observed contracts change.

