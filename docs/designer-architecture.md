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

| Current owner                                                                                                     | Responsibilities                                                                                                                                                                                                                                                                                                                                                                                             |
| ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `panel.js` / `BleEslDesigner`                                                                                     | Editor lifecycle and loading; selected tag and drafts; display and sensor-tile modes; markup and stage rendering; property UI; event wiring; import/export, save and send; Home Assistant API calls. It applies preview results through an explicit callback and exposes compatibility accessors for active session state.                                                                                   |
| `editor/session.js` / `EditorSession`                                                                             | Owns the active document, selected element, undo/redo history, dirty flag, history limit, and capture/restore/reset transitions.                                                                                                                                                                                                                                                                             |
| `editor/preview.js` / `PreviewController`                                                                         | Owns the 200 ms debounce, single in-flight request, one latest queued rerun, sequence invalidation, and stale-result/error suppression. It receives request, context validity, result, and error callbacks; it does not assign layers or render the stage.                                                                                                                                                   |
| `editor/canvas/geometry.js`                                                                                       | Pure canvas calculations for renderer-dependent visible bounds, render-shape signatures and record adoption, selection-overlay and context-menu geometry, alignment guides, fit zoom, new-element staggering, and move/resize frame clamping. Renderer records, layer bounds, viewport and tag dimensions, zoom, and snap tolerance are explicit inputs; it does not read the panel, DOM, or Home Assistant. |
| `editor/canvas/view.js`                                                                                           | Resolves layer labels and builds accessible canvas layer, cropped layer-image, exact-preview, alignment-guide, and selection-overlay markup from explicit view values. The panel prepares layer content and renderer metadata, attaches the result, restores focus, updates HA icons, and retains preview/state ownership.                                                                                   |
| `editor/canvas/sensor-content.js`                                                                                 | Renders sensor tile and template child markup from explicit display values. The panel resolves HA state, templates, weather values, numbers, and icons; this module does not query HA or own editor state.                                                                                                                                                                                                   |
| `editor/sensor-templates.js`                                                                                      | Owns pure sensor output classification, template compatibility/type enumeration, token substitution, and default sensor-template document construction. Document factories are explicit inputs; entity lookup, localization, and template editing state remain in the panel.                                                                                                                                 |
| `editor/entity-library.js`                                                                                        | Owns supported-entity filtering, numeric-sensor selection for plot defaults, entity search matching, entity display-name/value formatting rules, and selected-entity preview markup. Home Assistant state and formatting callbacks, localization, icon setup, and add actions remain at the panel boundary.                                                                                                  |
| `editor/tag-selector.js`                                                                                          | Resolves alias-state display names with a title fallback and renders escaped tag option markup with the selected tag and physical dimensions. The panel retains alias state lookup, tag loading, and selection state.                                                                                                                                                                                        |
| `editor/header-view.js`                                                                                           | Renders the editor title, version, and mode tabs from explicit mode, lock/loading state, version, translation, and escaping inputs. The panel retains Home Assistant menu setup and derives session/version state.                                                                                                                                                                                           |
| `editor/document-indicators.js`                                                                                   | Updates undo/redo availability and the dirty-save badge, label, and preview title without rebuilding the editor. The panel retains document history and dirty state and supplies translation and icon helpers.                                                                                                                                                                                               |
| `editor/element-actions.js`                                                                                       | Shares action metadata and accessible markup between the canvas context menu and inspector action bar. The panel retains context-menu positioning/focus and all document actions.                                                                                                                                                                                                                            |
| `editor/workspace-controls.js`                                                                                    | Renders accessible controls for collapsing the library and inspector panels and calculates sticky-header scroll offsets from explicit values. The panel retains layout state, DOM measurement, style application, and event handling.                                                                                                                                                                        |
| `editor/workspace-view.js`                                                                                         | Composes the complete library, preview/canvas shell, and inspector/layer workspace, including responsive layout styles. The panel supplies explicit view state and pre-rendered leaf content; lifecycle, focus/scroll preservation, canvas drawing, picker wiring, and editing actions remain in the panel.                                                                                                       |
| `editor/image-upload.js`                                                                                          | Owns the asynchronous image-file upload lifecycle, EXIF orientation correction, and stale-document/session guards. The panel continues to own upload busy state, history checkpoints, document edits, and error reporting through the explicit panel argument.                                                                                                                                               |
| `editor/color-picker.js`                                                                                          | Renders accessible color swatches from the supplied palette, including transparency for background controls. The panel owns palette selection, translation, and document edits through the existing `data-pick` event path.                                                                                                                                                                                  |
| `editor/entity-pickers.js`                                                                                        | Configures and upgrades the Home Assistant entity pickers used by the library, element binding, and template sample selection, and adapts their selection events through callbacks. State lookup and document edits remain in the panel.                                                                                                                                                                     |
| `editor/entity-icons.js`                                                                                          | Resolves the designer's default icon for a Home Assistant entity from its explicit state record. The panel keeps a compatibility method; icon-catalog loading and rendering remain separate.                                                                                                                                                                                                                 |
| `editor/template-controls.js`                                                                                     | Renders sensor-template controls and token-tool markup from explicit mode, values, choices, translation, and escaping inputs. The panel owns template editing state, sample selection, persistence, and document changes.                                                                                                                                                                                    |
| `editor/draft-store.js`                                                                                           | Owns the session-storage key, serialization, safe reads/writes, and same-size draft restoration. The panel selects which documents are dirty drafts; the manager imports `hasStoredDraft()` directly and imports the panel explicitly for custom-element registration.                                                                                                                                       |
| `editor/icon-picker.js`                                                                                           | Renders accessible icon glyph and chooser-button markup from the supplied icon catalog. The panel owns catalog loading, search-field events, and picker state.                                                                                                                                                                                                                                               |
| `editor/canvas/interactions.js`                                                                                   | Pointer, keyboard, and inline-text interaction handlers. They receive the panel explicitly and request document, history, preview, and rendering work through its existing methods; the panel keeps compatibility entry points and owns gesture state used by other workflows.                                                                                                                               |
| `editor/inspector/layers.js`                                                                                      | Renders layer rows and handles selection, visibility, ordering, and deletion. Rendering receives elements and label/icon/translation helpers explicitly; actions delegate document history and rerendering through the panel.                                                                                                                                                                                |
| `editor/inspector/spec-sections.js`                                                                               | Groups imagespec property markup into documentation, ordered common fields, position controls, and advanced settings. The panel supplies markup, translated labels, position controls, and the open state; this module does not own inspector state or document edits.                                                                                                                                       |
| `editor/inspector/spec-input.js`                                                                                  | Applies imagespec inspector values to nested spec data, retaining the last valid value for incomplete JSON or numbers and attaching accessible inline errors. The panel still owns checkpoints, document history, and dirty state.                                                                                                                                                                           |
| `editor/inspector/optional-properties.js`                                                                         | Renders optional style and advanced controls for legacy element types. Translation, HTML escaping, icon color picker, and supported dither methods are explicit inputs; document changes and history stay in the panel.                                                                                                                                                                                      |
| `editor/inspector/text-alignment.js`                                                                              | Renders font-size and accessible text-alignment controls for sensor and text elements. It receives translation and HTML-escaping helpers; `data-pick="align"` continues through the panel's existing edit and history path.                                                                                                                                                                                  |
| `editor/inspector/weather-controls.js`                                                                            | Renders weather sensor time and field selectors. It receives the selected sensor values and a translation callback; the panel decides when weather controls apply and continues to own property changes and history.                                                                                                                                                                                         |
| `editor/inspector/sensor-options.js`                                                                              | Prepares legacy sensor inspector style choices, numeric eligibility, weather state choices, and template sample states from explicit inputs. The panel retains Home Assistant lookup, localization, and template context ownership.                                                                                                                                                                          |
| `editor/inspector/legacy-properties.js`                                                                           | Composes property controls for non-imagespec elements into Content, Position, Style, and Advanced sections. The panel supplies explicit rendering callbacks and precomputed sensor choices; event handling, HA lookups, and document mutations remain panel-owned.                                                                                                                                           |
| `model.js`                                                                                                        | Shared document helpers: cloning, IDs, palette, empty document, element bounds/defaults, and JPEG orientation. These are mostly data-oriented helpers, although ID creation uses browser `crypto`.                                                                                                                                                                                                           |
| `editor/document-operations.js`                                                                                   | Pure imported-document normalization. The panel supplies document defaults, cloning, and ID creation as explicit dependencies.                                                                                                                                                                                                                                                                               |
| `spec-editor.js`, `dynamic-fields.js`                                                                             | Imagespec field markup and element creation, plus dynamic property controls used by the panel and dialogs. `applySpecInput` remains re-exported from `spec-editor.js` for compatibility; its implementation lives in `editor/inspector/spec-input.js`.                                                                                                                                                       |
| `component-editor.js`, `yaml-dialog.js`, `import-dialog.js`, `template-dialog.js`, `preview-parameters-dialog.js` | Focused custom elements for component configuration and modal workflows. The panel supplies their editor context and handles their results.                                                                                                                                                                                                                                                                  |
| `i18n.js`, `locales/`                                                                                             | Home Assistant language selection, translations, and localized rerender support.                                                                                                                                                                                                                                                                                                                             |
| `manager.js`                                                                                                      | Dashboard, device discovery/status presentation, filtering/sorting, editor entry/exit, automation association and editing. It embeds `ble-esl-designer` and owns automation configuration matching and saving.                                                                                                                                                                                               |

