#!/usr/bin/env python3
from __future__ import annotations

"""
EPUP: 架空キャラクター エピソード LLM分類審査システム

11,691件のFICTIONALエピソードを以下のカテゴリに分類:
- canon: 原作で明確に描かれたシーン
- fanon: 原作設定と整合する創作
- invalid: 設定違反（修正または再生成が必要）

使用方法:
    # JSONL生成（Batch API入力）
    python scripts/validation/fictional_episode_llm_classifier.py generate

    # Batch API送信
    python scripts/validation/fictional_episode_llm_classifier.py submit

    # ステータス確認
    python scripts/validation/fictional_episode_llm_classifier.py status --batch-id <batch_id>

    # 結果取得・集計
    python scripts/validation/fictional_episode_llm_classifier.py retrieve --batch-id <batch_id>

    # レポート生成
    python scripts/validation/fictional_episode_llm_classifier.py report

Author: EPUP Classification Team
Date: 2026-01-15
"""

import argparse
import csv
import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

# パス設定
MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = PROJECT_ROOT / "src/reports"
JSONL_OUTPUT = REPORT_DIR / "fictional_llm_classification_input.jsonl"
RESULTS_CSV = REPORT_DIR / "fictional_llm_classification_results.csv"
BATCH_INFO_FILE = REPORT_DIR / "fictional_classification_batch_info.json"

# Anthropic Batch API インポート
try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None  # type: ignore[misc, assignment]


# =============================================================================
# 定数・列挙型
# =============================================================================


class AuthenticityLevel(Enum):
    """真正性レベル"""

    CANON = "canon"  # 原作で明確に描かれたシーン
    FANON = "fanon"  # 原作設定と整合する創作
    INVALID = "invalid"  # 設定違反


class IssueType(Enum):
    """問題タイプ"""

    WORLD_SETTING_VIOLATION = "world_setting_violation"  # 世界観違反
    CHARACTER_SETTING_VIOLATION = "character_setting_violation"  # キャラ設定違反
    REALITY_MIXING = "reality_mixing"  # 現実との混同
    META_EXPRESSION = "meta_expression"  # メタ的表現
    CHARACTER_WORK_CONFUSION = "character_work_confusion"  # キャラと作品の混同


class Fixability(Enum):
    """修正可能性"""

    FIXABLE = "fixable"  # 部分削除・修正で対応可能
    REGENERATE = "regenerate"  # 全文再生成が必要


# =============================================================================
# 審査プロンプト
# =============================================================================

CLASSIFICATION_PROMPT_TEMPLATE = """あなたは架空キャラクターのエピソード品質審査官です。

【キャラクター】{person_name}
【作品】{work_title}
【年齢】{age}歳
【エピソード】
{episode_text}

以下の観点で審査し、JSON形式で回答してください：

## 審査項目

1. **authenticity** (必須): "canon" | "fanon" | "invalid"
   - canon: 原作で明確に描かれたシーン（出典が特定可能）
   - fanon: 原作で描かれていないが、設定と矛盾しない創作
   - invalid: 原作の設定・世界観と矛盾する

2. **confidence**: 0.0-1.0 (判定の確信度)

3. **issues**: 問題点のリスト（該当するもののみ）
   - world_setting_violation: 世界観違反（年号、地名、技術等）
   - character_setting_violation: キャラ設定違反（職業、能力等）
   - reality_mixing: 現実との混同（現実人物、企業等）
   - meta_expression: メタ的表現
   - character_work_confusion: キャラと作品の混同

4. **issue_details**: 具体的な問題箇所の説明（問題がある場合のみ）

5. **fixability**: "fixable" | "regenerate"（問題がある場合のみ）
   - fixable: 部分削除・修正で対応可能
   - regenerate: 全文再生成が必要

## 出力形式（JSON）
{{
  "authenticity": "fanon",
  "confidence": 0.85,
  "issues": ["world_setting_violation"],
  "issue_details": "「2019年」という現代年号が使用されているが、作品は大正時代設定",
  "fixability": "fixable"
}}

問題がない場合の出力例:
{{
  "authenticity": "fanon",
  "confidence": 0.90,
  "issues": [],
  "issue_details": null,
  "fixability": null
}}

JSONのみを出力してください。余計な説明は不要です。"""


