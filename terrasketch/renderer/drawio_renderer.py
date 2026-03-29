"""draw.io XMLレンダラー。

リソースグラフとレイアウト座標からdraw.io互換のXMLファイル（.drawio）を生成する。
生成されたファイルはdraw.io（diagrams.net）で直接開くか、
draw.io MCPサーバーで利用できる。
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import networkx as nx

from terrasketch.mapping.resource_map import DrawioStyle, get_drawio_style
from terrasketch.parser.state_parser import Resource


class DrawioRenderer:
    """Terraformリソースグラフをdraw.io XMLファイルとしてレンダリングする。"""

    def __init__(self) -> None:
        self._cell_id_counter = 2  # 0と1はdraw.ioが予約

    def _next_id(self) -> str:
        """次のユニークなセルIDを生成する。"""
        cid = str(self._cell_id_counter)
        self._cell_id_counter += 1
        return cid

    def create_node(
        self,
        parent: ET.Element,
        node_id: str,
        label: str,
        style: DrawioStyle,
        x: float,
        y: float,
    ) -> ET.Element:
        """draw.ioノード（mxCell）要素を作成する。

        Args:
            parent: セルを追加する親XML要素。
            node_id: ユニークなセルID。
            label: ノードの表示ラベル。
            style: ビジュアルプロパティを持つDrawioStyle。
            x: X座標。
            y: Y座標。

        Returns:
            作成されたmxCell要素。
        """
        cell = ET.SubElement(parent, "mxCell")
        cell.set("id", node_id)
        cell.set("value", label)
        cell.set("style", style.style)
        cell.set("vertex", "1")
        cell.set("parent", "1")

        geo = ET.SubElement(cell, "mxGeometry")
        geo.set("x", str(round(x)))
        geo.set("y", str(round(y)))
        geo.set("width", str(round(style.width)))
        geo.set("height", str(round(style.height)))
        geo.set("as", "geometry")

        return cell

    def create_edge(
        self,
        parent: ET.Element,
        edge_id: str,
        source_id: str,
        target_id: str,
    ) -> ET.Element:
        """draw.ioエッジ（mxCell）要素を作成する。

        Args:
            parent: セルを追加する親XML要素。
            edge_id: エッジのユニークなセルID。
            source_id: ソースノードのセルID。
            target_id: ターゲットノードのセルID。

        Returns:
            作成されたmxCellエッジ要素。
        """
        cell = ET.SubElement(parent, "mxCell")
        cell.set("id", edge_id)
        cell.set("value", "")
        cell.set(
            "style",
            "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;"
            "jettySize=auto;html=1;strokeColor=#666666;strokeWidth=2;",
        )
        cell.set("edge", "1")
        cell.set("parent", "1")
        cell.set("source", source_id)
        cell.set("target", target_id)

        geo = ET.SubElement(cell, "mxGeometry")
        geo.set("relative", "1")
        geo.set("as", "geometry")

        return cell

    @staticmethod
    def _get_container_origin(
        root: ET.Element, container_id: str
    ) -> tuple[float, float]:
        """コンテナセルの(x, y)原点を取得する。"""
        for cell in root.iter("mxCell"):
            if cell.get("id") == container_id:
                geo = cell.find("mxGeometry")
                if geo is not None:
                    return (
                        float(geo.get("x", "0")),
                        float(geo.get("y", "0")),
                    )
        return (0.0, 0.0)

    def render(
        self,
        graph: nx.DiGraph,
        positions: dict[str, tuple[float, float]],
        output_path: str | Path,
    ) -> Path:
        """グラフ全体をdraw.io XMLファイルとしてレンダリングする。

        Args:
            graph: ノードデータを持つリソース依存関係グラフ。
            positions: ノードアドレスから(x, y)座標へのマッピング。
            output_path: 出力.drawioファイルのパス。

        Returns:
            書き出された.drawioファイルのPath。
        """
        output_path = Path(output_path)

        # XML構造を構築
        mxfile = ET.Element("mxfile")
        mxfile.set("host", "terrasketch")
        mxfile.set("type", "device")

        diagram = ET.SubElement(mxfile, "diagram")
        diagram.set("id", "terrasketch-diagram")
        diagram.set("name", "TerraSketch")

        mx_graph_model = ET.SubElement(diagram, "mxGraphModel")
        mx_graph_model.set("dx", "1422")
        mx_graph_model.set("dy", "762")
        mx_graph_model.set("grid", "1")
        mx_graph_model.set("gridSize", "10")
        mx_graph_model.set("guides", "1")
        mx_graph_model.set("tooltips", "1")
        mx_graph_model.set("connect", "1")
        mx_graph_model.set("arrows", "1")
        mx_graph_model.set("fold", "1")
        mx_graph_model.set("page", "1")
        mx_graph_model.set("pageScale", "1")
        mx_graph_model.set("math", "0")
        mx_graph_model.set("shadow", "0")

        root = ET.SubElement(mx_graph_model, "root")

        # draw.ioが必要とするルートセル
        cell0 = ET.SubElement(root, "mxCell")
        cell0.set("id", "0")
        cell1 = ET.SubElement(root, "mxCell")
        cell1.set("id", "1")
        cell1.set("parent", "0")

        # ノードアドレスからセルIDへのマッピング
        node_cell_ids: dict[str, str] = {}

        # コンテナグループを構築（VPCが子リソースを包含）
        container_types = {"aws_vpc", "azurerm_virtual_network"}
        container_children: dict[str, list[str]] = {}
        contained_nodes: set[str] = set()

        for node_addr in graph.nodes:
            data = graph.nodes[node_addr]
            resource = data.get("resource")
            if resource and resource.type in container_types:
                children = list(nx.descendants(graph, node_addr))
                container_children[node_addr] = children
                contained_nodes.update(children)

        # コンテナノードを作成（VPCをバウンディングボックスとして描画）
        container_cell_ids: dict[str, str] = {}
        for container_addr, children in container_children.items():
            data = graph.nodes[container_addr]
            resource = data.get("resource")
            if resource is None:
                continue

            # 子ノードの位置からバウンディングボックスを計算
            child_positions = [
                positions.get(c, (100.0, 100.0)) for c in children
            ]
            container_pos = positions.get(container_addr, (100.0, 100.0))
            all_pos = child_positions + [container_pos]

            if all_pos:
                min_x = min(p[0] for p in all_pos) - 40
                min_y = min(p[1] for p in all_pos) - 60
                max_x = max(p[0] for p in all_pos) + 100
                max_y = max(p[1] for p in all_pos) + 100

                cell_id = self._next_id()
                container_cell_ids[container_addr] = cell_id
                node_cell_ids[container_addr] = cell_id

                container_style = (
                    "rounded=1;whiteSpace=wrap;html=1;fillColor=#e8f5e9;"
                    "strokeColor=#2e7d32;strokeWidth=2;dashed=1;"
                    "verticalAlign=top;align=left;spacingTop=5;spacingLeft=10;"
                    "fontSize=14;fontStyle=1;container=1;collapsible=0;"
                )
                cell = ET.SubElement(root, "mxCell")
                cell.set("id", cell_id)
                cell.set("value", f"{resource.type} / {resource.name}")
                cell.set("style", container_style)
                cell.set("vertex", "1")
                cell.set("parent", "1")

                geo = ET.SubElement(cell, "mxGeometry")
                geo.set("x", str(round(min_x)))
                geo.set("y", str(round(min_y)))
                geo.set("width", str(round(max_x - min_x)))
                geo.set("height", str(round(max_y - min_y)))
                geo.set("as", "geometry")

        # リソースノードを作成
        for node_addr in graph.nodes:
            data = graph.nodes[node_addr]
            resource: Resource | None = data.get("resource")

            if resource is None:
                continue

            # コンテナとして既に作成済みならスキップ
            if node_addr in container_cell_ids:
                continue

            cell_id = self._next_id()
            node_cell_ids[node_addr] = cell_id

            style = get_drawio_style(resource.type)
            label = data.get("label", f"{resource.type}\n{resource.name}")
            x, y = positions.get(node_addr, (100.0, 100.0))

            # 親を決定: コンテナ内ならコンテナ、それ以外はルート
            parent_id = "1"
            for container_addr, children in container_children.items():
                if node_addr in children and container_addr in container_cell_ids:
                    parent_id = container_cell_ids[container_addr]
                    break

            cell = ET.SubElement(root, "mxCell")
            cell.set("id", cell_id)
            cell.set("value", label)
            cell.set("style", style.style)
            cell.set("vertex", "1")
            cell.set("parent", parent_id)

            geo = ET.SubElement(cell, "mxGeometry")
            if parent_id != "1":
                # コンテナ内の相対座標を使用
                container_geo = self._get_container_origin(
                    root, container_cell_ids.get(
                        next(ca for ca, ch in container_children.items()
                             if node_addr in ch), ""
                    )
                )
                geo.set("x", str(round(x - container_geo[0])))
                geo.set("y", str(round(y - container_geo[1])))
            else:
                geo.set("x", str(round(x)))
                geo.set("y", str(round(y)))
            geo.set("width", str(round(style.width)))
            geo.set("height", str(round(style.height)))
            geo.set("as", "geometry")

        # エッジを作成
        for source, target in graph.edges:
            src_cell = node_cell_ids.get(source)
            tgt_cell = node_cell_ids.get(target)
            if src_cell and tgt_cell:
                edge_id = self._next_id()
                self.create_edge(root, edge_id, src_cell, tgt_cell)

        # ファイルに書き出し
        tree = ET.ElementTree(mxfile)
        ET.indent(tree, space="  ")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tree.write(str(output_path), encoding="unicode", xml_declaration=True)

        return output_path
