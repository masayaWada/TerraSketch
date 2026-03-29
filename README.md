# TerraSketch

Terraform state（JSON）を読み込むだけで、リソース間の依存関係を解析し、
クラウドアイコン付きの構成図をdraw.io/Mermaid形式で自動生成するローカル完結型ツール。

> **TerraSketch** は「Terraform state を唯一のソースオブトゥルース」とする設計原則に基づき、
> クラウド実環境や API に一切依存せず、state JSON だけから AWS / Azure の構成図を自動生成します。
> VPC コンテナグルーピング、セキュリティルール可視化、30 種以上のリソースアイコン対応を備え、
> CLI・GUI・draw.io・Mermaid の 4 通りで利用できます。

## 設計原則

**Terraform state を唯一のソースオブトゥルース（信頼の源泉）とする。**

- クラウド実環境や API には依存しない
- Terraform state（JSON）のみから構成図を生成
- 構成図は Terraform の派生物として扱う

## 主な特徴

- **Terraform state JSON のみで完結** — クラウド認証情報やAPIアクセス不要
- **draw.io / Mermaid / PlantUML 出力** — 3形式に対応、用途に応じて選択可能
- **VPC コンテナグルーピング** — VPC/VNet をバウンディングボックスで描画し、子リソースをネスト表示
- **セキュリティルール可視化** — SecurityGroup の ingress/egress ルールをノードラベルに表示
- **40種以上のリソースアイコン** — AWS 28種、Azure 13種のdraw.ioネイティブアイコン対応
- **HCL 直接解析** — State JSON がなくても .tf ファイルから構成図を生成可能
- **エッジタイプ区別** — 包含関係（実線）と参照関係（破線）を視覚的に区別
- **リソースツールチップ** — draw.io でホバー時に ARN/CIDR/タグ等の属性を表示
- **CLI / GUI 両対応** — コマンドライン・Tkinter GUI どちらからでも実行可能
- **リソースサマリー** — タイプ別集計、グラフ統計、ルート/リーフ分析
- **ローカル完結** — 外部サービスへの通信なし、OSS のみで構成

## セットアップ

### 必要環境

- Python 3.10 以上

### インストール

```bash
# リポジトリをクローン
git clone https://github.com/masayawada/terrasketch.git
cd terrasketch

# 依存パッケージのインストール
pip install -e .
```

### 依存ライブラリ

- `networkx` — グラフ構築・レイアウト計算

## 使い方

### Terraform state の取得

```bash
terraform show -json terraform.tfstate > state.json
```

### CLI モード

```bash
# draw.io 形式で出力（デフォルト）
terrasketch generate --state state.json --provider aws --output ./output

# Mermaid 形式で出力
terrasketch generate --state state.json --provider aws --format mermaid

# PlantUML 形式で出力
terrasketch generate --state state.json --provider aws --format plantuml

# HCL ファイルから直接生成
terrasketch generate --hcl main.tf --provider aws --output ./output

# HCL ディレクトリから生成
terrasketch generate --hcl ./terraform/ --provider aws --output ./output

# セキュリティルール注釈 + サマリー + 詳細ログ
terrasketch generate --state state.json --provider aws --security --summary --verbose
```

#### CLIオプション一覧

| フラグ | 説明 | デフォルト |
|---|---|---|
| `--state` | Terraform state JSON のパス | `--state` または `--hcl` が必須 |
| `--hcl` | Terraform HCL ファイル/ディレクトリのパス | `--state` または `--hcl` が必須 |
| `--provider` | クラウドプロバイダ (`aws` / `azure`) | `aws` |
| `--output` | 出力ディレクトリ | `.`（カレント） |
| `--format` | 出力形式 (`drawio` / `mermaid` / `plantuml`) | `drawio` |
| `--security` | セキュリティグループルールを構成図に注釈 | off |
| `--summary` | リソースサマリーを標準出力に表示 | off |
| `--verbose`, `-v` | デバッグレベルの詳細ログを表示 | off |

### GUI モード

```bash
terrasketch gui
```

GUI では以下の操作が可能:

1. state.json ファイルを選択
2. 出力フォルダを選択
3. プロバイダを選択（AWS / Azure）
4. 出力形式を選択（draw.io / Mermaid）
5. オプション設定（セキュリティルール表示 / サマリー表示）
6. 「構成図を生成」ボタンで実行
7. ログエリアで進捗確認

### サンプルで試す

```bash
terrasketch generate --state samples/sample_state.json --provider aws --output ./output
```

