#!/usr/bin/env python3
"""
EPUP (Episode Update Pipeline) 成果評価スクリプト

EPUPシステムの効果を評価し、レポートを生成する。

使用方法:
    python scripts/evaluate_epup_effectiveness.py
    python scripts/evaluate_epup_effectiveness.py --output reports/epup_evaluation.json

評価項目:
1. データ品質メトリクス
2. 違反検出・修正状況
3. 予防措置の有効性
4. 推奨改善事項
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.group_master import GROUP_ENTITIES, GROUP_MEMBER_MAP, SOLO_ARTISTS, is_group_entity


def evaluate_group_master_coverage(df: pd.DataFrame) -> dict:
    """グループマスターのカバレッジを評価"""
    # is_group_member が設定されている割合
    has_group_info = df["is_group_member"].notna() & (df["is_group_member"].astype(str) != "nan")
    group_info_rate = (has_group_info.sum() / len(df)) * 100

    # GROUP_MEMBER_MAP でカバーされている人物
    in_member_map = df["person_name"].isin(GROUP_MEMBER_MAP.keys()).sum()

    # SOLO_ARTISTS でカバーされている人物
    in_solo_artists = df["person_name"].isin(SOLO_ARTISTS).sum()

    # LLM補完候補（未設定かつMAPに未登録）
    not_in_map = ~df["person_name"].isin(GROUP_MEMBER_MAP.keys())
    not_in_solo = ~df["person_name"].isin(SOLO_ARTISTS)
    not_group_entity = ~df["person_name"].isin(GROUP_ENTITIES)
    not_fictional = ~df["person_type"].str.upper().str.contains("FICTIONAL", na=False)
    no_group_info = ~has_group_info

    llm_candidates = df[not_in_map & not_in_solo & not_group_entity & not_fictional & no_group_info]
    unique_llm_candidates = llm_candidates["person_name"].nunique()

    return {
        "total_episodes": len(df),
        "group_info_set_rate": round(group_info_rate, 2),
        "in_group_member_map": in_member_map,
        "in_solo_artists": in_solo_artists,
        "llm_complement_candidates": unique_llm_candidates,
    }


def evaluate_group_entity_violations(df: pd.DataFrame) -> dict:
    """GROUP_ENTITIES違反を評価"""
    violations = []
    for idx, row in df.iterrows():
        person_name = str(row.get("person_name", "")).strip()
        if is_group_entity(person_name):
            violations.append(
                {
                    "person_name": person_name,
                    "age": row.get("age"),
                    "category": row.get("category"),
                }
            )

    return {
        "violation_count": len(violations),
        "violation_rate": round((len(violations) / len(df)) * 100, 4) if len(df) > 0 else 0,
        "violations": violations,
    }


def evaluate_group_master_sync(df: pd.DataFrame) -> dict:
    """GROUP_MEMBER_MAPとデータの整合性を評価（新規追加）"""
    import pandas as pd

    sync_violations = []

    # GROUP_MEMBER_MAP に登録されている人物のデータが正しいか確認
    for person_name, expected_group in GROUP_MEMBER_MAP.items():
        matches = df[df["person_name"] == person_name]
        for idx, row in matches.iterrows():
            actual_member = row.get("is_group_member")
            actual_group = row.get("group_name")

            # 不整合チェック
            needs_fix = False
            # is_group_memberは文字列"True"、bool True、float 1.0など様々な形式がありうる
            is_member = str(actual_member).lower() in ("true", "1", "1.0")
            if not is_member:
                needs_fix = True
            if pd.isna(actual_group) or str(actual_group) == "nan" or actual_group != expected_group:
                needs_fix = True

            if needs_fix:
                sync_violations.append(
                    {
                        "person_name": person_name,
                        "expected_group": expected_group,
                        "actual_is_group_member": actual_member,
                        "actual_group_name": actual_group,
                    }
                )

    total_map_entries = len(df[df["person_name"].isin(GROUP_MEMBER_MAP.keys())])
    sync_rate = ((total_map_entries - len(sync_violations)) / total_map_entries * 100) if total_map_entries > 0 else 100

    return {
        "total_map_entries_in_data": total_map_entries,
        "sync_violation_count": len(sync_violations),
        "sync_rate": round(sync_rate, 2),
        "violations": sync_violations[:10],  # サンプル10件
    }


def evaluate_format_compliance(df: pd.DataFrame) -> dict:
    """フォーマット準拠率を評価"""
    import re

    # 正規フォーマット: 「あなたと同じN歳のとき、」で始まる
    valid_pattern = re.compile(r"^あなたと同じ\d+歳のとき、")
    # 代替フォーマット: 「同じN歳のとき、」で始まる
    alternate_pattern = re.compile(r"^同じ\d+歳のとき、")

    # LLM拒否応答パターン（冒頭パターン + 途中のメタ説明パターン）
    refusal_patterns = [
        # 冒頭パターン
        re.compile(r"^申し訳"),
        re.compile(r"^このリクエスト"),
        re.compile(r"^ご質問の"),
        # 途中のメタ説明パターン（Phase 25追加）
        re.compile(r"事実に基づいた.*?エピソードを生成することはできません"),
        re.compile(r"\d+歳時点のエピソードは.*?存在しません"),
        re.compile(r"\d+歳時点のエピソードは未来の出来事"),
        re.compile(r"\d+年生まれのため.*?現在"),
        re.compile(r"現在.*?まだ\d+歳.*?には達していない"),
        # 既存パターン
        re.compile(r"架空の.*エピソードは存在しません"),
        re.compile(r"実在しないため"),
        re.compile(r"このキャラクターは架空"),
    ]

    compliant_count = 0
    refusal_count = 0
    non_compliant = []

    for idx, row in df.iterrows():
        text = str(row.get("episode_text", ""))

        # LLM拒否応答チェック
        is_refusal = any(p.search(text) for p in refusal_patterns)
        if is_refusal:
            refusal_count += 1
            continue

        # フォーマットチェック
        if valid_pattern.match(text) or alternate_pattern.match(text):
            compliant_count += 1
        else:
            non_compliant.append(
                {
                    "person_name": row.get("person_name"),
                    "text_preview": text[:50] + "..." if len(text) > 50 else text,
                }
            )

    total = len(df)
    return {
        "total_episodes": total,
        "compliant_count": compliant_count,
        "compliance_rate": round((compliant_count / total) * 100, 2) if total > 0 else 0,
        "refusal_count": refusal_count,
        "refusal_rate": round((refusal_count / total) * 100, 2) if total > 0 else 0,
        "non_compliant_sample": non_compliant[:5],  # サンプル5件
    }


def evaluate_person_type_distribution(df: pd.DataFrame) -> dict:
    """person_type分布を評価"""
    # REAL/FICTIONAL分布
    type_counts = df["person_type"].str.upper().value_counts().to_dict()

    real_count = sum(v for k, v in type_counts.items() if "REAL" in str(k))
    fictional_count = sum(v for k, v in type_counts.items() if "FICTIONAL" in str(k))
    other_count = len(df) - real_count - fictional_count

    return {
        "real_count": real_count,
        "fictional_count": fictional_count,
        "other_count": other_count,
        "real_rate": round((real_count / len(df)) * 100, 2) if len(df) > 0 else 0,
        "fictional_rate": round((fictional_count / len(df)) * 100, 2) if len(df) > 0 else 0,
    }


def evaluate_age_coverage(df: pd.DataFrame) -> dict:
    """年齢カバレッジを評価"""
    target_ages = list(range(14, 76))  # 14-75歳

    # 年齢が有効な行のみ
    valid_age_df = df[df["age"].notna() & (df["age"] != "")]
    valid_age_df = valid_age_df[pd.to_numeric(valid_age_df["age"], errors="coerce").notna()]

    ages_present = set(valid_age_df["age"].astype(float).astype(int).unique())
    covered_ages = [a for a in target_ages if a in ages_present]
    missing_ages = [a for a in target_ages if a not in ages_present]

    # 年齢ごとのエピソード数
    age_counts = valid_age_df["age"].astype(float).astype(int).value_counts().sort_index()
    low_coverage_ages = [int(age) for age, count in age_counts.items() if count < 3 and 14 <= age <= 75]

    return {
        "target_age_range": "14-75",
        "covered_count": len(covered_ages),
        "missing_count": len(missing_ages),
        "coverage_rate": round((len(covered_ages) / len(target_ages)) * 100, 2),
        "missing_ages": missing_ages[:10],  # 最初の10件
        "low_coverage_ages": low_coverage_ages[:10],  # カバレッジが低い年齢
    }


def evaluate_category_distribution(df: pd.DataFrame) -> dict:
    """カテゴリ分布を評価"""
    category_counts = df["category"].value_counts().to_dict()

    total = len(df)
    category_rates = {k: round((v / total) * 100, 2) for k, v in category_counts.items()}

    return {
        "category_count": len(category_counts),
        "top_categories": dict(list(category_counts.items())[:10]),
        "category_rates": dict(list(category_rates.items())[:10]),
    }


def evaluate_placeholder_detection(df: pd.DataFrame) -> dict:
    """プレースホルダー検出率を評価（Phase 10追加）

    REAL人物のエピソードでプレースホルダーパターンが含まれているかをチェック。
    """
    import re

    # プレースホルダーパターン
    placeholder_patterns = [
        r"独自の視点と情熱を持って",
        r"その後の成功の基盤となる",
        r"周囲からの期待と自身の目標との間で",
        r"決断力と行動力で道を切り開いて",
        r"貴重な経験を積みました",
        r"新しい挑戦に取り組み",
        r"葛藤しながらも",
        r"キャリアの重要な転機を迎えました",
    ]

    # REAL人物のみ対象
    real_df = df[df["person_type"].str.upper().str.contains("REAL", na=False)]

    placeholder_count = 0
    placeholder_episodes = []

    for idx, row in real_df.iterrows():
        text = str(row.get("episode_text", ""))
        matches = sum(1 for p in placeholder_patterns if re.search(p, text))
        if matches >= 2:  # 2つ以上のパターンでプレースホルダー判定
            placeholder_count += 1
            placeholder_episodes.append(
                {
                    "episode_id": row.get("episode_id", ""),
                    "person_name": row.get("person_name", ""),
                    "pattern_count": matches,
                }
            )

    clean_rate = round(((len(real_df) - placeholder_count) / len(real_df)) * 100, 2) if len(real_df) > 0 else 100.0

    return {
        "total_real_episodes": len(real_df),
        "placeholder_count": placeholder_count,
        "clean_rate": clean_rate,
        "placeholder_samples": placeholder_episodes[:5],
    }


def evaluate_fact_density_quality(df: pd.DataFrame) -> dict:
    """事実密度品質を評価（Phase 10追加）

    低事実密度エピソードの割合を評価。
    """
    # 事実密度列が存在するか確認
    if "事実密度" not in df.columns:
        return {
            "has_fact_density_column": False,
            "total_with_score": 0,
            "low_density_count": 0,
            "average_density": 0,
        }

    # 数値変換
    df_with_score = df[df["事実密度"].notna()]
    df_with_score = df_with_score.copy()
    df_with_score["fact_density_float"] = pd.to_numeric(df_with_score["事実密度"], errors="coerce")
    df_valid = df_with_score[df_with_score["fact_density_float"].notna()]

    # REAL人物のみ
    real_valid = df_valid[df_valid["person_type"].str.upper().str.contains("REAL", na=False)]

    # 低事実密度（3.5以下）
    low_density = real_valid[real_valid["fact_density_float"] <= 3.5]

    average_density = round(real_valid["fact_density_float"].mean(), 2) if len(real_valid) > 0 else 0
    high_quality_rate = (
        round(((len(real_valid) - len(low_density)) / len(real_valid)) * 100, 2) if len(real_valid) > 0 else 100.0
    )

    return {
        "has_fact_density_column": True,
        "total_with_score": len(df_valid),
        "real_with_score": len(real_valid),
        "low_density_count": len(low_density),
        "low_density_rate": round((len(low_density) / len(real_valid)) * 100, 2) if len(real_valid) > 0 else 0,
        "high_quality_rate": high_quality_rate,
        "average_density": average_density,
    }


def evaluate_fictional_work_title_compliance(df: pd.DataFrame) -> dict:
    """架空キャラクター作品名準拠率を評価

    EPUP新機能: 架空キャラクターのエピソードでwork_titleが設定されている場合、
    リード文（冒頭100文字）に『作品名』が含まれているかをチェック。

    正しい例: 「あなたと同じ10歳のとき、ナミ『ONE PIECE』は〜」
    問題例: 「あなたと同じ10歳のとき、ナミは〜」（作品名欠落）
    """
    # 架空キャラクターを抽出
    fictional = df[df["person_type"].str.upper().str.contains("FICTIONAL", na=False)]

    # 作品名が設定されているものを抽出
    with_title = fictional[
        (fictional["work_title"].notna())
        & (fictional["work_title"].astype(str) != "nan")
        & (fictional["work_title"].astype(str).str.strip() != "")
    ]

    if len(with_title) == 0:
        return {
            "total_fictional": len(fictional),
            "with_work_title": 0,
            "compliant": 0,
            "non_compliant": 0,
            "compliance_rate": 100.0,
            "non_compliant_samples": [],
        }

    compliant = 0
    non_compliant_list = []

    for idx, row in with_title.iterrows():
        work_title = str(row["work_title"])
        episode_text = str(row.get("episode_text", ""))
        person_name = row.get("person_name", "")

        # リード文（冒頭100文字）に作品名があるか
        lead = episode_text[:100]
        expected = f"『{work_title}』"

        if expected in lead:
            compliant += 1
        else:
            non_compliant_list.append(
                {
                    "person_name": person_name,
                    "work_title": work_title,
                    "lead_preview": lead[:60] + "..." if len(lead) > 60 else lead,
                }
            )

    compliance_rate = round((compliant / len(with_title)) * 100, 2) if len(with_title) > 0 else 100.0

    return {
        "total_fictional": len(fictional),
        "with_work_title": len(with_title),
        "compliant": compliant,
        "non_compliant": len(non_compliant_list),
        "compliance_rate": compliance_rate,
        "non_compliant_samples": non_compliant_list[:5],  # サンプル5件
    }


def evaluate_episode_type_validity(df: pd.DataFrame) -> dict:
    """episode_typeの妥当性を評価（Phase 11追加）

    ACHIEVEMENTラベルが適切かどうかをキーワード分析でチェック。
    達成キーワードがなく困難キーワードがある場合は「疑わしい」と判定。
    """
    # 達成キーワード（明確な成功を示す）
    achievement_keywords = ["達成", "成功", "獲得", "受賞", "優勝", "完成", "実現", "勝利", "突破", "制覇"]
    # 困難キーワード（過程・試練を示す）
    struggle_keywords = ["困難", "迷い", "不安", "葛藤", "挫折", "苦悩", "模索", "試行錯誤"]

    # episode_type分布
    type_counts = df["episode_type"].value_counts().to_dict()

    # ACHIEVEMENT判定の妥当性チェック
    achievement_eps = df[df["episode_type"] == "ACHIEVEMENT"]
    suspicious_list = []

    for idx, row in achievement_eps.iterrows():
        text = str(row.get("episode_text", ""))
        has_achievement = any(kw in text for kw in achievement_keywords)
        has_struggle = any(kw in text for kw in struggle_keywords)

        # 達成キーワードなし、かつ困難キーワードあり = 疑わしい
        if not has_achievement and has_struggle:
            suspicious_list.append(
                {
                    "episode_id": row.get("episode_id", ""),
                    "person_name": row.get("person_name", ""),
                }
            )

    total_achievement = len(achievement_eps)
    suspicious_count = len(suspicious_list)
    validity_rate = (
        round((total_achievement - suspicious_count) / total_achievement * 100, 2) if total_achievement > 0 else 100.0
    )

    # ACHIEVEMENT率（全体に占める割合）
    achievement_rate = round(total_achievement / len(df) * 100, 2) if len(df) > 0 else 0

    return {
        "episode_type_distribution": type_counts,
        "total_achievement": total_achievement,
        "achievement_rate": achievement_rate,
        "suspicious_achievement_count": suspicious_count,
        "achievement_validity_rate": validity_rate,
        "suspicious_samples": suspicious_list[:5],
    }


def evaluate_yumeilist_coverage(df: pd.DataFrame) -> dict:
    """yumeilistカバレッジを評価（Phase 12追加）

    yumeilist251128.csvに登録されている有名人のうち、
    DBにどれだけカバーされているかを評価する。
    """
    yumeilist_path = project_root / "yumeilist251128.csv"

    if not yumeilist_path.exists():
        return {
            "yumeilist_exists": False,
            "total_yumeilist": 0,
            "covered": 0,
            "missing": 0,
            "coverage_rate": 100.0,
            "missing_samples": [],
        }

    try:
        yumeilist = pd.read_csv(yumeilist_path, encoding="utf-8-sig", on_bad_lines="skip")
    except Exception:
        return {
            "yumeilist_exists": False,
            "total_yumeilist": 0,
            "covered": 0,
            "missing": 0,
            "coverage_rate": 100.0,
            "missing_samples": [],
        }

    db_persons = set(df["person_name"].unique())
    covered = 0
    missing_list = []

    for _, row in yumeilist.iterrows():
        name = str(row.get("person_name", "")).strip()
        if not name or name == "nan":
            continue

        # 名前本体とエイリアス両方でチェック
        found = False
        if name in db_persons:
            found = True
        else:
            # 前方一致チェック（作品名やメンバー名が付加されているケース）
            for db_name in db_persons:
                if db_name.startswith(name):
                    found = True
                    break

        if not found:
            # エイリアスをチェック
            aliases = str(row.get("aliases", "")).strip()
            if aliases and aliases != "nan":
                for alias in aliases.split(";"):
                    alias = alias.strip()
                    if not alias:
                        continue
                    if alias in db_persons:
                        found = True
                        break
                    # エイリアスの前方一致も
                    for db_name in db_persons:
                        if db_name.startswith(alias):
                            found = True
                            break
                    if found:
                        break

        if found:
            covered += 1
        else:
            missing_list.append(
                {
                    "person_name": name,
                    "category": row.get("category", ""),
                    "tier": row.get("tier", 3),
                }
            )

    total = covered + len(missing_list)
    coverage_rate = round(covered / total * 100, 2) if total > 0 else 100.0

    # Tier1の不足を優先表示
    missing_sorted = sorted(missing_list, key=lambda x: (x.get("tier", 3), x.get("person_name", "")))

    return {
        "yumeilist_exists": True,
        "total_yumeilist": total,
        "covered": covered,
        "missing": len(missing_list),
        "coverage_rate": coverage_rate,
        "missing_samples": missing_sorted[:10],
    }


def evaluate_episode_depth(df: pd.DataFrame) -> dict:
    """エピソード深度を評価（Phase 13追加）

    重要人物のエピソード数が十分かどうかを評価する。
    yumeilistのTier1人物は複数エピソードを持つべき。
    """
    yumeilist_path = project_root / "yumeilist251128.csv"

    # 人物あたりのエピソード数
    person_episode_counts = df.groupby("person_name").size()
    avg_episodes = person_episode_counts.mean()
    single_episode_count = (person_episode_counts == 1).sum()
    single_episode_rate = single_episode_count / len(person_episode_counts) * 100

    result = {
        "total_unique_persons": len(person_episode_counts),
        "avg_episodes_per_person": round(avg_episodes, 2),
        "single_episode_count": int(single_episode_count),
        "single_episode_rate": round(single_episode_rate, 2),
        "tier_depth": {},
        "depth_deficient_tier1": [],
        "depth_score": 100.0,
    }

    if not yumeilist_path.exists():
        return result

    try:
        yumeilist = pd.read_csv(yumeilist_path, encoding="utf-8-sig", on_bad_lines="skip")
    except Exception:
        return result

    # Tier別の深度分析
    for tier in [1, 2]:
        tier_persons = yumeilist[yumeilist["tier"] == tier]["person_name"].tolist()
        tier_in_db = [p for p in tier_persons if p in person_episode_counts.index]

        if tier_in_db:
            tier_counts = person_episode_counts[tier_in_db]
            tier_single = (tier_counts == 1).sum()
            result["tier_depth"][f"tier_{tier}"] = {
                "total_persons": len(tier_in_db),
                "avg_episodes": round(tier_counts.mean(), 2),
                "single_episode_count": int(tier_single),
                "multi_episode_rate": round((len(tier_in_db) - tier_single) / len(tier_in_db) * 100, 2),
            }

    # Tier1で深度不足の人物
    tier1_persons = yumeilist[yumeilist["tier"] == 1]["person_name"].tolist()
    depth_deficient = []
    for person in tier1_persons:
        if person in person_episode_counts.index:
            ep_count = int(person_episode_counts[person])
            if ep_count <= 1:
                # 年齢情報も取得
                person_data = df[df["person_name"] == person]
                ages = sorted(person_data["age"].dropna().unique().tolist())
                depth_deficient.append(
                    {
                        "person_name": person,
                        "episode_count": ep_count,
                        "ages": ages,
                    }
                )

    result["depth_deficient_tier1"] = depth_deficient[:20]
    result["depth_deficient_tier1_count"] = len(depth_deficient)

    # 深度スコア計算（Tier1の複数エピソード率）
    tier1_data = result["tier_depth"].get("tier_1", {})
    if tier1_data:
        result["depth_score"] = tier1_data.get("multi_episode_rate", 100.0)

    return result


def generate_recommendations(evaluation: dict) -> list:
    """評価結果に基づく推奨事項を生成"""
    recommendations = []

    # グループ名混入
    if evaluation["group_entity_violations"]["violation_count"] > 0:
        recommendations.append(
            {
                "priority": "HIGH",
                "category": "データ品質",
                "issue": f"グループ名混入 {evaluation['group_entity_violations']['violation_count']}件",
                "action": "scripts/fix_group_in_person_name.py を実行して削除",
            }
        )

    # グループ情報カバレッジ
    if evaluation["group_master_coverage"]["group_info_set_rate"] < 95:
        recommendations.append(
            {
                "priority": "MEDIUM",
                "category": "グループ情報",
                "issue": f"グループ情報設定率 {evaluation['group_master_coverage']['group_info_set_rate']}%",
                "action": "scripts/llm_group_fill.py を実行して補完",
            }
        )

    # GROUP_MEMBER_MAP同期チェック（新規追加）
    if "group_master_sync" in evaluation:
        sync_info = evaluation["group_master_sync"]
        if sync_info["sync_violation_count"] > 0:
            recommendations.append(
                {
                    "priority": "HIGH",
                    "category": "グループ情報同期",
                    "issue": f"GROUP_MEMBER_MAP未反映 {sync_info['sync_violation_count']}件",
                    "action": "scripts/sync_group_from_master.py --execute を実行して同期",
                }
            )

    # フォーマット準拠率
    if evaluation["format_compliance"]["compliance_rate"] < 100:
        recommendations.append(
            {
                "priority": "MEDIUM",
                "category": "フォーマット",
                "issue": f"フォーマット準拠率 {evaluation['format_compliance']['compliance_rate']}%",
                "action": "非準拠エピソードの再生成を検討",
            }
        )

    # LLM拒否応答
    if evaluation["format_compliance"]["refusal_count"] > 0:
        recommendations.append(
            {
                "priority": "HIGH",
                "category": "コンテンツ品質",
                "issue": f"LLM拒否応答 {evaluation['format_compliance']['refusal_count']}件",
                "action": "scripts/fix_fictional_meta_episodes.py を実行して修正",
            }
        )

    # 年齢カバレッジ
    if evaluation["age_coverage"]["coverage_rate"] < 100:
        recommendations.append(
            {
                "priority": "LOW",
                "category": "カバレッジ",
                "issue": f"年齢カバレッジ {evaluation['age_coverage']['coverage_rate']}%",
                "action": f"不足年齢のエピソード生成: {evaluation['age_coverage']['missing_ages'][:5]}",
            }
        )

    # 架空キャラクター作品名準拠率
    if "fictional_work_title_compliance" in evaluation:
        fwt = evaluation["fictional_work_title_compliance"]
        if fwt["non_compliant"] > 0:
            recommendations.append(
                {
                    "priority": "HIGH",
                    "category": "作品名フォーマット",
                    "issue": f"作品名欠落 {fwt['non_compliant']}件 (準拠率 {fwt['compliance_rate']}%)",
                    "action": "scripts/fix_fictional_work_title_format.py --fix を実行して修正",
                }
            )

    # Phase 10: プレースホルダー
    if "placeholder_detection" in evaluation:
        pd_info = evaluation["placeholder_detection"]
        if pd_info["placeholder_count"] > 0:
            recommendations.append(
                {
                    "priority": "HIGH",
                    "category": "事実性",
                    "issue": f"プレースホルダー {pd_info['placeholder_count']}件 (クリーン率 {pd_info['clean_rate']}%)",
                    "action": "scripts/fix_placeholders_with_llm.py --execute を実行して修正",
                }
            )

    # Phase 10: 事実密度
    if "fact_density_quality" in evaluation:
        fd_info = evaluation["fact_density_quality"]
        if fd_info.get("low_density_count", 0) > 50:
            recommendations.append(
                {
                    "priority": "MEDIUM",
                    "category": "事実密度",
                    "issue": f"低事実密度エピソード {fd_info['low_density_count']}件 (平均 {fd_info['average_density']})",
                    "action": "scripts/enhance_fact_density.py --execute を実行して向上",
                }
            )

    # Phase 11: episode_type妥当性
    if "episode_type_validity" in evaluation:
        etv_info = evaluation["episode_type_validity"]
        if etv_info.get("suspicious_achievement_count", 0) > 10:
            recommendations.append(
                {
                    "priority": "HIGH",
                    "category": "ラベル妥当性",
                    "issue": f"疑わしいACHIEVEMENT {etv_info['suspicious_achievement_count']}件 (妥当性 {etv_info['achievement_validity_rate']}%)",
                    "action": "scripts/reclassify_suspicious_achievement.py --execute を実行して再分類",
                }
            )

    # Phase 12: yumeilistカバレッジ
    if "yumeilist_coverage" in evaluation:
        yl_info = evaluation["yumeilist_coverage"]
        if yl_info.get("yumeilist_exists") and yl_info.get("coverage_rate", 100) < 90:
            missing_names = [m["person_name"] for m in yl_info.get("missing_samples", [])[:5]]
            recommendations.append(
                {
                    "priority": "HIGH" if yl_info["coverage_rate"] < 70 else "MEDIUM",
                    "category": "有名人カバレッジ",
                    "issue": f"yumeilistカバレッジ {yl_info['coverage_rate']}% ({yl_info['covered']}/{yl_info['total_yumeilist']})",
                    "action": f"scripts/import_from_yumeilist.py --execute で不足補完。例: {missing_names}",
                }
            )

    # Phase 13: エピソード深度
    if "episode_depth" in evaluation:
        ed_info = evaluation["episode_depth"]
        tier1_deficient = ed_info.get("depth_deficient_tier1_count", 0)
        if tier1_deficient > 10:
            deficient_names = [d["person_name"] for d in ed_info.get("depth_deficient_tier1", [])[:5]]
            recommendations.append(
                {
                    "priority": "HIGH" if tier1_deficient > 30 else "MEDIUM",
                    "category": "エピソード深度",
                    "issue": f"Tier1重要人物でエピソード1件以下: {tier1_deficient}人 (深度スコア {ed_info['depth_score']}%)",
                    "action": f"scripts/expand_episode_depth.py --tier 1 --execute で追加生成。例: {deficient_names}",
                }
            )

    if not recommendations:
        recommendations.append(
            {
                "priority": "INFO",
                "category": "総合",
                "issue": "重大な問題なし",
                "action": "定期的なモニタリングを継続",
            }
        )

    return recommendations


def calculate_epup_score(evaluation: dict) -> dict:
    """EPUP総合スコアを計算"""
    # 各指標のスコア（100点満点）
    scores = {}

    # グループ名混入 (0件=100点)
    violation_count = evaluation["group_entity_violations"]["violation_count"]
    scores["group_entity_clean"] = 100 if violation_count == 0 else max(0, 100 - violation_count * 10)

    # グループ情報設定率
    scores["group_info_coverage"] = evaluation["group_master_coverage"]["group_info_set_rate"]

    # GROUP_MEMBER_MAP同期率（新規追加）
    if "group_master_sync" in evaluation:
        scores["group_master_sync"] = evaluation["group_master_sync"]["sync_rate"]
    else:
        scores["group_master_sync"] = 100.0

    # フォーマット準拠率
    scores["format_compliance"] = evaluation["format_compliance"]["compliance_rate"]

    # LLM拒否なし率
    refusal_rate = evaluation["format_compliance"]["refusal_rate"]
    scores["no_refusal"] = 100 - refusal_rate

    # 年齢カバレッジ
    scores["age_coverage"] = evaluation["age_coverage"]["coverage_rate"]

    # 作品名準拠率（架空キャラクター）
    if "fictional_work_title_compliance" in evaluation:
        fwt = evaluation["fictional_work_title_compliance"]
        scores["work_title_compliance"] = fwt["compliance_rate"]
    else:
        scores["work_title_compliance"] = 100.0

    # Phase 10: プレースホルダークリーン率
    if "placeholder_detection" in evaluation:
        scores["placeholder_clean"] = evaluation["placeholder_detection"]["clean_rate"]
    else:
        scores["placeholder_clean"] = 100.0

    # Phase 10: 事実密度品質
    if "fact_density_quality" in evaluation:
        scores["fact_density_quality"] = evaluation["fact_density_quality"]["high_quality_rate"]
    else:
        scores["fact_density_quality"] = 100.0

    # Phase 11: episode_type妥当性
    if "episode_type_validity" in evaluation:
        scores["episode_type_validity"] = evaluation["episode_type_validity"]["achievement_validity_rate"]
    else:
        scores["episode_type_validity"] = 100.0

    # Phase 12: yumeilistカバレッジ
    if "yumeilist_coverage" in evaluation and evaluation["yumeilist_coverage"].get("yumeilist_exists"):
        scores["yumeilist_coverage"] = evaluation["yumeilist_coverage"]["coverage_rate"]
    else:
        scores["yumeilist_coverage"] = 100.0  # yumeilistがない場合は100とする

    # Phase 13: エピソード深度
    if "episode_depth" in evaluation:
        scores["episode_depth"] = evaluation["episode_depth"]["depth_score"]
    else:
        scores["episode_depth"] = 100.0

    # 総合スコア（重み付け平均）
    weights = {
        "group_entity_clean": 0.06,
        "group_info_coverage": 0.06,
        "group_master_sync": 0.06,
        "format_compliance": 0.08,
        "no_refusal": 0.08,
        "age_coverage": 0.06,
        "work_title_compliance": 0.10,
        # Phase 10: 事実性チェック指標
        "placeholder_clean": 0.10,  # プレースホルダークリーン率
        "fact_density_quality": 0.08,  # 事実密度品質
        # Phase 11: ラベル妥当性
        "episode_type_validity": 0.12,  # episode_type妥当性
        # Phase 12: 有名人カバレッジ
        "yumeilist_coverage": 0.10,  # yumeilistカバレッジ
        # Phase 13: エピソード深度
        "episode_depth": 0.10,  # 重要人物のエピソード深度
    }

    total_score = sum(scores[k] * weights[k] for k in weights)

    return {
        "individual_scores": scores,
        "weights": weights,
        "total_score": round(total_score, 2),
        "grade": "A" if total_score >= 90 else "B" if total_score >= 80 else "C" if total_score >= 70 else "D",
    }


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="EPUP成果評価")
    parser.add_argument("--csv", type=str, help="対象CSVファイルパス")
    parser.add_argument("--output", type=str, help="出力JSONファイルパス")
    args = parser.parse_args()

    print("=" * 70)
    print("📊 EPUP (Episode Update Pipeline) 成果評価")
    print("=" * 70)

    # CSVファイルパス
    if args.csv:
        csv_path = Path(args.csv)
    else:
        # 優先順位: preserved/MASTER_EPISODES_CURRENT.csv > preserved/data/MASTER_EPISODES_CURRENT.csv
        csv_path = project_root / "preserved" / "MASTER_EPISODES_CURRENT.csv"
        if not csv_path.exists():
            csv_path = project_root / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"

    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        return 1

    print(f"\n📂 対象ファイル: {csv_path}")

    # CSV読み込み
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    print(f"📋 読み込み完了: {len(df)}件")

    # 各評価を実行
    print("\n🔍 評価実行中...")

    evaluation = {
        "timestamp": datetime.now().isoformat(),
        "source_file": str(csv_path),
        "total_episodes": len(df),
        "group_master_coverage": evaluate_group_master_coverage(df),
        "group_entity_violations": evaluate_group_entity_violations(df),
        "group_master_sync": evaluate_group_master_sync(df),  # 新規追加
        "format_compliance": evaluate_format_compliance(df),
        "person_type_distribution": evaluate_person_type_distribution(df),
        "age_coverage": evaluate_age_coverage(df),
        "category_distribution": evaluate_category_distribution(df),
        "fictional_work_title_compliance": evaluate_fictional_work_title_compliance(df),
        # Phase 10: 事実性チェック指標
        "placeholder_detection": evaluate_placeholder_detection(df),
        "fact_density_quality": evaluate_fact_density_quality(df),
        # Phase 11: episode_type妥当性チェック
        "episode_type_validity": evaluate_episode_type_validity(df),
        # Phase 12: yumeilistカバレッジ
        "yumeilist_coverage": evaluate_yumeilist_coverage(df),
        # Phase 13: エピソード深度
        "episode_depth": evaluate_episode_depth(df),
    }

    # EPUPスコア計算
    evaluation["epup_score"] = calculate_epup_score(evaluation)

    # 推奨事項生成
    evaluation["recommendations"] = generate_recommendations(evaluation)

    # 結果表示
    print("\n" + "=" * 70)
    print("📈 評価結果サマリー")
    print("=" * 70)

    print("\n【EPUPスコア】")
    score = evaluation["epup_score"]
    print(f"  総合スコア: {score['total_score']} / 100 (グレード: {score['grade']})")
    print("  内訳:")
    for k, v in score["individual_scores"].items():
        print(f"    - {k}: {v:.1f}")

    print("\n【グループマスターカバレッジ】")
    gm = evaluation["group_master_coverage"]
    print(f"  グループ情報設定率: {gm['group_info_set_rate']}%")
    print(f"  GROUP_MEMBER_MAP: {gm['in_group_member_map']}件")
    print(f"  SOLO_ARTISTS: {gm['in_solo_artists']}件")
    print(f"  LLM補完候補: {gm['llm_complement_candidates']}人")

    print("\n【GROUP_ENTITIES違反】")
    gv = evaluation["group_entity_violations"]
    print(f"  違反件数: {gv['violation_count']}件 ({gv['violation_rate']}%)")
    if gv["violations"]:
        print(f"  違反例: {[v['person_name'] for v in gv['violations'][:3]]}")

    print("\n【フォーマット準拠】")
    fc = evaluation["format_compliance"]
    print(f"  準拠率: {fc['compliance_rate']}% ({fc['compliant_count']}/{fc['total_episodes']})")
    print(f"  LLM拒否応答: {fc['refusal_count']}件 ({fc['refusal_rate']}%)")

    print("\n【person_type分布】")
    pt = evaluation["person_type_distribution"]
    print(f"  REAL: {pt['real_count']}件 ({pt['real_rate']}%)")
    print(f"  FICTIONAL: {pt['fictional_count']}件 ({pt['fictional_rate']}%)")

    print("\n【年齢カバレッジ】")
    ac = evaluation["age_coverage"]
    print(f"  カバー率: {ac['coverage_rate']}% ({ac['covered_count']}/{ac['covered_count'] + ac['missing_count']})")
    if ac["missing_ages"]:
        print(f"  不足年齢: {ac['missing_ages']}")

    print("\n【架空キャラクター作品名準拠】")
    fwt = evaluation["fictional_work_title_compliance"]
    print(f"  対象: {fwt['with_work_title']}件 (架空キャラ {fwt['total_fictional']}件中)")
    print(f"  準拠率: {fwt['compliance_rate']}% ({fwt['compliant']}/{fwt['with_work_title']})")
    if fwt["non_compliant_samples"]:
        print(
            f"  非準拠例: {[s['person_name'] + '『' + s['work_title'] + '』' for s in fwt['non_compliant_samples'][:3]]}"
        )

    print("\n【Phase 10: 事実性チェック】")
    ph = evaluation["placeholder_detection"]
    print(f"  プレースホルダー: {ph['placeholder_count']}件 (クリーン率 {ph['clean_rate']}%)")
    if ph["placeholder_samples"]:
        print(f"  検出例: {[s['person_name'] for s in ph['placeholder_samples'][:3]]}")

    fd = evaluation["fact_density_quality"]
    if fd.get("has_fact_density_column"):
        print(f"  低事実密度: {fd['low_density_count']}件 (平均 {fd['average_density']})")
        print(f"  高品質率: {fd['high_quality_rate']}%")

    print("\n【Phase 11: episode_type妥当性】")
    etv = evaluation["episode_type_validity"]
    print(f"  ACHIEVEMENT: {etv['total_achievement']}件 ({etv['achievement_rate']}%)")
    print(f"  疑わしいACHIEVEMENT: {etv['suspicious_achievement_count']}件")
    print(f"  妥当性率: {etv['achievement_validity_rate']}%")
    if etv.get("suspicious_samples"):
        print(f"  検出例: {[s['person_name'] for s in etv['suspicious_samples'][:3]]}")

    print("\n【Phase 12: yumeilistカバレッジ】")
    yl = evaluation["yumeilist_coverage"]
    if yl.get("yumeilist_exists"):
        print(f"  カバー率: {yl['coverage_rate']}% ({yl['covered']}/{yl['total_yumeilist']})")
        print(f"  不足人数: {yl['missing']}人")
        if yl.get("missing_samples"):
            missing_preview = [f"{m['person_name']}(Tier{m.get('tier', '?')})" for m in yl["missing_samples"][:5]]
            print(f"  不足例: {missing_preview}")
    else:
        print("  yumeilist251128.csv が存在しません")

    print("\n【Phase 13: エピソード深度】")
    ed = evaluation.get("episode_depth", {})
    if ed:
        print(f"  平均エピソード数/人: {ed.get('avg_episodes_per_person', 'N/A')}")
        print(f"  単一エピソード人物: {ed.get('single_episode_count', 0)}人 ({ed.get('single_episode_rate', 0)}%)")
        tier1_data = ed.get("tier_depth", {}).get("tier_1", {})
        if tier1_data:
            print(
                f"  Tier1深度: 平均{tier1_data.get('avg_episodes', 'N/A')}件, 複数EP率{tier1_data.get('multi_episode_rate', 0)}%"
            )
        deficient_count = ed.get("depth_deficient_tier1_count", 0)
        if deficient_count > 0:
            print(f"  Tier1深度不足: {deficient_count}人")
            deficient_names = [d["person_name"] for d in ed.get("depth_deficient_tier1", [])[:5]]
            print(f"  例: {deficient_names}")

    print("\n【推奨アクション】")
    for rec in evaluation["recommendations"]:
        priority_icon = "🔴" if rec["priority"] == "HIGH" else "🟡" if rec["priority"] == "MEDIUM" else "🟢"
        print(f"  {priority_icon} [{rec['category']}] {rec['issue']}")
        print(f"     → {rec['action']}")

    # レポート保存
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = project_root / "reports" / f"epup_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    output_path.parent.mkdir(exist_ok=True)

    # numpy/pandas型をPython標準型に変換
    def convert_to_serializable(obj):
        import numpy as np

        if isinstance(obj, dict):
            return {k: convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_to_serializable(v) for v in obj]
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        return obj

    evaluation_serializable = convert_to_serializable(evaluation)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(evaluation_serializable, f, ensure_ascii=False, indent=2)

    print(f"\n📄 レポート保存: {output_path}")
    print("\n" + "=" * 70)
    print("✅ 評価完了")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
