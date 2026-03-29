"""グラフビルダーのテスト。"""

import pytest

from terrasketch.graph.builder import build_graph
from terrasketch.graph.security import annotate_security_rules
from terrasketch.graph.summary import generate_summary
from terrasketch.parser.state_parser import Resource


def _make_resources():
    """テスト用のリソースセット（VPC, Subnet, EC2, SG）を生成する。"""
    vpc = Resource(
        id="vpc-1", type="aws_vpc", name="main",
        provider="aws", attributes={"id": "vpc-1"},
    )
    subnet = Resource(
        id="subnet-1", type="aws_subnet", name="pub",
        provider="aws", attributes={"id": "subnet-1", "vpc_id": "vpc-1"},
    )
    ec2 = Resource(
        id="i-1", type="aws_instance", name="web",
        provider="aws",
        attributes={
            "id": "i-1", "subnet_id": "subnet-1",
            "vpc_security_group_ids": ["sg-1"],
        },
    )
    sg = Resource(
        id="sg-1", type="aws_security_group", name="web_sg",
        provider="aws",
        attributes={
            "id": "sg-1", "vpc_id": "vpc-1",
            "ingress": [
                {"from_port": 80, "to_port": 80, "protocol": "tcp", "cidr_blocks": ["0.0.0.0/0"]},
            ],
            "egress": [
                {"from_port": 0, "to_port": 0, "protocol": "-1", "cidr_blocks": ["0.0.0.0/0"]},
            ],
        },
    )
    return [vpc, subnet, ec2, sg]


def test_build_graph_nodes():
    """全リソースがノードとして追加されることを確認。"""
    resources = _make_resources()
    graph = build_graph(resources)
    assert graph.number_of_nodes() == 4


def test_build_graph_edges():
    """正しい依存関係エッジが生成されることを確認。"""
    resources = _make_resources()
    graph = build_graph(resources)
    # VPC -> Subnet, VPC -> SG, Subnet -> EC2, SG -> EC2
    assert graph.number_of_edges() == 4
    assert graph.has_edge("aws_vpc.main", "aws_subnet.pub")
    assert graph.has_edge("aws_subnet.pub", "aws_instance.web")
    assert graph.has_edge("aws_vpc.main", "aws_security_group.web_sg")
    assert graph.has_edge("aws_security_group.web_sg", "aws_instance.web")


def test_build_graph_empty():
    """空のリソースリストからは空のグラフが生成されることを確認。"""
    graph = build_graph([])
    assert graph.number_of_nodes() == 0
    assert graph.number_of_edges() == 0


def test_build_graph_no_relations():
    """属性に関係性がないリソース同士はエッジが生成されないことを確認。"""
    r1 = Resource(id="x", type="aws_vpc", name="a", provider="aws", attributes={"id": "x"})
    r2 = Resource(id="y", type="aws_vpc", name="b", provider="aws", attributes={"id": "y"})
    graph = build_graph([r1, r2])
    assert graph.number_of_nodes() == 2
    assert graph.number_of_edges() == 0


def test_annotate_security_rules():
    """セキュリティルールの注釈がSGノードに正しく付与されることを確認。"""
    resources = _make_resources()
    graph = build_graph(resources)
    annotate_security_rules(graph)
    sg_data = graph.nodes["aws_security_group.web_sg"]
    assert "security_rules" in sg_data
    assert len(sg_data["security_rules"]) == 2


def test_generate_summary():
    """リソースサマリーに期待する情報が含まれることを確認。"""
    resources = _make_resources()
    graph = build_graph(resources)
    summary = generate_summary(resources, graph)
    assert "Total resources: 4" in summary
    assert "aws_vpc" in summary
    assert "Root resources" in summary
