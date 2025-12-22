#!/usr/bin/env python3
"""
SuperClaude Learning System
セッション間での知識蓄積と学習機能
"""

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field

logger = logging.getLogger(__name__)
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Pattern:
    """学習されたパターン"""

    pattern_id: str
    pattern_type: str  # error_fix, optimization, workflow
    context: str
    solution: str
    success_rate: float = 0.0
    usage_count: int = 0
    last_used: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProjectKnowledge:
    """プロジェクト固有の知識"""

    project_path: str
    project_id: str
    conventions: Dict[str, str] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    common_errors: List[Dict[str, Any]] = field(default_factory=list)
    file_patterns: Dict[str, str] = field(default_factory=dict)
    test_commands: List[str] = field(default_factory=list)
    build_commands: List[str] = field(default_factory=list)
    frequent_operations: List[Dict[str, Any]] = field(default_factory=list)
    custom_aliases: Dict[str, str] = field(default_factory=dict)
    last_updated: str = ""


@dataclass
class LearningEntry:
    """学習エントリ"""

    entry_id: str
    timestamp: str
    session_id: str
    entry_type: str  # success, error, optimization
    context: Dict[str, Any]
    action: str
    result: str
    outcome: str  # success, failure, partial
    confidence: float = 0.0
    reusable: bool = False


