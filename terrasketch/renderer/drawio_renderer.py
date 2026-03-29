"""draw.io XML renderer.

Generates a draw.io-compatible XML file (.drawio) from the resource graph
and layout positions. The generated file can be opened directly in
draw.io (diagrams.net) or consumed by a draw.io MCP server.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import networkx as nx

from terrasketch.mapping.resource_map import DrawioStyle, get_drawio_style
from terrasketch.parser.state_parser import Resource


class DrawioRenderer:
    """Renders a Terraform resource graph as a draw.io XML file."""

    def __init__(self) -> None:
        self._cell_id_counter = 2  # 0 and 1 reserved by draw.io

    def _next_id(self) -> str:
        cid = str(self._cell_id_counter)
        self._cell_id_counter += 1
        return cid

    def create_node(
        self,
        parent: ET.Element,
        node_id: str,
        label: str,
        style: DrawioStyle,
        x: float,
        y: float,
    ) -> ET.Element:
        """Create a draw.io node (mxCell) element.

        Args:
            parent: Parent XML element to attach the cell to.
            node_id: Unique cell ID.
            label: Display label for the node.
            style: DrawioStyle with visual properties.
            x: X coordinate.
            y: Y coordinate.

        Returns:
            The created mxCell element.
        """
        cell = ET.SubElement(parent, "mxCell")
        cell.set("id", node_id)
        cell.set("value", label)
        cell.set("style", style.style)
        cell.set("vertex", "1")
        cell.set("parent", "1")

        geo = ET.SubElement(cell, "mxGeometry")
        geo.set("x", str(round(x)))
        geo.set("y", str(round(y)))
        geo.set("width", str(round(style.width)))
        geo.set("height", str(round(style.height)))
        geo.set("as", "geometry")

        return cell

    def create_edge(
        self,
        parent: ET.Element,
        edge_id: str,
        source_id: str,
        target_id: str,
    ) -> ET.Element:
        """Create a draw.io edge (mxCell) element.

        Args:
            parent: Parent XML element to attach the cell to.
            edge_id: Unique cell ID for the edge.
            source_id: Source node cell ID.
            target_id: Target node cell ID.

        Returns:
            The created mxCell edge element.
        """
        cell = ET.SubElement(parent, "mxCell")
        cell.set("id", edge_id)
        cell.set("value", "")
        cell.set(
            "style",
            "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;"
            "jettySize=auto;html=1;strokeColor=#666666;strokeWidth=2;",
        )
        cell.set("edge", "1")
        cell.set("parent", "1")
        cell.set("source", source_id)
        cell.set("target", target_id)

        geo = ET.SubElement(cell, "mxGeometry")
        geo.set("relative", "1")
        geo.set("as", "geometry")

        return cell

    def render(
        self,
        graph: nx.DiGraph,
        positions: dict[str, tuple[float, float]],
        output_path: str | Path,
    ) -> Path:
        """Render the complete graph as a draw.io XML file.

        Args:
            graph: The resource dependency graph with node data.
            positions: Mapping of node address -> (x, y) coordinates.
            output_path: File path for the output .drawio file.

        Returns:
            Path to the written .drawio file.
        """
        output_path = Path(output_path)

        # Build XML structure
        mxfile = ET.Element("mxfile")
        mxfile.set("host", "terrasketch")
        mxfile.set("type", "device")

        diagram = ET.SubElement(mxfile, "diagram")
        diagram.set("id", "terrasketch-diagram")
        diagram.set("name", "TerraSketch")

        mx_graph_model = ET.SubElement(diagram, "mxGraphModel")
        mx_graph_model.set("dx", "1422")
        mx_graph_model.set("dy", "762")
        mx_graph_model.set("grid", "1")
        mx_graph_model.set("gridSize", "10")
        mx_graph_model.set("guides", "1")
        mx_graph_model.set("tooltips", "1")
        mx_graph_model.set("connect", "1")
        mx_graph_model.set("arrows", "1")
        mx_graph_model.set("fold", "1")
        mx_graph_model.set("page", "1")
        mx_graph_model.set("pageScale", "1")
        mx_graph_model.set("math", "0")
        mx_graph_model.set("shadow", "0")

        root = ET.SubElement(mx_graph_model, "root")

        # Required root cells for draw.io
        cell0 = ET.SubElement(root, "mxCell")
        cell0.set("id", "0")
        cell1 = ET.SubElement(root, "mxCell")
        cell1.set("id", "1")
        cell1.set("parent", "0")

        # Map node addresses to cell IDs
        node_cell_ids: dict[str, str] = {}

        # Create nodes
        for node_addr in graph.nodes:
            data = graph.nodes[node_addr]
            resource: Resource | None = data.get("resource")

            if resource is None:
                continue

            cell_id = self._next_id()
            node_cell_ids[node_addr] = cell_id

            style = get_drawio_style(resource.type)
            label = f"{resource.type}\n{resource.name}"
            x, y = positions.get(node_addr, (100.0, 100.0))

            self.create_node(root, cell_id, label, style, x, y)

        # Create edges
        for source, target in graph.edges:
            src_cell = node_cell_ids.get(source)
            tgt_cell = node_cell_ids.get(target)
            if src_cell and tgt_cell:
                edge_id = self._next_id()
                self.create_edge(root, edge_id, src_cell, tgt_cell)

        # Write to file
        tree = ET.ElementTree(mxfile)
        ET.indent(tree, space="  ")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tree.write(str(output_path), encoding="unicode", xml_declaration=True)

        return output_path
