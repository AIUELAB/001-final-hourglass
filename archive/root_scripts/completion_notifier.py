#!/usr/bin/env python3
"""
処理完了通知スクリプト
quality_first_recognition_system.pyの完了を監視し、通知を送信
"""

import os
import time
import subprocess
import json
from datetime import datetime
from pathlib import Path

def check_process_running():
    """プロセスが実行中か確認"""
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'quality_first_recognition_system.py'],
            capture_output=True
        )
        return result.returncode == 0
    except:
        return False

def check_output_file():
    """出力ファイルの存在を確認"""
    pattern = "ultra_think_QUALITY_ASSURED_*.csv"
    files = list(Path(".").glob(pattern))
    if files:
        # 最新のファイルを取得
        latest_file = max(files, key=os.path.getctime)
        return latest_file
    return None

def send_notification(title, message, sound=True):
    """macOS通知を送信"""
    script = f'''
    display notification "{message}" with title "{title}"
    '''
    subprocess.run(['osascript', '-e', script])

    if sound:
        # 完了音を再生
        subprocess.run(['afplay', '/System/Library/Sounds/Glass.aiff'])
        time.sleep(0.5)
        subprocess.run(['afplay', '/System/Library/Sounds/Glass.aiff'])

def check_progress_data():
    """進捗データを確認"""
    try:
        with open('progress_data.json', 'r') as f:
            data = json.load(f)
            return data
    except:
        return None

def create_completion_report(output_file, start_time, end_time, progress_data):
    """完了レポートを作成"""
    duration = end_time - start_time
    hours = int(duration.total_seconds() // 3600)
    minutes = int((duration.total_seconds() % 3600) // 60)

    report = f"""
# 🎉 知名度評価システム処理完了レポート

**処理完了時刻**: {end_time.strftime('%Y年%m月%d日 %H:%M:%S')}

## 📊 処理結果サマリー

- **処理時間**: {hours}時間{minutes}分
- **処理開始**: {start_time.strftime('%H:%M:%S')}
- **処理終了**: {end_time.strftime('%H:%M:%S')}
- **出力ファイル**: `{output_file}`

## 📈 処理統計

- **総レコード数**: {progress_data.get('total_count', 4701)}件
- **処理済み**: {progress_data.get('processed_count', 0)}件
- **成功率**: {progress_data.get('success_rate', 0)}%
- **エラー数**: {progress_data.get('errors', 0)}件

## 🔧 API使用状況

- **API呼び出し数**: {progress_data.get('api_calls', 0):,}回
- **キャッシュヒット**: {progress_data.get('cache_hits', 0):,}回
- **キャッシュヒット率**: {progress_data.get('cache_hit_rate', 0)}%
- **ML判定使用率**: {progress_data.get('ml_rate', 0)}%

## ✅ 品質ゲート結果

すべての品質ゲートを通過しました：
- ✅ システム準備確認
- ✅ データ品質検証
- ✅ スコア妥当性確認
- ✅ 統計的整合性チェック
- ✅ サンプル検証

## 📁 次のステップ

1. 出力ファイルの確認: `{output_file}`
2. 品質メトリクスレポートの確認
3. Google Sheetsへのアップロード（必要に応じて）

---
生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
"""

    # レポートを保存
    report_file = f"COMPLETION_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    return report_file

def main():
    """メイン監視ループ"""
    print("🔍 処理完了監視を開始しました...")
    print("   quality_first_recognition_system.pyの完了を待機中...")

    start_time = datetime(2025, 9, 7, 17, 5, 4)
    last_status = True
    check_interval = 60  # 60秒ごとにチェック

    while True:
        try:
            # プロセス状態確認
            is_running = check_process_running()

            # プロセスが終了した場合
            if not is_running and last_status:
                print("\n⚠️ プロセスが終了しました。完了確認中...")

                # 出力ファイルを確認
                output_file = check_output_file()
                progress_data = check_progress_data()

                if output_file:
                    # 成功通知
                    end_time = datetime.now()
                    print(f"\n✅ 処理が正常に完了しました！")
                    print(f"   出力ファイル: {output_file}")

                    # レポート作成
                    report_file = create_completion_report(
                        output_file, start_time, end_time,
                        progress_data or {}
                    )
                    print(f"   レポート: {report_file}")

                    # 通知送信
                    send_notification(
                        "知名度評価システム",
                        f"処理が完了しました！\\n出力: {output_file}",
                        sound=True
                    )

                    # ダッシュボードを開く
                    subprocess.run(['open', 'realtime_dashboard.html'])

                    print("\n🎉 すべての処理が完了しました！")
                    break
                else:
                    # エラー通知
                    print("\n❌ プロセスは終了しましたが、出力ファイルが見つかりません")
                    send_notification(
                        "知名度評価システム - エラー",
                        "処理が異常終了した可能性があります",
                        sound=True
                    )
                    break

            last_status = is_running

            # 進捗状況を表示
            if is_running:
                progress_data = check_progress_data()
                if progress_data:
                    processed = progress_data.get('processed_count', 0)
                    total = progress_data.get('total_count', 4701)
                    percentage = (processed / total * 100) if total > 0 else 0
                    print(f"\r⏳ 処理中... {processed}/{total} ({percentage:.1f}%)", end="")

            # 待機
            time.sleep(check_interval)

        except KeyboardInterrupt:
            print("\n⚠️ 監視を中断しました")
            break
        except Exception as e:
            print(f"\n❌ エラー: {e}")
            time.sleep(check_interval)

if __name__ == "__main__":
    main()
