#!/usr/bin/env python3
"""
禁止コンテンツ修正スクリプト

メタ説明/未来予測/推測を含むエピソードを「実活動に基づく出来事」に差し替える

禁止要素:
- メタ説明: 人物紹介、作品紹介、キャラ設定の説明
- 未来予測: 「今後〜だろう」「将来〜になる」「〜する予定」
- 推測: 「かもしれない」「と見られている」

使用方法:
    # dry-run（変更なし、検出のみ）
    python scripts/fix_prohibited_content.py --dry-run --count 10

    # サンプル実行（10件）
    python scripts/fix_prohibited_content.py --execute --count 10

    # 本番実行
    python scripts/fix_prohibited_content.py --execute --count 50

環境変数:
    ANTHROPIC_API_KEY: Anthropic APIキー
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import anthropic
import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 禁止パターン検出器をインポート
from episode_quality_system.template_blocker import TemplateBlocker

# CSVパス
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = PROJECT_ROOT / "reports"

# 環境変数チェック
API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY:
    print("❌ ANTHROPIC_API_KEY環境変数が設定されていません")
    sys.exit(1)

# Anthropic クライアント
client = anthropic.Anthropic(api_key=API_KEY)


class ProhibitedContentDetector:
    """禁止コンテンツ検出器"""

    def __init__(self):
        self.template_blocker = TemplateBlocker()

        # 未来予測パターン
        self.future_patterns = [
            (r"今後.*?だろう", "未来予測"),
            (r"今後.*?でしょう", "未来予測"),
            (r"する予定", "予定表現"),
            (r"予定(です|だ|である)", "予定表現"),
            (r"まだ到来していない", "未到達"),
            (r"まだ到達していない", "未到達"),
            (r"この年齢はまだ", "未到達"),
            (r"迎えることになります", "未来形"),
            (r"(する|なる)ことになる", "未来予測"),
            (r"(する|なる)はずだ", "推測"),
            (r"(今後|将来).*?(予想|予測|見込)", "未来予測"),
        ]

        # 推測パターン
        self.speculation_patterns = [
            (r"かもしれない", "推測"),
            (r"かもしれません", "推測"),
            (r"と見られている", "推測"),
            (r"と推測される", "推測"),
            (r"と思われる", "推測"),
            (r"と考えられる", "推測"),
            (r"おそらく", "推測"),
            (r"可能性がある", "推測"),
            (r"だろうと", "推測"),
            (r"ではないだろうか", "推測"),
        ]

        # メタ説明パターン
        self.meta_patterns = [
            (r"として知られる", "メタ説明"),
            (r"として知られて", "メタ説明"),
            (r"として有名", "メタ説明"),
            (r"で知られる", "メタ説明"),
            (r"代表作(は|として)", "メタ説明"),
            (r"人気を博した", "メタ説明"),
            (r"注目を集めた", "メタ説明"),
            (r"話題(を|と)なった", "メタ説明"),
            (r"として活躍", "メタ説明"),
            (r"として名を馳せ", "メタ説明"),
            (r"広く認知され", "メタ説明"),
            (r"という異名", "メタ説明"),
            (r"異名を持つ", "メタ説明"),
            # お断り系
            (r"申し訳ございません", "お断り"),
            (r"申し訳ありません", "お断り"),
            (r"生成することができません", "お断り"),
            (r"エピソードはありません", "お断り"),
            (r"情報がありません", "お断り"),
            # 架空キャラメタ
            (r"架空の(キャラクター|人物)", "メタ説明"),
            (r"実在しない", "メタ説明"),
            (r"フィクション(として|である)", "メタ説明"),
        ]

    def detect(self, episode_text: str, person_type: str = "REAL") -> Dict:
        """禁止コンテンツを検出"""
        if pd.isna(episode_text) or not episode_text:
            return {"has_violation": True, "types": ["EMPTY"], "details": []}

        violations = []
        types = set()

        # TemplateBlockerチェック
        should_block, tb_violations = self.template_blocker.check_episode(episode_text, person_type)
        if tb_violations:
            for v in tb_violations:
                violations.append({"pattern": v.pattern, "matched": v.matched_text, "type": v.type.value})
                types.add("TEMPLATE")

        # 未来予測チェック
        for pattern, vtype in self.future_patterns:
            matches = re.finditer(pattern, episode_text)
            for m in matches:
                violations.append({"pattern": pattern, "matched": m.group(), "type": f"FUTURE:{vtype}"})
                types.add("FUTURE")

        # 推測チェック
        for pattern, vtype in self.speculation_patterns:
            matches = re.finditer(pattern, episode_text)
            for m in matches:
                violations.append({"pattern": pattern, "matched": m.group(), "type": f"SPECULATION:{vtype}"})
                types.add("SPECULATION")

        # メタ説明チェック
        for pattern, vtype in self.meta_patterns:
            matches = re.finditer(pattern, episode_text)
            for m in matches:
                violations.append({"pattern": pattern, "matched": m.group(), "type": f"META:{vtype}"})
                types.add("META")

        return {"has_violation": len(violations) > 0, "types": list(types), "details": violations}


def build_fix_prompt(
    episode_text: str,
    person_name: str,
    age: int,
    person_type: str,
    violations: List[Dict],
    existing_episodes: List[str] = None,
) -> str:
    """修正用プロンプトを構築"""

    # 違反の説明
    violation_desc = []
    for v in violations[:5]:  # 最大5件
        violation_desc.append(f"  - {v['type']}: 「{v['matched']}」")

    violation_text = "\n".join(violation_desc) if violation_desc else "なし"

    # 既存エピソードがある場合は重複回避の指示を追加
    existing_text = ""
    if existing_episodes:
        existing_summary = "\n".join([f"  - {ep[:80]}..." for ep in existing_episodes[:3]])
        existing_text = f"""
