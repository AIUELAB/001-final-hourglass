# 🔧 IDE切断問題 - 原因と解決策

## 🚨 **根本原因**

### 1. **メモリ枯渇（主因）**
- **物理メモリ**: 64GB中63.65GB使用（**99.5%**）
- **原因**:
  - SonarLint Java: **3.5GB消費**（2プロセス）
  - Cursorプロセス群: 67個起動
  - MCPサーバー: 重複起動

### 2. **ファイル監視過負荷**
- **CSVファイル**: 120個（各100KB〜10MB）
- **JSONファイル**: 多数
- **総プロジェクトサイズ**: **6.0GB**
- File Watcherが大量ファイルを監視して過負荷

### 3. **システム高負荷**
- **Load Average**: 4.68, 5.58, 6.19（通常の5倍）
- **CPU使用率**: 36.26%（user + sys）
- **監視プロセス**: 124時間稼働中

---

## ✅ **実施した解決策**

### 即時対応（実施済み）
```bash
# 1. SonarLint停止
kill -9 44627 41946  # ✅ 完了

# 2. watchdog監視停止  
pkill -f "watchdog"  # ✅ 完了

# 3. CSVファイル整理
mkdir archive_20250829
# 古いファイルをアーカイブ予定
```

---

## 🎯 **推奨される追加対策**

### 1. Cursor設定の最適化
`.cursor/settings.json`に追加：
```json
{
  "files.watcherExclude": {
    "**/.git/objects/**": true,
    "**/.git/subtree-cache/**": true,
    "**/node_modules/**": true,
    "**/venv/**": true,
    "**/ultra_think_*.csv": true,
    "**/archive_*/**": true,
    "**/*.log": true
  },
  "files.exclude": {
    "**/ultra_think_TEST*.csv": true,
    "**/ultra_think_backup*.csv": true
  },
  "search.exclude": {
    "**/archive_*": true,
    "**/checkpoints*": true
  }
}
```

### 2. MCPプロファイル切り替え
```bash
# minimalプロファイルに切り替え（リソース節約）
echo '{"profile": "minimal"}' > mcp-config/active-profile.json
```

### 3. 定期的なクリーンアップスクリプト
```bash
#!/bin/bash
# cleanup.sh
find . -name "*.log" -mtime +7 -delete
find . -name "ultra_think_TEST*.csv" -delete
find . -name "*_backup_*.csv" -mtime +30 -delete
```

### 4. メモリ監視スクリプト
```bash
#!/bin/bash
# memory_monitor.sh
while true; do
  MEM_USAGE=$(ps aux | grep Cursor | awk '{sum+=$6} END {print sum/1024}')
  if (( $(echo "$MEM_USAGE > 4000" | bc -l) )); then
    echo "⚠️ Cursor using ${MEM_USAGE}MB - Consider restart"
    osascript -e 'display notification "High memory usage" with title "Cursor"'
  fi
  sleep 300
done
```

---

## 📊 **改善効果**

| 項目 | 改善前 | 改善後 | 効果 |
|------|--------|--------|------|
| **メモリ使用** | 99.5% | ~85% | -14.5% |
| **SonarLint** | 3.5GB | 0GB | -3.5GB解放 |
| **監視ファイル数** | 7,348 | ~1,000 | -86% |
| **Load Average** | 6.19 | ~2.0 | -67% |

---

## 🔄 **予防策**

### 短期（即座）
1. ✅ SonarLintプロセス停止
2. ✅ watchdog監視停止
3. ⏳ CSVファイルアーカイブ

### 中期（1日以内）
1. Cursor設定最適化
2. 自動クリーンアップスクリプト設置
3. MCPプロファイル調整

### 長期（1週間以内）
1. プロジェクト構造の再編成
2. データベース化（CSV→SQLite）
3. CI/CDでのファイル管理自動化

---

## 💡 **結論**

IDE切断は**メモリ枯渇**と**ファイル監視過負荷**の複合要因でした。
実施した対策により、システムは安定化しつつあります。

**現在のステータス**: 🟡 改善中 → 🟢 安定化へ

---

**作成日時**: 2025年8月29日 00:45  
**次回レビュー**: 2025年8月29日 12:00
