# iOS CI/CD パイプライン構成

Phase 1-25で構築したiOS CI/CDパイプラインの全体像。

---

## ワークフロー一覧

| ワークフロー | トリガー | 目的 |
|-------------|---------|------|
| `ios-quality-gate.yml` | PR (paths) | SwiftLint・Periphery・ビルド警告チェック |
| `ios-test.yml` | PR (paths) / push main / dispatch | Unit Test・UI Test・カバレッジ |
| `ios-release.yml` | tag `ios-v*` / dispatch | Archive・TestFlight・GitHub Release |

---

## ios-quality-gate.yml

3つのジョブを並列実行。

| ジョブ | timeout | 内容 |
|--------|---------|------|
| swiftlint | 10min | `--strict` モードで警告0件を強制 |
| periphery | 15min | 未使用コード検出（0件必須） |
| build | 20min | ビルド + 警告チェック（システム警告除外） |

**concurrency**: PR単位でキャンセル (`cancel-in-progress: true`)

---

## ios-test.yml

### ジョブ構成

```
detect-changes (ubuntu, 3min)
  ├── test (macos, 30min)     ← src変更時
  └── ui-test (macos, 30min)  ← ui-tests変更時
```

**detect-changes**: `dorny/paths-filter@v3` で変更ファイルを分類。

| フィルタ | 対象パス | 制御するジョブ |
|---------|---------|--------------|
| `src` | `*.swift`, `Podfile*`, `project.pbxproj`, `*.xcconfig` | test |
| `ui-tests` | `FinalHourglassUITests/**`, `*.swift`, `project.pbxproj` | ui-test |

### testジョブ
- Unit Test + カバレッジ計測
- コアロジック80%閾値チェック（LifeExpectancyCalculator, HealthScoreCalculator, UserModel）
- PR時: ベースブランチとのカバレッジ比較コメント
- main push時: Gistバッジ更新

### ui-testジョブ
- E2Eテスト（リトライ最大2回、`-retry-tests-on-failure`）
- 失敗時: スクリーンショット自動抽出・アップロード
- アクセシビリティテスト結果サマリー

### アーティファクト保持期間

| アーティファクト | 保持期間 |
|----------------|---------|
| coverage-report | 30日 |
| test-results | 7日 |
| ui-test-screenshots | 7日 |
| ui-test-results | 7日 |

---

## ios-release.yml

タグ `ios-v*` push または手動実行で起動。

```
validate → build-archive → upload-testflight → create-release
```

- **concurrency**: `cancel-in-progress: false`（リリースは途中キャンセルしない）
- セマンティックバージョニング検証（MAJOR.MINOR.PATCH）
- 手動実行時はmainブランチを強制

---

## 共通セットアップ (setup-ios action)

`.github/actions/setup-ios/action.yml` - composite action。

| input | default | 説明 |
|-------|---------|------|
| `install-cocoapods` | false | CocoaPodsキャッシュ + インストール |
| `install-xcpretty` | false | xcprettyインストール |
| `cache-derived-data` | false | DerivedDataキャッシュ |
| `working-directory` | `ios-apps/final-hourglass` | CocoaPods作業ディレクトリ |

### キャッシュキー

| キャッシュ | キー構成 |
|-----------|---------|
| CocoaPods | `{os}-pods-{hash(Podfile.lock)}` |
| DerivedData | `{os}-deriveddata-{hash(project.pbxproj, Podfile.lock)}` |

---

## パスフィルタ

各ワークフローがトリガーされるパス。

| パス | quality-gate | test (PR) | test (push) |
|------|:-----------:|:---------:|:-----------:|
| `*.swift` | o | o | o |
| `.swiftlint.yml` | o | - | - |
| `.periphery.yml` | o | - | - |
| `Podfile` | o | o | o |
| `Podfile.lock` | o | o | o |
| `project.pbxproj` | o | o | o |
| `*.xcconfig` | o | o | o |
| `FinalHourglassUITests/**` | - | o | o |

---

## ステータスバッジ

README.mdに以下のバッジを表示。

- **iOS Quality Gate** - ワークフローステータス
- **iOS Tests** - ワークフローステータス
- **iOS Release** - ワークフローステータス
- **iOS Coverage** - Gist endpoint経由の動的バッジ

---

## Phase履歴

| Phase | 内容 |
|-------|------|
| 1-4 | SwiftLint・Periphery・ビルド警告 品質ゲート構築 |
| 5-6 | Unit Test・カバレッジ計測・バッジ |
| 7-8 | UI Test・E2Eテスト基盤 |
| 9-10 | カバレッジ閾値・PR比較コメント |
| 11 | パフォーマンステスト結果サマリー |
| 12 | アクセシビリティテスト基盤 |
| 13 | セキュリティテスト基盤 |
| 14 | App Store Guidelines準拠テスト |
| 15 | リリースワークフロー自動化 |
| 19 | マトリクスビルド対応 |
| 20 | concurrency・timeout・artifact保持期間統一 |
| 21 | パスフィルタ最適化 |
| 22 | 共通セットアップcomposite action抽出 |
| 23 | READMEステータスバッジ統合 |
| 24 | DerivedDataキャッシュ最適化 |
| 25 | ワークフロー条件分岐 (dorny/paths-filter) |
| 26 | CI設定ドキュメント（本ファイル） |
