"""セキュリティグループルールの可視化。

リソース属性からセキュリティグループのルールを抽出し、
グラフのエッジやノードに人間が読める形式のルールサマリーを付与する。
"""

from __future__ import annotations

from typing import Any

import networkx as nx

from terrasketch.parser.state_parser import Resource


def annotate_security_rules(graph: nx.DiGraph) -> nx.DiGraph:
    """グラフにセキュリティグループのルール情報を付与する。

    各セキュリティグループノードからingress/egressルールを抽出し、
    ノードラベルにルールサマリーを追加する。

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

    return graph


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

    Args:
        resource: セキュリティグループのResource。

    Returns:
        全ルールをフォーマットしたテーブル文字列。
    """
    rules = _summarize_rules(resource)
    if not rules:
        return "ルールが定義されていません。"

    lines = [
        f"{'方向':<8} {'Proto':<6} {'ポート':<12} {'CIDR':<20} {'説明'}",
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
