"""PlantUMLダイアグラムレンダラー。

リソースグラフからPlantUMLコンポーネント図構文を生成する。
PlantUMLサーバーやCLIでPNG/SVG画像に変換可能。
"""

from __future__ import annotations

import re
from pathlib import Path

import networkx as nx

from terrasketch.parser.state_parser import Resource


# リソースタイプごとのPlantUMLステレオタイプとアイコン
_STEREOTYPE_MAP: dict[str, str] = {
    "aws_vpc": "<<VPC>>",
    "aws_subnet": "<<Subnet>>",
    "aws_instance": "<<EC2>>",
    "aws_security_group": "<<SecurityGroup>>",
    "aws_s3_bucket": "<<S3>>",
    "aws_lambda_function": "<<Lambda>>",
    "aws_db_instance": "<<RDS>>",
    "aws_lb": "<<ELB>>",
    "aws_alb": "<<ALB>>",
    "aws_ecs_cluster": "<<ECS>>",
    "aws_ecs_service": "<<ECS>>",
    "aws_dynamodb_table": "<<DynamoDB>>",
    "aws_cloudfront_distribution": "<<CloudFront>>",
    "aws_route53_zone": "<<Route53>>",
    "aws_internet_gateway": "<<IGW>>",
    "aws_nat_gateway": "<<NAT>>",
    "aws_route_table": "<<RouteTable>>",
    "azurerm_virtual_network": "<<VNet>>",
    "azurerm_subnet": "<<Subnet>>",
    "azurerm_linux_virtual_machine": "<<VM>>",
    "azurerm_windows_virtual_machine": "<<VM>>",
    "azurerm_network_security_group": "<<NSG>>",
    "azurerm_resource_group": "<<ResourceGroup>>",
    "azurerm_storage_account": "<<Storage>>",
    "azurerm_kubernetes_cluster": "<<AKS>>",
    # GCPリソース
    "google_compute_network": "<<VPCNetwork>>",
    "google_compute_subnetwork": "<<Subnet>>",
    "google_compute_instance": "<<GCE>>",
    "google_compute_firewall": "<<Firewall>>",
    "google_container_cluster": "<<GKE>>",
    "google_cloudfunctions_function": "<<CloudFunction>>",
    "google_sql_database_instance": "<<CloudSQL>>",
    "google_storage_bucket": "<<GCS>>",
    "google_pubsub_topic": "<<PubSub>>",
    "google_compute_forwarding_rule": "<<LoadBalancer>>",
    # Kubernetesリソース
    "kubernetes_namespace": "<<Namespace>>",
    "kubernetes_namespace_v1": "<<Namespace>>",
    "kubernetes_deployment": "<<Deployment>>",
    "kubernetes_deployment_v1": "<<Deployment>>",
    "kubernetes_service": "<<Service>>",
    "kubernetes_service_v1": "<<Service>>",
    "kubernetes_ingress": "<<Ingress>>",
    "kubernetes_ingress_v1": "<<Ingress>>",
    "kubernetes_pod": "<<Pod>>",
    "kubernetes_pod_v1": "<<Pod>>",
    "kubernetes_stateful_set": "<<StatefulSet>>",
    "kubernetes_stateful_set_v1": "<<StatefulSet>>",
    "kubernetes_daemon_set_v1": "<<DaemonSet>>",
    "kubernetes_config_map": "<<ConfigMap>>",
    "kubernetes_config_map_v1": "<<ConfigMap>>",
    "kubernetes_secret": "<<Secret>>",
    "kubernetes_secret_v1": "<<Secret>>",
    "kubernetes_horizontal_pod_autoscaler": "<<HPA>>",
    "kubernetes_horizontal_pod_autoscaler_v1": "<<HPA>>",
}

# リソースタイプごとのPlantUML色
_COLOR_MAP: dict[str, str] = {
    "vpc": "#E8F5E9",
    "subnet": "#E3F2FD",
    "compute": "#FFF3E0",
    "security": "#FCE4EC",
    "storage": "#F3E5F5",
    "network": "#FFF8E1",
    "database": "#E8EAF6",
}


def _sanitize_id(address: str) -> str:
    """リソースアドレスを有効なPlantUML識別子に変換する。"""
    return re.sub(r"[^a-zA-Z0-9_]", "_", address)


def _get_stereotype(resource_type: str) -> str:
    """リソースタイプに対応するPlantUMLステレオタイプを取得する。"""
    return _STEREOTYPE_MAP.get(resource_type, "<<Resource>>")


