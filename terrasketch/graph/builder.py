"""Graph builder for Terraform resources.

Constructs a directed graph (DiGraph) representing the relationships
between Terraform resources based on attribute references.
"""

from __future__ import annotations

import networkx as nx

from terrasketch.parser.state_parser import Resource


# Maps (resource_type, attribute_name) -> target resource type.
# The attribute value is expected to be the ID of the target resource.
_AWS_RELATIONSHIP_RULES: list[tuple[str, str, str]] = [
    ("aws_subnet", "vpc_id", "aws_vpc"),
    ("aws_instance", "subnet_id", "aws_subnet"),
    ("aws_security_group", "vpc_id", "aws_vpc"),
    ("aws_instance", "vpc_security_group_ids", "aws_security_group"),
    ("aws_network_interface", "subnet_id", "aws_subnet"),
    ("aws_nat_gateway", "subnet_id", "aws_subnet"),
    ("aws_route_table", "vpc_id", "aws_vpc"),
    ("aws_internet_gateway", "vpc_id", "aws_vpc"),
]

_AZURE_RELATIONSHIP_RULES: list[tuple[str, str, str]] = [
    ("azurerm_subnet", "virtual_network_name", "azurerm_virtual_network"),
    ("azurerm_linux_virtual_machine", "network_interface_ids", "azurerm_network_interface"),
    ("azurerm_network_interface", "subnet_id", "azurerm_subnet"),
    ("azurerm_network_security_group", "resource_group_name", "azurerm_resource_group"),
]

_ALL_RULES = _AWS_RELATIONSHIP_RULES + _AZURE_RELATIONSHIP_RULES


def _build_id_index(resources: list[Resource]) -> dict[str, Resource]:
    """Build an index mapping resource IDs to Resource objects."""
    index: dict[str, Resource] = {}
    for r in resources:
        if r.id:
            index[r.id] = r
    return index


def _build_type_index(resources: list[Resource]) -> dict[str, list[Resource]]:
    """Build an index mapping resource types to lists of Resources."""
    index: dict[str, list[Resource]] = {}
    for r in resources:
        index.setdefault(r.type, []).append(r)
    return index


def build_graph(resources: list[Resource]) -> nx.DiGraph:
    """Build a directed graph of resource relationships.

    Edges point from parent to child (e.g., VPC -> Subnet -> EC2).

    Args:
        resources: List of Resource objects from the parser.

    Returns:
        A networkx DiGraph with resource addresses as node IDs.
    """
    graph = nx.DiGraph()
    id_index = _build_id_index(resources)
    type_index = _build_type_index(resources)

    # Add all resources as nodes
    for r in resources:
        graph.add_node(
            r.address,
            resource=r,
            type=r.type,
            label=f"{r.type}\n{r.name}",
        )

    # Apply relationship rules
    for src_type, attr_name, tgt_type in _ALL_RULES:
        for src in type_index.get(src_type, []):
            attr_value = src.attributes.get(attr_name)
            if attr_value is None:
                continue

            # Handle both single values and lists
            ref_ids = attr_value if isinstance(attr_value, list) else [attr_value]

            for ref_id in ref_ids:
                if not isinstance(ref_id, str):
                    continue

                # Try to find target by ID
                target = id_index.get(ref_id)
                if target and target.type == tgt_type:
                    # Edge from parent (target) to child (src)
                    graph.add_edge(target.address, src.address)
                    continue

                # Fallback: match by name for Azure resources that use names
                for candidate in type_index.get(tgt_type, []):
                    if ref_id in (candidate.name, candidate.attributes.get("name", "")):
                        graph.add_edge(candidate.address, src.address)
                        break

    return graph
