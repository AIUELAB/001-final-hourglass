#!/usr/bin/env python3
"""
英語名から日本語名への変換スクリプト

機能:
1. to_translate.csvから変換対象を読み込む
2. データソース優先順位で日本語名を取得:
   - world_celebrity_master.csv のaliasesマッピング
   - LLM翻訳（Claude API）
3. 変換結果を出力

Usage:
    python scripts/translate_names_to_japanese.py [--dry-run] [--batch-size N]
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))


# ========================================
# 定数
# ========================================

PROJECT_ROOT = Path(__file__).parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
CELEBRITY_MASTER = PROJECT_ROOT / "data" / "world_celebrity_master.csv"
TO_TRANSLATE_CSV = PROJECT_ROOT / "output" / "name_detection" / "to_translate.csv"
OUTPUT_DIR = PROJECT_ROOT / "output" / "name_translation"


# ========================================
# マッピングローダー
# ========================================


def load_celebrity_mapping() -> Dict[str, str]:
    """
    world_celebrity_master.csvからEnglish→Japaneseマッピングを構築

    Returns:
        {英語名: 日本語名} の辞書
    """
    mapping = {}

    if not CELEBRITY_MASTER.exists():
        print(f"⚠️ Celebrity master not found: {CELEBRITY_MASTER}")
        return mapping

    df = pd.read_csv(CELEBRITY_MASTER, encoding="utf-8-sig")

    for _, row in df.iterrows():
        japanese_name = row.get("person_name", "")
        aliases = row.get("aliases", "")

        if pd.isna(japanese_name) or pd.isna(aliases):
            continue

        # aliasesは単一の英語名またはカンマ区切り
        for alias in str(aliases).split(","):
            alias = alias.strip()
            if alias:
                mapping[alias.lower()] = japanese_name

    print(f"📚 Celebrity mappingをロード: {len(mapping)}件")
    return mapping


# ========================================
# 日本人名のローマ字→漢字変換
# ========================================


def romanized_to_kanji_candidates(name: str) -> List[str]:
    """
    日本人名のローマ字表記から漢字候補を生成

    簡易的な変換ルール（実際にはLLMで正確な漢字を取得）

    Args:
        name: ローマ字表記の名前 (e.g., "Kitagawa Keiko")

    Returns:
        漢字候補リスト (e.g., ["北川景子"])
    """
    # 基本的にはLLMに任せるため、ここでは空リストを返す
    return []


# ========================================
# LLM翻訳
# ========================================


def translate_with_llm(names: List[Dict], batch_size: int = 20) -> List[Dict]:
    """
    Claude APIを使用して名前を日本語に翻訳

    Args:
        names: 翻訳対象の名前リスト [{"person_name": str, "name_type": str, "category": str}, ...]
        batch_size: バッチサイズ

    Returns:
        翻訳結果リスト [{"original": str, "japanese": str, "confidence": float, "source": str}, ...]
    """
    import anthropic

    client = anthropic.Anthropic()
    results = []

    # バッチ処理
    for i in range(0, len(names), batch_size):
        batch = names[i : i + batch_size]

        # プロンプト構築
        names_text = "\n".join(
            [
                f"- {n['person_name']} (カテゴリ: {n.get('category', 'N/A')}, タイプ: {n.get('name_type', 'unknown')})"
                for n in batch
            ]
        )

        prompt = f"""以下の人物名を日本語（カタカナまたは漢字）に変換してください。

【変換ルール】
1. romanized_japanese（日本人名のローマ字）: 漢字に変換（例: Kitagawa Keiko → 北川景子）
2. western_name（西洋人名）: カタカナに変換（例: Michael Jackson → マイケル・ジャクソン）
3. 名前の区切りには「・」を使用（例: Steve Jobs → スティーブ・ジョブズ）
4. 既に日本で広く知られている表記がある場合はそれを使用

【対象人物】
{names_text}

【出力形式】
以下のJSON形式で出力してください（他の説明は不要）:
[
  {{"original": "元の名前", "japanese": "日本語名", "confidence": 0.9}},
  ...
]