# =============================================================================
# データクラス
# =============================================================================


@dataclass
class ClassificationRequest:
    """分類リクエスト"""

    custom_id: str
    episode_id: str
    person_name: str
    work_title: str
    age: float
    episode_text: str


@dataclass
class ClassificationResult:
    """分類結果"""

    episode_id: str
    person_name: str
    work_title: str
    authenticity: str
    confidence: float
    issues: list[str] = field(default_factory=list)
    issue_details: Optional[str] = None
    fixability: Optional[str] = None
    raw_response: Optional[str] = None
    error: Optional[str] = None


# =============================================================================
# LLM分類システム
# =============================================================================


class FictionalEpisodeLLMClassifier:
    """
    架空キャラクターエピソードLLM分類システム

    Anthropic Batch APIを使用して、50%コスト削減で大量分類を実現。
    """

    def __init__(self, master_csv: Path = MASTER_CSV):
        self.master_csv = master_csv
        self._master_df: Optional[pd.DataFrame] = None
        self._client: Optional[Anthropic] = None  # type: ignore[valid-type]

    @property
    def master_df(self) -> pd.DataFrame:
        """マスターデータの遅延読み込み"""
        if self._master_df is None:
            if self.master_csv.exists():
                self._master_df = pd.read_csv(self.master_csv, encoding="utf-8-sig", low_memory=False)
            else:
                self._master_df = pd.DataFrame()
        return self._master_df

    @property
    def client(self) -> Anthropic:  # type: ignore[valid-type]
        """Anthropicクライアント"""
        if self._client is None:
            if Anthropic is None:
                raise ImportError("anthropic package required. Run: pip install anthropic")
            self._client = Anthropic()
        return self._client

    def get_fictional_episodes(self) -> pd.DataFrame:
        """FICTIONALエピソードを取得"""
        df = self.master_df
        if df.empty:
            return pd.DataFrame()

        # FICTIONALのみフィルタ
        fictional_df = df[df["person_type"].str.upper().str.contains("FICTIONAL", na=False)].copy()

        return fictional_df

    def create_classification_request(self, row: dict) -> ClassificationRequest:
        """分類リクエストを作成"""
        episode_id = str(row.get("episode_id", ""))
        person_name = str(row.get("person_name", ""))
        work_title = str(row.get("work_title", "") or "不明")
        age = float(row.get("age", 0) or 0)
        episode_text = str(row.get("episode_text", ""))

        # custom_idを生成（英数字のみ）
        name_hash = hashlib.md5(episode_id.encode()).hexdigest()[:12]
        custom_id = f"clf_{name_hash}"

        return ClassificationRequest(
            custom_id=custom_id,
            episode_id=episode_id,
            person_name=person_name,
            work_title=work_title,
            age=age,
            episode_text=episode_text,
        )

    def create_prompt(self, req: ClassificationRequest) -> str:
        """審査プロンプトを生成"""
        return CLASSIFICATION_PROMPT_TEMPLATE.format(
            person_name=req.person_name,
            work_title=req.work_title,
            age=int(req.age) if req.age else "不明",
            episode_text=req.episode_text,
        )

    def generate_jsonl(
        self,
        output_path: Path = JSONL_OUTPUT,
        limit: int = 0,
        model: str = "claude-3-5-haiku-20241022",
    ) -> int:
        """
        Batch API用JSONLを生成

        Args:
            output_path: 出力先パス
            limit: 処理件数制限（0=無制限）
            model: 使用モデル

        Returns:
            int: 生成されたリクエスト件数
        """
        fictional_df = self.get_fictional_episodes()
        if fictional_df.empty:
            print("No FICTIONAL episodes found")
            return 0

        # 制限適用
        if limit > 0:
            fictional_df = fictional_df.head(limit)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # エピソードIDマッピングを保存
        id_mapping = {}

        with open(output_path, "w", encoding="utf-8") as f:
            for _, row in fictional_df.iterrows():
                req = self.create_classification_request(row.to_dict())
                prompt = self.create_prompt(req)

                # Anthropic Batch API形式
                batch_request = {
                    "custom_id": req.custom_id,
                    "params": {"model": model, "max_tokens": 512, "messages": [{"role": "user", "content": prompt}]},
                }

                f.write(json.dumps(batch_request, ensure_ascii=False) + "\n")
                id_mapping[req.custom_id] = req.episode_id

        # IDマッピングを保存
        mapping_path = output_path.with_suffix(".mapping.json")
        with open(mapping_path, "w", encoding="utf-8") as f:
            json.dump(id_mapping, f, ensure_ascii=False, indent=2)

        count = len(fictional_df)
        print(f"Generated {count} requests to {output_path}")
        print(f"ID mapping saved to {mapping_path}")

        return count

    def submit_batch(
        self,
        jsonl_path: Path = JSONL_OUTPUT,
    ) -> str:
        """
        Batch APIに送信

        Args:
            jsonl_path: JSONL入力ファイル

        Returns:
            str: batch_id
        """
        if not jsonl_path.exists():
            raise FileNotFoundError(f"JSONL file not found: {jsonl_path}")

        # ファイルからリクエストを読み込み
        requests = []
        with open(jsonl_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    requests.append(json.loads(line))

        print(f"Submitting {len(requests)} requests...")

        # Batch APIに送信
        batch = self.client.messages.batches.create(requests=requests)

        # バッチ情報を保存
        batch_info = {
            "batch_id": batch.id,
            "created_at": datetime.now().isoformat(),
            "request_count": len(requests),
            "status": batch.processing_status,
            "jsonl_path": str(jsonl_path),
        }

        with open(BATCH_INFO_FILE, "w", encoding="utf-8") as f:
            json.dump(batch_info, f, ensure_ascii=False, indent=2)

        print(f"Batch submitted: {batch.id}")
        print(f"Status: {batch.processing_status}")
        print(f"Batch info saved to {BATCH_INFO_FILE}")

        return batch.id

    def check_status(self, batch_id: str) -> dict[str, str | int]:
        """
        バッチステータスを確認

        Args:
            batch_id: バッチID

        Returns:
            dict: ステータス情報
        """
        batch = self.client.messages.batches.retrieve(batch_id)

        status: dict[str, str | int] = {
            "batch_id": batch.id,
            "status": batch.processing_status,
        }

        if batch.request_counts:
            counts = batch.request_counts
            status["total"] = getattr(counts, "total", 0) or 0
            status["succeeded"] = counts.succeeded
            status["errored"] = counts.errored
            status["expired"] = counts.expired
            status["canceled"] = counts.canceled
            status["processing"] = counts.processing

        return status

    def retrieve_results(
        self,
        batch_id: str,
        output_csv: Path = RESULTS_CSV,
    ) -> list[ClassificationResult]:
        """
        結果を取得・解析

        Args:
            batch_id: バッチID
            output_csv: 結果CSV出力先

        Returns:
            list[ClassificationResult]: 分類結果リスト
        """
        # IDマッピングを読み込み
        mapping_path = JSONL_OUTPUT.with_suffix(".mapping.json")
        if mapping_path.exists():
            with open(mapping_path, encoding="utf-8") as f:
                id_mapping = json.load(f)
        else:
            id_mapping = {}

        # 結果を取得
        results_iter = self.client.messages.batches.results(batch_id)

        results = []
        for entry in results_iter:
            custom_id = entry.custom_id
            episode_id = id_mapping.get(custom_id, custom_id)

            result = ClassificationResult(
                episode_id=episode_id,
                person_name="",  # 後で補完
                work_title="",
                authenticity="unknown",
                confidence=0.0,
            )

            if entry.result.type == "succeeded":
                # 応答テキストを取得
                message = entry.result.message
                text_content = ""
                for block in message.content:
                    if hasattr(block, "text"):
                        text_content += block.text

                result.raw_response = text_content

                # JSONパース
                try:
                    parsed = json.loads(text_content)
                    result.authenticity = parsed.get("authenticity", "unknown")
                    result.confidence = float(parsed.get("confidence", 0.0))
                    result.issues = parsed.get("issues", [])
                    result.issue_details = parsed.get("issue_details")
                    result.fixability = parsed.get("fixability")
                except json.JSONDecodeError as e:
                    result.error = f"JSON parse error: {e}"
            else:
                result.error = f"Request failed: {entry.result.type}"

            results.append(result)

        # マスターデータから人物名・作品名を補完
        if not self.master_df.empty:
            ep_info = self.master_df.set_index("episode_id")[["person_name", "work_title"]].to_dict(orient="index")  # type: ignore[call-arg]
            for r in results:
                info = ep_info.get(r.episode_id, {})
                if isinstance(info, dict):
                    r.person_name = str(info.get("person_name", ""))
                    r.work_title = str(info.get("work_title", ""))

        # CSVに保存
        self._save_results_csv(results, output_csv)

        return results

    def _save_results_csv(
        self,
        results: list[ClassificationResult],
        output_csv: Path,
    ) -> None:
        """結果をCSVに保存"""
        output_csv.parent.mkdir(parents=True, exist_ok=True)

        with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
            fieldnames = [
                "episode_id",
                "person_name",
                "work_title",
                "authenticity",
                "confidence",
                "issues",
                "issue_details",
                "fixability",
                "error",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for r in results:
                writer.writerow(
                    {
                        "episode_id": r.episode_id,
                        "person_name": r.person_name,
                        "work_title": r.work_title,
                        "authenticity": r.authenticity,
                        "confidence": r.confidence,
                        "issues": "|".join(r.issues) if r.issues else "",
                        "issue_details": r.issue_details or "",
                        "fixability": r.fixability or "",
                        "error": r.error or "",
                    }
                )

        print(f"Results saved to {output_csv}")

    def generate_report(
        self,
        results_csv: Path = RESULTS_CSV,
    ) -> dict:
        """
        分類レポートを生成

        Args:
            results_csv: 結果CSVパス

        Returns:
            dict: レポートデータ
        """
        if not results_csv.exists():
            print(f"Results CSV not found: {results_csv}")
            return {}

        df = pd.read_csv(results_csv, encoding="utf-8-sig")

        # 集計
        total = len(df)

        # authenticity別
        auth_counts = df["authenticity"].value_counts().to_dict()

        # 問題タイプ別
        issue_counts: dict[str, int] = {}
        for issues_str in df["issues"].dropna():
            for issue in str(issues_str).split("|"):
                if issue:
                    issue_counts[issue] = issue_counts.get(issue, 0) + 1

        # fixability別
        fix_counts = df["fixability"].value_counts().to_dict()

        # エラー件数
        error_count = df["error"].notna().sum()

        # 高信頼度の分類
        high_confidence = df[df["confidence"] >= 0.8]

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_episodes": int(total),
            "authenticity_breakdown": {
                "canon": int(auth_counts.get("canon", 0)),
                "fanon": int(auth_counts.get("fanon", 0)),
                "invalid": int(auth_counts.get("invalid", 0)),
                "unknown": int(auth_counts.get("unknown", 0)),
            },
            "issue_type_breakdown": {k: int(v) for k, v in issue_counts.items()},
            "fixability_breakdown": {
                "fixable": int(fix_counts.get("fixable", 0)),
                "regenerate": int(fix_counts.get("regenerate", 0)),
            },
            "high_confidence_count": int(len(high_confidence)),
            "error_count": int(error_count),
            "average_confidence": float(df["confidence"].mean()) if total > 0 else 0.0,
        }

        # invalidエピソードの詳細
        invalid_df = df[df["authenticity"] == "invalid"]
        if not invalid_df.empty:
            report["invalid_episodes"] = invalid_df[
                ["episode_id", "person_name", "work_title", "issues", "issue_details"]
            ].to_dict(orient="records")[:50]  # type: ignore[call-arg, union-attr]

        # レポートを保存
        report_path = REPORT_DIR / "fictional_classification_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\nReport saved to {report_path}")

        return report

    def estimate_cost(self, episode_count: int) -> dict:
        """
        コスト見積もり

        Args:
            episode_count: エピソード件数

        Returns:
            dict: コスト見積もり
        """
        # Haiku料金（Batch API: 50%割引）
        # Input: $0.25/1M tokens (Batch: $0.125/1M)
        # Output: $1.25/1M tokens (Batch: $0.625/1M)

        # 推定トークン数
        avg_input_tokens = 450  # プロンプト + エピソードテキスト
        avg_output_tokens = 80  # JSON応答

        total_input_tokens = episode_count * avg_input_tokens
        total_output_tokens = episode_count * avg_output_tokens

        # Batch API価格（50%割引）
        input_cost = (total_input_tokens / 1_000_000) * 0.125
        output_cost = (total_output_tokens / 1_000_000) * 0.625
        total_cost = input_cost + output_cost

        return {
            "episode_count": episode_count,
            "estimated_input_tokens": total_input_tokens,
            "estimated_output_tokens": total_output_tokens,
            "estimated_cost_usd": round(total_cost, 2),
            "model": "claude-3-5-haiku-20241022",
            "note": "Batch API 50% discount applied",
        }


