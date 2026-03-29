"""Layout engine for positioning resource nodes.

Uses graphviz (via pygraphviz or pydot) to calculate hierarchical
positions for the resource graph.
"""

from __future__ import annotations

import networkx as nx


def calculate_layout(
    graph: nx.DiGraph,
    scale_x: float = 250.0,
    scale_y: float = 200.0,
) -> dict[str, tuple[float, float]]:
    """Calculate (x, y) positions for each node in the graph.

    Uses a hierarchical layout based on topological layers for directed
    graphs, with a spring layout fallback for cyclic or disconnected graphs.

    Args:
        graph: The resource dependency graph.
        scale_x: Horizontal spacing multiplier.
        scale_y: Vertical spacing multiplier.

    Returns:
        Dictionary mapping node address to (x, y) pixel coordinates.
    """
    if len(graph.nodes) == 0:
        return {}

    if len(graph.nodes) == 1:
        node = list(graph.nodes)[0]
        return {node: (100.0, 100.0)}

    # Try hierarchical layout for DAGs
    if nx.is_directed_acyclic_graph(graph):
        return _hierarchical_layout(graph, scale_x, scale_y)

    # Fallback to spring layout
    return _spring_layout(graph, scale_x, scale_y)


def _hierarchical_layout(
    graph: nx.DiGraph,
    scale_x: float,
    scale_y: float,
) -> dict[str, tuple[float, float]]:
    """Assign positions based on topological layers."""
    # Compute longest-path layering
    layers: dict[str, int] = {}
    for node in nx.topological_sort(graph):
        preds = list(graph.predecessors(node))
        if not preds:
            layers[node] = 0
        else:
            layers[node] = max(layers[p] for p in preds) + 1

    # Group nodes by layer
    layer_groups: dict[int, list[str]] = {}
    for node, layer in layers.items():
        layer_groups.setdefault(layer, []).append(node)

    # Assign coordinates
    positions: dict[str, tuple[float, float]] = {}
    start_x = 100.0
    start_y = 100.0

    for layer_idx in sorted(layer_groups):
        nodes_in_layer = sorted(layer_groups[layer_idx])
        total_width = (len(nodes_in_layer) - 1) * scale_x
        offset_x = start_x - total_width / 2

        for i, node in enumerate(nodes_in_layer):
            x = offset_x + i * scale_x
            y = start_y + layer_idx * scale_y
            positions[node] = (x, y)

    # Normalize so no negative coordinates
    if positions:
        min_x = min(p[0] for p in positions.values())
        min_y = min(p[1] for p in positions.values())
        offset_x = 100.0 - min_x if min_x < 100.0 else 0.0
        offset_y = 100.0 - min_y if min_y < 100.0 else 0.0
        if offset_x or offset_y:
            positions = {
                n: (x + offset_x, y + offset_y) for n, (x, y) in positions.items()
            }

    return positions


def _spring_layout(
    graph: nx.DiGraph,
    scale_x: float,
    scale_y: float,
) -> dict[str, tuple[float, float]]:
    """Fallback grid layout for non-DAG (cyclic) graphs.

    Arranges nodes in a simple grid pattern. This avoids a numpy
    dependency that nx.spring_layout requires.
    """
    import math

    nodes = sorted(graph.nodes)
    cols = max(1, math.ceil(math.sqrt(len(nodes))))

    positions: dict[str, tuple[float, float]] = {}
    for i, node in enumerate(nodes):
        row = i // cols
        col = i % cols
        x = 100.0 + col * scale_x
        y = 100.0 + row * scale_y
        positions[node] = (x, y)

    return positions
