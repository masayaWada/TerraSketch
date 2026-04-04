"""AWS / Azure 拡張リソースマッピング。

MVP範囲を超えた幅広いクラウドリソースに対するdraw.ioスタイルを提供する。
"""

from __future__ import annotations

from terrasketch.mapping.resource_map import DrawioStyle


EXTENDED_AWS_MAPPING: dict[str, DrawioStyle] = {
    # コンピューティング
    "aws_lambda_function": DrawioStyle(
        shape="mxgraph.aws4.lambda_function",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.lambda;",
    ),
    "aws_ecs_cluster": DrawioStyle(
        shape="mxgraph.aws4.ecs",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.ecs;",
    ),
    "aws_ecs_service": DrawioStyle(
        shape="mxgraph.aws4.ecs",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.ecs;",
    ),
    "aws_autoscaling_group": DrawioStyle(
        shape="mxgraph.aws4.auto_scaling2",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.auto_scaling2;",
    ),
    # ストレージ
    "aws_s3_bucket": DrawioStyle(
        shape="mxgraph.aws4.s3",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.s3;",
    ),
    "aws_ebs_volume": DrawioStyle(
        shape="mxgraph.aws4.elastic_block_store",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.elastic_block_store;",
    ),
    # データベース
    "aws_db_instance": DrawioStyle(
        shape="mxgraph.aws4.rds",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.rds;",
    ),
    "aws_dynamodb_table": DrawioStyle(
        shape="mxgraph.aws4.dynamodb",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.dynamodb;",
    ),
    "aws_elasticache_cluster": DrawioStyle(
        shape="mxgraph.aws4.elasticache",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.elasticache;",
    ),
    # ネットワーキング
    "aws_lb": DrawioStyle(
        shape="mxgraph.aws4.application_load_balancer",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.elastic_load_balancing;",
    ),
    "aws_alb": DrawioStyle(
        shape="mxgraph.aws4.application_load_balancer",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.elastic_load_balancing;",
    ),
    "aws_cloudfront_distribution": DrawioStyle(
        shape="mxgraph.aws4.cloudfront",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.cloudfront;",
    ),
    "aws_route53_zone": DrawioStyle(
        shape="mxgraph.aws4.route_53",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.route_53;",
    ),
    "aws_api_gateway_rest_api": DrawioStyle(
        shape="mxgraph.aws4.api_gateway",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.api_gateway;",
    ),
    "aws_elastic_ip": DrawioStyle(
        shape="mxgraph.aws4.elastic_ip_address",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.elastic_ip_address;",
    ),
    # セキュリティ / IAM
    "aws_iam_role": DrawioStyle(
        shape="mxgraph.aws4.role",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.role;",
    ),
    "aws_iam_policy": DrawioStyle(
        shape="mxgraph.aws4.policy",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.policy;",
    ),
    "aws_kms_key": DrawioStyle(
        shape="mxgraph.aws4.kms",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.kms;",
    ),
    # メッセージング
    "aws_sqs_queue": DrawioStyle(
        shape="mxgraph.aws4.sqs",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.sqs;",
    ),
    "aws_sns_topic": DrawioStyle(
        shape="mxgraph.aws4.sns",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.sns;",
    ),
    # モニタリング
    "aws_cloudwatch_log_group": DrawioStyle(
        shape="mxgraph.aws4.cloudwatch",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.cloudwatch;",
    ),
}

EXTENDED_AZURE_MAPPING: dict[str, DrawioStyle] = {
    "azurerm_windows_virtual_machine": DrawioStyle(
        shape="mxgraph.azure.virtual_machine",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.azure.virtual_machine;",
    ),
    "azurerm_storage_account": DrawioStyle(
        shape="mxgraph.azure.storage",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.azure.storage;",
    ),
    "azurerm_sql_server": DrawioStyle(
        shape="mxgraph.azure.sql_database",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.azure.sql_database;",
    ),
    "azurerm_lb": DrawioStyle(
        shape="mxgraph.azure.load_balancer_generic",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.azure.load_balancer_generic;",
    ),
    "azurerm_application_gateway": DrawioStyle(
        shape="mxgraph.azure.application_gateway",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.azure.application_gateway;",
    ),
    "azurerm_kubernetes_cluster": DrawioStyle(
        shape="mxgraph.azure.kubernetes",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.azure.kubernetes;",
    ),
    "azurerm_function_app": DrawioStyle(
        shape="mxgraph.azure.function_apps",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.azure.function_apps;",
    ),
}

