"""タグベースグルーピング機能のテスト。"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import networkx as nx
import pytest

from terrasketch.graph.grouping import (
    build_tag_group_map,
    group_resources_by_tag,
    parse_group_by,
)
from terrasketch.parser.state_parser import Resource


# --- parse_group_by テスト ---


class TestParseGroupBy:
    """parse_group_by 関数のテスト。"""

    def test_none_returns_none(self) -> None:
        """Noneを渡すとNoneが返る。"""
        assert parse_group_by(None) == (None, None)

    def test_module_returns_module(self) -> None:
        """'module' を渡すとmoduleタイプが返る。"""
        assert parse_group_by("module") == ("module", None)

    def test_tag_with_key(self) -> None:
        """'tag:Environment' を渡すとタグタイプとキーが返る。"""
        assert parse_group_by("tag:Environment") == ("tag", "Environment")

    def test_tag_with_complex_key(self) -> None:
        """'tag:team:name' のようなコロン含みのキー。"""
        assert parse_group_by("tag:team:name") == ("tag", "team:name")

    def test_tag_without_key_returns_none(self) -> None:
        """'tag:' のみでキーなしの場合はNoneが返る。"""
        assert parse_group_by("tag:") == (None, None)

    def test_unknown_value_returns_none(self) -> None:
        """不明な値はNoneが返る。"""
        assert parse_group_by("unknown") == (None, None)


# --- group_resources_by_tag テスト ---


def _make_resource(
    name: str,
    rtype: str = "aws_instance",
    tags: dict | None = None,
    tags_all: dict | None = None,
) -> Resource:
    """テスト用Resourceオブジェクトを生成する。"""
    attrs: dict = {}
    if tags is not None:
        attrs["tags"] = tags
    if tags_all is not None:
        attrs["tags_all"] = tags_all
    return Resource(
        id=f"i-{name}",
        type=rtype,
        name=name,
        provider="aws",
        attributes=attrs,
    )


class TestGroupResourcesByTag:
    """group_resources_by_tag 関数のテスト。"""

    def test_basic_grouping(self) -> None:
        """基本的なタグ値によるグルーピング。"""
        resources = [
            _make_resource("web1", tags={"Environment": "prod"}),
            _make_resource("web2", tags={"Environment": "prod"}),
            _make_resource("dev1", tags={"Environment": "dev"}),
        ]
        groups = group_resources_by_tag(resources, "Environment")
        assert len(groups) == 2
        assert len(groups["prod"]) == 2
        assert len(groups["dev"]) == 1

    def test_untagged_resources(self) -> None:
        """タグ未設定のリソースは (untagged) グループに分類される。"""
        resources = [
            _make_resource("web1", tags={"Environment": "prod"}),
            _make_resource("web2", tags={}),
            _make_resource("web3"),
        ]
        groups = group_resources_by_tag(resources, "Environment")
        assert len(groups["(untagged)"]) == 2
        assert len(groups["prod"]) == 1

    def test_azure_tags_all_fallback(self) -> None:
        """tags が空の場合に tags_all にフォールバックする。"""
        resources = [
            _make_resource("vm1", rtype="azurerm_linux_virtual_machine", tags_all={"Environment": "staging"}),
        ]
        groups = group_resources_by_tag(resources, "Environment")
        assert "staging" in groups
        assert len(groups["staging"]) == 1

    def test_nonstring_tag_value(self) -> None:
        """タグ値が文字列でない場合でもstr変換される。"""
        resources = [
            _make_resource("web1", tags={"Priority": 1}),
        ]
        groups = group_resources_by_tag(resources, "Priority")
        assert "1" in groups

    def test_empty_resources(self) -> None:
        """空のリソースリストでは空の辞書が返る。"""
        groups = group_resources_by_tag([], "Environment")
        assert groups == {}

    def test_nondict_tags_attribute(self) -> None:
        """tags属性が辞書でない場合は無視される。"""
        r = Resource(
            id="i-1", type="aws_instance", name="test",
            provider="aws", attributes={"tags": "not-a-dict"},
        )
        groups = group_resources_by_tag([r], "Environment")
        assert "(untagged)" in groups


# --- build_tag_group_map テスト ---


class TestBuildTagGroupMap:
    """build_tag_group_map 関数のテスト。"""

    def test_returns_address_lists(self) -> None:
        """アドレスベースのマップが返る。"""
        resources = [
            _make_resource("web1", tags={"Env": "prod"}),
            _make_resource("db1", rtype="aws_db_instance", tags={"Env": "prod"}),
            _make_resource("dev1", tags={"Env": "dev"}),
        ]
        tag_map = build_tag_group_map(resources, "Env")
        assert "aws_instance.web1" in tag_map["prod"]
        assert "aws_db_instance.db1" in tag_map["prod"]
        assert "aws_instance.dev1" in tag_map["dev"]


# --- レンダラー統合テスト ---


def _build_test_graph_with_tags() -> tuple[nx.DiGraph, dict[str, tuple[float, float]], dict[str, list[str]]]:
    """タグ付きリソースのテスト用グラフ・座標・タググループを構築する。"""
    resources = [
        _make_resource("web1", tags={"Environment": "prod"}),
        _make_resource("web2", tags={"Environment": "prod"}),
        _make_resource("dev1", tags={"Environment": "dev"}),
    ]
    graph = nx.DiGraph()
    for r in resources:
        graph.add_node(r.address, resource=r, type=r.type, label=f"{r.type}\n{r.name}")
    positions = {
        "aws_instance.web1": (100.0, 100.0),
        "aws_instance.web2": (300.0, 100.0),
        "aws_instance.dev1": (100.0, 300.0),
    }
    tag_groups = build_tag_group_map(resources, "Environment")
    return graph, positions, tag_groups


class TestDrawioTagGroups:
    """draw.ioレンダラーのタググループ出力テスト。"""

    def test_tag_group_containers_created(self, tmp_path: Path) -> None:
        """タググループがコンテナとして描画される。"""
        from terrasketch.renderer.drawio_renderer import DrawioRenderer

        graph, positions, tag_groups = _build_test_graph_with_tags()
        renderer = DrawioRenderer()
        result = renderer.render(graph, positions, tmp_path / "test.drawio", tag_groups=tag_groups)

        tree = ET.parse(str(result))
        root_el = tree.getroot()
        cells = list(root_el.iter("mxCell"))
        values = [c.get("value", "") for c in cells]

        assert "prod" in values
        assert "dev" in values


class TestMermaidTagGroups:
    """Mermaidレンダラーのタググループ出力テスト。"""

    def test_tag_group_subgraphs_created(self, tmp_path: Path) -> None:
        """タググループがsubgraphとして出力される。"""
        from terrasketch.renderer.mermaid_renderer import MermaidRenderer

        graph, positions, tag_groups = _build_test_graph_with_tags()
        renderer = MermaidRenderer()
        result = renderer.render(graph, positions, tmp_path / "test.md", tag_groups=tag_groups)

        content = result.read_text(encoding="utf-8")
        assert 'subgraph tag_prod_group["prod"]' in content
        assert 'subgraph tag_dev_group["dev"]' in content


class TestPlantUMLTagGroups:
    """PlantUMLレンダラーのタググループ出力テスト。"""

    def test_tag_group_packages_created(self, tmp_path: Path) -> None:
        """タググループがpackageとして出力される。"""
        from terrasketch.renderer.plantuml_renderer import PlantUMLRenderer

        graph, positions, tag_groups = _build_test_graph_with_tags()
        renderer = PlantUMLRenderer()
        result = renderer.render(graph, positions, tmp_path / "test.puml", tag_groups=tag_groups)

        content = result.read_text(encoding="utf-8")
        assert 'package "dev" #FFF3E0' in content
        assert 'package "prod" #FFF3E0' in content


class TestSvgTagGroups:
    """SVGレンダラーのタググループ出力テスト。"""

    def test_tag_group_rects_created(self, tmp_path: Path) -> None:
        """タググループが矩形として描画される。"""
        from terrasketch.renderer.svg_renderer import SvgRenderer

        graph, positions, tag_groups = _build_test_graph_with_tags()
        renderer = SvgRenderer()
        result = renderer.render(graph, positions, tmp_path / "test.svg", tag_groups=tag_groups)

        content = result.read_text(encoding="utf-8")
        assert "prod" in content
        assert "dev" in content
        assert "#fff3e0" in content


class TestTagGroupNone:
    """tag_groups=None の場合の後方互換性テスト。"""

    def test_drawio_no_tag_groups(self, tmp_path: Path) -> None:
        """tag_groups=Noneでも正常にレンダリングされる。"""
        from terrasketch.renderer.drawio_renderer import DrawioRenderer

        graph, positions, _ = _build_test_graph_with_tags()
        renderer = DrawioRenderer()
        result = renderer.render(graph, positions, tmp_path / "test.drawio")
        assert result.exists()

    def test_mermaid_no_tag_groups(self, tmp_path: Path) -> None:
        """tag_groups=Noneでも正常にレンダリングされる。"""
        from terrasketch.renderer.mermaid_renderer import MermaidRenderer

        graph, positions, _ = _build_test_graph_with_tags()
        renderer = MermaidRenderer()
        result = renderer.render(graph, positions, tmp_path / "test.md")
        assert result.exists()
