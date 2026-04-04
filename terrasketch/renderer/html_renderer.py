"""インタラクティブHTMLレンダラー。

Cytoscape.jsベースのインタラクティブ構成図をHTMLファイルとして生成する。
ズーム/パン/ノードクリック詳細/フィルタリングに対応する。
"""

from __future__ import annotations

import json
from pathlib import Path

import networkx as nx

from terrasketch.parser.state_parser import Resource


class HtmlRenderer:
    """TerraformリソースグラフをインタラクティブHTMLファイルとしてレンダリングする。"""

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
        """グラフをインタラクティブHTMLファイルとしてレンダリングする。

        Args:
            graph: リソース依存関係グラフ。
            positions: ノードアドレスから(x, y)座標へのマッピング。
            output_path: 出力.htmlファイルのパス。
            show_labels: エッジに接続属性名ラベルを表示するか。
            diff_mode: diff比較結果を色分けで表示するか。
            group_by_module: モジュール境界でグルーピングするか。
            tag_groups: タグベースグルーピング情報。

        Returns:
            書き出されたHTMLファイルのPath。
        """
        output_path = Path(output_path).with_suffix(".html")

        # Cytoscape.js用のグラフデータを構築
        elements = self._build_elements(graph, positions, show_labels, diff_mode,
                                         group_by_module, tag_groups)

        # HTMLテンプレートにデータを埋め込み
        html_content = _HTML_TEMPLATE.replace("{{GRAPH_DATA}}", json.dumps(elements, ensure_ascii=False))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_content, encoding="utf-8")
        return output_path

    def _build_elements(
        self,
        graph: nx.DiGraph,
        positions: dict[str, tuple[float, float]],
        show_labels: bool,
        diff_mode: bool,
        group_by_module: bool,
        tag_groups: dict[str, list[str]] | None,
    ) -> list[dict]:
        """Cytoscape.js形式のelementsリストを構築する。"""
        elements: list[dict] = []

        # 親グループノード（モジュール/タグ）
        if group_by_module:
            module_paths: set[str] = set()
            for node_addr in graph.nodes:
                mp = graph.nodes[node_addr].get("module_path", "")
                if mp:
                    module_paths.add(mp)
            for mp in sorted(module_paths):
                elements.append({
                    "data": {"id": f"module:{mp}", "label": mp, "node_type": "module_group"},
                    "classes": "group module-group",
                })

        if tag_groups:
            for tag_value in sorted(tag_groups.keys()):
                elements.append({
                    "data": {"id": f"tag:{tag_value}", "label": tag_value, "node_type": "tag_group"},
                    "classes": "group tag-group",
                })

        # コンテナタイプ
        container_types = {
            "aws_vpc", "azurerm_virtual_network", "google_compute_network",
            "kubernetes_namespace", "kubernetes_namespace_v1",
        }
        subnet_types = {"aws_subnet", "azurerm_subnet", "google_compute_subnetwork"}

        # VPC/Namespaceコンテナ
        vpc_children: dict[str, list[str]] = {}
        for node_addr in graph.nodes:
            data = graph.nodes[node_addr]
            resource = data.get("resource")
            if resource and resource.type in container_types:
                children = list(nx.descendants(graph, node_addr))
                vpc_children[node_addr] = children
                elements.append({
                    "data": {"id": node_addr, "label": f"{resource.type}\n{resource.name}", "node_type": "container"},
                    "classes": "container",
                })

        # タググループの逆引き（ノード → タグ値）
        tag_node_map: dict[str, str] = {}
        if tag_groups:
            for tag_value, addrs in tag_groups.items():
                for addr in addrs:
                    tag_node_map[addr] = tag_value

        # リソースノード
        for node_addr in graph.nodes:
            data = graph.nodes[node_addr]
            resource: Resource | None = data.get("resource")
            if resource is None:
                continue

            # コンテナは既に追加済み
            if resource.type in container_types:
                continue

            x, y = positions.get(node_addr, (100.0, 100.0))

            # 親を決定
            parent = None
            if group_by_module and data.get("module_path"):
                parent = f"module:{data['module_path']}"
            elif node_addr in tag_node_map:
                parent = f"tag:{tag_node_map[node_addr]}"
            else:
                # VPC/Namespaceコンテナの子
                for vpc_addr, children in vpc_children.items():
                    if node_addr in children:
                        parent = vpc_addr
                        break

            # ラベル構築
            label = f"{resource.type}\n{resource.name}"
            cost_label = data.get("cost_label", "")
            cost_diff_label = data.get("cost_diff_label", "")
            if cost_diff_label:
                label += f"\n{cost_diff_label}"
            elif cost_label:
                label += f"\n{cost_label}"

            # CSS クラス
            classes = _classify_resource(resource.type)
            if diff_mode:
                diff_status = data.get("diff_status", "unchanged")
                if diff_status != "unchanged":
                    classes += f" diff-{diff_status}"

            node_data: dict = {
                "id": node_addr,
                "label": label,
                "resource_type": resource.type,
                "provider": _detect_provider(resource.type),
                "node_type": "resource",
            }
            if parent:
                node_data["parent"] = parent

            # 詳細属性
            attrs = resource.attributes
            details: dict = {"type": resource.type, "name": resource.name}
            if resource.id:
                details["id"] = resource.id
            for key in ("arn", "cidr_block", "instance_type", "ami", "availability_zone"):
                if key in attrs:
                    details[key] = str(attrs[key])
            tags = attrs.get("tags")
            if isinstance(tags, dict):
                details["tags"] = tags
            if cost_label:
                details["cost"] = cost_label
            node_data["details"] = json.dumps(details, ensure_ascii=False)

            elements.append({
                "data": node_data,
                "position": {"x": x, "y": y},
                "classes": classes,
            })

        # エッジ
        for source, target, edge_data in graph.edges(data=True):
            relation_type = edge_data.get("relation_type", "contains")
            edge_entry: dict = {
                "data": {
                    "source": source,
                    "target": target,
                    "relation_type": relation_type,
                },
                "classes": f"edge-{relation_type}",
            }
            if show_labels:
                attr_name = edge_data.get("attr_name", "")
                if attr_name:
                    edge_entry["data"]["label"] = attr_name

            elements.append(edge_entry)

        return elements


