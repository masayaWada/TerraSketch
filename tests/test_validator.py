"""入力ファイルバリデーターのテスト。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from terrasketch.parser.validator import (
    ValidationResult,
    format_validation_result,
    validate_hcl_file,
    validate_state_file,
)


class TestValidateStateFile:
    """validate_state_fileのテスト群。"""

    def test_valid_state(self, tmp_path):
        """有効なstateファイルが検証を通過することを確認。"""
        state = {
            "values": {
                "root_module": {
                    "resources": [],
                }
            }
        }
        f = tmp_path / "state.json"
        f.write_text(json.dumps(state), encoding="utf-8")
        result = validate_state_file(str(f))
        assert result.valid is True
        assert result.errors == []

    def test_file_not_found(self):
        """存在しないファイルでエラーが出ることを確認。"""
        result = validate_state_file("/nonexistent/state.json")
        assert result.valid is False
        assert any("見つかりません" in e for e in result.errors)

    def test_directory_given(self, tmp_path):
        """ディレクトリを指定した場合のエラーを確認。"""
        result = validate_state_file(str(tmp_path))
        assert result.valid is False
        assert any("ディレクトリ" in e for e in result.errors)

    def test_wrong_extension(self, tmp_path):
        """不正な拡張子で警告が出ることを確認。"""
        f = tmp_path / "state.txt"
        f.write_text('{"values":{"root_module":{"resources":[]}}}', encoding="utf-8")
        result = validate_state_file(str(f))
        assert any("拡張子" in e for e in result.errors)

    def test_empty_file(self, tmp_path):
        """空ファイルでエラーが出ることを確認。"""
        f = tmp_path / "empty.json"
        f.write_text("", encoding="utf-8")
        result = validate_state_file(str(f))
        assert result.valid is False
        assert any("空" in e for e in result.errors)

    def test_invalid_json(self, tmp_path):
        """不正なJSONでエラーが出ることを確認。"""
        f = tmp_path / "bad.json"
        f.write_text("{broken json", encoding="utf-8")
        result = validate_state_file(str(f))
        assert result.valid is False
        assert any("JSON" in e for e in result.errors)

    def test_json_array(self, tmp_path):
        """JSONの配列がエラーになることを確認。"""
        f = tmp_path / "array.json"
        f.write_text("[1, 2, 3]", encoding="utf-8")
        result = validate_state_file(str(f))
        assert result.valid is False
        assert any("オブジェクト" in e for e in result.errors)

    def test_missing_values_key(self, tmp_path):
        """valuesキーがない場合のエラーを確認。"""
        f = tmp_path / "no_values.json"
        f.write_text('{"terraform_version": "1.0"}', encoding="utf-8")
        result = validate_state_file(str(f))
        assert result.valid is False
        assert any("values" in e for e in result.errors)

    def test_plan_file_hint(self, tmp_path):
        """plan出力に対するヒントが表示されることを確認。"""
        f = tmp_path / "plan.json"
        f.write_text('{"resource_changes": []}', encoding="utf-8")
        result = validate_state_file(str(f))
        assert result.valid is False
        assert any("plan" in h for h in result.hints)

    def test_missing_root_module(self, tmp_path):
        """root_moduleがない場合のエラーを確認。"""
        f = tmp_path / "no_root.json"
        f.write_text('{"values": {}}', encoding="utf-8")
        result = validate_state_file(str(f))
        assert result.valid is False
        assert any("root_module" in e for e in result.errors)

    def test_tfstate_extension(self, tmp_path):
        """tfstate拡張子が受け入れられることを確認。"""
        f = tmp_path / "terraform.tfstate"
        f.write_text('{"values":{"root_module":{"resources":[]}}}', encoding="utf-8")
        result = validate_state_file(str(f))
        assert result.valid is True


class TestValidateHclFile:
    """validate_hcl_fileのテスト群。"""

    def test_valid_hcl(self, tmp_path):
        """有効なHCLファイルが検証を通過することを確認。"""
        f = tmp_path / "main.tf"
        f.write_text('resource "aws_vpc" "main" {\n  cidr_block = "10.0.0.0/16"\n}\n', encoding="utf-8")
        result = validate_hcl_file(str(f))
        assert result.valid is True

    def test_file_not_found(self):
        """存在しないファイルでエラーが出ることを確認。"""
        result = validate_hcl_file("/nonexistent/main.tf")
        assert result.valid is False

    def test_directory_with_tf_files(self, tmp_path):
        """tfファイルを含むディレクトリが検証を通過することを確認。"""
        (tmp_path / "main.tf").write_text('resource "aws_vpc" "main" {}', encoding="utf-8")
        result = validate_hcl_file(str(tmp_path))
        assert result.valid is True

    def test_directory_without_tf_files(self, tmp_path):
        """tfファイルがないディレクトリでエラーが出ることを確認。"""
        (tmp_path / "readme.md").write_text("nothing", encoding="utf-8")
        result = validate_hcl_file(str(tmp_path))
        assert result.valid is False
        assert any(".tf" in e for e in result.errors)

    def test_wrong_extension(self, tmp_path):
        """不正な拡張子でエラーが出ることを確認。"""
        f = tmp_path / "main.py"
        f.write_text('resource "aws_vpc" "main" {}', encoding="utf-8")
        result = validate_hcl_file(str(f))
        assert result.valid is False
        assert any("拡張子" in e for e in result.errors)

    def test_empty_file(self, tmp_path):
        """空ファイルでエラーが出ることを確認。"""
        f = tmp_path / "empty.tf"
        f.write_text("", encoding="utf-8")
        result = validate_hcl_file(str(f))
        assert result.valid is False
        assert any("空" in e for e in result.errors)

    def test_no_resource_block(self, tmp_path):
        """resourceブロックがないファイルでエラーが出ることを確認。"""
        f = tmp_path / "variables.tf"
        f.write_text('variable "name" {\n  default = "test"\n}\n', encoding="utf-8")
        result = validate_hcl_file(str(f))
        assert result.valid is False
        assert any("resource" in e for e in result.errors)


class TestFormatValidationResult:
    """format_validation_resultのテスト群。"""

    def test_valid_result(self):
        """有効な結果がOKメッセージになることを確認。"""
        r = ValidationResult(valid=True, errors=[], hints=[])
        msg = format_validation_result(r)
        assert "検証OK" in msg

    def test_error_result(self):
        """エラー結果がエラーメッセージを含むことを確認。"""
        r = ValidationResult(
            valid=False,
            errors=["テストエラー"],
            hints=["テストヒント"],
        )
        msg = format_validation_result(r)
        assert "検証エラー" in msg
        assert "テストエラー" in msg
        assert "テストヒント" in msg
