"""Terraform Cloud連携クライアントのテスト。"""

from __future__ import annotations

import json
import os
from unittest.mock import patch, MagicMock

import pytest

from terrasketch.remote.tfc_client import TFCClient, fetch_and_generate


def test_tfc_client_requires_token():
    """トークン未指定でValueErrorが発生することを確認。"""
    with patch.dict(os.environ, {}, clear=True):
        # TFC_TOKENがない場合
        env = os.environ.copy()
        env.pop("TFC_TOKEN", None)
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="APIトークンが未指定"):
                TFCClient(token=None)


def test_tfc_client_uses_env_token():
    """環境変数TFC_TOKENが使用されることを確認。"""
    with patch.dict(os.environ, {"TFC_TOKEN": "test-token-123"}):
        client = TFCClient()
        assert client._token == "test-token-123"


def test_tfc_client_explicit_token():
    """明示的に指定したトークンが優先されることを確認。"""
    client = TFCClient(token="explicit-token")
    assert client._token == "explicit-token"


def test_tfc_client_custom_base_url():
    """カスタムベースURLが正しく設定されることを確認。"""
    client = TFCClient(token="test", base_url="https://tfe.example.com/api/v2")
    assert client._base_url == "https://tfe.example.com/api/v2"


def test_fetch_and_generate_invalid_workspace():
    """不正なワークスペース形式でValueErrorが発生することを確認。"""
    with pytest.raises(ValueError, match="<org>/<workspace>"):
        fetch_and_generate("invalid-format", token="test")


def test_tfc_client_get_workspace_id():
    """get_workspace_idが正しくIDを返すことを確認。"""
    client = TFCClient(token="test")

    mock_response = {
        "data": {
            "id": "ws-abc123",
            "type": "workspaces",
        }
    }

    with patch.object(client, "_request", return_value=mock_response):
        ws_id = client.get_workspace_id("my-org", "my-workspace")
        assert ws_id == "ws-abc123"


def test_tfc_client_get_current_state_version():
    """get_current_state_versionが正しくデータを返すことを確認。"""
    client = TFCClient(token="test")

    mock_response = {
        "data": {
            "id": "sv-xyz789",
            "type": "state-versions",
            "attributes": {
                "hosted-state-download-url": "https://example.com/state.json",
            },
        }
    }

    with patch.object(client, "_request", return_value=mock_response):
        sv = client.get_current_state_version("ws-abc123")
        assert sv["id"] == "sv-xyz789"
        assert "hosted-state-download-url" in sv["attributes"]
