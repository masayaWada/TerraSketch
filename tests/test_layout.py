"""レイアウトエンジンのテスト。"""

import networkx as nx
import pytest

from terrasketch.layout.engine import calculate_layout
from terrasketch.parser.state_parser import Resource


def test_empty_graph():
    """空のグラフでは空の座標辞書が返ることを確認。"""
    graph = nx.DiGraph()
    positions = calculate_layout(graph)
    assert positions == {}


def test_single_node():
    """単一ノードのグラフで座標が割り当てられることを確認。"""
    graph = nx.DiGraph()
    graph.add_node("a")
    positions = calculate_layout(graph)
    assert "a" in positions
    assert len(positions["a"]) == 2


def test_hierarchical_layout():
    """階層レイアウトで親ノードが子ノードより上に配置されることを確認。"""
    graph = nx.DiGraph()
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")
    positions = calculate_layout(graph)

    # 各ノードに座標が割り当てられている
    assert len(positions) == 3
    # 階層的配置: aはbより上、bはcより上（y値が小さい方が上）
    assert positions["a"][1] < positions["b"][1]
    assert positions["b"][1] < positions["c"][1]


def test_no_negative_coordinates():
    """全ノードの座標が非負であることを確認。"""
    graph = nx.DiGraph()
    graph.add_edge("a", "b")
    graph.add_edge("a", "c")
    graph.add_edge("a", "d")
    positions = calculate_layout(graph)
    for node, (x, y) in positions.items():
        assert x >= 0, f"ノード{node}のxが負: {x}"
        assert y >= 0, f"ノード{node}のyが負: {y}"


def test_grid_layout_fallback():
    """巡回グラフでグリッドレイアウトにフォールバックすることを確認。"""
    graph = nx.DiGraph()
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")
    graph.add_edge("c", "a")
    positions = calculate_layout(graph)
    assert len(positions) == 3
