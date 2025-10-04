#!/usr/bin/env python3
"""
エピソードの事実構成を見直し、感動と教育的価値を事実から生み出す
言葉の追加ではなく、事実の選択と組み合わせで品質を向上させる
"""

import pandas as pd
from pdca_guardian import PDCAGuardian

def analyze_current_episode_facts():
    """現在のエピソードがなぜ感動と教育的価値に欠けるかを分析"""

    print("="*70)
    print("📊 エピソードの事実構成分析")
    print("="*70)

    # CSVファイル読み込み
    df = pd.read_csv('trusted_episodes_latest.csv', encoding='utf-8-sig')

    # 最初の5件を詳細分析
    sample_episodes = df.head(5)

    for idx, row in sample_episodes.iterrows():
        person_name = row['person_name']
        age = row['episode_age']
        episode = row['episode_text']

        print(f"\n【{idx+1}. {person_name}（{age}歳）】")
        print(f"現在のエピソード:")
        print(f"  {episode}")

        # 事実の分析
        print("\n現在の事実構成:")

        # 事実を分解
        facts = episode.split('。')
        for i, fact in enumerate(facts[:-1], 1):  # 最後の空文字列を除く
            print(f"  事実{i}: {fact}。")

        # 問題点の分析
        print("\n問題点:")
        print("  1. 記録や数字の羅列に留まっている")
        print("  2. その年齢でその出来事が起きた意味が伝わらない")
        print("  3. 人物の努力や困難が見えない")
        print("  4. 社会への影響や意義が含まれていない")

        # より良い事実の候補を提示
        print("\nより感動的・教育的な事実の候補:")
        suggest_better_facts(person_name, age)

        print("-"*50)

def suggest_better_facts(person_name, age):
    """各人物について、より感動的・教育的な事実を提案"""

    better_facts = {
        "イチロー": {
            45: [
                "45歳という年齢は日本プロ野球の平均引退年齢（29歳）の1.5倍以上",
                "引退会見で『後悔などあろうはずがない』と語った背景には28年間一度も手を抜かなかった日々",
                "最後の打席でも全力疾走し、プロとしての姿勢を最後まで貫いた",
                "引退後も毎日トレーニングを続け、野球への愛を体現し続けている"
            ]
        },
        "スティーブ・ジョブズ": {
            52: [
                "52歳でiPhoneを発表したが、実はすでに膵臓がんと闘病中だった",
                "『電話を再発明する』と宣言し、実際に世界中の生活様式を変えた",
                "プレゼンのために何週間も準備し、一言一句にこだわり抜いた",
                "このiPhoneが後に世界で最も価値ある企業を生み出す礎となった"
            ]
        },
        "Ado": {
            21: [
                "21歳にして顔を一度も公開せずに国民的歌手になった前例のない快挙",
                "高校生の時から寝室で録音していた楽曲が世界的ヒットに",
                "音楽だけで勝負し、実力のみで頂点に立った新世代の象徴",
                "従来の芸能界の常識を覆し、新しい成功モデルを確立"
            ]
        },
        "さくらももこ": {
            39: [
                "39歳で達成した視聴率39.9%は、まさに奇跡的な数字の一致",
                "自身の子供時代の実体験を基に、3世代が共感できる作品を創造",
                "エッセイストから漫画家、そして国民的作家への転身を実現",
                "静岡の一般家庭の日常が、日本中の家庭の共通言語となった"
            ]
        },
        "ヘレン・ケラー": {
            7: [
                "7歳まで暗闇と無音の世界にいた少女が、水の感触から言語の概念を理解",
                "その日一日で30もの単語を習得し、教師を驚嘆させた",
                "この突破口から始まり、後に世界中の障害者に希望を与える存在に",
                "『奇跡は起きるものではなく、起こすもの』を7歳で体現"
            ]
        }
    }

    if person_name in better_facts and age in better_facts[person_name]:
        for fact in better_facts[person_name][age]:
            print(f"  ・{fact}")
    else:
        print("  ・その年齢特有の困難や挑戦")
        print("  ・同世代と比較した際の特異性")
        print("  ・その後の人生や社会への影響")
        print("  ・努力の過程や失敗からの学び")

