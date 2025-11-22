#!/usr/bin/env python3
"""
エピソード一覧テーブルにepisode_count（エピソード数）カラムを追加
"""

def add_episode_count_column():
    html_path = './preserved/episode_database_dashboard_v2.html'

    # HTMLファイルを読み込み
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. テーブルヘッダーに「エピソード数」カラムを追加
    # 「人物名」の後に挿入
    old_header = '''                            <th width="180px" class="sortable" data-sort="person">
                                人物名 <span class="sort-icon">⬍</span>
                            </th>
                            <th width="120px" class="sortable" data-sort="category">'''

    new_header = '''                            <th width="180px" class="sortable" data-sort="person">
                                人物名 <span class="sort-icon">⬍</span>
                            </th>
                            <th width="90px" class="sortable" data-sort="episode_count">
                                エピソード数 <span class="sort-icon">⬍</span>
                            </th>
                            <th width="120px" class="sortable" data-sort="category">'''

    content = content.replace(old_header, new_header)

    # 2. テーブル本体のレンダリング関数を修正
    # renderEpisodeTable関数内のtbody.innerHTMLを修正

    # colspanを7から8に変更（カラムが1つ増えたため）
    content = content.replace(
        '<td colspan="7" class="loading-cell">',
        '<td colspan="8" class="loading-cell">'
    )
    content = content.replace(
        '<td colspan="5" class="loading-cell"',
        '<td colspan="8" class="loading-cell"'
    )

    # 3. テーブル行に episode_count の表示を追加
    old_tbody = '''                            <td>
                                <div class="person-name-cell">
                                    <span class="entity-icon">${entityIcon}</span>
                                    <strong>${escapeHtml(ep.person_name)}</strong>
                                </div>
                            </td>
                            <td>
                                <span class="badge ${categoryClass}">${ep.category}</span>
                            </td>'''

    new_tbody = '''                            <td>
                                <div class="person-name-cell">
                                    <span class="entity-icon">${entityIcon}</span>
                                    <strong>${escapeHtml(ep.person_name)}</strong>
                                </div>
                            </td>
                            <td style="text-align: center;">
                                <span class="badge badge-primary" style="background: #3b82f6; color: white; font-weight: 600;">
                                    ${ep.episode_count || 1}件
                                </span>
                            </td>
                            <td>
                                <span class="badge ${categoryClass}">${ep.category}</span>
                            </td>'''

    content = content.replace(old_tbody, new_tbody)

    # 4. CSV読み込み時にepisode_countを保持することを確認
    # initEpisodeList関数を確認して、episode_countフィールドがマッピングされているか確認
    # Papa.parse の結果には自動的に含まれているはず

    # 5. ソート処理にepisode_countを追加
    old_sort = '''                        case 'person':
                            return a.person_name.localeCompare(b.person_name, 'ja');
                        case 'category':'''

    new_sort = '''                        case 'person':
                            return a.person_name.localeCompare(b.person_name, 'ja');
                        case 'episode_count':
                            return (parseFloat(a.episode_count) || 1) - (parseFloat(b.episode_count) || 1);
                        case 'category':'''

    content = content.replace(old_sort, new_sort)

    # 変更を保存
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("✅ エピソード数カラムを追加しました")
    print(f"📄 ファイル: {html_path}")
    print("\n追加内容:")
    print("  - テーブルヘッダーに「エピソード数」カラム")
    print("  - 各行にエピソード件数を表示（バッジ形式）")
    print("  - エピソード数でのソート機能")

if __name__ == '__main__':
    add_episode_count_column()
