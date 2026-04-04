"""セキュリティルール注釈の詳細テスト。"""

from __future__ import annotations

import networkx as nx

from terrasketch.graph.security import (
    annotate_security_rules,
    get_rules_table,
    _short_summary,
    _summarize_rules,
)
from terrasketch.parser.state_parser import Resource


def _make_sg_resource(ingress=None, egress=None):
    """テスト用のセキュリティグループリソースを作成する。"""
    attrs = {}
    if ingress is not None:
        attrs["ingress"] = ingress
    if egress is not None:
        attrs["egress"] = egress
    return Resource(
        id="sg-123",
        type="aws_security_group",
        name="test_sg",
        provider="aws",
        attributes=attrs,
    )


def _make_graph_with_sg(sg_resource, connected_resources=None):
    """SGを含むグラフを構築する。"""
    g = nx.DiGraph()
    g.add_node(
        sg_resource.address,
        resource=sg_resource,
        type=sg_resource.type,
        label=f"{sg_resource.type}\n{sg_resource.name}",
    )
    if connected_resources:
        for r in connected_resources:
            g.add_node(r.address, resource=r, type=r.type, label=f"{r.type}\n{r.name}")
            g.add_edge(r.address, sg_resource.address, relation_type="references")
    return g


def test_summarize_aws_ingress():
    """AWSのingressルールが正しく要約されることを確認。"""
    sg = _make_sg_resource(ingress=[
        {"from_port": 80, "to_port": 80, "protocol": "tcp", "cidr_blocks": ["0.0.0.0/0"]},
        {"from_port": 443, "to_port": 443, "protocol": "tcp", "cidr_blocks": ["0.0.0.0/0"]},
    ])
    rules = _summarize_rules(sg)
    assert len(rules) == 2
    assert rules[0]["direction"] == "ingress"
    assert rules[0]["from_port"] == 80


def test_summarize_aws_egress():
    """AWSのegressルールが正しく要約されることを確認。"""
    sg = _make_sg_resource(egress=[
        {"from_port": 0, "to_port": 65535, "protocol": "all"},
    ])
    rules = _summarize_rules(sg)
    assert len(rules) == 1
    assert rules[0]["direction"] == "egress"


def test_summarize_no_rules():
    """ルールなしの場合空リストが返ることを確認。"""
    sg = _make_sg_resource()
    rules = _summarize_rules(sg)
    assert rules == []


def test_summarize_invalid_ingress():
    """非リスト/非辞書のingressが無視されることを確認。"""
    sg = _make_sg_resource(ingress="not a list")
    rules = _summarize_rules(sg)
    assert rules == []

    sg2 = _make_sg_resource(ingress=["not a dict"])
    rules2 = _summarize_rules(sg2)
    assert rules2 == []


def test_short_summary_single_rule():
    """1ルールの短縮サマリーを確認。"""
    sg = _make_sg_resource(ingress=[
        {"from_port": 22, "to_port": 22, "protocol": "tcp"},
    ])
    summary = _short_summary(sg)
    assert "IN:tcp/22" in summary


def test_short_summary_range_port():
    """ポート範囲の短縮サマリーを確認。"""
    sg = _make_sg_resource(ingress=[
        {"from_port": 1024, "to_port": 65535, "protocol": "tcp"},
    ])
    summary = _short_summary(sg)
    assert "1024-65535" in summary


def test_short_summary_more_than_3():
    """4ルール以上で+N more表示を確認。"""
    sg = _make_sg_resource(ingress=[
        {"from_port": i, "to_port": i, "protocol": "tcp"} for i in range(80, 85)
    ])
    summary = _short_summary(sg)
    assert "+2 more" in summary


def test_short_summary_empty():
    """ルールなしの短縮サマリーが空文字列であることを確認。"""
    sg = _make_sg_resource()
    assert _short_summary(sg) == ""


def test_rules_table_no_rules():
    """ルールなしのテーブルがデフォルトメッセージを返すことを確認。"""
    sg = _make_sg_resource()
    table = get_rules_table(sg)
    assert "ルールが定義されていません" in table


def test_rules_table_with_rules():
    """ルール付きのテーブルにヘッダーとデータが含まれることを確認。"""
    sg = _make_sg_resource(ingress=[
        {"from_port": 80, "to_port": 80, "protocol": "tcp", "cidr_blocks": ["10.0.0.0/8"], "description": "HTTP"},
    ])
    table = get_rules_table(sg)
    assert "方向" in table
    assert "INGRESS" in table
    assert "HTTP" in table


def test_annotate_adds_security_rules():
    """annotate_security_rulesがノードにルール情報を付与することを確認。"""
    sg = _make_sg_resource(ingress=[
        {"from_port": 22, "to_port": 22, "protocol": "tcp", "cidr_blocks": ["0.0.0.0/0"]},
    ])
    graph = _make_graph_with_sg(sg)
    annotate_security_rules(graph)

    data = graph.nodes[sg.address]
    assert "security_rules" in data
    assert "security_tooltip" in data
    assert "IN:tcp/22" in data["label"]


def test_annotate_port_edges():
    """SGに接続するエッジにポートラベルが付与されることを確認。"""
    sg = _make_sg_resource(ingress=[
        {"from_port": 443, "to_port": 443, "protocol": "tcp"},
    ])
    ec2 = Resource(id="i-123", type="aws_instance", name="web", provider="aws", attributes={})
    graph = _make_graph_with_sg(sg, connected_resources=[ec2])
    annotate_security_rules(graph)

    edge_data = graph.edges[ec2.address, sg.address]
    assert "port_label" in edge_data
    assert "tcp/443" in edge_data["port_label"]


def test_annotate_skips_non_sg():
    """SG以外のノードは変更されないことを確認。"""
    vpc = Resource(id="vpc-1", type="aws_vpc", name="main", provider="aws")
    g = nx.DiGraph()
    g.add_node(vpc.address, resource=vpc, type=vpc.type, label="test")
    annotate_security_rules(g)
    assert "security_rules" not in g.nodes[vpc.address]


def test_annotate_node_without_resource():
    """resourceがNoneのノードがスキップされることを確認。"""
    g = nx.DiGraph()
    g.add_node("orphan", resource=None, type="unknown")
    annotate_security_rules(g)


def test_azure_nsg_rules():
    """Azure NSGルールが正しく要約されることを確認。"""
    nsg = Resource(
        id="nsg-1",
        type="azurerm_network_security_group",
        name="test_nsg",
        provider="azure",
        attributes={
            "security_rule": [
                {
                    "name": "AllowHTTP",
                    "direction": "Inbound",
                    "access": "Allow",
                    "protocol": "Tcp",
                    "destination_port_range": "80",
                    "source_address_prefix": "*",
                    "priority": 100,
                },
            ]
        },
    )
    rules = _summarize_rules(nsg)
    assert len(rules) == 1
    assert rules[0]["access"] == "Allow"
    assert rules[0]["priority"] == 100


def test_annotate_port_edges_multiple():
    """4つ以上のingressルールで+N表記を確認。"""
    sg = _make_sg_resource(ingress=[
        {"from_port": i, "to_port": i, "protocol": "tcp"} for i in [80, 443, 8080, 8443]
    ])
    ec2 = Resource(id="i-1", type="aws_instance", name="web", provider="aws", attributes={})
    graph = _make_graph_with_sg(sg, connected_resources=[ec2])
    annotate_security_rules(graph)
    edge = graph.edges[ec2.address, sg.address]
    assert "+1" in edge["port_label"]
