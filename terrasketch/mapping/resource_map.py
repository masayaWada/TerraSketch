"""Resource mapping between Terraform types and draw.io shapes/styles.

Maps Terraform resource types to draw.io shape identifiers and visual styles.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DrawioStyle:
    """Visual style information for a draw.io node."""

    shape: str
    width: float = 60.0
    height: float = 60.0
    style: str = ""


# AWS resource type -> draw.io style mapping
_AWS_MAPPING: dict[str, DrawioStyle] = {
    "aws_vpc": DrawioStyle(
        shape="mxgraph.aws4.vpc",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.vpc;",
    ),
    "aws_subnet": DrawioStyle(
        shape="mxgraph.aws4.subnet",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.subnet;",
    ),
    "aws_instance": DrawioStyle(
        shape="mxgraph.aws4.ec2",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.ec2;",
    ),
    "aws_security_group": DrawioStyle(
        shape="mxgraph.aws4.security_group",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.security_group;",
    ),
    "aws_internet_gateway": DrawioStyle(
        shape="mxgraph.aws4.internet_gateway",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.internet_gateway;",
    ),
    "aws_nat_gateway": DrawioStyle(
        shape="mxgraph.aws4.nat_gateway",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.nat_gateway;",
    ),
    "aws_route_table": DrawioStyle(
        shape="mxgraph.aws4.route_table",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.route_table;",
    ),
    "aws_network_interface": DrawioStyle(
        shape="mxgraph.aws4.elastic_network_interface",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.elastic_network_interface;",
    ),
}

# Azure resource type -> draw.io style mapping
_AZURE_MAPPING: dict[str, DrawioStyle] = {
    "azurerm_virtual_network": DrawioStyle(
        shape="mxgraph.azure.virtual_network",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.azure.virtual_network;",
    ),
    "azurerm_subnet": DrawioStyle(
        shape="mxgraph.azure.subnet",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.azure.subnet;",
    ),
    "azurerm_linux_virtual_machine": DrawioStyle(
        shape="mxgraph.azure.virtual_machine",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.azure.virtual_machine;",
    ),
    "azurerm_network_security_group": DrawioStyle(
        shape="mxgraph.azure.network_security_group",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.azure.network_security_group;",
    ),
    "azurerm_resource_group": DrawioStyle(
        shape="mxgraph.azure.resource_group",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.azure.resource_group;",
    ),
    "azurerm_network_interface": DrawioStyle(
        shape="mxgraph.azure.network_interface_card",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.azure.network_interface_card;",
    ),
}

# Default style for unmapped resources
_DEFAULT_STYLE = DrawioStyle(
    shape="rounded=1",
    width=120, height=60,
    style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;",
)


def get_drawio_style(resource_type: str) -> DrawioStyle:
    """Get the draw.io style for a Terraform resource type.

    Args:
        resource_type: Terraform resource type (e.g., 'aws_vpc').

    Returns:
        DrawioStyle with shape and style information.
    """
    if resource_type in _AWS_MAPPING:
        return _AWS_MAPPING[resource_type]
    if resource_type in _AZURE_MAPPING:
        return _AZURE_MAPPING[resource_type]
    return _DEFAULT_STYLE


def get_provider_from_type(resource_type: str) -> str:
    """Infer the cloud provider from a Terraform resource type.

    Args:
        resource_type: Terraform resource type string.

    Returns:
        Provider identifier ('aws', 'azure', or 'unknown').
    """
    if resource_type.startswith("aws_"):
        return "aws"
    if resource_type.startswith("azurerm_"):
        return "azure"
    return "unknown"
