"""コスト注釈機能のテスト。"""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
import pytest

from terrasketch.cost.annotator import (
    CostInfo,
    annotate_cost_diff,
    annotate_costs,
    parse_infracost,
)
from terrasketch.parser.state_parser import Resource


# --- CostInfo テスト ---


class TestCostInfo:
    """CostInfo データクラスのテスト。"""

    def test_cost_label_format(self) -> None:
        """コストラベルが正しいフォーマットで生成される。"""
        cost = CostInfo(monthly_cost=30.368, hourly_cost=0.0416)
        assert cost.cost_label == "$30.37/mo"

    def test_cost_label_none(self) -> None:
        """月額コストがNoneの場合は空文字列。"""
        cost = CostInfo(monthly_cost=None, hourly_cost=None)
        assert cost.cost_label == ""

    def test_cost_label_large(self) -> None:
        """大きな金額のフォーマット。"""
        cost = CostInfo(monthly_cost=1234.56, hourly_cost=None)
        assert cost.cost_label == "$1,234.56/mo"

    def test_cost_label_zero(self) -> None:
        """コスト0のフォーマット。"""
        cost = CostInfo(monthly_cost=0.0, hourly_cost=0.0)
        assert cost.cost_label == "$0.00/mo"


# --- parse_infracost テスト ---


