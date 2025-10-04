#!/usr/bin/env python3
"""
RULE_171の実際のエピソード全文でのテスト
"""

import sys
sys.path.insert(0, '/Users/admin/Documents/AIUELAB/001-final-hourglass')

from rules.rule_171_symbolism_scoring import evaluate_symbolism

# 実際のv3エピソード全文
test_episodes = [
    {
        "id": "EP011",
        "person": "ジェフ・ベゾス",
        "category": "起点・創業",
        "text": "あなたと同じ30歳のとき、ジェフ・ベゾスはヘッジファンドの副社長職を辞し、シアトルのガレージでAmazonを創業した。妻マッケンジーと車で大陸横断中に助手席でビジネスプランを作成。初日から注文のベルが鳴り止まず、自ら段ボールを組み立て膝をついて本を梱包した。年間2300%のインターネット成長率を信じた決断が、時価総額1.5兆ドル企業を生んだ。"
    },
    {
        "id": "EP033",
        "person": "堀江貴文",
        "category": "転落・挫折",
        "text": "あなたと同じ38歳のとき、堀江貴文は証券取引法違反で逮捕された。24歳で起業したオン・ザ・エッヂは2000年に売上高100億円、株価100倍に成長しライブドアに改称。ニッポン放送買収、プロ野球参入など次々と挑戦したが、株式分割を繰り返した資金調達が法に抵触し実刑判決を受けた。時代の寵児の転落は日本経済界に衝撃を与えた。"
    },
    {
        "id": "EP035",
        "person": "大江健三郎",
        "category": "世界的評価",
        "text": "あなたと同じ59歳のとき、大江健三郎はノーベル文学賞を受賞し、日本人8人目の受賞者となった。23歳で芥川賞『飼育』から36年、知的障害の長男・光との関係を描いた『個人的な体験』『万延元年のフットボール』など、人間の尊厳を問う作品が世界的に評価された。授賞式で日本語スピーチを行い、日本文学の独自性を示した。"
    },
    {
        "id": "EP052",
        "person": "新垣結衣",
        "category": "社会現象",
        "text": "あなたと同じ18歳のとき、新垣結衣は江崎グリコのポッキーCM「ポッキーダンス」に出演し、一夜にして全国区のスターとなった。沖縄から上京3年目の無名モデルが軽快なリズムで踊る姿が若者の心を掴み、社会現象に。YouTube再生回数1億回突破、ポッキー売上は前年比120%を記録した。"
    },
    {
        "id": "EP091",
        "person": "西野亮廣",
        "category": "社会現象",
        "text": "あなたと同じ42歳のとき、西野亮廣は絵本『えんとつ町のプペル』を分業制・全ページ無料公開という革新的手法で世に送り出し、累計70万部のベストセラーとした。33人の絵師と4年かけて制作、クラウドファンディングで1億円調達し映画化。従来の出版業界の常識を覆した。19歳でキングコング結成、お笑いで人気を博した後の挑戦だった。"
    }
]

print("=" * 80)
print("RULE_171: 実際のエピソード全文テスト")
print("=" * 80)
print()

pass_count = 0
fail_count = 0

for episode in test_episodes:
    print(f"{'='*80}")
    print(f"📋 {episode['id']} - {episode['person']}")
    print(f"{'='*80}")
    print(f"カテゴリ: {episode['category']}")
    print(f"テキスト: {episode['text'][:80]}...")
    print()

    result = evaluate_symbolism(episode["text"], {"category": episode["category"]})

    status = "✅ 合格" if result["passed"] else "❌ 不合格"
    print(f"{status} スコア: {result['score']:.1f}点 (基準: {result['threshold']}点)")
    print()
    print("📊 詳細:")
    print(f"  - カテゴリ: {result['category']}")
    print(f"  - 基準点: {result['base_score']}点")
    print(f"  - 強化要素: {len(result['multipliers'])}件")
    for factor, multiplier in result['multipliers'].items():
        print(f"     • {factor}: ×{multiplier}")
    print()

    if result["passed"]:
        pass_count += 1
    else:
        fail_count += 1

print("=" * 80)
print("📊 テスト結果サマリー")
print("=" * 80)
print(f"合格: {pass_count}/5件")
print(f"不合格: {fail_count}/5件")
print(f"合格率: {pass_count/5*100:.1f}%")
print()

if fail_count > 0:
    print("⚠️ 不合格エピソードがあります。")
    print("提案: 基準スコアを調整するか、乗数を増やす必要があります。")
else:
    print("🎉 すべてのエピソードが基準をクリアしました！")
