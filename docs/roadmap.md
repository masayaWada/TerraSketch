# TerraSketch ロードマップ

本ドキュメントでは、TerraSketch の今後の機能拡張計画を優先度順に整理する。

> **最終更新:** 2026-03-31
> **現在のバージョン:** v0.1.0

---

## 実装済み

- [x] ネスト属性パス解決 — `_get_nested()` でドット区切りパス（`vpc_config.subnet_ids`）を辿る
- [x] 切断グラフ分離レイアウト — `weakly_connected_components` で各コンポーネントを独立配置
- [x] テストカバレッジ強化 — 68件（parser 6, graph 11, layout 9, renderer 14, mapping 10, integration 4, hcl 12, 他 2）
- [x] エッジタイプ区別 — `contains`（包含: 緑実線）と `references`（参照: 青破線）の視覚的区別
- [x] Mermaid VPC/Subnetネスト — subgraph による VPC > Subnet > リソースの3階層表現
- [x] draw.io ツールチップ — ホバー時に ARN / CIDR / tags 等の属性を表示
- [x] ログ基盤整備 — `print` → `logging` モジュール化、`--verbose` フラグ対応
- [x] PlantUML レンダラー — ステレオタイプ・package階層化・エッジタイプ区別対応
- [x] Terraform HCL 解析 — 外部依存なしの軽量パーサー、`--hcl` オプション
- [x] CI/CD パイプライン — GitHub Actions（Python 3.10/3.11/3.12 マトリクス、ruff リンター）

---

## フェーズ 1 — 品質・安定性（優先度: 高）

- [x] **1-1. ビューポート自動計算**
  - 現状: draw.io のビューポートサイズが `dx="1422" dy="762"` にハードコード
  - 改善: 全ノード座標からバウンディングボックスを算出し `dx` / `dy` を動的設定
  - 対象: `terrasketch/renderer/drawio_renderer.py`

- [x] **1-2. GUI の PlantUML / HCL 対応**
  - 現状: GUI は draw.io / Mermaid のみ選択可能。PlantUML と HCL 入力は CLI 限定
  - 改善: 出力形式に PlantUML を追加、入力に HCL ファイル / ディレクトリ選択を追加
  - 対象: `terrasketch/gui/app.py`

- [x] **1-3. Subnet コンテナグルーピング（draw.io）**
  - 現状: draw.io の VPC コンテナ内で Subnet はフラットなノードとして描画される
  - 改善: VPC コンテナ内に Subnet コンテナ（`container=1`）をネスト、2段階バウンディングボックス計算
  - 対象: `terrasketch/renderer/drawio_renderer.py`

- [x] **1-4. エッジラベル表示**
  - 現状: エッジに関係タイプ情報はあるが、接続属性名（`vpc_id` 等）が構成図から読み取れない
  - 改善: `build_graph()` でエッジに `attr_name` を付与、`--labels` オプションで表示切替
  - 対象: `terrasketch/graph/builder.py`, 各レンダラー, `terrasketch/main.py`

---

## フェーズ 2 — 機能強化（優先度: 中）

- [ ] **2-1. diff モード（構成変更の可視化）**
  - 2つの Terraform state JSON を比較し、追加/削除/変更リソースを色分けで可視化
  - `terrasketch diff --before old_state.json --after new_state.json`
  - 追加: 緑、削除: 赤、変更: 黄。全レンダラーで対応
  - 新規: `terrasketch/diff/comparator.py`

- [ ] **2-2. レイアウトアルゴリズムの改善**
  - 現状: 同一層のノード配置が最適でない（交差エッジが多い場合がある）
  - 改善: Sugiyama アルゴリズムの交差最小化（barycenter法）を導入
  - `--layout` オプションで `hierarchical` / `grid` / `force` を選択可能に
  - 対象: `terrasketch/layout/engine.py`

