#!/usr/bin/env python3
"""
ダッシュボードv11生成スクリプト

Phase 27: 軽量化版ダッシュボード
- データを外部JSONファイルに分離（lazy loading対応）
- 削除済みカラム参照を除去
- Phase 26カラム（model, cost_usd）対応
- エピソードテキストを短縮（300文字）
- 数値精度を削減（小数点2桁）
"""

import csv
import gzip
import json
from datetime import datetime
from pathlib import Path

CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
DASHBOARD_PATH = Path("preserved/episode_database_dashboard_v11.html")
DATA_PATH = Path("preserved/data/dashboard_data_v11.json")
DATA_GZIP_PATH = Path("preserved/data/dashboard_data_v11.json.gz")

# fame_tier変換マップ (string→int)
TIER_TO_INT = {"SS": 1, "S": 2, "A": 3, "B": 4, "C": 5, "D": 6, "E": 7}


def _parse_fame_tier(val):
    """fame_tierを数値に変換"""
    if not val or val == "":
        return 7
    if val in TIER_TO_INT:
        return TIER_TO_INT[val]
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 7


def _safe_float(val, default=0.0, precision=2):
    """安全にfloat変換（精度制限付き）"""
    if not val or val == "":
        return default
    try:
        return round(float(val), precision)
    except (ValueError, TypeError):
        return default


def _safe_int(val, default=0):
    """安全にint変換"""
    if not val or val == "":
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def load_csv_data():
    """CSVからデータを読み込み（v11最適化版）"""
    episodes = []

    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            age = _safe_int(row.get("age", "0"))
            slot = _safe_int(row.get("slot", "0"))

            # nendai (年代ラベル) 生成
            nendai_labels = {1: "幼少期", 10: "10代", 20: "20代", 30: "30代", 40: "40代", 50: "50代", 60: "60歳以上"}
            if slot in nendai_labels:
                nendai = nendai_labels[slot]
            elif age >= 60:
                nendai = "60歳以上"
            elif age >= 10:
                nendai = f"{(age // 10) * 10}代"
            elif age >= 1:
                nendai = "幼少期"
            else:
                nendai = None

            # エピソードテキストを短縮（300文字）
            episode_text = row.get("episode_text", "")[:300].replace("\n", " ").replace("\r", "")

            episode = {
                # 基本情報
                "id": row.get("episode_id", ""),
                "pid": row.get("person_id", ""),
                "name": row.get("person_name", ""),
                "age": age,
                "slot": slot,
                "nd": nendai,  # nendai短縮
                "cat": row.get("category", ""),
                "type": row.get("episode_type", ""),
                "ts": row.get("generation_timestamp", ""),
                "text": episode_text,
                "etype": row.get("person_type", "REAL").lower(),
                "ptype": row.get("person_type", "REAL"),
                "work": row.get("work_title", "") or "",
                "group": row.get("group_name", "") or "",
                "is_grp": row.get("is_group_member", "False") == "True",
                "ep_cnt": _safe_int(row.get("episode_count", 1) or 1, 1),
                # Fame系（v3のみ使用 - 旧バージョン削除済み）
                "fame": _safe_float(row.get("fame_score_v3", 0)),
                "fame_jp": _safe_float(row.get("fame_score_japan", 0)),
                "ftier": _parse_fame_tier(row.get("fame_tier", "E")),
                "is_jp": row.get("is_japanese", "False") == "True",
                "slinks": _safe_int(row.get("sitelinks_count", 0)),
                "mlpv": _safe_int(row.get("multi_lang_pv", 0)),
                # Celebrity Score v2
                "celeb": _safe_float(row.get("celebrity_score_v2", 0)),
                "celeb_r": _safe_int(row.get("celebrity_rank_v2", 0)),
                # Episode Fame v6（最新版のみ - 旧バージョン削除済み）
                "efv6": _safe_float(row.get("episode_fame_v6", 0)),
                "eftv6": _safe_int(row.get("episode_fame_tier_v6", 0)),
                # 超総合スコア
                "super": _safe_float(row.get("super_total_score", 0)),
                # 8軸スコア
                "mem": _safe_float(row.get("記憶性スコア", 0)),
                "emp": _safe_float(row.get("共感性スコア", 0)),
                "sur": _safe_float(row.get("意外性スコア", 0)),
                "gen": _safe_float(row.get("生成品質スコア", 0)),
                "edu": _safe_float(row.get("教育的価値", 0)),
                "story": _safe_float(row.get("ストーリー品質", 0)),
                "fact": _safe_float(row.get("事実密度", 0)),
                "icon": _safe_float(row.get("象徴性スコア", 0)),
                # composite_score
                "comp": _safe_float(row.get("composite_score", 0)),
                # 5軸派生スコア
                "oq": _safe_float(row.get("総合品質", 0)),
                "ei": _safe_float(row.get("感情インパクト", 0)),
            }

            episodes.append(episode)

    return episodes


