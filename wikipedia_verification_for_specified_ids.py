#!/usr/bin/env python3
"""
Wikipedia検証システム - 指定されたperson_idの検証
"""

import json
import csv
import requests
import time
import urllib.parse
from datetime import datetime
import logging
from typing import Dict, List, Any, Optional

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WikipediaVerifier:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Ultra Think Wikipedia Verifier/1.0 (https://example.com/contact)'
        })
        self.rate_limit_delay = 0.5  # 500ms間隔
    
    def verify_wikipedia_existence(self, person_name: str, person_name_display: str = None) -> Dict[str, Any]:
        """
        Wikipedia検証を実行
        """
        names_to_check = [person_name]
        if person_name_display and person_name_display != person_name:
            names_to_check.append(person_name_display)
        
        logger.info(f"Wikipedia検証開始: {names_to_check}")
        
        for name in names_to_check:
            result = self._check_wikipedia_api(name)
            if result['exists']:
                logger.info(f"Wikipedia記事発見: {name} -> {result['title']}")
                return result
            
            # 英語表記での検索も試行
            result_en = self._check_wikipedia_api_en(name)
            if result_en['exists']:
                logger.info(f"English Wikipedia記事発見: {name} -> {result_en['title']}")
                return result_en
        
        logger.warning(f"Wikipedia記事未発見: {names_to_check}")
        return {
            'exists': False,
            'title': None,
            'url': None,
            'extract': None,
            'language': None,
            'search_terms': names_to_check,
            'checked_at': datetime.now().isoformat()
        }
    
    def _check_wikipedia_api(self, search_term: str) -> Dict[str, Any]:
        """日本語Wikipedia API検索"""
        time.sleep(self.rate_limit_delay)
        
        try:
            # 検索API
            search_url = "https://ja.wikipedia.org/api/rest_v1/page/search"
            search_params = {
                'q': search_term,
                'limit': 3
            }
            
            response = self.session.get(search_url, params=search_params, timeout=10)
            response.raise_for_status()
            search_data = response.json()
            
            if not search_data.get('pages'):
                return self._empty_result()
            
            # 最初の結果を詳細取得
            first_result = search_data['pages'][0]
            title = first_result['title']
            
            # 詳細情報取得
            summary_url = f"https://ja.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
            summary_response = self.session.get(summary_url, timeout=10)
            summary_response.raise_for_status()
            summary_data = summary_response.json()
            
            return {
                'exists': True,
                'title': title,
                'url': f"https://ja.wikipedia.org/wiki/{urllib.parse.quote(title)}",
                'extract': summary_data.get('extract', ''),
                'language': 'ja',
                'search_term': search_term,
                'checked_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"日本語Wikipedia API エラー ({search_term}): {str(e)}")
            return self._empty_result()
    
    def _check_wikipedia_api_en(self, search_term: str) -> Dict[str, Any]:
        """英語Wikipedia API検索"""
        time.sleep(self.rate_limit_delay)
        
        try:
            search_url = "https://en.wikipedia.org/api/rest_v1/page/search"
            search_params = {
                'q': search_term,
                'limit': 3
            }
            
            response = self.session.get(search_url, params=search_params, timeout=10)
            response.raise_for_status()
            search_data = response.json()
            
            if not search_data.get('pages'):
                return self._empty_result()
            
            first_result = search_data['pages'][0]
            title = first_result['title']
            
            summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
            summary_response = self.session.get(summary_url, timeout=10)
            summary_response.raise_for_status()
            summary_data = summary_response.json()
            
            return {
                'exists': True,
                'title': title,
                'url': f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title)}",
                'extract': summary_data.get('extract', ''),
                'language': 'en',
                'search_term': search_term,
                'checked_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"英語Wikipedia API エラー ({search_term}): {str(e)}")
            return self._empty_result()
    
    def _empty_result(self) -> Dict[str, Any]:
        """空の結果を返す"""
        return {
            'exists': False,
            'title': None,
            'url': None,
            'extract': None,
            'language': None,
            'checked_at': datetime.now().isoformat()
        }

