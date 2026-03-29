"""TerraSketch CLIおよびGUIエントリーポイント。

使用方法:
    # CLIモード
    terrasketch generate --state state.json --provider aws
    terrasketch generate --state state.json --provider aws --format mermaid
    terrasketch generate --state state.json --provider aws --security --summary

    # GUIモード
    terrasketch gui
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from terrasketch.graph.builder import build_graph
from terrasketch.graph.security import annotate_security_rules
from terrasketch.graph.summary import generate_summary
from terrasketch.layout.engine import calculate_layout
from terrasketch.parser.state_parser import parse_state
from terrasketch.renderer.drawio_renderer import DrawioRenderer
from terrasketch.renderer.mermaid_renderer import MermaidRenderer


def generate(
    state_path: str,
    provider: str,
    output_dir: str,
    output_format: str = "drawio",
    show_security: bool = False,
    show_summary: bool = False,
) -> Path:
    """構成図生成パイプライン全体を実行する。

    Args:
        state_path: Terraform state JSONファイルのパス。
        provider: クラウドプロバイダフィルタ（'aws' または 'azure'）。
        output_dir: 出力ファイルを書き出すディレクトリ。
        output_format: 出力形式（'drawio' または 'mermaid'）。
        show_security: セキュリティグループルールの注釈を付与するか。
        show_summary: リソースサマリーを標準出力に表示するか。

    Returns:
        生成された出力ファイルのPath。
    """
    print(f"[INFO] stateファイルを解析中: {state_path}")
    resources = parse_state(state_path)
    print(f"[INFO] {len(resources)}件のリソースを検出。")

    # プロバイダでフィルタリング
    prefix_map = {"aws": "aws_", "azure": "azurerm_"}
    prefix = prefix_map.get(provider, "")
    if prefix:
        resources = [r for r in resources if r.type.startswith(prefix)]
        print(f"[INFO] {provider.upper()}リソース{len(resources)}件にフィルタ。")

    if not resources:
        print("[WARN] 該当リソースが見つかりません。出力は空になります。")

    print("[INFO] 依存関係グラフを構築中...")
    graph = build_graph(resources)
    print(
        f"[INFO] グラフ: {graph.number_of_nodes()}ノード, "
        f"{graph.number_of_edges()}エッジ。"
    )

    if show_security:
        print("[INFO] セキュリティグループルールを注釈中...")
        annotate_security_rules(graph)

    if show_summary:
        summary = generate_summary(resources, graph)
        print(summary)

    print("[INFO] レイアウトを計算中...")
    positions = calculate_layout(graph)

    output_path = Path(output_dir)

    if output_format == "mermaid":
        print("[INFO] Mermaidダイアグラムをレンダリング中...")
        renderer = MermaidRenderer()
        result = renderer.render(graph, positions, output_path / "terrasketch_output.md")
    else:
        print("[INFO] draw.ioダイアグラムをレンダリング中...")
        renderer = DrawioRenderer()
        result = renderer.render(graph, positions, output_path / "terrasketch_output.drawio")

    print(f"[SUCCESS] 構成図を保存しました: {result}")
    return result


def main() -> None:
    """CLIエントリーポイント。"""
    parser = argparse.ArgumentParser(
        prog="terrasketch",
        description="TerraSketch - Terraform stateを唯一の信頼源としてAWS/Azureの構成図を自動生成",
    )
    subparsers = parser.add_subparsers(dest="command", help="利用可能なコマンド")

    # generateコマンド
    gen_parser = subparsers.add_parser(
        "generate", help="Terraform stateファイルから構成図を生成"
    )
    gen_parser.add_argument(
        "--state", required=True, help="Terraform state JSONファイルのパス"
    )
    gen_parser.add_argument(
        "--provider",
        choices=["aws", "azure"],
        default="aws",
        help="クラウドプロバイダ（デフォルト: aws）",
    )
    gen_parser.add_argument(
        "--output",
        default=".",
        help="出力ディレクトリ（デフォルト: カレントディレクトリ）",
    )
    gen_parser.add_argument(
        "--format",
        choices=["drawio", "mermaid"],
        default="drawio",
        help="出力形式（デフォルト: drawio）",
    )
    gen_parser.add_argument(
        "--security",
        action="store_true",
        help="セキュリティグループルールを構成図に注釈",
    )
    gen_parser.add_argument(
        "--summary",
        action="store_true",
        help="リソースサマリーを標準出力に表示",
    )

    # guiコマンド
    subparsers.add_parser("gui", help="GUIを起動")

    args = parser.parse_args()

    if args.command == "generate":
        generate(
            args.state,
            args.provider,
            args.output,
            output_format=args.format,
            show_security=args.security,
            show_summary=args.summary,
        )
    elif args.command == "gui":
        from terrasketch.gui.app import TerraSketchApp

        app = TerraSketchApp()
        app.run()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
