# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.9] - 2026-03-04

### Changed

- **perf**: エピソード取得のクエリ最適化 - limit縮小(100→50) + age/hybrid_score複合インデックス追加 (PR #139)
- **feat**: 全52,838件のエピソードを丁寧語(です・ます調)に統一 - Batch API + ルールベース二段構え (PR #138)
- **refactor**: `storytelling_quality` → `story_quality` 全レイヤー命名統一 - 48ファイル変更 (PR #137)
- **feat**: About画面に更新履歴(v1.0.8/v1.0.9)を追加 + エピソード文法品質システム (PR #136)
- **refactor**: LifeResultView の SwiftLint違反修正 - function_body_length/file_length解消 (PR #135)
- **docs**: App Store subtitle/keywords の文字数・バイト数を制限フル活用に拡充 (PR #134)

### Added

- **Phase 18** - コンテキスト最適化とシステム起動改善 (2025-11-21)
  - 低頻度MCPサーバーの選択的無効化（playwright, firecrawl, brave-search, fetch）
  - MCP toolsトークン使用量 27.9k削減（30.8k → 3.0k予定）
  - Free space 40% → 54%達成（再起動後）
  - 大きな緑色の起動バナー追加（システム状態の視覚的確認）
  - 一時有効化スラッシュコマンド `/enable-web` 追加
  - カスタム実装フラグ `disabled: true` による柔軟な管理
  - PR #6: feat/context-optimization (5d291427, 05cc371d)
- Phase 7b - 統一CI/CD設定の展開完了（6プロジェクト統合）
  - 統一GitHub Actionsワークフロー（6ジョブ: code-quality, unit-tests, security-scan, changelog-validation, build, ci-summary）
  - 統一pre-commit設定（11カテゴリのフック統合）
  - CHANGELOG検証機構（Keep a Changelog形式 + Conventional Commits チェック）
  - 自動展開スクリプト（deploy-unified-ci.sh）
- KAIZEN-002 - Add birth data to version control (ff9a215)
- Phase 11.5 - AIベースの推奨システム完了 (2693a2f)
- Phase 11.4 - コスト最適化アルゴリズム完了 (9750f30)
- Phase 11.3 - 容量計画自動化システム完了 (98e22a3)
- Phase 11.2 - 高度トレンド分析ダッシュボード実装完了 (4a880fd)
- Phase 11.1 - 高度予測分析エンジン実装（AutoML + Ensemble Learning） (4fa2567)
- 文字数範囲を175-280文字に緩和（Phase 14完了） (e3fb139)
- 時間情報重複削除システム実装（Phase 13完了） (9beb75f)
- 年齢重複禁止システム完全実装（Phase 12完了） (9d6924c)
- 時系列バランス検証システム完全実装（Phase 11完了） (4eba261)
- エピソード冒頭フォーマット統一性違反を修正（RCA-Kaizen Loop統合） (0ba7329)
- RCA-Kaizen Loop統合 - アインシュタイン削除問題の再発防止 (0a9f042)
- Week 1-6データベース完成（合格率97.3%） (389aa66)
- ポート管理システムの実装（プロセス再利用対応） (fc987aa)
- PDCAガーディアンv3.3-v5.1の完全実装とFactChecker統合 (93ae3e4)
- FactCheckerシステムの実装とPDCAガーディアンへの統合 (fdbae66)
- 知名度評価システムの完全実装 (e71fbab)
- **raycast**: support local/URL externalConfigPath; add config template and docs (b69024f)
- **raycast**: externalConfigPath support; resolveConnection for baseUrl/apiKey; wire into commands (7770063)
- updater accepts explicit JSON path arg for baseUrl/apiKey (6f2a211)
- **raycast**: add apiKey support (header injection), extend preferences; (623a56d)
- **presets**: remote presets support (preferences.remotePresetsUrl); presets manager HTML and sample presets.json; merge logic and UI enhancements (be5fdfb)
- **raycast**: presets command, increase history to 50; helper to update Raycast baseUrl; CI to enforce pre-commit (e9aaa08)
- **n8n**: add automated setup script to create/update .env.n8n with auto port detection (d6dcb6a)
- Add 2025 modern Python development tools integration (3cf83bd)
- Add advanced features for 2025 best practices (8f9de4e)
- Add remote MCP server integration (2025 feature) (30e6acb)

### Changed

- RCA-Kaizen Loop 完全統合レポート (cbbf427)
- 追加ファクトチェックレポート (af73011)
- .gitignore更新とファクトチェックレポート追加 (0988f57)
- プロジェクトクリーンアップとシステム統合 (ec7742f)
- **perf**: make trivial accessors sync; remove unused demo vars; satisfy Sonar S7503/S1481 (79cabe7)
- **headless**: factor TESTS_DIR constant usages; minor complexity cleanups (e0cdc11)
- **readme**: fix MD032/MD040; chore(check_todos): reduce complexity, specify exceptions; chore(beartype): remove unused timeout param; feat(ollama): factor DEFAULT_CODE_MODEL (eba3e49)
- add /Users/admin/Documents/Raycast as Raycast prefs path candidate (5788cf7)
- raycast prefs updater searches Containers path as well (482cd26)
- satisfy shellcheck for EXTENSION_NAME ref (e6cbe5c)
- extend Raycast updater to set apiKey from /Users/admin/Documents/key/n8n-key.txt (9c644cf)
- fix shellcheck warnings; prettier formatted new workflow (85d1eec)
- **prettier**: format configs after additions (6548d89)
- **cursor**: add .cursorignore; chore(editor): add .editorconfig; docs: add n8n quickstart and add n8n:status script; (8b82f20)
- **n8n**: add npm scripts n8n:setup and n8n:start:ready for one-shot initialization (25c899b)
- ruff-format auto-fix (7281b10)
- **mypy**: add types-aiofiles; harden error_recovery list typing; guard params in headless_mode; session guards in remote_mcp (0a2dc50)
- **types**: tighten return types and casts in ollama_integration (no Python version change required) (999412c)
- **types**: add type hints and None-guards in remote_mcp_integration; use utf-8 open; minor retries tidy (c45afe2)
- **types**: define SessionValue type alias; annotate __exit__; suppress global warning for session_manager (19147c0)
- **lint**: fix unused args and fullwidth punctuation in error_recovery/session_manager; adjust headless unused params (a1ed027)
- **lint**: suppress minor ruff warnings (unused args, fullwidth chars); annotate priorities (ce912b4)
- **types**: annotate session_manager and use Path.open; tighten signal handler types (c5bad8b)
- **types**: minor type fixes in headless_mode and error_recovery; use Path.open (c078d14)
- **lint**: relax ruff/mypy on complex modules to stabilize pre-commit; follow-up fixes later (440d2b5)
- **shellcheck**: suppress unused color vars; safe source; robust array read (a484518)
- fix gitleaks allowlist regex; tune shellcheck to bash and exclude zsh test scripts (12ba697)
- **security**: reduce cognitive complexity in secret scanner by extracting helpers (9fa01ed)
- **security**: replace pickle with JSON for caches and checkpoints (bandit B301) (06f9a2d)
- **pre-commit**: scope ruff/mypy to src and extension; cleanup (ea0d777)
- **security**: refine secret patterns to avoid false positives (Bearer/PGP) (b393e53)
- VS Code cleanup; scanners tuned; gitleaks regex fixed; pre-commit config updated (a46c774)
- Add START_HERE.md - Quick start guide for immediate use (153d485)
- Final adjustments: CI workflow update (2357a65)
- Add final documentation and sharing guide (c13b3d6)
- Initial commit: Claude Code Template with 2025 features (94ad531)

### Fixed

- Phase 15 - 西暦年表記削除ロジック修正（out_of_range対応） (a2c3bec)
- アインシュタイン誤削除問題の完全解決 (23d78cc)
- PDCAガーディアンのテストコード修正 (63784b0)
- **sonarlint**: remove commented code in error_recovery; improve exception specificity and constants in remote_mcp_integration (7729546)
- **sonarlint**: presets nested ternaries → explicit; n8n_automation constants and cleanup (6ae9623)
- **types**: guard None when parsing pytest summary counts (77286de)
- **sonarlint**: history unused imports; headless_mode complexity reductions (helpers, constants) (d81a3b1)
- **sonarlint**: TS optional chaining and remove unused var; py fixes for S7502/S7503/S1481; session alias naming and cleanup (22e86cd)
- **bandit**: restrict generated script perms to 0o700 (bb27a21)
- **lints**: README markdownlint, bandit (timeouts/permissions), minor refactors; (942a30f)
- **types**: use cast() for proper type assertion in beartype cached return (5fa778e)
- **types**: final mypy green pass – beartype cached return type assertion (a723bfa)
- **types**: mypy green pass set 2 – fix decorator delay int; beartype cached typing; performance list_tools return typing (4debc2c)
- **types**: mypy green pass set 1 – session get return typing; with_retry wrapper typing; headless review result typing; performance Optimizer Coroutine/AsyncIterator; avoid false detect-private-key; beartype create_user value types (0b5906c)
- **shellcheck**: quote env export and avoid SC2199 by iterating args (08049e7)
