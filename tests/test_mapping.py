"""Tests for resource mapping."""

from terrasketch.mapping.resource_map import (
    DrawioStyle,
    get_drawio_style,
    get_provider_from_type,
)


def test_aws_vpc_style():
    style = get_drawio_style("aws_vpc")
    assert "aws4" in style.style
    assert style.width == 60


def test_aws_instance_style():
    style = get_drawio_style("aws_instance")
    assert "ec2" in style.style


def test_azure_vnet_style():
    style = get_drawio_style("azurerm_virtual_network")
    assert "azure" in style.style


def test_unknown_resource_returns_default():
    style = get_drawio_style("unknown_resource_type")
    assert "rounded" in style.style


def test_extended_aws_resource():
    style = get_drawio_style("aws_s3_bucket")
    assert "s3" in style.style


def test_extended_aws_lambda():
    style = get_drawio_style("aws_lambda_function")
    assert "lambda" in style.style


def test_extended_azure_storage():
    style = get_drawio_style("azurerm_storage_account")
    assert "azure" in style.style


def test_provider_from_type_aws():
    assert get_provider_from_type("aws_vpc") == "aws"


def test_provider_from_type_azure():
    assert get_provider_from_type("azurerm_virtual_network") == "azure"


def test_provider_from_type_unknown():
    assert get_provider_from_type("google_compute_instance") == "unknown"
