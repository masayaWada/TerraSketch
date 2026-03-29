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

EXTENDED_AZURE_RELATIONSHIP_RULES: list[tuple[str, str, str]] = [
    ("azurerm_windows_virtual_machine", "network_interface_ids", "azurerm_network_interface"),
    ("azurerm_storage_account", "resource_group_name", "azurerm_resource_group"),
    ("azurerm_sql_server", "resource_group_name", "azurerm_resource_group"),
    ("azurerm_lb", "resource_group_name", "azurerm_resource_group"),
    ("azurerm_kubernetes_cluster", "resource_group_name", "azurerm_resource_group"),
    ("azurerm_function_app", "resource_group_name", "azurerm_resource_group"),
]
