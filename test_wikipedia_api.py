#!/usr/bin/env python3
"""
Wikipedia API テストスクリプト
"""

import requests
import urllib.parse

def test_wikipedia_api():
    # テスト用のページタイトル
    page_title = "藤井聡太"

    # APIエンドポイント
    api_url = "https://ja.wikipedia.org/w/api.php"

    params = {
        'action': 'query',
        'prop': 'revisions',
        'titles': page_title,
        'rvslots': '*',
        'rvprop': 'content',
        'format': 'json',
        'formatversion': '2'
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }

    print(f"Testing Wikipedia API for: {page_title}")
    print(f"URL: {api_url}")

    try:
        response = requests.get(api_url, params=params, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Content Type: {response.headers.get('content-type', 'unknown')}")

        if response.status_code == 200:
            # 最初の100文字を表示
            content = response.text[:500]
            print(f"Response (first 500 chars): {content}")

            # JSONとしてパース
            try:
                data = response.json()
                if 'query' in data and 'pages' in data['query']:
                    pages = data['query']['pages']
                    if pages and len(pages) > 0:
                        page = pages[0]
                        if 'revisions' in page:
                            print("\n✓ Wikipedia API is working!")
                            # Wikitextの最初の部分を表示
                            wikitext = page['revisions'][0]['slots']['main']['content']
                            print(f"\nWikitext (first 300 chars):\n{wikitext[:300]}")

                            # 生年月日を探す
                            import re
                            match = re.search(r'(\d{4})年.*?生まれ', wikitext[:2000])
                            if match:
                                print(f"\n✓ Found birth year: {match.group(1)}")
                        else:
                            print("\n✗ No revisions found")
                    else:
                        print("\n✗ No pages found")
                else:
                    print("\n✗ Invalid response structure")
            except Exception as e:
                print(f"\n✗ JSON parsing error: {e}")
        else:
            print(f"\n✗ HTTP error: {response.status_code}")

    except Exception as e:
        print(f"\n✗ Request error: {e}")

if __name__ == '__main__':
    test_wikipedia_api()
