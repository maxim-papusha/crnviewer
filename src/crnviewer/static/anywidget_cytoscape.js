const CYTOSCAPE_SOURCE = __CRNVIEWER_CYTOSCAPE_SOURCE__;

function ensureCytoscape() {
  if (typeof window.cytoscape === "function") {
    return;
  }
  const loaded = (globalThis.__crnviewerLoadedScripts ||= new Set());
  if (!loaded.has("cytoscape")) {
    const script = document.createElement("script");
    script.type = "text/javascript";
    script.text = CYTOSCAPE_SOURCE;
    document.head.appendChild(script);
    script.remove();
    loaded.add("cytoscape");
  }
  if (typeof window.cytoscape !== "function") {
    throw new Error("Embedded Cytoscape copy did not initialize");
  }
}

function getState(model) {
  const state = model.get("state") || {};
  const elements = state.elements || { nodes: [], edges: [] };
  const style = state.style || [];
  const layout = state.layout || { name: "cose", nodeDimensionsIncludeLabels: true, animate: false };
  const ui = state.ui || {};
  return { state, elements, style, layout, ui };
}

function applySizing(model, host, container) {
  host.style.width = model.get("width") || "100%";
  host.style.height = model.get("height") || "700px";
  container.style.width = "100%";
  container.style.height = "100%";
}

export function render({ model, el }) {
  const host = document.createElement("div");
  const container = document.createElement("div");
  host.appendChild(container);
  el.appendChild(host);

  let cy = null;

  function updateSelection() {
    if (!cy) {
      return;
    }
    const selected = cy.$("node:selected").map((node) => node.id());
    model.set("selected_node_ids", selected);
    model.save_changes();
  }

  function renderGraph() {
    applySizing(model, host, container);

    try {
      ensureCytoscape();
    } catch (error) {
      host.textContent = `Failed to load Cytoscape bundles: ${String(error)}`;
      return;
    }

    if (typeof window.cytoscape !== "function") {
      host.textContent = "Cytoscape.js is not available in this environment.";
      return;
    }

    const { elements, style, layout, ui } = getState(model);

    if (cy) {
      cy.destroy();
      cy = null;
      container.textContent = "";
    }

    const config = {
      container,
      elements,
      style,
      layout,
    };

    const requestedLayoutName = layout?.name;
    if (["elk", "klay", "cose-bilkent"].includes(requestedLayoutName)) {
      config.layout = { name: "cose", nodeDimensionsIncludeLabels: true, animate: false };
    }

    if (ui.zoom !== undefined && ui.zoom !== null) {
      config.zoom = ui.zoom;
    }
    if (ui.pan !== undefined && ui.pan !== null) {
      config.pan = ui.pan;
    }

    cy = window.cytoscape(config);
    cy.on("select", "node", updateSelection);
    cy.on("unselect", "node", updateSelection);
    cy.on("tap", "node", (event) => {
      const nodeId = event.target.id();
      model.set("last_action", { type: "node_tap", node_id: nodeId });
      model.save_changes();
    });
  }

  function updateSizeOnly() {
    applySizing(model, host, container);
    if (cy) {
      cy.resize();
    }
  }

  model.on("change:state", renderGraph);
  model.on("change:width", updateSizeOnly);
  model.on("change:height", updateSizeOnly);

  renderGraph();

  return () => {
    if (cy) {
      cy.destroy();
    }
  };
}
