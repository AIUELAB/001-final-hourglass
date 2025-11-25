#!/usr/bin/env python3
"""
12,410人達成のためのデータ収集戦略とコスト見積もり
"""

import json
from datetime import datetime

# 現在の状況
CURRENT_STATUS = {
    'total_people': 6150,
    'real_people': 6122,
    'fictional_people': 28,
    'required_total': 12410,
    'shortage': 6260
}

# カテゴリ別収集計画
COLLECTION_PLAN = {

    # ========== 優先度1: 日本市場向け（2,400人） ==========
    'japanese_priority': {
        'お笑い芸人': {
            'target': 300,
            'sources': ['吉本興業', 'ワタナベエンターテインメント', '人力舎', 'マセキ芸能社'],
            'examples': ['ダウンタウン世代', 'M-1歴代出場者', 'R-1歴代出場者', 'キングオブコント出場者'],
            'episode_types': ['デビュー年', 'ブレイク年', 'M-1出場年', '結婚年']
        },
        'YouTuber・VTuber': {
            'target': 400,
            'sources': ['UUUM所属', 'ホロライブ', 'にじさんじ', '個人勢'],
            'examples': ['登録者100万人以上', 'ゲーム実況者', '教育系', 'VTuber'],
            'episode_types': ['チャンネル開設年', '100万人突破年', '炎上年', '引退年']
        },
        'アイドル・声優': {
            'target': 500,
            'sources': ['ジャニーズ', 'AKBグループ', '坂道シリーズ', '声優事務所'],
            'examples': ['SMAP～Snow Man世代', 'AKB48全メンバー', '人気声優'],
            'episode_types': ['デビュー年', 'センター獲得年', '卒業年', '結婚発表年']
        },
        '日本のスポーツ選手': {
            'target': 600,
            'sources': ['プロ野球', 'Jリーグ', '大相撲', 'オリンピック選手'],
            'examples': ['歴代日本人メジャーリーガー', 'J1全選手', '横綱・大関経験者'],
            'episode_types': ['プロ入り年', '優勝年', 'タイトル獲得年', '引退年']
        },
        '日本の起業家': {
            'target': 300,
            'sources': ['上場企業創業者', 'ユニコーン企業', 'スタートアップ'],
            'examples': ['メルカリ山田進太郎', 'BASE鶴岡裕太', 'SmartHR宮田昇始'],
            'episode_types': ['起業年', '資金調達年', '上場年', 'EXIT年']
        },
        '日本の文化人': {
            'target': 300,
            'sources': ['作家', '漫画家', '映画監督', 'アーティスト'],
            'examples': ['直木賞・芥川賞受賞者', '週刊少年ジャンプ作家', '日本アカデミー賞受賞者'],
            'episode_types': ['デビュー年', '受賞年', '代表作発表年', '引退年']
        }
    },

    # ========== 優先度2: 架空キャラクター（1,500人） ==========
    'fictional_characters': {
        'アニメ・漫画': {
            'target': 600,
            'sources': ['ジャンプ作品', 'マガジン作品', 'サンデー作品', '深夜アニメ'],
            'examples': ['ONE PIECE全キャラ', 'NARUTO全キャラ', '進撃の巨人', '鬼滅の刃'],
            'episode_types': ['初登場年齢', '覚醒年齢', '死亡年齢', '結婚年齢']
        },
        'ゲームキャラクター': {
            'target': 400,
            'sources': ['FF全シリーズ', 'ドラクエ', 'ポケモン', 'ペルソナ'],
            'examples': ['主人公キャラ', 'ボスキャラ', '人気NPCキャラ'],
            'episode_types': ['冒険開始年齢', 'ラスボス撃破年齢', '仲間加入年齢']
        },
        '映画・ドラマ': {
            'target': 300,
            'sources': ['MCU', 'スターウォーズ', 'ハリポタ', '日本映画'],
            'examples': ['アベンジャーズ全員', 'ジェダイ騎士団', 'ホグワーツ生徒'],
            'episode_types': ['能力獲得年齢', '戦闘年齢', '死亡年齢']
        },
        'ライトノベル': {
            'target': 200,
            'sources': ['なろう系', 'ラノベ文庫', '電撃文庫'],
            'examples': ['転スラ', 'SAO', 'オーバーロード', 'リゼロ'],
            'episode_types': ['転生年齢', 'レベルアップ年齢', '覚醒年齢']
        }
    },

    # ========== 優先度3: 歴史的教訓（500人） ==========
    'historical_lessons': {
        '独裁者・戦争犯罪者': {
            'target': 100,
            'sources': ['20世紀の独裁者', 'ナチス幹部', '戦犯裁判記録'],
            'examples': ['ヒトラー', 'スターリン', '毛沢東', 'ポル・ポト'],
            'episode_types': ['権力掌握年', '粛清開始年', '戦争開始年', '失脚年']
        },
        '経済犯罪者': {
            'target': 150,
            'sources': ['金融詐欺事件', '粉飾決算', 'ポンジスキーム'],
            'examples': ['エンロン事件', 'リーマンショック関係者', '仮想通貨詐欺'],
            'episode_types': ['犯罪開始年', '逮捕年', '判決年', '出所年']
        },
        'カルト・テロリスト': {
            'target': 100,
            'sources': ['宗教カルト', 'テロ組織', '過激派'],
            'examples': ['オウム真理教', 'ISIS', 'アルカイダ'],
            'episode_types': ['組織加入年', '事件実行年', '逮捕年', '処刑年']
        },
        '汚職政治家': {
            'target': 150,
            'sources': ['ロッキード事件', 'リクルート事件', '各国汚職事件'],
            'examples': ['田中角栄', 'ニクソン', '朴槿恵'],
            'episode_types': ['当選年', '汚職開始年', '発覚年', '有罪判決年']
        }
    },

    # ========== 優先度4: テクノロジー・起業家（800人） ==========
    'technology_entrepreneurs': {
        'シリコンバレー': {
            'target': 300,
            'sources': ['Y Combinator卒業生', 'ユニコーン創業者', 'FAANG出身起業家'],
            'examples': ['イーロン・マスク', 'ジェフ・ベゾス', 'マーク・ザッカーバーグ'],
            'episode_types': ['起業年', '資金調達年', 'IPO年', 'EXIT年']
        },
        'AI・機械学習': {
            'target': 200,
            'sources': ['DeepMind', 'OpenAI', '大学研究者'],
            'examples': ['ジェフリー・ヒントン', 'ヤン・ルカン', 'サム・アルトマン'],
            'episode_types': ['博士号取得年', '論文発表年', '起業年', '受賞年']
        },
        '暗号通貨・Web3': {
            'target': 150,
            'sources': ['ブロックチェーン創業者', 'DeFiプロジェクト', 'NFT'],
            'examples': ['ヴィタリック・ブテリン', 'CZ (Binance)', 'SBF'],
            'episode_types': ['プロジェクト開始年', 'メインネット公開年', 'ハッキング年']
        },
        'ゲーム開発者': {
            'target': 150,
            'sources': ['任天堂', 'スクエニ', 'インディー開発者'],
            'examples': ['宮本茂', '小島秀夫', '田畑端'],
            'episode_types': ['入社年', '代表作発売年', '独立年', 'GOTY受賞年']
        }
    },

    # ========== 優先度5: スポーツ選手（1,000人） ==========
    'sports_athletes': {
        'サッカー': {
            'target': 300,
            'sources': ['FIFA登録選手', 'バロンドール受賞者', '各国代表'],
            'examples': ['メッシ', 'ロナウド', '歴代日本代表'],
            'episode_types': ['プロデビュー年', 'W杯出場年', 'バロンドール受賞年', '引退年']
        },
        'NBA・バスケ': {
            'target': 200,
            'sources': ['NBA選手', 'Bリーグ', 'ユーロリーグ'],
            'examples': ['レブロン・ジェームズ', '八村塁', '渡邊雄太'],
            'episode_types': ['ドラフト年', 'MVP受賞年', '優勝年', '引退年']
        },
        'オリンピック': {
            'target': 300,
            'sources': ['メダリスト', '世界記録保持者', '各国代表'],
            'examples': ['ウサイン・ボルト', '内村航平', '大谷翔平'],
            'episode_types': ['五輪初出場年', 'メダル獲得年', '世界記録樹立年']
        },
        'eスポーツ': {
            'target': 200,
            'sources': ['プロゲーマー', 'ストリーマー', '大会優勝者'],
            'examples': ['Faker', 'Ninja', '梅原大吾'],
            'episode_types': ['プロ転向年', '世界大会優勝年', '引退年']
        }
    },

    # ========== 優先度6: その他必須カテゴリ（560人） ==========
    'other_essential': {
        'ノーベル賞受賞者': {
            'target': 200,
            'sources': ['物理学賞', '化学賞', '医学生理学賞', '文学賞', '平和賞', '経済学賞'],
            'examples': ['山中伸弥', '大村智', '本庶佑'],
            'episode_types': ['博士号取得年', '発見年', '受賞年']
        },
        '映画・演劇': {
            'target': 200,
            'sources': ['アカデミー賞', 'カンヌ映画祭', 'ベルリン映画祭'],
            'examples': ['是枝裕和', '北野武', '黒澤明'],
            'episode_types': ['デビュー年', '代表作公開年', '受賞年']
        },
        '音楽・グラミー賞': {
            'target': 160,
            'sources': ['グラミー受賞者', 'ビルボード1位', '紅白出場者'],
            'examples': ['坂本龍一', 'BTS', 'ビリー・アイリッシュ'],
            'episode_types': ['デビュー年', 'ヒット曲発表年', '受賞年', '引退年']
        }
    }
}