`panel.js` is 3,201 lines and `manager.js` is 1,257 lines at this phase.
Line count is context, not a success metric: boundaries should follow ownership
and change flow, not arbitrary file-size targets.

## State ownership and access today

`EditorSession` is the live owner of the active document, selected element,
undo/redo stacks, and dirty flag. `BleEslDesigner` exposes `document`,
`selected`, `undoStack`, `redoStack`, and `dirty` compatibility accessors that
delegate to the session, so existing manager and host call sites remain valid
while callers migrate. Session methods own reset, capture/restore, history
checkpoints, undo/redo steps, and dirty transitions. The panel still owns
per-tag drafts, template drafts, mode, zoom, and rendered preview state. The
preview controller owns scheduling state and checks a captured document
session context plus its sequence before forwarding results or errors. The
panel retains `previewRequest()` as the replaceable request seam and
`queuePreview()` as a compatibility scheduling method. A pending timer is
also exposed through the read-only `previewTimer` compatibility accessor.
The manager does not own ordinary display editing state; it asks the editor
to load a tag and reads its draft indicator.

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

| Event                      | Current meaning                                                                                              |
| -------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `designer-context-changed` | Current tag, mode, and whether automation-save mode is active; manager updates its context header.           |
| `automation-save-request`  | Snapshot for a requested automation payload save; manager validates and writes the automation configuration. |

