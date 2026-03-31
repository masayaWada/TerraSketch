# CLAUDE.md — TerraSketch 開発ガイド

## プロジェクト概要

TerraSketch は Terraform state JSON を唯一の信頼源として、AWS/Azure のクラウド構成図を自動生成するPythonツール。
draw.io / Mermaid / PlantUML の3形式に対応し、CLI・GUI の両方で利用可能。

## クイックリファレンス

```bash
# インストール
pip install -e .

# テスト実行
python -m pytest tests/ -v

# サンプル実行（draw.io）
terrasketch generate --state samples/sample_state.json --provider aws --output ./output

# サンプル実行（Mermaid）
terrasketch generate --state samples/sample_state.json --provider aws --format mermaid --output ./output

# サンプル実行（PlantUML）
terrasketch generate --state samples/sample_state.json --provider aws --format plantuml --output ./output

# HCLファイルから生成
terrasketch generate --hcl samples/sample.tf --provider aws --output ./output

# GUI起動
terrasketch gui
```

## ディレクトリ構造

```
terrasketch/
├── parser/
│   ├── state_parser.py      # Terraform state JSON 解析（Resource dataclass）
│   └── hcl_parser.py        # Terraform HCL (.tf) 解析（外部依存なし）
├── graph/
│   ├── builder.py            # networkx DiGraph 構築・関係ルール適用
│   ├── security.py           # SG ingress/egress ルール注釈
│   └── summary.py            # リソース統計サマリー生成
├── layout/
│   └── engine.py             # 座標計算（階層/グリッド/切断グラフ分離）
├── renderer/
│   ├── drawio_renderer.py    # draw.io XML (mxfile) 生成
│   ├── mermaid_renderer.py   # Mermaid flowchart 生成
│   └── plantuml_renderer.py  # PlantUML コンポーネント図 生成
├── mapping/
│   ├── resource_map.py       # 基本リソース→draw.ioスタイルマッピング
│   └── extended_resources.py # 拡張リソースマッピング（40種以上）
├── gui/
│   └── app.py                # Tkinter GUI アプリケーション
└── main.py                   # CLI エントリーポイント
```

## コーディング規約

- **コメント・docstringは全て日本語**
- Python 3.10+ の型ヒント構文を使用（`from __future__ import annotations`）
- 外部依存は `networkx` のみ。numpy 等の追加依存は避ける
- テストの docstring も日本語で記述

## アーキテクチャの核心

### 処理パイプライン

```
入力（State JSON / HCL）
  → Parser（Resource リスト抽出）
  → Graph Builder（networkx DiGraph 構築）
  → [Security Annotator]（オプション）
  → Layout Engine（座標計算）
  → Renderer（draw.io / Mermaid / PlantUML 出力）
```

### 重要な設計判断

1. **Terraform state が唯一の信頼源** — クラウドAPI不要、ローカル完結
2. **numpy 不使用** — `nx.spring_layout` の代わりに自作の階層/グリッドレイアウトを使用
3. **関係ルール方式** — `(src_type, attr_name, tgt_type)` タプルで依存関係を定義
4. **エッジに関係タイプ** — `contains`（包含: VPC→Subnet）と `references`（参照: EC2→SG）を区別
5. **切断グラフ分離** — `nx.weakly_connected_components` で各コンポーネントを独立レイアウト
6. **ネスト属性パス** — `_get_nested()` でドット区切りパス（`vpc_config.subnet_ids`）を解決

### 関係ルールの追加方法

`graph/builder.py` の `_AWS_RELATIONSHIP_RULES` または `mapping/extended_resources.py` に
`(source_type, attribute_name, target_type)` タプルを追加する。
包含関係にする場合は `_CONTAINMENT_RULES` にも追加が必要。

## テスト

```bash
# 全テスト実行
python -m pytest tests/ -v

# 特定テストファイル
python -m pytest tests/test_graph.py -v

# 特定テスト関数
python -m pytest tests/test_graph.py::test_nested_attribute_in_graph -v
```

テスト75件: parser(6), graph(12), layout(9), renderer(20), mapping(10), integration(4), hcl_parser(12), 他(2)

## 新しいリソースタイプの追加

1. `mapping/resource_map.py` または `mapping/extended_resources.py` に `DrawioStyle` を追加
2. 関係ルールがあれば `graph/builder.py` の `_AWS_RELATIONSHIP_RULES` に追加
3. 包含関係なら `_CONTAINMENT_RULES` にも追加
4. `renderer/mermaid_renderer.py` の `_SHAPE_MAP` にMermaid形状を追加（任意）
5. `renderer/plantuml_renderer.py` の `_STEREOTYPE_MAP` にステレオタイプを追加（任意）

## 新しいレンダラーの追加

1. `renderer/` に `xxx_renderer.py` を作成
2. `render(graph, positions, output_path) -> Path` メソッドを実装
3. `main.py` の `generate()` に `elif output_format == "xxx":` 分岐を追加
4. CLI の `--format` choices にフォーマット名を追加

## 注意事項

- GCP対応は未実装（最低優先度）
- HCLパーサーは軽量実装。複雑なHCL式（条件式、for式）は未対応
- `--labels` オプションでエッジに接続属性名（`vpc_id` 等）を表示可能
