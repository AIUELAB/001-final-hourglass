#!/usr/bin/env python3
"""
VTuber/YouTuber専用エピソード生成スクリプト

VTuberは「年齢」ではなく「活動年数」でエピソードを生成する。
birth_yearがデビュー年の場合、活動1年目、3年目、5年目などで生成。

使用方法:
    # 分析のみ
    python scripts/expand_vtuber_episodes.py --analyze

    # エピソード生成
    python scripts/expand_vtuber_episodes.py --execute
"""

import argparse
import json
import os
import random
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

# VTuber/YouTuberカテゴリ
VTUBER_CATEGORIES = ["VTuber", "YouTuber", "インフルエンサー"]


def generate_episode_id() -> str:
    """episode_idを生成"""
    return f"EP-{uuid.uuid4().hex[:6].upper()}"


def is_vtuber_debut_year(birth_year: float, sub_category: str) -> bool:
    """birth_yearがVTuberデビュー年かどうか判定"""
    if pd.isna(birth_year):
        return False
    # 2015年以降のbirth_yearはデビュー年と判定
    if sub_category == "VTuber" and birth_year >= 2015:
        return True
    return False


def get_activity_years_to_generate(
    debut_year: int, existing_episodes: pd.DataFrame, num_episodes: int = 2
) -> list[int]:
    """
    活動年数をランダムに選択（高品質優先）

    Args:
        debut_year: デビュー年
        existing_episodes: 既存エピソード
        num_episodes: 生成数（デフォルト: 2）

    Returns:
        活動年数のリスト（例: [2, 5]）
    """
    current_year = datetime.now().year
    max_activity = current_year - debut_year

    if max_activity < 1:
        return [1]

    # 現実的な範囲に制限（最大10年まで）
    realistic_max = min(max_activity, 10)

    if realistic_max <= num_episodes:
        selected = list(range(1, realistic_max + 1))
    else:
        candidates = list(range(1, realistic_max + 1))
        selected = random.sample(candidates, num_episodes)

    selected.sort()
    return selected


