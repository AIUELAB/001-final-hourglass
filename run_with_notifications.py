#!/usr/bin/env python3
"""
通知システム統合ランナー
任意のPythonスクリプトを音声通知付きで実行
"""

import subprocess
import sys
import time

from simple_notification import notify_complete, notify_error, notify_success, notify_waiting


def run_script_with_notifications(script_path: str, *args):
    """スクリプトを通知付きで実行"""
    
    script_name = script_path.split('/')[-1].replace('.py', '')
    
    print(f"🚀 {script_name} を実行します...")
    print("=" * 50)
    
    start_time = time.time()
    
    try:
        # スクリプト実行
        result = subprocess.run(
            ["python", script_path] + list(args),
            capture_output=False,
            text=True,
            check=True
        )
        
        # 成功通知
        elapsed = time.time() - start_time
        notify_success(f"{script_name} が正常に完了しました！")
        notify_complete(f"実行時間: {elapsed:.1f}秒")
        
        return 0
        
    except subprocess.CalledProcessError as e:
        # エラー通知
        notify_error(f"{script_name} の実行中にエラーが発生しました")
        return e.returncode
        
    except KeyboardInterrupt:
        # 中断通知
        print("\n⚠️ ユーザーによって中断されました")
        return 130
        
    finally:
        # 待機通知
        notify_waiting("Claude Codeが次の指示を待っています...")

def run_data_quality_with_notifications():
    """データ品質監査を通知付きで実行"""
    
    print("🔍 データ品質監査を開始します...")
    
    import json

    from data_quality_audit_improved import ImprovedDataQualityAuditor
    
    try:
        # データ読み込み
        with open('final_12410_firebase_20250822_201828.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 監査実行
        auditor = ImprovedDataQualityAuditor()
        report = auditor.audit_data(data)
        
        # 結果計算
        total = report['summary']['total_records']
        issues = report['summary']['issues_found']
        quality_score = ((total - issues) / total * 100) if total > 0 else 0
        
        # 結果表示
        print("\n📊 監査結果:")
        print(f"  総レコード数: {total:,}")
        print(f"  問題件数: {issues:,}")
        print(f"  品質スコア: {quality_score:.1f}%")
        
        # スコアに応じた通知
        if quality_score >= 90:
            notify_success(f"優秀な品質スコア: {quality_score:.1f}%")
        elif quality_score >= 70:
            notify_complete(f"品質スコア: {quality_score:.1f}%")
        else:
            notify_error(f"品質改善が必要: {quality_score:.1f}%")
            
        return report
        
    except Exception as e:
        notify_error(f"監査エラー: {str(e)}")
        raise e
    finally:
        notify_waiting("監査完了。次の操作をお待ちしています...")

def main():
    """メイン処理"""
    
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python run_with_notifications.py <script.py> [args...]")
        print("  python run_with_notifications.py --audit  # データ品質監査")
        print("\n例:")
        print("  python run_with_notifications.py test_data_quality_improved.py")
        print("  python run_with_notifications.py data_quality_audit.py")
        return 1
    
    if sys.argv[1] == "--audit":
        # データ品質監査モード
        run_data_quality_with_notifications()
        return 0
    else:
        # 通常のスクリプト実行
        return run_script_with_notifications(sys.argv[1], *sys.argv[2:])

if __name__ == "__main__":
    exit_code = main()
    
    # 最終通知
    print("\n" + "=" * 50)
    notify_complete("Claude Codeの処理が完了しました")
    print("🎵 音声通知システムが有効です")
    
    sys.exit(exit_code)