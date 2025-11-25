#!/usr/bin/env python3
"""
自動コード品質チェック・修正スクリプト
- エラー・警告を常に0に保つ
- ユーザーインタラクションなしで自動実行
- ログファイルに結果を記録
"""
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


def log_message(message):
    """ログメッセージを出力"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}"
    print(log_line)

    # ログファイルにも記録
    with open('quality_monitor.log', 'a', encoding='utf-8') as f:
        f.write(log_line + '\n')

def create_backup():
    """現在のコードのバックアップを作成"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'quality_backup_{timestamp}'
    backup_path = Path.cwd() / 'quality_backups' / backup_name
    backup_path.mkdir(parents=True, exist_ok=True)

    # Pythonファイルのみをバックアップ
    for py_file in Path.cwd().rglob('*.py'):
        if py_file.exists():
            rel_path = py_file.relative_to(Path.cwd())
            backup_file = backup_path / rel_path
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(py_file, backup_file)

    log_message(f"✅ バックアップ作成: {backup_path}")
    return str(backup_path)

def check_ruff():
    """Ruffでコード品質をチェック"""
    try:
        result = subprocess.run(
            ['python3', '-m', 'ruff', 'check', '.'],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            return True, 0

        # エラー数をカウント
        error_lines = [line for line in result.stdout.split('\n') if line.strip()]
        return False, len(error_lines)

    except Exception as e:
        log_message(f"❌ Ruffチェックエラー: {e}")
        return False, -1

def check_py_compile():
    """py_compileで構文チェック"""
    try:
        error_count = 0
        for py_file in Path.cwd().rglob('*.py'):
            if py_file.exists():
                result = subprocess.run(
                    ['python3', '-m', 'py_compile', str(py_file)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode != 0:
                    error_count += 1

        return error_count == 0, error_count

    except Exception as e:
        log_message(f"❌ py_compileチェックエラー: {e}")
        return False, -1

def auto_fix_ruff():
    """Ruffで自動修正を実行"""
    try:
        log_message("🔧 Ruff自動修正実行中...")
        result = subprocess.run(
            ['python3', '-m', 'ruff', 'check', '--fix', '.'],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            log_message("✅ Ruff自動修正完了")
            return True
        else:
            log_message(f"⚠️ Ruff自動修正部分成功: {result.stderr}")
            return False

    except Exception as e:
        log_message(f"❌ Ruff自動修正エラー: {e}")
        return False

def check_quality():
    """全体的なコード品質をチェック"""
    log_message("🔍 コード品質チェック中...")

    # Ruffチェック
    ruff_ok, ruff_errors = check_ruff()
    log_message(f"  Ruff: {'✅ OK' if ruff_ok else f'❌ {ruff_errors}件のエラー'}")

    # py_compileチェック
    py_ok, py_errors = check_py_compile()
    log_message(f"  py_compile: {'✅ OK' if py_ok else f'❌ {py_errors}件のエラー'}")

    total_errors = (0 if ruff_ok else ruff_errors) + (0 if py_ok else py_errors)
    status = 'clean' if total_errors == 0 else 'has_errors'

    return {
        'timestamp': datetime.now().isoformat(),
        'ruff_ok': ruff_ok,
        'ruff_errors': ruff_errors,
        'py_compile_ok': py_ok,
        'py_compile_errors': py_errors,
        'total_errors': total_errors,
        'status': status
    }

def auto_fix_all():
    """すべての問題を自動修正"""
    log_message("🔧 自動修正開始...")

    # バックアップ作成
    backup_path = create_backup()

    # Ruff自動修正
    ruff_fixed = auto_fix_ruff()

    # 修正後の再チェック
    log_message("🔍 修正後の再チェック...")
    final_check = check_quality()

    if final_check['status'] == 'clean':
        log_message("✅ すべての問題が解決されました！")
    else:
        log_message(f"⚠️ 一部の問題が残っています: {final_check['total_errors']}件")

    return {
        'backup_created': backup_path,
        'ruff_fixed': ruff_fixed,
        'final_status': final_check['status']
    }

def continuous_monitoring(interval_seconds=30, max_iterations=None):
    """継続的な監視を実行"""
    log_message(f"🔄 継続的監視開始 (間隔: {interval_seconds}秒)")
    if max_iterations:
        log_message(f"最大実行回数: {max_iterations}")

    iteration = 0
    try:
        while True:
            iteration += 1
            if max_iterations and iteration > max_iterations:
                log_message(f"最大実行回数 {max_iterations} に達しました")
                break

            log_message("="*50)
            log_message(f"🕐 実行回数: {iteration}")

            # 品質チェック
            quality_report = check_quality()

            # 問題がある場合は自動修正
            if quality_report['status'] != 'clean':
                log_message(f"⚠️ 問題を検出: {quality_report['total_errors']}件")
                log_message("自動修正を実行します...")

                fix_report = auto_fix_all()
                log_message(f"✅ 修正完了: {fix_report['backup_created']}")

                # 修正後の最終チェック
                final_check = check_quality()
                if final_check['status'] == 'clean':
                    log_message("🎉 すべての問題が解決されました！")
                else:
                    log_message(f"⚠️ 一部の問題が残っています: {final_check['total_errors']}件")
            else:
                log_message("✅ コード品質良好 - エラー・警告なし")

            # 監視間隔待機
            log_message(f"⏳ {interval_seconds}秒後に再チェック...")
            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        log_message("🛑 監視を停止しました")
    except Exception as e:
        log_message(f"❌ 監視中エラー: {e}")

def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python3 auto_quality_check.py check     # 単発チェック")
        print("  python3 auto_quality_check.py fix       # 自動修正")
        print("  python3 auto_quality_check.py monitor   # 継続的監視")
        print("  python3 auto_quality_check.py monitor 60 5  # 60秒間隔で5回実行")
        sys.exit(1)

    command = sys.argv[1]

    if command == "check":
        # 単発チェック
        quality_report = check_quality()
        log_message(f"📊 品質レポート: {quality_report['status']}")
        log_message(f"  総エラー数: {quality_report['total_errors']}")

        # エラーがある場合は終了コード1で終了
        if quality_report['status'] != 'clean':
            sys.exit(1)
        else:
            sys.exit(0)

    elif command == "fix":
        # 自動修正
        quality_report = check_quality()
        if quality_report['status'] != 'clean':
            fix_report = auto_fix_all()
            log_message(f"修正完了: {fix_report['backup_created']}")

            # 修正後の最終チェック
            final_check = check_quality()
            if final_check['status'] == 'clean':
                log_message("✅ 修正成功")
                sys.exit(0)
            else:
                log_message("❌ 修正失敗")
                sys.exit(1)
        else:
            log_message("✅ 修正する問題がありません")
            sys.exit(0)

    elif command == "monitor":
        # 継続的監視
        interval = 30
        max_iterations = None

        if len(sys.argv) > 2:
            try:
                interval = int(sys.argv[2])
            except ValueError:
                pass

        if len(sys.argv) > 3:
            try:
                max_iterations = int(sys.argv[3])
            except ValueError:
                pass

        continuous_monitoring(interval, max_iterations)

    else:
        print(f"❌ 無効なコマンド: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
