#!/usr/bin/env python3
"""
Tier1重要人物に追加エピソードを生成するスクリプト

yumeilist251128.csvのTier1人物でエピソード数が少ない人物に対して、
異なる年齢でのエピソードを追加生成する。

使用方法:
    # 分析のみ
    python scripts/expand_episode_depth.py --analyze

    # Tier1人物に追加エピソード生成
    python scripts/expand_episode_depth.py --tier 1 --limit 30 --execute

    # 特定人物のみ
    python scripts/expand_episode_depth.py --person "ブル中野" --execute
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# パス
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
YUMEILIST_PATH = PROJECT_ROOT / "yumeilist251128.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"

# APIキー
API_KEY = os.getenv("ANTHROPIC_API_KEY")


def generate_episode_id() -> str:
    """episode_idを生成"""
    return f"EP-{uuid.uuid4().hex[:6].upper()}"


def get_suggested_ages(birth_year: int, existing_ages: list[float]) -> list[int]:
    """追加すべき年齢を提案"""
    current_year = 2024
    max_age = min(current_year - birth_year, 75)

    # 標準的なターゲット年齢
    target_ages = [20, 25, 30, 35, 40, 45, 50, 55, 60]

    # 既存の年齢を整数に変換
    existing_int = {int(a) for a in existing_ages if pd.notna(a)}

    # 追加候補（既存にない、かつmax_age以下）
    suggested = []
    for age in target_ages:
        if age not in existing_int and age <= max_age:
            # 近い年齢がなければ追加
            if not any(abs(age - e) <= 3 for e in existing_int):
                suggested.append(age)

    return suggested[:3]  # 最大3つ


def generate_episode(client, person_info: dict, age: int) -> dict | None:
    """LLMでエピソードを生成"""
    name = person_info.get("person_name", "")
    category = person_info.get("category", "")
    sub_category = person_info.get("sub_category", "")
    description = person_info.get("description", "")
    birth_year = person_info.get("birth_year")

    # 年代の計算
    if birth_year and str(birth_year).replace(".", "").isdigit():
        year = int(float(birth_year)) + age
    else:
        year = 2000 + age - 30

    # カテゴリ特化のヒント
    category_hints = {
        "プロレス（女子）": f"{age}歳頃のリング上での戦い、タイトル、ライバル関係、引退後の活動など",
        "シェフ": f"{age}歳頃の料理への挑戦、店舗経営、弟子の育成、新メニュー開発など",
        "YouTuber": f"{age}歳頃のチャンネル運営、人気企画、コラボ、社会的影響など",
        "VTuber": f"{age}歳頃の配信活動、ファンとの絆、ライブイベント、人気獲得など",
        "eスポーツ": f"{age}歳頃の大会成績、ライバルとの対戦、トレーニング、メンタル面など",
        "フィギュアスケート": f"{age}歳頃の演技、大会成績、コーチとの関係、怪我からの復帰など",
        "野球": f"{age}歳頃の試合成績、チームでの役割、トレーニング、メンタル面など",
        "サッカー": f"{age}歳頃の試合、チーム、移籍、代表活動など",
        "ボクシング": f"{age}歳頃の試合、タイトル、トレーニング、対戦相手との関係など",
    }

    hint = category_hints.get(sub_category, f"{age}歳頃の重要な出来事、転機、挑戦")

    prompt = f"""あなたは著名人のエピソードを生成する専門家です。

以下の人物について、{age}歳（{year}年頃）のときの印象的なエピソードを日本語で生成してください。

■ 人物情報
- 名前: {name}
- カテゴリ: {category}（{sub_category}）
- 説明: {description}
- 年齢: {age}歳（{year}年頃）

■ 生成要件
1. 形式: 「あなたと同じ{age}歳のとき、{name}は〜」で始める
2. 長さ: 200-300文字
3. 内容: {hint}
4. トーン: 教育的かつ感動的、事実ベース
5. 禁止事項:
   - メタ的表現（「と言われている」「エピソードは」など）
   - 曖昧な表現（「ようだ」「かもしれない」など）
   - 架空の事実（実際に起こっていないこと）

