#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Anthropic APIでのエピソード生成テスト"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Anthropic APIのテスト
import anthropic

print("="*60)
print("🎉 Anthropic API エピソード生成テスト")
print("="*60)

client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

# テストプロンプト（改善版）
prompt = """あなたは日本の歴史と文化に精通した伝記作家です。
以下の人物について、指定された年齢での最も印象的なエピソードを作成してください。

【必須要件】✨
1. 必ず「あなたと同じ25歳のとき、HIKAKINは」で始める
2. その後は年齢を二度と書かない！人名も代名詞で表現
3. 以下の要素を必ず含める：
   - 具体的な作品名/プロジェクト名/番組名
   - 具体的な数値（登録者数、再生回数、順位など）
   - 固有名詞（YouTube、企業名など）
   - 「日本初」「史上最年少」などの歴史的重要性キーワード
4. 感動的な要素を含める（努力→成功、転機となった瞬間）
5. 150-250文字で簡潔かつ具体的に

【人物情報】
名前: HIKAKIN
年齢: 25歳
生年: 1989年
カテゴリ: YouTuber

エピソード（1つだけ生成）:"""

try:
    # Claude-3 Haikuで生成（コスト効率が良い）
    response = client.messages.create(
        model='claude-3-haiku-20240307',
        max_tokens=500,
        temperature=0.7,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    episode = response.content[0].text

    print("\n📝 生成されたエピソード:")
    print("-"*60)
    print(episode)
    print("-"*60)

    # 文字数カウント
    print(f"\n📊 エピソード統計:")
    print(f"  文字数: {len(episode)}文字")

    # 必須要素のチェック
    checks = {
        "開始フォーマット": episode.startswith("あなたと同じ25歳のとき、HIKAKINは"),
        "数値データ": any(char.isdigit() for char in episode),
        "YouTube含む": "YouTube" in episode or "ユーチューブ" in episode,
        "適切な長さ": 150 <= len(episode) <= 250
    }

    print("\n✅ 品質チェック:")
    for key, value in checks.items():
        status = "✅" if value else "❌"
        print(f"  {status} {key}")

    print("\n💰 コスト情報:")
    print("  モデル: Claude-3 Haiku")
    print("  推定コスト: 約$0.0003（1エピソードあたり）")
    print(f"  $10で生成可能: 約{10 / 0.0003:.0f}エピソード")

except Exception as e:
    print(f"❌ エラー: {e}")

print("\n" + "="*60)
print("✅ テスト完了")
print("="*60)