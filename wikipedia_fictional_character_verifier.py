#!/usr/bin/env python3
"""
Wikipedia Fictional Character Verification System
===================================================

This script verifies which fictional characters have Wikipedia pages and
determines their cultural significance for database restoration.

Features:
- Wikipedia page existence verification
- Cultural significance classification
- Character importance scoring
- Database restoration recommendations
- Detailed reporting and logging

Author: Claude Code
Date: 2025-08-30
"""

import csv
import json
import requests
import time
import logging
import re
from typing import Dict, List, Tuple, Optional, Set
from urllib.parse import quote
from datetime import datetime
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'wikipedia_verification_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WikipediaVerifier:
    """Wikipedia page verification and cultural significance analyzer."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Cultural-Character-Verifier/1.0 (Educational Research)'
        })
        
        # Cultural significance categories with scoring
        self.cultural_categories = {
            'iconic_global': {
                'score': 100,
                'keywords': [
                    'mario', 'luigi', 'peach', 'bowser', 'yoshi',  # Nintendo icons
                    'link', 'zelda', 'ganondorf',  # Zelda series
                    'pikachu', 'pokemon', 'charizard', 'mewtwo', 'eevee',  # Pokemon
                    'sonic', 'pac-man', 'mega man', 'kirby',  # Gaming classics
                    'mickey mouse', 'donald duck', 'goofy',  # Disney
                    'hello kitty', 'totoro', 'spirited away'  # Japanese global icons
                ]
            },
            'japanese_cultural_heritage': {
                'score': 95,
                'keywords': [
                    'doraemon', 'anpanman', 'astro boy', 'sazae-san',  # National icons
                    'luffy', 'one piece', 'zoro', 'sanji',  # One Piece
                    'goku', 'vegeta', 'piccolo', 'gohan',  # Dragon Ball
                    'naruto', 'sasuke', 'sakura', 'kakashi',  # Naruto
                    'ichigo', 'rukia', 'bleach',  # Bleach
                    'edward elric', 'alphonse', 'fullmetal',  # FMA
                    'shinji ikari', 'rei ayanami', 'asuka',  # Evangelion
                ]
            },
            'anime_manga_major': {
                'score': 85,
                'keywords': [
                    'attack on titan', 'eren', 'mikasa', 'armin', 'levi',
                    'demon slayer', 'tanjiro', 'nezuko', 'zenitsu', 'inosuke',
                    'my hero academia', 'deku', 'bakugo', 'todoroki',
                    'death note', 'light yagami', 'l', 'ryuk',
                    'cowboy bebop', 'spike spiegel', 'faye valentine',
                    'sailor moon', 'usagi', 'tuxedo mask',
                ]
            },
            'gaming_franchises': {
                'score': 75,
                'keywords': [
                    'final fantasy', 'cloud', 'sephiroth', 'tifa', 'aerith',
                    'street fighter', 'ryu', 'chun-li', 'ken', 'guile',
                    'tekken', 'kazuya', 'heihachi', 'jin',
                    'mortal kombat', 'sub-zero', 'scorpion', 'raiden',
                ]
            },
            'cultural_minor': {
                'score': 50,
                'keywords': [
                    'spy x family', 'anya', 'loid', 'yor',  # Recent popular
                    'jujutsu kaisen', 'yuji', 'megumi', 'nobara',
                    'chainsaw man', 'denji', 'makima', 'power',
                ]
            }
        }
        
        # Languages to check for Wikipedia articles
        self.wikipedia_languages = ['en', 'ja', 'fr', 'de', 'es', 'it', 'ru', 'zh']
        
        # Cache for API results
        self.cache = {}
        
    def normalize_name(self, name: str) -> str:
        """Normalize character name for comparison."""
        if not name:
            return ""
        
        # Remove common suffixes and prefixes
        name = re.sub(r'\s*\([^)]+\)$', '', name)  # Remove parenthetical info
        name = re.sub(r'\s*(の|・|=|\-|_)\s*', ' ', name)  # Normalize separators
        name = name.strip().lower()
        
        return name
    
    def calculate_cultural_score(self, character_data: Dict[str, str]) -> Tuple[int, str]:
        """Calculate cultural significance score for a character."""
        name = character_data.get('person_name', '')
        name_ja = character_data.get('person_name_ja', '')
        display_name = character_data.get('person_name_display', '')
        occupation = character_data.get('occupation', '')
        
        # Combine all name variants for searching
        search_text = ' '.join([
            self.normalize_name(name),
            self.normalize_name(name_ja),
            self.normalize_name(display_name),
            self.normalize_name(occupation)
        ]).lower()
        
        max_score = 0
        best_category = 'unknown'
        
        # Check against cultural categories
        for category, config in self.cultural_categories.items():
            for keyword in config['keywords']:
                if keyword.lower() in search_text:
                    if config['score'] > max_score:
                        max_score = config['score']
                        best_category = category
                        
        return max_score, best_category
    
    def check_wikipedia_page(self, character_name: str, lang: str = 'en') -> Optional[Dict]:
        """Check if a Wikipedia page exists for the character."""
        try:
            # Create cache key
            cache_key = f"{lang}:{character_name}"
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            # Search for the page
            search_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(character_name)}"
            
            response = self.session.get(search_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if it's a valid page (not disambiguation, etc.)
                if data.get('type') == 'standard':
                    result = {
                        'exists': True,
                        'title': data.get('title', ''),
                        'description': data.get('description', ''),
                        'extract': data.get('extract', ''),
                        'url': data.get('content_urls', {}).get('desktop', {}).get('page', ''),
                        'language': lang
                    }
                    self.cache[cache_key] = result
                    return result
            
            # Page doesn't exist
            result = {'exists': False, 'language': lang}
            self.cache[cache_key] = result
            return result
            
        except Exception as e:
            logger.warning(f"Error checking Wikipedia for {character_name} ({lang}): {e}")
            return {'exists': False, 'error': str(e), 'language': lang}
    
    def verify_character_significance(self, character_data: Dict[str, str]) -> Dict:
        """Comprehensive verification of character's cultural significance."""
        result = {
            'character_id': character_data.get('person_id', ''),
            'character_name': character_data.get('person_name', ''),
            'japanese_name': character_data.get('person_name_ja', ''),
            'display_name': character_data.get('person_name_display', ''),
            'occupation': character_data.get('occupation', ''),
            'cultural_score': 0,
            'cultural_category': 'unknown',
            'wikipedia_pages': {},
            'recommendation': 'remove',
            'reasoning': []
        }
        
        # Calculate cultural significance score
        score, category = self.calculate_cultural_score(character_data)
        result['cultural_score'] = score
        result['cultural_category'] = category
        
        if score > 0:
            result['reasoning'].append(f"Cultural significance: {category} (score: {score})")
        
        # Check Wikipedia existence in multiple languages
        names_to_check = set()
        
        # Add all name variants
        for name_field in ['person_name', 'person_name_ja', 'person_name_display']:
            name = character_data.get(name_field, '').strip()
            if name and len(name) > 2:
                names_to_check.add(name)
        
        wikipedia_found = False
        
        for name in names_to_check:
            if wikipedia_found and len(result['wikipedia_pages']) >= 3:
                break  # Limit API calls
                
            for lang in self.wikipedia_languages[:4]:  # Check top 4 languages
                if wikipedia_found and len(result['wikipedia_pages']) >= 2:
                    break
                    
                wiki_result = self.check_wikipedia_page(name, lang)
                
                if wiki_result and wiki_result.get('exists'):
                    result['wikipedia_pages'][f'{lang}_{name}'] = wiki_result
                    wikipedia_found = True
                    result['reasoning'].append(f"Wikipedia page found: {wiki_result.get('url', '')}")
                    
                # Rate limiting
                time.sleep(0.1)
        
        # Make recommendation based on score and Wikipedia presence
        if score >= 95 or (score >= 75 and wikipedia_found):
            result['recommendation'] = 'restore_high_priority'
        elif score >= 70 or (score >= 50 and wikipedia_found):
            result['recommendation'] = 'restore_medium_priority'  
        elif score >= 40 or wikipedia_found:
            result['recommendation'] = 'restore_low_priority'
        else:
            result['recommendation'] = 'remove'
            result['reasoning'].append("Low cultural significance and no Wikipedia verification")
        
        return result
    
    def process_removed_characters_file(self, csv_file_path: str) -> Dict:
        """Process the removed fictional characters CSV file."""
        logger.info(f"Processing removed characters file: {csv_file_path}")
        
        results = {
            'total_processed': 0,
            'restore_high_priority': [],
            'restore_medium_priority': [],
            'restore_low_priority': [],
            'remove_confirmed': [],
            'errors': [],
            'summary_stats': {
                'cultural_categories': {},
                'wikipedia_languages': {},
                'recommendations': {}
            }
        }
        
        # Get unique characters (remove duplicates)
        unique_characters = {}
        
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                for row in reader:
                    person_id = row.get('person_id', '')
                    if person_id and person_id not in unique_characters:
                        unique_characters[person_id] = row
                        
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            results['errors'].append(f"File reading error: {e}")
            return results
        
        logger.info(f"Found {len(unique_characters)} unique characters to verify")
        
        # Process each unique character
        for i, (person_id, character_data) in enumerate(unique_characters.items(), 1):
            try:
                logger.info(f"Processing {i}/{len(unique_characters)}: {character_data.get('person_name', person_id)}")
                
                verification_result = self.verify_character_significance(character_data)
                
                # Categorize by recommendation
                recommendation = verification_result['recommendation']
                results[recommendation].append(verification_result)
                
                # Update statistics
                category = verification_result['cultural_category']
                results['summary_stats']['cultural_categories'][category] = \
                    results['summary_stats']['cultural_categories'].get(category, 0) + 1
                
                results['summary_stats']['recommendations'][recommendation] = \
                    results['summary_stats']['recommendations'].get(recommendation, 0) + 1
                
                for wiki_info in verification_result['wikipedia_pages'].values():
                    lang = wiki_info.get('language', 'unknown')
                    results['summary_stats']['wikipedia_languages'][lang] = \
                        results['summary_stats']['wikipedia_languages'].get(lang, 0) + 1
                
                results['total_processed'] += 1
                
                # Progress logging
                if i % 10 == 0:
                    logger.info(f"Progress: {i}/{len(unique_characters)} processed")
                    
                # Rate limiting to be respectful to Wikipedia
                time.sleep(0.2)
                
            except Exception as e:
                logger.error(f"Error processing character {person_id}: {e}")
                results['errors'].append(f"Character {person_id}: {e}")
        
        logger.info("Processing completed!")
        return results

