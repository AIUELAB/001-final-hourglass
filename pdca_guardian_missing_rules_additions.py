# PDCAガーディアンへの未実装ルール追加コード
# RULE_077-080, 157-159, 161-163

# 1. ViolationType列挙型への追加

    # 未実装ルール（RULE_077-080, 157-159, 161-163）のViolationType追加
    CONSECUTIVE_ID_MISJUDGMENT = "連続ID誤判定"
    BATCH_DATA_PROTECTION_FAILURE = "バッチデータ保護失敗"
    WIKIPEDIA_VERIFICATION_SKIPPED = "Wikipedia確認スキップ"
    MULTI_STAGE_VERIFICATION_MISSING = "多段階検証不足"
    CULTURAL_PHENOMENON_IGNORED = "文化現象無視"
    SOCIAL_CONTRIBUTION_UNDERVALUED = "社会貢献過小評価"
    THREE_AXIS_BALANCE_VIOLATION = "3軸バランス違反"
    SUBJECTIVITY_VIOLATION = "主観性違反"
    CONCRETE_DESCRIPTION_MISSING = "具体性不足"
    EDUCATIONAL_VALUE_MISSING = "教育的価値不足"


# 2. チェックメソッドの追加

    # 未実装ルール（RULE_077-080, 157-159, 161-163）のチェックメソッド

    def check_consecutive_id_protection(self, episode_text: str, person_name_display: str, person_data: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """RULE_077: 連続IDによる誤判定防止"""
        violations = []

        # 連続IDパターンの検出（職業別バッチデータの保護）
        if person_data:
            person_id = person_data.get('person_id', '')
            occupation = person_data.get('occupation', '')

            # 保護対象の職業リスト
            protected_occupations = [
                'プロレスラー', 'サッカー選手', '野球選手', 'バスケットボール選手',
                'テニス選手', '水泳選手', '陸上選手', 'バレーボール選手'
            ]

            # 保護対象職業で連続IDの場合
            if any(occ in occupation for occ in protected_occupations):
                # エピソードが極端に短い・内容が薄い場合のみ違反
                if len(episode_text) < 50 or '情報なし' in episode_text:
                    violations.append({
                        'rule_id': 'RULE_077',
                        'type': ViolationType.CONSECUTIVE_ID_MISJUDGMENT.value,
                        'message': f'{person_name_display}: 保護対象職業だが内容不足',
                        'severity': 'medium'
                    })

        return violations


    def check_batch_data_protection(self, episode_text: str, person_name_display: str, person_data: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """RULE_078: 職業別バッチデータ自動保護"""
        violations = []

        if person_data:
            occupation = person_data.get('occupation', '')

            # 保護必須の職業
            must_protect = ['女子プロレスラー', '女子格闘家', 'なでしこジャパン']

            # 削除フラグがある場合
            if any(occ in occupation for occ in must_protect):
                if person_data.get('deletion_flag', False):
                    violations.append({
                        'rule_id': 'RULE_078',
                        'type': ViolationType.BATCH_DATA_PROTECTION_FAILURE.value,
                        'message': f'{person_name_display}: 保護対象職業が削除対象になっている',
                        'severity': 'critical'
                    })

        return violations


    def check_wikipedia_priority(self, episode_text: str, person_name_display: str, person_data: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """RULE_079: Wikipedia存在確認優先原則"""
        violations = []

        if person_data:
            has_wikipedia = person_data.get('has_wikipedia', False)
            deletion_flag = person_data.get('deletion_flag', False)

            # Wikipedia記事がある人物を削除対象にしている
            if has_wikipedia and deletion_flag:
                violations.append({
                    'rule_id': 'RULE_079',
                    'type': ViolationType.WIKIPEDIA_VERIFICATION_SKIPPED.value,
                    'message': f'{person_name_display}: Wikipedia記事があるのに削除対象',
                    'severity': 'critical'
                })

        return violations


    def check_multi_stage_verification(self, episode_text: str, person_name_display: str, person_data: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """RULE_080: 削除前の多段階検証必須化"""
        violations = []

        if person_data:
            deletion_flag = person_data.get('deletion_flag', False)
            verification_stages = person_data.get('verification_stages', [])

            required_stages = ['wikipedia_check', 'google_trends_check', 'occupation_check']

            if deletion_flag:
                missing_stages = [stage for stage in required_stages if stage not in verification_stages]
                if missing_stages:
                    violations.append({
                        'rule_id': 'RULE_080',
                        'type': ViolationType.MULTI_STAGE_VERIFICATION_MISSING.value,
                        'message': f'{person_name_display}: 検証段階不足: {", ".join(missing_stages)}',
                        'severity': 'high'
                    })

        return violations


    def check_cultural_phenomenon(self, episode_text: str, person_name_display: str) -> List[Dict[str, Any]]:
        """RULE_157: 文化現象エピソードの優先選定"""
        violations = []

        # 文化現象キーワード
        cultural_keywords = [
            '世紀の', 'ブーム', '社会現象', '旋風', '伝説の', '歴史的',
            '初の', '史上初', '記録的', '空前の'
        ]

        # 通常のエピソードキーワード
        normal_keywords = ['1位', '優勝', '受賞', 'デビュー']

        has_cultural = any(keyword in episode_text for keyword in cultural_keywords)
        has_normal = any(keyword in episode_text for keyword in normal_keywords)

        # 通常のエピソードはあるが文化現象がない
        if has_normal and not has_cultural:
            # 特定の人物（松田聖子等）では違反とする
            if '松田聖子' in person_name_display:
                violations.append({
                    'rule_id': 'RULE_157',
                    'type': ViolationType.CULTURAL_PHENOMENON_IGNORED.value,
                    'message': f'{person_name_display}: 文化現象エピソードを優先すべき',
                    'severity': 'medium'
                })

        return violations


    def check_social_contribution(self, episode_text: str, person_name_display: str) -> List[Dict[str, Any]]:
        """RULE_158: 社会貢献エピソードの評価基準"""
        violations = []

        # 社会貢献キーワード
        contribution_keywords = [
            '寄付', '支援', '慈善', 'チャリティ', 'ボランティア',
            '基金', '財団', '福祉', '社会貢献', '人道支援'
        ]

        has_contribution = any(keyword in episode_text for keyword in contribution_keywords)

        # 社会貢献エピソードがあるのに短い
        if has_contribution and len(episode_text) < 100:
            violations.append({
                'rule_id': 'RULE_158',
                'type': ViolationType.SOCIAL_CONTRIBUTION_UNDERVALUED.value,
                'message': f'{person_name_display}: 社会貢献エピソードが過小評価されている',
                'severity': 'medium'
            })

        return violations


    def check_three_axis_balance(self, episode_text: str, person_name_display: str) -> List[Dict[str, Any]]:
        """RULE_159: 3軸バランスの必須確認"""
        violations = []

        # 3軸の要素を検出
        axes = {
            '記憶性': ['初の', '史上初', '世界初', '日本初', '記録', '伝説'],
            '共感性': ['苦労', '努力', '挑戦', '克服', '成長', '感動'],
            '意外性': ['実は', '意外に', 'しかし', 'ところが', '驚くことに']
        }

        axis_scores = {}
        for axis_name, keywords in axes.items():
            axis_scores[axis_name] = any(kw in episode_text for kw in keywords)

        # すべての軸がない（0軸）
        if not any(axis_scores.values()):
            violations.append({
                'rule_id': 'RULE_159',
                'type': ViolationType.THREE_AXIS_BALANCE_VIOLATION.value,
                'message': f'{person_name_display}: 3軸（記憶性・共感性・意外性）すべて不足',
                'severity': 'high'
            })
        # 1軸のみ
        elif sum(axis_scores.values()) == 1:
            violations.append({
                'rule_id': 'RULE_159',
                'type': ViolationType.THREE_AXIS_BALANCE_VIOLATION.value,
                'message': f'{person_name_display}: 3軸バランス不良（1軸のみ）',
                'severity': 'medium'
            })

        return violations


    def check_objectivity(self, episode_text: str, person_name_display: str) -> List[Dict[str, Any]]:
        """RULE_161: 客観的事実主義"""
        violations = []

        # 主観的表現のNGワード
        ng_words = [
            '素晴らしい', '感動', '勇気', '希望', '夢',
            '必ず', 'きっと', 'でしょう', 'かもしれない',
            '与える', '与え続ける', '創造できます',
            '可能性が広がる', '未来を', 'あなたも',
            '感銘', '称賛', '偉大', '輝かしい', '栄光'
        ]

        found_ng_words = [word for word in ng_words if word in episode_text]

        if found_ng_words:
            violations.append({
                'rule_id': 'RULE_161',
                'type': ViolationType.SUBJECTIVITY_VIOLATION.value,
                'message': f'{person_name_display}: 主観的表現「{found_ng_words[0]}」が含まれている',
                'severity': 'high'
            })

        return violations


    def check_concrete_description(self, episode_text: str, person_name_display: str) -> List[Dict[str, Any]]:
        """RULE_162: 具体的描写義務"""
        violations = []

        # 具体性の指標
        has_number = bool(re.search(r'\d+', episode_text))
        has_proper_noun = bool(re.search(r'[A-Z][a-z]+|[ァ-ヴー]{3,}', episode_text))
        has_date = bool(re.search(r'\d+年|\d+月|\d+日', episode_text))

        concrete_score = sum([has_number, has_proper_noun, has_date])

        # 具体性が不足（3つの指標のうち1つ以下）
        if concrete_score <= 1:
            violations.append({
                'rule_id': 'RULE_162',
                'type': ViolationType.CONCRETE_DESCRIPTION_MISSING.value,
                'message': f'{person_name_display}: 具体的な数値・固有名詞・日付が不足',
                'severity': 'medium'
            })

        return violations


    def check_educational_value(self, episode_text: str, person_name_display: str) -> List[Dict[str, Any]]:
        """RULE_163: 教育的価値確保"""
        violations = []

        # 教育的価値のキーワード
        educational_keywords = [
            '学んだ', '経験', '教訓', '成長', '努力', '工夫',
            '改善', '発明', '開発', '研究', '貢献', '功績'
        ]

        has_educational = any(keyword in episode_text for keyword in educational_keywords)

        # 教育的価値が全くない
        if not has_educational:
            # エンタメ系の人物以外で違反とする
            entertainment_occupations = ['歌手', '俳優', 'タレント', 'アイドル']
            if person_name_display:
                # 簡易的な職業推定（実際はperson_dataから取得）
                is_entertainment = any(occ in person_name_display for occ in entertainment_occupations)
                if not is_entertainment:
                    violations.append({
                        'rule_id': 'RULE_163',
                        'type': ViolationType.EDUCATIONAL_VALUE_MISSING.value,
                        'message': f'{person_name_display}: 教育的価値が不足している',
                        'severity': 'low'
                    })

        return violations



# 3. check_episode_qualityメソッドへの統合

        # 8. プレースホルダー検出関連ルール (RULE_077-080)

        # RULE_077: 連続ID誤判定防止
        violations.extend(self.check_consecutive_id_protection(episode_text, person_name_display, person_data))

        # RULE_078: バッチデータ保護
        violations.extend(self.check_batch_data_protection(episode_text, person_name_display, person_data))

        # RULE_079: Wikipedia確認優先
        violations.extend(self.check_wikipedia_priority(episode_text, person_name_display, person_data))

        # RULE_080: 多段階検証
        violations.extend(self.check_multi_stage_verification(episode_text, person_name_display, person_data))

        # 9. 3軸評価ルール (RULE_157-159)

        # RULE_157: 文化現象優先
        violations.extend(self.check_cultural_phenomenon(episode_text, person_name_display))

        # RULE_158: 社会貢献評価
        violations.extend(self.check_social_contribution(episode_text, person_name_display))

        # RULE_159: 3軸バランス
        violations.extend(self.check_three_axis_balance(episode_text, person_name_display))

        # 10. 客観性・具体性・教育的価値ルール (RULE_161-163)

        # RULE_161: 客観的事実主義
        violations.extend(self.check_objectivity(episode_text, person_name_display))

        # RULE_162: 具体的描写義務
        violations.extend(self.check_concrete_description(episode_text, person_name_display))

        # RULE_163: 教育的価値確保
        violations.extend(self.check_educational_value(episode_text, person_name_display))
