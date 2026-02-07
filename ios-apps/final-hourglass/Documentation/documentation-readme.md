# 最後の砂時計 - ドキュメント

このディレクトリには「最後の砂時計」アプリケーションの開発に必要なすべてのドキュメントが含まれています。

## 📁 ディレクトリ構造

```
Documentation/
├── DesignSystem/          # デザインシステム関連
│   ├── BrandGuidelines.md    # ブランドガイドライン
│   ├── ColorPalette.swift     # カラー定義
│   ├── DesignTokens.swift     # デザイントークン
│   ├── Components/            # UIコンポーネント仕様
│   ├── Examples/              # 実装例・スクリーンショット
│   └── Assets/                # アイコン・画像アセット
├── API/                   # API仕様書
├── Architecture/          # アーキテクチャ設計書
└── UserGuides/           # ユーザーガイド
```

## 🎨 デザインシステム

### 主要ドキュメント

1. **[ブランドガイドライン](DesignSystem/BrandGuidelines.md)**
   - ブランドコンセプト、カラーシステム、タイポグラフィなど

2. **[ColorPalette.swift](DesignSystem/ColorPalette.swift)**
   - アプリで使用するすべての色の定義
   - SwiftUIとUIKit両対応

3. **[DesignTokens.swift](DesignSystem/DesignTokens.swift)**
   - スペーシング、アニメーション、サイズなどの定数

### 使用方法

```swift
// プロジェクトでの使用例
import SwiftUI

// カラーの使用
Text("最後の砂時計")
    .foregroundColor(.mysticalPurple)
    .mysticalGlow()

// スペーシングの使用
VStack(spacing: Spacing.md) {
    // コンテンツ
}
```

## 🔧 開発ガイドライン

### 新機能開発時の手順

1. デザインシステムを確認
2. 既存のコンポーネントを再利用
3. 新しいパターンが必要な場合は、デザインシステムに追加
4. PRでレビューを受ける

### コード規約

- SwiftUIを優先的に使用
- デザイントークンを必ず使用（マジックナンバー禁止）
- アクセシビリティを考慮した実装

## 📝 ドキュメント更新ルール

1. **重大な変更時は必ず更新**
   - 新しいカラーやコンポーネントの追加
   - デザイン方針の変更
   - APIの仕様変更

2. **バージョン管理**
   - すべての変更はGitで管理
   - 意味のあるコミットメッセージを記載

3. **レビュープロセス**
   - デザインシステムの変更は必ずレビューを受ける
   - 破壊的変更は事前に周知

## 🔗 関連リソース

- [Figmaデザインファイル](https://figma.com/xxxxx) *(リンクを追加)*
- [APIドキュメント](API/README.md)
- [アーキテクチャ設計](Architecture/README.md)

## 📞 連絡先

質問や提案がある場合は、以下まで連絡してください：

- デザインシステム: @design-team
- 技術的な質問: @tech-lead
- プロジェクト全般: @project-manager

---

最終更新日: 2024年12月
