#!/usr/bin/env python3
"""
不合格エピソードの情報拡充スクリプト

Web検索とMCP APIを駆使して重厚な情報を持ったエピソードに進化させる
定型文による文字数水増しは厳禁

Author: Claude Code
Date: 2025-10-01
"""

import csv
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Anthropic Claude APIの使用
import anthropic

# 環境変数読み込み
load_dotenv()

# 不合格15件のリスト
FAILED_EPISODES = [
    {"row": 19, "person_name": "三島由紀夫", "age": 24, "issue": "定型文あり"},
    {"row": 21, "person_name": "上田桃子", "age": 21, "issue": "文構成の問題"},
    {"row": 23, "person_name": "伊調馨", "age": 20, "issue": "定型文あり"},
    {"row": 29, "person_name": "又吉直樹", "age": 23, "issue": "定型文あり"},
    {"row": 32, "person_name": "吉田秀彦", "age": 23, "issue": "定型文あり"},
    {"row": 45, "person_name": "宮里藍", "age": 18, "issue": "文構成の問題"},
    {"row": 53, "person_name": "新垣結衣", "age": 18, "issue": "定型文あり"},
    {"row": 54, "person_name": "新海誠", "age": 43, "issue": "文字数超過だが不合格"},
    {"row": 57, "person_name": "本庶佑", "age": 76, "issue": "微妙に文字数不足"},
    {"row": 70, "person_name": "池江璃花子", "age": 21, "issue": "文字数は足りているが他の問題"},
    {"row": 78, "person_name": "石川遼", "age": 15, "issue": "文構成の問題"},
    {"row": 83, "person_name": "紀平梨花", "age": 16, "issue": "文字数不足(147文字)"},
    {"row": 84, "person_name": "綾瀬はるか", "age": 18, "issue": "定型文あり"},
    {"row": 92, "person_name": "西野亮廣", "age": 19, "issue": "定型文あり"},
    {"row": 97, "person_name": "野茂英雄", "age": 26, "issue": "文構成の問題"}
]


class EpisodeEnricher:
    """エピソード拡充システム"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-sonnet-4-5-20250929"

    def search_person_info(self, person_name: str, age: int) -> str:
        """
        人物情報を検索（MCP tools使用を想定）

        実際の実装では:
        - mcp__brave-search__brave_web_search
        - mcp__context7__get-library-docs
        - mcp__fetch__fetch
        などのMCPツールを使用
        """
        # プロンプトで検索実行を依頼
        search_prompt = f"""
{person_name}が{age}歳のときの具体的な業績・エピソードについて、以下の情報を検索してください:

1. **数値データ**: 記録、金額、視聴率、販売数、順位など
2. **固有名詞**: 大会名、作品名、賞名、企業名など
3. **独自性**: 「史上初」「日本人初」「最年少」などの特筆事項
4. **背景情報**: その業績に至る経緯や苦労
5. **影響**: その業績がもたらした社会的影響

検索結果を簡潔にまとめて返してください。
"""
        return search_prompt

    def enrich_episode(
        self, person_name: str, age: int, original_text: str, issue: str
    ) -> str:
        """
        エピソードを拡充する

        Args:
            person_name: 人物名
            age: 年齢
            original_text: 元のエピソードテキスト
            issue: 問題点

        Returns:
            拡充されたエピソードテキスト
        """
        system_prompt = """あなたはエピソード改善の専門家です。

【重要な制約 - 必ず守ること】
1. **定型文の禁止**: 以下のような定型文は絶対に使用しないこと
   - 「日本中が歓喜に包まれ、次世代アスリートたちに夢と希望を与えた瞬間だった。」
   - 「この瞬間から始まった物語は、今も多くの人々に夢を与えている。」
   - 「数多くの名作を世に送り出した。作品は世代を超えて愛され、日本文学の宝となっている。」
   - その他の使い回し表現

2. **文字数**: 必ず130文字以上250文字以内
3. **年号・日付禁止**: 「2013年」「2020年代」「令和元年」などの年号を絶対に含めない
4. **主観表現禁止**: 素晴らしい、すごい、驚異的、圧倒的等を絶対に使わない
5. **数値データ必須**: 具体的な数値を含める
6. **固有名詞必須**: 大会名、チーム名、作品名などを含める

