#!/usr/bin/env python3
"""
Character Restoration Preview
============================

Shows exactly which characters would be restored without making changes.
Perfect for preview before running the full restoration system.

Author: Claude Code
Date: 2025-08-31
"""

import csv
import json
from collections import defaultdict

def preview_restoration():
    """Preview which characters would be restored."""
    
    # Must-restore cultural icons
    must_restore_keywords = [
        'doraemon', 'anpanman', 'mario', 'luigi', 'peach', 'bowser',
        'pikachu', 'charizard', 'mewtwo', 'link', 'zelda', 'ganondorf',
        'goku', 'vegeta', 'piccolo', 'naruto', 'sasuke', 'sakura',
        'luffy', 'zoro', 'sanji', 'nami', 'sonic', 'pac-man', 'kirby'
    ]
    
    # Load removed characters
    removed_file = "removed_fictional_characters_20250831_073627.csv"
    unique_characters = {}
    
    print("🎯 CHARACTER RESTORATION PREVIEW")
    print("=" * 60)
    print()
    
    try:
        with open(removed_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                person_id = row.get('person_id', '')
                if person_id and person_id not in unique_characters:
                    unique_characters[person_id] = row
    except FileNotFoundError:
        print(f"❌ Error: {removed_file} not found")
        return
    
    # Find characters that would be restored
    restoration_candidates = {
        'must_restore': [],
        'high_priority': [],
        'medium_priority': [],
        'false_positives': []
    }
    
    for char_id, char_data in unique_characters.items():
        names = [
            char_data.get('person_name', '').lower(),
            char_data.get('person_name_ja', '').lower(),
            char_data.get('person_name_display', '').lower()
        ]
        
        removal_reason = char_data.get('removal_reason', '').lower()
        occupation = char_data.get('occupation', '').lower()
        
        # Check for false positives (real people)
        if 'name pattern match' in removal_reason:
            real_occupations = ['ミュージシャン', '歌手', '女優', '俳優', '首相', 'ボクサー', 'プロ野球選手']
            if any(real_occ in char_data.get('occupation', '') for real_occ in real_occupations):
                restoration_candidates['false_positives'].append(char_data)
                continue
        
        # Check for must-restore characters
        is_must_restore = False
        for keyword in must_restore_keywords:
            if any(keyword in name for name in names if name):
                restoration_candidates['must_restore'].append(char_data)
                is_must_restore = True
                break
        
        if is_must_restore:
            continue
            
        # Check for high-priority characters
        high_priority_keywords = [
            'eren', 'mikasa', 'armin', 'levi',  # Attack on Titan
            'tanjiro', 'nezuko', 'zenitsu',    # Demon Slayer
            'edward', 'alphonse',               # Fullmetal Alchemist
            'shinji', 'rei', 'asuka',          # Evangelion
            'ichigo', 'rukia',                 # Bleach
            'saber', 'gilgamesh',              # Fate series
            'kenshin', 'sagara'                # Rurouni Kenshin
        ]
        
        is_high_priority = False
        for keyword in high_priority_keywords:
            if any(keyword in name for name in names if name):
                restoration_candidates['high_priority'].append(char_data)
                is_high_priority = True
                break
        
        if is_high_priority:
            continue
            
        # Check for medium-priority characters
        medium_keywords = [
            'anya', 'loid', 'yor',             # Spy x Family
            'yuji', 'megumi', 'nobara',        # Jujutsu Kaisen
            'denji', 'makima', 'power',        # Chainsaw Man
            'rimuru', 'veldora',               # That Time I Got Reincarnated
            'ainz', 'albedo'                   # Overlord
        ]
        
        for keyword in medium_keywords:
            if any(keyword in name for name in names if name):
                restoration_candidates['medium_priority'].append(char_data)
                break
    
    # Display results
    print("🚨 MUST-RESTORE CULTURAL ICONS:")
    print(f"   Total: {len(restoration_candidates['must_restore'])} characters")
    print()
    
    for char in sorted(restoration_candidates['must_restore'], 
                      key=lambda x: x.get('person_name_display', '')):
        name = char.get('person_name_display') or char.get('person_name', 'Unknown')
        japanese = char.get('person_name_ja', '')
        occupation = char.get('occupation', '')
        print(f"   ✅ {name}")
        if japanese and japanese != name:
            print(f"      📝 Japanese: {japanese}")
        if occupation:
            print(f"      💼 Role: {occupation}")
        print()
    
    print("🔴 HIGH-PRIORITY RESTORATIONS:")
    print(f"   Total: {len(restoration_candidates['high_priority'])} characters")
    print()
    
    for char in sorted(restoration_candidates['high_priority'][:10], 
                      key=lambda x: x.get('person_name_display', '')):
        name = char.get('person_name_display') or char.get('person_name', 'Unknown')
        japanese = char.get('person_name_ja', '')
        print(f"   🔸 {name} ({japanese})")
    
    if len(restoration_candidates['high_priority']) > 10:
        print(f"   ... and {len(restoration_candidates['high_priority']) - 10} more")
    print()
    
    print("🟡 MEDIUM-PRIORITY RESTORATIONS:")
    print(f"   Total: {len(restoration_candidates['medium_priority'])} characters")
    
    for char in sorted(restoration_candidates['medium_priority'][:5], 
                      key=lambda x: x.get('person_name_display', '')):
        name = char.get('person_name_display') or char.get('person_name', 'Unknown')
        print(f"   🔹 {name}")
    
    if len(restoration_candidates['medium_priority']) > 5:
        print(f"   ... and {len(restoration_candidates['medium_priority']) - 5} more")
    print()
    
    print("⚠️  FALSE POSITIVES (Real People to Restore):")
    print(f"   Total: {len(restoration_candidates['false_positives'])} people")
    print()
    
    for person in restoration_candidates['false_positives']:
        name = person.get('person_name_display') or person.get('person_name', 'Unknown')
        occupation = person.get('occupation', '')
        reason = person.get('removal_reason', '')[:50] + "..."
        print(f"   🚫 {name} ({occupation})")
        print(f"      📄 Reason: {reason}")
        print()
    
    # Summary
    total_restore = (len(restoration_candidates['must_restore']) + 
                    len(restoration_candidates['high_priority']) + 
                    len(restoration_candidates['medium_priority']))
    
    print("📊 RESTORATION SUMMARY:")
    print("=" * 40)
    print(f"Must-Restore Icons:     {len(restoration_candidates['must_restore']):2d}")
    print(f"High-Priority:          {len(restoration_candidates['high_priority']):2d}")  
    print(f"Medium-Priority:        {len(restoration_candidates['medium_priority']):2d}")
    print(f"False Positives:        {len(restoration_candidates['false_positives']):2d}")
    print("-" * 40)
    print(f"Total Characters:       {total_restore:2d}")
    print(f"Total Real People:      {len(restoration_candidates['false_positives']):2d}")
    print("-" * 40)
    print(f"GRAND TOTAL RESTORE:    {total_restore + len(restoration_candidates['false_positives']):2d}")
    print()
    
    # Show impact
    original_total = len(unique_characters)
    restore_percentage = (total_restore + len(restoration_candidates['false_positives'])) / original_total * 100
    
    print("📈 IMPACT ANALYSIS:")
    print(f"   Original Removed:     {original_total} characters")
    print(f"   Will Restore:         {total_restore + len(restoration_candidates['false_positives'])} characters")
    print(f"   Restoration Rate:     {restore_percentage:.1f}%")
    print(f"   Keep Removed:         {original_total - total_restore - len(restoration_candidates['false_positives'])} characters")
    print()
    
    print("🎯 NEXT STEPS:")
    print("1. Run: python3 wikipedia_fictional_character_verifier.py")
    print("2. Review the verification results")
    print("3. Run: python3 cultural_character_restorer.py")
    print("4. Confirm restoration when prompted")
    print()
    print("✅ System is ready for execution!")

if __name__ == "__main__":
    preview_restoration()