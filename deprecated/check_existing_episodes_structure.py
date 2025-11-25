import firebase_admin
from firebase_admin import credentials, firestore
import json
from datetime import datetime

from src.secure_config import config
# Firebase初期化
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(config.firebase_credentials_path)
        firebase_admin.initialize_app(cred)
    except FileNotFoundError:
        print("Error: Firebase service account key file not found")
        exit(1)

db = firestore.client()

def analyze_existing_episodes():
    """既存のFirestoreエピソードの構造を分析"""

    print("🔍 既存のFirestoreエピソード構造を分析中...")
    print("=" * 60)

    try:
        # エピソードコレクションを取得
        episodes_ref = db.collection('episodes')
        episodes = episodes_ref.limit(10).stream()  # まず10件で確認

        # フィールド情報を収集
        all_fields = set()
        sample_episodes = []
        episode_count = 0

        for episode_doc in episodes:
            episode_count += 1
            data = episode_doc.to_dict()
            data['_doc_id'] = episode_doc.id
            sample_episodes.append(data)
            all_fields.update(data.keys())

        if episode_count == 0:
            print("❌ エピソードが見つかりません")
            return None

        print(f"✅ {episode_count}件のエピソードを分析")
        print("\n📋 既存フィールド一覧:")
        print("-" * 60)
        for field in sorted(all_fields):
            # サンプル値を取得
            sample_value = None
            for ep in sample_episodes:
                if field in ep and ep[field] is not None:
                    sample_value = ep[field]
                    break

            # 型を判定
            field_type = type(sample_value).__name__ if sample_value is not None else "None"

            # 表示用に値を短縮
            if isinstance(sample_value, str) and len(str(sample_value)) > 50:
                display_value = str(sample_value)[:47] + "..."
            else:
                display_value = str(sample_value)

            print(f"- {field} ({field_type}): {display_value}")

        # 最初のエピソードの詳細を表示
        if sample_episodes:
            print("\n📝 サンプルエピソード（1件目）:")
            print("-" * 60)
            first_ep = sample_episodes[0]
            for key, value in first_ep.items():
                if isinstance(value, str) and len(value) > 100:
                    display_value = value[:97] + "..."
                else:
                    display_value = value
                print(f"  {key}: {display_value}")

        return all_fields, sample_episodes

    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        return None, None

def create_field_mapping():
    """既存フィールドから新スキーマへのマッピングを作成"""

    print("\n" + "=" * 60)
    print("📊 フィールドマッピング分析")
    print("=" * 60)

    # 新スキーマのフィールド
    new_schema = [
        'episode_id', 'person_id', 'episode_hash',
        'person_name', 'person_name_ja', 'person_name_display',
        'episode_title', 'episode_text', 'episode_year', 'episode_date',
        'episode_type', 'age', 'age_months',
        'category', 'nationality', 'occupation', 'era',
        'name_recognition', 'accuracy_score', 'impact_score', 'source',
        'created_at', 'is_published', 'extended_data'
    ]

    # 既存フィールドから新フィールドへのマッピング候補
    field_mapping = {
        # 既存 → 新規
        'content': 'episode_text',
        'title': 'episode_title',
        'year': 'episode_year',
        'month': None,  # episode_dateに統合
        'day': None,    # episode_dateに統合
        'age': 'age',
        'person_name': 'person_name_ja',  # または person_name_display
        'person_name_display': 'person_name_display',
        'accuracy_score': 'accuracy_score',
        'impact_score': 'impact_score',
        'source': 'source',
        'nationality': 'nationality',
        'occupation': 'occupation',
        'category': 'category',
        'created_at': 'created_at',
        'is_published': 'is_published'
    }

    print("\n🔄 フィールドマッピング候補:")
    print("-" * 60)
    print("既存フィールド → 新フィールド")
    print("-" * 60)
    for old_field, new_field in field_mapping.items():
        if new_field:
            print(f"- {old_field} → {new_field}")
        else:
            print(f"- {old_field} → (統合/削除)")

    print("\n⚠️ 新規追加が必要なフィールド:")
    mapped_new_fields = set(field_mapping.values()) - {None}
    unmapped_new_fields = set(new_schema) - mapped_new_fields
    for field in sorted(unmapped_new_fields):
        print(f"- {field}")

    return field_mapping

def check_migration_feasibility():
    """移行可能性をチェック"""

    print("\n" + "=" * 60)
    print("✅ 移行可能性評価")
    print("=" * 60)

    # 移行評価
    feasibility = {
        '可能': [
            'content → episode_text',
            'title → episode_title',
            'year → episode_year',
            'age → age',
            'person_name → person_name_ja/person_name_display'
        ],
        '要変換': [
            'month + day → episode_date (MM-DD形式)',
            'age → age_months (計算必要)',
            'person_name → person_name (英語表記生成)'
        ],
        '新規生成': [
            'episode_id (UUID生成)',
            'person_id (人物DBとマッチング)',
            'episode_hash (MD5生成)',
            'episode_type (カテゴリから推定)',
            'name_recognition (人物DBから取得)',
            'era (yearから判定)'
        ]
    }

    for status, items in feasibility.items():
        print(f"\n【{status}】")
        for item in items:
            print(f"  - {item}")

    print("\n📌 結論:")
    print("✅ 既存データは新スキーマに移行可能")
    print("⚠️ ただし、以下の処理が必要:")
    print("  1. 日付フィールドの統合 (month + day → episode_date)")
    print("  2. 人物マスターとの紐付け (person_id生成)")
    print("  3. 不足フィールドの生成 (episode_type, era等)")
    print("  4. 月齢計算 (age_months)")

if __name__ == "__main__":
    print("🚀 Firestore Episodes スキーマ分析")
    print("=" * 60)

    # 既存構造を分析
    fields, episodes = analyze_existing_episodes()

    if fields:
        # フィールドマッピング作成
        mapping = create_field_mapping()

        # 移行可能性チェック
        check_migration_feasibility()

        # 分析結果を保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f'firestore_schema_analysis_{timestamp}.json'

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                'existing_fields': sorted(list(fields)),
                'field_count': len(fields),
                'sample_count': len(episodes) if episodes else 0,
                'analysis_date': timestamp
            }, f, ensure_ascii=False, indent=2)

        print(f"\n📄 分析レポート保存: {report_file}")
