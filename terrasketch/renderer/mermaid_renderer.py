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
    # GCPリソース
    "google_compute_network": ("[[", "]]"),
    "google_compute_subnetwork": ("[[", "]]"),
    "google_compute_instance": ("[", "]"),
    "google_compute_firewall": ("{{", "}}"),
    "google_storage_bucket": ("[(", ")]"),
    "google_sql_database_instance": ("[(", ")]"),
    "google_cloudfunctions_function": (">", "]"),
    "google_container_cluster": ("[", "]"),
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
        show_labels: bool = False,
        diff_mode: bool = False,
        group_by_module: bool = False,
    ) -> Path:
        """グラフをMermaid markdownファイルとしてレンダリングする。

        Args:
            graph: リソース依存関係グラフ。
            positions: ノード座標（並び順の参考として使用、ピクセル配置には非使用）。
            output_path: 出力.mdファイルのパス。
            show_labels: エッジに接続属性名ラベルを表示するか。
            diff_mode: diff比較結果を色分けで表示するか。

        Returns:
            書き出されたMermaidファイルのPath。
        """
        output_path = Path(output_path).with_suffix(".md")
        lines: list[str] = []
        lines.append("```mermaid")
        lines.append("flowchart TD")

        # モジュール境界グルーピング（--group-by module）
        module_emitted: set[str] = set()
        if group_by_module:
            module_nodes: dict[str, list[str]] = {}
            for node_addr in graph.nodes:
                data = graph.nodes[node_addr]
                module_path = data.get("module_path", "")
                if module_path:
                    module_nodes.setdefault(module_path, []).append(node_addr)

            # モジュール subgraph を出力
            for mod_path in sorted(module_nodes.keys()):
                mod_id = _sanitize_id(mod_path)
                lines.append(f"    subgraph {mod_id}_module[\"{mod_path}\"]")
                for node_addr in sorted(module_nodes[mod_path]):
                    data = graph.nodes[node_addr]
                    resource = data.get("resource")
                    if resource is None:
                        continue
                    node_id = _sanitize_id(node_addr)
                    label = f"{resource.type}\\n{resource.name}"
                    open_b, close_b = _get_shape(resource.type)
                    lines.append(f"        {node_id}{open_b}\"{label}\"{close_b}")
                    module_emitted.add(node_addr)
                lines.append("    end")

        # VPC/VNet コンテナとSubnetコンテナの階層構造を構築
        container_types = {"aws_vpc", "azurerm_virtual_network", "google_compute_network"}
        subnet_types = {"aws_subnet", "azurerm_subnet", "google_compute_subnetwork"}

        # VPCの子ノードを収集
        vpc_children: dict[str, list[str]] = {}
        subnet_children: dict[str, list[str]] = {}
        contained_in_vpc: set[str] = set()
        contained_in_subnet: set[str] = set()

        for node_addr in graph.nodes:
            data = graph.nodes[node_addr]
            resource = data.get("resource")
            if resource is None:
                continue
            if resource.type in container_types:
                children = list(nx.descendants(graph, node_addr))
                vpc_children[node_addr] = children
                contained_in_vpc.update(children)
            elif resource.type in subnet_types:
                children = list(nx.descendants(graph, node_addr))
                subnet_children[node_addr] = children
                contained_in_subnet.update(children)

        # ノードを出力（VPC > Subnet > リソースの階層subgraph）
        emitted_nodes: set[str] = set()
        if group_by_module:
            emitted_nodes.update(module_emitted)

        for vpc_addr in sorted(vpc_children.keys()):
            vpc_data = graph.nodes[vpc_addr]
            vpc_resource = vpc_data.get("resource")
            if vpc_resource is None:
                continue
            vpc_id = _sanitize_id(vpc_addr)
            lines.append(f"    subgraph {vpc_id}_group[\"{vpc_resource.type} / {vpc_resource.name}\"]")
            emitted_nodes.add(vpc_addr)

            # VPC直下のSubnetをsubgraphとして出力
            for subnet_addr in sorted(subnet_children.keys()):
                if subnet_addr not in vpc_children.get(vpc_addr, []):
                    continue
                subnet_data = graph.nodes[subnet_addr]
                subnet_resource = subnet_data.get("resource")
                if subnet_resource is None:
                    continue
                sub_id = _sanitize_id(subnet_addr)
                lines.append(f"        subgraph {sub_id}_group[\"{subnet_resource.type} / {subnet_resource.name}\"]")
                emitted_nodes.add(subnet_addr)

                # Subnet内のリソース
                for child_addr in sorted(subnet_children[subnet_addr]):
                    if child_addr in emitted_nodes:
                        continue
                    child_data = graph.nodes[child_addr]
                    child_resource = child_data.get("resource")
                    if child_resource is None:
                        continue
                    child_node_id = _sanitize_id(child_addr)
                    label = f"{child_resource.type}\\n{child_resource.name}"
                    open_b, close_b = _get_shape(child_resource.type)
                    lines.append(f"            {child_node_id}{open_b}\"{label}\"{close_b}")
                    emitted_nodes.add(child_addr)

                lines.append("        end")

            # VPC直下（Subnet外）のリソース
            for child_addr in sorted(vpc_children[vpc_addr]):
                if child_addr in emitted_nodes:
                    continue
                child_data = graph.nodes[child_addr]
                child_resource = child_data.get("resource")
                if child_resource is None:
                    continue
                child_node_id = _sanitize_id(child_addr)
                label = f"{child_resource.type}\\n{child_resource.name}"
                open_b, close_b = _get_shape(child_resource.type)
                lines.append(f"        {child_node_id}{open_b}\"{label}\"{close_b}")
                emitted_nodes.add(child_addr)

            lines.append("    end")

        # VPC外のリソースを出力
        for node_addr in sorted(graph.nodes):
            if node_addr in emitted_nodes:
                continue
            data = graph.nodes[node_addr]
            resource = data.get("resource")
            if resource is None:
                continue
            node_id = _sanitize_id(node_addr)
            label = f"{resource.type}\\n{resource.name}"
            open_b, close_b = _get_shape(resource.type)
            lines.append(f"    {node_id}{open_b}\"{label}\"{close_b}")
            emitted_nodes.add(node_addr)

        # エッジを出力（包含関係は実線、参照関係は破線で区別）
        for source, target in graph.edges:
            src_id = _sanitize_id(source)
            tgt_id = _sanitize_id(target)

            edge_data = graph.edges[source, target]
            relation_type = edge_data.get("relation_type", "contains")
            label = edge_data.get("attr_name", "") if show_labels else ""

            if relation_type == "references":
                # 参照関係: 破線矢印
                if label:
                    lines.append(f"    {src_id} -.->|\"{label}\"| {tgt_id}")
                else:
                    lines.append(f"    {src_id} -.-> {tgt_id}")
            else:
                # 包含関係: 実線矢印
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

        if diff_mode:
            lines.append("    classDef diff_added fill:#c8e6c9,stroke:#2e7d32,stroke-width:3px")
            lines.append("    classDef diff_removed fill:#ffcdd2,stroke:#c62828,stroke-width:3px,stroke-dasharray:5 5")
            lines.append("    classDef diff_modified fill:#fff9c4,stroke:#f57f17,stroke-width:3px")

        # スタイルを各ノードに適用
        for node_addr in graph.nodes:
            data = graph.nodes[node_addr]
            resource = data.get("resource")
            if resource is None:
                continue
            node_id = _sanitize_id(node_addr)

            # diffモードではdiffステータスのスタイルを優先
            if diff_mode:
                diff_status = data.get("diff_status", "unchanged")
                if diff_status in ("added", "removed", "modified"):
                    lines.append(f"    class {node_id} diff_{diff_status}")
                    continue

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
    if resource_type.startswith("google_"):
        return "gcp"
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
