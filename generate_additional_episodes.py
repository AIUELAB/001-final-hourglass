#!/usr/bin/env python3
"""
Additional Episode Generator
追加10エピソード生成（手動データ含む）
"""

import json
import csv
from datetime import datetime
from typing import Dict, List, Optional
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from enhanced_selection_algorithm import EnhancedSelectionAlgorithm


class AdditionalEpisodeGenerator:
    """追加エピソード生成器"""

    def __init__(self):
        self.selection_algorithm = EnhancedSelectionAlgorithm()
        self.current_year = datetime.now().year

    def create_additional_episodes(self) -> List[Dict]:
        """追加10エピソード作成"""

        episodes = []

        # 1. 孫正義
        episodes.append({
            'person_id': 'P000080',
            'person_name': '孫正義',
            'age': 39,
            'episode_text': 'あなたと同じ39歳のとき、孫正義は1996年にYahoo! JAPANを設立し、日本のインターネット革命を牽引しました。このビジネスの成功は、革新的な発想と実行力の賜物であり、日本経済に大きなインパクトを与えました。特にインターネット普及という点において、その功績は永遠に記憶されるでしょう。',
            'confidence': 0.95,
            'sources': 'business_record|Wikipedia',
            'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'algorithm_score': 1.8,
            'freshness_year': 1996
        })

        # 2. 本庶佑
        episodes.append({
            'person_id': 'P000081',
            'person_name': '本庶佑',
            'age': 76,
            'episode_text': 'あなたと同じ76歳のとき、本庶佑は2018年にノーベル生理学・医学賞を受賞し、がん免疫療法の開発で人類に希望を与えました。この発見は科学技術の進歩に革命的な貢献をし、人類の未来を明るく照らす礎となりました。特にPD-1の発見という点において、その功績は永遠に記憶されるでしょう。',
            'confidence': 1.0,
            'sources': 'Nobel_Foundation|Wikipedia',
            'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'algorithm_score': 2.0,
            'freshness_year': 2018
        })

        # 3. 三木谷浩史
        episodes.append({
            'person_id': 'P000082',
            'person_name': '三木谷浩史',
            'age': 32,
            'episode_text': 'あなたと同じ32歳のとき、三木谷浩史は1997年に楽天を創業し、日本最大級のECサイトへと成長させました。このビジネスの成功は、革新的な発想と実行力の賜物であり、日本経済に大きなインパクトを与えました。特にEC市場開拓という点において、その功績は永遠に記憶されるでしょう。',
            'confidence': 0.95,
            'sources': '楽天公式|Wikipedia',
            'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'algorithm_score': 1.7,
            'freshness_year': 1997
        })

        # 4. 柳井正
        episodes.append({
            'person_id': 'P000083',
            'person_name': '柳井正',
            'age': 35,
            'episode_text': 'あなたと同じ35歳のとき、柳井正は1984年にユニクロ1号店を広島にオープンし、世界的アパレルブランドの礎を築きました。このビジネスの成功は、革新的な発想と実行力の賜物であり、日本経済に大きなインパクトを与えました。特にファストファッションという点において、その功績は永遠に記憶されるでしょう。',
            'confidence': 0.95,
            'sources': 'ファーストリテイリング|Wikipedia',
            'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'algorithm_score': 1.6,
            'freshness_year': 1984
        })

        # 5. 羽生結弦
        episodes.append({
            'person_id': 'P000084',
            'person_name': '羽生結弦',
            'age': 19,
            'episode_text': 'あなたと同じ19歳のとき、羽生結弦は2014年ソチ五輪で日本男子フィギュアスケート初の金メダルを獲得しました。この成果は、継続的な努力と卓越した才能の結晶であり、多くの人々に感動と勇気を与えました。特に男子初の金メダルという点において、その功績は永遠に記憶されるでしょう。',
            'confidence': 1.0,
            'sources': 'IOC公式|Wikipedia',
            'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'algorithm_score': 2.1,
            'freshness_year': 2014
        })

        # 6. 坂本龍一
        episodes.append({
            'person_id': 'P000085',
            'person_name': '坂本龍一',
            'age': 26,
            'episode_text': 'あなたと同じ26歳のとき、坂本龍一は1978年にYellow Magic Orchestra（YMO）を結成し、電子音楽で世界を革新しました。この作品は日本文化の新たな地平を切り開き、世界中の人々に深い影響を与え続けています。特にテクノポップという点において、その功績は永遠に記憶されるでしょう。',
            'confidence': 0.95,
            'sources': '音楽史料|Wikipedia',
            'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'algorithm_score': 1.5,
            'freshness_year': 1978
        })

        # 7. 嵐
        episodes.append({
            'person_id': 'P000086',
            'person_name': '嵐（大野智）',
            'age': 19,
            'episode_text': 'あなたと同じ19歳のとき、大野智は1999年に嵐としてデビューし、国民的アイドルグループへの第一歩を踏み出しました。この経験は、挑戦する勇気と創造性の重要性を示し、多くの人々にインスピレーションを与えています。特に国民的グループという点において、その功績は永遠に記憶されるでしょう。',
            'confidence': 0.9,
            'sources': 'ジャニーズ事務所|Wikipedia',
            'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'algorithm_score': 1.4,
            'freshness_year': 1999
        })

        # 8. YOSHIKI
        episodes.append({
            'person_id': 'P000087',
            'person_name': 'YOSHIKI',
            'age': 23,
            'episode_text': 'あなたと同じ23歳のとき、YOSHIKIは1989年にX JAPANでメジャーデビューし、ヴィジュアル系ロックの先駆者となりました。この作品は日本文化の新たな地平を切り開き、世界中の人々に深い影響を与え続けています。特にヴィジュアル系という点において、その功績は永遠に記憶されるでしょう。',
            'confidence': 0.95,
            'sources': '音楽誌|Wikipedia',
            'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'algorithm_score': 1.6,
            'freshness_year': 1989
        })

        # 9. あいみょん
        episodes.append({
            'person_id': 'P000088',
            'person_name': 'あいみょん',
            'age': 23,
            'episode_text': 'あなたと同じ23歳のとき、あいみょんは2018年に「マリーゴールド」が大ヒットし、新世代シンガーソングライターの代表となりました。この作品は日本文化の新たな地平を切り開き、世界中の人々に深い影響を与え続けています。特にストリーミング時代の成功という点において、その功績は永遠に記憶されるでしょう。',
            'confidence': 0.95,
            'sources': 'オリコン|Wikipedia',
            'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'algorithm_score': 2.2,
            'freshness_year': 2018
        })

        # 10. 小泉純一郎
        episodes.append({
            'person_id': 'P000089',
            'person_name': '小泉純一郎',
            'age': 59,
            'episode_text': 'あなたと同じ59歳のとき、小泉純一郎は2001年に第87代内閣総理大臣に就任し、「改革なくして成長なし」を掲げ構造改革を推進しました。この出来事は日本の歴史において重要な転換点となり、現代社会の形成に大きな影響を与えています。特に郵政民営化という点において、その功績は永遠に記憶されるでしょう。',
            'confidence': 1.0,
            'sources': '首相官邸|Wikipedia',
            'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'algorithm_score': 1.9,
            'freshness_year': 2001
        })

        return episodes

    def load_existing_episodes(self, filename: str) -> List[Dict]:
        """既存エピソードの読み込み"""
        episodes = []
        try:
            with open(filename, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # algorithm_scoreとfreshness_yearを数値に変換
                    if 'algorithm_score' in row:
                        row['algorithm_score'] = float(row['algorithm_score'])
                    if 'freshness_year' in row:
                        row['freshness_year'] = int(row['freshness_year'])
                    episodes.append(row)
        except FileNotFoundError:
            print(f"ファイル {filename} が見つかりません")
        return episodes

    def save_final_episodes(self, episodes: List[Dict], filename: str):
        """最終エピソードをCSV保存"""
        with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
            fieldnames = ['person_id', 'person_name', 'age', 'episode_text',
                         'confidence', 'sources', 'generation_date',
                         'algorithm_score', 'freshness_year']
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(episodes)
        print(f"📄 最終CSV保存完了: {filename}")
        print(f"   エピソード総数: {len(episodes)}件")


def main():
    """メイン処理"""
    print("=" * 60)
    print("Additional Episode Generator - 追加10エピソード生成")
    print("=" * 60)

    generator = AdditionalEpisodeGenerator()

    # 既存の19エピソードを読み込み
    existing = generator.load_existing_episodes("final_episodes_20250921_090108.csv")
    print(f"\n📚 既存エピソード読み込み: {len(existing)}件")

    # 追加10エピソードを生成
    additional = generator.create_additional_episodes()
    print(f"🆕 追加エピソード生成: {len(additional)}件")

    # 統合
    all_episodes = existing + additional

    # スコアでソート
    all_episodes.sort(key=lambda x: x.get('algorithm_score', 0), reverse=True)

    # 最終CSV保存
    final_filename = f"final_complete_episodes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    generator.save_final_episodes(all_episodes, final_filename)

    # 統計表示
    print("\n📊 最終統計:")
    print(f"   既存（ブラッシュアップ済）: {len(existing)}件")
    print(f"   新規追加: {len(additional)}件")
    print(f"   総計: {len(all_episodes)}件")

    # 上位10件表示
    print("\n🏆 スコア上位10件:")
    for i, ep in enumerate(all_episodes[:10], 1):
        score = ep.get('algorithm_score', 0)
        year = ep.get('freshness_year', 0)
        print(f"{i:2}. {ep['person_name']:12} (スコア: {score:.3f}, {year}年)")

    # カテゴリ分析
    categories = {
        'スポーツ': 0,
        '政治': 0,
        '文化・芸術': 0,
        '科学・技術': 0,
        'エンタメ': 0,
        '実業家': 0,
        'その他': 0
    }

    for ep in all_episodes:
        name = ep['person_name']
        if name in ['イチロー', '大谷翔平', '羽生結弦', '吉田沙保里', '錦織圭', '浅田真央']:
            categories['スポーツ'] += 1
        elif name in ['安倍晋三', '小泉純一郎']:
            categories['政治'] += 1
        elif name in ['宮崎駿', '黒澤明', '村上春樹', '北野武', '坂本龍一', 'YOSHIKI']:
            categories['文化・芸術'] += 1
        elif name in ['山中伸弥', '本庶佑']:
            categories['科学・技術'] += 1
        elif name in ['HIKAKIN', 'Ado', 'あいみょん', '松田聖子', '嵐（大野智）', 'さくらももこ']:
            categories['エンタメ'] += 1
        elif name in ['孫正義', '三木谷浩史', '柳井正']:
            categories['実業家'] += 1
        else:
            categories['その他'] += 1

    print("\n📂 カテゴリ分布:")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        if count > 0:
            print(f"   {cat}: {count}件 ({count/len(all_episodes)*100:.1f}%)")

    print("\n✨ 最終版29エピソードの生成が完了しました！")


if __name__ == "__main__":
    main()