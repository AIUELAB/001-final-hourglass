#!/usr/bin/env python3
"""
バリデーション済みエピソード生成システム
create_final_episodes_with_titles.pyの統合システム版

すべてのエピソードが統合バリデーションシステムを通過することを保証
"""

import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import json

# 統合システムをインポート
from unified_episode_factory import UnifiedEpisodeFactory, EpisodeGenerationRequest


class ValidatedEpisodeGenerator:
    """バリデーション済みエピソード生成器"""

    def __init__(self):
        """初期化"""
        # 統合ファクトリ（唯一の生成方法）
        self.factory = UnifiedEpisodeFactory()

        # 人物データベースの定義
        self.persons_data = self._define_persons_data()

        # 生成結果格納
        self.successful_episodes = []
        self.failed_episodes = []
        self.generation_stats = {
            'total_attempts': 0,
            'successful': 0,
            'failed': 0,
            'average_quality': 0.0,
            'min_quality': 100.0,
            'max_quality': 0.0
        }

    def _define_persons_data(self) -> Dict[str, Dict]:
        """101人の人物データを定義（カテゴリ付き）"""
        return {
            # 音楽系
            'Ado': {'age': 21, 'category': 'entertainment'},
            'YOSHIKI': {'age': 23, 'category': 'entertainment'},
            'あいみょん': {'age': 23, 'category': 'entertainment'},
            '坂本龍一': {'age': 35, 'category': 'entertainment'},
            '松田聖子': {'age': 18, 'category': 'entertainment'},
            '星野源': {'age': 35, 'category': 'entertainment'},
            '米津玄師': {'age': 27, 'category': 'entertainment'},

            # 映画・アニメ系
            '北野武': {'age': 50, 'category': 'entertainment'},
            '新海誠': {'age': 43, 'category': 'entertainment'},
            '宮崎駿': {'age': 60, 'category': 'entertainment'},
            '是枝裕和': {'age': 56, 'category': 'entertainment'},
            '黒澤明': {'age': 44, 'category': 'entertainment'},
            '手塚治虫': {'age': 31, 'category': 'entertainment'},

            # ドラマ・テレビ系
            '綾瀬はるか': {'age': 28, 'category': 'entertainment'},
            '新垣結衣': {'age': 28, 'category': 'entertainment'},
            '岡田准一': {'age': 33, 'category': 'entertainment'},
            '渡辺謙': {'age': 44, 'category': 'entertainment'},
            '福山雅治': {'age': 40, 'category': 'entertainment'},
            '松本人志': {'age': 27, 'category': 'entertainment'},
            '櫻井翔': {'age': 32, 'category': 'entertainment'},

            # 文学系
            '西野亮廣': {'age': 40, 'category': 'literature'},
            '村上春樹': {'age': 38, 'category': 'literature'},
            '又吉直樹': {'age': 35, 'category': 'literature'},
            '芥川龍之介': {'age': 23, 'category': 'literature'},
            '夏目漱石': {'age': 38, 'category': 'literature'},
            '三島由紀夫': {'age': 31, 'category': 'literature'},
            '大江健三郎': {'age': 29, 'category': 'literature'},
            '川端康成': {'age': 69, 'category': 'literature'},
            'さくらももこ': {'age': 21, 'category': 'literature'},

            # スポーツ系
            '大谷翔平': {'age': 29, 'category': 'sports'},
            'イチロー': {'age': 45, 'category': 'sports'},
            '松井秀喜': {'age': 31, 'category': 'sports'},
            '野茂英雄': {'age': 27, 'category': 'sports'},
            '田中将大': {'age': 25, 'category': 'sports'},
            '王貞治': {'age': 37, 'category': 'sports'},
            '長嶋茂雄': {'age': 28, 'category': 'sports'},
            '羽生結弦': {'age': 23, 'category': 'sports'},
            '浅田真央': {'age': 19, 'category': 'sports'},
            '荒川静香': {'age': 24, 'category': 'sports'},
            '高橋尚子': {'age': 28, 'category': 'sports'},
            '野口みずき': {'age': 25, 'category': 'sports'},
            '北島康介': {'age': 21, 'category': 'sports'},
            '内村航平': {'age': 23, 'category': 'sports'},
            '室伏広治': {'age': 29, 'category': 'sports'},
            '吉田沙保里': {'age': 23, 'category': 'sports'},
            '伊調馨': {'age': 23, 'category': 'sports'},
            '古賀稔彦': {'age': 25, 'category': 'sports'},
            '吉田秀彦': {'age': 23, 'category': 'sports'},
            '錦織圭': {'age': 24, 'category': 'sports'},
            '大坂なおみ': {'age': 20, 'category': 'sports'},
            '松山英樹': {'age': 29, 'category': 'sports'},
            '石川遼': {'age': 17, 'category': 'sports'},
            '渋野日向子': {'age': 20, 'category': 'sports'},
            '宮里藍': {'age': 19, 'category': 'sports'},
            '上田桃子': {'age': 21, 'category': 'sports'},
            '平野美宇': {'age': 17, 'category': 'sports'},
            '池江璃花子': {'age': 18, 'category': 'sports'},
            '紀平梨花': {'age': 16, 'category': 'sports'},
            '八村塁': {'age': 21, 'category': 'sports'},
            '久保建英': {'age': 18, 'category': 'sports'},

            # ビジネス系
            '孫正義': {'age': 40, 'category': 'business'},
            '三木谷浩史': {'age': 32, 'category': 'business'},
            '柳井正': {'age': 35, 'category': 'business'},
            '前澤友作': {'age': 29, 'category': 'business'},
            '堀江貴文': {'age': 31, 'category': 'business'},
            '藤田晋': {'age': 25, 'category': 'business'},
            '落合陽一': {'age': 31, 'category': 'business'},
            '松下幸之助': {'age': 22, 'category': 'business'},
            '盛田昭夫': {'age': 25, 'category': 'business'},
            '稲盛和夫': {'age': 27, 'category': 'business'},
            '豊田章男': {'age': 52, 'category': 'business'},
            'HIKAKIN': {'age': 31, 'category': 'business'},

            # 科学系
            '山中伸弥': {'age': 45, 'category': 'science'},
            '本庶佑': {'age': 76, 'category': 'science'},
            '大隅良典': {'age': 71, 'category': 'science'},
            '梶田隆章': {'age': 56, 'category': 'science'},
            '遠藤章': {'age': 46, 'category': 'science'},
            '満屋裕明': {'age': 35, 'category': 'science'},

            # 芸術系
            '草間彌生': {'age': 28, 'category': 'art'},
            '奈良美智': {'age': 41, 'category': 'art'},
            '村上隆': {'age': 39, 'category': 'art'},
            '横尾忠則': {'age': 35, 'category': 'art'},
            '安藤忠雄': {'age': 48, 'category': 'art'},

            # その他
            '小澤征爾': {'age': 24, 'category': 'entertainment'},
            '野村萬斎': {'age': 33, 'category': 'entertainment'},
            '安倍晋三': {'age': 52, 'category': 'politics'},
            '小泉純一郎': {'age': 59, 'category': 'politics'},
            'イモトアヤコ': {'age': 27, 'category': 'entertainment'},
            'ヘレン・ケラー': {'age': 24, 'category': 'other'},
            'マザー・テレサ': {'age': 40, 'category': 'other'},
            'マリー・キュリー': {'age': 36, 'category': 'science'},
            'マーティン・ルーサー・キング・ジュニア': {'age': 34, 'category': 'other'},
            'アルベルト・アインシュタイン': {'age': 26, 'category': 'science'},
            'イーロン・マスク': {'age': 30, 'category': 'business'},
            'ジェフ・ベゾス': {'age': 30, 'category': 'business'},
            'スティーブ・ジョブズ': {'age': 21, 'category': 'business'},
            'ビル・ゲイツ': {'age': 20, 'category': 'business'},
            '羽生善治': {'age': 26, 'category': 'other'},
            '藤井聡太': {'age': 19, 'category': 'other'},
            '福沢諭吉': {'age': 25, 'category': 'other'}
        }

    def generate_all_episodes(self):
        """全員分のエピソードを生成"""
        print("=" * 60)
        print("バリデーション済みエピソード生成開始")
        print(f"対象人物: {len(self.persons_data)}人")
        print("=" * 60)

        for i, (person_name, data) in enumerate(self.persons_data.items(), 1):
            print(f"\n[{i}/{len(self.persons_data)}] {person_name} ({data['age']}歳)")

            # リクエスト作成
            request = EpisodeGenerationRequest(
                person_name=person_name,
                age=data['age'],
                category=data.get('category', 'other'),
                min_quality_score=70.0,
                max_attempts=5,
                strict_mode=True
            )

            # エピソード生成（統合システム経由）
            self.generation_stats['total_attempts'] += 1
            response = self.factory.generate(request)

            if response.success:
                print(f"  ✅ 成功 (スコア: {response.quality_score:.1f})")
                print(f"     {response.episode[:60]}...")

                # 成功エピソード保存
                self.successful_episodes.append({
                    'person_name': person_name,
                    'age': data['age'],
                    'episode': response.episode,
                    'character_count': len(response.episode),
                    'quality_score': response.quality_score,
                    'category': data.get('category', 'other'),
                    'attempts': response.attempts
                })

                # 統計更新
                self.generation_stats['successful'] += 1
                self.generation_stats['min_quality'] = min(
                    self.generation_stats['min_quality'],
                    response.quality_score
                )
                self.generation_stats['max_quality'] = max(
                    self.generation_stats['max_quality'],
                    response.quality_score
                )

            else:
                print(f"  ❌ 失敗: {response.error_message}")

                # 失敗エピソード記録
                self.failed_episodes.append({
                    'person_name': person_name,
                    'age': data['age'],
                    'error': response.error_message,
                    'attempts': response.attempts
                })

                self.generation_stats['failed'] += 1

        # 平均品質スコア計算
        if self.successful_episodes:
            self.generation_stats['average_quality'] = sum(
                ep['quality_score'] for ep in self.successful_episodes
            ) / len(self.successful_episodes)

    def save_results(self):
        """結果をCSVファイルに保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if self.successful_episodes:
            # 成功エピソードをCSV保存
            success_df = pd.DataFrame(self.successful_episodes)
            success_path = f"validated_episodes_{timestamp}.csv"

            # UTF-8 BOM付きで保存（Excel対応）
            with open(success_path, 'w', encoding='utf-8-sig') as f:
                success_df.to_csv(f, index=False)

            print(f"\n✅ 成功エピソード保存: {success_path}")
            print(f"  件数: {len(self.successful_episodes)}")

        if self.failed_episodes:
            # 失敗エピソードをCSV保存
            failed_df = pd.DataFrame(self.failed_episodes)
            failed_path = f"failed_episodes_{timestamp}.csv"

            with open(failed_path, 'w', encoding='utf-8-sig') as f:
                failed_df.to_csv(f, index=False)

            print(f"\n⚠️ 失敗エピソード保存: {failed_path}")
            print(f"  件数: {len(self.failed_episodes)}")

    def show_statistics(self):
        """統計情報を表示"""
        print("\n" + "=" * 60)
        print("📊 生成統計")
        print("=" * 60)

        print(f"総試行数: {self.generation_stats['total_attempts']}")
        print(f"成功: {self.generation_stats['successful']}")
        print(f"失敗: {self.generation_stats['failed']}")

        if self.generation_stats['successful'] > 0:
            success_rate = (
                self.generation_stats['successful'] /
                self.generation_stats['total_attempts'] * 100
            )
            print(f"成功率: {success_rate:.1f}%")
            print(f"平均品質スコア: {self.generation_stats['average_quality']:.1f}")
            print(f"最低品質スコア: {self.generation_stats['min_quality']:.1f}")
            print(f"最高品質スコア: {self.generation_stats['max_quality']:.1f}")

        # カテゴリ別統計
        if self.successful_episodes:
            print("\nカテゴリ別成功数:")
            categories = {}
            for ep in self.successful_episodes:
                cat = ep['category']
                categories[cat] = categories.get(cat, 0) + 1

            for cat, count in sorted(categories.items()):
                print(f"  {cat}: {count}件")

    def verify_quality(self):
        """品質検証レポート"""
        if not self.successful_episodes:
            print("検証するエピソードがありません")
            return

        print("\n" + "=" * 60)
        print("🔍 品質検証レポート")
        print("=" * 60)

        # 品質基準チェック
        checks = {
            'length_ok': 0,
            'has_person_name': 0,
            'has_age': 0,
            'starts_correctly': 0,
            'ends_correctly': 0,
            'quality_above_70': 0
        }

        for ep in self.successful_episodes:
            episode = ep['episode']

            # 文字数チェック
            if 132 <= len(episode) <= 250:
                checks['length_ok'] += 1

            # 人物名チェック
            if ep['person_name'] in episode:
                checks['has_person_name'] += 1

            # 年齢チェック
            if f"{ep['age']}歳" in episode:
                checks['has_age'] += 1

            # フォーマットチェック
            if episode.startswith('あなたと同じ'):
                checks['starts_correctly'] += 1

            if episode.endswith('。'):
                checks['ends_correctly'] += 1

            # 品質スコアチェック
            if ep['quality_score'] >= 70:
                checks['quality_above_70'] += 1

        # 結果表示
        total = len(self.successful_episodes)
        for check_name, count in checks.items():
            percentage = count / total * 100
            status = "✅" if percentage == 100 else "⚠️"
            print(f"{status} {check_name}: {count}/{total} ({percentage:.1f}%)")


def main():
    """メイン処理"""
    generator = ValidatedEpisodeGenerator()

    # 全エピソード生成
    generator.generate_all_episodes()

    # 結果保存
    generator.save_results()

    # 統計表示
    generator.show_statistics()

    # 品質検証
    generator.verify_quality()

    print("\n✅ 処理完了")


if __name__ == "__main__":
    main()
