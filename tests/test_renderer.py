"""レンダラーのテスト。"""

import xml.etree.ElementTree as ET
from pathlib import Path

import networkx as nx
import pytest

from terrasketch.parser.state_parser import Resource
from terrasketch.renderer.drawio_renderer import DrawioRenderer
from terrasketch.renderer.mermaid_renderer import MermaidRenderer
from terrasketch.renderer.plantuml_renderer import PlantUMLRenderer


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


def test_drawio_edge_types(tmp_path):
    """draw.ioでエッジタイプに応じたスタイルが適用されることを確認。"""
    graph = _build_test_graph()
    # 包含エッジにrelation_typeを設定
    for u, v in graph.edges:
        graph.edges[u, v]["relation_type"] = "contains"
    positions = {"aws_vpc.main": (100, 100), "aws_subnet.pub": (100, 300)}
    renderer = DrawioRenderer()
    result = renderer.render(graph, positions, tmp_path / "edge_types.drawio")
    content = result.read_text(encoding="utf-8")
    # 包含エッジ��緑色
    assert "strokeColor=#2e7d32" in content


def test_drawio_tooltip(tmp_path):
    """draw.ioノードにツールチップ属性が含まれることを確認。"""
    graph = nx.DiGraph()
    ec2 = Resource(
        id="i-1", type="aws_instance", name="web", provider="aws",
        attributes={"id": "i-1", "instance_type": "t3.micro", "tags": {"Name": "web-server"}},
    )
    graph.add_node(ec2.address, resource=ec2, type=ec2.type, label=f"{ec2.type}\n{ec2.name}")
    positions = {"aws_instance.web": (100, 100)}
    renderer = DrawioRenderer()
    result = renderer.render(graph, positions, tmp_path / "tooltip.drawio")
    content = result.read_text(encoding="utf-8")
    assert "tooltip=" in content
    assert "instance_type" in content


def test_mermaid_edge_types(tmp_path):
    """Mermaidで参照エッジが破線矢印で出力されることを確認。"""
    graph = nx.DiGraph()
    vpc = Resource(id="vpc-1", type="aws_vpc", name="main", provider="aws", attributes={})
    sg = Resource(id="sg-1", type="aws_security_group", name="web_sg", provider="aws", attributes={})
    graph.add_node(vpc.address, resource=vpc, type=vpc.type, label=f"{vpc.type}\n{vpc.name}")
    graph.add_node(sg.address, resource=sg, type=sg.type, label=f"{sg.type}\n{sg.name}")
    graph.add_edge(vpc.address, sg.address, relation_type="references")
    positions = {"aws_vpc.main": (100, 100), "aws_security_group.web_sg": (100, 300)}
    renderer = MermaidRenderer()
    result = renderer.render(graph, positions, tmp_path / "edge_types.md")
    content = result.read_text(encoding="utf-8")
    assert "-.->", content


# --- PlantUMLレンダラーのテスト ---


def test_plantuml_render_creates_file(tmp_path):
    """PlantUMLレンダラーが.pumlファイル��作成することを確認。"""
    graph = _build_test_graph()
    positions = {"aws_vpc.main": (100, 100), "aws_subnet.pub": (100, 300)}
    renderer = PlantUMLRenderer()
    result = renderer.render(graph, positions, tmp_path / "out.puml")
    assert result.exists()
    assert result.suffix == ".puml"


def test_plantuml_render_valid_structure(tmp_path):
    """PlantUML出力に@startumlと@endumlが含まれることを確認。"""
    graph = _build_test_graph()
    positions = {"aws_vpc.main": (100, 100), "aws_subnet.pub": (100, 300)}
    renderer = PlantUMLRenderer()
    result = renderer.render(graph, positions, tmp_path / "out.puml")
    content = result.read_text(encoding="utf-8")
    assert "@startuml" in content
    assert "@enduml" in content