- [ ] **2-3. セキュリティルール詳細表示の強化**
  - 現状: ノードラベルに短縮形のみ、ツールチップにルールテーブル未統合
  - 改善: ツールチップに `get_rules_table()` 統合、Allow/Deny 色分け、ポート情報のエッジ注釈
  - 対象: `terrasketch/graph/security.py`, `terrasketch/renderer/drawio_renderer.py`

- [ ] **2-4. Terraform module 対応の強化**
  - 現状: `child_modules` を再帰的に辿るがモジュール境界の情報が失われる
  - 改善: `Resource` に `module_path` を追加、モジュール境界をコンテナ / subgraph で可視化
  - `--group-by module` オプションでグルーピング選択
  - 対象: `terrasketch/parser/state_parser.py`, 各レンダラー

- [ ] **2-5. SVG / PNG 直接出力**
  - draw.io を介さず SVG（XML直接生成、外部依存なし）/ PNG（`Pillow` オプション依存）を出力
  - `--format svg` / `--format png` で選択
  - 新規: `terrasketch/renderer/svg_renderer.py`

---

## フェーズ 3 — 拡張・エコシステム（優先度: 低〜中）

- [ ] **3-1. watch モード（ファイル変更監視）**
  - State / HCL の変更を監視し自動再生成（`watchdog` オプション依存、debounce 500ms）
  - `terrasketch watch --state state.json --output ./output`

- [ ] **3-2. Web UI（ブラウザベース）**
  - `terrasketch serve` でローカル HTTP サーバーを起動
  - ファイルアップロード → プレビュー → ダウンロードのワークフロー
  - Mermaid はブラウザ内でリアルタイムレンダリング
  - 依存: `http.server`（標準ライブラリのみ）
  - 新規: `terrasketch/web/server.py`, `terrasketch/web/templates/`

- [ ] **3-3. カスタムテーマ / スタイル設定**
  - `terrasketch.yaml` / `terrasketch.toml` でリソースの色・形状・アイコンをカスタマイズ
  - `--theme dark` / `--theme light` / `--theme custom` オプション
  - 設定例:
    ```yaml
    theme:
      background: "#ffffff"
      edge_contains_color: "#2e7d32"
      edge_references_color: "#1565c0"
    resources:
      aws_vpc:
        color: "#e8f5e9"
        icon: "mxgraph.aws4.vpc"
    ```
  - 新規: `terrasketch/config/theme.py`

- [ ] **3-4. Terraform Cloud / Enterprise 連携**
  - `terrasketch generate --tfc-workspace <org>/<workspace> --tfc-token <token>`
  - State Versions API から State JSON を直接取得
  - トークンは環境変数 `TFC_TOKEN` でも指定可能
  - ローカル完結原則との兼ね合いからオプション機能として分離
  - 新規: `terrasketch/remote/tfc_client.py`

- [ ] **3-5. プラグインシステム**
  - Python エントリーポイント（`[project.entry-points]`）で外部プラグインを発見
  - `terrasketch.renderers` / `terrasketch.mappings` グループでレンダラー・マッピングを拡張
  - プラグイン例:
    ```toml
    [project.entry-points."terrasketch.renderers"]
    d2 = "terrasketch_d2:D2Renderer"
    ```

---

## フェーズ 4 — プロバイダ拡張（優先度: 最低）

- [ ] **4-1. GCP 対応**
  - 初期: `google_compute_instance` / `google_compute_network` / `google_compute_subnetwork` 等の基本リソース + `mxgraph.gcp2.*` アイコン
  - 拡張: GKE、Cloud Functions、Cloud SQL、Cloud Storage、Firewall ルール可視化
  - 対象: `terrasketch/mapping/extended_resources.py`, `terrasketch/graph/builder.py`

- [ ] **4-2. マルチプロバイダ構成図**
  - `--provider all` でフィルタを無効化し、AWS / Azure / GCP を1つの構成図に混在表示
  - プロバイダごとのグルーピングと、プロバイダ間参照関係の表現

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
| 2026-03-31 | チェックリスト形式に変更 |
| 2026-03-29 | 初版作成。フェーズ1〜4の計画を策定 |
