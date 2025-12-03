"""
EPUP自動実行エンジン

Phase 5: 自動EPUPサイクル

エラー検出→分析→改善計画→実行追跡を自動化
"""

import asyncio
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from app.services.log_analyzer import EPUPPlan, ErrorPattern, log_analyzer
from app.services.log_database import log_db


# ========================================
# 定数・Enum
# ========================================


class JobStatus(str, Enum):
    """ジョブステータス"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """ステップステータス"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


EPUP_STEPS = [
    {"id": 1, "name": "root_cause_analysis", "label": "根本原因分析", "icon": "🔍"},
    {"id": 2, "name": "system_fix", "label": "システム修正", "icon": "⚙️"},
    {"id": 3, "name": "individual_fix", "label": "個別修正", "icon": "🔧"},
    {"id": 4, "name": "similar_search", "label": "類似検索", "icon": "🔎"},
    {"id": 5, "name": "batch_fix", "label": "一括修正", "icon": "📦"},
    {"id": 6, "name": "prevention", "label": "予防設計", "icon": "🛡️"},
    {"id": 7, "name": "monitoring", "label": "継続監視", "icon": "📊"},
]


# ========================================
# データクラス
# ========================================


@dataclass
class EPUPStepProgress:
    """EPUPステップ進捗"""

    step_id: int
    step_name: str
    label: str
    icon: str
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_name": self.step_name,
            "label": self.label,
            "icon": self.icon,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "error_message": self.error_message,
        }


@dataclass
class EPUPJob:
    """EPUPジョブ"""

    job_id: str
    status: JobStatus = JobStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    trigger: str = "manual"  # manual, auto, scheduled
    patterns_detected: List[Dict[str, Any]] = field(default_factory=list)
    plan: Optional[Dict[str, Any]] = None
    steps: List[EPUPStepProgress] = field(default_factory=list)
    summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        if not self.steps:
            self.steps = [
                EPUPStepProgress(
                    step_id=s["id"],
                    step_name=s["name"],
                    label=s["label"],
                    icon=s["icon"],
                )
                for s in EPUP_STEPS
            ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "trigger": self.trigger,
            "patterns_detected": self.patterns_detected,
            "plan": self.plan,
            "steps": [s.to_dict() for s in self.steps],
            "summary": self.summary,
            "error_message": self.error_message,
            "progress": self.get_progress(),
        }

    def get_progress(self) -> Dict[str, Any]:
        """進捗率を計算"""
        total = len(self.steps)
        completed = sum(1 for s in self.steps if s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED))
        in_progress = sum(1 for s in self.steps if s.status == StepStatus.IN_PROGRESS)
        failed = sum(1 for s in self.steps if s.status == StepStatus.FAILED)

        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "failed": failed,
            "percentage": round((completed / total) * 100) if total > 0 else 0,
        }


# ========================================
# EPUPエンジン
# ========================================


