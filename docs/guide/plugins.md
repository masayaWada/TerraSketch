# プラグイン開発ガイド

TerraSketch は Python エントリーポイントを使ったプラグインシステムを提供しています。

## プラグインの種類

| グループ名 | 説明 |
|---|---|
| `terrasketch.renderers` | カスタムレンダラー（出力形式の追加） |
| `terrasketch.mappings` | カスタムマッピング（リソースタイプのスタイル拡張） |

## レンダラープラグインの作成

### 1. レンダラークラスを実装

```python
from pathlib import Path
import networkx as nx


class D2Renderer:
    """D2言語でのダイアグラムレンダラー。"""

    def render(
        self,
        graph: nx.DiGraph,
        positions: dict[str, tuple[float, float]],
        output_path: Path,
        show_labels: bool = False,
        group_by_module: bool = False,
    ) -> Path:
        # レンダリングロジックを実装
        output_path = Path(output_path).with_suffix(".d2")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("# D2 diagram", encoding="utf-8")
        return output_path
```

### 2. エントリーポイントを登録

`pyproject.toml`:

```toml
[project.entry-points."terrasketch.renderers"]
d2 = "terrasketch_d2:D2Renderer"
```

### 3. プラグインのインストール

```bash
pip install terrasketch-d2
```

これで `--format d2` が使えるようになります。

## マッピングプラグインの作成

リソースタイプのスタイル定義を追加するプラグインです。

```python
from terrasketch.mapping.resource_map import DrawioStyle

CUSTOM_MAPPING = {
    "custom_resource_type": DrawioStyle(
        shape="rounded=1",
        width=80,
        height=60,
        style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffe0b2;",
    ),
}
```

`pyproject.toml`:

```toml
[project.entry-points."terrasketch.mappings"]
custom = "my_plugin:CUSTOM_MAPPING"
```

## 手動登録

コード内から直接プラグインを登録することもできます。

```python
from terrasketch.plugins import register_renderer, register_mapping

register_renderer("custom", MyRenderer)
register_mapping("custom", my_mapping)
```
