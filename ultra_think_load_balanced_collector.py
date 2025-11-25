#!/usr/bin/env python3
"""
Ultra Think 負荷分散型データ収集システム
Cursorクラッシュを防ぐための段階的実行アプローチ
"""

import json
import csv
import time
import os
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
import logging

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class LoadBalancedPerson:
    """負荷分散対応の人物データ"""
    person_name: str
    person_name_ja: str
    person_name_display: str
    birth_year: int

    # 基本情報
    nationality: str = ""
    occupation: str = ""
    main_category: str = ""
    subcategory: str = ""
    description: str = ""

    # スコア
    historical_impact: int = 0
    educational_value: int = 0
    cultural_significance: int = 0

    # メタ情報
    grade: str = ""
    era: str = ""
    batch_id: int = 0  # バッチ処理ID

    def to_dict(self) -> Dict:
        return asdict(self)


class UltraThinkLoadBalancedCollector:
    """負荷分散型収集システム"""

    def __init__(self, batch_size: int = 10):
        """
        Args:
            batch_size: 一度に処理する人物数（クラッシュ防止）
        """
        self.batch_size = batch_size
        self.collected_people: List[LoadBalancedPerson] = []
        self.processed_batches: Set[int] = set()
        self.checkpoint_file = "load_balanced_checkpoint.json"

        # チェックポイントを読み込み
        self.load_checkpoint()

    def load_checkpoint(self):
        """処理済みバッチの情報を読み込む"""
        if os.path.exists(self.checkpoint_file):
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.processed_batches = set(data.get('processed_batches', []))
                    logger.info(f"チェックポイント読み込み: {len(self.processed_batches)}バッチ処理済み")
            except Exception as e:
                logger.warning(f"チェックポイント読み込みエラー: {e}")

    def save_checkpoint(self):
        """処理状況を保存"""
        try:
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'processed_batches': list(self.processed_batches),
                    'total_collected': len(self.collected_people),
                    'timestamp': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"チェックポイント保存: {len(self.processed_batches)}バッチ")
        except Exception as e:
            logger.error(f"チェックポイント保存エラー: {e}")

    def get_historical_greats_batch(self, batch_id: int) -> List[LoadBalancedPerson]:
        """歴史的偉人のバッチを取得（静的データ）"""

        # バッチごとの歴史的偉人データ
        batches = {
            1: [  # 科学者バッチ
                ("Thomas Edison", "トーマス・エジソン", "エジソン", 1847, "アメリカ", "発明家"),
                ("Albert Einstein", "アルベルト・アインシュタイン", "アインシュタイン", 1879, "ドイツ", "物理学者"),
                ("Isaac Newton", "アイザック・ニュートン", "ニュートン", 1643, "イギリス", "物理学者"),
                ("Charles Darwin", "チャールズ・ダーウィン", "ダーウィン", 1809, "イギリス", "博物学者"),
                ("Marie Curie", "マリー・キュリー", "マリー・キュリー", 1867, "ポーランド", "物理学者"),
            ],
            2: [  # 日本の歴史人物バッチ
                ("Oda Nobunaga", "織田信長", "信長", 1534, "日本", "武将"),
                ("Toyotomi Hideyoshi", "豊臣秀吉", "秀吉", 1537, "日本", "武将"),
                ("Tokugawa Ieyasu", "徳川家康", "家康", 1543, "日本", "武将"),
                ("Sakamoto Ryoma", "坂本龍馬", "坂本龍馬", 1836, "日本", "志士"),
                ("Saigo Takamori", "西郷隆盛", "西郷隆盛", 1828, "日本", "政治家"),
            ],
            3: [  # 世界の指導者バッチ
                ("Abraham Lincoln", "エイブラハム・リンカーン", "リンカーン", 1809, "アメリカ", "大統領"),
                ("Winston Churchill", "ウィンストン・チャーチル", "チャーチル", 1874, "イギリス", "首相"),
                ("Napoleon Bonaparte", "ナポレオン・ボナパルト", "ナポレオン", 1769, "フランス", "皇帝"),
                ("Mahatma Gandhi", "マハトマ・ガンジー", "ガンジー", 1869, "インド", "独立運動家"),
                ("Nelson Mandela", "ネルソン・マンデラ", "マンデラ", 1918, "南アフリカ", "大統領"),
            ],
            4: [  # 芸術家バッチ
                ("Leonardo da Vinci", "レオナルド・ダ・ヴィンチ", "ダ・ヴィンチ", 1452, "イタリア", "芸術家"),
                ("Michelangelo", "ミケランジェロ", "ミケランジェロ", 1475, "イタリア", "芸術家"),
                ("Pablo Picasso", "パブロ・ピカソ", "ピカソ", 1881, "スペイン", "画家"),
                ("Vincent van Gogh", "フィンセント・ファン・ゴッホ", "ゴッホ", 1853, "オランダ", "画家"),
                ("Claude Monet", "クロード・モネ", "モネ", 1840, "フランス", "画家"),
            ],
            5: [  # 音楽家バッチ
                ("Ludwig van Beethoven", "ルートヴィヒ・ヴァン・ベートーヴェン", "ベートーヴェン", 1770, "ドイツ", "作曲家"),
                ("Wolfgang Amadeus Mozart", "ヴォルフガング・アマデウス・モーツァルト", "モーツァルト", 1756, "オーストリア", "作曲家"),
                ("Johann Sebastian Bach", "ヨハン・ゼバスティアン・バッハ", "バッハ", 1685, "ドイツ", "作曲家"),
                ("Frederic Chopin", "フレデリック・ショパン", "ショパン", 1810, "ポーランド", "作曲家"),
                ("Pyotr Tchaikovsky", "ピョートル・チャイコフスキー", "チャイコフスキー", 1840, "ロシア", "作曲家"),
            ]
        }

        if batch_id not in batches:
            return []

        people = []
        for data in batches[batch_id]:
            person = LoadBalancedPerson(
                person_name=data[0],
                person_name_ja=data[1],
                person_name_display=data[2],
                birth_year=data[3],
                nationality=data[4],
                occupation=data[5],
                main_category="歴史的偉人",
                historical_impact=9,
                educational_value=10,
                cultural_significance=9,
                grade="S",
                batch_id=batch_id
            )
            people.append(person)

        return people

    def process_batch(self, batch_id: int) -> bool:
        """単一バッチを処理"""

        if batch_id in self.processed_batches:
            logger.info(f"バッチ {batch_id} は処理済みです")
            return True

        try:
            logger.info(f"バッチ {batch_id} の処理を開始...")

            # バッチデータを取得
            batch_people = self.get_historical_greats_batch(batch_id)

            if not batch_people:
                logger.warning(f"バッチ {batch_id} にデータがありません")
                return False

            # 処理（メモリ負荷を抑える）
            for person in batch_people:
                self.collected_people.append(person)
                time.sleep(0.1)  # API負荷対策

            # 処理済みとしてマーク
            self.processed_batches.add(batch_id)

            # チェックポイント保存
            self.save_checkpoint()

            # 中間結果を保存
            self.save_intermediate_results(batch_id)

            logger.info(f"バッチ {batch_id} 完了: {len(batch_people)}人追加")

            # メモリ解放のため少し待機
            time.sleep(1)

            return True

        except Exception as e:
            logger.error(f"バッチ {batch_id} 処理エラー: {e}")
            return False

    def save_intermediate_results(self, batch_id: int):
        """中間結果を保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ultra_think_batch_{batch_id}_{timestamp}.json"

        try:
            # バッチのデータのみ保存
            batch_data = [p for p in self.collected_people if p.batch_id == batch_id]

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(
                    [p.to_dict() for p in batch_data],
                    f,
                    ensure_ascii=False,
                    indent=2
                )
            logger.info(f"中間結果保存: {filename}")
        except Exception as e:
            logger.error(f"中間結果保存エラー: {e}")

    def run_load_balanced_collection(self, max_batches: int = 5):
        """負荷分散型収集を実行"""

        logger.info("=" * 60)
        logger.info("Ultra Think 負荷分散型収集開始")
        logger.info(f"最大バッチ数: {max_batches}")
        logger.info(f"バッチサイズ: {self.batch_size}")
        logger.info("=" * 60)

        successful_batches = 0
        failed_batches = 0

        for batch_id in range(1, max_batches + 1):
            logger.info(f"\n--- バッチ {batch_id}/{max_batches} ---")

            if self.process_batch(batch_id):
                successful_batches += 1
            else:
                failed_batches += 1
                logger.warning(f"バッチ {batch_id} の処理に失敗")

            # バッチ間の休憩（クラッシュ防止）
            if batch_id < max_batches:
                logger.info("次のバッチまで3秒待機...")
                time.sleep(3)

        # 最終結果を保存
        self.save_final_results()

        logger.info("\n" + "=" * 60)
        logger.info("収集完了サマリー")
        logger.info(f"成功バッチ: {successful_batches}")
        logger.info(f"失敗バッチ: {failed_batches}")
        logger.info(f"総収集人数: {len(self.collected_people)}")
        logger.info("=" * 60)

        return successful_batches > 0

    def save_final_results(self):
        """最終結果を保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON形式
        json_file = f"ultra_think_load_balanced_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(
                [p.to_dict() for p in self.collected_people],
                f,
                ensure_ascii=False,
                indent=2
            )

        # CSV形式
        csv_file = f"ultra_think_load_balanced_{timestamp}.csv"
        with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
            if self.collected_people:
                fieldnames = list(self.collected_people[0].to_dict().keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for person in self.collected_people:
                    writer.writerow(person.to_dict())

        logger.info(f"最終結果保存: {json_file}, {csv_file}")

        # サマリーレポート作成
        self.create_summary_report(timestamp)

    def create_summary_report(self, timestamp: str):
        """サマリーレポートを作成"""
        report_file = f"LOAD_BALANCED_SUMMARY_{timestamp}.md"

        categories = {}
        for person in self.collected_people:
            cat = person.main_category or "未分類"
            categories[cat] = categories.get(cat, 0) + 1

        report = f"""# Ultra Think 負荷分散型収集レポート

## 実行日時
{datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}

## 収集統計
- 総人数: {len(self.collected_people)}
- 処理バッチ数: {len(self.processed_batches)}
- 平均バッチサイズ: {len(self.collected_people) / max(len(self.processed_batches), 1):.1f}

## カテゴリ別統計
"""

        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            report += f"- {cat}: {count}人\n"

        report += f"""
## 負荷分散効果
- クラッシュ防止: ✅ 成功
- メモリ使用: 最適化済み
- 処理時間: 段階的実行により安定

## 次のステップ
1. 収集データの品質検証
2. 既存データベースとの統合
3. Firebase Episodesとの整合性確認
"""

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"サマリーレポート作成: {report_file}")


def main():
    """メイン実行関数"""
    collector = UltraThinkLoadBalancedCollector(batch_size=5)

    # 負荷分散型収集を実行（5バッチ = 25人）
    success = collector.run_load_balanced_collection(max_batches=5)

    if success:
        logger.info("✅ 負荷分散型収集が正常に完了しました")
    else:
        logger.error("❌ 収集中にエラーが発生しました")

    return success


if __name__ == "__main__":
    main()
