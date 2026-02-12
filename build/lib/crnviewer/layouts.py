from __future__ import annotations

from collections import defaultdict, deque
from typing import Iterable, Literal

Direction = Literal["RIGHT", "LEFT", "DOWN", "UP"]


def _topological_layers(edges: Iterable[tuple[str, str]]) -> list[list[str]]:
    """Simple Kahn-based layering; cycles fall back to a single layer.

    Returns list of layers where each layer is a list of node ids.
    """

    outgoing: dict[str, set[str]] = defaultdict(set)
    indegree: dict[str, int] = defaultdict(int)
    nodes: set[str] = set()

    for src, tgt in edges:
        outgoing[src].add(tgt)
        indegree[tgt] += 1
        nodes.add(src)
        nodes.add(tgt)
    for n in nodes:
        indegree.setdefault(n, 0)
        outgoing.setdefault(n, set())

    q = deque([n for n, deg in indegree.items() if deg == 0])
    layers: list[list[str]] = []
    placed: set[str] = set()

    while q:
        layer = list(q)
        layers.append(layer)
        for n in list(q):
            q.popleft()
            placed.add(n)
            for m in outgoing[n]:
                indegree[m] -= 1
                if indegree[m] == 0:
                    q.append(m)

    if len(placed) != len(nodes):
        # Cycle detected: put everything in one layer to avoid crashing
        return [list(nodes)]

    return layers


def layered_preset_positions(
    nodes: list[dict],
    edges: list[dict],
    *,
    direction: Direction = "RIGHT",
    layer_spacing: float = 220.0,
    node_spacing: float = 180.0,
) -> list[dict]:
    """Assign deterministic layered positions for a Cytoscape preset layout.

    Useful when a notebook frontend (e.g., ipycytoscape) cannot load custom
    layout plugins like ELK. This creates a simple DAG-style layered layout
    server-side and returns node dictionaries with ``position`` filled in.

    Directions:
      RIGHT (default): x grows by layers, y stacks nodes
      LEFT: x decreases by layers
      DOWN: y grows by layers
      UP: y decreases by layers
    """

    id_to_node = {n["data"]["id"]: dict(n) for n in nodes}
    edge_pairs = [
        (e["data"]["source"], e["data"]["target"])
        for e in edges
        if "data" in e and "source" in e["data"] and "target" in e["data"]
    ]

    layers = _topological_layers(edge_pairs)

    for layer_idx, layer_nodes in enumerate(layers):
        for pos_idx, node_id in enumerate(layer_nodes):
            x = layer_idx * layer_spacing
            y = pos_idx * node_spacing
            id_to_node[node_id]["position"] = {"x": x, "y": y}

    if direction == "LEFT":
        for node in id_to_node.values():
            node["position"]["x"] *= -1
    elif direction == "DOWN":
        for node in id_to_node.values():
            node["position"]["x"], node["position"]["y"] = (
                node["position"]["y"],
                node["position"]["x"],
            )
    elif direction == "UP":
        for node in id_to_node.values():
            node["position"]["x"], node["position"]["y"] = (
                node["position"]["y"],
                -node["position"]["x"],
            )

    return list(id_to_node.values())
