#!/usr/bin/env python3
"""
Quick Character Analysis for Immediate Insights
===============================================

This script provides immediate analysis of removed fictional characters
without making external API calls, for quick decision making.

Author: Claude Code
Date: 2025-08-30
"""

import csv
import json
import re
from collections import defaultdict, Counter
from datetime import datetime
import pandas as pd

def analyze_removed_characters():
    """Quick analysis of removed fictional characters."""
    
    # Cultural significance indicators
    cultural_keywords = {
        'global_icons': [
            'mario', 'luigi', 'peach', 'bowser', 'yoshi',  # Nintendo
            'pikachu', 'pokemon', 'charizard', 'mewtwo',   # Pokemon  
            'link', 'zelda', 'ganondorf',                  # Zelda
            'sonic', 'pac-man', 'mega man', 'kirby',       # Gaming classics
            'mickey mouse', 'donald duck', 'hello kitty',  # Global characters
        ],
        'japanese_icons': [
            'doraemon', 'anpanman', 'astro boy', 'sazae',  # National icons
            'totoro', 'spirited away', 'nausicaa',         # Studio Ghibli
        ],
        'anime_major': [
            'goku', 'vegeta', 'piccolo', 'gohan',          # Dragon Ball
            'naruto', 'sasuke', 'sakura', 'kakashi',       # Naruto
            'luffy', 'zoro', 'sanji', 'nami',              # One Piece
            'ichigo', 'rukia', 'renji',                    # Bleach
            'edward', 'alphonse', 'roy mustang',           # FMA
            'shinji', 'rei', 'asuka', 'gendo',             # Evangelion
        ],
        'modern_popular': [
            'eren', 'mikasa', 'armin', 'levi',             # Attack on Titan
            'tanjiro', 'nezuko', 'zenitsu', 'inosuke',     # Demon Slayer
            'deku', 'bakugo', 'todoroki',                  # MHA
            'anya', 'loid', 'yor',                         # Spy x Family
        ]
    }
    
    # Load the removed characters file
    removed_file = "removed_fictional_characters_20250831_073627.csv"
    
    print("📊 Quick Analysis of Removed Fictional Characters")
    print("=" * 60)
    
    # Get unique characters
    unique_characters = {}
    total_rows = 0
    
    try:
        with open(removed_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                total_rows += 1
                person_id = row.get('person_id', '')
                if person_id and person_id not in unique_characters:
                    unique_characters[person_id] = row
        
        print(f"📋 Total rows in file: {total_rows}")
        print(f"🔍 Unique characters: {len(unique_characters)}")
        print()
        
        # Analyze removal reasons
        removal_reasons = Counter()
        for char in unique_characters.values():
            reason = char.get('removal_reason', 'unknown')
            removal_reasons[reason] += 1
        
        print("📈 Removal Reasons:")
        for reason, count in removal_reasons.most_common(5):
            print(f"  • {reason}: {count}")
        print()
        
        # Find culturally significant characters
        cultural_matches = defaultdict(list)
        must_restore = []
        
        for char_id, char_data in unique_characters.items():
            names = [
                char_data.get('person_name', '').lower(),
                char_data.get('person_name_ja', '').lower(), 
                char_data.get('person_name_display', '').lower()
            ]
            
            search_text = ' '.join(names)
            
            # Check against cultural categories
            for category, keywords in cultural_keywords.items():
                for keyword in keywords:
                    if any(keyword in name for name in names if name):
                        cultural_matches[category].append({
                            'id': char_id,
                            'name': char_data.get('person_name_display') or char_data.get('person_name', ''),
                            'japanese': char_data.get('person_name_ja', ''),
                            'occupation': char_data.get('occupation', ''),
                            'keyword': keyword
                        })
                        
                        # Global and Japanese icons are must-restore
                        if category in ['global_icons', 'japanese_icons']:
                            must_restore.append(char_data)
                        break
        
        print("🎯 Culturally Significant Characters Found:")
        print()
        
        total_cultural = 0
        for category, matches in cultural_matches.items():
            if matches:
                print(f"📌 {category.replace('_', ' ').title()}: {len(matches)} characters")
                total_cultural += len(matches)
                
                # Show top matches
                for match in sorted(matches, key=lambda x: x['name'])[:5]:
                    print(f"    • {match['name']} ({match['japanese']}) - {match['occupation']}")
                
                if len(matches) > 5:
                    print(f"    ... and {len(matches) - 5} more")
                print()
        
        print(f"🎯 Total Cultural Characters: {total_cultural}")
        print(f"🚨 Must-Restore Characters: {len(must_restore)}")
        print()
        
        # Analyze specific high-profile characters
        high_profile_search = [
            'doraemon', 'anpanman', 'mario', 'pikachu', 'goku', 'naruto', 
            'luffy', 'link', 'sonic', 'hello kitty', 'totoro'
        ]
        
        print("🌟 High-Profile Character Status:")
        high_profile_found = []
        
        for search_name in high_profile_search:
            found = False
            for char_id, char_data in unique_characters.items():
                names = [
                    char_data.get('person_name', '').lower(),
                    char_data.get('person_name_ja', '').lower(),
                    char_data.get('person_name_display', '').lower()
                ]
                
                if any(search_name in name for name in names if name):
                    display_name = char_data.get('person_name_display') or char_data.get('person_name', search_name)
                    print(f"  ✅ Found: {display_name}")
                    high_profile_found.append(char_data)
                    found = True
                    break
            
            if not found:
                print(f"  ❌ Missing: {search_name}")
        
        print()
        print(f"🎯 High-Profile Found: {len(high_profile_found)}/{len(high_profile_search)}")
        
        # Show incorrectly removed real people (false positives)
        print("\n⚠️  Potential False Positives (Real People Incorrectly Removed):")
        false_positives = []
        
        for char_id, char_data in unique_characters.items():
            removal_reason = char_data.get('removal_reason', '')
            occupation = char_data.get('occupation', '').lower()
            
            # Check for real people incorrectly flagged
            if 'name pattern match' in removal_reason.lower():
                name = char_data.get('person_name_display', char_data.get('person_name', ''))
                if any(real_occupation in occupation for real_occupation in 
                      ['ミュージシャン', '歌手', '女優', '俳優', '首相', 'ボクサー']):
                    false_positives.append({
                        'name': name,
                        'occupation': char_data.get('occupation', ''),
                        'reason': removal_reason
                    })
        
        for fp in false_positives[:5]:
            print(f"  • {fp['name']} ({fp['occupation']}) - {fp['reason'][:50]}...")
        
        if len(false_positives) > 5:
            print(f"  ... and {len(false_positives) - 5} more potential false positives")
        
        print()
        
        # Generate quick recommendations
        print("💡 Quick Restoration Recommendations:")
        print()
        print("🔴 IMMEDIATE RESTORATION (Cultural Icons):")
        print(f"  • {len(must_restore)} characters should be restored immediately")
        print("  • These include Doraemon, Mario, Pikachu, Goku, Naruto, etc.")
        print()
        print("🟡 REVIEW REQUIRED (False Positives):")
        print(f"  • {len(false_positives)} real people may have been incorrectly removed")
        print("  • Manual review recommended for name pattern matches")
        print()
        print("🟢 SELECTIVE RESTORATION:")
        print(f"  • {total_cultural - len(must_restore)} additional cultural characters")
        print("  • Wikipedia verification recommended for final decision")
        print()
        
        # Save quick analysis
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        analysis_data = {
            'analysis_date': datetime.now().isoformat(),
            'total_removed_rows': total_rows,
            'unique_characters': len(unique_characters),
            'cultural_categories': {k: len(v) for k, v in cultural_matches.items()},
            'must_restore_count': len(must_restore),
            'false_positives_count': len(false_positives),
            'high_profile_found': len(high_profile_found),
            'high_profile_total': len(high_profile_search),
            'removal_reasons': dict(removal_reasons),
            'recommendations': {
                'immediate_restore': len(must_restore),
                'review_required': len(false_positives),  
                'selective_restore': total_cultural - len(must_restore)
            }
        }
        
        with open(f'quick_character_analysis_{timestamp}.json', 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)
        
        print(f"📄 Analysis saved to: quick_character_analysis_{timestamp}.json")
        
    except FileNotFoundError:
        print(f"❌ Error: {removed_file} not found")
    except Exception as e:
        print(f"❌ Error during analysis: {e}")

if __name__ == "__main__":
    analyze_removed_characters()