"""レイアウトエンジン - リソースノードの座標計算。

有向グラフに対してトポロジカル層に基づく階層レイアウトを適用し、
各ノードの(x, y)座標を算出する。
交差最小化（barycenter法）、グリッド、フォースレイアウトに対応。
"""

from __future__ import annotations

import math

import networkx as nx


def calculate_layout(
    graph: nx.DiGraph,
    scale_x: float = 250.0,
    scale_y: float = 200.0,
    layout_type: str = "hierarchical",
) -> dict[str, tuple[float, float]]:
    """グラフの各ノードに対して(x, y)座標を計算する。

    Args:
        graph: リソース依存関係グラフ。
        scale_x: 水平方向の間隔倍率。
        scale_y: 垂直方向の間隔倍率。
        layout_type: レイアウトアルゴリズム（'hierarchical', 'grid', 'force'）。

    Returns:
        ノードアドレスから(x, y)ピクセル座標へのマッピング辞書。
    """
    if len(graph.nodes) == 0:
        return {}

    if len(graph.nodes) == 1:
        node = list(graph.nodes)[0]
        return {node: (100.0, 100.0)}

    # 明示的にgridまたはforceが指定された場合
    if layout_type == "grid":
        return _grid_layout(graph, scale_x, scale_y)
    if layout_type == "force":
        return _force_layout(graph, scale_x, scale_y)

    # hierarchical（デフォルト）: 切断グラフ→コンポーネント分離、DAG→階層、巡回→グリッド
    components = list(nx.weakly_connected_components(graph))
    if len(components) > 1:
        return _layout_disconnected(graph, components, scale_x, scale_y)

    if nx.is_directed_acyclic_graph(graph):
        return _hierarchical_layout(graph, scale_x, scale_y)

    return _grid_layout(graph, scale_x, scale_y)


def _layout_disconnected(
    graph: nx.DiGraph,
    components: list[set[str]],
    scale_x: float,
    scale_y: float,
    gap: float = 150.0,
) -> dict[str, tuple[float, float]]:
    """切断グラフの各連結成分を個別にレイアウトし、水平に並べる。

    各コンポーネントを独立してレイアウトした後、重ならないよう
    水平方向にオフセットを加えて配置する。

    Args:
        graph: リソース依存関係グラフ全体。
        components: 弱連結成分のリスト。
        scale_x: 水平方向の間隔倍率。
        scale_y: 垂直方向の間隔倍率。
        gap: コンポーネント間の水平マージン。
    """
    all_positions: dict[str, tuple[float, float]] = {}
    x_offset = 100.0

    # ノード数の大きい順にソート（メインコンポーネントを左に配置）
    sorted_components = sorted(components, key=len, reverse=True)

    for comp_nodes in sorted_components:
        subgraph = graph.subgraph(comp_nodes).copy()

        if len(subgraph.nodes) == 1:
            node = list(subgraph.nodes)[0]
            sub_pos = {node: (0.0, 100.0)}
        elif nx.is_directed_acyclic_graph(subgraph):
            sub_pos = _hierarchical_layout(subgraph, scale_x, scale_y)
        else:
            sub_pos = _grid_layout(subgraph, scale_x, scale_y)

        # サブポジションの最小x座標を0基準に正規化
        if sub_pos:
            min_x = min(p[0] for p in sub_pos.values())
            sub_pos = {n: (x - min_x, y) for n, (x, y) in sub_pos.items()}

        # 水平オフセットを適用
        for node, (x, y) in sub_pos.items():
            all_positions[node] = (x + x_offset, y)

        # 次のコンポーネント用にオフセットを更新
        if sub_pos:
            max_x = max(p[0] for p in sub_pos.values())
            x_offset += max_x + gap + scale_x

    return all_positions


def _hierarchical_layout(
    graph: nx.DiGraph,
    scale_x: float,
    scale_y: float,
) -> dict[str, tuple[float, float]]:
    """トポロジカル層に基づいて座標を割り当てる。

    Sugiyamaスタイルの階層レイアウト:
    1. 最長パスによる層分け
    2. barycenter法による交差最小化
    3. 座標割り当て
    """
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

    # barycenter法による交差最小化（複数回反復）
    layer_groups = _minimize_crossings(graph, layer_groups, iterations=4)

    # 座標を割り当て
    positions: dict[str, tuple[float, float]] = {}
    start_x = 100.0
    start_y = 100.0

    for layer_idx in sorted(layer_groups):
        nodes_in_layer = layer_groups[layer_idx]
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


def _minimize_crossings(
    graph: nx.DiGraph,
    layer_groups: dict[int, list[str]],
    iterations: int = 4,
) -> dict[int, list[str]]:
    """barycenter法によりエッジ交差を最小化する。

    各層のノード順序を、隣接層のノード位置の重心（barycenter）で
    ソートすることで交差を削減する。上下双方向の反復を行う。

    Args:
        graph: リソース依存関係グラフ。
        layer_groups: 層インデックスからノードリストへのマッピング。
        iterations: 反復回数（上→下 + 下→上で1回）。

    Returns:
        交差最小化後のlayer_groups。
    """
    sorted_layers = sorted(layer_groups.keys())
    if len(sorted_layers) <= 1:
        return layer_groups

    for _ in range(iterations):
        # 上から下へのスイープ
        for i in range(1, len(sorted_layers)):
            layer_idx = sorted_layers[i]
            prev_idx = sorted_layers[i - 1]
            prev_order = {n: pos for pos, n in enumerate(layer_groups[prev_idx])}
            layer_groups[layer_idx] = _sort_by_barycenter(
                graph, layer_groups[layer_idx], prev_order, direction="predecessors"
            )

        # 下から上へのスイープ
        for i in range(len(sorted_layers) - 2, -1, -1):
            layer_idx = sorted_layers[i]
            next_idx = sorted_layers[i + 1]
            next_order = {n: pos for pos, n in enumerate(layer_groups[next_idx])}
            layer_groups[layer_idx] = _sort_by_barycenter(
                graph, layer_groups[layer_idx], next_order, direction="successors"
            )

    return layer_groups


