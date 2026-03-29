"""TerraSketch GUIアプリケーション（Tkinter）。

stateファイル・出力ディレクトリ・プロバイダ選択のGUIを提供し、
バックグラウンドスレッドで構成図生成パイプラインを実行する。
"""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, scrolledtext, ttk
from typing import TextIO

from terrasketch.graph.builder import build_graph
from terrasketch.graph.security import annotate_security_rules
from terrasketch.graph.summary import generate_summary
from terrasketch.layout.engine import calculate_layout
from terrasketch.parser.state_parser import parse_state
from terrasketch.renderer.drawio_renderer import DrawioRenderer
from terrasketch.renderer.mermaid_renderer import MermaidRenderer


class LogRedirector:
    """書き込みをTkinterテキストウィジェットにリダイレクトする。"""

    def __init__(self, text_widget: scrolledtext.ScrolledText) -> None:
        self._widget = text_widget

    def write(self, message: str) -> None:
        self._widget.after(0, self._append, message)

    def _append(self, message: str) -> None:
        self._widget.configure(state=tk.NORMAL)
        self._widget.insert(tk.END, message)
        self._widget.see(tk.END)
        self._widget.configure(state=tk.DISABLED)

    def flush(self) -> None:
        pass


class TerraSketchApp:
    """メインGUIアプリケーションウィンドウ。"""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("TerraSketch - Terraform構成図生成ツール")
        self.root.geometry("700x550")
        self.root.resizable(True, True)

        self._state_path = tk.StringVar()
        self._output_dir = tk.StringVar(value=str(Path.cwd()))
        self._provider = tk.StringVar(value="aws")
        self._format = tk.StringVar(value="drawio")
        self._security = tk.BooleanVar(value=False)
        self._summary = tk.BooleanVar(value=False)

        self._build_ui()

    def _build_ui(self) -> None:
        """UIコンポーネントを構築する。"""
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # stateファイル選択
        file_frame = ttk.LabelFrame(main_frame, text="Stateファイル", padding=5)
        file_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Entry(file_frame, textvariable=self._state_path).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5)
        )
        ttk.Button(file_frame, text="参照...", command=self._browse_state).pack(
            side=tk.RIGHT
        )

        # 出力ディレクトリ選択
        out_frame = ttk.LabelFrame(main_frame, text="出力ディレクトリ", padding=5)
        out_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Entry(out_frame, textvariable=self._output_dir).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5)
        )
        ttk.Button(out_frame, text="参照...", command=self._browse_output).pack(
            side=tk.RIGHT
        )

        # プロバイダ選択
        prov_frame = ttk.LabelFrame(main_frame, text="プロバイダ", padding=5)
        prov_frame.pack(fill=tk.X, pady=(0, 5))

        for provider in ("aws", "azure"):
            ttk.Radiobutton(
                prov_frame, text=provider.upper(), value=provider,
                variable=self._provider,
            ).pack(side=tk.LEFT, padx=10)

        # 出力形式選択
        fmt_frame = ttk.LabelFrame(main_frame, text="出力形式", padding=5)
        fmt_frame.pack(fill=tk.X, pady=(0, 5))

        for fmt, label in (("drawio", "draw.io"), ("mermaid", "Mermaid")):
            ttk.Radiobutton(
                fmt_frame, text=label, value=fmt,
                variable=self._format,
            ).pack(side=tk.LEFT, padx=10)

        # オプション
        opts_frame = ttk.LabelFrame(main_frame, text="オプション", padding=5)
        opts_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Checkbutton(
            opts_frame, text="セキュリティルール表示", variable=self._security,
        ).pack(side=tk.LEFT, padx=10)
        ttk.Checkbutton(
            opts_frame, text="サマリー表示", variable=self._summary,
        ).pack(side=tk.LEFT, padx=10)

        # 実行ボタン
        self._run_btn = ttk.Button(
            main_frame, text="構成図を生成", command=self._run
        )
        self._run_btn.pack(pady=5)

        # ログ表示エリア
        log_frame = ttk.LabelFrame(main_frame, text="ログ", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self._log = scrolledtext.ScrolledText(
            log_frame, height=12, state=tk.DISABLED, wrap=tk.WORD
        )
        self._log.pack(fill=tk.BOTH, expand=True)

    def _browse_state(self) -> None:
        """stateファイル選択ダイアログを表示する。"""
        path = filedialog.askopenfilename(
            title="Terraform State JSONを選択",
            filetypes=[("JSONファイル", "*.json"), ("すべてのファイル", "*.*")],
        )
        if path:
            self._state_path.set(path)

    def _browse_output(self) -> None:
        """出力ディレクトリ選択ダイアログを表示する。"""
        path = filedialog.askdirectory(title="出力ディレクトリを選択")
        if path:
            self._output_dir.set(path)

    def _log_message(self, msg: str) -> None:
        """ログエリアにメッセージを追加する。"""
        self._log.configure(state=tk.NORMAL)
        self._log.insert(tk.END, msg + "\n")
        self._log.see(tk.END)
        self._log.configure(state=tk.DISABLED)

    def _run(self) -> None:
        """構成図生成をバックグラウンドスレッドで開始する。"""
        state_path = self._state_path.get().strip()
        output_dir = self._output_dir.get().strip()

        if not state_path:
            self._log_message("[ERROR] stateファイルを選択してください。")
            return
        if not output_dir:
            self._log_message("[ERROR] 出力ディレクトリを選択してください。")
            return

        self._run_btn.configure(state=tk.DISABLED)
        thread = threading.Thread(
            target=self._generate, args=(state_path, output_dir), daemon=True
        )
        thread.start()

    def _generate(self, state_path: str, output_dir: str) -> None:
        """構成図生成パイプラインを実行する（バックグラウンドスレッド）。"""
        try:
            self._log_message("[INFO] stateファイルを解析中...")
            resources = parse_state(state_path)
            self._log_message(f"[INFO] {len(resources)}件のリソースを検出。")

            provider = self._provider.get()
            prefix_map = {"aws": "aws_", "azure": "azurerm_"}
            prefix = prefix_map.get(provider, "")
            if prefix:
                filtered = [r for r in resources if r.type.startswith(prefix)]
                self._log_message(
                    f"[INFO] {provider.upper()}リソース{len(filtered)}件にフィルタ。"
                )
            else:
                filtered = resources

            self._log_message("[INFO] 依存関係グラフを構築中...")
            graph = build_graph(filtered)
            self._log_message(
                f"[INFO] グラフ: {graph.number_of_nodes()}ノード, "
                f"{graph.number_of_edges()}エッジ。"
            )

            if self._security.get():
                self._log_message("[INFO] セキュリティグループルールを注釈中...")
                annotate_security_rules(graph)

            if self._summary.get():
                summary = generate_summary(filtered, graph)
                self._log_message(summary)

            self._log_message("[INFO] レイアウトを計算中...")
            positions = calculate_layout(graph)

            fmt = self._format.get()
            if fmt == "mermaid":
                self._log_message("[INFO] Mermaidダイアグラムをレンダリング中...")
                renderer = MermaidRenderer()
                output_path = Path(output_dir) / "terrasketch_output.md"
            else:
                self._log_message("[INFO] draw.ioダイアグラムをレンダリング中...")
                renderer = DrawioRenderer()
                output_path = Path(output_dir) / "terrasketch_output.drawio"
            result = renderer.render(graph, positions, output_path)

            self._log_message(f"[SUCCESS] 構成図を保存しました: {result}")
        except Exception as e:
            self._log_message(f"[ERROR] {e}")
        finally:
            self.root.after(0, lambda: self._run_btn.configure(state=tk.NORMAL))

    def run(self) -> None:
        """Tkinterメインループを開始する。"""
        self.root.mainloop()