# コスト見積もり
COST_ESTIMATION = {
    'data_sources': {
        'Wikidata_API': {
            'cost_per_1000_queries': 0,  # 無料
            'estimated_queries': 50000,
            'total_cost': 0
        },
        'Wikipedia_API': {
            'cost_per_1000_queries': 0,  # 無料
            'estimated_queries': 30000,
            'total_cost': 0
        },
        'OpenAI_GPT4_processing': {
            'cost_per_1M_tokens': 30,  # $30 per 1M tokens
            'estimated_tokens': 5000000,  # 5M tokens
            'total_cost': 150  # $150
        },
        'Manual_data_entry': {
            'hours_required': 100,
            'cost_per_hour': 20,  # $20/hour
            'total_cost': 2000  # $2000
        }
    },
    'infrastructure': {
        'Firebase_Firestore': {
            'monthly_cost': 25,  # $25/month
            'duration_months': 1,
            'total_cost': 25
        },
        'Compute_resources': {
            'estimated_cost': 50
        }
    },
    'total_estimated_cost_usd': 2225,
    'total_estimated_cost_jpy': 334000  # 1 USD = 150 JPY
}

def generate_collection_script():
    """データ収集用のスクリプトを生成"""

    script = """
# データ収集計画サマリー

## 必要人数: 6,260人
## 推定コスト: $2,225 (約334,000円)

### カテゴリ別収集目標:

#### 1. 日本市場向け (2,400人)
- お笑い芸人: 300人
- YouTuber/VTuber: 400人
- アイドル/声優: 500人
- 日本のスポーツ選手: 600人
- 日本の起業家: 300人
- 日本の文化人: 300人

#### 2. 架空キャラクター (1,500人)
- アニメ/漫画: 600人
- ゲーム: 400人
- 映画/ドラマ: 300人
- ライトノベル: 200人

#### 3. 歴史的教訓 (500人)
- 独裁者/戦争犯罪者: 100人
- 経済犯罪者: 150人
- カルト/テロリスト: 100人
- 汚職政治家: 150人

#### 4. テクノロジー/起業家 (800人)
- シリコンバレー: 300人
- AI/機械学習: 200人
- 暗号通貨/Web3: 150人
- ゲーム開発者: 150人

#### 5. スポーツ選手 (1,000人)
- サッカー: 300人
- NBA/バスケ: 200人
- オリンピック: 300人
- eスポーツ: 200人

#### 6. その他必須 (560人)
- ノーベル賞: 200人
- 映画/演劇: 200人
- 音楽/グラミー: 160人

### データ収集方法:
1. WikidataのSPARQLクエリで基本データ取得
2. Wikipedia APIで詳細情報補完
3. 各業界の公式サイトからスクレイピング
4. GPT-4で年齢別エピソード生成
5. 手動でのデータ検証と補正

### 期待される成果:
- 総人数: 12,410人以上
- 各人物に2-3個の年齢別エピソード
- 全カテゴリをバランスよくカバー
- 日本市場に最適化されたコンテンツ
    """

    return script

