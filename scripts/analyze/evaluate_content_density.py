#!/usr/bin/env python3
"""
内容密度品質評価スクリプト

エピソードの「内容密度」を評価し、冗長パターンを検出する。
文字数だけでなく、情報の質と密度を評価。

使用方法:
    # レポート生成（ドライラン）
    python scripts/evaluate_content_density.py

    # CSV更新
    python scripts/evaluate_content_density.py --execute

    # 特定エピソードの評価
    python scripts/evaluate_content_density.py --episode EP-000001
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"

# =============================================================================
# 冗長パターン定義
# =============================================================================

REDUNDANCY_PATTERNS = {
    "severe": {
        "patterns": [
            r"(礎|基盤|土台)となった",
            r"刻まれて(いる|いた|います)",
            r"後世に(影響|残る|伝わる)",
            r"語り継がれて(いる|いた)",
            r"歴史に(名を|その名を)刻んだ",
            r"生涯.*忘れ(なかった|ませんでした)",
        ],
        "weight": -3.0,
        "description": "結論の一般化（検証不可能な主張）",
    },
    "moderate": {
        "patterns": [
            r"この(経験|時期|瞬間)が",
            r"という(言葉|思い|経験)",
            r"人生を.*変えた",
            r"(重要な|大きな|貴重な)(経験|教訓|出来事)",
            r"新たな(可能性|挑戦|一歩)",
            r"キャリアの(重要な)?転機",
        ],
        "weight": -2.0,
        "description": "メタ的説明（抽象的影響）",
    },
    "mild": {
        "patterns": [
            r"涙を(流した|流しました)",
            r"震える(手|声)",
            r"胸が熱くなった",
            r"心を打たれた",
            r"感動を(呼んだ|与えた)",
            r"魂の叫び",
        ],
        "weight": -1.0,
        "description": "抽象的感情表現（検証困難）",
    },
    "placeholder": {
        "patterns": [
            r"独自の視点と情熱を持って",
            r"その後の成功の基盤となる",
            r"決断力と行動力で道を切り開いて",
            r"貴重な経験を積みました",
            r"周囲からの期待と自身の目標との間で",
            r"葛藤しながらも",
        ],
        "weight": -2.5,
        "description": "プレースホルダー表現（汎用フレーズ）",
    },
}

# 情報密度検出パターン
INFO_DENSITY_PATTERNS = {
    "year": r"\d{4}年",
    "date": r"\d+月\d*日?",
    "work_title": r"『[^』]+』",
    "quote": r"「[^」]+」",
    "number": r"\d+[万億]?[人枚本部回個]",
    "rank": r"(第\d+[位回]|1位|優勝|準優勝)",
    "award": r"(賞|メダル|トロフィー|タイトル)を?(受賞|獲得|授与)",
}


def detect_redundancy_patterns(text: str) -> dict:
    """冗長パターンを検出"""
    detected = {
        "patterns": [],
        "total_count": 0,
        "total_penalty": 0.0,
        "by_severity": {},
    }

    for severity, config in REDUNDANCY_PATTERNS.items():
        matches = []
        for pattern in config["patterns"]:
            found = re.findall(pattern, text)
            if found:
                matches.extend(found if isinstance(found[0], str) else [m[0] for m in found])

        if matches:
            detected["patterns"].append(
                {
                    "severity": severity,
                    "matches": matches,
                    "count": len(matches),
                    "penalty": config["weight"] * len(matches),
                }
            )
            detected["by_severity"][severity] = len(matches)
            detected["total_count"] += len(matches)
            detected["total_penalty"] += config["weight"] * len(matches)

    return detected


def calculate_info_density(text: str) -> dict:
    """情報密度を計算"""
    char_count = len(text)
    if char_count == 0:
        return {"score": 0, "items": {}, "density_ratio": 0}

    items = {}
    total_count = 0

    for item_type, pattern in INFO_DENSITY_PATTERNS.items():
        matches = re.findall(pattern, text)
        count = len(matches)
        items[item_type] = count
        total_count += count

    # 100文字あたりの情報量
    density_ratio = total_count / (char_count / 100)

    return {
        "total_count": total_count,
        "items": items,
        "density_ratio": round(density_ratio, 2),
    }


def calculate_length_score(char_count: int) -> float:
    """文字数適正度スコア（0-3.0）"""
    if 200 <= char_count <= 300:
        return 3.0
    elif 180 <= char_count < 200 or 300 < char_count <= 350:
        return 2.5
    elif 150 <= char_count < 180 or 350 < char_count <= 400:
        return 2.0
    elif 100 <= char_count < 150 or 400 < char_count <= 500:
        return 1.0
    else:
        return 0.5


def calculate_structure_score(text: str) -> float:
    """構造品質スコア（0-2.0）"""
    sentences = re.split(r"[。！？]", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    sentence_count = len(sentences)

    if 3 <= sentence_count <= 6:
        return 2.0
    elif 2 <= sentence_count <= 8:
        return 1.5
    elif sentence_count == 1 or sentence_count > 10:
        return 0.5
    else:
        return 1.0


def calculate_content_density_quality(episode_data: dict) -> dict:
    """内容密度品質を総合評価（1.0-10.0）"""
    text = str(episode_data.get("episode_text", ""))
    char_count = len(text)

    # 各要素を計算
    length_score = calculate_length_score(char_count)
    redundancy = detect_redundancy_patterns(text)
    info_density = calculate_info_density(text)
    structure_score = calculate_structure_score(text)

    # 冗長性スコア（3.0からペナルティを引く）
    redundancy_score = max(0, 3.0 + redundancy["total_penalty"])

    # 情報密度スコア（0-2.0）
    density_ratio = info_density["density_ratio"]
    if density_ratio >= 2.0:
        info_density_score = 2.0
    elif density_ratio >= 1.5:
        info_density_score = 1.7
    elif density_ratio >= 1.0:
        info_density_score = 1.4
    elif density_ratio >= 0.5:
        info_density_score = 1.0
    else:
        info_density_score = 0.5

    # 総合スコア
    raw_score = length_score + redundancy_score + info_density_score + structure_score
    final_score = max(1.0, min(10.0, raw_score))

    return {
        "content_density_score": round(final_score, 2),
        "components": {
            "length_score": round(length_score, 2),
            "redundancy_score": round(redundancy_score, 2),
            "info_density_score": round(info_density_score, 2),
            "structure_score": round(structure_score, 2),
        },
        "char_count": char_count,
        "redundancy": redundancy,
        "info_density": info_density,
    }


def classify_issue_type(result: dict, row: dict) -> list:
    """問題タイプを分類"""
    issues = []
    char_count = result["char_count"]
    score = result["content_density_score"]
    redundancy_count = result["redundancy"]["total_count"]

    # 7軸平均スコア
    score_cols = [
        "memorability_score",
        "empathy_score",
        "surprise_score",
        "generation_quality_score",
        "educational_value",
        "story_quality",
        "factual_density",
    ]
    seven_axis_avg = sum(float(row.get(col, 0) or 0) for col in score_cols) / len(score_cols)

    if char_count > 300 and seven_axis_avg < 6.5:
        issues.append("long_low_score")
    if char_count < 150:
        issues.append("too_short")
    if redundancy_count >= 2:
        issues.append("high_redundancy")
    if result["info_density"]["density_ratio"] < 0.5:
        issues.append("low_info_density")

    return issues


def evaluate_all_episodes(df: pd.DataFrame) -> pd.DataFrame:
    """全エピソードを評価"""
    results = []

    for idx, row in df.iterrows():
        episode_data = row.to_dict()
        result = calculate_content_density_quality(episode_data)
        issues = classify_issue_type(result, episode_data)

        results.append(
            {
                "episode_id": row["episode_id"],
                "content_density_score": result["content_density_score"],
                "length_score": result["components"]["length_score"],
                "redundancy_score": result["components"]["redundancy_score"],
                "info_density_score": result["components"]["info_density_score"],
                "structure_score": result["components"]["structure_score"],
                "char_count": result["char_count"],
                "redundancy_count": result["redundancy"]["total_count"],
                "info_density_ratio": result["info_density"]["density_ratio"],
                "issues": issues,
                "redundancy_patterns": json.dumps(result["redundancy"]["by_severity"], ensure_ascii=False),
            }
        )

    return pd.DataFrame(results)


def generate_report(df: pd.DataFrame, results_df: pd.DataFrame) -> dict:
    """評価レポートを生成"""
    merged = df.merge(results_df, on="episode_id")

    report = {
        "timestamp": datetime.now().isoformat(),
        "total_episodes": len(df),
        "summary": {
            "average_content_density_score": round(results_df["content_density_score"].mean(), 2),
            "average_char_count": round(results_df["char_count"].mean(), 1),
            "high_quality_count": len(results_df[results_df["content_density_score"] >= 7.0]),
            "low_quality_count": len(results_df[results_df["content_density_score"] < 5.0]),
        },
        "distribution": {
            "9-10": len(results_df[results_df["content_density_score"] >= 9.0]),
            "7-9": len(
                results_df[(results_df["content_density_score"] >= 7.0) & (results_df["content_density_score"] < 9.0)]
            ),
            "5-7": len(
                results_df[(results_df["content_density_score"] >= 5.0) & (results_df["content_density_score"] < 7.0)]
            ),
            "3-5": len(
                results_df[(results_df["content_density_score"] >= 3.0) & (results_df["content_density_score"] < 5.0)]
            ),
            "1-3": len(results_df[results_df["content_density_score"] < 3.0]),
        },
        "issues": {
            "long_low_score": len([r for r in results_df["issues"] if "long_low_score" in r]),
            "too_short": len([r for r in results_df["issues"] if "too_short" in r]),
            "high_redundancy": len([r for r in results_df["issues"] if "high_redundancy" in r]),
            "low_info_density": len([r for r in results_df["issues"] if "low_info_density" in r]),
        },
        "redundancy_patterns": {},
    }

    # 冗長パターン集計
    for _, row in results_df.iterrows():
        patterns = json.loads(row["redundancy_patterns"])
        for severity, count in patterns.items():
            if severity not in report["redundancy_patterns"]:
                report["redundancy_patterns"][severity] = 0
            report["redundancy_patterns"][severity] += count

    # 高品質率
    report["summary"]["high_quality_rate"] = round(report["summary"]["high_quality_count"] / len(df) * 100, 2)

    return report


def main():
    parser = argparse.ArgumentParser(description="内容密度品質評価")
    parser.add_argument("--execute", action="store_true", help="CSVを更新")
    parser.add_argument("--episode", type=str, help="特定エピソードのみ評価")
    parser.add_argument("--limit", type=int, help="評価件数の上限")
    args = parser.parse_args()

    print("=" * 80)
    print("📊 内容密度品質評価")
    print("=" * 80)
    print()

    # CSV読み込み
    print("Step 1: CSVファイル読み込み中...")
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"  読み込み完了: {len(df):,}件")
    print()

    # 特定エピソードの評価
    if args.episode:
        ep = df[df["episode_id"] == args.episode]
        if len(ep) == 0:
            print(f"❌ エピソードが見つかりません: {args.episode}")
            return

        row = ep.iloc[0]
        result = calculate_content_density_quality(row.to_dict())

        print(f"エピソード: {args.episode}")
        print(f"人物: {row['person_name']} ({row['age']}歳)")
        print(f"文字数: {result['char_count']}")
        print()
        print("【スコア詳細】")
        print(f"  総合スコア: {result['content_density_score']}")
        print(f"  文字数適正度: {result['components']['length_score']}")
        print(f"  冗長性スコア: {result['components']['redundancy_score']}")
        print(f"  情報密度スコア: {result['components']['info_density_score']}")
        print(f"  構造品質スコア: {result['components']['structure_score']}")
        print()
        print("【冗長パターン検出】")
        for p in result["redundancy"]["patterns"]:
            print(f"  {p['severity']}: {p['matches']} (penalty: {p['penalty']})")
        print()
        print("【情報密度】")
        print(f"  密度比: {result['info_density']['density_ratio']}")
        for item_type, count in result["info_density"]["items"].items():
            if count > 0:
                print(f"  {item_type}: {count}")
        print()
        print("【本文】")
        print(row["episode_text"])
        return

    # 全エピソード評価
    print("Step 2: 全エピソード評価中...")
    if args.limit:
        df = df.head(args.limit)
    results_df = evaluate_all_episodes(df)
    print(f"  評価完了: {len(results_df):,}件")
    print()

    # レポート生成
    print("Step 3: レポート生成中...")
    report = generate_report(df, results_df)

    print()
    print("=" * 80)
    print("📈 評価結果サマリー")
    print("=" * 80)
    print()
    print(f"総エピソード数: {report['total_episodes']:,}")
    print(f"平均内容密度スコア: {report['summary']['average_content_density_score']}")
    print(f"平均文字数: {report['summary']['average_char_count']:.1f}")
    print(f"高品質率 (>=7.0): {report['summary']['high_quality_rate']}%")
    print()
    print("【スコア分布】")
    for range_name, count in report["distribution"].items():
        print(f"  {range_name}: {count}件")
    print()
    print("【検出された問題】")
    for issue, count in report["issues"].items():
        print(f"  {issue}: {count}件")
    print()
    print("【冗長パターン検出】")
    for severity, count in report["redundancy_patterns"].items():
        print(f"  {severity}: {count}件")
    print()

    # レポート保存
    REPORTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"content_density_evaluation_{timestamp}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"📄 レポート保存: {report_path}")

    # CSV更新
    if args.execute:
        print()
        print("Step 4: CSVファイル更新中...")

        # 既存カラムを更新または追加
        for col in ["content_density_score", "redundancy_patterns"]:
            if col not in df.columns:
                df[col] = None

        for _, result_row in results_df.iterrows():
            idx = df[df["episode_id"] == result_row["episode_id"]].index
            if len(idx) > 0:
                df.loc[idx[0], "content_density_score"] = result_row["content_density_score"]
                df.loc[idx[0], "redundancy_patterns"] = result_row["redundancy_patterns"]

        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"  ✅ CSV更新完了: {CSV_PATH}")

    print()
    print("🎉 完了!")


# =============================================================================
# 保存前バリデーション関数
# =============================================================================


class ContentDensityValidationError(Exception):
    """内容密度バリデーションエラー"""

    pass


def validate_episode_content_density(
    episode_text: str,
    person_name: str = "",
    age: int = 0,
    min_score: float = 6.0,
    min_char_count: int = 100,
    max_char_count: int = 450,
    max_redundancy: int = 2,
    raise_on_error: bool = False,
) -> dict:
    """
    エピソード保存前のバリデーション

    Args:
        episode_text: エピソード本文
        person_name: 人物名（ログ用）
        age: 年齢（ログ用）
        min_score: 最小許容スコア (default: 6.0)
        min_char_count: 最小文字数 (default: 100)
        max_char_count: 最大文字数 (default: 450)
        max_redundancy: 最大冗長パターン数 (default: 2)
        raise_on_error: エラー時に例外を発生させる

    Returns:
        dict: {
            "valid": bool,
            "score": float,
            "errors": list[str],
            "warnings": list[str],
            "details": dict
        }
    """
    errors = []
    warnings = []

    # 評価実行
    result = calculate_content_density_quality({"episode_text": episode_text})
    score = result["content_density_score"]
    char_count = result["char_count"]
    redundancy_count = result["redundancy"]["total_count"]

    # 文字数チェック
    if char_count < min_char_count:
        errors.append(f"文字数不足: {char_count} < {min_char_count}")
    elif char_count > max_char_count:
        errors.append(f"文字数超過: {char_count} > {max_char_count}")

    # スコアチェック
    if score < min_score:
        errors.append(f"内容密度スコア不足: {score:.2f} < {min_score}")

    # 冗長パターンチェック
    if redundancy_count > max_redundancy:
        errors.append(f"冗長パターン過多: {redundancy_count} > {max_redundancy}")
        if result["redundancy"]["patterns"]:
            for p in result["redundancy"]["patterns"]:
                warnings.append(f"  - {p['severity']}: {p['matches']}")

    # フォーマットチェック
    if not re.match(r"^あなたと同じ\d+歳のとき、", episode_text):
        errors.append("開始形式が不正: 「あなたと同じN歳のとき、」で始まっていない")

    # 低情報密度の警告
    if result["info_density"]["density_ratio"] < 0.5:
        warnings.append(f"情報密度が低い: {result['info_density']['density_ratio']:.2f}")

    is_valid = len(errors) == 0

    validation_result = {
        "valid": is_valid,
        "score": score,
        "char_count": char_count,
        "errors": errors,
        "warnings": warnings,
        "details": {
            "components": result["components"],
            "redundancy": result["redundancy"],
            "info_density": result["info_density"],
        },
    }

    if raise_on_error and not is_valid:
        error_msg = f"バリデーションエラー ({person_name}, {age}歳): " + "; ".join(errors)
        raise ContentDensityValidationError(error_msg)

    return validation_result


def batch_validate_episodes(
    episodes: list[dict],
    min_score: float = 6.0,
) -> dict:
    """
    複数エピソードのバッチバリデーション

    Args:
        episodes: エピソードのリスト (各辞書は episode_text, person_name, age を含む)
        min_score: 最小許容スコア

    Returns:
        dict: {
            "total": int,
            "valid_count": int,
            "invalid_count": int,
            "results": list[dict]
        }
    """
    results = []
    valid_count = 0
    invalid_count = 0

    for ep in episodes:
        validation = validate_episode_content_density(
            episode_text=ep.get("episode_text", ""),
            person_name=ep.get("person_name", ""),
            age=ep.get("age", 0),
            min_score=min_score,
        )

        results.append(
            {
                "person_name": ep.get("person_name", ""),
                "age": ep.get("age", 0),
                "valid": validation["valid"],
                "score": validation["score"],
                "errors": validation["errors"],
            }
        )

        if validation["valid"]:
            valid_count += 1
        else:
            invalid_count += 1

    return {
        "total": len(episodes),
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "valid_rate": round(valid_count / len(episodes) * 100, 2) if episodes else 100.0,
        "results": results,
    }


if __name__ == "__main__":
    main()
