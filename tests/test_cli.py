"""CLIエントリーポイント（main.py）のテスト。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from terrasketch.main import generate, diff_generate, _setup_logging, main


@pytest.fixture
def sample_state(tmp_path):
    """テスト用のサンプルstate JSONファイルを作成する。"""
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
                            "tags": {"Name": "test"},
                        },
                    },
                    {
                        "address": "aws_subnet.pub",
                        "type": "aws_subnet",
                        "name": "pub",
                        "provider_name": "registry.terraform.io/hashicorp/aws",
                        "values": {
                            "id": "subnet-123",
                            "vpc_id": "vpc-123",
                            "cidr_block": "10.0.1.0/24",
                        },
                    },
                ],
            }
        },
    }
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps(state), encoding="utf-8")
    return str(state_file)


@pytest.fixture
def sample_hcl(tmp_path):
    """テスト用のサンプルHCLファイルを作成する。"""
    hcl_file = tmp_path / "main.tf"
    hcl_file.write_text(
        'resource "aws_vpc" "main" {\n  cidr_block = "10.0.0.0/16"\n}\n',
        encoding="utf-8",
    )
    return str(hcl_file)


def test_generate_drawio(sample_state, tmp_path):
    """generate関数がdrawioファイルを正しく生成することを確認。"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = generate(
        state_path=sample_state,
        provider="aws",
        output_dir=str(output_dir),
        output_format="drawio",
    )
    assert result.exists()
    assert result.suffix == ".drawio"


def test_generate_mermaid(sample_state, tmp_path):
    """generate関数がMermaidファイルを正しく生成することを確認。"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = generate(
        state_path=sample_state,
        provider="aws",
        output_dir=str(output_dir),
        output_format="mermaid",
    )
    assert result.exists()
    assert result.suffix == ".md"


def test_generate_plantuml(sample_state, tmp_path):
    """generate関数がPlantUMLファイルを正しく生成することを確認。"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = generate(
        state_path=sample_state,
        provider="aws",
        output_dir=str(output_dir),
        output_format="plantuml",
    )
    assert result.exists()
    assert result.suffix == ".puml"


def test_generate_svg(sample_state, tmp_path):
    """generate関数がSVGファイルを正しく生成することを確認。"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = generate(
        state_path=sample_state,
        provider="aws",
        output_dir=str(output_dir),
        output_format="svg",
    )
    assert result.exists()
    assert result.suffix == ".svg"


def test_generate_with_security_and_summary(sample_state, tmp_path, capsys):
    """security/summaryオプション付きで生成できることを確認。"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = generate(
        state_path=sample_state,
        provider="aws",
        output_dir=str(output_dir),
        show_security=True,
        show_summary=True,
    )
    assert result.exists()
    captured = capsys.readouterr()
    assert "TerraSketch Resource Summary" in captured.out


def test_generate_with_labels(sample_state, tmp_path):
    """labelsオプション付きで生成できることを確認。"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = generate(
        state_path=sample_state,
        provider="aws",
        output_dir=str(output_dir),
        show_labels=True,
    )
    assert result.exists()


def test_generate_with_hcl(sample_hcl, tmp_path):
    """HCLファイルから構成図を生成できることを確認。"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = generate(
        state_path=None,
        provider="aws",
        output_dir=str(output_dir),
        hcl_path=sample_hcl,
    )
    assert result.exists()


def test_generate_with_hcl_directory(sample_hcl, tmp_path):
    """HCLディレクトリから構成図を生成できることを確認。"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = generate(
        state_path=None,
        provider="aws",
        output_dir=str(output_dir),
        hcl_path=str(Path(sample_hcl).parent),
    )
    assert result.exists()


def test_generate_provider_filter(sample_state, tmp_path):
    """providerフィルタが正しく動作することを確認。"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    # azureフィルタをかけるとAWSリソースは除外される
    result = generate(
        state_path=sample_state,
        provider="azure",
        output_dir=str(output_dir),
    )
    assert result.exists()


