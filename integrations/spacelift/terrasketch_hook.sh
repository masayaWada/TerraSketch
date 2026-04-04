#!/usr/bin/env bash
# =============================================================================
# TerraSketch Spacelift フック
# Spacelift の after_plan フェーズで構成図を自動生成する
# =============================================================================

set -euo pipefail

# --- 設定 ---
# 出力形式（mermaid / drawio / plantuml / svg / html）
TERRASKETCH_FORMAT="${TERRASKETCH_FORMAT:-mermaid}"
# プロバイダ（aws / azure / gcp / kubernetes / all）
TERRASKETCH_PROVIDER="${TERRASKETCH_PROVIDER:-all}"
# 追加オプション（例: --labels --security --summary）
TERRASKETCH_EXTRA_OPTS="${TERRASKETCH_EXTRA_OPTS:-}"

# --- ログ用ヘルパー ---
log_info() {
    echo "[TerraSketch] INFO: $*" >&2
}

log_warn() {
    echo "[TerraSketch] WARN: $*" >&2
}

log_error() {
    echo "[TerraSketch] ERROR: $*" >&2
}

# --- メイン処理 ---
# Spacelift ワークフローを失敗させないよう、エラー時は警告のみ出力して正常終了する
main() {
    # Spacelift 環境の確認
    local workspace_root="${SPACELIFT_WORKSPACE_ROOT:-$(pwd)}"
    log_info "ワークスペースルート: $workspace_root"

    # terrasketch コマンドの存在確認
    if ! command -v terrasketch &>/dev/null; then
        log_warn "terrasketch コマンドが見つかりません。pip install terrasketch でインストールしてください。"
        return 0
    fi

    # terraform コマンドの存在確認
    if ! command -v terraform &>/dev/null; then
        log_warn "terraform コマンドが見つかりません。構成図生成をスキップします。"
        return 0
    fi

    # 一時ディレクトリの作成
    local tmp_dir
    tmp_dir=$(mktemp -d)
    trap 'rm -rf "$tmp_dir"' EXIT

    local plan_json="${tmp_dir}/plan.json"
    local output_dir="${tmp_dir}/output"
    mkdir -p "$output_dir"

    # Spacelift のプランファイルを探す
    # Spacelift はプランを自動実行するため、state から構成図を生成する方法も利用可能
    local plan_file=""

    # Spacelift がプランファイルのパスを提供する場合
    if [[ -n "${SPACELIFT_PLAN_FILE:-}" && -f "${SPACELIFT_PLAN_FILE}" ]]; then
        plan_file="$SPACELIFT_PLAN_FILE"
    # デフォルトのプランファイルパスを確認
    elif [[ -f "${workspace_root}/spacelift.plan" ]]; then
        plan_file="${workspace_root}/spacelift.plan"
    elif [[ -f "${workspace_root}/plan.out" ]]; then
        plan_file="${workspace_root}/plan.out"
    fi

    if [[ -z "$plan_file" ]]; then
        # プランファイルが見つからない場合、state ファイルからの生成を試みる
        log_info "プランファイルが見つかりません。terraform show で現在の state から生成を試みます。"

        if ! terraform show -json > "$plan_json" 2>/dev/null; then
            log_warn "terraform show -json の実行に失敗しました。構成図生成をスキップします。"
            return 0
        fi

        if [[ ! -s "$plan_json" ]]; then
            log_warn "terraform show の出力が空です。構成図生成をスキップします。"
            return 0
        fi

        # state ベースの構成図を生成
        log_info "state ベースの構成図を生成中（形式: ${TERRASKETCH_FORMAT}, プロバイダ: ${TERRASKETCH_PROVIDER}）"
        # shellcheck disable=SC2086
        if ! terrasketch generate \
            --state "$plan_json" \
            --provider "$TERRASKETCH_PROVIDER" \
            --format "$TERRASKETCH_FORMAT" \
            --output "$output_dir" \
            $TERRASKETCH_EXTRA_OPTS 2>/dev/null; then
            log_warn "terrasketch generate の実行に失敗しました。構成図生成をスキップします。"
            return 0
        fi
    else
        # プランファイルを JSON に変換
        log_info "プランファイルを JSON に変換中: $plan_file"
        if ! terraform show -json "$plan_file" > "$plan_json" 2>/dev/null; then
            log_warn "terraform show -json の実行に失敗しました。構成図生成をスキップします。"
            return 0
        fi

        if [[ ! -s "$plan_json" ]]; then
            log_warn "変換後の JSON が空です。構成図生成をスキップします。"
            return 0
        fi

        # プラン構成図を生成
        log_info "プラン構成図を生成中（形式: ${TERRASKETCH_FORMAT}, プロバイダ: ${TERRASKETCH_PROVIDER}）"
        # shellcheck disable=SC2086
        if ! terrasketch plan \
            --plan "$plan_json" \
            --provider "$TERRASKETCH_PROVIDER" \
            --format "$TERRASKETCH_FORMAT" \
            --output "$output_dir" \
            $TERRASKETCH_EXTRA_OPTS 2>/dev/null; then
            log_warn "terrasketch plan の実行に失敗しました。構成図生成をスキップします。"
            return 0
        fi
    fi

    # 生成された構成図を標準出力に表示（Spacelift のログに記録される）
    output_diagram "$output_dir"

    log_info "構成図の生成が完了しました。"
}

# --- 構成図を出力 ---
output_diagram() {
    local output_dir="$1"

    # Mermaid 形式の場合
    if [[ "$TERRASKETCH_FORMAT" == "mermaid" ]]; then
        local mermaid_file
        mermaid_file=$(find "$output_dir" -name "*.mmd" -o -name "*.mermaid" | head -1)
        if [[ -n "$mermaid_file" && -f "$mermaid_file" ]]; then
            echo ""
            echo "========== TerraSketch 構成図 (Mermaid) =========="
            cat "$mermaid_file"
            echo "=================================================="
            echo ""
            return 0
        fi
    fi

    # PlantUML 形式の場合
    if [[ "$TERRASKETCH_FORMAT" == "plantuml" ]]; then
        local puml_file
        puml_file=$(find "$output_dir" -name "*.puml" | head -1)
        if [[ -n "$puml_file" && -f "$puml_file" ]]; then
            echo ""
            echo "========== TerraSketch 構成図 (PlantUML) =========="
            cat "$puml_file"
            echo "==================================================="
            echo ""
            return 0
        fi
    fi

    # 生成完了メッセージ
    log_info "構成図が ${TERRASKETCH_FORMAT} 形式で生成されました: $output_dir"
}

# --- 実行 ---
main "$@"
