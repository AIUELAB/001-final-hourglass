#!/usr/bin/env python3
"""
Refusalエピソード一括修正スクリプト

Phase 61: 検出された51件の問題エピソードを修正
- 死亡後年齢: 享年以下の年齢に修正して再生成
- 未来年齢: 現在年齢以下に修正して再生成
- グループ名: 削除
"""

import anthropic
import csv
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORT_PATH = PROJECT_ROOT / "reports" / "refusal_detection_20251203_141516.json"

# 人物の享年/現在年齢マッピング（検出されたRefusalから抽出）
# None = 削除対象（グループ名、組織名、問題あり）
PERSON_AGE_FIX = {
    # 死亡者（享年に近い年齢で再生成）
    "力道山": {"max_age": 38, "category": "スポーツ"},
    "チャーリー・パーカー": {"max_age": 33, "category": "音楽"},
    "織田信長": {"max_age": 47, "category": "歴史"},
    "上杉謙信": {"max_age": 47, "category": "歴史"},
    "坂本龍馬": {"max_age": 30, "category": "歴史"},
    "松尾芭蕉": {"max_age": 49, "category": "文学・芸術"},
    "武田信玄": {"max_age": 51, "category": "歴史"},
    "岩田聡": {"max_age": 54, "category": "ゲーム"},
    "りゅうちぇる": {"max_age": 26, "category": "エンターテイメント"},
    # 存命者（2024年現在の年齢に修正）
    "木村拓哉": {"max_age": 51, "category": "俳優・女優"},
    "石原さとみ": {"max_age": 37, "category": "俳優・女優"},
    "橋本環奈": {"max_age": 24, "category": "俳優・女優"},
    "小栗旬": {"max_age": 41, "category": "俳優・女優"},
    "山内健司": {"max_age": 42, "category": "お笑い"},
    "久保建英": {"max_age": 22, "category": "スポーツ"},
    "冨安健洋": {"max_age": 25, "category": "スポーツ"},
    "那須川天心": {"max_age": 25, "category": "スポーツ"},
    "内田真礼": {"max_age": 34, "category": "声優"},
    "あのちゃん": {"max_age": 22, "category": "エンターテイメント"},
    "桐生祥秀": {"max_age": 28, "category": "スポーツ"},
    "石田彰": {"max_age": 56, "category": "声優"},
    "楠木建": {"max_age": 60, "category": "学者"},
    "森本正治": {"max_age": 55, "category": "料理"},
    "脇屋友詞": {"max_age": 60, "category": "料理"},
    "水溜りボンド カンタ": {"max_age": 28, "category": "YouTuber"},
    # 削除対象（グループ名・組織名・問題あり）
    "乃木坂46": None,
    "欅坂46": None,
    "嵐": None,
    "SMAP": None,
    "X JAPAN": None,
    "L'Arc〜en〜Ciel": None,
    "サザンオールスターズ": None,
    "さんまに続く大御所": None,
    "サンドウィッチマン": None,
    "Hey! Say! JUMP": None,
    "King & Prince": None,
    "Perfume": None,
    "BABYMETAL": None,
    "Official髭男dism": None,
    "Every Little Thing": None,
    "ずっと真夜中でいいのに": None,
    "ヨルシカ": None,
    "聖路加国際病院": None,
    "鉄人 中村孝明": None,
    "ラファエル": None,
    "ジュキヤ": None,
    "ベニート・ムッソリーニ": None,
    "アドルフ・ヒトラー": None,
}


def generate_episode(client, person_name: str, age: int, category: str) -> str | None:
    """LLMでエピソードを再生成"""
    prompt = f"""あなたは、人物の人生における印象的なエピソードを生成する専門家です。

以下の人物について、{age}歳のときの印象的なエピソードを日本語で生成してください。

人物名: {person_name}
カテゴリ: {category}
年齢: {age}歳

【絶対厳守事項】
1. 「あなたと同じ{age}歳のとき、」で必ず始める
2. 具体的な事実や出来事を含める（年、場所、何をしたか）
3. 200-300文字
4. 以下のメタ表現は絶対に使用禁止：
   - 「申し訳」「できません」「存在しません」
   - 「架空」「フィクション」「実在しない」
   - 「エピソードを生成」「お伝えする」
5. 事実に基づいた内容のみ

エピソードテキスト（「あなたと同じ{age}歳のとき、」で始める）:"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=500,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text.strip()

        # 検証
        if not text.startswith("あなたと同じ"):
            print(f"  ⚠️ 形式不正: {text[:50]}...")
            return None

        refusal_patterns = ["申し訳", "できません", "存在しません", "架空", "フィクション"]
        for pattern in refusal_patterns:
            if pattern in text:
                print(f"  ⚠️ Refusal検出: {pattern}")
                return None

        return text
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return None


def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # レポート読み込み
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        report = json.load(f)

    problematic = report["problematic_episodes"]
    print(f"📊 問題エピソード: {len(problematic)}件")

    # CSV読み込み
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # 修正対象をperson_idでインデックス
    row_index = {row["person_id"]: i for i, row in enumerate(rows)}

    fixed_count = 0
    deleted_ids = []

    for ep in problematic:
        person_id = ep["person_id"]
        person_name = ep["person_name"]
        category = ep["category"]

        print(f"\n🔧 処理中: {person_name} (age={ep['age']}, type={ep['refusal_type']})")

        # 修正情報取得
        fix_info = PERSON_AGE_FIX.get(person_name)

        if fix_info is None:
            # グループ名など - 削除
            print(f"  🗑️ 削除対象: {person_name}")
            deleted_ids.append(person_id)
            continue

        new_age = fix_info["max_age"]

        # 再生成
        new_text = generate_episode(client, person_name, new_age, category)

        if new_text:
            idx = row_index.get(person_id)
            if idx is not None:
                rows[idx]["episode_text"] = new_text
                rows[idx]["age"] = new_age
                rows[idx]["char_count"] = len(new_text)
                print(f"  ✅ 修正完了: {new_age}歳のエピソードに更新")
                fixed_count += 1
        else:
            print("  ⚠️ 再生成失敗")

    # 削除対象を除外
    if deleted_ids:
        rows = [r for r in rows if r["person_id"] not in deleted_ids]
        print(f"\n🗑️ 削除: {len(deleted_ids)}件")

    # CSV書き出し
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("\n" + "=" * 60)
    print("📊 修正結果")
    print("=" * 60)
    print(f"修正成功: {fixed_count}件")
    print(f"削除: {len(deleted_ids)}件")
    print(f"残りエピソード: {len(rows)}件")


if __name__ == "__main__":
    main()
