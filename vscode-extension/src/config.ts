import * as vscode from "vscode";

/**
 * TerraSketch拡張機能の設定インターフェース
 */
export interface TerraSketchConfig {
  /** クラウドプロバイダ */
  readonly provider: "aws" | "azure" | "gcp" | "kubernetes" | "all";
  /** 出力形式 */
  readonly format: "drawio" | "mermaid" | "plantuml" | "svg" | "html";
  /** Python実行パス */
  readonly pythonPath: string;
  /** ファイル保存時の自動再生成 */
  readonly autoGenerate: boolean;
  /** 使用するランタイム（terraform / opentofu） */
  readonly runtime: "terraform" | "opentofu";
}

/** デフォルト設定値 */
const DEFAULTS: TerraSketchConfig = {
  provider: "aws",
  format: "drawio",
  pythonPath: "python",
  autoGenerate: false,
  runtime: "terraform",
} as const;

/**
 * VS Codeの設定からTerraSketchの設定を読み込む
 *
 * @returns 現在のTerraSketch設定（未設定項目はデフォルト値）
 */
export function getConfig(): TerraSketchConfig {
  const cfg = vscode.workspace.getConfiguration("terrasketch");

  return {
    provider: cfg.get<TerraSketchConfig["provider"]>("provider") ?? DEFAULTS.provider,
    format: cfg.get<TerraSketchConfig["format"]>("format") ?? DEFAULTS.format,
    pythonPath: cfg.get<string>("pythonPath") ?? DEFAULTS.pythonPath,
    autoGenerate: cfg.get<boolean>("autoGenerate") ?? DEFAULTS.autoGenerate,
    runtime: cfg.get<TerraSketchConfig["runtime"]>("runtime") ?? DEFAULTS.runtime,
  };
}

/**
 * デフォルト設定を取得する
 *
 * @returns デフォルト設定オブジェクト
 */
export function getDefaults(): Readonly<TerraSketchConfig> {
  return { ...DEFAULTS };
}