def _detect_provider(resource_type: str) -> str:
    """リソースタイプからプロバイダを判定する。"""
    if resource_type.startswith("aws_"):
        return "aws"
    if resource_type.startswith("azurerm_"):
        return "azure"
    if resource_type.startswith("google_"):
        return "gcp"
    if resource_type.startswith("kubernetes_"):
        return "kubernetes"
    return "unknown"


def _classify_resource(resource_type: str) -> str:
    """リソースタイプをCSSクラス名に変換する。"""
    if "vpc" in resource_type or "virtual_network" in resource_type or "compute_network" in resource_type:
        return "res-network"
    if "subnet" in resource_type:
        return "res-subnet"
    if any(k in resource_type for k in ("instance", "virtual_machine", "lambda", "ecs", "deployment", "pod")):
        return "res-compute"
    if any(k in resource_type for k in ("security_group", "network_security", "firewall")):
        return "res-security"
    if any(k in resource_type for k in ("s3", "storage", "db_instance", "rds", "sql", "dynamodb")):
        return "res-storage"
    if any(k in resource_type for k in ("service", "ingress", "lb", "alb", "gateway")):
        return "res-service"
    return "res-default"


# HTMLテンプレート（Cytoscape.js CDN使用）
_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TerraSketch - インタラクティブ構成図</title>
<script src="https://unpkg.com/cytoscape@3.28.1/dist/cytoscape.min.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; display: flex; height: 100vh; }
  #cy { flex: 1; background: #fafafa; }
  #sidebar { width: 320px; background: #fff; border-left: 1px solid #e0e0e0; overflow-y: auto; padding: 16px; display: none; }
  #sidebar.open { display: block; }
  #sidebar h3 { margin-bottom: 12px; color: #333; }
  #sidebar .detail-row { margin-bottom: 8px; font-size: 13px; }
  #sidebar .detail-key { font-weight: 600; color: #555; }
  #sidebar .detail-val { color: #333; word-break: break-all; }
  #toolbar { position: absolute; top: 12px; left: 12px; z-index: 10; display: flex; gap: 8px; flex-wrap: wrap; }
  #toolbar button, #toolbar select { padding: 6px 12px; border: 1px solid #ccc; border-radius: 4px; background: #fff; cursor: pointer; font-size: 12px; }
  #toolbar button:hover { background: #f0f0f0; }
  #search-input { padding: 6px 12px; border: 1px solid #ccc; border-radius: 4px; font-size: 12px; width: 180px; }
  .legend { position: absolute; bottom: 12px; left: 12px; z-index: 10; background: rgba(255,255,255,0.95); border: 1px solid #e0e0e0; border-radius: 6px; padding: 10px 14px; font-size: 11px; }
  .legend-item { display: flex; align-items: center; gap: 6px; margin: 3px 0; }
  .legend-color { width: 14px; height: 14px; border-radius: 3px; border: 1px solid #ccc; }
</style>
</head>
<body>
<div id="toolbar">
  <input id="search-input" type="text" placeholder="リソース名で検索...">
  <select id="provider-filter">
    <option value="all">全プロバイダ</option>
    <option value="aws">AWS</option>
    <option value="azure">Azure</option>
    <option value="gcp">GCP</option>
    <option value="kubernetes">Kubernetes</option>
  </select>
  <button onclick="cy.fit(50)">全体表示</button>
  <button onclick="cy.zoom(cy.zoom()*1.2)">拡大</button>
  <button onclick="cy.zoom(cy.zoom()/1.2)">縮小</button>
</div>
<div id="cy"></div>
<div id="sidebar">
  <h3>リソース詳細</h3>
  <div id="detail-content"></div>
</div>
<div class="legend">
  <div class="legend-item"><div class="legend-color" style="background:#fff3e0;border-color:#e65100"></div>コンピュート</div>
  <div class="legend-item"><div class="legend-color" style="background:#fce4ec;border-color:#b71c1c"></div>セキュリティ</div>
  <div class="legend-item"><div class="legend-color" style="background:#f3e5f5;border-color:#6a1b9a"></div>ストレージ/DB</div>
  <div class="legend-item"><div class="legend-color" style="background:#e3f2fd;border-color:#1565c0"></div>サービス/LB</div>
  <div class="legend-item"><div class="legend-color" style="background:#e8f5e9;border-color:#2e7d32"></div>ネットワーク</div>
</div>
<script>
const graphData = {{GRAPH_DATA}};
const cy = cytoscape({
  container: document.getElementById('cy'),
  elements: graphData,
  style: [
    { selector: 'node', style: {
      'label': 'data(label)', 'text-wrap': 'wrap', 'text-valign': 'center',
      'text-halign': 'center', 'font-size': '10px', 'width': 140, 'height': 60,
      'shape': 'roundrectangle', 'background-color': '#dae8fc', 'border-color': '#6c8ebf',
      'border-width': 1.5, 'padding': '8px',
    }},
    { selector: 'node.container', style: {
      'background-color': '#e8f5e9', 'border-color': '#2e7d32', 'border-width': 2,
      'border-style': 'dashed', 'text-valign': 'top', 'text-halign': 'left',
      'font-size': '13px', 'font-weight': 'bold', 'padding': '30px',
    }},
    { selector: 'node.group', style: {
      'background-color': '#f5f5f5', 'border-color': '#999', 'border-width': 2,
      'border-style': 'dashed', 'text-valign': 'top', 'font-weight': 'bold', 'padding': '20px',
    }},
    { selector: 'node.tag-group', style: { 'background-color': '#fff3e0', 'border-color': '#e65100' }},
    { selector: 'node.res-compute', style: { 'background-color': '#fff3e0', 'border-color': '#e65100' }},
    { selector: 'node.res-security', style: { 'background-color': '#fce4ec', 'border-color': '#b71c1c' }},
    { selector: 'node.res-storage', style: { 'background-color': '#f3e5f5', 'border-color': '#6a1b9a' }},
    { selector: 'node.res-service', style: { 'background-color': '#e3f2fd', 'border-color': '#1565c0' }},
    { selector: 'node.res-network', style: { 'background-color': '#e8f5e9', 'border-color': '#2e7d32' }},
    { selector: 'node.res-subnet', style: { 'background-color': '#e3f2fd', 'border-color': '#1565c0' }},
    { selector: 'node.diff-added', style: { 'background-color': '#c8e6c9', 'border-color': '#2e7d32', 'border-width': 3 }},
    { selector: 'node.diff-removed', style: { 'background-color': '#ffcdd2', 'border-color': '#c62828', 'border-width': 3, 'border-style': 'dashed' }},
    { selector: 'node.diff-modified', style: { 'background-color': '#fff9c4', 'border-color': '#f57f17', 'border-width': 3 }},
    { selector: 'edge', style: {
      'curve-style': 'bezier', 'target-arrow-shape': 'triangle', 'arrow-scale': 0.8,
      'width': 2, 'line-color': '#2e7d32', 'target-arrow-color': '#2e7d32',
    }},
    { selector: 'edge.edge-references', style: {
      'line-color': '#1565c0', 'target-arrow-color': '#1565c0', 'line-style': 'dashed', 'width': 1.5,
    }},
    { selector: 'edge[label]', style: { 'label': 'data(label)', 'font-size': '9px', 'text-rotation': 'autorotate' }},
  ],
  layout: { name: 'preset' },
  wheelSensitivity: 0.3,
});

// ノードクリックで詳細表示
cy.on('tap', 'node[node_type="resource"]', function(evt) {
  const node = evt.target;
  const sidebar = document.getElementById('sidebar');
  const content = document.getElementById('detail-content');
  try {
    const details = JSON.parse(node.data('details') || '{}');
    let html = '';
    for (const [key, val] of Object.entries(details)) {
      if (typeof val === 'object') {
        html += '<div class="detail-row"><span class="detail-key">' + key + ':</span><br><span class="detail-val">' + JSON.stringify(val, null, 2) + '</span></div>';
      } else {
        html += '<div class="detail-row"><span class="detail-key">' + key + ':</span> <span class="detail-val">' + val + '</span></div>';
      }
    }
    content.innerHTML = html;
    sidebar.classList.add('open');
  } catch(e) {}
});
cy.on('tap', function(evt) { if (evt.target === cy) document.getElementById('sidebar').classList.remove('open'); });

// 検索フィルタ
document.getElementById('search-input').addEventListener('input', function(e) {
  const q = e.target.value.toLowerCase();
  cy.nodes().forEach(n => { n.style('opacity', !q || n.data('label').toLowerCase().includes(q) ? 1 : 0.15); });
});

// プロバイダフィルタ
document.getElementById('provider-filter').addEventListener('change', function(e) {
  const p = e.target.value;
  cy.nodes('[node_type="resource"]').forEach(n => { n.style('opacity', p === 'all' || n.data('provider') === p ? 1 : 0.15); });
});
</script>
</body>
</html>
"""
