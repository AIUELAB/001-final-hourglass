#!/usr/bin/env python3
"""
final_complete_episodes.pyの統合システム版
101人分のエピソードを統合バリデーションシステムで生成
"""

import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple
from pathlib import Path
from unified_episode_factory import UnifiedEpisodeFactory, EpisodeGenerationRequest

class MigratedFinalCompleteEpisodes:
    """移行版：最終完全版エピソード生成"""

    def __init__(self):
        """初期化"""
        print("🔄" * 30)
        print("final_complete_episodes.py の統合システム版")
        print("🔄" * 30)

        # 統合ファクトリ使用
        self.factory = UnifiedEpisodeFactory()

        # 人物リスト定義（元のスクリプトから）
        self.persons = self._define_persons()

    def _define_persons(self) -> List[Tuple[str, int, str]]:
        """人物リストを定義（名前、年齢、カテゴリ）"""
        return [
            # スポーツ界
            ('平野美宇', 17, 'sports'),
            ('本田宗一郎', 55, 'business'),  # 実際はビジネスだが元スクリプトではスポーツに分類
            ('伊調馨', 33, 'sports'),
            ('室伏広治', 30, 'sports'),
            ('上田桃子', 21, 'sports'),
            ('宮里藍', 24, 'sports'),
            ('古賀稔彦', 25, 'sports'),
            ('吉田秀彦', 23, 'sports'),
            ('久保建英', 18, 'sports'),
            ('大谷翔平', 29, 'sports'),
            ('イチロー', 45, 'sports'),
            ('松井秀喜', 31, 'sports'),
            ('羽生結弦', 23, 'sports'),

            # エンターテイメント界
            ('岡田准一', 33, 'entertainment'),
            ('新垣結衣', 28, 'entertainment'),
            ('又吉直樹', 35, 'entertainment'),
            ('松田聖子', 18, 'entertainment'),
            ('松本人志', 27, 'entertainment'),
            ('櫻井翔', 32, 'entertainment'),
            ('渡辺謙', 44, 'entertainment'),
            ('田中圭', 34, 'entertainment'),
            ('北野武', 50, 'entertainment'),
            ('新海誠', 43, 'entertainment'),
            ('宮崎駿', 60, 'entertainment'),
            ('黒澤明', 44, 'entertainment'),
            ('手塚治虫', 31, 'entertainment'),
            ('坂本龍一', 35, 'entertainment'),
            ('HIKAKIN', 27, 'entertainment'),

            # 文化・学術界
            ('大江健三郎', 29, 'literature'),
            ('三島由紀夫', 31, 'literature'),
            ('奈良美智', 41, 'art'),
            ('安藤忠雄', 54, 'architecture'),
            ('小澤征爾', 37, 'music'),
            ('村上春樹', 38, 'literature'),
            ('草間彌生', 28, 'art'),
            ('横山大観', 30, 'art'),

            # 政治・ビジネス界
            ('石破茂', 29, 'politics'),
            ('盛田昭夫', 35, 'business'),
            ('豊田章男', 53, 'business'),
            ('孫正義', 33, 'business'),
            ('松下幸之助', 22, 'business'),
            ('本田宗一郎', 42, 'business'),
            ('藤井聡太', 18, 'sports'),  # 将棋はスポーツカテゴリ
            ('羽生善治', 23, 'sports'),

            # 科学・医学界
            ('遠藤章', 40, 'science'),
            ('山中伸弥', 50, 'science'),

            # 海外著名人
            ('マザー・テレサ', 40, 'humanitarian'),
            ('マリー・キュリー', 36, 'science'),
            ('マーティン・ルーサー・キング・ジュニア', 34, 'politics'),
            ('スティーブ・ウォズニアック', 26, 'business'),
            ('ウォーレン・バフェット', 35, 'business'),
            ('セルゲイ・ブリン', 25, 'business'),
            ('ラリー・ペイジ', 25, 'business'),
            ('ピーター・ティール', 31, 'business'),
            ('リチャード・ブランソン', 34, 'business'),
            ('スティーブ・ジョブズ', 21, 'business'),
            ('ビル・ゲイツ', 20, 'business'),
            ('イーロン・マスク', 30, 'business'),
            ('アルベルト・アインシュタイン', 26, 'science'),
            ('ヘレン・ケラー', 24, 'humanitarian'),
        ]

    def generate_all_episodes(self) -> pd.DataFrame:
        """全エピソードを生成"""
        print(f"=== エピソード生成開始 ===")
        print(f"対象人物: {len(self.persons)}人")
        print("=" * 60)

        results = []
        success_count = 0
        failed_persons = []

        for i, (person_name, age, category) in enumerate(self.persons, 1):
            print(f"\n[{i}/{len(self.persons)}] {person_name} ({age}歳) - {category}")

            # カテゴリマッピング（統合システムに合わせる）
            mapped_category = self._map_category(category)

            # エピソード生成リクエスト
            request = EpisodeGenerationRequest(
                person_name=person_name,
                age=age,
                category=mapped_category,
                min_quality_score=70.0,
                max_attempts=5,
                strict_mode=False  # 緩い設定で多くのエピソードを生成
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
                    'attempts': response.attempts
                })
                print(f"  ✅ 成功 (品質: {response.quality_score:.1f}, 文字数: {len(response.episode)})")
                success_count += 1
            else:
                failed_persons.append({
                    'person_name': person_name,
                    'age': age,
                    'category': category,
                    'error': response.error_message or "Unknown error"
                })
                print(f"  ❌ 失敗: {response.error_message}")

        # データフレーム作成
        df = pd.DataFrame(results)

        # 失敗記録も保存
        if failed_persons:
            df_failed = pd.DataFrame(failed_persons)
            failed_file = f"migrated_final_complete_failed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df_failed.to_csv(failed_file, index=False, encoding='utf-8-sig')
            print(f"\n⚠️ 失敗記録: {failed_file}")
            print(f"  失敗: {len(failed_persons)}件")

        # 統計表示
        print("\n" + "=" * 60)
        print("📊 生成統計")
        print("=" * 60)
        print(f"総対象数: {len(self.persons)}")
        print(f"成功: {success_count} ({success_count/len(self.persons)*100:.1f}%)")
        print(f"失敗: {len(failed_persons)} ({len(failed_persons)/len(self.persons)*100:.1f}%)")

        if len(df) > 0:
            print(f"\n平均文字数: {df['character_count'].mean():.1f}文字")
            print(f"平均品質スコア: {df['quality_score'].mean():.1f}")
            print(f"平均試行回数: {df['attempts'].mean():.1f}回")

            # カテゴリ別統計
            print("\nカテゴリ別成功数:")
            for cat in df['category'].unique():
                count = len(df[df['category'] == cat])
                print(f"  {cat}: {count}件")

        return df

    def _map_category(self, category: str) -> str:
        """カテゴリを統合システムの形式にマッピング"""
        mapping = {
            'sports': 'sports',
            'entertainment': 'entertainment',
            'literature': 'literature',
            'business': 'business',
            'art': 'entertainment',
            'architecture': 'business',
            'music': 'entertainment',
            'politics': 'business',
            'science': 'business',
            'humanitarian': 'business'
        }
        return mapping.get(category, 'business')

    def save_to_csv(self, df: pd.DataFrame, filename: str = None) -> str:
        """CSVファイルに保存"""
        if filename is None:
            filename = f"migrated_final_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        # UTF-8 BOMで保存（Excel対応）
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n✅ エピソード保存: {filename}")
        print(f"  成功: {len(df)}件")

        return filename

def main():
    """メイン実行"""
    generator = MigratedFinalCompleteEpisodes()

    # 全エピソード生成
    df = generator.generate_all_episodes()

    # CSV保存
    if len(df) > 0:
        filename = generator.save_to_csv(df)

        # サンプル表示
        print("\n📝 生成エピソードサンプル（最初の3件）:")
        for _, row in df.head(3).iterrows():
            print(f"\n【{row['person_name']}】")
            print(f"  エピソード: {row['episode'][:80]}...")
            print(f"  文字数: {row['character_count']}文字")
            print(f"  品質スコア: {row['quality_score']:.1f}")

    print("\n✅ 処理完了")

if __name__ == "__main__":
    main()
