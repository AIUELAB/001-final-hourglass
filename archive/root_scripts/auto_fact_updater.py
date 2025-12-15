#!/usr/bin/env python3
"""
Auto Fact Updater
データベースを自動的に最新情報で更新するシステム
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging
import sys

# モジュールのインポート
sys.path.append(str(Path(__file__).parent))
from fact_api_integration import FactAPIIntegration
from fact_freshness_checker import FactFreshnessChecker
from enhanced_selection_algorithm import EnhancedSelectionAlgorithm
from pdca_guardian import PDCAGuardian

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [AutoUpdater] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutoFactUpdater:
    """自動事実更新システム"""

    def __init__(self, database_path: str = "verified_facts_database_103persons.json"):
        self.database_path = database_path
        self.backup_path = database_path.replace('.json', '_backup.json')
        self.log_path = Path('logs/update_logs')
        self.log_path.mkdir(parents=True, exist_ok=True)

        # コンポーネント初期化
        self.api_integration = FactAPIIntegration()
        self.freshness_checker = FactFreshnessChecker(database_path)
        self.selection_algorithm = EnhancedSelectionAlgorithm()
        self.pdca_guardian = PDCAGuardian()

        self.database = self._load_database()
        self.update_stats = {
            'total_updated': 0,
            'total_failed': 0,
            'new_facts_added': 0,
            'start_time': None,
            'end_time': None
        }

    def _load_database(self) -> Dict:
        """データベースの読み込み"""
        try:
            with open(self.database_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Database not found: {self.database_path}")
            return {'verified_facts': {}}

    def _save_database(self, database: Dict):
        """データベースの保存（バックアップ付き）"""
        # バックアップ作成
        if Path(self.database_path).exists():
            with open(self.database_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            with open(self.backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Backup saved: {self.backup_path}")

        # 新データ保存
        with open(self.database_path, 'w', encoding='utf-8') as f:
            json.dump(database, f, ensure_ascii=False, indent=2)
        logger.info(f"Database updated: {self.database_path}")

    async def identify_update_targets(self, limit: int = 10) -> List[Tuple[str, Dict]]:
        """
        更新対象の人物を特定（優先順位付き）

        Args:
            limit: 更新する人物数の上限

        Returns:
            [(人物名, データ)]のリスト
        """
        targets = []

        # 鮮度レポート生成
        freshness_report = self.freshness_checker.generate_freshness_report()

        # 緊急更新が必要な人物を優先
        for person_info in freshness_report['critical_updates'][:limit]:
            person_name = person_info['name']
            if person_name in self.database.get('verified_facts', {}):
                targets.append((
                    person_name,
                    self.database['verified_facts'][person_name]
                ))

        # 不足分を通常更新対象から補充
        if len(targets) < limit:
            for person_info in freshness_report['persons_needing_update']:
                person_name = person_info['person_name']
                if person_name not in [t[0] for t in targets]:
                    if person_name in self.database.get('verified_facts', {}):
                        targets.append((
                            person_name,
                            self.database['verified_facts'][person_name]
                        ))
                        if len(targets) >= limit:
                            break

        logger.info(f"Identified {len(targets)} persons for update")
        return targets

    async def update_person_facts(self, person_name: str, person_data: Dict) -> Dict:
        """
        個人の事実データを更新

        Args:
            person_name: 人物名
            person_data: 既存の人物データ

        Returns:
            更新後のデータ
        """
        try:
            logger.info(f"Updating facts for {person_name}...")

            # API経由で最新データ取得
            async with self.api_integration as api:
                new_facts_data = await api.fetch_person_facts(person_name)

            if not new_facts_data or not new_facts_data.get('facts'):
                logger.warning(f"No new facts found for {person_name}")
                return person_data

            # 既存の事実と新規事実をマージ
            existing_facts = person_data.get('facts', [])
            new_facts = new_facts_data['facts']

            # 重複チェックしながらマージ
            merged_facts = self._merge_facts(existing_facts, new_facts)

            # PDCAガーディアンでチェック
            violations = self._validate_facts(merged_facts, person_name)
            if violations:
                logger.warning(f"Validation issues for {person_name}: {len(violations)} violations")

            # 更新データの構築
            updated_data = person_data.copy()
            updated_data['facts'] = merged_facts
            updated_data['last_updated'] = datetime.now().isoformat()
            updated_data['update_source'] = 'auto_updater'

            # 統計更新
            self.update_stats['new_facts_added'] += len(new_facts)
            self.update_stats['total_updated'] += 1

            logger.info(f"✅ Successfully updated {person_name}: {len(new_facts)} new facts added")
            return updated_data

        except Exception as e:
            logger.error(f"Failed to update {person_name}: {e}")
            self.update_stats['total_failed'] += 1
            return person_data

    def _merge_facts(self, existing: List[Dict], new: List[Dict]) -> List[Dict]:
        """
        既存と新規の事実をマージ（重複排除）

        Args:
            existing: 既存の事実リスト
            new: 新規の事実リスト

        Returns:
            マージされた事実リスト
        """
        # 既存事実のキーを生成（重複チェック用）
        existing_keys = set()
        for fact in existing:
            key = f"{fact.get('year', '')}{fact.get('fact', '')[:30]}"
            existing_keys.add(key)

        # 新規事実を追加（重複していないもののみ）
        merged = existing.copy()
        for fact in new:
            key = f"{fact.get('year', '')}{fact.get('fact', '')[:30]}"
            if key not in existing_keys:
                # yearフィールドを追加（キーワードから抽出）
                if 'year' not in fact and 'keywords' in fact:
                    for keyword in fact['keywords']:
                        if keyword.isdigit() and 2000 <= int(keyword) <= 2025:
                            fact['year'] = int(keyword)
                            break
                merged.append(fact)

        # スコアで再ソート
        merged.sort(
            key=lambda f: self.selection_algorithm.calculate_fact_score(f),
            reverse=True
        )

        return merged

    def _validate_facts(self, facts: List[Dict], person_name: str) -> List[Dict]:
        """
        事実データをPDCAガーディアンで検証

        Args:
            facts: 事実リスト
            person_name: 人物名

        Returns:
            違反リスト
        """
        violations = []

        # 各事実をチェック
        for fact in facts:
            # データ鮮度チェック
            person_data = {'facts': [fact]}
            freshness_violations = self.pdca_guardian.check_data_freshness(
                person_data,
                fact
            )
            violations.extend(freshness_violations)

        return violations

    async def run_batch_update(self, max_persons: int = 10):
        """
        バッチ更新の実行

        Args:
            max_persons: 更新する人物数の上限
        """
        logger.info("=" * 60)
        logger.info("Starting Auto Fact Update Batch")
        logger.info("=" * 60)

        self.update_stats['start_time'] = datetime.now()

        # 更新対象を特定
        targets = await self.identify_update_targets(max_persons)

        # 並列更新（最大5並列）
        batch_size = 5
        for i in range(0, len(targets), batch_size):
            batch = targets[i:i + batch_size]
            tasks = []

            for person_name, person_data in batch:
                tasks.append(self.update_person_facts(person_name, person_data))

            # バッチ実行
            updated_data_list = await asyncio.gather(*tasks)

            # データベースに反映
            for (person_name, _), updated_data in zip(batch, updated_data_list):
                self.database['verified_facts'][person_name] = updated_data

        self.update_stats['end_time'] = datetime.now()

        # データベース保存
        self._save_database(self.database)

        # レポート生成
        self._generate_update_report()

    def _generate_update_report(self):
        """更新レポートの生成"""
        duration = (self.update_stats['end_time'] - self.update_stats['start_time']).total_seconds()

        report = {
            'timestamp': datetime.now().isoformat(),
            'duration_seconds': duration,
            'statistics': {
                'total_updated': self.update_stats['total_updated'],
                'total_failed': self.update_stats['total_failed'],
                'new_facts_added': self.update_stats['new_facts_added'],
                'success_rate': (
                    self.update_stats['total_updated'] /
                    max(1, self.update_stats['total_updated'] + self.update_stats['total_failed'])
                ) * 100
            },
            'performance': {
                'persons_per_minute': (self.update_stats['total_updated'] / duration) * 60 if duration > 0 else 0,
                'facts_per_minute': (self.update_stats['new_facts_added'] / duration) * 60 if duration > 0 else 0
            }
        }

        # レポート保存
        report_path = self.log_path / f"update_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # コンソール出力
        print("\n" + "=" * 60)
        print("📊 Update Report")
        print("=" * 60)
        print(f"Duration: {duration:.1f} seconds")
        print(f"Updated: {self.update_stats['total_updated']} persons")
        print(f"Failed: {self.update_stats['total_failed']} persons")
        print(f"New Facts: {self.update_stats['new_facts_added']}")
        print(f"Success Rate: {report['statistics']['success_rate']:.1f}%")
        print(f"Performance: {report['performance']['persons_per_minute']:.1f} persons/min")
        print(f"\n📄 Report saved: {report_path}")


async def main():
    """メイン処理"""
    print("=" * 60)
    print("Auto Fact Updater - 自動データ更新システム")
    print("=" * 60)

    updater = AutoFactUpdater()

    # テスト実行（3人分のみ）
    print("\n🚀 Starting update for top 3 persons needing updates...")
    await updater.run_batch_update(max_persons=3)

    print("\n✅ Auto update completed!")


if __name__ == "__main__":
    asyncio.run(main())
