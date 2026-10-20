import {
  sharedProperties,
  setSharedProperty,
  beginMarquee,
} from "./editor/group-selection.js";
import { materialIcon } from "./editor/material-icons.js";
import {
  renderElementRotation,
  syncRotationInputs,
} from "./editor/rotation-control.js";
import { t, language, rerenderWithDialogs, errorText } from "./i18n.js";
import "./component-editor.js";
import "./yaml-dialog.js";
import "./import-dialog.js";
import "./template-dialog.js";
import "./preview-parameters-dialog.js";
import { newSpecElement, specEditorHtml, specLabel } from "./spec-editor.js";
import { applySpecInput } from "./editor/inspector/spec-input.js";
import { normalizeImportedDocument } from "./editor/document-operations.js";
import { handleImageUpload } from "./editor/image-upload.js";
import { renderColorPicker } from "./editor/color-picker.js";
import { renderToolbar, TOOLBAR_STYLE } from "./editor/toolbar-view.js";
import { renderWorkspace, WORKSPACE_STYLE } from "./editor/workspace-view.js";
import {
  clone,
  createId,
  palette,
  emptyDocument,
  clampBox,
  onLabel,
  newElement,
} from "./model.js";
import { EditorSession } from "./editor/session.js";
import {
  renderElementActionBar,
  renderElementActionMenu,
} from "./editor/element-actions.js";
import { PreviewController } from "./editor/preview.js";
import { renderStatusView, sendButtonHint } from "./editor/status-view.js";
import { renderHeader } from "./editor/header-view.js";
import {
  markDocumentDirty,
  syncDocumentHistoryControls,
} from "./editor/document-indicators.js";
import { renderTagOptions, resolveTagName } from "./editor/tag-selector.js";
import {
  renderPanelToggle,
  workspaceStickyOffsets,
} from "./editor/workspace-controls.js";
import {
  completeLoadingStep,
  createLoadingSteps,
  renderLoadingContent,
} from "./editor/loading-view.js";
import {
  renderIconChoices as renderIconChoicesMarkup,
  renderIconGlyph,
} from "./editor/icon-picker.js";
import {
  persistDrafts as persistStoredDrafts,
  restoreStoredDrafts as restoreDraftDocuments,
} from "./editor/draft-store.js";
import {
  entityName as resolveEntityName,
  entityValue as resolveEntityValue,
  firstNumericSensorEntity,
  filterEntities,
  listSupportedEntities,
  renderEntityPreview as renderEntityPreviewMarkup,
} from "./editor/entity-library.js";
import {
  configureBoundEntityPicker,
  configureLibraryEntityPicker,
  replaceEntityPickerElements,
} from "./editor/entity-pickers.js";
import { defaultEntityIcon } from "./editor/entity-icons.js";
import {
  renderTemplateControls,
  renderTemplateParts,
} from "./editor/template-controls.js";
import {
  createDefaultSensorTemplate,
  outputType as getSensorOutputType,
  sensorType as getSensorType,
  templateCompatibility as getTemplateCompatibility,
  templateTypes as getTemplateTypes,
  substituteTemplateTokens,
} from "./editor/sensor-templates.js";
import {
  handleLayerListClick,
  renderLayerRows,
} from "./editor/inspector/layers.js";
import { renderSpecEditorSections } from "./editor/inspector/spec-sections.js";
import { renderStateIconRows } from "./editor/inspector/state-icons.js";
import { renderSpecPalette } from "./editor/inspector/spec-palette.js";
import { renderOptionalProperties } from "./editor/inspector/optional-properties.js";
import { renderTextAlignmentControls } from "./editor/inspector/text-alignment.js";
import { renderWeatherControls } from "./editor/inspector/weather-controls.js";
import { renderLegacyElementProperties } from "./editor/inspector/legacy-properties.js";
import { buildSensorOptions } from "./editor/inspector/sensor-options.js";
import {
  beginTextEdit as beginCanvasTextEdit,
  finishTextEdit as finishCanvasTextEdit,
  handleKey as handleCanvasKey,
  handlePointer as handleCanvasPointer,
} from "./editor/canvas/interactions.js";
import { renderSensorContent } from "./editor/canvas/sensor-content.js";
import {
  renderAlignmentGuides,
  renderLayerImageMarkup,
  resolveLayerLabel,
  renderLayerMarkup,
  renderSelectionMarkup,
  renderStageMarkup,
} from "./editor/canvas/view.js";
import {
  alignmentGuides as calculateAlignmentGuides,
  adoptLayerRecords,
  clampMoved as clampMovedGeometry,
  clampResized as clampResizedGeometry,
  contextMenuPosition as calculateContextMenuPosition,
  createLayerRecords,
  elementShape,
  fitZoom as calculateFitZoom,
  moveBound as isMoveBound,
  selectionOverlayGeometry as calculateSelectionOverlayGeometry,
  staggerElement as calculateStaggeredElement,
  visibleBounds as calculateVisibleBounds,
} from "./editor/canvas/geometry.js";
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
const icon = materialIcon;
// Settings the inspector leaves unset until asked: blank means imagespec's default.
const optionalProperties = new Set([
  "valign",
  "fit",
  "max_lines",
  "min_font_size",
  "padding",
  "line_spacing",
  "font",
  "line_width",
  "radius",
  "stroke_width",
  "rotate",
  "direction",
  "thickness",
]);
// Whole-number ranges the schema accepts, kept when a value is typed.
const propertyRanges = {
  max_lines: [1, 20],
  min_font_size: [1, 200],
  padding: [0, 100],
  line_spacing: [0, 100],
  line_width: [1, 20],
  radius: [0, 200],
  stroke_width: [0, 20],
  thickness: [1, 100],
};
const shapeTypes = [
  "rectangle",
  "rounded_rectangle",
  "ellipse",
  "triangle",
  "line",
];
const toolIcon = materialIcon;
let fontsLoading;
// Started at import so the download overlaps the panel's other requests; a
// failure is forgotten so that Retry downloads the fonts again.
function loadFonts() {
  fontsLoading ||= Promise.all(
    [
      ["LabelMDI", "materialdesignicons-webfont.ttf"],
      ["LabelText", "NotoSansKR-Regular.ttf"],
    ].map(([family, file]) =>
      new FontFace(family, `url(/ble_esl_designer_fonts/${file})`)
        .load()
        .then((font) => document.fonts.add(font)),
    ),
  ).catch((error) => {
    fontsLoading = undefined;
    throw error;
  });
  return fontsLoading;
}
loadFonts().catch(() => {});
const loadingStyle = `.loading{display:flex;flex-direction:column;align-items:center;gap:12px;padding:64px 24px;color:var(--secondary-text-color,#637083)}.loading p{margin:0}.loading progress{width:min(360px,80%);height:8px;accent-color:#166d75}.loading .error{color:#c33}@keyframes spin{to{transform:rotate(360deg)}}.spinning ha-icon{animation:spin 1s linear infinite}`;
const style = `
.mdi{font-family:LabelMDI;line-height:1;display:inline-block;font-weight:normal;font-style:normal}.icon-popover{margin-top:8px}.icon-popover .icon-picker{margin-top:8px}.icon-choice{display:flex;align-items:center;gap:8px;width:100%;text-align:left}.toolbar .icon-button{border:1px solid var(--divider-color,#cbd3de)}:host{display:block;color:var(--primary-text-color,#18232f);background:var(--primary-background-color,#f5f7fa);font:14px system-ui;height:100%;overflow:auto}*{box-sizing:border-box}header{display:flex;align-items:center;gap:14px;box-sizing:border-box;min-height:var(--header-height,56px);padding:0 12px 0 24px;background:var(--card-background-color,white);border-bottom:1px solid var(--divider-color,#e0e5eb)}h1{font-size:20px;font-weight:400;margin:0}header span{color:var(--secondary-text-color,#637083)}.version{display:inline-flex;align-items:center;font-size:12px;font-weight:600;color:var(--secondary-text-color,#64748b);background:var(--secondary-background-color,#f1f5f9);padding:2px 7px;border-radius:9999px;line-height:1.3;border:1px solid var(--divider-color,#dde3e8)}button,input,select,textarea{font:inherit;color:inherit;background:var(--card-background-color,white);border:1px solid var(--divider-color,#cbd3de);border-radius:6px;padding:8px}button{cursor:pointer}button:hover{border-color:#257d86}button:disabled{opacity:.45;cursor:default}button.primary{background:#166d75;color:white;border-color:#166d75}button:focus-visible,input:focus-visible,select:focus-visible,.el:focus-visible{outline:2px solid #167c88;outline-offset:2px}.toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:14px 24px}.toolbar select{max-width:360px}
.toolbar select,.toolbar button,.library select,.library button{box-sizing:border-box;min-height:38px}.toolbar select,.library select{appearance:none;-webkit-appearance:none;padding-right:30px;background-image:linear-gradient(45deg,transparent 50%,currentColor 50%),linear-gradient(135deg,currentColor 50%,transparent 50%);background-position:calc(100% - 17px) 50%,calc(100% - 12px) 50%;background-size:5px 5px,5px 5px;background-repeat:no-repeat}.toolbar button.icon-button,.library button.icon-button{width:38px;height:38px}.template-start{display:grid;gap:8px;margin-bottom:12px}.template-hint{font-size:12px;line-height:1.4;color:var(--secondary-text-color,#637083);margin:0}.template-start[hidden]{display:none}.editor-bar{display:flex;align-items:center;gap:12px;padding:0 24px 12px}.editor-bar .spacer{flex:1}.icon-button{display:inline-flex;align-items:center;justify-content:center;width:38px;height:38px;padding:7px;border:0;background:transparent}.icon-button[aria-expanded="true"]{background:var(--secondary-background-color,#e9eff2)}.icon-button.danger:hover{color:#c33;background:#c331}.context-menu{position:fixed;z-index:1000;width:220px;padding:6px;background:var(--card-background-color,white);box-shadow:0 5px 24px #0003;border:1px solid var(--divider-color,#ddd);border-radius:8px}.context-menu button{display:flex;align-items:center;gap:10px;width:100%;text-align:left;border:0}.context-menu kbd{margin-left:auto}.delete-handle{position:absolute;right:0;top:-24px;width:24px;height:24px;display:flex;align-items:center;justify-content:center;padding:2px;border:1px solid #16838c;color:#b33;background:var(--card-background-color,white);z-index:5;border-radius:4px}.delete-handle svg{width:18px;height:18px}.context-menu kbd{float:right;font-size:11px;color:var(--secondary-text-color,#637083)}.template-controls{display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:0 24px 14px}.template-controls input[type="number"]{width:75px}.tabs{display:flex;gap:4px;margin-left:auto}.tabs button[aria-pressed="true"]{background:#166d75;color:white}.tile-icon{position:absolute;left:4px;top:10px;width:36px;height:36px;display:flex;align-items:center;justify-content:center}.tile-copy{margin-left:48px;padding:6px 0}.tile-copy .value{font-size:18px}.el ha-icon{--mdc-icon-size:32px}.el.icon-content ha-icon{--mdc-icon-size:inherit}.state-rules{margin:0}.template-note{margin:0 24px 12px}.picker{display:flex;gap:5px;flex-wrap:wrap}.swatch{width:28px;height:28px;padding:0;background:var(--swatch);border:1px solid #888;border-radius:50%}.swatch[aria-pressed="true"]{outline:2px solid #16838c;outline-offset:2px}.align-button{width:32px;height:32px;padding:5px}.align-button[aria-pressed="true"]{background:#16838c22;border-color:#16838c}.align-button svg{width:20px;height:20px}.icon-picker{display:grid;grid-template-columns:repeat(4,1fr);gap:4px;max-height:200px;overflow:auto}.icon-picker button{padding:6px}.icon-picker ha-icon{--mdc-icon-size:24px}.state-rules input{width:100%}.muted.help{display:none}h2{font-size:15px;margin:0 0 14px}p{line-height:1.5}.muted{color:var(--secondary-text-color,#637083);font-size:12px}.entity-preview{margin:12px 0 20px}.entity-state{display:flex;align-items:center;gap:10px;padding:10px;border:1px solid var(--divider-color,#ddd);border-radius:8px}.entity-state .state-copy{flex:1;min-width:0}.entity-state .state-name{font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.entity-state .state-value{font-size:18px;margin-top:4px}.entity-state ha-state-icon{--mdc-icon-size:28px}.entity-state button{flex:none}ha-entity-picker{display:block;width:100%;margin-bottom:12px}.entity{display:block;text-align:left;width:100%;margin:5px 0}.entity small{display:block;color:var(--secondary-text-color,#637083);font-size:11px;overflow:hidden;text-overflow:ellipsis}.entity[draggable]{cursor:grab}.tools{display:flex;flex-wrap:wrap;gap:6px}.stage{position:relative;transform-origin:top left;background:white;color:black;box-shadow:0 8px 24px #15293825;outline:1px solid #c5ced9;touch-action:none}.el{position:absolute;overflow:visible;cursor:move;outline:1px dashed transparent;touch-action:none;user-select:none}.el{pointer-events:none}.el .content{pointer-events:none}.hit-area{position:absolute;pointer-events:auto}.el:hover .hit-area{outline:1px dashed #1c8990}.el.editing .content{pointer-events:auto}.el.editing .hit-area{pointer-events:none}.el.selected{outline:1px solid #16838c}.el .content{height:100%;overflow:hidden;font-family:LabelText, sans-serif}.el.editing .content{visibility:visible!important;-webkit-user-select:text;user-select:text;cursor:text;white-space:pre-wrap;outline:0}.el.rendered .content{visibility:hidden}.layer-preview{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;image-rendering:pixelated}.el.editing .layer-preview,.stage.exact-mode .layer-preview{display:none}.label{font-size:12px;height:18px;white-space:nowrap;overflow:hidden}.value{white-space:nowrap;overflow:hidden}.handle{position:absolute;right:-3px;bottom:-3px;width:6px;height:6px;background:#16838c;cursor:nwse-resize;z-index:3}.exact{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;image-rendering:pixelated}.stage.exact-mode .content{visibility:hidden}.stage.exact-mode .el{background:transparent!important}.stage.exact-mode .el.selected{z-index:100}.status{min-height:28px;padding:0 24px 12px;color:var(--secondary-text-color,#637083)}.status.toasting{visibility:hidden}.toast{position:fixed;left:12px;right:12px;bottom:calc(16px + var(--toast-offset,0px));margin-inline:auto;width:fit-content;max-width:640px;z-index:60;display:flex;align-items:center;gap:8px;box-sizing:border-box;padding:10px 14px;border:1px solid var(--divider-color,#cbd3de);border-radius:8px;background:var(--card-background-color,white);color:var(--primary-text-color,#18232f);box-shadow:0 5px 24px #0003}.toast.error{border-color:#c33}.toast button{flex:none;padding:0 8px;line-height:20px}.toast.busy::before{content:"";flex:none;width:14px;height:14px;border:2px solid currentColor;border-right-color:transparent;border-radius:50%;animation:spin .8s linear infinite}.error{color:#c33}.props{display:grid;grid-template-columns:1fr 1fr;gap:9px}.props label{font-size:12px;display:flex;flex-direction:column;gap:5px}.props label.check{flex-direction:row;align-items:center}.props .wide{grid-column:1/-1}.props input,.props select,.props textarea{width:100%;min-width:0}.check{display:flex;align-items:center;gap:7px;margin:12px 0}.check input{width:auto}.layers{margin-top:16px;max-height:260px;overflow:auto}.layer-row{display:flex;align-items:center;gap:4px;margin:4px 0}.layer-row .layer{flex:1;min-width:0;margin:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.layer-row .icon-button{flex:none;width:32px;height:32px;padding:4px}.layer-row .icon-button svg{width:18px;height:18px}.layer{display:block;width:100%;text-align:left;margin:4px 0}.layer.active{border-color:#16838c}.side-column{display:flex;flex-direction:column;gap:18px}.side-column .layers{margin-top:0}.footer-tools{display:flex;flex-wrap:wrap;gap:6px;margin-top:14px}@media(max-width:1050px){.props{grid-template-columns:repeat(4,1fr)}}.element-actions{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}.element-actions .icon-button{border:1px solid var(--divider-color,#cbd3de);border-radius:6px}@media(pointer:coarse),(max-width:650px){.toolbar select,.toolbar button,.library select,.library button{min-height:40px}.toolbar button.icon-button,.library button.icon-button,.element-actions .icon-button,.layer-row .icon-button{width:40px;height:40px;min-height:40px}.tabs button{min-height:40px}.toolbar [data-action="zoom-in"],.toolbar [data-action="zoom-out"]{min-width:40px}.layer-row .layer{min-height:40px}}@media(max-width:650px){.toolbar,.editor-bar,.template-controls{padding:12px}header{flex-wrap:wrap;padding:4px 12px}header span{display:none}.entities{height:150px}.props{grid-template-columns:1fr 1fr}}
`;

