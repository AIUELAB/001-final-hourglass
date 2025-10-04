# エピソードファクトリv2 アラート対応ランブック

## 目次
1. [クリティカルアラート対応](#クリティカルアラート対応)
2. [警告アラート対応](#警告アラート対応)
3. [情報アラート対応](#情報アラート対応)
4. [エスカレーション手順](#エスカレーション手順)
5. [復旧確認手順](#復旧確認手順)

---

## クリティカルアラート対応

### 🚨 ServiceDown - サービス停止

**症状**: Episode Factoryサービスが2分以上ダウン

**影響度**: 🔴 クリティカル - 全機能停止

**対応手順**:

1. **即座確認** (1分以内)
   ```bash
   # サービスステータス確認
   kubectl get pods -n episode-factory
   kubectl describe pod <pod-name> -n episode-factory

   # ログ確認
   kubectl logs -n episode-factory deployment/episode-factory --tail=100
   ```

2. **再起動試行** (3分以内)
   ```bash
   # ポッド再起動
   kubectl rollout restart deployment/episode-factory -n episode-factory

   # 状態監視
   kubectl rollout status deployment/episode-factory -n episode-factory
   ```

3. **ロールバック判断** (5分以内)
   ```bash
   # 最近のデプロイ確認
   kubectl rollout history deployment/episode-factory -n episode-factory

   # 必要に応じてロールバック
   kubectl rollout undo deployment/episode-factory -n episode-factory
   ```

4. **エスカレーション** (10分以内)
   - インシデントコマンダーに通知
   - #incident-response Slackチャンネルに状況報告

**根本原因調査**:
- デプロイメント履歴確認
- 設定変更確認
- 依存サービス状態確認
- リソース枯渇チェック

---

### 🚨 SLOViolation - SLO違反

**症状**: 可用性が99.9%を下回る（5分間）

**影響度**: 🔴 クリティカル - SLA違反リスク

**対応手順**:

1. **現状把握** (即座)
   ```bash
   # メトリクス確認
   curl http://prometheus:9090/api/v1/query?query=episode_factory_availability_ratio

   # エラー率確認
   curl http://prometheus:9090/api/v1/query?query=rate(episode_factory_errors_total[5m])
   ```

2. **エラー原因特定** (3分以内)
   ```bash
   # エラーログ分析
   kubectl logs -n episode-factory deployment/episode-factory --since=10m | grep ERROR

   # トレース確認
   open http://jaeger:16686
   ```

3. **緊急対応** (5分以内)
   - トラフィック制限の検討
   - キャッシュ有効化
   - 非クリティカル機能の一時停止

4. **復旧措置** (10分以内)
   ```bash
   # オートスケール調整
   kubectl scale deployment/episode-factory --replicas=10 -n episode-factory

   # リソース制限緩和
   kubectl patch deployment/episode-factory -n episode-factory \
     -p '{"spec":{"template":{"spec":{"containers":[{"name":"episode-factory","resources":{"limits":{"memory":"2Gi","cpu":"1000m"}}}]}}}}'
   ```

**事後対応**:
- インシデントレポート作成
- RCA（根本原因分析）実施
- 予防策の検討と実装

---

### 🚨 ErrorBudgetBurnRateHigh - エラーバジェット急速消費

**症状**: エラーバジェットが時間あたり14.4倍速で消費

**影響度**: 🔴 クリティカル - 月間バジェット枯渇リスク

**対応手順**:

1. **消費原因特定** (即座)
   ```bash
   # エラー種別分析
   kubectl exec -n episode-factory deployment/episode-factory -- \
     curl -s localhost:9090/metrics | grep error
   ```

2. **機能フリーズ判断** (5分以内)
   - 新機能デプロイ停止
   - カナリアリリース中止
   - A/Bテスト停止

3. **安定化措置** (10分以内)
   ```bash
   # 安定版にピン留め
   kubectl set image deployment/episode-factory \
     episode-factory=episode-factory:v2.0.0-stable \
     -n episode-factory
   ```

**管理判断が必要な項目**:
- [ ] 機能フリーズ発動
- [ ] デプロイメント凍結
- [ ] 顧客通知の必要性

---

## 警告アラート対応

### ⚠️ HighErrorRate - 高エラー率

**症状**: エラー率が1%を超過（5分間）

**影響度**: 🟡 警告 - 品質低下

**対応手順**:

1. **エラーパターン分析** (5分以内)
   ```bash
   # エラー分類
   kubectl logs -n episode-factory deployment/episode-factory --since=30m | \
     grep ERROR | awk '{print $5}' | sort | uniq -c | sort -rn
   ```

2. **一時的緩和策** (10分以内)
   - リトライ設定調整
   - タイムアウト延長
   - サーキットブレーカー調整

3. **監視強化**
   - ダッシュボード常時表示
   - 15分ごとの状況確認

---

### ⚠️ HighLatency - 高レイテンシ

**症状**: P99レイテンシが100ms超過

**影響度**: 🟡 警告 - パフォーマンス低下

**対応手順**:

1. **ボトルネック特定** (5分以内)
   ```bash
   # スロークエリ確認
   kubectl exec -n episode-factory deployment/episode-factory -- \
     tail -n 100 /var/log/slow-query.log

   # CPU/メモリ確認
   kubectl top pods -n episode-factory
   ```

2. **スケーリング判断** (10分以内)
   ```bash
   # HPA状態確認
   kubectl get hpa -n episode-factory

   # 必要に応じて手動スケール
   kubectl scale deployment/episode-factory --replicas=8 -n episode-factory
   ```

---

### ⚠️ HighMemoryUsage - メモリ使用率高

**症状**: メモリ使用率が80%超過

**影響度**: 🟡 警告 - OOMKillリスク

**対応手順**:

1. **メモリリーク確認** (5分以内)
   ```bash
   # ヒープダンプ取得
   kubectl exec -n episode-factory deployment/episode-factory -- \
     jmap -dump:format=b,file=/tmp/heap.hprof <PID>
   ```

2. **一時対応** (10分以内)
   - キャッシュクリア
   - ワーカー再起動
   - GC実行

---

### ⚠️ LowQualityScore - 品質スコア低下

**症状**: 平均品質スコアが90未満（15分間）

**影響度**: 🟡 警告 - コンテンツ品質問題

**対応手順**:

1. **品質分析** (10分以内)
   ```bash
   # 低スコアエピソード抽出
   kubectl exec -n episode-factory deployment/episode-factory -- \
     python3 -c "import quality_analyzer; quality_analyzer.analyze_low_scores()"
   ```

2. **バリデーション強化** (30分以内)
   - 閾値調整
   - ルール追加
   - サンプル検証強化

---

## 情報アラート対応

### ℹ️ LowThroughput - 低スループット

**症状**: リクエスト数が10 req/s未満

**影響度**: 🟢 情報 - 異常の可能性

**対応手順**:

1. **原因確認** (時間があるとき)
   - 時間帯による正常な変動か確認
   - 上流サービスの状態確認
   - メンテナンス予定確認

---

## エスカレーション手順

### レベル1: チーム内対応（0-15分）
- オンコールエンジニアが初期対応
- Slackで状況共有
- 標準手順に従った対応

### レベル2: シニアエンジニア招集（15-30分）
- 問題が解決しない場合
- 複数システムに影響
- データ不整合の可能性

### レベル3: インシデントコマンダー（30分以上）
- 重大インシデント宣言
- 全体調整開始
- ステークホルダー通知

### レベル4: 経営層通知（1時間以上）
- SLA違反の可能性
- 大規模障害
- セキュリティインシデント

**連絡先リスト**:
| 役割 | 名前 | 連絡先 | 備考 |
|-----|------|--------|------|
| オンコール | - | PagerDuty | 24/7 |
| チームリード | - | Slack @teamlead | 営業時間 |
| インシデントコマンダー | - | 緊急電話 | 24/7 |
| CTO | - | メール+電話 | 重大時のみ |

---

## 復旧確認手順

### 1. サービス正常性確認
```bash
# ヘルスチェック
curl -f http://episode-factory:8000/health

# メトリクス確認
curl http://episode-factory:8000/metrics | grep error

# 最近のエラー確認
kubectl logs -n episode-factory deployment/episode-factory --since=5m | grep -c ERROR
```

### 2. SLI/SLO確認
```bash
# 可用性確認
curl http://prometheus:9090/api/v1/query?query=episode_factory_availability_ratio

# レイテンシ確認
curl http://prometheus:9090/api/v1/query?query=histogram_quantile(0.99,episode_factory_response_time_seconds_bucket)

# エラー率確認
curl http://prometheus:9090/api/v1/query?query=rate(episode_factory_errors_total[5m])
```

### 3. ユーザー影響確認
- サンプルリクエスト実行
- エンドツーエンドテスト実行
- ユーザーフィードバック確認

### 4. 事後作業
- [ ] インシデントレポート作成
- [ ] タイムライン整理
- [ ] 改善点の洗い出し
- [ ] ランブック更新
- [ ] 監視強化の検討

---

## アラート無効化手順（メンテナンス時）

```bash
# アラート一時無効化（メンテナンス用）
curl -X POST http://alertmanager:9093/api/v1/silences \
  -H "Content-Type: application/json" \
  -d '{
    "matchers": [
      {"name": "alertname", "value": ".*", "isRegex": true}
    ],
    "startsAt": "2024-01-01T00:00:00Z",
    "endsAt": "2024-01-01T02:00:00Z",
    "createdBy": "maintenance",
    "comment": "Scheduled maintenance"
  }'
```

---

## 関連ドキュメント

- [アーキテクチャ設計書](../docs/architecture.md)
- [監視ダッシュボード](http://grafana:3000/d/episode-factory)
- [SLO定義](../slo_definitions.yaml)
- [インシデント履歴](https://wiki.example.com/incidents)

---

*最終更新: 2025年1月23日*
*次回レビュー予定: 2025年2月23日*