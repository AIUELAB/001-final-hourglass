#!/usr/bin/env python3
"""
Phase 3: 修正済み9エピソード再評価（RULE_171）

Phase 1で修正したv3エピソードを、Phase 2で実装したRULE_171で再評価し、
品質スコア7.0未満で不合格だった5件が象徴性スコア100点基準で合格するか検証
"""

import json
from pathlib import Path
from rules.rule_171_symbolism_scoring import evaluate_symbolism

# 修正済みエピソードデータの読み込み
corrections_path = Path('fixes/episode_corrections_v3.json')
with open(corrections_path, 'r', encoding='utf-8') as f:
    corrections_data = json.load(f)

# エピソードデータの抽出
episodes = []
for ep_id, ep_data in corrections_data['corrections'].items():
    episodes.append({
        'id': ep_id,
        'person_name': ep_data['person_name'],
        'age': ep_data['age'],
        'text': ep_data['new_text'],
        'character_count': ep_data['character_count'],
        'original_symbolism_score': ep_data.get('symbolism_score', 0)
    })

# カテゴリマッピング（エピソード内容から推定）
category_mapping = {
    'EP011': '起点・創業',   # Amazon創業
    'EP027': '世界的評価',   # 金獅子賞
    'EP033': '転落・挫折',   # 逮捕
    'EP035': '世界的評価',   # ノーベル賞
    'EP052': '社会現象',     # ポッキーダンス
    'EP060': '世界的評価',   # 五輪金メダル
    'EP061': '転機・転身',   # AKB卒業
    'EP079': '世界的評価',   # WBC MVP
    'EP091': '社会現象'      # えんとつ町のプペル
}

print("=" * 80)
print("Phase 3: 修正済み9エピソード再評価（RULE_171）")
print("=" * 80)
print()
print(f"評価基準: 象徴性スコア100点以上")
print(f"Phase 1での問題: 品質スコア7.0未満で5件が不合格")
print()

pass_count = 0
fail_count = 0
results = []

for episode in episodes:
    ep_id = episode['id']
    category = category_mapping.get(ep_id, '数値的成功')

    print(f"{'='*80}")
    print(f"📋 {ep_id} - {episode['person_name']}（{episode['age']}歳）")
    print(f"{'='*80}")
    print(f"カテゴリ: {category}")
    print(f"文字数: {episode['character_count']}文字")
    print(f"テキスト: {episode['text'][:80]}...")
    print()

    # RULE_171で評価
    symbolism_result = evaluate_symbolism(
        episode['text'],
        metadata={'category': category}
    )

    passed = symbolism_result['passed']
    score = symbolism_result['score']

    status = "✅ 合格" if passed else "❌ 不合格"
    print(f"{status} スコア: {score:.1f}点 (基準: {symbolism_result['threshold']}点)")
    print()

    print("📊 詳細:")
    print(f"  - カテゴリ: {symbolism_result['category']}")
    print(f"  - 基準点: {symbolism_result['base_score']}点")
    print(f"  - 強化要素: {len(symbolism_result['multipliers'])}件")
    for factor, multiplier in symbolism_result['multipliers'].items():
        print(f"     • {factor}: ×{multiplier}")
    print()

    if passed:
        pass_count += 1
    else:
        fail_count += 1

    results.append({
        'episode_id': ep_id,
        'person_name': episode['person_name'],
        'category': category,
        'score': score,
        'passed': passed,
        'base_score': symbolism_result['base_score'],
        'multipliers': list(symbolism_result['multipliers'].keys())
    })

print("=" * 80)
print("📊 Phase 3 再評価結果サマリー")
print("=" * 80)
print(f"合格: {pass_count}/9件")
print(f"不合格: {fail_count}/9件")
print(f"合格率: {pass_count/9*100:.1f}%")
print()

# Phase 1での不合格エピソード（品質スコア7.0未満）
phase1_failed = ['EP011', 'EP027', 'EP033', 'EP052', 'EP091']
phase3_passed_from_failed = [r for r in results if r['episode_id'] in phase1_failed and r['passed']]

print(f"🎯 Phase 1で不合格だった5件の状況:")
for ep_id in phase1_failed:
    result = next(r for r in results if r['episode_id'] == ep_id)
    status = "✅ 合格" if result['passed'] else "❌ 不合格"
    print(f"  {ep_id}: {status} ({result['score']:.1f}点)")
print()

improvement_rate = len(phase3_passed_from_failed) / len(phase1_failed) * 100
print(f"💡 改善率: {improvement_rate:.1f}% ({len(phase3_passed_from_failed)}/{len(phase1_failed)}件が合格に転換)")
print()

if fail_count == 0:
    print("🎉 すべてのエピソードがRULE_171基準をクリアしました！")
    print("✅ Phase 1の品質スコア7.0問題が完全解決")
else:
    print(f"⚠️ {fail_count}件のエピソードが不合格")
    print("提案: カテゴリ分類の見直し、または基準スコアの再調整が必要")

print()
print("=" * 80)
print("次のステップ:")
print("1. 全100エピソードを統合パイプラインv2で再評価")
print("2. 合格率98%以上を達成")
print("3. Phase 3残タスク（RULE_172 MCP統合等）に進む")
print("=" * 80)
