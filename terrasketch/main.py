"""TerraSketch CLIおよびGUIエントリーポイント。

使用方法:
    # CLIモード
    terrasketch generate --state state.json --provider aws
    terrasketch generate --state state.json --provider aws --format mermaid
    terrasketch generate --state state.json --provider aws --security --summary

    # diffモード
    terrasketch diff --before old_state.json --after new_state.json

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
from terrasketch.renderer.svg_renderer import SvgRenderer


def generate(
    state_path: str | None,
    provider: str,
    output_dir: str,
    output_format: str = "drawio",
    show_security: bool = False,
    show_summary: bool = False,
    hcl_path: str | None = None,
    show_labels: bool = False,
    layout_type: str = "hierarchical",
    group_by: str | None = None,
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
        layout_type: レイアウトアルゴリズム（'hierarchical', 'grid', 'force'）。
        group_by: グルーピング方法（'module' またはNone）。

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

    logger.info("レイアウトを計算中（%s）...", layout_type)
    positions = calculate_layout(graph, layout_type=layout_type)

    output_path = Path(output_dir)

    group_by_module = group_by == "module"

    if output_format == "mermaid":
        logger.info("Mermaidダイアグラムをレンダリング中...")
        renderer = MermaidRenderer()
        result = renderer.render(graph, positions, output_path / "terrasketch_output.md", show_labels=show_labels, group_by_module=group_by_module)
    elif output_format == "plantuml":
        logger.info("PlantUMLダイアグラムをレンダリング中...")
        renderer = PlantUMLRenderer()
        result = renderer.render(graph, positions, output_path / "terrasketch_output.puml", show_labels=show_labels, group_by_module=group_by_module)
    elif output_format == "svg":
        logger.info("SVGダイアグラムをレンダリング中...")
        svg_renderer = SvgRenderer()
        result = svg_renderer.render(graph, positions, output_path / "terrasketch_output.svg", show_labels=show_labels, group_by_module=group_by_module)
    else:
        logger.info("draw.ioダイアグラムをレンダリング中...")
        renderer = DrawioRenderer()
        result = renderer.render(graph, positions, output_path / "terrasketch_output.drawio", show_labels=show_labels, group_by_module=group_by_module)

    logger.info("構成図を保存しました: %s", result)
    return result


def diff_generate(
    before_path: str,
    after_path: str,
    provider: str,
    output_dir: str,
    output_format: str = "drawio",
) -> Path:
    """2つのstateを比較し、差分を色分けした構成図を生成する。

    Args:
        before_path: 変更前のstate JSONファイルパス。
        after_path: 変更後のstate JSONファイルパス。
        provider: クラウドプロバイダフィルタ。
        output_dir: 出力ディレクトリ。
        output_format: 出力形式。

    Returns:
        生成されたファイルのPath。
    """
    from terrasketch.diff.comparator import build_diff_graph, compare_states

    logger.info("diff比較を実行中: %s → %s", before_path, after_path)
    resources, diff_status, changed_attrs = compare_states(before_path, after_path)

    # プロバイダフィルタ
    prefix_map = {"aws": "aws_", "azure": "azurerm_"}
    prefix = prefix_map.get(provider, "")
    if prefix:
        resources = [r for r in resources if r.type.startswith(prefix)]
        # diff_statusもフィルタ
        filtered_addrs = {r.address for r in resources}
        diff_status = {k: v for k, v in diff_status.items() if k in filtered_addrs}
        changed_attrs = {k: v for k, v in changed_attrs.items() if k in filtered_addrs}

    logger.info("diff対象リソース: %d件", len(resources))

    graph = build_diff_graph(resources, diff_status, changed_attrs)
    logger.info("diffグラフ: %dノード, %dエッジ", graph.number_of_nodes(), graph.number_of_edges())

    # diff統計をログ出力
    from terrasketch.diff.comparator import DiffStatus
    added = sum(1 for s in diff_status.values() if s == DiffStatus.ADDED)
    removed = sum(1 for s in diff_status.values() if s == DiffStatus.REMOVED)
    modified = sum(1 for s in diff_status.values() if s == DiffStatus.MODIFIED)
    logger.info("変更サマリー: 追加=%d, 削除=%d, 変更=%d", added, removed, modified)

    positions = calculate_layout(graph)
    output_path = Path(output_dir)

    if output_format == "mermaid":
        renderer = MermaidRenderer()
        result = renderer.render(graph, positions, output_path / "terrasketch_diff.md", diff_mode=True)
    elif output_format == "plantuml":
        renderer = PlantUMLRenderer()
        result = renderer.render(graph, positions, output_path / "terrasketch_diff.puml", diff_mode=True)
    else:
        renderer = DrawioRenderer()
        result = renderer.render(graph, positions, output_path / "terrasketch_diff.drawio", diff_mode=True)

    logger.info("diff構成図を保存しました: %s", result)
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
        choices=["drawio", "mermaid", "plantuml", "svg"],
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
        "--layout",
        choices=["hierarchical", "grid", "force"],
        default="hierarchical",
        help="レイアウトアルゴリズム（デフォルト: hierarchical）",
    )
    gen_parser.add_argument(
        "--group-by",
        choices=["module"],
        default=None,
        help="リソースのグルーピング方法（module: モジュール境界でグループ化）",
    )

    gen_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="デバッグレベルの詳細ログを表示",
    )

    # diffコマンド
    diff_parser = subparsers.add_parser(
        "diff", help="2つのTerraform stateを比較し、構成変更を可視化"
    )
    diff_parser.add_argument(
        "--before", required=True, help="変更前のstate JSONファイルのパス"
    )
    diff_parser.add_argument(
        "--after", required=True, help="変更後のstate JSONファイルのパス"
    )
    diff_parser.add_argument(
        "--provider",
        choices=["aws", "azure"],
        default="aws",
        help="クラウドプロバイダ（デフォルト: aws）",
    )
    diff_parser.add_argument(
        "--output",
        default=".",
        help="出力ディレクトリ（デフォルト: カレントディレクトリ）",
    )
    diff_parser.add_argument(
        "--format",
        choices=["drawio", "mermaid", "plantuml", "svg"],
        default="drawio",
        help="出力形式（デフォルト: drawio）",
    )
    diff_parser.add_argument(
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
            layout_type=args.layout,
            group_by=args.group_by,
        )
    elif args.command == "diff":
        diff_generate(
            before_path=args.before,
            after_path=args.after,
            provider=args.provider,
            output_dir=args.output,
            output_format=args.format,
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
