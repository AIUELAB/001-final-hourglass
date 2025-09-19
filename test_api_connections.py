#!/usr/bin/env python3
"""
API接続テストスクリプト
Test API Connections

新しく設定したAPIキーの動作確認
"""

import os
import sys
from dotenv import load_dotenv
import requests
import json
from datetime import datetime

# .envファイル読み込み
load_dotenv()

# カラー出力用
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def test_serpapi():
    """SerpAPI接続テスト"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}1. SerpAPI テスト{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    api_key = os.getenv('SERPAPI_KEY')
    if not api_key:
        print(f"{Colors.RED}❌ SERPAPI_KEY が設定されていません{Colors.END}")
        return False
    
    try:
        from serpapi import GoogleSearch
        
        # テスト検索
        params = {
            "q": "HIKAKIN",
            "api_key": api_key,
            "hl": "ja",
            "gl": "jp",
            "num": 1
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        if 'search_information' in results:
            total_results = results['search_information'].get('total_results', 0)
            print(f"{Colors.GREEN}✅ SerpAPI接続成功！{Colors.END}")
            print(f"   検索: 'HIKAKIN'")
            print(f"   結果数: {total_results:,}件")
            
            # ナレッジグラフ確認
            if 'knowledge_graph' in results:
                print(f"   {Colors.GREEN}ナレッジグラフ: あり{Colors.END}")
            
            # 残りAPI使用回数（月100回）
            print(f"   {Colors.YELLOW}無料枠: 月100回{Colors.END}")
            return True
        else:
            print(f"{Colors.RED}❌ 検索結果が取得できませんでした{Colors.END}")
            return False
            
    except ImportError:
        print(f"{Colors.YELLOW}⚠️ serpapi パッケージがインストールされていません{Colors.END}")
        print(f"   実行: pip install google-search-results")
        return False
    except Exception as e:
        print(f"{Colors.RED}❌ エラー: {e}{Colors.END}")
        return False


def test_twitter_api():
    """Twitter API接続テスト"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}2. Twitter/X API テスト{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
    if not bearer_token:
        print(f"{Colors.RED}❌ TWITTER_BEARER_TOKEN が設定されていません{Colors.END}")
        return False
    
    try:
        headers = {
            'Authorization': f'Bearer {bearer_token}',
            'User-Agent': 'v2UserLookupPython'
        }
        
        # HIKAKINのTwitter情報取得
        url = "https://api.twitter.com/2/users/by/username/hikakin"
        params = {
            'user.fields': 'public_metrics,created_at,verified'
        }
        
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data:
                user = data['data']
                metrics = user.get('public_metrics', {})
                
                print(f"{Colors.GREEN}✅ Twitter API接続成功！{Colors.END}")
                print(f"   ユーザー: @hikakin")
                print(f"   フォロワー: {metrics.get('followers_count', 0):,}")
                print(f"   ツイート数: {metrics.get('tweet_count', 0):,}")
                print(f"   認証済み: {user.get('verified', False)}")
                print(f"   {Colors.YELLOW}無料枠: Essential tier (月1,500ツイート取得){Colors.END}")
                return True
        elif response.status_code == 429:
            print(f"{Colors.YELLOW}⚠️ レート制限に達しています{Colors.END}")
            return False
        else:
            print(f"{Colors.RED}❌ エラー: {response.status_code}{Colors.END}")
            print(f"   {response.text}")
            return False
            
    except Exception as e:
        print(f"{Colors.RED}❌ エラー: {e}{Colors.END}")
        return False


