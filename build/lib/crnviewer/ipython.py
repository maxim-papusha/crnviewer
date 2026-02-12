from __future__ import annotations

import base64
from collections import defaultdict
from collections.abc import Hashable, Iterable, Mapping
from types import MappingProxyType
from typing import Any, Callable, ClassVar, Generic, Literal, Protocol, TypeVar

R = TypeVar("R", bound=Hashable)
S = TypeVar("S", bound=Hashable)


class ReactionContainerLike(Protocol[R, S]):
    """Structural protocol for reaction containers used by ``CyBuilder``."""

    @property
    def species(self) -> Iterable[S]:
        ...

    @property
    def reactions(self) -> Iterable[R]:
        ...

    def reactants_and_products_from_reaction(
        self, reaction: R
    ) -> tuple[Iterable[S], Iterable[S]]:
        ...


class CyBuilder(Generic[R, S]):
    """Minimal builder that only knows about nodes and edges."""

    nodes: dict[R | S, dict[str, Any]]
    edges: list[dict[str, Any]]
    xyz: bool = False
    default_color = "grey"
    node_size: tuple[int, int] = (300, 300)
    label_size: str = "30px"
    layout: Mapping[str, Any] = MappingProxyType({"name": "klay"})
    default_stylesheet: ClassVar[tuple[dict[str, Any], ...]] = (
        {
            "selector": "node",
            "style": {
                "width": node_size[0],
                "height": node_size[1],
                "shape": "roundrectangle",
                "background-color": "#fafafa",
                "border-color": "#888",
                "border-width": 2,
                "label": "data(label)",
                "font-size": label_size,
                "text-valign": "bottom",
                "text-halign": "center",
                "text-margin-y": "10px",
                "color": "#111",
                "padding": "6px",
            },
        },
        {
            "selector": "node[image]",
            "style": {
                "background-image": "data(image)",
                "background-fit": "contain",
                "background-clip": "node",
                "background-opacity": 1,
            },
        },
        {
            "selector": "edge",
            "style": {
                "curve-style": "bezier",
                "width": 2,
                "line-color": "data(color)",
                "target-arrow-color": "data(color)",
                "target-arrow-shape": "triangle",
            },
        },
    )

    def __init__(self) -> None:
        self.nodes = defaultdict(dict)
        self.edges = []

    def elements(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Return Cytoscape-friendly nodes and edges.

        Nodes may optionally contain an ``image`` data field; a stylesheet can
        reference it via ``background-image: data(image)``.
        """
        node_defs: list[dict[str, Any]] = []
        edge_defs: list[dict[str, Any]] = []
        node_ids: dict[R | S, int] = {}

        for i, (node, data) in enumerate(self.nodes.items()):
            node_ids[node] = i
            node_classes = " ".join(data.get("classes", [])) or "node"
            payload: dict[str, Any] = {
                "classes": node_classes,
                "position": {"x": 0, "y": 0},
                "data": {
                    "id": str(i),
                    "color": str(data.get("color", self.default_color)),
                },
            }

            label = data.get("label")
            if label is not None:
                payload["data"]["label"] = str(label)

            image = data.get("image")
            if image:
                payload["data"]["image"] = image

            node_defs.append(payload)

        for edge in self.edges:
            source = edge["source"]
            target = edge["target"]
            arrow = edge.get("arrow", True)
            edge_classes = " ".join(edge.get("classes", [])) or "edge"
            style = {"target-arrow-shape": "triangle"}
            if arrow is False:
                style["target-arrow-shape"] = "none"
            elif arrow == "double_headed":
                style["source-arrow-shape"] = "triangle"

            edge_defs.append(
                {
                    "classes": edge_classes,
                    "data": {
                        "source": str(node_ids[source]),
                        "target": str(node_ids[target]),
                        "color": str(edge.get("color", self.default_color)),
                    },
                    "style": style,
                }
            )

        return node_defs, edge_defs

    def add_node(
        self,
        node: R | S,
        *,
        label: str | None = None,
        image: str | None = None,
        classes: Iterable[str] | None = None,
    ) -> CyBuilder[R, S]:
        self.nodes[node] = {
            "label": label,
            "image": image,
            "classes": list(classes) if classes is not None else [],
        }
        return self

    def add_edge(
        self,
        source: R | S,
        target: R | S,
        *,
        arrow: Literal[False, True, "double_headed"] = True,
        classes: Iterable[str] | None = None,
    ) -> CyBuilder[R, S]:
        self.edges.append(
            {
                "source": source,
                "target": target,
                "arrow": arrow,
                "classes": list(classes) if classes is not None else [],
            }
        )
        return self

    @staticmethod
    def _svg_data_uri(svg: str) -> str:
        payload = base64.b64encode(svg.encode("utf-8")).decode("ascii")
        return f"data:image/svg+xml;base64,{payload}"


def _make_image(renderer: Any, obj: Hashable) -> str | None:
    if renderer is None or not hasattr(renderer, "svg"):
        return None
    svg = renderer.svg(obj)  # type: ignore[arg-type]
    return CyBuilder._svg_data_uri(svg)


def _make_label(
    label_func: Callable[[Hashable], str] | None,
    obj: Hashable,
    fallback: str,
) -> str | None:
    if label_func is None:
        return None
    try:
        return str(label_func(obj))
    except Exception:
        return fallback


def build_builder_from_container(
    container: ReactionContainerLike[R, S],
    *,
    view: Any | None = None,
    label_func: Callable[[Hashable], str] | None = None,
    skip_species: Iterable[S] | None = None,
    skip_reactions: Iterable[R] | None = None,
) -> CyBuilder[R, S]:
    """Create a ``CyBuilder`` from a reaction container, optionally skipping
    specific species or reactions."""

    try:
        from stereomolgraph.ipython import View2D
    except Exception:  # pragma: no cover - optional dependency
        View2D = None  # type: ignore

    builder: CyBuilder[R, S] = CyBuilder()
    excluded_species = set(skip_species or [])
    excluded_reactions = set(skip_reactions or [])

    renderer = view
    if renderer is None and View2D is not None:
        renderer = View2D(
            width=builder.node_size[0], height=builder.node_size[1]
        )

    for species in container.species:
        if species in excluded_species:
            continue
        builder.add_node(
            species,
            label=_make_label(label_func, species, str(species)),
            image=_make_image(renderer, species),
            classes=["species"],
        )

    for idx, reaction in enumerate(container.reactions, start=1):
        if reaction in excluded_reactions:
            continue
        builder.add_node(
            reaction,
            label=_make_label(label_func, reaction, f"rxn {idx}"),
            image=_make_image(renderer, reaction),
            classes=["reaction"],
        )
        reactants, products = container.reactants_and_products_from_reaction(
            reaction
        )
        for r in reactants:
            if r in excluded_species:
                continue
            builder.add_edge(r, reaction)
        for p in products:
            if p in excluded_species:
                continue
            builder.add_edge(reaction, p)

    return builder


def container_elements(
    container: ReactionContainerLike[R, S],
    *,
    view: Any | None = None,
    label_func: Callable[[Hashable], str] | None = None,
    skip_species: Iterable[S] | None = None,
    skip_reactions: Iterable[R] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return Cytoscape-ready (nodes, edges) for a reaction container.

    ``skip_species`` and ``skip_reactions`` filter out matching nodes and their
    incident edges.
    """

    builder = build_builder_from_container(
        container,
        view=view,
        label_func=label_func,
        skip_species=skip_species,
        skip_reactions=skip_reactions,
    )
    return builder.elements()


def display_crg_container_with_images(
    container: ReactionContainerLike[R, S],
    *,
    label_func: Callable[[Hashable], str] | None = None,
    skip_species: Iterable[S] | None = None,
    skip_reactions: Iterable[R] | None = None,
    height: str = "700px",
    width: str = "100%",
):
    """Display a reaction container with embedded SVG molecule depictions.

    Uses ``stereomolgraph.ipython.View2D`` when available to render SVGs for
    species and reaction nodes. Falls back to the plain widget when rendering
    is unavailable.
    """

    try:
        from stereomolgraph.ipython import View2D
    except Exception:
        View2D = None  # type: ignore

    view = None
    if View2D is not None:
        view = View2D(width=CyBuilder.node_size[0], height=CyBuilder.node_size[1])

    return display_container_widget(
        container,
        view=view,
        label_func=label_func,
        skip_species=skip_species,
        skip_reactions=skip_reactions,
        height=height,
        width=width,
    )


def display_container_widget(
    container: ReactionContainerLike[R, S],
    *,
    view: Any | None = None,
    label_func: Callable[[Hashable], str] | None = None,
    skip_species: Iterable[S] | None = None,
    skip_reactions: Iterable[R] | None = None,
    height: str = "700px",
    width: str = "100%",
):
    """Display a reaction container using ipycytoscape if available.

    Falls back to `display_container` (HTML iframe) when ipycytoscape is not
    installed.
    """

    import ipycytoscape as cy  # type: ignore

    nodes, edges = container_elements(
        container,
        view=view,
        label_func=label_func,
        skip_species=skip_species,
        skip_reactions=skip_reactions,
    )

    graph = {"nodes": nodes, "edges": edges}
    widget = cy.CytoscapeWidget()
    widget.graph.add_graph_from_json(graph)
    widget.set_style(list(CyBuilder.default_stylesheet))
    widget.set_layout(**dict(CyBuilder.layout))
    widget.layout.height = height
    widget.layout.width = width
    return widget
