#!/usr/bin/env python3
"""
3層パイプライン Layer1: 高速生成スクリプト

品質ゲートなしで大量のエピソードを高速生成する。
生成後はLayer2でバッチ評価し、Layer3で改稿する。

使用方法:
    # テスト実行（10件）
    python scripts/pipeline_layer1_generate.py --count 10 --dry-run

    # 本番実行（100件）
    python scripts/pipeline_layer1_generate.py --count 100 --execute

    # 特定年齢で生成
    python scripts/pipeline_layer1_generate.py --count 50 --ages 25,30,35 --execute

環境変数:
    ANTHROPIC_API_KEY: Anthropic APIキー
"""

import argparse
import csv
import hashlib
import os
import random
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import anthropic

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# グループ名検証モジュールをインポート（品質ゲート）
try:
    from src.validators.person_name_validator import (
        validate_before_episode_generation as validate_person_name,
    )
    from src.group_master import is_group_entity, GROUP_MEMBER_MAP

    GROUP_VALIDATION_AVAILABLE = True
except ImportError:
    GROUP_VALIDATION_AVAILABLE = False
    print("⚠️ グループ名検証モジュールが見つかりません。検証なしで続行します。")

# CSVパス
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
STAGING_CSV = PROJECT_ROOT / "generated" / "pipeline_staging.csv"
REPORT_DIR = PROJECT_ROOT / "reports"

# 環境変数チェック
API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY:
    print("❌ ANTHROPIC_API_KEY環境変数が設定されていません")
    sys.exit(1)

# Anthropic クライアント
client = anthropic.Anthropic(api_key=API_KEY)


# =============================================================================
# Layer1 設定（高速生成用）
# =============================================================================

LAYER1_CONFIG = {
    "api_delay": 0.3,  # API呼び出し間隔（秒）- 高速化
    "max_tokens": 400,  # 生成トークン上限
    "format_check_only": True,  # フォーマットチェックのみ
    "min_chars": 100,  # 最小文字数
    "max_chars": 500,  # 最大文字数
}

# フォーマットパターン
FORMAT_PATTERN = re.compile(r"^あなたと同じ\d+歳のとき[、,]")

# メタ表現パターン（禁止）
META_PATTERNS = [
    re.compile(r"架空の"),
    re.compile(r"フィクション"),
    re.compile(r"実在しない"),
    re.compile(r"存在しません"),
    re.compile(r"申し訳"),
]


@dataclass
class Layer1Stats:
    """Layer1生成統計"""

    total_attempted: int = 0
    generated: int = 0
    format_rejected: int = 0
    meta_rejected: int = 0
    length_rejected: int = 0
    name_mismatch_rejected: int = 0  # 名前-内容ミスマッチで拒否
    group_name_rejected: int = 0  # グループ名で拒否
    group_name_auto_fixed: int = 0  # グループ名自動修正
    api_errors: int = 0
    start_time: datetime = field(default_factory=datetime.now)

    def summary(self) -> Dict:
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return {
            "total_attempted": self.total_attempted,
            "generated": self.generated,
            "format_rejected": self.format_rejected,
            "meta_rejected": self.meta_rejected,
            "length_rejected": self.length_rejected,
            "name_mismatch_rejected": self.name_mismatch_rejected,
            "group_name_rejected": self.group_name_rejected,
            "group_name_auto_fixed": self.group_name_auto_fixed,
            "api_errors": self.api_errors,
            "success_rate": round(self.generated / max(1, self.total_attempted) * 100, 1),
            "elapsed_seconds": round(elapsed, 1),
            "episodes_per_minute": round(self.generated / max(1, elapsed / 60), 1),
        }


def generate_person_id(person_name: str) -> str:
    """person_nameからperson_idを生成"""
    hash_obj = hashlib.md5(person_name.encode("utf-8"), usedforsecurity=False)
    hash_hex = hash_obj.hexdigest()[:7].upper()
    return f"P{hash_hex}"


def generate_episode_id() -> str:
    """ユニークなepisode_idを生成"""
    timestamp = datetime.now().strftime("%y%m%d%H%M%S")
    random_suffix = random.randint(100, 999)
    return f"EP-{timestamp}{random_suffix}"