def _get_color(resource_type: str) -> str:
    """リソースタイプに対応する背景色を取得する。"""
    if "vpc" in resource_type or "virtual_network" in resource_type:
        return _COLOR_MAP["vpc"]
    if "subnet" in resource_type:
        return _COLOR_MAP["subnet"]
    if any(k in resource_type for k in ("instance", "virtual_machine", "lambda", "ecs")):
        return _COLOR_MAP["compute"]
    if any(k in resource_type for k in ("security_group", "network_security", "firewall")):
        return _COLOR_MAP["security"]
    if any(k in resource_type for k in ("s3", "storage", "ebs")):
        return _COLOR_MAP["storage"]
    if any(k in resource_type for k in ("lb", "alb", "gateway", "route")):
        return _COLOR_MAP["network"]
    if any(k in resource_type for k in ("db_instance", "dynamodb", "rds", "sql")):
        return _COLOR_MAP["database"]
    return "#FFFFFF"


class PlantUMLRenderer:
    """TerraformリソースグラフをPlantUMLコンポーネント図としてレンダリングする。"""

    # diffモード用の色マッピング
    _DIFF_COLORS = {
        "added": "#C8E6C9",
        "removed": "#FFCDD2",
        "modified": "#FFF9C4",
    }

    def render(
        self,
        graph: nx.DiGraph,
        positions: dict[str, tuple[float, float]],
        output_path: str | Path,
        show_labels: bool = False,
        diff_mode: bool = False,
        group_by_module: bool = False,
        tag_groups: dict[str, list[str]] | None = None,
    ) -> Path:
        """グラフをPlantUMLファイルとしてレンダリングする。

        Args:
            graph: リソース依存関係グラフ。
            positions: ノード座標（PlantUMLでは自動レイアウトのため参考情報）。
            output_path: 出力.pumlファイルのパス。
            show_labels: エッジに接続属性名ラベルを表示するか。
            diff_mode: diff比較結果を色分けで表示するか。

        Returns:
            書き出されたPlantUMLファイルのPath。
        """
        output_path = Path(output_path).with_suffix(".puml")
        lines: list[str] = []
        lines.append("@startuml TerraSketch")
        lines.append("")
        lines.append("' TerraSketchにより自動生成されたPlantUMLダイアグラム")
        lines.append("skinparam componentStyle rectangle")
        lines.append("skinparam defaultTextAlignment center")
        lines.append("skinparam shadowing false")
        lines.append("")

        # モジュール境界グルーピング
        module_emitted: set[str] = set()
        if group_by_module:
            module_nodes: dict[str, list[str]] = {}
            for node_addr in graph.nodes:
                data = graph.nodes[node_addr]
                module_path = data.get("module_path", "")
                if module_path:
                    module_nodes.setdefault(module_path, []).append(node_addr)

            for mod_path in sorted(module_nodes.keys()):
                lines.append(f'package "{mod_path}" #EEEEEE {{')
                for node_addr in sorted(module_nodes[mod_path]):
                    self._emit_component(graph, node_addr, lines, indent=4, diff_mode=diff_mode)
                    module_emitted.add(node_addr)
                lines.append("}")
                lines.append("")

        # タググループ package を出力
        tag_emitted: set[str] = set()
        if tag_groups:
            for tag_value in sorted(tag_groups.keys()):
                node_addrs = tag_groups[tag_value]
                valid_addrs = [a for a in node_addrs if a in graph.nodes and a not in module_emitted]
                if not valid_addrs:
                    continue
                lines.append(f'package "{tag_value}" #FFF3E0 {{')
                for node_addr in sorted(valid_addrs):
                    self._emit_component(graph, node_addr, lines, indent=4, diff_mode=diff_mode)
                    tag_emitted.add(node_addr)
                lines.append("}")
                lines.append("")

        # VPC/VNetコンテナの階層構造を構築
        container_types = {"aws_vpc", "azurerm_virtual_network", "google_compute_network", "kubernetes_namespace", "kubernetes_namespace_v1"}
        subnet_types = {"aws_subnet", "azurerm_subnet", "google_compute_subnetwork"}
        vpc_children: dict[str, list[str]] = {}
        subnet_children: dict[str, list[str]] = {}
        emitted_nodes: set[str] = set(module_emitted) | set(tag_emitted)

        for node_addr in graph.nodes:
            data = graph.nodes[node_addr]
            resource = data.get("resource")
            if resource is None:
                continue
            if resource.type in container_types:
                children = list(nx.descendants(graph, node_addr))
                vpc_children[node_addr] = children
            elif resource.type in subnet_types:
                children = list(nx.descendants(graph, node_addr))
                subnet_children[node_addr] = children

        # VPC > Subnet > リソースの階層をpackageで出力
        for vpc_addr in sorted(vpc_children.keys()):
            vpc_data = graph.nodes[vpc_addr]
            vpc_resource = vpc_data.get("resource")
            if vpc_resource is None:
                continue
            color = _get_color(vpc_resource.type)
            lines.append(
                f'package "{vpc_resource.type} / {vpc_resource.name}" {color} {{'
            )
            emitted_nodes.add(vpc_addr)

            # VPC内のSubnet
            for subnet_addr in sorted(subnet_children.keys()):
                if subnet_addr not in vpc_children.get(vpc_addr, []):
                    continue
                subnet_data = graph.nodes[subnet_addr]
                subnet_resource = subnet_data.get("resource")
                if subnet_resource is None:
                    continue
                sub_color = _get_color(subnet_resource.type)
                lines.append(
                    f'    package "{subnet_resource.type} / {subnet_resource.name}" {sub_color} {{'
                )
                emitted_nodes.add(subnet_addr)

                # Subnet内のリソース
                for child_addr in sorted(subnet_children[subnet_addr]):
                    if child_addr in emitted_nodes:
                        continue
                    self._emit_component(graph, child_addr, lines, indent=8, diff_mode=diff_mode)
                    emitted_nodes.add(child_addr)

                lines.append("    }")

            # VPC直下（Subnet外）のリソース
            for child_addr in sorted(vpc_children[vpc_addr]):
                if child_addr in emitted_nodes:
                    continue
                self._emit_component(graph, child_addr, lines, indent=4, diff_mode=diff_mode)
                emitted_nodes.add(child_addr)

            lines.append("}")
            lines.append("")

        # VPC外のリソース
        for node_addr in sorted(graph.nodes):
            if node_addr in emitted_nodes:
                continue
            self._emit_component(graph, node_addr, lines, indent=0, diff_mode=diff_mode)
            emitted_nodes.add(node_addr)

        lines.append("")

        # エッジを出力（包含=実線、参照=破線で区別）
        for source, target, edge_data in graph.edges(data=True):
            src_id = _sanitize_id(source)
            tgt_id = _sanitize_id(target)
            relation_type = edge_data.get("relation_type", "contains")
            label = edge_data.get("attr_name", "") if show_labels else ""

            if relation_type == "references":
                if label:
                    lines.append(f"{src_id} ..> {tgt_id} : {label}")
                else:
                    lines.append(f"{src_id} ..> {tgt_id}")
            else:
                if label:
                    lines.append(f"{src_id} --> {tgt_id} : {label}")
                else:
                    lines.append(f"{src_id} --> {tgt_id}")

        lines.append("")
        lines.append("@enduml")
        lines.append("")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines), encoding="utf-8")
        return output_path

    def _emit_component(
        self,
        graph: nx.DiGraph,
        node_addr: str,
        lines: list[str],
        indent: int = 0,
        diff_mode: bool = False,
    ) -> None:
        """単一リソースをPlantUMLコンポーネントとして出力する。"""
        data = graph.nodes[node_addr]
        resource = data.get("resource")
        if resource is None:
            return
        node_id = _sanitize_id(node_addr)
        stereotype = _get_stereotype(resource.type)
        color = _get_color(resource.type)

        # diffモード時は色とラベルを上書き
        label_prefix = ""
        if diff_mode:
            diff_status = data.get("diff_status", "unchanged")
            diff_color = self._DIFF_COLORS.get(diff_status)
            if diff_color:
                color = diff_color
                diff_labels = {"added": "[NEW] ", "removed": "[DEL] ", "modified": "[MOD] "}
                label_prefix = diff_labels.get(diff_status, "")

        # コストラベルを追加
        cost_suffix = ""
        cost_label = data.get("cost_label", "")
        cost_diff_label = data.get("cost_diff_label", "")
        if cost_diff_label:
            cost_suffix = f"\\n{cost_diff_label}"
        elif cost_label:
            cost_suffix = f"\\n{cost_label}"

        pad = " " * indent
        lines.append(
            f'{pad}component "{label_prefix}{resource.type}\\n{resource.name}{cost_suffix}" as {node_id} {stereotype} {color}'
        )