【既存エピソード（重複を避けてください）】
{existing_summary}
"""

    # person_typeに応じた指示
    if person_type == "FICTIONAL":
        type_instruction = """
【架空キャラクター用ルール】
- 作品世界内で実際に起きた出来事（作中イベント）を記述
- メタ的説明（「このキャラクターは〜」「設定上は〜」）は絶対禁止
- 作品設定に基づいた具体的な行動・出来事を描写
"""
    else:
        type_instruction = """
【実在人物用ルール】
- 現実世界で実際に起きた出来事を記述
- 具体的な年号、数値、固有名詞を含める
- 検証可能な事実に基づく（受賞、記録、発表など）
"""

    return f"""以下のエピソードを修正してください。禁止要素を排除し、「実際の活動に基づく具体的な出来事」に書き換えてください。

【現在のエピソード】
{episode_text}

【人物情報】
人物名: {person_name}
年齢: {age}歳
タイプ: {person_type}

【検出された禁止要素】
{violation_text}

{type_instruction}
{existing_text}
【絶対禁止】
- メタ説明（「〜として知られる」「〜で有名」「代表作は〜」）
- 未来予測（「今後〜だろう」「将来〜になる」「〜する予定」）
- 推測表現（「かもしれない」「と見られている」「おそらく」）
- 架空キャラの場合：「設定上は」「公式には」「物語では」などのメタ表現

【必須形式】
1. 「あなたと同じ{age}歳のとき、{person_name}は〜」で開始
2. 250-350文字程度
3. 具体的な出来事・行動・結果を記述
4. 感情や葛藤を含めてドラマ性を持たせる