class TestParseInfracost:
    """infracost JSON解析のテスト。"""

    def test_parse_sample_infracost(self) -> None:
        """サンプルinfracostファイルが正しく解析される。"""
        cost_map = parse_infracost("samples/sample_infracost.json")
        assert "aws_instance.web" in cost_map
        assert cost_map["aws_instance.web"].monthly_cost == pytest.approx(30.368)

    def test_null_hourly_cost(self) -> None:
        """hourly_costがnullでもパースされる。"""
        cost_map = parse_infracost("samples/sample_infracost.json")
        s3_cost = cost_map.get("aws_s3_bucket.data")
        assert s3_cost is not None
        assert s3_cost.hourly_cost is None
        assert s3_cost.monthly_cost == pytest.approx(2.30)

    def test_file_not_found(self) -> None:
        """存在しないファイルでFileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            parse_infracost("nonexistent_infracost.json")

    def test_invalid_json(self, tmp_path: Path) -> None:
        """不正なJSON構造でValueError。"""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text('"not an object"')
        with pytest.raises(ValueError):
            parse_infracost(bad_file)

    def test_empty_projects(self, tmp_path: Path) -> None:
        """projectsが空の場合は空マップ。"""
        empty_file = tmp_path / "empty.json"
        empty_file.write_text('{"projects": []}')
        cost_map = parse_infracost(empty_file)
        assert cost_map == {}


# --- annotate_costs テスト ---


def _make_graph_with_resources() -> nx.DiGraph:
    """テスト用グラフを構築する。"""
    graph = nx.DiGraph()
    for addr in ["aws_instance.web", "aws_db_instance.main", "aws_s3_bucket.data"]:
        rtype, rname = addr.split(".")
        r = Resource(id=addr, type=rtype, name=rname, provider="aws")
        graph.add_node(addr, resource=r, type=rtype, label=f"{rtype}\n{rname}")
    return graph


class TestAnnotateCosts:
    """コスト注釈のテスト。"""

    def test_costs_annotated_to_nodes(self) -> None:
        """コスト情報がグラフノードに付与される。"""
        graph = _make_graph_with_resources()
        cost_map = {
            "aws_instance.web": CostInfo(monthly_cost=30.0, hourly_cost=0.04),
            "aws_db_instance.main": CostInfo(monthly_cost=175.0, hourly_cost=0.24),
        }
        annotate_costs(graph, cost_map)

        assert graph.nodes["aws_instance.web"]["cost_monthly"] == 30.0
        assert graph.nodes["aws_instance.web"]["cost_label"] == "$30.00/mo"
        assert graph.nodes["aws_db_instance.main"]["cost_monthly"] == 175.0
        # コスト未設定のノードにはcost_labelがない
        assert "cost_label" not in graph.nodes["aws_s3_bucket.data"]

    def test_module_path_matching(self) -> None:
        """infracostのモジュールパス付きアドレスが正しくマッチする。"""
        graph = _make_graph_with_resources()
        cost_map = {
            "module.main.aws_instance.web": CostInfo(monthly_cost=30.0, hourly_cost=None),
        }
        annotate_costs(graph, cost_map)
        assert graph.nodes["aws_instance.web"]["cost_monthly"] == 30.0


# --- annotate_cost_diff テスト ---


class TestAnnotateCostDiff:
    """コスト差分注釈のテスト。"""

    def test_cost_increase(self) -> None:
        """コスト増加が正しく注釈される。"""
        graph = _make_graph_with_resources()
        before = {"aws_instance.web": CostInfo(monthly_cost=20.0, hourly_cost=None)}
        after = {"aws_instance.web": CostInfo(monthly_cost=30.0, hourly_cost=None)}
        annotate_cost_diff(graph, before, after)
        assert graph.nodes["aws_instance.web"]["cost_diff"] == pytest.approx(10.0)
        assert "+$10.00/mo" in graph.nodes["aws_instance.web"]["cost_diff_label"]

    def test_cost_decrease(self) -> None:
        """コスト減少が正しく注釈される。"""
        graph = _make_graph_with_resources()
        before = {"aws_instance.web": CostInfo(monthly_cost=30.0, hourly_cost=None)}
        after = {"aws_instance.web": CostInfo(monthly_cost=20.0, hourly_cost=None)}
        annotate_cost_diff(graph, before, after)
        assert graph.nodes["aws_instance.web"]["cost_diff"] == pytest.approx(-10.0)
        assert "$-10.00/mo" in graph.nodes["aws_instance.web"]["cost_diff_label"]

    def test_no_change_no_annotation(self) -> None:
        """コスト変化なしの場合はcost_diffが付与されない。"""
        graph = _make_graph_with_resources()
        before = {"aws_instance.web": CostInfo(monthly_cost=30.0, hourly_cost=None)}
        after = {"aws_instance.web": CostInfo(monthly_cost=30.0, hourly_cost=None)}
        annotate_cost_diff(graph, before, after)
        assert "cost_diff" not in graph.nodes["aws_instance.web"]


# --- レンダラー統合テスト ---


class TestCostRendering:
    """コストラベルのレンダラー出力テスト。"""

    def _build_cost_graph(self) -> tuple[nx.DiGraph, dict[str, tuple[float, float]]]:
        """コスト付きテスト用グラフを構築する。"""
        graph = _make_graph_with_resources()
        cost_map = {
            "aws_instance.web": CostInfo(monthly_cost=30.37, hourly_cost=None),
        }
        annotate_costs(graph, cost_map)
        positions = {
            "aws_instance.web": (100.0, 100.0),
            "aws_db_instance.main": (300.0, 100.0),
            "aws_s3_bucket.data": (100.0, 300.0),
        }
        return graph, positions

    def test_drawio_cost_label(self, tmp_path: Path) -> None:
        """draw.ioでコストラベルが表示される。"""
        from terrasketch.renderer.drawio_renderer import DrawioRenderer
        graph, positions = self._build_cost_graph()
        renderer = DrawioRenderer()
        result = renderer.render(graph, positions, tmp_path / "cost.drawio")
        content = result.read_text(encoding="utf-8")
        assert "$30.37/mo" in content

    def test_plantuml_cost_label(self, tmp_path: Path) -> None:
        """PlantUMLでコストラベルが表示される。"""
        from terrasketch.renderer.plantuml_renderer import PlantUMLRenderer
        graph, positions = self._build_cost_graph()
        renderer = PlantUMLRenderer()
        result = renderer.render(graph, positions, tmp_path / "cost.puml")
        content = result.read_text(encoding="utf-8")
        assert "$30.37/mo" in content

    def test_svg_cost_label(self, tmp_path: Path) -> None:
        """SVGでコストラベルが表示される。"""
        from terrasketch.renderer.svg_renderer import SvgRenderer
        graph, positions = self._build_cost_graph()
        renderer = SvgRenderer()
        result = renderer.render(graph, positions, tmp_path / "cost.svg")
        content = result.read_text(encoding="utf-8")
        assert "$30.37/mo" in content
