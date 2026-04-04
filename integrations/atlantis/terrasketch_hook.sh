#!/usr/bin/env bash
# =============================================================================
# TerraSketch Atlantis フック
# Atlantis カスタムワークフローの post-plan ステップで構成図を自動生成する
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
# Atlantis ワークフローを失敗させないよう、エラー時は警告のみ出力して正常終了する
main() {
    # PLANFILE 環境変数の確認
    if [[ -z "${PLANFILE:-}" ]]; then
        log_warn "PLANFILE 環境変数が未設定です。構成図生成をスキップします。"
        return 0
    fi

    if [[ ! -f "$PLANFILE" ]]; then
        log_warn "プランファイルが見つかりません: $PLANFILE。構成図生成をスキップします。"
        return 0
    fi

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

    # プランファイルを JSON 形式に変換
    log_info "プランファイルを JSON に変換中: $PLANFILE"
    if ! terraform show -json "$PLANFILE" > "$plan_json" 2>/dev/null; then
        log_warn "terraform show -json の実行に失敗しました。構成図生成をスキップします。"
        return 0
    fi

    # JSON ファイルのサイズ確認（空ファイルの場合はスキップ）
    if [[ ! -s "$plan_json" ]]; then
        log_warn "変換後の JSON が空です。構成図生成をスキップします。"
        return 0
    fi

    # TerraSketch でプラン構成図を生成
    log_info "構成図を生成中（形式: ${TERRASKETCH_FORMAT}, プロバイダ: ${TERRASKETCH_PROVIDER}）"
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

    # 生成された構成図をコメントに追加
    if [[ -n "${COMMENT_FILE:-}" ]]; then
        append_diagram_to_comment "$output_dir"
    else
        log_warn "COMMENT_FILE 環境変数が未設定です。PRコメントへの追加をスキップします。"
    fi

    log_info "構成図の生成が完了しました。"
}

# --- 構成図をAtlantis PRコメントに追加 ---
append_diagram_to_comment() {
    local output_dir="$1"

    # Mermaid 形式の場合、テキストをそのままコメントに埋め込む
    if [[ "$TERRASKETCH_FORMAT" == "mermaid" ]]; then
        local mermaid_file
        mermaid_file=$(find "$output_dir" -name "*.mmd" -o -name "*.mermaid" | head -1)
        if [[ -n "$mermaid_file" && -f "$mermaid_file" ]]; then
            {
                echo ""
                echo "---"
                echo ""
                echo "<details><summary>📐 TerraSketch 構成図（クリックで展開）</summary>"
                echo ""
                echo '```mermaid'
                cat "$mermaid_file"
                echo '```'
                echo ""
                echo "</details>"
            } >> "$COMMENT_FILE"
            log_info "Mermaid 構成図を PR コメントに追加しました。"
            return 0
        fi
    fi

    # PlantUML 形式の場合
    if [[ "$TERRASKETCH_FORMAT" == "plantuml" ]]; then
        local puml_file
        puml_file=$(find "$output_dir" -name "*.puml" | head -1)
        if [[ -n "$puml_file" && -f "$puml_file" ]]; then
            {
                echo ""
                echo "---"
                echo ""
                echo "<details><summary>📐 TerraSketch 構成図（クリックで展開）</summary>"
                echo ""
                echo '```plantuml'
                cat "$puml_file"
                echo '```'
                echo ""
                echo "</details>"
            } >> "$COMMENT_FILE"
            log_info "PlantUML 構成図を PR コメントに追加しました。"
            return 0
        fi
    fi

    # その他の形式の場合は生成完了メッセージのみ
    {
        echo ""
        echo "---"
        echo ""
        echo "> 📐 TerraSketch: 構成図が \`${TERRASKETCH_FORMAT}\` 形式で生成されました。"
    } >> "$COMMENT_FILE"
    log_info "構成図生成完了メッセージを PR コメントに追加しました。"
}

# --- 実行 ---
main "$@"
