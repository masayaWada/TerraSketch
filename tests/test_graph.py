"""グラフビルダーのテスト。"""

import pytest

from terrasketch.graph.builder import build_graph, _get_nested
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


# --- A-1: ネスト属性パス解決のテスト ---


def test_get_nested_simple():
    """単純なキーでネスト関数が動作することを確認。"""
    attrs = {"vpc_id": "vpc-1", "name": "test"}
    assert _get_nested(attrs, "vpc_id") == "vpc-1"
    assert _get_nested(attrs, "name") == "test"
    assert _get_nested(attrs, "missing") is None


def test_get_nested_dot_path():
    """ドット区切りパスでネストされた値を取得できることを確認。"""
    attrs = {
        "vpc_config": {
            "subnet_ids": ["subnet-1", "subnet-2"],
            "security_group_ids": ["sg-1"],
        }
    }
    assert _get_nested(attrs, "vpc_config.subnet_ids") == ["subnet-1", "subnet-2"]
    assert _get_nested(attrs, "vpc_config.security_group_ids") == ["sg-1"]
    assert _get_nested(attrs, "vpc_config.missing") is None


def test_get_nested_deep_path():
    """3階層以上のドットパスが動作することを確認。"""
    attrs = {"a": {"b": {"c": "value"}}}
    assert _get_nested(attrs, "a.b.c") == "value"
    assert _get_nested(attrs, "a.b.missing") is None
    assert _get_nested(attrs, "a.missing.c") is None


def test_get_nested_non_dict_intermediate():
    """中間値がdictでない場合にNoneが返ることを確認。"""
    attrs = {"vpc_config": "not_a_dict"}
    assert _get_nested(attrs, "vpc_config.subnet_ids") is None


def test_nested_attribute_in_graph():
    """ネスト属性パスでグラフのエッジが正しく構築されることを確認。"""
    vpc = Resource(
        id="vpc-1", type="aws_vpc", name="main",
        provider="aws", attributes={"id": "vpc-1"},
    )
    subnet = Resource(
        id="subnet-1", type="aws_subnet", name="pub",
        provider="aws", attributes={"id": "subnet-1", "vpc_id": "vpc-1"},
    )
    sg = Resource(
        id="sg-1", type="aws_security_group", name="lambda_sg",
        provider="aws", attributes={"id": "sg-1", "vpc_id": "vpc-1"},
    )
    lambda_fn = Resource(
        id="fn-1", type="aws_lambda_function", name="handler",
        provider="aws",
        attributes={
            "id": "fn-1",
            "vpc_config": {
                "subnet_ids": ["subnet-1"],
                "security_group_ids": ["sg-1"],
            },
        },
    )
    resources = [vpc, subnet, sg, lambda_fn]
    graph = build_graph(resources)

    # Lambda -> Subnet と Lambda -> SG のエッジが生成されるべき
    assert graph.has_edge("aws_subnet.pub", "aws_lambda_function.handler")
    assert graph.has_edge("aws_security_group.lambda_sg", "aws_lambda_function.handler")


def test_edge_attr_name():
    """エッジにattr_name属性が付与されることを確認。"""
    resources = _make_resources()
    graph = build_graph(resources)

    # VPC -> Subnet のエッジにattr_nameが付与される
    if graph.has_edge("aws_vpc.main", "aws_subnet.pub"):
        edge_data = graph.edges["aws_vpc.main", "aws_subnet.pub"]
        assert "attr_name" in edge_data
        assert edge_data["attr_name"] == "vpc_id"
