# 出力形式

TerraSketch は 4 つの出力形式に対応しています。

## draw.io（デフォルト）

`.drawio` ファイルを生成します。[draw.io（diagrams.net）](https://app.diagrams.net/) で開いて編集できます。

```bash
terrasketch generate --state state.json --provider aws --format drawio
```

**特徴:**

- AWS/Azure/GCP の公式アイコンを使用
- VPC/Subnet のコンテナグルーピング
- ツールチップにリソース属性を表示
- セキュリティグループルールの注釈

## Mermaid

`.md` ファイルに Mermaid flowchart 構文を生成します。GitHub、GitLab、Notion 等で直接プレビューできます。

```bash
terrasketch generate --state state.json --provider aws --format mermaid
```

**特徴:**

- リソースタイプに応じたノード形状
- CSS クラスによる色分け
- diff モードの色分け対応

## PlantUML

`.puml` ファイルを生成します。PlantUML サーバーや CLI で PNG/SVG 画像に変換できます。

```bash
terrasketch generate --state state.json --provider aws --format plantuml
```

**特徴:**

- コンポーネント図として出力
- ステレオタイプによるリソース分類
- package による階層グルーピング

## SVG

`.svg` ファイルを直接生成します。外部ツールなしで画像として利用できます。

```bash
terrasketch generate --state state.json --provider aws --format svg
```