def validate_format(text: str, person_type: str = "REAL") -> tuple[bool, str]:
    """
    基本フォーマット検証（高速版）
    Returns: (is_valid, rejection_reason)
    """
    if not text:
        return False, "empty"

    # 文字数チェック
    if len(text) < LAYER1_CONFIG["min_chars"]:
        return False, "too_short"
    if len(text) > LAYER1_CONFIG["max_chars"]:
        return False, "too_long"

    # フォーマットチェック
    if not FORMAT_PATTERN.match(text):
        return False, "format_mismatch"

    # メタ表現チェック（架空キャラの場合）
    if person_type == "FICTIONAL":
        for pattern in META_PATTERNS:
            if pattern.search(text):
                return False, "meta_expression"

    return True, ""


def validate_name_in_text(episode_text: str, person_name: str) -> tuple[bool, str]:
    """
    生成されたテキストに正しい人物名が含まれているか検証

    名前-内容ミスマッチを防ぐための重要な検証。
    LLMが別の人物についてのエピソードを生成した場合を検出する。

    Returns: (is_valid, extracted_name or error_message)
    """
    # 本文から人物名を抽出
    match = re.search(r"あなたと同じ\d+歳のとき[、,]\s*([^はがをにで、,]+?)(?:は|が)", episode_text)
    if not match:
        return False, "extraction_failed"

    text_name = match.group(1).strip()

    # 正規化
    def normalize(name: str) -> str:
        # 括弧内を除去
        name = re.sub(r"[（(][^)）]+[)）]", "", name)
        # 空白除去
        return name.strip().replace(" ", "").replace("　", "")

    pn = normalize(person_name)
    tn = normalize(text_name)

    # 完全一致
    if pn == tn:
        return True, text_name

    # 部分一致（名前の一部が含まれていればOK）
    if len(pn) >= 2 and len(tn) >= 2:
        if pn in tn or tn in pn:
            return True, text_name

    # 文字の重複率チェック（日本語名向け）
    pn_chars = set(pn)
    tn_chars = set(tn)
    common = pn_chars & tn_chars
    if len(common) >= 2 and len(common) / max(len(pn_chars), len(tn_chars)) >= 0.5:
        return True, text_name

    return False, text_name