def test_plantuml_render_contains_nodes(tmp_path):
    """PlantUML出力にリソースノードが含まれることを確認。"""
    graph = _build_test_graph()
    positions = {"aws_vpc.main": (100, 100), "aws_subnet.pub": (100, 300)}
    renderer = PlantUMLRenderer()
    result = renderer.render(graph, positions, tmp_path / "out.puml")
    content = result.read_text(encoding="utf-8")
    assert "aws_vpc" in content
    assert "aws_subnet" in content
    assert "-->" in content


def test_plantuml_vpc_package(tmp_path):
    """PlantUML出力でVPCがpackageとして描画されることを確認。"""
    graph = _build_test_graph()
    positions = {"aws_vpc.main": (100, 100), "aws_subnet.pub": (100, 300)}
    renderer = PlantUMLRenderer()
    result = renderer.render(graph, positions, tmp_path / "out.puml")
    content = result.read_text(encoding="utf-8")
    assert "package" in content


def test_plantuml_edge_types(tmp_path):
    """PlantUML出力で参照エッジが破線矢印で描画されることを確認。"""
    graph = nx.DiGraph()
    vpc = Resource(id="vpc-1", type="aws_vpc", name="main", provider="aws", attributes={})
    sg = Resource(id="sg-1", type="aws_security_group", name="web_sg", provider="aws", attributes={})
    graph.add_node(vpc.address, resource=vpc, type=vpc.type, label=f"{vpc.type}\n{vpc.name}")
    graph.add_node(sg.address, resource=sg, type=sg.type, label=f"{sg.type}\n{sg.name}")
    graph.add_edge(vpc.address, sg.address, relation_type="references")
    positions = {"aws_vpc.main": (100, 100), "aws_security_group.web_sg": (100, 300)}
    renderer = PlantUMLRenderer()
    result = renderer.render(graph, positions, tmp_path / "edge_types.puml")
    content = result.read_text(encoding="utf-8")
    assert "..>" in content


def test_plantuml_empty_graph(tmp_path):
    """空のグラフでも有効なPlantUMLファイルが生成されることを確認。"""
    graph = nx.DiGraph()
    renderer = PlantUMLRenderer()
    result = renderer.render(graph, {}, tmp_path / "empty.puml")
    assert result.exists()
    content = result.read_text(encoding="utf-8")
    assert "@startuml" in content
    assert "@enduml" in content


# --- Subnetコンテナグルーピングのテスト ---


def _build_vpc_subnet_ec2_graph():
    """テスト用のVPC->Subnet->EC2グラフを構築する。"""
    graph = nx.DiGraph()
    vpc = Resource(id="vpc-1", type="aws_vpc", name="main", provider="aws", attributes={})
    subnet = Resource(id="sub-1", type="aws_subnet", name="pub", provider="aws", attributes={})
    ec2 = Resource(id="i-1", type="aws_instance", name="web", provider="aws", attributes={})

    graph.add_node(vpc.address, resource=vpc, type=vpc.type, label=f"{vpc.type}\n{vpc.name}")
    graph.add_node(subnet.address, resource=subnet, type=subnet.type, label=f"{subnet.type}\n{subnet.name}")
    graph.add_node(ec2.address, resource=ec2, type=ec2.type, label=f"{ec2.type}\n{ec2.name}")
    graph.add_edge(vpc.address, subnet.address, relation_type="contains", attr_name="vpc_id")
    graph.add_edge(subnet.address, ec2.address, relation_type="contains", attr_name="subnet_id")
    return graph


def test_drawio_subnet_container(tmp_path):
    """draw.ioでSubnetがコンテナとして描画されることを確認。"""
    graph = _build_vpc_subnet_ec2_graph()
    positions = {
        "aws_vpc.main": (100, 100),
        "aws_subnet.pub": (100, 250),
        "aws_instance.web": (100, 400),
    }
    renderer = DrawioRenderer()
    result = renderer.render(graph, positions, tmp_path / "subnet_container.drawio")
    content = result.read_text(encoding="utf-8")
    # Subnetコンテナスタイル（青系の背景色）が含まれる
    assert "fillColor=#e3f2fd" in content
    # VPCコンテナスタイル（緑系の背景色）が含まれる
    assert "fillColor=#e8f5e9" in content


