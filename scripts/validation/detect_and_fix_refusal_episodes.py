#!/usr/bin/env python3
"""
お断り文エピソード検出・修正スクリプト

EP-977276（ジョン・ボーナム58歳）問題を契機に開発。
「年齢矛盾＋お断り文」パターンを検出し、修正キューに送る。

EPUP 7ステップ:
1. 原因究明 → 本スクリプトで検出
2. システム修正 → 生成スクリプトの品質ゲート強化
3. 個別訂正 → --fix オプションで実行
4. 類似探索 → 全エピソードスキャン
5. 一括修正 → --batch-fix オプション
6. 予防 → 品質ゲート統合
7. 監視 → EPUPダッシュボード連携

使用方法:
    # 検出のみ
    python scripts/detect_and_fix_refusal_episodes.py

    # 単一エピソード修正
    python scripts/detect_and_fix_refusal_episodes.py --fix --episode P122DBD7

    # バッチ修正（上位N件）
    python scripts/detect_and_fix_refusal_episodes.py --batch-fix --limit 10
"""

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent


# ============================
# 検出パターン定義
# ============================

# お断り文パターン（正規表現）
REFUSAL_PATTERNS = [
    # 明示的な拒否
    r"エピソードを作成することはできません",
    r"エピソードを作成することができません",
    r"エピソードを生成することはできません",
    r"エピソードを生成することができません",
    r"エピソードは実在しません",
    r"エピソードは存在しません",
    # 年齢矛盾の説明
    r"年齢になっていません",
    r"年齢に達していません",
    r"年齢には達していません",
    r"まだ到来していない",
    r"未来の出来事",
    r"未来となり",
    # メタ的説明
    r"お伝えする必要があります",
    r"重要な事実を確認",
    r"重要な事実をお伝え",
    # 代替提案
    r"お知らせください",
    r"ご希望でしたら",
    r"代わりに.*をご提案",
    r"代わりに.*ご提案いたします",
    # その他
    r"そのため.*できません",
    r"申し訳ございません.*生成",
    r"亡くなって.*ため.*できません",
    r"崩御.*ため.*できません",
]

# 正しいエピソード形式（冒頭パターン）
PROPER_FORMAT_PATTERN = r"^あなたと同じ\d+歳のとき[、, ]?"

# 死亡年情報（主要な人物）
# TODO: 外部データソースと連携
KNOWN_DEATH_YEARS = {
    "ジョン・ボーナム": (1948, 1980, 32),  # (生年, 没年, 享年)
    "カート・コバーン": (1967, 1994, 27),
    "ジミ・ヘンドリックス": (1942, 1970, 27),
    "ジョン・コルトレーン": (1926, 1967, 40),
    "アンディ・フグ": (1964, 2000, 35),
    "ジャニス・ジョプリン": (1943, 1970, 27),
    "エイミー・ワインハウス": (1983, 2011, 27),
    "フレディ・マーキュリー": (1946, 1991, 45),
    "マイケル・ジャクソン": (1958, 2009, 50),
    "ジョン・レノン": (1940, 1980, 40),
}


def detect_refusal_patterns(text: str) -> List[str]:
    """お断り文パターンを検出"""
    detected = []
    for pattern in REFUSAL_PATTERNS:
        if re.search(pattern, text):
            detected.append(pattern)
    return detected


def check_proper_format(text: str) -> bool:
    """正しいエピソード形式かチェック"""
    return bool(re.match(PROPER_FORMAT_PATTERN, text))


