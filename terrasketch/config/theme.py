"""カスタムテーマ / スタイル設定モジュール。

terrasketch.yaml / terrasketch.toml から色・形状・アイコンの
カスタム設定を読み込み、レンダラーに適用する。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("terrasketch")


@dataclass
class ThemeColors:
    """テーマの色設定。"""

    background: str = "#ffffff"
    edge_contains_color: str = "#2e7d32"
    edge_references_color: str = "#1565c0"
    node_default_fill: str = "#dae8fc"
    node_default_stroke: str = "#6c8ebf"
    vpc_fill: str = "#e8f5e9"
    vpc_stroke: str = "#2e7d32"
    subnet_fill: str = "#e3f2fd"
    subnet_stroke: str = "#1565c0"
    font_color: str = "#333333"


@dataclass
class ResourceStyle:
    """個別リソースタイプのスタイルオーバーライド。"""

    color: str = ""
    stroke: str = ""
    icon: str = ""


@dataclass
class Theme:
    """テーマ全体の設定。"""

    name: str = "default"
    colors: ThemeColors = field(default_factory=ThemeColors)
    resources: dict[str, ResourceStyle] = field(default_factory=dict)


# 組み込みテーマ定義
_BUILTIN_THEMES: dict[str, Theme] = {
    "default": Theme(name="default"),
    "light": Theme(
        name="light",
        colors=ThemeColors(
            background="#ffffff",
            node_default_fill="#f5f5f5",
            node_default_stroke="#bdbdbd",
            vpc_fill="#e8f5e9",
            subnet_fill="#e3f2fd",
            font_color="#333333",
        ),
    ),
    "dark": Theme(
        name="dark",
        colors=ThemeColors(
            background="#263238",
            edge_contains_color="#66bb6a",
            edge_references_color="#42a5f5",
            node_default_fill="#37474f",
            node_default_stroke="#78909c",
            vpc_fill="#1b5e20",
            vpc_stroke="#66bb6a",
            subnet_fill="#0d47a1",
            subnet_stroke="#42a5f5",
            font_color="#eceff1",
        ),
    ),
}

# 現在適用中のテーマ（グローバル）
_current_theme: Theme = _BUILTIN_THEMES["default"]


def get_current_theme() -> Theme:
    """現在適用中のテーマを返す。"""
    return _current_theme


def set_theme(theme: Theme) -> None:
    """テーマをグローバルに設定する。"""
    global _current_theme
    _current_theme = theme


def load_theme(name_or_path: str) -> Theme:
    """テーマ名またはファイルパスからテーマを読み込む。

    Args:
        name_or_path: 組み込みテーマ名（'default', 'light', 'dark'）、
                      またはYAML/TOMLファイルのパス。

    Returns:
        読み込んだThemeオブジェクト。
    """
    # 組み込みテーマ
    if name_or_path in _BUILTIN_THEMES:
        theme = _BUILTIN_THEMES[name_or_path]
        set_theme(theme)
        logger.info("組み込みテーマを適用: %s", name_or_path)
        return theme

    # ファイルからの読み込み
    path = Path(name_or_path)
    if not path.exists():
        # カレントディレクトリのterrasketch.yaml/toml/jsonを検索
        for candidate in ["terrasketch.yaml", "terrasketch.yml", "terrasketch.toml", "terrasketch.json"]:
            if Path(candidate).exists():
                path = Path(candidate)
                break
        else:
            logger.warning("テーマファイルが見つかりません: %s — デフォルトを使用", name_or_path)
            return _BUILTIN_THEMES["default"]

    logger.info("テーマファイルを読み込み中: %s", path)
    raw = _load_config_file(path)
    theme = _parse_theme_config(raw)
    set_theme(theme)
    return theme


def _load_config_file(path: Path) -> dict:
    """設定ファイルを読み込む（YAML/TOML/JSON対応）。"""
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()

    if suffix in (".yaml", ".yml"):
        return _parse_yaml(text)
    elif suffix == ".toml":
        return _parse_toml(text)
    elif suffix == ".json":
        return json.loads(text)
    else:
        # 拡張子不明の場合はJSONとして試行
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return _parse_yaml(text)


def _parse_yaml(text: str) -> dict:
    """簡易YAMLパーサー（外部依存なし、フラットなkey: value構造に対応）。"""
    result: dict = {}
    stack: list[tuple[dict, int]] = [(result, -1)]

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # インデントレベルを計算
        indent = len(line) - len(line.lstrip())

        # 現在のスタックをインデントに合わせて調整
        while len(stack) > 1 and stack[-1][1] >= indent:
            stack.pop()

        current_dict = stack[-1][0]

        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()

            if not value:
                # ネストされた辞書の開始
                new_dict: dict = {}
                current_dict[key] = new_dict
                stack.append((new_dict, indent))
            else:
                # 値をクォートから解放
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                current_dict[key] = value

    return result


def _parse_toml(text: str) -> dict:
    """簡易TOMLパーサー（外部依存なし、基本的な[section]とkey=value構造に対応）。"""
    result: dict = {}
    current_section: dict = result

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # セクションヘッダー [section.subsection]
        if stripped.startswith("[") and stripped.endswith("]"):
            section_path = stripped[1:-1].strip()
            current_section = result
            for part in section_path.split("."):
                part = part.strip()
                if part not in current_section:
                    current_section[part] = {}
                current_section = current_section[part]
            continue

        if "=" in stripped:
            key, _, value = stripped.partition("=")
            key = key.strip()
            value = value.strip()

            # 値のクォートを除去
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]

            current_section[key] = value

    return result


def _parse_theme_config(raw: dict) -> Theme:
    """設定辞書からThemeオブジェクトを構築する。"""
    theme_section = raw.get("theme", raw)

    # 色設定
    colors = ThemeColors()
    color_fields = {
        "background", "edge_contains_color", "edge_references_color",
        "node_default_fill", "node_default_stroke", "vpc_fill", "vpc_stroke",
        "subnet_fill", "subnet_stroke", "font_color",
    }
    for key in color_fields:
        value = theme_section.get(key)
        if value:
            setattr(colors, key, value)

    # リソースごとのスタイル
    resources: dict[str, ResourceStyle] = {}
    res_section = raw.get("resources", {})
    for res_type, props in res_section.items():
        if isinstance(props, dict):
            resources[res_type] = ResourceStyle(
                color=props.get("color", ""),
                stroke=props.get("stroke", ""),
                icon=props.get("icon", ""),
            )

    name = theme_section.get("name", raw.get("name", "custom"))
    return Theme(name=name, colors=colors, resources=resources)


def get_builtin_theme_names() -> list[str]:
    """利用可能な組み込みテーマ名のリストを返す。"""
    return list(_BUILTIN_THEMES.keys())