def generate_vtuber_episode(client, person_info: dict, activity_year: int) -> dict | None:
    """VTuber用エピソードを生成"""
    name = person_info["person_name"]
    sub_category = person_info.get("sub_category", "VTuber")
    description = person_info.get("description", "")
    debut_year = person_info.get("debut_year")

    if debut_year:
        calendar_year = int(debut_year) + activity_year - 1
    else:
        calendar_year = 2020 + activity_year

    # カテゴリ特化のヒント
    if sub_category == "VTuber":
        hint = f"活動{activity_year}年目の配信活動、ファンとの絆、人気企画、コラボ、ライブイベント、チャンネル成長など"
    elif sub_category == "YouTuber":
        hint = f"活動{activity_year}年目の動画制作、人気企画、チャンネル登録者数の成長、社会的影響など"
    else:
        hint = f"活動{activity_year}年目の重要な出来事、成長、転機"

    prompt = f"""あなたは著名人のエピソードを生成する専門家です。

以下のVTuber/YouTuberについて、活動{activity_year}年目（{calendar_year}年頃）の印象的なエピソードを日本語で生成してください。

■ 人物情報
- 名前: {name}
- カテゴリ: {sub_category}
- 説明: {description}
- 活動年数: {activity_year}年目（{calendar_year}年頃）

■ 生成要件
1. 形式: 「あなたと同じ活動{activity_year}年目のとき、{name}は〜」で始める
2. 長さ: 200-300文字
3. 内容: {hint}
4. トーン: 教育的かつ感動的、活動の成長を感じさせる
5. 禁止事項:
   - メタ的表現（「と言われている」「エピソードは」など）
   - 曖昧な表現（「ようだ」「かもしれない」など）
   - 「このキャラクターは架空です」などの説明
   - 実際の年齢への言及（活動年数で表現）

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
            "activity_year": activity_year,
            "calendar_year": calendar_year,
        }
    except Exception as e:
        print(f"  ❌ API エラー: {e}")
        return None


def analyze_vtuber_coverage(db: pd.DataFrame, yumeilist: pd.DataFrame) -> list[dict]:
    """VTuber/YouTuberのカバレッジを分析"""
    vtubers = yumeilist[yumeilist["sub_category"].isin(VTUBER_CATEGORIES)]

    results = []
    for _, row in vtubers.iterrows():
        name = row["person_name"]
        tier = row.get("tier", 2)
        birth_year = row.get("birth_year")
        sub_category = row.get("sub_category", "")

        # DB内のエピソード確認
        episodes = db[db["person_name"] == name]
        ep_count = len(episodes)

        # デビュー年判定
        is_debut = is_vtuber_debut_year(birth_year, sub_category)
        debut_year = int(birth_year) if is_debut and pd.notna(birth_year) else None

        results.append(
            {
                "person_name": name,
                "tier": tier,
                "sub_category": sub_category,
                "description": row.get("description", ""),
                "birth_year": birth_year,
                "is_debut_year": is_debut,
                "debut_year": debut_year,
                "episode_count": ep_count,
                "needs_episodes": ep_count < 2,
            }
        )

    # Tier順、エピソード数順でソート
    results.sort(key=lambda x: (x["tier"], x["episode_count"], x["person_name"]))

    return results


def main():
    parser = argparse.ArgumentParser(description="VTuber/YouTuberエピソード拡張")
    parser.add_argument("--analyze", action="store_true", help="分析のみ")
    parser.add_argument("--limit", type=int, default=15, help="生成上限（人数）")
    parser.add_argument("--execute", action="store_true", help="実行")
    args = parser.parse_args()

    print("=" * 70)
    print("📊 VTuber/YouTuber エピソード拡張システム (Phase 7)")
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

    # VTuber分析
    print("\n🔍 VTuber/YouTuber分析中...")
    vtubers = analyze_vtuber_coverage(db, yumeilist)

    needs_episodes = [v for v in vtubers if v["needs_episodes"]]

    print("\n【分析結果】")
    print(f"  VTuber/YouTuber総数: {len(vtubers)}人")
    print(f"  エピソード不足（2件未満）: {len(needs_episodes)}人")

    tier1_need = [v for v in needs_episodes if v["tier"] == 1]
    print(f"  うちTier1: {len(tier1_need)}人")

    if args.analyze:
        print("\n【VTuber/YouTuberリスト】")
        for i, v in enumerate(vtubers, 1):
            status = "✅" if not v["needs_episodes"] else "❌"
            debut = f"デビュー{v['debut_year']}" if v["debut_year"] else "年不明"
            print(
                f"  {i}. [{v['tier']}] {status} {v['person_name']} ({v['sub_category']}) - {v['episode_count']}件 ({debut})"
            )
        return 0

    if not args.execute:
        print("\n💡 --execute オプションで実行します")
        return 0

    # API確認
    if not API_KEY:
        print("❌ ANTHROPIC_API_KEY が設定されていません")
        return 1

    import anthropic

    client = anthropic.Anthropic(api_key=API_KEY)

    # Tier1優先でフィルタ
    targets = [v for v in needs_episodes if v["tier"] == 1][: args.limit]

    if not targets:
        print("⚠️ 対象人物がいません")
        return 0

    print(f"\n🔧 エピソード生成開始（{len(targets)}人）...")

    generated = []
    failed = []

    for i, person in enumerate(targets, 1):
        name = person["person_name"]
        debut_year = person.get("debut_year")

        print(f"\n[{i}/{len(targets)}] {name}")

        if debut_year:
            activity_years = get_activity_years_to_generate(debut_year, db, num_episodes=2)
            print(f"  デビュー: {debut_year}年, 活動年数候補: {activity_years}")
        else:
            # 推定デビュー年（2018年）を使用
            estimated_debut = 2018
            activity_years = get_activity_years_to_generate(estimated_debut, db, num_episodes=2)
            print(f"  デビュー年不明（推定{estimated_debut}年）, 活動年数候補: {activity_years}")

        for act_year in activity_years:
            person["debut_year"] = debut_year if debut_year else 2018
            result = generate_vtuber_episode(client, person, act_year)

            if not result or len(result.get("episode_text", "")) < 100:
                failed.append({"person_name": name, "activity_year": act_year})
                print(f"  ❌ 活動{act_year}年目: 生成失敗")
                continue

            episode_text = result["episode_text"]

            # フォーマットチェック
            if not episode_text.startswith("あなたと同じ"):
                failed.append({"person_name": name, "activity_year": act_year})
                print(f"  ❌ 活動{act_year}年目: フォーマット不正")
                continue

            # 年代計算（活動年数を仮の年齢として使用）
            fake_age = act_year + 19  # 活動1年目 = 20歳として

            if fake_age < 20:
                nendai = "10代"
            elif fake_age < 30:
                nendai = "20代"
            elif fake_age < 40:
                nendai = "30代"
            else:
                nendai = "40代"

            # 既存エピソードがあれば情報を継承
            existing = db[db["person_name"] == name]
            if len(existing) > 0:
                existing_row = existing.iloc[0]
                person_id = existing_row.get("person_id", "")
                category = existing_row.get("category", "エンターテイメント")
                person_type = existing_row.get("person_type", "REAL")
                is_group_member = existing_row.get("is_group_member")
                group_name = existing_row.get("group_name")
                fame_score = existing_row.get("fame_score")
            else:
                person_id = ""
                category = "エンターテイメント"
                person_type = "REAL"
                is_group_member = "YES"
                group_name = (
                    "ホロライブ"
                    if "ホロライブ" in person.get("description", "")
                    else "にじさんじ"
                    if "にじさんじ" in person.get("description", "")
                    else ""
                )
                fame_score = 8.0

            episode = {
                "episode_id": generate_episode_id(),
                "person_name": name,
                "person_id": person_id,
                "category": category,
                "person_type": person_type,
                "age": fake_age,
                "年代": nendai,
                "episode_text": episode_text,
                "episode_type": "ACHIEVEMENT",
                "is_group_member": is_group_member,
                "group_name": group_name,
                "fame_score": fame_score,
                "episode_fame_score": fame_score,
                "factual_density": 7.0,
                "source": "VTUBER_EXPANSION",
            }

            generated.append(episode)
            print(f"  ✅ 活動{act_year}年目: 生成完了 ({len(episode_text)}文字)")

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
    backup_path = CSV_PATH.with_suffix(f".bak_vtuber_{timestamp}.csv")
    db.to_csv(backup_path, index=False, encoding="utf-8-sig")
    print(f"\n💾 バックアップ: {backup_path}")

    # 保存
    combined_df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"💾 CSV更新完了: {CSV_PATH}")
    print(f"   エピソード数: {len(combined_df)}件 (+{len(generated)})")

    # レポート保存
    REPORTS_DIR.mkdir(exist_ok=True)
    report_path = REPORTS_DIR / f"vtuber_expansion_{timestamp}.json"

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
    print("✅ VTuber拡張完了")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
