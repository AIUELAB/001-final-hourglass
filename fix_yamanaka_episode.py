#!/usr/bin/env python3
"""
山中伸弥エピソードの手動修正
最も違反が多い（7違反）エピソードを修正
"""

from pdca_guardian import PDCAGuardian
import json

# 現在のエピソード
current_episode = """実はあなたと同じ50歳のとき、試行錯誤を重ねた結果、山中伸弥はiPS細胞（人工多能性幹細胞）の作製成功。再生医療革命の起点となり、難病治療の新たな希望を創出。この出来事は大きな転機となった。その影響は現在まで続いている。歴史に残る重要な節目となった。その功績は今も称えられている。"""

# PDCAガーディアンで違反確認
guardian = PDCAGuardian()
person_name = "山中伸弥"
age = 50
person_name_display = f"{person_name}（{age}歳）"

print("現在のエピソード：")
print(current_episode)
print(f"文字数: {len(current_episode)}")
print("\n" + "="*60)
print("違反内容の詳細分析")
print("="*60)

violations = guardian.check_episode_quality(
    episode_text=current_episode,
    age=age,
    person_name_display=person_name_display
)

for i, v in enumerate(violations, 1):
    print(f"\n違反{i}:")
    print(f"  ルール: {v.get('rule_id', 'UNKNOWN')}")
    print(f"  タイプ: {v.get('type', 'UNKNOWN')}")
    print(f"  説明: {v.get('message', '')}")

# 修正版の作成
print("\n" + "="*60)
print("修正版エピソード作成")
print("="*60)

# 違反を一つずつ修正
fixed_episode = current_episode

# 1. 主観的表現の削除（RULE_161関連）
# 「功績は今も称えられている」→ 客観的表現に
fixed_episode = fixed_episode.replace(
    "その功績は今も称えられている。",
    "この研究は医学の発展に寄与しました。"
)

# 2. 文末の改善 - 動詞・形容詞で終わる（RULE_165）
# 最後の文を動詞で終わるように
fixed_episode = fixed_episode.replace(
    "歴史に残る重要な節目となった。",
    "歴史に残る重要な節目となりました。"
)

# 3. 文字数調整（RULE_160: 150-250文字）
# 現在256文字なので短縮が必要
# 重複表現を削除
fixed_episode = fixed_episode.replace(
    "この出来事は大きな転機となった。その影響は現在まで続いている。",
    "この成果は医療分野に革新をもたらしました。"
)

# 4. より具体的な成果を追加（教育的価値）
fixed_episode = """実はあなたと同じ50歳のとき、山中伸弥は長年の研究の末、iPS細胞（人工多能性幹細胞）の作製に成功しました。わずか4つの遺伝子導入で体細胞を万能細胞に変換する技術を確立。再生医療の扉を開き、難病研究に新たな道を示しました。2012年のノーベル生理学・医学賞を受賞し、医学の発展に大きく貢献しました。"""

print("\n修正版エピソード：")
print(fixed_episode)
print(f"文字数: {len(fixed_episode)}")

# 修正版の違反チェック
print("\n" + "="*60)
print("修正版の違反チェック")
print("="*60)

new_violations = guardian.check_episode_quality(
    episode_text=fixed_episode,
    age=age,
    person_name_display=person_name_display
)

if new_violations:
    print(f"残存違反数: {len(new_violations)}")
    for i, v in enumerate(new_violations, 1):
        print(f"  {i}. {v.get('rule_id')}: {v.get('type')}")
else:
    print("✅ 全ての違反が修正されました！")

print("\n" + "="*60)
print("改善結果")
print("="*60)
print(f"違反削減: {len(violations)} → {len(new_violations)}")
print(f"改善率: {(1 - len(new_violations)/len(violations)) * 100:.1f}%")

# CSVフォーマットで出力
print("\n" + "="*60)
print("CSV用出力（コピー用）")
print("="*60)
print(f'"{fixed_episode}"')
