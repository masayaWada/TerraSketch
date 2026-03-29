"""Security group rule visualization.

Extracts security group rules from resource attributes and annotates
graph edges with human-readable rule summaries.
"""

from __future__ import annotations

from typing import Any

import networkx as nx

from terrasketch.parser.state_parser import Resource


def annotate_security_rules(graph: nx.DiGraph) -> nx.DiGraph:
    """Annotate graph edges with security group rule information.

    For each security group node, extracts ingress/egress rules and
    adds them as labels on the edges connecting the SG to other resources.

    Args:
        graph: The resource dependency graph (modified in place).

    Returns:
        The same graph with annotated edge labels.
    """
    for node_addr in list(graph.nodes):
        data = graph.nodes[node_addr]
        resource: Resource | None = data.get("resource")
        if resource is None:
            continue

        if resource.type not in ("aws_security_group", "azurerm_network_security_group"):
            continue

        rules_summary = _summarize_rules(resource)
        if rules_summary:
            graph.nodes[node_addr]["security_rules"] = rules_summary
            # Add rule summary to the node label
            short_summary = _short_summary(resource)
            if short_summary:
                current_label = graph.nodes[node_addr].get("label", "")
                graph.nodes[node_addr]["label"] = f"{current_label}\n{short_summary}"

    return graph


def _summarize_rules(resource: Resource) -> list[dict[str, Any]]:
    """Extract and summarize security rules from a resource's attributes."""
    rules: list[dict[str, Any]] = []

    # AWS Security Group
    for direction in ("ingress", "egress"):
        raw_rules = resource.attributes.get(direction, [])
        if not isinstance(raw_rules, list):
            continue
        for rule in raw_rules:
            if not isinstance(rule, dict):
                continue
            rules.append({
                "direction": direction,
                "from_port": rule.get("from_port", "*"),
                "to_port": rule.get("to_port", "*"),
                "protocol": rule.get("protocol", "all"),
                "cidr_blocks": rule.get("cidr_blocks", []),
                "description": rule.get("description", ""),
            })

    # Azure NSG
    for rule in resource.attributes.get("security_rule", []):
        if not isinstance(rule, dict):
            continue
        rules.append({
            "direction": rule.get("direction", "").lower(),
            "from_port": rule.get("destination_port_range", "*"),
            "to_port": rule.get("destination_port_range", "*"),
            "protocol": rule.get("protocol", "*"),
            "cidr_blocks": [rule.get("source_address_prefix", "")],
            "description": rule.get("name", ""),
            "access": rule.get("access", ""),
        })

    return rules


def _short_summary(resource: Resource) -> str:
    """Generate a short one-line summary of security rules."""
    parts: list[str] = []

    for direction in ("ingress", "egress"):
        raw_rules = resource.attributes.get(direction, [])
        if not isinstance(raw_rules, list):
            continue
        for rule in raw_rules:
            if not isinstance(rule, dict):
                continue
            proto = rule.get("protocol", "all")
            from_p = rule.get("from_port", "*")
            to_p = rule.get("to_port", "*")

            if from_p == to_p:
                port_str = str(from_p)
            else:
                port_str = f"{from_p}-{to_p}"

            arrow = "IN" if direction == "ingress" else "OUT"
            parts.append(f"{arrow}:{proto}/{port_str}")

    if not parts:
        return ""

    # Limit to first 3 rules to keep label readable
    display = parts[:3]
    if len(parts) > 3:
        display.append(f"+{len(parts) - 3} more")

    return " | ".join(display)


def get_rules_table(resource: Resource) -> str:
    """Generate a detailed rules table as a string.

    Useful for tooltips or detailed views.

    Args:
        resource: A security group Resource.

    Returns:
        Formatted string table of all rules.
    """
    rules = _summarize_rules(resource)
    if not rules:
        return "No rules defined."

    lines = [
        f"{'Dir':<8} {'Proto':<6} {'Ports':<12} {'CIDR':<20} {'Desc'}",
        "-" * 70,
    ]

    for r in rules:
        direction = r["direction"].upper()
        proto = str(r["protocol"])
        from_p = r["from_port"]
        to_p = r["to_port"]
        ports = str(from_p) if from_p == to_p else f"{from_p}-{to_p}"
        cidrs = ", ".join(r.get("cidr_blocks", []))
        desc = r.get("description", "")
        lines.append(f"{direction:<8} {proto:<6} {ports:<12} {cidrs:<20} {desc}")

    return "\n".join(lines)