def analyze_placeholder_patterns(name: str, occupation: str) -> Dict[str, Any]:
    """プレースホルダーパターンの分析"""
    placeholder_patterns = [
        # 機械的名前パターン
        r'Actor \d+',
        r'Singer \d+',
        r'Player \d+',
        r'Athlete \d+',
        r'Person \d+',
        # 一般的すぎる名前
        r'^(田中|佐藤|鈴木|高橋|渡辺|山田|中村|小林|加藤|吉田)\s*[一二三四五六七八九十]?$',
        # 職業名がそのまま名前
        r'^(俳優|歌手|選手|アスリート)$'
    ]
    
    import re
    is_placeholder = False
    detected_patterns = []
    
    for pattern in placeholder_patterns:
        if re.search(pattern, name) or re.search(pattern, occupation):
            is_placeholder = True
            detected_patterns.append(pattern)
    
    # 追加の分析
    analysis = {
        'is_placeholder': is_placeholder,
        'detected_patterns': detected_patterns,
        'name_length': len(name),
        'has_numbers': bool(re.search(r'\d', name)),
        'is_common_surname_only': len(name.split()) == 1 and name in ['田中', '佐藤', '鈴木', '高橋', '渡辺'],
        'analyzed_at': datetime.now().isoformat()
    }
    
    return analysis

