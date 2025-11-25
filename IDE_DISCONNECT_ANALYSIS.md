# IDE（Cursor）切断の根本原因分析レポート

**分析日時**: 2025年8月29日 00:43:00  
**システム状態**: macOS 64GB RAM、Load Average 18.39-19.64（危険レベル）

## 🚨 Critical Evidence - 根本原因の特定

### 1. メモリ枯渇による系統的障害
- **物理メモリ**: 64GB中63.65GB使用（99.5%使用率）
- **空きメモリ**: わずか350MB（134,955ページ × 4KB = 527MB）
- **メモリ圧縮**: 1.7GB圧縮済み（システム負荷の証拠）
- **結論**: メモリ枯渇がIDE切断の直接原因

### 2. 大量ファイル監視によるリソース枯渇
- **プロジェクトサイズ**: 6.0GB（異常に巨大）
- **CSV/JSONファイル**: 7,348個（プロジェクト全体）
- **プロジェクトルート直下**: 390個のCSV/JSONファイル
- **Cursorが開いているファイル**: 2,014個
- **結論**: ファイルウォッチャーが大量リソースを消費

### 3. SonarLint Java プロセスによるメモリリーク
```bash
PID 44627: Java SonarLint - 2.2GB RAM消費（3.3%）
PID 41946: Java SonarLint - 1.3GB RAM消費（1.9%）
```
- **合計**: 約3.5GBのメモリ消費
- **稼働時間**: 3時間以上継続
- **状況**: メモリリークの可能性が高い

### 4. MCPサーバーの多重起動
- **検出されたMCPサーバー**: 10プロセス
- **重複サーバー**: filesystem, playwright, brave-search, firecrawl
- **問題**: 同一サーバーが複数セッションで起動中

### 5. Cursor監視システムの暴走
- **監視プロセス**: 5個実行中
- **CPU消費**: PID 1846 - 124時間22分（異常な長時間稼働）
- **監視対象**: 誤ったパス（00-final-hourglass vs 001-final-hourglass）

## 🎯 優先度別解決策

### 🔴 CRITICAL - 即座に実行が必要

#### A. メモリ解放（即座に実行）
```bash
# SonarLint Javaプロセスの強制終了
kill -9 44627 41946

# 重複MCPサーバーの終了
pkill -f "mcp-server-playwright"
pkill -f "firecrawl-mcp"
pkill -f "brave-search-mcp"

# 誤った監視プロセスの終了
kill -9 1846
```

#### B. ファイルウォッチャー負荷軽減
```bash
# 不要なCSV/JSONファイルをアーカイブディレクトリに移動
mkdir -p archive_temp
mv ultra_think_*.csv archive_temp/
mv *.json archive_temp/
```

### 🟡 IMPORTANT - システム安定化

#### C. Cursor設定の最適化
1. **File Watcher除外設定**:
   ```json
   "files.watcherExclude": {
     "**/*.csv": true,
     "**/*.json": true,
     "**/archive_temp/**": true,
     "**/.git/**": true
   }
   ```

2. **SonarLint無効化**:
   ```json
   "sonarlint.rules": {},
   "sonarlint.disableTelemetry": true
   ```

#### D. MCP設定の最適化
```bash
# MCP設定をMinimalモードに変更
echo '{"profile": "minimal"}' > mcp-config/active-profile.json
```

### 🟢 RECOMMENDED - 長期安定性

#### E. プロジェクト構造の改善
```bash
# 大量ファイルの整理
mkdir -p {data,logs,backups,temp}
mv *_20250*.csv data/
mv *_log_*.json logs/
mv backup_*.csv backups/
```

#### F. リソース監視システム
```bash
# メモリ監視スクリプトの導入
cat > ~/.cursor-memory-guard.sh << 'EOF'
#!/bin/bash
while true; do
  mem_usage=$(vm_stat | awk '/Pages free:/ {print $3}' | tr -d '.')
  if [ $mem_usage -lt 200000 ]; then
    pkill -f "sonarlint-ls.jar"
    echo "Emergency: SonarLint killed due to memory pressure"
  fi
  sleep 30
done
EOF
chmod +x ~/.cursor-memory-guard.sh
```

## 📊 Impact Analysis - 影響度分析

### 障害連鎖の構造
```
大量ファイル（7,348個）
    ↓
File Watcher過負荷
    ↓
メモリ使用量増加（SonarLint 3.5GB）
    ↓
物理メモリ枯渇（99.5%使用）
    ↓
システムスワップ発生
    ↓
IDE応答性低下 → 切断
```

### パフォーマンス指標
- **Load Average**: 18.39（正常値：4.0以下）
- **CPU使用率**: 60.38% user + 18.85% sys = 79.23%
- **メモリ圧迫度**: 99.5%（危険域：85%以上）
- **ファイル記述子**: 2,014個（Cursorのみ）

## ⚡ Emergency Recovery Plan

### Phase 1: 即座のリソース解放（5分）
```bash
# 1. メモリ消費上位プロセス終了
kill -9 44627 41946 1846

# 2. 重複MCPサーバー終了
pkill -f "mcp-server"

# 3. Cursor再起動
osascript -e 'quit app "Cursor"'
sleep 5
open -a Cursor
```

### Phase 2: 構造的問題解決（15分）
```bash
# 4. ファイル整理
mkdir -p archive_$(date +%Y%m%d)
mv ultra_think_*.csv archive_$(date +%Y%m%d)/

# 5. 設定最適化
echo '{"profile": "minimal"}' > mcp-config/active-profile.json

# 6. 監視システム修正
sed -i '' 's/00-final-hourglass/001-final-hourglass/g' ~/.cursor-stability-monitor.sh
```

### Phase 3: 予防措置（30分）
- File Watcher除外設定
- SonarLint設定最適化
- メモリ監視システム導入

## 🔬 Technical Insights

### Root Cause Hierarchy
1. **Primary**: プロジェクト内の7,348個の大量ファイルによるFile Watcher過負荷
2. **Secondary**: SonarLint Javaプロセスのメモリリーク（3.5GB）
3. **Tertiary**: MCPサーバーの重複起動とリソース競合

### Prevention Strategy
```bash
# プロジェクト健全性チェック
find . -name "*.csv" -o -name "*.json" | wc -l  # 目標: <100
vm_stat | grep "Pages free"                      # 目標: >500,000
ps aux | grep java | wc -l                      # 目標: <2
```

## 📝 結論

**IDE切断の根本原因**: 6GBプロジェクト内の7,348個のファイルによるFile Watcher過負荷と、SonarLint Javaプロセスのメモリリーク（3.5GB）が組み合わさり、物理メモリの99.5%を消費。システム全体のLoad Averageが18.39に達し、IDEが応答不能となった。

**即座の解決策**: メモリ消費プロセス終了 → ファイル整理 → 設定最適化の3段階アプローチで、30分以内に安定性を回復可能。

**長期対策**: File Watcher除外設定、プロジェクト構造改善、リソース監視システム導入により、再発を防止。
