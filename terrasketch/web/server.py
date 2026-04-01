"""TerraSketch Web UI サーバー（標準ライブラリのみ）。

ブラウザベースのUIを提供し、ファイルアップロード→プレビュー→ダウンロードの
ワークフローを実現する。Mermaidはブラウザ内でリアルタイムレンダリング。
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger("terrasketch")

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _read_template(name: str) -> str:
    """テンプレートHTMLを読み込む。"""
    return (_TEMPLATE_DIR / name).read_text(encoding="utf-8")


class TerraSketchHandler(BaseHTTPRequestHandler):
    """TerraSketch Web UIのHTTPリクエストハンドラー。"""

    def log_message(self, format: str, *args: object) -> None:
        """ログをloggingモジュールに出力する。"""
        logger.info(format, *args)

    def do_GET(self) -> None:
        """GETリクエストを処理する。"""
        parsed = urlparse(self.path)

        if parsed.path == "/" or parsed.path == "":
            self._serve_html(_read_template("index.html"))
        elif parsed.path == "/download" and hasattr(self.server, "_last_result"):
            self._serve_download()
        else:
            self._send_error(404, "Not Found")

    def do_POST(self) -> None:
        """POSTリクエストを処理する。"""
        if self.path == "/generate":
            self._handle_generate()
        else:
            self._send_error(404, "Not Found")

    def _serve_html(self, html: str) -> None:
        """HTMLレスポンスを返す。"""
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_download(self) -> None:
        """生成済みファイルをダウンロードとして返す。"""
        result_path: Path = self.server._last_result
        if not result_path.exists():
            self._send_error(404, "ファイルが見つかりません")
            return
        data = result_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header(
            "Content-Disposition",
            f'attachment; filename="{result_path.name}"',
        )
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_error(self, code: int, message: str) -> None:
        """エラーレスポンスを返す。"""
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(message.encode("utf-8"))

    def _send_json(self, code: int, data: dict) -> None:
        """JSONレスポンスを返す。"""
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_generate(self) -> None:
        """構成図生成リクエストを処理する。"""
        content_type = self.headers.get("Content-Type", "")

        if "multipart/form-data" not in content_type:
            self._send_json(400, {"error": "multipart/form-data が必要です"})
            return

        # multipartを解析
        boundary = content_type.split("boundary=")[-1].encode()
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        fields, file_data, file_name = _parse_multipart(body, boundary)

        if not file_data:
            self._send_json(400, {"error": "ファイルがアップロードされていません"})
            return

        provider = fields.get("provider", "aws")
        output_format = fields.get("format", "drawio")

        try:
            from terrasketch.main import generate

            # 一時ファイルにアップロード内容を書き出し
            with tempfile.TemporaryDirectory() as tmpdir:
                input_path = Path(tmpdir) / file_name
                input_path.write_bytes(file_data)

                output_dir = Path(tmpdir) / "output"
                output_dir.mkdir()

                # HCLかStateかを拡張子で判定
                hcl_path = None
                state_path = None
                if file_name.endswith(".tf"):
                    hcl_path = str(input_path)
                else:
                    state_path = str(input_path)

                result = generate(
                    state_path=state_path,
                    provider=provider,
                    output_dir=str(output_dir),
                    output_format=output_format,
                    hcl_path=hcl_path,
                )

                # 結果を永続化してダウンロードに使えるようにする
                content = result.read_text(encoding="utf-8")

                # Mermaidの場合はプレビュー用にコンテンツも返す
                response: dict = {
                    "success": True,
                    "filename": result.name,
                    "format": output_format,
                }
                if output_format == "mermaid":
                    response["content"] = content
                elif output_format == "svg":
                    response["content"] = content

                # ダウンロード用に一時ディレクトリ外にコピー
                persist_dir = Path(tempfile.gettempdir()) / "terrasketch_web"
                persist_dir.mkdir(exist_ok=True)
                persist_path = persist_dir / result.name
                persist_path.write_text(content, encoding="utf-8")
                self.server._last_result = persist_path

                response["download_url"] = "/download"
                self._send_json(200, response)

        except Exception as e:
            logger.error("生成エラー: %s", e)
            self._send_json(500, {"error": str(e)})


def _parse_multipart(
    body: bytes, boundary: bytes
) -> tuple[dict[str, str], bytes | None, str]:
    """multipart/form-dataを手動解析する。

    Returns:
        (フィールド辞書, ファイルデータ, ファイル名) のタプル。
    """
    fields: dict[str, str] = {}
    file_data: bytes | None = None
    file_name = "upload.json"

    parts = body.split(b"--" + boundary)
    for part in parts:
        if not part or part.strip() in (b"", b"--"):
            continue

        # ヘッダーとボディを分離
        if b"\r\n\r\n" in part:
            header_section, body_section = part.split(b"\r\n\r\n", 1)
        elif b"\n\n" in part:
            header_section, body_section = part.split(b"\n\n", 1)
        else:
            continue

        # 末尾のCRLFを除去
        if body_section.endswith(b"\r\n"):
            body_section = body_section[:-2]
        elif body_section.endswith(b"\n"):
            body_section = body_section[:-1]

        header_text = header_section.decode("utf-8", errors="replace")

        # Content-Dispositionからname/filenameを取得
        name = ""
        fname = ""
        for line in header_text.split("\n"):
            line = line.strip()
            if line.lower().startswith("content-disposition"):
                for token in line.split(";"):
                    token = token.strip()
                    if token.startswith("name="):
                        name = token.split("=", 1)[1].strip('"')
                    elif token.startswith("filename="):
                        fname = token.split("=", 1)[1].strip('"')

        if fname:
            file_data = body_section
            file_name = fname
        elif name:
            fields[name] = body_section.decode("utf-8", errors="replace")

    return fields, file_data, file_name


def start_server(host: str = "127.0.0.1", port: int = 8080) -> None:
    """Web UIサーバーを起動する。

    Args:
        host: バインドするホスト名。
        port: ポート番号。
    """
    server = HTTPServer((host, port), TerraSketchHandler)
    logger.info("TerraSketch Web UI を起動中: http://%s:%d", host, port)
    print(f"TerraSketch Web UI: http://{host}:{port}")
    print("Ctrl+Cで終了")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("サーバーを停止します。")
    finally:
        server.server_close()
