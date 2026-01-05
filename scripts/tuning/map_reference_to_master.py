#!/usr/bin/env python3
"""
参照ランキングとマスターCSVの突合スクリプト

機能:
    1. 人物名正規化によるマッチング
    2. 年齢一致の確認
    3. マッチング信頼度の評価
    4. 現行超総合ランキングとの比較
"""

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class MappingResult:
    """マッピング結果"""

    ref_rank: int
    ref_person_name: str
    ref_age: int
    ref_source: str
    matched_episode_id: Optional[str]
    matched_person_name: Optional[str]
    matched_age: Optional[int]
    current_super_total: Optional[float]
    current_rank: Optional[int]
    confidence: str  # "high", "medium", "low", "no_match"
    match_reason: str


# 人物名正規化ルール
NAME_ALIASES = {
    "大谷翔平": ["大谷翔平"],
    "イチロー": ["イチロー", "鈴木一朗"],
    "孫正義": ["孫正義"],
    "羽生結弦": ["羽生結弦"],
    "スティーブ・ジョブズ": ["スティーブ・ジョブズ", "スティーブジョブズ", "Steve Jobs"],
    "マーク・ザッカーバーグ": ["マーク・ザッカーバーグ", "マークザッカーバーグ"],
    "本田宗一郎": ["本田宗一郎"],
    "宮崎駿": ["宮崎駿"],
    "坂本龍馬": ["坂本龍馬"],
    "手塚治虫": ["手塚治虫"],
    "織田信長": ["織田信長"],
    "豊臣秀吉": ["豊臣秀吉"],
    "徳川家康": ["徳川家康"],
    "松下幸之助": ["松下幸之助"],
    "黒澤明": ["黒澤明"],
    "藤井聡太": ["藤井聡太"],
    "浅田真央": ["浅田真央"],
    "木村拓哉": ["木村拓哉"],
    "北野武": ["北野武", "ビートたけし"],
    "松井秀喜": ["松井秀喜"],
    "錦織圭": ["錦織圭"],
    "カーネル・サンダース": ["カーネル・サンダース", "カーネルサンダース"],
    "伊能忠敬": ["伊能忠敬"],
    "安藤百福": ["安藤百福"],
    "矢沢永吉": ["矢沢永吉"],
    "J.K.ローリング": ["J.K.ローリング", "JKローリング", "ローリング"],
    "葛飾北斎": ["葛飾北斎"],
    "ジェフ・ベゾス": ["ジェフ・ベゾス", "ジェフベゾス"],
    "ウォルト・ディズニー": ["ウォルト・ディズニー", "ウォルトディズニー"],
    "三木谷浩史": ["三木谷浩史"],
    "マイケル・ジョーダン": ["マイケル・ジョーダン", "マイケルジョーダン"],
    "マザー・テレサ": ["マザー・テレサ", "マザーテレサ"],
    "夏目漱石": ["夏目漱石"],
    "ビル・ゲイツ": ["ビル・ゲイツ", "ビルゲイツ"],
    "中内㓛": ["中内㓛", "中内功"],
    "ココ・シャネル": ["ココ・シャネル", "ココシャネル"],
    "タモリ": ["タモリ"],
    "エイブラハム・リンカーン": ["エイブラハム・リンカーン", "リンカーン"],
    "植村直己": ["植村直己"],
    "出口治明": ["出口治明"],
    "岡本太郎": ["岡本太郎"],
    "田中角栄": ["田中角栄"],
    # 追加
    "アインシュタイン": ["アルベルト・アインシュタイン", "アインシュタイン"],
    "エルヴィス・プレスリー": ["エルヴィス・プレスリー", "エルビスプレスリー"],
    "ジミ・ヘンドリックス": ["ジミ・ヘンドリックス", "ジミヘンドリックス"],
    "バラク・オバマ": ["バラク・オバマ", "オバマ"],
}


def normalize_name(name: str) -> str:
    """人物名を正規化"""
    # 中黒・スペースの統一
    name = name.replace("・", "・").replace(" ", "").strip()
    return name


def find_name_in_master(ref_name: str, master_names: set) -> Optional[str]:
    """参照人物名からマスターCSV内の人物名を検索"""
    normalized_ref = normalize_name(ref_name)

    # 完全一致
    if normalized_ref in master_names:
        return normalized_ref

    # エイリアスチェック
    for canonical, aliases in NAME_ALIASES.items():
        if normalized_ref in [normalize_name(a) for a in aliases]:
            for alias in aliases:
                if normalize_name(alias) in master_names:
                    return normalize_name(alias)

    # 部分一致（最後の手段）
    for master_name in master_names:
        if normalized_ref in master_name or master_name in normalized_ref:
            return master_name

    return None


