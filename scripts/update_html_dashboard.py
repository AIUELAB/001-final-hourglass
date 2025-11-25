#!/usr/bin/env python3
"""
HTMLダッシュボードの統計データをAPIから取得するように更新
"""


def update_html_dashboard():
    html_path = "./preserved/episode_database_dashboard_v2.html"

    # HTMLファイルを読み込み
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 統計データ取得関数を追加
    stats_fetch_script = """
        // ========== API統計データ取得 ==========
        async function fetchAPIStats() {
            try {
                const response = await fetch('http://localhost:8000/api/stats/summary');
                const data = await response.json();

                console.log('✅ API統計データ取得成功:', data);

                // 統計カードを更新
                document.getElementById('total-episodes').textContent = data.total_characters.toLocaleString();

                const target = 22630;
                const gap = target - data.total_characters;
                const coveragePercent = (data.total_characters / target * 100).toFixed(2);

                document.getElementById('gap-count').textContent = gap.toLocaleString();
                document.getElementById('coverage-percent').textContent = coveragePercent + '%';

                // プログレスバー更新
                const progressFill = document.getElementById('coverage-progress');
                if (progressFill) {
                    progressFill.style.width = Math.min(coveragePercent, 100) + '%';
                }

                // 実在人物と架空キャラクター
                document.getElementById('real-episodes').textContent = data.male_count.toLocaleString();
                document.getElementById('fictional-episodes').textContent = data.female_count.toLocaleString();

            } catch (error) {
                console.error('❌ API統計データ取得エラー:', error);
                // エラー時はプレースホルダーを表示
                document.getElementById('total-episodes').textContent = 'エラー';
            }
        }

        // ========== タブ切り替え機能 =========="""

    # タブ切り替え機能の前に挿入
    content = content.replace("        // ========== タブ切り替え機能 ==========", stats_fetch_script)

    # DOMContentLoadedイベントでAPI統計を取得
    old_init = """        // 初期化
        window.addEventListener('DOMContentLoaded', () => {
            initTabs();
            loadHeatmapData();
            initEpisodeList();
        });"""

    new_init = """        // 初期化
        window.addEventListener('DOMContentLoaded', () => {
            initTabs();
            fetchAPIStats();  // API統計データを取得
            loadHeatmapData();
            initEpisodeList();
        });"""

    content = content.replace(old_init, new_init)

    # 変更を保存
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("✅ HTMLダッシュボードを更新しました")
    print(f"📄 ファイル: {html_path}")
    print("\n変更内容:")
    print("  - 統計データをAPIから取得するように変更")
    print("  - リアルタイムで最新のデータベース統計を表示")


if __name__ == "__main__":
    update_html_dashboard()
