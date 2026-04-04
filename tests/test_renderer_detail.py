"""レンダラーの詳細テスト — VPC/Subnetグルーピング、diffモード、モジュールグルーピング。"""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx

from terrasketch.parser.state_parser import Resource
from terrasketch.renderer.mermaid_renderer import MermaidRenderer, _classify_resource, _detect_provider
from terrasketch.renderer.plantuml_renderer import PlantUMLRenderer, _get_color, _get_stereotype


def _build_vpc_subnet_graph():
    """VPC > Subnet > EC2の階層グラフを構築する。"""
    resources = [
        Resource(id="vpc-1", type="aws_vpc", name="main", provider="aws", attributes={"id": "vpc-1"}),
        Resource(id="sub-1", type="aws_subnet", name="pub", provider="aws", attributes={"id": "sub-1", "vpc_id": "vpc-1"}),
        Resource(id="i-1", type="aws_instance", name="web", provider="aws", attributes={"id": "i-1", "subnet_id": "sub-1"}),
        Resource(id="sg-1", type="aws_security_group", name="web_sg", provider="aws", attributes={"id": "sg-1", "vpc_id": "vpc-1"}),
    ]
    g = nx.DiGraph()
    for r in resources:
        g.add_node(r.address, resource=r, type=r.type, label=f"{r.type}\n{r.name}", module_path="")
    # VPC -> Subnet -> EC2
    g.add_edge("aws_vpc.main", "aws_subnet.pub", relation_type="contains", attr_name="vpc_id")
    g.add_edge("aws_subnet.pub", "aws_instance.web", relation_type="contains", attr_name="subnet_id")
    g.add_edge("aws_vpc.main", "aws_security_group.web_sg", relation_type="contains", attr_name="vpc_id")
    g.add_edge("aws_instance.web", "aws_security_group.web_sg", relation_type="references", attr_name="vpc_security_group_ids")
    return g


def _build_diff_graph():
    """diffモードのグラフを構築する。"""
    g = nx.DiGraph()
    r_added = Resource(id="1", type="aws_subnet", name="new", provider="aws")
    r_removed = Resource(id="2", type="aws_subnet", name="old", provider="aws")
    r_modified = Resource(id="3", type="aws_vpc", name="main", provider="aws")
    r_unchanged = Resource(id="4", type="aws_instance", name="web", provider="aws")

    for r, status in [(r_added, "added"), (r_removed, "removed"), (r_modified, "modified"), (r_unchanged, "unchanged")]:
        g.add_node(r.address, resource=r, type=r.type, label=f"{r.type}\n{r.name}", diff_status=status)
    return g


def _build_module_graph():
    """モジュール境界グラフを構築する。"""
    g = nx.DiGraph()
    r1 = Resource(id="1", type="aws_vpc", name="main", provider="aws", module_path="module.vpc")
    r2 = Resource(id="2", type="aws_subnet", name="pub", provider="aws", module_path="module.vpc")
    r3 = Resource(id="3", type="aws_instance", name="web", provider="aws")
    for r in [r1, r2, r3]:
        g.add_node(r.address, resource=r, type=r.type, label=f"{r.type}\n{r.name}", module_path=r.module_path)
    g.add_edge(r1.address, r2.address, relation_type="contains", attr_name="vpc_id")
    return g


class TestMermaidRenderer:
    """MermaidRendererの詳細テスト。"""

    def test_vpc_subnet_hierarchy(self, tmp_path):
        """VPC/Subnet階層がsubgraphとして出力されることを確認。"""
        g = _build_vpc_subnet_graph()
        pos = {n: (i * 200.0, 0.0) for i, n in enumerate(g.nodes)}
        renderer = MermaidRenderer()
        result = renderer.render(g, pos, tmp_path / "out.md")
        content = result.read_text(encoding="utf-8")
        assert "subgraph" in content
        assert "aws_vpc" in content
        assert "aws_subnet" in content

    def test_labels(self, tmp_path):
        """show_labels=Trueでエッジラベルが出力されることを確認。"""
        g = _build_vpc_subnet_graph()
        pos = {n: (i * 200.0, 0.0) for i, n in enumerate(g.nodes)}
        renderer = MermaidRenderer()
        result = renderer.render(g, pos, tmp_path / "out.md", show_labels=True)
        content = result.read_text(encoding="utf-8")
        assert "vpc_id" in content

    def test_diff_mode(self, tmp_path):
        """diffモードで色分けクラスが出力されることを確認。"""
        g = _build_diff_graph()
        pos = {n: (i * 200.0, 0.0) for i, n in enumerate(g.nodes)}
        renderer = MermaidRenderer()
        result = renderer.render(g, pos, tmp_path / "out.md", diff_mode=True)
        content = result.read_text(encoding="utf-8")
        assert "diff_added" in content
        assert "diff_removed" in content
        assert "diff_modified" in content

    def test_module_grouping(self, tmp_path):
        """モジュールグルーピングがsubgraphとして出力されることを確認。"""
        g = _build_module_graph()
        pos = {n: (i * 200.0, 0.0) for i, n in enumerate(g.nodes)}
        renderer = MermaidRenderer()
        result = renderer.render(g, pos, tmp_path / "out.md", group_by_module=True)
        content = result.read_text(encoding="utf-8")
        assert "module.vpc" in content

    def test_classify_resource(self):
        """_classify_resourceが正しいCSSクラスを返すことを確認。"""
        assert _classify_resource("aws_vpc") == "vpc"
        assert _classify_resource("aws_subnet") == "subnet"
        assert _classify_resource("aws_instance") == "compute"
        assert _classify_resource("aws_security_group") == "security"
        assert _classify_resource("aws_s3_bucket") == "storage"
        assert _classify_resource("aws_unknown_type") == ""

    def test_detect_provider(self):
        """_detect_providerの各プロバイダ判定を確認。"""
        assert _detect_provider("aws_vpc") == "aws"
        assert _detect_provider("azurerm_virtual_network") == "azure"
        assert _detect_provider("google_compute_network") == "gcp"
        assert _detect_provider("custom_resource") == "unknown"


