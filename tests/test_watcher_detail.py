"""watcherモジュールの詳細テスト。"""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from terrasketch.watch.watcher import FileWatcher, watch_and_generate


def test_check_changes_file_deleted(tmp_path):
    """ファイル削除を検出できることを確認。"""
    f = tmp_path / "state.json"
    f.write_text("{}", encoding="utf-8")

    watcher = FileWatcher([str(f)], lambda: None, debounce_sec=0.1, poll_interval=0.1)

    # ファイルを削除
    f.unlink()
    changed = watcher._check_changes()
    assert len(changed) >= 1


def test_check_changes_new_file_in_dir(tmp_path):
    """ディレクトリ内に新しいファイルが追加された場合を確認。"""
    (tmp_path / "main.tf").write_text("", encoding="utf-8")
    watcher = FileWatcher([str(tmp_path)], lambda: None, debounce_sec=0.1, poll_interval=0.1)

    # 新しいファイルを追��
    (tmp_path / "new.tf").write_text('resource "aws_vpc" "new" {}', encoding="utf-8")
    # _resolve_filesを再実行して新ファイルを検出
    changed = watcher._check_changes()
    # 新ファイルはmtimeが0.0として追加され、実際のmtimeと異なるので変更として検出
    assert len(changed) >= 1


def test_callback_error_handling(tmp_path):
    """コールバック内のエラーがウォッチャーをクラッシュさせないことを確認。"""
    f = tmp_path / "state.json"
    f.write_text("{}", encoding="utf-8")

    error_count = []

    def bad_callback():
        error_count.append(1)
        raise RuntimeError("テストエラー")

    watcher = FileWatcher([str(f)], bad_callback, debounce_sec=0.1, poll_interval=0.1)
    watcher.start()

    try:
        time.sleep(0.2)
        f.write_text('{"updated": true}', encoding="utf-8")
        time.sleep(0.5)
    finally:
        watcher.stop()

    # エラーが発生してもウォッチャーは停止しない
    assert watcher.running is False  # stop()で停止済み
    assert len(error_count) >= 1


def test_start_idempotent(tmp_path):
    """start()の重複呼び出しが安全であることを確認。"""
    f = tmp_path / "state.json"
    f.write_text("{}", encoding="utf-8")
    watcher = FileWatcher([str(f)], lambda: None)
    watcher.start()
    watcher.start()  # 2回目は無視される
    assert watcher.running is True
    watcher.stop()


def test_watch_and_generate_no_paths():
    """watch_and_generateがパスなしでValueErrorを送出することを確認。"""
    with pytest.raises(ValueError, match="--state"):
        watch_and_generate(
            state_path=None,
            hcl_path=None,
            provider="aws",
            output_dir=".",
        )


def test_resolve_files_nonexistent_file(tmp_path):
    """存在しないファイルパスが無視されることを確認。"""
    watcher = FileWatcher([str(tmp_path / "nonexistent.json")], lambda: None)
    files = watcher._resolve_files()
    assert len(files) == 0
