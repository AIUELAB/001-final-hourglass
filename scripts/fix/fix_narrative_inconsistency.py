#!/usr/bin/env python3
"""
Narrative Inconsistency Fix Script

架空キャラクターエピソードの世界観違反を修正する統合スクリプト。

対象違反タイプ:
- Type 1: 実在機関への言及（大学、賞、研究機関等）
- Type 2: ファンタジー/歴史作品での現代年号
- Type 3: フランチャイズ間のキャラクター混合
- Type 4: キャラクター誤解（作者/監督として扱う等）

Usage:
    # dry-run（対象確認）
    python scripts/fix/fix_narrative_inconsistency.py --dry-run

    # 実行（バッチAPI送信）
    python scripts/fix/fix_narrative_inconsistency.py --execute

    # 結果取得
    python scripts/fix/fix_narrative_inconsistency.py --retrieve BATCH_ID
"""

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Paths
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORT_JSON = PROJECT_ROOT / "src" / "reports" / "narrative_inconsistency_scan.json"
OUTPUT_DIR = PROJECT_ROOT / "src" / "reports"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "backups"


# =============================================================================
# Type 4 Detection Patterns - Character Misunderstanding
# =============================================================================

# キャラクターを作者/監督/制作者として扱う誤りの検出パターン
CHARACTER_MISUNDERSTANDING_PATTERNS = [
    # 作品制作への関与
    r"映画プロデューサーとして",
    r"映画製作(総指揮|に携わ|を手がけ)",
    r"映画監督として",
    r"アニメ(制作|製作)に携わ",
    r"(原作|脚本|演出)を手がけ",
    r"シリーズ(構成|監督|制作)",
    r"ワーナー・ブラザース(との|と)(契約|提携|共同)",
    r"HBO映画",
    r"スタジオ・ジブリ(との|展)",
    # 実在クリエイターとの協業
    r"J\.K\.ローリング(と|の|との)",
    r"デヴィッド・ハイマン監督",
    r"ジョン・ラセター(と|の|との|が描いた)",
    r"高橋陽一先生",
    r"(原作者|作者|制作者|監督)との?協力",
    # 出版・映画業界の表現
    r"(初版|出版|刊行)(が|を|され)",
    r"(連載|掲載)(が|を|され|開始)",
    r"発行部数",
    r"週刊少年(ジャンプ|マガジン|サンデー)",
    r"アニメーション(界|賞|作品を研究)",
    r"映画祭で.*企画",
    r"映画学部",
    # 興行・ファン関連
    r"(興行|興収|収益).*ドル",
    r"ファンを巻き込む",
    r"クリエイティブプロジェクト",
    # 財団・組織の設立
    r"(ホグワーツ|魔法)財団",
    r"教育プログラムを立ち上げ",
]


def detect_type4_violations(episode_text: str, person_type: str, work_title: str) -> list[dict[str, str]]:
    """Type 4: キャラクター誤解違反を検出"""
    violations = []

    if "FICTIONAL" not in person_type.upper():
        return violations

    for pattern in CHARACTER_MISUNDERSTANDING_PATTERNS:
        match = re.search(pattern, episode_text)
        if match:
            violations.append(
                {
                    "violation_type": "TYPE_4_CHARACTER_MISUNDERSTANDING",
                    "detected_pattern": match.group(),
                    "severity": "ERROR",
                }
            )

    return violations


# =============================================================================
# Load and Merge Violations
# =============================================================================


def load_violations_from_report() -> list[dict[str, Any]]:
    """スキャンレポートから違反を読み込み"""
    if not REPORT_JSON.exists():
        logger.warning(f"スキャンレポートが見つかりません: {REPORT_JSON}")
        return []

    with open(REPORT_JSON, "r", encoding="utf-8") as f:
        report = json.load(f)

    return report.get("violations", [])


def detect_type4_from_csv(df: pd.DataFrame) -> list[dict[str, Any]]:
    """CSVから直接Type 4違反を検出"""
    violations = []

    for _, row in df.iterrows():
        person_type = str(row.get("person_type", ""))
        if "FICTIONAL" not in person_type.upper():
            continue

        episode_text = str(row.get("episode_text", ""))
        work_title = str(row.get("work_title", ""))

        type4_violations = detect_type4_violations(episode_text, person_type, work_title)

        for v in type4_violations:
            violations.append(
                {
                    "episode_id": str(row.get("episode_id", "")),
                    "person_name": str(row.get("person_name", "")),
                    "work_title": work_title,
                    "violation_type": v["violation_type"],
                    "detected_pattern": v["detected_pattern"],
                    "severity": v["severity"],
                    "text_snippet": episode_text[:150] + "..." if len(episode_text) > 150 else episode_text,
                }
            )

    return violations


