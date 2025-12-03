"""
LLMベースのログ分析サービス

Phase 4: EPUP自動分析サイクル

ログパターン検出、根本原因分析、改善提案生成を担当
"""

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import anthropic
from dotenv import load_dotenv

load_dotenv()


# ========================================
# 分析プロンプト定義
# ========================================

ERROR_PATTERN_PROMPT = """あなたはシステムログ分析の専門家です。以下のエラーログを分析し、パターンと根本原因を特定してください。

## 分析対象ログ（直近{count}件のエラー/警告）
```
{logs}
```

## 分析タスク
1. **エラーパターンの検出**: 繰り返し発生しているエラーを特定
2. **根本原因の推定**: 各パターンの根本原因を推定
3. **影響度評価**: ユーザー体験への影響を評価
4. **改善提案**: 具体的な修正アクションを提案

## 出力形式（JSON）
```json
{{
  "patterns": [
    {{
      "id": "PATTERN-001",
      "name": "パターン名",
      "count": 5,
      "severity": "high|medium|low",
      "description": "パターンの説明",
      "sample_messages": ["エラーメッセージ1", "エラーメッセージ2"],
      "root_cause": "推定される根本原因",
      "impact": "ユーザーへの影響",
      "suggestion": "改善提案"
    }}
  ],
  "summary": {{
    "total_errors": 10,
    "unique_patterns": 3,
    "critical_issues": 1,
    "health_score": 85
  }},
  "priority_actions": [
    "最優先で対応すべきアクション1",
    "次に対応すべきアクション2"
  ]
}}
```
"""

IMPROVEMENT_SUGGESTION_PROMPT = """あなたはEPUP（Error Prevention & User Protection）の専門家です。
以下のログ分析結果に基づいて、EPUP 7ステップに沿った改善計画を生成してください。

## 検出されたパターン
{patterns}

## EPUP 7ステップ
1. **根本原因分析**: 問題の真の原因を特定
2. **システム修正**: コード・設定レベルの修正
3. **個別修正**: 影響を受けたデータの修正
4. **類似検索**: 同様の問題がないか検索
5. **一括修正**: 類似問題の一括対応
6. **予防設計**: 再発防止の仕組み構築
7. **継続監視**: モニタリング体制の確立

## 出力形式（JSON）
```json
{{
  "epup_plan": {{
    "root_cause_analysis": {{
      "findings": ["発見事項1", "発見事項2"],
      "confidence": 0.85
    }},
    "system_fix": {{
      "files_to_modify": ["ファイル1", "ファイル2"],
      "changes": ["変更内容1", "変更内容2"]
    }},
    "individual_fix": {{
      "affected_items": 5,
      "fix_approach": "修正アプローチ"
    }},
    "similar_search": {{
      "search_query": "検索クエリ",
      "estimated_matches": 10
    }},
    "batch_fix": {{
      "scope": "影響範囲",
      "automation_possible": true
    }},
    "prevention": {{
      "validation_rules": ["ルール1", "ルール2"],
      "monitoring_triggers": ["トリガー1"]
    }},
    "monitoring": {{
      "metrics": ["監視指標1", "監視指標2"],
      "alert_thresholds": {{"error_rate": 0.05}}
    }}
  }},
  "estimated_effort": "high|medium|low",
  "priority": 1
}}
```
"""

SESSION_ANALYSIS_PROMPT = """あなたはUX分析の専門家です。以下のセッションログを分析し、ユーザー行動パターンと問題点を特定してください。

## セッション情報
- セッションID: {session_id}
- 開始時刻: {start_time}
- ログ件数: {log_count}
- エラー数: {error_count}

## セッションログ
```
{logs}
```

## 分析タスク
1. ユーザーの主な操作フロー
2. 問題が発生した操作
3. エラーが発生した文脈
4. UX改善のための提案

## 出力形式（JSON）
```json
{{
  "user_flow": ["操作1", "操作2", "操作3"],
  "problem_points": [
    {{
      "operation": "問題が発生した操作",
      "error": "エラー内容",
      "context": "発生状況",
      "suggestion": "改善提案"
    }}
  ],
  "ux_score": 75,
  "recommendations": ["推奨事項1", "推奨事項2"]
}}
```
"""


# ========================================
# データクラス
# ========================================


