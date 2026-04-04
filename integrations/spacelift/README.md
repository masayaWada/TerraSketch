# Spacelift 連携

Spacelift の `after_plan` フックに TerraSketch を統合し、プラン実行後に構成図を自動生成します。

## 前提条件

- Spacelift スタックが設定済みであること
- Spacelift のランタイム環境に Python 3.10+ がインストールされていること
- TerraSketch がインストールされていること:
  ```bash
  pip install terrasketch
  ```
- Terraform CLI が利用可能であること

## セットアップ手順

### 1. カスタムランタイム（推奨）

Spacelift のカスタム Docker ランタイムを使用して TerraSketch をプリインストールします。

`Dockerfile` の例:

```dockerfile
FROM public.ecr.aws/spacelift/runner-terraform:latest

# TerraSketch をインストール
RUN pip install terrasketch
```

### 2. before_init フックでのインストール（代替）

カスタムランタイムを使用しない場合、`before_init` フックで毎回インストールできます:

```bash
pip install terrasketch
```

> **注意**: 毎回インストールするため実行時間が増加します。カスタムランタイムの使用を推奨します。

### 3. フックスクリプトの配置

`integrations/spacelift/terrasketch_hook.sh` をリポジトリに含めます。

### 4. Spacelift スタックの設定

Spacelift の管理画面またはスタック設定ファイルで `after_plan` フックを設定します。

#### 管理画面から設定する場合

1. Spacelift ダッシュボードで対象スタックを開く
2. **Settings** > **Hooks** に移動
3. **After plan** セクションに以下を追加:
   ```bash
   bash integrations/spacelift/terrasketch_hook.sh
   ```

#### Spacelift Terraform プロバイダで設定する場合

```hcl
resource "spacelift_stack" "example" {
  name       = "my-infrastructure"
  repository = "my-repo"
  branch     = "main"

  after_plan = [
    "bash integrations/spacelift/terrasketch_hook.sh"
  ]
}
```

### 5. 環境変数（オプション）

Spacelift スタックの環境変数でフックの動作をカスタマイズできます:

| 変数名 | デフォルト値 | 説明 |
|--------|-------------|------|
| `TERRASKETCH_FORMAT` | `mermaid` | 出力形式（`mermaid` / `drawio` / `plantuml` / `svg` / `html`） |
| `TERRASKETCH_PROVIDER` | `all` | プロバイダ（`aws` / `azure` / `gcp` / `kubernetes` / `all`） |
| `TERRASKETCH_EXTRA_OPTS` | （空） | 追加オプション（例: `--labels --security`） |

Spacelift 管理画面の **Environment** セクションで設定するか、Terraform で定義できます:

```hcl
resource "spacelift_environment_variable" "terrasketch_provider" {
  stack_id = spacelift_stack.example.id
  name     = "TERRASKETCH_PROVIDER"
  value    = "aws"
}
```

## Spacelift 固有の環境変数

フックスクリプトは以下の Spacelift 環境変数を参照します:

| 変数名 | 説明 |
|--------|------|
| `SPACELIFT_WORKSPACE_ROOT` | Terraform ワークスペースのルートディレクトリ |
| `SPACELIFT_PLAN_FILE` | プランファイルのパス（利用可能な場合） |

## 出力

構成図は Spacelift の実行ログに出力されます。Mermaid 形式の場合:

```
========== TerraSketch 構成図 (Mermaid) ==========
graph TB
    subgraph vpc_main["aws_vpc.main"]
        subgraph subnet_public["aws_subnet.public"]
            aws_instance_web["aws_instance.web"]
        end
    end
    aws_instance_web -->|security_group_ids| aws_security_group_web
==================================================
```

## トラブルシューティング

### terrasketch コマンドが見つからない

- カスタムランタイムを使用している場合、Docker イメージに TerraSketch が含まれているか確認
- `before_init` フックでインストールしている場合、`pip install` が成功しているかログを確認
- Python の PATH が正しく設定されているか確認:
  ```bash
  which python3
  python3 -m pip show terrasketch
  ```

### プランファイルが見つからない

- Spacelift はプランファイルの場所がバージョンにより異なる場合があります
- `SPACELIFT_PLAN_FILE` 環境変数が設定されていない場合、スクリプトは `terraform show` で現在の state から構成図を生成します

### 構成図が空になる

- Terraform state にリソースが存在するか確認
- `TERRASKETCH_PROVIDER` がリソースのプロバイダと一致しているか確認（不明な場合は `all` を使用）
