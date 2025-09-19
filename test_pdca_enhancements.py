#!/usr/bin/env python3
"""
PDCAシステム機能強化テスト
時間見積もり違反と思考パターン監視の動作確認
"""

import sys
import json
from pathlib import Path
from pdca_guardian import PDCAGuardian
from pdca_management_system import PDCAManagementSystem
from quality_gates import QualityGateSystem

def test_proposal_checking():
    """提案チェック機能のテスト"""
    print("\n" + "="*60)
    print("🧪 提案チェック機能テスト")
    print("="*60)
    
    guardian = PDCAGuardian()
    
    # 問題のある提案例（実際に私が提案してしまった内容）
    bad_proposal = """
    ハイブリッドアプローチで処理を高速化します：
    1. 上位100件のみAPIで詳細確認（5分）
    2. 残りは簡易スコアリング（2分）
    3. 合計7-10分で完了可能
    """
    
    print("\n❌ 問題のある提案例:")
    print(bad_proposal)
    
    violations = guardian.check_proposal(bad_proposal)
    
    if violations:
        print("\n🚨 検出された違反:")
        for v in violations:
            print(f"  - {v}")
    
    # 正しい提案例
    good_proposal = """
    品質優先の完全処理を実施します：
    1. 全データに対してAPI検証（3-4時間）
    2. 完全な品質チェック（1時間）
    3. データ検証と監査ログ（30分）
    4. 合計5-8時間で品質保証付き完了
    """
    
    print("\n✅ 正しい提案例:")
    print(good_proposal)
    
    violations = guardian.check_proposal(good_proposal)
    
    if violations:
        print("\n違反検出:")
        for v in violations:
            print(f"  - {v}")
    else:
        print("\n✨ 違反なし - 品質優先の提案")

def test_thought_monitoring():
    """思考パターン監視機能のテスト"""
    print("\n" + "="*60)
    print("🧠 思考パターン監視テスト")
    print("="*60)
    
    system = PDCAManagementSystem()
    
    # 問題のある思考パターン
    problematic_thought = """
    時間短縮のため、ハイブリッド方式を採用。
    上位50件のみ処理して、残りは簡易版で対応。
    これで処理時間を90%削減できます。
    """
    
    print("\n監視対象テキスト:")
    print(problematic_thought)
    
    result = system.monitor_thought_patterns(thought_text=problematic_thought)
    
    print(f"\n品質スコア: {result['quality_score']}")
    print(f"違反検出数: {result['violations_found']}")
    
    if result['violations']:
        print("\n検出された問題パターン:")
        for v in result['violations']:
            print(f"  - タイプ: {v['type']}")
            print(f"    重要度: {v['severity']}")
    
    if result['recommendations']:
        print("\n改善提案:")
        for rec in result['recommendations']:
            print(f"  {rec}")

def test_time_estimation_gate():
    """時間見積もりゲートのテスト"""
    print("\n" + "="*60)
    print("⏱️ 時間見積もりゲートテスト")
    print("="*60)
    
    # テスト用の問題のあるスクリプトを作成
    test_script = """
#!/usr/bin/env python3
# 高速処理版 - 5時間の処理を10分に短縮！

def process_data():
    # ハイブリッドアプローチで処理時間を90%削減
    # 部分的な実行で効率を優先
    print("処理を10分で完了します")
    
    # TODO: 簡易版の実装
    return quick_process()  # 時間短縮のため簡易処理
"""
    
    test_file = Path("test_time_violation.py")
    test_file.write_text(test_script)
    
    print(f"\nテストファイル作成: {test_file}")
    
    # 品質ゲートチェック
    gate_system = QualityGateSystem()
    passed, results = gate_system.check_script(str(test_file))
    
    print(f"\n品質ゲート結果: {'✅ 通過' if passed else '❌ 失敗'}")
    
    # 時間見積もりゲートの結果を表示
    for result in results:
        if result['name'] == '時間見積もり妥当性':
            print(f"\n時間見積もりゲート:")
            print(f"  ステータス: {result['status']}")
            print(f"  メッセージ: {result['message']}")
            if result.get('details'):
                print(f"  詳細: {json.dumps(result['details'], ensure_ascii=False, indent=4)}")
    
    # テストファイル削除
    test_file.unlink()
    print(f"\nテストファイル削除: {test_file}")

def main():
    """メインテスト実行"""
    print("\n" + "="*70)
    print("🚀 PDCAシステム機能強化テスト開始")
    print("="*70)
    print("\n以下の新機能をテストします:")
    print("1. 提案段階チェック機能（pdca_guardian.py）")
    print("2. 思考パターン監視機能（pdca_management_system.py）") 
    print("3. 時間見積もりゲート（quality_gates.py）")
    
    # 各テスト実行
    test_proposal_checking()
    test_thought_monitoring()
    test_time_estimation_gate()
    
    print("\n" + "="*70)
    print("✅ すべてのテスト完了")
    print("="*70)
    print("\n🎯 結論:")
    print("PDCAシステムが強化され、品質妥協提案を事前に検出・防止できるようになりました。")
    print("「5時間を7-10分に短縮」のような非現実的な提案は自動的に拒否されます。")

if __name__ == "__main__":
    main()