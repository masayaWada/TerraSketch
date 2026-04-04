"""SVGレンダラー。

リソースグラフとレイアウト座標からSVGファイルを直接生成する。
外部依存なし（標準ライブラリのxml.etree.ElementTreeのみ使用）。
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import networkx as nx

from terrasketch.parser.state_parser import Resource


# リソースタイプごとの色マッピング
_COLOR_MAP: dict[str, tuple[str, str]] = {
    # (fill, stroke)
    "vpc": ("#e8f5e9", "#2e7d32"),
    "subnet": ("#e3f2fd", "#1565c0"),
    "compute": ("#fff3e0", "#e65100"),
    "security": ("#fce4ec", "#b71c1c"),
    "storage": ("#f3e5f5", "#6a1b9a"),
    "network": ("#fff8e1", "#f57f17"),
    "database": ("#e8eaf6", "#283593"),
    "default": ("#dae8fc", "#6c8ebf"),
}

# diffモード用の色
_DIFF_COLORS: dict[str, tuple[str, str]] = {
    "added": ("#c8e6c9", "#2e7d32"),
    "removed": ("#ffcdd2", "#c62828"),
    "modified": ("#fff9c4", "#f57f17"),
}


def _classify(resource_type: str) -> str:
    """リソースタイプを色カテゴリに分類する。"""
    if "vpc" in resource_type or "virtual_network" in resource_type:
        return "vpc"
    if "subnet" in resource_type:
        return "subnet"
    if any(k in resource_type for k in ("instance", "virtual_machine", "lambda", "ecs")):
        return "compute"
    if any(k in resource_type for k in ("security_group", "network_security", "firewall")):
        return "security"
    if any(k in resource_type for k in ("s3", "storage", "ebs")):
        return "storage"
    if any(k in resource_type for k in ("lb", "alb", "gateway", "route")):
        return "network"
    if any(k in resource_type for k in ("db_instance", "dynamodb", "rds", "sql")):
        return "database"
    return "default"


def _sanitize_id(address: str) -> str:
    """リソースアドレスを有効なSVG IDに変換する。"""
    return re.sub(r"[^a-zA-Z0-9_]", "_", address)


class SvgRenderer:
    """TerraformリソースグラフをSVGファイルとしてレンダリングする。"""

    NODE_WIDTH = 160
    NODE_HEIGHT = 60
    NODE_RX = 8

    def render(
        self,
        graph: nx.DiGraph,
        positions: dict[str, tuple[float, float]],
        output_path: str | Path,
        show_labels: bool = False,
        diff_mode: bool = False,
        group_by_module: bool = False,
        tag_groups: dict[str, list[str]] | None = None,
    ) -> Path:
        """グラフをSVGファイルとしてレンダリングする。

        Args:
            graph: リソース依存関係グラフ。
            positions: ノードアドレスから(x, y)座標へのマッピング。
            output_path: 出力.svgファイルのパス。
            show_labels: エッジに接続属性名ラベルを表示するか。
            diff_mode: diff比較結果を色分けで表示するか。
            group_by_module: モジュール境界でグルーピングするか。

        Returns:
            書き出されたSVGファイルのPath。
        """
        output_path = Path(output_path).with_suffix(".svg")

        # ビューポートサイズを計算
        margin = 100
        if positions:
            max_x = max(p[0] for p in positions.values()) + self.NODE_WIDTH + margin
            max_y = max(p[1] for p in positions.values()) + self.NODE_HEIGHT + margin
        else:
            max_x, max_y = 800, 600

        # SVGルート要素
        svg = ET.Element("svg")
        svg.set("xmlns", "http://www.w3.org/2000/svg")
        svg.set("width", str(int(max_x)))
        svg.set("height", str(int(max_y)))
        svg.set("viewBox", f"0 0 {int(max_x)} {int(max_y)}")

        # 背景
        bg = ET.SubElement(svg, "rect")
        bg.set("width", "100%")
        bg.set("height", "100%")
        bg.set("fill", "#ffffff")

        # マーカー定義（矢印ヘッド）
        defs = ET.SubElement(svg, "defs")
        for marker_id, color in [("arrow-contains", "#2e7d32"), ("arrow-references", "#1565c0")]:
            marker = ET.SubElement(defs, "marker")
            marker.set("id", marker_id)
            marker.set("viewBox", "0 0 10 7")
            marker.set("refX", "10")
            marker.set("refY", "3.5")
            marker.set("markerWidth", "10")
            marker.set("markerHeight", "7")
            marker.set("orient", "auto-start-reverse")
            polygon = ET.SubElement(marker, "polygon")
            polygon.set("points", "0 0, 10 3.5, 0 7")
            polygon.set("fill", color)

        # タググループの矩形を描画
        if tag_groups:
            for tag_value in sorted(tag_groups.keys()):
                node_addrs = tag_groups[tag_value]
                valid_addrs = [a for a in node_addrs if a in positions]
                if not valid_addrs:
                    continue
                group_positions = [positions[a] for a in valid_addrs]
                min_x = min(p[0] for p in group_positions) - 20
                min_y = min(p[1] for p in group_positions) - 40
                max_x = max(p[0] for p in group_positions) + self.NODE_WIDTH + 20
                max_y = max(p[1] for p in group_positions) + self.NODE_HEIGHT + 20

                group_rect = ET.SubElement(svg, "rect")
                group_rect.set("x", str(int(min_x)))
                group_rect.set("y", str(int(min_y)))
                group_rect.set("width", str(int(max_x - min_x)))
                group_rect.set("height", str(int(max_y - min_y)))
                group_rect.set("rx", "8")
                group_rect.set("fill", "#fff3e0")
                group_rect.set("stroke", "#e65100")
                group_rect.set("stroke-width", "2")
                group_rect.set("stroke-dasharray", "8,4")
                group_rect.set("opacity", "0.5")

                group_label = ET.SubElement(svg, "text")
                group_label.set("x", str(int(min_x + 10)))
                group_label.set("y", str(int(min_y + 16)))
                group_label.set("font-size", "13")
                group_label.set("font-weight", "bold")
                group_label.set("fill", "#e65100")
                group_label.text = tag_value

        # ノードの中心座標を計算
        node_centers: dict[str, tuple[float, float]] = {}
        for node_addr in graph.nodes:
            x, y = positions.get(node_addr, (100.0, 100.0))
            node_centers[node_addr] = (x + self.NODE_WIDTH / 2, y + self.NODE_HEIGHT / 2)

        # エッジを描画（ノードの下に配置）
        for source, target, edge_data in graph.edges(data=True):
            if source not in node_centers or target not in node_centers:
                continue
            sx, sy = node_centers[source]
            tx, ty = node_centers[target]

            relation_type = edge_data.get("relation_type", "contains")

            line = ET.SubElement(svg, "line")
            line.set("x1", str(int(sx)))
            line.set("y1", str(int(sy)))
            line.set("x2", str(int(tx)))
            line.set("y2", str(int(ty)))
            line.set("marker-end", f"url(#arrow-{relation_type})")

            if relation_type == "references":
                line.set("stroke", "#1565c0")
                line.set("stroke-width", "1.5")
                line.set("stroke-dasharray", "8,4")
            else:
                line.set("stroke", "#2e7d32")
                line.set("stroke-width", "2")

            # エッジラベル
            if show_labels:
                attr_name = edge_data.get("attr_name", "")
                if attr_name:
                    mid_x = (sx + tx) / 2
                    mid_y = (sy + ty) / 2
                    label_el = ET.SubElement(svg, "text")
                    label_el.set("x", str(int(mid_x)))
                    label_el.set("y", str(int(mid_y) - 5))
                    label_el.set("text-anchor", "middle")
                    label_el.set("font-size", "10")
                    label_el.set("fill", "#666666")
                    label_el.text = attr_name

        # ノードを描画
        for node_addr in graph.nodes:
            data = graph.nodes[node_addr]
            resource: Resource | None = data.get("resource")
            if resource is None:
                continue

            x, y = positions.get(node_addr, (100.0, 100.0))

            # 色を決定
            category = _classify(resource.type)
            fill, stroke = _COLOR_MAP.get(category, _COLOR_MAP["default"])
            stroke_width = "1.5"

            # diffモード
            diff_label_prefix = ""
            if diff_mode:
                diff_status = data.get("diff_status", "unchanged")
                if diff_status in _DIFF_COLORS:
                    fill, stroke = _DIFF_COLORS[diff_status]
                    stroke_width = "3"
                    diff_labels = {"added": "[NEW] ", "removed": "[DEL] ", "modified": "[MOD] "}
                    diff_label_prefix = diff_labels.get(diff_status, "")

            # ノード矩形
            rect = ET.SubElement(svg, "rect")
            rect.set("x", str(int(x)))
            rect.set("y", str(int(y)))
            rect.set("width", str(self.NODE_WIDTH))
            rect.set("height", str(self.NODE_HEIGHT))
            rect.set("rx", str(self.NODE_RX))
            rect.set("fill", fill)
            rect.set("stroke", stroke)
            rect.set("stroke-width", stroke_width)

            # リソースタイプ（上段）
            type_text = ET.SubElement(svg, "text")
            type_text.set("x", str(int(x + self.NODE_WIDTH / 2)))
            type_text.set("y", str(int(y + 24)))
            type_text.set("text-anchor", "middle")
            type_text.set("font-size", "11")
            type_text.set("font-weight", "bold")
            type_text.set("fill", "#333333")
            type_text.text = diff_label_prefix + resource.type

            # リソース名（下段）
            name_text = ET.SubElement(svg, "text")
            name_text.set("x", str(int(x + self.NODE_WIDTH / 2)))
            name_text.set("y", str(int(y + 42)))
            name_text.set("text-anchor", "middle")
            name_text.set("font-size", "10")
            name_text.set("fill", "#666666")
            name_text.text = resource.name

            # コストラベル（最下段）
            cost_label = data.get("cost_diff_label", "") or data.get("cost_label", "")
            if cost_label:
                cost_text = ET.SubElement(svg, "text")
                cost_text.set("x", str(int(x + self.NODE_WIDTH / 2)))
                cost_text.set("y", str(int(y + 56)))
                cost_text.set("text-anchor", "middle")
                cost_text.set("font-size", "9")
                cost_text.set("fill", "#e65100")
                cost_text.text = cost_label

        # ファイルに書き出し
        tree = ET.ElementTree(svg)
        ET.indent(tree, space="  ")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tree.write(str(output_path), encoding="unicode", xml_declaration=True)

        return output_path