# 拡張リレーションシップルール
EXTENDED_AWS_RELATIONSHIP_RULES: list[tuple[str, str, str]] = [
    ("aws_lb", "subnets", "aws_subnet"),
    ("aws_alb", "subnets", "aws_subnet"),
    ("aws_db_instance", "db_subnet_group_name", "aws_db_subnet_group"),
    ("aws_db_instance", "vpc_security_group_ids", "aws_security_group"),
    ("aws_lambda_function", "vpc_config.subnet_ids", "aws_subnet"),
    ("aws_lambda_function", "vpc_config.security_group_ids", "aws_security_group"),
    ("aws_ecs_service", "network_configuration.subnets", "aws_subnet"),
    ("aws_ecs_service", "network_configuration.security_groups", "aws_security_group"),
    ("aws_ecs_service", "cluster", "aws_ecs_cluster"),
    ("aws_ebs_volume", "availability_zone", "aws_instance"),
    ("aws_nat_gateway", "allocation_id", "aws_elastic_ip"),
    ("aws_cloudfront_distribution", "origin.domain_name", "aws_s3_bucket"),
    ("aws_route53_record", "zone_id", "aws_route53_zone"),
    ("aws_sns_topic_subscription", "topic_arn", "aws_sns_topic"),
    ("aws_sqs_queue_policy", "queue_url", "aws_sqs_queue"),
]

EXTENDED_GCP_MAPPING: dict[str, DrawioStyle] = {
    # コンテナオーケストレーション
    "google_container_cluster": DrawioStyle(
        shape="mxgraph.gcp2.google_container_engine",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.gcp2.google_container_engine;",
    ),
    "google_container_node_pool": DrawioStyle(
        shape="mxgraph.gcp2.google_container_engine",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.gcp2.google_container_engine;",
    ),
    # サーバーレス
    "google_cloudfunctions_function": DrawioStyle(
        shape="mxgraph.gcp2.cloud_functions",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.gcp2.cloud_functions;",
    ),
    # データベース
    "google_sql_database_instance": DrawioStyle(
        shape="mxgraph.gcp2.cloud_sql",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.gcp2.cloud_sql;",
    ),
    # ストレージ
    "google_storage_bucket": DrawioStyle(
        shape="mxgraph.gcp2.cloud_storage",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.gcp2.cloud_storage;",
    ),
    # メッセージング
    "google_pubsub_topic": DrawioStyle(
        shape="mxgraph.gcp2.cloud_pubsub",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.gcp2.cloud_pubsub;",
    ),
    "google_pubsub_subscription": DrawioStyle(
        shape="mxgraph.gcp2.cloud_pubsub",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.gcp2.cloud_pubsub;",
    ),
    # DNS
    "google_dns_managed_zone": DrawioStyle(
        shape="mxgraph.gcp2.cloud_dns",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.gcp2.cloud_dns;",
    ),
    # ロードバランサー
    "google_compute_forwarding_rule": DrawioStyle(
        shape="mxgraph.gcp2.cloud_load_balancing",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.gcp2.cloud_load_balancing;",
    ),
    # インスタンスグループ
    "google_compute_instance_group": DrawioStyle(
        shape="mxgraph.gcp2.compute_engine",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.gcp2.compute_engine;",
    ),
}

EXTENDED_GCP_RELATIONSHIP_RULES: list[tuple[str, str, str]] = [
    ("google_compute_subnetwork", "network", "google_compute_network"),
    ("google_compute_instance", "subnetwork", "google_compute_subnetwork"),
    ("google_compute_instance", "network_interface.subnetwork", "google_compute_subnetwork"),
    ("google_compute_firewall", "network", "google_compute_network"),
    ("google_container_cluster", "network", "google_compute_network"),
    ("google_container_cluster", "subnetwork", "google_compute_subnetwork"),
    ("google_container_node_pool", "cluster", "google_container_cluster"),
    ("google_cloudfunctions_function", "vpc_connector", "google_compute_network"),
    ("google_sql_database_instance", "private_network", "google_compute_network"),
    ("google_compute_forwarding_rule", "network", "google_compute_network"),
    ("google_compute_forwarding_rule", "subnetwork", "google_compute_subnetwork"),
    ("google_pubsub_subscription", "topic", "google_pubsub_topic"),
]

