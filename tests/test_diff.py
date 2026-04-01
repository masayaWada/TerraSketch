"""diffモジュールのテスト。"""

import json
from pathlib import Path

import pytest

from terrasketch.diff.comparator import (
    DiffStatus,
    _diff_attributes,
    build_diff_graph,
    compare_states,
)


def _write_state(tmp_path: Path, filename: str, resources: list[dict]) -> Path:
    """テスト用のstate JSONファイルを作成する。"""
    state = {
        "values": {
            "root_module": {
                "resources": resources,
            }
        }
    }
    path = tmp_path / filename
    path.write_text(json.dumps(state), encoding="utf-8")
    return path


def test_diff_added_resource(tmp_path):
    """新規追加リソースがADDEDとして検出されることを確認。"""
    before = _write_state(tmp_path, "before.json", [
        {"type": "aws_vpc", "name": "main", "values": {"id": "vpc-1"}, "provider_name": "aws"},
    ])
    after = _write_state(tmp_path, "after.json", [
        {"type": "aws_vpc", "name": "main", "values": {"id": "vpc-1"}, "provider_name": "aws"},
        {"type": "aws_subnet", "name": "pub", "values": {"id": "sub-1"}, "provider_name": "aws"},
    ])
    resources, diff_status, _ = compare_states(str(before), str(after))
    assert diff_status["aws_subnet.pub"] == DiffStatus.ADDED
    assert diff_status["aws_vpc.main"] == DiffStatus.UNCHANGED


def test_diff_removed_resource(tmp_path):
    """削除リソースがREMOVEDとして検出されることを確認。"""
    before = _write_state(tmp_path, "before.json", [
        {"type": "aws_vpc", "name": "main", "values": {"id": "vpc-1"}, "provider_name": "aws"},
        {"type": "aws_subnet", "name": "pub", "values": {"id": "sub-1"}, "provider_name": "aws"},
    ])
    after = _write_state(tmp_path, "after.json", [
        {"type": "aws_vpc", "name": "main", "values": {"id": "vpc-1"}, "provider_name": "aws"},
    ])
    resources, diff_status, _ = compare_states(str(before), str(after))
    assert diff_status["aws_subnet.pub"] == DiffStatus.REMOVED


def test_diff_modified_resource(tmp_path):
    """変更リソースがMODIFIEDとして検出されることを確認。"""
    before = _write_state(tmp_path, "before.json", [
        {"type": "aws_instance", "name": "web", "values": {"id": "i-1", "instance_type": "t3.micro"}, "provider_name": "aws"},
    ])
    after = _write_state(tmp_path, "after.json", [
        {"type": "aws_instance", "name": "web", "values": {"id": "i-1", "instance_type": "t3.large"}, "provider_name": "aws"},
    ])
    resources, diff_status, changed_attrs = compare_states(str(before), str(after))
    assert diff_status["aws_instance.web"] == DiffStatus.MODIFIED
    assert "instance_type" in changed_attrs["aws_instance.web"]


def test_diff_attributes():
    """属性差分の検出が正しく機能することを確認。"""
    before = {"name": "old", "size": 10, "tags": {"env": "dev"}}
    after = {"name": "new", "size": 10, "color": "blue"}
    changes = _diff_attributes(before, after)
    assert "name" in changes
    assert "color" in changes
    assert "tags" in changes
    assert "size" not in changes


def test_build_diff_graph(tmp_path):
    """diffグラフにdiff_status属性が正しく付与されることを確認。"""
    before = _write_state(tmp_path, "before.json", [
        {"type": "aws_vpc", "name": "main", "values": {"id": "vpc-1"}, "provider_name": "aws"},
    ])
    after = _write_state(tmp_path, "after.json", [
        {"type": "aws_vpc", "name": "main", "values": {"id": "vpc-1"}, "provider_name": "aws"},
        {"type": "aws_subnet", "name": "pub", "values": {"id": "sub-1"}, "provider_name": "aws"},
    ])
    resources, diff_status, changed_attrs = compare_states(str(before), str(after))
    graph = build_diff_graph(resources, diff_status, changed_attrs)
    assert graph.nodes["aws_subnet.pub"]["diff_status"] == "added"
    assert graph.nodes["aws_vpc.main"]["diff_status"] == "unchanged"


def test_diff_drawio_rendering(tmp_path):
    """diff結果がdraw.ioで色分けレンダリングされることを確認。"""
    from terrasketch.layout.engine import calculate_layout
    from terrasketch.renderer.drawio_renderer import DrawioRenderer

    before = _write_state(tmp_path, "before.json", [
        {"type": "aws_vpc", "name": "main", "values": {"id": "vpc-1"}, "provider_name": "aws"},
    ])
    after = _write_state(tmp_path, "after.json", [
        {"type": "aws_vpc", "name": "main", "values": {"id": "vpc-1"}, "provider_name": "aws"},
        {"type": "aws_instance", "name": "web", "values": {"id": "i-1"}, "provider_name": "aws"},
    ])
    resources, diff_status, changed_attrs = compare_states(str(before), str(after))
    graph = build_diff_graph(resources, diff_status, changed_attrs)
    positions = calculate_layout(graph)

    renderer = DrawioRenderer()
    result = renderer.render(graph, positions, tmp_path / "diff.drawio", diff_mode=True)
    content = result.read_text(encoding="utf-8")
    assert "[NEW]" in content
    assert "fillColor=#c8e6c9" in content
