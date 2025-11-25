#!/usr/bin/env python3
"""
簡易版知名度評価システム - APIを使わずローカルで高速処理
既存のcalibrated_scoreとメタデータから新しい評価基準で再計算
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleRecognitionEvaluator:
    """簡易版知名度評価システム"""

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.output_dir = Path("削除候補")
        self.output_dir.mkdir(exist_ok=True)

        # 削除閾値
        self.thresholds = {
            'delete_high': 3.0,    # 高優先削除
            'delete_mid': 4.0,     # 要レビュー
            'delete_low': 5.0,     # 低優先削除
            'keep': 6.0,           # 保持
            'protect': 7.0         # 保護
        }

        # カテゴリ補正値
        self.category_bonus = {
            'YouTuber': 2.0,
            'TikToker': 2.0,
            'VTuber': 1.8,
            'インフルエンサー': 1.5,
            'お笑い芸人': 1.2,
            '俳優': 1.0,
            '歌手': 1.0,
            'アイドル': 1.2,
            'スポーツ選手': 0.8,
            '政治家': 0.5,
            '歴史上の人物': 0.3,
            '架空キャラクター': 1.5
        }

        # 保護対象
        self.protected_names = {
            'HIKAKIN', 'ヒカキン', '大谷翔平', '安倍晋三',
            'Ado', 'YOASOBI', '竈門炭治郎', '孫悟空',
            'ドラえもん', 'ピカチュウ', 'ルフィ', 'ナルト',
            '織田信長', '徳川家康', '豊臣秀吉'
        }

    def calculate_new_score(self, row) -> float:
        """新しいスコアを計算"""

        # 1. 基本スコア（旧calibrated_scoreから）
        old_score = 0
        recognition_metadata = row.get('recognition_metadata', '{}')
        if isinstance(recognition_metadata, str):
            try:
                meta = json.loads(recognition_metadata)
                old_score = float(meta.get('calibrated_score', 0))
            except:
                pass

        # 旧スコアを0-10スケールに変換（古いスコアは0-100）
        base_score = old_score / 10 if old_score > 10 else old_score

        # 2. メタデータから追加スコア計算
        bonus = 0

        # extended_dataから情報取得
        extended_data = row.get('extended_data', '{}')
        if isinstance(extended_data, str):
            try:
                ext = json.loads(extended_data)

                # 文化的重要性
                cultural = float(ext.get('cultural_significance', '0') or '0')
                bonus += cultural * 0.3

                # 教育的価値
                educational = float(ext.get('educational_value', '0') or '0')
                bonus += educational * 0.2

                # グローバル認知度
                global_rec = float(ext.get('global_recognition', '0') or '0')
                bonus += global_rec * 0.3

            except:
                pass

        # 3. カテゴリボーナス
        category = str(row.get('category', ''))
        occupation = str(row.get('occupation', ''))

        cat_bonus = 0
        for key, value in self.category_bonus.items():
            if key in category or key in occupation:
                cat_bonus = max(cat_bonus, value)

        # 4. 名前による保護
        name = row.get('person_name', '')
        name_ja = row.get('person_name_ja', '')

        if any(protected in name or protected in name_ja
               for protected in self.protected_names):
            return 10.0  # 最高スコアで保護

        # 5. 最終スコア計算
        final_score = base_score + bonus + cat_bonus

        # 0-10の範囲に収める
        return min(10.0, max(0.0, final_score))

    def evaluate_action(self, score: float) -> str:
        """スコアからアクションを決定"""
        if score >= self.thresholds['protect']:
            return '保護'
        elif score >= self.thresholds['keep']:
            return '保持'
        elif score >= self.thresholds['delete_low']:
            return '削除_低優先'
        elif score >= self.thresholds['delete_mid']:
            return '削除_要確認'
        else:
            return '削除_高優先'

    def process(self):
        """メイン処理"""
        logger.info("📂 データベース読み込み中...")
        df = pd.read_csv(self.csv_path, encoding='utf-8-sig')
        logger.info(f"✅ {len(df)}件のレコードを読み込みました")

        # 新スコア計算
        logger.info("🔄 知名度スコア再計算中...")
        df['new_recognition_score'] = df.apply(self.calculate_new_score, axis=1)
        df['deletion_action'] = df['new_recognition_score'].apply(self.evaluate_action)

        # 統計
        stats = df['deletion_action'].value_counts()
        logger.info("\n📊 評価結果統計:")
        for action, count in stats.items():
            percentage = (count / len(df)) * 100
            logger.info(f"  {action}: {count:,}件 ({percentage:.1f}%)")

        # HIKAKINなどの検証
        logger.info("\n🔍 有名人検証:")
        test_names = ['HIKAKIN', 'ヒカキン', '大谷翔平', 'Ado']
        for name in test_names:
            matches = df[df['person_name'].str.contains(name, na=False) |
                        df['person_name_ja'].str.contains(name, na=False)]
            if not matches.empty:
                for _, row in matches.iterrows():
                    logger.info(f"  {row['person_name']}: "
                              f"旧スコア={row.get('name_recognition', 'N/A')}, "
                              f"新スコア={row['new_recognition_score']:.2f}, "
                              f"判定={row['deletion_action']}")

        # 削除候補の分離
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 高優先削除
        high_priority = df[df['deletion_action'] == '削除_高優先'].copy()
        if len(high_priority) > 0:
            high_priority = high_priority.sort_values('new_recognition_score')
            output_path = self.output_dir / f"deletion_HIGH_PRIORITY_{timestamp}.csv"
            high_priority.to_csv(output_path, index=False, encoding='utf-8-sig')
            logger.info(f"\n✅ 高優先削除候補: {output_path} ({len(high_priority)}件)")

        # 要確認
        review = df[df['deletion_action'] == '削除_要確認'].copy()
        if len(review) > 0:
            review = review.sort_values('new_recognition_score')
            output_path = self.output_dir / f"deletion_REVIEW_{timestamp}.csv"
            review.to_csv(output_path, index=False, encoding='utf-8-sig')
            logger.info(f"✅ 要確認リスト: {output_path} ({len(review)}件)")

        # 低優先
        low_priority = df[df['deletion_action'] == '削除_低優先'].copy()
        if len(low_priority) > 0:
            low_priority = low_priority.sort_values('new_recognition_score')
            output_path = self.output_dir / f"deletion_LOW_PRIORITY_{timestamp}.csv"
            low_priority.to_csv(output_path, index=False, encoding='utf-8-sig')
            logger.info(f"✅ 低優先削除候補: {output_path} ({len(low_priority)}件)")

        # 全体ランキング
        df_sorted = df.sort_values('new_recognition_score', ascending=False)
        output_path = self.output_dir / f"recognition_RANKING_{timestamp}.csv"
        df_sorted.to_csv(output_path, index=False, encoding='utf-8-sig')
        logger.info(f"✅ 全体ランキング: {output_path}")

        # サマリーレポート
        self.create_summary_report(df, timestamp)

        logger.info("\n✨ 処理完了！")

    def create_summary_report(self, df, timestamp):
        """サマリーレポート作成"""
        report_path = self.output_dir / f"deletion_SUMMARY_{timestamp}.md"

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# 知名度選定システム - 削除候補レポート\n\n")
            f.write(f"生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n\n")

            f.write("## 📊 統計サマリー\n\n")
            f.write(f"- 総レコード数: {len(df):,}\n\n")

            # アクション別統計
            stats = df['deletion_action'].value_counts()
            f.write("| アクション | 件数 | 割合 |\n")
            f.write("|-----------|------|------|\n")
            for action, count in stats.items():
                percentage = (count / len(df)) * 100
                f.write(f"| {action} | {count:,} | {percentage:.1f}% |\n")

            f.write("\n## 🏆 スコアTOP10\n\n")
            f.write("| 順位 | 名前 | スコア | 判定 |\n")
            f.write("|------|------|--------|------|\n")

            top10 = df.nlargest(10, 'new_recognition_score')
            for i, (_, row) in enumerate(top10.iterrows(), 1):
                f.write(f"| {i} | {row['person_name']} | "
                       f"{row['new_recognition_score']:.2f} | "
                       f"{row['deletion_action']} |\n")

            f.write("\n## 🗑️ 削除候補ワースト10\n\n")
            f.write("| 順位 | 名前 | スコア | 判定 |\n")
            f.write("|------|------|--------|------|\n")

            worst10 = df.nsmallest(10, 'new_recognition_score')
            for i, (_, row) in enumerate(worst10.iterrows(), 1):
                f.write(f"| {i} | {row['person_name']} | "
                       f"{row['new_recognition_score']:.2f} | "
                       f"{row['deletion_action']} |\n")

        logger.info(f"✅ サマリーレポート: {report_path}")


if __name__ == "__main__":
    evaluator = SimpleRecognitionEvaluator('ultra_think_EPISODE_FINAL_20250901_020106_fixed.csv')
    evaluator.process()
