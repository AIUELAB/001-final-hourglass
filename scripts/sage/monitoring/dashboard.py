"""
SAGE Monitoring Dashboard - Phase 7C

Streamlitベースのリアルタイム監視ダッシュボード。
KPI、品質、コスト、在庫状況を可視化。

起動方法:
    streamlit run scripts/sage/monitoring/dashboard.py --server.port 8501
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Streamlit インポート（オプショナル）
try:
    import streamlit as st

    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

from scripts.sage.monitoring.alerts import AlertManager, AlertSeverity, console_notifier


# ==============================================================================
# 設定
# ==============================================================================

DASHBOARD_CONFIG = {
    "page_title": "SAGE 監視ダッシュボード",
    "page_icon": "🎯",
    "layout": "wide",
    "refresh_interval_seconds": 300,  # 5分
    "master_csv_path": "preserved/data/MASTER_EPISODES_CURRENT.csv",
    "logs_dir": "src/reports/logs",
    "target_episodes_per_age": 365,
    "age_range": (0, 120),
}


# ==============================================================================
# データロード関数
# ==============================================================================


def load_master_csv() -> pd.DataFrame:
    """マスターCSVを読み込み"""
    csv_path = PROJECT_ROOT / DASHBOARD_CONFIG["master_csv_path"]
    if not csv_path.exists():
        return pd.DataFrame()

    try:
        return pd.read_csv(csv_path, encoding="utf-8-sig")
    except Exception as e:
        print(f"Error loading master CSV: {e}")
        return pd.DataFrame()


def load_run_logs(days: int = 7) -> list[dict[str, Any]]:
    """実行ログを読み込み"""
    logs_dir = PROJECT_ROOT / DASHBOARD_CONFIG["logs_dir"]
    if not logs_dir.exists():
        return []

    logs = []
    cutoff_date = datetime.now() - timedelta(days=days)

    for filepath in logs_dir.glob("run_*.json"):
        try:
            # ファイル名から日付を抽出
            filename = filepath.stem  # run_20260107_155811
            date_str = filename.split("_")[1]  # 20260107
            file_date = datetime.strptime(date_str, "%Y%m%d")

            if file_date >= cutoff_date:
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)
                    data["_filepath"] = str(filepath)
                    logs.append(data)
        except (ValueError, json.JSONDecodeError):
            continue

    return sorted(logs, key=lambda x: x.get("started_at", ""), reverse=True)


def load_inventory_data() -> dict[str, Any]:
    """在庫データを計算"""
    df = load_master_csv()
    if df.empty:
        return {}

    target = DASHBOARD_CONFIG["target_episodes_per_age"]
    age_min, age_max = DASHBOARD_CONFIG["age_range"]

    # 年齢別集計
    age_counts = df.groupby("age").size().to_dict()

    # 統計
    achieved_ages = sum(1 for age in range(age_min, age_max + 1) if age_counts.get(age, 0) >= target)
    total_ages = age_max - age_min + 1

    # 不足数
    shortage = {}
    for age in range(age_min, age_max + 1):
        current = age_counts.get(age, 0)
        if current < target:
            shortage[age] = target - current

    return {
        "total_episodes": len(df),
        "total_ages": total_ages,
        "achieved_ages": achieved_ages,
        "achievement_rate": achieved_ages / total_ages * 100 if total_ages > 0 else 0,
        "age_counts": age_counts,
        "shortage": shortage,
        "target_per_age": target,
    }


def load_kpi_history(days: int = 7) -> pd.DataFrame:
    """KPI履歴をDataFrameで取得"""
    logs = load_run_logs(days)
    if not logs:
        return pd.DataFrame()

    records = []
    for log in logs:
        records.append(
            {
                "timestamp": log.get("started_at", ""),
                "acceptance_rate": log.get("acceptance_rate", 0) * 100,
                "accepted_count": log.get("accepted_count", 0),
                "rejected_count": log.get("rejected_count", 0),
                "generated_count": log.get("generated_count", 0),
                "cost_usd": log.get("cost_metrics", {}).get("estimated_cost_usd", 0),
            }
        )

    df = pd.DataFrame(records)
    if not df.empty and "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")
    return df


def calculate_current_metrics() -> dict[str, float]:
    """現在のメトリクスを計算"""
    logs = load_run_logs(days=1)
    df = load_master_csv()

    # デフォルト値
    metrics = {
        "acceptance_rate": 0.0,
        "avg_generation_quality": 0.0,
        "avg_factual_density": 0.0,
        "daily_cost_usd": 0.0,
        "error_rate": 0.0,
        "total_episodes": len(df) if not df.empty else 0,
    }

    if logs:
        # 直近ログからメトリクス計算
        total_accepted = sum(log.get("accepted_count", 0) for log in logs)
        total_generated = sum(log.get("generated_count", 0) for log in logs)
        total_rejected = sum(log.get("rejected_count", 0) for log in logs)
        total_cost = sum(log.get("cost_metrics", {}).get("estimated_cost_usd", 0) for log in logs)

        if total_generated > 0:
            metrics["acceptance_rate"] = total_accepted / total_generated * 100
            metrics["error_rate"] = total_rejected / total_generated * 100

        metrics["daily_cost_usd"] = total_cost

    if not df.empty:
        # マスターCSVからスコア平均
        if "生成品質スコア" in df.columns:
            quality_scores = pd.to_numeric(df["生成品質スコア"], errors="coerce")
            metrics["avg_generation_quality"] = quality_scores.mean()

        if "事実密度" in df.columns:
            factual_scores = pd.to_numeric(df["事実密度"], errors="coerce")
            metrics["avg_factual_density"] = factual_scores.mean()

    return metrics


# ==============================================================================
# Streamlit ダッシュボード
# ==============================================================================


def render_dashboard() -> None:
    """Streamlitダッシュボードを描画"""
    if not STREAMLIT_AVAILABLE:
        print("Streamlit is not installed. Run: pip install streamlit")
        return

    st.set_page_config(
        page_title=DASHBOARD_CONFIG["page_title"],
        page_icon=DASHBOARD_CONFIG["page_icon"],
        layout=DASHBOARD_CONFIG["layout"],
    )

    st.title(f"{DASHBOARD_CONFIG['page_icon']} {DASHBOARD_CONFIG['page_title']}")
    st.caption(f"最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # サイドバー
    with st.sidebar:
        st.header("設定")
        refresh_interval = st.selectbox(
            "自動更新間隔",
            options=[60, 300, 900, 0],
            format_func=lambda x: f"{x}秒" if x > 0 else "無効",
            index=1,
        )
        days_filter = st.slider("履歴期間（日）", 1, 30, 7)

        st.divider()
        if st.button("今すぐ更新", use_container_width=True):
            st.rerun()

    # 自動更新
    if refresh_interval > 0:
        st.empty()
        import time

        # 注: 実際の自動更新は st_autorefresh を使用するのがベター

    # メトリクス取得
    metrics = calculate_current_metrics()
    inventory = load_inventory_data()
    kpi_history = load_kpi_history(days_filter)

    # アラートチェック
    alert_manager = AlertManager()
    alerts = alert_manager.check_metrics(metrics)

    # アラート表示
    if alerts:
        st.subheader("🚨 アラート")
        for alert in alerts:
            if alert.severity == AlertSeverity.CRITICAL:
                st.error(f"**CRITICAL**: {alert.message}")
            elif alert.severity == AlertSeverity.WARNING:
                st.warning(f"**WARNING**: {alert.message}")
            else:
                st.info(f"**INFO**: {alert.message}")
        st.divider()

    # KPI メトリクスカード
    st.subheader("📊 主要KPI")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "採用率",
            f"{metrics['acceptance_rate']:.1f}%",
            delta="目標: 90%",
            delta_color="normal" if metrics["acceptance_rate"] >= 90 else "inverse",
        )

    with col2:
        st.metric(
            "総エピソード",
            f"{metrics['total_episodes']:,}",
        )

    with col3:
        st.metric(
            "平均生成品質",
            f"{metrics['avg_generation_quality']:.1f}",
            delta="目標: 8.0",
            delta_color="normal" if metrics["avg_generation_quality"] >= 8.0 else "inverse",
        )

    with col4:
        st.metric(
            "日次コスト",
            f"${metrics['daily_cost_usd']:.2f}",
        )

    st.divider()

    # 在庫状況
    st.subheader("📦 在庫状況")
    if inventory:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "365達成年齢",
                f"{inventory['achieved_ages']}/{inventory['total_ages']}",
                delta=f"{inventory['achievement_rate']:.1f}%",
            )

        with col2:
            shortage_total = sum(inventory["shortage"].values())
            st.metric("不足エピソード", f"{shortage_total:,}")

        with col3:
            st.metric("目標/年齢", f"{inventory['target_per_age']}")

        # 年齢分布ヒートマップ
        st.subheader("年齢別エピソード数")

        age_data = []
        for age in range(0, 121):
            count = inventory["age_counts"].get(age, 0)
            target = inventory["target_per_age"]
            status = "達成" if count >= target else "未達成"
            age_data.append({"年齢": age, "エピソード数": count, "状態": status})

        age_df = pd.DataFrame(age_data)

        # バーチャート
        st.bar_chart(age_df.set_index("年齢")["エピソード数"], use_container_width=True)

        # 未達成年齢リスト
        with st.expander("未達成年齢一覧"):
            shortage_df = pd.DataFrame(
                [{"年齢": age, "不足数": count} for age, count in sorted(inventory["shortage"].items())[:20]]
            )
            st.dataframe(shortage_df, use_container_width=True)

    st.divider()

    # KPI推移グラフ
    st.subheader("📈 KPI推移")
    if not kpi_history.empty:
        tab1, tab2 = st.tabs(["採用率", "コスト"])

        with tab1:
            st.line_chart(
                kpi_history.set_index("timestamp")["acceptance_rate"],
                use_container_width=True,
            )

        with tab2:
            st.line_chart(
                kpi_history.set_index("timestamp")["cost_usd"],
                use_container_width=True,
            )
    else:
        st.info("履歴データがありません")

    st.divider()

    # 直近の実行ログ
    st.subheader("📋 直近の実行ログ")
    logs = load_run_logs(days_filter)[:10]
    if logs:
        log_data = []
        for log in logs:
            log_data.append(
                {
                    "実行ID": log.get("run_id", ""),
                    "開始時刻": log.get("started_at", "")[:19],
                    "生成数": log.get("generated_count", 0),
                    "採用数": log.get("accepted_count", 0),
                    "却下数": log.get("rejected_count", 0),
                    "採用率": f"{log.get('acceptance_rate', 0) * 100:.1f}%",
                    "コスト": f"${log.get('cost_metrics', {}).get('estimated_cost_usd', 0):.3f}",
                    "dry_run": log.get("dry_run", True),
                }
            )
        st.dataframe(pd.DataFrame(log_data), use_container_width=True)
    else:
        st.info("実行ログがありません")


# ==============================================================================
# コンソールダッシュボード（Streamlit なし用）
# ==============================================================================


def render_console_dashboard() -> None:
    """コンソールにダッシュボードを表示"""
    print("\n" + "=" * 60)
    print(f"🎯 SAGE 監視ダッシュボード - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # メトリクス
    metrics = calculate_current_metrics()
    inventory = load_inventory_data()

    print("\n📊 主要KPI")
    print("-" * 40)
    print(f"  採用率:        {metrics['acceptance_rate']:.1f}%")
    print(f"  総エピソード:  {metrics['total_episodes']:,}")
    print(f"  平均生成品質:  {metrics['avg_generation_quality']:.1f}")
    print(f"  平均事実密度:  {metrics['avg_factual_density']:.1f}")
    print(f"  日次コスト:    ${metrics['daily_cost_usd']:.2f}")

    if inventory:
        print("\n📦 在庫状況")
        print("-" * 40)
        print(
            f"  365達成年齢: {inventory['achieved_ages']}/{inventory['total_ages']} ({inventory['achievement_rate']:.1f}%)"
        )
        print(f"  不足エピソード: {sum(inventory['shortage'].values()):,}")

        # 上位5不足年齢
        print("\n  不足年齢 TOP5:")
        sorted_shortage = sorted(inventory["shortage"].items(), key=lambda x: x[1], reverse=True)[:5]
        for age, count in sorted_shortage:
            print(f"    年齢{age:3d}: {count:3d}件不足")

    # アラートチェック
    print("\n🚨 アラート")
    print("-" * 40)
    alert_manager = AlertManager()
    alert_manager.add_notifier(console_notifier)
    alerts = alert_manager.check_metrics(metrics)
    if not alerts:
        print("  アラートなし ✓")

    print("\n" + "=" * 60)


# ==============================================================================
# メイン
# ==============================================================================


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SAGE Monitoring Dashboard")
    parser.add_argument("--console", action="store_true", help="コンソール表示モード")
    args = parser.parse_args()

    if args.console or not STREAMLIT_AVAILABLE:
        render_console_dashboard()
    else:
        render_dashboard()