修正後のエピソード:"""


def fix_episode_with_llm(
    episode_text: str,
    person_name: str,
    age: int,
    person_type: str,
    violations: List[Dict],
    existing_episodes: List[str] = None,
) -> Optional[str]:
    """LLMでエピソードを修正"""
    prompt = build_fix_prompt(episode_text, person_name, age, person_type, violations, existing_episodes)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=600, messages=[{"role": "user", "content": prompt}]
        )
        fixed_text = response.content[0].text.strip()

        # フォーマットチェック・修正
        expected_start = f"あなたと同じ{age}歳のとき、{person_name}"
        if not fixed_text.startswith(expected_start):
            # 自動修正を試みる
            if f"{person_name}" in fixed_text:
                rest = fixed_text.split(person_name, 1)[-1]
                # 「はは」の重複を防ぐ
                if rest.startswith("はは"):
                    rest = rest[1:]  # 最初の「は」を削除
                elif not rest.startswith("は"):
                    rest = "は" + rest
                fixed_text = f"あなたと同じ{age}歳のとき、{person_name}" + rest

        # 重複助詞「はは」を修正
        fixed_text = re.sub(r"(\w)はは", r"\1は", fixed_text)

        return fixed_text

    except Exception as e:
        print(f"  ❌ LLMエラー: {e}")
        return None


def get_existing_episodes(df: pd.DataFrame, person_name: str) -> List[str]:
    """同一人物の既存エピソードを取得"""
    person_eps = df[df["person_name"] == person_name]["episode_text"].tolist()
    return [str(ep) for ep in person_eps if pd.notna(ep)]


def main():
    parser = argparse.ArgumentParser(description="禁止コンテンツ修正")
    parser.add_argument("--count", type=int, default=10, help="修正件数")
    parser.add_argument("--execute", action="store_true", help="本番実行（CSVを更新）")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン（検出のみ）")
    parser.add_argument(
        "--category", type=str, default="all", choices=["all", "META", "FUTURE", "SPECULATION"], help="対象カテゴリ"
    )

    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("⚠️ --dry-run または --execute を指定してください")
        return

    print("=" * 70)
    print(f"🔧 禁止コンテンツ修正 {'(dry-run)' if args.dry_run else '(実行)'}")
    print("=" * 70)
    print(f"  対象カテゴリ: {args.category}")
    print(f"  修正件数: {args.count}")

    # CSV読み込み
    print(f"\n📂 CSV読み込み: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"  総レコード: {len(df)}件")

    # 検出器初期化
    detector = ProhibitedContentDetector()

    # 全件スキャンして禁止コンテンツを検出
    print("\n🔍 禁止コンテンツ検出中...")
    violations_list = []

    for idx, row in df.iterrows():
        episode_text = row.get("episode_text", "")
        person_type = row.get("person_type", "REAL")
        result = detector.detect(episode_text, person_type)

        if result["has_violation"]:
            # カテゴリフィルタ
            if args.category != "all":
                if args.category not in result["types"]:
                    continue

            # 主要カテゴリ（META/FUTURE/SPECULATION）のみ対象
            priority_types = {"META", "FUTURE", "SPECULATION"}
            if not priority_types.intersection(result["types"]):
                continue

            violations_list.append(
                {
                    "index": idx,
                    "episode_id": row.get("episode_id", ""),
                    "person_name": row.get("person_name", ""),
                    "age": row.get("age", 0),
                    "person_type": person_type,
                    "episode_text": episode_text,
                    "violation_types": result["types"],
                    "violation_details": result["details"],
                }
            )

    print(f"  検出件数: {len(violations_list)}件")

    if not violations_list:
        print("\n✅ 禁止コンテンツなし")
        return

    # 対象を絞り込み
    target_list = violations_list[: args.count]
    print(f"  修正対象: {len(target_list)}件")

    # dry-runの場合は検出結果のみ表示
    if args.dry_run:
        print("\n" + "-" * 70)
        print("📋 検出された禁止コンテンツ（修正対象サンプル）")
        print("-" * 70)

        for item in target_list[:10]:
            print(f"\n【{item['episode_id']}】{item['person_name']}（{item['age']}歳）")
            print(f"  カテゴリ: {', '.join(item['violation_types'])}")
            print(f"  エピソード: {item['episode_text'][:100]}...")
            for v in item["violation_details"][:3]:
                print(f"    - {v['type']}: 「{v['matched']}」")

        # レポート保存
        REPORT_DIR.mkdir(exist_ok=True)
        report_path = REPORT_DIR / f"prohibited_content_dryrun_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_detected": len(violations_list),
            "target_count": len(target_list),
            "category_filter": args.category,
            "samples": target_list[:50],
        }
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n📄 レポート保存: {report_path}")
        return

    # 本番実行
    print("\n" + "=" * 70)
    print("🔧 修正実行開始")
    print("=" * 70)

    fix_log = []
    success_count = 0
    fail_count = 0

    for i, item in enumerate(target_list, 1):
        print(f"\n[{i}/{len(target_list)}] {item['person_name']}（{item['age']}歳）")
        print(f"  ID: {item['episode_id']}")
        print(f"  違反: {', '.join(item['violation_types'])}")

        # 既存エピソード取得（重複回避用）
        existing = get_existing_episodes(df, item["person_name"])
        existing = [ep for ep in existing if ep != item["episode_text"]]

        # LLMで修正
        fixed_text = fix_episode_with_llm(
            item["episode_text"],
            item["person_name"],
            int(item["age"]),
            item["person_type"],
            item["violation_details"],
            existing,
        )

        if not fixed_text:
            print("  ❌ 修正失敗")
            fail_count += 1
            continue

        # 修正後の検証
        recheck = detector.detect(fixed_text, item["person_type"])
        if recheck["has_violation"] and {"META", "FUTURE", "SPECULATION"}.intersection(recheck["types"]):
            print(f"  ⚠️ 修正後も違反あり: {recheck['types']}")
            # 再試行せず記録のみ
            fix_log.append(
                {
                    "episode_id": item["episode_id"],
                    "person_name": item["person_name"],
                    "age": item["age"],
                    "status": "PARTIAL",
                    "original": item["episode_text"],
                    "fixed": fixed_text,
                    "original_violations": item["violation_types"],
                    "remaining_violations": recheck["types"],
                    "reason": "修正後も一部違反が残存",
                }
            )
        else:
            # 成功
            df.loc[item["index"], "episode_text"] = fixed_text
            # source列がNaNの場合は空文字列として扱う
            current_source = df.loc[item["index"], "source"]
            if pd.isna(current_source):
                current_source = ""
            df.loc[item["index"], "source"] = str(current_source) + "→CONTENT_FIXED"

            fix_log.append(
                {
                    "episode_id": item["episode_id"],
                    "person_name": item["person_name"],
                    "age": item["age"],
                    "status": "SUCCESS",
                    "original": item["episode_text"],
                    "fixed": fixed_text,
                    "original_violations": item["violation_types"],
                    "remaining_violations": [],
                    "reason": "禁止コンテンツを実活動ベースに差し替え",
                }
            )
            success_count += 1
            print("  ✅ 修正完了")
            print(f"     Before: {item['episode_text'][:60]}...")
            print(f"     After: {fixed_text[:60]}...")

        # レート制限対策
        time.sleep(0.5)

    # 結果サマリー
    print("\n" + "=" * 70)
    print("📊 修正結果サマリー")
    print("=" * 70)
    print(f"  対象件数: {len(target_list)}")
    print(f"  成功: {success_count}件")
    print(f"  失敗: {fail_count}件")
    print(f"  部分成功: {len(target_list) - success_count - fail_count}件")

    # CSV保存
    if success_count > 0:
        print("\n💾 CSV保存中...")
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"  保存完了: {CSV_PATH}")

    # レポート保存
    REPORT_DIR.mkdir(exist_ok=True)
    report_path = REPORT_DIR / f"prohibited_content_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    report = {
        "timestamp": datetime.now().isoformat(),
        "total_detected": len(violations_list),
        "target_count": len(target_list),
        "success_count": success_count,
        "fail_count": fail_count,
        "category_filter": args.category,
        "fix_log": fix_log,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📄 レポート保存: {report_path}")

    # CSV形式のログも保存
    if fix_log:
        log_csv_path = REPORT_DIR / f"prohibited_content_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        log_df = pd.DataFrame(
            [
                {
                    "episode_id": l["episode_id"],
                    "person_name": l["person_name"],
                    "age": l["age"],
                    "status": l["status"],
                    "original_violations": ",".join(l["original_violations"]),
                    "remaining_violations": ",".join(l["remaining_violations"]),
                    "reason": l["reason"],
                    "original_text": l["original"][:200],
                    "fixed_text": l["fixed"][:200] if l["fixed"] else "",
                }
                for l in fix_log
            ]
        )
        log_df.to_csv(log_csv_path, index=False, encoding="utf-8-sig")
        print(f"📄 ログCSV保存: {log_csv_path}")

    print("\n✅ 完了")


if __name__ == "__main__":
    main()
