#!/usr/bin/env python3
"""
Fail-Fastバリデーター
Fail-Fast Validator for Early Error Detection

エラーを早期に検出し、不正確なデータの流通を防ぐシステム。
「動いているふり」をせず、問題があれば即座に停止します。
"""

import logging
import traceback
from typing import Any, Dict, List, Optional, Callable, TypeVar, Union
from functools import wraps
from datetime import datetime
import json
import sys

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

T = TypeVar('T')


class ValidationError(Exception):
    """検証エラーの基底クラス"""
    pass


class PreconditionError(ValidationError):
    """前提条件エラー"""
    pass


class PostconditionError(ValidationError):
    """事後条件エラー"""
    pass


class InvariantError(ValidationError):
    """不変条件エラー"""
    pass


class DataIntegrityError(ValidationError):
    """データ整合性エラー"""
    pass


class FailFastValidator:
    """Fail-Fastバリデーター"""
    
    def __init__(self, strict_mode: bool = True):
        """
        初期化
        
        Args:
            strict_mode: 厳格モード（Trueの場合、わずかな問題でも停止）
        """
        self.strict_mode = strict_mode
        self.validation_history: List[Dict[str, Any]] = []
        self.error_count = 0
        self.warning_count = 0
        
    def validate_precondition(self, 
                             condition: Callable[[], bool],
                             error_message: str,
                             context: Optional[Dict[str, Any]] = None):
        """
        前提条件の検証
        
        Args:
            condition: 検証条件（Trueを返すべき）
            error_message: エラーメッセージ
            context: コンテキスト情報
        
        Raises:
            PreconditionError: 前提条件を満たさない場合
        """
        try:
            if not condition():
                self._log_validation_failure("PRECONDITION", error_message, context)
                raise PreconditionError(f"前提条件エラー: {error_message}")
        except Exception as e:
            if not isinstance(e, PreconditionError):
                self._log_validation_failure("PRECONDITION_CHECK_ERROR", str(e), context)
                raise PreconditionError(f"前提条件チェック中のエラー: {e}")
            raise
    
    def validate_postcondition(self,
                              condition: Callable[[], bool],
                              error_message: str,
                              context: Optional[Dict[str, Any]] = None):
        """
        事後条件の検証
        
        Args:
            condition: 検証条件
            error_message: エラーメッセージ
            context: コンテキスト情報
        
        Raises:
            PostconditionError: 事後条件を満たさない場合
        """
        try:
            if not condition():
                self._log_validation_failure("POSTCONDITION", error_message, context)
                raise PostconditionError(f"事後条件エラー: {error_message}")
        except Exception as e:
            if not isinstance(e, PostconditionError):
                self._log_validation_failure("POSTCONDITION_CHECK_ERROR", str(e), context)
                raise PostconditionError(f"事後条件チェック中のエラー: {e}")
            raise
    
    def validate_invariant(self,
                          condition: Callable[[], bool],
                          error_message: str,
                          context: Optional[Dict[str, Any]] = None):
        """
        不変条件の検証
        
        Args:
            condition: 検証条件
            error_message: エラーメッセージ
            context: コンテキスト情報
        
        Raises:
            InvariantError: 不変条件を満たさない場合
        """
        try:
            if not condition():
                self._log_validation_failure("INVARIANT", error_message, context)
                raise InvariantError(f"不変条件エラー: {error_message}")
        except Exception as e:
            if not isinstance(e, InvariantError):
                self._log_validation_failure("INVARIANT_CHECK_ERROR", str(e), context)
                raise InvariantError(f"不変条件チェック中のエラー: {e}")
            raise
    
    def validate_not_dummy(self,
                          data: Any,
                          field_name: str = "data") -> Any:
        """
        ダミーデータでないことを検証
        
        Args:
            data: 検証対象データ
            field_name: フィールド名
        
        Returns:
            検証済みデータ
        
        Raises:
            DataIntegrityError: ダミーデータの場合
        """
        # ダミーデータのパターン
        dummy_patterns = [
            data is None,
            data == 0 and field_name in ['total_results', 'count', 'score'],
            data == [] and field_name in ['results', 'data', 'items'],
            data == {} and field_name in ['response', 'data'],
            isinstance(data, str) and data in ['', 'dummy', 'test', 'placeholder', 'TODO', 'FIXME'],
            isinstance(data, dict) and data.get('source') in ['fallback', 'simulated', 'mock'],
            isinstance(data, dict) and data.get('total_results') == 0,
        ]
        
        if any(dummy_patterns):
            self._log_validation_failure(
                "DUMMY_DATA_DETECTED",
                f"{field_name}にダミーデータを検出",
                {'field': field_name, 'value': data}
            )
            if self.strict_mode:
                raise DataIntegrityError(
                    f"ダミーデータ検出: {field_name}={data}\n"
                    f"実際のAPIレスポンスを取得してください。"
                )
        
        return data
    
    def validate_api_response(self,
                            response: Dict[str, Any],
                            required_fields: List[str]) -> Dict[str, Any]:
        """
        APIレスポンスの検証
        
        Args:
            response: APIレスポンス
            required_fields: 必須フィールド
        
        Returns:
            検証済みレスポンス
        
        Raises:
            DataIntegrityError: 不正なレスポンスの場合
        """
        # Null/Emptyチェック
        if not response:
            raise DataIntegrityError("APIレスポンスが空です")
        
        # 必須フィールドチェック
        missing_fields = [f for f in required_fields if f not in response]
        if missing_fields:
            raise DataIntegrityError(
                f"APIレスポンスに必須フィールドがありません: {missing_fields}"
            )
        
        # ダミーレスポンスチェック
        if response.get('source') in ['fallback', 'simulated', 'default']:
            raise DataIntegrityError(
                f"実際のAPIレスポンスではありません: source={response.get('source')}"
            )
        
        # 結果の妥当性チェック
        if 'total_results' in response:
            self.validate_not_dummy(response['total_results'], 'total_results')
        
        if 'results' in response:
            self.validate_not_dummy(response['results'], 'results')
        
        return response
    
    def validate_score_range(self,
                           score: float,
                           min_val: float = 0.0,
                           max_val: float = 10.0,
                           person_name: Optional[str] = None) -> float:
        """
        スコア範囲の検証
        
        Args:
            score: スコア値
            min_val: 最小値
            max_val: 最大値
            person_name: 人物名（ログ用）
        
        Returns:
            検証済みスコア
        
        Raises:
            DataIntegrityError: 範囲外の場合
        """
        if not min_val <= score <= max_val:
            context = {'score': score, 'range': f'{min_val}-{max_val}'}
            if person_name:
                context['person'] = person_name
            
            self._log_validation_failure("SCORE_OUT_OF_RANGE", "スコア範囲外", context)
            
            raise DataIntegrityError(
                f"スコア{score}が範囲外です（{min_val}-{max_val}）"
                f"{f' 人物: {person_name}' if person_name else ''}"
            )
        
        return score
    
    def validate_famous_person_score(self,
                                   person_id: str,
                                   person_name: str,
                                   score: float,
                                   min_required: float = 7.0):
        """
        有名人のスコア検証
        
        Args:
            person_id: 人物ID
            person_name: 人物名
            score: スコア
            min_required: 最低必要スコア
        
        Raises:
            DataIntegrityError: スコアが低すぎる場合
        """
        # 有名人リスト（実際はconfigから読み込むべき）
        famous_persons = {
            'P000013': {'name': 'HIKAKIN', 'min_score': 7.0},
            'P000001': {'name': '宮崎駿', 'min_score': 8.0},
            'P000002': {'name': 'ビートたけし', 'min_score': 7.5},
        }
        
        if person_id in famous_persons:
            expected_min = famous_persons[person_id]['min_score']
            if score < expected_min:
                self._log_validation_failure(
                    "FAMOUS_PERSON_LOW_SCORE",
                    f"{person_name}のスコアが異常に低い",
                    {
                        'person_id': person_id,
                        'person_name': person_name,
                        'actual_score': score,
                        'expected_min': expected_min
                    }
                )
                
                if self.strict_mode:
                    raise DataIntegrityError(
                        f"有名人{person_name}(ID:{person_id})のスコア{score}が"
                        f"最低基準{expected_min}未満です。\n"
                        f"Web検索APIが正しく動作していない可能性があります。"
                    )
    
    def validate_deletion_rate(self,
                              total: int,
                              deleted: int,
                              max_rate: float = 0.20):
        """
        削除率の検証
        
        Args:
            total: 総数
            deleted: 削除数
            max_rate: 最大許容削除率
        
        Raises:
            DataIntegrityError: 削除率が異常な場合
        """
        if total == 0:
            return
        
        deletion_rate = deleted / total
        
        if deletion_rate > max_rate:
            self._log_validation_failure(
                "HIGH_DELETION_RATE",
                f"削除率{deletion_rate:.1%}が異常",
                {
                    'total': total,
                    'deleted': deleted,
                    'rate': deletion_rate,
                    'max_allowed': max_rate
                }
            )
            
            # 45%超は明らかに異常
            if deletion_rate > 0.45:
                raise DataIntegrityError(
                    f"削除率{deletion_rate:.1%}は異常に高い値です。\n"
                    f"総数{total}件中{deleted}件が削除対象となっています。\n"
                    f"Web検索スコアが正しく計算されていない可能性があります。"
                )
    
    def fail_fast_decorator(self, 
                           precondition: Optional[Callable] = None,
                           postcondition: Optional[Callable] = None,
                           invariant: Optional[Callable] = None):
        """
        Fail-Fastデコレーター
        
        Args:
            precondition: 前提条件
            postcondition: 事後条件
            invariant: 不変条件
        
        Returns:
            デコレーター関数
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args, **kwargs) -> T:
                # 前提条件チェック
                if precondition:
                    self.validate_precondition(
                        lambda: precondition(*args, **kwargs),
                        f"{func.__name__}の前提条件失敗"
                    )
                
                # 不変条件チェック（実行前）
                if invariant:
                    self.validate_invariant(
                        lambda: invariant(*args, **kwargs),
                        f"{func.__name__}の不変条件失敗（実行前）"
                    )
                
                try:
                    # 関数実行
                    result = func(*args, **kwargs)
                    
                    # 事後条件チェック
                    if postcondition:
                        self.validate_postcondition(
                            lambda: postcondition(result),
                            f"{func.__name__}の事後条件失敗"
                        )
                    
                    # 不変条件チェック（実行後）
                    if invariant:
                        self.validate_invariant(
                            lambda: invariant(*args, **kwargs),
                            f"{func.__name__}の不変条件失敗（実行後）"
                        )
                    
                    return result
                    
                except Exception as e:
                    self._log_validation_failure(
                        "FUNCTION_EXECUTION_ERROR",
                        f"{func.__name__}実行中のエラー",
                        {'error': str(e), 'traceback': traceback.format_exc()}
                    )
                    raise
            
            return wrapper
        return decorator
    
    def _log_validation_failure(self,
                              failure_type: str,
                              message: str,
                              context: Optional[Dict[str, Any]] = None):
        """
        検証失敗のログ記録
        
        Args:
            failure_type: 失敗タイプ
            message: メッセージ
            context: コンテキスト
        """
        entry = {
            'timestamp': datetime.now().isoformat(),
            'type': failure_type,
            'message': message,
            'context': context or {},
            'stack_trace': traceback.format_stack()
        }
        
        self.validation_history.append(entry)
        self.error_count += 1
        
        logger.error(f"VALIDATION_FAILURE: {failure_type} - {message}")
        if context:
            logger.error(f"Context: {json.dumps(context, ensure_ascii=False)[:500]}")
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """
        検証サマリーの取得
        
        Returns:
            サマリー情報
        """
        return {
            'total_validations': len(self.validation_history),
            'error_count': self.error_count,
            'warning_count': self.warning_count,
            'strict_mode': self.strict_mode,
            'recent_failures': self.validation_history[-5:] if self.validation_history else []
        }


# 使用例
def process_person_with_validation(person_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fail-Fast検証を適用した人物データ処理
    
    Args:
        person_data: 人物データ
    
    Returns:
        処理済みデータ
    """
    validator = FailFastValidator(strict_mode=True)
    
    # 前提条件：必須フィールドが存在
    validator.validate_precondition(
        lambda: all(k in person_data for k in ['person_id', 'person_name']),
        "必須フィールドが不足",
        {'data': person_data}
    )
    
    # APIレスポンスを取得（仮想）
    api_response = {
        'total_results': 0,  # これはダミーデータ
        'results': [],
        'source': 'simulated'
    }
    
    # APIレスポンスを検証（ダミーデータなのでエラーになるはず）
    try:
        validated_response = validator.validate_api_response(
            api_response,
            ['total_results', 'results']
        )
    except DataIntegrityError as e:
        logger.error(f"API検証失敗: {e}")
        raise  # Fail-Fast: 即座に停止
    
    # この行には到達しない（上でエラー）
    return person_data


