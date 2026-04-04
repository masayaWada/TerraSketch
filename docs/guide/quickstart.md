# クイックスタート

## 1. State JSON を用意する

```bash
cd your-terraform-project
terraform show -json > state.json
```

## 2. 構成図を生成する

```bash
# draw.io形式（デフォルト）
terrasketch generate --state state.json --provider aws --output ./output

# Mermaid形式
terrasketch generate --state state.json --provider aws --format mermaid --output ./output

# PlantUML形式
terrasketch generate --state state.json --provider aws --format plantuml --output ./output
```

## 3. 入力ファイルを事前検証する

```bash
terrasketch validate --state state.json
```

## 4. Diff モードで変更を可視化

```bash
terrasketch diff --before old_state.json --after new_state.json --provider aws --output ./output
```

## 5. オプション

| オプション | 説明 |
|---|---|
| `--provider` | `aws` / `azure` / `gcp` / `all` |
| `--format` | `drawio` / `mermaid` / `plantuml` / `svg` |
| `--security` | セキュリティグループルールを注釈 |
| `--summary` | リソースサマリーを表示 |
| `--labels` | エッジに属性名ラベルを表示 |
| `--layout` | `hierarchical` / `grid` / `force` |
| `--group-by module` | モジュール境界でグルーピング |
| `--theme` | テーマ名またはテーマファイルのパス |
