#!/usr/bin/env python3
"""
賞のコンテキスト判定を修正
国内賞と国際賞を正確に区別
"""

def add_award_context(episode: str, fact_text: str) -> str:
    """
    賞に関する適切なコンテキストを追加

    Args:
        episode: 現在のエピソード文
        fact_text: 事実テキスト

    Returns:
        コンテキストが追加されたエピソード
    """

    # 国際的な賞（世界レベル）
    international_awards = [
        ('ノーベル', "人類の進歩に貢献したその功績は、世界中の人々に希望をもたらしています。"),
        ('グラミー賞', "世界最高峰の音楽賞での栄誉は、日本の音楽の素晴らしさを世界に示しました。"),
        ('アカデミー賞', "映画界最高の栄誉は、日本映画の芸術性を世界に証明しました。"),  # Oscarのみ
        ('Oscar', "映画界最高の栄誉は、日本映画の芸術性を世界に証明しました。"),
        ('オスカー', "映画界最高の栄誉は、日本映画の芸術性を世界に証明しました。"),
        ('カンヌ', "世界三大映画祭での受賞は、その芸術性が国際的に認められた証です。"),
        ('ヴェネツィア国際映画祭', "世界三大映画祭での栄冠は、映画史に残る快挙となりました。"),
        ('ベルリン国際映画祭', "世界三大映画祭での評価は、その作品の普遍的価値を証明しました。"),
        ('ゴールデングローブ', "ハリウッド外国人記者協会が認めた才能は、世界的な評価を得ました。")
    ]

    # 国内賞（日本国内）
    domestic_awards = [
        ('日本アカデミー賞', "日本映画界最高峰の賞での評価は、国内での確固たる地位を築きました。"),
        ('日本レコード大賞', "日本音楽界の最高栄誉は、その年を代表する作品として記憶に残ります。"),
        ('芥川賞', "日本文学界の登竜門での受賞は、新たな才能の誕生を告げました。"),
        ('直木賞', "日本の大衆文学の最高峰に輝き、多くの読者に愛される作家となりました。"),
        ('紫綬褒章', "日本国からの栄誉は、長年の功績が認められた証です。"),
        ('文化勲章', "日本文化への貢献が国家レベルで認められた最高の栄誉です。"),
        ('国民栄誉賞', "日本国民に希望と勇気を与えた功績が称えられました。")
    ]

    # 国際的な賞のチェック（順序重要：より具体的なものから）
    for award_name, context in international_awards:
        if award_name in fact_text:
            # ただし「日本アカデミー賞」は除外
            if award_name == 'アカデミー賞' and '日本アカデミー' in fact_text:
                continue
            return episode + context

    # 国内賞のチェック
    for award_name, context in domestic_awards:
        if award_name in fact_text:
            return episode + context

    # その他の賞（汎用的な表現）
    if any(k in fact_text for k in ['賞', '受賞', '表彰']):
        if '国際' in fact_text or 'International' in fact_text or '世界' in fact_text:
            return episode + "国際的な評価を受けたこの栄誉は、日本の存在感を高めました。"
        else:
            return episode + "この栄誉は長年の努力が実を結んだ瞬間でした。"

    return episode


# テストケース
def test_award_context():
    """賞のコンテキスト判定をテスト"""

    test_cases = [
        ("日本アカデミー賞優秀主演男優賞", "日本映画界最高峰の賞での評価は、国内での確固たる地位を築きました。"),
        ("アカデミー賞受賞", "映画界最高の栄誉は、日本映画の芸術性を世界に証明しました。"),
        ("グラミー賞受賞", "世界最高峰の音楽賞での栄誉は、日本の音楽の素晴らしさを世界に示しました。"),
        ("ノーベル賞受賞", "人類の進歩に貢献したその功績は、世界中の人々に希望をもたらしています。"),
        ("芥川賞受賞", "日本文学界の登竜門での受賞は、新たな才能の誕生を告げました。"),
        ("カンヌ国際映画祭パルムドール", "世界三大映画祭での受賞は、その芸術性が国際的に認められた証です。")
    ]

    print("賞コンテキスト判定テスト")
    print("=" * 60)

    for fact_text, expected in test_cases:
        result = add_award_context("", fact_text)
        status = "✅" if result == expected else "❌"
        print(f"{status} {fact_text[:20]}...")
        if result != expected:
            print(f"   期待: {expected[:30]}...")
            print(f"   実際: {result[:30]}...")

    print("=" * 60)


if __name__ == "__main__":
    test_award_context()

    # 櫻井翔のケースを修正
    sakurai_fact = "2010年、主演映画『神様のカルテ』で日本アカデミー賞優秀主演男優賞"
    base_episode = "あなたと同じ28歳のとき、櫻井翔は"

    correct_context = add_award_context(base_episode + sakurai_fact, sakurai_fact)

    print("\n櫻井翔のエピソード修正:")
    print("修正前: ...日本アカデミー賞優秀主演男優賞。世界が認めたその才能は...")
    print("修正後: " + correct_context)