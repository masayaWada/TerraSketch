"""Terraformリソースタイプとdraw.ioシェイプ/スタイルのマッピング。

Terraformリソースタイプをdraw.ioのシェイプ識別子とビジュアルスタイルに対応付ける。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DrawioStyle:
    """draw.ioノードのビジュアルスタイル情報。"""

    shape: str
    width: float = 60.0
    height: float = 60.0
    style: str = ""


# AWSリソースタイプ -> draw.ioスタイル マッピング
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

# Azureリソースタイプ -> draw.ioスタイル マッピング
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

# GCPリソースタイプ -> draw.ioスタイル マッピング
_GCP_MAPPING: dict[str, DrawioStyle] = {
    "google_compute_instance": DrawioStyle(
        shape="mxgraph.gcp2.compute_engine",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.gcp2.compute_engine;",
    ),
    "google_compute_network": DrawioStyle(
        shape="mxgraph.gcp2.virtual_private_cloud",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.gcp2.virtual_private_cloud;",
    ),
    "google_compute_subnetwork": DrawioStyle(
        shape="mxgraph.gcp2.virtual_private_cloud",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.gcp2.virtual_private_cloud;",
    ),
    "google_compute_firewall": DrawioStyle(
        shape="mxgraph.gcp2.cloud_firewall_rules",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.gcp2.cloud_firewall_rules;",
    ),
    "google_compute_address": DrawioStyle(
        shape="mxgraph.gcp2.external_ip_addresses",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.gcp2.external_ip_addresses;",
    ),
    "google_compute_router": DrawioStyle(
        shape="mxgraph.gcp2.cloud_router",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.gcp2.cloud_router;",
    ),
}

# 未マッピングリソース用のデフォルトスタイル
_DEFAULT_STYLE = DrawioStyle(
    shape="rounded=1",
    width=120, height=60,
    style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;",
)


def _load_extended() -> None:
    """初回ミス時に拡張リソースマッピングを遅延ロードする。"""
    global _extended_loaded
    if _extended_loaded:
        return
    _extended_loaded = True
    try:
        from terrasketch.mapping.extended_resources import (
            EXTENDED_AWS_MAPPING,
            EXTENDED_AZURE_MAPPING,
            EXTENDED_GCP_MAPPING,
        )
        _AWS_MAPPING.update(EXTENDED_AWS_MAPPING)
        _AZURE_MAPPING.update(EXTENDED_AZURE_MAPPING)
        _GCP_MAPPING.update(EXTENDED_GCP_MAPPING)
    except ImportError:
        pass


_extended_loaded = False


def get_drawio_style(resource_type: str) -> DrawioStyle:
    """Terraformリソースタイプに対応するdraw.ioスタイルを取得する。

    Args:
        resource_type: Terraformリソースタイプ（例: 'aws_vpc'）。

    Returns:
        シェイプとスタイル情報を含むDrawioStyle。
    """
    if resource_type in _AWS_MAPPING:
        return _AWS_MAPPING[resource_type]
    if resource_type in _AZURE_MAPPING:
        return _AZURE_MAPPING[resource_type]
    if resource_type in _GCP_MAPPING:
        return _GCP_MAPPING[resource_type]

    # 拡張マッピングを試行
    _load_extended()
    if resource_type in _AWS_MAPPING:
        return _AWS_MAPPING[resource_type]
    if resource_type in _AZURE_MAPPING:
        return _AZURE_MAPPING[resource_type]
    if resource_type in _GCP_MAPPING:
        return _GCP_MAPPING[resource_type]

    return _DEFAULT_STYLE


def get_provider_from_type(resource_type: str) -> str:
    """Terraformリソースタイプからクラウドプロバイダを推定する。

    Args:
        resource_type: Terraformリソースタイプ文字列。

    Returns:
        プロバイダ識別子（'aws', 'azure', または 'unknown'）。
    """
    if resource_type.startswith("aws_"):
        return "aws"
    if resource_type.startswith("azurerm_"):
        return "azure"
    if resource_type.startswith("google_"):
        return "gcp"
    return "unknown"
