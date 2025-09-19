#!/usr/bin/env python3
"""
監査ログシステム（Audit Logger System）
Complete audit trail for quality-first processing

すべての判定、API呼び出し、品質チェックを記録し、
人間が検証可能な形で出力します。
問題発生時の原因追跡を容易にします。
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import hashlib
import traceback
from enum import Enum
import gzip
import shutil

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AuditLevel(Enum):
    """監査レベル"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AuditCategory(Enum):
    """監査カテゴリ"""
    API_CALL = "API呼び出し"
    VALIDATION = "検証"
    DECISION = "判定"
    DATA_QUALITY = "データ品質"
    SYSTEM = "システム"
    SECURITY = "セキュリティ"
    PERFORMANCE = "パフォーマンス"


class AuditLogger:
    """監査ログシステム"""
    
    def __init__(self, 
                 log_dir: str = "audit_logs",
                 max_size_mb: int = 100,
                 retention_days: int = 90,
                 compress_after_days: int = 7):
        """
        初期化
        
        Args:
            log_dir: ログディレクトリ
            max_size_mb: 最大ファイルサイズ（MB）
            retention_days: ログ保持日数
            compress_after_days: 圧縮までの日数
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.retention_days = retention_days
        self.compress_after_days = compress_after_days
        
        # セッション情報
        self.session_id = self._generate_session_id()
        self.session_start = datetime.now()
        
        # 現在のログファイル
        self.current_log_file = self._get_log_filename()
        
        # メモリバッファ（パフォーマンス向上のため）
        self.buffer: List[Dict[str, Any]] = []
        self.buffer_size = 100  # 100件ごとにフラッシュ
        
        # 統計情報
        self.stats = {
            'total_entries': 0,
            'by_level': {},
            'by_category': {},
            'api_calls': 0,
            'validations': 0,
            'errors': 0
        }
        
        # 初期化ログ
        self.log(
            AuditLevel.INFO,
            AuditCategory.SYSTEM,
            "監査ログシステム起動",
            {'session_id': self.session_id}
        )
    
    def log(self,
            level: AuditLevel,
            category: AuditCategory,
            message: str,
            details: Optional[Dict[str, Any]] = None,
            person_id: Optional[str] = None,
            api_name: Optional[str] = None):
        """
        監査ログ記録
        
        Args:
            level: ログレベル
            category: カテゴリ
            message: メッセージ
            details: 詳細情報
            person_id: 関連する人物ID
            api_name: 関連するAPI名
        """
        entry = {
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id,
            'level': level.value,
            'category': category.value,
            'message': message,
            'details': details or {},
            'person_id': person_id,
            'api_name': api_name,
            'stack_trace': None
        }
        
        # エラーの場合はスタックトレースを追加
        if level in [AuditLevel.ERROR, AuditLevel.CRITICAL]:
            entry['stack_trace'] = traceback.format_stack()
            self.stats['errors'] += 1
        
        # 統計更新
        self._update_stats(level, category)
        
        # バッファに追加
        self.buffer.append(entry)
        
        # バッファがいっぱいならフラッシュ
        if len(self.buffer) >= self.buffer_size:
            self.flush()
        
        # ログレベルに応じてloggerにも出力
        log_message = f"[{category.value}] {message}"
        if level == AuditLevel.DEBUG:
            logger.debug(log_message)
        elif level == AuditLevel.INFO:
            logger.info(log_message)
        elif level == AuditLevel.WARNING:
            logger.warning(log_message)
        elif level == AuditLevel.ERROR:
            logger.error(log_message)
        elif level == AuditLevel.CRITICAL:
            logger.critical(log_message)
    
    def log_api_call(self,
                    api_name: str,
                    request: Dict[str, Any],
                    response: Optional[Dict[str, Any]] = None,
                    error: Optional[str] = None,
                    duration_ms: Optional[float] = None):
        """
        API呼び出しのログ
        
        Args:
            api_name: API名
            request: リクエスト内容
            response: レスポンス内容
            error: エラー情報
            duration_ms: 実行時間（ミリ秒）
        """
        details = {
            'request': request,
            'response': response,
            'error': error,
            'duration_ms': duration_ms,
            'success': error is None
        }
        
        # ダミーデータ検出
        if response:
            dummy_indicators = self._detect_dummy_data(response)
            if dummy_indicators:
                details['dummy_data_detected'] = True
                details['dummy_indicators'] = dummy_indicators
                self.log(
                    AuditLevel.ERROR,
                    AuditCategory.API_CALL,
                    f"{api_name}からダミーデータを検出",
                    details,
                    api_name=api_name
                )
                return
        
        level = AuditLevel.ERROR if error else AuditLevel.INFO
        self.log(
            level,
            AuditCategory.API_CALL,
            f"{api_name} API呼び出し",
            details,
            api_name=api_name
        )
        
        self.stats['api_calls'] += 1
    
    def log_validation(self,
                      validation_type: str,
                      target: str,
                      result: bool,
                      details: Optional[Dict[str, Any]] = None,
                      person_id: Optional[str] = None):
        """
        検証のログ
        
        Args:
            validation_type: 検証タイプ
            target: 検証対象
            result: 検証結果
            details: 詳細情報
            person_id: 人物ID
        """
        level = AuditLevel.INFO if result else AuditLevel.WARNING
        message = f"{validation_type}検証: {target} - {'成功' if result else '失敗'}"
        
        self.log(
            level,
            AuditCategory.VALIDATION,
            message,
            details,
            person_id=person_id
        )
        
        self.stats['validations'] += 1
    
    def log_decision(self,
                    decision_type: str,
                    decision: str,
                    reason: str,
                    confidence: Optional[float] = None,
                    person_id: Optional[str] = None,
                    details: Optional[Dict[str, Any]] = None):
        """
        判定のログ
        
        Args:
            decision_type: 判定タイプ（削除、保持など）
            decision: 判定結果
            reason: 判定理由
            confidence: 信頼度
            person_id: 人物ID
            details: 詳細情報
        """
        decision_details = {
            'decision_type': decision_type,
            'decision': decision,
            'reason': reason,
            'confidence': confidence
        }
        if details:
            decision_details.update(details)
        
        self.log(
            AuditLevel.INFO,
            AuditCategory.DECISION,
            f"{decision_type}: {decision}",
            decision_details,
            person_id=person_id
        )
    
    def log_data_quality_issue(self,
                              issue_type: str,
                              description: str,
                              severity: str = "WARNING",
                              affected_data: Optional[Any] = None,
                              person_id: Optional[str] = None):
        """
        データ品質問題のログ
        
        Args:
            issue_type: 問題タイプ
            description: 問題の説明
            severity: 深刻度
            affected_data: 影響を受けるデータ
            person_id: 人物ID
        """
        level = AuditLevel.CRITICAL if severity == "CRITICAL" else \
                AuditLevel.ERROR if severity == "ERROR" else \
                AuditLevel.WARNING
        
        self.log(
            level,
            AuditCategory.DATA_QUALITY,
            f"データ品質問題: {issue_type}",
            {
                'description': description,
                'severity': severity,
                'affected_data': str(affected_data)[:500] if affected_data else None
            },
            person_id=person_id
        )
    
    def _detect_dummy_data(self, data: Dict[str, Any]) -> List[str]:
        """
        ダミーデータの検出
        
        Args:
            data: チェック対象データ
        
        Returns:
            検出されたダミーデータの指標リスト
        """
        indicators = []
        
        # 典型的なダミーデータパターン
        if data.get('total_results') == 0:
            indicators.append('total_results is 0')
        
        if data.get('results') == []:
            indicators.append('empty results array')
        
        if data.get('source') in ['fallback', 'simulated', 'mock', 'dummy']:
            indicators.append(f"source is {data.get('source')}")
        
        # TODOやFIXMEの検出
        data_str = str(data)
        for keyword in ['TODO', 'FIXME', 'HACK', 'XXX', 'placeholder']:
            if keyword in data_str:
                indicators.append(f"contains {keyword}")
        
        return indicators
    
    def flush(self):
        """バッファをファイルにフラッシュ"""
        if not self.buffer:
            return
        
        # ファイルサイズチェック
        if self._check_file_size():
            self._rotate_log()
        
        # ログファイルに書き込み
        try:
            with open(self.current_log_file, 'a', encoding='utf-8') as f:
                for entry in self.buffer:
                    f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            
            self.buffer.clear()
            
        except Exception as e:
            logger.error(f"ログ書き込みエラー: {e}")
    
    def _check_file_size(self) -> bool:
        """ファイルサイズチェック"""
        if not self.current_log_file.exists():
            return False
        return self.current_log_file.stat().st_size >= self.max_size_bytes
    
    def _rotate_log(self):
        """ログローテーション"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_name = self.current_log_file.stem + f'_{timestamp}.json'
        rotated_file = self.log_dir / new_name
        
        self.current_log_file.rename(rotated_file)
        self.current_log_file = self._get_log_filename()
        
        logger.info(f"ログローテーション: {rotated_file}")
    
    def _get_log_filename(self) -> Path:
        """現在のログファイル名を取得"""
        date_str = datetime.now().strftime('%Y%m%d')
        return self.log_dir / f'audit_{date_str}.json'
    
    def _generate_session_id(self) -> str:
        """セッションID生成"""
        timestamp = datetime.now().isoformat()
        return hashlib.md5(timestamp.encode()).hexdigest()[:8]
    
    def _update_stats(self, level: AuditLevel, category: AuditCategory):
        """統計情報更新"""
        self.stats['total_entries'] += 1
        
        level_key = level.value
        if level_key not in self.stats['by_level']:
            self.stats['by_level'][level_key] = 0
        self.stats['by_level'][level_key] += 1
        
        category_key = category.value
        if category_key not in self.stats['by_category']:
            self.stats['by_category'][category_key] = 0
        self.stats['by_category'][category_key] += 1
    
    def compress_old_logs(self):
        """古いログファイルを圧縮"""
        cutoff_date = datetime.now() - timedelta(days=self.compress_after_days)
        
        for log_file in self.log_dir.glob('audit_*.json'):
            # すでに圧縮済みはスキップ
            if log_file.suffix == '.gz':
                continue
            
            # ファイルの更新日時をチェック
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if mtime < cutoff_date:
                # 圧縮
                gz_file = log_file.with_suffix('.json.gz')
                with open(log_file, 'rb') as f_in:
                    with gzip.open(gz_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # 元ファイル削除
                log_file.unlink()
                logger.info(f"ログファイル圧縮: {gz_file}")
    
    def cleanup_old_logs(self):
        """古いログファイルを削除"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        for log_file in self.log_dir.glob('audit_*'):
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if mtime < cutoff_date:
                log_file.unlink()
                logger.info(f"古いログファイル削除: {log_file}")
    
    def export_session_summary(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        セッションサマリーのエクスポート
        
        Args:
            output_file: 出力ファイル名
        
        Returns:
            サマリー情報
        """
        # 最後のバッファをフラッシュ
        self.flush()
        
        session_duration = (datetime.now() - self.session_start).total_seconds()
        
        summary = {
            'session_id': self.session_id,
            'session_start': self.session_start.isoformat(),
            'session_duration_seconds': session_duration,
            'statistics': self.stats,
            'quality_issues': self._get_quality_issues(),
            'api_performance': self._get_api_performance(),
            'validation_results': self._get_validation_results()
        }
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            logger.info(f"セッションサマリー出力: {output_file}")
        
        return summary
    
    def _get_quality_issues(self) -> List[Dict[str, Any]]:
        """品質問題のサマリー取得"""
        issues = []
        
        # 現在のログファイルから品質問題を抽出
        if self.current_log_file.exists():
            with open(self.current_log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry.get('category') == AuditCategory.DATA_QUALITY.value:
                            issues.append({
                                'timestamp': entry['timestamp'],
                                'message': entry['message'],
                                'severity': entry.get('details', {}).get('severity', 'WARNING')
                            })
                    except json.JSONDecodeError:
                        continue
        
        return issues
    
    def _get_api_performance(self) -> Dict[str, Any]:
        """APIパフォーマンスのサマリー取得"""
        api_stats = {
            'total_calls': self.stats['api_calls'],
            'success_rate': 0.0,
            'average_duration_ms': 0.0,
            'timeout_count': 0,
            'dummy_data_count': 0
        }
        
        # 詳細統計の計算（実際のログファイルから）
        # ここでは簡略化
        
        return api_stats
    
    def _get_validation_results(self) -> Dict[str, Any]:
        """検証結果のサマリー取得"""
        return {
            'total_validations': self.stats['validations'],
            'errors': self.stats['errors'],
            'error_rate': self.stats['errors'] / max(self.stats['validations'], 1)
        }
    
    def __enter__(self):
        """コンテキストマネージャー: 開始"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャー: 終了"""
        if exc_type:
            self.log(
                AuditLevel.ERROR,
                AuditCategory.SYSTEM,
                f"エラーによる終了: {exc_type.__name__}",
                {'error': str(exc_val), 'traceback': traceback.format_exc()}
            )
        
        # バッファをフラッシュ
        self.flush()
        
        # セッション終了ログ
        self.log(
            AuditLevel.INFO,
            AuditCategory.SYSTEM,
            "監査ログシステム終了",
            self.get_summary()
        )
        
        # 最後のフラッシュ
        self.flush()
    
    def get_summary(self) -> Dict[str, Any]:
        """現在の統計サマリー取得"""
        return {
            'session_id': self.session_id,
            'total_entries': self.stats['total_entries'],
            'by_level': self.stats['by_level'],
            'by_category': self.stats['by_category'],
            'api_calls': self.stats['api_calls'],
            'validations': self.stats['validations'],
            'errors': self.stats['errors']
        }


def main():
    """テスト実行"""
    print("="*60)
    print("監査ログシステム テスト")
    print("="*60)
    
    # 監査ログシステムの使用例
    with AuditLogger() as audit:
        # API呼び出しログ
        audit.log_api_call(
            api_name="brave_search",
            request={'query': 'HIKAKIN'},
            response={'total_results': 0, 'results': [], 'source': 'simulated'},
            duration_ms=150.5
        )
        
        # 検証ログ
        audit.log_validation(
            validation_type="スコア範囲",
            target="P000013",
            result=False,
            details={'score': 3.3, 'expected_min': 7.0},
            person_id="P000013"
        )
        
        # 判定ログ
        audit.log_decision(
            decision_type="削除判定",
            decision="DELETE_HIGH_CONFIDENCE",
            reason="スコアが基準値未満",
            confidence=0.95,
            person_id="P000013",
            details={'score': 3.3, 'threshold': 4.0}
        )
        
        # データ品質問題ログ
        audit.log_data_quality_issue(
            issue_type="ダミーデータ検出",
            description="Web検索APIがダミーデータを返しています",
            severity="CRITICAL",
            affected_data={'api': 'brave_search', 'response': {'total_results': 0}}
        )
        
        # セッションサマリー出力
        summary = audit.export_session_summary('audit_summary.json')
        
        print("\n📊 監査ログサマリー:")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    
    print("\n✅ 監査ログシステムのテスト完了")


if __name__ == "__main__":
    main()