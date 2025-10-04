#!/usr/bin/env python3
"""
Phase 3: 全100エピソード再評価 v2（改善版カテゴリ推定）

カテゴリ推定ロジックを改善し、より正確な象徴性評価を実施
"""

import csv
from pathlib import Path
from rules.rule_171_symbolism_scoring import evaluate_symbolism
from datetime import datetime

# CSVファイルのパス
csv_path = Path('#episodes_fixed_v3_20251002.csv')

# 改善版カテゴリ推定
def estimate_category_improved(episode_text: str) -> str:
    """エピソードテキストからカテゴリを推定（改善版）"""
    text = episode_text

    # 世界的評価（最優先）
    world_keywords = [
        'ノーベル', '金メダル', 'オリンピック', '世界選手権', 'ワールドカップ',
        '世界記録', 'アカデミー', 'グラミー', 'カンヌ', '金獅子', 'ヴェネツィア',
        'MVP', '世界大会', '国際大会', '世界初', '世界的', 'グローバル'
    ]
    if any(kw in text for kw in world_keywords):
        return '世界的評価'

    # 起点・創業
    origin_keywords = [
        '創業', '設立', '開始', '創設', '起業', '立ち上げ', '創刊',
        'デビュー', '新ジャンル', '確立', '定着させ', '新しい職業',
        'という新しい', '新しい成功モデル', 'パイオニア', '先駆'
    ]
    if any(kw in text for kw in origin_keywords):
        return '起点・創業'

    # 社会現象
    social_keywords = [
        '社会現象', 'ブーム', '流行', 'バズ', '話題', '注目', '一夜にして',
        '全国区', '国民的', '紅白', '視聴率', '100億', '登録者',
        '再生回数', 'YouTube'
    ]
    if any(kw in text for kw in social_keywords):
        return '社会現象'

    # 転落・挫折
    downfall_keywords = ['逮捕', '有罪', '失敗', '挫折', '破産', '辞任', '引退', '幕を下ろ']
    if any(kw in text for kw in downfall_keywords):
        return '転落・挫折'

    # 転機・転身
    turning_keywords = [
        '転身', '転機', '転向', '決断', '変革', '革命', '再定義',
        '歴史を変えた', '根本から', '概念を', '転換', '突破'
    ]
    if any(kw in text for kw in turning_keywords):
        return '転機・転身'

    # 大胆な決断
    bold_keywords = ['捨て', '辞し', '退職', '離れ', '挑戦']
    if any(kw in text for kw in bold_keywords):
        return '大胆な決断'

    # それでも該当しない場合、数値をチェック
    numerical_keywords = ['億', '万人', '記録', '達成', '突破']
    if any(kw in text for kw in numerical_keywords):
        # 数値があっても革新性があれば転機・転身
        innovation_keywords = ['革新', '新時代', '新しい', '画期的']
        if any(kw in text for kw in innovation_keywords):
            return '転機・転身'

    # デフォルト
    return '数値的成功'

