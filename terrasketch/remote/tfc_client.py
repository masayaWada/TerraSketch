"""Terraform Cloud / Enterprise 連携クライアント。

State Versions API から最新の Terraform state JSON を取得する。
外部依存なし（urllib.request のみ使用）。
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger("terrasketch")

# Terraform Cloud API ベースURL
_TFC_API_BASE = "https://app.terraform.io/api/v2"


class TFCClient:
    """Terraform Cloud / Enterprise のAPIクライアント。

    Args:
        token: APIトークン。省略時は環境変数TFC_TOKENを使用。
        base_url: APIベースURL。Enterpriseの場合はカスタムURLを指定。
    """

    def __init__(
        self,
        token: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self._token = token or os.environ.get("TFC_TOKEN", "")
        if not self._token:
            raise ValueError(
                "APIトークンが未指定です。--tfc-token オプションまたは "
                "環境変数 TFC_TOKEN を設定してください。"
            )
        self._base_url = (base_url or _TFC_API_BASE).rstrip("/")

    def _request(self, path: str) -> dict:
        """API GETリクエストを実行する。"""
        url = f"{self._base_url}{path}"
        req = Request(url)
        req.add_header("Authorization", f"Bearer {self._token}")
        req.add_header("Content-Type", "application/vnd.api+json")

        logger.debug("TFC API リクエスト: %s", url)
        try:
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"TFC APIエラー ({e.code}): {body}"
            ) from e
        except URLError as e:
            raise RuntimeError(
                f"TFC API接続エラー: {e.reason}"
            ) from e

    def get_workspace_id(self, org: str, workspace: str) -> str:
        """ワークスペース名からIDを取得する。

        Args:
            org: Terraform Cloud組織名。
            workspace: ワークスペース名。

        Returns:
            ワークスペースID。
        """
        data = self._request(f"/organizations/{org}/workspaces/{workspace}")
        return data["data"]["id"]

    def get_current_state_version(self, workspace_id: str) -> dict:
        """ワークスペースの最新state versionを取得する。

        Args:
            workspace_id: ワークスペースID。

        Returns:
            state versionのAPIレスポンス。
        """
        data = self._request(
            f"/workspaces/{workspace_id}/current-state-version"
        )
        return data["data"]

    def download_state(self, workspace_id: str) -> str:
        """最新のstate JSONをダウンロードし一時ファイルに保存する。

        Args:
            workspace_id: ワークスペースID。

        Returns:
            ダウンロードしたstate JSONファイルのパス。
        """
        state_version = self.get_current_state_version(workspace_id)
        download_url = state_version["attributes"]["hosted-state-download-url"]

        logger.info("State JSONをダウンロード中...")
        req = Request(download_url)
        req.add_header("Authorization", f"Bearer {self._token}")

        with urlopen(req, timeout=60) as resp:
            state_json = resp.read()

        # 一時ファイルに保存
        tmp = tempfile.NamedTemporaryFile(
            suffix=".json", prefix="tfc_state_", delete=False
        )
        tmp.write(state_json)
        tmp.close()

        logger.info("State JSONを保存: %s (%d bytes)", tmp.name, len(state_json))
        return tmp.name


def fetch_and_generate(
    workspace_spec: str,
    token: str | None = None,
    provider: str = "aws",
    output_dir: str = ".",
    output_format: str = "drawio",
    base_url: str | None = None,
) -> Path:
    """TFCからstateを取得し構成図を生成する。

    Args:
        workspace_spec: "<org>/<workspace>" 形式のワークスペース指定。
        token: APIトークン。
        provider: クラウドプロバイダ。
        output_dir: 出力ディレクトリ。
        output_format: 出力形式。
        base_url: APIベースURL（Enterprise用）。

    Returns:
        生成されたファイルのPath。
    """
    if "/" not in workspace_spec:
        raise ValueError(
            "ワークスペース指定は '<org>/<workspace>' 形式で指定してください。"
        )

    org, workspace = workspace_spec.split("/", 1)
    client = TFCClient(token=token, base_url=base_url)

    logger.info("ワークスペースを取得中: %s/%s", org, workspace)
    workspace_id = client.get_workspace_id(org, workspace)
    logger.info("ワークスペースID: %s", workspace_id)

    state_path = client.download_state(workspace_id)

    try:
        from terrasketch.main import generate

        result = generate(
            state_path=state_path,
            provider=provider,
            output_dir=output_dir,
            output_format=output_format,
        )
        return result
    finally:
        # 一時ファイルを削除
        try:
            os.unlink(state_path)
        except OSError:
            pass
