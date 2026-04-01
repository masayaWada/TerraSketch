"""セキュリティグループルールの可視化。

リソース属性からセキュリティグループのルールを抽出し、
グラフのエッジやノードに人間が読める形式のルールサマリーを付与する。
ツールチップにルールテーブルを統合し、Allow/Deny色分けに対応。
"""

from __future__ import annotations

from typing import Any

import networkx as nx

from terrasketch.parser.state_parser import Resource


def annotate_security_rules(graph: nx.DiGraph) -> nx.DiGraph:
    """グラフにセキュリティグループのルール情報を付与する。

    各セキュリティグループノードからingress/egressルールを抽出し、
    ノードラベルにルールサマリー、ツールチップにルールテーブルを追加する。

    Args:
        graph: リソース依存関係グラフ（インプレースで変更）。

    Returns:
        ルール情報が付与された同一のグラフ。
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
            # ノードラベルにルールサマリーを追加
            short_summary = _short_summary(resource)
            if short_summary:
                current_label = graph.nodes[node_addr].get("label", "")
                graph.nodes[node_addr]["label"] = f"{current_label}\n{short_summary}"

            # ツールチップにルールテーブルを追加
            rules_table = get_rules_table(resource)
            graph.nodes[node_addr]["security_tooltip"] = rules_table

            # ポート情報をエッジ注釈として付与
            _annotate_port_edges(graph, node_addr, rules_summary)

    return graph


def _annotate_port_edges(
    graph: nx.DiGraph,
    sg_addr: str,
    rules: list[dict[str, Any]],
) -> None:
    """セキュリティグループに関連するエッジにポート情報を注釈する。"""
    # ingressルールからポート情報を収集
    ingress_ports: list[str] = []
    for rule in rules:
        if rule["direction"] == "ingress":
            from_p = rule["from_port"]
            to_p = rule["to_port"]
            proto = rule["protocol"]
            if from_p == to_p:
                ingress_ports.append(f"{proto}/{from_p}")
            else:
                ingress_ports.append(f"{proto}/{from_p}-{to_p}")

    if not ingress_ports:
        return

    port_label = ", ".join(ingress_ports[:3])
    if len(ingress_ports) > 3:
        port_label += f" +{len(ingress_ports) - 3}"

    # このSGに接続するエッジにポートラベルを付与
    for pred in graph.predecessors(sg_addr):
        edge_data = graph.edges[pred, sg_addr]
        if edge_data.get("relation_type") == "references":
            edge_data["port_label"] = port_label
    for succ in graph.successors(sg_addr):
        edge_data = graph.edges[sg_addr, succ]
        if edge_data.get("relation_type") == "references":
            edge_data["port_label"] = port_label


def _summarize_rules(resource: Resource) -> list[dict[str, Any]]:
    """リソースの属性からセキュリティルールを抽出・要約する。"""
    rules: list[dict[str, Any]] = []

    # AWSセキュリティグループ
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
                "access": "Allow",
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
            "access": rule.get("access", "Allow"),
            "priority": rule.get("priority", 100),
        })

    return rules


def _short_summary(resource: Resource) -> str:
    """セキュリティルールの1行サマリーを生成する。"""
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

    # ラベルの可読性を保つため、最大3ルールまで表示
    display = parts[:3]
    if len(parts) > 3:
        display.append(f"+{len(parts) - 3} more")

    return " | ".join(display)


def get_rules_table(resource: Resource) -> str:
    """詳細なルールテーブルを文字列として生成する。

    ツールチップや詳細ビューでの使用を想定。
    Allow/Denyの区別、優先度情報を含む。

    Args:
        resource: セキュリティグループのResource。

    Returns:
        全ルールをフォーマットしたテーブル文字列。
    """
    rules = _summarize_rules(resource)
    if not rules:
        return "ルールが定義されていません。"

    lines = [
        f"{'方向':<8} {'Access':<6} {'Proto':<6} {'ポート':<12} {'CIDR':<20} {'説明'}",
        "-" * 76,
    ]

    for r in rules:
        direction = r["direction"].upper()
        access = r.get("access", "Allow")
        proto = str(r["protocol"])
        from_p = r["from_port"]
        to_p = r["to_port"]
        ports = str(from_p) if from_p == to_p else f"{from_p}-{to_p}"
        cidrs = ", ".join(r.get("cidr_blocks", []))
        desc = r.get("description", "")
        lines.append(f"{direction:<8} {access:<6} {proto:<6} {ports:<12} {cidrs:<20} {desc}")

    return "\n".join(lines)