def main():
    """テスト実行"""
    print("="*60)
    print("Fail-Fastバリデーター テスト")
    print("="*60)
    
    validator = FailFastValidator(strict_mode=True)
    
    # テスト1: ダミーデータ検出
    print("\n🔍 Test 1: ダミーデータ検出")
    try:
        validator.validate_not_dummy(0, 'total_results')
    except DataIntegrityError as e:
        print(f"✅ 期待通りエラー: {e}")
    
    # テスト2: APIレスポンス検証
    print("\n🔍 Test 2: ダミーAPIレスポンス検証")
    dummy_response = {
        'total_results': 0,
        'results': [],
        'source': 'simulated'
    }
    try:
        validator.validate_api_response(dummy_response, ['total_results', 'results'])
    except DataIntegrityError as e:
        print(f"✅ 期待通りエラー: {e}")
    
    # テスト3: 有名人スコア検証
    print("\n🔍 Test 3: HIKAKINの低スコア検証")
    try:
        validator.validate_famous_person_score('P000013', 'HIKAKIN', 3.3)
    except DataIntegrityError as e:
        print(f"✅ 期待通りエラー: {e}")
    
    # テスト4: 高削除率検証
    print("\n🔍 Test 4: 45.6%削除率の検証")
    try:
        validator.validate_deletion_rate(4701, 2145)
    except DataIntegrityError as e:
        print(f"✅ 期待通りエラー: {e}")
    
    # サマリー表示
    print("\n📊 検証サマリー:")
    summary = validator.get_validation_summary()
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    
    print("\n✅ Fail-Fastバリデーターのテスト完了")


if __name__ == "__main__":
    main()