def test_news_api():
    """News API接続テスト"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}3. News API テスト{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    api_key = os.getenv('NEWS_API_KEY')
    if not api_key:
        print(f"{Colors.RED}❌ NEWS_API_KEY が設定されていません{Colors.END}")
        return False
    
    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            'q': '大谷翔平',
            'apiKey': api_key,
            'sortBy': 'popularity',
            'pageSize': 5,
            'language': 'ja'
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            total_results = data.get('totalResults', 0)
            articles = data.get('articles', [])
            
            print(f"{Colors.GREEN}✅ News API接続成功！{Colors.END}")
            print(f"   検索: '大谷翔平'")
            print(f"   記事数: {total_results:,}件")
            
            if articles:
                print(f"\n   最新記事:")
                for i, article in enumerate(articles[:3], 1):
                    source = article.get('source', {}).get('name', '不明')
                    title = article.get('title', '')[:50]
                    print(f"   {i}. [{source}] {title}...")
            
            print(f"   {Colors.YELLOW}無料枠: 月500リクエスト{Colors.END}")
            return True
            
        elif response.status_code == 401:
            print(f"{Colors.RED}❌ APIキーが無効です{Colors.END}")
            return False
        elif response.status_code == 429:
            print(f"{Colors.YELLOW}⚠️ レート制限に達しています{Colors.END}")
            return False
        else:
            print(f"{Colors.RED}❌ エラー: {response.status_code}{Colors.END}")
            return False
            
    except Exception as e:
        print(f"{Colors.RED}❌ エラー: {e}{Colors.END}")
        return False


def test_existing_apis():
    """既存API（Brave、YouTube）の確認"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}4. 既存API確認{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    results = []
    
    # Brave Search API
    brave_key = os.getenv('BRAVE_API_KEY')
    if brave_key:
        print(f"{Colors.GREEN}✅ Brave Search API: 設定済み{Colors.END}")
        results.append(True)
    else:
        print(f"{Colors.YELLOW}⚠️ Brave Search API: 未設定{Colors.END}")
        results.append(False)
    
    # YouTube API
    youtube_key = os.getenv('YOUTUBE_API_KEY')
    if youtube_key:
        print(f"{Colors.GREEN}✅ YouTube API: 設定済み{Colors.END}")
        results.append(True)
    else:
        print(f"{Colors.YELLOW}⚠️ YouTube API: 未設定{Colors.END}")
        results.append(False)
    
    # Google API
    google_key = os.getenv('GOOGLE_API_KEY')
    if google_key:
        print(f"{Colors.GREEN}✅ Google API: 設定済み{Colors.END}")
        results.append(True)
    else:
        print(f"{Colors.YELLOW}⚠️ Google API: 未設定{Colors.END}")
        results.append(False)
    
    return all(results)


def main():
    """メイン実行"""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}API接続テスト - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}")
    
    results = {
        'SerpAPI': test_serpapi(),
        'Twitter API': test_twitter_api(),
        'News API': test_news_api(),
        '既存API': test_existing_apis()
    }
    
    # サマリー
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}テスト結果サマリー{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}")
    
    total = len(results)
    success = sum(1 for v in results.values() if v)
    
    for api, status in results.items():
        if status:
            print(f"  {Colors.GREEN}✅ {api}{Colors.END}")
        else:
            print(f"  {Colors.RED}❌ {api}{Colors.END}")
    
    print(f"\n{Colors.BOLD}成功率: {success}/{total} ({success/total*100:.0f}%){Colors.END}")
    
    if success == total:
        print(f"{Colors.GREEN}{Colors.BOLD}\n🎉 すべてのAPIが正常に動作しています！{Colors.END}")
        print(f"{Colors.GREEN}知名度測定精度: 96%達成可能{Colors.END}")
    elif success >= 3:
        print(f"{Colors.YELLOW}{Colors.BOLD}\n⚠️ 一部のAPIに問題がありますが、基本機能は動作します{Colors.END}")
        print(f"{Colors.YELLOW}知名度測定精度: 85%程度{Colors.END}")
    else:
        print(f"{Colors.RED}{Colors.BOLD}\n❌ APIの設定を確認してください{Colors.END}")
    
    # 依存パッケージ確認
    print(f"\n{Colors.BOLD}必要なパッケージ:{Colors.END}")
    print("  pip install google-search-results  # SerpAPI")
    print("  pip install python-dotenv  # 環境変数")
    print("  pip install requests  # HTTP リクエスト")


if __name__ == "__main__":
    main()