エピソードテキストのみを出力してください:"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
        )
        return {
            "episode_text": response.content[0].text.strip(),
            "age": age,
        }
    except Exception as e:
        print(f"  ❌ API エラー: {e}")
        return None


def analyze_depth_deficiency(db: pd.DataFrame, yumeilist: pd.DataFrame) -> list[dict]:
    """深度不足の人物を分析"""
    person_counts = db.groupby("person_name").agg(
        episode_count=("episode_id", "count"),
        ages=("age", lambda x: sorted(x.dropna().unique().tolist())),
    )

    deficient = []

    for _, row in yumeilist.iterrows():
        name = row["person_name"]
        tier = row.get("tier", 3)

        if name in person_counts.index:
            info = person_counts.loc[name]
            ep_count = info["episode_count"]
            existing_ages = info["ages"]

            if ep_count <= 1:
                birth_year = row.get("birth_year")
                if birth_year and str(birth_year).replace(".", "").isdigit():
                    suggested = get_suggested_ages(int(float(birth_year)), existing_ages)
                else:
                    suggested = []

                deficient.append(
                    {
                        "person_name": name,
                        "tier": tier,
                        "category": row.get("category", ""),
                        "sub_category": row.get("sub_category", ""),
                        "description": row.get("description", ""),
                        "birth_year": birth_year,
                        "episode_count": ep_count,
                        "existing_ages": existing_ages,
                        "suggested_ages": suggested,
                    }
                )

    # Tier順、エピソード数順でソート
    deficient.sort(key=lambda x: (x["tier"], x["episode_count"], x["person_name"]))

    return deficient


