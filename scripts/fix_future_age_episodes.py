#!/usr/bin/env python3
"""
未来年齢違反エピソードを有効な年齢に修正するスクリプト

機能:
1. 未来年齢違反エピソードを検出
2. 有効な年齢範囲内でランダムに新しい年齢を選択
3. LLMでその年齢のエピソードを再生成
4. CSVを更新

使用方法:
    python scripts/fix_future_age_episodes.py --dry-run
    python scripts/fix_future_age_episodes.py --execute
    python scripts/fix_future_age_episodes.py --execute --batch-size 20
"""

import argparse
import json
import os
import random
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 生年データベースをインポート
from src.birth_year_database import get_birth_year, get_max_valid_age

# Anthropic API
try:
    import anthropic

    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"


def detect_future_violations(df: pd.DataFrame, current_year: int = 2025) -> list:
    """未来年齢違反を検出"""
    violations = []

    for idx, row in df.iterrows():
        person_name = str(row["person_name"])
        age = row["age"]

        if pd.isna(age):
            continue

        age = int(age)
        birth_year = get_birth_year(person_name)

        if birth_year is not None:
            episode_year = birth_year + age
            max_valid_age = current_year - birth_year

            if episode_year > current_year:
                violations.append(
                    {
                        "index": idx,
                        "episode_id": row["episode_id"],
                        "person_name": person_name,
                        "current_age": age,
                        "birth_year": birth_year,
                        "max_valid_age": max_valid_age,
                        "category": row.get("category", ""),
                        "episode_text": row.get("episode_text", ""),
                    }
                )

    return violations


