import * as vscode from "vscode";
import * as path from "path";
import { spawn, ChildProcess } from "child_process";
import { getConfig } from "./config";
import { TerraSketchPreviewPanel } from "./preview";

/** ステータスバーの表示状態 */
type StatusState = "idle" | "generating" | "watching" | "error";

/** ステータスバーアイテム */
let statusBarItem: vscode.StatusBarItem;

/** watchモードのファイル保存リスナー */
let watchDisposable: vscode.Disposable | undefined;

/** watchモードが有効かどうか */
let isWatching = false;

/** 現在実行中のCLIプロセス */
let activeProcess: ChildProcess | undefined;

/**
 * 拡張機能のアクティベーション
 *
 * 3つのコマンド（generate / preview / watch）を登録し、
 * ステータスバーアイテムを初期化する。
 *
 * @param context - 拡張機能コンテキスト
 */
export function activate(context: vscode.ExtensionContext): void {
  // ステータスバーの初期化
  statusBarItem = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Left,
    100,
  );
  statusBarItem.command = "terrasketch.generate";
  updateStatusBar("idle");
  statusBarItem.show();
  context.subscriptions.push(statusBarItem);

  // コマンド: 構成図を生成
  const generateCmd = vscode.commands.registerCommand(
    "terrasketch.generate",
    () => handleGenerate(),
  );

  // コマンド: 構成図をプレビュー
  const previewCmd = vscode.commands.registerCommand(
    "terrasketch.preview",
    () => handlePreview(context.extensionUri),
  );

  // コマンド: ファイル監視の切替
  const watchCmd = vscode.commands.registerCommand(
    "terrasketch.watch",
    () => handleWatchToggle(context),
  );

  context.subscriptions.push(generateCmd, previewCmd, watchCmd);
}

/**
 * 拡張機能のディアクティベーション
 *
 * watchモードの停止と実行中プロセスの終了を行う。
 */
export function deactivate(): void {
  stopWatch();
  if (activeProcess) {
    activeProcess.kill();
    activeProcess = undefined;
  }
}

/**
 * 構成図生成コマンドのハンドラ
 *
 * アクティブファイルの拡張子（.tf / .tfstate）を判定し、
 * terrasketch CLIを呼び出して構成図を生成する。
 */
async function handleGenerate(): Promise<void> {
  const filePath = getActiveFilePath();
  if (!filePath) {
    return;
  }

  const inputFlag = detectInputFlag(filePath);
  if (!inputFlag) {
    vscode.window.showErrorMessage(
      "TerraSketch: 対応ファイル（.tf / .tfstate / .json）を開いてください",
    );
    return;
  }

  const config = getConfig();
  const outputDir = path.dirname(filePath);

  const args = buildCliArgs(inputFlag, filePath, config, outputDir);
  await runTerraSketch(args);
}

/**
 * プレビューコマンドのハンドラ
 *
 * SVGまたはHTML形式で構成図を生成し、WebViewパネルに表示する。
 *
 * @param extensionUri - 拡張機能のルートURI
 */
async function handlePreview(extensionUri: vscode.Uri): Promise<void> {
  const filePath = getActiveFilePath();
  if (!filePath) {
    return;
  }

  const inputFlag = detectInputFlag(filePath);
  if (!inputFlag) {
    vscode.window.showErrorMessage(
      "TerraSketch: 対応ファイル（.tf / .tfstate / .json）を開いてください",
    );
    return;
  }

  const config = getConfig();
  // プレビューではSVGまたはHTMLを使用
  const previewFormat = config.format === "html" ? "html" : "svg";
  const outputDir = path.dirname(filePath);
  const baseName = path.basename(filePath, path.extname(filePath));
  const ext = previewFormat === "html" ? ".html" : ".svg";
  const outputPath = path.join(outputDir, `${baseName}_diagram${ext}`);

  const args = buildCliArgs(inputFlag, filePath, config, outputDir, previewFormat);

  const success = await runTerraSketch(args);
  if (success) {
    TerraSketchPreviewPanel.createOrShow(extensionUri, outputPath);
  }
}

/**
 * watchモード切替のハンドラ
 *
 * ファイル保存時に自動で構成図を再生成するモードのON/OFFを切り替える。
 *
 * @param context - 拡張機能コンテキスト
 */
function handleWatchToggle(context: vscode.ExtensionContext): void {
  if (isWatching) {
    stopWatch();
    vscode.window.showInformationMessage("TerraSketch: ファイル監視を停止しました");
  } else {
    startWatch(context);
    vscode.window.showInformationMessage("TerraSketch: ファイル監視を開始しました");
  }
}

/**
 * watchモードを開始する
 *
 * .tf / .tfstate / .json ファイルの保存を監視し、自動で構成図を再生成する。
 *
 * @param context - 拡張機能コンテキスト
 */
