# TerraSketch 拡張ガイド

本ドキュメントでは、TerraSketch に新しいリソースタイプ、関係ルール、レンダラーを追加する方法を解説する。

## 1. 新しいリソースタイプの追加

### 1.1 draw.io アイコンマッピング

**対象ファイル:** `terrasketch/mapping/extended_resources.py`

```python
# EXTENDED_AWS_MAPPING に追加
"aws_new_resource": DrawioStyle(
    shape="mxgraph.aws4.new_resource",
    width=60, height=60,
    style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;"
          "verticalAlign=top;align=center;html=1;"
          "shape=mxgraph.aws4.resourceIcon;"
          "resIcon=mxgraph.aws4.new_resource;",
),
```

draw.io のアイコン名は [draw.io の AWS4 ステンシル](https://www.diagrams.net/blog/aws-diagrams) を参照。

### 1.2 Mermaid 形状（任意）

**対象ファイル:** `terrasketch/renderer/mermaid_renderer.py`

```python
# _SHAPE_MAP に追加
_SHAPE_MAP: dict[str, tuple[str, str]] = {
    ...
    "aws_new_resource": ("[", "]"),  # 矩形
}
```

| 形状 | 構文 | 用途例 |
|---|---|---|
| 矩形 | `[`, `]` | 一般リソース |
| 角丸 | `(`, `)` | サービス |
| 六角形 | `{{`, `}}` | セキュリティ |
| 円筒 | `[(`, `)]` | ストレージ・DB |
| スタジアム | `([`, `])` | ロードバランサー |
| 二重括弧 | `[[`, `]]` | ネットワーク |
| 非対称 | `>`, `]` | サーバーレス |

### 1.3 PlantUML ステレオタイプ（任意）

**対象ファイル:** `terrasketch/renderer/plantuml_renderer.py`

```python
# _STEREOTYPE_MAP に追加
_STEREOTYPE_MAP: dict[str, str] = {
    ...
    "aws_new_resource": "<<NewResource>>",
}
```

### 1.4 CSS クラス分類（任意）

**対象ファイル:** `terrasketch/renderer/mermaid_renderer.py`

`_classify_resource()` 関数に分類ロジックを追加:

```python
def _classify_resource(resource_type: str) -> str:
    ...
    if "new_category" in resource_type:
        return "new_class"
    ...
```

## 2. 関係ルールの追加

### 2.1 基本ルール

**対象ファイル:** `terrasketch/graph/builder.py`

```python
_AWS_RELATIONSHIP_RULES: list[tuple[str, str, str]] = [
    ...
    # (ソースタイプ, 属性名, ターゲットタイプ)
    ("aws_new_resource", "vpc_id", "aws_vpc"),
]
```

### 2.2 拡張ルール

**対象ファイル:** `terrasketch/mapping/extended_resources.py`

```python
EXTENDED_AWS_RELATIONSHIP_RULES: list[tuple[str, str, str]] = [
    ...
    # ネスト属性もドット区切りで指定可能
    ("aws_new_resource", "config.subnet_ids", "aws_subnet"),
]
```

### 2.3 包含関係の定義

エッジを「包含（VPCがSubnetを含む等）」として扱う場合:

**対象ファイル:** `terrasketch/graph/builder.py`

```python
_CONTAINMENT_RULES: set[tuple[str, str, str]] = {
    ...
    ("aws_new_resource", "vpc_id", "aws_vpc"),
}
```

包含関係に定義しない場合、自動的に「参照」関係として扱われる。

### 2.4 属性名の仕様

| パターン | 例 | 説明 |
|---|---|---|
| 単純キー | `"vpc_id"` | `resource.attributes["vpc_id"]` を参照 |
| ドット区切り | `"vpc_config.subnet_ids"` | `resource.attributes["vpc_config"]["subnet_ids"]` を再帰的に辿る |
| リスト値 | `"subnet_ids"` → `["sub-1", "sub-2"]` | リスト内の各要素について個別にエッジを生成 |

## 3. 新しいレンダラーの追加

### 3.1 レンダラークラスの作成

**新規ファイル:** `terrasketch/renderer/xxx_renderer.py`

```python
"""XXXダイアグラムレンダラー。"""

from __future__ import annotations

from pathlib import Path

import networkx as nx


class XxxRenderer:
    """TerraformリソースグラフをXXX形式でレンダリングする。"""

    def render(
        self,
        graph: nx.DiGraph,
        positions: dict[str, tuple[float, float]],
        output_path: str | Path,
    ) -> Path:
        """グラフをXXXファイルとしてレンダリングする。

        Args:
            graph: リソース依存関係グラフ。
                   ノード属性: resource (Resource), type (str), label (str)
                   エッジ属性: relation_type ("contains" | "references")
            positions: ノードアドレス → (x, y) 座標のマッピング。
            output_path: 出力ファイルのパス。

        Returns:
            書き出されたファイルのPath。
        """
        output_path = Path(output_path).with_suffix(".xxx")

        # ノードの走査
        for node_addr in graph.nodes:
            data = graph.nodes[node_addr]
            resource = data.get("resource")  # Resource オブジェクト
            x, y = positions.get(node_addr, (100.0, 100.0))
            # ... ノードの描画 ...

        # エッジの走査
        for source, target, edge_data in graph.edges(data=True):
            relation_type = edge_data.get("relation_type", "contains")
            # ... エッジの描画 ...

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        return output_path
```

### 3.2 CLI への統合

**対象ファイル:** `terrasketch/main.py`

```python
# インポート追加
from terrasketch.renderer.xxx_renderer import XxxRenderer

# generate() 内に分岐追加
elif output_format == "xxx":
    logger.info("XXXダイアグラムをレンダリング中...")
    renderer = XxxRenderer()
    result = renderer.render(graph, positions, output_path / "terrasketch_output.xxx")

# argparse の choices 更新
gen_parser.add_argument(
    "--format",
    choices=["drawio", "mermaid", "plantuml", "xxx"],
    ...
)
```

### 3.3 テストの追加

**対象ファイル:** `tests/test_renderer.py`

```python
from terrasketch.renderer.xxx_renderer import XxxRenderer

def test_xxx_render_creates_file(tmp_path):
    """XXXレンダラーがファイルを作成することを確認。"""
    graph = _build_test_graph()
    positions = {"aws_vpc.main": (100, 100), "aws_subnet.pub": (100, 300)}
    renderer = XxxRenderer()
    result = renderer.render(graph, positions, tmp_path / "out.xxx")
    assert result.exists()

def test_xxx_empty_graph(tmp_path):
    """空のグラフでも有効なファイルが生成されることを確認。"""
    graph = nx.DiGraph()
    renderer = XxxRenderer()
    result = renderer.render(graph, {}, tmp_path / "empty.xxx")
    assert result.exists()
```

## 4. 新しいプロバイダの追加（例: GCP）

### 4.1 リソースマッピング

```python
# mapping/extended_resources.py に追加
EXTENDED_GCP_MAPPING: dict[str, DrawioStyle] = {
    "google_compute_instance": DrawioStyle(...),
    "google_compute_network": DrawioStyle(...),
    ...
}
```

### 4.2 関係ルール

```python
EXTENDED_GCP_RELATIONSHIP_RULES: list[tuple[str, str, str]] = [
    ("google_compute_instance", "network_interface.0.network", "google_compute_network"),
    ...
]
```

### 4.3 builder.py での読み込み

```python
try:
    from terrasketch.mapping.extended_resources import (
        ...
        EXTENDED_GCP_RELATIONSHIP_RULES,
    )
    _ALL_RULES = _ALL_RULES + ... + EXTENDED_GCP_RELATIONSHIP_RULES
except ImportError:
    pass
```

### 4.4 CLI のプロバイダ選択

```python
gen_parser.add_argument(
    "--provider",
    choices=["aws", "azure", "gcp"],
    ...
)
```

`generate()` 関数内のフィルタに `"gcp": "google_"` を追加。