def calculate_episodes_distribution():
    """エピソード分布の計算"""

    total_people = CURRENT_STATUS['required_total']
    episodes_per_person = 3
    total_episodes = total_people * episodes_per_person

    # 年齢別エピソード分布
    age_distribution = {
        '0-9歳': total_episodes * 0.05,    # 5%
        '10-19歳': total_episodes * 0.15,  # 15%
        '20-29歳': total_episodes * 0.25,  # 25%
        '30-39歳': total_episodes * 0.20,  # 20%
        '40-49歳': total_episodes * 0.15,  # 15%
        '50-59歳': total_episodes * 0.10,  # 10%
        '60-69歳': total_episodes * 0.05,  # 5%
        '70歳以上': total_episodes * 0.05  # 5%
    }

    return {
        'total_people': total_people,
        'total_episodes': total_episodes,
        'age_distribution': age_distribution
    }

def main():
    """メイン処理"""

    print("=" * 70)
    print("📊 12,410人データベース構築計画")
    print("=" * 70)

    # 現状分析
    print("\n【現在の状況】")
    for key, value in CURRENT_STATUS.items():
        print(f"  {key}: {value:,}")

    # 収集計画
    print("\n【カテゴリ別収集計画】")
    total_planned = 0
    for category, subcategories in COLLECTION_PLAN.items():
        category_total = sum(sub['target'] for sub in subcategories.values())
        total_planned += category_total
        print(f"\n{category}: {category_total:,}人")
        for subcat, details in subcategories.items():
            print(f"  └─ {subcat}: {details['target']}人")

    print(f"\n合計収集予定: {total_planned:,}人")

    # コスト見積もり
    print("\n【コスト見積もり】")
    print(f"推定総コスト: ${COST_ESTIMATION['total_estimated_cost_usd']:,}")
    print(f"推定総コスト（円）: ¥{COST_ESTIMATION['total_estimated_cost_jpy']:,}")

    print("\n内訳:")
    for source, details in COST_ESTIMATION['data_sources'].items():
        print(f"  {source}: ${details['total_cost']}")

    # エピソード分布
    episodes_dist = calculate_episodes_distribution()
    print("\n【エピソード分布計画】")
    print(f"総エピソード数: {episodes_dist['total_episodes']:,}")
    print("\n年齢別分布:")
    for age_range, count in episodes_dist['age_distribution'].items():
        print(f"  {age_range}: {int(count):,}エピソード")

    # スクリプト生成
    script = generate_collection_script()

    # ファイル出力
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"data_collection_plan_{timestamp}.json"

    output_data = {
        'timestamp': timestamp,
        'current_status': CURRENT_STATUS,
        'collection_plan': COLLECTION_PLAN,
        'cost_estimation': COST_ESTIMATION,
        'episodes_distribution': episodes_dist,
        'summary': script
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 計画書を作成しました: {output_file}")

    return output_file

if __name__ == "__main__":
    main()