`model.js` exports `clone`, `createId`, `palette`, `emptyDocument`,
`onLabel`, `clampBox`, `newElement`, and `jpegOrientation`. Keep document
helpers independent of HA state and DOM where practical; callers currently
depend on the document shape and defaults produced there.

### Manager-to-editor compatibility surface

`manager.js` imports `hasStoredDraft(entryId)` from `editor/draft-store.js` and
imports `panel.js` for custom-element registration. It uses the editor element
as a cross-component API for editing operations. Before narrowing that API,
preserve or deliberately migrate these call sites:

| Purpose                                          | Current editor surface used by the manager                                                                                                                                                                                                                                                                                                    |
| ------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Readiness and host setup                         | `ready`, `readyPromise`, `hass`, `panel`, `narrow`, `tag`, `tags`, `mode`, `switchMode(mode)`, and the `managed` attribute. `readyPromise` lets automation import wait for the first boot attempt.                                                                                                                                            |
| Ordinary editor navigation                       | `load(tag)`, `hasDraft(entryId)`, and `displaySession?.tag` when returning to the tag design parked during tile-style editing.                                                                                                                                                                                                                |
| Automation session lifecycle                     | `captureEditorSession()`, `beginAutomationSession(token)`, `setAutomationReturnState(state, token)`, and `restoreEditorSession(state, token)`. The manager allocates the monotonically increasing session token and owns the automation session/source; the editor stores that token and checks it against asynchronous import/save requests. |
| Automation payload import and preview parameters | `prepareAutomationPayload(payload, background, entryId, previewVariables)`, `requestPreviewVariables(variables, missingName)`, `applyAutomationPayload(result, payload, background, allowEmpty, entryId, token, previewVariables)`, plus `document` to record the imported background.                                                        |
| Automation payload export and completion         | `api("export", data)` produces the validated payload. The manager then writes HA automation config. On success it compares `editor.document` with the submitted snapshot; if unchanged, it directly sets `editor.dirty = false` and calls `editor.render()`.                                                                                  |

