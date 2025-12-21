#!/usr/bin/env python3
"""
HTMLダッシュボードにReactタブを追加するスクリプト
"""


def add_react_tabs():
    html_path = "./preserved/episode_database_dashboard_v2.html"

    # HTMLファイルを読み込み
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. タブボタンを追加（既存のタブボタンの後に追加）
    # 行783: <button class="tab-button" data-tab="episodes">📋 エピソード</button>
    # の後に追加
    tab_buttons_insert = """            <button class="tab-button" data-tab="react-stats">📊 React統計</button>
            <button class="tab-button" data-tab="react-characters">👥 キャラクター一覧</button>"""

    content = content.replace(
        '            <button class="tab-button" data-tab="episodes">📋 エピソード</button>',
        '            <button class="tab-button" data-tab="episodes">📋 エピソード</button>\n' + tab_buttons_insert,
    )

    # 2. iframeスタイルCSSを追加
    # .tab-panel のスタイル定義の後に追加
    iframe_css = """
        .iframe-container {
            width: 100%;
            height: calc(100vh - 200px);
            min-height: 600px;
            border: none;
            background: white;
        }

        .iframe-container iframe {
            width: 100%;
            height: 100%;
            border: none;
        }
"""

    # .tab-panel.active の後に挿入
    content = content.replace(
        "        .tab-panel.active {\n            display: block;\n        }",
        "        .tab-panel.active {\n            display: block;\n        }" + iframe_css,
    )

    # 3. タブパネルを追加（タブ5: エピソード一覧の前に追加）
    # <!-- タブ5: エピソード一覧 --> の前に追加
    react_panels = """
        <!-- タブ6: React統計ダッシュボード -->
        <div class="tab-panel" id="react-stats-panel">
            <div class="iframe-container">
                <iframe src="http://localhost:5175/" title="React統計ダッシュボード"></iframe>
            </div>
        </div>
        <!-- タブ6: React統計ダッシュボード 終了 -->

        <!-- タブ7: Reactキャラクター一覧 -->
        <div class="tab-panel" id="react-characters-panel">
            <div class="iframe-container">
                <iframe src="http://localhost:5175/characters" title="Reactキャラクター一覧"></iframe>
            </div>
        </div>
        <!-- タブ7: Reactキャラクター一覧 終了 -->

"""

    content = content.replace(
        "        <!-- タブ5: エピソード一覧 -->", react_panels + "        <!-- タブ5: エピソード一覧 -->"
    )

    # 変更を保存
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("✅ HTMLダッシュボードにReactタブを追加しました")
    print(f"📄 ファイル: {html_path}")
    print("\n追加されたタブ:")
    print("  - 📊 React統計 (http://localhost:5175/)")
    print("  - 👥 キャラクター一覧 (http://localhost:5175/characters)")


if __name__ == "__main__":
    add_react_tabs()
