#!/usr/bin/env python3
"""
LLMを使用したグループ情報補完スクリプト

MAPに登録されていない人物のグループ情報をLLMで判定・補完する。

使用方法:
    # ドライラン（LLM呼び出しなし、対象者リストのみ表示）
    python scripts/llm_group_fill.py --dry-run

    # バッチ実行（デフォルト50件）
    python scripts/llm_group_fill.py --batch-size 50

    # 特定のカテゴリのみ対象
    python scripts/llm_group_fill.py --category "芸人" --batch-size 20

環境変数:
    ANTHROPIC_API_KEY: Anthropic APIキー
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.group_master import GROUP_ENTITIES, GROUP_MEMBER_MAP, SOLO_ARTISTS, get_group_info

# Anthropic API
try:
    import anthropic

    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


# グループ判定プロンプト
GROUP_JUDGMENT_PROMPT = """以下の日本の有名人について、グループ所属を判定してください。

【人物情報】
名前: {person_name}
職業カテゴリ: {category}
エピソード抜粋: {episode_snippet}

【判定基準】
1. **所属 (is_group_member=true)**
   - 音楽バンド/ユニットのメンバー（例: Mr.Children, B'z, サザンオールスターズ）
   - お笑いコンビ/トリオのメンバー（例: ダウンタウン, ナインティナイン）
   - アイドルグループのメンバー（例: 嵐, AKB48, 乃木坂46）
   - YouTubeグループのメンバー（例: Fischer's, 東海オンエア）
   - 解散グループでも、グループ名での認知が高ければ「所属」

2. **無所属 (is_group_member=false)**
   - デビュー時からソロ活動（例: 宇多田ヒカル, 米津玄師）
   - ピン芸人（例: 明石家さんま, 有吉弘行）
   - グループ脱退後ソロ活動が主
   - 俳優、スポーツ選手、政治家、経営者など（通常グループ概念なし）

3. **判定不能 (is_group_member=null)**
   - 情報が不十分で判断できない場合

