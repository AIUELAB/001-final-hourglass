#!/usr/bin/env python3
"""
Wikipedia APIの動作をデバッグ
なぜ架空の名前でも「見つかる」と判定されるのか調査
"""

import requests
import json

def test_wikipedia_search(query, lang='ja'):
    """Wikipedia API検索をデバッグ"""
    print(f"\n検索クエリ: '{query}' ({lang}.wikipedia)")
    
    if lang == 'ja':
        url = "https://ja.wikipedia.org/w/api.php"
    else:
        url = "https://en.wikipedia.org/w/api.php"
    
    params = {
        'action': 'query',
        'format': 'json',
        'list': 'search',
        'srsearch': query,
        'srlimit': 5
    }
    
    # User-Agentを設定
    headers = {
        'User-Agent': 'Ultra Think Wikipedia Validator/1.0 (https://example.com/contact) Python/requests'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = data.get('query', {}).get('search', [])
            
            print(f"結果: {len(results)}件")
            if results:
                for i, result in enumerate(results[:3], 1):
                    print(f"  {i}. {result.get('title', 'N/A')}")
                    # スニペット（要約）も表示
                    snippet = result.get('snippet', '')
                    # HTMLタグを除去
                    import re
                    snippet_clean = re.sub('<.*?>', '', snippet)
                    if snippet_clean:
                        print(f"     要約: {snippet_clean[:100]}...")
                return True
            else:
                print("  結果なし")
                return False
        else:
            print(f"  エラー: HTTPステータス {response.status_code}")
            return False
    except Exception as e:
        print(f"  エラー: {e}")
        return False
    
    return False


def test_various_queries():
    """様々なクエリでテスト"""
    
    test_cases = [
        # 実在の人物
        ("安倍晋三", True),
        ("大谷翔平", True),
        ("新垣結衣", True),
        
        # 架空の人物（期待: False）
        ("テスト太郎123", False),
        ("サンプル花子456", False),
        ("プレースホルダー次郎", False),
        ("ダミーユーザー789", False),
        
        # 曖昧なケース
        ("田中太郎", None),  # 一般的な名前
        ("山田花子", None),  # 一般的な名前
    ]
    
    print("=" * 60)
    print("Wikipedia API テスト")
    print("=" * 60)
    
    success_count = 0
    failure_count = 0
    
    for query, expected in test_cases:
        found = test_wikipedia_search(query, 'ja')
        
        # 期待値との比較
        if expected is not None:
            if found == expected:
                print(f"  ✅ 期待通り: {'見つかった' if found else '見つからなかった'}")
                success_count += 1
            else:
                print(f"  ❌ 期待と異なる: 期待={'見つかる' if expected else '見つからない'}, 実際={'見つかった' if found else '見つからなかった'}")
                failure_count += 1
        else:
            print(f"  ⚠️ 不定: {'見つかった' if found else '見つからなかった'}")
    
    print("\n" + "=" * 60)
    print(f"テスト結果: 成功 {success_count}, 失敗 {failure_count}")
    
    if failure_count > 0:
        print("\n⚠️ Wikipedia APIが予期しない結果を返しています。")
        print("部分一致や類似名での検索結果が返されている可能性があります。")


def test_exact_match():
    """完全一致テスト"""
    print("\n" + "=" * 60)
    print("完全一致テスト")
    print("=" * 60)
    
    # より厳密な検索（タイトル完全一致）
    test_names = [
        "テスト太郎123",
        "安倍晋三"
    ]
    
    for name in test_names:
        print(f"\n'{name}'の完全一致検索:")
        
        # ページタイトル検索
        url = "https://ja.wikipedia.org/w/api.php"
        params = {
            'action': 'query',
            'format': 'json',
            'titles': name,
            'prop': 'info'
        }
        
        headers = {
            'User-Agent': 'Ultra Think Wikipedia Validator/1.0 (https://example.com/contact) Python/requests'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            pages = data.get('query', {}).get('pages', {})
            
            for page_id, page_info in pages.items():
                if page_id == '-1':
                    print(f"  ❌ ページ存在せず")
                else:
                    print(f"  ✅ ページ存在: {page_info.get('title', 'N/A')}")


if __name__ == "__main__":
    # 1. 様々なクエリでテスト
    test_various_queries()
    
    # 2. 完全一致テスト
    test_exact_match()