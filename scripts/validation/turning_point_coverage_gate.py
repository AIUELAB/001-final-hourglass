#!/usr/bin/env python3
"""
重要転機カバレッジ品質ゲート

有名人物のエピソードに重要転機が含まれているかをチェックする品質ゲート。
生成パイプラインに組み込んで、転機欠落を検出・警告する。

使用方法:
    from scripts.validation.turning_point_coverage_gate import (
        check_turning_point_coverage,
        get_coverage_report,
    )

    # 単一人物チェック
    result = check_turning_point_coverage("ウラジーミル・プーチン", "政治家", episodes)
    if result["status"] == "FAIL":
        print(f"警告: {result['message']}")

    # 全体レポート
    report = get_coverage_report(all_episodes)
"""

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


# 職種別の必須転機キーワード（最低1つは含まれるべき）
TURNING_POINT_REQUIREMENTS = {
    "政治家": {
        "keywords": ["大統領", "首相", "総理", "主席", "書記長", "総統", "国王", "女王", "皇帝", "当選", "就任"],
        "description": "最高職への就任/当選",
        "severity": "high",  # 高重要度: 必須
    },
    "政治・社会": {  # categoryが「政治・社会」の場合も対応
        "keywords": ["大統領", "首相", "総理", "主席", "書記長", "総統", "国王", "女王", "皇帝", "当選", "就任"],
        "description": "最高職への就任/当選",
        "severity": "high",
    },
    "科学者": {
        "keywords": ["ノーベル", "発見", "発明", "理論", "証明", "受賞"],
        "description": "ノーベル賞/代表的発見",
        "severity": "high",
    },
    "科学・技術": {
        "keywords": ["ノーベル", "発見", "発明", "理論", "証明", "受賞"],
        "description": "ノーベル賞/代表的発見",
        "severity": "high",
    },
    "アスリート": {
        "keywords": ["金メダル", "オリンピック", "世界記録", "世界選手権", "優勝", "制覇", "MVP"],
        "description": "五輪/世界大会優勝、世界記録",
        "severity": "medium",  # 中重要度: 推奨
    },
    "スポーツ": {
        "keywords": ["金メダル", "オリンピック", "世界記録", "世界選手権", "優勝", "制覇", "MVP"],
        "description": "五輪/世界大会優勝、世界記録",
        "severity": "medium",
    },
    "映画監督": {
        "keywords": ["アカデミー賞", "カンヌ", "パルム・ドール", "金獅子", "ベルリン", "代表作"],
        "description": "世界的受賞/代表作発表",
        "severity": "medium",
    },
    "芸術・文化": {
        "keywords": ["アカデミー賞", "カンヌ", "パルム・ドール", "金獅子", "芥川賞", "直木賞", "代表作"],
        "description": "主要賞/代表作発表",
        "severity": "medium",
    },
    "作家": {
        "keywords": ["ノーベル文学賞", "芥川賞", "直木賞", "ベストセラー", "代表作"],
        "description": "文学賞/代表作発表",
        "severity": "medium",
    },
    "実業家": {
        "keywords": ["創業", "設立", "上場", "IPO", "CEO"],
        "description": "会社創業/上場",
        "severity": "medium",
    },
    "ビジネス": {
        "keywords": ["創業", "設立", "上場", "IPO", "CEO"],
        "description": "会社創業/上場",
        "severity": "medium",
    },
}

# 有名度閾値（この値以上の人物は転機チェック対象）
CELEBRITY_THRESHOLD = 500.0  # celebrity_score_v2


@dataclass
class CoverageResult:
    """カバレッジチェック結果"""

    status: str  # "PASS", "WARN", "FAIL"
    person_name: str
    category: str
    episode_count: int
    covered_keywords: List[str]
    missing_keywords: List[str]
    message: str
    severity: str  # "high", "medium", "low"


