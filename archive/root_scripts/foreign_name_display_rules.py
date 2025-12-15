#!/usr/bin/env python3
"""
Foreign Name Display Rules System
外国語表記ルールシステム

Implements cultural context rules for determining proper display names
based on nationality, occupation, and industry standards.
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class DisplayNameType(Enum):
    """Types of display name formats"""
    ORIGINAL_ALPHABET = "original_alphabet"  # PSY, BTS
    KATAKANA = "katakana"  # マイケル・ジャクソン
    JAPANESE = "japanese"  # 日本語表記
    MIXED_PARENTHESES = "mixed_parentheses"  # Jin (BTS)
    ESTABLISHED_STAGE = "established_stage"  # hyde, GACKT

@dataclass
class DisplayNameRule:
    """Display name rule definition"""
    rule_id: str
    priority: int
    nationality_pattern: str
    occupation_pattern: str
    display_type: DisplayNameType
    description: str
    examples: List[str]

class ForeignNameDisplayRules:
    """Foreign name display rules engine"""

    def __init__(self):
        """Initialize display rules system"""
        self.rules = self.load_rules()
        self.korean_agencies = self.load_korean_agencies()
        self.established_names = self.load_established_names()
        self.katakana_dictionary = self.load_katakana_dictionary()

    def load_rules(self) -> List[DisplayNameRule]:
        """Load display name rules"""
        return [
            # Priority 1: K-pop/Korean Entertainment
            DisplayNameRule(
                rule_id="kpop_alphabet",
                priority=1,
                nationality_pattern="韓国",
                occupation_pattern="歌手|アイドル|K-POP|ラッパー",
                display_type=DisplayNameType.ORIGINAL_ALPHABET,
                description="K-pop artists use original alphabet names",
                examples=["PSY", "BTS", "BLACKPINK", "TWICE"]
            ),

            # Priority 2: Japanese with established English stage names
            DisplayNameRule(
                rule_id="japanese_established_english",
                priority=2,
                nationality_pattern="日本",
                occupation_pattern="ミュージシャン|歌手|アーティスト",
                display_type=DisplayNameType.ESTABLISHED_STAGE,
                description="Japanese artists with established English stage names",
                examples=["hyde", "YOSHIKI", "GACKT", "Ado"]
            ),

            # Priority 3: Japanese default
            DisplayNameRule(
                rule_id="japanese_default",
                priority=3,
                nationality_pattern="日本",
                occupation_pattern=".*",
                display_type=DisplayNameType.JAPANESE,
                description="Japanese people use Japanese display names",
                examples=["ヒカキン", "あいみょん", "米津玄師"]
            ),

            # Priority 4: Western artists
            DisplayNameRule(
                rule_id="western_katakana",
                priority=4,
                nationality_pattern="アメリカ|イギリス|カナダ|フランス|ドイツ|イタリア|スペイン",
                occupation_pattern=".*",
                display_type=DisplayNameType.KATAKANA,
                description="Western artists use established katakana",
                examples=["マイケル・ジャクソン", "マドンナ", "レディー・ガガ"]
            ),

            # Priority 5: Chinese/Taiwanese
            DisplayNameRule(
                rule_id="chinese_original",
                priority=5,
                nationality_pattern="中国|台湾|香港",
                occupation_pattern=".*",
                display_type=DisplayNameType.ORIGINAL_ALPHABET,
                description="Chinese names in original form or romanization",
                examples=["Jay Chou", "Jackie Chan", "Teresa Teng"]
            )
        ]

    def load_korean_agencies(self) -> List[str]:
        """Load list of Korean entertainment agencies"""
        return [
            "YG Entertainment", "YG", "YGエンターテインメント",
            "SM Entertainment", "SM", "SMエンターテインメント",
            "JYP Entertainment", "JYP", "JYPエンターテインメント",
            "HYBE", "BigHit", "Big Hit Entertainment",
            "Pledis", "Pledis Entertainment",
            "Starship", "Starship Entertainment",
            "Cube", "Cube Entertainment",
            "FNC", "FNC Entertainment",
            "Woollim", "Woollim Entertainment"
        ]

    def load_established_names(self) -> Dict[str, str]:
        """Load established stage names that should be preserved"""
        return {
            # Japanese artists with English stage names
            "hyde": "hyde",
            "HYDE": "hyde",  # Normalize
            "YOSHIKI": "YOSHIKI",
            "GACKT": "GACKT",
            "Gackt": "GACKT",  # Normalize
            "Ado": "Ado",
            "DAIGO": "DAIGO",
            "DJ LOVE": "DJ LOVE",
            "Eve": "Eve",
            "Fukase": "Fukase",
            "HIKAKIN": "ヒカキン",  # Should be Japanese
            "SEIKIN": "セイキン",  # Should be Japanese

            # K-pop stage names
            "RM": "RM",
            "Rap Monster": "RM",  # Old name
            "Jin": "Jin",
            "Suga": "Suga",
            "J-Hope": "J-Hope",
            "Jimin": "Jimin",
            "V": "V",
            "Jungkook": "Jungkook",
            "Jung Kook": "Jungkook",  # Alternative spelling

            # BLACKPINK
            "Jennie": "Jennie",
            "Lisa": "Lisa",
            "Rosé": "Rosé",
            "Rose": "Rosé",  # Without accent
            "Jisoo": "Jisoo",

            # Other K-pop
            "G-Dragon": "G-Dragon",
            "G-DRAGON": "G-Dragon",  # Normalize
            "GD": "G-Dragon",
            "IU": "IU",
            "アイユー": "IU"  # Convert katakana
        }

    def load_katakana_dictionary(self) -> Dict[str, str]:
        """Load katakana conversion dictionary for Western names"""
        return {
            # Common Western artists
            "Michael Jackson": "マイケル・ジャクソン",
            "Madonna": "マドンナ",
            "Lady Gaga": "レディー・ガガ",
            "Beyonce": "ビヨンセ",
            "Beyoncé": "ビヨンセ",
            "Taylor Swift": "テイラー・スウィフト",
            "Ed Sheeran": "エド・シーラン",
            "Bruno Mars": "ブルーノ・マーズ",
            "Ariana Grande": "アリアナ・グランデ",
            "Justin Bieber": "ジャスティン・ビーバー",
            "Billie Eilish": "ビリー・アイリッシュ",
            "Adele": "アデル",
            "Eminem": "エミネム",
            "Drake": "ドレイク",
            "Kanye West": "カニエ・ウェスト",
            "Rihanna": "リアーナ",
            "Mariah Carey": "マライア・キャリー",
            "Whitney Houston": "ホイットニー・ヒューストン",
            "Celine Dion": "セリーヌ・ディオン",
            "Elton John": "エルトン・ジョン",
            "Paul McCartney": "ポール・マッカートニー",
            "John Lennon": "ジョン・レノン"
        }

    def determine_display_type(self, person_data: Dict) -> Tuple[DisplayNameType, str]:
        """
        Determine the appropriate display type for a person

        Returns:
            Tuple of (DisplayNameType, reasoning)
        """
        nationality = person_data.get('nationality', '')
        occupation = str(person_data.get('occupation', ''))
        current_display = person_data.get('person_name_display', '')
        person_name = person_data.get('person_name', '')
        agency = person_data.get('agency', '')

        # Check established names first
        if current_display in self.established_names:
            return (DisplayNameType.ESTABLISHED_STAGE,
                   f"Established stage name: {self.established_names[current_display]}")

        if person_name in self.established_names:
            return (DisplayNameType.ESTABLISHED_STAGE,
                   f"Established stage name: {self.established_names[person_name]}")

        # Check Korean entertainment context
        if self.is_korean_entertainment(person_data):
            return (DisplayNameType.ORIGINAL_ALPHABET,
                   "K-pop/Korean entertainment uses original alphabet names")

        # Apply rules by priority
        for rule in sorted(self.rules, key=lambda r: r.priority):
            if self.matches_rule(person_data, rule):
                return (rule.display_type, rule.description)

        # Default: keep current
        return (DisplayNameType.ORIGINAL_ALPHABET if self.is_alphabet(current_display) else DisplayNameType.KATAKANA,
               "No specific rule matched, keeping current format")

    def is_korean_entertainment(self, person_data: Dict) -> bool:
        """Check if person is in Korean entertainment industry"""
        nationality = person_data.get('nationality', '')
        occupation = str(person_data.get('occupation', ''))
        agency = str(person_data.get('agency', ''))
        group = str(person_data.get('group', ''))

        # Check nationality and occupation
        if nationality == '韓国':
            if any(term in occupation for term in ['歌手', 'アイドル', 'K-POP', 'ラッパー', '俳優', '女優']):
                return True

        # Check agency
        if any(k_agency in agency for k_agency in self.korean_agencies):
            return True

        # Check known K-pop groups
        kpop_groups = ['BTS', '防弾少年団', 'BLACKPINK', 'TWICE', 'SEVENTEEN',
                      'Stray Kids', 'ENHYPEN', 'TXT', 'ATEEZ', 'NCT']
        if any(k_group in group for k_group in kpop_groups):
            return True

        return False

    def matches_rule(self, person_data: Dict, rule: DisplayNameRule) -> bool:
        """Check if person data matches a rule"""
        nationality = person_data.get('nationality', '')
        occupation = str(person_data.get('occupation', ''))

        # Check nationality pattern
        if not re.search(rule.nationality_pattern, nationality):
            return False

        # Check occupation pattern
        if not re.search(rule.occupation_pattern, occupation):
            return False

        return True

    def is_alphabet(self, text: str) -> bool:
        """Check if text is primarily alphabet characters"""
        if not text:
            return False
        # Remove spaces, hyphens, parentheses
        cleaned = re.sub(r'[\s\-\(\)（）]', '', text)
        # Check if >50% is ASCII alphabet
        alphabet_chars = sum(1 for c in cleaned if c.isascii() and c.isalpha())
        return alphabet_chars > len(cleaned) * 0.5

    def apply_display_rules(self, person_data: Dict) -> Dict:
        """
        Apply display rules to determine correct display name

        Returns:
            Dictionary with corrected display name and metadata
        """
        current_display = person_data.get('person_name_display', '')
        person_name = person_data.get('person_name', '')
        person_name_ja = person_data.get('person_name_ja', '')

        display_type, reasoning = self.determine_display_type(person_data)

        # Determine corrected display based on type
        corrected_display = current_display  # Default: no change

        if display_type == DisplayNameType.ORIGINAL_ALPHABET:
            # Should use alphabet - check if currently katakana
            if re.search(r'[ァ-ヶー]', current_display):
                # Try to find alphabet version
                if person_name and self.is_alphabet(person_name):
                    corrected_display = person_name
                elif current_display in self.established_names:
                    corrected_display = self.established_names[current_display]
                else:
                    # Check reverse katakana dictionary
                    for eng, kat in self.katakana_dictionary.items():
                        if kat == current_display:
                            corrected_display = eng
                            break

        elif display_type == DisplayNameType.KATAKANA:
            # Should use katakana - check if currently alphabet
            if self.is_alphabet(current_display):
                # Try katakana dictionary
                if current_display in self.katakana_dictionary:
                    corrected_display = self.katakana_dictionary[current_display]
                elif person_name_ja and re.search(r'[ァ-ヶー]', person_name_ja):
                    corrected_display = person_name_ja

        elif display_type == DisplayNameType.JAPANESE:
            # Should use Japanese - prefer person_name_ja
            if person_name_ja:
                corrected_display = person_name_ja
            elif not self.is_alphabet(current_display):
                corrected_display = current_display

        elif display_type == DisplayNameType.ESTABLISHED_STAGE:
            # Use established stage name
            if current_display in self.established_names:
                corrected_display = self.established_names[current_display]
            elif person_name in self.established_names:
                corrected_display = self.established_names[person_name]

        # Clean up formatting
        corrected_display = self.normalize_display_name(corrected_display)

        return {
            'person_id': person_data.get('person_id'),
            'original_display': current_display,
            'corrected_display': corrected_display,
            'display_type': display_type.value,
            'reasoning': reasoning,
            'changed': current_display != corrected_display,
            'confidence': self.calculate_confidence(person_data, display_type)
        }

    def normalize_display_name(self, name: str) -> str:
        """Normalize display name formatting"""
        if not name:
            return name

        # Trim whitespace
        name = name.strip()

        # Normalize parentheses
        name = name.replace('（', ' (').replace('）', ')')
        name = re.sub(r'\s+\(', ' (', name)
        name = re.sub(r'^\s+', '', name)

        # Normalize spaces
        name = re.sub(r'\s+', ' ', name)

        return name

    def calculate_confidence(self, person_data: Dict, display_type: DisplayNameType) -> float:
        """Calculate confidence score for the correction"""
        confidence = 0.5  # Base confidence

        # Higher confidence for established names
        if display_type == DisplayNameType.ESTABLISHED_STAGE:
            confidence = 0.95

        # Higher confidence for Korean entertainment
        elif self.is_korean_entertainment(person_data):
            confidence = 0.9

        # Medium-high confidence for clear nationality matches
        elif person_data.get('nationality') in ['日本', '韓国', 'アメリカ', 'イギリス']:
            confidence = 0.85

        # Lower confidence for edge cases
        else:
            confidence = 0.7

        return confidence

    def batch_apply_rules(self, persons: List[Dict]) -> List[Dict]:
        """Apply rules to multiple persons"""
        results = []

        for person in persons:
            result = self.apply_display_rules(person)
            results.append(result)

        return results

    def generate_rules_report(self, results: List[Dict]) -> Dict:
        """Generate summary report of rule applications"""
        total = len(results)
        changed = sum(1 for r in results if r['changed'])

        by_type = {}
        for result in results:
            dtype = result.get('display_type', 'unknown')
            by_type[dtype] = by_type.get(dtype, 0) + 1

        confidence_buckets = {
            'high': sum(1 for r in results if r.get('confidence', 0) >= 0.9),
            'medium': sum(1 for r in results if 0.7 <= r.get('confidence', 0) < 0.9),
            'low': sum(1 for r in results if r.get('confidence', 0) < 0.7)
        }

        return {
            'total_processed': total,
            'changes_needed': changed,
            'change_percentage': (changed / total * 100) if total > 0 else 0,
            'by_display_type': by_type,
            'confidence_distribution': confidence_buckets
        }


def main():
    """Test the display rules system"""
    rules = ForeignNameDisplayRules()

    # Test cases
    test_cases = [
        {
            'person_id': 'P000022',
            'person_name': 'PSY',
            'person_name_display': 'サイ',
            'person_name_ja': 'サイ',
            'nationality': '韓国',
            'occupation': '歌手'
        },
        {
            'person_id': 'P000013',
            'person_name': 'HIKAKIN',
            'person_name_display': 'HIKAKIN',
            'person_name_ja': 'ヒカキン',
            'nationality': '日本',
            'occupation': 'YouTuber'
        },
        {
            'person_id': 'P000100',
            'person_name': 'Michael Jackson',
            'person_name_display': 'Michael Jackson',
            'person_name_ja': 'マイケル・ジャクソン',
            'nationality': 'アメリカ',
            'occupation': '歌手'
        }
    ]

    print("Testing Foreign Name Display Rules\n" + "="*50)

    for test in test_cases:
        result = rules.apply_display_rules(test)

        print(f"\nPerson: {test['person_name']} ({test['nationality']})")
        print(f"Current: {result['original_display']}")
        print(f"Corrected: {result['corrected_display']}")
        print(f"Type: {result['display_type']}")
        print(f"Changed: {result['changed']}")
        print(f"Confidence: {result['confidence']:.2f}")
        print(f"Reasoning: {result['reasoning']}")


if __name__ == "__main__":
    main()
