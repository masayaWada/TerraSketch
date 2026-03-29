"""HCLパーサーのテスト。"""

from pathlib import Path

import pytest

from terrasketch.parser.hcl_parser import parse_hcl, parse_hcl_directory


SAMPLE_HCL = Path(__file__).parent.parent / "samples" / "sample.tf"
SAMPLES_DIR = Path(__file__).parent.parent / "samples"


def test_parse_hcl_returns_resources():
    """HCLファイルからリソースが抽出されることを確認。"""
    resources = parse_hcl(SAMPLE_HCL)
    assert len(resources) == 4


def test_parse_hcl_resource_types():
    """抽出されたリソースのタイプが正しいことを確認。"""
    resources = parse_hcl(SAMPLE_HCL)
    types = {r.type for r in resources}
    assert "aws_vpc" in types
    assert "aws_subnet" in types
    assert "aws_instance" in types
    assert "aws_security_group" in types


def test_parse_hcl_resource_names():
    """抽出されたリソースの名前が正しいことを確認。"""
    resources = parse_hcl(SAMPLE_HCL)
    names = {r.name for r in resources}
    assert "main" in names
    assert "public" in names
    assert "web" in names
    assert "web_sg" in names


def test_parse_hcl_attributes():
    """リソース属性が正しく抽出されることを確認。"""
    resources = parse_hcl(SAMPLE_HCL)
    vpc = next(r for r in resources if r.type == "aws_vpc")
    assert vpc.attributes.get("cidr_block") == "10.0.0.0/16"


def test_parse_hcl_tags():
    """tags属性がdict形式で正しく抽出されることを確認。"""
    resources = parse_hcl(SAMPLE_HCL)
    vpc = next(r for r in resources if r.type == "aws_vpc")
    tags = vpc.attributes.get("tags")
    assert isinstance(tags, dict)
    assert tags.get("Name") == "main-vpc"
    assert tags.get("Environment") == "production"


def test_parse_hcl_provider_detection():
    """プロバイダが正しく推定されることを確認。"""
    resources = parse_hcl(SAMPLE_HCL)
    for r in resources:
        assert "aws" in r.provider


def test_parse_hcl_file_not_found():
    """存在しないファイルでFileNotFoundErrorが発生することを確認。"""
    with pytest.raises(FileNotFoundError):
        parse_hcl("nonexistent.tf")


def test_parse_hcl_directory():
    """ディレクトリ内の.tfファイルからリソースが抽出されることを確認。"""
    resources = parse_hcl_directory(SAMPLES_DIR)
    # samples/sample.tf から4リソースが抽出される
    tf_resources = [r for r in resources if r.type.startswith("aws_")]
    assert len(tf_resources) >= 4


def test_parse_hcl_directory_not_found():
    """存在しないディレクトリでFileNotFoundErrorが発生することを確認。"""
    with pytest.raises(FileNotFoundError):
        parse_hcl_directory("nonexistent_dir")


def test_parse_hcl_list_attributes():
    """リスト属性が正しく抽出されることを確認。"""
    resources = parse_hcl(SAMPLE_HCL)
    ec2 = next(r for r in resources if r.type == "aws_instance")
    sg_ids = ec2.attributes.get("vpc_security_group_ids")
    assert isinstance(sg_ids, list)
    assert "sg-12345" in sg_ids


def test_parse_hcl_empty_file(tmp_path):
    """空の.tfファイルからは空のリストが返ることを確認。"""
    empty_tf = tmp_path / "empty.tf"
    empty_tf.write_text("", encoding="utf-8")
    resources = parse_hcl(empty_tf)
    assert resources == []


def test_parse_hcl_comments(tmp_path):
    """コメント付きHCLが正しく解析されることを確認。"""
    hcl_content = '''
# This is a comment
// Another comment
/* Block comment */
resource "aws_vpc" "test" {
  cidr_block = "10.0.0.0/16"
}
'''
    tf_file = tmp_path / "comments.tf"
    tf_file.write_text(hcl_content, encoding="utf-8")
    resources = parse_hcl(tf_file)
    assert len(resources) == 1
    assert resources[0].type == "aws_vpc"
