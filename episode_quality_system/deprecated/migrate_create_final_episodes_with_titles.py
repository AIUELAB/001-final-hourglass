#!/usr/bin/env python3
"""
create_final_episodes_with_titles.pyの統合システム版
ハードコードされたエピソードを統合バリデーション経由で生成
"""

import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
import json

# 統合システムをインポート
from unified_episode_factory import UnifiedEpisodeFactory, EpisodeGenerationRequest

class MigratedFinalEpisodesWithTitles:
    """移行版：タイトル付き最終エピソード生成"""

    def __init__(self):
        """初期化"""
        # 統合ファクトリを使用
        self.factory = UnifiedEpisodeFactory()

        # 人物データ（元のファイルから抽出）
        self.persons_data = self._load_persons_data()

        # 生成結果
        self.generated_episodes = []
        self.failed_generations = []

    def _load_persons_data(self) -> Dict[str, Dict]:
        """人物データを定義（101人）"""
        return {
            # 音楽系
            'Ado': {'age': 21, 'category': 'entertainment', 'title': '新世代の歌姫'},
            'YOSHIKI': {'age': 23, 'category': 'entertainment', 'title': 'X JAPANリーダー'},
            'あいみょん': {'age': 23, 'category': 'entertainment', 'title': 'シンガーソングライター'},
            '坂本龍一': {'age': 35, 'category': 'entertainment', 'title': '世界的音楽家'},
            '松田聖子': {'age': 18, 'category': 'entertainment', 'title': '永遠のアイドル'},
            '星野源': {'age': 35, 'category': 'entertainment', 'title': 'マルチタレント'},
            '米津玄師': {'age': 27, 'category': 'entertainment', 'title': '音楽の革命児'},

            # 映画・アニメ系
            '北野武': {'age': 50, 'category': 'entertainment', 'title': '世界のキタノ'},
            '新海誠': {'age': 43, 'category': 'entertainment', 'title': 'アニメーション監督'},
            '宮崎駿': {'age': 60, 'category': 'entertainment', 'title': 'アニメの巨匠'},
            '是枝裕和': {'age': 56, 'category': 'entertainment', 'title': '映画監督'},
            '黒澤明': {'age': 44, 'category': 'entertainment', 'title': '映画界の巨星'},
            '手塚治虫': {'age': 31, 'category': 'entertainment', 'title': 'マンガの神様'},

            # ドラマ・テレビ系
            '綾瀬はるか': {'age': 28, 'category': 'entertainment', 'title': '国民的女優'},
            '新垣結衣': {'age': 28, 'category': 'entertainment', 'title': 'ガッキー'},
            '岡田准一': {'age': 33, 'category': 'entertainment', 'title': 'V6メンバー'},
            '渡辺謙': {'age': 44, 'category': 'entertainment', 'title': '国際派俳優'},
            '福山雅治': {'age': 40, 'category': 'entertainment', 'title': 'アーティスト俳優'},
            '松本人志': {'age': 27, 'category': 'entertainment', 'title': 'ダウンタウン'},
            '櫻井翔': {'age': 32, 'category': 'entertainment', 'title': '嵐のメンバー'},
            '田中圭': {'age': 34, 'category': 'entertainment', 'title': '俳優'},

            # 文学系
            '西野亮廣': {'age': 40, 'category': 'literature', 'title': 'キングコング'},
            '村上春樹': {'age': 38, 'category': 'literature', 'title': '世界的作家'},
            '又吉直樹': {'age': 35, 'category': 'literature', 'title': 'ピース芸人作家'},
            '芥川龍之介': {'age': 23, 'category': 'literature', 'title': '文豪'},
            '夏目漱石': {'age': 38, 'category': 'literature', 'title': '近代文学の父'},
            '三島由紀夫': {'age': 31, 'category': 'literature', 'title': '昭和の文豪'},
            '大江健三郎': {'age': 29, 'category': 'literature', 'title': 'ノーベル賞作家'},
            '川端康成': {'age': 69, 'category': 'literature', 'title': 'ノーベル文学賞'},
            'さくらももこ': {'age': 21, 'category': 'literature', 'title': 'ちびまる子ちゃん作者'},

            # スポーツ系
            '大谷翔平': {'age': 29, 'category': 'sports', 'title': '二刀流の天才'},
            'イチロー': {'age': 45, 'category': 'sports', 'title': '安打製造機'},
            '松井秀喜': {'age': 31, 'category': 'sports', 'title': 'ゴジラ'},
            '野茂英雄': {'age': 27, 'category': 'sports', 'title': 'トルネード投法'},
            '田中将大': {'age': 25, 'category': 'sports', 'title': 'マー君'},
            '王貞治': {'age': 37, 'category': 'sports', 'title': '世界のホームラン王'},
            '長嶋茂雄': {'age': 28, 'category': 'sports', 'title': 'ミスタージャイアンツ'},
            '羽生結弦': {'age': 23, 'category': 'sports', 'title': 'フィギュアの王子'},
            '浅田真央': {'age': 19, 'category': 'sports', 'title': 'フィギュアの女王'},
            '荒川静香': {'age': 24, 'category': 'sports', 'title': 'イナバウアー'},
            '高橋尚子': {'age': 28, 'category': 'sports', 'title': 'Qちゃん'},
            '野口みずき': {'age': 25, 'category': 'sports', 'title': 'マラソン金メダリスト'},
            '北島康介': {'age': 21, 'category': 'sports', 'title': 'チョー気持ちいい'},
            '内村航平': {'age': 23, 'category': 'sports', 'title': '体操の王様'},
            '室伏広治': {'age': 29, 'category': 'sports', 'title': 'ハンマー投げの鉄人'},
            '吉田沙保里': {'age': 23, 'category': 'sports', 'title': '霊長類最強女子'},
            '伊調馨': {'age': 23, 'category': 'sports', 'title': 'レスリング女王'},
            '古賀稔彦': {'age': 25, 'category': 'sports', 'title': '平成の三四郎'},
            '吉田秀彦': {'age': 23, 'category': 'sports', 'title': '柔道金メダリスト'},
            '錦織圭': {'age': 24, 'category': 'sports', 'title': 'テニスプレイヤー'},
            '大坂なおみ': {'age': 20, 'category': 'sports', 'title': 'テニス世界1位'},
            '松山英樹': {'age': 29, 'category': 'sports', 'title': 'マスターズ優勝'},
            '石川遼': {'age': 17, 'category': 'sports', 'title': 'ハニカミ王子'},
            '渋野日向子': {'age': 20, 'category': 'sports', 'title': 'スマイリングシンデレラ'},
            '宮里藍': {'age': 19, 'category': 'sports', 'title': 'ゴルフ世界ランク1位'},
            '上田桃子': {'age': 21, 'category': 'sports', 'title': 'プロゴルファー'},
            '平野美宇': {'age': 17, 'category': 'sports', 'title': '卓球選手'},
            '池江璃花子': {'age': 18, 'category': 'sports', 'title': '水泳の新星'},
            '紀平梨花': {'age': 16, 'category': 'sports', 'title': 'フィギュアスケート'},
            '八村塁': {'age': 21, 'category': 'sports', 'title': 'NBA選手'},
            '久保建英': {'age': 18, 'category': 'sports', 'title': 'サッカー天才'},

            # ビジネス系
            '孫正義': {'age': 40, 'category': 'business', 'title': 'ソフトバンク創業者'},
            '三木谷浩史': {'age': 32, 'category': 'business', 'title': '楽天創業者'},
            '柳井正': {'age': 35, 'category': 'business', 'title': 'ユニクロ創業者'},
            '前澤友作': {'age': 29, 'category': 'business', 'title': 'ZOZO創業者'},
            '堀江貴文': {'age': 31, 'category': 'business', 'title': 'ホリエモン'},
            '藤田晋': {'age': 25, 'category': 'business', 'title': 'サイバーエージェント'},
            '落合陽一': {'age': 31, 'category': 'business', 'title': 'メディアアーティスト'},
            '松下幸之助': {'age': 22, 'category': 'business', 'title': '経営の神様'},
            '盛田昭夫': {'age': 25, 'category': 'business', 'title': 'ソニー創業者'},
            '稲盛和夫': {'age': 27, 'category': 'business', 'title': '京セラ創業者'},
            '豊田章男': {'age': 52, 'category': 'business', 'title': 'トヨタ社長'},
            '本田宗一郎': {'age': 42, 'category': 'business', 'title': 'ホンダ創業者'},
            'HIKAKIN': {'age': 31, 'category': 'business', 'title': 'YouTuber'},

            # 科学系
            '山中伸弥': {'age': 45, 'category': 'science', 'title': 'iPS細胞'},
            '本庶佑': {'age': 76, 'category': 'science', 'title': 'ノーベル医学賞'},
            '大隅良典': {'age': 71, 'category': 'science', 'title': 'ノーベル生理学賞'},
            '梶田隆章': {'age': 56, 'category': 'science', 'title': 'ノーベル物理学賞'},
            '遠藤章': {'age': 46, 'category': 'science', 'title': 'スタチン発見'},
            '満屋裕明': {'age': 35, 'category': 'science', 'title': 'HIV治療薬開発'},

            # 芸術系
            '草間彌生': {'age': 28, 'category': 'art', 'title': '前衛芸術家'},
            '奈良美智': {'age': 41, 'category': 'art', 'title': '現代美術家'},
            '村上隆': {'age': 39, 'category': 'art', 'title': 'ポップアート'},
            '横尾忠則': {'age': 35, 'category': 'art', 'title': 'グラフィックデザイナー'},
            '安藤忠雄': {'age': 48, 'category': 'art', 'title': '建築家'},
            '横山大観': {'age': 30, 'category': 'art', 'title': '日本画家'},

            # その他
            '小澤征爾': {'age': 24, 'category': 'entertainment', 'title': '世界的指揮者'},
            '野村萬斎': {'age': 33, 'category': 'entertainment', 'title': '狂言師'},
            '安倍晋三': {'age': 52, 'category': 'politics', 'title': '元首相'},
            '小泉純一郎': {'age': 59, 'category': 'politics', 'title': '元首相'},
            '石破茂': {'age': 29, 'category': 'politics', 'title': '政治家'},
            'イモトアヤコ': {'age': 27, 'category': 'entertainment', 'title': '珍獣ハンター'},
            '羽生善治': {'age': 26, 'category': 'other', 'title': '将棋永世七冠'},
            '藤井聡太': {'age': 19, 'category': 'other', 'title': '将棋八冠'},
            '福沢諭吉': {'age': 25, 'category': 'other', 'title': '教育者'},

            # 海外の著名人
            'ヘレン・ケラー': {'age': 24, 'category': 'other', 'title': '教育家'},
            'マザー・テレサ': {'age': 40, 'category': 'other', 'title': '聖人'},
            'マリー・キュリー': {'age': 36, 'category': 'science', 'title': 'ノーベル賞科学者'},
            'マーティン・ルーサー・キング・ジュニア': {'age': 34, 'category': 'other', 'title': '公民権運動指導者'},
            'アルベルト・アインシュタイン': {'age': 26, 'category': 'science', 'title': '相対性理論'},
            'イーロン・マスク': {'age': 30, 'category': 'business', 'title': 'テスラCEO'},
            'ジェフ・ベゾス': {'age': 30, 'category': 'business', 'title': 'Amazon創業者'},
            'スティーブ・ジョブズ': {'age': 21, 'category': 'business', 'title': 'Apple創業者'},
            'ビル・ゲイツ': {'age': 20, 'category': 'business', 'title': 'Microsoft創業者'}
        }

    def generate_all_episodes(self):
        """全エピソードを生成"""
        total = len(self.persons_data)
        print(f"=== タイトル付きエピソード生成開始 ===")
        print(f"対象人物: {total}人")
        print("=" * 60)

        for i, (person_name, data) in enumerate(self.persons_data.items(), 1):
            print(f"\n[{i}/{total}] {person_name} ({data['title']}) - {data['age']}歳")

            # リクエスト作成
            request = EpisodeGenerationRequest(
                person_name=person_name,
                age=data['age'],
                category=data.get('category', 'other'),
                min_quality_score=70.0,
                max_attempts=5,
                strict_mode=True
            )

            # エピソード生成
            response = self.factory.generate(request)

            if response.success:
                print(f"  ✅ 成功 (品質: {response.quality_score:.1f})")
                self.generated_episodes.append({
                    'person_name': person_name,
                    'title': data['title'],
                    'age': data['age'],
                    'episode': response.episode,
                    'character_count': len(response.episode),
                    'quality_score': response.quality_score,
                    'category': data.get('category', 'other')
                })
            else:
                print(f"  ❌ 失敗: {response.error_message}")
                self.failed_generations.append({
                    'person_name': person_name,
                    'title': data['title'],
                    'error': response.error_message
                })

    def save_results(self):
        """結果を保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if self.generated_episodes:
            # CSVとして保存
            df = pd.DataFrame(self.generated_episodes)
            csv_path = f"migrated_episodes_with_titles_{timestamp}.csv"

            # UTF-8 BOM付きで保存
            with open(csv_path, 'w', encoding='utf-8-sig') as f:
                df.to_csv(f, index=False)

            print(f"\n✅ エピソード保存: {csv_path}")
            print(f"  成功: {len(self.generated_episodes)}件")

        if self.failed_generations:
            df_failed = pd.DataFrame(self.failed_generations)
            failed_path = f"failed_episodes_{timestamp}.csv"

            with open(failed_path, 'w', encoding='utf-8-sig') as f:
                df_failed.to_csv(f, index=False)

            print(f"⚠️ 失敗記録: {failed_path}")
            print(f"  失敗: {len(self.failed_generations)}件")

    def show_statistics(self):
        """統計情報を表示"""
        print("\n" + "=" * 60)
        print("📊 生成統計")
        print("=" * 60)

        total = len(self.persons_data)
        success = len(self.generated_episodes)
        failed = len(self.failed_generations)

        print(f"総対象数: {total}")
        print(f"成功: {success} ({success/total*100:.1f}%)")
        print(f"失敗: {failed} ({failed/total*100:.1f}%)")

        if self.generated_episodes:
            avg_length = sum(e['character_count'] for e in self.generated_episodes) / len(self.generated_episodes)
            avg_score = sum(e['quality_score'] for e in self.generated_episodes) / len(self.generated_episodes)

            print(f"\n平均文字数: {avg_length:.1f}文字")
            print(f"平均品質スコア: {avg_score:.1f}")

            # カテゴリ別統計
            categories = {}
            for ep in self.generated_episodes:
                cat = ep['category']
                categories[cat] = categories.get(cat, 0) + 1

            print("\nカテゴリ別成功数:")
            for cat, count in sorted(categories.items()):
                print(f"  {cat}: {count}件")


def main():
    """メイン処理"""
    print("\n" + "🔄" * 30)
    print("create_final_episodes_with_titles.py の統合システム版")
    print("🔄" * 30)

    generator = MigratedFinalEpisodesWithTitles()

    # エピソード生成
    generator.generate_all_episodes()

    # 結果保存
    generator.save_results()

    # 統計表示
    generator.show_statistics()

    print("\n✅ 処理完了")


if __name__ == "__main__":
    main()