#!/usr/bin/env python3
"""
生涯ハイライト選定システム
人物の生涯で最も重要な7つの瞬間を選定する
年齢カテゴリは表示形式のみで、選定基準ではない
"""

import re
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import json

@dataclass
class LifeEvent:
    """生涯の出来事"""
    actual_age: int
    event_text: str
    impact_score: float
    global_significance: float  # 世界的重要度
    historical_value: float     # 歴史的価値
    social_influence: float     # 社会的影響力
    career_importance: float    # キャリアにおける重要性
    event_type: str             # achievement/milestone/turning_point/legacy
    keywords: List[str]

    @property
    def total_importance(self) -> float:
        """総合重要度スコア"""
        return (
            self.impact_score * 0.3 +
            self.global_significance * 0.3 +
            self.historical_value * 0.2 +
            self.social_influence * 0.1 +
            self.career_importance * 0.1
        )


class LifetimeHighlightSelector:
    """生涯ハイライト選定システム"""

    def __init__(self):
        """初期化"""
        # 表示用の年齢スロット（これは固定）
        self.display_slots = [1, 10, 20, 30, 40, 50, 60]

        # グローバルインパクト評価基準
        self.global_impact_indicators = {
            'world_records': ['世界記録', '世界初', '世界一', 'ワールド', 'グローバル', '国際'],
            'major_awards': ['MVP', 'ノーベル', 'アカデミー', 'グランプリ', '最優秀', '殿堂'],
            'historical_first': ['史上初', '史上最', '前人未到', '歴史的', '革命的', '画期的'],
            'international_recognition': ['世界的', '国際的', 'メジャー', 'ワールドカップ', 'オリンピック', 'WBC'],
            'cultural_impact': ['社会現象', 'ブーム', '〜の父', '〜の母', '伝説', 'レジェンド']
        }

        # イベントタイプの重要度重み付け
        self.event_type_weights = {
            'world_achievement': 1.0,      # 世界的偉業
            'national_achievement': 0.7,   # 国内偉業
            'career_milestone': 0.5,       # キャリアマイルストーン
            'personal_milestone': 0.3,     # 個人的節目
            'biographical': 0.1            # 伝記的情報
        }

    def select_seven_highlights(self,
                               person_data: Dict[str, Any],
                               all_life_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        人物の生涯で最も重要な7つの瞬間を選定

        Args:
            person_data: 人物データ
            all_life_events: すべての生涯イベント

        Returns:
            7つの最重要エピソード（表示スロット割り当て済み）
        """
        # Step 1: すべてのイベントを重要度でスコアリング
        scored_events = self._score_all_events(person_data, all_life_events)

        # Step 2: 絶対的な重要度でTOP7を選定
        top_seven = self._select_top_seven(scored_events)

        # Step 3: 表示スロットに最適配置
        assigned_episodes = self._assign_to_display_slots(top_seven)

        # Step 4: エピソード形式に変換
        formatted_episodes = self._format_episodes(person_data, assigned_episodes)

        return formatted_episodes

    def _score_all_events(self,
                         person_data: Dict[str, Any],
                         all_events: List[Dict[str, Any]]) -> List[LifeEvent]:
        """
        すべてのイベントをスコアリング
        """
        scored_events = []

        for event in all_events:
            # グローバル重要度を計算
            global_sig = self._calculate_global_significance(event)

            # 歴史的価値を計算
            historical_val = self._calculate_historical_value(event)

            # 社会的影響力を計算
            social_inf = self._calculate_social_influence(event)

            # キャリア重要性を計算
            career_imp = self._calculate_career_importance(event, person_data)

            # インパクトスコアを計算
            impact = self._calculate_impact_score(event)

            # イベントタイプを判定
            event_type = self._determine_event_type(event)

            # キーワード抽出
            keywords = self._extract_keywords(event.get('text', ''))

            life_event = LifeEvent(
                actual_age=event.get('age', 0),
                event_text=event.get('text', ''),
                impact_score=impact,
                global_significance=global_sig,
                historical_value=historical_val,
                social_influence=social_inf,
                career_importance=career_imp,
                event_type=event_type,
                keywords=keywords
            )

            scored_events.append(life_event)

        return scored_events

    def _calculate_global_significance(self, event: Dict[str, Any]) -> float:
        """
        グローバル重要度を計算
        世界的な視点での重要性を評価
        """
        score = 0.0
        text = event.get('text', '')

        # 世界的指標のチェック
        for category, indicators in self.global_impact_indicators.items():
            for indicator in indicators:
                if indicator in text:
                    if category == 'world_records':
                        score += 30
                    elif category == 'major_awards':
                        score += 25
                    elif category == 'historical_first':
                        score += 20
                    elif category == 'international_recognition':
                        score += 15
                    elif category == 'cultural_impact':
                        score += 10

        # MLB, NBA, NFL等のメジャーリーグ
        major_leagues = ['MLB', 'メジャーリーグ', 'NBA', 'NFL', 'NHL', 'プレミアリーグ']
        if any(league in text for league in major_leagues):
            score += 20

        # 日本国内リーグ（NPB, Jリーグ等）
        domestic_leagues = ['NPB', '日本プロ野球', 'Jリーグ', 'Bリーグ']
        if any(league in text for league in domestic_leagues):
            score += 10

        return min(score, 100)  # 最大100点

    def _calculate_historical_value(self, event: Dict[str, Any]) -> float:
        """
        歴史的価値を計算
        後世への影響や記録の永続性を評価
        """
        score = 0.0
        text = event.get('text', '')

        # 歴史的キーワード
        historical_keywords = {
            '史上初': 30,
            '史上最': 25,
            '記録': 20,
            '歴史': 15,
            '初めて': 15,
            '革命': 20,
            '伝説': 15,
            '不滅': 20,
            '前人未到': 25,
            '金字塔': 20
        }

        for keyword, points in historical_keywords.items():
            if keyword in text:
                score += points

        # 記録の具体性（数値が含まれているか）
        import re
        if re.search(r'\d+', text):
            score += 10

        return min(score, 100)

    def _calculate_social_influence(self, event: Dict[str, Any]) -> float:
        """
        社会的影響力を計算
        """
        score = 0.0
        text = event.get('text', '')

        social_keywords = {
            '社会現象': 30,
            'ブーム': 25,
            '話題': 15,
            '注目': 15,
            '影響': 20,
            '貢献': 20,
            '変革': 25,
            'パイオニア': 25,
            '先駆者': 20
        }

        for keyword, points in social_keywords.items():
            if keyword in text:
                score += points

        return min(score, 100)

    def _calculate_career_importance(self, event: Dict[str, Any], person_data: Dict[str, Any]) -> float:
        """
        キャリアにおける重要性を計算
        """
        score = 0.0
        text = event.get('text', '')

        career_keywords = {
            'デビュー': 20,
            '引退': 25,
            '転機': 20,
            '独立': 20,
            '設立': 20,
            '受賞': 25,
            '達成': 20,
            '優勝': 25,
            '移籍': 15,
            '就任': 20
        }

        for keyword, points in career_keywords.items():
            if keyword in text:
                score += points

        # 人物の専門分野に関連するキーワードがあれば加点
        occupation = person_data.get('occupation', '')
        if occupation and occupation in text:
            score += 15

        return min(score, 100)

    def _calculate_impact_score(self, event: Dict[str, Any]) -> float:
        """
        総合的なインパクトスコアを計算
        """
        text = event.get('text', '')
        score = 0.0

        # テキストの長さと具体性
        if len(text) > 100:
            score += 10
        if len(text) > 150:
            score += 10

        # 固有名詞の数
        import re
        proper_nouns = re.findall(r'[A-Z][a-z]+|[ァ-ヴー]+|[一-龥]+', text)
        score += min(len(proper_nouns) * 2, 20)

        # 数値データの存在
        numbers = re.findall(r'\d+', text)
        score += min(len(numbers) * 5, 20)

        # 引用符や「」の使用（具体的な発言や作品名）
        if '「' in text or '」' in text or '"' in text:
            score += 10

        return min(score, 100)

    def _determine_event_type(self, event: Dict[str, Any]) -> str:
        """
        イベントタイプを判定
        """
        text = event.get('text', '')

        # 世界的偉業
        if any(word in text for word in ['世界', 'ワールド', 'グローバル', '国際', 'メジャー']):
            return 'world_achievement'

        # 国内偉業
        if any(word in text for word in ['日本初', '日本一', '国内', '全国']):
            return 'national_achievement'

        # キャリアマイルストーン
        if any(word in text for word in ['デビュー', '引退', '転機', '独立']):
            return 'career_milestone'

        # 個人的節目
        if any(word in text for word in ['誕生', '結婚', '死去']):
            return 'personal_milestone'

        # デフォルト
        return 'biographical'

    def _extract_keywords(self, text: str) -> List[str]:
        """
        重要キーワードを抽出
        """
        keywords = []

        # 重要なキーワードパターン
        important_patterns = [
            r'MVP', r'世界[一初]', r'日本[一初]', r'史上[初最]',
            r'優勝', r'新記録', r'ノーベル', r'アカデミー',
            r'WBC', r'メジャー', r'オリンピック', r'ワールドカップ'
        ]

        for pattern in important_patterns:
            matches = re.findall(pattern, text)
            keywords.extend(matches)

        return list(set(keywords))  # 重複を除去

    def _select_top_seven(self, events: List[LifeEvent]) -> List[LifeEvent]:
        """
        絶対的な重要度でTOP7を選定
        """
        # 総合重要度でソート
        sorted_events = sorted(events, key=lambda x: x.total_importance, reverse=True)

        # TOP7を選定
        top_seven = sorted_events[:7]

        # 最低限の多様性を確保（同じタイプのイベントが5個以上にならないように）
        event_types = {}
        final_selection = []
        reserves = []

        for event in top_seven:
            event_type = event.event_type
            if event_types.get(event_type, 0) < 4:
                final_selection.append(event)
                event_types[event_type] = event_types.get(event_type, 0) + 1
            else:
                reserves.append(event)

        # 7個に満たない場合は予備から補充
        if len(final_selection) < 7:
            for event in sorted_events[7:]:
                if event not in reserves:
                    final_selection.append(event)
                    if len(final_selection) == 7:
                        break

        return final_selection

    def _assign_to_display_slots(self, events: List[LifeEvent]) -> List[Tuple[int, LifeEvent]]:
        """
        7つのイベントを表示スロットに最適配置
        """
        assignments = []
        used_slots = set()
        used_events = set()

        # Step 1: 完全一致する年齢があれば優先配置
        for event in events:
            if event.actual_age in self.display_slots and event.actual_age not in used_slots:
                assignments.append((event.actual_age, event))
                used_slots.add(event.actual_age)
                used_events.add(id(event))

        # Step 2: 残りのイベントを最も近いスロットに配置
        for event in events:
            if id(event) in used_events:
                continue

            # 最も近い空きスロットを探す
            best_slot = None
            min_distance = float('inf')

            for slot in self.display_slots:
                if slot in used_slots:
                    continue
                distance = abs(event.actual_age - slot)
                if distance < min_distance:
                    min_distance = distance
                    best_slot = slot

            if best_slot is not None:
                assignments.append((best_slot, event))
                used_slots.add(best_slot)
                used_events.add(id(event))

        # Step 3: 埋まらなかったスロットには補完エピソードを作成
        for slot in self.display_slots:
            if slot not in used_slots:
                # 最も重要度の低いイベントから補完
                placeholder_event = LifeEvent(
                    actual_age=slot,
                    event_text='',
                    impact_score=0,
                    global_significance=0,
                    historical_value=0,
                    social_influence=0,
                    career_importance=0,
                    event_type='biographical',
                    keywords=[]
                )
                assignments.append((slot, placeholder_event))

        # スロット順にソート
        assignments.sort(key=lambda x: x[0])

        return assignments

    def _format_episodes(self,
                        person_data: Dict[str, Any],
                        assignments: List[Tuple[int, LifeEvent]]) -> List[Dict[str, Any]]:
        """
        エピソードを最終形式に変換
        """
        formatted = []
        person_name = person_data.get('person_name_display', '人物')

        for display_age, event in assignments:
            if event.event_text:
                # 既存のイベントテキストを使用
                if event.actual_age != display_age:
                    # 年齢調整が必要な場合
                    episode_text = self._adjust_age_in_text(
                        event.event_text,
                        event.actual_age,
                        display_age,
                        person_name
                    )
                else:
                    episode_text = event.event_text
            else:
                # プレースホルダーエピソードを作成
                episode_text = self._create_placeholder_episode(display_age, person_name)

            formatted.append({
                'age_category': display_age,
                'actual_age': event.actual_age,
                'episode_text': episode_text,
                'importance_score': event.total_importance,
                'event_type': event.event_type,
                'keywords': event.keywords,
                'age_adjusted': event.actual_age != display_age
            })

        return formatted

    def _adjust_age_in_text(self, text: str, actual_age: int, display_age: int, person_name: str) -> str:
        """
        エピソードテキスト内の年齢を調整
        """
        # 年齢部分を置換
        adjusted = re.sub(
            r'あなたと同じ\d+歳のとき',
            f'あなたと同じ{display_age}歳のとき',
            text
        )

        # 実年齢への言及を追加（重要な場合のみ）
        if abs(actual_age - display_age) > 3:
            # 大幅な調整の場合は実年齢を明記
            adjusted = adjusted.replace(
                f'{person_name}は',
                f'{person_name}は（実際は{actual_age}歳）',
                1  # 最初の1箇所のみ
            )

        return adjusted

    def _create_placeholder_episode(self, age: int, person_name: str) -> str:
        """
        プレースホルダーエピソードを作成
        """
        templates = {
            1: f"あなたと同じ1歳のとき、{person_name}は家族の愛情に包まれて成長し、将来の才能の芽が育まれていました。",
            10: f"あなたと同じ10歳のとき、{person_name}は学校生活を送りながら、将来の夢に向かって基礎を築いていました。",
            20: f"あなたと同じ20歳のとき、{person_name}は専門分野での研鑽を積み、プロフェッショナルへの道を歩み始めていました。",
            30: f"あなたと同じ30歳のとき、{person_name}は実力を発揮し始め、業界での存在感を確立していました。",
            40: f"あなたと同じ40歳のとき、{person_name}は円熟期を迎え、その分野でのリーダーとして活躍していました。",
            50: f"あなたと同じ50歳のとき、{person_name}は豊富な経験を活かし、後進の育成にも力を注いでいました。",
            60: f"あなたと同じ60歳のとき、{person_name}は長年の功績が認められ、その分野の発展に大きく貢献していました。"
        }

        return templates.get(age, f"あなたと同じ{age}歳のとき、{person_name}は活動を続けていました。")

    def generate_importance_report(self, formatted_episodes: List[Dict[str, Any]]) -> str:
        """
        重要度レポートを生成
        """
        report = []
        report.append("="*60)
        report.append("📊 生涯ハイライト選定レポート")
        report.append("="*60)
        report.append("")

        # 総合評価
        avg_importance = sum(ep['importance_score'] for ep in formatted_episodes) / 7

        if avg_importance >= 70:
            grade = "S級（歴史的人物）"
        elif avg_importance >= 50:
            grade = "A級（極めて重要）"
        elif avg_importance >= 30:
            grade = "B級（重要）"
        else:
            grade = "C級（標準）"

        report.append(f"総合評価: {grade}")
        report.append(f"平均重要度スコア: {avg_importance:.1f}")
        report.append("")

        # 個別エピソード
        report.append("## 選定された7つのハイライト")
        for ep in formatted_episodes:
            report.append("")
            report.append(f"### {ep['age_category']}歳カテゴリ")
            report.append(f"重要度スコア: {ep['importance_score']:.1f}")
            report.append(f"イベントタイプ: {ep['event_type']}")
            if ep['age_adjusted']:
                report.append(f"年齢調整: {ep['actual_age']}歳 → {ep['age_category']}歳")
            if ep['keywords']:
                report.append(f"キーワード: {', '.join(ep['keywords'][:5])}")
            report.append(f"エピソード: {ep['episode_text'][:100]}...")

        return "\n".join(report)


def test_lifetime_highlights():
    """テスト実行"""
    selector = LifetimeHighlightSelector()

    # テスト用の人物データ（大谷翔平）
    person_data = {
        'person_name_display': '大谷翔平',
        'occupation': '野球選手'
    }

    # すべての生涯イベント（重要度順不同）
    all_events = [
        {'age': 1, 'text': 'あなたと同じ1歳のとき、大谷翔平は岩手県で生まれました。'},
        {'age': 18, 'text': 'あなたと同じ18歳のとき、大谷翔平は日本ハムに入団しました。'},
        {'age': 20, 'text': 'あなたと同じ20歳のとき、大谷翔平は日本プロ野球で2桁勝利・2桁本塁打を達成しました。'},
        {'age': 23, 'text': 'あなたと同じ23歳のとき、大谷翔平はメジャーリーグに移籍し、エンゼルスで新人王を獲得しました。'},
        {'age': 27, 'text': 'あなたと同じ27歳のとき、大谷翔平はアメリカンリーグMVPを満票で受賞し、日本人として2人目の快挙を達成しました。'},
        {'age': 28, 'text': 'あなたと同じ28歳のとき、大谷翔平はWBC日本代表として世界一に貢献し、大会MVPに選出されました。'},
        {'age': 29, 'text': 'あなたと同じ29歳のとき、大谷翔平は史上初の2年連続「10勝&40本塁打」を達成し、MLB史に新たな金字塔を打ち立てました。'},
        {'age': 25, 'text': 'あなたと同じ25歳のとき、大谷翔平はMLBオールスターゲームに初選出され、日本人初の二刀流選手として先発出場しました。'},
        {'age': 26, 'text': 'あなたと同じ26歳のとき、大谷翔平は46本塁打を放ち、日本人選手のシーズン最多本塁打記録を更新しました。'}
    ]

    # ハイライト選定
    highlights = selector.select_seven_highlights(person_data, all_events)

    # レポート生成
    report = selector.generate_importance_report(highlights)
    print(report)

    print("\n" + "="*60)
    print("✅ 生涯ハイライト選定システム - テスト完了")
    print("="*60)


if __name__ == "__main__":
    test_lifetime_highlights()