def extract_birth_year_from_text(text: str) -> Optional[int]:
    """テキストから生年を抽出"""
    patterns = [
        r"(\d{4})年生まれ",
        r"(\d{4})年に生まれ",
        r"生年[：:]?\s*(\d{4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            year = int(match.group(1))
            if 1800 <= year <= 2010:
                return year
    return None


def extract_death_year_from_text(text: str) -> Optional[int]:
    """テキストから没年を抽出"""
    patterns = [
        r"(\d{4})年.*?(亡くなり|急逝|死去|没し|逝去)",
        r"(\d{4})年\d+月\d+日.*?(亡くなり|急逝|死去)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            year = int(match.group(1))
            if 1900 <= year <= 2025:
                return year
    return None


def classify_refusal_type(row: Dict, detected_patterns: List[str]) -> str:
    """お断り文のタイプを分類"""
    text = row.get("episode_text", "")
    person_name = row.get("person_name", "")
    age = float(row.get("age", 0)) if row.get("age") else 0

    # 既知の死亡者チェック
    if person_name in KNOWN_DEATH_YEARS:
        birth_year, death_year, max_age = KNOWN_DEATH_YEARS[person_name]
        if age > max_age:
            return "DECEASED_AGE_EXCEEDED"

    # テキストから死亡情報を抽出
    death_year = extract_death_year_from_text(text)
    if death_year:
        return "DECEASED_MENTIONED"

    # 未来年齢パターン
    future_patterns = ["未来", "まだ", "現在.*歳", "到来していない"]
    if any(re.search(p, text) for p in future_patterns):
        return "FUTURE_AGE"

    return "OTHER_REFUSAL"


def analyze_episode(row: Dict) -> Dict:
    """エピソードを分析"""
    text = row.get("episode_text", "")
    person_name = row.get("person_name", "")
    person_id = row.get("person_id", "")
    age = row.get("age", "")

    # 検出
    detected_patterns = detect_refusal_patterns(text)
    has_proper_format = check_proper_format(text)

    result = {
        "person_id": person_id,
        "person_name": person_name,
        "age": age,
        "category": row.get("category", ""),
        "is_refusal": len(detected_patterns) > 0,
        "detected_patterns": detected_patterns,
        "has_proper_format": has_proper_format,
        "refusal_type": None,
        "recommended_action": None,
        "text_preview": text[:200],
    }

    if result["is_refusal"]:
        result["refusal_type"] = classify_refusal_type(row, detected_patterns)

        # 推奨アクション決定
        if result["refusal_type"] == "DECEASED_AGE_EXCEEDED":
            if person_name in KNOWN_DEATH_YEARS:
                max_age = KNOWN_DEATH_YEARS[person_name][2]
                result["recommended_action"] = f"年齢を{max_age}歳以下に変更して再生成"
                result["suggested_age"] = max_age
        elif result["refusal_type"] == "FUTURE_AGE":
            # テキストから生年を抽出して現在年齢を計算
            birth_year = extract_birth_year_from_text(text)
            if birth_year:
                current_year = datetime.now().year
                current_age = current_year - birth_year - 1  # 1歳引いて安全マージン
                if current_age > 0:
                    result["suggested_age"] = current_age
                    result["recommended_action"] = f"年齢を{current_age}歳に変更して再生成"
                else:
                    result["recommended_action"] = "削除推奨（年齢計算不可）"
            else:
                result["recommended_action"] = "現在年齢以下に変更して再生成、または削除"
        else:
            result["recommended_action"] = "内容確認後、再生成または削除"

    return result


def scan_all_episodes(csv_path: Path) -> Tuple[List[Dict], Dict]:
    """全エピソードをスキャン"""
    problematic = []
    stats = {
        "total": 0,
        "proper": 0,
        "refusal": 0,
        "no_format": 0,
        "by_type": {},
    }

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stats["total"] += 1
            result = analyze_episode(row)

            if result["is_refusal"]:
                stats["refusal"] += 1
                refusal_type = result["refusal_type"]
                stats["by_type"][refusal_type] = stats["by_type"].get(refusal_type, 0) + 1
                problematic.append(result)
            elif not result["has_proper_format"]:
                stats["no_format"] += 1
            else:
                stats["proper"] += 1

    return problematic, stats


def generate_corrected_episode(person_name: str, suggested_age: int, category: str) -> Optional[str]:
    """LLMで修正エピソードを生成（APIキー必要）"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        prompt = f"""あなたは、人物の人生における印象的なエピソードを生成する専門家です。

以下の人物について、{suggested_age}歳のときの印象的なエピソードを日本語で生成してください。

人物名: {person_name}
カテゴリ: {category}
年齢: {suggested_age}歳

エピソードの要件:
1. 「あなたと同じ{suggested_age}歳のとき、{person_name}は〜」という形式で必ず始める
2. 具体的な事実や出来事を含める
3. 記憶に残る印象的な内容にする
4. 200-300文字程度
5. educational_valueのある内容にする
6. 事実に基づいた内容にする（架空の内容は避ける）
7. 「エピソードを作成できません」「申し訳ございません」等のメタ説明は絶対に含めない

エピソードテキスト:"""

        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=500,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
        )

        episode_text = message.content[0].text.strip()

        # 生成結果の検証
        if not check_proper_format(episode_text):
            print("  ⚠️ 生成結果が正しい形式ではありません")
            return None

        if detect_refusal_patterns(episode_text):
            print("  ⚠️ 生成結果にお断り文が含まれています")
            return None

        return episode_text

    except Exception as e:
        print(f"  ❌ エピソード生成エラー: {e}")
        return None


def fix_episode_in_csv(csv_path: Path, person_id: str, new_text: str, new_age: int) -> bool:
    """CSVファイル内のエピソードを修正"""
    rows = []
    modified = False

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row.get("person_id") == person_id:
                row["episode_text"] = new_text
                row["age"] = new_age
                row["char_count"] = len(new_text)
                row["episode_type"] = "ACHIEVEMENT"
                modified = True
            rows.append(row)

    if modified:
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return modified


def main():
    parser = argparse.ArgumentParser(description="お断り文エピソード検出・修正")
    parser.add_argument("--csv", type=str, help="対象CSVファイルパス")
    parser.add_argument("--fix", action="store_true", help="修正モード")
    parser.add_argument("--episode", type=str, help="修正対象person_id")
    parser.add_argument("--batch-fix", action="store_true", help="バッチ修正モード")
    parser.add_argument("--limit", type=int, default=10, help="バッチ修正の件数上限")
    parser.add_argument("--output", type=str, help="出力JSONファイルパス")
    args = parser.parse_args()

    print("=" * 70)
    print("🔍 お断り文エピソード検出・修正スクリプト")
    print("=" * 70)

    # CSVパス決定
    if args.csv:
        csv_path = Path(args.csv)
    else:
        csv_path = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"

    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        return 1

    print(f"\n📂 対象ファイル: {csv_path}")

    # 全スキャン
    print("\n🔍 全エピソードをスキャン中...")
    problematic, stats = scan_all_episodes(csv_path)

    # 結果表示
    print("\n" + "=" * 70)
    print("📊 スキャン結果")
    print("=" * 70)
    print(f"総エピソード数: {stats['total']:,}件")
    print(f"正常エピソード: {stats['proper']:,}件 ({stats['proper']/stats['total']*100:.1f}%)")
    print(f"お断り文エピソード: {stats['refusal']:,}件 ({stats['refusal']/stats['total']*100:.1f}%)")
    print(f"形式不正エピソード: {stats['no_format']:,}件 ({stats['no_format']/stats['total']*100:.1f}%)")

    print("\n【お断り文タイプ別】")
    for refusal_type, count in sorted(stats["by_type"].items(), key=lambda x: -x[1]):
        type_labels = {
            "DECEASED_AGE_EXCEEDED": "死亡後の年齢指定",
            "DECEASED_MENTIONED": "死亡言及あり",
            "FUTURE_AGE": "未来の年齢指定",
            "OTHER_REFUSAL": "その他のお断り",
        }
        print(f"  {type_labels.get(refusal_type, refusal_type)}: {count}件")

    print("\n【検出された問題エピソード（上位20件）】")
    for i, ep in enumerate(problematic[:20], 1):
        print(f"\n  [{i}] {ep['person_name']} (age={ep['age']})")
        print(f"      タイプ: {ep['refusal_type']}")
        print(f"      推奨: {ep['recommended_action']}")
        if ep.get("suggested_age"):
            print(f"      推奨年齢: {ep['suggested_age']}歳")
        print(f"      本文: {ep['text_preview'][:80]}...")

    # 修正モード
    if args.fix and args.episode:
        print("\n" + "=" * 70)
        print(f"🔧 修正モード: {args.episode}")
        print("=" * 70)

        target = next((ep for ep in problematic if ep["person_id"] == args.episode), None)
        if not target:
            print(f"❌ 対象エピソードが見つかりません: {args.episode}")
            return 1

        print(f"対象: {target['person_name']} (現在age={target['age']})")

        if target.get("suggested_age"):
            print(f"推奨年齢: {target['suggested_age']}歳で再生成します...")
            new_text = generate_corrected_episode(target["person_name"], target["suggested_age"], target["category"])

            if new_text:
                print("\n✅ 新エピソード生成成功:")
                print(f"   {new_text[:150]}...")

                if fix_episode_in_csv(csv_path, args.episode, new_text, target["suggested_age"]):
                    print("\n✅ CSVファイル更新完了")
                else:
                    print("\n❌ CSVファイル更新失敗")
            else:
                print("\n❌ エピソード生成失敗")
        else:
            print("⚠️ 推奨年齢が特定できないため、手動対応が必要です")

    # バッチ修正モード
    if args.batch_fix:
        print("\n" + "=" * 70)
        print(f"🔧 バッチ修正モード（上限: {args.limit}件）")
        print("=" * 70)

        # DECEASED_AGE_EXCEEDED と FUTURE_AGE タイプを自動修正
        auto_fixable = [
            ep
            for ep in problematic
            if ep["refusal_type"] in ("DECEASED_AGE_EXCEEDED", "FUTURE_AGE") and ep.get("suggested_age")
        ]

        print(f"自動修正可能: {len(auto_fixable)}件")

        fixed_count = 0
        for ep in auto_fixable[: args.limit]:
            print(f"\n  修正中: {ep['person_name']} ({ep['age']}歳 → {ep['suggested_age']}歳)")

            new_text = generate_corrected_episode(ep["person_name"], ep["suggested_age"], ep["category"])

            if new_text and fix_episode_in_csv(csv_path, ep["person_id"], new_text, ep["suggested_age"]):
                print("    ✅ 修正完了")
                fixed_count += 1
            else:
                print("    ❌ 修正失敗")

        print(f"\n📊 バッチ修正結果: {fixed_count}/{min(len(auto_fixable), args.limit)}件")

    # レポート出力
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = PROJECT_ROOT / "reports" / f'refusal_detection_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

    output_path.parent.mkdir(exist_ok=True)

    report = {
        "timestamp": datetime.now().isoformat(),
        "source_file": str(csv_path),
        "stats": stats,
        "problematic_episodes": problematic,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n📄 レポート保存: {output_path}")

    # CSV同期のリマインダー
    print("\n" + "=" * 70)
    print("💡 次のステップ")
    print("=" * 70)
    print("1. 問題エピソードを確認して修正方針を決定")
    print("2. --fix --episode <person_id> で個別修正")
    print("3. --batch-fix で自動修正可能なエピソードを一括修正")
    print("4. 修正後、CSVファイルを同期:")
    print("   cp preserved/data/MASTER_EPISODES_CURRENT.csv MASTER_EPISODES_CURRENT.csv")
    print("   cp preserved/data/MASTER_EPISODES_CURRENT.csv data/MASTER_EPISODES_CURRENT.csv")

    return 0


if __name__ == "__main__":
    sys.exit(main())
