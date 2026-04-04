"""TFCクライアントの詳細テスト。"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from terrasketch.remote.tfc_client import TFCClient, fetch_and_generate


def test_request_http_error():
    """HTTPErrorが適切にRuntimeErrorに変換されることを確認。"""
    client = TFCClient(token="test")

    mock_error = HTTPError(
        url="https://example.com",
        code=404,
        msg="Not Found",
        hdrs={},
        fp=MagicMock(read=MagicMock(return_value=b"not found")),
    )

    with patch("terrasketch.remote.tfc_client.urlopen", side_effect=mock_error):
        with pytest.raises(RuntimeError, match="TFC APIエラー"):
            client._request("/test")


def test_request_url_error():
    """URLErrorが適切にRuntimeErrorに変換されることを確認。"""
    client = TFCClient(token="test")

    with patch("terrasketch.remote.tfc_client.urlopen", side_effect=URLError("connection refused")):
        with pytest.raises(RuntimeError, match="TFC API接続エラー"):
            client._request("/test")


def test_request_success():
    """正常なリクエストがJSONを返すことを確認。"""
    client = TFCClient(token="test")

    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"data": "ok"}'
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("terrasketch.remote.tfc_client.urlopen", return_value=mock_resp):
        result = client._request("/test")
        assert result == {"data": "ok"}


def test_download_state():
    """download_stateが一時ファイルを作成することを確認。"""
    client = TFCClient(token="test")

    mock_sv = {
        "attributes": {
            "hosted-state-download-url": "https://example.com/state.json",
        }
    }

    state_content = b'{"values":{"root_module":{"resources":[]}}}'
    mock_resp = MagicMock()
    mock_resp.read.return_value = state_content
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch.object(client, "get_current_state_version", return_value=mock_sv):
        with patch("terrasketch.remote.tfc_client.urlopen", return_value=mock_resp):
            path = client.download_state("ws-123")
            try:
                assert Path(path).exists()
                content = Path(path).read_bytes()
                assert b"root_module" in content
            finally:
                os.unlink(path)


def test_fetch_and_generate_full(tmp_path):
    """fetch_and_generateのE2Eフローを確認。"""
    state = {
        "values": {
            "root_module": {
                "resources": [
                    {
                        "type": "aws_vpc",
                        "name": "main",
                        "provider_name": "aws",
                        "values": {"id": "vpc-1"},
                    }
                ]
            }
        }
    }
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps(state), encoding="utf-8")

    with patch("terrasketch.remote.tfc_client.TFCClient") as MockClient:
        instance = MockClient.return_value
        instance.get_workspace_id.return_value = "ws-123"
        instance.download_state.return_value = str(state_file)

        output_dir = tmp_path / "output"
        output_dir.mkdir()
        result = fetch_and_generate(
            workspace_spec="org/workspace",
            token="test",
            provider="aws",
            output_dir=str(output_dir),
        )
        assert result.exists()


def test_base_url_trailing_slash():
    """base_urlの末尾スラッシュが除去されることを確認。"""
    client = TFCClient(token="test", base_url="https://tfe.example.com/api/v2/")
    assert client._base_url == "https://tfe.example.com/api/v2"
