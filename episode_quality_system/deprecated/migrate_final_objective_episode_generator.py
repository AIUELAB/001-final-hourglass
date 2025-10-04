#!/usr/bin/env python3
"""
final_objective_episode_generator.pyの統合システム版
客観的で事実ベースのエピソードを統合バリデーションシステムで生成
"""

import json
import csv
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from unified_episode_factory import UnifiedEpisodeFactory, EpisodeGenerationRequest

class MigratedObjectiveEpisodeGenerator:
    """移行版：客観的エピソード生成器"""

    def __init__(self):
        """初期化"""
        print("🔄" * 30)
        print("final_objective_episode_generator.py の統合システム版")
        print("🔄" * 30)

        # 統合ファクトリ使用
        self.factory = UnifiedEpisodeFactory()

        # 101人の人物リスト（年齢とカテゴリ付き）
        self.persons = self._define_all_persons()

        self.generated_count = 0
        self.quality_stats = {
            'high_quality': 0,
            'medium_quality': 0,
            'low_quality': 0,
            'failed': 0
        }

    def _define_all_persons(self) -> List[Tuple[str, int, str]]:
        """全101人を定義（名前、年齢、カテゴリ）"""
        return [
            # 日本のスポーツ選手
            ('大谷翔平', 29, 'sports'),
            ('イチロー', 45, 'sports'),
            ('松井秀喜', 31, 'sports'),
            ('羽生結弦', 23, 'sports'),
            ('藤井聡太', 18, 'sports'),
            ('羽生善治', 23, 'sports'),
            ('久保建英', 18, 'sports'),
            ('平野美宇', 17, 'sports'),
            ('伊調馨', 33, 'sports'),
            ('室伏広治', 30, 'sports'),
            ('上田桃子', 21, 'sports'),
            ('宮里藍', 24, 'sports'),
            ('古賀稔彦', 25, 'sports'),
            ('吉田秀彦', 23, 'sports'),
            ('高橋尚子', 28, 'sports'),
            ('野村忠宏', 24, 'sports'),
            ('内村航平', 23, 'sports'),
            ('浅田真央', 20, 'sports'),
            ('北島康介', 24, 'sports'),
            ('錦織圭', 24, 'sports'),

            # エンターテイメント
            ('HIKAKIN', 27, 'entertainment'),
            ('北野武', 50, 'entertainment'),
            ('新海誠', 43, 'entertainment'),
            ('宮崎駿', 60, 'entertainment'),
            ('黒澤明', 44, 'entertainment'),
            ('手塚治虫', 31, 'entertainment'),
            ('坂本龍一', 35, 'entertainment'),
            ('岡田准一', 33, 'entertainment'),
            ('新垣結衣', 28, 'entertainment'),
            ('又吉直樹', 35, 'entertainment'),
            ('松田聖子', 18, 'entertainment'),
            ('松本人志', 27, 'entertainment'),
            ('櫻井翔', 32, 'entertainment'),
            ('渡辺謙', 44, 'entertainment'),
            ('田中圭', 34, 'entertainment'),
            ('星野源', 35, 'entertainment'),
            ('米津玄師', 27, 'entertainment'),
            ('Ado', 21, 'entertainment'),
            ('YOSHIKI', 23, 'entertainment'),
            ('あいみょん', 23, 'entertainment'),

            # 文学・芸術
            ('村上春樹', 38, 'literature'),
            ('大江健三郎', 29, 'literature'),
            ('三島由紀夫', 31, 'literature'),
            ('川端康成', 45, 'literature'),
            ('谷崎潤一郎', 30, 'literature'),
            ('夏目漱石', 40, 'literature'),
            ('芥川龍之介', 25, 'literature'),
            ('太宰治', 30, 'literature'),
            ('草間彌生', 28, 'art'),
            ('奈良美智', 41, 'art'),
            ('横山大観', 30, 'art'),
            ('安藤忠雄', 54, 'architecture'),

            # ビジネス
            ('孫正義', 33, 'business'),
            ('松下幸之助', 22, 'business'),
            ('本田宗一郎', 42, 'business'),
            ('盛田昭夫', 35, 'business'),
            ('豊田章男', 53, 'business'),
            ('稲盛和夫', 27, 'business'),
            ('柳井正', 35, 'business'),
            ('三木谷浩史', 32, 'business'),
            ('前澤友作', 35, 'business'),
            ('堀江貴文', 32, 'business'),

            # 科学・学術
            ('山中伸弥', 50, 'science'),
            ('遠藤章', 40, 'science'),
            ('湯川秀樹', 28, 'science'),
            ('朝永振一郎', 31, 'science'),
            ('江崎玲於奈', 33, 'science'),
            ('利根川進', 47, 'science'),
            ('小柴昌俊', 43, 'science'),
            ('南部陽一郎', 31, 'science'),
            ('益川敏英', 35, 'science'),
            ('小林誠', 36, 'science'),

            # 海外著名人
            ('スティーブ・ジョブズ', 21, 'business'),
            ('ビル・ゲイツ', 20, 'business'),
            ('イーロン・マスク', 30, 'business'),
            ('マーク・ザッカーバーグ', 19, 'business'),
            ('ジェフ・ベゾス', 30, 'business'),
            ('ウォーレン・バフェット', 35, 'business'),
            ('セルゲイ・ブリン', 25, 'business'),
            ('ラリー・ペイジ', 25, 'business'),
            ('スティーブ・ウォズニアック', 26, 'business'),
            ('ピーター・ティール', 31, 'business'),
            ('リチャード・ブランソン', 34, 'business'),
            ('アルベルト・アインシュタイン', 26, 'science'),
            ('マリー・キュリー', 36, 'science'),
            ('トーマス・エジソン', 32, 'science'),
            ('ニコラ・テスラ', 28, 'science'),
            ('マザー・テレサ', 40, 'humanitarian'),
            ('マーティン・ルーサー・キング・ジュニア', 34, 'politics'),
            ('ネルソン・マンデラ', 45, 'politics'),
            ('ウィンストン・チャーチル', 40, 'politics'),
            ('ジョン・F・ケネディ', 43, 'politics'),
            ('バラク・オバマ', 47, 'politics'),
            ('ヘレン・ケラー', 24, 'humanitarian'),

            # その他日本の著名人
            ('小澤征爾', 37, 'music'),
            ('YMO細野晴臣', 31, 'music'),
            ('坂本龍馬', 31, 'history'),
            ('織田信長', 35, 'history'),
            ('豊臣秀吉', 45, 'history'),
            ('徳川家康', 42, 'history'),
            ('西郷隆盛', 40, 'history'),
            ('福沢諭吉', 33, 'education'),
        ]

    def generate_all_objective_episodes(self) -> pd.DataFrame:
        """全人物の客観的エピソードを生成"""
        print(f"\n=== 客観的エピソード生成開始 ===")
        print(f"対象人物: {len(self.persons)}人")
        print(f"厳格な品質基準を適用")
        print("=" * 60)

        results = []
        success_count = 0
        failed_persons = []

        for i, (person_name, age, category) in enumerate(self.persons, 1):
            print(f"\n[{i}/{len(self.persons)}] {person_name} ({age}歳) - {category}")

            # エピソード生成（客観性重視）
            request = EpisodeGenerationRequest(
                person_name=person_name,
                age=age,
                category=category,
                min_quality_score=80.0,  # 高品質基準
                max_attempts=7,  # 多めの試行
                strict_mode=True  # 厳格モード
            )

            # 生成実行
            response = self.factory.generate(request)

            if response.success and response.episode:
                results.append({
                    'person_name': person_name,
                    'age': age,
                    'category': category,
                    'episode': response.episode,
                    'character_count': len(response.episode),
                    'quality_score': response.quality_score,
                    'attempts': response.attempts,
                    'validation_issues': len(response.validation_result.issues) if response.validation_result else 0
                })

                # 品質統計更新
                if response.quality_score >= 90:
                    self.quality_stats['high_quality'] += 1
                elif response.quality_score >= 70:
                    self.quality_stats['medium_quality'] += 1
                else:
                    self.quality_stats['low_quality'] += 1

                print(f"  ✅ 成功 (品質: {response.quality_score:.1f}, 文字数: {len(response.episode)}, 試行: {response.attempts}回)")
                success_count += 1
                self.generated_count += 1

            else:
                self.quality_stats['failed'] += 1
                failed_persons.append({
                    'person_name': person_name,
                    'age': age,
                    'category': category,
                    'error': response.error_message or "品質基準を満たせませんでした",
                    'attempts': response.attempts
                })
                print(f"  ❌ 失敗: {response.error_message} (試行: {response.attempts}回)")

        # データフレーム作成
        df = pd.DataFrame(results)

        # 失敗記録も保存
        if failed_persons:
            df_failed = pd.DataFrame(failed_persons)
            failed_file = f"objective_failed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df_failed.to_csv(failed_file, index=False, encoding='utf-8-sig')
            print(f"\n⚠️ 失敗記録: {failed_file}")
            print(f"  失敗: {len(failed_persons)}件")

        # 詳細な統計表示
        self._display_statistics(df, failed_persons)

        return df

    def _display_statistics(self, df: pd.DataFrame, failed_persons: List):
        """詳細な統計を表示"""
        print("\n" + "=" * 60)
        print("📊 客観的エピソード生成統計")
        print("=" * 60)

        total = len(self.persons)
        success = len(df)
        failed = len(failed_persons)

        print(f"総対象数: {total}人")
        print(f"成功: {success} ({success/total*100:.1f}%)")
        print(f"失敗: {failed} ({failed/total*100:.1f}%)")

        print("\n品質分布:")
        print(f"  高品質 (90点以上): {self.quality_stats['high_quality']}件")
        print(f"  中品質 (70-89点): {self.quality_stats['medium_quality']}件")
        print(f"  低品質 (70点未満): {self.quality_stats['low_quality']}件")
        print(f"  生成失敗: {self.quality_stats['failed']}件")

        if len(df) > 0:
            print(f"\n成功エピソードの統計:")
            print(f"  平均文字数: {df['character_count'].mean():.1f}文字")
            print(f"  最小文字数: {df['character_count'].min()}文字")
            print(f"  最大文字数: {df['character_count'].max()}文字")
            print(f"  平均品質スコア: {df['quality_score'].mean():.1f}")
            print(f"  平均試行回数: {df['attempts'].mean():.1f}回")

            # カテゴリ別統計
            print("\nカテゴリ別成功数:")
            category_stats = df.groupby('category').agg({
                'quality_score': 'mean',
                'character_count': 'mean',
                'person_name': 'count'
            }).round(1)

            for cat, row in category_stats.iterrows():
                print(f"  {cat}:")
                print(f"    成功数: {int(row['person_name'])}件")
                print(f"    平均品質: {row['quality_score']}")
                print(f"    平均文字数: {row['character_count']}")

    def save_to_csv(self, df: pd.DataFrame) -> str:
        """CSVファイルに保存"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"objective_episodes_{timestamp}.csv"

        # UTF-8 BOMで保存（Excel対応）
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n✅ エピソード保存: {filename}")
        print(f"  成功: {len(df)}件")

        return filename

    def save_to_json(self, df: pd.DataFrame) -> str:
        """JSON形式でも保存"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"objective_episodes_{timestamp}.json"

        episodes_dict = {}
        for _, row in df.iterrows():
            episodes_dict[row['person_name']] = {
                'age': row['age'],
                'category': row['category'],
                'episode': row['episode'],
                'quality_score': row['quality_score'],
                'character_count': row['character_count']
            }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(episodes_dict, f, ensure_ascii=False, indent=2)

        print(f"✅ JSON保存: {filename}")
        return filename

def main():
    """メイン実行"""
    generator = MigratedObjectiveEpisodeGenerator()

    # 全エピソード生成
    df = generator.generate_all_objective_episodes()

    # 保存
    if len(df) > 0:
        csv_file = generator.save_to_csv(df)
        json_file = generator.save_to_json(df)

        # サンプル表示
        print("\n📝 高品質エピソードサンプル（品質スコアTop5）:")
        top_episodes = df.nlargest(5, 'quality_score')
        for _, row in top_episodes.iterrows():
            print(f"\n【{row['person_name']}】({row['quality_score']:.1f}点)")
            print(f"  {row['episode'][:100]}...")
            print(f"  文字数: {row['character_count']}文字")

    print("\n✅ 客観的エピソード生成完了")
    print(f"総生成数: {generator.generated_count}エピソード")

if __name__ == "__main__":
    main()