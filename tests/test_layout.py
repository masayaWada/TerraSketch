"""Tests for the layout engine."""

import networkx as nx
import pytest

from terrasketch.layout.engine import calculate_layout
from terrasketch.parser.state_parser import Resource


def test_empty_graph():
    graph = nx.DiGraph()
    positions = calculate_layout(graph)
    assert positions == {}


def test_single_node():
    graph = nx.DiGraph()
    graph.add_node("a")
    positions = calculate_layout(graph)
    assert "a" in positions
    assert len(positions["a"]) == 2


def test_hierarchical_layout():
    graph = nx.DiGraph()
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")
    positions = calculate_layout(graph)

    # Each node should have a position
    assert len(positions) == 3
    # Hierarchical: a should be above b, b above c (lower y = higher)
    assert positions["a"][1] < positions["b"][1]
    assert positions["b"][1] < positions["c"][1]


def test_no_negative_coordinates():
    graph = nx.DiGraph()
    graph.add_edge("a", "b")
    graph.add_edge("a", "c")
    graph.add_edge("a", "d")
    positions = calculate_layout(graph)
    for node, (x, y) in positions.items():
        assert x >= 0, f"Node {node} has negative x: {x}"
        assert y >= 0, f"Node {node} has negative y: {y}"


def test_spring_layout_fallback():
    """Cyclic graph triggers spring layout."""
    graph = nx.DiGraph()
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")
    graph.add_edge("c", "a")
    positions = calculate_layout(graph)
    assert len(positions) == 3
