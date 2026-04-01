"""カスタムテーマモジュールのテスト。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from terrasketch.config.theme import (
    Theme,
    ThemeColors,
    ResourceStyle,
    get_builtin_theme_names,
    get_current_theme,
    load_theme,
    set_theme,
    _parse_yaml,
    _parse_toml,
    _parse_theme_config,
)


def test_builtin_theme_names():
    """組み込みテーマ名のリストが正しいことを確認。"""
    names = get_builtin_theme_names()
    assert "default" in names
    assert "light" in names
    assert "dark" in names


def test_load_builtin_default():
    """デフォルトテーマの読み込みを確認。"""
    theme = load_theme("default")
    assert theme.name == "default"
    assert theme.colors.background == "#ffffff"


def test_load_builtin_dark():
    """ダークテーマの読み込みを確認。"""
    theme = load_theme("dark")
    assert theme.name == "dark"
    assert theme.colors.background == "#263238"
    assert theme.colors.font_color == "#eceff1"


def test_load_builtin_light():
    """ライトテーマの読み込みを確認。"""
    theme = load_theme("light")
    assert theme.name == "light"
    assert theme.colors.node_default_fill == "#f5f5f5"


def test_set_and_get_theme():
    """テーマの設定と取得が正しく動作することを確認。"""
    custom = Theme(name="test", colors=ThemeColors(background="#000000"))
    set_theme(custom)
    current = get_current_theme()
    assert current.name == "test"
    assert current.colors.background == "#000000"
    # デフォルトに戻す
    load_theme("default")


def test_parse_yaml_basic():
    """簡易YAMLパーサーの基本動作を確認。"""
    yaml_text = """
theme:
  background: "#263238"
  font_color: "#eceff1"
resources:
  aws_vpc:
    color: "#e8f5e9"
    icon: "mxgraph.aws4.vpc"
"""
    result = _parse_yaml(yaml_text)
    assert result["theme"]["background"] == "#263238"
    assert result["resources"]["aws_vpc"]["color"] == "#e8f5e9"


def test_parse_toml_basic():
    """簡易TOMLパーサーの基本動作を確認。"""
    toml_text = """
[theme]
background = "#ffffff"
font_color = "#333333"

[resources.aws_vpc]
color = "#e8f5e9"
icon = "mxgraph.aws4.vpc"
"""
    result = _parse_toml(toml_text)
    assert result["theme"]["background"] == "#ffffff"
    assert result["resources"]["aws_vpc"]["color"] == "#e8f5e9"


def test_load_theme_from_yaml_file(tmp_path):
    """YAMLファイルからテーマを読み込めることを確認。"""
    yaml_file = tmp_path / "terrasketch.yaml"
    yaml_file.write_text("""
theme:
  background: "#ff0000"
  edge_contains_color: "#00ff00"
resources:
  aws_vpc:
    color: "#0000ff"
""", encoding="utf-8")

    theme = load_theme(str(yaml_file))
    assert theme.colors.background == "#ff0000"
    assert theme.colors.edge_contains_color == "#00ff00"
    assert "aws_vpc" in theme.resources
    assert theme.resources["aws_vpc"].color == "#0000ff"
    # デフォルトに戻す
    load_theme("default")


def test_load_theme_from_json_file(tmp_path):
    """JSONファイルからテーマを読み込めることを確認。"""
    json_file = tmp_path / "terrasketch.json"
    json_file.write_text(json.dumps({
        "theme": {
            "background": "#123456",
        },
        "resources": {
            "aws_instance": {
                "color": "#abcdef",
            }
        }
    }), encoding="utf-8")

    theme = load_theme(str(json_file))
    assert theme.colors.background == "#123456"
    assert "aws_instance" in theme.resources
    # デフォルトに戻す
    load_theme("default")


def test_load_nonexistent_returns_default():
    """存在しないテーマファイルでデフォルトが返ることを確認。"""
    theme = load_theme("/nonexistent/theme.yaml")
    assert theme.name == "default"


def test_parse_theme_config():
    """_parse_theme_configが正しくThemeを構築することを確認。"""
    raw = {
        "theme": {
            "background": "#aaa",
            "vpc_fill": "#bbb",
        },
        "resources": {
            "aws_vpc": {"color": "#ccc", "icon": "test_icon"},
        },
    }
    theme = _parse_theme_config(raw)
    assert theme.colors.background == "#aaa"
    assert theme.colors.vpc_fill == "#bbb"
    assert theme.resources["aws_vpc"].icon == "test_icon"
