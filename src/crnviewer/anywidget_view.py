from __future__ import annotations

import importlib.resources as resources
import json
from collections.abc import Mapping
from typing import Any

import traitlets
import anywidget  # type: ignore[import-not-found]


def _read_widget_esm() -> str:
    template_path = resources.files("crnviewer.static").joinpath(
        "anywidget_cytoscape.js"
    )
    cytoscape_path = resources.files("crnviewer.static").joinpath(
        "cytoscape.min.js"
    )

    with template_path.open("r", encoding="utf-8") as stream:
        template = stream.read()
    with cytoscape_path.open("r", encoding="utf-8") as stream:
        cytoscape_source = stream.read()

    return template.replace(
        "__CRNVIEWER_CYTOSCAPE_SOURCE__",
        json.dumps(cytoscape_source),
    )


class CytoscapeAnyWidget(anywidget.AnyWidget):  # type: ignore[misc]
    """Custom anywidget wrapper for Cytoscape network rendering."""

    _esm = _read_widget_esm()

    state = traitlets.Dict(default_value={}).tag(sync=True)
    width = traitlets.Unicode("100%").tag(sync=True)
    height = traitlets.Unicode("700px").tag(sync=True)
    selected_node_ids = traitlets.List(
        trait=traitlets.Unicode(),
        default_value=[],
    ).tag(sync=True)
    action = traitlets.Dict(default_value={}).tag(sync=True)
    last_action = traitlets.Dict(default_value={}).tag(sync=True)

    def __init__(
        self,
        *,
        state: Mapping[str, Any],
        width: str = "100%",
        height: str = "700px",
    ) -> None:
        super().__init__()  # type: ignore[misc]
        self.state = dict(state)
        self.width = width
        self.height = height

    def update_state(self, state: Mapping[str, Any]) -> None:
        self.state = dict(state)
