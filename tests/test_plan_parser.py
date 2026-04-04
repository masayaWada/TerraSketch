"""Terraform plan パーサーのテスト。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from terrasketch.diff.comparator import DiffStatus
from terrasketch.parser.plan_parser import parse_plan


# --- サンプルplanファイルの解析テスト ---


class TestParsePlanSample:
    """サンプルplanファイルの解析テスト。"""

    def test_parse_sample_plan(self) -> None:
        """サンプルplanファイルが正しく解析される。"""
        resources, diff_status, changed_attrs = parse_plan("samples/sample_plan.json")
        assert len(resources) >= 4  # VPC, Subnet, 新EC2, SG + 削除EC2

    def test_create_action_detected(self) -> None:
        """create アクションが ADDED として検出される。"""
        resources, diff_status, _ = parse_plan("samples/sample_plan.json")
        assert diff_status.get("aws_instance.web_new") == DiffStatus.ADDED

    def test_delete_action_detected(self) -> None:
        """delete アクションが REMOVED として検出される。"""
        resources, diff_status, _ = parse_plan("samples/sample_plan.json")
        assert diff_status.get("aws_instance.old_web") == DiffStatus.REMOVED

    def test_update_action_detected(self) -> None:
        """update アクションが MODIFIED として検出される。"""
        resources, diff_status, _ = parse_plan("samples/sample_plan.json")
        assert diff_status.get("aws_security_group.web") == DiffStatus.MODIFIED

    def test_noop_action_detected(self) -> None:
        """no-op アクションが UNCHANGED として検出される。"""
        resources, diff_status, _ = parse_plan("samples/sample_plan.json")
        assert diff_status.get("aws_vpc.main") == DiffStatus.UNCHANGED

    def test_changed_attrs_for_modified(self) -> None:
        """変更属性がMODIFIEDリソースに記録される。"""
        _, _, changed_attrs = parse_plan("samples/sample_plan.json")
        sg_changes = changed_attrs.get("aws_security_group.web", {})
        assert "description" in sg_changes

    def test_deleted_resource_included(self) -> None:
        """削除予定のリソースもリソースリストに含まれる。"""
        resources, _, _ = parse_plan("samples/sample_plan.json")
        addrs = {r.address for r in resources}
        assert "aws_instance.old_web" in addrs


# --- エッジケーステスト ---


class TestParsePlanEdgeCases:
    """plan パーサーのエッジケーステスト。"""

    def test_file_not_found(self) -> None:
        """存在しないファイルでFileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            parse_plan("nonexistent_plan.json")

    def test_invalid_json_structure(self, tmp_path: Path) -> None:
        """planned_values がないJSONでValueError。"""
        plan_file = tmp_path / "bad_plan.json"
        plan_file.write_text('{"resource_changes": []}')
        with pytest.raises(ValueError, match="planned_values"):
            parse_plan(plan_file)

    def test_replace_action(self, tmp_path: Path) -> None:
        """delete+create（置換）がMODIFIEDとして検出される。"""
        plan_data = {
            "planned_values": {"root_module": {"resources": [
                {"address": "aws_instance.web", "type": "aws_instance", "name": "web",
                 "provider_name": "aws", "values": {"id": "i-new"}},
            ]}},
            "resource_changes": [{
                "address": "aws_instance.web",
                "type": "aws_instance",
                "name": "web",
                "change": {"actions": ["delete", "create"],
                           "before": {"id": "i-old"},
                           "after": {"id": "i-new"}},
            }],
        }
        plan_file = tmp_path / "replace_plan.json"
        plan_file.write_text(json.dumps(plan_data))
        _, diff_status, _ = parse_plan(plan_file)
        assert diff_status.get("aws_instance.web") == DiffStatus.MODIFIED

    def test_empty_resource_changes(self, tmp_path: Path) -> None:
        """resource_changes が空の場合。"""
        plan_data = {
            "planned_values": {"root_module": {"resources": [
                {"address": "aws_vpc.main", "type": "aws_vpc", "name": "main",
                 "provider_name": "aws", "values": {"id": "vpc-1"}},
            ]}},
            "resource_changes": [],
        }
        plan_file = tmp_path / "empty_changes.json"
        plan_file.write_text(json.dumps(plan_data))
        resources, diff_status, _ = parse_plan(plan_file)
        assert len(resources) == 1
        assert diff_status.get("aws_vpc.main") == DiffStatus.UNCHANGED

    def test_child_modules_in_plan(self, tmp_path: Path) -> None:
        """子モジュールのリソースも正しく抽出される。"""
        plan_data = {
            "planned_values": {"root_module": {
                "resources": [],
                "child_modules": [{
                    "address": "module.vpc",
                    "resources": [
                        {"address": "module.vpc.aws_vpc.main", "type": "aws_vpc",
                         "name": "main", "provider_name": "aws",
                         "values": {"id": "vpc-1"}},
                    ],
                }],
            }},
            "resource_changes": [{
                "address": "module.vpc.aws_vpc.main",
                "type": "aws_vpc",
                "name": "main",
                "change": {"actions": ["create"], "before": None, "after": {"id": "vpc-1"}},
            }],
        }
        plan_file = tmp_path / "module_plan.json"
        plan_file.write_text(json.dumps(plan_data))
        resources, diff_status, _ = parse_plan(plan_file)
        assert len(resources) == 1
        assert resources[0].module_path == "module.vpc"


# --- バリデーターテスト ---


class TestPlanValidation:
    """plan JSONバリデーションのテスト。"""

    def test_valid_plan_file(self) -> None:
        """正常なplanファイルの検証が通る。"""
        from terrasketch.parser.validator import validate_plan_file
        result = validate_plan_file("samples/sample_plan.json")
        assert result.valid

    def test_invalid_plan_missing_keys(self, tmp_path: Path) -> None:
        """必須キーが欠落したplanファイルの検証が失敗する。"""
        from terrasketch.parser.validator import validate_plan_file
        bad_file = tmp_path / "bad.json"
        bad_file.write_text('{"terraform_version": "1.6.0"}')
        result = validate_plan_file(bad_file)
        assert not result.valid
        assert any("planned_values" in e for e in result.errors)

    def test_state_file_detected_as_plan_error(self, tmp_path: Path) -> None:
        """stateファイルをplanとして検証するとヒントが表示される。"""
        from terrasketch.parser.validator import validate_plan_file
        state_file = tmp_path / "state.json"
        state_file.write_text('{"values": {"root_module": {"resources": []}}}')
        result = validate_plan_file(state_file)
        assert not result.valid
        assert any("state" in h for h in result.hints)

    def test_nonexistent_plan_file(self) -> None:
        """存在しないファイルで検証失敗。"""
        from terrasketch.parser.validator import validate_plan_file
        result = validate_plan_file("nonexistent.json")
        assert not result.valid


# --- レンダリング統合テスト ---


class TestPlanRendering:
    """plan構成図レンダリングの統合テスト。"""

    def test_plan_generate_drawio(self, tmp_path: Path) -> None:
        """planからdraw.io構成図が生成される。"""
        from terrasketch.main import plan_generate
        result = plan_generate(
            plan_path="samples/sample_plan.json",
            provider="aws",
            output_dir=str(tmp_path),
            output_format="drawio",
        )
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "mxfile" in content

    def test_plan_generate_mermaid(self, tmp_path: Path) -> None:
        """planからMermaid構成図が生成される。"""
        from terrasketch.main import plan_generate
        result = plan_generate(
            plan_path="samples/sample_plan.json",
            provider="aws",
            output_dir=str(tmp_path),
            output_format="mermaid",
        )
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "mermaid" in content
