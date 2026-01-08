"""
Gate DAG - Phase 7B

ゲートチェック依存関係DAG。独立したゲートを並列実行して処理時間を短縮。
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class GateType(Enum):
    """ゲートタイプ"""

    # 生成前チェック（最初に実行必須）
    PRE_GENERATION = "pre_generation"
    DIVERSITY_QUOTA = "diversity_quota"

    # 生成後チェック（生成完了後に実行、並列可能グループ）
    PROHIBITED_PATTERNS = "prohibited_patterns"
    SPECIFICITY = "specificity"
    ANTI_GAMING = "anti_gaming"
    FACT_CHECK = "fact_check"
    DUPLICATE = "duplicate"
    POLITE_FORM = "polite_form"  # 丁寧語チェック

    # 品質評価（スコア計算後に実行）
    QUALITY_GATE = "quality_gate"
    SUPER_TOTAL = "super_total"

    # 最終チェック（すべて完了後）
    INVENTORY = "inventory"
    CATEGORY_EVALUATOR = "category_evaluator"


@dataclass
class GateResult:
    """ゲート実行結果"""

    gate_type: GateType
    passed: bool
    message: str = ""
    duration_seconds: float = 0.0
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class GateDependency:
    """ゲート依存関係"""

    gate_type: GateType
    depends_on: list[GateType] = field(default_factory=list)
    is_parallel_safe: bool = True  # 並列実行可能か


class GateDAG:
    """
    ゲートチェック依存関係DAG

    ゲート間の依存関係を定義し、並列実行可能なゲートを特定。
    独立したゲートを同時に実行することで処理時間を短縮。

    依存関係グラフ:
    ```
    PRE_GENERATION ──┬── GENERATION ──┬── PROHIBITED_PATTERNS ──┐
                     │                ├── SPECIFICITY ──────────┤
                     │                ├── ANTI_GAMING ──────────┼── QUALITY_GATE ── SUPER_TOTAL ── INVENTORY
                     │                ├── FACT_CHECK ───────────┤
    DIVERSITY_QUOTA ─┘                └── DUPLICATE ────────────┘
    ```
    """

    # 依存関係定義
    DEPENDENCIES = {
        # 生成前チェック（シーケンシャル）
        GateType.PRE_GENERATION: GateDependency(
            gate_type=GateType.PRE_GENERATION,
            depends_on=[],
            is_parallel_safe=True,
        ),
        GateType.DIVERSITY_QUOTA: GateDependency(
            gate_type=GateType.DIVERSITY_QUOTA,
            depends_on=[],
            is_parallel_safe=True,
        ),
        # 生成後チェック（並列可能）
        GateType.PROHIBITED_PATTERNS: GateDependency(
            gate_type=GateType.PROHIBITED_PATTERNS,
            depends_on=[],  # 生成後、独立
            is_parallel_safe=True,
        ),
        GateType.SPECIFICITY: GateDependency(
            gate_type=GateType.SPECIFICITY,
            depends_on=[],
            is_parallel_safe=True,
        ),
        GateType.ANTI_GAMING: GateDependency(
            gate_type=GateType.ANTI_GAMING,
            depends_on=[],
            is_parallel_safe=True,
        ),
        GateType.FACT_CHECK: GateDependency(
            gate_type=GateType.FACT_CHECK,
            depends_on=[],
            is_parallel_safe=True,
        ),
        GateType.DUPLICATE: GateDependency(
            gate_type=GateType.DUPLICATE,
            depends_on=[],
            is_parallel_safe=False,  # マスターCSV参照のため
        ),
        GateType.POLITE_FORM: GateDependency(
            gate_type=GateType.POLITE_FORM,
            depends_on=[],
            is_parallel_safe=True,  # 丁寧語チェック（並列可）
        ),
        # 品質評価（前段チェック完了後）
        GateType.QUALITY_GATE: GateDependency(
            gate_type=GateType.QUALITY_GATE,
            depends_on=[
                GateType.PROHIBITED_PATTERNS,
                GateType.SPECIFICITY,
                GateType.ANTI_GAMING,
                GateType.FACT_CHECK,
                GateType.DUPLICATE,
            ],
            is_parallel_safe=True,
        ),
        GateType.SUPER_TOTAL: GateDependency(
            gate_type=GateType.SUPER_TOTAL,
            depends_on=[GateType.QUALITY_GATE],
            is_parallel_safe=True,
        ),
        # 最終チェック
        GateType.INVENTORY: GateDependency(
            gate_type=GateType.INVENTORY,
            depends_on=[GateType.SUPER_TOTAL],
            is_parallel_safe=True,
        ),
        GateType.CATEGORY_EVALUATOR: GateDependency(
            gate_type=GateType.CATEGORY_EVALUATOR,
            depends_on=[GateType.SUPER_TOTAL],
            is_parallel_safe=True,
        ),
    }

    # 並列実行グループ定義
    PARALLEL_GROUPS = [
        # グループ1: 生成後の独立チェック（並列実行可能）
        [
            GateType.PROHIBITED_PATTERNS,
            GateType.SPECIFICITY,
            GateType.ANTI_GAMING,
            GateType.FACT_CHECK,
        ],
        # グループ2: 最終チェック（並列実行可能）
        [
            GateType.INVENTORY,
            GateType.CATEGORY_EVALUATOR,
        ],
    ]

    def __init__(self):
        self._gate_handlers: dict[GateType, Callable] = {}
        self._results: dict[GateType, GateResult] = {}

    def register_handler(self, gate_type: GateType, handler: Callable) -> None:
        """
        ゲートハンドラーを登録

        Args:
            gate_type: ゲートタイプ
            handler: ゲート処理関数（引数なし、GateResult を返す）
        """
        self._gate_handlers[gate_type] = handler

    def get_parallel_group(self, gate_types: list[GateType]) -> list[list[GateType]]:
        """
        並列実行可能なゲートをグループ化

        Args:
            gate_types: 実行対象のゲートリスト

        Returns:
            list[list[GateType]]: 並列実行グループのリスト（順序通りに実行）
        """
        groups = []

        # 依存関係に基づいてトポロジカルソート
        remaining = set(gate_types)
        completed = set()

        while remaining:
            # 依存関係が満たされたゲートを抽出
            ready = []
            for gate in remaining:
                dep = self.DEPENDENCIES.get(gate)
                if dep is None:
                    ready.append(gate)
                elif all(d in completed or d not in gate_types for d in dep.depends_on):
                    ready.append(gate)

            if not ready:
                # 循環依存がある場合
                logger.warning(f"Circular dependency detected: {remaining}")
                break

            # 並列実行可能なゲートをグループ化
            parallel_ready = [g for g in ready if self.DEPENDENCIES.get(g, GateDependency(g)).is_parallel_safe]
            sequential_ready = [g for g in ready if g not in parallel_ready]

            if parallel_ready:
                groups.append(parallel_ready)
            for gate in sequential_ready:
                groups.append([gate])

            remaining -= set(ready)
            completed.update(ready)

        return groups

    async def execute_gates_async(
        self,
        gate_types: list[GateType],
    ) -> dict[GateType, GateResult]:
        """
        ゲートを依存関係に従って非同期実行

        Args:
            gate_types: 実行対象のゲートリスト

        Returns:
            dict[GateType, GateResult]: 各ゲートの実行結果
        """
        self._results = {}
        groups = self.get_parallel_group(gate_types)

        for group in groups:
            if len(group) == 1:
                # 単一ゲート（シーケンシャル）
                result = await self._execute_gate_async(group[0])
                self._results[group[0]] = result
                if not result.passed:
                    # 失敗したら即終了
                    break
            else:
                # 複数ゲート（並列）
                tasks = [self._execute_gate_async(gate) for gate in group]
                results = await asyncio.gather(*tasks)

                all_passed = True
                for gate, result in zip(group, results):
                    self._results[gate] = result
                    if not result.passed:
                        all_passed = False

                if not all_passed:
                    # いずれかが失敗したら終了
                    break

        return self._results

    async def _execute_gate_async(self, gate_type: GateType) -> GateResult:
        """
        単一ゲートを非同期実行

        Args:
            gate_type: ゲートタイプ

        Returns:
            GateResult: 実行結果
        """
        import time

        handler = self._gate_handlers.get(gate_type)
        if handler is None:
            return GateResult(
                gate_type=gate_type,
                passed=True,
                message=f"No handler registered for {gate_type.value}",
            )

        start_time = time.time()
        try:
            # ハンドラーが async かどうかで分岐
            if asyncio.iscoroutinefunction(handler):
                result = await handler()
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, handler)

            duration = time.time() - start_time

            if isinstance(result, GateResult):
                result.duration_seconds = duration
                return result
            elif isinstance(result, bool):
                return GateResult(
                    gate_type=gate_type,
                    passed=result,
                    duration_seconds=duration,
                )
            else:
                return GateResult(
                    gate_type=gate_type,
                    passed=True,
                    message=f"Unexpected result type: {type(result)}",
                    duration_seconds=duration,
                )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Gate {gate_type.value} failed: {e}")
            return GateResult(
                gate_type=gate_type,
                passed=False,
                message=str(e),
                duration_seconds=duration,
            )

    def execute_gates_sync(self, gate_types: list[GateType]) -> dict[GateType, GateResult]:
        """
        ゲートを同期実行（互換性用）

        Args:
            gate_types: 実行対象のゲートリスト

        Returns:
            dict[GateType, GateResult]: 各ゲートの実行結果
        """
        return asyncio.run(self.execute_gates_async(gate_types))

    def get_first_failure(self) -> Optional[GateResult]:
        """
        最初の失敗結果を取得

        Returns:
            Optional[GateResult]: 失敗結果、またはNone
        """
        for result in self._results.values():
            if not result.passed:
                return result
        return None

    def all_passed(self) -> bool:
        """
        すべてのゲートが通過したか確認

        Returns:
            bool: すべて通過した場合True
        """
        return all(r.passed for r in self._results.values())


# ==============================================================================
# 便利関数
# ==============================================================================


def get_post_generation_gates() -> list[GateType]:
    """
    生成後に実行するゲートリストを取得

    Returns:
        list[GateType]: ゲートタイプリスト
    """
    return [
        GateType.PROHIBITED_PATTERNS,
        GateType.SPECIFICITY,
        GateType.ANTI_GAMING,
        GateType.FACT_CHECK,
        GateType.DUPLICATE,
        GateType.QUALITY_GATE,
        GateType.SUPER_TOTAL,
    ]


def get_parallel_gates() -> list[GateType]:
    """
    並列実行可能なゲートリストを取得

    Returns:
        list[GateType]: ゲートタイプリスト
    """
    return [
        GateType.PROHIBITED_PATTERNS,
        GateType.SPECIFICITY,
        GateType.ANTI_GAMING,
        GateType.FACT_CHECK,
    ]


# ==============================================================================
# テスト
# ==============================================================================


if __name__ == "__main__":
    import time

    print("=== GateDAG Test ===")

    dag = GateDAG()

    # テスト用ハンドラー登録
    def make_handler(name: str, duration: float, passed: bool):
        def handler():
            time.sleep(duration)
            return GateResult(
                gate_type=GateType.PROHIBITED_PATTERNS,  # ダミー
                passed=passed,
                message=f"{name} completed",
            )

        return handler

    dag.register_handler(GateType.PROHIBITED_PATTERNS, make_handler("prohibited", 0.1, True))
    dag.register_handler(GateType.SPECIFICITY, make_handler("specificity", 0.1, True))
    dag.register_handler(GateType.ANTI_GAMING, make_handler("anti_gaming", 0.1, True))
    dag.register_handler(GateType.FACT_CHECK, make_handler("fact_check", 0.1, True))
    dag.register_handler(GateType.DUPLICATE, make_handler("duplicate", 0.1, True))
    dag.register_handler(GateType.QUALITY_GATE, make_handler("quality_gate", 0.1, True))
    dag.register_handler(GateType.SUPER_TOTAL, make_handler("super_total", 0.1, True))

    # 並列グループ表示
    gates = get_post_generation_gates()
    groups = dag.get_parallel_group(gates)
    print("\n並列実行グループ:")
    for i, group in enumerate(groups):
        print(f"  Group {i + 1}: {[g.value for g in group]}")

    # 同期実行（シーケンシャル）
    print("\n--- シーケンシャル実行 ---")
    start = time.time()
    for gate in gates:
        handler = dag._gate_handlers.get(gate)
        if handler:
            handler()
    seq_time = time.time() - start
    print(f"所要時間: {seq_time:.2f}秒")

    # 非同期実行（並列）
    print("\n--- 並列実行 ---")
    start = time.time()
    results = dag.execute_gates_sync(gates)
    par_time = time.time() - start
    print(f"所要時間: {par_time:.2f}秒")

    # 速度比較
    print(f"\n高速化: {seq_time / par_time:.2f}x")

    # 結果表示
    print("\n結果:")
    for gate, result in results.items():
        status = "✓" if result.passed else "✗"
        print(f"  {status} {gate.value}: {result.duration_seconds:.3f}s")

    print("\n=== Test Complete ===")