生成された `terrasketch_output.drawio` を [draw.io](https://app.diagrams.net/) で開くと構成図を確認できます。

## アーキテクチャ

```
terrasketch/
├── parser/       # 入力ファイル解析
│   ├── state_parser.py       # Terraform state JSON 解析
│   └── hcl_parser.py         # Terraform HCL (.tf) 解析
├── graph/        # リソース依存関係グラフ構築 (networkx)
│   ├── builder.py      # グラフビルダー（ネスト属性・エッジタイプ対応）
│   ├── security.py     # セキュリティルール可視化
│   └── summary.py      # リソースサマリー生成
├── layout/       # ノード座標計算（階層/グリッド/切断グラフ分離）
├── renderer/     # 出力レンダラー
│   ├── drawio_renderer.py    # draw.io XML 生成（ツールチップ付き）
│   ├── mermaid_renderer.py   # Mermaid flowchart 生成（VPCネスト対応）
│   └── plantuml_renderer.py  # PlantUML コンポーネント図 生成
├── mapping/      # Terraform → draw.io アイコンマッピング
│   ├── resource_map.py       # 基本マッピング（MVP）
│   └── extended_resources.py # 拡張マッピング（40種以上）
├── gui/          # Tkinter GUI
└── main.py       # CLI / GUI エントリーポイント
```

### 処理フロー

```
Terraform State JSON / HCL ファイル
    ↓
1. Parser（リソース抽出）
    ↓
2. Graph Builder（依存関係グラフ構築 + エッジタイプ分類）
    ↓
3. Security Annotator（SGルール注釈）※オプション
    ↓
4. Layout Engine（ノード座標計算 + 切断グラフ分離）
    ↓
5. Renderer（draw.io / Mermaid / PlantUML 生成）
    ↓
.drawio / .md / .puml 出力ファイル
```

詳細な設計ドキュメントは `docs/` ディレクトリを参照:
- `docs/architecture.md` — アーキテクチャ設計書
- `docs/data-flow.md` — データフロー詳細
- `docs/extension-guide.md` — 拡張ガイド
- `docs/roadmap.md` — 機能拡張ロードマップ

## 対応リソース

### AWS（28種）

**基本（MVP）:**
`aws_vpc` / `aws_subnet` / `aws_instance`（EC2）/ `aws_security_group` / `aws_internet_gateway` / `aws_nat_gateway` / `aws_route_table` / `aws_network_interface`

**拡張:**
`aws_lambda_function` / `aws_ecs_cluster` / `aws_ecs_service` / `aws_autoscaling_group` / `aws_s3_bucket` / `aws_ebs_volume` / `aws_db_instance`（RDS）/ `aws_dynamodb_table` / `aws_elasticache_cluster` / `aws_lb` / `aws_alb` / `aws_cloudfront_distribution` / `aws_route53_zone` / `aws_api_gateway_rest_api` / `aws_elastic_ip` / `aws_iam_role` / `aws_iam_policy` / `aws_kms_key` / `aws_sqs_queue` / `aws_sns_topic` / `aws_cloudwatch_log_group`

### Azure（13種）

**基本:**
`azurerm_virtual_network` / `azurerm_subnet` / `azurerm_linux_virtual_machine` / `azurerm_network_security_group` / `azurerm_resource_group` / `azurerm_network_interface`

**拡張:**
`azurerm_windows_virtual_machine` / `azurerm_storage_account` / `azurerm_sql_server` / `azurerm_lb` / `azurerm_application_gateway` / `azurerm_kubernetes_cluster` / `azurerm_function_app`

未対応リソースはデフォルトスタイル（角丸矩形）で表示されます。

## テスト

```bash
python -m pytest tests/ -v
```

68件のユニットテスト・統合テストを収録:

- `test_parser.py` — state JSON 解析（正常系・異常系・子モジュール）
- `test_hcl_parser.py` — HCL解析（リソース抽出・属性・タグ・コメント）
- `test_graph.py` — グラフ構築・ネスト属性・セキュリティ注釈・サマリー
- `test_layout.py` — 階層レイアウト・グリッド・切断グラフ分離・大規模グラフ
- `test_renderer.py` — draw.io / Mermaid / PlantUML・エッジタイプ・ツールチップ
- `test_mapping.py` — AWS/Azure/拡張リソースマッピング・プロバイダ判定
- `test_integration.py` — サンプルstateからの全パイプライン（3形式）

## 拡張ポイント

以下の拡張が容易にできる設計（詳細は `docs/extension-guide.md` を参照）:

| 拡張内容 | 対象ファイル |
|---|---|
| プロバイダ追加（GCP等） | `mapping/extended_resources.py`, `graph/builder.py` |
| 関係ルール追加 | `graph/builder.py`, `mapping/extended_resources.py` |
| 出力形式追加 | `renderer/` に新レンダラーを追加、`main.py` に分岐追加 |
| セキュリティ可視化強化 | `graph/security.py` |

## ライセンス

MIT