def main():
    """メイン処理"""
    
    # 抽出されたデータ（検索結果から）
    found_records = [
        {
            'person_id': 'P001562',
            'person_name': '三浦 光政',
            'person_name_display': '三浦光政',
            'occupation': '大名',
            'nationality': '日本',
            'category': '歴史'
        },
        {
            'person_id': 'P001563',
            'person_name': '三浦 光氏',
            'person_name_display': '三浦光氏',
            'occupation': '家臣',
            'nationality': '日本',
            'category': '歴史'
        },
        {
            'person_id': 'P001565',
            'person_name': '三浦 康定',
            'person_name_display': '三浦康定',
            'occupation': '藩主',
            'nationality': '日本',
            'category': '歴史'
        },
        {
            'person_id': 'P001567',
            'person_name': '三浦 忠政',
            'person_name_display': '三浦忠政',
            'occupation': '家臣',
            'nationality': '日本',
            'category': '歴史'
        },
        {
            'person_id': 'P001568',
            'person_name': '三浦 正盛',
            'person_name_display': '三浦正盛',
            'occupation': '藩主',
            'nationality': '日本',
            'category': '歴史'
        },
        {
            'person_id': 'P001576',
            'person_name': '三浦 義経',
            'person_name_display': '三浦義経',
            'occupation': '武将',
            'nationality': '日本',
            'category': '歴史'
        },
        {
            'person_id': 'P001577',
            'person_name': '三浦雄一郎',
            'person_name_display': '三浦雄一郎',
            'occupation': '冒険家',
            'nationality': '日本',
            'category': 'その他'
        },
        {
            'person_id': 'P002839',
            'person_name': '小林七海',
            'person_name_display': '小林七海',
            'occupation': '俳優',
            'nationality': '日本',
            'category': 'エンタメ'
        },
        {
            'person_id': 'P002864',
            'person_name': '小林楓',
            'person_name_display': '小林楓',
            'occupation': '歌手',
            'nationality': '日本',
            'category': 'エンタメ'
        },
        {
            'person_id': 'P002875',
            'person_name': '小林美咲',
            'person_name_display': '小林美咲',
            'occupation': '歌手',
            'nationality': '日本',
            'category': 'エンタメ'
        },
        {
            'person_id': 'P003081',
            'person_name': '山本 陸',
            'person_name_display': '山本陸',
            'occupation': '俳優',
            'nationality': '日本',
            'category': 'エンタメ'
        },
        {
            'person_id': 'P004252',
            'person_name': '渡辺愛',
            'person_name_display': '渡辺愛',
            'occupation': '俳優',
            'nationality': '日本',
            'category': 'エンタメ'
        },
        {
            'person_id': 'P004257',
            'person_name': '渡辺楓',
            'person_name_display': '渡辺楓',
            'occupation': '俳優',
            'nationality': '日本',
            'category': 'エンタメ'
        },
        {
            'person_id': 'P004266',
            'person_name': '渡辺真央',
            'person_name_display': '渡辺真央',
            'occupation': '歌手',
            'nationality': '日本',
            'category': 'エンタメ'
        },
        {
            'person_id': 'P004271',
            'person_name': '渡辺美里',
            'person_name_display': '渡辺美里',
            'occupation': '歌手',
            'nationality': '日本',
            'category': 'エンタメ'
        },
        {
            'person_id': 'P004279',
            'person_name': '渡辺 陸',
            'person_name_display': '渡辺陸',
            'occupation': '俳優',
            'nationality': '日本',
            'category': 'エンタメ'
        },
        {
            'person_id': 'P005334',
            'person_name': '阿部蓮',
            'person_name_display': '阿部蓮',
            'occupation': '体操選手（平行棒）',
            'nationality': '日本',
            'category': 'スポーツ'
        },
        {
            'person_id': 'P005338',
            'person_name': '阿部陸',
            'person_name_display': '阿部陸',
            'occupation': 'アメフト選手（RB）',
            'nationality': '日本',
            'category': 'スポーツ'
        },
        {
            'person_id': 'P005339',
            'person_name': '阿部陽菜',
            'person_name_display': '阿部陽菜',
            'occupation': 'テニス選手（選手）',
            'nationality': '日本',
            'category': 'スポーツ'
        },
        {
            'person_id': 'P005340',
            'person_name': '阿部颯太',
            'person_name_display': '阿部颯太',
            'occupation': 'サッカー選手（FW）',
            'nationality': '日本',
            'category': 'スポーツ'
        }
    ]
    
    verifier = WikipediaVerifier()
    results = []
    
    logger.info(f"Wikipedia検証開始: {len(found_records)}件のレコード")
    
    for record in found_records:
        logger.info(f"検証中: {record['person_id']} - {record['person_name']}")
        
        # プレースホルダー分析
        placeholder_analysis = analyze_placeholder_patterns(
            record['person_name'], 
            record['occupation']
        )
        
        # Wikipedia検証
        wikipedia_result = verifier.verify_wikipedia_existence(
            record['person_name'],
            record.get('person_name_display')
        )
        
        # 結果をまとめる
        result = {
            **record,
            'placeholder_analysis': placeholder_analysis,
            'wikipedia_verification': wikipedia_result,
            'final_status': 'FOUND' if wikipedia_result['exists'] else 'NOT_FOUND',
            'verification_completed_at': datetime.now().isoformat()
        }
        
        results.append(result)
        
        # プログレス表示
        if wikipedia_result['exists']:
            logger.info(f"✅ Wikipedia記事発見: {record['person_name']} -> {wikipedia_result['title']}")
        else:
            logger.warning(f"❌ Wikipedia記事未発見: {record['person_name']}")
    
    # 結果をJSONファイルに保存
    output_file = f"wikipedia_verification_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # サマリー出力
    found_count = sum(1 for r in results if r['final_status'] == 'FOUND')
    not_found_count = sum(1 for r in results if r['final_status'] == 'NOT_FOUND')
    placeholder_count = sum(1 for r in results if r['placeholder_analysis']['is_placeholder'])
    
    summary = {
        'total_records': len(results),
        'wikipedia_found': found_count,
        'wikipedia_not_found': not_found_count,
        'placeholder_detected': placeholder_count,
        'verification_date': datetime.now().isoformat(),
        'breakdown_by_category': {}
    }
    
    # カテゴリ別集計
    for category in set(r['category'] for r in results):
        category_records = [r for r in results if r['category'] == category]
        summary['breakdown_by_category'][category] = {
            'total': len(category_records),
            'found': sum(1 for r in category_records if r['final_status'] == 'FOUND'),
            'not_found': sum(1 for r in category_records if r['final_status'] == 'NOT_FOUND'),
            'placeholder': sum(1 for r in category_records if r['placeholder_analysis']['is_placeholder'])
        }
    
    # サマリーを出力
    logger.info("=" * 60)
    logger.info("Wikipedia検証結果サマリー")
    logger.info("=" * 60)
    logger.info(f"検証対象: {summary['total_records']}件")
    logger.info(f"Wikipedia記事発見: {found_count}件 ({found_count/len(results)*100:.1f}%)")
    logger.info(f"Wikipedia記事未発見: {not_found_count}件 ({not_found_count/len(results)*100:.1f}%)")
    logger.info(f"プレースホルダー検出: {placeholder_count}件 ({placeholder_count/len(results)*100:.1f}%)")
    
    logger.info("\nカテゴリ別詳細:")
    for category, stats in summary['breakdown_by_category'].items():
        logger.info(f"{category}: {stats['found']}/{stats['total']} 発見 ({stats['found']/stats['total']*100:.1f}%)")
    
    # サマリーファイルも保存
    summary_file = f"wikipedia_verification_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n結果ファイル: {output_file}")
    logger.info(f"サマリーファイル: {summary_file}")
    
    return results

if __name__ == "__main__":
    main()