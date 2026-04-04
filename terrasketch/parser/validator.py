"""入力ファイルの事前検証モジュール。

State JSON / HCL ファイルの形式チェックを行い、
ユーザーフレンドリーなエラーメッセージと対処ヒントを提供する。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ValidationResult:
    """検証結果を格納するデータクラス。"""

    valid: bool
    errors: list[str]
    hints: list[str]


def validate_state_file(file_path: str | Path) -> ValidationResult:
    """Terraform state JSONファイルを検証する。

    Args:
        file_path: 検証対象のファイルパス。

    Returns:
        検証結果。
    """
    path = Path(file_path)
    errors: list[str] = []
    hints: list[str] = []

    # ファイル存在チェック
    if not path.exists():
        errors.append(f"ファイルが見つかりません: {path}")
        hints.append("ファイルパスが正しいか確認してください。")
        return ValidationResult(valid=False, errors=errors, hints=hints)

    if not path.is_file():
        errors.append(f"ディレクトリが指定されました: {path}")
        hints.append("state JSONファイルのパスを指定してください。HCLディレクトリの場合は --hcl オプションを使用してください。")
        return ValidationResult(valid=False, errors=errors, hints=hints)

    # 拡張子チェック
    if path.suffix not in (".json", ".tfstate"):
        errors.append(f"予期しないファイル拡張子です: {path.suffix}")
        hints.append(
            "Terraform state JSONファイルは .json または .tfstate 拡張子を持ちます。"
            " `terraform show -json > state.json` で生成してください。"
        )

    # JSON解析チェック
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        errors.append("ファイルがUTF-8テキストとして読み込めません。")
        hints.append("バイナリファイルが指定されていないか確認してください。")
        return ValidationResult(valid=False, errors=errors, hints=hints)

    if not content.strip():
        errors.append("ファイルが空です。")
        hints.append("`terraform show -json` でstate JSONを生成してください。")
        return ValidationResult(valid=False, errors=errors, hints=hints)

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        errors.append(f"JSONの構文エラーです（行 {e.lineno}, 列 {e.colno}）: {e.msg}")
        hints.append("ファイルが有効なJSON形式か確認してください。")
        return ValidationResult(valid=False, errors=errors, hints=hints)

    if not isinstance(data, dict):
        errors.append("JSONのルート要素がオブジェクトではありません。")
        hints.append("`terraform show -json` の出力形式を確認してください。")
        return ValidationResult(valid=False, errors=errors, hints=hints)

    # Terraform / OpenTofu state構造チェック
    is_opentofu = "opentofu_version" in data
    runtime_name = "OpenTofu" if is_opentofu else "Terraform"
    show_cmd = "tofu show -json" if is_opentofu else "terraform show -json"

    if "values" not in data:
        errors.append("必須キー 'values' が見つかりません。")
        if "resource_changes" in data:
            hints.append(
                f"これは {runtime_name} plan の出力です。state JSONを使用するには "
                f"`{show_cmd}` を実行してください。"
            )
        elif "terraform_version" in data or "opentofu_version" in data:
            hints.append(
                f"{runtime_name} state形式ですが 'values' キーがありません。"
                f" `{show_cmd}` で再出力してください。"
            )
        else:
            hints.append(
                "Terraform / OpenTofu state JSON形式ではないようです。"
                " `terraform show -json > state.json` または"
                " `tofu show -json > state.json` で生成してください。"
            )

    values = data.get("values", {})
    if isinstance(values, dict) and "root_module" not in values:
        errors.append("必須キー 'values.root_module' が見つかりません。")
        hints.append("state JSONが不完全な可能性があります。`terraform show -json` で再生成してください。")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        hints=hints,
    )


def validate_hcl_file(file_path: str | Path) -> ValidationResult:
    """Terraform HCLファイルまたはディレクトリを検証する。

    Args:
        file_path: 検証対象のファイルまたはディレクトリのパス。

    Returns:
        検証結果。
    """
    path = Path(file_path)
    errors: list[str] = []
    hints: list[str] = []

    if not path.exists():
        errors.append(f"ファイルが見つかりません: {path}")
        hints.append("パスが正しいか確認してください。")
        return ValidationResult(valid=False, errors=errors, hints=hints)

    if path.is_dir():
        tf_files = list(path.glob("*.tf"))
        if not tf_files:
            errors.append(f"ディレクトリ内に .tf ファイルが見つかりません: {path}")
            hints.append("Terraform構成ファイルを含むディレクトリを指定してください。")
    elif path.is_file():
        if path.suffix != ".tf":
            errors.append(f"予期しないファイル拡張子です: {path.suffix}")
            hints.append("Terraform HCLファイルは .tf 拡張子を持ちます。state JSONファイルの場合は --state オプションを使用してください。")
        else:
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                errors.append("ファイルがUTF-8テキストとして読み込めません。")
                return ValidationResult(valid=False, errors=errors, hints=hints)

            if not content.strip():
                errors.append("ファイルが空です。")
                hints.append("Terraformリソース定義を含む .tf ファイルを指定してください。")
            elif "resource" not in content and "data" not in content:
                errors.append("resource ブロックが見つかりません。")
                hints.append("ファイルに `resource` ブロックが定義されているか確認してください。")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        hints=hints,
    )


def validate_plan_file(file_path: str | Path) -> ValidationResult:
    """Terraform plan JSONファイルを検証する。

    Args:
        file_path: 検証対象のファイルパス。

    Returns:
        検証結果。
    """
    path = Path(file_path)
    errors: list[str] = []
    hints: list[str] = []

    if not path.exists():
        errors.append(f"ファイルが見つかりません: {path}")
        hints.append("ファイルパスが正しいか確認してください。")
        return ValidationResult(valid=False, errors=errors, hints=hints)

    if not path.is_file():
        errors.append(f"ディレクトリが指定されました: {path}")
        hints.append("plan JSONファイルのパスを指定してください。")
        return ValidationResult(valid=False, errors=errors, hints=hints)

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        errors.append("ファイルがUTF-8テキストとして読み込めません。")
        return ValidationResult(valid=False, errors=errors, hints=hints)

    if not content.strip():
        errors.append("ファイルが空です。")
        hints.append("`terraform show -json <planfile>` でplan JSONを生成してください。")
        return ValidationResult(valid=False, errors=errors, hints=hints)

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        errors.append(f"JSONの構文エラーです（行 {e.lineno}, 列 {e.colno}）: {e.msg}")
        return ValidationResult(valid=False, errors=errors, hints=hints)

    if not isinstance(data, dict):
        errors.append("JSONのルート要素がオブジェクトではありません。")
        return ValidationResult(valid=False, errors=errors, hints=hints)

    # plan JSON構造チェック（Terraform / OpenTofu 共通）
    is_opentofu = "opentofu_version" in data
    show_cmd = "tofu show -json <planfile>" if is_opentofu else "terraform show -json <planfile>"

    if "planned_values" not in data:
        errors.append("必須キー 'planned_values' が見つかりません。")
        if "values" in data and "root_module" in data.get("values", {}):
            hints.append(
                "これは state の出力です。plan JSONを使用するには "
                f"`{show_cmd}` を実行してください。"
            )
        else:
            hints.append(
                "Terraform / OpenTofu plan JSON形式ではないようです。"
                " `terraform show -json <planfile>` または"
                " `tofu show -json <planfile>` で生成してください。"
            )

    if "resource_changes" not in data:
        errors.append("必須キー 'resource_changes' が見つかりません。")
        hints.append("plan JSONが不完全な可能性があります。")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        hints=hints,
    )


def format_validation_result(result: ValidationResult) -> str:
    """検証結果をユーザー向けメッセージに整形する。

    Args:
        result: 検証結果。

    Returns:
        整形されたメッセージ文字列。
    """
    if result.valid:
        return "検証OK: 入力ファイルは有効です。"

    lines: list[str] = []
    lines.append("検証エラー:")
    for error in result.errors:
        lines.append(f"  ✗ {error}")

    if result.hints:
        lines.append("")
        lines.append("ヒント:")
        for hint in result.hints:
            lines.append(f"  → {hint}")

    return "\n".join(lines)