@dataclass
class ErrorPattern:
    """検出されたエラーパターン"""

    id: str
    name: str
    count: int
    severity: str
    description: str
    sample_messages: List[str]
    root_cause: str
    impact: str
    suggestion: str


@dataclass
class AnalysisSummary:
    """分析サマリー"""

    total_errors: int
    unique_patterns: int
    critical_issues: int
    health_score: int


@dataclass
class AnalysisResult:
    """分析結果"""

    patterns: List[ErrorPattern]
    summary: AnalysisSummary
    priority_actions: List[str]
    raw_response: str
    success: bool
    error_message: Optional[str] = None
    analyzed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class EPUPPlan:
    """EPUP改善計画"""

    root_cause_analysis: Dict[str, Any]
    system_fix: Dict[str, Any]
    individual_fix: Dict[str, Any]
    similar_search: Dict[str, Any]
    batch_fix: Dict[str, Any]
    prevention: Dict[str, Any]
    monitoring: Dict[str, Any]
    estimated_effort: str
    priority: int


# ========================================
# ログ分析サービス
# ========================================


class LogAnalyzer:
    """LLMベースのログ分析サービス"""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        """
        初期化

        Args:
            api_key: Anthropic API Key（省略時は環境変数から取得）
            model: 使用するモデル名
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self.client = None
        self.request_count = 0
        self.total_tokens = 0

        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)

    def is_available(self) -> bool:
        """LLM機能が利用可能かチェック"""
        return self.client is not None

    def analyze_error_patterns(self, logs: List[Dict[str, Any]], max_logs: int = 100) -> AnalysisResult:
        """
        エラーパターンを分析

        Args:
            logs: ログエントリのリスト
            max_logs: 分析対象の最大件数

        Returns:
            AnalysisResult: 分析結果
        """
        if not self.is_available():
            return AnalysisResult(
                patterns=[],
                summary=AnalysisSummary(0, 0, 0, 100),
                priority_actions=[],
                raw_response="",
                success=False,
                error_message="LLM API not configured",
            )

        # エラー/警告のみをフィルタ
        error_logs = [log for log in logs if log.get("level") in ("error", "warn")][:max_logs]

        if not error_logs:
            return AnalysisResult(
                patterns=[],
                summary=AnalysisSummary(0, 0, 0, 100),
                priority_actions=["エラーは検出されませんでした"],
                raw_response="",
                success=True,
            )

        # ログをテキスト形式に変換
        log_text = "\n".join(
            f"[{log.get('timestamp', '')}] [{log.get('level', 'log').upper()}] {log.get('message', '')}"
            for log in error_logs
        )

        prompt = ERROR_PATTERN_PROMPT.format(count=len(error_logs), logs=log_text)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )

            self.request_count += 1
            self.total_tokens += response.usage.input_tokens + response.usage.output_tokens

            raw_text = response.content[0].text
            return self._parse_pattern_response(raw_text)

        except anthropic.RateLimitError:
            return AnalysisResult(
                patterns=[],
                summary=AnalysisSummary(0, 0, 0, 0),
                priority_actions=[],
                raw_response="",
                success=False,
                error_message="API rate limit exceeded",
            )
        except Exception as e:
            return AnalysisResult(
                patterns=[],
                summary=AnalysisSummary(0, 0, 0, 0),
                priority_actions=[],
                raw_response="",
                success=False,
                error_message=str(e),
            )

    def _parse_pattern_response(self, raw_text: str) -> AnalysisResult:
        """パターン分析レスポンスをパース"""
        try:
            json_start = raw_text.find("{")
            json_end = raw_text.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                return AnalysisResult(
                    patterns=[],
                    summary=AnalysisSummary(0, 0, 0, 0),
                    priority_actions=[],
                    raw_response=raw_text,
                    success=False,
                    error_message="No JSON found in response",
                )

            json_str = raw_text[json_start:json_end]
            data = json.loads(json_str)

            patterns = [
                ErrorPattern(
                    id=p.get("id", f"PATTERN-{i}"),
                    name=p.get("name", "Unknown"),
                    count=p.get("count", 1),
                    severity=p.get("severity", "medium"),
                    description=p.get("description", ""),
                    sample_messages=p.get("sample_messages", []),
                    root_cause=p.get("root_cause", ""),
                    impact=p.get("impact", ""),
                    suggestion=p.get("suggestion", ""),
                )
                for i, p in enumerate(data.get("patterns", []))
            ]

            summary_data = data.get("summary", {})
            summary = AnalysisSummary(
                total_errors=summary_data.get("total_errors", 0),
                unique_patterns=summary_data.get("unique_patterns", len(patterns)),
                critical_issues=summary_data.get("critical_issues", 0),
                health_score=summary_data.get("health_score", 100),
            )

            return AnalysisResult(
                patterns=patterns,
                summary=summary,
                priority_actions=data.get("priority_actions", []),
                raw_response=raw_text,
                success=True,
            )

        except json.JSONDecodeError as e:
            return AnalysisResult(
                patterns=[],
                summary=AnalysisSummary(0, 0, 0, 0),
                priority_actions=[],
                raw_response=raw_text,
                success=False,
                error_message=f"JSON parse error: {e}",
            )

    def generate_epup_plan(self, patterns: List[ErrorPattern]) -> Optional[EPUPPlan]:
        """
        EPUP改善計画を生成

        Args:
            patterns: 検出されたエラーパターン

        Returns:
            EPUPPlan: 改善計画（失敗時はNone）
        """
        if not self.is_available() or not patterns:
            return None

        patterns_text = "\n".join(
            f"- {p.name}: {p.description} (件数: {p.count}, 重要度: {p.severity})" for p in patterns
        )

        prompt = IMPROVEMENT_SUGGESTION_PROMPT.format(patterns=patterns_text)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )

            self.request_count += 1
            self.total_tokens += response.usage.input_tokens + response.usage.output_tokens

            raw_text = response.content[0].text
            return self._parse_epup_response(raw_text)

        except Exception:
            return None

    def _parse_epup_response(self, raw_text: str) -> Optional[EPUPPlan]:
        """EPUP計画レスポンスをパース"""
        try:
            json_start = raw_text.find("{")
            json_end = raw_text.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                return None

            json_str = raw_text[json_start:json_end]
            data = json.loads(json_str)

            plan_data = data.get("epup_plan", data)

            return EPUPPlan(
                root_cause_analysis=plan_data.get("root_cause_analysis", {}),
                system_fix=plan_data.get("system_fix", {}),
                individual_fix=plan_data.get("individual_fix", {}),
                similar_search=plan_data.get("similar_search", {}),
                batch_fix=plan_data.get("batch_fix", {}),
                prevention=plan_data.get("prevention", {}),
                monitoring=plan_data.get("monitoring", {}),
                estimated_effort=data.get("estimated_effort", "medium"),
                priority=data.get("priority", 1),
            )

        except (json.JSONDecodeError, KeyError):
            return None

    def analyze_session(self, session_id: str, start_time: str, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        セッションを分析

        Args:
            session_id: セッションID
            start_time: 開始時刻
            logs: セッションのログ

        Returns:
            Dict: 分析結果
        """
        if not self.is_available():
            return {"success": False, "error": "LLM API not configured"}

        error_count = sum(1 for log in logs if log.get("level") == "error")

        log_text = "\n".join(
            f"[{log.get('timestamp', '')}] [{log.get('level', 'log').upper()}] {log.get('message', '')}"
            for log in logs[:50]  # 最大50件
        )

        prompt = SESSION_ANALYSIS_PROMPT.format(
            session_id=session_id,
            start_time=start_time,
            log_count=len(logs),
            error_count=error_count,
            logs=log_text,
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            self.request_count += 1
            self.total_tokens += response.usage.input_tokens + response.usage.output_tokens

            raw_text = response.content[0].text

            # JSONパース
            json_start = raw_text.find("{")
            json_end = raw_text.rfind("}") + 1

            if json_start != -1 and json_end > 0:
                data = json.loads(raw_text[json_start:json_end])
                data["success"] = True
                return data

            return {"success": False, "error": "Failed to parse response"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_usage_stats(self) -> Dict[str, Any]:
        """使用統計を取得"""
        return {
            "request_count": self.request_count,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.total_tokens * 0.000003,
            "is_available": self.is_available(),
        }


# グローバルインスタンス
log_analyzer = LogAnalyzer()
