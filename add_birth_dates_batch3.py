
#!/usr/bin/env python3
import pandas as pd
import requests
import time
import re
from datetime import datetime
import urllib.parse
from pathlib import Path
import concurrent.futures
from threading import Lock

df_lock = Lock()
progress_lock = Lock()

global_counters = {
    "processed": 0,
    "success": 0,
    "birth_dates": 0,
    "birth_years": 0,
    "errors": 0
}

def extract_birth_info_from_wikitext(wikitext):
    match = re.search(r"\{\{(?:生年月日|birth\s*date)[^|]*\|(\d{4})\|(\d{1,2})\|(\d{1,2})", wikitext, re.IGNORECASE)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        if 1800 <= year <= 2024 and 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}", year
    
    match = re.search(r"生年月日[^=]*=.*?(\d{4})年(\d{1,2})月(\d{1,2})日", wikitext[:2000])
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        if 1800 <= year <= 2024 and 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}", year
    
    match = re.search(r"(\d{4})年.*?生まれ", wikitext[:2000])
    if match:
        year = int(match.group(1))
        if 1800 <= year <= 2024:
            return None, year
    
    match = re.search(r"（(\d{4})年.*?[-–]", wikitext[:1000])
    if match:
        year = int(match.group(1))
        if 1800 <= year <= 2024:
            return None, year
    
    return None, None

def get_wikipedia_content(wikipedia_url, session=None):
    if not wikipedia_url or pd.isna(wikipedia_url) or wikipedia_url == "": 
        return None
    
    title_match = re.search(r"/wiki/(.+)$", wikipedia_url)
    if not title_match:
        return None
    
    page_title = urllib.parse.unquote(title_match.group(1))
    api_url = "https://ja.wikipedia.org/w/api.php"
    
    params = {
        "action": "query",
        "prop": "revisions",
        "titles": page_title,
        "rvslots": "*",
        "rvprop": "content",
        "format": "json",
        "formatversion": "2"
    }
    
    try:
        if session:
            response = session.get(api_url, params=params, timeout=5)
        else:
            response = requests.get(api_url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if "query" in data and "pages" in data["query"]:
                pages = data["query"]["pages"]
                if pages and len(pages) > 0:
                    page = pages[0]
                    if "revisions" in page and len(page["revisions"]) > 0:
                        wikitext = page["revisions"][0]["slots"]["main"]["content"]
                        return wikitext
    except Exception:
        return None
    
    return None

def process_batch(df, batch_indices, thread_id):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "BirthDateExtractor/1.0 (Educational Purpose)"
    })
    
    local_success = 0
    local_birth_dates = 0
    local_birth_years = 0
    local_errors = 0
    
    for i, idx in enumerate(batch_indices, 1):
        row = df.loc[idx]
        person_name = row["person_name_display"]
        wikipedia_url = row["wikipedia_url"]
        
        wikitext = get_wikipedia_content(wikipedia_url, session)
        
        if wikitext:
            birth_date, birth_year = extract_birth_info_from_wikitext(wikitext)
            
            if birth_date or birth_year:
                local_success += 1
                
                with df_lock:
                    if birth_date:
                        df.at[idx, "birth_date"] = birth_date
                        df.at[idx, "birth_year_int"] = birth_year
                        local_birth_dates += 1
                        print(f"[Thread{thread_id}][{i:3d}/{len(batch_indices)}] ✅ {person_name}: 生年月日 {birth_date}")
                    elif birth_year:
                        df.at[idx, "birth_year_int"] = birth_year
                        local_birth_years += 1
                        print(f"[Thread{thread_id}][{i:3d}/{len(batch_indices)}] 📅 {person_name}: 生年 {birth_year}")
            else:
                print(f"[Thread{thread_id}][{i:3d}/{len(batch_indices)}] ⚪ {person_name}: 生年情報なし")
        else:
            local_errors += 1
            print(f"[Thread{thread_id}][{i:3d}/{len(batch_indices)}] ❌ {person_name}: Wikipedia取得失敗")
        
        time.sleep(0.2 + thread_id * 0.1)
        
        with progress_lock:
            global_counters["processed"] += 1
            if global_counters["processed"] % 20 == 0:
                print(f"\n📊 全体進捗: {global_counters["processed"]}件処理済み\n")
    
    session.close()
    
    return {
        "success": local_success,
        "birth_dates": local_birth_dates,
        "birth_years": local_birth_years,
        "errors": local_errors
    }