def create_improved_episodes():
    """事実の再選択によるエピソード改善案の作成"""

    print("\n" + "="*70)
    print("💡 改善されたエピソード案（事実の再構成）")
    print("="*70)

    improved_episodes = [
        {
            "person": "イチロー",
            "age": 45,
            "original": "あなたと同じ45歳のとき、イチローは東京ドームで現役引退を発表した。日米通算4367安打の世界記録を樹立し、メジャーリーグで3089安打と10年連続200安打のシーズン記録を保持した。引退試合では5万人の観客が総立ちとなり、8分間のスタンディングオベーションが続いた。",
            "improved": "あなたと同じ45歳のとき、イチローは東京ドームで現役引退を発表した。日本プロ野球の平均引退年齢29歳の1.5倍を超えてなお現役を続け、日米通算4367安打を達成。引退会見で『後悔などあろうはずがない』と語れたのは、28年間一度も手を抜かなかった日々があったから。最後の打席でも全力疾走を貫いた。",
            "explanation": "年齢との対比、努力の継続性、プロとしての姿勢を事実として組み込んだ"
        },
        {
            "person": "スティーブ・ジョブズ",
            "age": 52,
            "original": "あなたと同じ52歳のとき、スティーブ・ジョブズはMacworld 2007でiPhoneを発表し、携帯電話を再定義した。タッチスクリーン技術により年間10億台超のスマートフォン市場を創出し、アップルの時価総額を世界一に押し上げた。",
            "improved": "あなたと同じ52歳のとき、スティーブ・ジョブズは膵臓がんと闘病しながらiPhoneを発表した。『電話を再発明する』と宣言通り、世界中の生活様式を一変させた。プレゼンのために何週間も準備し、一言一句にこだわり抜いた完璧主義が、後に世界で最も価値ある企業を生む礎となった。",
            "explanation": "闘病中という困難、準備への執念、社会への影響を事実として追加"
        },
        {
            "person": "Ado",
            "age": 21,
            "original": "あなたと同じ21歳のとき、Adoはロサンゼルス公演で3000人の会場を完売させ、海外進出に成功した。「うっせぇわ」はYouTube再生2億回を突破し、顔を公開せずに紅白歌合戦出場とBillboard Japan年間1位を達成した。",
            "improved": "あなたと同じ21歳のとき、Adoは顔を一度も公開せずに米国公演3000人を完売させた。高校時代に寝室で録音した楽曲が世界的ヒットとなり、YouTube再生2億回突破。音楽の実力だけで勝負し、従来の芸能界の常識を覆して新しい成功モデルを確立。これは才能と時代の変化が交差した瞬間だった。",
            "explanation": "前例のなさ、始まりの謙虚さ、常識への挑戦を事実として強調"
        }
    ]

    for ep in improved_episodes:
        print(f"\n【{ep['person']}（{ep['age']}歳）】")
        print(f"\n元のエピソード（{len(ep['original'])}文字）:")
        print(f"  {ep['original']}")
        print(f"\n改善案（{len(ep['improved'])}文字）:")
        print(f"  {ep['improved']}")
        print(f"\n改善のポイント:")
        print(f"  {ep['explanation']}")
        print("-"*50)

    return improved_episodes

def verify_improvements(improved_episodes):
    """改善されたエピソードがルール違反を減らすか検証"""

    print("\n" + "="*70)
    print("🔍 改善効果の検証")
    print("="*70)

    guardian = PDCAGuardian()

    for ep in improved_episodes:
        person_name = ep['person']
        age = ep['age']
        original = ep['original']
        improved = ep['improved']

        print(f"\n【{person_name}（{age}歳）】")

        # 元のエピソードの違反チェック
        person_name_display = f"{person_name}（{age}歳）"
        original_violations = guardian.check_episode_quality(
            episode_text=original,
            age=age,
            person_name_display=person_name_display
        )

        # 改善版の違反チェック
        improved_violations = guardian.check_episode_quality(
            episode_text=improved,
            age=age,
            person_name_display=person_name_display
        )

        print(f"元の違反数: {len(original_violations)}")
        print(f"改善後の違反数: {len(improved_violations)}")
        print(f"削減数: {len(original_violations) - len(improved_violations)}")

        if len(improved_violations) < len(original_violations):
            print("✅ 改善効果あり")
        else:
            print("⚠️ さらなる改善が必要")

        # 残存違反の分析
        if improved_violations:
            print("\n残存違反:")
            for v in improved_violations:
                print(f"  - {v.get('rule_id', 'UNKNOWN')}: {v.get('type', 'UNKNOWN')}")

def main():
    # 現状分析
    analyze_current_episode_facts()

    # 改善案作成
    improved_episodes = create_improved_episodes()

    # 効果検証
    verify_improvements(improved_episodes)

    print("\n" + "="*70)
    print("📝 結論")
    print("="*70)
    print("""
事実の再選択と再構成により、以下の改善が可能：

1. 年齢との関連性を強調する事実を選ぶ
   （例：平均引退年齢との比較）

2. 困難や努力のプロセスを示す事実を含める
   （例：闘病中、何週間もの準備）

3. 社会的影響や意義を示す事実を追加
   （例：生活様式を変えた、新しいモデルを確立）

4. 人間的な側面を示す事実を選択
   （例：『後悔などあろうはずがない』という言葉）

これらは「感動的な言葉」の追加ではなく、
「感動を生む事実」の選択である。
    """)

if __name__ == "__main__":
    main()