def map_reference_to_master(ref_episodes: list, df: pd.DataFrame) -> list[MappingResult]:
    """参照エピソードをマスターCSVにマッピング"""
    results = []
    master_names = set(df["person_name"].dropna().unique())

    # 現行ランキング（super_total_scoreでソート）
    df["super_total_score_float"] = pd.to_numeric(df["super_total_score"], errors="coerce")
    df_sorted = df.sort_values("super_total_score_float", ascending=False).reset_index(drop=True)
    df_sorted["current_rank"] = range(1, len(df_sorted) + 1)

    for ref in ref_episodes:
        ref_name = ref["person_name"]
        ref_age = ref["age"]

        matched_name = find_name_in_master(ref_name, master_names)

        if matched_name:
            # マッチしたエピソードを探す
            matched_eps = df_sorted[
                (df_sorted["person_name"] == matched_name)
                & (pd.to_numeric(df_sorted["age"], errors="coerce") == ref_age)
            ]

            if not matched_eps.empty:
                # 年齢一致: 高信頼
                ep = matched_eps.iloc[0]
                results.append(
                    MappingResult(
                        ref_rank=ref["rank"],
                        ref_person_name=ref_name,
                        ref_age=ref_age,
                        ref_source=ref["source"],
                        matched_episode_id=ep["episode_id"],
                        matched_person_name=ep["person_name"],
                        matched_age=int(float(ep["age"])),
                        current_super_total=float(ep["super_total_score_float"])
                        if pd.notna(ep["super_total_score_float"])
                        else None,
                        current_rank=int(ep["current_rank"]),
                        confidence="high",
                        match_reason="人物名+年齢一致",
                    )
                )
            else:
                # 年齢不一致: 同一人物の最上位エピソード
                person_eps = df_sorted[df_sorted["person_name"] == matched_name]
                if not person_eps.empty:
                    ep = person_eps.iloc[0]
                    results.append(
                        MappingResult(
                            ref_rank=ref["rank"],
                            ref_person_name=ref_name,
                            ref_age=ref_age,
                            ref_source=ref["source"],
                            matched_episode_id=ep["episode_id"],
                            matched_person_name=ep["person_name"],
                            matched_age=int(float(ep["age"])) if pd.notna(ep["age"]) else None,
                            current_super_total=float(ep["super_total_score_float"])
                            if pd.notna(ep["super_total_score_float"])
                            else None,
                            current_rank=int(ep["current_rank"]),
                            confidence="medium",
                            match_reason=f"人物名一致（年齢不一致: 参照{ref_age}歳 vs マスター{ep['age']}歳）",
                        )
                    )
        else:
            # マッチなし
            results.append(
                MappingResult(
                    ref_rank=ref["rank"],
                    ref_person_name=ref_name,
                    ref_age=ref_age,
                    ref_source=ref["source"],
                    matched_episode_id=None,
                    matched_person_name=None,
                    matched_age=None,
                    current_super_total=None,
                    current_rank=None,
                    confidence="no_match",
                    match_reason="マスターCSVに該当人物なし",
                )
            )

    return results


def main():
    """メイン処理"""
    # 参照データ読み込み
    ref_path = PROJECT_ROOT / "src/reports/reference_rankings_extracted.json"
    with open(ref_path, encoding="utf-8") as f:
        ref_data = json.load(f)

    print(f"参照データ読み込み: Claude {len(ref_data['claude'])}件, Gemini {len(ref_data['gemini'])}件")

    # マスターCSV読み込み
    csv_path = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
    df = pd.read_csv(csv_path, dtype=str)
    print(f"マスターCSV読み込み: {len(df)}件")

    # マッピング実行
    claude_results = map_reference_to_master(ref_data["claude"], df)
    gemini_results = map_reference_to_master(ref_data["gemini"], df)

    # 統計
    def summarize(results: list[MappingResult], source: str) -> dict:
        high = len([r for r in results if r.confidence == "high"])
        medium = len([r for r in results if r.confidence == "medium"])
        no_match = len([r for r in results if r.confidence == "no_match"])
        return {
            "source": source,
            "total": len(results),
            "high_confidence": high,
            "medium_confidence": medium,
            "no_match": no_match,
            "match_rate": f"{(high + medium) / len(results) * 100:.1f}%",
        }

    claude_summary = summarize(claude_results, "claude")
    gemini_summary = summarize(gemini_results, "gemini")

    print("\n=== Claude マッピング結果 ===")
    print(f"  高信頼: {claude_summary['high_confidence']}")
    print(f"  中信頼: {claude_summary['medium_confidence']}")
    print(f"  マッチなし: {claude_summary['no_match']}")
    print(f"  マッチ率: {claude_summary['match_rate']}")

    print("\n=== Gemini マッピング結果 ===")
    print(f"  高信頼: {gemini_summary['high_confidence']}")
    print(f"  中信頼: {gemini_summary['medium_confidence']}")
    print(f"  マッチなし: {gemini_summary['no_match']}")
    print(f"  マッチ率: {gemini_summary['match_rate']}")

    # マッチなしの一覧
    print("\n=== マッチなし一覧 ===")
    for r in claude_results + gemini_results:
        if r.confidence == "no_match":
            print(f"  [{r.ref_source}] {r.ref_rank}位: {r.ref_person_name}（{r.ref_age}歳）")

    # 結果保存
    output = {
        "claude": [asdict(r) for r in claude_results],
        "gemini": [asdict(r) for r in gemini_results],
        "summary": {
            "claude": claude_summary,
            "gemini": gemini_summary,
        },
    }

    output_path = PROJECT_ROOT / "src/reports/reference_mapping_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n結果を保存: {output_path}")


if __name__ == "__main__":
    main()
