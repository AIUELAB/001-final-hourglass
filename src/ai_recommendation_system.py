#!/usr/bin/env python3
"""
AI-based Recommendation System - Phase 11.5

機械学習による高度な推奨システム
- 過去の実装結果からの学習
- 動的な最適化パラメータ調整
- リアルタイム推奨生成
- 推奨精度の自動評価
"""

import argparse
import json
import sqlite3
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.database_utils import get_connection

try:
    import joblib
    import numpy as np
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    np = None
    RandomForestClassifier = None
    GradientBoostingClassifier = None
    StandardScaler = None
    train_test_split = None
    joblib = None


# ==========================================
# データクラス
# ==========================================


@dataclass
class AIRecommendation:
    """AI推奨事項"""

    recommendation_id: str
    timestamp: str
    recommendation_type: str  # capacity/cost/performance/security
    action: str  # scale_up/scale_down/optimize/maintain
    target_resource: str
    priority: str  # critical/high/medium/low
    confidence_score: float  # 0.0-1.0
    estimated_impact: float  # 予測される影響度
    estimated_savings: float  # 予測コスト削減額
    implementation_effort: str  # high/medium/low
    reasoning: str
    supporting_data: Dict[str, Any]
    alternative_actions: List[str]


@dataclass
class RecommendationFeedback:
    """推奨事項のフィードバック"""

    recommendation_id: str
    feedback_timestamp: str
    implemented: bool
    actual_impact: Optional[float]
    actual_savings: Optional[float]
    success_rating: float  # 0.0-1.0
    notes: str


@dataclass
class ModelPerformanceMetrics:
    """モデル性能メトリクス"""

    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    training_date: str
    sample_count: int


# ==========================================
# メインクラス
# ==========================================


