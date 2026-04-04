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

    # エッジスタイル定義: 包含関係と参照関係で視覚的に区別
    _EDGE_STYLES = {
        "contains": (
            "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;"
            "jettySize=auto;html=1;strokeColor=#2e7d32;strokeWidth=2;"
        ),
        "references": (
            "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;"
            "jettySize=auto;html=1;strokeColor=#1565c0;strokeWidth=1;"
            "dashed=1;dashPattern=8 4;"
        ),
    }

    def create_edge(
        self,
        parent: ET.Element,
        edge_id: str,
        source_id: str,
        target_id: str,
        relation_type: str = "contains",
    ) -> ET.Element:
        """draw.ioエッジ（mxCell）要素を作成する。

        Args:
            parent: セルを追加する親XML要素。
            edge_id: エッジのユニークなセルID。
            source_id: ソースノードのセルID。
            target_id: ターゲットノードのセルID。
            relation_type: 関係タイプ（'contains' または 'references'）。

        Returns:
            作成されたmxCellエッジ要素。
        """
        cell = ET.SubElement(parent, "mxCell")
        cell.set("id", edge_id)
        cell.set("value", "")
        style = self._EDGE_STYLES.get(relation_type, self._EDGE_STYLES["contains"])
        cell.set("style", style)
        cell.set("edge", "1")
        cell.set("parent", "1")
        cell.set("source", source_id)
        cell.set("target", target_id)

        geo = ET.SubElement(cell, "mxGeometry")
        geo.set("relative", "1")
        geo.set("as", "geometry")

        return cell

    @staticmethod
    def _build_tooltip(resource: Resource) -> str:
        """リソース属性からツールチップ用のHTMLテキストを構築する。

        ARN、CIDR、タグ等の重要な属性をツールチップに含める。
        """
        attrs = resource.attributes
        tooltip_parts: list[str] = []

        tooltip_parts.append(f"Type: {resource.type}")
        tooltip_parts.append(f"Name: {resource.name}")
        if resource.id:
            tooltip_parts.append(f"ID: {resource.id}")

        # 主要属性を抽出
        _TOOLTIP_KEYS = [
            "arn", "cidr_block", "cidr_blocks", "availability_zone",
            "instance_type", "ami", "engine", "engine_version",
            "address_space", "location", "sku_name",
        ]
        for key in _TOOLTIP_KEYS:
            value = attrs.get(key)
            if value is not None:
                tooltip_parts.append(f"{key}: {value}")

        # タグを表示
        tags = attrs.get("tags")
        if isinstance(tags, dict) and tags:
            tag_str = ", ".join(f"{k}={v}" for k, v in sorted(tags.items()))
            tooltip_parts.append(f"Tags: {tag_str}")

        return "&#xa;".join(tooltip_parts)

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

    # diffモード用のスタイルオーバーライド
    _DIFF_STYLE_OVERRIDES = {
        "added": "fillColor=#c8e6c9;strokeColor=#2e7d32;strokeWidth=3;",
        "removed": "fillColor=#ffcdd2;strokeColor=#c62828;strokeWidth=3;dashed=1;",
        "modified": "fillColor=#fff9c4;strokeColor=#f57f17;strokeWidth=3;",
    }

    def render(
        self,
        graph: nx.DiGraph,
        positions: dict[str, tuple[float, float]],
        output_path: str | Path,
        show_labels: bool = False,
        diff_mode: bool = False,
        group_by_module: bool = False,
    ) -> Path:
        """グラフ全体をdraw.io XMLファイルとしてレンダリングする。

        Args:
            graph: ノードデータを持つリソース依存関係グラフ。
            positions: ノードアドレスから(x, y)座標へのマッピング。
            output_path: 出力.drawioファイルのパス。
            show_labels: エッジに接続属性名ラベルを表示するか。
            diff_mode: diff比較結果を色分けで表示するか。

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
        # ビューポートサイズは全ノード配置後に動的設定するため、仮値を設定
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

        # モジュール境界コンテナを作成
        module_cell_ids: dict[str, str] = {}
        if group_by_module:
            module_nodes: dict[str, list[str]] = {}
            for node_addr in graph.nodes:
                data = graph.nodes[node_addr]
                module_path = data.get("module_path", "")
                if module_path:
                    module_nodes.setdefault(module_path, []).append(node_addr)

            module_style = (
                "rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;"
                "strokeColor=#666666;strokeWidth=2;dashed=1;"
                "verticalAlign=top;align=left;spacingTop=5;spacingLeft=10;"
                "fontSize=13;fontStyle=1;container=1;collapsible=0;"
            )
            for mod_path, mod_nodes in module_nodes.items():
                mod_positions = [positions.get(n, (100.0, 100.0)) for n in mod_nodes]
                min_x = min(p[0] for p in mod_positions) - 50
                min_y = min(p[1] for p in mod_positions) - 70
                max_x = max(p[0] for p in mod_positions) + 110
                max_y = max(p[1] for p in mod_positions) + 110

                cell_id = self._next_id()
                module_cell_ids[mod_path] = cell_id

                cell = ET.SubElement(root, "mxCell")
                cell.set("id", cell_id)
                cell.set("value", mod_path)
                cell.set("style", module_style)
                cell.set("vertex", "1")
                cell.set("parent", "1")

                geo = ET.SubElement(cell, "mxGeometry")
                geo.set("x", str(round(min_x)))
                geo.set("y", str(round(min_y)))
                geo.set("width", str(round(max_x - min_x)))
                geo.set("height", str(round(max_y - min_y)))
                geo.set("as", "geometry")

        # コンテナグループを構築（VPC > Subnet の2段階ネスト）
        vpc_types = {"aws_vpc", "azurerm_virtual_network", "google_compute_network"}
        subnet_types = {"aws_subnet", "azurerm_subnet", "google_compute_subnetwork"}

        # VPCとSubnetの子ノードを収集
        vpc_children: dict[str, list[str]] = {}
        subnet_children: dict[str, list[str]] = {}

        for node_addr in graph.nodes:
            data = graph.nodes[node_addr]
            resource = data.get("resource")
            if resource is None:
                continue
            if resource.type in vpc_types:
                vpc_children[node_addr] = list(nx.descendants(graph, node_addr))
            elif resource.type in subnet_types:
                subnet_children[node_addr] = list(nx.descendants(graph, node_addr))

        # VPCコンテナを作成
        vpc_cell_ids: dict[str, str] = {}
        subnet_cell_ids: dict[str, str] = {}

        vpc_style = (
            "rounded=1;whiteSpace=wrap;html=1;fillColor=#e8f5e9;"
            "strokeColor=#2e7d32;strokeWidth=2;dashed=1;"
            "verticalAlign=top;align=left;spacingTop=5;spacingLeft=10;"
            "fontSize=14;fontStyle=1;container=1;collapsible=0;"
        )
        subnet_style = (
            "rounded=1;whiteSpace=wrap;html=1;fillColor=#e3f2fd;"
            "strokeColor=#1565c0;strokeWidth=1;dashed=1;"
            "verticalAlign=top;align=left;spacingTop=5;spacingLeft=10;"
            "fontSize=12;fontStyle=1;container=1;collapsible=0;"
        )

        for vpc_addr, children in vpc_children.items():
            data = graph.nodes[vpc_addr]
            resource = data.get("resource")
            if resource is None:
                continue

            # 全子ノード（VPC自身含む）の位置からバウンディングボックスを計算
            child_positions = [positions.get(c, (100.0, 100.0)) for c in children]
            vpc_pos = positions.get(vpc_addr, (100.0, 100.0))
            all_pos = child_positions + [vpc_pos]

            min_x = min(p[0] for p in all_pos) - 40
            min_y = min(p[1] for p in all_pos) - 60
            max_x = max(p[0] for p in all_pos) + 100
            max_y = max(p[1] for p in all_pos) + 100

            cell_id = self._next_id()
            vpc_cell_ids[vpc_addr] = cell_id
            node_cell_ids[vpc_addr] = cell_id

            cell = ET.SubElement(root, "mxCell")
            cell.set("id", cell_id)
            cell.set("value", f"{resource.type} / {resource.name}")
            cell.set("style", vpc_style)
            cell.set("vertex", "1")
            cell.set("parent", "1")

            geo = ET.SubElement(cell, "mxGeometry")
            geo.set("x", str(round(min_x)))
            geo.set("y", str(round(min_y)))
            geo.set("width", str(round(max_x - min_x)))
            geo.set("height", str(round(max_y - min_y)))
            geo.set("as", "geometry")

        # Subnetコンテナを作成（VPC内にネスト）
        for subnet_addr, children in subnet_children.items():
            data = graph.nodes[subnet_addr]
            resource = data.get("resource")
            if resource is None:
                continue

            # このSubnetが属するVPCを特定
            parent_vpc_id = "1"
            parent_vpc_addr = None
            for vpc_addr, vpc_ch in vpc_children.items():
                if subnet_addr in vpc_ch and vpc_addr in vpc_cell_ids:
                    parent_vpc_id = vpc_cell_ids[vpc_addr]
                    parent_vpc_addr = vpc_addr
                    break

            # 子ノードの位置からSubnetバウンディングボックスを計算
            child_positions = [positions.get(c, (100.0, 100.0)) for c in children]
            subnet_pos = positions.get(subnet_addr, (100.0, 100.0))
            all_pos = child_positions + [subnet_pos]

            min_x = min(p[0] for p in all_pos) - 30
            min_y = min(p[1] for p in all_pos) - 50
            max_x = max(p[0] for p in all_pos) + 90
            max_y = max(p[1] for p in all_pos) + 90

            # VPC内なら相対座標に変換
            if parent_vpc_addr and parent_vpc_id != "1":
                vpc_origin = self._get_container_origin(root, parent_vpc_id)
                rel_min_x = min_x - vpc_origin[0]
                rel_min_y = min_y - vpc_origin[1]
            else:
                rel_min_x = min_x
                rel_min_y = min_y

            cell_id = self._next_id()
            subnet_cell_ids[subnet_addr] = cell_id
            node_cell_ids[subnet_addr] = cell_id

            cell = ET.SubElement(root, "mxCell")
            cell.set("id", cell_id)
            cell.set("value", f"{resource.type} / {resource.name}")
            cell.set("style", subnet_style)
            cell.set("vertex", "1")
            cell.set("parent", parent_vpc_id)

            geo = ET.SubElement(cell, "mxGeometry")
            geo.set("x", str(round(rel_min_x)))
            geo.set("y", str(round(rel_min_y)))
            geo.set("width", str(round(max_x - min_x)))
            geo.set("height", str(round(max_y - min_y)))
            geo.set("as", "geometry")

        # 全コンテナセルIDをまとめる
        all_container_ids = {**vpc_cell_ids, **subnet_cell_ids}

        # リソースノードを作成
        for node_addr in graph.nodes:
            data = graph.nodes[node_addr]
            resource: Resource | None = data.get("resource")

            if resource is None:
                continue

            # コンテナとして既に作成済みならスキップ
            if node_addr in all_container_ids:
                continue

            cell_id = self._next_id()
            node_cell_ids[node_addr] = cell_id

            style = get_drawio_style(resource.type)
            label = data.get("label", f"{resource.type}\n{resource.name}")
            x, y = positions.get(node_addr, (100.0, 100.0))

            # 親を決定: Subnetコンテナ内 > VPCコンテナ内 > ルート
            parent_id = "1"
            parent_container_id = None

            # まずSubnetコンテナをチェック
            for s_addr, s_children in subnet_children.items():
                if node_addr in s_children and s_addr in subnet_cell_ids:
                    parent_id = subnet_cell_ids[s_addr]
                    parent_container_id = s_addr
                    break

            # Subnetに属さない場合、VPCコンテナをチェック
            if parent_container_id is None:
                for v_addr, v_children in vpc_children.items():
                    if node_addr in v_children and v_addr in vpc_cell_ids:
                        parent_id = vpc_cell_ids[v_addr]
                        parent_container_id = v_addr
                        break

            # diffモード時はスタイルとラベルを上書き
            node_style = style.style
            if diff_mode:
                diff_status = data.get("diff_status", "unchanged")
                override = self._DIFF_STYLE_OVERRIDES.get(diff_status)
                if override:
                    node_style = style.style + override
                    diff_labels = {"added": "[NEW] ", "removed": "[DEL] ", "modified": "[MOD] "}
                    label = diff_labels.get(diff_status, "") + label

            cell = ET.SubElement(root, "mxCell")
            cell.set("id", cell_id)
            cell.set("value", label)
            cell.set("style", node_style)
            cell.set("vertex", "1")
            cell.set("parent", parent_id)
            # セキュリティルールテーブルがあればツールチップに統合
            tooltip = self._build_tooltip(resource)
            security_tooltip = data.get("security_tooltip")
            if security_tooltip:
                tooltip += "&#xa;&#xa;" + security_tooltip.replace("\n", "&#xa;")
            cell.set("tooltip", tooltip)

            geo = ET.SubElement(cell, "mxGeometry")
            if parent_container_id is not None:
                # コンテナ内の相対座標を計算
                # Subnet内の場合: Subnet原点からの相対座標
                # VPC内（Subnet外）の場合: VPC原点からの相対座標
                container_origin = self._get_container_origin(
                    root, all_container_ids[parent_container_id]
                )
                # Subnetコンテナ内のノードは、SubnetがVPC内の相対座標を持つため
                # 絶対座標からSubnetの絶対位置を引く必要がある
                if parent_container_id in subnet_cell_ids:
                    # Subnetの親VPCを見つける
                    vpc_origin = (0.0, 0.0)
                    for v_addr, v_ch in vpc_children.items():
                        if parent_container_id in v_ch and v_addr in vpc_cell_ids:
                            vpc_origin = self._get_container_origin(root, vpc_cell_ids[v_addr])
                            break
                    # Subnet絶対座標 = VPC原点 + Subnet相対座標
                    abs_sx = vpc_origin[0] + container_origin[0]
                    abs_sy = vpc_origin[1] + container_origin[1]
                    geo.set("x", str(round(x - abs_sx)))
                    geo.set("y", str(round(y - abs_sy)))
                else:
                    geo.set("x", str(round(x - container_origin[0])))
                    geo.set("y", str(round(y - container_origin[1])))
            else:
                geo.set("x", str(round(x)))
                geo.set("y", str(round(y)))
            geo.set("width", str(round(style.width)))
            geo.set("height", str(round(style.height)))
            geo.set("as", "geometry")

        # エッジを作成（関係タイプに応じたスタイルを適用）
        for source, target, edge_data in graph.edges(data=True):
            src_cell = node_cell_ids.get(source)
            tgt_cell = node_cell_ids.get(target)
            if src_cell and tgt_cell:
                edge_id = self._next_id()
                relation_type = edge_data.get("relation_type", "contains")
                edge_cell = self.create_edge(
                    root, edge_id, src_cell, tgt_cell,
                    relation_type=relation_type,
                )
                if show_labels:
                    attr_name = edge_data.get("attr_name", "")
                    if attr_name:
                        edge_cell.set("value", attr_name)

        # ビューポートサイズを全ノード座標から動的計算
        viewport_margin = 200
        if positions:
            all_x = [p[0] for p in positions.values()]
            all_y = [p[1] for p in positions.values()]
            vp_dx = max(int(max(all_x) + viewport_margin), 800)
            vp_dy = max(int(max(all_y) + viewport_margin), 600)
        else:
            vp_dx, vp_dy = 800, 600
        mx_graph_model.set("dx", str(vp_dx))
        mx_graph_model.set("dy", str(vp_dy))
        mx_graph_model.set("pageWidth", str(vp_dx))
        mx_graph_model.set("pageHeight", str(vp_dy))

        # ファイルに書き出し
        tree = ET.ElementTree(mxfile)
        ET.indent(tree, space="  ")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tree.write(str(output_path), encoding="unicode", xml_declaration=True)

        return output_path
