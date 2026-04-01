"""プラグインシステムのテスト。"""

from __future__ import annotations

from terrasketch.plugins import (
    discover_plugins,
    get_renderer,
    get_mapping,
    get_renderer_plugins,
    get_mapping_plugins,
    register_renderer,
    register_mapping,
    _renderer_plugins,
    _mapping_plugins,
)


def setup_function():
    """テスト前にレジストリをクリアする。"""
    _renderer_plugins.clear()
    _mapping_plugins.clear()


def test_discover_plugins_no_error():
    """discover_pluginsがエラーなく実行されることを確認。"""
    discover_plugins()
    # 外部プラグインがなくてもエラーにならない


def test_register_renderer():
    """レンダラーの手動登録と取得を確認。"""

    class MockRenderer:
        pass

    register_renderer("mock", MockRenderer)
    assert get_renderer("mock") is MockRenderer


def test_register_mapping():
    """マッピングの手動登録と取得を確認。"""
    mock_mapping = {"aws_test": "test_style"}
    register_mapping("mock_map", mock_mapping)
    assert get_mapping("mock_map") is mock_mapping


def test_get_renderer_not_found():
    """未登録のレンダラーはNoneが返ることを確認。"""
    assert get_renderer("nonexistent") is None


def test_get_mapping_not_found():
    """未登録のマッピングはNoneが返ることを確認。"""
    assert get_mapping("nonexistent") is None


def test_get_renderer_plugins_returns_copy():
    """get_renderer_pluginsがコピーを返すことを確認。"""

    class FakeRenderer:
        pass

    register_renderer("fake", FakeRenderer)
    plugins = get_renderer_plugins()
    assert "fake" in plugins
    # 返却値を変更してもレジストリに影響しない
    plugins["fake"] = None
    assert get_renderer("fake") is FakeRenderer


def test_get_mapping_plugins_returns_copy():
    """get_mapping_pluginsがコピーを返すことを確認。"""
    register_mapping("test", {"key": "value"})
    plugins = get_mapping_plugins()
    assert "test" in plugins
    plugins.clear()
    assert get_mapping("test") is not None
