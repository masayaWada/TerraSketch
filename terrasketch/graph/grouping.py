"""タグベースグルーピングモジュール。

リソースを指定されたタグキーの値に基づいてグループ化し、
構成図上でコンテナとして可視化するための情報を提供する。
"""

from __future__ import annotations

from terrasketch.parser.state_parser import Resource


_UNTAGGED_GROUP = "(untagged)"


def parse_group_by(group_by: str | None) -> tuple[str | None, str | None]:
    """--group-by オプションの値を解析する。

    Args:
        group_by: CLIオプションの値（'module', 'tag:Environment' 等）。

    Returns:
        (group_type, group_key) のタプル。
        - group_type: 'module', 'tag', または None。
        - group_key: タグキー名（'tag:xxx' の場合のみ）。
    """
    if group_by is None:
        return None, None
    if group_by == "module":
        return "module", None
    if group_by.startswith("tag:"):
        tag_key = group_by[4:]
        if tag_key:
            return "tag", tag_key
    return None, None


def group_resources_by_tag(
    resources: list[Resource],
    tag_key: str,
) -> dict[str, list[Resource]]:
    """リソースを指定タグキーの値でグループ化する。

    Args:
        resources: グループ化対象のリソースリスト。
        tag_key: グループ化に使用するタグキー名。

    Returns:
        タグ値からリソースリストへの辞書。タグ未設定のリソースは
        '(untagged)' グループに分類される。
    """
    groups: dict[str, list[Resource]] = {}
    for resource in resources:
        tags = resource.attributes.get("tags", {})
        if not isinstance(tags, dict):
            tags = {}
        # Azure の tags_all もフォールバックで参照
        if not tags:
            tags = resource.attributes.get("tags_all", {})
            if not isinstance(tags, dict):
                tags = {}
        tag_value = tags.get(tag_key, _UNTAGGED_GROUP)
        if not isinstance(tag_value, str):
            tag_value = str(tag_value)
        groups.setdefault(tag_value, []).append(resource)
    return groups


def build_tag_group_map(
    resources: list[Resource],
    tag_key: str,
) -> dict[str, list[str]]:
    """リソースアドレスベースのタググループマップを構築する。

    レンダラーに渡すために、タグ値からリソースアドレスのリストを返す。

    Args:
        resources: グループ化対象のリソースリスト。
        tag_key: グループ化に使用するタグキー名。

    Returns:
        タグ値からリソースアドレスリストへの辞書。
    """
    groups = group_resources_by_tag(resources, tag_key)
    return {
        tag_value: [r.address for r in group_resources]
        for tag_value, group_resources in groups.items()
    }
