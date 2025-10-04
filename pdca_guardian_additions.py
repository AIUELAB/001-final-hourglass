# PDCAガーディアンへの追加コード

# 1. ViolationType列挙型への追加

    # 未実装ルールのViolationType追加 (v5.5-5.11)
    CHARACTER_COUNT_VIOLATION_STRICT = "文字数制限違反（150-250）"
    SENTENCE_ENDING_VIOLATION = "文末表現違反（動詞・形容詞）"
    FACT_FIRST_PRINCIPLE_VIOLATION = "事実優先原則違反"
    FACT_VERIFICATION_FAILURE = "ファクト検証失敗"
    QUALITY_PRIORITY_VIOLATION = "品質優先原則違反"
    BATCH_INDIVIDUAL_VERIFICATION_FAILURE = "バッチ個別検証失敗"


# 2. チェックメソッドの追加

    # 未実装ルールのチェックメソッド (v5.5-5.11)

    def check_character_count_strict(self, episode_text: str, person_name_display: str) -> List[Dict[str, Any]]:
        """RULE_160: 文字数150-250制限の厳格チェック"""
        violations = []
        text_length = len(episode_text)

        if text_length < 150:
            violations.append({
                'rule_id': 'RULE_160',
                'type': ViolationType.CHARACTER_COUNT_VIOLATION_STRICT.value,
                'message': f'{person_name_display}: エピソードが短すぎます（{text_length}文字 < 150文字）',
                'severity': 'critical'
            })
        elif text_length > 250:
            violations.append({
                'rule_id': 'RULE_160',
                'type': ViolationType.CHARACTER_COUNT_VIOLATION_STRICT.value,
                'message': f'{person_name_display}: エピソードが長すぎます（{text_length}文字 > 250文字）',
                'severity': 'critical'
            })

        return violations


    def check_sentence_ending(self, episode_text: str, person_name_display: str) -> List[Dict[str, Any]]:
        """RULE_165: 動詞・形容詞終了チェック"""
        violations = []

        # 文末パターンの判定
        noun_endings = ['だった', 'であった', 'である', 'です', 'でした']
        verb_adj_endings = ['した', 'った', 'んだ', 'いた', 'れた', 'せた', 'かった', 'い。', 'る。']

        text = episode_text.rstrip('。')
        is_noun_ending = any(text.endswith(ending) for ending in noun_endings)
        is_verb_adj_ending = any(text.endswith(ending.rstrip('。')) for ending in verb_adj_endings)

        if is_noun_ending and not is_verb_adj_ending:
            violations.append({
                'rule_id': 'RULE_165',
                'type': ViolationType.SENTENCE_ENDING_VIOLATION.value,
                'message': f'{person_name_display}: 名詞終わりで味気ない（動詞・形容詞で終わるべき）',
                'severity': 'medium'
            })

        return violations


    def check_fact_first_principle(self, episode_text: str, person_name_display: str) -> List[Dict[str, Any]]:
        """RULE_166: 事実優先原則チェック"""
        violations = []

        # 主観的表現のチェック
        subjective_patterns = [
            '素晴らしい', 'すばらしい', '偉大な', '驚異的な', '感動的な',
            '美しい', '輝かしい', '華麗な', '壮大な', '圧倒的な'
        ]

        subjective_found = [p for p in subjective_patterns if p in episode_text]
        if subjective_found:
            violations.append({
                'rule_id': 'RULE_166',
                'type': ViolationType.FACT_FIRST_PRINCIPLE_VIOLATION.value,
                'message': f'{person_name_display}: 主観的表現「{subjective_found[0]}」が含まれています（事実のみを記述すべき）',
                'severity': 'high'
            })

        return violations


    def check_fact_verification(self, episode_text: str, person_name_display: str, person_data: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """RULE_167: ファクトチェック"""
        violations = []

        # 基本的な事実チェック（年代の矛盾など）
        if person_data:
            birth_year = person_data.get('birth_year')
            if birth_year:
                # 年代が含まれている場合の整合性チェック
                year_pattern = r'(\d{4})年'
                years = re.findall(year_pattern, episode_text)
                for year_str in years:
                    year = int(year_str)
                    age = person_data.get('age', 0)
                    expected_year = birth_year + age
                    if abs(year - expected_year) > 1:  # 1年の誤差を許容
                        violations.append({
                            'rule_id': 'RULE_167',
                            'type': ViolationType.FACT_VERIFICATION_FAILURE.value,
                            'message': f'{person_name_display}: 年代の矛盾（{year}年は{age}歳時と一致しない）',
                            'severity': 'critical'
                        })

        return violations


    def check_quality_priority(self, episode_text: str, person_name_display: str, quality_score: float = 0) -> List[Dict[str, Any]]:
        """RULE_168: 品質優先原則チェック"""
        violations = []

        # 品質スコアが低い場合
        if quality_score < 7.0:
            violations.append({
                'rule_id': 'RULE_168',
                'type': ViolationType.QUALITY_PRIORITY_VIOLATION.value,
                'message': f'{person_name_display}: 品質スコア{quality_score:.1f}が基準値7.0未満',
                'severity': 'high'
            })

        # 具体性チェック
        concrete_indicators = ['数字', '固有名詞', '具体的な場所', '具体的な日付']
        has_concrete = any(
            bool(re.search(r'\d+', episode_text)) if ind == '数字' else
            bool(re.search(r'[A-Z][a-z]+|[ァ-ヴー]{3,}', episode_text)) if ind == '固有名詞' else
            False
            for ind in concrete_indicators
        )

        if not has_concrete:
            violations.append({
                'rule_id': 'RULE_168',
                'type': ViolationType.QUALITY_PRIORITY_VIOLATION.value,
                'message': f'{person_name_display}: 具体的な情報が不足しています',
                'severity': 'medium'
            })

        return violations


    def check_batch_individual_verification(self, episodes: List[str], person_name_display: str) -> List[Dict[str, Any]]:
        """RULE_169: バッチ処理での個別検証"""
        violations = []

        # エピソードの重複チェック
        seen = set()
        for i, episode in enumerate(episodes):
            # 主要な内容を抽出（最初の50文字）
            key = episode[:50] if len(episode) > 50 else episode
            if key in seen:
                violations.append({
                    'rule_id': 'RULE_169',
                    'type': ViolationType.BATCH_INDIVIDUAL_VERIFICATION_FAILURE.value,
                    'message': f'{person_name_display}: エピソード{i+1}が重複している可能性があります',
                    'severity': 'high'
                })
            seen.add(key)

        # バッチ全体の品質チェック
        if len(episodes) < 7:
            violations.append({
                'rule_id': 'RULE_169',
                'type': ViolationType.BATCH_INDIVIDUAL_VERIFICATION_FAILURE.value,
                'message': f'{person_name_display}: エピソード数が不足（{len(episodes)}/7）',
                'severity': 'critical'
            })

        return violations



# 3. check_episode_qualityメソッドへの統合

        # 7. 未実装ルールの統合チェック (RULE_160, 165-168)

        # RULE_160: 文字数制限（150-250）
        violations.extend(self.check_character_count_strict(episode_text, person_name_display))

        # RULE_165: 動詞・形容詞終了
        violations.extend(self.check_sentence_ending(episode_text, person_name_display))

        # RULE_166: 事実優先原則
        violations.extend(self.check_fact_first_principle(episode_text, person_name_display))

        # RULE_167: ファクトチェック
        violations.extend(self.check_fact_verification(episode_text, person_name_display, person_data))

        # RULE_168: 品質優先原則
        quality_score = self._calculate_episode_quality_score(episode_text) if hasattr(self, '_calculate_episode_quality_score') else 0
        violations.extend(self.check_quality_priority(episode_text, person_name_display, quality_score))
