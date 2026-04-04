# TerraSketch ロードマップ

本ドキュメントでは、TerraSketch の今後の機能拡張計画を優先度順に整理する。

> **最終更新:** 2026-04-04
> **現在のバージョン:** v0.4.0

---

## 実装済み（v0.1.0 → v0.2.0）

<details>
<summary>クリックで展開</summary>

- Terraform state JSON / HCL 解析
- draw.io / Mermaid / PlantUML / SVG 出力
- AWS / Azure / GCP マルチプロバイダ対応
- VPC → Subnet コンテナグルーピング
- エッジタイプ区別（contains / references）・ラベル表示
- diff モード（構成変更の色分け可視化）
- レイアウトアルゴリズム選択（hierarchical / grid / force）
- セキュリティルール詳細表示・ツールチップ
- Terraform module 境界の可視化
- watch モード（ファイル変更監視・自動再生成）
- Web UI / GUI（タブ化UI）
- カスタムテーマ（TOML設定）
- Terraform Cloud / Enterprise 連携
- プラグインシステム（entry_points）
- GitHub Actions CI/CD

</details>

---

## フェーズ 5 — DX・品質向上（優先度: 高）✅ 完了

- [x] **5-1. PyPI パッケージ公開**
  - `pyproject.toml` 整備（メタデータ・分類子・ライセンス・README・URL）
  - SemVer v0.2.0 でバージョニング
  - GitHub Actions で PyPI への自動リリースパイプライン構築（`.github/workflows/release.yml`）

- [x] **5-2. テストカバレッジ 90%+ 到達**
  - 154件 → 270件にテスト拡充（CLI、バリデーター、Web統合、セキュリティ詳細等）
  - `pytest-cov` でカバレッジ閾値85%ゲート設定、実測91%+
  - GUI（Tkinter）はカバレッジ対象から除外

- [x] **5-3. エラーメッセージの改善**
  - `terrasketch validate --state/--hcl` で入力ファイルの事前検証
  - JSON構文エラー、plan出力の誤指定、欠落キー等に対処ヒントを表示
  - `generate` コマンド実行前にも自動検証を実施

- [x] **5-4. ドキュメントサイト構築**
  - MkDocs Material でドキュメントサイト生成
  - チュートリアル、CLIリファレンス、出力形式ガイド、プラグイン開発ガイド
  - GitHub Pages へのデプロイ自動化（`.github/workflows/docs.yml`）

---

## フェーズ 6 — 機能拡張（優先度: 中）✅ 完了

- [x] **6-1. Kubernetes リソース対応**
  - Terraform の `kubernetes_*` リソース（Namespace/Deployment/Service/Ingress/Pod/StatefulSet/ConfigMap/Secret/HPA）を構成図に可視化
  - Namespace をコンテナとして階層表現（全4+1レンダラー対応）
  - `--provider kubernetes` フィルタ、Mermaid形状・PlantUMLステレオタイプ定義
  - サンプル: `samples/sample_k8s_state.json`

- [x] **6-2. コスト注釈表示**
  - `infracost breakdown --format json` 出力との統合（`--cost` オプション）
  - ノードに月額コスト推定を注釈表示（全5レンダラー対応）
  - diffモードでのコスト増減の色分け（`annotate_cost_diff()`）
  - サンプル: `samples/sample_infracost.json`

- [x] **6-3. インタラクティブ HTML 出力**
  - Cytoscape.js ベースのインタラクティブ構成図
  - ズーム・パン・ノードクリックで詳細サイドパネル表示
  - プロバイダ別フィルタ、リソース名検索
  - `--format html` で出力、diff/plan/cost/タグ全対応

- [x] **6-4. Terraform plan 対応**
  - `terraform show -json <planfile>` 形式のplan JSON解析
  - `terrasketch plan --plan <planfile>` で変更予測の構成図を生成
  - create/delete/update/replace を色分け表示（既存diff機構を再利用）
  - plan JSONバリデーション（`validate_plan_file()`）
  - サンプル: `samples/sample_plan.json`

- [x] **6-5. タグベースグルーピング**
  - `--group-by tag:Environment` でタグ値に基づくグルーピング
  - 任意のタグキーを指定可能、Azure `tags_all` フォールバック対応
  - 全5レンダラーでグループコンテナ/subgraph/package/rect描画

---

## フェーズ 7 — エコシステム連携（優先度: 低〜中）✅ 完了

- [x] **7-1. VS Code 拡張**
  - `.tf` / `.tfstate` ファイルからワンクリックで構成図生成（コマンドパレット対応）
  - サイドパネルでのプレビュー表示（SVG / HTML WebView）
  - ファイル保存時の自動更新（watch モード統合）
  - 設定: provider / format / pythonPath / autoGenerate / runtime
  - `vscode-extension/` ディレクトリにTypeScript製拡張の雛形

- [x] **7-2. GitHub Actions アクション公開**
  - `uses: terrasketch/action@v1` で PR に構成図を自動コメント
  - diff モードで変更前後の構成図比較を PR レビューに統合
  - アーティファクトとして構成図ファイルを保存
  - Composite Action（`action/action.yml`）+ PRコメントスクリプト（`action/comment.py`）
  - セルフテスト用ワークフロー（`.github/workflows/test-action.yml`）

- [x] **7-3. Atlantis / Spacelift 連携**
  - PR ベースの Terraform ワークフローに構成図生成を組み込み
  - plan 実行後に自動で構成図を生成しコメント投稿
  - Atlantis カスタムワークフロー用フックスクリプト + `atlantis.yaml` サンプル
  - Spacelift after_plan フックスクリプト
  - `integrations/atlantis/` / `integrations/spacelift/` ディレクトリ

- [x] **7-4. OpenTofu 対応**
  - OpenTofu の state 形式との互換性検証・対応（`opentofu_version` 自動検出）
  - `--runtime opentofu` / `--runtime auto` オプション（全コマンド対応）
  - バリデーターの OpenTofu 対応（エラーメッセージに `tofu` コマンドを案内）
  - サンプル: `samples/sample_opentofu_state.json`、テスト22件追加

---

## フェーズ 8 — 高度な可視化（優先度: 低）

- [ ] **8-1. ネットワークトポロジービュー**
  - CIDR ベースのサブネット配置・ルートテーブル可視化
  - VPN / Peering / Transit Gateway の接続図
  - セキュリティグループのルールフロー図

- [ ] **8-2. 時系列変更ビュー**
  - 複数の state バージョンを時系列でアニメーション表示
  - Git 履歴から state の変遷を自動追跡
  - タイムラインスライダーでの状態遷移

- [ ] **8-3. AI 支援レイアウト**
  - リソース間の論理的関係を考慮した自動レイアウト最適化
  - ユーザーの手動配置を学習し、類似構成に適用
  - 構成図の自然言語サマリー生成

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
| 2026-04-04 | v0.4.0 — フェーズ7完了（VS Code拡張・GitHub Actions・Atlantis/Spacelift連携・OpenTofu対応） |
| 2026-04-04 | v0.3.0 — フェーズ6完了（K8s対応・コスト注釈・HTML出力・plan対応・タググルーピング） |
| 2026-04-04 | v0.2.0 — フェーズ5完了（PyPI公開準備・テスト91%+・エラー改善・ドキュメントサイト） |
| 2026-04-04 | v0.2.0 — フェーズ1〜4完了。フェーズ5〜8の新計画を策定 |
| 2026-03-31 | チェックリスト形式に変更 |
| 2026-03-29 | 初版作成。フェーズ1〜4の計画を策定 |