class TestPlantUMLRenderer:
    """PlantUMLRendererの詳細テスト。"""

    def test_vpc_subnet_hierarchy(self, tmp_path):
        """VPC/Subnet階層がpackageとして出力されることを確認。"""
        g = _build_vpc_subnet_graph()
        pos = {n: (i * 200.0, 0.0) for i, n in enumerate(g.nodes)}
        renderer = PlantUMLRenderer()
        result = renderer.render(g, pos, tmp_path / "out.puml")
        content = result.read_text(encoding="utf-8")
        assert "package" in content
        assert "component" in content

    def test_labels(self, tmp_path):
        """show_labels=Trueでエッジラベルが出力されることを確認。"""
        g = _build_vpc_subnet_graph()
        pos = {n: (i * 200.0, 0.0) for i, n in enumerate(g.nodes)}
        renderer = PlantUMLRenderer()
        result = renderer.render(g, pos, tmp_path / "out.puml", show_labels=True)
        content = result.read_text(encoding="utf-8")
        assert "vpc_id" in content

    def test_diff_mode(self, tmp_path):
        """diffモードでコンポーネントにステータスラベルが出力されることを確認。"""
        g = _build_diff_graph()
        pos = {n: (i * 200.0, 0.0) for i, n in enumerate(g.nodes)}
        renderer = PlantUMLRenderer()
        result = renderer.render(g, pos, tmp_path / "out.puml", diff_mode=True)
        content = result.read_text(encoding="utf-8")
        assert "[NEW]" in content
        assert "[DEL]" in content
        # aws_vpcはコンテナタイプのためpackageとしてレンダリングされ、
        # [MOD]ラベルはcomponent（_emit_component）でのみ付与される

    def test_module_grouping(self, tmp_path):
        """モジュールグルーピングがpackageとして出力されることを確認。"""
        g = _build_module_graph()
        pos = {n: (i * 200.0, 0.0) for i, n in enumerate(g.nodes)}
        renderer = PlantUMLRenderer()
        result = renderer.render(g, pos, tmp_path / "out.puml", group_by_module=True)
        content = result.read_text(encoding="utf-8")
        assert "module.vpc" in content

    def test_get_stereotype(self):
        """_get_stereotypeの各リソースタイプを確認。"""
        assert "EC2" in _get_stereotype("aws_instance")
        assert "VPC" in _get_stereotype("aws_vpc")
        assert "Resource" in _get_stereotype("unknown_type")

    def test_get_color(self):
        """_get_colorの各リソースカテゴリを確認。"""
        assert _get_color("aws_vpc") == "#E8F5E9"
        assert _get_color("aws_subnet") == "#E3F2FD"
        assert _get_color("aws_instance") == "#FFF3E0"
        assert _get_color("aws_security_group") == "#FCE4EC"
        assert _get_color("aws_s3_bucket") == "#F3E5F5"
        assert _get_color("aws_lb") == "#FFF8E1"
        assert _get_color("aws_dynamodb_table") == "#E8EAF6"
        assert _get_color("unknown_type") == "#FFFFFF"

    def test_references_edge_style(self, tmp_path):
        """参照エッジが破線で出力されることを確認。"""
        g = _build_vpc_subnet_graph()
        pos = {n: (i * 200.0, 0.0) for i, n in enumerate(g.nodes)}
        renderer = PlantUMLRenderer()
        result = renderer.render(g, pos, tmp_path / "out.puml")
        content = result.read_text(encoding="utf-8")
        assert "..>" in content  # 参照関係の破線矢印


class TestGCPRendering:
    """GCPリソースのレンダリングテスト。"""

    def test_gcp_vpc_subnet(self, tmp_path):
        """GCP VPC/Subnetが正しくレンダリングされることを確認。"""
        resources = [
            Resource(id="net-1", type="google_compute_network", name="vpc", provider="gcp"),
            Resource(id="sub-1", type="google_compute_subnetwork", name="sub", provider="gcp"),
        ]
        g = nx.DiGraph()
        for r in resources:
            g.add_node(r.address, resource=r, type=r.type, label=f"{r.type}\n{r.name}", module_path="")
        g.add_edge("google_compute_network.vpc", "google_compute_subnetwork.sub", relation_type="contains")
        pos = {n: (i * 200.0, 0.0) for i, n in enumerate(g.nodes)}

        for RendererClass, suffix in [
            (MermaidRenderer, ".md"),
            (PlantUMLRenderer, ".puml"),
        ]:
            renderer = RendererClass()
            result = renderer.render(g, pos, tmp_path / f"gcp{suffix}")
            content = result.read_text(encoding="utf-8")
            assert "google_compute_network" in content
