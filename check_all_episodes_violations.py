#!/usr/bin/env python3
"""
29件すべてのエピソードの違反状況を詳細にチェック
"""

import pandas as pd
from pdca_guardian import PDCAGuardian
from collections import defaultdict

def check_all_violations():
    """29件すべてのエピソードの違反をチェック"""

    # CSVファイル読み込み
    df = pd.read_csv('trusted_episodes_latest.csv', encoding='utf-8-sig')
    guardian = PDCAGuardian()

    print("="*70)
    print("📊 29件のエピソード違反状況詳細レポート")
    print("="*70)

    # 違反統計を集計
    violation_stats = defaultdict(int)
    episodes_with_violations = []
    episodes_without_violations = []

    # 違反タイプ別のエピソードリスト
    violation_by_type = defaultdict(list)

    for idx, row in df.iterrows():
        person_name = row['person_name']
        age = row['episode_age']
        episode_text = row['episode_text']
        character_count = row['character_count']
        person_name_display = f"{person_name}（{age}歳）"

        # 違反チェック
        violations = guardian.check_episode_quality(
            episode_text=episode_text,
            age=age,
            person_name_display=person_name_display
        )

        if violations:
            episodes_with_violations.append({
                'person': person_name,
                'age': age,
                'violations': violations,
                'violation_count': len(violations),
                'character_count': character_count
            })

            # 違反タイプ別に集計
            for v in violations:
                vtype = v.get('type', 'UNKNOWN')
                rule_id = v.get('rule_id', 'UNKNOWN')
                violation_key = f"{rule_id}_{vtype}"
                violation_stats[violation_key] += 1
                violation_by_type[violation_key].append(person_name_display)
        else:
            episodes_without_violations.append({
                'person': person_name,
                'age': age,
                'character_count': character_count
            })

    # 1. 基準を満たしているエピソード
    print("\n✅ 基準を満たしているエピソード:")
    print("-"*50)

    if episodes_without_violations:
        print(f"【{len(episodes_without_violations)}件】")
        for ep in episodes_without_violations:
            print(f"  ✓ {ep['person']}（{ep['age']}歳）- {ep['character_count']}文字")
    else:
        print("  なし（全エピソードに何らかの違反があります）")

    # 2. 基準に足りていないエピソード
    print("\n❌ 基準に足りていないエピソード:")
    print("-"*50)

    if episodes_with_violations:
        print(f"【{len(episodes_with_violations)}件】")

        # 違反数で並び替え（多い順）
        episodes_with_violations.sort(key=lambda x: x['violation_count'], reverse=True)

        for ep in episodes_with_violations:
            print(f"\n  {ep['person']}（{ep['age']}歳）- 違反{ep['violation_count']}件")
            # 主な違反を表示（最大3件）
            for v in ep['violations'][:3]:
                rule_id = v.get('rule_id', 'UNKNOWN')
                vtype = v.get('type', 'UNKNOWN')
                print(f"    • {rule_id}: {vtype}")

    # 3. 違反タイプ別統計
    print("\n📈 違反タイプ別統計:")
    print("-"*50)

    # 違反数でソート
    sorted_violations = sorted(violation_stats.items(), key=lambda x: x[1], reverse=True)

    for violation_key, count in sorted_violations:
        # キーから情報を抽出
        parts = violation_key.split('_', 1)
        rule_id = parts[0]
        vtype = parts[1] if len(parts) > 1 else 'UNKNOWN'

        print(f"\n{rule_id} - {vtype}: {count}件")

        # このタイプの違反があるエピソードの例を表示（最大3件）
        examples = violation_by_type[violation_key][:3]
        for ex in examples:
            print(f"  例: {ex}")

    # 4. サマリー
    print("\n" + "="*70)
    print("📊 サマリー")
    print("="*70)

    total = len(df)
    no_violation = len(episodes_without_violations)
    with_violation = len(episodes_with_violations)

    print(f"総エピソード数: {total}件")
    print(f"基準達成: {no_violation}件 ({no_violation/total*100:.1f}%)")
    print(f"基準未達: {with_violation}件 ({with_violation/total*100:.1f}%)")

    # 最も多い違反タイプ
    if sorted_violations:
        top_violation = sorted_violations[0]
        print(f"\n最も多い違反: {top_violation[0].split('_', 1)[1]} ({top_violation[1]}件)")

    # 平均違反数
    if episodes_with_violations:
        avg_violations = sum(ep['violation_count'] for ep in episodes_with_violations) / len(episodes_with_violations)
        print(f"違反エピソードの平均違反数: {avg_violations:.1f}件")

    return episodes_without_violations, episodes_with_violations

def main():
    no_violation, with_violation = check_all_violations()

    # 推奨事項を表示
    print("\n" + "="*70)
    print("💡 推奨事項")
    print("="*70)

    if len(no_violation) == 0:
        print("""
現在、すべてのエピソードが何らかの基準違反を抱えています。

主な問題:
1. 3軸バランス違反（記憶性・共感性・意外性）
2. 品質スコア不足（7.0未満）
3. 教育的価値の欠如

改善方法:
- プロセスや困難を示す事実を追加
- 年齢との関連性を強化
- 社会的影響や教訓を含める
        """)
    else:
        print(f"""
{len(no_violation)}件のエピソードは基準を満たしています。
残り{len(with_violation)}件の改善が必要です。
        """)

if __name__ == "__main__":
    main()
