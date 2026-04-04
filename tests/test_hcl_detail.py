"""HCLパーサーの詳細テスト。"""

from __future__ import annotations

from pathlib import Path

import pytest

from terrasketch.parser.hcl_parser import (
    _detect_provider,
    _extract_block,
    _extract_resources,
    _parse_attributes,
    _strip_comments,
    parse_hcl,
    parse_hcl_directory,
)


class TestStripComments:
    """_strip_commentsのテスト。"""

    def test_line_comment_hash(self):
        """#行コメントの除去を確認。"""
        result = _strip_comments('key = "value" # comment')
        assert "comment" not in result
        assert "key" in result

    def test_line_comment_slash(self):
        """//行コメントの除去を確認。"""
        result = _strip_comments('key = "value" // comment')
        assert "comment" not in result

    def test_block_comment(self):
        """ブロックコメントの除去を確認。"""
        result = _strip_comments('before /* block */ after')
        assert "block" not in result
        assert "before" in result
        assert "after" in result


class TestExtractBlock:
    """_extract_blockのテスト。"""

    def test_simple_block(self):
        """単純なブロック抽出を確認。"""
        result = _extract_block('{ key = "val" }', 0)
        assert result is not None
        assert "key" in result

    def test_nested_blocks(self):
        """ネストされたブロックの正しい抽出を確認。"""
        content = '{ outer { inner = 1 } end = 2 }'
        result = _extract_block(content, 0)
        assert "inner" in result
        assert "end" in result

    def test_no_opening_brace(self):
        """開き括弧がない場合Noneが返ることを確認。"""
        assert _extract_block("no brace", 0) is None

    def test_unbalanced_braces(self):
        """閉じ括弧がない場合Noneが返ることを確認。"""
        assert _extract_block("{ unclosed", 0) is None

    def test_string_with_braces(self):
        """文字列内の括弧が無視されることを確認。"""
        content = '{ key = "{ not a block }" }'
        result = _extract_block(content, 0)
        assert result is not None
        assert "not a block" in result


class TestParseAttributes:
    """_parse_attributesのテスト。"""

    def test_string_value(self):
        """文字列値の解析を確認。"""
        attrs = _parse_attributes('  name = "test"')
        assert attrs["name"] == "test"

    def test_integer_value(self):
        """整数値の解析を確認。"""
        attrs = _parse_attributes("  count = 3 ")
        assert attrs["count"] == 3

    def test_float_value(self):
        """浮動小数点値の解析を確認。"""
        attrs = _parse_attributes("  rate = 1.5 ")
        assert attrs["rate"] == 1.5

    def test_boolean_value(self):
        """ブール値の解析を確認。"""
        attrs = _parse_attributes("  enabled = true \n  disabled = false ")
        assert attrs["enabled"] is True
        assert attrs["disabled"] is False

    def test_list_value(self):
        """リスト値の解析を確認。"""
        attrs = _parse_attributes('  cidrs = ["10.0.0.0/8", "172.16.0.0/12"]')
        assert attrs["cidrs"] == ["10.0.0.0/8", "172.16.0.0/12"]

    def test_tags_block(self):
        """tagsブロックの解析を確認。"""
        block = '  tags = {\n    Name = "test"\n    Env = "dev"\n  }'
        attrs = _parse_attributes(block)
        assert attrs["tags"]["Name"] == "test"
        assert attrs["tags"]["Env"] == "dev"


class TestDetectProvider:
    """_detect_providerのテスト。"""

    def test_aws(self):
        assert _detect_provider("aws_vpc") == "registry.terraform.io/hashicorp/aws"

    def test_azure(self):
        assert _detect_provider("azurerm_virtual_network") == "registry.terraform.io/hashicorp/azurerm"

    def test_gcp(self):
        assert _detect_provider("google_compute_network") == "registry.terraform.io/hashicorp/google"

    def test_unknown(self):
        assert _detect_provider("custom_resource") == "unknown"


class TestExtractResources:
    """_extract_resourcesのテスト。"""

    def test_no_resources(self):
        """リソースブロックがない場合空リストが返ることを確認。"""
        result = _extract_resources('variable "name" { default = "test" }')
        assert result == []

    def test_multiple_resources(self):
        """複数リソースが正しく抽出されることを確認。"""
        hcl = '''
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}
resource "aws_subnet" "pub" {
  vpc_id = "vpc-123"
  cidr_block = "10.0.1.0/24"
}
'''
        result = _extract_resources(hcl)
        assert len(result) == 2
        assert result[0].type == "aws_vpc"
        assert result[1].type == "aws_subnet"

    def test_block_extraction_failure(self):
        """不正なブロックがスキップされることを確認。"""
        hcl = 'resource "aws_vpc" "bad" {'  # 閉じ括弧なし
        result = _extract_resources(hcl)
        assert len(result) == 0


class TestParseHcl:
    """parse_hcl / parse_hcl_directoryのテスト。"""

    def test_file_not_found(self):
        """存在しないファイルでFileNotFoundErrorが発生することを確認。"""
        with pytest.raises(FileNotFoundError):
            parse_hcl("/nonexistent/file.tf")

    def test_directory_not_found(self):
        """存在しないディレクトリでFileNotFoundErrorが発生することを確認。"""
        with pytest.raises(FileNotFoundError):
            parse_hcl_directory("/nonexistent/dir")

    def test_parse_valid_file(self, tmp_path):
        """有効なHCLファイルの解析を確認。"""
        f = tmp_path / "main.tf"
        f.write_text('resource "aws_vpc" "main" {\n  cidr_block = "10.0.0.0/16"\n}\n', encoding="utf-8")
        result = parse_hcl(str(f))
        assert len(result) == 1
        assert result[0].type == "aws_vpc"
        assert result[0].attributes["cidr_block"] == "10.0.0.0/16"

    def test_parse_directory(self, tmp_path):
        """ディレクトリ内の全tfファイルが解析されることを確認。"""
        (tmp_path / "vpc.tf").write_text('resource "aws_vpc" "main" {\n  cidr_block = "10.0.0.0/16"\n}\n', encoding="utf-8")
        (tmp_path / "subnet.tf").write_text('resource "aws_subnet" "pub" {\n  cidr_block = "10.0.1.0/24"\n}\n', encoding="utf-8")
        result = parse_hcl_directory(str(tmp_path))
        assert len(result) == 2
