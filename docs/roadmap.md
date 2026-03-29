# TerraSketch ロードマップ

本ドキュメントでは、TerraSketch の今後の機能拡張計画を優先度順に整理する。

> **最終更新:** 2026-03-29
> **現在のバージョン:** v0.1.0

---

## 現在の実装状況

### 完了済み

| カテゴリ | 項目 | 概要 |
|---|---|---|
| 基盤 | ネスト属性パス解決 | `_get_nested()` でドット区切りパス（`vpc_config.subnet_ids`）を辿る |
| 基盤 | 切断グラフ分離レイアウト | `weakly_connected_components` で各コンポーネントを独立配置 |
| 基盤 | テストカバレッジ強化 | 68件（parser 6, graph 11, layout 9, renderer 14, mapping 10, integration 4, hcl 12, 他 2） |
| UX | エッジタイプ区別 | `contains`（包含: 緑実線）と `references`（参照: 青破線）の視覚的区別 |
| UX | Mermaid VPC/Subnetネスト | subgraph による VPC > Subnet > リソースの3階層表現 |
| UX | draw.io ツールチップ | ホバー時に ARN / CIDR / tags 等の属性を表示 |
| UX | ログ基盤整備 | `print` → `logging` モジュール化、`--verbose` フラグ対応 |
| 拡張 | PlantUML レンダラー | ステレオタイプ・package階層化・エッジタイプ区別対応 |
| 拡張 | Terraform HCL 解析 | 外部依存なしの軽量パーサー、`--hcl` オプション |
| 拡張 | CI/CD パイプライン | GitHub Actions（Python 3.10/3.11/3.12 マトリクス、ruff リンター） |

---

## フェーズ 1 — 品質・安定性（優先度: 高）

### 1-1. ビューポート自動計算

**現状の課題:**
draw.io レンダラーのビューポートサイズが `dx="1422" dy="762"` にハードコードされている。
ノード数が多い場合やレイアウトが広がった場合に、描画範囲外にノードがはみ出す。

**改善方針:**
- 全ノードの座標からバウンディングボックスを算出
- マージンを加えた値を `dx` / `dy` に動的設定
- ページサイズ（`pageWidth` / `pageHeight`）も連動して調整

**対象ファイル:** `terrasketch/renderer/drawio_renderer.py`

### 1-2. GUI の PlantUML / HCL 対応

**現状の課題:**
GUI は draw.io / Mermaid のみ選択可能。PlantUML 出力と HCL 入力は CLI 限定。

**改善方針:**
- 出力形式に PlantUML を追加
- 入力形式に HCL ファイル / ディレクトリ選択を追加
- `main.py` の `generate()` を共通呼び出しにリファクタリング

**対象ファイル:** `terrasketch/gui/app.py`

### 1-3. Subnet コンテナグルーピング（draw.io）

**現状の課題:**
draw.io の VPC コンテナ内で Subnet はフラットなノードとして描画される。
Mermaid / PlantUML では Subnet の subgraph / package ネストが既に実装済みだが、draw.io は未対応。

**改善方針:**
- VPC コンテナ内に Subnet コンテナ（`container=1`）をネスト
- Subnet の子孫リソース座標を Subnet コンテナの相対座標に変換
- 2段階バウンディングボックス計算（VPC → Subnet → リソース）

**対象ファイル:** `terrasketch/renderer/drawio_renderer.py`

### 1-4. エッジラベル表示

**現状の課題:**
エッジに関係タイプ（contains / references）の情報はあるが、表示ラベルがない。
どの属性で繋がっているか（`vpc_id`、`subnet_id`等）が構成図から読み取れない。

**改善方針:**
- `build_graph()` でエッジに `attr_name` 属性を付与
- draw.io / Mermaid / PlantUML の各レンダラーで、`--labels` オプション有効時にエッジラベルを表示
- デフォルトは非表示（図の可読性を優先）

