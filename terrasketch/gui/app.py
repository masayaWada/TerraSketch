"""TerraSketch GUI application using Tkinter.

Provides a graphical interface for selecting state files, output directories,
and providers, then runs the diagram generation pipeline in a background thread.
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
    """Redirects write calls to a Tkinter text widget."""

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
    """Main GUI application window."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("TerraSketch - Terraform Diagram Generator")
        self.root.geometry("700x500")
        self.root.resizable(True, True)

        self._state_path = tk.StringVar()
        self._output_dir = tk.StringVar(value=str(Path.cwd()))
        self._provider = tk.StringVar(value="aws")
        self._format = tk.StringVar(value="drawio")
        self._security = tk.BooleanVar(value=False)
        self._summary = tk.BooleanVar(value=False)

        self._build_ui()

    def _build_ui(self) -> None:
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # State file selection
        file_frame = ttk.LabelFrame(main_frame, text="State File", padding=5)
        file_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Entry(file_frame, textvariable=self._state_path).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5)
        )
        ttk.Button(file_frame, text="Browse...", command=self._browse_state).pack(
            side=tk.RIGHT
        )

        # Output directory selection
        out_frame = ttk.LabelFrame(main_frame, text="Output Directory", padding=5)
        out_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Entry(out_frame, textvariable=self._output_dir).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5)
        )
        ttk.Button(out_frame, text="Browse...", command=self._browse_output).pack(
            side=tk.RIGHT
        )

        # Provider selection
        prov_frame = ttk.LabelFrame(main_frame, text="Provider", padding=5)
        prov_frame.pack(fill=tk.X, pady=(0, 5))

        for provider in ("aws", "azure"):
            ttk.Radiobutton(
                prov_frame, text=provider.upper(), value=provider,
                variable=self._provider,
            ).pack(side=tk.LEFT, padx=10)

        # Output format selection
        fmt_frame = ttk.LabelFrame(main_frame, text="Output Format", padding=5)
        fmt_frame.pack(fill=tk.X, pady=(0, 5))

        for fmt, label in (("drawio", "draw.io"), ("mermaid", "Mermaid")):
            ttk.Radiobutton(
                fmt_frame, text=label, value=fmt,
                variable=self._format,
            ).pack(side=tk.LEFT, padx=10)

        # Options
        opts_frame = ttk.LabelFrame(main_frame, text="Options", padding=5)
        opts_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Checkbutton(
            opts_frame, text="Security Rules", variable=self._security,
        ).pack(side=tk.LEFT, padx=10)
        ttk.Checkbutton(
            opts_frame, text="Show Summary", variable=self._summary,
        ).pack(side=tk.LEFT, padx=10)

        # Execute button
        self._run_btn = ttk.Button(
            main_frame, text="Generate Diagram", command=self._run
        )
        self._run_btn.pack(pady=5)

        # Log area
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self._log = scrolledtext.ScrolledText(
            log_frame, height=12, state=tk.DISABLED, wrap=tk.WORD
        )
        self._log.pack(fill=tk.BOTH, expand=True)

    def _browse_state(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Terraform State JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if path:
            self._state_path.set(path)

    def _browse_output(self) -> None:
        path = filedialog.askdirectory(title="Select Output Directory")
        if path:
            self._output_dir.set(path)

    def _log_message(self, msg: str) -> None:
        self._log.configure(state=tk.NORMAL)
        self._log.insert(tk.END, msg + "\n")
        self._log.see(tk.END)
        self._log.configure(state=tk.DISABLED)

    def _run(self) -> None:
        state_path = self._state_path.get().strip()
        output_dir = self._output_dir.get().strip()

        if not state_path:
            self._log_message("[ERROR] Please select a state file.")
            return
        if not output_dir:
            self._log_message("[ERROR] Please select an output directory.")
            return

        self._run_btn.configure(state=tk.DISABLED)
        thread = threading.Thread(
            target=self._generate, args=(state_path, output_dir), daemon=True
        )
        thread.start()

    def _generate(self, state_path: str, output_dir: str) -> None:
        try:
            self._log_message("[INFO] Parsing state file...")
            resources = parse_state(state_path)
            self._log_message(f"[INFO] Found {len(resources)} resources.")

            provider = self._provider.get()
            prefix_map = {"aws": "aws_", "azure": "azurerm_"}
            prefix = prefix_map.get(provider, "")
            if prefix:
                filtered = [r for r in resources if r.type.startswith(prefix)]
                self._log_message(
                    f"[INFO] Filtered to {len(filtered)} {provider.upper()} resources."
                )
            else:
                filtered = resources

            self._log_message("[INFO] Building dependency graph...")
            graph = build_graph(filtered)
            self._log_message(
                f"[INFO] Graph: {graph.number_of_nodes()} nodes, "
                f"{graph.number_of_edges()} edges."
            )

            if self._security.get():
                self._log_message("[INFO] Annotating security group rules...")
                annotate_security_rules(graph)

            if self._summary.get():
                summary = generate_summary(filtered, graph)
                self._log_message(summary)

            self._log_message("[INFO] Calculating layout...")
            positions = calculate_layout(graph)

            fmt = self._format.get()
            if fmt == "mermaid":
                self._log_message("[INFO] Rendering Mermaid diagram...")
                renderer = MermaidRenderer()
                output_path = Path(output_dir) / "terrasketch_output.md"
            else:
                self._log_message("[INFO] Rendering draw.io diagram...")
                renderer = DrawioRenderer()
                output_path = Path(output_dir) / "terrasketch_output.drawio"
            result = renderer.render(graph, positions, output_path)

            self._log_message(f"[SUCCESS] Diagram saved to: {result}")
        except Exception as e:
            self._log_message(f"[ERROR] {e}")
        finally:
            self.root.after(0, lambda: self._run_btn.configure(state=tk.NORMAL))

    def run(self) -> None:
        """Start the Tkinter main loop."""
        self.root.mainloop()
