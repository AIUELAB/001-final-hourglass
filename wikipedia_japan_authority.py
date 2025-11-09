#!/usr/bin/env python3
"""
Wikipedia Japan Authority System
Wikipedia日本語版による正式名称確認システム

This system uses Wikipedia Japan page titles as the authoritative source
for determining correct display names for persons in the database.
"""

import requests
import json
import time
import os
import sqlite3
from src.database_utils import get_connection
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import re
from urllib.parse import quote

class WikipediaJapanAuthority:
    """Wikipedia Japan authority service for name validation"""
    
    def __init__(self, cache_days: int = 30):
        """
        Initialize Wikipedia Japan authority service
        
        Args:
            cache_days: Number of days to cache Wikipedia results
        """
        self.api_base = "https://ja.wikipedia.org/w/api.php"
        self.cache_days = cache_days
        self.cache_db = "wikipedia_cache.db"
        self.manual_overrides = self.load_manual_overrides()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'UltraThinkBot/1.0 (https://example.com/contact)'
        })
        
        # Initialize cache database
        self.init_cache_db()
        
    def init_cache_db(self):
        """Initialize SQLite cache database"""
        conn = get_connection(self.cache_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wikipedia_cache (
                query TEXT PRIMARY KEY,
                page_title TEXT,
                redirect_from TEXT,
                categories TEXT,
                extract TEXT,
                cached_at TIMESTAMP,
                confidence REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def load_manual_overrides(self) -> Dict[str, str]:
        """Load manual override rules for special cases"""
        overrides_file = "wikipedia_manual_overrides.json"
        
        if os.path.exists(overrides_file):
            with open(overrides_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # Default overrides for known edge cases
        default_overrides = {
            # K-pop artists - use original alphabet
            "PSY": "PSY",
            "サイ": "PSY",
            "BTS": "BTS",
            "防弾少年団": "BTS",
            "BLACKPINK": "BLACKPINK",
            "ブラックピンク": "BLACKPINK",
            "TWICE": "TWICE",
            "トゥワイス": "TWICE",
            "SEVENTEEN": "SEVENTEEN",
            "セブンティーン": "SEVENTEEN",
            "Stray Kids": "Stray Kids",
            "ストレイキッズ": "Stray Kids",
            "ENHYPEN": "ENHYPEN",
            "エンハイプン": "ENHYPEN",
            "IVE": "IVE",
            "アイヴ": "IVE",
            "LE SSERAFIM": "LE SSERAFIM",
            "ル・セラフィム": "LE SSERAFIM",
            
            # BTS members - use stage names
            "RM": "RM",
            "Jin": "Jin",
            "ジン": "Jin",
            "Suga": "Suga",
            "シュガ": "Suga",
            "J-Hope": "J-Hope",
            "ジェイホープ": "J-Hope",
            "Jimin": "Jimin",
            "ジミン": "Jimin",
            "V": "V",
            "ヴィ": "V",
            "Jungkook": "Jungkook",
            "ジョングク": "Jungkook",
            
            # Japanese artists with established English names
            "hyde": "hyde",
            "YOSHIKI": "YOSHIKI",
            "GACKT": "GACKT",
            "Ado": "Ado",
            "DAIGO": "DAIGO",
            "HIKAKIN": "ヒカキン"
        }
        
        # Save default overrides
        with open(overrides_file, 'w', encoding='utf-8') as f:
            json.dump(default_overrides, f, ensure_ascii=False, indent=2)
        
        return default_overrides
    
    def get_cached_result(self, query: str) -> Optional[Dict]:
        """Get cached Wikipedia result if still valid"""
        conn = get_connection(self.cache_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT page_title, redirect_from, categories, extract, cached_at, confidence
            FROM wikipedia_cache
            WHERE query = ? AND cached_at > ?
        ''', (query, datetime.now() - timedelta(days=self.cache_days)))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'page_title': result[0],
                'redirect_from': result[1],
                'categories': json.loads(result[2]) if result[2] else [],
                'extract': result[3],
                'cached_at': result[4],
                'confidence': result[5]
            }
        
        return None
    
    def save_to_cache(self, query: str, result: Dict):
        """Save Wikipedia result to cache"""
        conn = get_connection(self.cache_db)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO wikipedia_cache
            (query, page_title, redirect_from, categories, extract, cached_at, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            query,
            result.get('page_title', ''),
            result.get('redirect_from', ''),
            json.dumps(result.get('categories', []), ensure_ascii=False),
            result.get('extract', ''),
            datetime.now(),
            result.get('confidence', 0.0)
        ))
        
        conn.commit()
        conn.close()
    
    def search_wikipedia(self, query: str) -> Optional[Dict]:
        """Search Wikipedia Japan for a person"""
        # Check manual overrides first
        if query in self.manual_overrides:
            return {
                'page_title': self.manual_overrides[query],
                'confidence': 1.0,
                'source': 'manual_override'
            }
        
        # Check cache
        cached = self.get_cached_result(query)
        if cached:
            cached['source'] = 'cache'
            return cached
        
        # Search Wikipedia
        try:
            # First try exact title match
            page_info = self.get_page_info(query)
            if page_info:
                self.save_to_cache(query, page_info)
                page_info['source'] = 'wikipedia_exact'
                return page_info
            
            # Try search API
            search_results = self.search_pages(query)
            if search_results:
                # Get the first result's page info
                first_result = search_results[0]
                page_info = self.get_page_info(first_result['title'])
                if page_info:
                    # Calculate confidence based on search rank and title similarity
                    confidence = self.calculate_confidence(query, first_result['title'])
                    page_info['confidence'] = confidence
                    self.save_to_cache(query, page_info)
                    page_info['source'] = 'wikipedia_search'
                    return page_info
        
        except Exception as e:
            print(f"Error searching Wikipedia for '{query}': {e}")
        
        return None
    
    def get_page_info(self, title: str) -> Optional[Dict]:
        """Get detailed page information from Wikipedia"""
        params = {
            'action': 'query',
            'format': 'json',
            'titles': title,
            'prop': 'info|categories|extracts|redirects',
            'inprop': 'displaytitle',
            'exintro': True,
            'explaintext': True,
            'exsentences': 2
        }
        
        try:
            response = self.session.get(self.api_base, params=params)
            response.raise_for_status()
            data = response.json()
            
            pages = data.get('query', {}).get('pages', {})
            
            for page_id, page_data in pages.items():
                if page_id != '-1':  # Page exists
                    # Get display title (canonical form)
                    display_title = page_data.get('displaytitle', page_data.get('title', ''))
                    
                    # Remove HTML tags if present
                    display_title = re.sub(r'<[^>]+>', '', display_title)
                    
                    # Get categories
                    categories = [cat['title'] for cat in page_data.get('categories', [])]
                    
                    # Check if it's a person page
                    is_person = self.is_person_page(categories, page_data.get('extract', ''))
                    
                    return {
                        'page_title': display_title,
                        'redirect_from': None,
                        'categories': categories,
                        'extract': page_data.get('extract', ''),
                        'is_person': is_person,
                        'confidence': 1.0 if is_person else 0.7
                    }
        
        except Exception as e:
            print(f"Error getting page info for '{title}': {e}")
        
        return None
    
    def search_pages(self, query: str, limit: int = 5) -> List[Dict]:
        """Search for pages matching the query"""
        params = {
            'action': 'query',
            'format': 'json',
            'list': 'search',
            'srsearch': query,
            'srlimit': limit,
            'srinfo': 'totalhits'
        }
        
        try:
            response = self.session.get(self.api_base, params=params)
            response.raise_for_status()
            data = response.json()
            
            return data.get('query', {}).get('search', [])
        
        except Exception as e:
            print(f"Error searching pages for '{query}': {e}")
        
        return []
    
    def is_person_page(self, categories: List[str], extract: str) -> bool:
        """Determine if a Wikipedia page is about a person"""
        # Check categories for person indicators
        person_category_patterns = [
            r'年生',  # Birth year
            r'存命人物',  # Living person
            r'年没',  # Death year
            r'歌手',  # Singer
            r'俳優',  # Actor
            r'アイドル',  # Idol
            r'ミュージシャン',  # Musician
            r'政治家',  # Politician
            r'実業家',  # Businessperson
            r'作家',  # Writer
            r'芸人',  # Entertainer
            r'YouTuber',
            r'の人物',  # People from...
        ]
        
        for category in categories:
            for pattern in person_category_patterns:
                if re.search(pattern, category):
                    return True
        
        # Check extract for person indicators
        person_extract_patterns = [
            r'生まれ',  # Born
            r'本名',  # Real name
            r'出身',  # From/Origin
            r'である。',  # Is a...
            r'歌手',
            r'俳優',
            r'アイドル'
        ]
        
        for pattern in person_extract_patterns:
            if re.search(pattern, extract):
                return True
        
        return False
    
    def calculate_confidence(self, query: str, found_title: str) -> float:
        """Calculate confidence score for a match"""
        # Exact match
        if query == found_title:
            return 1.0
        
        # Case-insensitive match
        if query.lower() == found_title.lower():
            return 0.95
        
        # One contains the other
        if query in found_title or found_title in query:
            return 0.85
        
        # Partial match
        query_parts = set(query.split())
        title_parts = set(found_title.split())
        overlap = len(query_parts & title_parts)
        
        if overlap > 0:
            return 0.5 + (0.3 * overlap / max(len(query_parts), len(title_parts)))
        
        return 0.3
    
    def get_canonical_name(self, person_name: str, nationality: str = None, 
                          occupation: str = None) -> Dict:
        """
        Get the canonical display name for a person
        
        Args:
            person_name: Person's name to look up
            nationality: Person's nationality (helps with context)
            occupation: Person's occupation (helps with context)
        
        Returns:
            Dictionary with canonical name and confidence
        """
        # Check manual overrides first
        if person_name in self.manual_overrides:
            return {
                'canonical_name': self.manual_overrides[person_name],
                'confidence': 1.0,
                'source': 'manual_override',
                'reasoning': 'Manually configured override'
            }
        
        # Apply cultural rules before Wikipedia search
        cultural_result = self.apply_cultural_rules(person_name, nationality, occupation)
        if cultural_result and cultural_result.get('confidence', 0) >= 0.9:
            return cultural_result
        
        # Search Wikipedia
        wiki_result = self.search_wikipedia(person_name)
        
        if wiki_result and wiki_result.get('is_person', False):
            return {
                'canonical_name': wiki_result['page_title'],
                'confidence': wiki_result.get('confidence', 0.7),
                'source': wiki_result.get('source', 'wikipedia'),
                'reasoning': f"Wikipedia Japan page title: {wiki_result['page_title']}"
            }
        
        # Fall back to cultural rules
        if cultural_result:
            return cultural_result
        
        # No authoritative source found
        return {
            'canonical_name': person_name,
            'confidence': 0.3,
            'source': 'unchanged',
            'reasoning': 'No authoritative source found'
        }
    
    def apply_cultural_rules(self, person_name: str, nationality: str, 
                            occupation: str) -> Optional[Dict]:
        """Apply cultural context rules for name display"""
        # K-pop rule: Korean entertainers keep alphabet names
        if nationality == '韓国':
            if occupation and any(term in str(occupation) for term in ['歌手', 'アイドル', 'K-POP', 'ラッパー']):
                # If it's already alphabet, keep it
                if re.match(r'^[A-Za-z\s\-]+$', person_name):
                    return {
                        'canonical_name': person_name,
                        'confidence': 0.95,
                        'source': 'cultural_rule',
                        'reasoning': 'K-pop artists use original alphabet names in Japan'
                    }
                # If it's katakana, might need to convert
                elif re.search(r'[ァ-ヶー]', person_name):
                    # Check if we have a known conversion
                    if person_name in self.manual_overrides:
                        return {
                            'canonical_name': self.manual_overrides[person_name],
                            'confidence': 0.9,
                            'source': 'cultural_rule',
                            'reasoning': 'K-pop artist katakana converted to alphabet'
                        }
        
        # Japanese artist rule
        if nationality == '日本':
            # Check if it's an established English stage name
            established_english = ['hyde', 'YOSHIKI', 'GACKT', 'Ado', 'DAIGO']
            if person_name in established_english:
                return {
                    'canonical_name': person_name,
                    'confidence': 0.95,
                    'source': 'cultural_rule',
                    'reasoning': 'Established English stage name for Japanese artist'
                }
        
        return None
    
    def validate_display_name(self, current_display: str, person_data: Dict) -> Dict:
        """
        Validate a current display name against Wikipedia authority
        
        Args:
            current_display: Current display name in database
            person_data: Full person data including nationality, occupation, etc.
        
        Returns:
            Validation result with recommendations
        """
        canonical_result = self.get_canonical_name(
            current_display,
            person_data.get('nationality'),
            person_data.get('occupation')
        )
        
        is_valid = canonical_result['canonical_name'] == current_display
        
        return {
            'is_valid': is_valid,
            'current': current_display,
            'recommended': canonical_result['canonical_name'],
            'confidence': canonical_result['confidence'],
            'source': canonical_result['source'],
            'reasoning': canonical_result['reasoning'],
            'needs_correction': not is_valid and canonical_result['confidence'] >= 0.7
        }
    
    def batch_validate(self, persons: List[Dict]) -> List[Dict]:
        """
        Validate multiple persons in batch
        
        Args:
            persons: List of person dictionaries
        
        Returns:
            List of validation results
        """
        results = []
        
        for i, person in enumerate(persons):
            # Rate limiting
            if i > 0 and i % 10 == 0:
                time.sleep(1)  # Be nice to Wikipedia servers
            
            validation = self.validate_display_name(
                person.get('person_name_display', ''),
                person
            )
            
            validation['person_id'] = person.get('person_id')
            results.append(validation)
            
            # Progress indicator
            if (i + 1) % 50 == 0:
                print(f"Validated {i + 1}/{len(persons)} persons...")
        
        return results
    
    def generate_authority_report(self, validation_results: List[Dict]) -> Dict:
        """Generate summary report of validation results"""
        total = len(validation_results)
        valid = sum(1 for r in validation_results if r['is_valid'])
        needs_correction = sum(1 for r in validation_results if r.get('needs_correction', False))
        
        by_source = {}
        for result in validation_results:
            source = result.get('source', 'unknown')
            by_source[source] = by_source.get(source, 0) + 1
        
        confidence_buckets = {
            'high': sum(1 for r in validation_results if r.get('confidence', 0) >= 0.9),
            'medium': sum(1 for r in validation_results if 0.7 <= r.get('confidence', 0) < 0.9),
            'low': sum(1 for r in validation_results if r.get('confidence', 0) < 0.7)
        }
        
        return {
            'total_validated': total,
            'valid_count': valid,
            'valid_percentage': (valid / total * 100) if total > 0 else 0,
            'needs_correction': needs_correction,
            'by_source': by_source,
            'confidence_distribution': confidence_buckets,
            'timestamp': datetime.now().isoformat()
        }


def main():
    """Test the Wikipedia authority system"""
    authority = WikipediaJapanAuthority()
    
    # Test cases
    test_cases = [
        {'name': 'PSY', 'nationality': '韓国', 'occupation': '歌手'},
        {'name': 'サイ', 'nationality': '韓国', 'occupation': 'K-POPアイドル'},
        {'name': 'マイケル・ジャクソン', 'nationality': 'アメリカ', 'occupation': '歌手'},
        {'name': 'HIKAKIN', 'nationality': '日本', 'occupation': 'YouTuber'},
        {'name': 'Ado', 'nationality': '日本', 'occupation': '歌手'},
    ]
    
    print("Testing Wikipedia Japan Authority System\n" + "="*50)
    
    for test in test_cases:
        result = authority.get_canonical_name(
            test['name'],
            test['nationality'],
            test['occupation']
        )
        
        print(f"\nInput: {test['name']} ({test['nationality']})")
        print(f"Canonical: {result['canonical_name']}")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"Source: {result['source']}")
        print(f"Reasoning: {result['reasoning']}")


if __name__ == "__main__":
    main()