import { test, expect } from "@playwright/test";

test("workspace view composes responsive panels, preview shell, and accessible controls", async ({
  page,
}) => {
  await page.goto("/");
  const output = await page.evaluate(async () => {
    const { renderWorkspace, WORKSPACE_STYLE } =
      await import("/frontend/editor/workspace-view.js");
    const result = renderWorkspace({
      tag: { width: 296, height: 128, colors: '<black & "white">' },
      mode: "template",
      libraryOpen: false,
      inspectorOpen: true,
      sessionLocked: true,
      preview: true,
      zoom: 1.25,
      background: "#fff",
      sampleEntity: null,
      tipsOpen: true,
      hasElement: false,
      translate: (key) => key,
      escapeHtml: (value) =>
        String(value).replace(
          /[&<>"']/g,
          (char) =>
            ({
              "&": "&amp;",
              "<": "&lt;",
              ">": "&gt;",
              '"': "&quot;",
              "'": "&#39;",
            })[char],
        ),
      toggles: {
        libraryOpen:
          '<button data-action="toggle-library" aria-expanded="true">Library</button>',
        libraryClosed:
          '<button data-action="toggle-library" aria-expanded="false">Library</button>',
        inspectorOpen:
          '<button data-action="toggle-inspector" aria-expanded="true">Inspector</button>',
        inspectorClosed:
          '<button data-action="toggle-inspector" aria-expanded="false">Inspector</button>',
      },
      libraryContent:
        '<ha-entity-picker id="entity-picker"></ha-entity-picker><button data-action="add-component">Add</button>',
      elementActions: '<div class="element-actions">Actions</div>',
      propertyContent: '<label>Property<input value="ready"></label>',
      layerRows: '<button class="layer" data-id="one">One</button>',
    });
    return { markup: result, style: WORKSPACE_STYLE };
  });

  const workspace = await page.evaluate((markup) => {
    const host = document.createElement("div");
    host.innerHTML = markup;
    const canvas = host.querySelector(".stage");
    return {
      classes: host.querySelector(".workspace").className,
      libraryHidden: host.querySelector("#library .template-start").hidden,
      previewHeading: host.querySelector(".preview-card h2").textContent,
      canvasLabel: canvas.getAttribute("aria-label"),
      canvasSize: [canvas.style.width, canvas.style.height],
      emptyNote: host.querySelector(".empty-note")?.textContent,
      libraryToggle: host
        .querySelector(".preview-card [data-action='toggle-library']")
        ?.getAttribute("aria-expanded"),
      inspectorHeading: host.querySelector("#inspector h2").textContent,
      hasProperties: Boolean(host.querySelector("#inspector .props input")),
      hasLayers: Boolean(host.querySelector(".layers [data-id='one']")),
      tipsOpen: host.querySelector(".tips").open,
    };
  }, output.markup);

  expect(workspace.classes).toBe("workspace library-closed ");
  expect(workspace.libraryHidden).toBe(true);
  expect(workspace.previewHeading).toContain("296 × 128");
  expect(workspace.previewHeading).toContain('<black & "white">');
  expect(workspace.canvasLabel).toBe("Display canvas");
  expect(workspace.canvasSize).toEqual(["296px", "128px"]);
  expect(workspace.emptyNote).toContain("Choose a sample sensor");
  expect(workspace.libraryToggle).toBe("false");
  expect(workspace.inspectorHeading).toBe("Select an element");
  expect(workspace.hasProperties).toBe(true);
  expect(workspace.hasLayers).toBe(true);
  expect(workspace.tipsOpen).toBe(true);
  expect(output.markup).toContain(
    'aria-describedby="canvas-tips canvas-tips-select"',
  );
  expect(output.style).toContain(".workspace.library-closed");
  expect(output.style).toContain("@media(max-width:650px)");
});
