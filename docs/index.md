# TerraSketch

**Terraform state を唯一の信頼源として、AWS/Azure/GCP のクラウド構成図を自動生成するツール。**

## 特徴

- **マルチプロバイダ対応**: AWS、Azure、GCP のリソースを自動認識
- **複数出力形式**: draw.io / Mermaid / PlantUML / SVG
- **VPC/Subnet グルーピング**: コンテナ構造で視覚的に階層表現
- **diff モード**: 2 つの state を比較し変更箇所を色分け表示
- **外部依存最小**: `networkx` のみ。numpy 等不要
- **CLI / GUI / Web UI** すべてに対応
- **プラグインシステム**: レンダラー・マッピングを拡張可能

## クイックスタート

```bash
pip install terrasketch

# State JSONから構成図を生成
terrasketch generate --state state.json --provider aws --output ./output

# Mermaid形式で出力
terrasketch generate --state state.json --provider aws --format mermaid --output ./output

# GCPリソース
terrasketch generate --state state.json --provider gcp --output ./output

# マルチプロバイダ
terrasketch generate --state state.json --provider all --output ./output
```

## 処理パイプライン

```
入力（State JSON / HCL）
  → Parser（Resource リスト抽出）
  → Graph Builder（networkx DiGraph 構築）
  → [Security Annotator]（オプション）
  → Layout Engine（座標計算）
  → Renderer（draw.io / Mermaid / PlantUML / SVG 出力）
```

## ライセンス

MIT License
