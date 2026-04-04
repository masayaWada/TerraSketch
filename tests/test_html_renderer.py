"""インタラクティブHTMLレンダラーのテスト。"""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
import pytest

from terrasketch.graph.builder import build_graph
from terrasketch.parser.state_parser import Resource
from terrasketch.renderer.html_renderer import HtmlRenderer


# --- ヘルパー ---


def _make_resource(name: str, rtype: str = "aws_instance", **attrs: object) -> Resource:
    """テスト用Resourceを生成する。"""
    return Resource(
        id=f"i-{name}", type=rtype, name=name, provider="aws",
        attributes=dict(attrs),
    )


def _build_test_graph() -> tuple[nx.DiGraph, dict[str, tuple[float, float]]]:
    """テスト用グラフと座標を構築する。"""
    resources = [
        _make_resource("web1", "aws_instance"),
        _make_resource("main", "aws_vpc"),
        _make_resource("pub", "aws_subnet", vpc_id="i-main"),
    ]
    graph = build_graph(resources)
    positions = {
        "aws_instance.web1": (100.0, 100.0),
        "aws_vpc.main": (50.0, 50.0),
        "aws_subnet.pub": (50.0, 150.0),
    }
    return graph, positions


# --- 基本テスト ---


class TestHtmlRendererBasic:
    """HTMLレンダラーの基本テスト。"""

    def test_generates_html_file(self, tmp_path: Path) -> None:
        """HTMLファイルが生成される。"""
        graph, positions = _build_test_graph()
        renderer = HtmlRenderer()
        result = renderer.render(graph, positions, tmp_path / "test.html")
        assert result.exists()
        assert result.suffix == ".html"

    def test_html_contains_cytoscape(self, tmp_path: Path) -> None:
        """生成されたHTMLにCytoscape.jsが含まれる。"""
        graph, positions = _build_test_graph()
        renderer = HtmlRenderer()
        result = renderer.render(graph, positions, tmp_path / "test.html")
        content = result.read_text(encoding="utf-8")
        assert "cytoscape" in content.lower()

    def test_html_contains_resource_data(self, tmp_path: Path) -> None:
        """生成されたHTMLにリソースデータが含まれる。"""
        graph, positions = _build_test_graph()
        renderer = HtmlRenderer()
        result = renderer.render(graph, positions, tmp_path / "test.html")
        content = result.read_text(encoding="utf-8")
        assert "aws_instance" in content
        assert "web1" in content

    def test_html_contains_filter_ui(self, tmp_path: Path) -> None:
        """フィルタリングUIが含まれる。"""
        graph, positions = _build_test_graph()
        renderer = HtmlRenderer()
        result = renderer.render(graph, positions, tmp_path / "test.html")
        content = result.read_text(encoding="utf-8")
        assert "provider-filter" in content
        assert "search-input" in content


# --- JSONデータ構造テスト ---


class TestHtmlRendererElements:
    """Cytoscape.js elements構造のテスト。"""

    def test_elements_contain_nodes(self) -> None:
        """elementsにノードが含まれる。"""
        graph, positions = _build_test_graph()
        renderer = HtmlRenderer()
        elements = renderer._build_elements(graph, positions, False, False, False, None)
        node_ids = [e["data"]["id"] for e in elements if "source" not in e.get("data", {})]
        assert "aws_instance.web1" in node_ids

    def test_elements_contain_edges(self) -> None:
        """elementsにエッジが含まれる。"""
        graph, positions = _build_test_graph()
        renderer = HtmlRenderer()
        elements = renderer._build_elements(graph, positions, False, False, False, None)
        edges = [e for e in elements if "source" in e.get("data", {})]
        assert len(edges) > 0

    def test_elements_with_edge_labels(self) -> None:
        """show_labels=Trueでエッジラベルが含まれる。"""
        graph, positions = _build_test_graph()
        renderer = HtmlRenderer()
        elements = renderer._build_elements(graph, positions, True, False, False, None)
        edges_with_labels = [e for e in elements if "label" in e.get("data", {})]
        assert len(edges_with_labels) > 0

    def test_diff_mode_classes(self) -> None:
        """diffモードでdiff CSSクラスが付与される。"""
        graph, positions = _build_test_graph()
        graph.nodes["aws_instance.web1"]["diff_status"] = "added"
        renderer = HtmlRenderer()
        elements = renderer._build_elements(graph, positions, False, True, False, None)
        web_node = next(e for e in elements if e.get("data", {}).get("id") == "aws_instance.web1")
        assert "diff-added" in web_node["classes"]

    def test_tag_groups_in_elements(self) -> None:
        """タググループがelementsに含まれる。"""
        graph, positions = _build_test_graph()
        tag_groups = {"prod": ["aws_instance.web1"]}
        renderer = HtmlRenderer()
        elements = renderer._build_elements(graph, positions, False, False, False, tag_groups)
        group_ids = [e["data"]["id"] for e in elements if "tag:" in e.get("data", {}).get("id", "")]
        assert "tag:prod" in group_ids

    def test_node_has_details(self) -> None:
        """ノードにdetails属性（JSON文字列）が含まれる。"""
        graph, positions = _build_test_graph()
        renderer = HtmlRenderer()
        elements = renderer._build_elements(graph, positions, False, False, False, None)
        web_node = next(e for e in elements if e.get("data", {}).get("id") == "aws_instance.web1")
        details = json.loads(web_node["data"]["details"])
        assert details["type"] == "aws_instance"
        assert details["name"] == "web1"

    def test_provider_attribute(self) -> None:
        """ノードにprovider属性が含まれる。"""
        graph, positions = _build_test_graph()
        renderer = HtmlRenderer()
        elements = renderer._build_elements(graph, positions, False, False, False, None)
        web_node = next(e for e in elements if e.get("data", {}).get("id") == "aws_instance.web1")
        assert web_node["data"]["provider"] == "aws"


# --- 統合テスト ---


class TestHtmlRendererIntegration:
    """HTMLレンダラーの統合テスト。"""

    def test_generate_html_from_sample_state(self, tmp_path: Path) -> None:
        """サンプルstateからHTML構成図が生成できる。"""
        from terrasketch.main import generate
        result = generate(
            state_path="samples/sample_state.json",
            provider="aws",
            output_dir=str(tmp_path),
            output_format="html",
        )
        assert result.exists()
        assert result.suffix == ".html"
        content = result.read_text(encoding="utf-8")
        assert "graphData" in content

    def test_generate_html_with_tag_groups(self, tmp_path: Path) -> None:
        """タググループ付きHTML構成図が生成できる。"""
        graph, positions = _build_test_graph()
        tag_groups = {"prod": ["aws_instance.web1"]}
        renderer = HtmlRenderer()
        result = renderer.render(graph, positions, tmp_path / "tags.html", tag_groups=tag_groups)
        content = result.read_text(encoding="utf-8")
        assert "prod" in content

    def test_empty_graph(self, tmp_path: Path) -> None:
        """空のグラフでもHTMLが生成される。"""
        graph = nx.DiGraph()
        renderer = HtmlRenderer()
        result = renderer.render(graph, {}, tmp_path / "empty.html")
        assert result.exists()
