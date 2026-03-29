"""Resource summary generation.

Produces human-readable summaries of the parsed Terraform resources,
useful for CLI output and logging.
"""

from __future__ import annotations

from collections import Counter

import networkx as nx

from terrasketch.parser.state_parser import Resource


def generate_summary(resources: list[Resource], graph: nx.DiGraph) -> str:
    """Generate a text summary of resources and their relationships.

    Args:
        resources: List of parsed resources.
        graph: The dependency graph built from the resources.

    Returns:
        A formatted summary string.
    """
    lines: list[str] = []

    lines.append("=" * 60)
    lines.append("  TerraSketch Resource Summary")
    lines.append("=" * 60)
    lines.append("")

    # Resource count by type
    type_counts = Counter(r.type for r in resources)
    lines.append(f"Total resources: {len(resources)}")
    lines.append("")
    lines.append("Resources by type:")
    for rtype, count in sorted(type_counts.items()):
        lines.append(f"  {rtype}: {count}")

    lines.append("")

    # Provider breakdown
    provider_counts = Counter(_detect_provider(r.type) for r in resources)
    lines.append("Resources by provider:")
    for provider, count in sorted(provider_counts.items()):
        lines.append(f"  {provider}: {count}")

    lines.append("")

    # Graph statistics
    lines.append("Graph statistics:")
    lines.append(f"  Nodes: {graph.number_of_nodes()}")
    lines.append(f"  Edges: {graph.number_of_edges()}")

    if graph.number_of_nodes() > 0:
        components = nx.number_weakly_connected_components(graph)
        lines.append(f"  Connected components: {components}")

        # Root nodes (no incoming edges)
        roots = [n for n in graph.nodes if graph.in_degree(n) == 0]
        lines.append(f"  Root resources: {len(roots)}")
        for r in roots:
            lines.append(f"    - {r}")

        # Leaf nodes (no outgoing edges)
        leaves = [n for n in graph.nodes if graph.out_degree(n) == 0]
        lines.append(f"  Leaf resources: {len(leaves)}")
        for l in leaves:
            lines.append(f"    - {l}")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


def _detect_provider(resource_type: str) -> str:
    if resource_type.startswith("aws_"):
        return "AWS"
    if resource_type.startswith("azurerm_"):
        return "Azure"
    return "Other"