# エピソードを読み込み
episodes = []
with open(csv_path, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        episodes.append(row)

print("=" * 80)
print("Phase 3: 全100エピソード再評価 v2（改善版）")
print("=" * 80)
print(f"評価日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"評価基準: 象徴性スコア100点以上")
print(f"改善点: カテゴリ推定ロジックの改善")
print(f"エピソード数: {len(episodes)}件")
print()

pass_count = 0
fail_count = 0
results = []
failed_episodes = []

for i, episode in enumerate(episodes, 1):
    ep_id = episode.get('episode_id', f'EP{i:03d}')
    person_name = episode.get('person_name', '')
    episode_text = episode.get('episode_text', '')
    character_count = len(episode_text)

    # 改善版カテゴリ推定
    category = estimate_category_improved(episode_text)

    # RULE_171で評価
    try:
        symbolism_result = evaluate_symbolism(
            episode_text,
            metadata={'category': category}
        )

        passed = symbolism_result['passed']
        score = symbolism_result['score']

        if passed:
            pass_count += 1
            status = "✅"
        else:
            fail_count += 1
            status = "❌"
            failed_episodes.append({
                'id': ep_id,
                'person': person_name,
                'score': score,
                'category': category,
                'text': episode_text[:80] + '...'
            })

        results.append({
            'episode_id': ep_id,
            'person_name': person_name,
            'category': category,
            'score': score,
            'passed': passed,
            'character_count': character_count
        })

        # 進捗表示（10件ごと）
        if i % 10 == 0:
            print(f"進捗: {i}/100件完了 (合格: {pass_count}, 不合格: {fail_count})")

    except Exception as e:
        print(f"⚠️ {ep_id} - エラー: {e}")
        fail_count += 1

print()
print("=" * 80)
print("📊 Phase 3 全100エピソード再評価結果 v2")
print("=" * 80)
print(f"合格: {pass_count}/100件")
print(f"不合格: {fail_count}/100件")
print(f"合格率: {pass_count/100*100:.1f}%")
print()

# 目標達成判定
if pass_count >= 98:
    print("🎉 目標達成！合格率98%以上を達成しました！")
    print(f"✅ {pass_count}件が象徴性スコア100点基準をクリア")
elif pass_count >= 95:
    print("✅ 優秀！合格率95%以上を達成")
    print(f"残り{100-pass_count}件の改善で目標達成可能")
elif pass_count >= 90:
    print("⚠️ 良好。合格率90%以上")
    print(f"残り{100-pass_count}件の改善が必要")
else:
    print(f"❌ 改善が必要。合格率{pass_count}%")
    print(f"残り{100-pass_count}件の改善が必要")

# 不合格エピソードの詳細
if failed_episodes:
    print()
    print(f"{'='*80}")
    print(f"❌ 不合格エピソード一覧（{len(failed_episodes)}件）")
    print(f"{'='*80}")
    for ep in failed_episodes[:10]:  # 最初の10件のみ表示
        print(f"{ep['id']} - {ep['person']}")
        print(f"  スコア: {ep['score']:.1f}点")
        print(f"  カテゴリ: {ep['category']}")
        print(f"  テキスト: {ep['text']}")
        print()

    if len(failed_episodes) > 10:
        print(f"... 他 {len(failed_episodes) - 10}件")

# カテゴリ別集計
print()
print(f"{'='*80}")
print("📈 カテゴリ別集計")
print(f"{'='*80}")
category_stats = {}
for result in results:
    cat = result['category']
    if cat not in category_stats:
        category_stats[cat] = {'total': 0, 'passed': 0}
    category_stats[cat]['total'] += 1
    if result['passed']:
        category_stats[cat]['passed'] += 1

for cat, stats in sorted(category_stats.items(), key=lambda x: x[1]['total'], reverse=True):
    pass_rate = stats['passed'] / stats['total'] * 100 if stats['total'] > 0 else 0
    print(f"{cat}: {stats['passed']}/{stats['total']}件 ({pass_rate:.1f}%)")

# 結果をCSV保存
output_path = Path('evaluation_results_100_rule171_v2_20251002.csv')
with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['episode_id', 'person_name', 'category',
                                            'score', 'passed', 'character_count'])
    writer.writeheader()
    writer.writerows(results)

print()
print(f"✅ 評価結果を {output_path} に保存しました")
print()
print("=" * 80)
print("次のステップ:")
if pass_count >= 98:
    print("1. Phase 3完了 - Phase 4へ進む")
    print("2. RULE_172のMCP統合を実施")
elif pass_count >= 95:
    print("1. 残りの不合格エピソードを個別分析")
    print("2. 微調整後、目標98%達成")
else:
    print("1. 不合格エピソードのカテゴリ分析")
    print("2. 基準スコアの調整検討")
print("=" * 80)