def main():
    """Main execution function."""
    verifier = WikipediaVerifier()
    
    # Path to the removed characters file
    removed_file_path = "removed_fictional_characters_20250831_073627.csv"
    
    if not os.path.exists(removed_file_path):
        logger.error(f"File not found: {removed_file_path}")
        return
    
    # Process the file
    results = verifier.process_removed_characters_file(removed_file_path)
    
    # Generate timestamp for output files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save detailed results
    results_file = f"wikipedia_verification_results_{timestamp}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Generate restoration recommendations
    restoration_file = f"character_restoration_recommendations_{timestamp}.csv"
    
    with open(restoration_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'person_id', 'character_name', 'japanese_name', 'display_name',
            'cultural_score', 'cultural_category', 'recommendation',
            'wikipedia_pages_count', 'reasoning'
        ])
        
        # Write restoration candidates
        for priority in ['restore_high_priority', 'restore_medium_priority', 'restore_low_priority']:
            for character in results[priority]:
                writer.writerow([
                    character['character_id'],
                    character['character_name'],
                    character['japanese_name'],
                    character['display_name'],
                    character['cultural_score'],
                    character['cultural_category'],
                    character['recommendation'],
                    len(character['wikipedia_pages']),
                    ' | '.join(character['reasoning'])
                ])
    
    # Generate summary report
    report_file = f"restoration_summary_report_{timestamp}.md"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# Fictional Character Restoration Analysis Report\n\n")
        f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write(f"## Executive Summary\n\n")
        f.write(f"- **Total Characters Analyzed**: {results['total_processed']}\n")
        f.write(f"- **High Priority Restorations**: {len(results['restore_high_priority'])}\n")
        f.write(f"- **Medium Priority Restorations**: {len(results['restore_medium_priority'])}\n")
        f.write(f"- **Low Priority Restorations**: {len(results['restore_low_priority'])}\n")
        f.write(f"- **Confirmed Removals**: {len(results['remove_confirmed'])}\n\n")
        
        f.write(f"## High Priority Restoration Candidates\n\n")
        f.write(f"These characters should definitely be restored to the database:\n\n")
        
        for character in sorted(results['restore_high_priority'], 
                              key=lambda x: x['cultural_score'], reverse=True)[:20]:
            f.write(f"### {character['display_name'] or character['character_name']}\n")
            f.write(f"- **ID**: {character['character_id']}\n")
            f.write(f"- **Cultural Score**: {character['cultural_score']}\n")
            f.write(f"- **Category**: {character['cultural_category']}\n")
            f.write(f"- **Wikipedia Pages**: {len(character['wikipedia_pages'])}\n")
            f.write(f"- **Reasoning**: {' | '.join(character['reasoning'])}\n\n")
        
        f.write(f"## Cultural Categories Distribution\n\n")
        for category, count in sorted(results['summary_stats']['cultural_categories'].items(), 
                                    key=lambda x: x[1], reverse=True):
            f.write(f"- **{category}**: {count}\n")
        
        f.write(f"\n## Wikipedia Language Coverage\n\n")
        for lang, count in sorted(results['summary_stats']['wikipedia_languages'].items(),
                                key=lambda x: x[1], reverse=True):
            f.write(f"- **{lang}**: {count}\n")
    
    # Print summary to console
    logger.info("=" * 60)
    logger.info("RESTORATION ANALYSIS COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total processed: {results['total_processed']}")
    logger.info(f"High priority: {len(results['restore_high_priority'])}")
    logger.info(f"Medium priority: {len(results['restore_medium_priority'])}")
    logger.info(f"Low priority: {len(results['restore_low_priority'])}")
    logger.info(f"Remove confirmed: {len(results['remove_confirmed'])}")
    logger.info("=" * 60)
    logger.info(f"Results saved to: {results_file}")
    logger.info(f"Recommendations saved to: {restoration_file}")
    logger.info(f"Report saved to: {report_file}")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()