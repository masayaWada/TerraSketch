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


# --- A-2: 切断グラフ分離レイアウトのテスト ---


def test_disconnected_graph_no_overlap():
    """切断グラフの各コンポーネントが重ならないことを確認。"""
    graph = nx.DiGraph()
    # コンポーネント1: a -> b -> c
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")
    # コンポーネント2: x -> y（切断）
    graph.add_edge("x", "y")

    positions = calculate_layout(graph)
    assert len(positions) == 5

    # 各コンポーネントのx座標範囲を取得
    comp1_xs = [positions[n][0] for n in ["a", "b", "c"]]
    comp2_xs = [positions[n][0] for n in ["x", "y"]]

    # コンポーネント1（ノード数が多い）が左、コンポーネント2が右
    # 重なりがないことを確認
    assert max(comp1_xs) < min(comp2_xs) or max(comp2_xs) < min(comp1_xs)


def test_disconnected_single_nodes():
    """孤立ノード複数が正しく分離配置されることを確認。"""
    graph = nx.DiGraph()
    graph.add_node("isolated_1")
    graph.add_node("isolated_2")
    graph.add_node("isolated_3")

    positions = calculate_layout(graph)
    assert len(positions) == 3

    # 全ノードが異なる座標を持つ
    coords = list(positions.values())
    assert len(set(coords)) == 3


def test_disconnected_mixed_dag_and_cycle():
    """DAGコンポーネントと巡回コンポーネントが混在する切断グラフ。"""
    graph = nx.DiGraph()
    # DAGコンポーネント
    graph.add_edge("a", "b")
    # 巡回コンポーネント
    graph.add_edge("x", "y")
    graph.add_edge("y", "z")
    graph.add_edge("z", "x")

    positions = calculate_layout(graph)
    assert len(positions) == 5

    # 全ノードの座標が正
    for _, (x, y) in positions.items():
        assert x >= 0
        assert y >= 0


def test_large_graph_performance():
    """大規模グラフ（100ノード）のレイアウトが完了することを確認。"""
    graph = nx.DiGraph()
    # 10本の独立チェーン（各10ノード）
    for chain in range(10):
        for i in range(9):
            graph.add_edge(f"c{chain}_n{i}", f"c{chain}_n{i+1}")

    positions = calculate_layout(graph)
    assert len(positions) == 100


# --- フェーズ2: レイアウトアルゴリズム改善のテスト ---


def test_grid_layout_explicit():
    """明示的にgridレイアウトを選択した場合の動作を確認。"""
    graph = nx.DiGraph()
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")
    positions = calculate_layout(graph, layout_type="grid")
    assert len(positions) == 3


def test_force_layout():
    """forceレイアウトが座標を返すことを確認。"""
    graph = nx.DiGraph()
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")
    graph.add_edge("a", "c")
    positions = calculate_layout(graph, layout_type="force")
    assert len(positions) == 3
    # 全座標が非負
    for _, (x, y) in positions.items():
        assert x >= 0
        assert y >= 0


def test_barycenter_reduces_crossings():
    """交差最小化が適用されてもレイアウトが正常に完了することを確認。"""
    graph = nx.DiGraph()
    # 2層のグラフ: a,b -> c,d,e
    graph.add_edge("a", "c")
    graph.add_edge("a", "e")
    graph.add_edge("b", "d")
    graph.add_edge("b", "c")
    positions = calculate_layout(graph, layout_type="hierarchical")
    assert len(positions) == 5
    # 第1層（a,b）が第2層（c,d,e）より上にある
    layer1_y = max(positions["a"][1], positions["b"][1])
    layer2_y = min(positions["c"][1], positions["d"][1], positions["e"][1])
    assert layer1_y < layer2_y
