"""PRコメントにMermaid構成図を投稿するスクリプト。

GitHub REST APIを使用して、PRコメントにTerraSketchで生成した
Mermaid構成図を投稿・更新する。外部依存なし（urllib.requestのみ使用）。

環境変数:
    GITHUB_TOKEN: GitHub APIアクセストークン
    GITHUB_REPOSITORY: リポジトリ名（owner/repo形式）
    GITHUB_EVENT_PATH: GitHubイベントJSONファイルのパス
    OUTPUT_PATH: 生成された構成図ファイルのパス
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# PRコメントの識別用マーカー（既存コメントの更新に使用）
COMMENT_MARKER = "<!-- terrasketch-diagram -->"

# コメント本文の最大文字数（GitHub APIの制限を考慮）
MAX_COMMENT_LENGTH = 60000


def _get_env(name: str) -> str:
    """環境変数を取得する。未設定の場合はエラー終了。

    Args:
        name: 環境変数名。

    Returns:
        環境変数の値。

    Raises:
        SystemExit: 環境変数が未設定の場合。
    """
    value = os.environ.get(name, "")
    if not value:
        print(f"::error::環境変数 {name} が設定されていません", file=sys.stderr)
        sys.exit(1)
    return value


def _get_pr_number() -> int | None:
    """GitHubイベントJSONからPR番号を取得する。

    Returns:
        PR番号。PRイベントでない場合はNone。
    """
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if not event_path or not Path(event_path).exists():
        return None

    with open(event_path, encoding="utf-8") as f:
        event = json.load(f)

    pr_data = event.get("pull_request") or event.get("issue")
    if pr_data and "number" in pr_data:
        return int(pr_data["number"])
    return None


def _github_api(
    method: str,
    url: str,
    token: str,
    data: dict | None = None,
) -> dict:
    """GitHub REST APIにリクエストを送信する。

    Args:
        method: HTTPメソッド（GET, POST, PATCH）。
        url: APIエンドポイントURL。
        token: GitHub APIトークン。
        data: リクエストボディ（JSON）。

    Returns:
        APIレスポンスの辞書。

    Raises:
        urllib.error.HTTPError: APIリクエストが失敗した場合。
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    body = json.dumps(data).encode("utf-8") if data else None
    if body:
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _find_existing_comment(
    repo: str,
    pr_number: int,
    token: str,
) -> int | None:
    """マーカー付きの既存コメントを検索する。

    Args:
        repo: リポジトリ名（owner/repo形式）。
        pr_number: PR番号。
        token: GitHub APIトークン。

    Returns:
        既存コメントのID。見つからない場合はNone。
    """
    page = 1
    while True:
        url = (
            f"https://api.github.com/repos/{repo}"
            f"/issues/{pr_number}/comments?per_page=100&page={page}"
        )
        try:
            comments = _github_api("GET", url, token)
        except urllib.error.HTTPError:
            return None

        if not comments:
            break

        for comment in comments:
            body = comment.get("body", "")
            if COMMENT_MARKER in body:
                return int(comment["id"])

        page += 1

    return None


def _build_comment_body(diagram_content: str) -> str:
    """PRコメント本文を構築する。

    大きな構成図の場合は切り詰めメッセージを付与する。

    Args:
        diagram_content: Mermaid構成図の内容。

    Returns:
        コメント本文。
    """
    header = f"""{COMMENT_MARKER}
## TerraSketch インフラ構成図

> Terraform stateから自動生成された構成図です。

"""

    footer = """

---
<sub>TerraSketch GitHub Action により自動生成</sub>
"""

    # ダイアグラム本文を構築
    diagram_block = f"```mermaid\n{diagram_content}\n```"
    full_body = header + diagram_block + footer

    # 最大文字数を超える場合は切り詰め
    if len(full_body) > MAX_COMMENT_LENGTH:
        truncate_msg = (
            "\n\n> **注意**: 構成図が大きすぎるため切り詰められました。"
            "完全な構成図はアーティファクトを参照してください。\n"
        )
        # 切り詰め後のダイアグラム最大長を計算
        max_diagram_len = (
            MAX_COMMENT_LENGTH
            - len(header)
            - len(footer)
            - len(truncate_msg)
            - len("```mermaid\n\n```")
        )
        truncated_content = diagram_content[:max_diagram_len]
        diagram_block = f"```mermaid\n{truncated_content}\n```"
        full_body = header + diagram_block + truncate_msg + footer

    return full_body


def main() -> None:
    """メインエントリーポイント。PRコメントを投稿または更新する。"""
    token = _get_env("GITHUB_TOKEN")
    repo = _get_env("GITHUB_REPOSITORY")
    output_path = _get_env("OUTPUT_PATH")

    # PR番号を取得
    pr_number = _get_pr_number()
    if pr_number is None:
        print("::warning::PRイベントではないためコメント投稿をスキップします")
        return

    # 構成図ファイルを読み込み
    output_file = Path(output_path)
    if not output_file.exists():
        print(f"::error::構成図ファイルが見つかりません: {output_path}", file=sys.stderr)
        sys.exit(1)

    diagram_content = output_file.read_text(encoding="utf-8")
    if not diagram_content.strip():
        print("::warning::構成図ファイルが空です。コメント投稿をスキップします")
        return

    # コメント本文を構築
    comment_body = _build_comment_body(diagram_content)

    # 既存コメントの検索
    existing_id = _find_existing_comment(repo, pr_number, token)

    try:
        if existing_id:
            # 既存コメントを更新
            url = f"https://api.github.com/repos/{repo}/issues/comments/{existing_id}"
            _github_api("PATCH", url, token, {"body": comment_body})
            print(f"::notice::既存のPRコメントを更新しました（コメントID: {existing_id}）")
        else:
            # 新規コメントを作成
            url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
            result = _github_api("POST", url, token, {"body": comment_body})
            print(f"::notice::PRコメントを投稿しました（コメントID: {result.get('id')}）")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if hasattr(e, "read") else ""
        print(
            f"::error::PRコメントの投稿に失敗しました: {e.code} {e.reason}\n{error_body}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
