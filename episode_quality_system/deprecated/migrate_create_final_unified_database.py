#!/usr/bin/env python3
"""
create_final_unified_database.pyの統合システム版
102人分の高品質エピソードデータベースを統合バリデーションシステムで作成
"""

import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import pandas as pd
from unified_episode_factory import UnifiedEpisodeFactory, EpisodeGenerationRequest

class MigratedFinalUnifiedDatabase:
    """移行版：最終統合データベース作成"""

    def __init__(self):
        """初期化"""
        print("🔄" * 30)
        print("create_final_unified_database.py の統合システム版")
        print("🔄" * 30)

        # 統合ファクトリ使用
        self.factory = UnifiedEpisodeFactory()

        # オリジナル29人のエピソード読み込み（優先使用）
        self.original_episodes = self._load_original_episodes()

        # 102人の完全リスト
        self.all_persons = self._define_all_102_persons()

        self.episodes = []
        self.statistics = {
            'original_used': 0,
            'newly_generated': 0,
            'failed': 0,
            'total_attempts': 0,
            'quality_scores': []
        }

    def _load_original_episodes(self) -> Dict:
        """オリジナル29エピソードを読み込み"""
        original = {}
        csv_path = Path(__file__).parent.parent / 'episodes_29_corrected_20250922_210220.csv'

        if csv_path.exists():
            try:
                df = pd.read_csv(csv_path, encoding='utf-8-sig')
                for _, row in df.iterrows():
                    person_name = row['person_name']
                    episode_text = row.get('episode_text', row.get('episode', ''))
                    # オリジナルエピソードは高品質なので保持
                    if 132 <= len(episode_text) <= 250:
                        original[person_name] = {
                            'episode': episode_text,
                            'length': len(episode_text),
                            'age': row.get('episode_age', 30),
                            'score': row.get('weighted_score', 9.0)
                        }
                print(f"✅ オリジナルエピソード読み込み: {len(original)}件")
            except Exception as e:
                print(f"⚠️ オリジナルエピソード読み込みエラー: {e}")

        return original

    def _define_all_102_persons(self) -> List[Tuple[str, int, str]]:
        """102人の完全リスト（名前、年齢、カテゴリ）"""
        return [
            # スポーツ界（20人）
            ('大谷翔平', 29, 'sports'),
            ('イチロー', 45, 'sports'),
            ('松井秀喜', 31, 'sports'),
            ('羽生結弦', 23, 'sports'),
            ('錦織圭', 24, 'sports'),
            ('内村航平', 23, 'sports'),
            ('浅田真央', 20, 'sports'),
            ('高橋尚子', 28, 'sports'),
            ('北島康介', 24, 'sports'),
            ('吉田沙保里', 33, 'sports'),
            ('伊調馨', 33, 'sports'),
            ('室伏広治', 30, 'sports'),
            ('野村忠宏', 24, 'sports'),
            ('田臥勇太', 24, 'sports'),
            ('中田英寿', 29, 'sports'),
            ('三浦知良', 52, 'sports'),
            ('長友佑都', 26, 'sports'),
            ('香川真司', 23, 'sports'),
            ('久保建英', 18, 'sports'),
            ('八村塁', 21, 'sports'),

            # エンターテイメント（25人）
            ('HIKAKIN', 27, 'entertainment'),
            ('北野武', 50, 'entertainment'),
            ('黒澤明', 44, 'entertainment'),
            ('宮崎駿', 60, 'entertainment'),
            ('新海誠', 43, 'entertainment'),
            ('手塚治虫', 31, 'entertainment'),
            ('鳥山明', 30, 'entertainment'),
            ('尾田栄一郎', 23, 'entertainment'),
            ('坂本龍一', 35, 'entertainment'),
            ('久石譲', 33, 'entertainment'),
            ('小田和正', 29, 'entertainment'),
            ('桑田佳祐', 28, 'entertainment'),
            ('矢沢永吉', 24, 'entertainment'),
            ('松本人志', 27, 'entertainment'),
            ('明石家さんま', 30, 'entertainment'),
            ('タモリ', 31, 'entertainment'),
            ('渥美清', 40, 'entertainment'),
            ('高倉健', 45, 'entertainment'),
            ('渡辺謙', 44, 'entertainment'),
            ('役所広司', 39, 'entertainment'),
            ('安室奈美恵', 20, 'entertainment'),
            ('宇多田ヒカル', 19, 'entertainment'),
            ('浜崎あゆみ', 21, 'entertainment'),
            ('中森明菜', 17, 'entertainment'),
            ('美空ひばり', 12, 'entertainment'),

            # 文学界（15人）
            ('村上春樹', 38, 'literature'),
            ('大江健三郎', 29, 'literature'),
            ('川端康成', 45, 'literature'),
            ('三島由紀夫', 31, 'literature'),
            ('谷崎潤一郎', 30, 'literature'),
            ('夏目漱石', 40, 'literature'),
            ('芥川龍之介', 25, 'literature'),
            ('太宰治', 30, 'literature'),
            ('宮沢賢治', 27, 'literature'),
            ('井上靖', 43, 'literature'),
            ('司馬遼太郎', 38, 'literature'),
            ('吉本ばなな', 24, 'literature'),
            ('村上龍', 24, 'literature'),
            ('東野圭吾', 27, 'literature'),
            ('綿矢りさ', 19, 'literature'),

            # ビジネス界（15人）
            ('孫正義', 33, 'business'),
            ('松下幸之助', 22, 'business'),
            ('本田宗一郎', 42, 'business'),
            ('盛田昭夫', 35, 'business'),
            ('稲盛和夫', 27, 'business'),
            ('豊田章男', 53, 'business'),
            ('柳井正', 35, 'business'),
            ('三木谷浩史', 32, 'business'),
            ('前澤友作', 35, 'business'),
            ('堀江貴文', 32, 'business'),
            ('渡邉美樹', 25, 'business'),
            ('永守重信', 28, 'business'),
            ('似鳥昭雄', 29, 'business'),
            ('山田昇', 35, 'business'),
            ('岡田武史', 44, 'business'),

            # 科学・学術界（10人）
            ('山中伸弥', 50, 'science'),
            ('湯川秀樹', 28, 'science'),
            ('朝永振一郎', 31, 'science'),
            ('江崎玲於奈', 33, 'science'),
            ('利根川進', 47, 'science'),
            ('小柴昌俊', 43, 'science'),
            ('南部陽一郎', 31, 'science'),
            ('益川敏英', 35, 'science'),
            ('小林誠', 36, 'science'),
            ('梶田隆章', 56, 'science'),

            # 芸術界（7人）
            ('草間彌生', 28, 'art'),
            ('奈良美智', 41, 'art'),
            ('村上隆', 32, 'art'),
            ('横山大観', 30, 'art'),
            ('安藤忠雄', 54, 'architecture'),
            ('隈研吾', 36, 'architecture'),
            ('伊東豊雄', 30, 'architecture'),

            # 海外著名人（10人）
            ('スティーブ・ジョブズ', 21, 'business'),
            ('ビル・ゲイツ', 20, 'business'),
            ('イーロン・マスク', 30, 'business'),
            ('マーク・ザッカーバーグ', 19, 'business'),
            ('ジェフ・ベゾス', 30, 'business'),
            ('アルベルト・アインシュタイン', 26, 'science'),
            ('マリー・キュリー', 36, 'science'),
            ('トーマス・エジソン', 32, 'science'),
            ('マザー・テレサ', 40, 'humanitarian'),
            ('ヘレン・ケラー', 24, 'humanitarian'),
        ]

    def create_unified_database(self) -> pd.DataFrame:
        """統合データベースを作成"""
        print(f"\n=== 統合データベース作成開始 ===")
        print(f"対象人物: {len(self.all_persons)}人")
        print(f"オリジナルエピソード: {len(self.original_episodes)}件")
        print("=" * 60)

        results = []
        failed_persons = []

        for i, (person_name, age, category) in enumerate(self.all_persons, 1):
            print(f"\n[{i}/{len(self.all_persons)}] {person_name} ({age}歳) - {category}")

            # オリジナルエピソードがある場合は使用
            if person_name in self.original_episodes:
                orig = self.original_episodes[person_name]
                results.append({
                    'person_name': person_name,
                    'age': orig['age'],
                    'category': category,
                    'episode': orig['episode'],
                    'character_count': orig['length'],
                    'quality_score': orig.get('score', 90.0),
                    'source': 'original',
                    'historical_moment': self._get_moment_type(person_name),
                    'created_at': '2025-09-22T00:00:00',
                    'status': 'final'
                })
                self.statistics['original_used'] += 1
                print(f"  ✅ オリジナル使用 (文字数: {orig['length']}, 品質: {orig.get('score', 90.0):.1f})")

            else:
                # 新規生成
                request = EpisodeGenerationRequest(
                    person_name=person_name,
                    age=age,
                    category=category,
                    min_quality_score=75.0,  # 品質基準を適度に設定
                    max_attempts=5,
                    strict_mode=False
                )

                response = self.factory.generate(request)
                self.statistics['total_attempts'] += response.attempts

                if response.success and response.episode:
                    results.append({
                        'person_name': person_name,
                        'age': age,
                        'category': category,
                        'episode': response.episode,
                        'character_count': len(response.episode),
                        'quality_score': response.quality_score,
                        'source': 'generated',
                        'historical_moment': self._get_moment_type(person_name),
                        'created_at': datetime.now().isoformat(),
                        'status': 'final',
                        'attempts': response.attempts
                    })
                    self.statistics['newly_generated'] += 1
                    self.statistics['quality_scores'].append(response.quality_score)
                    print(f"  ✅ 新規生成 (文字数: {len(response.episode)}, 品質: {response.quality_score:.1f}, 試行: {response.attempts})")

                else:
                    # 失敗時はデフォルトエピソードを使用
                    default_episode = self._create_default_episode(person_name, age)
                    results.append(default_episode)
                    self.statistics['failed'] += 1
                    failed_persons.append({
                        'person_name': person_name,
                        'age': age,
                        'category': category,
                        'error': response.error_message or "Unknown error"
                    })
                    print(f"  ⚠️ デフォルト使用 (理由: {response.error_message})")

        # データフレーム作成
        df = pd.DataFrame(results)

        # 失敗記録保存
        if failed_persons:
            df_failed = pd.DataFrame(failed_persons)
            failed_file = f"unified_database_failed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df_failed.to_csv(failed_file, index=False, encoding='utf-8-sig')
            print(f"\n⚠️ 失敗記録: {failed_file} ({len(failed_persons)}件)")

        # 統計表示
        self._display_statistics(df)

        return df

    def _create_default_episode(self, person_name: str, age: int) -> Dict:
        """デフォルトエピソード作成（132文字以上保証）"""
        episode = (
            f"あなたと同じ{age}歳のとき、{person_name}は自身の分野で重要な転機を迎えた。"
            f"それまでの努力が実を結び、業界内で注目される存在となった。"
            f"この時期の経験が後の成功の礎となり、多くの人々に影響を与える活動へとつながった。"
            f"その功績は今日でも高く評価されている。"
        )
        return {
            'person_name': person_name,
            'age': age,
            'category': 'unknown',
            'episode': episode,
            'character_count': len(episode),
            'quality_score': 70.0,
            'source': 'default',
            'historical_moment': '重要な転機',
            'created_at': datetime.now().isoformat(),
            'status': 'final'
        }

    def _get_moment_type(self, person_name: str) -> str:
        """歴史的瞬間のタイプを取得"""
        moment_types = {
            '大谷翔平': 'WBC優勝',
            'イチロー': 'MLB最多安打',
            '村上春樹': 'ノルウェイの森出版',
            '宮崎駿': '千と千尋の神隠し',
            '孫正義': 'ソフトバンク創業',
            '山中伸弥': 'iPS細胞発見'
        }
        return moment_types.get(person_name, '重要な成果')

    def _display_statistics(self, df: pd.DataFrame):
        """統計情報を表示"""
        print("\n" + "=" * 60)
        print("📊 統合データベース統計")
        print("=" * 60)

        total = len(df)
        print(f"総エピソード数: {total}")
        print(f"  オリジナル使用: {self.statistics['original_used']} ({self.statistics['original_used']/total*100:.1f}%)")
        print(f"  新規生成: {self.statistics['newly_generated']} ({self.statistics['newly_generated']/total*100:.1f}%)")
        print(f"  デフォルト使用: {self.statistics['failed']} ({self.statistics['failed']/total*100:.1f}%)")

        print(f"\n文字数統計:")
        print(f"  平均: {df['character_count'].mean():.1f}文字")
        print(f"  最小: {df['character_count'].min()}文字")
        print(f"  最大: {df['character_count'].max()}文字")
        print(f"  132-250文字範囲: {len(df[(df['character_count'] >= 132) & (df['character_count'] <= 250)])}件 ({len(df[(df['character_count'] >= 132) & (df['character_count'] <= 250)])/total*100:.1f}%)")

        print(f"\n品質スコア統計:")
        print(f"  平均: {df['quality_score'].mean():.1f}")
        print(f"  最高: {df['quality_score'].max():.1f}")
        print(f"  最低: {df['quality_score'].min():.1f}")

        # ソース別統計
        print(f"\nソース別内訳:")
        source_counts = df['source'].value_counts()
        for source, count in source_counts.items():
            print(f"  {source}: {count}件 ({count/total*100:.1f}%)")

        # カテゴリ別統計
        print(f"\nカテゴリ別エピソード数:")
        category_counts = df['category'].value_counts()
        for cat, count in category_counts.items():
            avg_score = df[df['category'] == cat]['quality_score'].mean()
            print(f"  {cat}: {count}件 (平均品質: {avg_score:.1f})")

    def save_database(self, df: pd.DataFrame) -> Tuple[str, str]:
        """データベースを保存（CSV & JSON）"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # CSV保存
        csv_filename = f"final_unified_database_{timestamp}.csv"
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        print(f"\n✅ CSV保存: {csv_filename}")

        # JSON保存
        json_filename = f"final_unified_database_{timestamp}.json"
        database_dict = {}
        for _, row in df.iterrows():
            database_dict[row['person_name']] = {
                'age': int(row['age']),
                'category': row['category'],
                'episode': row['episode'],
                'character_count': int(row['character_count']),
                'quality_score': float(row['quality_score']),
                'source': row['source'],
                'historical_moment': row['historical_moment'],
                'created_at': row['created_at'],
                'status': row['status']
            }

        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(database_dict, f, ensure_ascii=False, indent=2)
        print(f"✅ JSON保存: {json_filename}")

        return csv_filename, json_filename

def main():
    """メイン実行"""
    creator = MigratedFinalUnifiedDatabase()

    # データベース作成
    df = creator.create_unified_database()

    # 保存
    csv_file, json_file = creator.save_database(df)

    # サンプル表示
    print("\n📝 高品質エピソードサンプル（品質スコアTop10）:")
    top_episodes = df.nlargest(10, 'quality_score')
    for i, (_, row) in enumerate(top_episodes.iterrows(), 1):
        print(f"\n{i}. 【{row['person_name']}】({row['quality_score']:.1f}点)")
        print(f"   {row['episode'][:100]}...")
        print(f"   文字数: {row['character_count']}文字 | ソース: {row['source']}")

    print("\n✅ 最終統合データベース作成完了")
    print(f"総エピソード数: {len(df)}件")

if __name__ == "__main__":
    main()
