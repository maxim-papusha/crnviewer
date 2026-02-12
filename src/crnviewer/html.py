from __future__ import annotations

import importlib.resources as resources
import json
import uuid
from typing import Any, Mapping

from .ipython import CyBuilder
from .state import cybuilder_state


def _read_static_text(name: str) -> str:
    """Return the contents of a static asset shipped with the package."""

    path = resources.files("crnviewer.static").joinpath(name)
    with path.open("r", encoding="utf-8") as stream:
        return stream.read()


def cybuilder_html(
    builder: CyBuilder[Any, Any],
    *,
    layout: str = "cose",
    layout_options: Mapping[str, Any] | None = None,
    pixel_ratio: float | None = 3.0,
) -> str:
    """Return a standalone HTML snippet visualizing a ``CyBuilder``.

    The output embeds Cytoscape.js plus the cytoscape-elk plugin so layered
    layouts are available, cytoscape-klay for Klay layout support, and
    cytoscape-cose-bilkent for the COSE-Bilkent force layout. ``layout`` may be
    any Cytoscape layout name; use ``"layered"`` to select the ELK layered
    algorithm, ``"klay"`` for the Klay layout, or ``"cose-bilkent"`` for the
    Bilkent force-directed layout. ``layout_options`` are merged into the chosen
    layout configuration. The container is rendered full-viewport with margins
    removed. ``pixel_ratio`` optionally overrides the Cytoscape canvas pixel
    ratio for sharper rendering (defaults to the browser device pixel ratio
    when ``None``).
    """

    state = cybuilder_state(
        builder,
        layout=layout,
        layout_options=layout_options,
        stylesheet=list(CyBuilder.default_stylesheet),
    )
    return state_html(state, pixel_ratio=pixel_ratio)


