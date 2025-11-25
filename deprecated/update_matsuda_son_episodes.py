#!/usr/bin/env python3
"""
松田聖子と孫正義のエピソードを更新
記録・記憶・共感の3軸で最適化
"""

import json
from datetime import datetime

def update_episodes():
    """データベースに新エピソードを追加"""

    # データベース読み込み
    with open('verified_facts_database_103persons.json', 'r', encoding='utf-8') as f:
        database = json.load(f)

    # 松田聖子のエピソード更新
    if "松田聖子" in database['verified_facts']:
        # 既存のエピソードを保持しつつ、新しいエピソードを追加
        matsuda_facts = [
            {
                "age": 26,
                "fact": "1988年、女性ソロアーティスト史上空前の24作連続オリコン1位を達成、『旅立ちはフリージア』まで8年間の快挙",
                "sources": ["オリコン公式記録", "Wikipedia", "音楽業界誌"],
                "confidence": 1.0,
                "emotional_score": 0.95,  # 継続的努力への感動
                "educational_score": 0.9,
                "keywords": ["24作連続", "オリコン1位", "女性ソロ史上初", "1988年"],
                "importance_score": 3.0,  # 記録として最高レベル
                "memory_score": 0.95,  # 80年代を象徴
                "empathy_score": 0.85,  # プロフェッショナリズムへの共感
                "ownership_type": "individual"
            },
            {
                "age": 23,
                "fact": "1985年10月、神田正輝との結婚を発表、『世紀の結婚』として社会現象化、セイコちゃんカットが全国的ブームに",
                "sources": ["週刊誌各誌", "Wikipedia", "芸能史記録"],
                "confidence": 1.0,
                "emotional_score": 0.92,
                "educational_score": 0.7,
                "keywords": ["世紀の結婚", "神田正輝", "セイコちゃんカット", "1985年"],
                "importance_score": 2.8,
                "memory_score": 0.98,  # 社会現象として強烈な記憶
                "empathy_score": 0.90,  # 恋愛・結婚の普遍的共感
                "ownership_type": "individual"
            },
            {
                "age": 20,
                "fact": "1982年、『赤いスイートピー』が大ヒット、松田聖子の代表曲として時代を超えて愛される名曲に",
                "sources": ["オリコン", "Wikipedia"],
                "confidence": 1.0,
                "emotional_score": 0.90,
                "educational_score": 0.75,
                "keywords": ["赤いスイートピー", "1982年", "代表曲"],
                "importance_score": 2.5,
                "memory_score": 0.92,
                "empathy_score": 0.88,
                "ownership_type": "individual"
            }
        ]

        # 既存のエピソードと統合（重複を避ける）
        existing_ages = [f['age'] for f in database['verified_facts']['松田聖子']['facts']]
        for new_fact in matsuda_facts:
            if new_fact['age'] not in existing_ages:
                database['verified_facts']['松田聖子']['facts'].append(new_fact)
            else:
                # 既存のエピソードを更新
                for i, fact in enumerate(database['verified_facts']['松田聖子']['facts']):
                    if fact['age'] == new_fact['age']:
                        database['verified_facts']['松田聖子']['facts'][i] = new_fact
                        break

    # 孫正義のエピソード更新
    if "孫正義" in database['verified_facts']:
        son_facts = [
            {
                "age": 54,
                "fact": "2011年、東日本大震災に個人として100億円を寄付、さらに退任までの報酬全額を被災地へ寄付することを表明",
                "sources": ["ソフトバンク公式発表", "新聞各紙", "Wikipedia"],
                "confidence": 1.0,
                "emotional_score": 0.98,  # 利他的行動への感動
                "educational_score": 0.95,
                "keywords": ["東日本大震災", "100億円寄付", "2011年", "社会貢献"],
                "importance_score": 3.5,  # 社会的影響極大
                "memory_score": 0.96,  # 国難と結びついた強い記憶
                "empathy_score": 0.95,  # 困難時の助け合いへの共感
                "ownership_type": "individual",
                "category": "social_contribution"
            },
            {
                "age": 60,
                "fact": "2017年、SoftBank Vision Fund（約10兆円規模）を設立、世界最大のテクノロジー投資ファンドとして歴史を変える",
                "sources": ["SoftBank公式", "Wall Street Journal", "Wikipedia"],
                "confidence": 1.0,
                "emotional_score": 0.85,
                "educational_score": 0.92,
                "keywords": ["Vision Fund", "10兆円", "2017年", "テクノロジー投資"],
                "importance_score": 3.2,
                "memory_score": 0.75,  # ビジネス界では歴史的
                "empathy_score": 0.60,  # 規模が大きすぎて共感困難
                "ownership_type": "individual"
            },
            {
                "age": 50,
                "fact": "2007年、スティーブ・ジョブズと直接交渉し、iPhone日本独占販売権を獲得、『握手の約束』で歴史的契約",
                "sources": ["ビジネス誌各誌", "Wikipedia", "自伝"],
                "confidence": 0.95,
                "emotional_score": 0.90,
                "educational_score": 0.88,
                "keywords": ["iPhone", "スティーブ・ジョブズ", "2007年", "独占販売"],
                "importance_score": 2.8,
                "memory_score": 0.88,
                "empathy_score": 0.75,
                "ownership_type": "collaborative"
            }
        ]

        # 既存のエピソードと統合
        existing_ages = [f['age'] for f in database['verified_facts']['孫正義']['facts']]
        for new_fact in son_facts:
            if new_fact['age'] not in existing_ages:
                database['verified_facts']['孫正義']['facts'].append(new_fact)
            else:
                # 既存のエピソードを更新
                for i, fact in enumerate(database['verified_facts']['孫正義']['facts']):
                    if fact['age'] == new_fact['age']:
                        database['verified_facts']['孫正義']['facts'][i] = new_fact
                        break

    # メタデータ更新
    database['metadata'] = database.get('metadata', {})
    database['metadata']['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    database['metadata']['episode_optimization'] = {
        "version": "2.0",
        "optimization_type": "3-axis evaluation",
        "axes": ["record", "memory", "empathy"],
        "weights": {
            "record": 0.2,
            "memory": 0.4,
            "empathy": 0.4
        }
    }

    # 保存
    with open('verified_facts_database_103persons.json', 'w', encoding='utf-8') as f:
        json.dump(database, f, ensure_ascii=False, indent=2)

    print("✅ エピソード更新完了:")
    print("\n📝 松田聖子:")
    print("  - 26歳: 24作連続オリコン1位（記録的偉業）")
    print("  - 23歳: 世紀の結婚とセイコちゃんカット（社会現象）")
    print("  - 20歳: 赤いスイートピー（時代を超えた名曲）")
    print("\n💰 孫正義:")
    print("  - 54歳: 震災寄付100億円（社会貢献）")
    print("  - 60歳: Vision Fund 10兆円（ビジネス記録）")
    print("  - 50歳: iPhone日本独占販売（歴史的契約）")

    # 3軸評価の表示
    print("\n📊 3軸評価スコア:")
    for person in ["松田聖子", "孫正義"]:
        if person in database['verified_facts']:
            print(f"\n{person}:")
            for fact in database['verified_facts'][person]['facts'][:3]:
                age = fact['age']
                memory = fact.get('memory_score', 0.5)
                empathy = fact.get('empathy_score', 0.5)
                importance = fact.get('importance_score', 1.0)

                # 3軸総合スコア計算
                total_score = (importance * 0.2) + (memory * 0.4) + (empathy * 0.4)

                print(f"  {age}歳: 記録={importance:.1f}, 記憶={memory:.2f}, 共感={empathy:.2f} → 総合={total_score:.2f}")


if __name__ == "__main__":
    update_episodes()