This inventory reflects real coupling, including direct state mutation through
compatibility accessors. It is a compatibility constraint for staged work, not
a recommendation to keep these members public forever. A later API extraction
should replace the manager's direct `document`/`dirty` access with an explicit
contract only when all callers and stale-session checks move together.

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
- **Preview freshness:** preview is debounced (currently 200 ms), with one
  in-flight request and at most one queued rerun that reads the latest editor
  state. Sequence invalidation and captured session checks ensure only the
  newest relevant response or error reaches the panel. A late response cannot
  overwrite a newer document/session or a live gesture. The panel callback
  assigns layer results and draws the stage. Removing a template sample
  invalidates pending and queued preview work. Preview-parameter changes
  invalidate the applicable preview cache without becoming document edits.
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

The primary existing browser coverage is in `tests/components/ble_esl/frontend/editor.spec.js`,
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
5. Preview scheduling is extracted into `editor/preview.js`. Keep its callback
   contract, sequence/session invalidation rules, and gesture-time rendering
   coordinated as the remaining editor views are extracted.
6. Split by cohesive responsibility and actual dependency direction. Do not
   create a file or custom element solely to meet a line-count target.
7. Keep each migration step reviewable and reversible; update this baseline
   when observed contracts change.

The first runtime extraction moves imported-document normalization into
`editor/document-operations.js`. `BleEslDesigner.normalizeImportedDocument()`
remains as a compatibility delegate, and the operation receives document
defaults, cloning, and ID generation explicitly. Imported document fields,
legacy element defaults, and missing-ID generation remain unchanged.

The canvas geometry extraction moves renderer-aware shape signatures, visible
bounds, alignment guide calculations, and move/resize frame clamping into
`editor/canvas/geometry.js`. The panel keeps compatibility methods and applies
returned frame copies to its active document, preserving history ownership.
Geometry receives layer records and renderer bounds explicitly; pointer
gesture state, canvas markup, and element staggering remain panel responsibilities.

The canvas view extraction moves layer wrapper markup, exact-preview composition,
alignment-guide markup, and selection-overlay markup into
`editor/canvas/view.js`. The panel still prepares each element's content and
render freshness, attaches the composed markup, restores keyboard focus, updates
Home Assistant icons, and mutates selection/preview state. The view module has
no panel, DOM, geometry, or Home Assistant dependency.

The sensor-content extraction moves template-child and sensor-tile markup into
`editor/canvas/sensor-content.js`. The panel continues to resolve Home Assistant
state, templates, sensor values, weather attributes, and icons, then passes the
display values and rendering helpers explicitly. Template substitution,
conditional child selection, scaling, and tile markup stay in the canvas view
module; it does not own state or make Home Assistant lookups.

