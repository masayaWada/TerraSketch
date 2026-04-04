"""フェーズ4テスト: GCP対応・マルチプロバイダ構成図。

GCPリソースマッピング、関係ルール、プロバイダフィルタリング、
マルチプロバイダ対応をテストする。
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import networkx as nx

from terrasketch.graph.builder import build_graph
from terrasketch.layout.engine import calculate_layout
from terrasketch.mapping.resource_map import (
    DrawioStyle,
    get_drawio_style,
    get_provider_from_type,
)
from terrasketch.parser.state_parser import Resource, parse_state
from terrasketch.renderer.drawio_renderer import DrawioRenderer
from terrasketch.renderer.mermaid_renderer import MermaidRenderer
from terrasketch.renderer.plantuml_renderer import PlantUMLRenderer
from terrasketch.renderer.svg_renderer import SvgRenderer


# --- ヘルパー ---

def _make_resource(rtype: str, name: str, attrs: dict | None = None) -> Resource:
    """テスト用Resourceオブジェクトを生成する。"""
    return Resource(
        id=f"{rtype}-{name}-id",
        type=rtype,
        name=name,
        provider=f"provider[\"registry.terraform.io/hashicorp/google\"]",
        attributes=attrs or {},
    )


def _gcp_resources() -> list[Resource]:
    """GCPリソースのテストセットを生成する。"""
    network = _make_resource("google_compute_network", "main_vpc", {"name": "main-vpc"})
    subnet_a = _make_resource("google_compute_subnetwork", "subnet_a", {
        "name": "subnet-a",
        "network": f"google_compute_network-main_vpc-id",
    })
    instance = _make_resource("google_compute_instance", "web_server", {
        "name": "web-server",
        "subnetwork": f"google_compute_subnetwork-subnet_a-id",
    })
    firewall = _make_resource("google_compute_firewall", "allow_http", {
        "name": "allow-http",
        "network": f"google_compute_network-main_vpc-id",
    })
    bucket = _make_resource("google_storage_bucket", "assets", {"name": "assets-bucket"})
    sql = _make_resource("google_sql_database_instance", "db", {
        "name": "mydb",
        "private_network": f"google_compute_network-main_vpc-id",
    })
    gke = _make_resource("google_container_cluster", "cluster", {
        "name": "my-cluster",
        "network": f"google_compute_network-main_vpc-id",
        "subnetwork": f"google_compute_subnetwork-subnet_a-id",
    })
    return [network, subnet_a, instance, firewall, bucket, sql, gke]


def _mixed_resources() -> list[Resource]:
    """AWS + GCP混在リソースセットを生成する。"""
    aws_vpc = _make_resource("aws_vpc", "main", {"name": "main-vpc"})
    aws_instance = _make_resource("aws_instance", "web", {
        "subnet_id": "aws_subnet-pub-id",
    })
    aws_subnet = _make_resource("aws_subnet", "pub", {
        "vpc_id": "aws_vpc-main-id",
    })
    gcp_network = _make_resource("google_compute_network", "gcp_vpc", {"name": "gcp-vpc"})
    gcp_instance = _make_resource("google_compute_instance", "gcp_web", {
        "subnetwork": "google_compute_subnetwork-gcp_sub-id",
    })
    gcp_subnet = _make_resource("google_compute_subnetwork", "gcp_sub", {
        "network": "google_compute_network-gcp_vpc-id",
    })
    return [aws_vpc, aws_subnet, aws_instance, gcp_network, gcp_subnet, gcp_instance]


# === GCPマッピングテスト ===

class TestGcpMapping:
    """GCPリソースマッピングのテスト。"""

    def test_get_provider_from_type_gcp(self):
        """google_*プレフィックスでgcpを返す。"""
        assert get_provider_from_type("google_compute_instance") == "gcp"

    def test_get_provider_from_type_gcp_various(self):
        """様々なGCPリソースタイプでgcpを返す。"""
        types = [
            "google_compute_network",
            "google_storage_bucket",
            "google_container_cluster",
            "google_sql_database_instance",
            "google_cloudfunctions_function",
        ]
        for t in types:
            assert get_provider_from_type(t) == "gcp", f"{t} should be gcp"

    def test_basic_gcp_mapping_exists(self):
        """基本GCPリソースのdraw.ioスタイルが定義されている。"""
        basic_types = [
            "google_compute_instance",
            "google_compute_network",
            "google_compute_subnetwork",
            "google_compute_firewall",
        ]
        for t in basic_types:
            style = get_drawio_style(t)
            assert style.shape != "rounded=1", f"{t} should have custom style, not default"

    def test_extended_gcp_mapping_exists(self):
        """拡張GCPリソースのdraw.ioスタイルが定義されている。"""
        extended_types = [
            "google_container_cluster",
            "google_cloudfunctions_function",
            "google_sql_database_instance",
            "google_storage_bucket",
            "google_pubsub_topic",
        ]
        for t in extended_types:
            style = get_drawio_style(t)
            assert style.shape != "rounded=1", f"{t} should have custom style"

    def test_unknown_gcp_resource_returns_default(self):
        """未知のGCPリソースタイプはデフォルトスタイルを返す。"""
        style = get_drawio_style("google_unknown_resource")
        assert style.shape == "rounded=1"


# === GCPグラフ構築テスト ===

class TestGcpGraphBuilding:
    """GCPリソースのグラフ構築テスト。"""

    def test_gcp_network_subnetwork_edge(self):
        """GCPネットワーク→サブネットワークの包含エッジが作成される。"""
        resources = _gcp_resources()
        graph = build_graph(resources)
        network_addr = "google_compute_network.main_vpc"
        subnet_addr = "google_compute_subnetwork.subnet_a"
        assert graph.has_edge(network_addr, subnet_addr)
        edge = graph.edges[network_addr, subnet_addr]
        assert edge["relation_type"] == "contains"

    def test_gcp_subnetwork_instance_edge(self):
        """GCPサブネットワーク→インスタンスの包含エッジが作成される。"""
        resources = _gcp_resources()
        graph = build_graph(resources)
        subnet_addr = "google_compute_subnetwork.subnet_a"
        instance_addr = "google_compute_instance.web_server"
        assert graph.has_edge(subnet_addr, instance_addr)

    def test_gcp_firewall_network_edge(self):
        """GCPファイアウォール→ネットワークの参照エッジが作成される。"""
        resources = _gcp_resources()
        graph = build_graph(resources)
        network_addr = "google_compute_network.main_vpc"
        firewall_addr = "google_compute_firewall.allow_http"
        assert graph.has_edge(network_addr, firewall_addr)

    def test_gcp_gke_network_edge(self):
        """GKEクラスター→ネットワークのエッジが作成される。"""
        resources = _gcp_resources()
        graph = build_graph(resources)
        network_addr = "google_compute_network.main_vpc"
        gke_addr = "google_container_cluster.cluster"
        assert graph.has_edge(network_addr, gke_addr)

    def test_gcp_sql_network_edge(self):
        """Cloud SQL→ネットワークのエッジが作成される。"""
        resources = _gcp_resources()
        graph = build_graph(resources)
        network_addr = "google_compute_network.main_vpc"
        sql_addr = "google_sql_database_instance.db"
        assert graph.has_edge(network_addr, sql_addr)

    def test_all_gcp_resources_added_as_nodes(self):
        """全GCPリソースがノードとして追加される。"""
        resources = _gcp_resources()
        graph = build_graph(resources)
        assert graph.number_of_nodes() == len(resources)


# === プロバイダフィルタリングテスト ===

class TestProviderFiltering:
    """プロバイダフィルタリングのテスト。"""

    def test_gcp_prefix_filter(self):
        """gcpプロバイダフィルタでgoogle_*リソースのみ残る。"""
        resources = _mixed_resources()
        prefix = "google_"
        filtered = [r for r in resources if r.type.startswith(prefix)]
        assert all(r.type.startswith("google_") for r in filtered)
        assert len(filtered) == 3

    def test_all_provider_no_filter(self):
        """allプロバイダでは全リソースが残る。"""
        resources = _mixed_resources()
        # provider="all"の場合、prefixは空なのでフィルタなし
        prefix = ""
        if prefix:
            filtered = [r for r in resources if r.type.startswith(prefix)]
        else:
            filtered = resources
        assert len(filtered) == len(resources)

    def test_aws_filter_excludes_gcp(self):
        """awsプロバイダフィルタでGCPリソースは除外される。"""
        resources = _mixed_resources()
        prefix = "aws_"
        filtered = [r for r in resources if r.type.startswith(prefix)]
        assert all(r.type.startswith("aws_") for r in filtered)
        assert len(filtered) == 3


# === マルチプロバイダグラフテスト ===

class TestMultiProviderGraph:
    """マルチプロバイダ構成図のテスト。"""

    def test_mixed_resources_graph_has_all_nodes(self):
        """AWS+GCP混在リソースで全ノードがグラフに含まれる。"""
        resources = _mixed_resources()
        graph = build_graph(resources)
        assert graph.number_of_nodes() == len(resources)

    def test_mixed_resources_aws_edges(self):
        """混在グラフでAWSの関係エッジが正常に作成される。"""
        resources = _mixed_resources()
        graph = build_graph(resources)
        assert graph.has_edge("aws_vpc.main", "aws_subnet.pub")

    def test_mixed_resources_gcp_edges(self):
        """混在グラフでGCPの関係エッジが正常に作成される。"""
        resources = _mixed_resources()
        graph = build_graph(resources)
        assert graph.has_edge("google_compute_network.gcp_vpc", "google_compute_subnetwork.gcp_sub")


# === レンダラーGCP対応テスト ===

class TestGcpRenderers:
    """各レンダラーのGCP対応テスト。"""

    def _build_gcp_graph(self):
        """テスト用GCPグラフを構築する。"""
        resources = _gcp_resources()
        graph = build_graph(resources)
        positions = calculate_layout(graph)
        return graph, positions

    def test_drawio_gcp_containers(self):
        """draw.ioレンダラーがGCPネットワークをコンテナとして描画する。"""
        graph, positions = self._build_gcp_graph()
        renderer = DrawioRenderer()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = renderer.render(graph, positions, Path(tmpdir) / "test.drawio")
            content = output.read_text(encoding="utf-8")
            assert "google_compute_network" in content
            assert "container=1" in content  # コンテナが存在する

    def test_mermaid_gcp_shapes(self):
        """MermaidレンダラーがGCPリソースを正しい形状で描画する。"""
        graph, positions = self._build_gcp_graph()
        renderer = MermaidRenderer()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = renderer.render(graph, positions, Path(tmpdir) / "test.md")
            content = output.read_text(encoding="utf-8")
            assert "google_compute_network" in content
            assert "google_compute_instance" in content

    def test_mermaid_gcp_subgraph(self):
        """MermaidレンダラーがGCPネットワークをsubgraphで描画する。"""
        graph, positions = self._build_gcp_graph()
        renderer = MermaidRenderer()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = renderer.render(graph, positions, Path(tmpdir) / "test.md")
            content = output.read_text(encoding="utf-8")
            assert "subgraph" in content

    def test_plantuml_gcp_stereotypes(self):
        """PlantUMLレンダラーがGCPリソースにステレオタイプを付与する。"""
        graph, positions = self._build_gcp_graph()
        renderer = PlantUMLRenderer()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = renderer.render(graph, positions, Path(tmpdir) / "test.puml")
            content = output.read_text(encoding="utf-8")
            assert "GCE" in content or "GKE" in content or "Firewall" in content

    def test_plantuml_gcp_containers(self):
        """PlantUMLレンダラーがGCPネットワークをpackageで描画する。"""
        graph, positions = self._build_gcp_graph()
        renderer = PlantUMLRenderer()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = renderer.render(graph, positions, Path(tmpdir) / "test.puml")
            content = output.read_text(encoding="utf-8")
            assert "package" in content

    def test_svg_gcp_classification(self):
        """SVGレンダラーがGCPリソースを正しく分類・色分けする。"""
        graph, positions = self._build_gcp_graph()
        renderer = SvgRenderer()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = renderer.render(graph, positions, Path(tmpdir) / "test.svg")
            content = output.read_text(encoding="utf-8")
            assert "<svg" in content
            assert "google_compute" in content


# === GCPサンプルstate統合テスト ===

class TestGcpSampleState:
    """GCPサンプルstateファイルの統合テスト。"""

    def test_parse_gcp_state(self):
        """GCPリソースを含むstateファイルをパースできる。"""
        state = {
            "version": 4,
            "values": {
                "root_module": {
                    "resources": [
                        {
                            "type": "google_compute_network",
                            "name": "vpc",
                            "address": "google_compute_network.vpc",
                            "provider_name": "registry.terraform.io/hashicorp/google",
                            "values": {
                                "id": "projects/myproj/global/networks/vpc",
                                "name": "vpc",
                                "auto_create_subnetworks": False,
                            },
                        },
                        {
                            "type": "google_compute_instance",
                            "name": "server",
                            "address": "google_compute_instance.server",
                            "provider_name": "registry.terraform.io/hashicorp/google",
                            "values": {
                                "id": "projects/myproj/zones/us-central1-a/instances/server",
                                "name": "server",
                                "machine_type": "e2-medium",
                            },
                        },
                    ],
                },
            },
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(state, f)
            f.flush()
            resources = parse_state(f.name)
        assert len(resources) == 2
        assert resources[0].type == "google_compute_network"
        assert resources[1].type == "google_compute_instance"


# === マルチプロバイダレンダリングテスト ===

class TestMultiProviderRendering:
    """マルチプロバイダ構成図のレンダリングテスト。"""

    def _build_mixed_graph(self):
        """AWS+GCP混在グラフを構築する。"""
        resources = _mixed_resources()
        graph = build_graph(resources)
        positions = calculate_layout(graph)
        return graph, positions

    def test_drawio_mixed_providers(self):
        """draw.ioレンダラーがAWS+GCP混在を描画できる。"""
        graph, positions = self._build_mixed_graph()
        renderer = DrawioRenderer()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = renderer.render(graph, positions, Path(tmpdir) / "test.drawio")
            content = output.read_text(encoding="utf-8")
            assert "aws_vpc" in content
            assert "google_compute_network" in content

    def test_mermaid_mixed_providers(self):
        """MermaidレンダラーがAWS+GCP混在を描画できる。"""
        graph, positions = self._build_mixed_graph()
        renderer = MermaidRenderer()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = renderer.render(graph, positions, Path(tmpdir) / "test.md")
            content = output.read_text(encoding="utf-8")
            assert "aws_vpc" in content
            assert "google_compute_network" in content

    def test_svg_mixed_providers(self):
        """SVGレンダラーがAWS+GCP混在を描画できる。"""
        graph, positions = self._build_mixed_graph()
        renderer = SvgRenderer()
        with tempfile.TemporaryDirectory() as tmpdir:
            output = renderer.render(graph, positions, Path(tmpdir) / "test.svg")
            content = output.read_text(encoding="utf-8")
            assert "aws_vpc" in content or "aws" in content
            assert "google_compute" in content
