"""watchモジュールのテスト。"""

from __future__ import annotations

import json
import time
from pathlib import Path

from terrasketch.watch.watcher import FileWatcher


def test_file_watcher_detects_change(tmp_path):
    """ファイル変更を検出してコールバックが呼ばれることを確認。"""
    test_file = tmp_path / "state.json"
    test_file.write_text("{}", encoding="utf-8")

    callback_called = []

    def on_change():
        callback_called.append(True)

    watcher = FileWatcher(
        [str(test_file)],
        on_change,
        debounce_sec=0.1,
        poll_interval=0.1,
    )
    watcher.start()

    try:
        # ファイルを変更
        time.sleep(0.2)
        test_file.write_text('{"updated": true}', encoding="utf-8")
        # debounce + poll待ち
        time.sleep(0.5)
    finally:
        watcher.stop()

    assert len(callback_called) >= 1


def test_file_watcher_debounce(tmp_path):
    """debounceにより連続変更がまとめられることを確認。"""
    test_file = tmp_path / "state.json"
    test_file.write_text("{}", encoding="utf-8")

    callback_count = []

    def on_change():
        callback_count.append(True)

    watcher = FileWatcher(
        [str(test_file)],
        on_change,
        debounce_sec=0.3,
        poll_interval=0.05,
    )
    watcher.start()

    try:
        time.sleep(0.1)
        # 短い間隔で連続変更
        for i in range(3):
            test_file.write_text(f'{{"v": {i}}}', encoding="utf-8")
            time.sleep(0.05)
        # debounce待ち
        time.sleep(0.5)
    finally:
        watcher.stop()

    # debounceによりコールバックは1回にまとまる（厳密には環境依存だが1〜2回）
    assert 1 <= len(callback_count) <= 2


def test_file_watcher_directory(tmp_path):
    """ディレクトリ内のファイル変更を検出できることを確認。"""
    tf_file = tmp_path / "main.tf"
    tf_file.write_text('resource "aws_vpc" "main" {}', encoding="utf-8")

    callback_called = []

    def on_change():
        callback_called.append(True)

    watcher = FileWatcher(
        [str(tmp_path)],
        on_change,
        debounce_sec=0.1,
        poll_interval=0.1,
    )
    watcher.start()

    try:
        time.sleep(0.2)
        tf_file.write_text('resource "aws_vpc" "updated" {}', encoding="utf-8")
        time.sleep(0.5)
    finally:
        watcher.stop()

    assert len(callback_called) >= 1


def test_file_watcher_stop(tmp_path):
    """stop()で監視が正常に停止することを確認。"""
    test_file = tmp_path / "state.json"
    test_file.write_text("{}", encoding="utf-8")

    watcher = FileWatcher(
        [str(test_file)],
        lambda: None,
        debounce_sec=0.1,
        poll_interval=0.1,
    )
    watcher.start()
    assert watcher.running is True

    watcher.stop()
    assert watcher.running is False


def test_file_watcher_resolve_files(tmp_path):
    """_resolve_filesがディレクトリ内の.tf/.jsonファイルを検出することを確認。"""
    (tmp_path / "main.tf").write_text("", encoding="utf-8")
    (tmp_path / "vars.tf").write_text("", encoding="utf-8")
    (tmp_path / "state.json").write_text("{}", encoding="utf-8")
    (tmp_path / "readme.md").write_text("", encoding="utf-8")

    watcher = FileWatcher([str(tmp_path)], lambda: None)
    files = watcher._resolve_files()
    names = {f.name for f in files}
    assert "main.tf" in names
    assert "vars.tf" in names
    assert "state.json" in names
    assert "readme.md" not in names
