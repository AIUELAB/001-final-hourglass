#!/usr/bin/env python3
"""
EPUP品質自動改善スクリプト

バックグラウンドで以下のタスクを順次実行:
1. episode_drama_quality改善
2. content_density低品質改善
3. 新規人物追加

使用方法:
    nohup python scripts/auto_improve_all.py > logs/auto_improve.log 2>&1 &

環境変数:
    ANTHROPIC_API_KEY: Anthropic APIキー
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

# ログディレクトリ
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# ログファイル
LOG_FILE = LOG_DIR / f"auto_improve_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"


def log(message: str):
    """ログ出力"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}"
    print(log_message, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_message + "\n")


def run_script(script_path: str, args: list[str] = None) -> tuple[bool, str]:
    """スクリプトを実行"""
    cmd = ["./venv/bin/python", script_path]
    if args:
        cmd.extend(args)

    log(f"実行: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10分タイムアウト
            env={**os.environ, "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", "")},
        )

        if result.returncode == 0:
            log(f"✅ 成功: {script_path}")
            return True, result.stdout
        else:
            log(f"❌ 失敗: {script_path}")
            log(f"エラー: {result.stderr[:500]}")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        log(f"⏰ タイムアウト: {script_path}")
        return False, "Timeout"
    except Exception as e:
        log(f"❌ 例外: {e}")
        return False, str(e)


def get_current_stats() -> dict:
    """現在の統計を取得"""
    import pandas as pd

    csv_path = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
    df = pd.read_csv(csv_path)

    return {
        "total_episodes": len(df),
        "unique_persons": df["person_id"].nunique(),
        "avg_drama_score": df["composite_score"].mean() if "composite_score" in df.columns else 0,
    }


def phase1_drama_improvement():
    """Phase 1: ドラマ品質改善"""
    log("=" * 60)
    log("Phase 1: ドラマ品質改善")
    log("=" * 60)

    # 低ドラマエピソードの改善を3回繰り返す
    for i in range(3):
        log(f"バッチ {i + 1}/3")
        success, output = run_script("scripts/improve_low_drama_episodes.py", ["--limit", "30", "--execute"])
        if not success:
            log(f"バッチ {i + 1} 失敗、スキップ")
            continue

        # 改善がなくなったら終了
        if "改善対象: 0件" in output or "処理対象なし" in output or "対象: 0件" in output:
            log("改善対象がなくなりました")
            break

    log("Phase 1 完了")


def phase2_content_density():
    """Phase 2: 内容密度改善"""
    log("=" * 60)
    log("Phase 2: 内容密度改善")
    log("=" * 60)

    # 内容密度改善を3回繰り返す
    for i in range(3):
        log(f"バッチ {i + 1}/3")
        success, output = run_script("scripts/improve_content_density.py", ["--batch-size", "50", "--execute"])
        if not success:
            log(f"バッチ {i + 1} 失敗、スキップ")

        # 改善がなくなったら終了
        if "問題エピソード: 0件" in output:
            log("改善対象がなくなりました")
            break

    log("Phase 2 完了")


def phase3_person_expansion():
    """Phase 3: 新規人物追加"""
    log("=" * 60)
    log("Phase 3: 新規人物追加")
    log("=" * 60)

    # yumeilistからインポート
    log("yumeilistインポート試行...")
    success, output = run_script("scripts/import_from_yumeilist.py", ["--limit", "30", "--execute"])

    if not success or "追加: 0件" in output:
        log("yumeilistからの追加なし")

    log("Phase 3 完了")


def phase4_reclassify():
    """Phase 4: ACHIEVEMENT再分類"""
    log("=" * 60)
    log("Phase 4: ACHIEVEMENT再分類")
    log("=" * 60)

    success, output = run_script("scripts/reclassify_suspicious_achievement.py", ["--batch-size", "30", "--execute"])

    log("Phase 4 完了")


def phase5_final_evaluation():
    """Phase 5: 最終評価"""
    log("=" * 60)
    log("Phase 5: 最終EPUP評価")
    log("=" * 60)

    success, output = run_script("scripts/evaluate_epup_effectiveness.py", [])

    # 結果をパース
    if success:
        # レポートファイルを探す
        import glob

        reports = sorted(glob.glob("reports/epup_evaluation_*.json"), reverse=True)
        if reports:
            with open(reports[0], encoding="utf-8") as f:
                data = json.load(f)

            log("=" * 60)
            log("最終結果")
            log("=" * 60)
            log(f"総エピソード数: {data.get('total_episodes', 'N/A')}")
            log(f"EPUPスコア: {data.get('epup_score', {}).get('total_score', 'N/A')}")
            log(f"グレード: {data.get('epup_score', {}).get('grade', 'N/A')}")

    log("Phase 5 完了")


def update_session_status():
    """セッション状態を更新"""
    import glob

    # 最新のEPUPレポートを取得
    reports = sorted(glob.glob("reports/epup_evaluation_*.json"), reverse=True)
    if not reports:
        return

    with open(reports[0], encoding="utf-8") as f:
        data = json.load(f)

    session_data = {
        "session_id": f"auto_improve_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now().isoformat(),
        "status": "completed",
        "summary": "自動品質改善完了",
        "verification_results": {
            "total_episodes": data.get("total_episodes", 0),
            "epup_score": data.get("epup_score", {}).get("total_score", 0),
            "grade": data.get("epup_score", {}).get("grade", "N/A"),
        },
        "log_file": str(LOG_FILE),
    }

    session_path = PROJECT_ROOT / ".session/current_session.json"
    with open(session_path, "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)

    log(f"セッション状態を更新: {session_path}")


def main():
    """メイン処理"""
    log("=" * 60)
    log("EPUP品質自動改善スクリプト開始")
    log("=" * 60)

    # API キー確認
    if not os.getenv("ANTHROPIC_API_KEY"):
        log("❌ ANTHROPIC_API_KEY が設定されていません")
        sys.exit(1)

    # 開始時の統計
    try:
        stats = get_current_stats()
        log(f"開始時: {stats['total_episodes']}件, {stats['unique_persons']}人物")
    except Exception as e:
        log(f"統計取得エラー: {e}")

    # 各フェーズを実行
    try:
        phase1_drama_improvement()
        phase2_content_density()
        phase3_person_expansion()
        phase4_reclassify()
        phase5_final_evaluation()
        update_session_status()
    except Exception as e:
        log(f"❌ 致命的エラー: {e}")
        import traceback

        log(traceback.format_exc())
        sys.exit(1)

    # 終了時の統計
    try:
        stats = get_current_stats()
        log(f"終了時: {stats['total_episodes']}件, {stats['unique_persons']}人物")
    except Exception as e:
        log(f"統計取得エラー: {e}")

    log("=" * 60)
    log("✅ 全フェーズ完了")
    log(f"ログファイル: {LOG_FILE}")
    log("=" * 60)


if __name__ == "__main__":
    main()
