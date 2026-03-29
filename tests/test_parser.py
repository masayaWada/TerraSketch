"""Terraform stateパーサーのテスト。"""

import json
import tempfile
from pathlib import Path

import pytest

from terrasketch.parser.state_parser import Resource, parse_state


def _write_state(tmp_path: Path, state: dict) -> Path:
    """テスト用のstate JSONファイルを一時ディレクトリに書き出す。"""
    path = tmp_path / "state.json"
    path.write_text(json.dumps(state), encoding="utf-8")
    return path


@pytest.fixture
def sample_state(tmp_path):
    """VPCとSubnetを含むサンプルstateのフィクスチャ。"""
    state = {
        "format_version": "1.0",
        "terraform_version": "1.7.0",
        "values": {
            "root_module": {
                "resources": [
                    {
                        "address": "aws_vpc.main",
                        "type": "aws_vpc",
                        "name": "main",
                        "provider_name": "registry.terraform.io/hashicorp/aws",
                        "values": {
                            "id": "vpc-123",
                            "cidr_block": "10.0.0.0/16",
                        },
                    },
                    {
                        "address": "aws_subnet.pub",
                        "type": "aws_subnet",
                        "name": "pub",
                        "provider_name": "registry.terraform.io/hashicorp/aws",
                        "values": {
                            "id": "subnet-456",
                            "vpc_id": "vpc-123",
                            "cidr_block": "10.0.1.0/24",
                        },
                    },
                ]
            }
        },
    }
    return _write_state(tmp_path, state)


def test_parse_state_returns_resources(sample_state):
    """パース結果がResourceオブジェクトのリストであることを確認。"""
    resources = parse_state(sample_state)
    assert len(resources) == 2
    assert all(isinstance(r, Resource) for r in resources)


def test_parse_state_resource_fields(sample_state):
    """各Resourceのフィールドが正しく抽出されていることを確認。"""
    resources = parse_state(sample_state)
    vpc = next(r for r in resources if r.type == "aws_vpc")
    assert vpc.name == "main"
    assert vpc.id == "vpc-123"
    assert vpc.attributes["cidr_block"] == "10.0.0.0/16"
    assert vpc.address == "aws_vpc.main"


def test_parse_state_file_not_found():
    """存在しないファイルパスでFileNotFoundErrorが発生することを確認。"""
    with pytest.raises(FileNotFoundError):
        parse_state("/nonexistent/path.json")


def test_parse_state_invalid_json(tmp_path):
    """'values'キーが欠落したJSONでValueErrorが発生することを確認。"""
    path = tmp_path / "bad.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="missing 'values'"):
        parse_state(path)


def test_parse_state_missing_root_module(tmp_path):
    """'root_module'キーが欠落したJSONでValueErrorが発生することを確認。"""
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"values": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="missing 'values.root_module'"):
        parse_state(path)


def test_parse_state_child_modules(tmp_path):
    """子モジュール内のリソースも正しく抽出されることを確認。"""
    state = {
        "values": {
            "root_module": {
                "resources": [
                    {
                        "address": "aws_vpc.main",
                        "type": "aws_vpc",
                        "name": "main",
                        "provider_name": "aws",
                        "values": {"id": "vpc-1"},
                    }
                ],
                "child_modules": [
                    {
                        "resources": [
                            {
                                "address": "module.net.aws_subnet.a",
                                "type": "aws_subnet",
                                "name": "a",
                                "provider_name": "aws",
                                "values": {"id": "subnet-1", "vpc_id": "vpc-1"},
                            }
                        ]
                    }
                ],
            }
        }
    }
    path = _write_state(tmp_path, state)
    resources = parse_state(path)
    assert len(resources) == 2
    types = {r.type for r in resources}
    assert types == {"aws_vpc", "aws_subnet"}
