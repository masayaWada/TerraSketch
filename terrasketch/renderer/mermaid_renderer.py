"""Mermaidダイアグラムレンダラー。

リソースグラフからMermaid flowchart構文を生成する。
GitHub、GitLab、Notion等のMermaid対応ビューアで表示可能。
"""

from __future__ import annotations

import re
from pathlib import Path

import networkx as nx

from terrasketch.parser.state_parser import Resource


# リソースタイプごとのMermaidノード形状
_SHAPE_MAP: dict[str, tuple[str, str]] = {
    "aws_vpc": ("[[", "]]"),           # サブルーチン（二重括弧）
    "aws_subnet": ("[[", "]]"),
    "aws_instance": ("[", "]"),        # 矩形
    "aws_security_group": ("{{", "}}"),  # 六角形
    "aws_s3_bucket": ("[(", ")]"),     # 円筒形
    "aws_db_instance": ("[(", ")]"),
    "aws_lambda_function": (">", "]"), # 非対称
    "aws_lb": ("([", "])"),            # スタジアム形
}

_DEFAULT_SHAPE = ("[", "]")


def _sanitize_id(address: str) -> str:
    """リソースアドレスを有効なMermaidノードIDに変換する。"""
    return re.sub(r"[^a-zA-Z0-9_]", "_", address)


def _get_shape(resource_type: str) -> tuple[str, str]:
    """リソースタイプに対応するMermaidの形状括弧を取得する。"""
    return _SHAPE_MAP.get(resource_type, _DEFAULT_SHAPE)


class MermaidRenderer:
    """Terraformリソースグラフをmermaid flowchartとしてレンダリングする。"""

    def render(
        self,
        graph: nx.DiGraph,
        positions: dict[str, tuple[float, float]],
        output_path: str | Path,
    ) -> Path:
        """グラフをMermaid markdownファイルとしてレンダリングする。

        Args:
            graph: リソース依存関係グラフ。
            positions: ノード座標（並び順の参考として使用、ピクセル配置には非使用）。
            output_path: 出力.mdファイルのパス。

        Returns:
            書き出されたMermaidファイルのPath。
        """
        output_path = Path(output_path).with_suffix(".md")
        lines: list[str] = []
        lines.append("```mermaid")
        lines.append("flowchart TD")

        # プロバイダ別にノードをグループ化（subgraphスタイリング用）
        provider_groups: dict[str, list[str]] = {}
        for node_addr in graph.nodes:
            data = graph.nodes[node_addr]
            resource: Resource | None = data.get("resource")
            if resource is None:
                continue

            provider = _detect_provider(resource.type)
            provider_groups.setdefault(provider, []).append(node_addr)

        # プロバイダ別にノードを出力
        for provider, nodes in sorted(provider_groups.items()):
            if provider != "unknown":
                lines.append(f"    subgraph {provider.upper()}")

            for node_addr in sorted(nodes):
                data = graph.nodes[node_addr]
                resource = data.get("resource")
                if resource is None:
                    continue

                node_id = _sanitize_id(node_addr)
                label = f"{resource.type}\\n{resource.name}"
                open_b, close_b = _get_shape(resource.type)
                lines.append(f"        {node_id}{open_b}\"{label}\"{close_b}")

            if provider != "unknown":
                lines.append("    end")

        # エッジを出力
        for source, target in graph.edges:
            src_id = _sanitize_id(source)
            tgt_id = _sanitize_id(target)

            edge_data = graph.edges[source, target]
            label = edge_data.get("label", "")
            if label:
                lines.append(f"    {src_id} -->|\"{label}\"| {tgt_id}")
            else:
                lines.append(f"    {src_id} --> {tgt_id}")

        # スタイルクラス定義
        lines.append("")
        lines.append("    classDef vpc fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px")
        lines.append("    classDef subnet fill:#e3f2fd,stroke:#1565c0,stroke-width:1px")
        lines.append("    classDef compute fill:#fff3e0,stroke:#e65100,stroke-width:1px")
        lines.append("    classDef security fill:#fce4ec,stroke:#b71c1c,stroke-width:1px")
        lines.append("    classDef storage fill:#f3e5f5,stroke:#6a1b9a,stroke-width:1px")

        # スタイルを各ノードに適用
        for node_addr in graph.nodes:
            data = graph.nodes[node_addr]
            resource = data.get("resource")
            if resource is None:
                continue
            node_id = _sanitize_id(node_addr)
            css_class = _classify_resource(resource.type)
            if css_class:
                lines.append(f"    class {node_id} {css_class}")

        lines.append("```")
        lines.append("")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines), encoding="utf-8")
        return output_path


def _detect_provider(resource_type: str) -> str:
    """リソースタイプからプロバイダを判定する。"""
    if resource_type.startswith("aws_"):
        return "aws"
    if resource_type.startswith("azurerm_"):
        return "azure"
    return "unknown"


def _classify_resource(resource_type: str) -> str:
    """リソースタイプをMermaidスタイリング用のCSSクラスに分類する。"""
    if "vpc" in resource_type or "virtual_network" in resource_type:
        return "vpc"
    if "subnet" in resource_type:
        return "subnet"
    if any(k in resource_type for k in ("instance", "virtual_machine", "lambda", "ecs")):
        return "compute"
    if any(k in resource_type for k in ("security_group", "network_security", "firewall")):
        return "security"
    if any(k in resource_type for k in ("s3", "storage", "db_instance", "rds")):
        return "storage"
    return ""