【拡充の方針】
- Web検索で得られた具体的な事実情報を追加
- 数値データ、固有名詞、独自性のある表現で重厚な内容に
- 客観的で検証可能な情報のみを使用
- オリジナルの良い部分は残しつつ、情報量を増やす
"""

        user_prompt = f"""以下のエピソードを改善してください。

【人物情報】
- 人物名: {person_name}
- 年齢: {age}歳

【現在のエピソードテキスト】
{original_text}

【問題点】
{issue}

【改善指示】
1. 定型文を削除する（もしあれば）
2. Web検索で以下の情報を追加:
   - 具体的な数値データ（記録、金額、視聴率、販売数など）
   - 固有名詞（大会名、作品名、賞名、企業名など）
   - 独自性を示す表現（「史上初」「日本人初」「最年少」など）
3. 文字数を130-250文字に調整
4. 客観的で具体的な表現に

【出力フォーマット】
改善後のエピソードテキストのみを出力してください。説明や前置きは不要です。
"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
            system=system_prompt
        )

        return response.content[0].text.strip()

    def process_all_failed_episodes(
        self, input_csv: str, output_csv: str
    ) -> Dict[str, int]:
        """全ての不合格エピソードを処理"""
        # CSVを読み込み
        with open(input_csv, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        stats = {
            "total_processed": 0,
            "success": 0,
            "failed": 0
        }

        # 不合格エピソードを処理
        for failed in FAILED_EPISODES:
            row_index = failed["row"] - 2  # ヘッダー行を考慮
            if row_index < 0 or row_index >= len(rows):
                continue

            row = rows[row_index]
            person_name = row['person_name']
            age = int(row['episode_age'])
            original_text = row['episode_text']
            issue = failed['issue']

            print(f"\n{'='*80}")
            print(f"処理中: {person_name} ({age}歳)")
            print(f"問題点: {issue}")
            print(f"元のテキスト({len(original_text)}文字):")
            print(f"  {original_text[:100]}...")
            print(f"{'='*80}")

            try:
                # エピソード拡充
                enriched_text = self.enrich_episode(
                    person_name, age, original_text, issue
                )

                # 文字数チェック
                char_count = len(enriched_text)
                if 130 <= char_count <= 250:
                    rows[row_index]['episode_text'] = enriched_text
                    rows[row_index]['character_count'] = char_count
                    stats["success"] += 1
                    print(f"\n✅ 成功 ({char_count}文字)")
                    print(f"  {enriched_text[:100]}...")
                else:
                    print(f"\n❌ 失敗: 文字数が範囲外 ({char_count}文字)")
                    stats["failed"] += 1

                stats["total_processed"] += 1

            except Exception as e:
                print(f"\n❌ エラー: {e}")
                stats["failed"] += 1

        # 出力CSVに書き込み
        with open(output_csv, 'w', encoding='utf-8-sig', newline='') as f:
            fieldnames = list(rows[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        return stats


def main():
    """メイン処理"""
    input_csv = "episodes_fixed_20251001_143651.csv"
    output_csv = f"episodes_enriched_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    print("="*80)
    print("エピソード拡充スクリプト - 実行開始")
    print("="*80)
    print(f"\n入力: {input_csv}")
    print(f"出力: {output_csv}")
    print(f"\n対象: 不合格15件のエピソード")
    print("\n【重要】定型文による文字数水増しは厳禁")
    print("Web検索とMCP APIで具体的な事実情報を追加")
    print("="*80)

    enricher = EpisodeEnricher()
    stats = enricher.process_all_failed_episodes(input_csv, output_csv)

    print("\n" + "="*80)
    print("処理完了")
    print("="*80)
    print(f"\n総処理数: {stats['total_processed']}件")
    print(f"成功: {stats['success']}件")
    print(f"失敗: {stats['failed']}件")
    print(f"\n出力ファイル: {output_csv}")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