def generate_new_episode(person_name: str, new_age: int, category: str, client) -> str:
    """LLMで新しいエピソードを生成"""

    prompt = f"""以下の人物について、{new_age}歳の時のエピソードを生成してください。

人物: {person_name}
カテゴリ: {category}
年齢: {new_age}歳

要件:
1. 「あなたと同じ{new_age}歳のとき、{person_name}は...」で始める
2. 具体的な事実やエピソードを含める
3. 150-250文字程度
4. その年齢で実際に起きた出来事や状況を反映する

エピソードのみを出力してください（説明やメタ的なコメントは不要）:"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=500, messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text.strip()


def select_valid_age(person_name: str, max_valid_age: int, existing_ages: list) -> int:
    """有効な年齢を選択（既存の年齢を避ける）"""
    # 10歳から最大有効年齢の範囲で、既存の年齢を除外
    min_age = 10
    valid_ages = [a for a in range(min_age, max_valid_age + 1) if a not in existing_ages]

    if not valid_ages:
        # 既存の年齢しかない場合は最大有効年齢を使用
        return max_valid_age

    # 重みづけ: 20-50歳のエピソードを優先
    weighted_ages = []
    for a in valid_ages:
        if 20 <= a <= 50:
            weighted_ages.extend([a] * 3)  # 3倍の重み
        else:
            weighted_ages.append(a)

    return random.choice(weighted_ages)


def main():
    parser = argparse.ArgumentParser(description="未来年齢違反エピソードを修正")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン（変更なし）")
    parser.add_argument("--execute", action="store_true", help="実行")
    parser.add_argument("--batch-size", type=int, default=30, help="一度に処理する件数")
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        args.dry_run = True

    print("=" * 70)
    print(f"🔧 未来年齢違反エピソード修正 ({'dry-run' if args.dry_run else '実行'})")
    print("=" * 70)

    # データ読み込み
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"📂 CSV読み込み: {CSV_PATH}")
    print(f"  レコード数: {len(df)}件")

    # 違反検出
    violations = detect_future_violations(df)
    print(f"\n🔍 未来年齢違反: {len(violations)}件")

    if not violations:
        print("✅ 違反なし")
        return

    # 人物ごとの既存年齢を取得
    person_ages = {}
    for _, row in df.iterrows():
        pn = str(row["person_name"])
        if pn not in person_ages:
            person_ages[pn] = []
        if pd.notna(row["age"]):
            person_ages[pn].append(int(row["age"]))

    # 修正計画
    fix_plan = []
    for v in violations:
        existing = person_ages.get(v["person_name"], [])
        new_age = select_valid_age(v["person_name"], v["max_valid_age"], existing)

        fix_plan.append(
            {
                **v,
                "new_age": new_age,
            }
        )

    # 人物ごとの集計表示
    person_summary = {}
    for plan in fix_plan:
        pn = plan["person_name"]
        if pn not in person_summary:
            person_summary[pn] = {"count": 0, "max_valid": plan["max_valid_age"]}
        person_summary[pn]["count"] += 1

    print("\n📊 人物別集計:")
    for pn, data in sorted(person_summary.items(), key=lambda x: -x[1]["count"]):
        print(f"  {pn}: {data['count']}件 (最大有効年齢: {data['max_valid']}歳)")

    if args.dry_run:
        print("\n⚠️ ドライラン: 変更は保存されません")
        print(f"\n修正予定: {len(fix_plan)}件")
        for plan in fix_plan[:10]:
            print(f"  [{plan['episode_id']}] {plan['person_name']}: {plan['current_age']}歳 → {plan['new_age']}歳")
        if len(fix_plan) > 10:
            print(f"  ... 他 {len(fix_plan) - 10}件")
        return

    # LLM実行
    if not HAS_ANTHROPIC:
        print("❌ anthropicライブラリが必要です")
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY環境変数が必要です")
        return

    client = anthropic.Anthropic(api_key=api_key)

    # バッチサイズで制限
    batch = fix_plan[: args.batch_size]
    print(f"\n🔄 エピソード再生成中... ({len(batch)}/{len(fix_plan)}件)")

    results = []
    for i, plan in enumerate(batch, 1):
        print(f"  [{i}/{len(batch)}] {plan['person_name']}: {plan['current_age']}歳 → {plan['new_age']}歳...", end=" ")

        try:
            new_text = generate_new_episode(plan["person_name"], plan["new_age"], plan["category"], client)

            # DataFrame更新
            df.loc[plan["index"], "age"] = plan["new_age"]
            df.loc[plan["index"], "episode_text"] = new_text

            # person_agesも更新（次の選択に影響）
            if plan["person_name"] in person_ages:
                person_ages[plan["person_name"]].append(plan["new_age"])

            results.append(
                {
                    "episode_id": plan["episode_id"],
                    "person_name": plan["person_name"],
                    "old_age": plan["current_age"],
                    "new_age": plan["new_age"],
                    "status": "success",
                    "new_text_preview": new_text[:100] + "..." if len(new_text) > 100 else new_text,
                }
            )
            print("✅")

        except Exception as e:
            results.append(
                {
                    "episode_id": plan["episode_id"],
                    "person_name": plan["person_name"],
                    "old_age": plan["current_age"],
                    "new_age": plan["new_age"],
                    "status": "error",
                    "error": str(e),
                }
            )
            print(f"❌ {e}")

    # 保存
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"\n💾 CSV更新完了: {CSV_PATH}")

    # レポート
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_violations": len(violations),
        "batch_processed": len(batch),
        "remaining": len(violations) - len(batch),
        "total_fixed": len([r for r in results if r["status"] == "success"]),
        "total_errors": len([r for r in results if r["status"] == "error"]),
        "results": results,
    }

    report_path = REPORTS_DIR / f"future_age_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"📄 レポート: {report_path}")

    success_count = report["total_fixed"]
    error_count = report["total_errors"]
    remaining = report["remaining"]
    print(f"\n✅ 完了: {success_count}件修正, {error_count}件エラー")
    if remaining > 0:
        print(f"⚠️ 残り {remaining}件 → 再度実行してください")


if __name__ == "__main__":
    main()