def main():
    print("=" * 80)
    print("🎯 優先度ベース処理の継続（次のバッチ）")
    print("=" * 80)
    
    input_file = "ultra_think_WITH_BIRTH_DATES_PRIORITY_20250917_020633.csv"
    
    if not Path(input_file).exists():
        print(f"❌ ファイルが見つかりません: {input_file}")
        return
    
    print(f"\n📂 データ読み込み中: {input_file}")
    df = pd.read_csv(input_file, encoding="utf-8-sig")
    print(f"✅ データ読み込み完了: {len(df):,}件")
    
    existing_birth_date = df["birth_date"].notna().sum()
    existing_birth_year = df["birth_year_int"].notna().sum()
    print(f"\n📊 既存データ:")
    print(f"  - 生年月日: {existing_birth_date:,}件")
    print(f"  - 生年: {existing_birth_year:,}件")
    
    wiki_mask = (
        df["wikipedia_url"].notna() &
        (df["wikipedia_url"] != "") &
        df["birth_year_int"].isna()
    )
    target_df = df[wiki_mask].copy()
    
    print(f"\n🎯 処理対象: Wikipedia URLがあり生年データがない {len(target_df):,}件")
    
    print("\n📈 優先度スコアを計算中...")
    
    category_priority = {
        "歴史的偉人": 10,
        "文化・芸術": 8,
        "政治": 7,
        "文化・学術": 6,
        "エンタメ": 5,
        "スポーツ": 4,
        "政治・経済": 3,
        "その他": 2
    }
    
    occupation_priority = {
        "政治家": 10,
        "作家": 9,
        "大統領": 8,
        "野球選手": 7,
        "お笑い芸人": 6,
        "俳優": 5,
        "歌手": 4,
        "YouTuber": 3
    }
    
    target_df["priority_score"] = 0
    
    if "category" in target_df.columns:
        for cat, score in category_priority.items():
            mask = target_df["category"] == cat
            target_df.loc[mask, "priority_score"] += score * 100
    
    if "occupation" in target_df.columns:
        for occ, score in occupation_priority.items():
            mask = target_df["occupation"] == occ
            target_df.loc[mask, "priority_score"] += score * 50
    
    if "fame_score" in target_df.columns:
        max_fame = target_df["fame_score"].max()
        if max_fame > 0:
            target_df["priority_score"] += (target_df["fame_score"] / max_fame * 100).fillna(0)
    
    target_df = target_df.sort_values("priority_score", ascending=False)
    
    limit = 500
    if len(target_df) > limit:
        print(f"\n⚠️ 効率化のため上位{limit}件のみ処理します")
        target_df = target_df.head(limit)
    
    target_indices = target_df.index.tolist()
    
    num_threads = 5
    batch_size = len(target_indices) // num_threads
    batches = []
    
    for i in range(num_threads):
        start = i * batch_size
        if i == num_threads - 1:
            batch = target_indices[start:]
        else:
            batch = target_indices[start:start + batch_size]
        if batch:
            batches.append(batch)
    
    print(f"\n🚀 {num_threads}スレッドで並列処理を開始（各スレッド約{batch_size}件）...")
    print("-" * 80)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        for i, batch in enumerate(batches):
            future = executor.submit(process_batch, df, batch, i+1)
            futures.append(future)
        
        total_results = {
            "success": 0,
            "birth_dates": 0,
            "birth_years": 0,
            "errors": 0
        }
        
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            for key in total_results:
                total_results[key] += result[key]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"ultra_think_WITH_BIRTH_DATES_BATCH3_{timestamp}.csv"
    
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    
    print("\n" + "=" * 80)
    print("📊 バッチ3処理結果サマリー")
    print("=" * 80)
    print(f"✅ 成功: {total_results["success"]:,}件")
    print(f"  - 生年月日取得: {total_results["birth_dates"]:,}件")
    print(f"  - 生年のみ取得: {total_results["birth_years"]:,}件")
    print(f"❌ エラー: {total_results["errors"]:,}件")
    if len(target_indices) > 0:
        print(f"📈 成功率: {total_results["success"]/len(target_indices)*100:.1f}%")
    print(f"\n💾 保存先: {output_file}")
    
    final_birth_date = df["birth_date"].notna().sum()
    final_birth_year = df["birth_year_int"].notna().sum()
    print(f"\n📈 累積データ状況:")
    print(f"  - 生年月日: {final_birth_date:,}件 (増加: +{final_birth_date - existing_birth_date:,})")
    print(f"  - 生年: {final_birth_year:,}件 (増加: +{final_birth_year - existing_birth_year:,})")
    print(f"  - カバー率: {final_birth_year / len(df) * 100:.1f}%")

if __name__ == "__main__":
    main()
