# TerraSketch

Terraform state から draw.io 構成図を自動生成するツール。

## 設計原則

**Terraform state を唯一のソースオブトゥルース（信頼の源泉）とする。**

- クラウド実環境や API には依存しない
- Terraform state（JSON）のみから構成図を生成
- 構成図は Terraform の派生物として扱う

## 機能

- Terraform state JSON を解析し、リソースの依存関係グラフを構築
- draw.io 形式（`.drawio`）の構成図を自動生成
- AWS / Azure リソースのアイコンマッピング対応
- CLI / GUI の両方で実行可能

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
terrasketch generate --state state.json --provider aws --output ./output
```

オプション:

| フラグ | 説明 | デフォルト |
|---|---|---|
| `--state` | Terraform state JSON のパス | （必須） |
| `--provider` | クラウドプロバイダ (`aws` / `azure`) | `aws` |
| `--output` | 出力ディレクトリ | `.`（カレント） |

### GUI モード

```bash
terrasketch gui
```

GUI では以下の操作が可能:

1. state.json ファイルを選択
2. 出力フォルダを選択
3. プロバイダを選択（AWS / Azure）
4. 「Generate Diagram」ボタンで実行
5. ログエリアで進捗確認

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
├── layout/       # ノード座標計算
├── renderer/     # draw.io XML 生成
├── mapping/      # Terraform → draw.io アイコンマッピング
├── gui/          # Tkinter GUI
└── main.py       # CLI / GUI エントリーポイント
```

### 処理フロー

1. `state.json` 読み込み
2. リソース抽出（Parser）
3. 依存関係グラフ構築（Graph Builder）
4. レイアウト座標計算（Layout Engine）
5. draw.io XML 生成・出力（Renderer）

## MVP 対応リソース

### AWS

- `aws_vpc`
- `aws_subnet`
- `aws_instance`（EC2）
- `aws_security_group`

### Azure（拡張済み）

- `azurerm_virtual_network`
- `azurerm_subnet`
- `azurerm_linux_virtual_machine`
- `azurerm_network_security_group`

未対応リソースはデフォルトスタイルで表示されます。

## 拡張ポイント

以下の拡張が容易にできる設計:

- **プロバイダ追加**: `mapping/resource_map.py` にマッピングを追加
- **関係ルール追加**: `graph/builder.py` にルールを追加
- **出力形式追加**: `renderer/` に Mermaid / PlantUML レンダラーを追加
- **HCL 解析**: `parser/` に HCL パーサーを追加
- **セキュリティ可視化**: SecurityGroup のルールをエッジラベルとして表示

## ライセンス

MIT