**対象ファイル:** `terrasketch/graph/builder.py`, 各レンダラー, `terrasketch/main.py`

---

## フェーズ 2 — 機能強化（優先度: 中）

### 2-1. diff モード（構成変更の可視化）

**概要:**
2つの Terraform state JSON を比較し、追加・削除・変更されたリソースを色分けで可視化する。

**設計方針:**
- `terrasketch diff --before old_state.json --after new_state.json`
- 追加リソース: 緑、削除リソース: 赤、変更リソース: 黄
- draw.io / Mermaid / PlantUML 全レンダラーで対応
- diff の判定基準: リソースアドレス（`type.name`）の一致

**新規ファイル:** `terrasketch/diff/comparator.py`
**対象ファイル:** `terrasketch/main.py`, 各レンダラー

### 2-2. レイアウトアルゴリズムの改善

**現状の課題:**
- 階層レイアウトはトポロジカルソートの最長パスに基づくが、同一層のノード配置が最適でない（交差エッジが多い場合がある）
- VPC 間のリソースが離れすぎる場合がある

**改善方針:**
- Sugiyama アルゴリズムの交差最小化ステップ（barycenter法）を導入
- コンテナ（VPC/Subnet）のサイズに基づく配置最適化
- `--layout` オプションで `hierarchical` / `grid` / `force` を選択可能に

**対象ファイル:** `terrasketch/layout/engine.py`

### 2-3. セキュリティルール詳細表示の強化

**現状の課題:**
- セキュリティルールはノードラベルに短縮形で表示されるのみ
- draw.io のツールチップにルールテーブルが含まれていない
- NSG ルールの priority / access（Allow/Deny）の可視化が不十分

**改善方針:**
- ツールチップに `get_rules_table()` の出力を統合
- ルール数に基づくノードサイズの動的調整
- Allow/Deny を色分け（緑/赤）で draw.io スタイルに反映
- SGルール間のフロー可視化（SG → EC2 のエッジにポート情報を注釈）

**対象ファイル:** `terrasketch/graph/security.py`, `terrasketch/renderer/drawio_renderer.py`

### 2-4. Terraform module 対応の強化

**現状の課題:**
- State Parser は `child_modules` を再帰的に辿るが、モジュール境界の情報が失われる
- どのリソースがどのモジュールに属するか区別できない

**改善方針:**
- `Resource` データクラスに `module_path` フィールドを追加
- モジュール境界を draw.io のコンテナ / Mermaid の subgraph で可視化
- `--group-by module` オプションでモジュール単位のグルーピングを選択可能に

**対象ファイル:** `terrasketch/parser/state_parser.py`, レンダラー各種

### 2-5. SVG / PNG 直接出力

**概要:**
draw.io を介さず、SVG または PNG を直接出力する。

**設計方針:**
- SVG: XML ベースで直接生成（外部依存なし）
- PNG: `cairosvg` または `Pillow` を使用（オプション依存）
- `--format svg` / `--format png` で選択

**新規ファイル:** `terrasketch/renderer/svg_renderer.py`

---

## フェーズ 3 — 拡張・エコシステム（優先度: 低〜中）

### 3-1. watch モード（ファイル変更監視）

**概要:**
State ファイルや HCL ファイルの変更を監視し、自動的に構成図を再生成する。

**設計方針:**
- `terrasketch watch --state state.json --output ./output`
- `watchdog` ライブラリ（オプション依存）によるファイル監視
- 変更検出時にパイプラインを再実行
- debounce（500ms）で頻繁な書き込みを抑制

**対象ファイル:** `terrasketch/main.py`（新規サブコマンド）

### 3-2. Web UI（ブラウザベース）

**概要:**
Tkinter GUI の代替として、ブラウザベースの Web UI を提供する。

**設計方針:**
- `terrasketch serve` でローカル HTTP サーバーを起動
- ファイルアップロード → プレビュー → ダウンロードのワークフロー
- Mermaid はブラウザ内でリアルタイムレンダリング
- draw.io / PlantUML はファイルダウンロード
- 依存: `http.server`（標準ライブラリのみ）

