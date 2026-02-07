# Final Hourglass - App Storeリリースガイド

このドキュメントは、Final HourglassをApp Storeにリリースするための手順を説明します。

---

## 1. 事前準備

### 1.1 必要なアカウント
- [ ] Apple Developer Program メンバーシップ（年間$99）
- [ ] App Store Connect アカウント

### 1.2 証明書とプロファイル
- [ ] Distribution Certificate（配布用証明書）
- [ ] App Store Provisioning Profile

### 1.3 必要な素材
- [ ] アプリアイコン（1024x1024px）
- [ ] スクリーンショット
  - 6.7インチ（iPhone 15 Pro Max）: 1290 x 2796px
  - 6.1インチ（iPhone 15 Pro）: 1179 x 2556px
  - 6.5インチ（iPhone 11 Pro Max）: 1242 x 2688px（オプション）
- [ ] プライバシーポリシーURL
- [ ] サポートURL

---

## 2. Xcode設定

### 2.1 ビルド設定確認
```
Target > Build Settings
- Build Active Architecture Only: No（Release）
- Enable Bitcode: No
- Strip Debug Symbols During Copy: Yes
```

### 2.2 バージョン設定
```
Target > General
- Version: 1.0.0（CFBundleShortVersionString）
- Build: 1（CFBundleVersion）
```

### 2.3 署名設定
```
Target > Signing & Capabilities
- Team: [Your Team]
- Signing Certificate: Apple Distribution
- Provisioning Profile: [App Store Profile]
```

---

## 3. App Store Connect設定

### 3.1 アプリ情報

#### 基本情報
| 項目 | 内容 |
|------|------|
| アプリ名 | Final Hourglass |
| サブタイトル | 残り寿命カウンター |
| カテゴリ | ヘルスケア/フィットネス または ライフスタイル |
| 年齢制限 | 4+ |
| 価格 | 無料 |

#### 説明文（日本語）
```
あなたの残り寿命を可視化するアプリです。

【機能】
• 生年月日と健康情報から予想寿命を計算
• 残り時間をリアルタイムでカウントダウン
• 同じ年齢の著名人のエピソードを毎日表示
• お気に入りエピソードの保存機能

【注意事項】
このアプリで表示される寿命は統計データに基づく予測であり、
実際の寿命を保証するものではありません。
医療的なアドバイスとして使用しないでください。

健康的な生活を送るきっかけとして、
残りの人生を大切に過ごすためのモチベーションツールとしてお使いください。
```

#### キーワード
```
寿命, カウントダウン, 健康, ライフスタイル, 人生, 時間管理, モチベーション
```

### 3.2 プライバシー情報

App Privacy（アプリのプライバシー）設定:

| データタイプ | 収集 | 用途 |
|-------------|------|------|
| 健康・フィットネス | はい | アプリ機能 |
| 連絡先情報 | いいえ | - |
| 位置情報 | いいえ | - |
| 識別子 | いいえ | - |
| 使用状況データ | はい | 分析 |

---

## 4. ビルドとアップロード

### 4.1 Archive作成
```bash
# Xcodeで
Product > Archive

# または、コマンドラインで
xcodebuild archive \
  -scheme FinalHourglass \
  -archivePath ./build/FinalHourglass.xcarchive
```

### 4.2 App Store Connectへアップロード
```
Xcode > Window > Organizer
> Archives > Distribute App
> App Store Connect > Upload
```

### 4.3 TestFlight配信（推奨）
1. App Store Connectで「TestFlight」タブを開く
2. ビルドを選択
3. テスターグループを作成/選択
4. テスト配信を開始

---

## 5. 審査提出

### 5.1 審査前チェックリスト
- [ ] アプリが正常に動作する
- [ ] プライバシーポリシーが公開されている
- [ ] スクリーンショットが最新
- [ ] 説明文に誤りがない
- [ ] 免責事項が明記されている

### 5.2 審査メモ（App Store Review Notes）
```
このアプリは統計データに基づいて予想寿命を計算するエンターテインメントアプリです。

重要な注意点:
- 表示される寿命は統計的予測であり、医療診断ではありません
- ユーザーにはアプリ内で明確にこの旨を通知しています
- 健康情報は端末内にのみ保存され、外部に送信されません

テストアカウントは不要です。
```

### 5.3 審査で注意すべき点
1. **ヘルスケア関連の免責事項**: 寿命計算が医療アドバイスでないことを明記
2. **年齢制限**: 内容が適切であれば4+
3. **コンテンツ**: エピソードに不適切な内容がないか確認

---

## 6. リリース後

### 6.1 モニタリング
- クラッシュレポートの確認（App Store Connect > Analytics）
- ユーザーレビューの確認と返信
- ダウンロード数の追跡

### 6.2 アップデート計画
- バグ修正は迅速に対応
- 新機能は次期バージョンで検討
- iOS新バージョン対応

---

## 7. トラブルシューティング

### よくある審査リジェクト理由と対策

| リジェクト理由 | 対策 |
|---------------|------|
| メタデータの問題 | 説明文を修正、スクリーンショットを更新 |
| クラッシュ | デバッグして修正 |
| プライバシー | プライバシーポリシーを追加/更新 |
| 年齢制限 | レーティングを再評価 |
| 医療アプリ判定 | 免責事項を強化、エンターテインメント性を強調 |

---

## 連絡先

審査に関する質問は以下で対応:
- App Store Connect > お問い合わせ
- developer.apple.com/contact/

---

*最終更新: 2026年2月*