def generate_dashboard_html(episode_count: int, person_count: int) -> str:
    """ダッシュボードHTMLを生成（データ外部読み込み版）"""

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Episode Database Dashboard v11</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0a; color: #e0e0e0; }}
        .header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 20px; text-align: center; border-bottom: 1px solid #333; }}
        .header h1 {{ font-size: 1.8rem; margin-bottom: 10px; background: linear-gradient(90deg, #00d4ff, #7b2cbf); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .stats {{ display: flex; justify-content: center; gap: 30px; margin-top: 15px; flex-wrap: wrap; }}
        .stat {{ text-align: center; }}
        .stat-value {{ font-size: 1.5rem; font-weight: bold; color: #00d4ff; }}
        .stat-label {{ font-size: 0.8rem; color: #888; }}
        .loading {{ text-align: center; padding: 50px; color: #888; }}
        .loading-spinner {{ border: 4px solid #333; border-top: 4px solid #00d4ff; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto 20px; }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
        .filters {{ background: #1a1a1a; padding: 15px; display: flex; gap: 15px; flex-wrap: wrap; align-items: center; justify-content: center; border-bottom: 1px solid #333; }}
        .filter-group {{ display: flex; align-items: center; gap: 8px; }}
        .filter-group label {{ font-size: 0.85rem; color: #888; }}
        .filter-group select, .filter-group input {{ background: #2a2a2a; border: 1px solid #444; color: #e0e0e0; padding: 6px 10px; border-radius: 4px; font-size: 0.85rem; }}
        .filter-group select:focus, .filter-group input:focus {{ outline: none; border-color: #00d4ff; }}
        .content {{ padding: 20px; max-width: 1400px; margin: 0 auto; }}
        .episode-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 15px; }}
        .episode-card {{ background: #1a1a1a; border-radius: 8px; padding: 15px; border: 1px solid #333; transition: all 0.2s; }}
        .episode-card:hover {{ border-color: #00d4ff; transform: translateY(-2px); }}
        .card-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }}
        .person-info {{ flex: 1; }}
        .person-name {{ font-size: 1.1rem; font-weight: bold; color: #fff; }}
        .person-meta {{ font-size: 0.8rem; color: #888; margin-top: 3px; }}
        .scores {{ display: flex; gap: 8px; flex-wrap: wrap; }}
        .score-badge {{ background: #2a2a2a; padding: 3px 8px; border-radius: 4px; font-size: 0.75rem; }}
        .score-badge.super {{ background: linear-gradient(135deg, #7b2cbf, #00d4ff); color: #fff; }}
        .score-badge.fame {{ background: #1a472a; color: #4ade80; }}
        .score-badge.tier {{ background: #472a1a; color: #fbbf24; }}
        .episode-text {{ font-size: 0.85rem; color: #ccc; line-height: 1.5; margin-top: 10px; max-height: 100px; overflow: hidden; }}
        .axis-scores {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; margin-top: 10px; font-size: 0.7rem; }}
        .axis-score {{ background: #2a2a2a; padding: 4px; border-radius: 3px; text-align: center; }}
        .axis-score .label {{ color: #888; }}
        .axis-score .value {{ color: #00d4ff; font-weight: bold; }}
        .pagination {{ display: flex; justify-content: center; gap: 10px; margin-top: 20px; padding: 20px; }}
        .pagination button {{ background: #2a2a2a; border: 1px solid #444; color: #e0e0e0; padding: 8px 16px; border-radius: 4px; cursor: pointer; transition: all 0.2s; }}
        .pagination button:hover:not(:disabled) {{ background: #3a3a3a; border-color: #00d4ff; }}
        .pagination button:disabled {{ opacity: 0.5; cursor: not-allowed; }}
        .pagination .page-info {{ display: flex; align-items: center; color: #888; }}
        .no-results {{ text-align: center; padding: 50px; color: #888; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 0.8rem; border-top: 1px solid #333; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Episode Database Dashboard v11</h1>
        <p style="color: #888; font-size: 0.9rem;">Phase 27: 軽量化版 - {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        <div class="stats">
            <div class="stat">
                <div class="stat-value" id="stat-episodes">{episode_count:,}</div>
                <div class="stat-label">Total Episodes</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="stat-persons">{person_count:,}</div>
                <div class="stat-label">Persons</div>
            </div>
            <div class="stat">
                <div class="stat-value" id="stat-filtered">-</div>
                <div class="stat-label">Filtered</div>
            </div>
        </div>
    </div>

    <div class="filters">
        <div class="filter-group">
            <label>Search:</label>
            <input type="text" id="filter-search" placeholder="Name or text...">
        </div>
        <div class="filter-group">
            <label>Category:</label>
            <select id="filter-category">
                <option value="">All</option>
            </select>
        </div>
        <div class="filter-group">
            <label>Age:</label>
            <select id="filter-nendai">
                <option value="">All</option>
                <option value="幼少期">幼少期</option>
                <option value="10代">10代</option>
                <option value="20代">20代</option>
                <option value="30代">30代</option>
                <option value="40代">40代</option>
                <option value="50代">50代</option>
                <option value="60歳以上">60歳以上</option>
            </select>
        </div>
        <div class="filter-group">
            <label>Fame Tier:</label>
            <select id="filter-tier">
                <option value="">All</option>
                <option value="1">SS</option>
                <option value="2">S</option>
                <option value="3">A</option>
                <option value="4">B</option>
                <option value="5">C</option>
            </select>
        </div>
        <div class="filter-group">
            <label>Sort:</label>
            <select id="sort-by">
                <option value="super">Super Total Score</option>
                <option value="efv6">Episode Fame v6</option>
                <option value="fame">Fame Score</option>
                <option value="celeb">Celebrity Score</option>
                <option value="comp">Composite Score</option>
                <option value="ts">Latest</option>
            </select>
        </div>
        <div class="filter-group">
            <label>Per Page:</label>
            <select id="per-page">
                <option value="50">50</option>
                <option value="100" selected>100</option>
                <option value="200">200</option>
            </select>
        </div>
    </div>

    <div class="content">
        <div id="loading" class="loading">
            <div class="loading-spinner"></div>
            <p>Loading episode data...</p>
        </div>
        <div id="episode-grid" class="episode-grid" style="display: none;"></div>
        <div id="no-results" class="no-results" style="display: none;">
            <p>No episodes found matching your criteria.</p>
        </div>
    </div>

    <div class="pagination" id="pagination" style="display: none;">
        <button id="btn-first">&laquo; First</button>
        <button id="btn-prev">&lsaquo; Prev</button>
        <span class="page-info">Page <span id="current-page">1</span> of <span id="total-pages">1</span></span>
        <button id="btn-next">Next &rsaquo;</button>
        <button id="btn-last">Last &raquo;</button>
    </div>

    <div class="footer">
        <p>Episode Database Dashboard v11 | Phase 27: Lightweight Edition</p>
        <p>Data: {episode_count:,} episodes, {person_count:,} persons | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <script>
    // v11: External data loading with pagination
    let allEpisodes = [];
    let filteredEpisodes = [];
    let currentPage = 1;
    let perPage = 100;
    let categories = new Set();

    const TIER_LABELS = {{1: 'SS', 2: 'S', 3: 'A', 4: 'B', 5: 'C', 6: 'D', 7: 'E'}};

    async function loadData() {{
        try {{
            const response = await fetch('data/dashboard_data_v11.json');
            allEpisodes = await response.json();

            // Collect categories
            allEpisodes.forEach(ep => {{
                if (ep.cat) categories.add(ep.cat);
            }});

            // Populate category filter
            const catSelect = document.getElementById('filter-category');
            [...categories].sort().forEach(cat => {{
                const opt = document.createElement('option');
                opt.value = cat;
                opt.textContent = cat;
                catSelect.appendChild(opt);
            }});

            document.getElementById('loading').style.display = 'none';
            document.getElementById('episode-grid').style.display = 'grid';
            document.getElementById('pagination').style.display = 'flex';

            applyFilters();
        }} catch (err) {{
            document.getElementById('loading').innerHTML = '<p style="color: #ff6b6b;">Error loading data: ' + err.message + '</p>';
        }}
    }}

    function applyFilters() {{
        const search = document.getElementById('filter-search').value.toLowerCase();
        const category = document.getElementById('filter-category').value;
        const nendai = document.getElementById('filter-nendai').value;
        const tier = document.getElementById('filter-tier').value;
        const sortBy = document.getElementById('sort-by').value;
        perPage = parseInt(document.getElementById('per-page').value);

        filteredEpisodes = allEpisodes.filter(ep => {{
            if (search && !ep.name.toLowerCase().includes(search) && !ep.text.toLowerCase().includes(search)) return false;
            if (category && ep.cat !== category) return false;
            if (nendai && ep.nd !== nendai) return false;
            if (tier && ep.ftier !== parseInt(tier)) return false;
            return true;
        }});

        // Sort
        filteredEpisodes.sort((a, b) => {{
            if (sortBy === 'ts') return (b.ts || '').localeCompare(a.ts || '');
            return (b[sortBy] || 0) - (a[sortBy] || 0);
        }});

        document.getElementById('stat-filtered').textContent = filteredEpisodes.length.toLocaleString();
        currentPage = 1;
        renderPage();
    }}

    function renderPage() {{
        const grid = document.getElementById('episode-grid');
        const noResults = document.getElementById('no-results');
        const totalPages = Math.ceil(filteredEpisodes.length / perPage) || 1;

        document.getElementById('current-page').textContent = currentPage;
        document.getElementById('total-pages').textContent = totalPages;
        document.getElementById('btn-first').disabled = currentPage === 1;
        document.getElementById('btn-prev').disabled = currentPage === 1;
        document.getElementById('btn-next').disabled = currentPage === totalPages;
        document.getElementById('btn-last').disabled = currentPage === totalPages;

        if (filteredEpisodes.length === 0) {{
            grid.style.display = 'none';
            noResults.style.display = 'block';
            return;
        }}

        grid.style.display = 'grid';
        noResults.style.display = 'none';

        const start = (currentPage - 1) * perPage;
        const pageEpisodes = filteredEpisodes.slice(start, start + perPage);

        grid.innerHTML = pageEpisodes.map(ep => `
            <div class="episode-card">
                <div class="card-header">
                    <div class="person-info">
                        <div class="person-name">${{ep.name}}</div>
                        <div class="person-meta">${{ep.age}}歳 | ${{ep.cat}} | ${{ep.nd || '-'}}</div>
                    </div>
                    <div class="scores">
                        <span class="score-badge super">S:${{ep.super.toFixed(0)}}</span>
                        <span class="score-badge fame">F:${{ep.fame.toFixed(1)}}</span>
                        <span class="score-badge tier">${{TIER_LABELS[ep.ftier] || 'E'}}</span>
                    </div>
                </div>
                <div class="episode-text">${{ep.text}}</div>
                <div class="axis-scores">
                    <div class="axis-score"><span class="label">記憶</span><span class="value">${{ep.mem.toFixed(1)}}</span></div>
                    <div class="axis-score"><span class="label">共感</span><span class="value">${{ep.emp.toFixed(1)}}</span></div>
                    <div class="axis-score"><span class="label">意外</span><span class="value">${{ep.sur.toFixed(1)}}</span></div>
                    <div class="axis-score"><span class="label">品質</span><span class="value">${{ep.gen.toFixed(1)}}</span></div>
                    <div class="axis-score"><span class="label">教育</span><span class="value">${{ep.edu.toFixed(1)}}</span></div>
                    <div class="axis-score"><span class="label">物語</span><span class="value">${{ep.story.toFixed(1)}}</span></div>
                    <div class="axis-score"><span class="label">事実</span><span class="value">${{ep.fact.toFixed(1)}}</span></div>
                    <div class="axis-score"><span class="label">象徴</span><span class="value">${{ep.icon.toFixed(1)}}</span></div>
                </div>
            </div>
        `).join('');
    }}

    // Event listeners
    document.getElementById('filter-search').addEventListener('input', debounce(applyFilters, 300));
    document.getElementById('filter-category').addEventListener('change', applyFilters);
    document.getElementById('filter-nendai').addEventListener('change', applyFilters);
    document.getElementById('filter-tier').addEventListener('change', applyFilters);
    document.getElementById('sort-by').addEventListener('change', applyFilters);
    document.getElementById('per-page').addEventListener('change', applyFilters);

    document.getElementById('btn-first').addEventListener('click', () => {{ currentPage = 1; renderPage(); }});
    document.getElementById('btn-prev').addEventListener('click', () => {{ if (currentPage > 1) {{ currentPage--; renderPage(); }} }});
    document.getElementById('btn-next').addEventListener('click', () => {{ const totalPages = Math.ceil(filteredEpisodes.length / perPage); if (currentPage < totalPages) {{ currentPage++; renderPage(); }} }});
    document.getElementById('btn-last').addEventListener('click', () => {{ currentPage = Math.ceil(filteredEpisodes.length / perPage); renderPage(); }});

    function debounce(func, wait) {{
        let timeout;
        return function(...args) {{
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        }};
    }}

    // Load data on page load
    loadData();
    </script>
</body>
</html>"""

    return html


def main():
    print("=== ダッシュボード v11 生成 ===")
    print("Phase 27: 軽量化版\n")

    print("CSVデータ読み込み中...")
    episodes = load_csv_data()
    print(f"エピソード数: {len(episodes)}")

    # 統計
    persons = {}
    for ep in episodes:
        pid = ep["pid"]
        if pid not in persons:
            persons[pid] = ep

    print(f"人物数: {len(persons)}")

    # JSONデータを外部ファイルに保存
    print("\nJSONデータ生成中...")
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(episodes, f, ensure_ascii=False, separators=(",", ":"))

    json_size = DATA_PATH.stat().st_size / (1024 * 1024)
    print(f"JSON保存: {DATA_PATH} ({json_size:.2f} MB)")

    # Gzip版も作成
    with gzip.open(DATA_GZIP_PATH, "wt", encoding="utf-8") as f:
        json.dump(episodes, f, ensure_ascii=False, separators=(",", ":"))

    gzip_size = DATA_GZIP_PATH.stat().st_size / (1024 * 1024)
    print(f"Gzip保存: {DATA_GZIP_PATH} ({gzip_size:.2f} MB)")

    # HTMLダッシュボード生成
    print("\nHTML生成中...")
    html = generate_dashboard_html(len(episodes), len(persons))

    with open(DASHBOARD_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    html_size = DASHBOARD_PATH.stat().st_size / (1024 * 1024)
    print(f"HTML保存: {DASHBOARD_PATH} ({html_size:.2f} MB)")

    # Top 10 Super Total Score
    sorted_super = sorted(episodes, key=lambda x: x["super"], reverse=True)
    print("\nTop 10 Super Total Score:")
    for i, ep in enumerate(sorted_super[:10], 1):
        print(f"  {i:2d}. {ep['name']} ({ep['age']}歳): {ep['super']:.0f}")

    # サイズ比較
    print("\n=== サイズ比較 ===")
    v10_size = 30.87  # MB (既知)
    print(f"v10: {v10_size:.2f} MB (embedded)")
    print(f"v11 HTML: {html_size:.2f} MB")
    print(f"v11 JSON: {json_size:.2f} MB")
    print(f"v11 合計: {html_size + json_size:.2f} MB")
    print(f"削減率: {(1 - (html_size + json_size) / v10_size) * 100:.1f}%")

    print("\n✓ ダッシュボード v11 生成完了!")


if __name__ == "__main__":
    main()
