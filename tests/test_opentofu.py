"""OpenTofu対応のテスト。

OpenTofu state形式の自動検出、パース、バリデーション、
構成図生成パイプラインの動作を検証する。
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from terrasketch.parser.state_parser import Resource, detect_runtime, parse_state
from terrasketch.parser.validator import validate_state_file, validate_plan_file


# === サンプルデータ ===

SAMPLE_OPENTOFU_STATE = Path("samples/sample_opentofu_state.json")


def _make_state(runtime: str = "opentofu") -> dict:
    """テスト用のstate辞書を生成する。"""
    state = {
        "format_version": "1.0",
        "values": {
            "root_module": {
                "resources": [
                    {
                        "address": "aws_vpc.main",
                        "mode": "managed",
                        "type": "aws_vpc",
                        "name": "main",
                        "provider_name": "registry.opentofu.org/hashicorp/aws",
                        "values": {
                            "id": "vpc-123",
                            "cidr_block": "10.0.0.0/16",
                            "tags": {"Name": "test-vpc"},
                        },
                    }
                ]
            }
        },
    }
    if runtime == "opentofu":
        state["opentofu_version"] = "1.8.0"
    else:
        state["terraform_version"] = "1.7.0"
    return state


def _write_json(data: dict, path: Path) -> Path:
    """辞書をJSONファイルに書き出す。"""
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


# === detect_runtime テスト ===


class TestDetectRuntime:
    """ランタイム自動検出のテスト。"""

    def test_opentofu形式を検出(self) -> None:
        state = {"opentofu_version": "1.8.0", "values": {}}
        assert detect_runtime(state) == "opentofu"

    def test_terraform形式を検出(self) -> None:
        state = {"terraform_version": "1.7.0", "values": {}}
        assert detect_runtime(state) == "terraform"

    def test_バージョンキーなしはterraformと判定(self) -> None:
        state = {"values": {}}
        assert detect_runtime(state) == "terraform"

    def test_両方のキーがある場合はopentofuを優先(self) -> None:
        state = {"opentofu_version": "1.8.0", "terraform_version": "1.7.0", "values": {}}
        assert detect_runtime(state) == "opentofu"


# === parse_state テスト ===


class TestParseStateOpenTofu:
    """OpenTofu state JSONのパーステスト。"""

    def test_サンプルファイルからリソースを抽出(self) -> None:
        resources = parse_state(SAMPLE_OPENTOFU_STATE)
        assert len(resources) == 3
        types = {r.type for r in resources}
        assert "aws_vpc" in types
        assert "aws_subnet" in types
        assert "aws_instance" in types

    def test_runtime_autoでOpenTofu形式を正しくパース(self) -> None:
        resources = parse_state(SAMPLE_OPENTOFU_STATE, runtime="auto")
        assert len(resources) == 3

    def test_runtime_opentofuを明示指定(self) -> None:
        resources = parse_state(SAMPLE_OPENTOFU_STATE, runtime="opentofu")
        assert len(resources) == 3

    def test_runtime_terraformを明示指定してもパース可能(self) -> None:
        """OpenTofuファイルでもruntime=terraformでパースできる（構造は同一）。"""
        resources = parse_state(SAMPLE_OPENTOFU_STATE, runtime="terraform")
        assert len(resources) == 3

    def test_一時ファイルでOpenTofu形式をパース(self, tmp_path: Path) -> None:
        state = _make_state("opentofu")
        path = _write_json(state, tmp_path / "state.json")
        resources = parse_state(path, runtime="auto")
        assert len(resources) == 1
        assert resources[0].type == "aws_vpc"

    def test_provider_nameにopentofuレジストリが含まれる(self) -> None:
        resources = parse_state(SAMPLE_OPENTOFU_STATE)
        for r in resources:
            assert "opentofu" in r.provider

    def test_リソース属性が正しく抽出される(self) -> None:
        resources = parse_state(SAMPLE_OPENTOFU_STATE)
        vpc = next(r for r in resources if r.type == "aws_vpc")
        assert vpc.attributes["cidr_block"] == "10.0.0.0/16"
        assert vpc.attributes["tags"]["Name"] == "main-vpc"


# === バリデーター テスト ===


class TestValidatorOpenTofu:
    """OpenTofu形式のバリデーションテスト。"""

    def test_OpenTofu_stateファイルがvalid(self) -> None:
        result = validate_state_file(SAMPLE_OPENTOFU_STATE)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_valuesキーなしのOpenTofuファイル(self, tmp_path: Path) -> None:
        data = {"opentofu_version": "1.8.0", "format_version": "1.0"}
        path = _write_json(data, tmp_path / "bad.json")
        result = validate_state_file(path)
        assert result.valid is False
        assert any("values" in e for e in result.errors)
        assert any("OpenTofu" in h for h in result.hints)

    def test_OpenTofu_plan形式の誤指定を検出(self, tmp_path: Path) -> None:
        data = {
            "opentofu_version": "1.8.0",
            "resource_changes": [],
            "planned_values": {"root_module": {}},
        }
        path = _write_json(data, tmp_path / "plan.json")
        result = validate_state_file(path)
        assert result.valid is False
        assert any("OpenTofu" in h or "tofu" in h for h in result.hints)

    def test_OpenTofu_plan_JSONがvalid(self, tmp_path: Path) -> None:
        data = {
            "opentofu_version": "1.8.0",
            "planned_values": {"root_module": {"resources": []}},
            "resource_changes": [],
        }
        path = _write_json(data, tmp_path / "plan.json")
        result = validate_plan_file(path)
        assert result.valid is True


# === 構成図生成パイプライン テスト ===


class TestOpenTofuPipeline:
    """OpenTofu stateからの構成図生成パイプライン統合テスト。"""

    def test_グラフ構築が成功する(self) -> None:
        from terrasketch.graph.builder import build_graph

        resources = parse_state(SAMPLE_OPENTOFU_STATE)
        graph = build_graph(resources)
        assert graph.number_of_nodes() > 0

    def test_レイアウト計算が成功する(self) -> None:
        from terrasketch.graph.builder import build_graph
        from terrasketch.layout.engine import calculate_layout

        resources = parse_state(SAMPLE_OPENTOFU_STATE)
        graph = build_graph(resources)
        positions = calculate_layout(graph)
        assert len(positions) > 0

    def test_Mermaid出力が生成される(self, tmp_path: Path) -> None:
        from terrasketch.main import generate

        result = generate(
            state_path=str(SAMPLE_OPENTOFU_STATE),
            provider="aws",
            output_dir=str(tmp_path),
            output_format="mermaid",
            runtime="opentofu",
        )
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "flowchart" in content

    def test_drawio出力が生成される(self, tmp_path: Path) -> None:
        from terrasketch.main import generate

        result = generate(
            state_path=str(SAMPLE_OPENTOFU_STATE),
            provider="aws",
            output_dir=str(tmp_path),
            output_format="drawio",
            runtime="auto",
        )
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "mxfile" in content

    def test_SVG出力が生成される(self, tmp_path: Path) -> None:
        from terrasketch.main import generate

        result = generate(
            state_path=str(SAMPLE_OPENTOFU_STATE),
            provider="aws",
            output_dir=str(tmp_path),
            output_format="svg",
            runtime="auto",
        )
        assert result.exists()

    def test_HTML出力が生成される(self, tmp_path: Path) -> None:
        from terrasketch.main import generate

        result = generate(
            state_path=str(SAMPLE_OPENTOFU_STATE),
            provider="aws",
            output_dir=str(tmp_path),
            output_format="html",
            runtime="auto",
        )
        assert result.exists()

    def test_PlantUML出力が生成される(self, tmp_path: Path) -> None:
        from terrasketch.main import generate

        result = generate(
            state_path=str(SAMPLE_OPENTOFU_STATE),
            provider="aws",
            output_dir=str(tmp_path),
            output_format="plantuml",
            runtime="auto",
        )
        assert result.exists()
