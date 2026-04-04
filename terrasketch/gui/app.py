"""TerraSketch GUIアプリケーション（Tkinter）。

全機能をGUIから利用可能にする統合インターフェース:
- 構成図生成（State JSON / HCL）
- Diff比較モード
- ファイル変更監視（Watch）
- Web UIサーバー起動
- Terraform Cloud連携
- テーマ・レイアウト・グルーピング設定
"""

from __future__ import annotations

import logging
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, scrolledtext, ttk

from terrasketch.graph.builder import build_graph
from terrasketch.graph.security import annotate_security_rules
from terrasketch.graph.summary import generate_summary
from terrasketch.layout.engine import calculate_layout
from terrasketch.parser.state_parser import parse_state
from terrasketch.renderer.drawio_renderer import DrawioRenderer
from terrasketch.renderer.mermaid_renderer import MermaidRenderer
from terrasketch.renderer.plantuml_renderer import PlantUMLRenderer
from terrasketch.renderer.svg_renderer import SvgRenderer

logger = logging.getLogger("terrasketch")


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
        self.root.geometry("780x750")
        self.root.resizable(True, True)

        # --- 変数定義 ---
        # モード選択
        self._mode = tk.StringVar(value="generate")

        # 生成モード
        self._input_type = tk.StringVar(value="state")
        self._state_path = tk.StringVar()
        self._hcl_path = tk.StringVar()
        self._output_dir = tk.StringVar(value=str(Path.cwd()))
        self._provider = tk.StringVar(value="aws")
        self._format = tk.StringVar(value="drawio")
        self._security = tk.BooleanVar(value=False)
        self._summary = tk.BooleanVar(value=False)
        self._labels = tk.BooleanVar(value=False)
        self._layout = tk.StringVar(value="hierarchical")
        self._group_by = tk.StringVar(value="none")
        self._theme = tk.StringVar(value="default")
        self._theme_file = tk.StringVar()

        # Diffモード
        self._before_path = tk.StringVar()
        self._after_path = tk.StringVar()

        # Watchモード
        self._watch_active = False
        self._watcher = None

        # Web UIモード
        self._web_host = tk.StringVar(value="127.0.0.1")
        self._web_port = tk.StringVar(value="8080")
        self._web_running = False
        self._web_server_thread = None

        # TFCモード
        self._tfc_workspace = tk.StringVar()
        self._tfc_token = tk.StringVar()
        self._tfc_url = tk.StringVar()

        self._build_ui()

    # ------------------------------------------------------------------ UI構築
    def _build_ui(self) -> None:
        """UIコンポーネントを構築する。"""
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ========== モードタブ ==========
        self._notebook = ttk.Notebook(main_frame)
        self._notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # --- 生成タブ ---
        self._tab_generate = ttk.Frame(self._notebook, padding=5)
        self._notebook.add(self._tab_generate, text="構成図生成")
        self._build_generate_tab(self._tab_generate)

        # --- Diffタブ ---
        self._tab_diff = ttk.Frame(self._notebook, padding=5)
        self._notebook.add(self._tab_diff, text="Diff比較")
        self._build_diff_tab(self._tab_diff)

        # --- Watchタブ ---
        self._tab_watch = ttk.Frame(self._notebook, padding=5)
        self._notebook.add(self._tab_watch, text="Watch監視")
        self._build_watch_tab(self._tab_watch)

        # --- Web UIタブ ---
        self._tab_web = ttk.Frame(self._notebook, padding=5)
        self._notebook.add(self._tab_web, text="Web UI")
        self._build_web_tab(self._tab_web)

        # --- TFCタブ ---
        self._tab_tfc = ttk.Frame(self._notebook, padding=5)
        self._notebook.add(self._tab_tfc, text="TFC連携")
        self._build_tfc_tab(self._tab_tfc)

        # ========== ログ表示エリア（共通） ==========
        log_frame = ttk.LabelFrame(main_frame, text="ログ", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self._log = scrolledtext.ScrolledText(
            log_frame, height=10, state=tk.DISABLED, wrap=tk.WORD
        )
        self._log.pack(fill=tk.BOTH, expand=True)

    # ---- 生成タブ ----
    def _build_generate_tab(self, parent: ttk.Frame) -> None:
        """構成図生成タブを構築する。"""
        # 入力形式選択
        input_type_frame = ttk.LabelFrame(parent, text="入力形式", padding=5)
        input_type_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Radiobutton(
            input_type_frame, text="State JSON", value="state",
            variable=self._input_type, command=self._toggle_input,
        ).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(
            input_type_frame, text="HCL ファイル", value="hcl",
            variable=self._input_type, command=self._toggle_input,
        ).pack(side=tk.LEFT, padx=10)

        # stateファイル選択
        self._state_frame = ttk.LabelFrame(parent, text="Stateファイル", padding=5)
        self._state_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Entry(self._state_frame, textvariable=self._state_path).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(self._state_frame, text="参照...", command=self._browse_state).pack(side=tk.RIGHT)

        # HCLファイル/ディレクトリ選択
        self._hcl_frame = ttk.LabelFrame(parent, text="HCLファイル / ディレクトリ", padding=5)
        ttk.Entry(self._hcl_frame, textvariable=self._hcl_path).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        hcl_btn_frame = ttk.Frame(self._hcl_frame)
        hcl_btn_frame.pack(side=tk.RIGHT)
        ttk.Button(hcl_btn_frame, text="ファイル...", command=self._browse_hcl_file).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(hcl_btn_frame, text="フォルダ...", command=self._browse_hcl_dir).pack(side=tk.LEFT)

        # 共通設定（プロバイダ・出力形式・出力先）
        self._build_common_settings(parent)

        # 詳細オプション
        opts_frame = ttk.LabelFrame(parent, text="オプション", padding=5)
        opts_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Checkbutton(opts_frame, text="セキュリティルール", variable=self._security).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(opts_frame, text="サマリー表示", variable=self._summary).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(opts_frame, text="エッジラベル", variable=self._labels).pack(side=tk.LEFT, padx=5)

        # レイアウト・グルーピング・テーマ
        adv_frame = ttk.LabelFrame(parent, text="レイアウト / テーマ", padding=5)
        adv_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(adv_frame, text="レイアウト:").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Combobox(
            adv_frame, textvariable=self._layout, width=12, state="readonly",
            values=["hierarchical", "grid", "force"],
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(adv_frame, text="グループ:").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Combobox(
            adv_frame, textvariable=self._group_by, width=8, state="readonly",
            values=["none", "module"],
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(adv_frame, text="テーマ:").pack(side=tk.LEFT, padx=(0, 2))
        ttk.Combobox(
            adv_frame, textvariable=self._theme, width=10, state="readonly",
            values=["default", "light", "dark", "custom"],
        ).pack(side=tk.LEFT, padx=(0, 5))
        self._theme_file_btn = ttk.Button(
            adv_frame, text="ファイル...", command=self._browse_theme_file,
            state=tk.DISABLED,
        )
        self._theme_file_btn.pack(side=tk.LEFT)
        self._theme.trace_add("write", self._on_theme_change)

        # 実行ボタン
        self._gen_btn = ttk.Button(parent, text="構成図を生成", command=self._run_generate)
        self._gen_btn.pack(pady=5)

    # ---- Diffタブ ----
    def _build_diff_tab(self, parent: ttk.Frame) -> None:
        """Diff比較タブを構築する。"""
        # Before
        before_frame = ttk.LabelFrame(parent, text="変更前 State JSON", padding=5)
        before_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Entry(before_frame, textvariable=self._before_path).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(before_frame, text="参照...", command=self._browse_before).pack(side=tk.RIGHT)

        # After
        after_frame = ttk.LabelFrame(parent, text="変更後 State JSON", padding=5)
        after_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Entry(after_frame, textvariable=self._after_path).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(after_frame, text="参照...", command=self._browse_after).pack(side=tk.RIGHT)

        # プロバイダ・出力形式・出力先
        self._build_diff_settings(parent)

        # 実行ボタン
        self._diff_btn = ttk.Button(parent, text="Diff構成図を生成", command=self._run_diff)
        self._diff_btn.pack(pady=5)

    # ---- Watchタブ ----
    def _build_watch_tab(self, parent: ttk.Frame) -> None:
        """Watch監視タブを構築する。"""
        desc = ttk.Label(
            parent,
            text="State/HCLファイルの変更を監視し、自動で構成図を再生成します。",
            wraplength=700,
        )
        desc.pack(anchor=tk.W, pady=(0, 10))

        # 監視対象
        watch_input_frame = ttk.LabelFrame(parent, text="監視対象", padding=5)
        watch_input_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(watch_input_frame, text="入力形式は「構成図生成」タブの設定を使用します。").pack(anchor=tk.W)

        # 出力先
        watch_out_frame = ttk.LabelFrame(parent, text="出力ディレクトリ", padding=5)
        watch_out_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(watch_out_frame, text="「構成図生成」タブの出力ディレクトリ設定を使用します。").pack(anchor=tk.W)

        # 開始/停止ボタン
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(pady=5)
        self._watch_start_btn = ttk.Button(btn_frame, text="監視を開始", command=self._start_watch)
        self._watch_start_btn.pack(side=tk.LEFT, padx=5)
        self._watch_stop_btn = ttk.Button(btn_frame, text="監視を停止", command=self._stop_watch, state=tk.DISABLED)
        self._watch_stop_btn.pack(side=tk.LEFT, padx=5)

        # ステータス
        self._watch_status = tk.StringVar(value="停止中")
        ttk.Label(parent, textvariable=self._watch_status, foreground="gray").pack(anchor=tk.W)

    # ---- Web UIタブ ----
    def _build_web_tab(self, parent: ttk.Frame) -> None:
        """Web UIタブを構築する。"""
        desc = ttk.Label(
            parent,
            text="ブラウザベースのWeb UIを起動します。ファイルアップロード→プレビュー→ダウンロードのワークフローを提供します。",
            wraplength=700,
        )
        desc.pack(anchor=tk.W, pady=(0, 10))

        settings_frame = ttk.LabelFrame(parent, text="サーバー設定", padding=5)
        settings_frame.pack(fill=tk.X, pady=(0, 5))

        row1 = ttk.Frame(settings_frame)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="ホスト:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(row1, textvariable=self._web_host, width=20).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Label(row1, text="ポート:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(row1, textvariable=self._web_port, width=8).pack(side=tk.LEFT)

        btn_frame = ttk.Frame(parent)
        btn_frame.pack(pady=5)
        self._web_start_btn = ttk.Button(btn_frame, text="サーバーを起動", command=self._start_web)
        self._web_start_btn.pack(side=tk.LEFT, padx=5)
        self._web_stop_btn = ttk.Button(btn_frame, text="サーバーを停止", command=self._stop_web, state=tk.DISABLED)
        self._web_stop_btn.pack(side=tk.LEFT, padx=5)

        self._web_status = tk.StringVar(value="停止中")
        ttk.Label(parent, textvariable=self._web_status, foreground="gray").pack(anchor=tk.W)

    # ---- TFCタブ ----
    def _build_tfc_tab(self, parent: ttk.Frame) -> None:
        """Terraform Cloud連携タブを構築する。"""
        desc = ttk.Label(
            parent,
            text="Terraform Cloud / Enterprise からStateを取得し、構成図を生成します。",
            wraplength=700,
        )
        desc.pack(anchor=tk.W, pady=(0, 10))

        settings_frame = ttk.LabelFrame(parent, text="TFC設定", padding=5)
        settings_frame.pack(fill=tk.X, pady=(0, 5))

        row1 = ttk.Frame(settings_frame)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="ワークスペース (org/workspace):").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(row1, textvariable=self._tfc_workspace, width=35).pack(side=tk.LEFT, fill=tk.X, expand=True)

        row2 = ttk.Frame(settings_frame)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="APIトークン:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(row2, textvariable=self._tfc_token, width=40, show="*").pack(side=tk.LEFT, fill=tk.X, expand=True)

        row3 = ttk.Frame(settings_frame)
        row3.pack(fill=tk.X, pady=2)
        ttk.Label(row3, text="APIベースURL (Enterprise用, 省略可):").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(row3, textvariable=self._tfc_url, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # プロバイダ・出力形式・出力先
        self._build_tfc_output_settings(parent)

        self._tfc_btn = ttk.Button(parent, text="TFCから構成図を生成", command=self._run_tfc)
        self._tfc_btn.pack(pady=5)

    # ---- 共通設定ビルダー ----
    def _build_common_settings(self, parent: ttk.Frame) -> None:
        """プロバイダ・出力形式・出力先の共通UIを構築する（生成タブ用）。"""
        # 出力ディレクトリ選択
        out_frame = ttk.LabelFrame(parent, text="出力ディレクトリ", padding=5)
        out_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Entry(out_frame, textvariable=self._output_dir).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(out_frame, text="参照...", command=self._browse_output).pack(side=tk.RIGHT)

        # プロバイダ + 出力形式（横並び）
        row_frame = ttk.Frame(parent)
        row_frame.pack(fill=tk.X, pady=(0, 5))

        prov_frame = ttk.LabelFrame(row_frame, text="プロバイダ", padding=5)
        prov_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        for prov in ("aws", "azure", "gcp", "all"):
            ttk.Radiobutton(prov_frame, text=prov.upper(), value=prov, variable=self._provider).pack(side=tk.LEFT, padx=10)

        fmt_frame = ttk.LabelFrame(row_frame, text="出力形式", padding=5)
        fmt_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        for fmt, label in (("drawio", "draw.io"), ("mermaid", "Mermaid"), ("plantuml", "PlantUML"), ("svg", "SVG")):
            ttk.Radiobutton(fmt_frame, text=label, value=fmt, variable=self._format).pack(side=tk.LEFT, padx=5)

    def _build_diff_settings(self, parent: ttk.Frame) -> None:
        """Diffタブ用のプロバイダ・出力形式・出力先を構築する。"""
        # Diff用にもプロバイダ・フォーマット・出力先が必要だが、生成タブの変数を共有
        out_frame = ttk.LabelFrame(parent, text="出力ディレクトリ", padding=5)
        out_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Entry(out_frame, textvariable=self._output_dir).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(out_frame, text="参照...", command=self._browse_output).pack(side=tk.RIGHT)

        row_frame = ttk.Frame(parent)
        row_frame.pack(fill=tk.X, pady=(0, 5))

        prov_frame = ttk.LabelFrame(row_frame, text="プロバイダ", padding=5)
        prov_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        for prov in ("aws", "azure", "gcp", "all"):
            ttk.Radiobutton(prov_frame, text=prov.upper(), value=prov, variable=self._provider).pack(side=tk.LEFT, padx=10)

        fmt_frame = ttk.LabelFrame(row_frame, text="出力形式", padding=5)
        fmt_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        for fmt, label in (("drawio", "draw.io"), ("mermaid", "Mermaid"), ("plantuml", "PlantUML"), ("svg", "SVG")):
            ttk.Radiobutton(fmt_frame, text=label, value=fmt, variable=self._format).pack(side=tk.LEFT, padx=5)

    def _build_tfc_output_settings(self, parent: ttk.Frame) -> None:
        """TFCタブ用のプロバイダ・出力形式・出力先を構築する。"""
        out_frame = ttk.LabelFrame(parent, text="出力ディレクトリ", padding=5)
        out_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Entry(out_frame, textvariable=self._output_dir).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(out_frame, text="参照...", command=self._browse_output).pack(side=tk.RIGHT)

        row_frame = ttk.Frame(parent)
        row_frame.pack(fill=tk.X, pady=(0, 5))

        prov_frame = ttk.LabelFrame(row_frame, text="プロバイダ", padding=5)
        prov_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        for prov in ("aws", "azure", "gcp", "all"):
            ttk.Radiobutton(prov_frame, text=prov.upper(), value=prov, variable=self._provider).pack(side=tk.LEFT, padx=10)

        fmt_frame = ttk.LabelFrame(row_frame, text="出力形式", padding=5)
        fmt_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        for fmt, label in (("drawio", "draw.io"), ("mermaid", "Mermaid"), ("plantuml", "PlantUML"), ("svg", "SVG")):
            ttk.Radiobutton(fmt_frame, text=label, value=fmt, variable=self._format).pack(side=tk.LEFT, padx=5)

    # ----------------------------------------------------------------- イベント
    def _toggle_input(self) -> None:
        """入力形式の切替に応じてフレームの表示/非表示を切り替える。"""
        if self._input_type.get() == "state":
            self._hcl_frame.pack_forget()
            self._state_frame.pack(
                fill=tk.X, pady=(0, 5),
                before=self._state_frame.master.winfo_children()[2],
            )
        else:
            self._state_frame.pack_forget()
            self._hcl_frame.pack(
                fill=tk.X, pady=(0, 5),
                before=self._state_frame.master.winfo_children()[2],
            )

    def _on_theme_change(self, *_args: object) -> None:
        """テーマ選択の変更時にカスタムファイル参照ボタンを有効/無効化する。"""
        if self._theme.get() == "custom":
            self._theme_file_btn.configure(state=tk.NORMAL)
        else:
            self._theme_file_btn.configure(state=tk.DISABLED)

    # ------------------------------------------------------------------ ファイル選択
    def _browse_state(self) -> None:
        """stateファイル選択ダイアログを表示する。"""
        path = filedialog.askopenfilename(
            title="Terraform State JSONを選択",
            filetypes=[("JSONファイル", "*.json"), ("すべてのファイル", "*.*")],
        )
        if path:
            self._state_path.set(path)

    def _browse_hcl_file(self) -> None:
        """HCLファイル選択ダイアログを表示する。"""
        path = filedialog.askopenfilename(
            title="Terraform HCLファイルを選択",
            filetypes=[("Terraformファイル", "*.tf"), ("すべてのファイル", "*.*")],
        )
        if path:
            self._hcl_path.set(path)

    def _browse_hcl_dir(self) -> None:
        """HCLディレクトリ選択ダイアログを表示する。"""
        path = filedialog.askdirectory(title="Terraform HCLディレクトリを選択")
        if path:
            self._hcl_path.set(path)

    def _browse_output(self) -> None:
        """出力ディレクトリ選択ダイアログを表示する。"""
        path = filedialog.askdirectory(title="出力ディレクトリを選択")
        if path:
            self._output_dir.set(path)

    def _browse_before(self) -> None:
        """変更前stateファイル選択ダイアログを表示する。"""
        path = filedialog.askopenfilename(
            title="変更前のState JSONを選択",
            filetypes=[("JSONファイル", "*.json"), ("すべてのファイル", "*.*")],
        )
        if path:
            self._before_path.set(path)

    def _browse_after(self) -> None:
        """変更後stateファイル選択ダイアログを表示する。"""
        path = filedialog.askopenfilename(
            title="変更後のState JSONを選択",
            filetypes=[("JSONファイル", "*.json"), ("すべてのファイル", "*.*")],
        )
        if path:
            self._after_path.set(path)

    def _browse_theme_file(self) -> None:
        """テーマファイル選択ダイアログを表示する。"""
        path = filedialog.askopenfilename(
            title="テーマファイルを選択",
            filetypes=[
                ("YAML", "*.yaml *.yml"),
                ("TOML", "*.toml"),
                ("JSON", "*.json"),
                ("すべてのファイル", "*.*"),
            ],
        )
        if path:
            self._theme_file.set(path)

    # ------------------------------------------------------------------ ログ
    def _log_message(self, msg: str) -> None:
        """ログエリアにメッセージを追加する。"""
        self._log.configure(state=tk.NORMAL)
        self._log.insert(tk.END, msg + "\n")
        self._log.see(tk.END)
        self._log.configure(state=tk.DISABLED)

    # ------------------------------------------------------------------ 構成図生成
    def _run_generate(self) -> None:
        """構成図生成をバックグラウンドスレッドで開始する。"""
        if self._input_type.get() == "state":
            input_path = self._state_path.get().strip()
            if not input_path:
                self._log_message("[ERROR] stateファイルを選択してください。")
                return
        else:
            input_path = self._hcl_path.get().strip()
            if not input_path:
                self._log_message("[ERROR] HCLファイルまたはディレクトリを選択してください。")
                return

        output_dir = self._output_dir.get().strip()
        if not output_dir:
            self._log_message("[ERROR] 出力ディレクトリを選択してください。")
            return

        self._gen_btn.configure(state=tk.DISABLED)
        thread = threading.Thread(
            target=self._generate, args=(input_path, output_dir), daemon=True,
        )
        thread.start()

    def _get_theme_value(self) -> str | None:
        """テーマ設定値を返す。"""
        theme = self._theme.get()
        if theme == "custom":
            return self._theme_file.get().strip() or None
        if theme == "default":
            return None
        return theme

    def _generate(self, input_path: str, output_dir: str) -> None:
        """構成図生成パイプラインを実行する（バックグラウンドスレッド）。"""
        try:
            from terrasketch.main import generate

            hcl_path = None
            state_path = None
            if self._input_type.get() == "hcl":
                hcl_path = input_path
                self._log_message(f"[INFO] HCL入力: {input_path}")
            else:
                state_path = input_path
                self._log_message(f"[INFO] State入力: {input_path}")

            group_by = self._group_by.get()
            if group_by == "none":
                group_by = None

            result = generate(
                state_path=state_path,
                provider=self._provider.get(),
                output_dir=output_dir,
                output_format=self._format.get(),
                show_security=self._security.get(),
                show_summary=self._summary.get(),
                hcl_path=hcl_path,
                show_labels=self._labels.get(),
                layout_type=self._layout.get(),
                group_by=group_by,
                theme=self._get_theme_value(),
            )
            self._log_message(f"[SUCCESS] 構成図を保存しました: {result}")
        except Exception as e:
            self._log_message(f"[ERROR] {e}")
        finally:
            self.root.after(0, lambda: self._gen_btn.configure(state=tk.NORMAL))

    # ------------------------------------------------------------------ Diff
    def _run_diff(self) -> None:
        """Diff比較をバックグラウンドスレッドで開始する。"""
        before = self._before_path.get().strip()
        after = self._after_path.get().strip()
        output_dir = self._output_dir.get().strip()

        if not before:
            self._log_message("[ERROR] 変更前のstateファイルを選択してください。")
            return
        if not after:
            self._log_message("[ERROR] 変更後のstateファイルを選択してください。")
            return
        if not output_dir:
            self._log_message("[ERROR] 出力ディレクトリを選択してください。")
            return

        self._diff_btn.configure(state=tk.DISABLED)
        thread = threading.Thread(
            target=self._diff_generate, args=(before, after, output_dir), daemon=True,
        )
        thread.start()

    def _diff_generate(self, before: str, after: str, output_dir: str) -> None:
        """Diff比較パイプラインを実行する（バックグラウンドスレッド）。"""
        try:
            from terrasketch.main import diff_generate

            self._log_message(f"[INFO] Diff比較: {before} → {after}")
            result = diff_generate(
                before_path=before,
                after_path=after,
                provider=self._provider.get(),
                output_dir=output_dir,
                output_format=self._format.get(),
            )
            self._log_message(f"[SUCCESS] Diff構成図を保存しました: {result}")
        except Exception as e:
            self._log_message(f"[ERROR] {e}")
        finally:
            self.root.after(0, lambda: self._diff_btn.configure(state=tk.NORMAL))

    # ------------------------------------------------------------------ Watch
    def _start_watch(self) -> None:
        """ファイル変更監視を開始する。"""
        if self._input_type.get() == "state":
            input_path = self._state_path.get().strip()
            if not input_path:
                self._log_message("[ERROR] 監視対象のstateファイルを「構成図生成」タブで選択してください。")
                return
        else:
            input_path = self._hcl_path.get().strip()
            if not input_path:
                self._log_message("[ERROR] 監視対象のHCLファイルを「構成図生成」タブで選択してください。")
                return

        output_dir = self._output_dir.get().strip()
        if not output_dir:
            self._log_message("[ERROR] 出力ディレクトリを選択してください。")
            return

        from terrasketch.watch.watcher import FileWatcher
        from terrasketch.main import generate

        state_path = input_path if self._input_type.get() == "state" else None
        hcl_path = input_path if self._input_type.get() == "hcl" else None

        group_by = self._group_by.get()
        if group_by == "none":
            group_by = None

        def regenerate() -> None:
            """監視コールバック: 構成図を再生成する。"""
            try:
                result = generate(
                    state_path=state_path,
                    provider=self._provider.get(),
                    output_dir=output_dir,
                    output_format=self._format.get(),
                    hcl_path=hcl_path,
                    show_labels=self._labels.get(),
                    layout_type=self._layout.get(),
                    group_by=group_by,
                    theme=self._get_theme_value(),
                )
                self._log_message(f"[WATCH] 再生成完了: {result}")
            except Exception as e:
                self._log_message(f"[WATCH ERROR] {e}")

        watch_paths = [input_path]
        self._watcher = FileWatcher(watch_paths, regenerate, debounce_sec=0.5, poll_interval=1.0)

        # 初回生成
        self._log_message("[WATCH] 初回生成を実行中...")
        threading.Thread(target=regenerate, daemon=True).start()

        self._watcher.start()
        self._watch_active = True
        self._watch_start_btn.configure(state=tk.DISABLED)
        self._watch_stop_btn.configure(state=tk.NORMAL)
        self._watch_status.set("監視中...")
        self._log_message("[WATCH] ファイル変更監視を開始しました。")

    def _stop_watch(self) -> None:
        """ファイル変更監視を停止する。"""
        if self._watcher:
            self._watcher.stop()
            self._watcher = None
        self._watch_active = False
        self._watch_start_btn.configure(state=tk.NORMAL)
        self._watch_stop_btn.configure(state=tk.DISABLED)
        self._watch_status.set("停止中")
        self._log_message("[WATCH] ファイル変更監視を停止しました。")

    # ------------------------------------------------------------------ Web UI
    def _start_web(self) -> None:
        """Web UIサーバーをバックグラウンドで起動する。"""
        host = self._web_host.get().strip()
        try:
            port = int(self._web_port.get().strip())
        except ValueError:
            self._log_message("[ERROR] ポート番号が不正です。")
            return

        from http.server import HTTPServer
        from terrasketch.web.server import TerraSketchHandler

        try:
            self._web_server = HTTPServer((host, port), TerraSketchHandler)
        except OSError as e:
            self._log_message(f"[ERROR] サーバー起動失敗: {e}")
            return

        self._web_running = True
        self._web_server_thread = threading.Thread(
            target=self._web_server.serve_forever, daemon=True,
        )
        self._web_server_thread.start()

        self._web_start_btn.configure(state=tk.DISABLED)
        self._web_stop_btn.configure(state=tk.NORMAL)
        self._web_status.set(f"起動中: http://{host}:{port}")
        self._log_message(f"[WEB] サーバーを起動しました: http://{host}:{port}")

    def _stop_web(self) -> None:
        """Web UIサーバーを停止する。"""
        if hasattr(self, "_web_server") and self._web_server:
            self._web_server.shutdown()
            self._web_server.server_close()
            self._web_server = None

        self._web_running = False
        self._web_start_btn.configure(state=tk.NORMAL)
        self._web_stop_btn.configure(state=tk.DISABLED)
        self._web_status.set("停止中")
        self._log_message("[WEB] サーバーを停止しました。")

    # ------------------------------------------------------------------ TFC
    def _run_tfc(self) -> None:
        """TFC連携をバックグラウンドスレッドで開始する。"""
        workspace = self._tfc_workspace.get().strip()
        if not workspace:
            self._log_message("[ERROR] ワークスペース（org/workspace）を入力してください。")
            return

        if "/" not in workspace:
            self._log_message("[ERROR] ワークスペースは 'org/workspace' 形式で入力してください。")
            return

        output_dir = self._output_dir.get().strip()
        if not output_dir:
            self._log_message("[ERROR] 出力ディレクトリを選択してください。")
            return

        token = self._tfc_token.get().strip() or None
        base_url = self._tfc_url.get().strip() or None

        self._tfc_btn.configure(state=tk.DISABLED)
        thread = threading.Thread(
            target=self._tfc_generate,
            args=(workspace, token, base_url, output_dir),
            daemon=True,
        )
        thread.start()

    def _tfc_generate(
        self, workspace: str, token: str | None, base_url: str | None, output_dir: str
    ) -> None:
        """TFC連携パイプラインを実行する（バックグラウンドスレッド）。"""
        try:
            from terrasketch.remote.tfc_client import fetch_and_generate

            self._log_message(f"[TFC] ワークスペース {workspace} からstate取得中...")
            result = fetch_and_generate(
                workspace_spec=workspace,
                token=token,
                provider=self._provider.get(),
                output_dir=output_dir,
                output_format=self._format.get(),
                base_url=base_url,
            )
            self._log_message(f"[SUCCESS] TFC構成図を保存しました: {result}")
        except Exception as e:
            self._log_message(f"[ERROR] {e}")
        finally:
            self.root.after(0, lambda: self._tfc_btn.configure(state=tk.NORMAL))

    # ------------------------------------------------------------------ メインループ
    def run(self) -> None:
        """Tkinterメインループを開始する。"""
        self.root.mainloop()