def llm_generate_fast(
    person_name: str,
    category: str,
    age: int,
    person_type: str = "REAL",
    work_title: Optional[str] = None,
) -> Optional[str]:
    """
    高速エピソード生成（品質要件を簡略化）
    """
    # EPUP Phase2: 事実優先プロンプトに変更（意外性必須を削除）
    if person_type == "FICTIONAL" and work_title:
        prompt = f"""架空キャラクター「{person_name}」（作品『{work_title}』）の{age}歳のときのエピソードを生成してください。

【最重要】必ず「{person_name}」という人物名を使用してください。

【形式】「あなたと同じ{age}歳のとき、{person_name}は〜」で必ず始めてください。

【作品世界内で描写】
  - キャラクターの性格に基づいた行動
  - 作品設定と矛盾しない内容

【絶対禁止】
  - 「架空です」「実在しません」等のメタ的説明
  - 「フィクションとして」「設定上は」等の断り書き

【文字数】200-350文字程度

エピソード:"""
    else:
        # REAL人物: 事実優先プロンプト
        prompt = f"""「{person_name}」（{category}）の{age}歳のときの事実に基づくエピソードを生成してください。

【最重要】必ず「{person_name}」という人物名を使用してください。
※グループ名、略称、別名への置き換えは禁止です。

【形式】「あなたと同じ{age}歳のとき、{person_name}は〜」で必ず始めてください。

【事実優先】以下を必ず含めてください：
  - 具体的な年号（例: 1985年、2003年）
  - 数値データ（記録、順位、金額など）
  - 検証可能な出来事や業績

【禁止事項】
  - 架空の出来事の創作
  - 「実は」「意外にも」などの誇張表現
  - 検証不可能な内面描写の過度な創作

【文字数】200-350文字程度

エピソード:"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=LAYER1_CONFIG["max_tokens"],
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"  ❌ API Error: {e}")
        return None


def load_candidates(ages: Optional[List[int]] = None, limit: int = 100) -> List[Dict]:
    """
    生成候補を読み込む（マスターCSVから未生成の人物×年齢を抽出）

    デフォルトで5-74歳のみを対象とする（0-4歳、75歳以上は除外）
    """
    # デフォルト年齢範囲（意味のあるエピソードが生成しやすい年齢帯）
    DEFAULT_AGE_MIN = 5
    DEFAULT_AGE_MAX = 74

    # マスターから既存の (person_name, age) ペアを取得
    existing_pairs = set()
    if MASTER_CSV.exists():
        with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pn = row.get("person_name", "")
                age = row.get("age", "")
                if pn and age:
                    existing_pairs.add((pn, age))

    # ステージングからも既存ペアを取得
    if STAGING_CSV.exists():
        with open(STAGING_CSV, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pn = row.get("person_name", "")
                age = row.get("age", "")
                if pn and age:
                    existing_pairs.add((pn, age))

    # 候補テンプレートから読み込み
    template_path = PROJECT_ROOT / "templates" / "phase66_candidates.csv"
    if not template_path.exists():
        print(f"❌ テンプレートが見つかりません: {template_path}")
        return []

    candidates = []
    with open(template_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pn = row.get("person_name", "")
            age = row.get("age", "")

            # 年齢フィルター
            if age:
                try:
                    age_int = int(age)
                    # 明示的な年齢リストが指定された場合
                    if ages:
                        if age_int not in ages:
                            continue
                    # デフォルト: 5-74歳のみ
                    else:
                        if age_int < DEFAULT_AGE_MIN or age_int > DEFAULT_AGE_MAX:
                            continue
                except ValueError:
                    continue
            else:
                # 年齢が空の場合はスキップ
                continue

            # 既存チェック
            if (pn, age) in existing_pairs:
                continue

            candidates.append(
                {
                    "person_name": pn,
                    "age": age,
                    "category": row.get("category", ""),
                    "person_type": row.get("person_type", "REAL"),
                    "work_title": row.get("work_title", ""),
                }
            )

            if len(candidates) >= limit * 2:  # 余裕を持って取得
                break

    random.shuffle(candidates)
    return candidates[:limit]


def run_layer1(count: int, ages: Optional[List[int]], execute: bool) -> Dict:
    """
    Layer1 高速生成を実行
    """
    print("=" * 60)
    print("🚀 Layer1: 高速エピソード生成")
    print("=" * 60)
    print(f"  目標件数: {count}")
    print(f"  年齢フィルター: {ages if ages else '全年齢'}")
    print(f"  実行モード: {'本番' if execute else 'ドライラン'}")
    print()

    # 候補読み込み
    candidates = load_candidates(ages, count * 2)
    print(f"  📋 候補数: {len(candidates)}")

    if len(candidates) < count:
        print(f"  ⚠️ 候補不足: {len(candidates)} < {count}")

    stats = Layer1Stats()
    generated_episodes = []

    # ステージングCSVのヘッダー
    fieldnames = [
        "episode_id",
        "person_id",
        "person_name",
        "category",
        "age",
        "episode_type",
        "episode_text",
        "person_type",
        "work_title",
        "group_name",
        "is_group_member",
        "source",
        "generated_at",
        "layer1_status",
    ]

    for i, cand in enumerate(candidates):
        if len(generated_episodes) >= count:
            break

        stats.total_attempted += 1
        person_name = cand["person_name"]
        age = cand["age"]
        category = cand["category"]
        person_type = cand.get("person_type", "REAL")
        work_title = cand.get("work_title", "")

        print(f"\n[{i+1}/{len(candidates)}] {person_name} ({age}歳) ...", end=" ")

        # ===== 品質ゲート: グループ名チェック =====
        group_name = ""
        is_group_member = False
        if GROUP_VALIDATION_AVAILABLE and person_type != "FICTIONAL":
            is_valid, message, suggested_fix = validate_person_name(person_name, person_type)
            if not is_valid:
                if suggested_fix:
                    old_name = person_name
                    person_name = suggested_fix["person_name"]
                    if "group_name" in suggested_fix:
                        group_name = suggested_fix["group_name"]
                        is_group_member = suggested_fix.get("is_group_member", True)
                    stats.group_name_auto_fixed += 1
                    print(f"⚠️ 修正: {old_name} → {person_name}")
                else:
                    stats.group_name_rejected += 1
                    print(f"❌ Group rejected: {message}")
                    continue

            # 追加チェック: グループ名そのものがperson_nameの場合
            if is_group_entity(person_name):
                stats.group_name_rejected += 1
                print(f"❌ Group entity: {person_name}")
                continue

            # グループメンバー情報を取得
            if not group_name and person_name in GROUP_MEMBER_MAP:
                group_name = GROUP_MEMBER_MAP[person_name]
                is_group_member = True

        # 生成
        episode_text = llm_generate_fast(person_name, category, int(age), person_type, work_title)

        if not episode_text:
            stats.api_errors += 1
            print("❌ API Error")
            continue

        # フォーマット検証
        is_valid, reason = validate_format(episode_text, person_type)

        if not is_valid:
            if reason == "format_mismatch":
                stats.format_rejected += 1
            elif reason == "meta_expression":
                stats.meta_rejected += 1
            elif reason in ("too_short", "too_long"):
                stats.length_rejected += 1
            print(f"❌ Rejected: {reason}")
            continue

        # 名前-内容一致検証（ミスマッチ防止の重要なチェック）
        name_valid, extracted_name = validate_name_in_text(episode_text, person_name)
        if not name_valid:
            stats.name_mismatch_rejected += 1
            print(f"❌ Name mismatch: {person_name} ≠ {extracted_name}")
            continue

        # 成功
        stats.generated += 1
        print(f"✅ {len(episode_text)}字")

        episode = {
            "episode_id": generate_episode_id(),
            "person_id": generate_person_id(person_name),
            "person_name": person_name,
            "category": category,
            "age": age,
            "episode_type": "TURNING_POINT",  # デフォルト
            "episode_text": episode_text,
            "person_type": person_type,
            "work_title": work_title,
            "group_name": group_name,
            "is_group_member": is_group_member,
            "source": "layer1_fast",
            "generated_at": datetime.now().isoformat(),
            "layer1_status": "pending_evaluation",
        }
        generated_episodes.append(episode)

        # API制限
        time.sleep(LAYER1_CONFIG["api_delay"])

    # 結果サマリ
    print("\n" + "=" * 60)
    print("📊 Layer1 生成結果")
    print("=" * 60)
    summary = stats.summary()
    for k, v in summary.items():
        print(f"  {k}: {v}")

    # ステージングCSVに保存
    if execute and generated_episodes:
        STAGING_CSV.parent.mkdir(parents=True, exist_ok=True)

        # 既存データと統合
        existing = []
        if STAGING_CSV.exists():
            with open(STAGING_CSV, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                existing = list(reader)

        all_episodes = existing + generated_episodes

        with open(STAGING_CSV, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for ep in all_episodes:
                # 欠損フィールド補完
                row = {k: ep.get(k, "") for k in fieldnames}
                writer.writerow(row)

        print(f"\n✅ ステージングCSVに保存: {STAGING_CSV}")
        print(f"   新規追加: {len(generated_episodes)}件")
        print(f"   累計: {len(all_episodes)}件")

    # レポート保存
    REPORT_DIR.mkdir(exist_ok=True)
    report_path = REPORT_DIR / f"layer1_generate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    import json

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "config": LAYER1_CONFIG,
                "stats": summary,
                "sample_episodes": [
                    {
                        "person_name": ep["person_name"],
                        "age": ep["age"],
                        "text_preview": ep["episode_text"][:100],
                    }
                    for ep in generated_episodes[:5]
                ],
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"📝 レポート保存: {report_path}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Layer1 高速エピソード生成")
    parser.add_argument("--count", type=int, default=10, help="生成件数")
    parser.add_argument("--ages", type=str, help="年齢フィルター（カンマ区切り）")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン")
    parser.add_argument("--execute", action="store_true", help="本番実行")
    args = parser.parse_args()

    ages = None
    if args.ages:
        ages = [int(a.strip()) for a in args.ages.split(",")]

    execute = args.execute and not args.dry_run

    run_layer1(args.count, ages, execute)


if __name__ == "__main__":
    main()
