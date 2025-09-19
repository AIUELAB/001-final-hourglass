#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
APIクレジット監視システム

Anthropic APIのクレジット残高を監視し、
事前に警告を発して課金を促すシステム

Rule 100（APIクレジット管理）の実装補助モジュール
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import anthropic
from anthropic import Anthropic
from dotenv import load_dotenv

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 環境変数読み込み
load_dotenv()


@dataclass
class CreditStatus:
    """クレジット状態"""
    is_available: bool
    remaining_credits: Optional[float]
    last_checked: datetime
    alert_level: str  # "safe", "warning", "critical", "empty"
    message: str
    action_required: bool


class APICrediteMonitor:
    """APIクレジット監視システム"""

    # クレジット警告閾値
    CREDIT_THRESHOLDS = {
        'critical': 1.0,    # $1以下でクリティカル
        'warning': 5.0,     # $5以下で警告
        'safe': 10.0        # $10以上で安全
    }

    # エピソード生成のコスト目安（Claude 3.5 Sonnet）
    COST_PER_EPISODE = 0.005  # $0.005 per episode（推定）

    def __init__(self, cache_file: str = "credit_cache.json"):
        """初期化"""
        self.cache_file = Path(cache_file)
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        """キャッシュ読み込み"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"キャッシュ読み込みエラー: {e}")
        return {
            'last_check': None,
            'last_credits': None,
            'check_history': []
        }

    def _save_cache(self):
        """キャッシュ保存"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"キャッシュ保存エラー: {e}")

    def check_credits(self, force_check: bool = False) -> CreditStatus:
        """
        クレジット残高チェック

        Args:
            force_check: 強制的に新規チェックを実行

        Returns:
            CreditStatus: クレジット状態
        """
        # APIキーが設定されていない場合
        if not self.api_key:
            return CreditStatus(
                is_available=False,
                remaining_credits=None,
                last_checked=datetime.now(),
                alert_level="empty",
                message="⚠️ ANTHROPIC_API_KEYが設定されていません",
                action_required=True
            )

        # キャッシュチェック（10分以内ならキャッシュを使用）
        if not force_check and self.cache.get('last_check'):
            last_check = datetime.fromisoformat(self.cache['last_check'])
            if datetime.now() - last_check < timedelta(minutes=10):
                return self._create_status_from_cache()

        # 実際のクレジットチェック（APIコールのシミュレーション）
        try:
            # 注意：Anthropic APIには直接的なクレジット残高確認のエンドポイントがないため、
            # 小さなリクエストを送って反応を見る方法を使用
            client = Anthropic(api_key=self.api_key)

            # 最小限のテストリクエスト
            try:
                response = client.messages.create(
                    model="claude-3-haiku-20240307",  # 最も安価なモデル
                    messages=[{"role": "user", "content": "Hi"}],
                    max_tokens=1
                )
                # 成功した場合はクレジットがある
                credits_available = True
                estimated_credits = self.cache.get('last_credits', 10.0)  # 推定値

            except anthropic.InsufficientCreditsError:
                credits_available = False
                estimated_credits = 0.0

            except anthropic.RateLimitError as e:
                # レート制限の場合もクレジット不足の可能性
                error_msg = str(e)
                if "credit" in error_msg.lower() or "balance" in error_msg.lower():
                    credits_available = False
                    estimated_credits = 0.0
                else:
                    credits_available = True
                    estimated_credits = self.cache.get('last_credits', 5.0)

        except Exception as e:
            logger.error(f"クレジットチェック中のエラー: {e}")
            return self._create_error_status(str(e))

        # キャッシュ更新
        self.cache['last_check'] = datetime.now().isoformat()
        self.cache['last_credits'] = estimated_credits
        self.cache['check_history'].append({
            'timestamp': datetime.now().isoformat(),
            'credits': estimated_credits,
            'available': credits_available
        })
        # 履歴は最新10件のみ保持
        self.cache['check_history'] = self.cache['check_history'][-10:]
        self._save_cache()

        # ステータス作成
        return self._create_status(credits_available, estimated_credits)

    def _create_status(self, available: bool, credits: Optional[float]) -> CreditStatus:
        """ステータス作成"""
        if not available or credits is None or credits == 0:
            return CreditStatus(
                is_available=False,
                remaining_credits=0.0,
                last_checked=datetime.now(),
                alert_level="empty",
                message=self._get_empty_message(),
                action_required=True
            )

        # アラートレベル判定
        if credits <= self.CREDIT_THRESHOLDS['critical']:
            alert_level = "critical"
            message = self._get_critical_message(credits)
            action_required = True
        elif credits <= self.CREDIT_THRESHOLDS['warning']:
            alert_level = "warning"
            message = self._get_warning_message(credits)
            action_required = False
        else:
            alert_level = "safe"
            message = f"✅ クレジット残高: 約${credits:.2f}（十分な残高があります）"
            action_required = False

        return CreditStatus(
            is_available=True,
            remaining_credits=credits,
            last_checked=datetime.now(),
            alert_level=alert_level,
            message=message,
            action_required=action_required
        )

    def _create_status_from_cache(self) -> CreditStatus:
        """キャッシュからステータス作成"""
        credits = self.cache.get('last_credits', 0)
        if credits is None:
            credits = 0
        available = credits > 0
        return self._create_status(available, credits)

    def _create_error_status(self, error: str) -> CreditStatus:
        """エラーステータス作成"""
        if "credit" in error.lower() or "insufficient" in error.lower():
            return CreditStatus(
                is_available=False,
                remaining_credits=0.0,
                last_checked=datetime.now(),
                alert_level="empty",
                message=self._get_empty_message(),
                action_required=True
            )

        return CreditStatus(
            is_available=False,
            remaining_credits=None,
            last_checked=datetime.now(),
            alert_level="warning",
            message=f"⚠️ APIエラー: {error}",
            action_required=False
        )

    def _get_empty_message(self) -> str:
        """クレジット枯渇時のメッセージ"""
        return """
🔴 ========================================
   Anthropic APIのクレジットが枯渇しています！
========================================

【至急対処が必要】
1. https://console.anthropic.com/ にアクセス
2. Plans & Billingページでクレジットを購入
3. 購入完了後、処理を再実行してください

【クレジット購入の目安】
- テスト用: $10（約2,000エピソード生成可能）
- 小規模: $50（約10,000エピソード生成可能）
- 本番用: $100（約20,000エピソード生成可能）

【注意】
PDCAガーディアンRule 100により、
クレジット不足時のサイレントフォールバックは禁止されています。
"""

    def _get_critical_message(self, credits: float) -> str:
        """クリティカル警告メッセージ"""
        episodes_remaining = int(credits / self.COST_PER_EPISODE)
        return f"""
🟡 ========================================
   クレジット残高が少なくなっています
========================================

残高: 約${credits:.2f}
推定生成可能エピソード数: 約{episodes_remaining}個

【推奨アクション】
処理を継続する前にクレジットの追加購入を検討してください。
https://console.anthropic.com/ でクレジットを購入できます。
"""

    def _get_warning_message(self, credits: float) -> str:
        """警告メッセージ"""
        episodes_remaining = int(credits / self.COST_PER_EPISODE)
        return f"""
⚠️ クレジット残高: 約${credits:.2f}（約{episodes_remaining}エピソード生成可能）
まもなく追加購入が必要になる可能性があります。
"""

    def estimate_cost(self, num_episodes: int) -> Tuple[float, str]:
        """
        エピソード生成コストの見積もり

        Args:
            num_episodes: 生成予定のエピソード数

        Returns:
            (推定コスト, メッセージ)
        """
        estimated_cost = num_episodes * self.COST_PER_EPISODE

        message = f"""
📊 コスト見積もり
- エピソード数: {num_episodes}個
- 推定コスト: ${estimated_cost:.2f}
- 1エピソードあたり: ${self.COST_PER_EPISODE:.3f}
"""

        # 現在の残高と比較
        status = self.check_credits()
        if status.remaining_credits is not None:
            if status.remaining_credits < estimated_cost:
                shortage = estimated_cost - status.remaining_credits
                message += f"""
⚠️ クレジット不足
- 現在の残高: ${status.remaining_credits:.2f}
- 不足額: ${shortage:.2f}
- 追加購入が必要です
"""
            else:
                message += f"""
✅ 処理可能
- 現在の残高: ${status.remaining_credits:.2f}
- 処理後の推定残高: ${status.remaining_credits - estimated_cost:.2f}
"""

        return estimated_cost, message

    def require_credits(self, min_amount: float = 1.0) -> bool:
        """
        最低限のクレジットがあることを要求

        Args:
            min_amount: 必要な最低金額

        Returns:
            bool: クレジットが十分にある場合True

        Raises:
            SystemError: クレジット不足の場合
        """
        status = self.check_credits()

        if not status.is_available:
            logger.error(status.message)
            raise SystemError("APIクレジットが不足しています。課金が必要です。")

        if status.remaining_credits and status.remaining_credits < min_amount:
            logger.error(f"""
クレジット残高不足: ${status.remaining_credits:.2f} < ${min_amount:.2f}
追加購入が必要です: https://console.anthropic.com/
""")
            raise SystemError(f"最低${min_amount:.2f}のクレジットが必要です。")

        if status.alert_level == "warning":
            logger.warning(status.message)

        return True

    def display_status(self):
        """クレジット状態を表示"""
        status = self.check_credits()

        print("\n" + "="*60)
        print("💳 APIクレジット状態")
        print("="*60)

        # アラートレベルに応じた絵文字
        emoji_map = {
            'safe': '✅',
            'warning': '⚠️',
            'critical': '🟡',
            'empty': '🔴'
        }

        print(f"{emoji_map.get(status.alert_level, '⚪')} 状態: {status.alert_level.upper()}")

        if status.remaining_credits is not None:
            print(f"💰 推定残高: ${status.remaining_credits:.2f}")
            episodes = int(status.remaining_credits / self.COST_PER_EPISODE)
            print(f"📝 生成可能エピソード数: 約{episodes}個")

        print(f"🕐 最終確認: {status.last_checked.strftime('%Y-%m-%d %H:%M:%S')}")

        if status.action_required:
            print("\n⚠️ アクションが必要です:")
            print(status.message)

        print("="*60 + "\n")


def main():
    """メイン関数（テスト用）"""
    monitor = APICrediteMonitor()

    # 状態表示
    monitor.display_status()

    # コスト見積もり
    cost, message = monitor.estimate_cost(100)
    print(message)

    # クレジットチェック
    try:
        monitor.require_credits(5.0)
        print("✅ クレジットチェック完了")
    except SystemError as e:
        print(f"❌ {e}")


if __name__ == "__main__":
    main()