confidenceは変換の確信度（0.0-1.0）を示します:
- 1.0: 確実（著名人で定着した表記がある）
- 0.8-0.9: 高い確信（一般的な変換ルールに従う）
- 0.5-0.7: 中程度（複数の表記が考えられる）
- 0.5未満: 低い（推測による変換）
"""

        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514", max_tokens=4096, messages=[{"role": "user", "content": prompt}]
            )

            # レスポンス解析
            content = response.content[0].text

            # JSON部分を抽出
            json_match = re.search(r"\[[\s\S]*\]", content)
            if json_match:
                batch_results = json.loads(json_match.group())
                for result in batch_results:
                    result["source"] = "llm"
                results.extend(batch_results)
            else:
                print(f"⚠️ JSON解析失敗: {content[:200]}")

        except Exception as e:
            print(f"❌ LLM翻訳エラー: {e}")
            # エラー時は元の名前をそのまま返す
            for n in batch:
                results.append(
                    {"original": n["person_name"], "japanese": n["person_name"], "confidence": 0.0, "source": "error"}
                )

        # レート制限対策
        if i + batch_size < len(names):
            time.sleep(1)

        print(f"  翻訳進捗: {min(i + batch_size, len(names))}/{len(names)}")

    return results


# ========================================
# メイン処理
# ========================================


class NameTranslator:
    """名前翻訳クラス"""

    def __init__(self):
        self.celebrity_mapping = load_celebrity_mapping()
        self.results: List[Dict] = []

    def translate_all(
        self, to_translate_path: str, dry_run: bool = True, batch_size: int = 20, limit: int = None
    ) -> Dict:
        """
        全ての対象を翻訳

        Args:
            to_translate_path: 翻訳対象CSVパス
            dry_run: ドライランモード（True=実際の変更なし）
            batch_size: LLM翻訳のバッチサイズ
            limit: 処理件数制限

        Returns:
            翻訳結果サマリー
        """
        # 翻訳対象を読み込み
        df = pd.read_csv(to_translate_path, encoding="utf-8-sig")
        print(f"📖 翻訳対象をロード: {len(df)}件")

        if limit:
            df = df.head(limit)
            print(f"  制限適用: {len(df)}件")

        # マッピングで解決できるものを分離
        mapped = []
        needs_llm = []

        for _, row in df.iterrows():
            person_name = row["person_name"]
            name_lower = person_name.lower()

            if name_lower in self.celebrity_mapping:
                mapped.append(
                    {
                        "person_id": row["person_id"],
                        "original": person_name,
                        "japanese": self.celebrity_mapping[name_lower],
                        "confidence": 1.0,
                        "source": "celebrity_master",
                        "name_type": row.get("name_type", "unknown"),
                        "category": row.get("category", ""),
                    }
                )
            else:
                needs_llm.append(
                    {
                        "person_id": row["person_id"],
                        "person_name": person_name,
                        "name_type": row.get("name_type", "unknown"),
                        "category": row.get("category", ""),
                    }
                )

        print(f"📗 マッピングで解決: {len(mapped)}件")
        print(f"🤖 LLM翻訳が必要: {len(needs_llm)}件")

        # マッピング解決済みを結果に追加
        self.results.extend(mapped)

        # LLM翻訳
        if needs_llm and not dry_run:
            print("\n🤖 LLM翻訳を開始...")
            llm_results = translate_with_llm(needs_llm, batch_size)

            # person_idを紐付け
            for i, result in enumerate(llm_results):
                if i < len(needs_llm):
                    result["person_id"] = needs_llm[i]["person_id"]
                    result["name_type"] = needs_llm[i]["name_type"]
                    result["category"] = needs_llm[i]["category"]
                    self.results.append(result)
        elif needs_llm and dry_run:
            print("\n⚠️ ドライランモード: LLM翻訳はスキップ")
            for item in needs_llm:
                self.results.append(
                    {
                        "person_id": item["person_id"],
                        "original": item["person_name"],
                        "japanese": f"[翻訳未実行: {item['person_name']}]",
                        "confidence": 0.0,
                        "source": "dry_run",
                        "name_type": item["name_type"],
                        "category": item["category"],
                    }
                )

        return self._get_summary()

    def _get_summary(self) -> Dict:
        """翻訳結果サマリーを取得"""
        source_counts = {}
        confidence_sum = 0

        for r in self.results:
            source = r.get("source", "unknown")
            source_counts[source] = source_counts.get(source, 0) + 1
            confidence_sum += r.get("confidence", 0)

        avg_confidence = confidence_sum / len(self.results) if self.results else 0

        return {
            "timestamp": datetime.now().isoformat(),
            "total_translated": len(self.results),
            "by_source": source_counts,
            "average_confidence": avg_confidence,
        }

    def export_results(self, output_dir: str):
        """結果をファイルに出力"""
        os.makedirs(output_dir, exist_ok=True)

        # CSV出力
        if self.results:
            df = pd.DataFrame(self.results)
            csv_path = os.path.join(output_dir, "translation_results.csv")
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            print(f"✅ 翻訳結果CSV: {csv_path}")

        # サマリーJSON
        summary = self._get_summary()
        json_path = os.path.join(output_dir, "translation_summary.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"✅ サマリーJSON: {json_path}")


def main():
    parser = argparse.ArgumentParser(description="英語名から日本語名への変換")
    parser.add_argument("--input", default=str(TO_TRANSLATE_CSV), help="翻訳対象CSVファイル")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR), help="出力ディレクトリ")
    parser.add_argument("--dry-run", action="store_true", help="ドライランモード（LLM翻訳をスキップ）")
    parser.add_argument("--execute", action="store_true", help="実際に翻訳を実行")
    parser.add_argument("--batch-size", type=int, default=20, help="LLM翻訳のバッチサイズ")
    parser.add_argument("--limit", type=int, default=None, help="処理件数制限")

    args = parser.parse_args()

    # ドライランがデフォルト
    dry_run = not args.execute

    print("=" * 60)
    print("英語名→日本語名 変換スクリプト")
    print("=" * 60)
    print(f"入力: {args.input}")
    print(f"出力: {args.output_dir}")
    print(f"モード: {'実行' if not dry_run else 'ドライラン'}")
    print(f"バッチサイズ: {args.batch_size}")
    if args.limit:
        print(f"件数制限: {args.limit}")
    print()

    # 入力ファイル確認
    if not Path(args.input).exists():
        print(f"❌ 入力ファイルが見つかりません: {args.input}")
        print("先にdetect_english_names.pyを実行してください")
        sys.exit(1)

    # 翻訳実行
    translator = NameTranslator()
    summary = translator.translate_all(args.input, dry_run=dry_run, batch_size=args.batch_size, limit=args.limit)

    # 結果表示
    print()
    print("=" * 60)
    print("翻訳結果サマリー")
    print("=" * 60)
    print(f"翻訳件数: {summary['total_translated']:,}")
    print(f"平均確信度: {summary['average_confidence']:.2f}")
    print()
    print("ソース別内訳:")
    for source, count in summary["by_source"].items():
        print(f"  - {source}: {count:,}件")

    # サンプル表示
    if translator.results:
        print()
        print("=" * 60)
        print("翻訳サンプル（最初の10件）")
        print("=" * 60)
        for r in translator.results[:10]:
            conf = r.get("confidence", 0)
            print(f"  {r['original']} → {r['japanese']} (確信度: {conf:.1f}, {r['source']})")

    # ファイル出力
    print()
    print("=" * 60)
    print("ファイル出力")
    print("=" * 60)
    translator.export_results(args.output_dir)

    print()
    print("✅ 翻訳完了")

    if dry_run:
        print()
        print("💡 実際に翻訳を実行するには --execute オプションを付けて再実行してください")


if __name__ == "__main__":
    main()
