"""
Alert Manager - Phase 7C

アラート管理・通知機能。
品質低下やシステム異常を検出して通知。
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """アラート重要度"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class KPIAlert:
    """KPIアラート"""

    severity: AlertSeverity
    metric_name: str
    current_value: float
    threshold: float
    message: str
    timestamp: str = ""
    acknowledged: bool = False

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict[str, Any]:
        """辞書に変換"""
        return {
            "severity": self.severity.value,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "message": self.message,
            "timestamp": self.timestamp,
            "acknowledged": self.acknowledged,
        }


@dataclass
class AlertRule:
    """アラートルール"""

    metric_name: str
    operator: str  # "lt", "gt", "eq", "ne"
    threshold: float
    severity: AlertSeverity
    message_template: str

    def evaluate(self, value: float) -> Optional[KPIAlert]:
        """ルールを評価してアラートを生成"""
        triggered = False

        if self.operator == "lt" and value < self.threshold:
            triggered = True
        elif self.operator == "gt" and value > self.threshold:
            triggered = True
        elif self.operator == "eq" and value == self.threshold:
            triggered = True
        elif self.operator == "ne" and value != self.threshold:
            triggered = True
        elif self.operator == "le" and value <= self.threshold:
            triggered = True
        elif self.operator == "ge" and value >= self.threshold:
            triggered = True

        if triggered:
            return KPIAlert(
                severity=self.severity,
                metric_name=self.metric_name,
                current_value=value,
                threshold=self.threshold,
                message=self.message_template.format(
                    value=value,
                    threshold=self.threshold,
                    metric=self.metric_name,
                ),
            )
        return None


# デフォルトアラートルール
DEFAULT_ALERT_RULES = [
    # 採用率
    AlertRule(
        metric_name="acceptance_rate",
        operator="lt",
        threshold=80.0,
        severity=AlertSeverity.WARNING,
        message_template="採用率が低下: {value:.1f}% < {threshold:.1f}%",
    ),
    AlertRule(
        metric_name="acceptance_rate",
        operator="lt",
        threshold=70.0,
        severity=AlertSeverity.CRITICAL,
        message_template="採用率が危険水準: {value:.1f}% < {threshold:.1f}%",
    ),
    # 生成品質
    AlertRule(
        metric_name="avg_generation_quality",
        operator="lt",
        threshold=8.0,
        severity=AlertSeverity.WARNING,
        message_template="平均生成品質が低下: {value:.1f} < {threshold:.1f}",
    ),
    # factual_density
    AlertRule(
        metric_name="avg_factual_density",
        operator="lt",
        threshold=7.0,
        severity=AlertSeverity.WARNING,
        message_template="平均factual_densityが低下: {value:.1f} < {threshold:.1f}",
    ),
    # コスト
    AlertRule(
        metric_name="daily_cost_usd",
        operator="gt",
        threshold=10.0,
        severity=AlertSeverity.WARNING,
        message_template="日次コストが上昇: ${value:.2f} > ${threshold:.2f}",
    ),
    AlertRule(
        metric_name="daily_cost_usd",
        operator="gt",
        threshold=50.0,
        severity=AlertSeverity.CRITICAL,
        message_template="日次コストが危険水準: ${value:.2f} > ${threshold:.2f}",
    ),
    # エラー率
    AlertRule(
        metric_name="error_rate",
        operator="gt",
        threshold=10.0,
        severity=AlertSeverity.WARNING,
        message_template="エラー率が上昇: {value:.1f}% > {threshold:.1f}%",
    ),
    AlertRule(
        metric_name="error_rate",
        operator="gt",
        threshold=25.0,
        severity=AlertSeverity.CRITICAL,
        message_template="エラー率が危険水準: {value:.1f}% > {threshold:.1f}%",
    ),
]