def merge_and_deduplicate_violations(
    report_violations: list[dict[str, Any]], type4_violations: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """違反をマージして episode_id でデデュプリケート"""
    # episode_id -> violation data (全タイプをマージ)
    deduplicated: dict[str, dict[str, Any]] = {}

    all_violations = report_violations + type4_violations

    for v in all_violations:
        episode_id = v.get("episode_id", "")
        if not episode_id:
            continue

        if episode_id not in deduplicated:
            deduplicated[episode_id] = {
                "episode_id": episode_id,
                "person_name": v.get("person_name", ""),
                "work_title": v.get("work_title", ""),
                "violation_types": [],
                "detected_patterns": [],
                "text_snippet": v.get("text_snippet", ""),
            }

        vtype = v.get("violation_type", "")
        pattern = v.get("detected_pattern", "")

        if vtype and vtype not in deduplicated[episode_id]["violation_types"]:
            deduplicated[episode_id]["violation_types"].append(vtype)
        if pattern and pattern not in deduplicated[episode_id]["detected_patterns"]:
            deduplicated[episode_id]["detected_patterns"].append(pattern)

    return deduplicated


# =============================================================================
# Prompts
# =============================================================================

SYSTEM_PROMPT = """あなたは物語世界のエピソード生成AIです。以下のルールを絶対に守ってください。

【最重要ルール - 世界観厳守】
1. このキャラクターは作品世界の住人です
2. 漫画・アニメの「作者」「制作者」「監督」ではありません
3. 現実世界の大学（東京大学等）、賞（アカデミー賞等）、機関（NASA等）に言及しないでください
4. 西暦年号（19XX年、20XX年）を使用しないでください（ファンタジー/歴史作品の場合）
5. 「週刊少年ジャンプ」「発行部数」「連載」などのメタ表現は禁止です
6. 作品内の出来事・場所・人物のみを使用してください
7. キャラクターの作品内での活動を具体的に描写してください

【絶対遵守ルール】
1. すべての文を常体（だ・である調）で終えてください
2. 主語は人物名または「彼/彼女」を使用してください
3. 「私は」「私の」「私が」は絶対に使用しないでください
4. 冒頭は必ず「あなたと同じX歳のとき、[人物名]は」形式で開始してください

【メタ表現禁止ルール】
5. 作品名を「」で囲んで言及しないでください（例: 「鬼滅の刃」）
6. 「〜シリーズ」「〜の世界」「〜の物語」などの表現を禁止します
7. 「アニメ」「漫画」「映画」「原作」などのメタ的表現は禁止です
8. キャラクターは作品世界内の実在人物として扱ってください
9. 読者/視聴者視点ではなく、キャラクターと同じ世界に生きている視点で書いてください

【禁止表現リスト】
- 「映画プロデューサー」「映画製作」「映画監督」
- 「ワーナー・ブラザース」「HBO」「スタジオ・ジブリ」
- 「J.K.ローリング」「ジョン・ラセター」などの実在クリエイター
- 「初版」「出版」「連載」「発行部数」
- 「アカデミー賞」「グラミー賞」「映画祭」
- 「東京大学」「ハーバード大学」等の実在大学
- 「NASA」「CERN」「WHO」等の実在機関
- 「〜財団を設立」「教育プログラムを立ち上げ」
- 「興行収入」「ファンを巻き込む」

【品質基準】
- 作品内の具体的なイベント・場所・人物を3つ以上
- 固有名詞を5つ以上
- 250〜350文字で完結"""


def create_user_prompt(
    person_name: str,
    age: int,
    work_title: str,
    violation_types: list[str],
    detected_patterns: list[str],
    current_text: str,
) -> str:
    """ユーザープロンプトを生成"""
    violation_descriptions = []

    if "TYPE_1_REAL_INSTITUTION" in violation_types:
        violation_descriptions.append("- 実在機関への言及（大学、賞、研究機関等）")
    if "TYPE_2_MODERN_YEAR_IN_FANTASY" in violation_types:
        violation_descriptions.append("- ファンタジー/歴史作品での現代年号（19XX年、20XX年）")
    if "TYPE_3_CROSS_FRANCHISE" in violation_types:
        violation_descriptions.append("- 他作品キャラクターへの言及")
    if "TYPE_4_CHARACTER_MISUNDERSTANDING" in violation_types:
        violation_descriptions.append("- キャラクターを作者/監督/制作者として扱う誤り")

    violations_text = "\n".join(violation_descriptions) if violation_descriptions else "- 世界観違反"
    patterns_text = "\n".join([f"- {p}" for p in detected_patterns[:5]]) if detected_patterns else "- 不明"

    return f"""# エピソード再生成タスク

## 対象
- 人物名: {person_name}
- 年齢: {age}歳
- 作品世界: {work_title}

## 現在のエピソード（世界観違反あり - 修正必要）
{current_text}

## 検出された違反タイプ
{violations_text}

## 検出されたパターン（一部）
{patterns_text}

## 問題点
このエピソードは、キャラクターを作品世界の外側から見た視点で書いています。
キャラクターは作品の「登場人物」ではなく、その世界で生きている「実在の人物」です。

例えば:
- ハリー・ポッターは「映画プロデューサー」ではなく「魔法使い」です
- 炭治郎は「アニメキャラ」ではなく「鬼殺隊士」です
- 悟空は「漫画の主人公」ではなく「サイヤ人の戦士」です

## 要求
上記を参考に、**世界観を厳守した**新しいエピソードを生成してください。
キャラクターを作品世界内の実在人物として扱い、その世界の出来事として記述してください。

## 必須条件
1. 冒頭は「あなたと同じ{age}歳のとき、{person_name}は」で開始
2. 250文字以上
3. 作品世界内の出来事・場所・人物のみ使用
4. 現実世界の機関・賞・年号を使用しない
5. 常体（だ・である調）で記述
6. キャラクターの作品内での具体的な活動・出来事を描写

## 出力形式
エピソードテキストのみを出力してください。"""


# =============================================================================
# Batch API Operations
# =============================================================================


def create_batch_requests(violations: dict[str, dict[str, Any]], df: pd.DataFrame) -> list[dict]:
    """Batch API用のリクエストを生成"""
    requests = []

    # episode_id -> row のマッピングを作成
    episode_rows = {str(row["episode_id"]): row for _, row in df.iterrows()}

    for episode_id, v_data in violations.items():
        if episode_id not in episode_rows:
            logger.warning(f"episode_id not found in CSV: {episode_id}")
            continue

        row = episode_rows[episode_id]
        person_name = str(row.get("person_name", ""))
        age_val = row.get("age")
        age = int(float(age_val)) if age_val is not None else 0
        work_title = str(row.get("work_title", ""))
        episode_text = str(row.get("episode_text", ""))

        user_prompt = create_user_prompt(
            person_name=person_name,
            age=age,
            work_title=work_title,
            violation_types=v_data.get("violation_types", []),
            detected_patterns=v_data.get("detected_patterns", []),
            current_text=episode_text,
        )

        requests.append(
            {
                "custom_id": f"fix_narrative_{episode_id}",
                "params": {
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1000,
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
            }
        )

    return requests


def submit_batch(requests: list[dict]) -> str:
    """Batch APIにリクエストを送信"""
    import anthropic

    client = anthropic.Anthropic()

    # JSONLファイルを作成（ログ用）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    jsonl_path = OUTPUT_DIR / f"narrative_fix_batch_{timestamp}.jsonl"

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for req in requests:
            f.write(json.dumps(req, ensure_ascii=False) + "\n")

    logger.info(f"バッチファイル作成: {jsonl_path}")

    # Batch API送信
    batch_requests: list = [
        {
            "custom_id": req["custom_id"],
            "params": {
                "model": req["params"]["model"],
                "max_tokens": req["params"]["max_tokens"],
                "system": req["params"]["system"],
                "messages": req["params"]["messages"],
            },
        }
        for req in requests
    ]
    batch = client.messages.batches.create(requests=batch_requests)

    logger.info(f"バッチ送信完了: {batch.id}")

    # バッチ情報を保存
    batch_info_path = OUTPUT_DIR / f"narrative_fix_batch_info_{timestamp}.json"
    with open(batch_info_path, "w", encoding="utf-8") as f:
        json.dump(
            {"batch_id": batch.id, "created_at": timestamp, "request_count": len(requests)},
            f,
            ensure_ascii=False,
            indent=2,
        )

    return batch.id


def retrieve_and_apply(batch_id: str) -> int:
    """バッチ結果を取得して適用"""
    import anthropic

    client = anthropic.Anthropic()

    # バッチ状態確認
    batch = client.messages.batches.retrieve(batch_id)
    logger.info(f"バッチ状態: {batch.processing_status}")

    if batch.processing_status != "ended":
        logger.warning(f"バッチ未完了: {batch.processing_status}")
        logger.info(f"  成功: {batch.request_counts.succeeded}")
        logger.info(f"  処理中: {batch.request_counts.processing}")
        logger.info(f"  失敗: {batch.request_counts.errored}")
        return 0

    # 結果取得
    results = list(client.messages.batches.results(batch_id))
    logger.info(f"結果取得: {len(results)}件")

    # マスターCSV読み込み
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig", low_memory=False)

    updated = 0
    failed = 0
    still_short = 0

    for result in results:
        if result.result.type != "succeeded":
            logger.warning(f"失敗: {result.custom_id}")
            failed += 1
            continue

        episode_id = result.custom_id.replace("fix_narrative_", "")
        content_block = result.result.message.content[0]
        if not hasattr(content_block, "text"):
            logger.warning(f"{episode_id}: テキストブロックなし")
            failed += 1
            continue
        new_text = content_block.text.strip()  # type: ignore[union-attr]

        # 長さチェック
        if len(new_text) < 200:
            logger.warning(f"{episode_id}: 再生成後も短い ({len(new_text)}文字)")
            still_short += 1
            continue

        # 更新
        mask = df["episode_id"] == episode_id
        if mask.sum() == 1:
            df.loc[mask, "episode_text"] = new_text
            updated += 1
        else:
            logger.warning(f"{episode_id}: CSVで見つからない (match: {mask.sum()})")

    # 保存
    if updated > 0:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        backup_path = BACKUP_DIR / f"MASTER_pre_narrative_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df_original = pd.read_csv(MASTER_CSV, encoding="utf-8-sig", low_memory=False)
        df_original.to_csv(backup_path, index=False, encoding="utf-8-sig")
        logger.info(f"バックアップ: {backup_path}")

        df.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")
        logger.info(f"マスターCSV更新: {updated}件")

    logger.info(f"統計: 更新={updated}, 失敗={failed}, 短文={still_short}")

    return updated


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(description="Narrative Inconsistency Fix")
    parser.add_argument("--dry-run", action="store_true", help="対象確認のみ")
    parser.add_argument("--execute", action="store_true", help="バッチAPI送信")
    parser.add_argument("--retrieve", type=str, help="バッチ結果取得 (BATCH_ID)")
    args = parser.parse_args()

    if args.retrieve:
        updated = retrieve_and_apply(args.retrieve)
        logger.info(f"更新完了: {updated}件")
        return

    # マスターCSV読み込み
    logger.info(f"読み込み: {MASTER_CSV}")
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig", low_memory=False)
    logger.info(f"総エピソード数: {len(df)}")

    # Type 1-3: レポートから読み込み
    logger.info("スキャンレポートから違反を読み込み中...")
    report_violations = load_violations_from_report()
    logger.info(f"レポート違反: {len(report_violations)}件")

    # Type 4: CSVから直接検出
    logger.info("Type 4 (Character Misunderstanding) を検出中...")
    type4_violations = detect_type4_from_csv(df)
    logger.info(f"Type 4 違反: {len(type4_violations)}件")

    # マージ & デデュプリケート
    logger.info("違反をマージ & デデュプリケート中...")
    deduplicated = merge_and_deduplicate_violations(report_violations, type4_violations)
    logger.info(f"デデュプリケート後: {len(deduplicated)}件 (ユニークエピソード)")

    if len(deduplicated) == 0:
        logger.info("対象なし")
        return

    # 統計表示
    type_counts: dict[str, int] = {}
    for v_data in deduplicated.values():
        for vtype in v_data.get("violation_types", []):
            type_counts[vtype] = type_counts.get(vtype, 0) + 1

    print("\n" + "=" * 60)
    print("Narrative Inconsistency Summary")
    print("=" * 60)
    print(f"Total unique episodes with violations: {len(deduplicated)}")
    print("\nBy violation type:")
    for vtype, count in sorted(type_counts.items()):
        print(f"  {vtype}: {count}")

    if args.dry_run:
        print("\n" + "-" * 60)
        print("Sample violations (first 10):")
        print("-" * 60)
        for i, (episode_id, v_data) in enumerate(list(deduplicated.items())[:10]):
            print(f"\n[{i+1}] {v_data['person_name']} ({v_data['work_title']})")
            print(f"    Episode ID: {episode_id}")
            print(f"    Types: {', '.join(v_data['violation_types'])}")
            print(f"    Patterns: {v_data['detected_patterns'][:3]}")

        print("\n" + "=" * 60)
        print(f"Total target episodes: {len(deduplicated)}")
        print("Run with --execute to submit to Batch API")
        print("=" * 60)
        return

    if args.execute:
        # バッチリクエスト作成・送信
        requests = create_batch_requests(deduplicated, df)
        logger.info(f"バッチリクエスト作成: {len(requests)}件")

        batch_id = submit_batch(requests)

        print("\n" + "=" * 60)
        print("Batch API Submitted")
        print("=" * 60)
        print(f"Batch ID: {batch_id}")
        print(f"Request count: {len(requests)}")
        print("\n結果取得コマンド:")
        print(f"  python scripts/fix/fix_narrative_inconsistency.py --retrieve {batch_id}")
        print("=" * 60)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