def _sort_by_barycenter(
    graph: nx.DiGraph,
    nodes: list[str],
    adjacent_order: dict[str, int],
    direction: str = "predecessors",
) -> list[str]:
    """隣接層のノード位置の重心でソートする。

    Args:
        graph: グラフ。
        nodes: ソート対象のノードリスト。
        adjacent_order: 隣接層のノード→位置のマッピング。
        direction: 'predecessors' または 'successors'。

    Returns:
        重心順にソートされたノードリスト。
    """
    barycenters: dict[str, float] = {}

    for node in nodes:
        if direction == "predecessors":
            neighbors = list(graph.predecessors(node))
        else:
            neighbors = list(graph.successors(node))

        positions = [adjacent_order[n] for n in neighbors if n in adjacent_order]
        if positions:
            barycenters[node] = sum(positions) / len(positions)
        else:
            # 隣接ノードがない場合は現在の位置を維持
            barycenters[node] = float(nodes.index(node))

    return sorted(nodes, key=lambda n: barycenters[n])


def _grid_layout(
    graph: nx.DiGraph,
    scale_x: float,
    scale_y: float,
) -> dict[str, tuple[float, float]]:
    """非DAG（巡回グラフ）用のグリッドレイアウト。

    numpy依存を回避するため、nx.spring_layoutの代わりに
    シンプルなグリッド配置を使用する。
    """
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


def _force_layout(
    graph: nx.DiGraph,
    scale_x: float,
    scale_y: float,
    iterations: int = 50,
) -> dict[str, tuple[float, float]]:
    """簡易フォースディレクテッドレイアウト（numpy不使用）。

    ノード間の反発力とエッジの引力をシミュレートして座標を計算する。
    外部依存なしの軽量実装。

    Args:
        graph: リソース依存関係グラフ。
        scale_x: 水平スケール（理想エッジ長の基準）。
        scale_y: 垂直スケール。
        iterations: シミュレーション反復回数。

    Returns:
        ノードアドレスから(x, y)座標へのマッピング。
    """
    nodes = list(graph.nodes)
    n = len(nodes)
    if n == 0:
        return {}

    # 初期位置を円形に配置
    positions: dict[str, list[float]] = {}
    radius = scale_x * math.sqrt(n) / 2
    for i, node in enumerate(nodes):
        angle = 2 * math.pi * i / n
        positions[node] = [
            radius * math.cos(angle) + radius,
            radius * math.sin(angle) + radius,
        ]

    ideal_length = (scale_x + scale_y) / 2
    temperature = ideal_length * 2

    for iteration in range(iterations):
        # クーリング
        temp = temperature * (1.0 - iteration / iterations)
        if temp < 0.1:
            break

        displacements: dict[str, list[float]] = {node: [0.0, 0.0] for node in nodes}

        # 反発力（全ノードペア）
        for i in range(n):
            for j in range(i + 1, n):
                ni, nj = nodes[i], nodes[j]
                dx = positions[ni][0] - positions[nj][0]
                dy = positions[ni][1] - positions[nj][1]
                dist = math.sqrt(dx * dx + dy * dy) + 0.01
                # クーロンの法則
                force = (ideal_length * ideal_length) / dist
                fx = (dx / dist) * force
                fy = (dy / dist) * force
                displacements[ni][0] += fx
                displacements[ni][1] += fy
                displacements[nj][0] -= fx
                displacements[nj][1] -= fy

        # 引力（エッジ接続ノード）
        for u, v in graph.edges:
            dx = positions[u][0] - positions[v][0]
            dy = positions[u][1] - positions[v][1]
            dist = math.sqrt(dx * dx + dy * dy) + 0.01
            # フックの法則
            force = (dist * dist) / ideal_length
            fx = (dx / dist) * force
            fy = (dy / dist) * force
            displacements[u][0] -= fx
            displacements[u][1] -= fy
            displacements[v][0] += fx
            displacements[v][1] += fy

        # 変位を適用（温度で制限）
        for node in nodes:
            dx = displacements[node][0]
            dy = displacements[node][1]
            dist = math.sqrt(dx * dx + dy * dy) + 0.01
            scale = min(dist, temp) / dist
            positions[node][0] += dx * scale
            positions[node][1] += dy * scale

    # 正規化: 最小座標を(100, 100)に
    result: dict[str, tuple[float, float]] = {}
    if positions:
        min_x = min(p[0] for p in positions.values())
        min_y = min(p[1] for p in positions.values())
        for node, (x, y) in positions.items():
            result[node] = (x - min_x + 100.0, y - min_y + 100.0)

    return result
