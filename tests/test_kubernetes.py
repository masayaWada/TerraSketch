"""Kubernetesリソース対応のテスト。"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import networkx as nx
import pytest

from terrasketch.graph.builder import build_graph
from terrasketch.mapping.resource_map import get_drawio_style, get_provider_from_type
from terrasketch.parser.state_parser import Resource


# --- ヘルパー ---


def _k8s_resource(
    name: str,
    rtype: str = "kubernetes_deployment",
    namespace_id: str = "app-ns",
    **extra_attrs: object,
) -> Resource:
    """テスト用Kubernetesリソースを生成する。"""
    attrs: dict = {
        "id": f"ns/{name}",
        "metadata": {"name": name, "namespace": namespace_id},
        **extra_attrs,
    }
    return Resource(
        id=f"ns/{name}",
        type=rtype,
        name=name,
        provider="registry.terraform.io/hashicorp/kubernetes",
        attributes=attrs,
    )


def _k8s_namespace(name: str = "app") -> Resource:
    """テスト用Kubernetes Namespaceリソースを生成する。"""
    return Resource(
        id=f"{name}-ns",
        type="kubernetes_namespace",
        name=name,
        provider="registry.terraform.io/hashicorp/kubernetes",
        attributes={
            "id": f"{name}-ns",
            "metadata": {"name": name},
        },
    )


# --- マッピングテスト ---


class TestK8sMapping:
    """Kubernetesリソースのdraw.ioマッピングテスト。"""

    @pytest.mark.parametrize("rtype", [
        "kubernetes_namespace",
        "kubernetes_namespace_v1",
        "kubernetes_deployment",
        "kubernetes_deployment_v1",
        "kubernetes_service",
        "kubernetes_service_v1",
        "kubernetes_ingress",
        "kubernetes_ingress_v1",
        "kubernetes_pod",
        "kubernetes_pod_v1",
        "kubernetes_stateful_set",
        "kubernetes_stateful_set_v1",
        "kubernetes_config_map",
        "kubernetes_config_map_v1",
        "kubernetes_secret",
        "kubernetes_secret_v1",
        "kubernetes_horizontal_pod_autoscaler",
    ])
    def test_k8s_resource_has_drawio_style(self, rtype: str) -> None:
        """K8sリソースタイプにdraw.ioスタイルがマッピングされている。"""
        style = get_drawio_style(rtype)
        assert style.shape != "rounded=1", f"{rtype} にスタイルが未定義"

    def test_provider_detection_kubernetes(self) -> None:
        """kubernetes_ プレフィックスが正しく検出される。"""
        assert get_provider_from_type("kubernetes_deployment") == "kubernetes"
        assert get_provider_from_type("kubernetes_namespace_v1") == "kubernetes"


# --- グラフ構築テスト ---


class TestK8sGraphBuilding:
    """Kubernetesリソースのグラフ構築テスト。"""

    def test_namespace_contains_deployment(self) -> None:
        """Namespace→Deploymentの包含関係がグラフに構築される。"""
        ns = _k8s_namespace("app")
        deploy = _k8s_resource("web", "kubernetes_deployment", namespace_id=ns.id)

        graph = build_graph([ns, deploy])
        assert graph.has_node(ns.address)
        assert graph.has_node(deploy.address)

        # Namespace→Deployment のエッジが存在する（包含関係）
        if graph.has_edge(ns.address, deploy.address):
            edge_data = graph.edges[ns.address, deploy.address]
            assert edge_data["relation_type"] == "contains"

    def test_namespace_contains_service(self) -> None:
        """Namespace→Serviceの包含関係がグラフに構築される。"""
        ns = _k8s_namespace("app")
        svc = _k8s_resource("web-svc", "kubernetes_service", namespace_id=ns.id)

        graph = build_graph([ns, svc])
        if graph.has_edge(ns.address, svc.address):
            edge_data = graph.edges[ns.address, svc.address]
            assert edge_data["relation_type"] == "contains"

    def test_multiple_resources_in_namespace(self) -> None:
        """複数リソースが同一Namespaceに含まれる。"""
        ns = _k8s_namespace("app")
        deploy = _k8s_resource("web", "kubernetes_deployment", namespace_id=ns.id)
        svc = _k8s_resource("web-svc", "kubernetes_service", namespace_id=ns.id)
        cm = _k8s_resource("config", "kubernetes_config_map", namespace_id=ns.id)

        graph = build_graph([ns, deploy, svc, cm])
        assert graph.number_of_nodes() == 4

    def test_resources_without_namespace(self) -> None:
        """Namespaceなしのリソースもグラフに追加される。"""
        deploy = _k8s_resource("web", "kubernetes_deployment", namespace_id="nonexistent")
        graph = build_graph([deploy])
        assert graph.has_node(deploy.address)


# --- レンダラーテスト ---


def _build_k8s_graph() -> tuple[nx.DiGraph, dict[str, tuple[float, float]]]:
    """K8sリソースのテスト用グラフと座標を構築する。"""
    ns = _k8s_namespace("app")
    deploy = _k8s_resource("web", "kubernetes_deployment", namespace_id=ns.id)
    svc = _k8s_resource("web-svc", "kubernetes_service", namespace_id=ns.id)

    graph = build_graph([ns, deploy, svc])
    positions = {
        ns.address: (100.0, 100.0),
        deploy.address: (150.0, 250.0),
        svc.address: (350.0, 250.0),
    }
    return graph, positions


class TestK8sDrawioRenderer:
    """K8s対応のdraw.ioレンダラーテスト。"""

    def test_namespace_as_container(self, tmp_path: Path) -> None:
        """Namespaceがコンテナとして描画される。"""
        from terrasketch.renderer.drawio_renderer import DrawioRenderer

        graph, positions = _build_k8s_graph()
        renderer = DrawioRenderer()
        result = renderer.render(graph, positions, tmp_path / "k8s.drawio")

        tree = ET.parse(str(result))
        cells = list(tree.getroot().iter("mxCell"))
        values = [c.get("value", "") for c in cells]
        # Namespace はコンテナとして描画される
        assert any("kubernetes_namespace" in v for v in values)


class TestK8sMermaidRenderer:
    """K8s対応のMermaidレンダラーテスト。"""

    def test_namespace_as_subgraph(self, tmp_path: Path) -> None:
        """Namespaceがsubgraphとして出力される。"""
        from terrasketch.renderer.mermaid_renderer import MermaidRenderer

        graph, positions = _build_k8s_graph()
        renderer = MermaidRenderer()
        result = renderer.render(graph, positions, tmp_path / "k8s.md")

        content = result.read_text(encoding="utf-8")
        assert "subgraph" in content
        assert "kubernetes_namespace" in content


class TestK8sPlantUMLRenderer:
    """K8s対応のPlantUMLレンダラーテスト。"""

    def test_namespace_as_package(self, tmp_path: Path) -> None:
        """Namespaceがpackageとして出力される。"""
        from terrasketch.renderer.plantuml_renderer import PlantUMLRenderer

        graph, positions = _build_k8s_graph()
        renderer = PlantUMLRenderer()
        result = renderer.render(graph, positions, tmp_path / "k8s.puml")

        content = result.read_text(encoding="utf-8")
        assert "package" in content
        assert "kubernetes_namespace" in content


class TestK8sSvgRenderer:
    """K8s対応のSVGレンダラーテスト。"""

    def test_k8s_resources_rendered(self, tmp_path: Path) -> None:
        """K8sリソースがSVGに描画される。"""
        from terrasketch.renderer.svg_renderer import SvgRenderer

        graph, positions = _build_k8s_graph()
        renderer = SvgRenderer()
        result = renderer.render(graph, positions, tmp_path / "k8s.svg")

        content = result.read_text(encoding="utf-8")
        assert "kubernetes_deployment" in content
        assert "kubernetes_service" in content


class TestK8sSampleState:
    """K8sサンプルstateファイルの解析テスト。"""

    def test_parse_k8s_sample(self) -> None:
        """K8sサンプルstateが正しく解析される。"""
        from terrasketch.parser.state_parser import parse_state

        resources = parse_state("samples/sample_k8s_state.json")
        assert len(resources) == 6

        types = {r.type for r in resources}
        assert "kubernetes_namespace" in types
        assert "kubernetes_deployment" in types
        assert "kubernetes_service" in types
        assert "kubernetes_ingress" in types
        assert "kubernetes_config_map" in types
        assert "kubernetes_secret" in types

    def test_k8s_provider_filter(self) -> None:
        """kubernetes プロバイダフィルタが機能する。"""
        from terrasketch.parser.state_parser import parse_state

        resources = parse_state("samples/sample_k8s_state.json")
        k8s_resources = [r for r in resources if r.type.startswith("kubernetes_")]
        assert len(k8s_resources) == 6