class LearningSystem:
    """セッション間学習システム"""

    def __init__(self, learning_dir: str = "~/.claude/learning"):
        self.learning_dir = Path(learning_dir).expanduser()
        self.learning_dir.mkdir(parents=True, exist_ok=True)

        # 各種ストレージパス
        self.patterns_dir = self.learning_dir / "patterns"
        self.projects_dir = self.learning_dir / "projects"
        self.entries_dir = self.learning_dir / "entries"
        self.cache_dir = self.learning_dir / "cache"

        for dir_path in [self.patterns_dir, self.projects_dir, self.entries_dir, self.cache_dir]:
            dir_path.mkdir(exist_ok=True)

        # メモリキャッシュ
        self.patterns_cache: Dict[str, Pattern] = {}
        self.projects_cache: Dict[str, ProjectKnowledge] = {}
        self.context_embeddings: Dict[str, Any] = {}

        # 初期化
        self.load_patterns()
        self.load_project_knowledge()

    def load_patterns(self) -> None:
        """保存されたパターンを読み込み"""
        pattern_files = self.patterns_dir.glob("*.json")

        for file_path in pattern_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    pattern = Pattern(**data)
                    self.patterns_cache[pattern.pattern_id] = pattern
            except Exception as e:
                logger.debug(f"パターン読み込みスキップ {file_path}: {e}")
                continue

    def load_project_knowledge(self) -> None:
        """プロジェクト知識を読み込み"""
        project_files = self.projects_dir.glob("*.json")

        for file_path in project_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    knowledge = ProjectKnowledge(**data)
                    self.projects_cache[knowledge.project_id] = knowledge
            except Exception as e:
                logger.debug(f"プロジェクト知識読み込みスキップ {file_path}: {e}")
                continue

    def get_project_id(self, project_path: str) -> str:
        """プロジェクトパスからIDを生成（セキュリティ用途ではない）"""
        return hashlib.md5(project_path.encode(), usedforsecurity=False).hexdigest()[:12]

    def learn_from_success(self, context: Dict[str, Any], action: str, result: str) -> str:
        """成功事例から学習"""
        entry_id = datetime.now().strftime("entry_%Y%m%d_%H%M%S_%f")

        entry = LearningEntry(
            entry_id=entry_id,
            timestamp=datetime.now().isoformat(),
            session_id=context.get("session_id", "unknown"),
            entry_type="success",
            context=context,
            action=action,
            result=result,
            outcome="success",
            confidence=0.9,
            reusable=True,
        )

        # エントリを保存
        self._save_entry(entry)

        # パターンを抽出
        pattern = self._extract_pattern(entry)
        if pattern:
            self._save_pattern(pattern)

        return entry_id

    def learn_from_error(self, context: Dict[str, Any], error: str, solution: Optional[str] = None) -> str:
        """エラーから学習"""
        entry_id = datetime.now().strftime("error_%Y%m%d_%H%M%S_%f")

        entry = LearningEntry(
            entry_id=entry_id,
            timestamp=datetime.now().isoformat(),
            session_id=context.get("session_id", "unknown"),
            entry_type="error",
            context=context,
            action=error,
            result=solution or "unresolved",
            outcome="failure" if not solution else "success",
            confidence=0.7 if solution else 0.3,
            reusable=bool(solution),
        )

        # エントリを保存
        self._save_entry(entry)

        # プロジェクトのエラーリストを更新
        if "project_path" in context:
            self._update_project_errors(context["project_path"], error, solution)

        return entry_id

    def learn_project_convention(self, project_path: str, convention_type: str, value: str) -> None:
        """プロジェクトの規約を学習"""
        project_id = self.get_project_id(project_path)

        if project_id not in self.projects_cache:
            self.projects_cache[project_id] = ProjectKnowledge(
                project_path=project_path, project_id=project_id, last_updated=datetime.now().isoformat()
            )

        knowledge = self.projects_cache[project_id]
        knowledge.conventions[convention_type] = value
        knowledge.last_updated = datetime.now().isoformat()

        self._save_project_knowledge(knowledge)

    def learn_frequent_operation(self, project_path: str, operation: Dict[str, Any]) -> None:
        """頻繁な操作を学習"""
        project_id = self.get_project_id(project_path)

        if project_id not in self.projects_cache:
            self.projects_cache[project_id] = ProjectKnowledge(
                project_path=project_path, project_id=project_id, last_updated=datetime.now().isoformat()
            )

        knowledge = self.projects_cache[project_id]

        # 既存の操作を更新または新規追加
        existing = next(
            (op for op in knowledge.frequent_operations if op.get("command") == operation.get("command")), None
        )

        if existing:
            existing["count"] = existing.get("count", 0) + 1
            existing["last_used"] = datetime.now().isoformat()
        else:
            operation["count"] = 1
            operation["last_used"] = datetime.now().isoformat()
            knowledge.frequent_operations.append(operation)

        # 頻度順にソート（上位20個のみ保持）
        knowledge.frequent_operations.sort(key=lambda x: x.get("count", 0), reverse=True)
        knowledge.frequent_operations = knowledge.frequent_operations[:20]

        knowledge.last_updated = datetime.now().isoformat()
        self._save_project_knowledge(knowledge)

    def get_similar_patterns(self, context: Dict[str, Any], limit: int = 5) -> List[Pattern]:
        """類似パターンを取得"""
        context_str = json.dumps(context, sort_keys=True)
        context_hash = hashlib.md5(context_str.encode(), usedforsecurity=False).hexdigest()

        # キャッシュチェック（ローカルキャッシュファイルのみ）
        cache_file = self.cache_dir / f"similar_{context_hash}.json"
        if cache_file.exists() and cache_file.stat().st_mtime > (datetime.now() - timedelta(hours=1)).timestamp():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                    return [Pattern(**p) for p in cached_data][:limit]
            except Exception as e:
                logger.debug(f"キャッシュ読み込みスキップ: {e}")

        # 類似度計算（簡易版）
        scored_patterns = []
        for pattern in self.patterns_cache.values():
            score = self._calculate_similarity(context, pattern)
            if score > 0.3:  # 閾値
                scored_patterns.append((score, pattern))

        # スコア順にソート
        scored_patterns.sort(key=lambda x: x[0], reverse=True)
        similar_patterns = [p for _, p in scored_patterns[:limit]]

        # キャッシュ保存
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump([asdict(p) for p in similar_patterns], f, ensure_ascii=False)
        except Exception as e:
            logger.debug(f"キャッシュ保存スキップ: {e}")

        return similar_patterns

    def get_project_knowledge(self, project_path: str) -> Optional[ProjectKnowledge]:
        """プロジェクト知識を取得"""
        project_id = self.get_project_id(project_path)
        return self.projects_cache.get(project_id)

    def suggest_solution(self, error_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """エラーに対する解決策を提案"""
        # 類似パターンを探す
        similar_patterns = self.get_similar_patterns(error_context, limit=3)

        if not similar_patterns:
            return None

        # 最も成功率の高いパターンを選択
        best_pattern = max(similar_patterns, key=lambda p: p.success_rate)

        if best_pattern.success_rate < 0.5:
            return None

        return {
            "pattern_id": best_pattern.pattern_id,
            "solution": best_pattern.solution,
            "confidence": best_pattern.success_rate,
            "usage_count": best_pattern.usage_count,
            "context": best_pattern.context,
        }

    def get_project_shortcuts(self, project_path: str) -> Dict[str, Any]:
        """プロジェクトのショートカットを取得"""
        knowledge = self.get_project_knowledge(project_path)
        if not knowledge:
            return {}

        return {
            "test": knowledge.test_commands[0] if knowledge.test_commands else None,
            "build": knowledge.build_commands[0] if knowledge.build_commands else None,
            "frequent_ops": knowledge.frequent_operations[:5],
            "aliases": knowledge.custom_aliases,
            "conventions": knowledge.conventions,
        }

    def _extract_pattern(self, entry: LearningEntry) -> Optional[Pattern]:
        """エントリからパターンを抽出"""
        if not entry.reusable or entry.confidence < 0.7:
            return None

        pattern_id = hashlib.md5(f"{entry.action}{entry.result}".encode(), usedforsecurity=False).hexdigest()[:12]

        # 既存パターンをチェック
        if pattern_id in self.patterns_cache:
            pattern = self.patterns_cache[pattern_id]
            pattern.usage_count += 1
            pattern.last_used = datetime.now().isoformat()

            # 成功率を更新（移動平均）
            if entry.outcome == "success":
                pattern.success_rate = pattern.success_rate * 0.9 + 1.0 * 0.1
            else:
                pattern.success_rate = pattern.success_rate * 0.9 + 0.0 * 0.1

            return pattern

        # 新規パターン作成
        return Pattern(
            pattern_id=pattern_id,
            pattern_type=entry.entry_type,
            context=json.dumps(entry.context),
            solution=entry.result,
            success_rate=0.9 if entry.outcome == "success" else 0.3,
            usage_count=1,
            last_used=datetime.now().isoformat(),
            tags=self._extract_tags(entry.context),
        )

    def _extract_tags(self, context: Dict[str, Any]) -> List[str]:
        """コンテキストからタグを抽出"""
        tags = []

        # ファイル拡張子
        if "file_path" in context:
            ext = Path(context["file_path"]).suffix
            if ext:
                tags.append(ext[1:])

        # ツール名
        if "tool" in context:
            tags.append(context["tool"])

        # エラータイプ
        if "error_type" in context:
            tags.append(context["error_type"])

        return tags

    def _calculate_similarity(self, context: Dict[str, Any], pattern: Pattern) -> float:
        """コンテキストとパターンの類似度を計算"""
        try:
            pattern_context = json.loads(pattern.context)
        except Exception as e:
            logger.debug(f"パターンコンテキスト解析スキップ: {e}")
            return 0.0

        score = 0.0
        total_weight = 0.0

        # キーの一致度
        context_keys = set(context.keys())
        pattern_keys = set(pattern_context.keys())
        key_overlap = len(context_keys & pattern_keys) / max(len(context_keys | pattern_keys), 1)
        score += key_overlap * 0.3
        total_weight += 0.3

        # 値の一致度（重要なキーのみ）
        important_keys = ["error_type", "tool", "file_extension", "operation"]
        for key in important_keys:
            if key in context and key in pattern_context:
                if context[key] == pattern_context[key]:
                    score += 0.2
                total_weight += 0.2

        # タグの一致度
        if pattern.tags:
            context_tags = self._extract_tags(context)
            tag_overlap = len(set(context_tags) & set(pattern.tags)) / max(
                len(set(context_tags) | set(pattern.tags)), 1
            )
            score += tag_overlap * 0.2
            total_weight += 0.2

        return score / max(total_weight, 1)

    def _save_pattern(self, pattern: Pattern) -> None:
        """パターンを保存"""
        self.patterns_cache[pattern.pattern_id] = pattern

        file_path = self.patterns_dir / f"{pattern.pattern_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(asdict(pattern), f, indent=2, ensure_ascii=False)

    def _save_entry(self, entry: LearningEntry) -> None:
        """エントリを保存"""
        file_path = self.entries_dir / f"{entry.entry_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(asdict(entry), f, indent=2, ensure_ascii=False)

    def _save_project_knowledge(self, knowledge: ProjectKnowledge) -> None:
        """プロジェクト知識を保存"""
        file_path = self.projects_dir / f"{knowledge.project_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(asdict(knowledge), f, indent=2, ensure_ascii=False)

    def _update_project_errors(self, project_path: str, error: str, solution: Optional[str]) -> None:
        """プロジェクトのエラーリストを更新"""
        project_id = self.get_project_id(project_path)

        if project_id not in self.projects_cache:
            self.projects_cache[project_id] = ProjectKnowledge(
                project_path=project_path, project_id=project_id, last_updated=datetime.now().isoformat()
            )

        knowledge = self.projects_cache[project_id]

        # エラーを追加（最新20個のみ保持）
        error_entry = {
            "error": error,
            "solution": solution,
            "timestamp": datetime.now().isoformat(),
            "resolved": bool(solution),
        }

        knowledge.common_errors.insert(0, error_entry)
        knowledge.common_errors = knowledge.common_errors[:20]
        knowledge.last_updated = datetime.now().isoformat()

        self._save_project_knowledge(knowledge)

    def get_learning_stats(self) -> Dict[str, Any]:
        """学習統計を取得"""
        return {
            "total_patterns": len(self.patterns_cache),
            "total_projects": len(self.projects_cache),
            "high_confidence_patterns": sum(1 for p in self.patterns_cache.values() if p.success_rate > 0.8),
            "frequently_used_patterns": sorted(
                [(p.pattern_id, p.usage_count) for p in self.patterns_cache.values()], key=lambda x: x[1], reverse=True
            )[:5],
            "recent_learning": len(list(self.entries_dir.glob("*.json"))),
        }


# グローバルインスタンス
learning_system = LearningSystem()


if __name__ == "__main__":
    # テスト実行
    learner = LearningSystem()

    # 成功事例から学習
    context = {"session_id": "test_session", "file_path": "/test/file.py", "tool": "pytest", "operation": "test"}

    entry_id = learner.learn_from_success(context=context, action="pytest tests/", result="All tests passed")
    print(f"Learned from success: {entry_id}")

    # プロジェクト規約を学習
    learner.learn_project_convention("/test/project", "test_command", "pytest tests/ -v")

    # 学習統計を表示
    stats = learner.get_learning_stats()
    print("\n=== Learning Stats ===")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