def state_html(
    state: Mapping[str, Any],
    *,
    pixel_ratio: float | None = 3.0,
) -> str:
    elements = state.get("elements", {"nodes": [], "edges": []})
    style = state.get("style", list(CyBuilder.default_stylesheet))
    layout_config = state.get(
        "layout",
        {
            "name": "cose",
            "nodeDimensionsIncludeLabels": True,
            "animate": False,
        },
    )

    graph_json = json.dumps(dict(elements))
    style_json = json.dumps(list(style))
    layout_json = json.dumps(dict(layout_config))
    container_id = f"cy-{uuid.uuid4().hex}"

    cytoscape_js = _read_static_text("cytoscape.min.js")

    scripts: list[str] = ["<script>" + cytoscape_js + "</script>"]
    chosen_layout = str(layout_config.get("name", "cose"))

    if chosen_layout == "elk":
        elk_js = _read_static_text("elk.bundled.js")
        cytoscape_elk_js = _read_static_text("cytoscape-elk.min.js")
        scripts.extend([
            "<script>" + elk_js + "</script>",
            "<script>" + cytoscape_elk_js + "</script>",
        ])
    elif chosen_layout == "klay":
        klay_js = _read_static_text("klay.js")
        cytoscape_klay_js = _read_static_text("cytoscape-klay.js")
        scripts.extend([
            "<script>" + klay_js + "</script>",
            "<script>" + cytoscape_klay_js + "</script>",
        ])
    elif chosen_layout == "cose-bilkent":
        cose_bilkent_js = _read_static_text("cytoscape-cose-bilkent.js")
        scripts.append("<script>" + cose_bilkent_js + "</script>")

    container_css = (
        "html, body { margin: 0; padding: 0; width: 100vw; height: 100vh; overflow: hidden; }"
        f"#{container_id} {{ width: 100vw; height: 100vh; }}"
        ".controls { position: fixed; top: 10px; left: 10px; z-index: 999; }"
        "button { padding: 8px 12px; cursor: pointer; background: #fff; border: 1px solid #ccc; border-radius: 4px; font-family: sans-serif; }"
        "button:hover { background: #f0f0f0; }"
    )

    pixel_ratio_json = "null" if pixel_ratio is None else json.dumps(pixel_ratio)
    scripts_html = "".join(scripts)

    # Inline Cytoscape.js, elkjs, and cytoscape-elk so the HTML works offline.
    return (
        "<!DOCTYPE html>"
        "<html><head>"
        "<meta charset='utf-8'/>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'/>"
        "<style>"
        f"{container_css}"
        "</style>"
        + scripts_html
        + "</head><body>"
        "<div class='controls'>"
        "<button id='download-btn'>Download with Positions</button>"
        "</div>"
        f"<div id='{container_id}'></div>"
        "<script id='cy-init'>"
        "(function(){"
        "const layoutDefaults = { nodeDimensionsIncludeLabels: true, animate: false };\n"
        "const elements = /* ELEMENTS_START */ "
        f"{graph_json} /* ELEMENTS_END */;\n"
        "const stylesheet = "
        f"{style_json};\n"
        "const layoutCfg = /* LAYOUT_START */ "
        f"{layout_json} /* LAYOUT_END */;\n"
        "const zoom = /* ZOOM_START */ null /* ZOOM_END */;\n"
        "const pan = /* PAN_START */ null /* PAN_END */;\n"
        "const pixelRatio = "
        f"{pixel_ratio_json};\n"
        "if (typeof cytoscapeElk === 'function') { cytoscape.use(cytoscapeElk); }"
        "if (typeof cytoscapeKlay === 'function') { cytoscape.use(cytoscapeKlay); }"
        "if (typeof cytoscapeCoseBilkent === 'function') { cytoscape.use(cytoscapeCoseBilkent); }"
        "const finalLayout = Object.assign({}, layoutDefaults, layoutCfg);"
        "const cyConfig = {"
        f"container: document.getElementById('{container_id}'),"
        "elements: elements,"
        "style: stylesheet,"
        "layout: finalLayout,"
        "};"
        "if (pixelRatio !== null) { cyConfig.pixelRatio = pixelRatio; }"
        "if (zoom !== null) { cyConfig.zoom = zoom; }"
        "if (pan !== null) { cyConfig.pan = pan; }"
        "const cy = window.cy = cytoscape(cyConfig);"
        ""
        "const downloadBtn = document.getElementById('download-btn');"
        "if (downloadBtn) {"
        "  downloadBtn.addEventListener('click', () => {"
        "    const clone = document.documentElement.cloneNode(true);"
        "    const script = clone.querySelector('#cy-init');"
        "    const controls = clone.querySelector('.controls');"
        "    if (controls) controls.remove();"
        "    let text = script.textContent;"
        "    const currentElements = cy.elements().jsons();"
        "    const currentZoom = cy.zoom();"
        "    const currentPan = cy.pan();"
        "    text = text.replace(/\\/\\* ELEMENTS_START \\*\\/.*\\/\\* ELEMENTS_END \\*\\//, () => '/* ELEMENTS_START */ ' + JSON.stringify(currentElements) + ' /* ELEMENTS_END */');"
        "    text = text.replace(/\\/\\* LAYOUT_START \\*\\/.*\\/\\* LAYOUT_END \\*\\//, () => '/* LAYOUT_START */ { \"name\": \"preset\" } /* LAYOUT_END */');"
        "    text = text.replace(/\\/\\* ZOOM_START \\*\\/.*\\/\\* ZOOM_END \\*\\//, () => '/* ZOOM_START */ ' + currentZoom + ' /* ZOOM_END */');"
        "    text = text.replace(/\\/\\* PAN_START \\*\\/.*\\/\\* PAN_END \\*\\//, () => '/* PAN_START */ ' + JSON.stringify(currentPan) + ' /* PAN_END */');"
        "    script.textContent = text;"
        "    const html = '<!DOCTYPE html>\\n' + clone.outerHTML;"
        "    const blob = new Blob([html], { type: 'text/html' });"
        "    const url = URL.createObjectURL(blob);"
        "    const a = document.createElement('a');"
        "    a.href = url;"
        "    a.download = 'network.html';"
        "    a.click();"
        "    URL.revokeObjectURL(url);"
        "  });"
        "}"
        "})();"
        "</script>"
        "</body></html>"
    )

