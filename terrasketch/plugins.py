"""プラグインシステム。

Pythonエントリーポイントを使って外部プラグインを発見・ロードする。
`terrasketch.renderers` / `terrasketch.mappings` グループで
レンダラー・マッピングを拡張可能。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("terrasketch")

# プラグインレジストリ
_renderer_plugins: dict[str, Any] = {}
_mapping_plugins: dict[str, Any] = {}


def discover_plugins() -> None:
    """エントリーポイントからプラグインを発見してレジストリに登録する。"""
    _discover_group("terrasketch.renderers", _renderer_plugins)
    _discover_group("terrasketch.mappings", _mapping_plugins)


def _discover_group(group: str, registry: dict[str, Any]) -> None:
    """指定グループのエントリーポイントを読み込む。"""
    try:
        # Python 3.10+: importlib.metadata
        from importlib.metadata import entry_points

        eps = entry_points()
        # Python 3.12+ は group パラメータ直接指定可能
        # 互換性のため辞書/リスト両方に対応
        if hasattr(eps, "select"):
            group_eps = eps.select(group=group)
        elif isinstance(eps, dict):
            group_eps = eps.get(group, [])
        else:
            group_eps = []

        for ep in group_eps:
            try:
                plugin = ep.load()
                registry[ep.name] = plugin
                logger.info("プラグインをロード: [%s] %s", group, ep.name)
            except Exception as e:
                logger.warning("プラグインのロードに失敗: [%s] %s — %s", group, ep.name, e)

    except ImportError:
        logger.debug("importlib.metadata が利用できません。プラグイン検出をスキップ。")


def get_renderer_plugins() -> dict[str, Any]:
    """登録済みレンダラープラグインを返す。"""
    return dict(_renderer_plugins)


def get_mapping_plugins() -> dict[str, Any]:
    """登録済みマッピングプラグインを返す。"""
    return dict(_mapping_plugins)


def get_renderer(name: str) -> Any | None:
    """名前でレンダラープラグインを取得する。

    Args:
        name: レンダラー名（エントリーポイント名）。

    Returns:
        レンダラークラス。見つからない場合はNone。
    """
    return _renderer_plugins.get(name)


def get_mapping(name: str) -> Any | None:
    """名前でマッピングプラグインを取得する。

    Args:
        name: マッピング名（エントリーポイント名）。

    Returns:
        マッピングモジュールまたはオブジェクト。見つからない場合はNone。
    """
    return _mapping_plugins.get(name)


def register_renderer(name: str, renderer_class: Any) -> None:
    """レンダラープラグインを手動登録する。

    Args:
        name: レンダラー名。
        renderer_class: レンダラークラス。
    """
    _renderer_plugins[name] = renderer_class
    logger.info("レンダラーを手動登録: %s", name)


def register_mapping(name: str, mapping: Any) -> None:
    """マッピングプラグインを手動登録する。

    Args:
        name: マッピング名。
        mapping: マッピングモジュールまたはオブジェクト。
    """
    _mapping_plugins[name] = mapping
    logger.info("マッピングを手動登録: %s", name)
