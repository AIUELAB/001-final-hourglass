# 統合ルール管理システム - 運用マニュアル

**作成日**: 2025年10月2日
**バージョン**: 1.0.0
**最終更新**: 2025年10月2日

---

## 📋 目次

1. [システム概要](#システム概要)
2. [日常運用](#日常運用)
3. [ルール管理操作](#ルール管理操作)
4. [監視とアラート](#監視とアラート)
5. [トラブルシューティング](#トラブルシューティング)
6. [緊急時対応](#緊急時対応)
7. [定期メンテナンス](#定期メンテナンス)

---

## システム概要

### アーキテクチャ

```
統合ルール管理システム
│
├─ rules_registry.json        # 単一情報源（Single Source of Truth）
│   └─ 74ルールの完全定義
│
├─ 自動同期システム
│   ├─ pdca_guardian.py       # PDCAシステムに同期
│   └─ episode_guardian_config.json  # エピソード生成に同期
│
└─ 監視システム
    ├─ ヘルスモニター         # 6時間ごとの自動チェック
    ├─ Gitフック             # コミット時の自動同期
    └─ ファイル監視           # リアルタイム変更検出
```

### 主要コンポーネント

| ファイル | 役割 | 更新頻度 |
|---------|------|----------|
| `rules_registry.json` | ルール定義の中央レジストリ | 手動（必要時） |
| `pdca_guardian.py` | PDCAシステム本体 | 自動同期 |
| `episode_guardian_config.json` | エピソード生成設定 | 自動同期 |
| `rule_health_report.json` | ヘルスチェック結果 | 6時間ごと |
| `rule_sync_report.json` | 同期ステータス | 同期時 |

---

## 日常運用

### 起動時チェック（毎日1回推奨）

```bash
# ヘルスチェック実行
python3 rule_health_monitor.py

# 期待する出力:
# ✅ ドキュメント完全性: PASS
# ✅ 矛盾検出: PASS
# ✅ 同期ステータス: PASS
# ✅ ファイル整合性: PASS
# ✅ ルール統計: PASS
# ✅ 総合判定: PASS
```

### 週次チェック（毎週月曜日推奨）

```bash
# 1. 詳細レポートの確認
cat rule_health_report.json | python3 -m json.tool

# 2. 同期ステータスの確認
cat rule_sync_report.json | python3 -m json.tool

# 3. 自動同期ログの確認
cat rule_auto_sync_log.json | python3 -m json.tool | head -50
```

### 監視システムの状態確認

#### macOS (launchd)
```bash
# ステータス確認
launchctl list | grep unified-rule-system

# ログ確認
tail -f logs/rule_health_launchd.log
```

#### Linux (systemd)
```bash
# タイマー状態確認
systemctl --user status unified-rule-health-monitor.timer

# ログ確認
journalctl --user -u unified-rule-health-monitor.service -f
```

#### 共通 (cron)
```bash
# cron設定確認
crontab -l | grep rule_health

# cronログ確認
tail -f logs/rule_health_cron.log
```

---

## ルール管理操作

### ルールの追加

```python
from unified_rule_management_system import UnifiedRuleRegistry, RuleCategory, RulePriority, RuleStatus

# レジストリ読み込み
registry = UnifiedRuleRegistry()

# 新しいルール追加
registry.add_rule(
    rule_id="RULE_999",
    name="新しいルール名",
    description="詳細な説明文...",
    category=RuleCategory.DATA_QUALITY,
    priority=RulePriority.MEDIUM,
    tags=["tag1", "tag2"]
)

# 保存
registry.save()
```

### ルールの更新

```python
# レジストリ読み込み
registry = UnifiedRuleRegistry()

# ルール更新
updates = {
    'description': '更新された説明文...',
    'priority': RulePriority.HIGH
}

registry.update_rule("RULE_999", updates)

# 保存
registry.save()
```

### ルールの非推奨化

```python
# レジストリ読み込み
registry = UnifiedRuleRegistry()

# 非推奨化（別のルールに置き換え）
registry.deprecate_rule(
    rule_id="RULE_999",
    replaced_by="RULE_1000"
)

# 保存
registry.save()
```

### 同期の実行

```bash
# 手動同期
python3 rule_sync_automation.py

# 期待する出力:
# ✅ PDCAガーディアン同期完了: 73ルール
# ✅ EpisodeGuardian設定同期完了: 73ルール
# ✅ 全システム同期成功 (2/2)
```

### Git操作での自動同期

```bash
# rules_registry.jsonを変更
vi rules_registry.json

# コミット時に自動同期が実行される
git add rules_registry.json
git commit -m "Add new rule RULE_999"

# 自動的に以下が実行される:
# 1. rule_sync_automation.py による同期
# 2. 同期結果のステージング
# 3. rule_health_monitor.py によるヘルスチェック
```

---

## 監視とアラート

### ヘルスチェック項目

| 項目 | 正常基準 | 警告基準 | 異常基準 |
|------|---------|---------|---------|
| **ドキュメント率** | ≥95% | 90-95% | <90% |
| **矛盾数** | 0件 | - | ≥1件 |
| **同期経過時間** | ≤24時間 | 24-48時間 | >48時間 |
| **チェックサム一致** | 一致 | - | 不一致 |
| **ファイル整合性** | 問題なし | - | 問題あり |

### アラート対応フロー

```
アラート検出
    ↓
ヘルスレポート確認
    ↓
該当項目の詳細分析
    ↓
┌─────────────────┐
│ドキュメント率低下│ → 未ドキュメントルールを特定・文書化
├─────────────────┤
│矛盾検出         │ → 矛盾内容を分析・ルール調整
├─────────────────┤
│同期遅延         │ → 手動同期実行・原因調査
├─────────────────┤
│チェックサム不一致│ → ファイル比較・再同期実行
├─────────────────┤
│ファイル整合性    │ → バックアップから復元検討
└─────────────────┘
    ↓
再ヘルスチェック実行
    ↓
正常化確認
```

### 自動監視の設定確認

```bash
# 定期監視が正常に動作しているか確認
./scripts/setup-rule-monitoring.sh

# 出力の確認ポイント:
# - cronジョブ登録済み
# - launchd/systemd設定完了
# - 初回ヘルスチェック成功
```

---

## トラブルシューティング

### 問題1: 同期が失敗する

**症状**: `rule_sync_automation.py`実行時にエラー

**原因と対処**:

1. **構文エラー**
   ```bash
   # Python構文チェック
   python3 -m py_compile pdca_guardian.py

   # エラーがある場合はバックアップから復元
   cp rule_backups/pdca_guardian.py.backup_* pdca_guardian.py
   ```

2. **JSON形式エラー**
   ```bash
   # JSON検証
   python3 -m json.tool rules_registry.json > /dev/null

   # エラーがある場合は手動修正
   vi rules_registry.json
   ```

3. **権限エラー**
   ```bash
   # ファイル権限確認
   ls -la rules_registry.json pdca_guardian.py episode_guardian_config.json

   # 必要に応じて権限変更
   chmod 644 rules_registry.json pdca_guardian.py episode_guardian_config.json
   ```

### 問題2: ヘルスチェックが警告を出す

**症状**: `WARN`ステータスが表示される

**対処フロー**:

```bash
# 1. 詳細レポートを確認
cat rule_health_report.json | python3 -m json.tool

# 2. 該当項目の詳細を分析
#    例: ドキュメント率低下の場合
python3 <<EOF
from unified_rule_management_system import UnifiedRuleRegistry
registry = UnifiedRuleRegistry()
for rule_id, rule in registry.rules.items():
    if not rule.description:
        print(f"未ドキュメント: {rule_id} - {rule.name}")
EOF

# 3. 問題を修正

# 4. 再チェック
python3 rule_health_monitor.py
```

### 問題3: 矛盾が検出される

**症状**: ヘルスチェックで矛盾が報告される

**対処**:

```python
from unified_rule_management_system import UnifiedRuleRegistry

# 矛盾を詳細に分析
registry = UnifiedRuleRegistry()
conflicts = registry.detect_conflicts()

for rule1_id, rule2_id, reason in conflicts:
    print(f"矛盾: {rule1_id} ⇔ {rule2_id}")
    print(f"理由: {reason}")

    rule1 = registry.rules[rule1_id]
    rule2 = registry.rules[rule2_id]

    print(f"\n{rule1_id}:")
    print(f"  名前: {rule1.name}")
    print(f"  優先度: {rule1.priority}")
    print(f"  カテゴリ: {rule1.category}")

    print(f"\n{rule2_id}:")
    print(f"  名前: {rule2.name}")
    print(f"  優先度: {rule2.priority}")
    print(f"  カテゴリ: {rule2.category}")

    # 解決策を検討:
    # - 片方を非推奨化
    # - ルール定義を調整
    # - 優先度を変更
```

### 問題4: 自動監視が動作しない

**macOS (launchd)**:
```bash
# ステータス確認
launchctl list | grep unified-rule-system

# ロード状態確認
launchctl print gui/$(id -u)/com.unified-rule-system.health-monitor

# アンロード・リロード
launchctl unload ~/Library/LaunchAgents/com.unified-rule-system.health-monitor.plist
launchctl load ~/Library/LaunchAgents/com.unified-rule-system.health-monitor.plist

# ログ確認
cat logs/rule_health_launchd.log
cat logs/rule_health_launchd.err
```

**Linux (systemd)**:
```bash
# タイマー状態確認
systemctl --user status unified-rule-health-monitor.timer

# 即座に実行（テスト）
systemctl --user start unified-rule-health-monitor.service

# ログ確認
journalctl --user -u unified-rule-health-monitor.service -n 50
```

**cron**:
```bash
# crontab確認
crontab -l

# cronログ確認
cat logs/rule_health_cron.log

# 手動実行テスト
cd /Users/admin/Documents/AIUELAB/001-final-hourglass && /usr/bin/python3 rule_health_monitor.py
```

---

## 緊急時対応

### シナリオ1: システム全体が動作しない

**即座の対応**:

```bash
# 1. バックアップから完全復元
cp rule_backups/pdca_guardian.py.backup_* pdca_guardian.py
cp rule_backups/episode_guardian_config.json.backup_* episode_guardian_config.json

# 2. 構文チェック
python3 -m py_compile pdca_guardian.py

# 3. JSON検証
python3 -m json.tool episode_guardian_config.json > /dev/null

# 4. ヘルスチェック
python3 rule_health_monitor.py

# 5. 再同期
python3 rule_sync_automation.py
```

### シナリオ2: ルールが適用されない

**診断と対処**:

```bash
# 1. 同期ステータス確認
cat rule_sync_report.json | python3 -m json.tool

# 2. チェックサム確認
python3 <<EOF
from unified_rule_management_system import UnifiedRuleRegistry
registry = UnifiedRuleRegistry()
print(f"レジストリチェックサム: {registry.checksum}")

import json
with open('rule_sync_report.json') as f:
    sync_report = json.load(f)
print(f"同期レポートチェックサム: {sync_report['checksum']}")

if registry.checksum == sync_report['checksum']:
    print("✅ 一致")
else:
    print("❌ 不一致 - 再同期が必要")
EOF

# 3. 不一致の場合は再同期
python3 rule_sync_automation.py

# 4. アプリケーション再起動
# PDCAシステム・エピソード生成システムを再起動
```

### シナリオ3: データ損失リスク

**予防と復旧**:

```bash
# 1. 定期バックアップの確認
ls -lht rule_backups/ | head -10

# 2. Gitコミット履歴の確認
git log --oneline rules_registry.json | head -10

# 3. 必要に応じてGitから復元
git show HEAD~1:rules_registry.json > rules_registry_recovered.json

# 4. 復元したファイルを検証
python3 -m json.tool rules_registry_recovered.json > /dev/null

# 5. 問題なければ置換
mv rules_registry_recovered.json rules_registry.json

# 6. 再同期
python3 rule_sync_automation.py
```

---

## 定期メンテナンス

### 月次タスク（毎月1日推奨）

1. **バックアップの整理**
   ```bash
   # 古いバックアップを削除（60日以上前）
   find rule_backups/ -name "*.backup_*" -mtime +60 -delete

   # 残りのバックアップ数確認
   ls -1 rule_backups/ | wc -l
   ```

2. **ログのローテーション**
   ```bash
   # ログファイルの圧縮・アーカイブ
   gzip logs/rule_health_cron.log
   mv logs/rule_health_cron.log.gz logs/archive/rule_health_cron_$(date +%Y%m).log.gz

   # 古いログ削除（90日以上前）
   find logs/archive/ -name "*.log.gz" -mtime +90 -delete
   ```

3. **ルール品質レビュー**
   ```python
   from unified_rule_management_system import UnifiedRuleRegistry

   registry = UnifiedRuleRegistry()

   # ドキュメントが古いルールをリスト
   from datetime import datetime, timedelta
   threshold = datetime.now() - timedelta(days=180)

   old_rules = []
   for rule_id, rule in registry.rules.items():
       updated_at = datetime.fromisoformat(rule.updated_at)
       if updated_at < threshold:
           old_rules.append((rule_id, rule.name, rule.updated_at))

   print(f"180日以上更新されていないルール: {len(old_rules)}件")
   for rule_id, name, updated_at in old_rules:
       print(f"  {rule_id}: {name} (最終更新: {updated_at})")
   ```

### 四半期タスク（1/4/7/10月）

1. **包括的レビュー**
   - すべてのルール定義の妥当性確認
   - 廃止候補ルールの特定
   - 新規ルールの必要性検討

2. **パフォーマンス最適化**
   - レジストリファイルサイズ確認
   - 検索・同期速度の測定
   - 必要に応じて最適化実施

3. **ドキュメント更新**
   - 本マニュアルの見直し
   - FAQの追加
   - ベストプラクティスの更新

---

## 運用メトリクス

### 追跡すべき指標

| 指標 | 目標値 | 測定方法 |
|------|--------|----------|
| **ドキュメント率** | 100% | `rule_health_report.json` |
| **矛盾数** | 0件 | `rule_health_report.json` |
| **同期成功率** | >99% | `rule_auto_sync_log.json` |
| **ヘルスチェック成功率** | 100% | 監視ログ |
| **平均同期時間** | <10秒 | 同期ログ |

### レポート作成

```bash
# 月次レポート生成スクリプト
cat > generate_monthly_report.sh <<'EOF'
#!/bin/bash
echo "統合ルール管理システム - 月次レポート"
echo "生成日: $(date)"
echo ""

echo "=== ヘルスチェック概要 ==="
python3 <<PY
import json
with open('rule_health_report.json') as f:
    report = json.load(f)
print(f"最終チェック: {report['timestamp']}")
print(f"総合判定: {report['checks'][-1]['status']}")
print(f"  PASS: {report['summary']['pass']}件")
print(f"  WARN: {report['summary']['warn']}件")
print(f"  FAIL: {report['summary']['fail']}件")
PY

echo ""
echo "=== 同期ステータス ==="
python3 <<PY
import json
with open('rule_sync_report.json') as f:
    report = json.load(f)
print(f"最終同期: {report['sync_timestamp']}")
print(f"総ルール数: {report['total_rules']}")
print(f"アクティブ: {report['active_rules']}")
print(f"同期先: {', '.join(report['targets_synced'])}")
PY

echo ""
echo "=== ルール統計 ==="
python3 <<PY
from unified_rule_management_system import UnifiedRuleRegistry
from collections import Counter

registry = UnifiedRuleRegistry()
categories = Counter(rule.category.value for rule in registry.rules.values())

print("カテゴリ別ルール数:")
for category, count in categories.most_common():
    print(f"  {category}: {count}件")
PY
EOF

chmod +x generate_monthly_report.sh
```

---

## 連絡先とサポート

### システム管理者

- **担当者**: [管理者名]
- **連絡先**: [メールアドレス]
- **緊急連絡**: [電話番号]

### エスカレーションフロー

```
レベル1: 自己解決
    ↓ (解決しない場合)
レベル2: システム管理者に連絡
    ↓ (解決しない場合)
レベル3: 開発チームに連絡
    ↓ (重大な問題の場合)
レベル4: 緊急対応チーム招集
```

---

## 付録

### A. ファイル一覧

| ファイル | 説明 | バックアップ | 更新頻度 |
|---------|------|------------|----------|
| `rules_registry.json` | ルールレジストリ | 同期時 | 手動 |
| `pdca_guardian.py` | PDCAシステム | 同期時 | 自動 |
| `episode_guardian_config.json` | エピソード設定 | 同期時 | 自動 |
| `rule_health_report.json` | ヘルスレポート | 不要 | 6時間 |
| `rule_sync_report.json` | 同期レポート | 不要 | 同期時 |
| `rule_auto_sync_log.json` | 自動同期ログ | 不要 | 変更時 |

### B. コマンドリファレンス

```bash
# ヘルスチェック実行
python3 rule_health_monitor.py

# 手動同期実行
python3 rule_sync_automation.py

# 自動同期デーモン起動
python3 rule_auto_sync_watcher.py --daemon

# Gitフックインストール
python3 rule_auto_sync_watcher.py --install-hook

# 定期監視セットアップ
./scripts/setup-rule-monitoring.sh

# ルール検証
python3 test_unified_rule_system.py
```

### C. よくある質問（FAQ）

**Q1: ルールを追加したが反映されない**

A: 同期を実行してください。
```bash
python3 rule_sync_automation.py
```

**Q2: ヘルスチェックが失敗する**

A: 詳細レポートを確認し、該当項目を修正してください。
```bash
cat rule_health_report.json | python3 -m json.tool
```

**Q3: バックアップから復元したい**

A: 最新のバックアップをコピーしてください。
```bash
ls -lht rule_backups/ | head -5
cp rule_backups/[最新ファイル] [復元先]
```

---

**運用マニュアル終わり**

*このマニュアルは定期的に見直し、最新の運用実態を反映させてください。*
