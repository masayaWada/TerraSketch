"""Terraform HCLファイル（.tf）からリソース定義を抽出する軽量パーサー。

外部依存ライブラリなしで、Terraformの `resource` ブロックを解析し、
リソースタイプ・名前・属性を抽出する。

制限事項:
- 変数展開（var.xxx, local.xxx）は文字列としてそのまま保持
- 複雑なHCL式（条件式、for式等）は未対応
- ネストされたブロック（dynamic等）は辞書として簡易的に抽出
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from terrasketch.parser.state_parser import Resource


def parse_hcl(file_path: str | Path) -> list[Resource]:
    """単一の.tfファイルからresourceブロックを解析しResourceリストを返す。

    Args:
        file_path: Terraform .tfファイルのパス。

    Returns:
        抽出されたResourceオブジェクトのリスト。

    Raises:
        FileNotFoundError: ファイルが存在しない場合。
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"HCL file not found: {path}")

    content = path.read_text(encoding="utf-8")
    return _extract_resources(content)


def parse_hcl_directory(dir_path: str | Path) -> list[Resource]:
    """ディレクトリ内の全.tfファイルからresourceブロックを解析する。

    Args:
        dir_path: .tfファイルを含むディレクトリのパス。

    Returns:
        全ファイルから抽出されたResourceオブジェクトのリスト。

    Raises:
        FileNotFoundError: ディレクトリが存在しない場合。
    """
    directory = Path(dir_path)
    if not directory.is_dir():
        raise FileNotFoundError(f"Directory not found: {directory}")

    resources: list[Resource] = []
    for tf_file in sorted(directory.glob("*.tf")):
        resources.extend(parse_hcl(tf_file))
    return resources


def _extract_resources(content: str) -> list[Resource]:
    """HCLテキストからresourceブロックを抽出する。"""
    resources: list[Resource] = []

    # コメントを除去
    content = _strip_comments(content)

    # resource "type" "name" { ... } パターンを検索
    pattern = re.compile(
        r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{', re.MULTILINE
    )

    for match in pattern.finditer(content):
        resource_type = match.group(1)
        resource_name = match.group(2)
        block_start = match.end() - 1  # '{' の位置

        # 対応する閉じ括弧を見つける
        block_content = _extract_block(content, block_start)
        if block_content is None:
            continue

        # ブロック内の属性を解析
        attributes = _parse_attributes(block_content)

        # プロバイダを推定
        provider = _detect_provider(resource_type)

        resource = Resource(
            id=attributes.get("id", ""),
            type=resource_type,
            name=resource_name,
            provider=provider,
            attributes=attributes,
        )
        resources.append(resource)

    return resources


def _strip_comments(content: str) -> str:
    """HCLのコメント（# / // / /* */）を除去する。"""
    # ブロックコメント
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    # 行コメント（文字列リテラル内は除外しない簡易版）
    content = re.sub(r'(#|//).*$', '', content, flags=re.MULTILINE)
    return content


def _extract_block(content: str, start: int) -> str | None:
    """開き括弧の位置から対応する閉じ括弧までの内容を抽出する。"""
    if start >= len(content) or content[start] != '{':
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i in range(start, len(content)):
        ch = content[i]

        if escape_next:
            escape_next = False
            continue
        if ch == '\\':
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue

        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return content[start + 1:i]

    return None


def _parse_attributes(block: str) -> dict[str, Any]:
    """ブロック内容からキー=値ペアを抽出する。"""
    attrs: dict[str, Any] = {}

    # 単純な key = value パターン
    # 文字列値
    for match in re.finditer(
        r'(\w+)\s*=\s*"([^"]*)"', block
    ):
        attrs[match.group(1)] = match.group(2)

    # 数値
    for match in re.finditer(
        r'(\w+)\s*=\s*(\d+(?:\.\d+)?)\s', block
    ):
        key = match.group(1)
        if key not in attrs:
            value = match.group(2)
            attrs[key] = float(value) if '.' in value else int(value)

    # ブール値
    for match in re.finditer(
        r'(\w+)\s*=\s*(true|false)\s', block
    ):
        key = match.group(1)
        if key not in attrs:
            attrs[key] = match.group(2) == "true"

    # リスト値（簡易: ["a", "b"] 形式）
    for match in re.finditer(
        r'(\w+)\s*=\s*\[([^\]]*)\]', block
    ):
        key = match.group(1)
        if key not in attrs:
            items = re.findall(r'"([^"]*)"', match.group(2))
            attrs[key] = items

    # tags = { ... } ブロック
    for match in re.finditer(
        r'tags\s*=\s*\{([^}]*)\}', block
    ):
        tag_content = match.group(1)
        tags: dict[str, str] = {}
        for tag_match in re.finditer(
            r'(\w+)\s*=\s*"([^"]*)"', tag_content
        ):
            tags[tag_match.group(1)] = tag_match.group(2)
        if tags:
            attrs["tags"] = tags

    return attrs


def _detect_provider(resource_type: str) -> str:
    """リソースタイプからプロバイダ名を推定する。"""
    if resource_type.startswith("aws_"):
        return "registry.terraform.io/hashicorp/aws"
    if resource_type.startswith("azurerm_"):
        return "registry.terraform.io/hashicorp/azurerm"
    if resource_type.startswith("google_"):
        return "registry.terraform.io/hashicorp/google"
    return "unknown"