def main():
    parser = argparse.ArgumentParser(description="エピソード深度拡張")
    parser.add_argument("--analyze", action="store_true", help="分析のみ")
    parser.add_argument("--tier", type=int, help="対象Tier（1-2）")
    parser.add_argument("--person", type=str, help="特定人物のみ")
    parser.add_argument("--limit", type=int, default=30, help="生成上限（人数）")
    parser.add_argument("--ages-per-person", type=int, default=2, help="1人あたりの追加年齢数")
    parser.add_argument("--execute", action="store_true", help="実行")
    args = parser.parse_args()

    print("=" * 70)
    print("📊 エピソード深度拡張システム (Phase 13)")
    print("=" * 70)

    # CSV読み込み
    if not CSV_PATH.exists():
        print(f"❌ CSVが見つかりません: {CSV_PATH}")
        return 1

    db = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"\n📂 DB: {len(db)}件 ({db['person_name'].nunique()}人)")

    # yumeilist読み込み
    if not YUMEILIST_PATH.exists():
        print(f"❌ yumeilistが見つかりません: {YUMEILIST_PATH}")
        return 1

    yumeilist = pd.read_csv(YUMEILIST_PATH, encoding="utf-8-sig")
    print(f"📂 yumeilist: {len(yumeilist)}件")

    # 深度不足分析
    print("\n🔍 深度不足分析中...")
    deficient = analyze_depth_deficiency(db, yumeilist)

    print("\n【分析結果】")
    print(f"  深度不足人物（エピソード1件以下）: {len(deficient)}人")

    tier_counts = {}
    for d in deficient:
        tier = d["tier"]
        if tier not in tier_counts:
            tier_counts[tier] = 0
        tier_counts[tier] += 1

    for tier, count in sorted(tier_counts.items()):
        print(f"  Tier {tier}: {count}人")

    if args.analyze:
        print("\n【深度不足人物リスト（優先度順）】")
        for i, d in enumerate(deficient[:30], 1):
            print(f"  {i}. [{d['tier']}] {d['person_name']} ({d['sub_category']})")
            print(f"      現在: {d['existing_ages']} → 追加候補: {d['suggested_ages']}")
        return 0

    if not args.execute:
        print("\n💡 --execute オプションで実行します")
        return 0

    # フィルタリング
    targets = deficient

    if args.tier:
        targets = [t for t in targets if t["tier"] == args.tier]
        print(f"\n🎯 Tier {args.tier} に絞り込み: {len(targets)}人")

    if args.person:
        targets = [t for t in targets if args.person in t["person_name"]]
        print(f"🎯 人物名 '{args.person}' に絞り込み: {len(targets)}人")

    targets = targets[: args.limit]

    if not targets:
        print("⚠️ 対象人物がいません")
        return 0

    # API確認
    if not API_KEY:
        print("❌ ANTHROPIC_API_KEY が設定されていません")
        return 1

    import anthropic

    client = anthropic.Anthropic(api_key=API_KEY)

    print(f"\n🔧 エピソード生成開始（{len(targets)}人 × 最大{args.ages_per_person}年齢）...")

    generated = []
    failed = []

    for i, person in enumerate(targets, 1):
        name = person["person_name"]
        suggested_ages = person["suggested_ages"][: args.ages_per_person]

        if not suggested_ages:
            print(f"\n[{i}/{len(targets)}] {name}: 追加候補年齢なし、スキップ")
            continue

        print(f"\n[{i}/{len(targets)}] {name}")
        print(f"  追加予定年齢: {suggested_ages}")

        for age in suggested_ages:
            result = generate_episode(client, person, age)

            if not result or len(result.get("episode_text", "")) < 100:
                failed.append({"person_name": name, "age": age})
                print(f"  ❌ {age}歳: 生成失敗")
                continue

            episode_text = result["episode_text"]

            # フォーマットチェック
            if not episode_text.startswith("あなたと同じ"):
                failed.append({"person_name": name, "age": age})
                print(f"  ❌ {age}歳: フォーマット不正")
                continue

            # 年代計算
            if age < 10:
                nendai = "0代"
            elif age < 20:
                nendai = "10代"
            elif age < 30:
                nendai = "20代"
            elif age < 40:
                nendai = "30代"
            elif age < 50:
                nendai = "40代"
            elif age < 60:
                nendai = "50代"
            else:
                nendai = "60代"

            # DB用の既存人物情報を取得
            existing = db[db["person_name"] == name].iloc[0]

            episode = {
                "episode_id": generate_episode_id(),
                "person_name": name,
                "person_id": existing.get("person_id", ""),
                "category": existing.get("category", person["category"]),
                "person_type": existing.get("person_type", "REAL"),
                "age": age,
                "年代": nendai,
                "episode_text": episode_text,
                "episode_type": "ACHIEVEMENT",
                "is_group_member": existing.get("is_group_member"),
                "group_name": existing.get("group_name"),
                "fame_score": existing.get("fame_score"),
                "episode_fame_score": existing.get("episode_fame_score"),
                "事実密度": 7.0,
                "source": "DEPTH_EXPANSION",
            }

            generated.append(episode)
            print(f"  ✅ {age}歳: 生成完了 ({len(episode_text)}文字)")

    print(f"\n{'=' * 70}")
    print("📊 結果")
    print(f"{'=' * 70}")
    print(f"  成功: {len(generated)}件")
    print(f"  失敗: {len(failed)}件")

    if not generated:
        print("⚠️ 生成されたエピソードがありません")
        return 0

    # CSVに追加
    new_df = pd.DataFrame(generated)

    for col in db.columns:
        if col not in new_df.columns:
            new_df[col] = ""

    new_df = new_df[db.columns]

    combined_df = pd.concat([db, new_df], ignore_index=True)

    # バックアップ
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = CSV_PATH.with_suffix(f".bak_depth_{timestamp}.csv")
    db.to_csv(backup_path, index=False, encoding="utf-8-sig")
    print(f"\n💾 バックアップ: {backup_path}")

    # 保存
    combined_df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"💾 CSV更新完了: {CSV_PATH}")
    print(f"   エピソード数: {len(combined_df)}件 (+{len(generated)})")

    # レポート保存
    REPORTS_DIR.mkdir(exist_ok=True)
    report_path = REPORTS_DIR / f"depth_expansion_{timestamp}.json"

    report = {
        "timestamp": timestamp,
        "targets": len(targets),
        "generated": len(generated),
        "failed": len(failed),
        "episodes": [
            {
                "episode_id": e["episode_id"],
                "person_name": e["person_name"],
                "age": e["age"],
            }
            for e in generated
        ],
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"📄 レポート: {report_path}")

    print("\n" + "=" * 70)
    print("✅ 深度拡張完了")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
