"""レンダラーのテスト。"""

import xml.etree.ElementTree as ET
from pathlib import Path

import networkx as nx
import pytest

from terrasketch.parser.state_parser import Resource
from terrasketch.renderer.drawio_renderer import DrawioRenderer
from terrasketch.renderer.mermaid_renderer import MermaidRenderer


def _build_test_graph():
    """テスト用のVPC->Subnetグラフを構築する。"""
    graph = nx.DiGraph()
    vpc = Resource(id="vpc-1", type="aws_vpc", name="main", provider="aws", attributes={})
    subnet = Resource(id="sub-1", type="aws_subnet", name="pub", provider="aws", attributes={})

    graph.add_node(vpc.address, resource=vpc, type=vpc.type, label=f"{vpc.type}\n{vpc.name}")
    graph.add_node(subnet.address, resource=subnet, type=subnet.type, label=f"{subnet.type}\n{subnet.name}")
    graph.add_edge(vpc.address, subnet.address)
    return graph


def test_drawio_render_creates_file(tmp_path):
    """draw.ioレンダラーが.drawioファイルを作成することを確認。"""
    graph = _build_test_graph()
    positions = {"aws_vpc.main": (100, 100), "aws_subnet.pub": (100, 300)}
    renderer = DrawioRenderer()
    result = renderer.render(graph, positions, tmp_path / "out.drawio")
    assert result.exists()
    assert result.suffix == ".drawio"


def test_drawio_render_valid_xml(tmp_path):
    """生成されたdraw.ioファイルが有効なXMLであることを確認。"""
    graph = _build_test_graph()
    positions = {"aws_vpc.main": (100, 100), "aws_subnet.pub": (100, 300)}
    renderer = DrawioRenderer()
    result = renderer.render(graph, positions, tmp_path / "out.drawio")
    tree = ET.parse(str(result))
    root = tree.getroot()
    assert root.tag == "mxfile"
    cells = root.findall(".//mxCell")
    # 最低: cell0, cell1, VPCコンテナ, Subnetノード, エッジ
    assert len(cells) >= 4


def test_drawio_render_contains_nodes(tmp_path):
    """draw.io出力にリソースノードが含まれることを確認。"""
    graph = _build_test_graph()
    positions = {"aws_vpc.main": (100, 100), "aws_subnet.pub": (100, 300)}
    renderer = DrawioRenderer()
    result = renderer.render(graph, positions, tmp_path / "out.drawio")
    content = result.read_text(encoding="utf-8")
    assert "aws_vpc" in content
    assert "aws_subnet" in content


def test_mermaid_render_creates_file(tmp_path):
    """Mermaidレンダラーが.mdファイルを作成することを確認。"""
    graph = _build_test_graph()
    positions = {"aws_vpc.main": (100, 100), "aws_subnet.pub": (100, 300)}
    renderer = MermaidRenderer()
    result = renderer.render(graph, positions, tmp_path / "out.md")
    assert result.exists()
    assert result.suffix == ".md"


def test_mermaid_render_contains_nodes(tmp_path):
    """Mermaid出力にノードとエッジが含まれることを確認。"""
    graph = _build_test_graph()
    positions = {"aws_vpc.main": (100, 100), "aws_subnet.pub": (100, 300)}
    renderer = MermaidRenderer()
    result = renderer.render(graph, positions, tmp_path / "out.md")
    content = result.read_text(encoding="utf-8")
    assert "flowchart TD" in content
    assert "aws_vpc" in content
    assert "aws_subnet" in content
    assert "-->" in content


def test_mermaid_render_has_styles(tmp_path):
    """Mermaid出力にスタイルクラス定義が含まれることを確認。"""
    graph = _build_test_graph()
    positions = {"aws_vpc.main": (100, 100), "aws_subnet.pub": (100, 300)}
    renderer = MermaidRenderer()
    result = renderer.render(graph, positions, tmp_path / "out.md")
    content = result.read_text(encoding="utf-8")
    assert "classDef vpc" in content


def test_drawio_empty_graph(tmp_path):
    """空のグラフでも有効なdraw.io XMLが生成されることを確認。"""
    graph = nx.DiGraph()
    renderer = DrawioRenderer()
    result = renderer.render(graph, {}, tmp_path / "empty.drawio")
    assert result.exists()
    tree = ET.parse(str(result))
    assert tree.getroot().tag == "mxfile"
