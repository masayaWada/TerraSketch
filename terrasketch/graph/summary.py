"""リソースサマリーの生成。

解析済みTerraformリソースの人間が読めるサマリーを生成する。
CLIの出力やログ表示に使用。
"""

from __future__ import annotations

from collections import Counter

import networkx as nx

from terrasketch.parser.state_parser import Resource


def generate_summary(resources: list[Resource], graph: nx.DiGraph) -> str:
    """リソースと依存関係のテキストサマリーを生成する。

    Args:
        resources: 解析済みリソースのリスト。
        graph: リソースから構築された依存関係グラフ。

    Returns:
        フォーマット済みのサマリー文字列。
    """
    lines: list[str] = []

    lines.append("=" * 60)
    lines.append("  TerraSketch Resource Summary")
    lines.append("=" * 60)
    lines.append("")

    # タイプ別リソース数
    type_counts = Counter(r.type for r in resources)
    lines.append(f"Total resources: {len(resources)}")
    lines.append("")
    lines.append("Resources by type:")
    for rtype, count in sorted(type_counts.items()):
        lines.append(f"  {rtype}: {count}")

    lines.append("")

    # プロバイダ別内訳
    provider_counts = Counter(_detect_provider(r.type) for r in resources)
    lines.append("Resources by provider:")
    for provider, count in sorted(provider_counts.items()):
        lines.append(f"  {provider}: {count}")

    lines.append("")

    # グラフ統計
    lines.append("Graph statistics:")
    lines.append(f"  Nodes: {graph.number_of_nodes()}")
    lines.append(f"  Edges: {graph.number_of_edges()}")

    if graph.number_of_nodes() > 0:
        components = nx.number_weakly_connected_components(graph)
        lines.append(f"  Connected components: {components}")

        # ルートノード（入次数0）
        roots = [n for n in graph.nodes if graph.in_degree(n) == 0]
        lines.append(f"  Root resources: {len(roots)}")
        for r in roots:
            lines.append(f"    - {r}")

        # リーフノード（出次数0）
        leaves = [n for n in graph.nodes if graph.out_degree(n) == 0]
        lines.append(f"  Leaf resources: {len(leaves)}")
        for leaf in leaves:
            lines.append(f"    - {leaf}")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


def _detect_provider(resource_type: str) -> str:
    """リソースタイプからクラウドプロバイダを判定する。"""
    if resource_type.startswith("aws_"):
        return "AWS"
    if resource_type.startswith("azurerm_"):
        return "Azure"
    return "Other"