class EPUPEngine:
    """EPUP自動実行エンジン"""

    def __init__(self):
        self.jobs: Dict[str, EPUPJob] = {}
        self.current_job: Optional[EPUPJob] = None
        self.auto_mode: bool = False
        self.auto_interval: int = 300  # 5分
        self.error_threshold: int = 5  # エラー5件以上で自動トリガー
        self._auto_task: Optional[asyncio.Task] = None
        self._step_handlers: Dict[str, Callable] = {}
        self._subscribers: List[Callable] = []

        # ステップハンドラ登録
        self._register_default_handlers()

    def _register_default_handlers(self):
        """デフォルトステップハンドラを登録"""
        self._step_handlers = {
            "root_cause_analysis": self._handle_root_cause_analysis,
            "system_fix": self._handle_system_fix,
            "individual_fix": self._handle_individual_fix,
            "similar_search": self._handle_similar_search,
            "batch_fix": self._handle_batch_fix,
            "prevention": self._handle_prevention,
            "monitoring": self._handle_monitoring,
        }

    # ========================================
    # ジョブ管理
    # ========================================

    def create_job(self, trigger: str = "manual") -> EPUPJob:
        """新しいジョブを作成"""
        job_id = f"EPUP-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        job = EPUPJob(job_id=job_id, trigger=trigger)
        self.jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[EPUPJob]:
        """ジョブを取得"""
        return self.jobs.get(job_id)

    def list_jobs(self, limit: int = 20) -> List[EPUPJob]:
        """ジョブ一覧を取得"""
        sorted_jobs = sorted(self.jobs.values(), key=lambda j: j.created_at, reverse=True)
        return sorted_jobs[:limit]

    def cancel_job(self, job_id: str) -> bool:
        """ジョブをキャンセル"""
        job = self.jobs.get(job_id)
        if job and job.status in (JobStatus.PENDING, JobStatus.RUNNING):
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.utcnow().isoformat()
            self._notify_subscribers(job, "cancelled")
            return True
        return False

    # ========================================
    # EPUP実行
    # ========================================

    async def run_cycle(self, trigger: str = "manual") -> EPUPJob:
        """EPUPサイクルを実行"""
        job = self.create_job(trigger=trigger)
        self.current_job = job

        try:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow().isoformat()
            self._notify_subscribers(job, "started")

            # Step 0: エラーパターン検出
            await self._detect_patterns(job)

            if not job.patterns_detected:
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.utcnow().isoformat()
                job.summary = {
                    "result": "no_issues",
                    "message": "問題となるエラーパターンは検出されませんでした",
                }
                self._notify_subscribers(job, "completed")
                return job

            # Step 0.5: EPUP計画生成
            await self._generate_plan(job)

            if not job.plan:
                job.status = JobStatus.FAILED
                job.completed_at = datetime.utcnow().isoformat()
                job.error_message = "EPUP計画の生成に失敗しました"
                self._notify_subscribers(job, "failed")
                return job

            # Steps 1-7: 各ステップ実行
            for step in job.steps:
                if job.status == JobStatus.CANCELLED:
                    break

                await self._execute_step(job, step)

            # 完了
            if job.status != JobStatus.CANCELLED:
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.utcnow().isoformat()
                job.summary = self._generate_summary(job)
                self._notify_subscribers(job, "completed")

        except Exception as e:
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow().isoformat()
            job.error_message = str(e)
            self._notify_subscribers(job, "failed")

        finally:
            self.current_job = None

        return job

    async def _detect_patterns(self, job: EPUPJob):
        """エラーパターンを検出"""
        # ログDBからエラー/警告を取得
        error_logs, _ = log_db.get_log_entries(level="error", page_size=100)
        warn_logs, _ = log_db.get_log_entries(level="warn", page_size=100)
        logs = error_logs + warn_logs

        if not logs:
            return

        # LLM分析
        result = log_analyzer.analyze_error_patterns(logs, max_logs=100)

        if result.success and result.patterns:
            job.patterns_detected = [asdict(p) for p in result.patterns]

    async def _generate_plan(self, job: EPUPJob):
        """EPUP計画を生成"""
        if not job.patterns_detected:
            return

        # ErrorPatternオブジェクトに変換
        patterns = [
            ErrorPattern(
                id=p.get("id", ""),
                name=p.get("name", ""),
                count=p.get("count", 0),
                severity=p.get("severity", "medium"),
                description=p.get("description", ""),
                sample_messages=p.get("sample_messages", []),
                root_cause=p.get("root_cause", ""),
                impact=p.get("impact", ""),
                suggestion=p.get("suggestion", ""),
            )
            for p in job.patterns_detected
        ]

        plan = log_analyzer.generate_epup_plan(patterns)

        if plan:
            job.plan = asdict(plan)

    async def _execute_step(self, job: EPUPJob, step: EPUPStepProgress):
        """ステップを実行"""
        step.status = StepStatus.IN_PROGRESS
        step.started_at = datetime.utcnow().isoformat()
        self._notify_subscribers(job, "step_started", step.step_name)

        try:
            handler = self._step_handlers.get(step.step_name)
            if handler:
                result = await handler(job, step)
                step.result = result
                step.status = StepStatus.COMPLETED
            else:
                step.status = StepStatus.SKIPPED
                step.result = {"message": "ハンドラ未実装"}

        except Exception as e:
            step.status = StepStatus.FAILED
            step.error_message = str(e)

        finally:
            step.completed_at = datetime.utcnow().isoformat()
            self._notify_subscribers(job, "step_completed", step.step_name)

    # ========================================
    # ステップハンドラ
    # ========================================

    async def _handle_root_cause_analysis(self, job: EPUPJob, step: EPUPStepProgress) -> Dict[str, Any]:
        """根本原因分析"""
        plan_data = job.plan.get("root_cause_analysis", {}) if job.plan else {}

        return {
            "findings": plan_data.get("findings", []),
            "confidence": plan_data.get("confidence", 0),
            "action": "分析結果をレビューしてください",
        }

    async def _handle_system_fix(self, job: EPUPJob, step: EPUPStepProgress) -> Dict[str, Any]:
        """システム修正"""
        plan_data = job.plan.get("system_fix", {}) if job.plan else {}

        return {
            "files_to_modify": plan_data.get("files_to_modify", []),
            "changes": plan_data.get("changes", []),
            "action": "修正対象ファイルを確認してください",
            "auto_fixable": False,  # 自動修正は危険なためデフォルトOFF
        }

    async def _handle_individual_fix(self, job: EPUPJob, step: EPUPStepProgress) -> Dict[str, Any]:
        """個別修正"""
        plan_data = job.plan.get("individual_fix", {}) if job.plan else {}

        return {
            "affected_items": plan_data.get("affected_items", 0),
            "fix_approach": plan_data.get("fix_approach", ""),
            "action": "影響を受けたアイテムを修正してください",
        }

    async def _handle_similar_search(self, job: EPUPJob, step: EPUPStepProgress) -> Dict[str, Any]:
        """類似検索"""
        plan_data = job.plan.get("similar_search", {}) if job.plan else {}

        # 実際に類似ログを検索
        search_query = plan_data.get("search_query", "")
        similar_logs = []

        if search_query:
            all_logs, _ = log_db.get_log_entries(page_size=500)
            similar_logs = [log for log in all_logs if search_query.lower() in log.get("message", "").lower()]

        return {
            "search_query": search_query,
            "estimated_matches": plan_data.get("estimated_matches", 0),
            "actual_matches": len(similar_logs),
            "action": "類似問題が見つかりました" if similar_logs else "類似問題なし",
        }

    async def _handle_batch_fix(self, job: EPUPJob, step: EPUPStepProgress) -> Dict[str, Any]:
        """一括修正"""
        plan_data = job.plan.get("batch_fix", {}) if job.plan else {}

        return {
            "scope": plan_data.get("scope", ""),
            "automation_possible": plan_data.get("automation_possible", False),
            "action": "一括修正の範囲を確認してください",
        }

    async def _handle_prevention(self, job: EPUPJob, step: EPUPStepProgress) -> Dict[str, Any]:
        """予防設計"""
        plan_data = job.plan.get("prevention", {}) if job.plan else {}

        return {
            "validation_rules": plan_data.get("validation_rules", []),
            "monitoring_triggers": plan_data.get("monitoring_triggers", []),
            "action": "予防ルールを実装してください",
        }

    async def _handle_monitoring(self, job: EPUPJob, step: EPUPStepProgress) -> Dict[str, Any]:
        """継続監視"""
        plan_data = job.plan.get("monitoring", {}) if job.plan else {}

        return {
            "metrics": plan_data.get("metrics", []),
            "alert_thresholds": plan_data.get("alert_thresholds", {}),
            "action": "監視設定を確認してください",
            "monitoring_enabled": True,
        }

    def _generate_summary(self, job: EPUPJob) -> Dict[str, Any]:
        """サマリーを生成"""
        progress = job.get_progress()

        return {
            "result": "success" if progress["failed"] == 0 else "partial",
            "patterns_found": len(job.patterns_detected),
            "steps_completed": progress["completed"],
            "steps_failed": progress["failed"],
            "recommendations": [s.result.get("action", "") for s in job.steps if s.result and s.result.get("action")],
        }

    # ========================================
    # 自動モード
    # ========================================

    async def start_auto_mode(self, interval: int = 300, threshold: int = 5):
        """自動モードを開始"""
        self.auto_mode = True
        self.auto_interval = interval
        self.error_threshold = threshold

        if self._auto_task:
            self._auto_task.cancel()

        self._auto_task = asyncio.create_task(self._auto_cycle_loop())

    async def stop_auto_mode(self):
        """自動モードを停止"""
        self.auto_mode = False
        if self._auto_task:
            self._auto_task.cancel()
            self._auto_task = None

    async def _auto_cycle_loop(self):
        """自動サイクルループ"""
        while self.auto_mode:
            try:
                # エラー数をチェック
                stats = log_db.get_stats()
                error_count = stats.get("by_level", {}).get("error", 0)

                if error_count >= self.error_threshold:
                    await self.run_cycle(trigger="auto")

                await asyncio.sleep(self.auto_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[EPUP] Auto cycle error: {e}")
                await asyncio.sleep(60)

    # ========================================
    # イベント通知
    # ========================================

    def subscribe(self, callback: Callable):
        """イベント購読"""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable):
        """イベント購読解除"""
        self._subscribers.remove(callback)

    def _notify_subscribers(self, job: EPUPJob, event: str, step_name: Optional[str] = None):
        """購読者に通知"""
        for callback in self._subscribers:
            try:
                callback({"event": event, "job_id": job.job_id, "step": step_name, "job": job})
            except Exception:
                pass

    # ========================================
    # 統計
    # ========================================

    def get_stats(self) -> Dict[str, Any]:
        """統計を取得"""
        jobs_list = list(self.jobs.values())

        return {
            "total_jobs": len(jobs_list),
            "by_status": {status.value: sum(1 for j in jobs_list if j.status == status) for status in JobStatus},
            "by_trigger": {
                "manual": sum(1 for j in jobs_list if j.trigger == "manual"),
                "auto": sum(1 for j in jobs_list if j.trigger == "auto"),
                "scheduled": sum(1 for j in jobs_list if j.trigger == "scheduled"),
            },
            "auto_mode": self.auto_mode,
            "auto_interval": self.auto_interval,
            "error_threshold": self.error_threshold,
            "current_job_id": self.current_job.job_id if self.current_job else None,
        }


# グローバルインスタンス
epup_engine = EPUPEngine()
