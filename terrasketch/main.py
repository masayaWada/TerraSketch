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
import logging
import sys
from pathlib import Path

logger = logging.getLogger("terrasketch")

from terrasketch.graph.builder import build_graph
from terrasketch.graph.security import annotate_security_rules
from terrasketch.graph.summary import generate_summary
from terrasketch.layout.engine import calculate_layout
from terrasketch.parser.state_parser import parse_state
from terrasketch.renderer.drawio_renderer import DrawioRenderer
from terrasketch.renderer.mermaid_renderer import MermaidRenderer
from terrasketch.renderer.plantuml_renderer import PlantUMLRenderer


def generate(
    state_path: str | None,
    provider: str,
    output_dir: str,
    output_format: str = "drawio",
    show_security: bool = False,
    show_summary: bool = False,
    hcl_path: str | None = None,
    show_labels: bool = False,
) -> Path:
    """構成図生成パイプライン全体を実行する。

    Args:
        state_path: Terraform state JSONファイルのパス。
        provider: クラウドプロバイダフィルタ（'aws' または 'azure'）。
        output_dir: 出力ファイルを書き出すディレクトリ。
        output_format: 出力形式（'drawio'、'mermaid'、'plantuml'）。
        show_security: セキュリティグループルールの注釈を付与するか。
        show_summary: リソースサマリーを標準出力に表示するか。
        hcl_path: Terraform HCLファイルまたはディレクトリのパス。
        show_labels: エッジに接続属性名ラベルを表示するか。

    Returns:
        生成された出力ファイルのPath。
    """
    if hcl_path:
        from terrasketch.parser.hcl_parser import parse_hcl, parse_hcl_directory
        hcl = Path(hcl_path)
        if hcl.is_dir():
            logger.info("HCLディレクトリを解析中: %s", hcl_path)
            resources = parse_hcl_directory(hcl_path)
        else:
            logger.info("HCLファイルを解析中: %s", hcl_path)
            resources = parse_hcl(hcl_path)
    else:
        logger.info("stateファイルを解析中: %s", state_path)
        resources = parse_state(state_path)
    logger.info("%d件のリソースを検出。", len(resources))

    # プロバイダでフィルタリング
    prefix_map = {"aws": "aws_", "azure": "azurerm_"}
    prefix = prefix_map.get(provider, "")
    if prefix:
        resources = [r for r in resources if r.type.startswith(prefix)]
        logger.info("%sリソース%d件にフィルタ。", provider.upper(), len(resources))

    if not resources:
        logger.warning("該当リソースが見つかりません。出力は空になります。")

    logger.info("依存関係グラフを構築中...")
    graph = build_graph(resources)
    logger.info(
        "グラフ: %dノード, %dエッジ。",
        graph.number_of_nodes(),
        graph.number_of_edges(),
    )

    if show_security:
        logger.info("セキュリティグループルールを注釈中...")
        annotate_security_rules(graph)

    if show_summary:
        summary = generate_summary(resources, graph)
        print(summary)

    logger.info("レイアウトを計算中...")
    positions = calculate_layout(graph)

    output_path = Path(output_dir)

    if output_format == "mermaid":
        logger.info("Mermaidダイアグラムをレンダリング中...")
        renderer = MermaidRenderer()
        result = renderer.render(graph, positions, output_path / "terrasketch_output.md", show_labels=show_labels)
    elif output_format == "plantuml":
        logger.info("PlantUMLダイアグラムをレンダリング中...")
        renderer = PlantUMLRenderer()
        result = renderer.render(graph, positions, output_path / "terrasketch_output.puml", show_labels=show_labels)
    else:
        logger.info("draw.ioダイアグラムをレンダリング中...")
        renderer = DrawioRenderer()
        result = renderer.render(graph, positions, output_path / "terrasketch_output.drawio", show_labels=show_labels)

    logger.info("構成図を保存しました: %s", result)
    return result


def _setup_logging(verbose: bool = False) -> None:
    """ロギングの基本設定を行う。"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )


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
        "--state", help="Terraform state JSONファイルのパス"
    )
    gen_parser.add_argument(
        "--hcl", help="Terraform HCLファイルまたはディレクトリのパス"
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
        choices=["drawio", "mermaid", "plantuml"],
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

    gen_parser.add_argument(
        "--labels",
        action="store_true",
        help="エッジに接続属性名（vpc_id等）のラベルを表示",
    )

    gen_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="デバッグレベルの詳細ログを表示",
    )

    # guiコマンド
    subparsers.add_parser("gui", help="GUIを起動")

    args = parser.parse_args()

    _setup_logging(getattr(args, "verbose", False))

    if args.command == "generate":
        if not args.state and not args.hcl:
            gen_parser.error("--state または --hcl のいずれかを指定してください。")
        generate(
            state_path=args.state,
            provider=args.provider,
            output_dir=args.output,
            output_format=args.format,
            show_security=args.security,
            show_summary=args.summary,
            hcl_path=args.hcl,
            show_labels=args.labels,
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