The sensor-template rules extraction moves output classification, entity type,
template compatibility, template type enumeration, and the default sensor tile
document factory into `editor/sensor-templates.js`. The panel retains
compatibility methods and supplies the document factories. Home Assistant
entity discovery, translation, editing state, and template persistence remain
in the panel.

The entity-library extraction moves the supported-domain predicate, search
matching, and selected-entity preview markup into `editor/entity-library.js`.
The panel supplies Home Assistant states, formatted names and values,
translation, and HTML escaping, and continues to configure the state icon,
picker events, and sensor-add action. This keeps entity-library rules
independent of the panel and Home Assistant runtime.

The entity display-formatting extraction moves entity-name fallback and sensor
value formatting rules into `editor/entity-library.js`. The panel supplies the
Home Assistant formatter and translated unavailable label, retaining its
compatibility methods and state lookup boundary. Text elements, missing or
unknown states, decimal precision, units, and Home Assistant formatted values
keep their established behavior.

The plot-default entity extraction moves selection of the first numeric
`sensor.*` state into `editor/entity-library.js`. The panel supplies the
discovered entity list and retains imagespec construction, document edits, and
history ownership.

The interaction extraction moves keyboard commands, pointer gestures, and
inline text editing into `editor/canvas/interactions.js`. The panel retains its
`key()`, `pointer()`, `beginTextEdit()`, and `finishTextEdit()` compatibility
methods and continues to own gesture state so session changes and other panel
flows can cancel or finish gestures as before.

The layer-list extraction moves row rendering and layer selection, visibility,
ordering, and deletion actions into `editor/inspector/layers.js`. The panel
continues to compose the inspector and owns the document and edit history; the
layer module preserves the front-first order, accessible labels, and focus
restoration after a row action.

The imagespec inspector extraction moves field grouping into
`editor/inspector/spec-sections.js`. It keeps documentation first, sorts common
fields by the established priority, preserves required nested groups, places
position controls between common and advanced settings, and receives the
advanced section's open state from the panel. `BleEslDesigner` continues to
compose the inspector and owns its state and document updates.

The legacy property-control extraction moves optional style and advanced
markup for text, shapes, images, icons, progress bars, and gauges into
`editor/inspector/optional-properties.js`. The panel supplies translation,
escaping, the icon color picker, and renderer-supported dither methods. It
continues to compose these controls and owns all property edits and history.

The text-style extraction moves the font-size field and left/center/right
alignment controls into `editor/inspector/text-alignment.js`. The renderer
preserves the existing button labels, pressed state, and `data-pick="align"`
event contract; the panel continues to apply changes and record history.

The weather-sensor control extraction moves the “When” and “Show” selectors
into `editor/inspector/weather-controls.js`. The panel still decides whether
the selected entity is a weather sensor and owns all resulting document edits
and history.

The legacy inspector composition extraction moves non-imagespec property
markup assembly into `editor/inspector/legacy-properties.js`. It composes the
existing optional-property, text-alignment, and weather-control renderers and
keeps the established field ordering and event attributes. The panel retains
the imagespec path, supplies Home Assistant and template context, and handles
all edits, focus, and undo history.

The draft-store extraction moves the session-storage format and safe
serialization into `editor/draft-store.js`. It preserves the storage key,
same-dimension restore rule, one-shot removal after restore, and quiet handling
of blocked/full storage. The panel still decides which active or parked
documents count as dirty drafts, while the manager reads the stored-draft flag
directly rather than coupling that query to the panel module.

The icon-picker extraction moves icon glyph and chooser-button markup into
`editor/icon-picker.js`. The panel retains icon-catalog loading, search events,
and selected-icon actions; the module receives the catalog and escaping helper
explicitly and preserves the existing case-insensitive filtering, 120-item
limit, and accessible button attributes.

