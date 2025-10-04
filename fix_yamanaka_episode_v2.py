#!/usr/bin/env python3
"""
山中伸弥エピソードの完全修正版
"""

from pdca_guardian import PDCAGuardian

# 修正版エピソード（文字数を150文字以上に、3軸バランスを改善）
fixed_episode = """あなたと同じ50歳のとき、山中伸弥は長年の研究努力が実を結び、iPS細胞（人工多能性幹細胞）の作製に成功しました。実はわずか4つの遺伝子導入で体細胞を万能細胞に変換する画期的技術を確立。パーキンソン病やALSなど難病研究に革新をもたらし、2012年ノーベル生理学・医学賞を受賞。日本の再生医療研究を世界トップレベルに押し上げました。"""

# PDCAガーディアンで違反確認
guardian = PDCAGuardian()
person_name = "山中伸弥"
age = 50
person_name_display = f"{person_name}（{age}歳）"

print("修正版エピソード（v2）：")
print(fixed_episode)
print(f"文字数: {len(fixed_episode)}")

print("\n" + "="*60)
print("違反チェック")
print("="*60)

violations = guardian.check_episode_quality(
    episode_text=fixed_episode,
    age=age,
    person_name_display=person_name_display
)

if violations:
    print(f"残存違反数: {len(violations)}")
    for i, v in enumerate(violations, 1):
        print(f"\n違反{i}:")
        print(f"  ルール: {v.get('rule_id', 'UNKNOWN')}")
        print(f"  タイプ: {v.get('type', 'UNKNOWN')}")
        print(f"  説明: {v.get('message', '')}")
else:
    print("✅ 全ての違反が修正されました！")

print("\n" + "="*60)
print("CSV用出力")
print("="*60)
print(f'山中伸弥,山中伸弥,50,50,"{fixed_episode}"')