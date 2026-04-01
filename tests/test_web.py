"""Web UIサーバーモジュールのテスト。"""

from __future__ import annotations

import json
import threading
import time
from http.client import HTTPConnection
from pathlib import Path

import pytest

from terrasketch.web.server import TerraSketchHandler, _parse_multipart, start_server


def test_parse_multipart_basic():
    """multipart/form-dataの基本的な解析を確認。"""
    boundary = b"----WebKitBoundary123"
    body = (
        b"------WebKitBoundary123\r\n"
        b'Content-Disposition: form-data; name="provider"\r\n'
        b"\r\n"
        b"aws\r\n"
        b"------WebKitBoundary123\r\n"
        b'Content-Disposition: form-data; name="format"\r\n'
        b"\r\n"
        b"mermaid\r\n"
        b"------WebKitBoundary123\r\n"
        b'Content-Disposition: form-data; name="file"; filename="state.json"\r\n'
        b"Content-Type: application/json\r\n"
        b"\r\n"
        b'{"values":{"root_module":{"resources":[]}}}\r\n'
        b"------WebKitBoundary123--\r\n"
    )

    fields, file_data, file_name = _parse_multipart(body, boundary)

    assert fields["provider"] == "aws"
    assert fields["format"] == "mermaid"
    assert file_name == "state.json"
    assert file_data is not None
    assert b"root_module" in file_data


def test_parse_multipart_no_file():
    """ファイルなしのmultipartを解析した場合の動作を確認。"""
    boundary = b"----boundary"
    body = (
        b"------boundary\r\n"
        b'Content-Disposition: form-data; name="provider"\r\n'
        b"\r\n"
        b"azure\r\n"
        b"------boundary--\r\n"
    )

    fields, file_data, file_name = _parse_multipart(body, boundary)
    assert fields["provider"] == "azure"
    assert file_data is None


def test_template_exists():
    """index.htmlテンプレートが存在することを確認。"""
    template_path = Path(__file__).parent.parent / "terrasketch" / "web" / "templates" / "index.html"
    assert template_path.exists()
    content = template_path.read_text(encoding="utf-8")
    assert "TerraSketch" in content
    assert "<form" in content


def test_template_has_upload_form():
    """テンプレートにファイルアップロードフォームが含まれることを確認。"""
    template_path = Path(__file__).parent.parent / "terrasketch" / "web" / "templates" / "index.html"
    content = template_path.read_text(encoding="utf-8")
    assert 'type="file"' in content
    assert "provider" in content
    assert "format" in content
