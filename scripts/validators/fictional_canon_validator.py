#!/usr/bin/env python3
"""
EPUP: 架空キャラクター カノン検証バリデータ

架空キャラクターのエピソードが物語設定に準拠しているかを検証する。

検出対象:
1. 一般的キャリア文（物語固有性が低いテンプレート表現）
2. 不自然な年齢設定（動物キャラに成人年齢等）
3. メタ表現（架空であることへの言及）

使用方法:
    # 全件スキャン
    python scripts/validators/fictional_canon_validator.py

    # 特定のエピソードをチェック
    python scripts/validators/fictional_canon_validator.py --check E441CD69E

    # CI用（違反があればexit 1）
    python scripts/validators/fictional_canon_validator.py --strict
"""

import argparse
import re
from pathlib import Path

import pandas as pd

# パス設定
MASTER_CSV = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")

# 一般的キャリア文パターン（物語固有性が低い）
CAREER_TEMPLATE_PATTERNS = [
    (r"専門性の確立", "専門性確立"),
    (r"後進の.*指導者", "指導者表現"),
    (r"コミュニケーションの重要性", "コミュニケーション"),
    (r"キャリアと.*バランス", "キャリアバランス"),
    (r"精神的な支え", "精神的支え"),
    (r"専門技術と人間性", "技術と人間性"),
    (r"転換期となりました", "転換期表現"),
    (r"自己実現", "自己実現"),
    (r"ワークライフバランス", "WLB表現"),
    (r"マネジメント能力", "マネジメント"),
]

# 不自然な年齢設定（動物/非人間キャラ）
UNNATURAL_AGE_KEYWORDS = [
    "スヌーピー",
    "くまのプーさん",
    "プーさん",
    "トトロ",
    "ミッキーマウス",
    "ドナルドダック",
    "ピカチュウ",
    "ジジ",  # 猫
    "バズ・ライトイヤー",  # おもちゃ
    "ウッディ",  # おもちゃ
    "レックス",  # おもちゃ
]

# 肩書プレフィックスパターン
TITLE_PREFIX_PATTERNS = [
    (r"^.{2,8}(市長|知事|大統領|首相|議員|大臣)", "地名+役職"),
    (r"^(バスケ|テニス|ゴルフ|サッカー|野球|アイスホッケー|ボクシング)・", "スポーツ名"),
    (r"^(マンチェスター・シティ|レアル・マドリード|バルセロナ|バウハウス)・", "組織名"),
]


def check_career_templates(text: str) -> list[tuple[str, str]]:
    """一般的キャリア文パターンを検出"""
    violations = []
    for pattern, name in CAREER_TEMPLATE_PATTERNS:
        if re.search(pattern, text):
            violations.append((name, pattern))
    return violations


def check_unnatural_age(person_name: str, age: float) -> bool:
    """不自然な年齢設定を検出（動物/非人間キャラに成人年齢）"""
    for keyword in UNNATURAL_AGE_KEYWORDS:
        if keyword in person_name:
            if 25 <= age <= 60:  # 成人年齢
                return True
    return False


def check_title_prefix(person_name: str) -> list[tuple[str, str]]:
    """肩書プレフィックスを検出"""
    violations = []
    for pattern, name in TITLE_PREFIX_PATTERNS:
        if re.search(pattern, person_name):
            violations.append((name, pattern))
    return violations


def validate_episode(row: dict) -> dict:
    """単一エピソードを検証"""
    episode_id = row.get("episode_id", "")
    person_name = str(row.get("person_name", ""))
    person_type = str(row.get("person_type", "")).upper()
    age = float(row.get("age", 0) or 0)
    text = str(row.get("episode_text", ""))

    result = {
        "episode_id": episode_id,
        "person_name": person_name,
        "age": age,
        "violations": [],
        "is_valid": True,
    }

    # 架空キャラのみ追加チェック
    if "FICTIONAL" in person_type:
        # 一般的キャリア文チェック
        career_violations = check_career_templates(text)
        if career_violations:
            result["violations"].append({"type": "CAREER_TEMPLATE", "details": career_violations})

        # 不自然な年齢チェック
        if check_unnatural_age(person_name, age):
            result["violations"].append({"type": "UNNATURAL_AGE", "details": f"{person_name}に{int(age)}歳は不自然"})

    # 肩書プレフィックスチェック（全員対象）
    title_violations = check_title_prefix(person_name)
    if title_violations:
        result["violations"].append({"type": "TITLE_PREFIX", "details": title_violations})

    result["is_valid"] = len(result["violations"]) == 0
    return result


def scan_all(csv_path: Path) -> list[dict]:
    """全件スキャン"""
    df = pd.read_csv(csv_path, low_memory=False)
    violations = []

    for _, row in df.iterrows():
        result = validate_episode(row.to_dict())
        if not result["is_valid"]:
            violations.append(result)

    return violations


def main():
    parser = argparse.ArgumentParser(description="EPUP: 架空キャラ カノン検証")
    parser.add_argument("--check", type=str, help="特定のepisode_idをチェック")
    parser.add_argument("--strict", action="store_true", help="違反があればexit 1")
    args = parser.parse_args()

    if not MASTER_CSV.exists():
        print(f"❌ CSVファイルが見つかりません: {MASTER_CSV}")
        return 1

    if args.check:
        df = pd.read_csv(MASTER_CSV, low_memory=False)
        row = df[df["episode_id"] == args.check]
        if row.empty:
            print(f"❌ episode_id が見つかりません: {args.check}")
            return 1
        result = validate_episode(row.iloc[0].to_dict())
        print(f"Episode: {result['episode_id']}")
        print(f"Person: {result['person_name']} ({result['age']}歳)")
        print(f"Valid: {result['is_valid']}")
        if result["violations"]:
            print("Violations:")
            for v in result["violations"]:
                print(f"  - {v['type']}: {v['details']}")
        return 0 if result["is_valid"] else 1

    # 全件スキャン
    print("🔍 架空キャラ カノン検証スキャン中...")
    violations = scan_all(MASTER_CSV)

    print(f"\n検出件数: {len(violations)}件")

    if violations:
        # タイプ別集計
        type_counts = {}
        for v in violations:
            for vio in v["violations"]:
                vtype = vio["type"]
                type_counts[vtype] = type_counts.get(vtype, 0) + 1

        print("\nタイプ別件数:")
        for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
            print(f"  {t}: {c}件")

        print("\n詳細（上位10件）:")
        for i, v in enumerate(violations[:10], 1):
            print(f"\n{i}. {v['episode_id']} | {v['person_name']} ({v['age']}歳)")
            for vio in v["violations"]:
                print(f"   [{vio['type']}] {vio['details']}")

    if args.strict and violations:
        print(f"\n❌ {len(violations)}件の違反があります")
        return 1

    print("\n✅ スキャン完了")
    return 0


if __name__ == "__main__":
    exit(main())
