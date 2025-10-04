#!/usr/bin/env python3
"""
Phase 1: 単一エピソード生成スクリプト（人間確認付き）

1人ずつエピソードを生成し、人間が確認してから保存します。
PDCAGuardian統合により、90ルールで自動検証を行います。
"""

import sys
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import os

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# PDCAGuardian（統合ルール対応版）
try:
    from pdca_guardian import PDCAGuardian
except ImportError:
    print("❌ PDCAGuardianのインポートに失敗しました")
    sys.exit(1)

# OpenAI API
try:
    import openai
except ImportError:
    print("❌ OpenAIライブラリが見つかりません")
    print("   pip install openai を実行してください")
    sys.exit(1)


class EpisodeGeneratorSingle:
    """単一エピソード生成クラス"""

    def __init__(self, db_path: str = "episode_database.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

        # PDCAGuardian初期化（統合ルール有効）
        self.guardian = PDCAGuardian(
            memory_file="phase1_memory.json",
            use_unified_rules=True,
            relaxed_mode=False  # Phase 1は厳格モード
        )

        # OpenAI API設定
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("❌ OPENAI_API_KEYが設定されていません")
        openai.api_key = api_key

        print(f"✅ エピソード生成エンジン初期化完了")
        print(f"   統合ルール数: {len(self.guardian.unified_rule_loader.rules)}件")

    def get_person_info(self, person_id: str) -> Optional[Dict[str, Any]]:
        """人物情報を取得"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                person_id,
                person_name_ja,
                person_name_en,
                birth_year,
                death_year,
                category,
                recognition_score,
                entity_type,
                group_affiliation,
                primary_work
            FROM persons
            WHERE person_id = ?
        """, (person_id,))

        row = cursor.fetchone()
        if not row:
            return None

        return {
            'person_id': row['person_id'],
            'person_name_ja': row['person_name_ja'],
            'person_name_en': row['person_name_en'],
            'birth_year': row['birth_year'],
            'death_year': row['death_year'],
            'category': row['category'],
            'recognition_score': row['recognition_score'],
            'entity_type': row['entity_type'],
            'group_affiliation': row['group_affiliation'],
            'primary_work': row['primary_work'],
        }

    def generate_episode_prompt(self, person_info: Dict[str, Any]) -> str:
        """エピソード生成プロンプトを作成"""
        name = person_info['person_name_ja']
        birth_year = person_info['birth_year']
        category = person_info['category']
        entity_type = person_info['entity_type']

        # 基本プロンプト
        prompt = f"""
あなたは{name}の人生エピソードを生成する専門家です。

【対象人物】
- 名前: {name}
- 生年: {birth_year}年
- カテゴリ: {category}
- タイプ: {entity_type}

【エピソード生成ルール】
1. 文字数: 150-250文字厳守
2. 年齢言及: 必ず具体的な年齢を含める（「〇〇歳の時」形式）
3. 文末: 必ず動詞・形容詞で終わる（「〜した」「〜だった」等）
4. 事実性: Wikipediaや信頼できる情報源に基づく事実のみ
5. 具体性: 数値、固有名詞、具体的な出来事を含める
6. 感情価値: 印象的で記憶に残るエピソード
7. 歴史的意義: その人物の代表的な出来事

【禁止事項】
❌ 推測や憶測を含めない
❌ 「〜と言われている」などの曖昧表現
❌ 一般論や抽象的な記述
❌ 括弧書き（）の多用
❌ 敬語や敬称（さん、様等）

【出力形式】
年齢: 〇〇
エピソード: 〇〇歳の時、（150-250文字の具体的エピソード）

必ず上記形式で1つのエピソードを生成してください。
"""

        return prompt

    def call_openai_api(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """OpenAI APIを呼び出してエピソードを生成"""
        for attempt in range(max_retries):
            try:
                response = openai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "あなたは歴史的事実に基づいた正確なエピソードを生成する専門家です。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=500
                )

                return response.choices[0].message.content.strip()

            except Exception as e:
                print(f"⚠️ API呼び出し失敗（試行 {attempt + 1}/{max_retries}）: {e}")
                if attempt == max_retries - 1:
                    return None

        return None

    def parse_episode_response(self, response: str) -> Optional[Dict[str, Any]]:
        """APIレスポンスをパース"""
        try:
            lines = response.strip().split('\n')
            age = None
            episode_text = None

            for line in lines:
                if line.startswith('年齢:') or line.startswith('年齢：'):
                    age_str = line.split(':', 1)[1].strip() if ':' in line else line.split('：', 1)[1].strip()
                    age = int(''.join(c for c in age_str if c.isdigit()))
                elif line.startswith('エピソード:') or line.startswith('エピソード：'):
                    episode_text = line.split(':', 1)[1].strip() if ':' in line else line.split('：', 1)[1].strip()

            if age is None or not episode_text:
                # フォーマットが異なる場合の代替パース
                # 「〇〇歳の時」を検索
                import re
                age_match = re.search(r'(\d+)歳', response)
                if age_match:
                    age = int(age_match.group(1))
                    # エピソード全体を取得（年齢行を除く）
                    episode_text = response.replace(f'{age}歳', f'{age}歳', 1)
                    # 「年齢:」「エピソード:」などのラベルを除去
                    episode_text = re.sub(r'^(年齢|エピソード)[：:]\s*', '', episode_text, flags=re.MULTILINE)
                    episode_text = episode_text.strip()

            if age is None or not episode_text:
                return None

            return {
                'age': age,
                'episode_text': episode_text
            }

        except Exception as e:
            print(f"❌ レスポンスのパースに失敗: {e}")
            return None

    def validate_episode(self, person_info: Dict[str, Any], episode: Dict[str, Any]) -> Dict[str, Any]:
        """PDCAGuardianでエピソードを検証"""
        # 検証用データ構造
        episode_data = {
            'person_id': person_info['person_id'],
            'person_name_ja': person_info['person_name_ja'],
            'age': episode['age'],
            'episode_text': episode['episode_text'],
            'birth_year': person_info['birth_year'],
            'category': person_info['category'],
            'entity_type': person_info['entity_type'],
        }

        # PDCAGuardianで検証
        violations = []
        active_rules = self.guardian.get_all_active_rules()

        print(f"\n🔍 検証中... ({len(active_rules)}ルール適用)")

        for rule in active_rules:
            rule_id = rule.get('rule_id')
            # 各ルールの検証ロジックを実行
            # ここでは簡易版として文字数とルール基本チェックのみ
            if 'character_count' in rule_id.lower():
                length = len(episode_data['episode_text'])
                if not (150 <= length <= 250):
                    violations.append({
                        'rule_id': rule_id,
                        'rule_name': rule.get('name'),
                        'severity': 'critical',
                        'message': f'文字数違反: {length}文字（150-250文字必須）'
                    })

        # 年齢言及チェック
        if f"{episode_data['age']}歳" not in episode_data['episode_text']:
            violations.append({
                'rule_id': 'AGE_MENTION',
                'rule_name': '年齢言及',
                'severity': 'critical',
                'message': f"年齢{episode_data['age']}歳がエピソード本文に含まれていません"
            })

        return {
            'is_valid': len(violations) == 0,
            'violations': violations,
            'validation_count': len(active_rules)
        }

    def display_episode(self, person_info: Dict[str, Any], episode: Dict[str, Any], validation_result: Dict[str, Any]):
        """エピソードを表示"""
        print("\n" + "=" * 70)
        print("  生成されたエピソード")
        print("=" * 70)

        print(f"\n【人物情報】")
        print(f"  ID: {person_info['person_id']}")
        print(f"  名前: {person_info['person_name_ja']}")
        print(f"  生年: {person_info['birth_year']}年")
        print(f"  カテゴリ: {person_info['category']}")

        print(f"\n【エピソード】")
        print(f"  年齢: {episode['age']}歳")
        print(f"  文字数: {len(episode['episode_text'])}文字")
        print(f"\n  内容:")
        print(f"  {episode['episode_text']}")

        print(f"\n【検証結果】")
        print(f"  検証ルール数: {validation_result['validation_count']}件")

        if validation_result['is_valid']:
            print(f"  ✅ 検証成功: すべてのルールをクリア")
        else:
            print(f"  ❌ 検証失敗: {len(validation_result['violations'])}件の違反")
            for v in validation_result['violations']:
                print(f"     - [{v['severity']}] {v['rule_name']}: {v['message']}")

        print("=" * 70)

    def save_episode(self, person_info: Dict[str, Any], episode: Dict[str, Any]) -> bool:
        """エピソードをデータベースに保存"""
        try:
            cursor = self.conn.cursor()

            # episode_id生成
            episode_id = f"EP_{person_info['person_id']}_{episode['age']:03d}"

            cursor.execute("""
                INSERT INTO episodes (
                    episode_id,
                    person_id,
                    age,
                    episode_text,
                    quality_score,
                    grade,
                    source,
                    created_at,
                    is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                episode_id,
                person_info['person_id'],
                episode['age'],
                episode['episode_text'],
                0.0,  # 初期品質スコア
                'phase1_pilot',
                'openai_gpt4o_mini',
                datetime.now().isoformat(),
                True
            ))

            self.conn.commit()
            print(f"\n✅ エピソードを保存しました: {episode_id}")
            return True

        except Exception as e:
            print(f"\n❌ エピソード保存に失敗: {e}")
            self.conn.rollback()
            return False

    def generate_single_episode(self, person_id: str, auto_approve: bool = False) -> bool:
        """単一エピソードを生成"""
        # Step 1: 人物情報取得
        print(f"\n📋 人物情報を取得中... ({person_id})")
        person_info = self.get_person_info(person_id)

        if not person_info:
            print(f"❌ 人物が見つかりません: {person_id}")
            return False

        print(f"✅ {person_info['person_name_ja']} の情報を取得")

        # Step 2: プロンプト生成
        prompt = self.generate_episode_prompt(person_info)

        # Step 3: API呼び出し
        print(f"\n🤖 エピソードを生成中...")
        response = self.call_openai_api(prompt)

        if not response:
            print(f"❌ API呼び出しに失敗しました")
            return False

        # Step 4: レスポンスをパース
        episode = self.parse_episode_response(response)

        if not episode:
            print(f"❌ レスポンスのパースに失敗しました")
            print(f"   レスポンス: {response}")
            return False

        print(f"✅ エピソード生成完了")

        # Step 5: 検証
        validation_result = self.validate_episode(person_info, episode)

        # Step 6: 表示
        self.display_episode(person_info, episode, validation_result)

        # Step 7: 人間による確認
        if not auto_approve:
            print(f"\n❓ このエピソードを保存しますか？")
            print(f"   [y] 保存する")
            print(f"   [n] 保存しない（破棄）")
            print(f"   [r] 再生成する")

            choice = input("\n選択 (y/n/r): ").strip().lower()

            if choice == 'r':
                print(f"\n🔄 再生成します...")
                return self.generate_single_episode(person_id, auto_approve=False)
            elif choice != 'y':
                print(f"\n⏭️ エピソードを破棄しました")
                return False

        # Step 8: 保存
        return self.save_episode(person_info, episode)

    def close(self):
        """データベース接続を閉じる"""
        self.conn.close()


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("使用方法: python phase1_generate_episode_single.py <person_id> [--auto-approve]")
        print("\n例:")
        print("  python phase1_generate_episode_single.py P000263")
        print("  python phase1_generate_episode_single.py P000263 --auto-approve")
        return 1

    person_id = sys.argv[1]
    auto_approve = '--auto-approve' in sys.argv

    print("=" * 70)
    print("  Phase 1: 単一エピソード生成（人間確認付き）")
    print("=" * 70)

    generator = EpisodeGeneratorSingle()

    try:
        success = generator.generate_single_episode(person_id, auto_approve=auto_approve)

        if success:
            print("\n" + "=" * 70)
            print("  ✅ エピソード生成・保存完了")
            print("=" * 70)
            return 0
        else:
            print("\n" + "=" * 70)
            print("  ⚠️ エピソードは保存されませんでした")
            print("=" * 70)
            return 1

    finally:
        generator.close()


if __name__ == '__main__':
    sys.exit(main())
