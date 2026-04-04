# CLI リファレンス

## コマンド一覧

### `terrasketch generate`

Terraform state / HCL ファイルから構成図を生成する。

```bash
terrasketch generate --state state.json --provider aws [OPTIONS]
terrasketch generate --hcl main.tf --provider aws [OPTIONS]
terrasketch generate --hcl ./terraform/ --provider aws [OPTIONS]
```

**必須引数（いずれか）:**

- `--state FILE` — Terraform state JSON ファイル
- `--hcl FILE|DIR` — Terraform HCL ファイルまたはディレクトリ

**オプション:**

| フラグ | デフォルト | 説明 |
|---|---|---|
| `--provider` | `aws` | `aws` / `azure` / `gcp` / `all` |
| `--output` | `.` | 出力ディレクトリ |
| `--format` | `drawio` | `drawio` / `mermaid` / `plantuml` / `svg` |
| `--security` | off | セキュリティグループルールを注釈 |
| `--summary` | off | リソースサマリーを標準出力に表示 |
| `--labels` | off | エッジに接続属性名ラベルを表示 |
| `--layout` | `hierarchical` | `hierarchical` / `grid` / `force` |
| `--group-by` | なし | `module` — モジュール境界でグルーピング |
| `--theme` | なし | テーマ名またはテーマファイルのパス |
| `-v, --verbose` | off | デバッグログを表示 |

### `terrasketch validate`

入力ファイルの形式を事前検証する。

```bash
terrasketch validate --state state.json
terrasketch validate --hcl main.tf
```

### `terrasketch diff`

2 つの state を比較し、構成変更を色分け可視化する。

```bash
terrasketch diff --before old.json --after new.json --provider aws --output ./output
```

### `terrasketch watch`

ファイル変更を監視し、構成図を自動再生成する。

```bash
terrasketch watch --state state.json --output ./output
```

### `terrasketch serve`

Web UI をブラウザで起動する。

```bash
terrasketch serve --port 8080
```

### `terrasketch tfc`

Terraform Cloud/Enterprise から state を取得し構成図を生成する。

```bash
terrasketch tfc --workspace org/workspace --provider aws --output ./output
```

### `terrasketch gui`

Tkinter ベースの GUI を起動する。

```bash
terrasketch gui
```
