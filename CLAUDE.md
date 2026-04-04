# CLAUDE.md — TerraSketch 開発ガイド

## プロジェクト概要

TerraSketch は Terraform / OpenTofu state JSON を唯一の信頼源として、AWS/Azure/GCP/Kubernetes のクラウド構成図を自動生成するPythonツール。
draw.io / Mermaid / PlantUML / SVG / HTML（インタラクティブ）の5形式に対応し、CLI・GUI の両方で利用可能。
`--provider all` でマルチプロバイダ混在構成図も生成可能。

## クイックリファレンス

```bash
# インストール（開発用: pytest-cov等を含む）
pip install -e ".[dev]"

# テスト実行（カバレッジ計測は pyproject.toml の addopts で自動有効）
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

# Kubernetesリソース
terrasketch generate --state samples/sample_k8s_state.json --provider kubernetes --output ./output

# Terraform plan プレビュー
terrasketch plan --plan samples/sample_plan.json --provider aws --output ./output

# コスト注釈付き
terrasketch generate --state samples/sample_state.json --provider aws --cost samples/sample_infracost.json --output ./output

# インタラクティブHTML出力
terrasketch generate --state samples/sample_state.json --provider aws --format html --output ./output

# タグベースグルーピング
terrasketch generate --state samples/sample_state.json --provider aws --group-by tag:Environment --output ./output

# GUI起動
terrasketch gui

# OpenTofu state（自動検出）
terrasketch generate --state samples/sample_opentofu_state.json --provider aws --output ./output

# OpenTofu明示指定
terrasketch generate --state samples/sample_opentofu_state.json --provider aws --runtime opentofu --output ./output
```

## ディレクトリ構造

```
terrasketch/
├── parser/
│   ├── state_parser.py      # Terraform / OpenTofu state JSON 解析（Resource dataclass）
│   ├── hcl_parser.py        # Terraform HCL (.tf) 解析（外部依存なし）
│   ├── plan_parser.py       # Terraform plan JSON 解析
│   └── validator.py         # 入力ファイル事前検証（--validate オプション）
├── cost/
│   └── annotator.py          # infracost JSON 解析・コスト注釈
├── graph/
│   ├── builder.py            # networkx DiGraph 構築・関係ルール適用
│   ├── grouping.py           # タグベースグルーピング
│   ├── security.py           # SG ingress/egress ルール注釈
│   └── summary.py            # リソース統計サマリー生成
├── layout/
│   └── engine.py             # 座標計算（階層/グリッド/切断グラフ分離）
├── renderer/
│   ├── drawio_renderer.py    # draw.io XML (mxfile) 生成
│   ├── mermaid_renderer.py   # Mermaid flowchart 生成
│   ├── plantuml_renderer.py  # PlantUML コンポーネント図 生成
│   ├── svg_renderer.py       # SVG/PNG 直接生成
│   └── html_renderer.py      # インタラクティブHTML（Cytoscape.js）生成
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

action/
├── action.yml                # GitHub Actions Composite Action 定義
└── comment.py                # PRコメント投稿スクリプト（urllib.request）

integrations/
├── atlantis/
│   ├── terrasketch_hook.sh   # Atlantis post-plan フックスクリプト
│   ├── atlantis.yaml.example # Atlantis カスタムワークフロー設定例
│   └── README.md             # Atlantis 連携セットアップガイド
└── spacelift/
    ├── terrasketch_hook.sh   # Spacelift after_plan フックスクリプト
    └── README.md             # Spacelift 連携セットアップガイド

vscode-extension/
├── package.json              # VS Code拡張マニフェスト
├── tsconfig.json             # TypeScript設定
├── .vscodeignore             # パッケージ除外設定
└── src/
    ├── extension.ts          # 拡張メインロジック（3コマンド登録）
    ├── preview.ts            # WebViewプレビューパネル
    ├── config.ts             # VS Code設定読み取り
    └── test/extension.test.ts # 拡張テスト雛形
```

## コーディング規約

- **コメント・docstringは全て日本語**
- Python 3.10+ の型ヒント構文を使用（`from __future__ import annotations`）
- 外部依存は `networkx` のみ。numpy 等の追加依存は避ける
- テストの docstring も日本語で記述

## Resource dataclass

- `Resource(id, type, name, provider, attributes={}, module_path="")` — `address` はプロパティ（`{type}.{name}`）でコンストラクタ引数ではない
- state JSON は `terraform show -json` / `tofu show -json` 形式: `values.root_module.resources[].values` に属性が格納される
- OpenTofu state は `opentofu_version` キーで自動検出。`--runtime` オプションで明示切替も可能

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

テスト388件: parser(6), graph(12), layout(9), renderer(20+16), mapping(11), integration(4), hcl_parser(12+15), diff(5), tfc(6+5), theme(10), watch(5+6), web(4+8), phase4_gcp(27), cli(22), validator(15), security_detail(14), tag_grouping(19), kubernetes(28), plan_parser(18), cost(17), html_renderer(14), opentofu(22), 他(23)
カバレッジ90%+（GUI除外）。`pyproject.toml` で `pytest-cov` 設定済み。

## テスト時の注意事項

- GUI（`terrasketch/gui/*`）はカバレッジ対象外（`pyproject.toml` の `[tool.coverage.run]` で除外）
- `logging.basicConfig` はpytest環境で効果がないため、ログレベルのアサートは避ける
- レンダラーのVPC/Subnet等コンテナタイプは `package`/`subgraph` としてレンダリングされ、`component`/ノードとは異なるコードパスを通る
- `.claude/` と `.coverage` はコミット対象外。ステージされていたら `git reset HEAD` で除外

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
- 将来の拡張計画: `docs/roadmap.md`（フェーズ8）
- `terrasketch validate` で入力ファイルの事前検証が可能（state / hcl / plan）
- OpenTofu stateも透過的にサポート（`--runtime auto` で自動検出）
- GitHub Actions: `action/action.yml` で `uses: terrasketch/action@v1` として利用可能
- Atlantis / Spacelift: `integrations/` ディレクトリにフックスクリプトを提供
- VS Code拡張: `vscode-extension/` にTypeScript製拡張の雛形（開発には `npm install && npm run compile`）
