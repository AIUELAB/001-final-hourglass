"""エピソード管理サービス

エピソードのCRUD操作を提供
"""

import csv
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from app.models import Episode, EpisodeCreate, EpisodeUpdate


class EpisodeManager:
    """エピソード管理クラス"""

    def __init__(self, csv_path: str):
        """
        Args:
            csv_path: CSVファイルのパス
        """
        self.csv_path = Path(csv_path)
        self.episodes: List[Dict] = []
        self._load_episodes()

    def _load_episodes(self):
        """CSVからエピソードを読み込み"""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSVファイルが見つかりません: {self.csv_path}")

        with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            self.episodes = [row for row in reader]

    def _save_episodes(self):
        """エピソードをCSVに保存"""
        if not self.episodes:
            return

        # フィールド名を取得（最初のエピソードから）
        fieldnames = list(self.episodes[0].keys())

        # バックアップ作成
        backup_path = self.csv_path.with_suffix('.csv.backup')
        if self.csv_path.exists():
            import shutil
            shutil.copy(self.csv_path, backup_path)

        # CSVに書き込み
        with open(self.csv_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.episodes)

    def _generate_person_id(self, person_name: str) -> str:
        """person_idを生成

        Args:
            person_name: 人物名

        Returns:
            8文字のハッシュID（例: P46DE283）
        """
        # 名前とタイムスタンプからハッシュ生成
        timestamp = datetime.now().isoformat()
        hash_input = f"{person_name}{timestamp}".encode('utf-8')
        hash_value = hashlib.md5(hash_input).hexdigest()[:7].upper()
        return f"P{hash_value}"

    def _calculate_composite_score(self, episode_data: Dict) -> Optional[float]:
        """総合スコアを計算

        7軸スコアの平均値を算出

        Args:
            episode_data: エピソードデータ

        Returns:
            総合スコア（7軸平均）
        """
        score_fields = [
            '記憶性スコア', '共感性スコア', '意外性スコア',
            '生成品質スコア', '教育的価値', 'ストーリー品質', '事実密度'
        ]

        scores = []
        for field in score_fields:
            value = episode_data.get(field)
            if value and value != '':
                try:
                    scores.append(float(value))
                except (ValueError, TypeError):
                    pass

        if scores:
            return sum(scores) / len(scores)
        return None

    def get_episode_by_id(self, person_id: str) -> Optional[Episode]:
        """IDでエピソードを取得

        Args:
            person_id: エピソードID

        Returns:
            エピソード、見つからない場合はNone
        """
        for ep in self.episodes:
            if ep.get('person_id') == person_id:
                return Episode(**ep)
        return None

    def list_episodes(
        self,
        page: int = 1,
        page_size: int = 20,
        filter_person_type: Optional[str] = None
    ) -> Tuple[List[Episode], int]:
        """エピソード一覧を取得

        Args:
            page: ページ番号（1から開始）
            page_size: ページサイズ
            filter_person_type: 人物タイプでフィルター（REAL/FICTIONAL）

        Returns:
            (エピソードリスト, 総件数)
        """
        # フィルタリング
        filtered = self.episodes
        if filter_person_type:
            filtered = [ep for ep in filtered if ep.get('person_type') == filter_person_type]

        total = len(filtered)

        # ページング
        start = (page - 1) * page_size
        end = start + page_size
        paginated = filtered[start:end]

        episodes = [Episode(**ep) for ep in paginated]
        return episodes, total

    def create_episode(self, episode_data: EpisodeCreate) -> Episode:
        """新しいエピソードを作成

        Args:
            episode_data: エピソード作成データ

        Returns:
            作成されたエピソード
        """
        # person_idを生成
        person_id = self._generate_person_id(episode_data.person_name)

        # 既存のフィールド構造を維持しつつ新規エピソード作成
        new_episode = {
            'person_id': person_id,
            'person_name': episode_data.person_name,
            'age': episode_data.age,
            'episode_text': episode_data.episode_text,
            'category': episode_data.category or '',
            'episode_type': episode_data.episode_type or '',
            'person_type': episode_data.person_type or 'REAL',
            'work_title': episode_data.work_title or '',
            'group_name': episode_data.group_name or '',
            'is_group_member': str(episode_data.is_group_member) if episode_data.is_group_member is not None else '',
            '人生の節目タグ': episode_data.milestone_tags or '',
            '記憶性スコア': str(episode_data.memorability_score) if episode_data.memorability_score is not None else '',
            '共感性スコア': str(episode_data.empathy_score) if episode_data.empathy_score is not None else '',
            '意外性スコア': str(episode_data.surprise_score) if episode_data.surprise_score is not None else '',
            '生成品質スコア': str(episode_data.generation_quality_score) if episode_data.generation_quality_score is not None else '',
            '教育的価値': str(episode_data.educational_value) if episode_data.educational_value is not None else '',
            'ストーリー品質': str(episode_data.storytelling_quality) if episode_data.storytelling_quality is not None else '',
            '事実密度': str(episode_data.factual_density) if episode_data.factual_density is not None else '',
            'generation_timestamp': datetime.now().isoformat(),
            'char_count': str(len(episode_data.episode_text)),
        }

        # composite_scoreを計算
        composite = self._calculate_composite_score(new_episode)
        new_episode['composite_score'] = str(composite) if composite else ''

        # 既存のエピソードから他のフィールドのデフォルト値を取得
        if self.episodes:
            template = self.episodes[0]
            for key in template.keys():
                if key not in new_episode:
                    new_episode[key] = ''

        # エピソードリストに追加
        self.episodes.append(new_episode)

        # CSVに保存
        self._save_episodes()

        return Episode(**new_episode)

    def update_episode(self, person_id: str, episode_data: EpisodeUpdate) -> Optional[Episode]:
        """エピソードを更新

        Args:
            person_id: エピソードID
            episode_data: 更新データ

        Returns:
            更新されたエピソード、見つからない場合はNone
        """
        for i, ep in enumerate(self.episodes):
            if ep.get('person_id') == person_id:
                # 提供されたフィールドのみ更新
                update_dict = episode_data.model_dump(exclude_unset=True)

                # スコアフィールドの日本語名マッピング
                field_mapping = {
                    'memorability_score': '記憶性スコア',
                    'empathy_score': '共感性スコア',
                    'surprise_score': '意外性スコア',
                    'generation_quality_score': '生成品質スコア',
                    'educational_value': '教育的価値',
                    'storytelling_quality': 'ストーリー品質',
                    'factual_density': '事実密度',
                    'milestone_tags': '人生の節目タグ'
                }

                for eng_name, jp_name in field_mapping.items():
                    if eng_name in update_dict:
                        value = update_dict[eng_name]
                        ep[jp_name] = str(value) if value is not None else ''
                        del update_dict[eng_name]

                # 残りのフィールドを更新
                for key, value in update_dict.items():
                    if value is not None:
                        ep[key] = value

                # episode_textが更新された場合、char_countを再計算
                if 'episode_text' in update_dict:
                    ep['char_count'] = str(len(update_dict['episode_text']))

                # composite_scoreを再計算
                composite = self._calculate_composite_score(ep)
                ep['composite_score'] = str(composite) if composite else ''

                # CSVに保存
                self._save_episodes()

                return Episode(**ep)

        return None

    def delete_episode(self, person_id: str) -> bool:
        """エピソードを削除

        Args:
            person_id: エピソードID

        Returns:
            削除成功の場合True
        """
        for i, ep in enumerate(self.episodes):
            if ep.get('person_id') == person_id:
                self.episodes.pop(i)
                self._save_episodes()
                return True
        return False

    def search_episodes(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Episode], int]:
        """エピソードを検索

        Args:
            query: 検索クエリ（人物名またはエピソードテキスト）
            page: ページ番号
            page_size: ページサイズ

        Returns:
            (検索結果リスト, 総件数)
        """
        query_lower = query.lower()
        filtered = [
            ep for ep in self.episodes
            if query_lower in ep.get('person_name', '').lower() or
               query_lower in ep.get('episode_text', '').lower()
        ]

        total = len(filtered)

        # ページング
        start = (page - 1) * page_size
        end = start + page_size
        paginated = filtered[start:end]

        episodes = [Episode(**ep) for ep in paginated]
        return episodes, total