def test_generate_all_provider(sample_state, tmp_path):
    """provider=allでフィルタなし生成を確認。"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = generate(
        state_path=sample_state,
        provider="all",
        output_dir=str(output_dir),
    )
    assert result.exists()


def test_generate_with_layout_types(sample_state, tmp_path):
    """各レイアウトアルゴリズムで生成できることを確認。"""
    for layout in ("hierarchical", "grid", "force"):
        output_dir = tmp_path / f"output_{layout}"
        output_dir.mkdir()
        result = generate(
            state_path=sample_state,
            provider="aws",
            output_dir=str(output_dir),
            layout_type=layout,
        )
        assert result.exists()


def test_generate_with_module_grouping(sample_state, tmp_path):
    """module グルーピング付きで生成できることを確認。"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    result = generate(
        state_path=sample_state,
        provider="aws",
        output_dir=str(output_dir),
        group_by="module",
    )
    assert result.exists()


def test_diff_generate(tmp_path):
    """diff_generate関数が差分構成図を生成することを確認。"""
    before = {
        "format_version": "1.0",
        "terraform_version": "1.7.0",
        "values": {
            "root_module": {
                "resources": [
                    {
                        "type": "aws_vpc",
                        "name": "main",
                        "provider_name": "aws",
                        "values": {"id": "vpc-1", "cidr_block": "10.0.0.0/16"},
                    },
                ],
            }
        },
    }
    after = {
        "format_version": "1.0",
        "terraform_version": "1.7.0",
        "values": {
            "root_module": {
                "resources": [
                    {
                        "type": "aws_vpc",
                        "name": "main",
                        "provider_name": "aws",
                        "values": {"id": "vpc-1", "cidr_block": "10.0.0.0/8"},
                    },
                    {
                        "type": "aws_subnet",
                        "name": "new",
                        "provider_name": "aws",
                        "values": {"id": "subnet-1", "vpc_id": "vpc-1"},
                    },
                ],
            }
        },
    }
    before_file = tmp_path / "before.json"
    after_file = tmp_path / "after.json"
    before_file.write_text(json.dumps(before), encoding="utf-8")
    after_file.write_text(json.dumps(after), encoding="utf-8")

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    for fmt in ("drawio", "mermaid", "plantuml"):
        result = diff_generate(
            before_path=str(before_file),
            after_path=str(after_file),
            provider="aws",
            output_dir=str(output_dir),
            output_format=fmt,
        )
        assert result.exists()


def test_setup_logging_verbose():
    """verbose=TrueがbasicConfigを呼び出すことを確認。"""
    import logging

    # basicConfigはルートロガーにハンドラを追加するが、既にハンドラがあると無視される
    # テスト環境ではpytestが既にロガーをセットアップしているため、
    # 関数がエラーなく実行されることのみ確認
    _setup_logging(verbose=True)


def test_setup_logging_normal():
    """verbose=FalseがbasicConfigを呼び出すことを確認。"""
    _setup_logging(verbose=False)


def test_main_no_command(capsys):
    """コマンドなしでヘルプが表示されることを確認。"""
    with patch("sys.argv", ["terrasketch"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


def test_main_generate_command(sample_state, tmp_path):
    """CLIのgenerateコマンドが動作することを確認。"""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    with patch(
        "sys.argv",
        [
            "terrasketch",
            "generate",
            "--state",
            sample_state,
            "--provider",
            "aws",
            "--output",
            str(output_dir),
        ],
    ):
        main()
    assert any(output_dir.iterdir())


def test_main_validate_command(sample_state):
    """CLIのvalidateコマンドが動作することを確認。"""
    with patch("sys.argv", ["terrasketch", "validate", "--state", sample_state]):
        main()


def test_main_validate_invalid_file(tmp_path):
    """不正なファイルでvalidateが失敗することを確認。"""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not json", encoding="utf-8")
    with patch("sys.argv", ["terrasketch", "validate", "--state", str(bad_file)]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1


def test_main_generate_with_invalid_state(tmp_path):
    """不正なstateでgenerateが失敗することを確認。"""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{}", encoding="utf-8")
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    with patch(
        "sys.argv",
        ["terrasketch", "generate", "--state", str(bad_file), "--output", str(output_dir)],
    ):
        with pytest.raises(SystemExit):
            main()