// In the manager, the bars are siblings of the scrolling content. This also
// keeps the scrollbar below the header instead of running through it.
const managedStyle = `
.editor-content{display:contents}
:host([managed]){display:flex;flex-direction:column;min-height:0;overflow:hidden}
:host([managed]) header,:host([managed]) .toolbar,:host([managed]) .template-controls{position:static;flex:none}
:host([managed]) ::slotted(.editor-nav){display:flex;flex:none}
:host([managed]) .editor-content{display:block;flex:1;min-height:0;overflow:auto;overscroll-behavior:contain}
@media(max-width:650px){:host([managed]) header{flex-wrap:nowrap;min-height:48px;padding:0 12px}:host([managed]) header ha-menu-button,:host([managed]) header h1,:host([managed]) header .version{display:none}:host([managed]) .tabs{margin-left:0;flex:1}:host([managed]) .tabs button{flex:1}}
`;

// HA tears the panel down on in-app navigation, which beforeunload never sees,
// so unsaved designs are parked here for the rest of the browser session.
export class BleEslDesigner extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.tags = [];
    // Shown instead of the editor until the first boot() has its data.
    this.loading = {
      error: null,
      steps: createLoadingSteps(),
    };
    this.ready = false;
    this.readyPromise = new Promise((resolve) => (this.resolveReady = resolve));
    this.refreshing = false;
    this.session = new EditorSession(emptyDocument());
    this.zoom = 1;
    this.zoomMode = "fit";
    this.resizeObserver = new ResizeObserver(() => {
      this.fitPreview();
      this.stickyOffsets();
    });
    this.search = "";
    this.libraryEntity = "";
    this.status = "";
    this.notice = null;
    this.errorSource = null;
    this.preview = null;
    this.layerPreviews = {};
    this._automationPreviewVariables = null;
    this.specAdvancedOpen = false;
    this.busy = false;
    this.pendingUploads = new Set();
    this.drafts = new Map();
    this.libraryOpen = true;
    this.inspectorOpen = true;
    this.templates = {};
    this.icons = {};
    this.templateDrafts = new Map();
    this.sampleEntity = "";
    this.mode = "display";
    this.templateKey = "output:numeric";
    this.previewController = new PreviewController({
      request: () => this.previewRequest(),
      captureContext: () => this.documentSessionContext(),
      isValid: (context, sequence) =>
        sequence === this.previewController.sequence &&
        this.isConnected &&
        !this.gesture &&
        this.isDocumentSessionCurrent(context),
      onResult: (result) => this.applyPreviewResult(result),
      onError: (error) => this.report(error, "preview"),
    });
    this.shadowRoot.addEventListener("contextmenu", (event) =>
      this.contextMenu(event),
    );
    this.shadowRoot.addEventListener("pointerdown", (event) => {
      if (!event.target.closest(".context-menu")) this.closeContextMenu();
    });
    this.shadowRoot.addEventListener("click", (event) => this.click(event));
    this.shadowRoot.addEventListener("change", (event) => this.change(event));
    this.shadowRoot.addEventListener("input", (event) => this.input(event));
    this.shadowRoot.addEventListener("focusout", (event) => {
      this.typingProperty = null;
      if (event.target.dataset.editText) this.finishTextEdit();
    });
    this.shadowRoot.addEventListener("keydown", (event) => this.key(event));
    this.shadowRoot.addEventListener("pointerdown", (event) =>
      this.pointer(event),
    );
    this.shadowRoot.addEventListener("dragstart", (event) => {
      const button = event.target.closest("[data-entity]");
      if (button)
        event.dataTransfer.setData("text/plain", button.dataset.entity);
    });
    this.shadowRoot.addEventListener("dragover", (event) => {
      if (event.target.closest(".stage")) event.preventDefault();
    });
    this.shadowRoot.addEventListener("drop", (event) => this.drop(event));
  }
  // Keep the existing manager and host surface stable while EditorSession
  // becomes the single owner of active document state.
  get document() {
    return this.session.document;
  }
  set document(value) {
    this.session.document = value;
  }
  get selected() {
    return this.session.selected;
  }
  set selected(value) {
    this.session.selected = value;
    this._selection = new Set(value ? [value] : []);
  }
  get selectedIds() {
    const ids = this._selection?.has(this.selected)
      ? this._selection
      : new Set(this.selected ? [this.selected] : []);
    return new Set(
      this.document.elements.filter((e) => ids.has(e.id)).map((e) => e.id),
    );
  }
  selectIds(ids, primary = this.selected) {
    this._selection = new Set(ids);
    this.session.selected = this._selection.has(primary)
      ? primary
      : [...this._selection].at(-1) || null;
  }
  toggleSelection(id) {
    const ids = this.selectedIds;
    if (ids.has(id)) ids.delete(id);
    else ids.add(id);
    this.selectIds(ids, id);
  }
  get selectedElements() {
    return this.document.elements.filter((e) => this.selectedIds.has(e.id));
  }
  beginMarquee(event) {
    beginMarquee(this, event);
  }
  get undoStack() {
    return this.session.undoStack;
  }
  set undoStack(value) {
    this.session.undoStack = value;
  }
  get redoStack() {
    return this.session.redoStack;
  }
  set redoStack(value) {
    this.session.redoStack = value;
  }
  get dirty() {
    return this.session.dirty;
  }
  set dirty(value) {
    this.session.markDirty(value);
  }
  set panel(value) {
    this._panelInfo = value;
    if (this.started) this.render();
  }
  captureEditorSession() {
    this.gestureFinish?.(false);
    this.finishTextEdit();
    const copyMap = (items) =>
      new Map([...items].map(([key, value]) => [key, clone(value)]));
    return {
      tag: this.tag ? clone(this.tag) : null,
      document: clone(this.document),
      selected: this.selected,
      dirty: this.dirty,
      undoStack: clone(this.undoStack),
      redoStack: clone(this.redoStack),
      drafts: copyMap(this.drafts),
      mode: this.mode,
      displaySession: this.displaySession ? clone(this.displaySession) : null,
      templateKey: this.templateKey,
      templateDrafts: copyMap(this.templateDrafts),
      templateName: this.templateName,
      templateSensorType: this.templateSensorType,
      sampleEntity: this.sampleEntity,
      zoom: this.zoom,
      zoomMode: this.zoomMode,
      libraryOpen: this.libraryOpen,
      inspectorOpen: this.inspectorOpen,
      search: this.search,
    };
  }
  documentSessionContext() {
    return {
      tag: this.tag,
      entryId: this.tag?.entry_id,
      document: this.document,
      token: this._automationSessionToken,
      mode: this.mode,
      cancelled: false,
    };
  }
  isDocumentSessionCurrent(context) {
    return (
      this.isDocumentSessionOwner(context) && this.document === context.document
    );
  }
  isDocumentSessionOwner(context) {
    return (
      context &&
      !context.cancelled &&
      this.tag === context.tag &&
      this.tag?.entry_id === context.entryId &&
      this._automationSessionToken === context.token &&
      this.mode === context.mode
    );
  }
  beginAutomationSession(token) {
    this._previewParametersDialog?.close(null);
    this._automationSessionToken = token;
    this._automationPreviewVariables = null;
    this._automationReturnState = null;
    this._automationSessionPending = true;
    this._automationSaveMode = false;
    this.busy = true;
    this.gestureFinish?.(false);
    if (this.started) this.render();
  }
  setAutomationReturnState(state, token) {
    if (token === this._automationSessionToken)
      this._automationReturnState = state;
  }
  prepareAutomationPayload(
    payload,
    background,
    entryId,
    previewVariables = {},
  ) {
    return this.api("import_payload", {
      entry_id: entryId,
      payload,
      background,
      existing: 0,
      preview_variables: previewVariables,
    });
  }
  applyAutomationPayload(
    result,
    payload,
    background,
    allowEmpty,
    entryId,
    token,
    previewVariables = {},
  ) {
    if (
      token !== this._automationSessionToken ||
      !this._automationSessionPending ||
      this.tag?.entry_id !== entryId
    )
      return false;
    if (result.issues.length || (!allowEmpty && result.different_pixels !== 0))
      return false;
    const document = clone(this.document);
    document.elements = result.elements;
    document.background = palette(this.tag.colors).includes(background)
      ? background
      : "white";
    this.session.reset(document, {
      selected: result.elements.at(-1)?.id || null,
    });
    this.busy = false;
    this._automationSessionPending = false;
    this._automationSaveMode = true;
    this._automationPreviewVariables = clone(previewVariables);
    this._automationBackground = this.document.background;
    this.preview = null;
    this.layerPreviews = {};
    this.layerBounds = {};
    this.layerOffsets = {};
    this.layerRecords = [];
    this.templateEntities = [];
    this.invalidatePreview();
    this.render();
    this.queuePreview();
    return true;
  }
  restoreEditorSession(state, token) {
    if (token !== this._automationSessionToken) return false;
    this._previewParametersDialog?.close(null);
    this._automationSessionToken = null;
    this._automationSessionPending = false;
    this._automationSaveMode = false;
    this._automationPreviewVariables = null;
    this._automationBackground = null;
    this._automationReturnState = null;
    this.busy = false;
    this.converting = false;
    this.convertRun = (this.convertRun || 0) + 1;
    this.invalidatePreview();
    this.gestureCancel?.();
    this.editingTextId = null;
    this.typingProperty = null;
    if (!state) {
      this.session.markDirty(false);
      this.session.clearHistory();
      if (this.ready && this.tag) {
        this.drafts.delete(this.tag.entry_id);
        this.load(
          this.tags.find((item) => item.entry_id === this.tag.entry_id) ||
            this.tag,
        );
      }
      return true;
    }
    const tag = state.tag?.entry_id
      ? this.tags.find((item) => item.entry_id === state.tag.entry_id) ||
        state.tag
      : state.tag;
    this.tag = tag;
    this.session.restore({
      document: clone(state.document),
      selected: state.selected,
      dirty: state.dirty,
      undoStack: clone(state.undoStack),
      redoStack: clone(state.redoStack),
    });
    this.drafts = new Map(
      [...state.drafts].map(([key, value]) => [key, clone(value)]),
    );
    this.mode = state.mode;
    this.displaySession = state.displaySession
      ? clone(state.displaySession)
      : null;
    if (this.displaySession?.tag?.entry_id)
      this.displaySession.tag =
        this.tags.find(
          (item) => item.entry_id === this.displaySession.tag.entry_id,
        ) || this.displaySession.tag;
    this.templateKey = state.templateKey;
    this.templateDrafts = new Map(
      [...state.templateDrafts].map(([key, value]) => [key, clone(value)]),
    );
    this.templateName = state.templateName;
    this.templateSensorType = state.templateSensorType;
    this.sampleEntity = state.sampleEntity;
    this.zoom = state.zoom;
    this.zoomMode = state.zoomMode;
    this.libraryOpen = state.libraryOpen;
    this.inspectorOpen = state.inspectorOpen;
    this.search = state.search;
    this.preview = null;
    this.layerPreviews = {};
    this.error = false;
    this.errorSource = null;
    this.status = "Ready";
    if (this.started) {
      this.render();
      this.queuePreview();
    }
    return true;
  }
  set hass(value) {
    const previous = this._hass;
    this._hass = value;
    if (language(previous) !== language(value) && this.started) {
      // Partially typed JSON/numbers live in controls until they are valid.
      // Preserve that raw draft without putting invalid values into the spec.
      const specDrafts = [
        ...this.shadowRoot.querySelectorAll("[data-spec]"),
      ].map((input) => ({
        path: input.dataset.spec,
        value: input.value,
        invalid: input.getAttribute("aria-invalid") === "true",
        focused: input === this.shadowRoot.activeElement,
        start: input.selectionStart,
        end: input.selectionEnd,
      }));
      rerenderWithDialogs(this.shadowRoot, value, () => this.render());
      for (const draft of specDrafts) {
        const input = this.shadowRoot.querySelector(
          `[data-spec="${CSS.escape(draft.path)}"]`,
        );
        if (!input) continue;
        input.value = draft.value;
        if (draft.invalid && this.element?.type === "imagespec")
          applySpecInput(
            input,
            clone(this.element.spec),
            this.specDefinition(this.element),
            value,
          );
        if (draft.focused) {
          input.focus({ preventScroll: true });
          if (typeof draft.start === "number")
            input.setSelectionRange(draft.start, draft.end);
        }
      }
      for (const dialog of document.querySelectorAll("ble-esl-import-dialog"))
        if (dialog.panel === this) dialog.updateHass(value);
      for (const dialog of document.querySelectorAll("ble-esl-template-dialog"))
        if (dialog.panel === this) dialog.updateHass(value);
    }
    this.renderEntityPreview();
    this.shadowRoot
      .querySelector("ble-esl-component-editor")
      ?.updateHass(value);
    this.shadowRoot.querySelectorAll("ha-entity-picker").forEach((picker) => {
      picker.hass = value;
    });
    if (this.isConnected && !this.started) this.boot();
    else if (
      this.tag &&
      !this.gesture &&
      ((this.templateEntities || []).some(
        (id) => previous?.states[id] !== value.states[id],
      ) ||
        (this.mode === "template" &&
          previous?.states[this.sampleEntity] !==
            value.states[this.sampleEntity]) ||
        this.document.elements.some(
          (element) =>
            element.entity_id &&
            previous?.states[element.entity_id] !==
              value.states[element.entity_id],
        ))
    ) {
      this.drawStage();
      this.queuePreview();
    }
  }
  get hass() {
    return this._hass;
  }
  connectedCallback() {
    this.beforeUnload = (event) => {
      // Work set aside by switching between Display and Sensor templates counts.
      const saved = this._automationReturnState;
      if (
        this.dirty ||
        this.drafts.size ||
        (this.mode === "template" && this.displaySession?.dirty) ||
        [...this.templateDrafts].some(
          ([key, draft]) =>
            draft.dirty &&
            !(this.mode === "template" && key === this.templateKey),
        ) ||
        saved?.dirty ||
        saved?.drafts?.size ||
        (saved?.mode === "template" && saved?.displaySession?.dirty) ||
        [...(saved?.templateDrafts || [])].some(([, draft]) => draft.dirty)
      )
        event.preventDefault();
    };
    window.addEventListener("beforeunload", this.beforeUnload);
    this.render();
    if (this.hass && !this.started) this.boot();
  }
  // Unsaved ordinary designs, including the one being edited right now.
  draftDocuments() {
    const source = this._automationSessionToken
      ? this._automationReturnState
      : this;
    const drafts = new Map(source?.drafts || []);
    // In Sensor tile styles the tag design is parked in displaySession.
    const current =
      source?.mode === "template"
        ? source.displaySession
        : {
            tag: source?.tag,
            document: source?.document,
            dirty: source?.dirty,
          };
    if (current?.tag && current.dirty)
      drafts.set(current.tag.entry_id, current.document);
    return drafts;
  }
  hasDraft(entryId) {
    return this.draftDocuments().has(entryId);
  }
  persistDrafts() {
    persistStoredDrafts(this.draftDocuments(), this.tags);
  }
  // Only drafts for a tag of the same size come back; the rest are dropped.
  restoreStoredDrafts() {
    restoreDraftDocuments(this.drafts, this.tags);
  }
  disconnectedCallback() {
    // An instance that never loaded must not wipe drafts it never restored.
    if (this.ready) this.persistDrafts();
    clearTimeout(this.noticeTimer);
    window.removeEventListener("beforeunload", this.beforeUnload);
    this.invalidatePreview();
    this.gestureCancel?.();
    this.gesture = null;
    this.resizeObserver.disconnect();
  }
  async boot() {
    this.started = true;
    const initial = !this.ready;
    // A request that outlives a failed attempt must not touch the next one.
    const run = (this.bootRun = (this.bootRun || 0) + 1);
    if (initial) {
      this.loading = {
        error: null,
        steps: createLoadingSteps(),
      };
    } else {
      this.refreshing = true;
      this.error = false;
      this.status = "Refreshing tags…";
    }
    this.render();
    try {
      // The tag list must not wait for HA's lazily loaded entity picker:
      // in Safari the card helpers that load it may never settle.
      if (!customElements.get("ha-entity-picker") && !this.pickerPending) {
        // Once per panel: boot() runs again on "Refresh tags".
        this.pickerPending = true;
        loadEntityPicker();
        customElements.whenDefined("ha-entity-picker").then(() => {
          this.pickerPending = false;
          if (this.isConnected) this.upgradeEntityPickers();
        });
      }
      const step = (key, promise) =>
        Promise.resolve(promise).then((value) => {
          if (run === this.bootRun) this.stepDone(key);
          return value;
        });
      // Fonts and icons are fetched once; Refresh only re-reads the tags.
      const [, icons, templates, specs, tags] = await Promise.all([
        step("fonts", initial && loadFonts()),
        step(
          "icons",
          initial &&
            fetch(new URL("./icons.json", import.meta.url)).then((response) =>
              response.json(),
            ),
        ),
        step("templates", this.api("templates")),
        step("specs", this.api("specs")),
        step("tags", this.api("list")),
      ]);
      if (icons) this.icons = icons;
      this.templates = templates;
      this.specs = specs;
      this.tags = tags;
      this.restoreStoredDrafts();
      this.mode = "display";
      // Reveal the editor before load(): it renders.
      this.ready = true;
      this.resolveReady();
      this.loading = null;
      this.refreshing = false;
      // Stay on the tag being edited: load() files an unsaved design under
      // the tag it is leaving, so this.tag must still be that one.
      const tag =
        this.tags.find((item) => item.entry_id === this.tag?.entry_id) ||
        this.tags[0];
      if (tag) {
        this._automationBootLoadAllowed = Boolean(
          this._automationSessionPending,
        );
        this.load(tag);
        this._automationBootLoadAllowed = false;
      } else {
        this.tag = undefined;
        this.status =
          "Add a BLE ESL device in Settings → Devices & services first.";
        this.render();
      }
    } catch (error) {
      if (this.loading) {
        this.loading.error = error.message || String(error);
        this.resolveReady();
        this.render();
      } else {
        this.refreshing = false;
        this.report(error);
        this.render();
      }
    }
  }
  stepDone(key) {
    if (!completeLoadingStep(this.loading, key)) return;
    const node = this.shadowRoot.querySelector(".loading");
    if (node) node.innerHTML = this.loadingInner();
  }
  loadingInner() {
    return renderLoadingContent(this.loading, {
      translate: (key, values) => t(this.hass, key, values),
      escapeHtml: esc,
    });
  }
  headerHtml() {
    const sessionLocked =
      this._automationSessionPending || this._automationSaveMode;
    const version =
      this._panelInfo?.config?.version ||
      import.meta.url.match(/\/ble_esl_designer\/([^/]+)\//)?.[1];
    return renderHeader({
      mode: this.mode,
      loading: this.loading,
      refreshing: this.refreshing,
      sessionLocked,
      version,
      translate: (key) => t(this.hass, key),
      escapeHtml: esc,
    });
  }
  renderLoading() {
    this.shadowRoot.innerHTML = `<style>${style} header{position:sticky;top:0;z-index:30} ${loadingStyle}${managedStyle}</style>${this.headerHtml()}<slot name="managed-navigation"></slot><div class="loading" role="status" aria-live="polite">${this.loadingInner()}</div>`;
    const menu = this.shadowRoot.querySelector("ha-menu-button");
    if (menu) {
      menu.hass = this.hass;
      menu.narrow = this.narrow;
    }
    // Every re-render of the error (e.g. the click handler's) keeps the focus.
    this.shadowRoot.querySelector(".loading button")?.focus();
  }
  async api(action, extra = {}) {
    const result = await this.hass.callWS({
      type: "ble_esl/designer",
      action,
      ...extra,
    });
    if (action === "save")
      this.dispatchEvent(
        new CustomEvent("design-saved", {
          detail: { entry_id: extra.entry_id, document: clone(result) },
          bubbles: true,
          composed: true,
        }),
      );
    return result;
  }
  load(tag) {
    if (
      this._automationSaveMode ||
      (this._automationSessionPending && !this._automationBootLoadAllowed)
    )
      return false;
    if (this.tag && this.dirty)
      this.drafts.set(this.tag.entry_id, clone(this.document));
    if (this.templateAutomation?.entryId !== tag.entry_id)
      this.templateAutomation = null;
    this.tag = tag;
    this.automationImportRun = (this.automationImportRun || 0) + 1;
    this.session.reset(
      clone(this.drafts.get(tag.entry_id) || tag.document || emptyDocument()),
      { dirty: this.drafts.has(tag.entry_id) },
    );
    this.preview = null;
    this.layerPreviews = {};
    this.error = false;
    this.status = tag.writable
      ? "Ready"
      : "Discovery only: preview is available; sending is not supported yet.";
    this.render();
    this.queuePreview();
  }
  checkpoint() {
    this.session.checkpoint();
    this.syncHistoryControls();
  }
  syncHistoryControls() {
    syncDocumentHistoryControls(this.shadowRoot, {
      undoCount: this.undoStack.length,
      redoCount: this.redoStack.length,
      busy: this.busy,
    });
  }
  // Without a full render: show that there is something to save, and that
  // the picture is no longer the exact render.
  markDirty() {
    markDocumentDirty(this.shadowRoot, {
      undoCount: this.undoStack.length,
      redoCount: this.redoStack.length,
      busy: this.busy,
      automationSaveMode: this._automationSaveMode,
      mode: this.mode,
      translate: (key) => t(this.hass, key),
      saveIcon: toolIcon("save"),
    });
  }
  edited(render = true) {
    this.session.markDirty();
    this.preview = null;
    this.invalidatePreview();
    if (render) this.render();
    else {
      this.drawStage();
      this.markDirty();
    }
    this.queuePreview();
  }
  // The user's alias for a tag (as the dashboard shows it), else the product title.
  tagName(tag) {
    const state = this.hass?.states?.[tag.entities?.alias];
    return resolveTagName(tag, state);
  }
  report(error, source = "operation") {
    this.status = errorText(
      this.hass,
      source === "preview" ? "Preview failed" : "Something went wrong",
      error,
    );
    this.error = true;
    this.errorSource = source;
    this.renderStatus();
  }
  // Why the Send button is off, or what it is doing; plain "Send to tag" otherwise.
  sendHint(tag) {
    return sendButtonHint({
      tag,
      busy: this.busy,
      status: this.status,
      translate: (message) => t(this.hass, message),
    });
  }
  renderStatus() {
    renderStatusView({
      root: this.shadowRoot,
      getState: () => ({
        status: this.status,
        error: this.error,
        errorSource: this.errorSource,
        notice: this.notice,
        busy: this.busy,
      }),
      noticeTimer: this.noticeTimer,
      translate: (key) => t(this.hass, key),
      setNoticeTimer: (timer) => (this.noticeTimer = timer),
      onNoticeTimeout: () => {
        this.notice = null;
        this.status = "Ready";
        this.renderStatus();
      },
    });
  }
  get element() {
    return this.document.elements.find(
      (element) => element.id === this.selected,
    );
  }
  entities() {
    return listSupportedEntities(this.hass?.states);
  }
  entityName(state) {
    return resolveEntityName(state, this.hass);
  }
  value(element) {
    return resolveEntityValue(element, this.hass, t(this.hass, "Unavailable"));
  }
  sensorType(state) {
    return getSensorType(state);
  }
  sampleState() {
    return this.hass.states[this.sampleEntity];
  }
  defaultTemplate() {
    return createDefaultSensorTemplate({ emptyDocument, newElement });
  }
  outputType(state) {
    return getSensorOutputType(state);
  }
  templateCompatibility(template, key) {
    return getTemplateCompatibility(template, key);
  }
  templateTypes() {
    return getTemplateTypes(this.templates, this.templateDrafts);
  }
  templateControls() {
    if (this.mode !== "template") return "";
    return renderTemplateControls({
      mode: this.mode,
      translate: (text, vars) => t(this.hass, text, vars),
      escapeHtml: esc,
      sampleOutput: this.outputType(this.sampleState()),
      templateTypes: this.templateTypes(),
      templates: this.templates,
      templateDrafts: this.templateDrafts,
      templateKey: this.templateKey,
      templateName: this.templateName,
      width: this.tag?.width,
      height: this.tag?.height,
    });
  }
  templateParts() {
    return renderTemplateParts({
      mode: this.mode,
      translate: (text) => t(this.hass, text),
    });
  }
  switchMode(mode) {
    // Automation edits are isolated display sessions; don't let the user
    // switch into template mode and later restore an imported draft as normal.
    if (
      mode === this.mode ||
      this.refreshing ||
      this._automationSessionPending ||
      this._automationSaveMode
    )
      return;
    if (mode === "template") {
      const active = this.session.capture();
      this.displaySession = {
        tag: this.tag,
        document: active.document,
        selected: active.selected,
        dirty: active.dirty,
        undo: active.undoStack,
        redo: active.redoStack,
      };
      this.mode = mode;
      this.loadTemplate(this.templateKey);
    } else {
      this.rememberTemplate();
      this.mode = mode;
      const session = this.displaySession;
      this.tag = session.tag;
      this.session.restore({
        document: session.document,
        selected: session.selected,
        dirty: session.dirty,
        undoStack: session.undo,
        redoStack: session.redo,
      });
      this.preview = null;
      this.layerPreviews = {};
      this.render();
      this.queuePreview();
    }
  }
  rememberTemplate() {
    if (this.mode === "template" && this.tag)
      this.templateDrafts.set(this.templateKey, {
        width: this.tag.width,
        height: this.tag.height,
        document: clone(this.document),
        name: this.templateName,
        sensor_type: this.templateSensorType,
        dirty: this.dirty,
      });
  }
  loadTemplate(key) {
    if (this.tag?.title === this.templateKey) this.rememberTemplate();
    this.templateKey = key;
    const template = this.templateDrafts.get(key) ||
      this.templates[key] || {
        width: 140,
        height: 60,
        document: this.defaultTemplate(),
        dirty: false,
      };
    this.tag = {
      width: template.width,
      height: template.height,
      colors: "BWRY",
      title: key,
      writable: false,
    };
    this.layerPreviews = {};
    this.templateName =
      template.name ||
      (key.startsWith("output:")
        ? t(this.hass, "{type} style", { type: key.split(":")[1] })
        : key.replace(":", " · "));
    this.templateSensorType =
      template.sensor_type || key.split(":").slice(0, 2).join(":");
    const document = clone(template.document);
    if (
      !this.templates[key] &&
      !this.templateDrafts.has(key) &&
      /^(binary_sensor|weather):|^output:(binary|weather)/.test(key)
    )
      document.elements = document.elements.filter(
        (el) => el.text !== "{{state}} {{unit}}",
      );
    this.session.reset(document, { dirty: !!template.dirty });
    this.sampleEntity =
      this.entities().find(
        (state) =>
          this.outputType(state) === this.templateCompatibility(template, key),
      )?.entity_id ||
      this.entities().find(
        (state) =>
          state.entity_id.split(".")[0] ===
          this.templateSensorType.split(":")[0],
      )?.entity_id ||
      "";
    this.preview = null;
    this.status = "";
    this.render();
    this.queuePreview();
  }
  createSensorTemplate() {
    if (this.refreshing) {
      // switchMode() would decline: put the picker back instead.
      this.render();
      return;
    }
    const element = this.element;
    const state = this.hass.states[element.entity_id];
    const type = "output:" + this.outputType(state);
    const sample = element.entity_id;
    const source =
      this.templates[element.template === "auto" ? type : element.template];
    const initial = clone(source?.document || this.defaultTemplate());
    if (!source && /^output:(binary|weather)/.test(type))
      initial.elements = initial.elements.filter(
        (el) => el.text !== "{{state}} {{unit}}",
      );
    this.switchMode("template");
    const key = type + ":custom:" + createId();
    this.templateDrafts.set(key, {
      width: source?.width || 140,
      height: source?.height || 60,
      name: t(this.hass, "{name} style", { name: this.entityName(state) }),
      sensor_type: type,
      document: initial,
      dirty: true,
    });
    this.loadTemplate(key);
    this.sampleEntity = sample;
    this.createdForElement = element.id;
    this.render();
    this.queuePreview();
  }
  previewRequest() {
    if (this.mode === "template")
      return this.api("preview_template", {
        template: {
          width: this.tag.width,
          height: this.tag.height,
          name: this.templateName,
          sensor_type: this.templateSensorType,
          document: clone(this.document),
        },
        entity_id: this.sampleEntity,
      });
    return this.api("preview", {
      entry_id: this.tag.entry_id,
      document: clone(this.document),
      ...(this._automationSaveMode
        ? { preview_variables: clone(this._automationPreviewVariables || {}) }
        : {}),
    });
  }
  async requestPreviewVariables(variables, missingName = null) {
    if (
      !this._automationSessionToken ||
      (!this._automationSaveMode && !this._automationSessionPending)
    )
      return null;
    const context = this.documentSessionContext();
    const modal = document.createElement("ble-esl-preview-parameters-dialog");
    this._previewParametersDialog = modal;
    this.shadowRoot.append(modal);
    const value = await modal.open(this, variables || {}, missingName);
    if (this._previewParametersDialog === modal)
      this._previewParametersDialog = null;
    if (
      value === null ||
      !this.isDocumentSessionOwner(context) ||
      this.document !== context.document ||
      (!this._automationSaveMode && !this._automationSessionPending)
    )
      return null;
    return clone(value);
  }
  invalidatePreviewForParameters() {
    this.preview = null;
    this.layerPreviews = {};
    this.layerBounds = {};
    this.layerOffsets = {};
    this.layerRecords = [];
    this.templateEntities = [];
    this.invalidatePreview();
    this.render();
    if (this._automationSaveMode) this.queuePreview();
  }
  async editAutomationPreviewVariables() {
    if (!this._automationSaveMode || this._automationSessionPending) return;
    const context = this.documentSessionContext();
    const value = await this.requestPreviewVariables(
      this._automationPreviewVariables || {},
    );
    if (!value || !this.isDocumentSessionCurrent(context)) return;
    this._automationPreviewVariables = clone(value);
    this.invalidatePreviewForParameters();
  }
  tokenText(text) {
    if (this.mode !== "template") return text;
    const state = this.sampleState();
    const values = {
      name: state ? this.entityName(state) : "Name",
      state: state?.state || "State",
      unit: state?.attributes.unit_of_measurement || "",
      icon: state?.attributes.icon || this.defaultIcon(state),
    };
    return substituteTemplateTokens(text, values);
  }
  defaultIcon(state) {
    return defaultEntityIcon(state);
  }
  iconGlyph(name, size = 24) {
    return renderIconGlyph(name, size, this.icons, esc);
  }
  renderIconChoices(search = "") {
    const grid = this.shadowRoot.querySelector(".icon-picker");
    if (grid) grid.innerHTML = renderIconChoicesMarkup(this.icons, search, esc);
  }
  colorPicker(key, value, label) {
    return renderColorPicker({
      key,
      value,
      label,
      colors: palette(this.tag.colors),
      translate: (message) => t(this.hass, message),
    });
  }
  panelMenu(action, open, label, id) {
    return renderPanelToggle({
      action,
      open,
      label,
      id,
      translate: (message, values) => t(this.hass, message, values),
      iconMarkup: icon("menu"),
    });
  }
  render() {
    if (this.loading) {
      this.resizeObserver.disconnect();
      this.renderLoading();
      return;
    }
    this.finishTextEdit();
    const activeControl = this.shadowRoot.activeElement;
    let focusSelector = null;
    if (activeControl?.id) focusSelector = `#${CSS.escape(activeControl.id)}`;
    else if (activeControl?.classList?.contains("el"))
      focusSelector = `.el[data-id="${CSS.escape(activeControl.dataset.id)}"]`;
    else if (activeControl?.classList?.contains("stage"))
      focusSelector = ".stage";
    else if (activeControl?.attributes) {
      const identity = [...activeControl.attributes]
        .filter((attribute) => attribute.name.startsWith("data-"))
        .map(
          (attribute) => `[${attribute.name}="${CSS.escape(attribute.value)}"]`,
        )
        .join("");
      if (identity)
        focusSelector = `${activeControl.tagName.toLowerCase()}${identity}`;
      else if (activeControl.matches("summary"))
        focusSelector = activeControl.closest(".tips")
          ? ".tips > summary"
          : activeControl.closest(".advanced")
            ? ".advanced > summary"
            : null;
    }
    // Rebuilding the tree resets every scroll position; keep the canvas,
    // the layer list and the inspector where the user left them.
    const scrolled = [".canvas-wrap", ".layers", ".inspector"].map(
      (selector) => {
        const node = this.shadowRoot.querySelector(selector);
        return [selector, node?.scrollLeft, node?.scrollTop];
      },
    );
    const tag = this.tag,
      element = this.element,
      sessionLocked =
        this._automationSessionPending || this._automationSaveMode;
    const workspaceMarkup = tag
      ? renderWorkspace({
          tag,
          mode: this.mode,
          libraryOpen: this.libraryOpen,
          inspectorOpen: this.inspectorOpen,
          sessionLocked,
          preview: Boolean(this.preview),
          zoom: this.zoom,
          background: this.document.background,
          sampleEntity: this.sampleEntity,
          tipsOpen: this.tipsOpen,
          hasElement: Boolean(element),
          translate: (key) => t(this.hass, key),
          escapeHtml: esc,
          toggles: {
            libraryOpen: this.panelMenu(
              "toggle-library",
              true,
              "entities",
              "library",
            ),
            libraryClosed: this.panelMenu(
              "toggle-library",
              false,
              "entities",
              "library",
            ),
            inspectorOpen: this.panelMenu(
              "toggle-inspector",
              true,
              "properties",
              "inspector",
            ),
            inspectorClosed: this.panelMenu(
              "toggle-inspector",
              false,
              "properties",
              "inspector",
            ),
          },
          libraryContent: `${this.templateParts()}<div ${this.mode === "template" ? "hidden" : ""}><ha-entity-picker id="entity-picker"></ha-entity-picker><div class="entity-preview"></div></div><h2>${t(this.hass, "Components")}</h2><p class="hint">${t(this.hass, "Use the icon buttons to add text, a shape, an icon or an image. Add component offers sensors, bars, gauges and more.")}</p><button data-action="add-component">${t(this.hass, "＋ Add component")}</button><div class="tools"><button class="icon-button" data-add="text" aria-label="${t(this.hass, "Add text")}" title="${t(this.hass, "Text")}">${toolIcon("text")}</button><button class="icon-button" data-add="rectangle" aria-label="${t(this.hass, "Add shape")}" title="${t(this.hass, "Shape")}">${toolIcon("shape")}</button><button class="icon-button" data-add="icon" aria-label="${t(this.hass, "Add icon")}" title="${t(this.hass, "Icon")}">${toolIcon("icon")}</button><button class="icon-button" data-add="image" aria-label="${t(this.hass, "Add image")}" title="${t(this.hass, "Image")}">${toolIcon("image")}</button></div>${this.specPalette()}<div class="footer-tools"><button data-action="yaml" ${this.mode === "template" ? "hidden" : ""}>${t(this.hass, "Payload YAML")}</button><button data-action="import-yaml" ${this.mode === "template" ? "hidden" : ""}>${t(this.hass, "Import YAML")}</button><button data-action="export">${t(this.hass, "Export JSON")}</button><button data-action="import" ${this.mode === "template" ? "hidden" : ""}>${t(this.hass, "Import JSON")}</button><input id="file" type="file" accept="application/json" hidden></div>`,
          elementActions: element ? this.elementActions() : "",
          propertyContent: `${element && this.selectedElements.length === 1 && element.type !== "imagespec" ? `<button class="wide" data-action="configure-component">${t(this.hass, "Configure")}</button>${this.mode === "template" ? "" : `<button class="wide" data-action="convert" title="${t(this.hass, "Turn this into plain imagespec elements to edit field by field; a sensor's value becomes a template")}">${t(this.hass, "Convert to elements")}</button>`}` : ""}${this.properties(element)}`,
          layerRows: renderLayerRows({
            elements: this.document.elements,
            selected: this.selected,
            selectedIds: this.selectedIds,
            layerLabel: (item) => this.layerLabel(item),
            t: (key, values) => t(this.hass, key, values),
            esc,
            icon,
            toolIcon,
          }),
        })
      : "";
    this.shadowRoot.innerHTML = `<style>${style} .el.selected{outline:none!important;border:none!important} ${TOOLBAR_STYLE} ${WORKSPACE_STYLE} [hidden]{display:none!important} .spec-group{border:1px solid var(--divider-color,#cbd3de);border-radius:6px;margin:0;padding:6px 8px} .spec-group legend{font-size:12px} .spec-doc{display:block;font-size:12px} .props textarea[data-json]{font:11px ui-monospace,Menlo,Consolas,monospace} [aria-invalid="true"]{border-color:#c33!important} .field-error{display:block;color:#c33;font-size:12px;margin-top:2px} .group-title{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--secondary-text-color,#637083);margin:12px 0 0;font-weight:600} .advanced summary{cursor:pointer;margin:10px 0 6px;color:var(--secondary-text-color,#637083)} .swatch{box-shadow:0 0 0 1px var(--secondary-text-color,#888)} .dirty-badge{font-size:12px;color:#b45309;white-space:nowrap} .status.error{display:flex;align-items:center;gap:8px;color:#c33} .status button{padding:0 8px;line-height:20px} .hint{font-size:12px;line-height:1.4;color:var(--secondary-text-color,#637083);margin:4px 0 8px} .layer-row.hidden-layer .layer{opacity:.5;text-decoration:line-through} .el.hidden-el{opacity:.3} ${loadingStyle}${managedStyle}</style>${this.headerHtml()}<slot name="managed-navigation"></slot>${this.templateControls()}${renderToolbar(
      {
        tag,
        mode: this.mode,
        sessionLocked,
        refreshing: this.refreshing,
        busy: this.busy,
        status: this.status,
        dirty: this.dirty,
        automationSessionPending: this._automationSessionPending,
        automationSaveMode: this._automationSaveMode,
        showHiddenIcons: Boolean(this.showHiddenIcons),
        undoAvailable: this.undoStack.length > 0,
        redoAvailable: this.redoStack.length > 0,
        zoomMode: this.zoomMode,
        zoom: this.zoom,
        tags: this.tags,
        translate: (key, values) => t(this.hass, key, values),
        escapeHtml: esc,
        icon: toolIcon,
        tagName: (item) => this.tagName(item),
        renderTagOptions,
        sendHint: (item) => this.sendHint(item),
      },
    )}<div class="editor-content"><div class="status" role="status"></div>${workspaceMarkup}</div>`;
    const saveButton = this.shadowRoot.querySelector('[data-action="save"]');
    if (this._automationSaveMode && saveButton) {
      const label = t(this.hass, "Save to automation");
      saveButton.textContent = label;
      saveButton.classList.add("automation-save");
      saveButton.setAttribute("aria-label", label);
      saveButton.title = label;
    }
    this.renderEntities();
    this.bindEntityPickers();
    this.shadowRoot
      .querySelector("details.advanced")
      ?.addEventListener("toggle", (event) => {
        this.advancedOpen = event.target.open;
      });
    this.shadowRoot
      .querySelector("details.spec-advanced")
      ?.addEventListener("toggle", (event) => {
        this.specAdvancedOpen = event.target.open;
      });
    this.shadowRoot
      .querySelector("details.tips")
      ?.addEventListener("toggle", (event) => {
        this.tipsOpen = event.target.open;
      });
    this.drawStage();
    this.renderStatus();
    this.resizeObserver.disconnect();
    const previewWindow = this.shadowRoot.querySelector(".canvas-wrap");
    if (previewWindow) {
      this.resizeObserver.observe(previewWindow);
      this.fitPreview();
    }
    // The bars wrap with the width: follow their real height.
    // and the panel itself, as the bars turn static on a short window.
    for (const bar of this.shadowRoot.querySelectorAll("header, .toolbar"))
      this.resizeObserver.observe(bar);
    this.resizeObserver.observe(this);
    this.stickyOffsets();
    let focusTarget = focusSelector
      ? this.shadowRoot.querySelector(focusSelector)
      : null;
    if (focusTarget?.closest("#library") && !this.libraryOpen)
      focusTarget = this.shadowRoot.querySelector(
        '.preview-card [data-action="toggle-library"]',
      );
    if (focusTarget?.closest("#inspector") && !this.inspectorOpen)
      focusTarget = this.shadowRoot.querySelector(
        '.preview-card [data-action="toggle-inspector"]',
      );
    if (!focusTarget?.closest("[hidden]"))
      focusTarget?.focus({ preventScroll: true });
    const menu = this.shadowRoot.querySelector("ha-menu-button");
    if (menu) {
      menu.hass = this.hass;
      menu.narrow = this.narrow;
    }
    if (this.yamlExport) {
      // render() rebuilds the shadow tree, so the dialog opens after it.
      const dialog = document.createElement("ble-esl-yaml-dialog");
      this.shadowRoot.append(dialog);
      dialog.open(
        this.yamlExport,
        () => {
          this.render();
          this.shadowRoot.querySelector('[data-action="yaml"]')?.focus();
        },
        this.hass,
        async (document) => {
          const result = await this.api("save", {
            entry_id: this.tag.entry_id,
            document,
          });
          this.adoptDocument(result);
          this.dirty = false;
          return result;
        },
      );
      this.yamlExport = null;
    }
    if (this.busy) {
      this.shadowRoot.querySelector(".workspace")?.setAttribute("inert", "");
      this.shadowRoot
        .querySelectorAll("button")
        .forEach((button) => (button.disabled = true));
      this.shadowRoot
        .querySelectorAll("input, select, textarea, ha-entity-picker")
        .forEach((control) => {
          if ("disabled" in control) control.disabled = true;
          control.setAttribute("aria-disabled", "true");
        });
    }
    for (const [selector, left, top] of scrolled) {
      const node = this.shadowRoot.querySelector(selector);
      if (node && top !== undefined) {
        node.scrollLeft = left;
        node.scrollTop = top;
      }
    }
    this.dispatchEvent(
      new CustomEvent("designer-context-changed", {
        bubbles: true,
        composed: true,
        detail: {
          tag: this.tag,
          mode: this.mode,
          automationSaveMode: this._automationSaveMode,
        },
      }),
    );
  }
  openComponentEditor(element) {
    const modal = document.createElement("ble-esl-component-editor");
    this.shadowRoot.append(modal);
    modal.open(this, element);
  }
  // The toolbar sticks under the header, and a control scrolled into view must
  // land below both bars instead of behind them.
  stickyOffsets() {
    const header = this.shadowRoot.querySelector("header"),
      toolbar = this.shadowRoot.querySelector(".toolbar");
    if (!header || !toolbar) return;
    const fixed =
      !this.hasAttribute("managed") &&
      getComputedStyle(header).position === "sticky";
    const offsets = workspaceStickyOffsets({
      headerHeight: header.offsetHeight,
      toolbarHeight: toolbar.offsetHeight,
      fixed,
    });
    this.style.setProperty("--bar-top", offsets.barTop);
    this.style.scrollPaddingTop = offsets.scrollPaddingTop;
  }
  fitPreview() {
    if (this.zoomMode !== "fit" || !this.tag) return;
    const previewWindow = this.shadowRoot.querySelector(".canvas-wrap");
    if (!previewWindow) return;
    this.zoom = calculateFitZoom({
      viewportWidth: previewWindow.clientWidth,
      viewportHeight: previewWindow.clientHeight,
      tagWidth: this.tag.width,
      tagHeight: this.tag.height,
    });
    const stage = this.shadowRoot.querySelector(".stage"),
      space = this.shadowRoot.querySelector(".stage-space");
    stage.style.transform = `scale(${this.zoom})`;
    space.style.width = `${this.tag.width * this.zoom}px`;
    space.style.height = `${this.tag.height * this.zoom}px`;
    this.updateSelectionOverlay();
    const option = this.shadowRoot.querySelector('#zoom option[value="fit"]');
    if (option)
      option.textContent = `${t(this.hass, "Fit")} (${Math.round(this.zoom * 100)}%)`;
  }
  stateIconRows(element) {
    return renderStateIconRows({
      element,
      sample: this.sampleState(),
      outputType: (state) => this.outputType(state),
      defaultIcon: (state) => this.defaultIcon(state),
      iconGlyph: (name) => this.iconGlyph(name),
      translate: (message, values) => t(this.hass, message, values),
      escapeHtml: esc,
    });
  }
  // The layer of an element that draws beyond its frame is cropped to what it
  // drew: it sits at an offset from the frame and follows the frame's scale.
  layerImage(element, src) {
    return renderLayerImageMarkup({
      element,
      src,
      offset:
        this.showHiddenIcons && this.layerPreviews._ghosts?.[element.id]
          ? this.layerPreviews._ghost_offsets?.[element.id]
          : this.layerOffsets?.[element.id],
      bounds:
        this.showHiddenIcons && this.layerPreviews._ghosts?.[element.id]
          ? this.layerPreviews._ghost_bounds?.[element.id]
          : this.layerBounds?.[element.id],
      record: this.layerRecords?.[element.id],
    });
  }
  layerLabel(item) {
    return resolveLayerLabel(item, {
      state: this.hass?.states[item.entity_id],
      entityName: (state) => this.entityName(state),
      specLabel,
    });
  }
  specDefinition(element) {
    return this.specs?.types.find((type) => type.type === element.spec?.type);
  }
  // Every imagespec element, by category, to add beside the quick buttons.
  specPalette() {
    return renderSpecPalette({
      specs: this.specs,
      mode: this.mode,
      translate: (message) => t(this.hass, message),
      escapeHtml: esc,
    });
  }
  addSpec(type) {
    const definition = this.specs.types.find((item) => item.type === type);
    if (!definition) return;
    this.checkpoint();
    const element = newSpecElement(definition, newElement, this.tag);
    this.stagger(element);
    if (type === "plot") {
      // The example names a sensor nobody has; start from one that records numbers.
      const sensor = firstNumericSensorEntity(this.entities());
      if (sensor) element.spec.data[0].entity = sensor.entity_id;
    }
    this.document.elements.push(element);
    this.selected = element.id;
    this.edited();
    this.focusElement();
  }
  // The selected element as imagespec elements, in its place, saying how
  // exactly they draw what it did.
  async convertSelected(context = this.documentSessionContext()) {
    const element = this.element;
    // One at a time: the element has to be where the request left it.
    if (!element || this.converting) return;
    this.converting = true;
    const run = (this.convertRun = (this.convertRun || 0) + 1);
    try {
      await this.convertElement(element, context);
    } finally {
      if (run === this.convertRun) this.converting = false;
    }
  }
  async convertElement(element, context = this.documentSessionContext()) {
    if (!this.isDocumentSessionCurrent(context)) return;
    const originalElement = JSON.stringify(element);
    this.status = "Converting…";
    this.renderStatus();
    const result = await this.api("convert", {
      entry_id: context.entryId,
      document: context.document,
      element_id: element.id,
    });
    if (!this.isDocumentSessionCurrent(context)) return;
    const index = this.document.elements.findIndex(
      (el) => el.id === element.id,
    );
    if (
      index < 0 ||
      JSON.stringify(this.document.elements[index]) !== originalElement
    ) {
      // Deleted or undone while the server worked: nothing to replace.
      this.status = "The element changed; nothing was converted";
      this.renderStatus();
      return;
    }
    if (!result.elements.length) {
      this.error = true;
      this.errorSource = "operation";
      this.status = result.issues.join("; ") || "Nothing to convert";
      this.renderStatus();
      return;
    }
    this.checkpoint();
    this.document.elements.splice(index, 1, ...result.elements);
    this.selected = result.elements[0].id;
    this.error = false;
    this.errorSource = null;
    const skipped = result.issues.length
      ? {
          key: "; {count} not converted",
          values: { count: result.issues.length },
        }
      : "";
    this.status = {
      key:
        result.different_pixels === 0
          ? "Converted to {count} elements, drawn exactly as before{skipped}"
          : "Converted to {count} elements; {pixels} pixels differ from before{skipped}",
      values: {
        count: result.elements.length,
        pixels: result.different_pixels ?? "?",
        skipped,
      },
    };
    this.edited();
  }
  // A pasted payload as elements, added to the display or replacing it.
  async importYaml(text, replace, context = this.documentSessionContext()) {
    if (!this.isDocumentSessionCurrent(context)) return { stale: true };
    const result = await this.api("import_yaml", {
      entry_id: context.entryId,
      text,
      // A display holds a limited number of elements; the server keeps to it.
      existing: replace ? 0 : context.document.elements.length,
      preview_variables: this._automationSaveMode
        ? clone(this._automationPreviewVariables || {})
        : {},
    });
    if (!this.isDocumentSessionCurrent(context)) return { stale: true };
    if (result.missing_parameters?.length)
      throw new Error(
        t(this.hass, "Import needs a preview parameter: {name}", {
          name: result.missing_parameters[0],
        }),
      );
    if (result.elements.length) {
      this.checkpoint();
      if (replace) {
        this.document.elements = [];
        if (palette(this.tag.colors).includes(result.background))
          this.document.background = result.background;
      }
      this.document.elements.push(...result.elements);
      this.selected = result.elements.at(-1).id;
      this.edited();
    }
    return result;
  }
  // A ready-made design, added like an imported payload. The automation it
  // suggests (its triggers) is kept for Create automation.
  async applyDesignTemplate(id, parameters, replace, context) {
    if (!this.isDocumentSessionCurrent(context)) return { stale: true };
    const result = await this.api("apply_design_template", {
      entry_id: context.entryId,
      template_id: id,
      parameters,
      existing: replace ? 0 : context.document.elements.length,
    });
    if (!this.isDocumentSessionCurrent(context)) return { stale: true };
    if (result.elements.length) {
      this.checkpoint();
      if (replace) {
        this.document.elements = [];
        if (palette(this.tag.colors).includes(result.background))
          this.document.background = result.background;
      }
      this.document.elements.push(...result.elements);
      this.selected = result.elements.at(-1).id;
      this.templateAutomation = result.template.automation
        ? {
            entryId: context.entryId,
            defaults: result.template.automation,
            // The triggers belong to this design: once its elements are gone
            // (undo, replace, import, delete) they are no longer offered.
            elementIds: result.elements.map((element) => element.id),
          }
        : null;
      this.edited();
    }
    return result;
  }
  createAutomationFromTemplate() {
    this.shadowRoot.querySelector('[data-action="create-automation"]')?.click();
  }
  // Undo steps only for edits that took: half-typed input changes nothing.
  pushUndo(snapshot) {
    this.session.pushUndo(snapshot);
    this.syncHistoryControls();
  }
  specInput(input) {
    const element = this.element;
    if (element?.type !== "imagespec") return;
    const first = this.typingProperty !== input,
      before = first ? clone(this.document) : null;
    if (
      !applySpecInput(
        input,
        element.spec,
        this.specDefinition(element),
        this.hass,
      )
    )
      return;
    if (first) {
      this.pushUndo(before);
      this.typingProperty = input;
    }
    this.edited(false);
    this.markDirty();
  }
  // Optional settings of the older kinds: left blank they keep imagespec's
  // default, so a design that never sets one draws as before.
  extraProperties(element) {
    return renderOptionalProperties(element, {
      translate: (message) => t(this.hass, message),
      escapeHtml: esc,
      colorPicker: (key, value, label) => this.colorPicker(key, value, label),
      ditherMethods: this.specs?.dither_methods,
    });
  }
  properties(element) {
    if (this.selectedElements.length > 1)
      return sharedProperties(this, (message) => t(this.hass, message), esc);
    if (!element)
      return `<p class="muted wide">${t(this.hass, "Click a block to move, resize, or bind it to an entity.")}</p>${this.mode === "display" && !this._automationSaveMode ? `<h3 class="wide group-title">${t(this.hass, "Display")}</h3>${this.colorPicker("display-background", this.document.background, t(this.hass, "Background"))}` : ""}`;
    if (element.type === "imagespec") {
      const field = (key, label, type = "text") =>
        `<label class="">${label}<input data-property="${key}" type="${type}" value="${esc(element[key] ?? "")}" ${type === "number" ? 'step="1"' : ""}></label>`;
      const position = `<h3 class="wide group-title">${t(this.hass, "Position & size (px)")}</h3>${[
        "x",
        "y",
        "width",
        "height",
      ]
        .map((key) => field(key, key[0].toUpperCase() + key.slice(1), "number"))
        .join("")}`;
      return this.specEditorSections(
        specEditorHtml(
          this.specDefinition(element),
          element.spec,
          this.tag.colors,
          this.specs?.dither_methods || [],
          this.hass,
        ),
        position +
          renderElementRotation(element, (message) => t(this.hass, message)),
      );
    }

    const sensorOptions = buildSensorOptions(element, {
      mode: this.mode,
      templateKey: this.templateKey,
      templates: this.templates,
      templateDrafts: this.templateDrafts,
      templateSensorType: this.templateSensorType,
      state:
        element.type === "sensor" ? this.hass.states[element.entity_id] : null,
      entities:
        this.mode === "template" && element.type !== "icon"
          ? this.entities()
          : [],
      outputType: (state) => this.outputType(state),
      templateCompatibility: (template, key) =>
        this.templateCompatibility(template, key),
      sensorType: (state) => this.sensorType(state),
      outputStyleLabel: (type) => t(this.hass, "{type} style", { type }),
    });

    const translate = (message, values) => t(this.hass, message, values);
    return renderLegacyElementProperties(element, {
      translate,
      escapeHtml: esc,
      colorPicker: (key, value, label) => this.colorPicker(key, value, label),
      iconGlyph: (name, size) => this.iconGlyph(name, size),
      tokenText: (value) => this.tokenText(value),
      stateIconRows: (item) => this.stateIconRows(item),
      extraProperties: (item) => this.extraProperties(item),
      textAlignmentControls: (item) =>
        renderTextAlignmentControls(item, {
          translate: (message) => translate(message),
          escapeHtml: esc,
        }),
      weatherControls: (item) =>
        renderWeatherControls(item, {
          translate: (message) => translate(message),
        }),
      shapeTypes,
      mode: this.mode,
      advancedOpen: this.advancedOpen,
      sensorOptions,
    });
  }
  specEditorSections(markup, position) {
    return renderSpecEditorSections({
      markup,
      position,
      translate: (message) => t(this.hass, message),
      advancedOpen: this.specAdvancedOpen,
    });
  }
  // Pickers created before HA defined the element keep their properties as
  // plain fields that can shadow the upgraded element's accessors. Swap in
  // fresh ones without a full render(), which would end inline editing and
  // drop an open dialog or menu.
  upgradeEntityPickers() {
    replaceEntityPickerElements(this.shadowRoot, () =>
      document.createElement("ha-entity-picker"),
    );
    this.renderEntities();
    this.bindEntityPickers();
    this.shadowRoot.querySelector("ble-esl-component-editor")?.upgradeSource();
  }
  renderEntities() {
    const picker = this.shadowRoot.querySelector("#entity-picker");
    if (!picker) return;
    configureLibraryEntityPicker(picker, {
      hass: this.hass,
      value: this.libraryEntity,
      label: t(this.hass, "Sensor"),
      searchLabel: t(this.hass, "Search sensors"),
      onValueChanged: (id) => {
        if (!id) {
          this.libraryEntity = "";
          this.renderEntityPreview();
          return;
        }
        this.libraryEntity = id;
        this.add("sensor", this.hass.states[id]);
      },
    });
    this.renderEntityPreview();
  }
  bindEntityPickers() {
    const configure = (picker, value, label) =>
      configureBoundEntityPicker(picker, {
        hass: this.hass,
        value,
        label,
        includeDomains:
          this.shadowRoot.querySelector("#entity-picker").includeDomains,
        onValueChanged: (next) =>
          this.change({
            target: { id: picker.id, dataset: picker.dataset, value: next },
          }),
      });
    const bound = this.shadowRoot.querySelector(
      'ha-entity-picker[data-property="entity_id"]',
    );
    if (bound)
      configure(bound, this.element.entity_id, t(this.hass, "Bound entity"));
    const sample = this.shadowRoot.querySelector("#template-sample");
    if (sample)
      configure(sample, this.sampleEntity, t(this.hass, "Sample sensor"));
  }
  renderEntityPreview() {
    const node = this.shadowRoot.querySelector(".entity-preview");
    const state = this.hass?.states[this.libraryEntity];
    if (!node) return;
    node.innerHTML = renderEntityPreviewMarkup({
      state,
      name: state ? this.entityName(state) : "",
      value: state ? this.hass.formatEntityState?.(state) || state.state : "",
      addLabel: t(this.hass, "Add selected sensor"),
      escapeHtml: esc,
    });
    const icon = node.querySelector("ha-state-icon");
    if (icon) {
      icon.hass = this.hass;
      icon.stateObj = state;
    }
  }
  filteredEntities() {
    return filterEntities(this.entities(), this.search, (state) =>
      this.entityName(state),
    );
  }
  sensorContent(element, state, label) {
    let key = element.template || "auto";
    if (key === "auto" && state) {
      key = this.sensorType(state);
      if (!this.templates[key])
        key = state.entity_id.split(".")[0] + ":default";
    }
    const template = this.templates[key];
    let templateValues;
    if (template && state) {
      templateValues = {
        name: label,
        state:
          element.decimals === undefined ||
          ["unknown", "unavailable"].includes(state.state)
            ? state.state
            : Number(state.state).toFixed(element.decimals),
        unit: element.show_unit
          ? state.attributes.unit_of_measurement || ""
          : "",
        icon: this.defaultIcon(state),
      };
      return renderSensorContent({
        element,
        stateValue: state.state,
        label,
        template,
        templateValues,
        escapeHtml: esc,
        iconGlyph: (name, size) => this.iconGlyph(name, size),
      });
    }

    const weatherNumber =
      state?.entity_id.startsWith("weather.") &&
      element.weather_field &&
      element.weather_field !== "condition";
    const visual =
      state?.entity_id.startsWith("binary_sensor.") ||
      (state?.entity_id.startsWith("weather.") && !weatherNumber);
    const value = weatherNumber
      ? String(state.attributes[element.weather_field] ?? "") +
        (element.show_unit && state.attributes[element.weather_field + "_unit"]
          ? " " + state.attributes[element.weather_field + "_unit"]
          : "")
      : this.value(element);
    const iconName = weatherNumber
      ? this.defaultIcon({
          entity_id: "sensor.weather",
          state: value,
          attributes: { device_class: element.weather_field },
        })
      : this.defaultIcon(state);
    return renderSensorContent({
      element,
      stateValue: state?.state,
      label,
      template: undefined,
      iconName,
      value,
      visual,
      escapeHtml: esc,
      iconGlyph: (name, size) => this.iconGlyph(name, size),
    });
  }
  drawStage() {
    const stage = this.shadowRoot.querySelector(".stage");
    if (!stage || this.editingTextId) return;
    const focused = this.shadowRoot.activeElement,
      focusedId = focused?.dataset.id,
      focusedStage = focused?.classList?.contains("stage");
    stage.classList.toggle("exact-mode", !!this.preview);
    const layers = this.document.elements.map((element, index) => {
      const state = this.hass?.states[element.entity_id];
      const label =
        element.type === "imagespec"
          ? this.layerLabel(element)
          : element.label ||
            (state ? this.entityName(state) : element.entity_id);
      let content = "";
      if (element.type === "sensor")
        content = this.sensorContent(element, state, label);
      if (element.type === "image" && element.image)
        content = `<img src="${esc(element.image)}" alt="" style="width:100%;height:100%;object-fit:${element.image_fit === "stretch" ? "fill" : element.image_fit === "fill" ? "cover" : "contain"}${element.circle ? ";border-radius:50%" : ""}${element.rotate ? `;transform:rotate(${Number(element.rotate) || 0}deg)` : ""}">`;
      if (element.type === "text")
        content = esc(this.tokenText(element.text)).replace(/\n/g, "<br>");
      if (element.type === "icon")
        content = this.iconGlyph(
          this.tokenText(
            element.state_icons?.[this.sampleState()?.state] || element.icon,
          ),
          Math.min(element.width, element.height),
        );
      if (shapeTypes.includes(element.type)) {
        const hollow = element.type !== "line" && element.filled === false;
        const paint = hollow
          ? `fill="none" stroke="currentColor" stroke-width="${(element.line_width || 1) * 2}" vector-effect="non-scaling-stroke"`
          : 'fill="currentColor"';
        const radius =
          element.radius ?? Math.min(element.width, element.height) / 5;
        const shape =
          element.type === "triangle"
            ? `<polygon points="50,0 100,100 0,100" ${paint}/>`
            : element.type === "ellipse"
              ? `<ellipse cx="50" cy="50" rx="50" ry="50" ${paint}/>`
              : `<rect width="100" height="100" rx="${element.type === "rounded_rectangle" ? (radius / element.width) * 100 : 0}" ry="${element.type === "rounded_rectangle" ? (radius / element.height) * 100 : 0}" ${paint}/>`;
        content = `<svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">${shape}</svg>`;
      }
      const record = this.layerRecords?.[element.id];
      const stale =
        !record ||
        record.shape !== this.shape(element) ||
        record.size[0] !== element.width ||
        record.size[1] !== element.height;
      if (element.type === "imagespec" && stale)
        content = `<div role="status" aria-label="${t(this.hass, "Preview updating")}" title="${t(this.hass, "This element needs a renderer preview to show its current appearance")}" style="width:100%;height:100%;display:grid;place-items:center;overflow:hidden;border:1px dashed #16838c;background:repeating-linear-gradient(135deg,transparent 0 6px,#16838c12 6px 12px);color:var(--secondary-text-color,#637083);font:10px system-ui;text-align:center">${t(this.hass, "Preview updating…")}</div>`;
      const ghost =
        !stale &&
        this.showHiddenIcons &&
        this.layerPreviews._ghosts?.[element.id];
      const rendered =
        (this.gesture && element.type === "image") || stale
          ? undefined
          : ghost || this.layerPreviews[element.id];
      const visible = this.visibleBounds(element);
      const box = [0, 0, element.width, element.height];
      const hitBounds =
        visible === undefined ? box : (visible ?? (rendered ? null : box));
      return renderLayerMarkup({
        element,
        index,
        selected: this.selectedIds.has(element.id),
        rendered,
        ghost: Boolean(ghost),
        label,
        content,
        hitBounds,
        layerImage: rendered ? this.layerImage(element, rendered) : "",
        faded:
          this.mode === "template" &&
          element.state &&
          element.state !== this.sampleState()?.state,
        escape: esc,
      });
    });
    stage.innerHTML = renderStageMarkup({
      preview: this.preview,
      previewLabel: t(this.hass, "Exact rendered display"),
      layers,
      guides: this.alignmentGuidesMarkup(),
      selection: this.selectionMarkup(),
    });
    if (focusedId)
      stage
        .querySelector(`.el[data-id="${CSS.escape(focusedId)}"]`)
        ?.focus({ preventScroll: true });
    else if (focusedStage) stage.focus({ preventScroll: true });
    stage.querySelectorAll("ha-state-icon").forEach((icon) => {
      const element = this.document.elements.find(
        (el) => el.id === icon.closest("[data-id]").dataset.id,
      );
      icon.hass = this.hass;
      icon.stateObj = this.hass.states[element.entity_id];
    });
  }
  selectionMarkup() {
    const coarsePointer = window.matchMedia("(pointer: coarse)").matches;
    return this.selectedElements
      .map((element) =>
        renderSelectionMarkup({
          element,
          multiple: this.selectedElements.length > 1,
          geometry: calculateSelectionOverlayGeometry({
            element,
            visible: this.visibleBounds(element),
            zoom: this.zoom,
            coarsePointer,
          }),
          translate: (key, values) => t(this.hass, key, values),
          escape: esc,
          deleteIcon: icon("delete"),
        }),
      )
      .join("");
  }

  alignmentGuidesMarkup() {
    return renderAlignmentGuides(this.snapGuides);
  }
  alignmentGuides(element, resize) {
    return calculateAlignmentGuides({
      element,
      elements: this.document.elements,
      tag: this.tag,
      layerRecords: this.layerRecords,
      layerBounds: this.layerBounds,
      zoom: this.zoom,
      resize,
      snapTolerance: 6,
    });
  }
  updateSelectionOverlay() {
    for (const overlay of this.shadowRoot.querySelectorAll(".selection-box")) {
      const element = this.document.elements.find(
        (e) => e.id === overlay.dataset.id,
      );
      if (!element) continue;
      const geometry = calculateSelectionOverlayGeometry({
        element,
        visible: this.visibleBounds(element),
        zoom: this.zoom,
        coarsePointer: window.matchMedia("(pointer: coarse)").matches,
      });
      overlay.style.left = `${geometry.left}px`;
      overlay.style.top = `${geometry.top}px`;
      overlay.style.width = `${geometry.width}px`;
      overlay.style.height = `${geometry.height}px`;
      overlay.style.outlineWidth = `${1.5 / this.zoom}px`;
      for (const handle of overlay.querySelectorAll(".handle")) {
        const corner = handle.dataset.corner;
        handle.style.left = `${corner.endsWith("w") ? -geometry.handleSize : geometry.width}px`;
        handle.style.top = `${corner.startsWith("n") ? -geometry.handleSize : geometry.height}px`;
        handle.style.width = `${geometry.handleSize}px`;
        handle.style.height = `${geometry.handleSize}px`;
      }
      const moveTarget = overlay.querySelector(".move-handle");
      if (moveTarget) {
        moveTarget.style.left = `${geometry.width / 2 - geometry.handleSize / 2}px`;
        moveTarget.style.top = `${geometry.height / 2 - geometry.handleSize / 2}px`;
        moveTarget.style.width = `${geometry.handleSize}px`;
        moveTarget.style.height = `${geometry.handleSize}px`;
        moveTarget.style.display =
          Math.max(geometry.width, geometry.height) * this.zoom < 36
            ? "grid"
            : "none";
      }
      const trash = overlay.querySelector(".delete-handle");
      if (trash) trash.style.transform = `scale(${1 / this.zoom})`;
    }
  }
  // Content bounds come from the last render and are relative to the element.
  // Moving the element keeps them. Resizing it grows or shrinks them with the
  // frame, so a dragged handle stays under the pointer. Any other edit (font
  // size, text...) leaves them describing the old content, so the element's
  // frame stands in until the new preview arrives.
  shape(element) {
    return elementShape(element);
  }
  // The server returns the saved document with its defaults filled in. That
  // changes nothing on screen, so what the last render still describes stays.
  adoptDocument(saved) {
    const records = adoptLayerRecords({
      currentElements: this.document.elements,
      savedElements: saved.elements,
      layerRecords: this.layerRecords,
      hasVisibleBounds: (element) => this.visibleBounds(element) !== undefined,
    });
    this.document = saved;
    this.layerRecords = records;
  }
  renderRecords() {
    return createLayerRecords(this.document.elements);
  }
  // undefined: not known, use the frame. null: rendered with nothing visible.
  visibleBounds(element) {
    return calculateVisibleBounds(element, {
      record: this.layerRecords?.[element.id],
      layerBounds:
        this.showHiddenIcons && this.layerPreviews._ghosts?.[element.id]
          ? this.layerPreviews._ghost_bounds
          : this.layerBounds,
    });
  }
  // Clamp a moved element so what it draws, not just its frame, stays on the
  // label. With an anchor other than "lt" ("mm", "rm", ...) the ink sits at an
  // offset from the frame and can otherwise leave the label on one side while
  // not reaching the edge on the other.
  // `bound`: the element was on the label before, so one hanging off it stays put.
  // `visible` is the drawn area relative to the frame, measured before the move.
  clampMoved(element, bound, visible) {
    Object.assign(
      element,
      clampMovedGeometry(element, this.tag, bound, visible),
    );
    return element;
  }
  // Whether a move keeps the element on the label. Its frame may hang off the
  // label after an earlier clamped move while what it draws is still on it:
  // that one is bound as well, or its next move would not be clamped at all.
  moveBound(element, visible) {
    return isMoveBound(element, this.tag, visible);
  }
  // After a resize: trim the frame so the grown content stays on the label.
  clampResized(element) {
    Object.assign(
      element,
      clampResizedGeometry(element, {
        tag: this.tag,
        layerRecords: this.layerRecords,
        layerBounds: this.layerBounds,
      }),
    );
  }
  // A new element lands beside the ones already there, not exactly on them.
  stagger(element) {
    Object.assign(
      element,
      calculateStaggeredElement(element, this.document.elements, this.tag),
    );
  }
  add(type, entity, x, y) {
    this.checkpoint();
    const element = newElement(type, this.tag, entity);
    if (x !== undefined) {
      element.x = x;
      element.y = y;
      clampBox(element, this.tag);
    } else this.stagger(element);
    this.document.elements.push(element);
    this.selected = element.id;
    this.edited();
    this.focusElement();
  }
  focusElement() {
    this.shadowRoot
      .querySelector(this.selected ? `[data-id="${this.selected}"]` : ".stage")
      ?.focus({ preventScroll: true });
  }
  async click(event) {
    const button = event.target.closest("button");
    if (!button || this.busy) return;
    this.gestureFinish?.(false);
    this.closeContextMenu();
    if (["display-mode", "template-mode"].includes(button.dataset.action)) {
      this.switchMode(
        button.dataset.action === "template-mode" ? "template" : "display",
      );
      return;
    }
    if (button.dataset.action === "convert") {
      const context = this.documentSessionContext();
      try {
        await this.convertSelected(context);
      } catch (error) {
        if (this.isDocumentSessionCurrent(context)) this.report(error);
      }
      return;
    }
    if (button.dataset.action === "import-yaml") {
      // Outside the panel: a change to the display rebuilds the panel's tree.
      const dialog = document.createElement("ble-esl-import-dialog");
      document.body.append(dialog);
      dialog.open(
        this,
        () =>
          this.shadowRoot.querySelector('[data-action="import-yaml"]')?.focus(),
        this.documentSessionContext(),
      );
      return;
    }
    if (button.dataset.action === "design-templates") {
      const dialog = document.createElement("ble-esl-template-dialog");
      document.body.append(dialog);
      dialog.open(
        this,
        () =>
          this.shadowRoot
            .querySelector('[data-action="design-templates"]')
            ?.focus(),
        this.documentSessionContext(),
      );
      return;
    }
    if (button.dataset.action === "add-spec") {
      const type = this.shadowRoot.querySelector("#add-spec")?.value;
      if (type) this.addSpec(type);
      return;
    }
    if (button.dataset.action === "add-current-entity") {
      this.add("sensor", this.hass.states[this.libraryEntity]);
      return;
    }
    if (button.dataset.action === "add-icon-state") {
      const state = this.shadowRoot
        .querySelector("#new-icon-state")
        .value.trim();
      if (!state) return;
      this.checkpoint();
      this.element.state_icons ||= {};
      this.element.state_icons[state] = "{{icon}}";
      this.edited();
      return;
    }
    if (button.dataset.iconState !== undefined) {
      // A state row: choose its icon here instead of opening the editor.
      const popover = this.shadowRoot.querySelector(".icon-popover");
      this.iconMappingState = button.dataset.iconState;
      popover.hidden = false;
      this.renderIconChoices();
      popover.querySelector("#icon-search").focus();
      return;
    }
    if (
      ["add-component", "configure-component", "pick-icon"].includes(
        button.dataset.action,
      )
    ) {
      this.openComponentEditor(
        button.dataset.action === "add-component" ? null : this.element,
      );
      return;
    }
    if (button.dataset.icon) {
      this.checkpoint();
      if (this.iconMappingState !== undefined) {
        this.element.state_icons ||= {};
        this.element.state_icons[this.iconMappingState] = button.dataset.icon;
        this.element.state = "";
        this.iconMappingState = undefined;
      } else this.element.icon = button.dataset.icon;
      this.edited();
      return;
    }
    if (button.dataset.action === "add-state-icon") {
      this.add("icon");
      this.element.icon = "{{icon}}";
      this.edited();
      return;
    }
    if (button.dataset.pick) {
      this.checkpoint();
      if (button.dataset.pick === "display-background")
        this.document.background = button.dataset.value;
      else if (this.element)
        setSharedProperty(this, button.dataset.pick, button.dataset.value);
      this.edited();
      return;
    }
    if (button.dataset.token) {
      this.add("text");
      this.element.text = `{{${button.dataset.token}}}`;
      this.edited();
      this.focusElement();
      return;
    }
    if (
      ["duplicate", "delete", "back", "front", "center"].includes(
        button.dataset.action,
      )
    ) {
      this.transform(button.dataset.action);
      return;
    }
    if (
      ["toggle-library", "toggle-inspector"].includes(button.dataset.action)
    ) {
      if (button.dataset.action === "toggle-library")
        this.libraryOpen = !this.libraryOpen;
      else this.inspectorOpen = !this.inspectorOpen;
      this.render();
      return;
    }
    if (["zoom-in", "zoom-out", "fit"].includes(button.dataset.action)) {
      if (button.dataset.action === "fit") this.zoomMode = "fit";
      else {
        this.zoomMode = "manual";
        this.zoom = Math.max(
          0.1,
          Math.min(
            8,
            Math.round(
              this.zoom *
                (button.dataset.action === "zoom-in" ? 1.25 : 0.8) *
                100,
            ) / 100,
          ),
        );
      }
      this.render();
      return;
    }
    if (button.dataset.entity) {
      this.add("sensor", this.hass.states[button.dataset.entity]);
      return;
    }
    if (button.dataset.add) {
      this.add(button.dataset.add);
      return;
    }
    if (
      button.dataset.select &&
      (event.shiftKey || event.ctrlKey || event.metaKey)
    ) {
      this.toggleSelection(button.dataset.select);
      this.render();
      this.focusElement();
      return;
    }
    if (handleLayerListClick(this, button)) return;
    const action = button.dataset.action;
    if (action === "tag-orientation") {
      await this.setTagOrientation(Number(button.dataset.rotation));
      return;
    }
    if (action === "show-hidden-icons") {
      this.showHiddenIcons = !this.showHiddenIcons;
      button.setAttribute("aria-pressed", String(this.showHiddenIcons));
      this.drawStage();
      return;
    }
    if (action === "preview-variables") {
      this.editAutomationPreviewVariables();
      return;
    }
    if (action === "save" && this._automationSaveMode) {
      const sessionToken = this._automationSessionToken;
      const entryId = this.tag?.entry_id;
      try {
        this.gestureFinish?.(false);
        if (this.pendingUploads.size)
          await Promise.all([...this.pendingUploads]);
        if (
          sessionToken !== this._automationSessionToken ||
          !this._automationSaveMode ||
          this.mode !== "display" ||
          this.tag?.entry_id !== entryId
        )
          return;
        this.dispatchEvent(
          new CustomEvent("automation-save-request", {
            detail: {
              session_token: sessionToken,
              entry_id: entryId,
              document: clone(this.document),
              background: this.document.background,
              preview_variables: clone(this._automationPreviewVariables || {}),
            },
            bubbles: true,
            composed: true,
          }),
        );
      } catch (error) {
        if (sessionToken === this._automationSessionToken) this.report(error);
      }
      return;
    }
    if (action === "dismiss-status") {
      this.notice = null;
      this.error = false;
      this.errorSource = null;
      this.status = "Ready";
      this.renderStatus();
      this.shadowRoot.querySelector(".stage")?.focus();
      return;
    }
    try {
      if (["save", "preview", "send"].includes(action)) {
        // Finish canvas edits and in-flight uploads before freezing the request.
        this.gestureFinish?.(false);
        this.busy = true;
        this.error = false;
        this.errorSource = null;
        this.status = action === "send" ? "Sending display…" : "Working…";
        this.notice = action === "send" ? this.status : null;
        this.render();
        if (this.pendingUploads.size)
          await Promise.all([...this.pendingUploads]);
        if (action === "send") {
          this.adoptDocument(
            await this.api("save", {
              entry_id: this.tag.entry_id,
              document: this.document,
            }),
          );
          this.tag.document = clone(this.document);
          this.dirty = false;
          this.drafts.delete(this.tag.entry_id);
        }
        const result =
          this.mode === "template"
            ? action === "save"
              ? await this.api("save_template", {
                  key: this.templateKey,
                  template: {
                    width: this.tag.width,
                    height: this.tag.height,
                    name: this.templateName,
                    sensor_type: this.templateSensorType,
                    document: this.document,
                  },
                })
              : await this.previewRequest()
            : await this.api(action, {
                entry_id: this.tag.entry_id,
                document: this.document,
              });
        if (action === "save") {
          this.adoptDocument(
            this.mode === "template" ? result.document : result,
          );
          if (this.mode === "template")
            this.templates[this.templateKey] = clone(result);
          this.tag.document = clone(this.document);
          this.drafts.delete(this.tag.entry_id);
          this.dirty = false;
          if (this.mode === "template" && this.createdForElement) {
            const session = this.displaySession;
            session.undo.push(clone(session.document));
            session.redo = [];
            session.document.elements.find(
              (el) => el.id === this.createdForElement,
            ).template = this.templateKey;
            session.dirty = true;
            this.createdForElement = null;
          }
          this.status =
            this.mode === "template" ? "Style saved" : "Display saved";
          this.notice = this.status;
        }
        if (action === "preview") {
          this.preview = result.png;
          this.layerPreviews = result.layers;
          this.layerBounds = result.layers._bounds || {};
          this.layerOffsets = result.layers._offsets || {};
          this.layerRecords = this.renderRecords();
          this.templateEntities = [
            ...new Set(Object.values(result.layers._dependencies || {}).flat()),
          ];
          this.status = "Exact rendered preview";
        }
        if (action === "send") {
          const sent = {
            written: "Display sent and acknowledged",
            locked: "Not sent: the tag's write lock is on",
            duplicate: "Not sent: the display is unchanged",
            dropped: "Not sent: a newer write replaced this one",
            failed: {
              key: "Sending failed{error}",
              values: { error: result.error ? `: ${result.error}` : "" },
            },
          };
          this.status = sent[result.status] || result.status;
          this.notice = this.status;
          this.error = ["locked", "failed"].includes(result.status);
        }
      } else if (action === "restore") {
        if (
          this._automationSaveMode ||
          this.mode === "template" ||
          !this.tag ||
          !this.dirty
        )
          return;
        if (
          !window.confirm(
            t(
              this.hass,
              "Restore the last saved design? Unsaved changes will be discarded.",
            ),
          )
        )
          return;
        const restored = clone(this.tag.document || emptyDocument());
        this.drafts.delete(this.tag.entry_id);
        this.session.reset(restored);
        this.preview = null;
        this.layerPreviews = {};
        this.layerBounds = {};
        this.layerOffsets = {};
        this.layerRecords = this.renderRecords();
        this.selected = null;
        this.status = "Ready";
        this.notice = null;
        this.error = false;
        this.invalidatePreview();
        this.render();
        this.queuePreview();
      } else if (action === "reload") {
        // Retry after a failed first load shows the error instead.
        if (this.refreshing || (this.loading && !this.loading.error)) return;
        this.started = false;
        await this.boot();
        return;
      } else if (action === "undo" || action === "redo") {
        if (this.session.stepHistory(action)) {
          if (!this.element) this.selected = null;
          this.edited();
        }
      } else if (["yaml", "create-automation"].includes(action)) {
        this.busy = true;
        this.error = false;
        this.errorSource = null;
        this.status = "Exporting payload…";
        this.render();
        if (this.pendingUploads.size)
          await Promise.all([...this.pendingUploads]);
        this.yamlExport = await this.api(
          action === "yaml" ? "export" : "automation",
          {
            entry_id: this.tag.entry_id,
            document: this.document,
            ...(action === "create-automation" &&
            this.templateAutomation?.entryId === this.tag.entry_id &&
            this.templateAutomation.elementIds.every((id) =>
              this.document.elements.some((element) => element.id === id),
            )
              ? { automation_defaults: this.templateAutomation.defaults }
              : {}),
          },
        );
        if (this.yamlExport.automation) {
          const alias = this.hass.states[this.tag.entities?.alias]?.state;
          if (alias && !["unknown", "unavailable"].includes(alias))
            this.yamlExport.automation.alias = alias;
        }
        this.status = "Payload exported";
      } else if (action === "export") {
        const blob = new Blob([JSON.stringify(this.document, null, 2)], {
            type: "application/json",
          }),
          url = URL.createObjectURL(blob),
          link = document.createElement("a");
        link.href = url;
        link.download = `${
          (this.mode === "template" ? this.templateName : this.tag?.title)
            ?.replace(/[\\/:*?"<>|\s]+/g, "-")
            .replace(/^[-.]+|[-.]+$/g, "") || "label-display"
        }.json`;
        link.click();
        URL.revokeObjectURL(url);
      } else if (action === "import")
        this.shadowRoot.querySelector("#file").click();
      else this.transform(action);
    } catch (error) {
      this.report(error, action === "preview" ? "preview" : "operation");
    } finally {
      this.busy = false;
      this.render();
    }
  }
  transform(action) {
    const element = this.element;
    if (!element) return;
    if (!["duplicate", "delete", "back", "front", "center"].includes(action))
      return;
    this.checkpoint();
    if (this.selectedElements.length > 1) {
      const selected = this.selectedElements,
        remaining = this.document.elements.filter(
          (e) => !this.selectedIds.has(e.id),
        );
      if (action === "duplicate") {
        const copies = selected.map((e) => ({
          ...clone(e),
          id: createId(),
          x: e.x + 8,
          y: e.y + 8,
        }));
        this.document.elements.push(...copies);
        this.selectIds(copies.map((e) => e.id));
      } else if (action === "delete") {
        this.document.elements = remaining;
        this.selected = null;
      } else if (action === "back")
        this.document.elements = [...selected, ...remaining];
      else if (action === "front")
        this.document.elements = [...remaining, ...selected];
      else if (action === "center") {
        const left = Math.min(...selected.map((e) => e.x)),
          right = Math.max(...selected.map((e) => e.x + e.width));
        const dx = Math.round((this.tag.width - (right - left)) / 2) - left;
        selected.forEach((e) => (e.x += dx));
      }
      this.edited();
      this.focusElement();
      return;
    }
    const elements = this.document.elements,
      index = elements.indexOf(element);
    if (action === "duplicate") {
      const copy = clone(element);
      copy.id = createId();
      // Step back instead when the copy would be clamped onto the original.
      copy.x += copy.x + copy.width + 8 > this.tag.width ? -8 : 8;
      copy.y += copy.y + copy.height + 8 > this.tag.height ? -8 : 8;
      clampBox(copy, this.tag, onLabel(element, this.tag));
      elements.push(copy);
      this.selected = copy.id;
    }
    if (action === "delete") {
      elements.splice(index, 1);
      this.selected = null;
    }
    if (action === "back") {
      elements.splice(index, 1);
      elements.unshift(element);
    }
    if (action === "front") {
      elements.splice(index, 1);
      elements.push(element);
    }
    if (action === "center")
      element.x = Math.round((this.tag.width - element.width) / 2);
    this.edited();
    this.focusElement();
  }
  closeContextMenu() {
    this.shadowRoot.querySelector(".context-menu")?.remove();
  }
  contextMenu(event) {
    if (event.target.isContentEditable) return;
    const node = event.target.closest("[data-id], [data-select]");
    if (!node || this.busy) return;
    event.preventDefault();
    if (event.ctrlKey) {
      event.preventDefault();
      return;
    }
    const id = node.dataset.id || node.dataset.select;
    if (this.selectedIds.has(id)) this.selectIds(this.selectedIds, id);
    else this.selected = id;
    this.render();
    const menu = document.createElement("div");
    menu.className = "context-menu";
    menu.setAttribute("role", "menu");
    menu.setAttribute("aria-label", t(this.hass, "Element actions"));
    const position = calculateContextMenuPosition({
      pointerX: event.clientX,
      pointerY: event.clientY,
      viewportWidth: window.innerWidth,
      viewportHeight: window.innerHeight,
    });
    menu.style.left = `${position.left}px`;
    menu.style.top = `${position.top}px`;
    menu.innerHTML = renderElementActionMenu({
      t: (message) => t(this.hass, message),
      icon,
      toolIcon,
    });
    this.shadowRoot.append(menu);
    menu.querySelector("button").focus();
  }
  // The same actions as the right-click menu, reachable by touch.
  elementActions() {
    return renderElementActionBar({
      busy: this.busy,
      t: (message) => t(this.hass, message),
      icon,
      toolIcon,
    });
  }
  beginTextEdit() {
    return beginCanvasTextEdit(this);
  }
  finishTextEdit() {
    return finishCanvasTextEdit(this);
  }
  input(event) {
    if (this.busy) return;
    this.gestureFinish?.(false);
    const input = event.target;
    if (input.dataset.editText) {
      if (this.typingProperty !== input) {
        this.checkpoint();
        this.typingProperty = input;
      }
      this.element.text = input.innerText;
      this.dirty = true;
      const field = this.shadowRoot.querySelector('[data-property="text"]');
      if (field) field.value = this.element.text;
      const layer = this.shadowRoot.querySelector(
        `[data-select="${this.selected}"]`,
      );
      if (layer) layer.textContent = this.element.text;
      this.markDirty();
      return;
    }
    if (input.id === "template-name") {
      this.templateName = input.value;
      this.dirty = true;
      return;
    }
    if (["template-width", "template-height"].includes(input.id)) {
      if (!input.validity.valid || !input.value) return;
      this.tag[input.id === "template-width" ? "width" : "height"] = Number(
        input.value,
      );
      this.document.elements.forEach((el) => clampBox(el, this.tag, false));
      const stage = this.shadowRoot.querySelector(".stage");
      stage.style.width = `${this.tag.width}px`;
      stage.style.height = `${this.tag.height}px`;
      this.edited(false);
      this.fitPreview();
      return;
    }
    if (input.id === "icon-search") {
      this.renderIconChoices(input.value);
      return;
    }
    if (input.id === "search") {
      this.search = input.value;
      this.renderEntities();
    } else if (
      input.dataset.spec &&
      ["text", "textarea"].includes(input.type)
    ) {
      this.specInput(input);
    } else if (
      input.dataset.property &&
      this.element &&
      ["text", "textarea", "number", "range"].includes(input.type)
    ) {
      if (input.type === "number" && !input.validity.valid) return;
      if (this.typingProperty !== input) {
        this.checkpoint();
        this.typingProperty = input;
        this.typedOnLabel = onLabel(this.element, this.tag);
        this.typedMoveBound = this.moveBound(
          this.element,
          this.visibleBounds(this.element),
        );
      }
      this.updateProperty(input);
      this.edited(false);
      this.markDirty();
      const layer = this.shadowRoot.querySelector(
        `[data-select="${this.selected}"]`,
      );
      if (layer) layer.textContent = this.layerLabel(this.element);
    }
  }
  updateProperty(input) {
    const key = input.dataset.property;
    if (this.selectedElements.length > 1) {
      if (input.value === "" && ["number", "range"].includes(input.type))
        return;
      const value = ["number", "range"].includes(input.type)
        ? Number(input.value)
        : input.type === "checkbox"
          ? input.checked
          : input.value;
      setSharedProperty(this, key, value);
      if (key === "rotation") syncRotationInputs(this.shadowRoot, value);
      return;
    }
    if (key === "weather_field" && input.value === "condition")
      delete this.element.decimals;
    if (key === "type") {
      if (input.value === "line") this.element.height = 2;
      else if (this.element.type === "line") this.element.height = 40;
    }
    if (key === "entity_id" && this.element.entity_id !== input.value) {
      const defaults = newElement(
        "sensor",
        this.tag,
        this.hass.states[input.value],
      );
      delete this.element.decimals;
      if (defaults.decimals !== undefined)
        this.element.decimals = defaults.decimals;
      this.element.show_unit = defaults.show_unit;
    }
    if (
      (key === "decimals" || optionalProperties.has(key)) &&
      input.type !== "checkbox" &&
      input.value === ""
    )
      delete this.element[key];
    else if (key === "dither") {
      if (input.value === "") delete this.element.dither;
      else this.element.dither = input.value === "none" ? false : input.value;
    } else if (key === "rotation") {
      this.element.rotation = Number(input.value);
      syncRotationInputs(this.shadowRoot, this.element.rotation);
    } else
      this.element[key] =
        input.type === "checkbox"
          ? input.checked
          : input.type === "number"
            ? Number(input.value)
            : input.value;
    if (key === "font_size")
      this.element.font_size = Math.max(
        8,
        Math.min(200, this.element.font_size),
      );
    if (propertyRanges[key] && this.element[key] !== undefined)
      this.element[key] = Math.max(
        propertyRanges[key][0],
        Math.min(propertyRanges[key][1], Math.round(this.element[key])),
      );
    if (key === "decimals" && this.element.decimals !== undefined)
      this.element.decimals = Math.max(0, Math.min(6, this.element.decimals));
    // Typed geometry is kept to the label when the field is committed.
    clampBox(this.element, this.tag, false);
  }
  async setTagOrientation(rotation) {
    try {
      const result = await this.api("orientation", {
        entry_id: this.tag.entry_id,
        rotation,
      });
      Object.assign(this.tag, result);
      this.render();
      this.fitPreview();
      this.queuePreview();
    } catch (error) {
      this.report(error);
    }
  }
  async change(event) {
    if (this.busy) return;
    this.gestureFinish?.(false);
    const input = event.target,
      id = input.id;
    if (id === "template-type") {
      this.loadTemplate(input.value);
      return;
    }
    if (id === "template-sample") {
      this.sampleEntity = input.value;
      this.templateSensorType = "output:" + this.outputType(this.sampleState());
      this.dirty = true;
      this.render();
      this.preview = null;
      this.drawStage();
      this.queuePreview();
      return;
    }
    if (["template-width", "template-height"].includes(id)) {
      this.tag[id === "template-width" ? "width" : "height"] = Math.max(
        16,
        Math.min(1000, Number(input.value)),
      );
      this.document.elements.forEach((el) => clampBox(el, this.tag, false));
      this.edited();
      return;
    }
    if (id === "tag") {
      if (this._automationSessionPending || this._automationSaveMode) {
        this.render();
        return;
      }
      this.gestureFinish?.(false);
      this.load(this.tags.find((tag) => tag.entry_id === input.value));
      this.dispatchEvent(
        new CustomEvent("tag-changed", {
          detail: { entry_id: input.value },
          bubbles: true,
          composed: true,
        }),
      );
      return;
    }
    if (id === "zoom") {
      this.zoomMode = input.value === "fit" ? "fit" : "manual";
      if (this.zoomMode === "manual") this.zoom = Number(input.value);
      this.render();
      return;
    }
    if (id === "image-file") {
      handleImageUpload(this, input);
      return;
    }
    if (id === "file") {
      const file = input.files?.[0];
      if (!file) return;
      const context = this.documentSessionContext();
      this.busy = true;
      this.status = "Checking display…";
      this.render();
      try {
        const imported = JSON.parse(await file.text());
        if (!this.isDocumentSessionCurrent(context)) return;
        await this.api("preview", {
          entry_id: context.entryId,
          document: imported,
        });
        if (!this.isDocumentSessionCurrent(context)) return;
        if (
          this.dirty &&
          !window.confirm(
            t(
              this.hass,
              "Replace the current design with the imported file? You can undo this.",
            ),
          )
        ) {
          this.status = "Ready";
          return;
        }
        this.checkpoint();
        this.document = this.normalizeImportedDocument(imported);
        this.selected = null;
        this.edited();
      } catch (error) {
        if (this.isDocumentSessionCurrent(context)) this.report(error);
      } finally {
        if (this.isDocumentSessionOwner(context)) {
          this.busy = false;
          this.render();
        }
      }
      return;
    }
    if (id === "background") {
      this.checkpoint();
      this.document.background = input.value;
      this.edited();
      return;
    }
    // Chosen with the Add button: arrow keys move through the list, they
    // must not add an element at every step.
    if (id === "add-spec") return;
    if (input.dataset.spec) {
      if (input.matches("select") && this.element?.type === "imagespec") {
        const before = clone(this.document);
        if (
          applySpecInput(
            input,
            this.element.spec,
            this.specDefinition(this.element),
            this.hass,
          )
        ) {
          this.pushUndo(before);
          this.edited();
        }
      }
      return;
    }
    if (input.dataset.property === "template" && input.value === "__new__") {
      this.createSensorTemplate();
      return;
    }
    if (input.dataset.property && this.element) {
      if (
        this.selectedElements.length > 1 &&
        ["text", "textarea", "number", "range"].includes(input.type)
      ) {
        this.updateProperty(input);
        return;
      }
      if (["text", "textarea", "number", "range"].includes(input.type)) {
        if (["x", "y", "width", "height"].includes(input.dataset.property)) {
          // Judged before the edit: an off-label imported frame stays put.
          const onFrame = this.typedOnLabel ?? true;
          if (["x", "y"].includes(input.dataset.property))
            this.clampMoved(
              this.element,
              this.typedMoveBound ?? true,
              this.visibleBounds(this.element),
            );
          else clampBox(this.element, this.tag, onFrame);
          this.edited();
        } else if (["number", "range"].includes(input.type)) {
          // Show the value the element kept: it may have been clamped to the
          // allowed range, or refused as out of range.
          const key = input.dataset.property,
            snapshot = clone(this.document),
            before = JSON.stringify(this.element[key]);
          this.updateProperty(input);
          input.value = this.element[key] ?? "";
          if (JSON.stringify(this.element[key]) !== before) {
            if (this.typingProperty !== input) this.pushUndo(snapshot);
            this.edited(false);
          }
        }
        return;
      }
      this.checkpoint();
      this.updateProperty(input);
      this.edited();
    }
  }
  normalizeImportedDocument(document) {
    return normalizeImportedDocument(document, {
      emptyDocument,
      clone,
      createId,
    });
  }

  key(event) {
    return handleCanvasKey(this, event);
  }
  pointer(event) {
    return handleCanvasPointer(this, event);
  }
  drop(event) {
    if (this.busy) return;
    const stage = event.target.closest(".stage");
    if (!stage) return;
    event.preventDefault();
    const rect = stage.getBoundingClientRect();
    this.gestureFinish?.(false);
    const entity = this.hass.states[event.dataTransfer.getData("text/plain")];
    if (!entity) return;
    this.add(
      "sensor",
      entity,
      Math.round((event.clientX - rect.left) / this.zoom),
      Math.round((event.clientY - rect.top) / this.zoom),
    );
  }
  get previewTimer() {
    // Compatibility for existing browser checks that cancel a pending render.
    return this.previewController?.timer || null;
  }
  invalidatePreview() {
    this.previewController.invalidate();
  }
  applyPreviewResult(result) {
    this.preview = result.png;
    this.layerPreviews = result.layers;
    this.layerBounds = result.layers._bounds || {};
    this.layerOffsets = result.layers._offsets || {};
    this.layerRecords = this.renderRecords();
    this.templateEntities = [
      ...new Set(Object.values(result.layers._dependencies || {}).flat()),
    ];
    this.drawStage();
    const title = this.shadowRoot
      .querySelector(".canvas-wrap")
      ?.previousElementSibling?.querySelector("span");
    if (title) title.textContent = t(this.hass, "Exact rendered preview");
    if (this.error && this.errorSource === "preview") {
      // The render that failed has been fixed.
      this.error = false;
      this.errorSource = null;
      this.status = "Exact rendered preview";
      this.renderStatus();
    }
  }
  queuePreview() {
    this.previewController.cancelScheduled();
    if (!this.tag || this.editingTextId) return;
    if (this.mode === "template" && !this.sampleEntity) {
      this.invalidatePreview();
      return;
    }
    this.previewController.schedule();
  }
}
// HA loads ha-entity-picker lazily. Opening this panel directly (or reloading
// it) happens before any page that uses the picker, so load it through a card
// editor. Runs in the background: nothing may wait on it.
async function loadEntityPicker() {
  try {
    const helpers = await window.loadCardHelpers?.();
    const card = await helpers?.createCardElement({
      type: "entities",
      entities: [],
    });
    await card?.constructor?.getConfigElement?.();
  } catch (error) {
    console.warn("ESL Designer: could not load the entity picker", error);
  }
}

if (!customElements.get("ble-esl-designer"))
  customElements.define("ble-esl-designer", BleEslDesigner);
