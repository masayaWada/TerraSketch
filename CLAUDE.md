# CLAUDE.md — TerraSketch 開発ガイド

## プロジェクト概要

TerraSketch は Terraform state JSON を唯一の信頼源として、AWS/Azure/GCP のクラウド構成図を自動生成するPythonツール。
draw.io / Mermaid / PlantUML の3形式に対応し、CLI・GUI の両方で利用可能。
`--provider all` でマルチプロバイダ混在構成図も生成可能。

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

# GCPサンプル実行
terrasketch generate --state samples/sample_gcp_state.json --provider gcp --output ./output

# マルチプロバイダ
terrasketch generate --state samples/sample_state.json --provider all --output ./output

# diff モード
terrasketch diff --before samples/sample_state.json --after samples/sample_state_v2.json --provider aws --output ./output

# Web UI起動
terrasketch serve --port 8080

# 入力ファイルの事前検証
terrasketch validate --state samples/sample_state.json
terrasketch validate --hcl samples/sample.tf

# GUI起動
terrasketch gui
```

## ディレクトリ構造

```
terrasketch/
├── parser/
│   ├── state_parser.py      # Terraform state JSON 解析（Resource dataclass）
│   ├── hcl_parser.py        # Terraform HCL (.tf) 解析（外部依存なし）
│   └── validator.py         # 入力ファイル事前検証（--validate オプション）
├── graph/
│   ├── builder.py            # networkx DiGraph 構築・関係ルール適用
│   ├── security.py           # SG ingress/egress ルール注釈
│   └── summary.py            # リソース統計サマリー生成
├── layout/
│   └── engine.py             # 座標計算（階層/グリッド/切断グラフ分離）
├── renderer/
│   ├── drawio_renderer.py    # draw.io XML (mxfile) 生成
│   ├── mermaid_renderer.py   # Mermaid flowchart 生成
│   ├── plantuml_renderer.py  # PlantUML コンポーネント図 生成
│   └── svg_renderer.py       # SVG/PNG 直接生成
├── diff/
│   └── comparator.py         # 2つのstate比較・差分グラフ構築
├── config/
│   └── theme.py              # カスタムテーマ設定（TOML読み込み）
├── watch/
│   └── watcher.py            # ファイル変更監視・自動再生成
├── web/
│   ├── server.py             # Web UIサーバー（標準ライブラリのみ）
│   └── templates/index.html  # Web UI HTMLテンプレート
├── remote/
│   └── tfc_client.py         # Terraform Cloud/Enterprise API クライアント
├── plugins.py                # プラグイン発見・ロード（entry_points）
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

## Resource dataclass

- `Resource(id, type, name, provider, attributes={}, module_path="")` — `address` はプロパティ（`{type}.{name}`）でコンストラクタ引数ではない
- state JSON は `terraform show -json` 形式: `values.root_module.resources[].values` に属性が格納される

## アーキテクチャの核心

### 処理パイプライン

```
入力（State JSON / HCL）
  → Parser（Resource リスト抽出）
  → Graph Builder（networkx DiGraph 構築）
  → [Security Annotator]（オプション）
  → Layout Engine（座標計算）
  → Renderer（draw.io / Mermaid / PlantUML / SVG 出力）
```

### 重要な設計判断

1. **Terraform state が唯一の信頼源** — クラウドAPI不要、ローカル完結
2. **numpy 不使用** — `nx.spring_layout` の代わりに自作の階層/グリッドレイアウトを使用
3. **関係ルール方式** — `(src_type, attr_name, tgt_type)` タプルで依存関係を定義
4. **エッジに関係タイプ** — `contains`（包含: VPC→Subnet）と `references`（参照: EC2→SG）を区別
5. **切断グラフ分離** — `nx.weakly_connected_components` で各コンポーネントを独立レイアウト
6. **ネスト属性パス** — `_get_nested()` でドット区切りパス（`vpc_config.subnet_ids`）を解決

### 関係ルールの追加方法

`graph/builder.py` の `_AWS/_AZURE/_GCP_RELATIONSHIP_RULES` または `mapping/extended_resources.py` に
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

テスト270件: parser(6), graph(12), layout(9), renderer(20+16), mapping(11), integration(4), hcl_parser(12+15), diff(5), tfc(6+5), theme(10), watch(5+6), web(4+8), phase4_gcp(27), cli(22), validator(15), security_detail(14), 他(23)
カバレッジ91%+（GUI除外）。`pyproject.toml` で `pytest-cov` 設定済み。

## 新しいリソースタイプの追加

0. 新プロバイダの場合: 4レンダラーの `vpc_types` / `subnet_types` / `container_types` セットにも追加
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

- HCLパーサーは軽量実装。複雑なHCL式（条件式、for式）は未対応
- `--labels` オプションでエッジに接続属性名（`vpc_id` 等）を表示可能
- `--provider gcp` でGCPリソースの構成図を生成可能
- `--provider all` でAWS/Azure/GCP混在のマルチプロバイダ構成図を生成可能
- GCPサンプル: `samples/sample_gcp_state.json`
- 将来の拡張計画: `docs/roadmap.md`（フェーズ6〜8）
- `terrasketch validate` で入力ファイルの事前検証が可能
