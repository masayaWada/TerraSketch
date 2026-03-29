"""リソースマッピングのテスト。"""

from terrasketch.mapping.resource_map import (
    DrawioStyle,
    get_drawio_style,
    get_provider_from_type,
)


def test_aws_vpc_style():
    """AWS VPCにAWS4アイコンスタイルが返ることを確認。"""
    style = get_drawio_style("aws_vpc")
    assert "aws4" in style.style
    assert style.width == 60


def test_aws_instance_style():
    """AWS EC2にEC2アイコンスタイルが返ることを確認。"""
    style = get_drawio_style("aws_instance")
    assert "ec2" in style.style


def test_azure_vnet_style():
    """Azure VNetにAzureアイコンスタイルが返ることを確認。"""
    style = get_drawio_style("azurerm_virtual_network")
    assert "azure" in style.style


def test_unknown_resource_returns_default():
    """未知のリソースタイプにデフォルトスタイルが返ることを確認。"""
    style = get_drawio_style("unknown_resource_type")
    assert "rounded" in style.style


def test_extended_aws_resource():
    """拡張AWS S3リソースに正しいスタイルが返ることを確認。"""
    style = get_drawio_style("aws_s3_bucket")
    assert "s3" in style.style


def test_extended_aws_lambda():
    """拡張AWS Lambdaリソースに正しいスタイルが返ることを確認。"""
    style = get_drawio_style("aws_lambda_function")
    assert "lambda" in style.style


def test_extended_azure_storage():
    """拡張Azure Storageリソースに正しいスタイルが返ることを確認。"""
    style = get_drawio_style("azurerm_storage_account")
    assert "azure" in style.style


def test_provider_from_type_aws():
    """AWSリソースタイプからプロバイダ'aws'が判定されることを確認。"""
    assert get_provider_from_type("aws_vpc") == "aws"


def test_provider_from_type_azure():
    """Azureリソースタイプからプロバイダ'azure'が判定されることを確認。"""
    assert get_provider_from_type("azurerm_virtual_network") == "azure"


def test_provider_from_type_unknown():
    """未知のリソースタイプからプロバイダ'unknown'が判定されることを確認。"""
    assert get_provider_from_type("google_compute_instance") == "unknown"