function startWatch(context: vscode.ExtensionContext): void {
  isWatching = true;
  updateStatusBar("watching");

  watchDisposable = vscode.workspace.onDidSaveTextDocument((doc) => {
    const ext = path.extname(doc.fileName).toLowerCase();
    if (ext === ".tf" || ext === ".tfstate" || ext === ".json") {
      handleGenerate();
    }
  });

  context.subscriptions.push(watchDisposable);
}

/** watchモードを停止する */
function stopWatch(): void {
  isWatching = false;
  updateStatusBar("idle");

  if (watchDisposable) {
    watchDisposable.dispose();
    watchDisposable = undefined;
  }
}

/**
 * アクティブエディタのファイルパスを取得する
 *
 * @returns ファイルパス。エディタが開かれていない場合はundefined
 */
function getActiveFilePath(): string | undefined {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showErrorMessage("TerraSketch: ファイルが開かれていません");
    return undefined;
  }
  return editor.document.fileName;
}

/**
 * ファイル拡張子からCLIの入力フラグを判定する
 *
 * @param filePath - 入力ファイルパス
 * @returns CLIフラグ文字列（"--state" / "--hcl"）。未対応形式の場合はundefined
 */
function detectInputFlag(filePath: string): string | undefined {
  const ext = path.extname(filePath).toLowerCase();
  const baseName = path.basename(filePath).toLowerCase();

  if (ext === ".tf") {
    return "--hcl";
  }
  if (ext === ".tfstate" || baseName.endsWith(".tfstate.json")) {
    return "--state";
  }
  if (ext === ".json") {
    // .json ファイルはstateファイルとして扱う
    return "--state";
  }
  return undefined;
}

/**
 * terrasketch CLIの引数を組み立てる
 *
 * @param inputFlag - 入力フラグ（"--state" / "--hcl"）
 * @param filePath - 入力ファイルパス
 * @param config - TerraSketch設定
 * @param outputDir - 出力ディレクトリ
 * @param formatOverride - 出力形式の上書き（省略時は設定値を使用）
 * @returns CLIに渡す引数配列
 */
function buildCliArgs(
  inputFlag: string,
  filePath: string,
  config: ReturnType<typeof getConfig>,
  outputDir: string,
  formatOverride?: string,
): string[] {
  const format = formatOverride ?? config.format;
  return [
    "-m",
    "terrasketch",
    "generate",
    inputFlag,
    filePath,
    "--provider",
    config.provider,
    "--format",
    format,
    "--output",
    outputDir,
  ];
}

/**
 * terrasketch CLIをサブプロセスとして実行する
 *
 * @param args - CLIに渡す引数配列
 * @returns 成功した場合true
 */
async function runTerraSketch(args: string[]): Promise<boolean> {
  const config = getConfig();

  return new Promise<boolean>((resolve) => {
    updateStatusBar("generating");

    const proc = spawn(config.pythonPath, args, {
      cwd: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath,
      shell: true,
    });

    activeProcess = proc;

    let stdout = "";
    let stderr = "";

    proc.stdout?.on("data", (data: Buffer) => {
      stdout += data.toString();
    });

    proc.stderr?.on("data", (data: Buffer) => {
      stderr += data.toString();
    });

    proc.on("close", (code) => {
      activeProcess = undefined;

      if (code === 0) {
        updateStatusBar(isWatching ? "watching" : "idle");
        vscode.window.showInformationMessage(
          `TerraSketch: 構成図を生成しました`,
        );
        resolve(true);
      } else {
        updateStatusBar("error");
        const errMsg = stderr.trim() || `終了コード: ${code}`;
        vscode.window.showErrorMessage(
          `TerraSketch: 生成に失敗しました - ${errMsg}`,
        );
        resolve(false);
      }
    });

    proc.on("error", (err) => {
      activeProcess = undefined;
      updateStatusBar("error");
      vscode.window.showErrorMessage(
        `TerraSketch: CLIの実行に失敗しました - ${err.message}`,
      );
      resolve(false);
    });
  });
}

/**
 * ステータスバーの表示を更新する
 *
 * @param state - 表示状態
 */
function updateStatusBar(state: StatusState): void {
  switch (state) {
    case "idle":
      statusBarItem.text = "$(file-media) TerraSketch";
      statusBarItem.tooltip = "クリックして構成図を生成";
      statusBarItem.backgroundColor = undefined;
      break;
    case "generating":
      statusBarItem.text = "$(sync~spin) TerraSketch: 生成中...";
      statusBarItem.tooltip = "構成図を生成しています";
      statusBarItem.backgroundColor = undefined;
      break;
    case "watching":
      statusBarItem.text = "$(eye) TerraSketch: 監視中";
      statusBarItem.tooltip = "ファイル変更を監視中（クリックで生成）";
      statusBarItem.backgroundColor = undefined;
      break;
    case "error":
      statusBarItem.text = "$(error) TerraSketch: エラー";
      statusBarItem.tooltip = "最後の生成でエラーが発生しました";
      statusBarItem.backgroundColor = new vscode.ThemeColor(
        "statusBarItem.errorBackground",
      );
      break;
  }
}