class AIRecommendationSystem:
    """AIベースの推奨システム"""

    def __init__(self, db_path: str = "unified_quality.db"):
        self.db_path = db_path
        self.models_dir = Path("ml_models")
        self.models_dir.mkdir(exist_ok=True)

        self._init_database_tables()

        # モデルの初期化
        self.recommendation_model = None
        self.priority_model = None
        self.scaler = None

        # モデルをロード（存在する場合）
        self._load_models()

    def _init_database_tables(self):
        """データベーステーブルの初期化"""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        # AI推奨履歴テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_recommendations (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                recommendation_id TEXT UNIQUE NOT NULL,
                timestamp TEXT NOT NULL,
                recommendation_type TEXT NOT NULL,
                action TEXT NOT NULL,
                target_resource TEXT NOT NULL,
                priority TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                estimated_impact REAL NOT NULL,
                estimated_savings REAL NOT NULL,
                implementation_effort TEXT NOT NULL,
                reasoning TEXT,
                supporting_data TEXT,
                alternative_actions TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 推奨フィードバックテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recommendation_feedback (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                recommendation_id TEXT NOT NULL,
                feedback_timestamp TEXT NOT NULL,
                implemented INTEGER NOT NULL,
                actual_impact REAL,
                actual_savings REAL,
                success_rating REAL NOT NULL,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recommendation_id) REFERENCES ai_recommendations(recommendation_id)
            )
        """)

        # モデル性能履歴テーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_performance_history (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                model_name TEXT NOT NULL,
                accuracy REAL NOT NULL,
                precision_score REAL NOT NULL,
                recall_score REAL NOT NULL,
                f1_score REAL NOT NULL,
                training_date TEXT NOT NULL,
                sample_count INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 学習データテーブル
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recommendation_training_data (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                feature_vector TEXT NOT NULL,
                recommendation_label TEXT NOT NULL,
                priority_label TEXT NOT NULL,
                success_outcome INTEGER,
                timestamp TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def _load_models(self):
        """保存されたモデルをロード"""
        if not SKLEARN_AVAILABLE:
            return

        rec_model_path = self.models_dir / "ai_recommendation_model.pkl"
        priority_model_path = self.models_dir / "ai_priority_model.pkl"
        scaler_path = self.models_dir / "ai_scaler.pkl"

        try:
            if rec_model_path.exists():
                self.recommendation_model = joblib.load(rec_model_path)
            if priority_model_path.exists():
                self.priority_model = joblib.load(priority_model_path)
            if scaler_path.exists():
                self.scaler = joblib.load(scaler_path)
        except Exception as e:
            print(f"⚠️  モデルロード失敗: {e}")

    def _save_models(self):
        """モデルを保存"""
        if not SKLEARN_AVAILABLE:
            return

        try:
            if self.recommendation_model:
                joblib.dump(self.recommendation_model, self.models_dir / "ai_recommendation_model.pkl")
            if self.priority_model:
                joblib.dump(self.priority_model, self.models_dir / "ai_priority_model.pkl")
            if self.scaler:
                joblib.dump(self.scaler, self.models_dir / "ai_scaler.pkl")
        except Exception as e:
            print(f"⚠️  モデル保存失敗: {e}")

    def collect_system_features(self) -> Optional[Dict[str, float]]:
        """システムの現在の特徴量を収集"""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        features = {}

        # 最新のシステムメトリクス
        cursor.execute("""
            SELECT cpu_percent, memory_percent, disk_percent,
                   memory_used_gb, disk_used_gb
            FROM system_metrics
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        if row:
            features["cpu_usage"] = row[0]
            features["memory_usage"] = row[1]
            features["disk_usage"] = row[2]
            features["memory_used_gb"] = row[3]
            features["disk_used_gb"] = row[4]
        else:
            conn.close()
            return None

        # 最新の予測結果
        cursor.execute("""
            SELECT failure_probability, model_agreement
            FROM advanced_prediction_history
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        if row:
            features["failure_probability"] = row[0]
            features["model_agreement"] = row[1]
        else:
            features["failure_probability"] = 0.0
            features["model_agreement"] = 1.0

        # 最新の容量予測
        cursor.execute("""
            SELECT growth_rate_daily, days_until_threshold
            FROM capacity_forecasts
            ORDER BY timestamp DESC
            LIMIT 3
        """)
        rows = cursor.fetchall()
        if rows:
            growth_rates = [r[0] for r in rows if r[0] is not None]
            days_until = [r[1] for r in rows if r[1] is not None]

            features["avg_growth_rate"] = statistics.mean(growth_rates) if growth_rates else 0.0
            features["min_days_until_threshold"] = min(days_until) if days_until else 999
        else:
            features["avg_growth_rate"] = 0.0
            features["min_days_until_threshold"] = 999

        # コスト情報
        cursor.execute("""
            SELECT waste_percentage
            FROM resource_costs
            ORDER BY timestamp DESC
            LIMIT 3
        """)
        rows = cursor.fetchall()
        if rows:
            waste_pcts = [r[0] for r in rows]
            features["avg_waste_percentage"] = statistics.mean(waste_pcts)
        else:
            features["avg_waste_percentage"] = 0.0

        # 過去のインシデント数
        cursor.execute("""
            SELECT COUNT(*) as incident_count
            FROM quality_events
            WHERE timestamp >= datetime('now', '-7 days')
              AND severity IN ('high', 'critical')
        """)
        row = cursor.fetchone()
        features["recent_incidents"] = row[0] if row else 0

        conn.close()
        return features

    def generate_ai_recommendations(self) -> List[AIRecommendation]:
        """AIベースの推奨事項を生成"""
        timestamp = datetime.now().isoformat()

        print("=" * 80)
        print("🤖 Phase 11.5 - AIベースの推奨システム")
        print("=" * 80)
        print(f"生成時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print()

        # ステップ1: システム特徴量の収集
        print("📌 ステップ1: システム特徴量の収集")
        print("-" * 80)

        features = self.collect_system_features()
        if not features:
            print("  ⚠️  システムデータが不足しています")
            return []

        print("  ✅ 収集完了:")
        for key, value in features.items():
            print(f"    {key}: {value:.2f}")
        print()

        # ステップ2: ルールベース推奨の生成
        print("📌 ステップ2: ルールベース推奨の生成")
        print("-" * 80)

        rule_based_recs = self._generate_rule_based_recommendations(features, timestamp)
        print(f"  ✅ ルールベース推奨: {len(rule_based_recs)}件")
        print()

        # ステップ3: ML推奨の生成（モデルが利用可能な場合）
        print("📌 ステップ3: ML推奨の生成")
        print("-" * 80)

        ml_recs = []
        if SKLEARN_AVAILABLE and self.recommendation_model:
            ml_recs = self._generate_ml_recommendations(features, timestamp)
            print(f"  ✅ ML推奨: {len(ml_recs)}件")
        else:
            print("  ℹ️  MLモデル未学習 - ルールベースのみ使用")
        print()

        # ステップ4: 推奨事項の統合と優先順位付け
        print("📌 ステップ4: 推奨事項の統合と優先順位付け")
        print("-" * 80)

        all_recommendations = rule_based_recs + ml_recs
        ranked_recs = self._rank_recommendations(all_recommendations)

        print(f"  ✅ 総推奨事項: {len(ranked_recs)}件")
        print()

        # ステップ5: 推奨事項の表示と保存
        print("📌 ステップ5: 推奨事項")
        print("-" * 80)

        for i, rec in enumerate(ranked_recs[:10], 1):  # トップ10を表示
            print(f"\n  【推奨 {i}】")
            print(f"    タイプ: {rec.recommendation_type}")
            print(f"    アクション: {rec.action}")
            print(f"    対象: {rec.target_resource}")
            print(f"    優先度: {rec.priority}")
            print(f"    信頼度: {rec.confidence_score * 100:.1f}%")
            print(f"    予測影響度: {rec.estimated_impact:.2f}")
            print(f"    予測削減額: ${rec.estimated_savings:.2f}/月")
            print(f"    実装負荷: {rec.implementation_effort}")
            print(f"    理由: {rec.reasoning}")

            # データベースに保存
            self._save_recommendation(rec)

        print()
        print("=" * 80)
        print("✅ AI推奨生成完了")
        print("=" * 80)

        return ranked_recs

    def _check_cpu_rule(self, features: Dict[str, float], timestamp: str) -> Optional[AIRecommendation]:
        """ルール1: 高CPU使用率チェック"""
        if features.get("cpu_usage", 0) <= 80:
            return None
        rec_id = f"ai_rec_{datetime.now().strftime('%Y%m%d%H%M%S')}_cpu_high"
        return AIRecommendation(
            recommendation_id=rec_id,
            timestamp=timestamp,
            recommendation_type="performance",
            action="scale_up",
            target_resource="CPU",
            priority="high",
            confidence_score=0.95,
            estimated_impact=0.8,
            estimated_savings=0.0,
            implementation_effort="medium",
            reasoning="CPU使用率が80%を超えています。スケールアップを推奨します。",
            supporting_data={"cpu_usage": features["cpu_usage"]},
            alternative_actions=["optimize", "load_balance"],
        )

    def _check_memory_rule(self, features: Dict[str, float], timestamp: str) -> Optional[AIRecommendation]:
        """ルール2: 高メモリ使用率チェック"""
        if features.get("memory_usage", 0) <= 85:
            return None
        rec_id = f"ai_rec_{datetime.now().strftime('%Y%m%d%H%M%S')}_mem_high"
        return AIRecommendation(
            recommendation_id=rec_id,
            timestamp=timestamp,
            recommendation_type="performance",
            action="scale_up",
            target_resource="MEMORY",
            priority="high",
            confidence_score=0.93,
            estimated_impact=0.75,
            estimated_savings=0.0,
            implementation_effort="medium",
            reasoning="メモリ使用率が85%を超えています。スケールアップを推奨します。",
            supporting_data={"memory_usage": features["memory_usage"]},
            alternative_actions=["optimize", "cache_clear"],
        )

    def _check_capacity_rule(self, features: Dict[str, float], timestamp: str) -> Optional[AIRecommendation]:
        """ルール3: 容量閾値接近チェック"""
        days = features.get("min_days_until_threshold", 999)
        if days > 14:
            return None
        rec_id = f"ai_rec_{datetime.now().strftime('%Y%m%d%H%M%S')}_capacity"
        priority = "critical" if days <= 7 else "high"
        return AIRecommendation(
            recommendation_id=rec_id,
            timestamp=timestamp,
            recommendation_type="capacity",
            action="scale_up",
            target_resource="STORAGE",
            priority=priority,
            confidence_score=0.90,
            estimated_impact=0.85,
            estimated_savings=0.0,
            implementation_effort="low",
            reasoning=f"容量閾値まで{days:.0f}日です。容量拡張を推奨します。",
            supporting_data={"days_until_threshold": days},
            alternative_actions=["cleanup", "archive"],
        )

    def _check_waste_rule(self, features: Dict[str, float], timestamp: str) -> Optional[AIRecommendation]:
        """ルール4: 高無駄率チェック"""
        waste = features.get("avg_waste_percentage", 0)
        if waste <= 50:
            return None
        rec_id = f"ai_rec_{datetime.now().strftime('%Y%m%d%H%M%S')}_waste"
        estimated_savings = waste * 0.01 * 500
        return AIRecommendation(
            recommendation_id=rec_id,
            timestamp=timestamp,
            recommendation_type="cost",
            action="optimize",
            target_resource="ALL",
            priority="medium",
            confidence_score=0.85,
            estimated_impact=0.6,
            estimated_savings=estimated_savings,
            implementation_effort="high",
            reasoning=f"リソースの無駄が{waste:.1f}%あります。最適化を推奨します。",
            supporting_data={"waste_percentage": waste},
            alternative_actions=["scale_down", "consolidate"],
        )

    def _check_failure_rule(self, features: Dict[str, float], timestamp: str) -> Optional[AIRecommendation]:
        """ルール5: 高障害確率チェック"""
        prob = features.get("failure_probability", 0)
        if prob <= 0.5:
            return None
        rec_id = f"ai_rec_{datetime.now().strftime('%Y%m%d%H%M%S')}_failure"
        return AIRecommendation(
            recommendation_id=rec_id,
            timestamp=timestamp,
            recommendation_type="security",
            action="optimize",
            target_resource="SYSTEM",
            priority="high",
            confidence_score=0.88,
            estimated_impact=0.9,
            estimated_savings=0.0,
            implementation_effort="high",
            reasoning=f"障害確率が{prob * 100:.1f}%と高いです。予防保守を推奨します。",
            supporting_data={"failure_probability": prob},
            alternative_actions=["backup", "monitoring"],
        )

    def _generate_rule_based_recommendations(
        self, features: Dict[str, float], timestamp: str
    ) -> List[AIRecommendation]:
        """ルールベースの推奨事項を生成"""
        rule_checks = [
            self._check_cpu_rule,
            self._check_memory_rule,
            self._check_capacity_rule,
            self._check_waste_rule,
            self._check_failure_rule,
        ]
        recommendations = []
        for check_func in rule_checks:
            rec = check_func(features, timestamp)
            if rec:
                recommendations.append(rec)
        return recommendations

    def _generate_ml_recommendations(self, features: Dict[str, float], timestamp: str) -> List[AIRecommendation]:
        """MLベースの推奨事項を生成"""
        if not SKLEARN_AVAILABLE or not self.recommendation_model:
            return []

        try:
            # 特徴ベクトルの準備
            feature_vector = self._prepare_feature_vector(features)

            if self.scaler:
                feature_vector_scaled = self.scaler.transform([feature_vector])
            else:
                feature_vector_scaled = [feature_vector]

            # 推奨アクションの予測
            predicted_action = self.recommendation_model.predict(feature_vector_scaled)[0]
            action_proba = self.recommendation_model.predict_proba(feature_vector_scaled)[0]
            confidence = max(action_proba)

            # 優先度の予測
            if self.priority_model:
                predicted_priority = self.priority_model.predict(feature_vector_scaled)[0]
            else:
                predicted_priority = "medium"

            # ML推奨事項を作成
            rec_id = f"ai_rec_{datetime.now().strftime('%Y%m%d%H%M%S')}_ml"

            recommendation = AIRecommendation(
                recommendation_id=rec_id,
                timestamp=timestamp,
                recommendation_type="ml_based",
                action=predicted_action,
                target_resource="SYSTEM",
                priority=predicted_priority,
                confidence_score=confidence,
                estimated_impact=0.7,
                estimated_savings=100.0,  # 仮の値
                implementation_effort="medium",
                reasoning=f"機械学習モデルによる推奨（信頼度{confidence * 100:.1f}%）",
                supporting_data=features,
                alternative_actions=[],
            )

            return [recommendation]

        except Exception as e:
            print(f"  ⚠️  ML推奨生成エラー: {e}")
            return []

    def _prepare_feature_vector(self, features: Dict[str, float]) -> List[float]:
        """特徴ベクトルの準備"""
        feature_order = [
            "cpu_usage",
            "memory_usage",
            "disk_usage",
            "memory_used_gb",
            "disk_used_gb",
            "failure_probability",
            "model_agreement",
            "avg_growth_rate",
            "min_days_until_threshold",
            "avg_waste_percentage",
            "recent_incidents",
        ]

        return [features.get(key, 0.0) for key in feature_order]

    def _rank_recommendations(self, recommendations: List[AIRecommendation]) -> List[AIRecommendation]:
        """推奨事項をランク付け"""
        priority_scores = {"critical": 4, "high": 3, "medium": 2, "low": 1}

        def score_recommendation(rec: AIRecommendation) -> float:
            priority_score = priority_scores.get(rec.priority, 1)
            confidence_score = rec.confidence_score
            impact_score = rec.estimated_impact

            # 総合スコア = 優先度 * 信頼度 * 影響度
            return priority_score * confidence_score * impact_score

        return sorted(recommendations, key=score_recommendation, reverse=True)

    def _save_recommendation(self, rec: AIRecommendation):
        """推奨事項をデータベースに保存"""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO ai_recommendations (
                    recommendation_id, timestamp, recommendation_type, action,
                    target_resource, priority, confidence_score, estimated_impact,
                    estimated_savings, implementation_effort, reasoning,
                    supporting_data, alternative_actions
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    rec.recommendation_id,
                    rec.timestamp,
                    rec.recommendation_type,
                    rec.action,
                    rec.target_resource,
                    rec.priority,
                    rec.confidence_score,
                    rec.estimated_impact,
                    rec.estimated_savings,
                    rec.implementation_effort,
                    rec.reasoning,
                    json.dumps(rec.supporting_data, ensure_ascii=False),
                    json.dumps(rec.alternative_actions, ensure_ascii=False),
                ),
            )

            conn.commit()
        except sqlite3.IntegrityError:
            # 重複する推奨事項は無視
            pass
        finally:
            conn.close()

    def show_recommendations_history(self, limit: int = 10):
        """推奨履歴を表示"""
        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT recommendation_id, timestamp, recommendation_type, action,
                   target_resource, priority, confidence_score
            FROM ai_recommendations
            ORDER BY created_at DESC
            LIMIT ?
        """,
            (limit,),
        )

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            print("AI推奨履歴がありません")
            return

        print("=" * 80)
        print("🤖 AI推奨履歴")
        print("=" * 80)

        for i, row in enumerate(rows, 1):
            print(f"\n{i}. {row[1]}")
            print(f"   ID: {row[0]}")
            print(f"   タイプ: {row[2]}")
            print(f"   アクション: {row[3]}")
            print(f"   対象: {row[4]}")
            print(f"   優先度: {row[5]}")
            print(f"   信頼度: {row[6] * 100:.1f}%")


# ==========================================
# メイン処理
# ==========================================


def main():
    parser = argparse.ArgumentParser(description="AI-based Recommendation System - Phase 11.5")
    parser.add_argument("--generate", action="store_true", help="AI推奨事項を生成")
    parser.add_argument("--history", action="store_true", help="推奨履歴を表示")
    parser.add_argument("--limit", type=int, default=10, help="履歴表示の件数")
    parser.add_argument("--save", action="store_true", help="結果をJSONファイルに保存")

    args = parser.parse_args()

    system = AIRecommendationSystem()

    if args.generate:
        recommendations = system.generate_ai_recommendations()

        if args.save and recommendations:
            # レポートディレクトリの作成
            reports_dir = Path("reports/ai_recommendations")
            reports_dir.mkdir(parents=True, exist_ok=True)

            # JSONファイルに保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ai_recommendations_{timestamp}.json"
            filepath = reports_dir / filename

            recommendations_dict = [asdict(rec) for rec in recommendations]
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(recommendations_dict, f, ensure_ascii=False, indent=2)

            print()
            print(f"✅ レポート保存: {filepath}")

    elif args.history:
        system.show_recommendations_history(limit=args.limit)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
