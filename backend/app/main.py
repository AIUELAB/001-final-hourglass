#!/usr/bin/env python3
"""
FastAPI メインアプリケーション

最期の砂時計キャラクターデータベースAPI
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
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
    GenderStats,
    EpisodeCategoryStats,
    WorkStats,
    FameScore,
    FameRanking
)
from app.database import db
from app.utils.csv_loader import import_csv_to_db, get_default_csv_path, get_csv_modification_time


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

# 静的ファイルマウント（CSVファイルへのアクセス用）
project_root = Path(__file__).parent.parent.parent
app.mount("/data", StaticFiles(directory=str(project_root)), name="data")


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
# データ管理エンドポイント
# ========================================

@app.get("/api/data/version")
async def get_data_version():
    """
    CSVデータのバージョン情報取得

    Returns:
        - csv_path: CSVファイルパス
        - last_modified: 最終更新時刻（UNIXタイムスタンプ）
        - last_modified_iso: 最終更新時刻（ISO 8601形式）
    """
    from datetime import datetime

    csv_path = get_default_csv_path()
    mtime = get_csv_modification_time(str(csv_path))

    return {
        "csv_path": str(csv_path),
        "last_modified": mtime,
        "last_modified_iso": datetime.fromtimestamp(mtime).isoformat() if mtime > 0 else None,
        "exists": csv_path.exists()
    }


@app.post("/api/data/refresh")
async def refresh_data():
    """
    CSVデータを強制的に再読み込み

    データベースの既存データを削除し、CSVから再インポートします。

    Returns:
        - success: 成功フラグ
        - count: インポート件数
        - message: メッセージ
    """
    try:
        csv_path = get_default_csv_path()

        if not csv_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"CSVファイルが見つかりません: {csv_path}"
            )

        # 強制再インポート
        count = import_csv_to_db(db, str(csv_path), force=True)

        return {
            "success": True,
            "count": count,
            "message": f"データを再読み込みしました（{count}件）"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"データ再読み込みエラー: {str(e)}"
        )


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

    # 全キャラクター取得
    all_characters, total = db.get_all_characters(page=1, page_size=10000)

    # curator_notesから実在/架空を判定（"Type: FICTIONAL" または "Type: REAL" 形式）
    fictional_count = sum(1 for c in all_characters if 'TYPE: FICTIONAL' in c.get('curator_notes', '').upper())
    real_count = total - fictional_count

    # ジャンル数
    genre_stats = db.get_genre_stats()
    total_genres = len(genre_stats)

    return StatsSummary(
        total_characters=total,
        total_genres=total_genres,
        female_count=fictional_count,
        male_count=real_count,
        female_ratio=round(fictional_count / total * 100, 1) if total > 0 else 0,
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

    # 全キャラクター取得
    all_characters, total = db.get_all_characters(page=1, page_size=10000)

    # curator_notesから実在/架空を判定（"Type: FICTIONAL" または "Type: REAL" 形式）
    fictional_count = sum(1 for c in all_characters if 'TYPE: FICTIONAL' in c.get('curator_notes', '').upper())
    real_count = total - fictional_count

    return [
        GenderStats(
            gender="架空",
            count=fictional_count,
            percentage=round(fictional_count / total * 100, 1) if total > 0 else 0
        ),
        GenderStats(
            gender="実在",
            count=real_count,
            percentage=round(real_count / total * 100, 1) if total > 0 else 0
        )
    ]


@app.get("/api/stats/episode-categories", response_model=list[EpisodeCategoryStats])
async def get_episode_category_stats():
    """エピソードカテゴリ分布取得"""
    stats = db.get_episode_category_stats()

    return [
        EpisodeCategoryStats(
            category=s['category'],
            count=s['count'],
            percentage=s['percentage']
        )
        for s in stats
    ]


@app.get("/api/stats/works", response_model=list[WorkStats])
async def get_work_stats(limit: int = Query(20, ge=1, le=50, description="取得件数")):
    """作品別キャラクター数取得（上位N件）"""
    stats = db.get_work_stats(limit=limit)

    return [
        WorkStats(
            work_title=s['work_title'],
            count=s['count'],
            percentage=s['percentage']
        )
        for s in stats
    ]


@app.get("/api/stats/fame-ranking", response_model=FameRanking)
async def get_fame_ranking(
    limit: int = Query(100, ge=1, le=500, description="取得件数"),
    order_by: str = Query('fame_score', description="ソートフィールド (fame_score/composite_score)")
):
    """
    有名度ランキング取得

    - **limit**: 取得件数（最大500）
    - **order_by**: ソートフィールド
      - fame_score: 有名度スコア順
      - composite_score: 総合スコア順
    """
    rankings, total = db.get_fame_ranking(limit=limit, order_by=order_by)

    return FameRanking(
        total=total,
        rankings=[
            FameScore(
                id=r['id'],
                person_name=r['person_name'],
                fame_tier=r['fame_tier'],
                fame_score=r['fame_score'],
                composite_score=r['composite_score'],
                wikipedia_ja=r['wikipedia_ja'],
                textbook=r['textbook'],
                award_level=r['award_level'],
                notoriety=r['notoriety'],
                last_updated=r['last_updated']
            )
            for r in rankings
        ]
    )


# ========================================
# ルートエンドポイント
# ========================================

@app.get("/")
async def root():
    """ルートエンドポイント - HTMLダッシュボード v3を返す"""
    # preservedディレクトリのHTMLファイルを返す（v3がデフォルト）
    html_path = Path(__file__).parent.parent.parent / "preserved" / "episode_database_dashboard_v3.html"

    if html_path.exists():
        return FileResponse(
            html_path,
            media_type="text/html",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    else:
        # HTMLが見つからない場合はJSON情報を返す
        return {
            "message": "最期の砂時計 キャラクターデータベースAPI",
            "version": "3.0.0",
            "docs": "/docs",
            "dashboard": f"episode_database_dashboard_v3.html not found at {html_path}",
            "endpoints": {
                "characters": "/api/characters",
                "search": "/api/characters/search/?q=桜木",
                "filter": "/api/characters/filter/?genre=スポーツ漫画",
                "stats": "/api/stats/summary",
                "v2": "/v2",
                "v3": "/v3"
            }
        }


@app.get("/v2")
async def dashboard_v2():
    """ダッシュボード v2 へのアクセス"""
    html_path = Path(__file__).parent.parent.parent / "preserved" / "episode_database_dashboard_v2.html"

    if html_path.exists():
        return FileResponse(
            html_path,
            media_type="text/html",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    else:
        raise HTTPException(status_code=404, detail="Dashboard v2 not found")


@app.get("/v3")
async def dashboard_v3():
    """ダッシュボード v3 へのアクセス"""
    html_path = Path(__file__).parent.parent.parent / "preserved" / "episode_database_dashboard_v3.html"

    if html_path.exists():
        return FileResponse(
            html_path,
            media_type="text/html",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    else:
        raise HTTPException(status_code=404, detail="Dashboard v3 not found")
