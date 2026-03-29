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
- **draw.io / Mermaid 出力** — 2形式に対応、用途に応じて選択可能
- **VPC コンテナグルーピング** — VPC/VNet をバウンディングボックスで描画し、子リソースをネスト表示
- **セキュリティルール可視化** — SecurityGroup の ingress/egress ルールをノードラベルに表示
- **30種以上のリソースアイコン** — AWS 28種、Azure 13種のdraw.ioネイティブアイコン対応
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

# セキュリティルール注釈 + サマリー表示
terrasketch generate --state state.json --provider aws --security --summary
```

#### CLIオプション一覧

| フラグ | 説明 | デフォルト |
|---|---|---|
| `--state` | Terraform state JSON のパス | （必須） |
| `--provider` | クラウドプロバイダ (`aws` / `azure`) | `aws` |
| `--output` | 出力ディレクトリ | `.`（カレント） |
| `--format` | 出力形式 (`drawio` / `mermaid`) | `drawio` |
| `--security` | セキュリティグループルールを構成図に注釈 | off |
| `--summary` | リソースサマリーを標準出力に表示 | off |

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
├── parser/       # Terraform state JSON 解析
├── graph/        # リソース依存関係グラフ構築 (networkx)
│   ├── builder.py      # グラフビルダー
│   ├── security.py     # セキュリティルール可視化
│   └── summary.py      # リソースサマリー生成
├── layout/       # ノード座標計算（階層/グリッド）
├── renderer/     # 出力レンダラー
│   ├── drawio_renderer.py    # draw.io XML 生成
│   └── mermaid_renderer.py   # Mermaid flowchart 生成
├── mapping/      # Terraform → draw.io アイコンマッピング
│   ├── resource_map.py       # 基本マッピング（MVP）
│   └── extended_resources.py # 拡張マッピング（30種以上）
├── gui/          # Tkinter GUI
└── main.py       # CLI / GUI エントリーポイント
```

### 処理フロー

```
Terraform State JSON
    ↓
1. Parser（リソース抽出）
    ↓
2. Graph Builder（依存関係グラフ構築）
    ↓
3. Security Annotator（SGルール注釈）※オプション
    ↓
4. Layout Engine（ノード座標計算）
    ↓
5. Renderer（draw.io XML or Mermaid 生成）
    ↓
.drawio / .md 出力ファイル
```

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

37件のユニットテスト・統合テストを収録:

- `test_parser.py` — state JSON 解析（正常系・異常系・子モジュール）
- `test_graph.py` — グラフ構築・セキュリティ注釈・サマリー
- `test_layout.py` — 階層レイアウト・グリッドフォールバック・座標正規化
- `test_renderer.py` — draw.io XML 生成・Mermaid 生成・空グラフ
- `test_mapping.py` — AWS/Azure/拡張リソースマッピング・プロバイダ判定
- `test_integration.py` — サンプルstateからの全パイプライン

## 拡張ポイント

以下の拡張が容易にできる設計:

| 拡張内容 | 対象ファイル |
|---|---|
| プロバイダ追加（GCP等） | `mapping/resource_map.py`, `mapping/extended_resources.py` |
| 関係ルール追加 | `graph/builder.py`, `mapping/extended_resources.py` |
| 出力形式追加（PlantUML等） | `renderer/` に新レンダラーを追加 |
| HCL 解析 | `parser/` に HCL パーサーを追加 |
| セキュリティ可視化強化 | `graph/security.py` |

## ライセンス

MIT