The entity-icon extraction moves the pure default-icon mapping for weather,
binary sensors, and common sensor device classes into `editor/entity-icons.js`.
It preserves entity-provided icon overrides and the existing fallback values.
The panel keeps its compatibility method and continues to own entity lookup and
template editing behavior.

The template-control extraction moves sensor-template control and token-tool
markup into `editor/template-controls.js`. The panel supplies current template
values and choices plus translation and escaping helpers; template selection,
sample-entity handling, persistence, and document edits stay in the panel.

The status-view extraction moves inline status and floating notice presentation
into `editor/status-view.js`. The panel supplies the current status snapshot,
translation and timeout callbacks; it retains status state and notice timing
ownership. Routine status text, preview errors, dismiss controls, and temporary
save/send notices preserve their existing accessibility behavior. The status
module also resolves the send-button hint from explicit tag capability and
busy-status values; the panel remains the state owner.

The loading-view extraction moves initial loading-step definitions,
completion transitions, and progress/error markup into
`editor/loading-view.js`. The panel retains boot requests, step completion
timing, the loading shell, and retry behavior; the view receives loading state
plus translation and HTML-escaping helpers.

The header-view extraction moves the editor title, version label, and mode-tab
markup into `editor/header-view.js`. The panel continues to derive the version
and session lock and configure the Home Assistant menu; the view receives the
mode and readiness state plus translation and escaping helpers. Tab labels,
pressed state, lock-based disabling, and version escaping are preserved.

The tag-selector extraction moves tag option markup into
`editor/tag-selector.js`. The panel supplies the current tags, selected tag,
display-name callback, and HTML escaping helper; tag loading, alias state
lookup, and selection handling remain panel-owned.

The tag alias display-name extraction moves unavailable, unknown, and blank
alias-state fallback rules into `editor/tag-selector.js`. The panel supplies
the resolved alias state; the module falls back to the tag title when that
state cannot provide a display name.

The document-indicators extraction moves the in-place updates for undo/redo
availability and dirty-save presentation into
`editor/document-indicators.js`. The panel retains its compatibility methods,
history and dirty-state ownership, and supplies the save-mode value, translated
labels, and save icon. The accessible save labels, keyboard shortcut hint,
dirty badge, and preview title remain unchanged.

The element-actions extraction moves the shared action metadata and markup for
the canvas context menu and inspector action bar into
`editor/element-actions.js`. The panel retains context-menu placement and focus,
action event handling, translation, and all document mutations. The action set,
shortcuts, accessible labels, and busy-state disabling remain unchanged.

The image-upload extraction moves image reading, JPEG EXIF orientation
correction, and asynchronous upload cleanup into `editor/image-upload.js`.
The panel passes itself explicitly; the upload still uses the existing history,
dirty-state, busy-state, error, and render paths. Stale uploads continue to be
discarded when their element, document, tag, or automation session has changed.

The color-picker extraction moves accessible swatch markup into
`editor/color-picker.js`. The panel supplies the tag palette and translated
labels, and continues to own color selection and document history through the
existing `data-pick` event path. Background controls retain their transparent
swatch and patterned preview.

The legacy sensor-options extraction moves preparation of compatible template
styles, numeric-field eligibility, weather template states, and sample state
choices into `editor/inspector/sensor-options.js`. The panel supplies resolved
Home Assistant states, templates, entities, and classification callbacks;
lookup, localization, inspector rendering, and document edits remain at the
panel boundary. The legacy inspector continues to receive the same
`sensorOptions` shape.

The imagespec palette extraction moves grouped renderer-type selector markup
into `editor/inspector/spec-palette.js`. The panel supplies renderer metadata,
mode, translation, and escaping; imagespec element construction, default
sensor selection for plots, document history, and focus remain panel-owned.

The state-icon inspector extraction moves state-to-icon row and picker markup
into `editor/inspector/state-icons.js`. The panel supplies sample state,
output classification, default icon and glyph callbacks, translation, and
escaping. Icon catalog state, mapping edits, and document history remain in
the panel.

