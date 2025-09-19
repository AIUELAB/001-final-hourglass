#!/usr/bin/env python3
"""
Final Deduplication Pass - Remove ALL remaining duplicates
最終重複除去パス
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json

def final_deduplication(csv_file: str):
    """Remove all remaining duplicate person_ids"""
    print(f"Loading {csv_file}...")
    df = pd.read_csv(csv_file, encoding='utf-8')
    original_count = len(df)
    
    print(f"Original records: {original_count:,}")
    print(f"Unique person_ids: {df['person_id'].nunique():,}")
    
    # Find all duplicate person_ids
    person_id_counts = df['person_id'].value_counts()
    duplicate_person_ids = person_id_counts[person_id_counts > 1]
    
    print(f"\nFound {len(duplicate_person_ids)} person_ids with duplicates")
    
    if len(duplicate_person_ids) == 0:
        print("✅ No duplicates found!")
        return df
    
    # Process each duplicate
    rows_to_keep = []
    processed_person_ids = set()
    removed_count = 0
    
    for person_id, count in duplicate_person_ids.items():
        if person_id in processed_person_ids:
            continue
            
        # Get all records for this person_id
        duplicate_records = df[df['person_id'] == person_id]
        
        # Calculate quality scores
        best_idx = None
        best_score = -1
        
        for idx, record in duplicate_records.iterrows():
            score = 0
            # Quality scoring
            score += record.get('accuracy_score', 0)
            score += record.get('name_recognition', 0) 
            score += record.get('impact_score', 0)
            
            # Bonus for field completeness
            for field in ['nationality', 'occupation', 'person_name_ja', 'category', 'episode_text']:
                if pd.notna(record.get(field)) and str(record.get(field)).strip():
                    score += 10
            
            if score > best_score:
                best_score = score
                best_idx = idx
        
        # Keep only the best record
        rows_to_keep.append(best_idx)
        processed_person_ids.add(person_id)
        removed_count += (count - 1)
    
    # Also keep all non-duplicate records
    non_duplicate_person_ids = df[~df['person_id'].isin(duplicate_person_ids.index)]['person_id'].unique()
    for person_id in non_duplicate_person_ids:
        record_idx = df[df['person_id'] == person_id].index[0]
        rows_to_keep.append(record_idx)
    
    # Create final dataframe
    df_final = df.loc[rows_to_keep].copy()
    df_final = df_final.sort_values('person_id').reset_index(drop=True)
    
    final_count = len(df_final)
    print(f"\n📊 Final Results:")
    print(f"   Records before: {original_count:,}")
    print(f"   Records after: {final_count:,}")
    print(f"   Removed: {original_count - final_count:,} ({((original_count - final_count) / original_count * 100):.1f}%)")
    print(f"   Unique person_ids: {df_final['person_id'].nunique():,}")
    
    # Verify no duplicates remain
    final_duplicates = df_final['person_id'].value_counts()
    final_duplicates = final_duplicates[final_duplicates > 1]
    
    if len(final_duplicates) == 0:
        print("✅ SUCCESS: All duplicates removed!")
    else:
        print(f"⚠️ WARNING: {len(final_duplicates)} duplicates still remain")
    
    return df_final


def main():
    # Process the deduplicated file
    input_file = 'ultra_think_DEDUPLICATED_20250831_175609.csv'
    
    # Run final deduplication
    df_final = final_deduplication(input_file)
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'ultra_think_FINAL_CLEAN_{timestamp}.csv'
    df_final.to_csv(output_file, index=False, encoding='utf-8')
    
    print(f"\n✅ Final clean database saved to: {output_file}")
    print(f"   Ready for Google Sheets sync!")
    
    # Save statistics
    stats = {
        'timestamp': timestamp,
        'input_file': input_file,
        'output_file': output_file,
        'final_records': len(df_final),
        'unique_person_ids': df_final['person_id'].nunique(),
        'status': 'success'
    }
    
    stats_file = f'final_dedup_stats_{timestamp}.json'
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    print(f"📊 Statistics saved to: {stats_file}")
    
    return output_file


if __name__ == "__main__":
    output = main()