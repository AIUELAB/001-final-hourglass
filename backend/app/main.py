#!/usr/bin/env python3
"""
FastAPI メインアプリケーション

最期の砂時計キャラクターデータベースAPI
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import Optional
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from app.models import (
    Character,
    CharacterList,
    StatsSummary,
    GenreStats,
    GenderStats
)
from app.database import db
from app.utils.csv_loader import import_csv_to_db, get_default_csv_path


# FastAPIアプリケーション初期化
app = FastAPI(
    title="最期の砂時計 キャラクターデータベースAPI",
    description="100件の完璧なキャラクターデータベースを提供するREST API",
    version="1.0.0"
)

# CORS設定（フロントエンドからのアクセスを許可）
# 環境変数から読み込み、デフォルトは開発環境用
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5175,http://localhost:3000")
cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """アプリケーション起動時の処理"""
    print("🚀 FastAPI起動中...")

    # データベース接続
    db.connect()
    db.create_table()

    # CSVデータインポート
    csv_path = get_default_csv_path()
    if csv_path.exists():
        count = import_csv_to_db(db, str(csv_path))
        print(f"✅ CSVインポート完了: {count}件")
    else:
        print(f"⚠️  CSV未検出: {csv_path}")

    print("🎊 APIサーバー起動完了！")


@app.on_event("shutdown")
async def shutdown():
    """アプリケーション終了時の処理"""
    db.disconnect()
    print("👋 APIサーバー停止")


# ========================================
# ヘルスチェック
# ========================================

@app.get("/api/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {"status": "healthy", "message": "API is running"}


# ========================================
# キャラクター関連エンドポイント
# ========================================

@app.get("/api/characters", response_model=CharacterList)
async def get_characters(
    page: int = Query(1, ge=1, description="ページ番号"),
    page_size: int = Query(20, ge=1, le=100, description="ページサイズ")
):
    """
    全キャラクター取得（ページネーション対応）

    - **page**: ページ番号（1始まり）
    - **page_size**: 1ページあたりの件数（最大100）
    """
    characters, total = db.get_all_characters(page=page, page_size=page_size)

    return CharacterList(
        total=total,
        page=page,
        page_size=page_size,
        characters=characters
    )


@app.get("/api/characters/{character_id}", response_model=Character)
async def get_character(character_id: int):
    """
    特定キャラクター取得

    - **character_id**: キャラクターID
    """
    character = db.get_character_by_id(character_id)

    if not character:
        raise HTTPException(status_code=404, detail="キャラクターが見つかりません")

    return character


@app.get("/api/characters/search/", response_model=list[Character])
async def search_characters(
    q: str = Query(..., min_length=1, description="検索クエリ")
):
    """
    キャラクター検索

    - **q**: 検索クエリ（キャラクター名または作品名）
    """
    characters = db.search_characters(q)
    return characters


@app.get("/api/characters/filter/", response_model=list[Character])
async def filter_characters(
    genre: Optional[str] = Query(None, description="ジャンル"),
    gender: Optional[str] = Query(None, description="性別（female/male）")
):
    """
    キャラクターフィルタリング

    - **genre**: ジャンル（完全一致）
    - **gender**: 性別（female/male）
    """
    characters = db.filter_characters(genre=genre, gender=gender)
    return characters


# ========================================
# 統計関連エンドポイント
# ========================================

@app.get("/api/stats/summary", response_model=StatsSummary)
async def get_stats_summary():
    """統計サマリー取得"""

    # 女性キャラクターリスト
    female_characters = {
        'フグ田サザエ', 'ナミ', 'ニコ・ロビン', '毛利蘭', '竈門禰豆子',
        '胡蝶しのぶ', '浅倉南', '月野うさぎ', '綾波レイ',
        '猪熊柔', '渚美都', '大林萬理子', '速水ヒロ', '恩田希', '猪野井香鈴',
        '鹿目まどか', '暁美ほむら', '美墨なぎさ（キュアブラック）', '平沢唯', '涼宮ハルヒ',
        '峰不二子', 'ナウシカ', '神楽', 'リナ・インバース',
        '咲', '田所恵', '見崎鳴',
        '春野サクラ', '灰原哀', 'アスナ（結城明日奈）'
    }

    # 全キャラクター取得
    all_characters, total = db.get_all_characters(page=1, page_size=1000)

    # 女性・男性カウント
    female_count = sum(1 for c in all_characters if c.character_name in female_characters)
    male_count = total - female_count

    # ジャンル数
    genre_stats = db.get_genre_stats()
    total_genres = len(genre_stats)

    return StatsSummary(
        total_characters=total,
        total_genres=total_genres,
        female_count=female_count,
        male_count=male_count,
        female_ratio=round(female_count / total * 100, 1),
        era_range="1960年代～2020年代"
    )


@app.get("/api/stats/genres", response_model=list[GenreStats])
async def get_genre_stats():
    """ジャンル分布取得"""
    stats = db.get_genre_stats()

    return [
        GenreStats(
            genre=s['genre'],
            count=s['count'],
            percentage=s['percentage']
        )
        for s in stats
    ]


@app.get("/api/stats/gender", response_model=list[GenderStats])
async def get_gender_stats():
    """性別比率取得"""

    # 女性キャラクターリスト
    female_characters = {
        'フグ田サザエ', 'ナミ', 'ニコ・ロビン', '毛利蘭', '竈門禰豆子',
        '胡蝶しのぶ', '浅倉南', '月野うさぎ', '綾波レイ',
        '猪熊柔', '渚美都', '大林萬理子', '速水ヒロ', '恩田希', '猪野井香鈴',
        '鹿目まどか', '暁美ほむら', '美墨なぎさ（キュアブラック）', '平沢唯', '涼宮ハルヒ',
        '峰不二子', 'ナウシカ', '神楽', 'リナ・インバース',
        '咲', '田所恵', '見崎鳴',
        '春野サクラ', '灰原哀', 'アスナ（結城明日奈）'
    }

    # 全キャラクター取得
    all_characters, total = db.get_all_characters(page=1, page_size=1000)

    # 女性・男性カウント
    female_count = sum(1 for c in all_characters if c.character_name in female_characters)
    male_count = total - female_count

    return [
        GenderStats(
            gender="女性",
            count=female_count,
            percentage=round(female_count / total * 100, 1)
        ),
        GenderStats(
            gender="男性",
            count=male_count,
            percentage=round(male_count / total * 100, 1)
        )
    ]


# ========================================
# ルートエンドポイント
# ========================================

@app.get("/")
async def root():
    """ルートエンドポイント - HTMLダッシュボードを返す"""
    # プロジェクトルートのHTMLファイルを返す
    html_path = Path(__file__).parent.parent.parent / "episode_database_dashboard_v2.html"

    if html_path.exists():
        return FileResponse(
            html_path,
            media_type="text/html",
            headers={"Cache-Control": "no-cache"}
        )
    else:
        # HTMLが見つからない場合はJSON情報を返す
        return {
            "message": "最期の砂時計 キャラクターデータベースAPI",
            "version": "1.0.0",
            "docs": "/docs",
            "dashboard": "episode_database_dashboard_v2.html not found",
            "endpoints": {
                "characters": "/api/characters",
                "search": "/api/characters/search/?q=桜木",
                "filter": "/api/characters/filter/?genre=スポーツ漫画",
                "stats": "/api/stats/summary"
            }
        }