The fit-zoom extraction moves the viewport-to-tag scale calculation into
`editor/canvas/geometry.js`. The panel still reads viewport dimensions and
applies the resulting scale to the stage, while geometry preserves the 60 px
margin, hundredth-step rounding, and 0.1–8.0 limits without DOM dependencies.

The layer-image view extraction moves renderer-cropped layer image markup into
`editor/canvas/view.js`. The panel supplies the image source, visible-content
offset and bounds, and renderer size record. The view preserves frame-growth
scaling for non-text elements and leaves renderer state and stage attachment
with the panel.

The new-element placement extraction moves diagonal collision staggering into
`editor/canvas/geometry.js`. The panel supplies the candidate, existing
elements, and tag dimensions, then applies the returned position through its
existing creation flow. The helper preserves the 8 px steps and edge stop while
leaving document mutation and history with the panel.

The layer-record extraction moves creation of render identity and frame-size
snapshots into `editor/canvas/geometry.js`. The panel decides when to capture
them, while geometry creates detached records used for preview freshness and
renderer-bound calculations.

The render-record adoption extraction moves retention of measured layer
records across server document normalization into `editor/canvas/geometry.js`.
The panel supplies current and saved elements, previous records, and its
visible-bounds callback, then replaces the document. Geometry keeps only
previously measured ids, refreshes each shape signature from the saved element,
and retains its measured frame size.

The workspace-panel control extraction moves the shared accessible collapse
button markup into `editor/workspace-controls.js`. The panel supplies each
panel's action, state, label, target id, translated strings, and menu icon;
layout state and toggle handling remain in the panel.

The workspace sticky-offset extraction moves CSS offset formatting into
`editor/workspace-controls.js`. The panel still measures the header and toolbar
and decides whether the header is fixed, then applies the returned top and
scroll-padding values.

The sensor-template token extraction moves substitution of `{{name}}`,
`{{state}}`, `{{unit}}`, and `{{icon}}` into `editor/sensor-templates.js`.
The panel still checks template mode and resolves Home Assistant sample values;
the pure helper only replaces the established tokens.

The selection-overlay geometry extraction centralizes the visible-frame
position, dimensions, and pointer-scaled handle size in
`editor/canvas/geometry.js`. The panel supplies the current element, renderer
bounds, zoom, and pointer mode to both initial canvas markup and live overlay
updates; the view receives the computed geometry and retains markup ownership.

The context-menu placement extraction moves pointer-to-viewport clamping into
`editor/canvas/geometry.js`. The panel supplies pointer and viewport
coordinates, then retains menu construction, accessibility attributes, focus,
and action handling.

The layer-label extraction moves element-specific and Home Assistant fallback
precedence into `editor/canvas/view.js`. The panel supplies the resolved state,
entity-name formatter, and imagespec label helper; state lookup and localization
remain at the panel boundary.

The entity-picker upgrade extraction moves replacement of legacy picker nodes
and attribute copying into `editor/entity-pickers.js`. The panel supplies its
shadow root and custom-element factory, then retains picker configuration,
entity lookup, and rerender callbacks.

The toolbar presentation extraction moves the state-driven editor toolbar
markup and its sticky-header, sticky-toolbar, and labeled-action style rules
into `editor/toolbar-view.js`. The panel supplies the current tag and editor
state, translated text, icons, and tag/send helpers. It retains state
derivation, event handling, automation-save label adjustment, and all toolbar
workflows.

The workspace-view extraction moves the full three-column library,
preview/canvas shell, and inspector/layers composition, together with their
responsive layout rules, into `editor/workspace-view.js`. The panel supplies
derived display state, toggle controls, and leaf markup for library tools,
element properties/actions, and layer rows. It still owns focus and scroll
restoration, HA picker wiring, canvas measurement/drawing, document state, and
all editing workflows.