# =============================================================================
# CLI
# =============================================================================


def print_progress_bar(status: dict[str, str | int]) -> None:
    """進捗バーを表示"""
    total = int(status.get("total", 0))
    succeeded = int(status.get("succeeded", 0))
    errored = int(status.get("errored", 0))
    # processing は取得のみで表示には使用しない

    if total == 0:
        return

    progress = (succeeded + errored) / total
    bar_width = 50
    filled = int(bar_width * progress)

    print("╔════════════════════════════════════════════════════════════════╗")
    print("║           Batch API リアルタイム進捗                           ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()
    print(f"  📦 Batch ID: {status.get('batch_id', 'N/A')}")
    print()
    print(f"  ┌{'─' * (bar_width + 2)}┐")
    print(f"  │ {'█' * filled}{'░' * (bar_width - filled)} │")
    print(f"  └{'─' * (bar_width + 2)}┘")
    print()

    status_text = status.get("status", "unknown")
    status_emoji = "✅" if status_text == "ended" else "⏳"
    print(f"  {status_emoji} ステータス: {status_text}")
    print()
    print("  ┌─────────────────┬─────────────────┬─────────────────┐")
    print("  │    📊 総数      │   ✅ 成功       │   ❌ 失敗       │")
    print("  ├─────────────────┼─────────────────┼─────────────────┤")
    print(f"  │   {total:>6} 件     │   {succeeded:>6} 件     │   {errored:>6} 件     │")
    print("  └─────────────────┴─────────────────┴─────────────────┘")


def print_report_summary(report: dict) -> None:
    """レポートサマリーを表示"""
    print("\n" + "=" * 70)
    print("EPUP: 架空キャラクター エピソード LLM分類レポート")
    print("=" * 70)

    print(f"\n総エピソード数: {report.get('total_episodes', 0)}件")
    print(f"平均確信度: {report.get('average_confidence', 0):.2%}")

    print("\n📊 真正性別内訳:")
    auth = report.get("authenticity_breakdown", {})
    print(f"  - canon (原作準拠):  {auth.get('canon', 0):>6}件")
    print(f"  - fanon (設定整合):  {auth.get('fanon', 0):>6}件")
    print(f"  - invalid (違反):    {auth.get('invalid', 0):>6}件")

    print("\n⚠️ 問題タイプ別:")
    for issue, count in report.get("issue_type_breakdown", {}).items():
        print(f"  - {issue}: {count}件")

    print("\n🔧 修正可能性:")
    fix = report.get("fixability_breakdown", {})
    print(f"  - fixable (修正可): {fix.get('fixable', 0):>6}件")
    print(f"  - regenerate (再生成): {fix.get('regenerate', 0):>6}件")

    if report.get("error_count", 0) > 0:
        print(f"\n❌ エラー: {report.get('error_count')}件")


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="EPUP: 架空キャラクター エピソード LLM分類システム")
    subparsers = parser.add_subparsers(dest="command", help="コマンド")

    # generate: JSONL生成
    gen_parser = subparsers.add_parser("generate", help="Batch API用JSONLを生成")
    gen_parser.add_argument("--limit", type=int, default=0, help="処理件数制限")
    gen_parser.add_argument(
        "--model",
        type=str,
        default="claude-3-5-haiku-20241022",
        help="使用モデル",
    )
    gen_parser.add_argument(
        "--output",
        type=str,
        default=str(JSONL_OUTPUT),
        help="出力先パス",
    )

    # submit: バッチ送信
    submit_parser = subparsers.add_parser("submit", help="Batch APIに送信")
    submit_parser.add_argument(
        "--jsonl",
        type=str,
        default=str(JSONL_OUTPUT),
        help="JSONL入力ファイル",
    )

    # status: ステータス確認
    status_parser = subparsers.add_parser("status", help="バッチステータスを確認")
    status_parser.add_argument("--batch-id", type=str, help="バッチID")

    # retrieve: 結果取得
    retrieve_parser = subparsers.add_parser("retrieve", help="結果を取得・解析")
    retrieve_parser.add_argument("--batch-id", type=str, help="バッチID")
    retrieve_parser.add_argument(
        "--output",
        type=str,
        default=str(RESULTS_CSV),
        help="結果CSV出力先",
    )

    # report: レポート生成
    report_parser = subparsers.add_parser("report", help="分類レポートを生成")
    report_parser.add_argument(
        "--results-csv",
        type=str,
        default=str(RESULTS_CSV),
        help="結果CSVパス",
    )

    # estimate: コスト見積もり
    estimate_parser = subparsers.add_parser("estimate", help="コスト見積もり")
    estimate_parser.add_argument(
        "--count",
        type=int,
        default=0,
        help="エピソード件数（0=全件）",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    classifier = FictionalEpisodeLLMClassifier()

    # コマンド実行
    if args.command == "generate":
        print("=" * 70)
        print("EPUP: JSONL生成")
        print("=" * 70)

        count = classifier.generate_jsonl(
            output_path=Path(args.output),
            limit=args.limit,
            model=args.model,
        )

        # コスト見積もりも表示
        estimate = classifier.estimate_cost(count)
        print(f"\n推定コスト: ${estimate['estimated_cost_usd']:.2f}")

    elif args.command == "submit":
        print("=" * 70)
        print("EPUP: Batch API送信")
        print("=" * 70)

        batch_id = classifier.submit_batch(jsonl_path=Path(args.jsonl))
        print(f"\n送信完了: {batch_id}")
        print(
            "ステータス確認: python scripts/validation/fictional_episode_llm_classifier.py status --batch-id "
            + batch_id
        )

    elif args.command == "status":
        batch_id = args.batch_id

        # バッチIDが指定されていない場合、保存済みの情報から取得
        if not batch_id and BATCH_INFO_FILE.exists():
            with open(BATCH_INFO_FILE, encoding="utf-8") as f:
                batch_info = json.load(f)
            batch_id = batch_info.get("batch_id")

        if not batch_id:
            print("Error: batch_id required. Use --batch-id or run submit first.")
            return 1

        status = classifier.check_status(batch_id)
        print_progress_bar(status)

    elif args.command == "retrieve":
        batch_id = args.batch_id

        # バッチIDが指定されていない場合、保存済みの情報から取得
        if not batch_id and BATCH_INFO_FILE.exists():
            with open(BATCH_INFO_FILE, encoding="utf-8") as f:
                batch_info = json.load(f)
            batch_id = batch_info.get("batch_id")

        if not batch_id:
            print("Error: batch_id required. Use --batch-id or run submit first.")
            return 1

        print("=" * 70)
        print("EPUP: 結果取得")
        print("=" * 70)

        results = classifier.retrieve_results(
            batch_id=batch_id,
            output_csv=Path(args.output),
        )

        print(f"\n取得件数: {len(results)}件")

        # 簡易集計
        auth_counts: dict[str, int] = {}
        for r in results:
            auth_counts[r.authenticity] = auth_counts.get(r.authenticity, 0) + 1

        print("\n真正性別:")
        for auth, count in auth_counts.items():
            print(f"  {auth}: {count}件")

    elif args.command == "report":
        report = classifier.generate_report(
            results_csv=Path(args.results_csv),
        )
        print_report_summary(report)

    elif args.command == "estimate":
        count = args.count
        if count == 0:
            fictional_df = classifier.get_fictional_episodes()
            count = len(fictional_df)

        print("=" * 70)
        print("EPUP: コスト見積もり")
        print("=" * 70)

        estimate = classifier.estimate_cost(count)

        print(f"\n対象エピソード数: {estimate['episode_count']:,}件")
        print(f"推定入力トークン: {estimate['estimated_input_tokens']:,}")
        print(f"推定出力トークン: {estimate['estimated_output_tokens']:,}")
        print(f"使用モデル: {estimate['model']}")
        print(f"\n推定コスト: ${estimate['estimated_cost_usd']:.2f}")
        print(f"({estimate['note']})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
