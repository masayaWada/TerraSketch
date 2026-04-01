"""ファイル変更監視モジュール（外部依存なし）。

State JSON / HCL ファイルの変更を検出し、構成図を自動再生成する。
polling方式（os.stat mtime）で実装し、debounce（500ms）で連続変更をまとめる。
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path

logger = logging.getLogger("terrasketch")


class FileWatcher:
    """ファイル変更を監視し、コールバックを呼び出すポーリングベースのウォッチャー。

    Args:
        paths: 監視対象のファイルパスリスト。
        callback: 変更検出時に呼び出すコールバック関数。
        debounce_sec: 最後の変更からコールバック発火までの待ち時間（秒）。
        poll_interval: ポーリング間隔（秒）。
    """

    def __init__(
        self,
        paths: list[str | Path],
        callback: callable,
        debounce_sec: float = 0.5,
        poll_interval: float = 1.0,
    ) -> None:
        self._paths = [Path(p) for p in paths]
        self._callback = callback
        self._debounce_sec = debounce_sec
        self._poll_interval = poll_interval
        self._running = False
        self._thread: threading.Thread | None = None
        self._mtimes: dict[str, float] = {}
        self._init_mtimes()

    def _init_mtimes(self) -> None:
        """監視対象ファイルの初期mtimeを記録する。"""
        for p in self._resolve_files():
            try:
                self._mtimes[str(p)] = os.stat(str(p)).st_mtime
            except OSError:
                self._mtimes[str(p)] = 0.0

    def _resolve_files(self) -> list[Path]:
        """パスリストからファイル一覧を解決する（ディレクトリは*.tf/*.jsonを展開）。"""
        files: list[Path] = []
        for p in self._paths:
            if p.is_dir():
                files.extend(p.glob("*.tf"))
                files.extend(p.glob("*.json"))
            elif p.exists():
                files.append(p)
        return files

    def _check_changes(self) -> list[str]:
        """mtimeの変更を検出し、変更されたファイルパスのリストを返す。"""
        changed: list[str] = []
        current_files = self._resolve_files()

        # 新しいファイルの追加を検出
        current_paths = {str(f) for f in current_files}
        for fp in current_paths:
            if fp not in self._mtimes:
                self._mtimes[fp] = 0.0

        for fp in list(self._mtimes.keys()):
            try:
                new_mtime = os.stat(fp).st_mtime
            except OSError:
                # ファイルが削除された場合
                if fp in current_paths:
                    continue
                del self._mtimes[fp]
                changed.append(fp)
                continue

            if new_mtime != self._mtimes[fp]:
                self._mtimes[fp] = new_mtime
                changed.append(fp)

        return changed

    def _poll_loop(self) -> None:
        """ポーリングループ。変更検出→debounce→コールバック。"""
        last_change_time: float | None = None

        while self._running:
            changed = self._check_changes()

            if changed:
                for fp in changed:
                    logger.info("変更を検出: %s", fp)
                last_change_time = time.monotonic()

            if last_change_time is not None:
                elapsed = time.monotonic() - last_change_time
                if elapsed >= self._debounce_sec:
                    logger.info("debounce完了 — 構成図を再生成します...")
                    try:
                        self._callback()
                    except Exception as e:
                        logger.error("再生成中にエラー: %s", e)
                    last_change_time = None

            time.sleep(self._poll_interval)

    def start(self) -> None:
        """監視を開始する（バックグラウンドスレッド）。"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info("ファイル監視を開始しました。Ctrl+Cで終了。")

    def stop(self) -> None:
        """監視を停止する。"""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        logger.info("ファイル監視を停止しました。")

    @property
    def running(self) -> bool:
        """監視中かどうかを返す。"""
        return self._running


def watch_and_generate(
    state_path: str | None,
    hcl_path: str | None,
    provider: str,
    output_dir: str,
    output_format: str = "drawio",
    show_labels: bool = False,
    layout_type: str = "hierarchical",
    group_by: str | None = None,
) -> None:
    """ファイル変更を監視し、変更時に自動で構成図を再生成する。

    Args:
        state_path: Terraform state JSONファイルのパス。
        hcl_path: HCLファイルまたはディレクトリのパス。
        provider: クラウドプロバイダフィルタ。
        output_dir: 出力ディレクトリ。
        output_format: 出力形式。
        show_labels: エッジラベル表示。
        layout_type: レイアウトアルゴリズム。
        group_by: グルーピング方法。
    """
    from terrasketch.main import generate

    # 監視対象パスを決定
    watch_paths: list[str] = []
    if state_path:
        watch_paths.append(state_path)
    if hcl_path:
        watch_paths.append(hcl_path)

    if not watch_paths:
        raise ValueError("--state または --hcl のいずれかを指定してください。")

    def regenerate() -> None:
        """構成図を再生成するコールバック。"""
        generate(
            state_path=state_path,
            provider=provider,
            output_dir=output_dir,
            output_format=output_format,
            hcl_path=hcl_path,
            show_labels=show_labels,
            layout_type=layout_type,
            group_by=group_by,
        )

    # 初回生成
    logger.info("初回生成を実行します...")
    regenerate()

    # 監視開始
    watcher = FileWatcher(watch_paths, regenerate, debounce_sec=0.5, poll_interval=1.0)
    watcher.start()

    try:
        while watcher.running:
            time.sleep(0.5)
    except KeyboardInterrupt:
        logger.info("キーボード割り込みを検出。")
    finally:
        watcher.stop()