**新規ファイル:** `terrasketch/web/server.py`, `terrasketch/web/templates/`

### 3-3. カスタムテーマ / スタイル設定

**概要:**
リソースの色、形状、フォントなどをユーザーが設定ファイルで自由にカスタマイズ可能にする。

**設計方針:**
- `terrasketch.yaml` または `terrasketch.toml` 形式の設定ファイル
- リソースタイプ → 色、形状、アイコン のオーバーライド
- `--theme dark` / `--theme light` / `--theme custom` オプション
- デフォルトテーマは現在の配色を維持

```yaml
# terrasketch.yaml 例
theme:
  background: "#ffffff"
  edge_contains_color: "#2e7d32"
  edge_references_color: "#1565c0"

resources:
  aws_vpc:
    color: "#e8f5e9"
    icon: "mxgraph.aws4.vpc"
  aws_instance:
    color: "#fff3e0"
```

**新規ファイル:** `terrasketch/config/theme.py`

### 3-4. Terraform Cloud / Enterprise 連携

**概要:**
Terraform Cloud の API から直接 State を取得し、構成図を生成する。

**設計方針:**
- `terrasketch generate --tfc-workspace <org>/<workspace> --tfc-token <token>`
- Terraform Cloud State Versions API からの State JSON 取得
- トークンは環境変数 `TFC_TOKEN` でも指定可能
- **ローカル完結の原則** との兼ね合いから、オプション機能として明確に分離

**新規ファイル:** `terrasketch/remote/tfc_client.py`

### 3-5. プラグインシステム

**概要:**
サードパーティによるリソースマッピング・レンダラー・関係ルールの追加を可能にする。

**設計方針:**
- Python のエントリーポイント（`[project.entry-points]`）を活用
- `terrasketch.renderers` / `terrasketch.mappings` グループで外部プラグインを発見
- プラグインテンプレートリポジトリを提供

```toml
# 外部プラグインの pyproject.toml
[project.entry-points."terrasketch.renderers"]
d2 = "terrasketch_d2:D2Renderer"
```

---

## フェーズ 4 — プロバイダ拡張（優先度: 最低）

### 4-1. GCP 対応

**前提:** ユーザーの利用実態に基づき、最低優先度として位置付ける。

**対応範囲（初期）:**
- `google_compute_instance` / `google_compute_network` / `google_compute_subnetwork` 等の基本リソース
- draw.io の GCP アイコン（`mxgraph.gcp2.*`）
- 基本的な関係ルール（VPC → Subnet → Instance）

**対応範囲（拡張）:**
- GKE、Cloud Functions、Cloud SQL、Cloud Storage 等
- Firewall ルールの可視化

**対象ファイル:** `terrasketch/mapping/extended_resources.py`, `terrasketch/graph/builder.py`

### 4-2. マルチプロバイダ構成図

**概要:**
1つの構成図に AWS と Azure（将来は GCP も）のリソースを混在表示する。

**現状:**
`--provider` フラグでフィルタリングしているため、単一プロバイダのみ表示可能。

**改善方針:**
- `--provider all` オプションでフィルタを無効化
- プロバイダごとにレンダラー側でグルーピング
- プロバイダ間の参照関係（例: AWS→Azure のピアリング）を表現

---

## 優先度判定の基準

| 基準 | 説明 |
|---|---|
| **ユーザー影響度** | 日常の利用体験にどれだけ影響するか |
| **技術的依存関係** | 他の機能の前提条件になるか |
| **実装コスト** | 既存アーキテクチャへの影響範囲 |
| **外部依存** | 新たな依存ライブラリが必要か（最小依存原則） |

---

## 変更履歴

| 日付 | 内容 |
|---|---|
| 2026-03-29 | 初版作成。フェーズ1〜4の計画を策定 |