# Kubernetesリソースマッピング
EXTENDED_K8S_MAPPING: dict[str, DrawioStyle] = {
    # Namespace（コンテナ型）
    "kubernetes_namespace": DrawioStyle(
        shape="mxgraph.kubernetes.ns",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.kubernetes.ns;",
    ),
    "kubernetes_namespace_v1": DrawioStyle(
        shape="mxgraph.kubernetes.ns",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.kubernetes.ns;",
    ),
    # Deployment
    "kubernetes_deployment": DrawioStyle(
        shape="mxgraph.kubernetes.deploy",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.kubernetes.deploy;",
    ),
    "kubernetes_deployment_v1": DrawioStyle(
        shape="mxgraph.kubernetes.deploy",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.kubernetes.deploy;",
    ),
    # Service
    "kubernetes_service": DrawioStyle(
        shape="mxgraph.kubernetes.svc",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.kubernetes.svc;",
    ),
    "kubernetes_service_v1": DrawioStyle(
        shape="mxgraph.kubernetes.svc",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.kubernetes.svc;",
    ),
    # Ingress
    "kubernetes_ingress": DrawioStyle(
        shape="mxgraph.kubernetes.ing",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.kubernetes.ing;",
    ),
    "kubernetes_ingress_v1": DrawioStyle(
        shape="mxgraph.kubernetes.ing",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.kubernetes.ing;",
    ),
    # Pod
    "kubernetes_pod": DrawioStyle(
        shape="mxgraph.kubernetes.pod",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.kubernetes.pod;",
    ),
    "kubernetes_pod_v1": DrawioStyle(
        shape="mxgraph.kubernetes.pod",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.kubernetes.pod;",
    ),
    # StatefulSet
    "kubernetes_stateful_set": DrawioStyle(
        shape="mxgraph.kubernetes.sts",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.kubernetes.sts;",
    ),
    "kubernetes_stateful_set_v1": DrawioStyle(
        shape="mxgraph.kubernetes.sts",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.kubernetes.sts;",
    ),
    # DaemonSet
    "kubernetes_daemon_set_v1": DrawioStyle(
        shape="mxgraph.kubernetes.ds",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.kubernetes.ds;",
    ),
    # ConfigMap / Secret
    "kubernetes_config_map": DrawioStyle(
        shape="mxgraph.kubernetes.cm",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.kubernetes.cm;",
    ),
    "kubernetes_config_map_v1": DrawioStyle(
        shape="mxgraph.kubernetes.cm",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.kubernetes.cm;",
    ),
    "kubernetes_secret": DrawioStyle(
        shape="mxgraph.kubernetes.secret",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.kubernetes.secret;",
    ),
    "kubernetes_secret_v1": DrawioStyle(
        shape="mxgraph.kubernetes.secret",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.kubernetes.secret;",
    ),
    # HPA
    "kubernetes_horizontal_pod_autoscaler": DrawioStyle(
        shape="mxgraph.kubernetes.hpa",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.kubernetes.hpa;",
    ),
    "kubernetes_horizontal_pod_autoscaler_v1": DrawioStyle(
        shape="mxgraph.kubernetes.hpa",
        width=60, height=60,
        style="outlineConnect=0;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;shape=mxgraph.kubernetes.hpa;",
    ),
}

# Kubernetesリレーションシップルール
EXTENDED_K8S_RELATIONSHIP_RULES: list[tuple[str, str, str]] = [
    # Namespace包含（metadata.namespace による名前参照）
    ("kubernetes_deployment", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_deployment_v1", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_deployment_v1", "metadata.namespace", "kubernetes_namespace_v1"),
    ("kubernetes_service", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_service_v1", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_service_v1", "metadata.namespace", "kubernetes_namespace_v1"),
    ("kubernetes_ingress", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_ingress_v1", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_ingress_v1", "metadata.namespace", "kubernetes_namespace_v1"),
    ("kubernetes_pod", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_pod_v1", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_pod_v1", "metadata.namespace", "kubernetes_namespace_v1"),
    ("kubernetes_stateful_set", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_stateful_set_v1", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_stateful_set_v1", "metadata.namespace", "kubernetes_namespace_v1"),
    ("kubernetes_daemon_set_v1", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_daemon_set_v1", "metadata.namespace", "kubernetes_namespace_v1"),
    ("kubernetes_config_map", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_config_map_v1", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_config_map_v1", "metadata.namespace", "kubernetes_namespace_v1"),
    ("kubernetes_secret", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_secret_v1", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_secret_v1", "metadata.namespace", "kubernetes_namespace_v1"),
]

# Kubernetesの包含関係
K8S_CONTAINMENT_RULES: set[tuple[str, str, str]] = {
    ("kubernetes_deployment", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_deployment_v1", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_deployment_v1", "metadata.namespace", "kubernetes_namespace_v1"),
    ("kubernetes_service", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_service_v1", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_service_v1", "metadata.namespace", "kubernetes_namespace_v1"),
    ("kubernetes_ingress", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_ingress_v1", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_ingress_v1", "metadata.namespace", "kubernetes_namespace_v1"),
    ("kubernetes_pod", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_pod_v1", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_pod_v1", "metadata.namespace", "kubernetes_namespace_v1"),
    ("kubernetes_stateful_set", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_stateful_set_v1", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_stateful_set_v1", "metadata.namespace", "kubernetes_namespace_v1"),
    ("kubernetes_daemon_set_v1", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_daemon_set_v1", "metadata.namespace", "kubernetes_namespace_v1"),
    ("kubernetes_config_map", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_config_map_v1", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_config_map_v1", "metadata.namespace", "kubernetes_namespace_v1"),
    ("kubernetes_secret", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_secret_v1", "metadata.namespace", "kubernetes_namespace"),
    ("kubernetes_secret_v1", "metadata.namespace", "kubernetes_namespace_v1"),
}

EXTENDED_AZURE_RELATIONSHIP_RULES: list[tuple[str, str, str]] = [
    ("azurerm_windows_virtual_machine", "network_interface_ids", "azurerm_network_interface"),
    ("azurerm_storage_account", "resource_group_name", "azurerm_resource_group"),
    ("azurerm_sql_server", "resource_group_name", "azurerm_resource_group"),
    ("azurerm_lb", "resource_group_name", "azurerm_resource_group"),
    ("azurerm_kubernetes_cluster", "resource_group_name", "azurerm_resource_group"),
    ("azurerm_function_app", "resource_group_name", "azurerm_resource_group"),
]
