"""Integration test: full pipeline from sample state to output."""

from pathlib import Path

from terrasketch.graph.builder import build_graph
from terrasketch.graph.security import annotate_security_rules
from terrasketch.layout.engine import calculate_layout
from terrasketch.parser.state_parser import parse_state
from terrasketch.renderer.drawio_renderer import DrawioRenderer
from terrasketch.renderer.mermaid_renderer import MermaidRenderer


SAMPLE_STATE = Path(__file__).parent.parent / "samples" / "sample_state.json"


def test_full_pipeline_drawio(tmp_path):
    resources = parse_state(SAMPLE_STATE)
    assert len(resources) == 6

    graph = build_graph(resources)
    assert graph.number_of_nodes() == 6
    assert graph.number_of_edges() > 0

    annotate_security_rules(graph)

    positions = calculate_layout(graph)
    assert len(positions) == 6

    renderer = DrawioRenderer()
    output = renderer.render(graph, positions, tmp_path / "out.drawio")
    assert output.exists()
    content = output.read_text(encoding="utf-8")
    assert "mxfile" in content
    assert "aws_vpc" in content


def test_full_pipeline_mermaid(tmp_path):
    resources = parse_state(SAMPLE_STATE)
    graph = build_graph(resources)
    positions = calculate_layout(graph)

    renderer = MermaidRenderer()
    output = renderer.render(graph, positions, tmp_path / "out.md")
    assert output.exists()
    content = output.read_text(encoding="utf-8")
    assert "flowchart TD" in content
    assert "-->" in content


def test_provider_filtering(tmp_path):
    resources = parse_state(SAMPLE_STATE)
    aws_only = [r for r in resources if r.type.startswith("aws_")]
    assert len(aws_only) == len(resources)  # sample is all AWS

    graph = build_graph(aws_only)
    positions = calculate_layout(graph)
    renderer = DrawioRenderer()
    output = renderer.render(graph, positions, tmp_path / "filtered.drawio")
    assert output.exists()
