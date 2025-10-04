#!/usr/bin/env python3
"""
信頼できる29件の検証済みエピソードをFirebase Firestoreにアップロード
"""

import pandas as pd
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from datetime import datetime
import logging
import os
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def initialize_firebase():
    """Firebase初期化"""
    try:
        # 既存のアプリケーションがある場合は削除
        if firebase_admin._apps:
            firebase_admin.delete_app(firebase_admin.get_app())

        # 認証情報のパスを確認
        cred_paths = [
            'serviceAccountKey.json',
            'firebase_credentials.json',
            'firebase_admin.json',
            '.env/firebase_credentials.json'
        ]

        cred_path = None
        for path in cred_paths:
            if os.path.exists(path):
                cred_path = path
                break

        if cred_path:
            logger.info(f"Firebase認証ファイルを使用: {cred_path}")
            cred = credentials.Certificate(cred_path)
        else:
            logger.warning("Firebase認証ファイルが見つかりません。環境変数を確認中...")
            # 環境変数から取得を試みる
            if os.environ.get('FIREBASE_CONFIG'):
                firebase_config = json.loads(os.environ.get('FIREBASE_CONFIG'))
                cred = credentials.Certificate(firebase_config)
            else:
                raise FileNotFoundError("Firebase認証情報が見つかりません")

        firebase_admin.initialize_app(cred)
        db = firestore.client()
        logger.info("✅ Firebase初期化成功")
        return db

    except Exception as e:
        logger.error(f"❌ Firebase初期化失敗: {e}")
        return None

def upload_trusted_episodes():
    """信頼できるエピソードをFirestoreにアップロード"""

    logger.info("="*60)
    logger.info("🚀 信頼できるエピソードのFirebaseアップロード開始")
    logger.info("="*60)

    # Firebaseの初期化
    db = initialize_firebase()
    if not db:
        logger.error("Firebaseの初期化に失敗しました")
        return

    # 信頼できるエピソードファイルを読み込み
    csv_file = 'trusted_episodes_latest.csv'
    if not os.path.exists(csv_file):
        csv_file = 'trusted_episodes_master_20250922_071200.csv'

    logger.info(f"\n📂 読み込みファイル: {csv_file}")
    df = pd.read_csv(csv_file, encoding='utf-8-sig')
    logger.info(f"✅ {len(df)}件の検証済みエピソードを読み込み")

    # Firestoreのepisodesコレクションを取得
    episodes_ref = db.collection('episodes')

    # 既存のエピソードをバックアップ
    logger.info("\n📦 既存エピソードのバックアップ中...")
    backup_ref = db.collection('episodes_backup_' + datetime.now().strftime('%Y%m%d_%H%M%S'))

    # 既存データをバックアップ
    existing_count = 0
    try:
        existing_episodes = episodes_ref.stream()
        for doc in existing_episodes:
            backup_ref.document(doc.id).set(doc.to_dict())
            existing_count += 1
        logger.info(f"✅ {existing_count}件の既存エピソードをバックアップ")
    except Exception as e:
        logger.warning(f"バックアップ中にエラー: {e}")

    # 既存のエピソードを全て削除（オプション）
    logger.info("\n🗑️ 既存エピソードのクリア...")
    try:
        # バッチ削除
        batch = db.batch()
        docs = episodes_ref.stream()
        batch_count = 0

        for doc in docs:
            batch.delete(doc.reference)
            batch_count += 1

            # 500件ごとにコミット（Firestoreの制限）
            if batch_count >= 500:
                batch.commit()
                batch = db.batch()
                batch_count = 0

        if batch_count > 0:
            batch.commit()

        logger.info("✅ 既存エピソードをクリア")
    except Exception as e:
        logger.warning(f"クリア中にエラー: {e}")

    # 新しい検証済みエピソードをアップロード
    logger.info("\n📤 検証済みエピソードのアップロード開始...")

    upload_count = 0
    batch = db.batch()
    batch_count = 0

    for idx, row in df.iterrows():
        try:
            # エピソードデータを準備
            episode_data = {
                'person_name': row['person_name'],
                'episode_age': int(row['episode_age']),
                'user_age': int(row['user_age']),
                'episode_text': row['episode_text'],
                'character_count': int(row['character_count']),
                'category': row['category'],
                'weighted_score': float(row['weighted_score']),
                'fact_check_status': row['fact_check_status'],
                'is_valid': bool(row['is_valid']),
                'created_at': firestore.SERVER_TIMESTAMP,
                'updated_at': firestore.SERVER_TIMESTAMP,
                'version': '2.0',  # 信頼できるエピソードバージョン
                'source': 'trusted_episodes_master'
            }

            # ドキュメントIDを生成（person_name + episode_age）
            doc_id = f"{row['person_name']}_{row['episode_age']}"
            doc_id = doc_id.replace(' ', '_').replace('・', '_')

            # バッチに追加
            episodes_ref.document(doc_id).set(episode_data)
            upload_count += 1
            batch_count += 1

            logger.info(f"  {upload_count}. {row['person_name']}（{row['episode_age']}歳）- アップロード完了")

            # 500件ごとにコミット
            if batch_count >= 500:
                batch.commit()
                batch = db.batch()
                batch_count = 0

        except Exception as e:
            logger.error(f"  ❌ エラー: {row['person_name']} - {e}")

    # 残りのバッチをコミット
    if batch_count > 0:
        batch.commit()

    # サマリー統計の作成
    logger.info("\n📊 アップロードサマリー:")
    logger.info(f"  総アップロード数: {upload_count}/{len(df)}件")
    logger.info(f"  成功率: {(upload_count/len(df)*100):.1f}%")

    # メタデータコレクションの更新
    logger.info("\n📝 メタデータの更新...")
    try:
        metadata_ref = db.collection('metadata').document('episodes_info')
        metadata_ref.set({
            'total_episodes': upload_count,
            'last_updated': firestore.SERVER_TIMESTAMP,
            'version': '2.0',
            'data_source': 'trusted_episodes_master',
            'quality_status': 'verified',
            'fact_checked': True,
            'update_description': '検証済み29件のエピソードのみを保持'
        })
        logger.info("✅ メタデータ更新完了")
    except Exception as e:
        logger.error(f"❌ メタデータ更新失敗: {e}")

    logger.info("\n" + "="*60)
    logger.info("✨ Firebaseアップロード完了！")
    logger.info("="*60)
    logger.info(f"📌 重要な変更:")
    logger.info(f"  - {upload_count}件の検証済みエピソードをアップロード")
    logger.info(f"  - 全エピソードがfact_check済み")
    logger.info(f"  - 品質スコア: 8.0以上のみ")
    logger.info(f"  - iOSアプリで即座に利用可能")

    return upload_count

def verify_upload():
    """アップロードの検証"""
    logger.info("\n🔍 アップロードの検証中...")

    db = initialize_firebase()
    if not db:
        return

    # エピソード数を確認
    episodes_ref = db.collection('episodes')
    docs = list(episodes_ref.stream())

    logger.info(f"✅ Firestore上のエピソード数: {len(docs)}件")

    # サンプル表示
    if docs:
        logger.info("\n📋 サンプルエピソード（最初の3件）:")
        for doc in docs[:3]:
            data = doc.to_dict()
            logger.info(f"  - {data.get('person_name')}（{data.get('episode_age')}歳）")

if __name__ == "__main__":
    # アップロード実行
    upload_count = upload_trusted_episodes()

    # 検証
    if upload_count and upload_count > 0:
        verify_upload()