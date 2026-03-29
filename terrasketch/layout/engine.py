"""レイアウトエンジン - リソースノードの座標計算。

有向グラフに対してトポロジカル層に基づく階層レイアウトを適用し、
各ノードの(x, y)座標を算出する。
"""

from __future__ import annotations

import networkx as nx


def calculate_layout(
    graph: nx.DiGraph,
    scale_x: float = 250.0,
    scale_y: float = 200.0,
) -> dict[str, tuple[float, float]]:
    """グラフの各ノードに対して(x, y)座標を計算する。

    DAG（有向非巡回グラフ）にはトポロジカル層ベースの階層レイアウトを適用。
    巡回グラフや切断グラフにはグリッドレイアウトをフォールバックとして使用。

    Args:
        graph: リソース依存関係グラフ。
        scale_x: 水平方向の間隔倍率。
        scale_y: 垂直方向の間隔倍率。

    Returns:
        ノードアドレスから(x, y)ピクセル座標へのマッピング辞書。
    """
    if len(graph.nodes) == 0:
        return {}

    if len(graph.nodes) == 1:
        node = list(graph.nodes)[0]
        return {node: (100.0, 100.0)}

    # DAGの場合は階層レイアウトを適用
    if nx.is_directed_acyclic_graph(graph):
        return _hierarchical_layout(graph, scale_x, scale_y)

    # フォールバック: グリッドレイアウト
    return _grid_layout(graph, scale_x, scale_y)


def _hierarchical_layout(
    graph: nx.DiGraph,
    scale_x: float,
    scale_y: float,
) -> dict[str, tuple[float, float]]:
    """トポロジカル層に基づいて座標を割り当てる。"""
    # 最長パスによる層分け
    layers: dict[str, int] = {}
    for node in nx.topological_sort(graph):
        preds = list(graph.predecessors(node))
        if not preds:
            layers[node] = 0
        else:
            layers[node] = max(layers[p] for p in preds) + 1

    # 層ごとにノードをグループ化
    layer_groups: dict[int, list[str]] = {}
    for node, layer in layers.items():
        layer_groups.setdefault(layer, []).append(node)

    # 座標を割り当て
    positions: dict[str, tuple[float, float]] = {}
    start_x = 100.0
    start_y = 100.0

    for layer_idx in sorted(layer_groups):
        nodes_in_layer = sorted(layer_groups[layer_idx])
        total_width = (len(nodes_in_layer) - 1) * scale_x
        offset_x = start_x - total_width / 2

        for i, node in enumerate(nodes_in_layer):
            x = offset_x + i * scale_x
            y = start_y + layer_idx * scale_y
            positions[node] = (x, y)

    # 負の座標が出ないように正規化
    if positions:
        min_x = min(p[0] for p in positions.values())
        min_y = min(p[1] for p in positions.values())
        offset_x = 100.0 - min_x if min_x < 100.0 else 0.0
        offset_y = 100.0 - min_y if min_y < 100.0 else 0.0
        if offset_x or offset_y:
            positions = {
                n: (x + offset_x, y + offset_y) for n, (x, y) in positions.items()
            }

    return positions


def _grid_layout(
    graph: nx.DiGraph,
    scale_x: float,
    scale_y: float,
) -> dict[str, tuple[float, float]]:
    """非DAG（巡回グラフ）用のグリッドレイアウト。

    numpy依存を回避するため、nx.spring_layoutの代わりに
    シンプルなグリッド配置を使用する。
    """
    import math

    nodes = sorted(graph.nodes)
    cols = max(1, math.ceil(math.sqrt(len(nodes))))

    positions: dict[str, tuple[float, float]] = {}
    for i, node in enumerate(nodes):
        row = i // cols
        col = i % cols
        x = 100.0 + col * scale_x
        y = 100.0 + row * scale_y
        positions[node] = (x, y)

    return positions