class AlertManager:
    """
    アラート管理クラス

    KPIを監視してアラートを生成・通知。
    """

    def __init__(
        self,
        rules: Optional[list[AlertRule]] = None,
        log_dir: str = "src/reports/logs",
    ):
        self.rules = rules or DEFAULT_ALERT_RULES
        self.log_dir = log_dir
        self.alerts: list[KPIAlert] = []
        self._notifiers: list[Callable[[KPIAlert], None]] = []

    def add_notifier(self, notifier: Callable[[KPIAlert], None]) -> None:
        """通知ハンドラを追加"""
        self._notifiers.append(notifier)

    def check_metrics(self, metrics: dict[str, float]) -> list[KPIAlert]:
        """
        メトリクスをチェックしてアラートを生成

        Args:
            metrics: メトリクス辞書 {"metric_name": value}

        Returns:
            list[KPIAlert]: 発火したアラートリスト
        """
        new_alerts: list[KPIAlert] = []

        for rule in self.rules:
            if rule.metric_name in metrics:
                value = metrics[rule.metric_name]
                alert = rule.evaluate(value)
                if alert:
                    new_alerts.append(alert)
                    self.alerts.append(alert)

                    # 通知
                    for notifier in self._notifiers:
                        try:
                            notifier(alert)
                        except Exception as e:
                            logger.error(f"Notifier failed: {e}")

        return new_alerts

    def get_active_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
    ) -> list[KPIAlert]:
        """
        アクティブなアラートを取得

        Args:
            severity: フィルタする重要度（省略時は全て）

        Returns:
            list[KPIAlert]: アラートリスト
        """
        active = [a for a in self.alerts if not a.acknowledged]
        if severity:
            active = [a for a in active if a.severity == severity]
        return active

    def acknowledge(self, index: int) -> bool:
        """
        アラートを確認済みにする

        Args:
            index: アラートのインデックス

        Returns:
            bool: 成功した場合True
        """
        if 0 <= index < len(self.alerts):
            self.alerts[index].acknowledged = True
            return True
        return False

    def clear_acknowledged(self) -> int:
        """
        確認済みアラートをクリア

        Returns:
            int: クリアした件数
        """
        original_count = len(self.alerts)
        self.alerts = [a for a in self.alerts if not a.acknowledged]
        return original_count - len(self.alerts)

    def save_alerts(self, filepath: Optional[str] = None) -> None:
        """アラートをJSONに保存"""
        if filepath is None:
            filepath = os.path.join(self.log_dir, f"alerts_{datetime.now().strftime('%Y%m%d')}.json")

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump([a.to_dict() for a in self.alerts], f, ensure_ascii=False, indent=2)

    def load_alerts(self, filepath: str) -> None:
        """アラートをJSONから読み込み"""
        if not os.path.exists(filepath):
            return

        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            self.alerts.append(
                KPIAlert(
                    severity=AlertSeverity(item["severity"]),
                    metric_name=item["metric_name"],
                    current_value=item["current_value"],
                    threshold=item["threshold"],
                    message=item["message"],
                    timestamp=item["timestamp"],
                    acknowledged=item.get("acknowledged", False),
                )
            )


# ==============================================================================
# 通知ハンドラ
# ==============================================================================


def console_notifier(alert: KPIAlert) -> None:
    """コンソール通知"""
    icon = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}.get(alert.severity.value, "📢")
    print(f"{icon} [{alert.severity.value.upper()}] {alert.message}")


def slack_notifier(alert: KPIAlert) -> None:
    """Slack通知（環境変数で設定）"""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return

    import requests

    icon = {"critical": ":rotating_light:", "warning": ":warning:", "info": ":information_source:"}.get(
        alert.severity.value, ":bell:"
    )

    payload = {
        "text": f"{icon} *[{alert.severity.value.upper()}]* {alert.message}",
        "attachments": [
            {
                "color": {"critical": "danger", "warning": "warning", "info": "good"}.get(alert.severity.value, "good"),
                "fields": [
                    {"title": "Metric", "value": alert.metric_name, "short": True},
                    {"title": "Value", "value": f"{alert.current_value:.2f}", "short": True},
                    {"title": "Threshold", "value": f"{alert.threshold:.2f}", "short": True},
                    {"title": "Time", "value": alert.timestamp, "short": True},
                ],
            }
        ],
    }

    try:
        requests.post(webhook_url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Slack notification failed: {e}")


def file_notifier(alert: KPIAlert, filepath: str = "src/reports/logs/alerts.log") -> None:
    """ファイル通知"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(
            f"[{alert.timestamp}] [{alert.severity.value.upper()}] "
            f"{alert.metric_name}: {alert.current_value:.2f} "
            f"(threshold: {alert.threshold:.2f}) - {alert.message}\n"
        )


# ==============================================================================
# テスト
# ==============================================================================


if __name__ == "__main__":
    print("=== AlertManager Test ===")

    # アラートマネージャー作成
    manager = AlertManager()
    manager.add_notifier(console_notifier)

    # テストメトリクス
    test_metrics = {
        "acceptance_rate": 75.0,  # 警告: < 80%
        "avg_generation_quality": 7.5,  # 警告: < 8.0
        "avg_factual_density": 7.5,  # OK: >= 7.0
        "daily_cost_usd": 15.0,  # 警告: > 10.0
        "error_rate": 5.0,  # OK: <= 10%
    }

    print("\n--- Checking metrics ---")
    alerts = manager.check_metrics(test_metrics)
    print(f"\nTriggered alerts: {len(alerts)}")

    # アクティブアラート
    print("\n--- Active alerts ---")
    for i, alert in enumerate(manager.get_active_alerts()):
        print(f"  [{i}] {alert.severity.value}: {alert.message}")

    # Critical アラートのみ
    print("\n--- Critical alerts ---")
    critical = manager.get_active_alerts(AlertSeverity.CRITICAL)
    print(f"  Count: {len(critical)}")

    # アラート確認
    print("\n--- Acknowledging first alert ---")
    manager.acknowledge(0)
    print(f"Active alerts after ack: {len(manager.get_active_alerts())}")

    print("\n=== Test Complete ===")