def test_drawio_subnet_nested_in_vpc(tmp_path):
    """draw.ioでSubnetコンテナがVPCコンテナ内にネストされることを確認。"""
    graph = _build_vpc_subnet_ec2_graph()
    positions = {
        "aws_vpc.main": (100, 100),
        "aws_subnet.pub": (100, 250),
        "aws_instance.web": (100, 400),
    }
    renderer = DrawioRenderer()
    result = renderer.render(graph, positions, tmp_path / "nested.drawio")
    tree = ET.parse(str(result))
    root = tree.getroot()

    # VPCセルのIDを取得
    vpc_cell = None
    subnet_cell = None
    for cell in root.findall(".//mxCell"):
        value = cell.get("value", "")
        if "aws_vpc" in value and "container=1" in cell.get("style", ""):
            vpc_cell = cell
        elif "aws_subnet" in value and "container=1" in cell.get("style", ""):
            subnet_cell = cell

    assert vpc_cell is not None, "VPCコンテナセルが見つからない"
    assert subnet_cell is not None, "Subnetコンテナセルが見つからない"
    # SubnetのparentがVPCのIDであることを確認
    assert subnet_cell.get("parent") == vpc_cell.get("id")


# --- エッジラベル表示のテスト ---


def test_drawio_edge_labels(tmp_path):
    """draw.ioでshow_labels有効時にエッジにattr_nameが表示されることを確認。"""
    graph = _build_vpc_subnet_ec2_graph()
    positions = {
        "aws_vpc.main": (100, 100),
        "aws_subnet.pub": (100, 250),
        "aws_instance.web": (100, 400),
    }
    renderer = DrawioRenderer()
    result = renderer.render(graph, positions, tmp_path / "labels.drawio", show_labels=True)
    content = result.read_text(encoding="utf-8")
    assert "vpc_id" in content
    assert "subnet_id" in content


def test_drawio_edge_labels_hidden_by_default(tmp_path):
    """draw.ioでデフォルトではエッジラベルが非表示であることを確認。"""
    graph = _build_vpc_subnet_ec2_graph()
    positions = {
        "aws_vpc.main": (100, 100),
        "aws_subnet.pub": (100, 250),
        "aws_instance.web": (100, 400),
    }
    renderer = DrawioRenderer()
    result = renderer.render(graph, positions, tmp_path / "nolabels.drawio")
    tree = ET.parse(str(result))
    root = tree.getroot()
    # エッジセルのvalueが空であることを確認
    for cell in root.findall(".//mxCell"):
        if cell.get("edge") == "1":
            assert cell.get("value") == ""


def test_mermaid_edge_labels(tmp_path):
    """Mermaidでshow_labels有効時にエッジにattr_nameが表示されることを確認。"""
    graph = _build_vpc_subnet_ec2_graph()
    positions = {
        "aws_vpc.main": (100, 100),
        "aws_subnet.pub": (100, 250),
        "aws_instance.web": (100, 400),
    }
    renderer = MermaidRenderer()
    result = renderer.render(graph, positions, tmp_path / "labels.md", show_labels=True)
    content = result.read_text(encoding="utf-8")
    assert "vpc_id" in content
    assert "subnet_id" in content


def test_plantuml_edge_labels(tmp_path):
    """PlantUMLでshow_labels有効時にエッジにattr_nameが表示されることを確認。"""
    graph = _build_vpc_subnet_ec2_graph()
    positions = {
        "aws_vpc.main": (100, 100),
        "aws_subnet.pub": (100, 250),
        "aws_instance.web": (100, 400),
    }
    renderer = PlantUMLRenderer()
    result = renderer.render(graph, positions, tmp_path / "labels.puml", show_labels=True)
    content = result.read_text(encoding="utf-8")
    assert ": vpc_id" in content or ": subnet_id" in content
