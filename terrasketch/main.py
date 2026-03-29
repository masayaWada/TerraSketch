"""TerraSketch CLI and GUI entry point.

Usage:
    # CLI mode
    terrasketch generate --state state.json --provider aws
    terrasketch generate --state state.json --provider aws --format mermaid
    terrasketch generate --state state.json --provider aws --security --summary

    # GUI mode
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
    """Run the full diagram generation pipeline.

    Args:
        state_path: Path to the Terraform state JSON file.
        provider: Cloud provider filter ('aws' or 'azure').
        output_dir: Directory to write the output file.
        output_format: Output format ('drawio' or 'mermaid').
        show_security: Whether to annotate security group rules.
        show_summary: Whether to print a resource summary.

    Returns:
        Path to the generated output file.
    """
    print(f"[INFO] Parsing state file: {state_path}")
    resources = parse_state(state_path)
    print(f"[INFO] Found {len(resources)} resources.")

    # Filter by provider
    prefix_map = {"aws": "aws_", "azure": "azurerm_"}
    prefix = prefix_map.get(provider, "")
    if prefix:
        resources = [r for r in resources if r.type.startswith(prefix)]
        print(f"[INFO] Filtered to {len(resources)} {provider.upper()} resources.")

    if not resources:
        print("[WARN] No matching resources found. Output will be empty.")

    print("[INFO] Building dependency graph...")
    graph = build_graph(resources)
    print(
        f"[INFO] Graph: {graph.number_of_nodes()} nodes, "
        f"{graph.number_of_edges()} edges."
    )

    if show_security:
        print("[INFO] Annotating security group rules...")
        annotate_security_rules(graph)

    if show_summary:
        summary = generate_summary(resources, graph)
        print(summary)

    print("[INFO] Calculating layout...")
    positions = calculate_layout(graph)

    output_path = Path(output_dir)

    if output_format == "mermaid":
        print("[INFO] Rendering Mermaid diagram...")
        renderer = MermaidRenderer()
        result = renderer.render(graph, positions, output_path / "terrasketch_output.md")
    else:
        print("[INFO] Rendering draw.io diagram...")
        renderer = DrawioRenderer()
        result = renderer.render(graph, positions, output_path / "terrasketch_output.drawio")

    print(f"[SUCCESS] Diagram saved to: {result}")
    return result


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="terrasketch",
        description="TerraSketch - Generate draw.io diagrams from Terraform state",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # generate command
    gen_parser = subparsers.add_parser(
        "generate", help="Generate a diagram from a Terraform state file"
    )
    gen_parser.add_argument(
        "--state", required=True, help="Path to the Terraform state JSON file"
    )
    gen_parser.add_argument(
        "--provider",
        choices=["aws", "azure"],
        default="aws",
        help="Cloud provider (default: aws)",
    )
    gen_parser.add_argument(
        "--output",
        default=".",
        help="Output directory (default: current directory)",
    )
    gen_parser.add_argument(
        "--format",
        choices=["drawio", "mermaid"],
        default="drawio",
        help="Output format (default: drawio)",
    )
    gen_parser.add_argument(
        "--security",
        action="store_true",
        help="Annotate security group rules on the diagram",
    )
    gen_parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a resource summary to stdout",
    )

    # gui command
    subparsers.add_parser("gui", help="Launch the graphical user interface")

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
