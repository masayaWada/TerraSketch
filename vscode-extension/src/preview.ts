import * as vscode from "vscode";
import * as fs from "fs";

/**
 * TerraSketchの構成図プレビューパネルを管理するクラス
 *
 * WebViewを使用してSVG/HTMLの構成図をエディタ内に表示する。
 * シングルトンパターンにより、同時に1つのプレビューパネルのみ存在する。
 */
export class TerraSketchPreviewPanel {
  /** WebViewパネルのビュータイプ識別子 */
  public static readonly viewType = "terrasketch.preview";

  /** 現在のシングルトンインスタンス */
  private static currentPanel: TerraSketchPreviewPanel | undefined;

  /** VS Code WebViewパネル */
  private readonly panel: vscode.WebviewPanel;

  /** イベントリスナーの破棄用配列 */
  private readonly disposables: vscode.Disposable[] = [];

  /**
   * プレビューパネルを作成または既存パネルを前面に表示する
   *
   * @param extensionUri - 拡張機能のルートURI
   * @param filePath - 表示するファイルのパス（SVGまたはHTML）
   */
  public static createOrShow(extensionUri: vscode.Uri, filePath: string): void {
    const column = vscode.ViewColumn.Beside;

    if (TerraSketchPreviewPanel.currentPanel) {
      TerraSketchPreviewPanel.currentPanel.panel.reveal(column);
      TerraSketchPreviewPanel.currentPanel.updateContent(filePath);
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      TerraSketchPreviewPanel.viewType,
      "TerraSketch プレビュー",
      column,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [extensionUri],
      },
    );

    TerraSketchPreviewPanel.currentPanel = new TerraSketchPreviewPanel(panel);
    TerraSketchPreviewPanel.currentPanel.updateContent(filePath);
  }

  /**
   * 現在のプレビューパネルのコンテンツを更新する（watchモード用）
   *
   * @param filePath - 表示するファイルのパス
   */
  public static refresh(filePath: string): void {
    if (TerraSketchPreviewPanel.currentPanel) {
      TerraSketchPreviewPanel.currentPanel.updateContent(filePath);
    }
  }

  private constructor(panel: vscode.WebviewPanel) {
    this.panel = panel;

    this.panel.onDidDispose(() => this.dispose(), null, this.disposables);
  }

  /**
   * ファイルの内容を読み込んでWebViewに表示する
   *
   * @param filePath - 表示するファイルパス（.svg または .html）
   */
  private updateContent(filePath: string): void {
    if (!fs.existsSync(filePath)) {
      this.panel.webview.html = this.buildErrorHtml(
        `ファイルが見つかりません: ${filePath}`,
      );
      return;
    }

    const content = fs.readFileSync(filePath, "utf-8");
    const ext = filePath.toLowerCase();

    if (ext.endsWith(".html")) {
      this.panel.webview.html = this.buildHtmlWrapper(content);
    } else if (ext.endsWith(".svg")) {
      this.panel.webview.html = this.buildSvgHtml(content);
    } else {
      this.panel.webview.html = this.buildErrorHtml(
        `未対応のファイル形式です: ${filePath}`,
      );
    }
  }

  /**
   * SVGコンテンツをWebView用HTMLにラップする
   *
   * @param svgContent - SVG文字列
   * @returns Content Security Policy付きの完全なHTML
   */
  private buildSvgHtml(svgContent: string): string {
    const nonce = this.getNonce();
    return `<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy"
        content="default-src 'none'; img-src data: https:; style-src 'nonce-${nonce}'; script-src 'none';">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TerraSketch プレビュー</title>
  <style nonce="${nonce}">
    body {
      margin: 0;
      padding: 16px;
      background: var(--vscode-editor-background);
      color: var(--vscode-editor-foreground);
      display: flex;
      justify-content: center;
      align-items: flex-start;
      overflow: auto;
    }
    svg {
      max-width: 100%;
      height: auto;
    }
  </style>
</head>
<body>
  ${svgContent}
</body>
</html>`;
  }

  /**
   * HTML構成図（Cytoscape.js等）をWebView用にラップする
   *
   * @param htmlContent - 完全なHTML文字列
   * @returns Content Security Policy付きのHTML（スクリプト許可）
   */
  private buildHtmlWrapper(htmlContent: string): string {
    // HTML形式はCytoscape.jsを含むため、スクリプト実行を許可する
    // インラインスクリプトとCDNからのロードを許可
    return htmlContent.replace(
      "<head>",
      `<head>
  <meta http-equiv="Content-Security-Policy"
        content="default-src 'none'; img-src data: https:; style-src 'unsafe-inline' https:; script-src 'unsafe-inline' https://cdnjs.cloudflare.com https://unpkg.com;">`,
    );
  }

  /**
   * エラーメッセージ表示用HTMLを生成する
   *
   * @param message - エラーメッセージ
   * @returns エラー表示用HTML
   */
  private buildErrorHtml(message: string): string {
    return `<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline';">
  <title>TerraSketch エラー</title>
  <style>
    body {
      margin: 0;
      padding: 32px;
      background: var(--vscode-editor-background);
      color: var(--vscode-errorForeground, #f44);
      font-family: var(--vscode-font-family);
      font-size: var(--vscode-font-size);
    }
  </style>
</head>
<body>
  <h2>TerraSketch エラー</h2>
  <p>${this.escapeHtml(message)}</p>
</body>
</html>`;
  }

  /**
   * CSPノンスを生成する
   *
   * @returns ランダムな32文字のノンス文字列
   */
  private getNonce(): string {
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    let result = "";
    for (let i = 0; i < 32; i++) {
      result += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return result;
  }

  /**
   * HTML特殊文字をエスケープする
   *
   * @param text - エスケープ対象文字列
   * @returns エスケープ済み文字列
   */
  private escapeHtml(text: string): string {
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /** パネルとリソースを破棄する */
  private dispose(): void {
    TerraSketchPreviewPanel.currentPanel = undefined;
    this.panel.dispose();
    for (const d of this.disposables) {
      d.dispose();
    }
  }
}
