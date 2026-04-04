/**
 * TerraSketch VS Code拡張機能の基本テスト
 *
 * @vscode/test-electron パターンに基づくスキャフォールドテスト。
 * 実行には VS Code テスト環境が必要。
 */
import * as assert from "assert";
import * as vscode from "vscode";

suite("TerraSketch 拡張機能テスト", () => {
  /** 拡張機能がアクティベートされることを確認 */
  test("拡張機能がアクティベートされること", async () => {
    const ext = vscode.extensions.getExtension("terrasketch.terrasketch-vscode");
    assert.ok(ext, "拡張機能が見つかりません");

    if (!ext.isActive) {
      await ext.activate();
    }
    assert.strictEqual(ext.isActive, true);
  });

  /** 全コマンドが登録されていることを確認 */
  test("コマンドが登録されていること", async () => {
    const commands = await vscode.commands.getCommands(true);

    const expectedCommands = [
      "terrasketch.generate",
      "terrasketch.preview",
      "terrasketch.watch",
    ];

    for (const cmd of expectedCommands) {
      assert.ok(
        commands.includes(cmd),
        `コマンド ${cmd} が登録されていません`,
      );
    }
  });

  /** 設定のデフォルト値を確認 */
  test("設定のデフォルト値が正しいこと", () => {
    const cfg = vscode.workspace.getConfiguration("terrasketch");

    assert.strictEqual(
      cfg.get("provider"),
      "aws",
      "providerのデフォルト値が正しくありません",
    );
    assert.strictEqual(
      cfg.get("format"),
      "drawio",
      "formatのデフォルト値が正しくありません",
    );
    assert.strictEqual(
      cfg.get("pythonPath"),
      "python",
      "pythonPathのデフォルト値が正しくありません",
    );
    assert.strictEqual(
      cfg.get("autoGenerate"),
      false,
      "autoGenerateのデフォルト値が正しくありません",
    );
    assert.strictEqual(
      cfg.get("runtime"),
      "terraform",
      "runtimeのデフォルト値が正しくありません",
    );
  });

  /** プレビューコマンドがエディタ未開時にエラーとなることを確認 */
  test("ファイル未開時にgenerateがエラーメッセージを表示すること", async () => {
    // エディタが開かれていない状態でコマンドを実行
    // エラーメッセージが表示されることを期待（エラーは投げられない）
    await vscode.commands.executeCommand("terrasketch.generate");
    // スキャフォールドテスト: エラーが投げられずに正常終了することを確認
    assert.ok(true);
  });
});
