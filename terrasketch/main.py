"""TerraSketch CLIおよびGUIエントリーポイント。

使用方法:
    # CLIモード
    terrasketch generate --state state.json --provider aws
    terrasketch generate --state state.json --provider aws --format mermaid
    terrasketch generate --state state.json --provider aws --security --summary

    # diffモード
    terrasketch diff --before old_state.json --after new_state.json

    # watchモード
    terrasketch watch --state state.json --output ./output

    # Web UIモード
    terrasketch serve --port 8080

    # Terraform Cloud連携
    terrasketch tfc --workspace org/workspace --provider aws

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
from terrasketch.renderer.html_renderer import HtmlRenderer
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
    theme: str | None = None,
    cost_path: str | None = None,
    runtime: str = "auto",
    *,
    _resources_override: list | None = None,
) -> Path:
    """構成図生成パイプライン全体を実行する。

    Args:
        state_path: Terraform state JSONファイルのパス。
        provider: クラウドプロバイダフィルタ（'aws' または 'azure'）。
        output_dir: 出力ファイルを書き出すディレクトリ。
        output_format: 出力形式（'drawio'、'mermaid'、'plantuml'、'svg'）。
        show_security: セキュリティグループルールの注釈を付与するか。
        show_summary: リソースサマリーを標準出力に表示するか。
        hcl_path: Terraform HCLファイルまたはディレクトリのパス。
        show_labels: エッジに接続属性名ラベルを表示するか。
        layout_type: レイアウトアルゴリズム（'hierarchical', 'grid', 'force'）。
        group_by: グルーピング方法（'module' またはNone）。
        theme: テーマ名またはテーマファイルのパス。

    Returns:
        生成された出力ファイルのPath。
    """
    # テーマの適用
    if theme:
        from terrasketch.config.theme import load_theme
        load_theme(theme)

    # プラグインの発見
    from terrasketch.plugins import discover_plugins
    discover_plugins()

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
        resources = parse_state(state_path, runtime=runtime)
    logger.info("%d件のリソースを検出。", len(resources))

    # プロバイダでフィルタリング
    prefix_map = {"aws": "aws_", "azure": "azurerm_", "gcp": "google_", "kubernetes": "kubernetes_"}
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

    # コスト注釈
    if cost_path:
        from terrasketch.cost.annotator import annotate_costs, parse_infracost
        logger.info("infracostデータを読み込み中: %s", cost_path)
        cost_map = parse_infracost(cost_path)
        annotate_costs(graph, cost_map)
        logger.info("コスト注釈を %d リソースに適用。", sum(1 for n in graph.nodes if "cost_label" in graph.nodes[n]))

    if show_security:
        logger.info("セキュリティグループルールを注釈中...")
        annotate_security_rules(graph)

    if show_summary:
        summary = generate_summary(resources, graph)
        print(summary)

    logger.info("レイアウトを計算中（%s）...", layout_type)
    positions = calculate_layout(graph, layout_type=layout_type)

    output_path = Path(output_dir)

    # グルーピング設定の解析
    from terrasketch.graph.grouping import build_tag_group_map, parse_group_by
    group_type, tag_key = parse_group_by(group_by)
    group_by_module = group_type == "module"
    tag_groups: dict[str, list[str]] | None = None
    if group_type == "tag" and tag_key:
        tag_groups = build_tag_group_map(resources, tag_key)
        logger.info("タグ '%s' で %d グループに分類。", tag_key, len(tag_groups))

    # プラグインレンダラーの確認
    from terrasketch.plugins import get_renderer
    plugin_renderer_class = get_renderer(output_format)

    if plugin_renderer_class:
        logger.info("プラグインレンダラーを使用: %s", output_format)
        renderer = plugin_renderer_class()
        result = renderer.render(graph, positions, output_path / f"terrasketch_output.{output_format}", show_labels=show_labels, group_by_module=group_by_module, tag_groups=tag_groups)
    elif output_format == "mermaid":
        logger.info("Mermaidダイアグラムをレンダリング中...")
        renderer = MermaidRenderer()
        result = renderer.render(graph, positions, output_path / "terrasketch_output.md", show_labels=show_labels, group_by_module=group_by_module, tag_groups=tag_groups)
    elif output_format == "plantuml":
        logger.info("PlantUMLダイアグラムをレンダリング中...")
        renderer = PlantUMLRenderer()
        result = renderer.render(graph, positions, output_path / "terrasketch_output.puml", show_labels=show_labels, group_by_module=group_by_module, tag_groups=tag_groups)
    elif output_format == "svg":
        logger.info("SVGダイアグラムをレンダリング中...")
        svg_renderer = SvgRenderer()
        result = svg_renderer.render(graph, positions, output_path / "terrasketch_output.svg", show_labels=show_labels, group_by_module=group_by_module, tag_groups=tag_groups)
    elif output_format == "html":
        logger.info("インタラクティブHTMLをレンダリング中...")
        html_renderer = HtmlRenderer()
        result = html_renderer.render(graph, positions, output_path / "terrasketch_output.html", show_labels=show_labels, group_by_module=group_by_module, tag_groups=tag_groups)
    else:
        logger.info("draw.ioダイアグラムをレンダリング中...")
        renderer = DrawioRenderer()
        result = renderer.render(graph, positions, output_path / "terrasketch_output.drawio", show_labels=show_labels, group_by_module=group_by_module, tag_groups=tag_groups)

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
    prefix_map = {"aws": "aws_", "azure": "azurerm_", "gcp": "google_", "kubernetes": "kubernetes_"}
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
    elif output_format == "svg":
        svg_renderer = SvgRenderer()
        result = svg_renderer.render(graph, positions, output_path / "terrasketch_diff.svg", diff_mode=True)
    elif output_format == "html":
        html_renderer = HtmlRenderer()
        result = html_renderer.render(graph, positions, output_path / "terrasketch_diff.html", diff_mode=True)
    else:
        renderer = DrawioRenderer()
        result = renderer.render(graph, positions, output_path / "terrasketch_diff.drawio", diff_mode=True)

    logger.info("diff構成図を保存しました: %s", result)
    return result


def plan_generate(
    plan_path: str,
    provider: str,
    output_dir: str,
    output_format: str = "drawio",
) -> Path:
    """Terraform planファイルから変更予測の構成図を生成する。

    Args:
        plan_path: Terraform plan JSONファイルパス。
        provider: クラウドプロバイダフィルタ。
        output_dir: 出力ディレクトリ。
        output_format: 出力形式。

    Returns:
        生成されたファイルのPath。
    """
    from terrasketch.diff.comparator import build_diff_graph
    from terrasketch.parser.plan_parser import parse_plan

    logger.info("planファイルを解析中: %s", plan_path)
    resources, diff_status, changed_attrs = parse_plan(plan_path)

    # プロバイダフィルタ
    prefix_map = {"aws": "aws_", "azure": "azurerm_", "gcp": "google_", "kubernetes": "kubernetes_"}
    prefix = prefix_map.get(provider, "")
    if prefix:
        resources = [r for r in resources if r.type.startswith(prefix)]
        filtered_addrs = {r.address for r in resources}
        diff_status = {k: v for k, v in diff_status.items() if k in filtered_addrs}
        changed_attrs = {k: v for k, v in changed_attrs.items() if k in filtered_addrs}

    logger.info("plan対象リソース: %d件", len(resources))

    graph = build_diff_graph(resources, diff_status, changed_attrs)
    logger.info("planグラフ: %dノード, %dエッジ", graph.number_of_nodes(), graph.number_of_edges())

    # plan統計をログ出力
    from terrasketch.diff.comparator import DiffStatus
    added = sum(1 for s in diff_status.values() if s == DiffStatus.ADDED)
    removed = sum(1 for s in diff_status.values() if s == DiffStatus.REMOVED)
    modified = sum(1 for s in diff_status.values() if s == DiffStatus.MODIFIED)
    logger.info("plan変更サマリー: 追加=%d, 削除=%d, 変更=%d", added, removed, modified)

    positions = calculate_layout(graph)
    output_path = Path(output_dir)

    if output_format == "mermaid":
        renderer = MermaidRenderer()
        result = renderer.render(graph, positions, output_path / "terrasketch_plan.md", diff_mode=True)
    elif output_format == "plantuml":
        renderer = PlantUMLRenderer()
        result = renderer.render(graph, positions, output_path / "terrasketch_plan.puml", diff_mode=True)
    elif output_format == "svg":
        svg_renderer = SvgRenderer()
        result = svg_renderer.render(graph, positions, output_path / "terrasketch_plan.svg", diff_mode=True)
    elif output_format == "html":
        html_renderer = HtmlRenderer()
        result = html_renderer.render(graph, positions, output_path / "terrasketch_plan.html", diff_mode=True)
    else:
        renderer = DrawioRenderer()
        result = renderer.render(graph, positions, output_path / "terrasketch_plan.drawio", diff_mode=True)

    logger.info("plan構成図を保存しました: %s", result)
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
        description="TerraSketch - Terraform stateを唯一の信頼源としてAWS/Azure/GCPの構成図を自動生成",
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
        choices=["aws", "azure", "gcp", "kubernetes", "all"],
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
        choices=["drawio", "mermaid", "plantuml", "svg", "html"],
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
        default=None,
        help="リソースのグルーピング方法（module: モジュール境界、tag:<key>: タグ値でグループ化）",
    )
    gen_parser.add_argument(
        "--theme",
        default=None,
        help="テーマ名（default/light/dark）またはテーマファイルのパス",
    )
    gen_parser.add_argument(
        "--cost",
        default=None,
        help="infracost JSON出力ファイルのパス（ノードにコスト注釈を表示）",
    )

    gen_parser.add_argument(
        "--runtime",
        choices=["terraform", "opentofu", "auto"],
        default="auto",
        help="ランタイム指定（auto: 自動検出、terraform: Terraform、opentofu: OpenTofu）",
    )
    gen_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="デバッグレベルの詳細ログを表示",
    )

    # validateコマンド
    validate_parser = subparsers.add_parser(
        "validate", help="入力ファイルの形式を事前検証"
    )
    validate_parser.add_argument(
        "--state", help="検証するTerraform state JSONファイルのパス"
    )
    validate_parser.add_argument(
        "--hcl", help="検証するTerraform HCLファイルまたはディレクトリのパス"
    )
    validate_parser.add_argument(
        "--plan", help="検証するTerraform plan JSONファイルのパス"
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
        choices=["aws", "azure", "gcp", "kubernetes", "all"],
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
        choices=["drawio", "mermaid", "plantuml", "svg", "html"],
        default="drawio",
        help="出力形式（デフォルト: drawio）",
    )
    diff_parser.add_argument(
        "--runtime",
        choices=["terraform", "opentofu", "auto"],
        default="auto",
        help="ランタイム指定（auto: 自動検出、terraform: Terraform、opentofu: OpenTofu）",
    )
    diff_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="デバッグレベルの詳細ログを表示",
    )

    # planコマンド
    plan_parser = subparsers.add_parser(
        "plan", help="Terraform planファイルから変更予測の構成図を生成"
    )
    plan_parser.add_argument(
        "--plan", required=True, help="Terraform plan JSON���ァイルのパス（terraform show -json <planfile>）"
    )
    plan_parser.add_argument(
        "--provider",
        choices=["aws", "azure", "gcp", "kubernetes", "all"],
        default="aws",
        help="クラウドプロバイダ（デフォルト: aws）",
    )
    plan_parser.add_argument(
        "--output",
        default=".",
        help="出力ディレクトリ（デフォルト: カレントディレクトリ）",
    )
    plan_parser.add_argument(
        "--format",
        choices=["drawio", "mermaid", "plantuml", "svg", "html"],
        default="drawio",
        help="出力形式（デフォルト: drawio）",
    )
    plan_parser.add_argument(
        "--runtime",
        choices=["terraform", "opentofu", "auto"],
        default="auto",
        help="ランタイム指定（auto: 自動検出、terraform: Terraform、opentofu: OpenTofu）",
    )
    plan_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="デバッグレベルの詳細ログを表示",
    )

    # watchコマンド
    watch_parser = subparsers.add_parser(
        "watch", help="ファイル変更を監視し構成図を自動再生成"
    )
    watch_parser.add_argument(
        "--state", help="Terraform state JSONファイルのパス"
    )
    watch_parser.add_argument(
        "--hcl", help="Terraform HCLファイルまたはディレクトリのパス"
    )
    watch_parser.add_argument(
        "--provider",
        choices=["aws", "azure", "gcp", "kubernetes", "all"],
        default="aws",
        help="クラウドプロバイダ（デフォルト: aws）",
    )
    watch_parser.add_argument(
        "--output",
        default="./output",
        help="出力ディレクトリ（デフォルト: ./output）",
    )
    watch_parser.add_argument(
        "--format",
        choices=["drawio", "mermaid", "plantuml", "svg", "html"],
        default="drawio",
        help="出力形式（デフォルト: drawio）",
    )
    watch_parser.add_argument(
        "--labels",
        action="store_true",
        help="エッジラベルを表示",
    )
    watch_parser.add_argument(
        "--layout",
        choices=["hierarchical", "grid", "force"],
        default="hierarchical",
        help="レイアウトアルゴリズム",
    )
    watch_parser.add_argument(
        "--group-by",
        default=None,
        help="リソースのグルーピング方法（module: モジュール境界、tag:<key>: タグ値でグループ化）",
    )
    watch_parser.add_argument(
        "--runtime",
        choices=["terraform", "opentofu", "auto"],
        default="auto",
        help="ランタイム指定（auto: 自動検出、terraform: Terraform、opentofu: OpenTofu）",
    )
    watch_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="デバッグレベルの詳細ログを表示",
    )

    # serveコマンド
    serve_parser = subparsers.add_parser(
        "serve", help="Web UIをブラウザで起動"
    )
    serve_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="バインドするホスト名（デフォルト: 127.0.0.1）",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="ポート番号（デフォルト: 8080）",
    )
    serve_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="デバッグレベルの詳細ログを表示",
    )

    # tfcコマンド
    tfc_parser = subparsers.add_parser(
        "tfc", help="Terraform Cloud/Enterpriseからstateを取得し構成図を生成"
    )
    tfc_parser.add_argument(
        "--workspace", required=True,
        help="ワークスペース指定（<org>/<workspace>形式）",
    )
    tfc_parser.add_argument(
        "--tfc-token",
        default=None,
        help="Terraform Cloud APIトークン（環境変数TFC_TOKENでも指定可）",
    )
    tfc_parser.add_argument(
        "--tfc-url",
        default=None,
        help="Terraform Enterprise APIベースURL",
    )
    tfc_parser.add_argument(
        "--provider",
        choices=["aws", "azure", "gcp", "kubernetes", "all"],
        default="aws",
        help="クラウドプロバイダ（デフォルト: aws）",
    )
    tfc_parser.add_argument(
        "--output",
        default=".",
        help="出力ディレクトリ（デフォルト: カレントディレクトリ）",
    )
    tfc_parser.add_argument(
        "--format",
        choices=["drawio", "mermaid", "plantuml", "svg", "html"],
        default="drawio",
        help="出力形式（デフォルト: drawio）",
    )
    tfc_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="デバッグレベルの詳細ログを表示",
    )

    # guiコマンド
    subparsers.add_parser("gui", help="GUIを起動")

    args = parser.parse_args()

    _setup_logging(getattr(args, "verbose", False))

    if args.command == "validate":
        from terrasketch.parser.validator import (
            format_validation_result,
            validate_hcl_file,
            validate_plan_file,
            validate_state_file,
        )

        if not args.state and not args.hcl and not args.plan:
            validate_parser.error("--state、--hcl、--plan のいずれかを指定してください。")
        if args.state:
            result = validate_state_file(args.state)
            print(format_validation_result(result))
            if not result.valid:
                sys.exit(1)
        if args.hcl:
            result = validate_hcl_file(args.hcl)
            print(format_validation_result(result))
            if not result.valid:
                sys.exit(1)
        if args.plan:
            result = validate_plan_file(args.plan)
            print(format_validation_result(result))
            if not result.valid:
                sys.exit(1)
        return

    if args.command == "generate":
        if not args.state and not args.hcl:
            gen_parser.error("--state または --hcl のいずれかを指定してください。")

        # 入力ファイルの事前検証
        from terrasketch.parser.validator import (
            format_validation_result,
            validate_hcl_file,
            validate_state_file,
        )

        if args.state:
            vr = validate_state_file(args.state)
            if not vr.valid:
                print(format_validation_result(vr), file=sys.stderr)
                sys.exit(1)
        if args.hcl:
            vr = validate_hcl_file(args.hcl)
            if not vr.valid:
                print(format_validation_result(vr), file=sys.stderr)
                sys.exit(1)

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
            theme=args.theme,
            cost_path=getattr(args, "cost", None),
            runtime=args.runtime,
        )
    elif args.command == "diff":
        diff_generate(
            before_path=args.before,
            after_path=args.after,
            provider=args.provider,
            output_dir=args.output,
            output_format=args.format,
        )
    elif args.command == "plan":
        # 入力ファイルの事前検証
        from terrasketch.parser.validator import (
            format_validation_result,
            validate_plan_file,
        )
        vr = validate_plan_file(args.plan)
        if not vr.valid:
            print(format_validation_result(vr), file=sys.stderr)
            sys.exit(1)

        plan_generate(
            plan_path=args.plan,
            provider=args.provider,
            output_dir=args.output,
            output_format=args.format,
        )
    elif args.command == "watch":
        if not args.state and not args.hcl:
            watch_parser.error("--state または --hcl のいずれかを指定してください。")
        from terrasketch.watch.watcher import watch_and_generate
        watch_and_generate(
            state_path=args.state,
            hcl_path=args.hcl,
            provider=args.provider,
            output_dir=args.output,
            output_format=args.format,
            show_labels=args.labels,
            layout_type=args.layout,
            group_by=args.group_by,
        )
    elif args.command == "serve":
        from terrasketch.web.server import start_server
        start_server(host=args.host, port=args.port)
    elif args.command == "tfc":
        from terrasketch.remote.tfc_client import fetch_and_generate
        fetch_and_generate(
            workspace_spec=args.workspace,
            token=args.tfc_token,
            provider=args.provider,
            output_dir=args.output,
            output_format=args.format,
            base_url=args.tfc_url,
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
