"""Web UIサーバーの統合テスト。"""

from __future__ import annotations

import json
import threading
import time
from http.client import HTTPConnection
from pathlib import Path

import pytest

from terrasketch.web.server import TerraSketchHandler, _parse_multipart, _read_template


@pytest.fixture
def server():
    """テスト用HTTPサーバーを起動する。"""
    from http.server import HTTPServer

    srv = HTTPServer(("127.0.0.1", 0), TerraSketchHandler)
    port = srv.server_address[1]
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield port
    srv.shutdown()


def test_get_index(server):
    """GETリクエストでindex.htmlが返ることを確認。"""
    conn = HTTPConnection("127.0.0.1", server)
    conn.request("GET", "/")
    resp = conn.getresponse()
    assert resp.status == 200
    body = resp.read().decode("utf-8")
    assert "TerraSketch" in body
    conn.close()


def test_get_404(server):
    """存在しないパスで404が返ることを確認。"""
    conn = HTTPConnection("127.0.0.1", server)
    conn.request("GET", "/nonexistent")
    resp = conn.getresponse()
    assert resp.status == 404
    conn.close()


def test_post_generate_no_content_type(server):
    """Content-Typeなしで400が返ることを確認。"""
    conn = HTTPConnection("127.0.0.1", server)
    conn.request("POST", "/generate", body=b"test", headers={"Content-Type": "text/plain"})
    resp = conn.getresponse()
    assert resp.status == 400
    data = json.loads(resp.read().decode("utf-8"))
    assert "error" in data
    conn.close()


def test_post_generate_no_file(server):
    """ファイルなしmultipartで400が返ることを確認。"""
    boundary = "----TestBoundary123"
    body = (
        f"------TestBoundary123\r\n"
        f'Content-Disposition: form-data; name="provider"\r\n'
        f"\r\n"
        f"aws\r\n"
        f"------TestBoundary123--\r\n"
    ).encode("utf-8")

    conn = HTTPConnection("127.0.0.1", server)
    conn.request(
        "POST",
        "/generate",
        body=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary=----TestBoundary123",
            "Content-Length": str(len(body)),
        },
    )
    resp = conn.getresponse()
    assert resp.status == 400
    data = json.loads(resp.read().decode("utf-8"))
    assert "error" in data
    conn.close()


def test_post_generate_success(server):
    """有効なstateファイルで構成図が生成されることを確認。"""
    state_json = json.dumps({
        "values": {
            "root_module": {
                "resources": [
                    {
                        "type": "aws_vpc",
                        "name": "test",
                        "provider_name": "aws",
                        "values": {"id": "vpc-1", "cidr_block": "10.0.0.0/16"},
                    }
                ]
            }
        }
    })

    boundary = "----TestBoundary456"
    body = (
        f"------TestBoundary456\r\n"
        f'Content-Disposition: form-data; name="provider"\r\n'
        f"\r\n"
        f"aws\r\n"
        f"------TestBoundary456\r\n"
        f'Content-Disposition: form-data; name="format"\r\n'
        f"\r\n"
        f"mermaid\r\n"
        f"------TestBoundary456\r\n"
        f'Content-Disposition: form-data; name="file"; filename="state.json"\r\n'
        f"Content-Type: application/json\r\n"
        f"\r\n"
        f"{state_json}\r\n"
        f"------TestBoundary456--\r\n"
    ).encode("utf-8")

    conn = HTTPConnection("127.0.0.1", server)
    conn.request(
        "POST",
        "/generate",
        body=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary=----TestBoundary456",
            "Content-Length": str(len(body)),
        },
    )
    resp = conn.getresponse()
    assert resp.status == 200
    data = json.loads(resp.read().decode("utf-8"))
    assert data["success"] is True
    assert "content" in data  # mermaidなのでcontentが返る
    conn.close()


def test_post_404(server):
    """存在しないPOSTパスで404が返ることを確認。"""
    conn = HTTPConnection("127.0.0.1", server)
    conn.request("POST", "/nonexistent", body=b"")
    resp = conn.getresponse()
    assert resp.status == 404
    conn.close()


def test_download_no_result(server):
    """生成前にdownloadで404が返ることを確認。"""
    conn = HTTPConnection("127.0.0.1", server)
    conn.request("GET", "/download")
    resp = conn.getresponse()
    assert resp.status == 404
    conn.close()


def test_read_template():
    """テンプレート読み込み関数が動作することを確認。"""
    html = _read_template("index.html")
    assert "TerraSketch" in html


def test_send_json_and_error(server):
    """_send_jsonと_send_errorの基本動作を確認。"""
    # これはPOST /generateの400レスポンスで暗黙にテストされている
    conn = HTTPConnection("127.0.0.1", server)
    conn.request("POST", "/generate", body=b"", headers={"Content-Type": "text/plain"})
    resp = conn.getresponse()
    assert resp.status == 400
    conn.close()