def check_turning_point_coverage(
    person_name: str,
    category: str,
    episodes: List[dict],
    celebrity_score: Optional[float] = None,
) -> CoverageResult:
    """
    人物の転機カバレッジをチェック

    Args:
        person_name: 人物名
        category: カテゴリ（職種）
        episodes: その人物のエピソードリスト
        celebrity_score: 有名度スコア（閾値チェック用）

    Returns:
        CoverageResult: チェック結果
    """
    # 有名度が低い場合はスキップ
    if celebrity_score is not None and celebrity_score < CELEBRITY_THRESHOLD:
        return CoverageResult(
            status="SKIP",
            person_name=person_name,
            category=category,
            episode_count=len(episodes),
            covered_keywords=[],
            missing_keywords=[],
            message=f"有名度{celebrity_score:.1f}が閾値{CELEBRITY_THRESHOLD}未満のためスキップ",
            severity="low",
        )

    # カテゴリの要件を取得
    requirements = TURNING_POINT_REQUIREMENTS.get(category)
    if not requirements:
        return CoverageResult(
            status="SKIP",
            person_name=person_name,
            category=category,
            episode_count=len(episodes),
            covered_keywords=[],
            missing_keywords=[],
            message=f"カテゴリ'{category}'に転機要件が定義されていません",
            severity="low",
        )

    # 全エピソードテキストを結合
    all_text = " ".join(ep.get("episode_text", "") for ep in episodes)

    # キーワードチェック
    covered = [kw for kw in requirements["keywords"] if kw in all_text]
    missing = [kw for kw in requirements["keywords"] if kw not in all_text]

    severity = requirements.get("severity", "medium")

    if covered:
        return CoverageResult(
            status="PASS",
            person_name=person_name,
            category=category,
            episode_count=len(episodes),
            covered_keywords=covered,
            missing_keywords=missing,
            message=f"転機カバー: {', '.join(covered)}",
            severity=severity,
        )
    else:
        status = "FAIL" if severity == "high" else "WARN"
        return CoverageResult(
            status=status,
            person_name=person_name,
            category=category,
            episode_count=len(episodes),
            covered_keywords=[],
            missing_keywords=requirements["keywords"],
            message=f"転機未カバー: {requirements['description']}が見つかりません",
            severity=severity,
        )


def get_coverage_report(
    all_episodes: List[dict],
    celebrity_threshold: float = CELEBRITY_THRESHOLD,
) -> dict:
    """
    全エピソードから転機カバレッジレポートを生成

    Returns:
        dict: レポート情報
    """
    # 人物別にグループ化
    person_map = defaultdict(list)
    person_info = {}

    for ep in all_episodes:
        name = ep.get("person_name", "")
        if name:
            person_map[name].append(ep)
            # 最初のエピソードから情報を取得
            if name not in person_info:
                person_info[name] = {
                    "category": ep.get("category", ""),
                    "celebrity_score": float(ep.get("celebrity_score_v2") or 0),
                }

    results = {
        "pass": [],
        "warn": [],
        "fail": [],
        "skip": [],
    }

    for person_name, episodes in person_map.items():
        info = person_info.get(person_name, {})
        result = check_turning_point_coverage(
            person_name=person_name,
            category=info.get("category", ""),
            episodes=episodes,
            celebrity_score=info.get("celebrity_score"),
        )
        results[result.status.lower()].append(result)

    return {
        "total_persons": len(person_map),
        "pass_count": len(results["pass"]),
        "warn_count": len(results["warn"]),
        "fail_count": len(results["fail"]),
        "skip_count": len(results["skip"]),
        "results": results,
    }


def main():
    """CLIエントリポイント"""
    csv_path = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")

    print("=" * 70)
    print("転機カバレッジ品質ゲート")
    print("=" * 70)

    # エピソード読み込み
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        all_episodes = list(reader)

    print(f"総エピソード数: {len(all_episodes)}")

    report = get_coverage_report(all_episodes)

    print(f"\n人物数: {report['total_persons']}")
    print(f"  PASS: {report['pass_count']}")
    print(f"  WARN: {report['warn_count']}")
    print(f"  FAIL: {report['fail_count']}")
    print(f"  SKIP: {report['skip_count']}")

    # FAIL/WARN の詳細
    if report["results"]["fail"]:
        print("\n" + "=" * 70)
        print("【FAIL】転機カバレッジ失敗（高重要度）")
        print("=" * 70)
        for r in report["results"]["fail"][:10]:
            print(f"  {r.person_name} ({r.category}, {r.episode_count}件): {r.message}")

    if report["results"]["warn"]:
        print("\n" + "=" * 70)
        print("【WARN】転機カバレッジ警告（中重要度）")
        print("=" * 70)
        for r in report["results"]["warn"][:10]:
            print(f"  {r.person_name} ({r.category}, {r.episode_count}件): {r.message}")


if __name__ == "__main__":
    main()
