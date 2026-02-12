from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, TYPE_CHECKING, cast

if TYPE_CHECKING:
    from .ipython import CyBuilder

SCHEMA_VERSION = "0.1"


def resolve_layout_config(
    *,
    layout: str = "cose",
    layout_options: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    layout_config: dict[str, Any]
    if layout == "layered":
        layout_config = {
            "name": "elk",
            "nodeDimensionsIncludeLabels": True,
            "animate": False,
            "elk": {"algorithm": "layered"},
        }
    else:
        layout_config = {
            "name": layout,
            "nodeDimensionsIncludeLabels": True,
            "animate": False,
        }

    if layout_options:
        if layout_config["name"] == "elk":
            elk_opts = layout_config.setdefault("elk", {})
            for key, value in layout_options.items():
                if key.startswith("elk."):
                    stripped = key.removeprefix("elk.")
                    elk_opts[stripped] = value
                elif key.startswith("elk:"):
                    stripped = key.removeprefix("elk:")
                    elk_opts[stripped] = value
                elif key.startswith("layered."):
                    elk_opts[key] = value
                elif key in {"algorithm", "direction", "edgeRouting"}:
                    elk_opts[key] = value
                else:
                    layout_config[key] = value
        else:
            layout_config.update(layout_options)

    return layout_config


def cybuilder_state(
    builder: "CyBuilder[Any, Any]",
    *,
    layout: str = "cose",
    layout_options: Mapping[str, Any] | None = None,
    stylesheet: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    node_defs, edge_defs = builder.elements()

    return {
        "schema_version": SCHEMA_VERSION,
        "elements": {"nodes": node_defs, "edges": edge_defs},
        "style": (
            stylesheet
            if stylesheet is not None
            else list(builder.default_stylesheet)
        ),
        "layout": resolve_layout_config(
            layout=layout,
            layout_options=layout_options,
        ),
        "ui": {"zoom": None, "pan": None},
    }


def to_json(state: Mapping[str, Any]) -> str:
    return json.dumps(dict(state))


def from_json(payload: str) -> dict[str, Any]:
    loaded = json.loads(payload)
    if not isinstance(loaded, dict):
        raise TypeError("State JSON must decode to an object")
    return cast(dict[str, Any], loaded)