【出力形式】
以下のJSON形式で出力してください。説明文は不要です。
{{
  "is_group_member": true/false/null,
  "group_name": "グループ名" または null,
  "confidence": 0.0-1.0,
  "reason": "判定理由（20文字以内）"
}}
"""


def get_candidates(df: pd.DataFrame, category_filter: Optional[str] = None) -> pd.DataFrame:
    """
    LLM補完の対象候補を取得

    Args:
        df: データフレーム
        category_filter: カテゴリフィルタ（オプション）

    Returns:
        候補のデータフレーム
    """
    # 既にgroup情報が設定されているものを除外
    has_group = df["group_name"].notna() & (df["group_name"] != "") & (df["group_name"].astype(str) != "nan")
    has_member_flag = df["is_group_member"].notna() & (df["is_group_member"].astype(str) != "nan")

    # 未設定のもの
    candidates = df[~has_group & ~has_member_flag].copy()

    # MAPに登録済みの人物を除外
    candidates = candidates[~candidates["person_name"].isin(GROUP_MEMBER_MAP.keys())]
    candidates = candidates[~candidates["person_name"].isin(SOLO_ARTISTS)]

    # グループ名そのもの（GROUP_ENTITIES）を除外
    # ※ person_name がグループ名の場合は LLM 補完の対象外
    candidates = candidates[~candidates["person_name"].isin(GROUP_ENTITIES)]

    # FICTIONALを除外
    candidates = candidates[~candidates["person_type"].str.upper().str.contains("FICTIONAL", na=False)]

    # カテゴリフィルタ
    if category_filter:
        if "category" in candidates.columns:
            candidates = candidates[candidates["category"].str.contains(category_filter, na=False)]

    # 重複するperson_nameを除外（最初の1件のみ残す）
    candidates = candidates.drop_duplicates(subset=["person_name"], keep="first")

    return candidates


def call_llm(person_name: str, category: str, episode_snippet: str) -> Optional[Dict]:
    """
    LLMを呼び出してグループ情報を判定

    Args:
        person_name: 人物名
        category: カテゴリ
        episode_snippet: エピソード抜粋

    Returns:
        判定結果の辞書 または None
    """
    if not HAS_ANTHROPIC:
        return None

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    client = anthropic.Anthropic(api_key=api_key)

    prompt = GROUP_JUDGMENT_PROMPT.format(
        person_name=person_name,
        category=category or "不明",
        episode_snippet=episode_snippet[:200] if episode_snippet else "なし",
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )

        result_text = response.content[0].text.strip()

        # JSON部分を抽出
        if "{" in result_text and "}" in result_text:
            json_start = result_text.index("{")
            json_end = result_text.rindex("}") + 1
            json_str = result_text[json_start:json_end]
            return json.loads(json_str)

    except json.JSONDecodeError:
        return None
    except Exception as e:
        print(f"  ⚠️ API Error: {e}")
        return None

    return None


def process_batch(
    df: pd.DataFrame,
    candidates: pd.DataFrame,
    batch_size: int,
    dry_run: bool = False,
) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    バッチ処理でLLM補完を実行

    Args:
        df: 元のデータフレーム
        candidates: 候補のデータフレーム
        batch_size: バッチサイズ
        dry_run: ドライランかどうか

    Returns:
        (更新後のデータフレーム, 変更ログ)
    """
    changes = []
    batch = candidates.head(batch_size)

    print(f"\n🔄 バッチ処理開始: {len(batch)}件")

    for i, (idx, row) in enumerate(batch.iterrows(), 1):
        person_name = row["person_name"]
        category = row.get("category", "")
        episode_text = row.get("episode_text", "")

        print(f"  [{i}/{len(batch)}] {person_name}...", end=" ")

        if dry_run:
            print("(ドライラン)")
            continue

        # LLM呼び出し
        result = call_llm(person_name, category, episode_text)

        if result:
            is_member = result.get("is_group_member")
            group_name = result.get("group_name")
            confidence = result.get("confidence", 0)
            reason = result.get("reason", "")

            if confidence >= 0.7:  # 信頼度70%以上のみ適用
                # 同じperson_nameの全行を更新
                mask = df["person_name"] == person_name
                df.loc[mask, "is_group_member"] = is_member
                if is_member and group_name:
                    df.loc[mask, "group_name"] = group_name

                status = f"所属({group_name})" if is_member else "無所属"
                print(f"✅ {status} (信頼度: {confidence:.0%})")

                changes.append(
                    {
                        "person_name": person_name,
                        "is_group_member": is_member,
                        "group_name": group_name,
                        "confidence": confidence,
                        "reason": reason,
                    }
                )
            else:
                print(f"⏭️ 信頼度不足 ({confidence:.0%})")
        else:
            print("❌ 判定失敗")

        # レート制限対策
        time.sleep(0.5)

    return df, changes


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="LLMを使用したグループ情報補完")
    parser.add_argument("--batch-size", type=int, default=50, help="バッチサイズ（デフォルト: 50）")
    parser.add_argument("--category", type=str, help="対象カテゴリフィルタ")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン（LLM呼び出しなし）")
    parser.add_argument("--csv", type=str, help="対象CSVファイルパス")
    args = parser.parse_args()

    # 環境チェック
    if not args.dry_run:
        if not HAS_ANTHROPIC:
            print("❌ anthropicライブラリがインストールされていません")
            print("   pip install anthropic")
            return 1

        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("❌ ANTHROPIC_API_KEYが設定されていません")
            return 1

    # CSVファイルパス
    if args.csv:
        csv_path = Path(args.csv)
    else:
        csv_path = project_root / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"

    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        return 1

    print(f"📂 対象ファイル: {csv_path}")

    # CSV読み込み
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    print(f"📊 読み込み完了: {len(df)}件")

    # 候補取得
    candidates = get_candidates(df, args.category)
    print(f"🎯 LLM補完候補: {len(candidates)}件（ユニーク人物）")

    if len(candidates) == 0:
        print("✅ 補完対象がありません")
        return 0

    # カテゴリ別の内訳
    if "category" in candidates.columns:
        print("\n【カテゴリ別内訳】")
        category_counts = candidates["category"].value_counts().head(10)
        for cat, count in category_counts.items():
            print(f"  {cat}: {count}件")

    # サンプル表示
    print("\n【候補サンプル（先頭10件）】")
    for _, row in candidates.head(10).iterrows():
        cat = row.get("category", "不明")
        print(f"  - {row['person_name']} ({cat})")

    if args.dry_run:
        print("\n💡 実際に補完を実行するには --dry-run を外してください")
        print(f"   python {Path(__file__).name} --batch-size {args.batch_size}")
        return 0

    # バッチ処理
    df, changes = process_batch(df, candidates, args.batch_size, dry_run=False)

    if changes:
        # バックアップ作成
        backup_path = csv_path.with_name(csv_path.stem + f"_backup_llm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        df_original = pd.read_csv(csv_path, encoding="utf-8-sig")
        df_original.to_csv(backup_path, index=False, encoding="utf-8-sig")
        print(f"\n📦 バックアップ: {backup_path}")

        # 保存
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"💾 保存完了: {csv_path}")

        # レポート保存
        report_path = project_root / "reports" / f"llm_group_fill_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.parent.mkdir(exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "batch_size": args.batch_size,
                    "changes_count": len(changes),
                    "changes": changes,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(f"📄 レポート: {report_path}")

        # サマリー
        print(f"\n✅ 補完完了: {len(changes)}件")
        member_count = sum(1 for c in changes if c["is_group_member"])
        solo_count = len(changes) - member_count
        print(f"   所属: {member_count}件, 無所属: {solo_count}件")
    else:
        print("\n⚠️ 補完対象がありませんでした")

    return 0


if __name__ == "__main__":
    sys.exit(main())
