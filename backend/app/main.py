#!/usr/bin/env python3
"""
FastAPI メインアプリケーション

最期の砂時計キャラクターデータベースAPI
"""

import asyncio
import csv
import io
import json
import os
import sys
from datetime import timedelta
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

# 環境変数の読み込み
load_dotenv()

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from app.analytics import ScoreAnalytics
from app.database import db
from app.models import (
    # Phase 3: 分析モデル
    AxisStatistics,
    Character,
    CharacterList,
    CorrelationRow,
    DistributionBin,
    # Phase 5: エピソード管理モデル
    Episode,
    EpisodeCategoryStats,
    EpisodeCreate,
    EpisodeDeleteResponse,
    EpisodeList,
    LLMEvaluationResponse,
    EpisodeSearchResponse,
    # Phase 4: 検索・品質モデル
    EpisodeSearchResult,
    EpisodeUpdate,
    FameRanking,
    FameScore,
    GenderStats,
    GenreStats,
    QualityReport,
    ScoreSummary,
    SearchStatsResponse,
    StatsSummary,
    # Phase 5: 認証モデル
    Token,
    TopPerformer,
    User,
    WorkStats,
)
from app.utils.advanced_search import AdvancedSearchEngine
from app.utils.auth_simple import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_user,
    create_access_token,
    get_current_user,
    get_user,
    require_role,
)
from app.utils.csv_loader import get_csv_modification_time, get_default_csv_path, import_csv_to_db
from app.utils.data_quality import DataQualityManager
from app.utils.episode_manager import EpisodeManager
from app.utils.score_calculator import (
    calculate_hybrid_rule_scores,
    calculate_hybrid_scores_dynamic,
    detect_episode_characteristics,
    evaluate_with_llm,
)
from app.utils.csv_cache import csv_cache
from app.services import get_file_watcher, sse_manager
from app.services.log_database import log_db
from app.services.log_sse import log_sse_manager
from app.routers import logs as logs_router

# FastAPIアプリケーション初期化
app = FastAPI(
    title="最期の砂時計 キャラクターデータベースAPI",
    description="100件の完璧なキャラクターデータベースを提供するREST API",
    version="1.0.0",
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
preserved_dir = project_root / "preserved"
app.mount("/preserved", StaticFiles(directory=str(preserved_dir)), name="preserved")
app.mount("/data", StaticFiles(directory=str(project_root)), name="data")

# ログ収集APIルーター登録
app.include_router(logs_router.router, prefix="/api/logs", tags=["logs"])


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

    # ファイル監視開始
    file_watcher = get_file_watcher(csv_path)
    file_watcher.register_callback(on_csv_updated)
    file_watcher.start()
    print("👁️ ファイル監視開始")

    # SSEハートビート開始
    await sse_manager.start_heartbeat()
    print("💓 SSEハートビート開始")

    # ログ収集システム初期化
    log_db.connect()
    log_db.create_tables()
    await log_sse_manager.start_heartbeat()
    print("📝 ログ収集システム起動完了")

    print("🎊 APIサーバー起動完了！")


def on_csv_updated(mtime: float):
    """CSV更新時のコールバック（同期的に呼ばれる）"""
    csv_path = get_default_csv_path()
    csv_cache.invalidate(str(csv_path))
    metadata = csv_cache.get_metadata(str(csv_path))
    print(f"🔔 CSV更新検出: mtime={mtime}")

    # 非同期ブロードキャストをスケジュール
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(
            sse_manager.broadcast(
                "data_updated",
                {
                    "type": "csv_updated",
                    "mtime": mtime,
                    "checksum": metadata.get("checksum"),
                    "row_count": metadata.get("row_count"),
                },
            )
        )


@app.on_event("shutdown")
async def shutdown():
    """アプリケーション終了時の処理"""
    # ファイル監視停止
    csv_path = get_default_csv_path()
    file_watcher = get_file_watcher(csv_path)
    file_watcher.stop()

    # SSEハートビート停止
    await sse_manager.stop_heartbeat()

    # ログ収集システム停止
    await log_sse_manager.stop_heartbeat()
    log_db.disconnect()
    print("📝 ログ収集システム停止")

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
# SSE (Server-Sent Events) エンドポイント
# ========================================


@app.get("/api/events/data")
async def sse_data_events(request: Request):
    """
    SSEデータ更新イベントストリーム

    CSVファイルが更新されると、data_updated イベントを送信します。
    30秒ごとにheartbeatイベントを送信して接続を維持します。

    Returns:
        EventSourceResponse: SSEストリーム
    """
    client = await sse_manager.connect()

    async def generate():
        try:
            async for event in sse_manager.event_generator(client):
                if await request.is_disconnected():
                    break
                yield event
        finally:
            sse_manager.disconnect(client.client_id)

    return EventSourceResponse(generate())


@app.get("/api/data/meta")
async def get_data_metadata():
    """
    CSVデータのメタデータ取得（ETag用）

    Returns:
        - exists: ファイル存在フラグ
        - mtime: 更新時刻
        - size: ファイルサイズ
        - checksum: チェックサム
        - row_count: 行数（キャッシュ済みの場合）
        - etag: HTTP ETag値
    """
    csv_path = get_default_csv_path()
    metadata = csv_cache.get_metadata(str(csv_path))
    return metadata


# ========================================
# Phase 5: 認証エンドポイント
# ========================================


@app.post("/api/auth/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    ログインエンドポイント

    ユーザー名とパスワードで認証し、JWTアクセストークンを発行します。

    Args:
        form_data: OAuth2PasswordRequestForm（username, password）

    Returns:
        Token: アクセストークンとトークンタイプ

    Raises:
        HTTPException: 認証失敗時（401）

    Example:
        デフォルトユーザー:
        - admin / admin123 (管理者)
        - editor / editor123 (編集者)
        - viewer / viewer123 (閲覧者)
    """
    user = authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="ユーザー名またはパスワードが正しくありません",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.get("disabled", False):
        raise HTTPException(
            status_code=401,
            detail="このアカウントは無効化されています",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # JWTトークン生成
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/auth/me", response_model=User)
async def get_current_user_info(current_username: str = Depends(get_current_user)):
    """
    現在のユーザー情報取得

    JWTトークンから現在のユーザー情報を取得します。

    Args:
        current_username: 認証済みユーザー名（自動取得）

    Returns:
        User: ユーザー情報

    Raises:
        HTTPException: ユーザーが見つからない場合（404）

    Example:
        認証ヘッダー:
        Authorization: Bearer <access_token>
    """
    user = get_user(current_username)

    if user is None:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    # パスワードハッシュを除外してレスポンス
    return User(
        username=user["username"],
        email=user["email"],
        full_name=user["full_name"],
        role=user["role"],
        disabled=user.get("disabled", False),
    )


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
        "exists": csv_path.exists(),
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
            raise HTTPException(status_code=404, detail=f"CSVファイルが見つかりません: {csv_path}")

        # 強制再インポート
        count = import_csv_to_db(db, str(csv_path), force=True)

        return {"success": True, "count": count, "message": f"データを再読み込みしました（{count}件）"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"データ再読み込みエラー: {str(e)}")


# ========================================
# キャラクター関連エンドポイント
# ========================================


@app.get("/api/characters", response_model=CharacterList)
async def get_characters(
    page: int = Query(1, ge=1, description="ページ番号"),
    page_size: int = Query(20, ge=1, le=100, description="ページサイズ"),
):
    """
    全キャラクター取得（ページネーション対応）

    - **page**: ページ番号（1始まり）
    - **page_size**: 1ページあたりの件数（最大100）
    """
    characters, total = db.get_all_characters(page=page, page_size=page_size)

    return CharacterList(total=total, page=page, page_size=page_size, characters=characters)


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
async def search_characters(q: str = Query(..., min_length=1, description="検索クエリ")):
    """
    キャラクター検索

    - **q**: 検索クエリ（キャラクター名または作品名）
    """
    characters = db.search_characters(q)
    return characters


@app.get("/api/characters/filter/", response_model=list[Character])
async def filter_characters(
    genre: Optional[str] = Query(None, description="ジャンル"),
    gender: Optional[str] = Query(None, description="性別（female/male）"),
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
    fictional_count = sum(1 for c in all_characters if "TYPE: FICTIONAL" in c.get("curator_notes", "").upper())
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
        era_range="1960年代～2020年代",
    )


@app.get("/api/stats/genres", response_model=list[GenreStats])
async def get_genre_stats():
    """ジャンル分布取得"""
    stats = db.get_genre_stats()

    return [GenreStats(genre=s["genre"], count=s["count"], percentage=s["percentage"]) for s in stats]


@app.get("/api/stats/gender", response_model=list[GenderStats])
async def get_gender_stats():
    """性別比率取得"""

    # 全キャラクター取得
    all_characters, total = db.get_all_characters(page=1, page_size=10000)

    # curator_notesから実在/架空を判定（"Type: FICTIONAL" または "Type: REAL" 形式）
    fictional_count = sum(1 for c in all_characters if "TYPE: FICTIONAL" in c.get("curator_notes", "").upper())
    real_count = total - fictional_count

    return [
        GenderStats(
            gender="架空", count=fictional_count, percentage=round(fictional_count / total * 100, 1) if total > 0 else 0
        ),
        GenderStats(gender="実在", count=real_count, percentage=round(real_count / total * 100, 1) if total > 0 else 0),
    ]


@app.get("/api/stats/episode-categories", response_model=list[EpisodeCategoryStats])
async def get_episode_category_stats():
    """エピソードカテゴリ分布取得"""
    stats = db.get_episode_category_stats()

    return [EpisodeCategoryStats(category=s["category"], count=s["count"], percentage=s["percentage"]) for s in stats]


@app.get("/api/stats/works", response_model=list[WorkStats])
async def get_work_stats(limit: int = Query(20, ge=1, le=50, description="取得件数")):
    """作品別キャラクター数取得（上位N件）"""
    stats = db.get_work_stats(limit=limit)

    return [WorkStats(work_title=s["work_title"], count=s["count"], percentage=s["percentage"]) for s in stats]


@app.get("/api/stats/fame-ranking", response_model=FameRanking)
async def get_fame_ranking(
    limit: int = Query(100, ge=1, le=500, description="取得件数"),
    order_by: str = Query("fame_score", description="ソートフィールド (fame_score/composite_score)"),
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
                id=r["id"],
                person_name=r["person_name"],
                fame_tier=r["fame_tier"],
                fame_score=r["fame_score"],
                composite_score=r["composite_score"],
                wikipedia_ja=r["wikipedia_ja"],
                textbook=r["textbook"],
                award_level=r["award_level"],
                notoriety=r["notoriety"],
                last_updated=r["last_updated"],
                # Phase 1: 3軸評価カラム
                milestone_tags=r.get("milestone_tags"),
                memorability_score=r.get("memorability_score"),
                empathy_score=r.get("empathy_score"),
                surprise_score=r.get("surprise_score"),
                # Phase 2: 4軸評価カラム
                generation_quality_score=r.get("generation_quality_score"),
                educational_value=r.get("educational_value"),
                storytelling_quality=r.get("storytelling_quality"),
                factual_density=r.get("factual_density"),
            )
            for r in rankings
        ],
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
                "Expires": "0",
            },
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
                "v3": "/v3",
            },
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
                "Expires": "0",
            },
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
                "Expires": "0",
            },
        )
    else:
        raise HTTPException(status_code=404, detail="Dashboard v3 not found")


@app.get("/v4")
async def dashboard_v4():
    """ダッシュボード v4 へのアクセス"""
    html_path = Path(__file__).parent.parent.parent / "preserved" / "episode_database_dashboard_v4.html"

    if html_path.exists():
        return FileResponse(
            html_path,
            media_type="text/html",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    else:
        raise HTTPException(status_code=404, detail="Dashboard v4 not found")


@app.get("/logs-dashboard")
async def logs_dashboard():
    """ログ分析ダッシュボード"""
    html_path = Path(__file__).parent.parent.parent / "preserved" / "log_analysis_dashboard.html"

    if html_path.exists():
        return FileResponse(
            html_path,
            media_type="text/html",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    else:
        raise HTTPException(status_code=404, detail="Log analysis dashboard not found")


# ========================================
# Phase 3: 分析エンドポイント
# ========================================


@app.get("/api/analytics/summary", response_model=ScoreSummary)
async def get_analytics_summary():
    """7軸スコアの総合サマリー"""
    csv_path = get_default_csv_path()
    analytics = ScoreAnalytics(str(csv_path))

    summary = analytics.get_score_summary()

    return ScoreSummary(
        total_episodes=summary["total_episodes"], axes=[AxisStatistics(**axis) for axis in summary["axes"]]
    )


@app.get("/api/analytics/distribution")
async def get_score_distribution(bin_size: float = Query(0.5, ge=0.1, le=2.0)):
    """スコア分布ヒストグラム"""
    csv_path = get_default_csv_path()
    analytics = ScoreAnalytics(str(csv_path))

    distributions = analytics.calculate_distribution(bin_size=bin_size)

    return {
        "bin_size": bin_size,
        "distributions": {axis: [DistributionBin(**bin) for bin in bins] for axis, bins in distributions.items()},
    }


@app.get("/api/analytics/correlation")
async def get_correlation_matrix():
    """軸間の相関係数マトリックス"""
    csv_path = get_default_csv_path()
    analytics = ScoreAnalytics(str(csv_path))

    matrix = analytics.calculate_correlation_matrix()

    return {"matrix": [CorrelationRow(**row) for row in matrix]}


@app.get("/api/analytics/top-performers")
async def get_top_performers(top_n: int = Query(50, ge=1, le=200)):
    """総合スコア上位のエピソード"""
    csv_path = get_default_csv_path()
    analytics = ScoreAnalytics(str(csv_path))

    performers = analytics.get_top_performers(top_n=top_n)

    return {"total": len(performers), "top_n": top_n, "performers": [TopPerformer(**p) for p in performers]}


# ========================================
# Phase 4: 高度な検索エンドポイント
# ========================================


@app.get("/api/search/advanced", response_model=EpisodeSearchResponse)
async def advanced_search(
    query: Optional[str] = Query(None, description="検索クエリ（人物名・エピソード）"),
    min_memorability_score: Optional[float] = Query(None, ge=0, le=10, description="記憶性スコア最小値"),
    max_memorability_score: Optional[float] = Query(None, ge=0, le=10, description="記憶性スコア最大値"),
    min_empathy_score: Optional[float] = Query(None, ge=0, le=10, description="共感性スコア最小値"),
    max_empathy_score: Optional[float] = Query(None, ge=0, le=10, description="共感性スコア最大値"),
    min_surprise_score: Optional[float] = Query(None, ge=0, le=10, description="意外性スコア最小値"),
    max_surprise_score: Optional[float] = Query(None, ge=0, le=10, description="意外性スコア最大値"),
    min_generation_quality: Optional[float] = Query(None, ge=0, le=10, description="生成品質スコア最小値"),
    max_generation_quality: Optional[float] = Query(None, ge=0, le=10, description="生成品質スコア最大値"),
    min_educational_value: Optional[float] = Query(None, ge=0, le=10, description="教育的価値最小値"),
    max_educational_value: Optional[float] = Query(None, ge=0, le=10, description="教育的価値最大値"),
    min_storytelling_quality: Optional[float] = Query(None, ge=0, le=10, description="ストーリー品質最小値"),
    max_storytelling_quality: Optional[float] = Query(None, ge=0, le=10, description="ストーリー品質最大値"),
    min_factual_density: Optional[float] = Query(None, ge=0, le=10, description="事実密度最小値"),
    max_factual_density: Optional[float] = Query(None, ge=0, le=10, description="事実密度最大値"),
    min_composite_score: Optional[float] = Query(None, ge=0, le=10, description="総合スコア最小値"),
    max_composite_score: Optional[float] = Query(None, ge=0, le=10, description="総合スコア最大値"),
    min_age: Optional[float] = Query(None, ge=0, le=150, description="年齢最小値"),
    max_age: Optional[float] = Query(None, ge=0, le=150, description="年齢最大値"),
    sort_by: str = Query("composite_score", description="ソート基準"),
    order: str = Query("desc", description="並び順（asc/desc）"),
    page: int = Query(1, ge=1, description="ページ番号"),
    page_size: int = Query(20, ge=1, le=100, description="ページサイズ"),
):
    """
    高度な検索

    7軸スコア、総合スコア、年齢範囲などの複数条件で検索
    """
    csv_path = get_default_csv_path()
    search_engine = AdvancedSearchEngine(str(csv_path))

    results, total = search_engine.search(
        query=query,
        min_memorability_score=min_memorability_score,
        max_memorability_score=max_memorability_score,
        min_empathy_score=min_empathy_score,
        max_empathy_score=max_empathy_score,
        min_surprise_score=min_surprise_score,
        max_surprise_score=max_surprise_score,
        min_generation_quality=min_generation_quality,
        max_generation_quality=max_generation_quality,
        min_educational_value=min_educational_value,
        max_educational_value=max_educational_value,
        min_storytelling_quality=min_storytelling_quality,
        max_storytelling_quality=max_storytelling_quality,
        min_factual_density=min_factual_density,
        max_factual_density=max_factual_density,
        min_composite_score=min_composite_score,
        max_composite_score=max_composite_score,
        min_age=min_age,
        max_age=max_age,
        sort_by=sort_by,
        order=order,
        page=page,
        page_size=page_size,
    )

    search_results = [
        EpisodeSearchResult(
            person_name=r.get("person_name", ""),
            age=r.get("age", ""),
            episode=r.get("episode", ""),
            composite_score=r.get("composite_score", 0.0),
            memorability_score=r.get("記憶性スコア", 0.0),
            empathy_score=r.get("共感性スコア", 0.0),
            surprise_score=r.get("意外性スコア", 0.0),
            generation_quality_score=r.get("生成品質スコア", 0.0),
            educational_value=r.get("教育的価値", 0.0),
            storytelling_quality=r.get("ストーリー品質", 0.0),
            factual_density=r.get("事実密度", 0.0),
        )
        for r in results
    ]

    return EpisodeSearchResponse(total=total, page=page, page_size=page_size, results=search_results)


@app.get("/api/search/stats", response_model=SearchStatsResponse)
async def get_search_stats():
    """
    検索統計情報取得

    スコア範囲、年齢範囲などの統計情報
    """
    csv_path = get_default_csv_path()
    search_engine = AdvancedSearchEngine(str(csv_path))

    stats = search_engine.get_search_stats()

    return SearchStatsResponse(
        total_episodes=stats["total_episodes"], score_ranges=stats["score_ranges"], age_range=stats["age_range"]
    )


# ========================================
# Phase 4: データ品質管理API
# ========================================


@app.get("/api/quality/report", response_model=QualityReport)
async def get_quality_report():
    """
    データ品質レポート取得

    重複検出、外れ値検出、完全性チェックを含む総合品質レポート
    """
    csv_path = get_default_csv_path()
    quality_manager = DataQualityManager(str(csv_path))

    report = quality_manager.get_quality_report()

    return QualityReport(**report)


# ========================================
# Phase 4: データエクスポートAPI
# ========================================


@app.get("/api/export/csv")
async def export_csv(
    query: Optional[str] = Query(None), min_composite_score: Optional[float] = Query(None, ge=0, le=10)
):
    """
    CSV形式でエクスポート

    フィルタリング条件に合致するエピソードをCSV形式でダウンロード
    """
    csv_path = get_default_csv_path()
    search_engine = AdvancedSearchEngine(str(csv_path))

    # 検索実行
    results, total = search_engine.search(
        query=query,
        min_composite_score=min_composite_score,
        page=1,
        page_size=10000,  # 全件取得
    )

    # CSV生成
    output = io.StringIO()
    if results:
        fieldnames = list(results[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=episodes_export.csv"},
    )


@app.get("/api/export/json")
async def export_json(
    query: Optional[str] = Query(None), min_composite_score: Optional[float] = Query(None, ge=0, le=10)
):
    """
    JSON形式でエクスポート

    フィルタリング条件に合致するエピソードをJSON形式でダウンロード
    """
    csv_path = get_default_csv_path()
    search_engine = AdvancedSearchEngine(str(csv_path))

    # 検索実行
    results, total = search_engine.search(
        query=query,
        min_composite_score=min_composite_score,
        page=1,
        page_size=10000,  # 全件取得
    )

    # JSON生成
    json_data = json.dumps({"total": total, "results": results}, ensure_ascii=False, indent=2)

    return Response(
        content=json_data,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=episodes_export.json"},
    )


# ========================================
# Phase 5: エピソード管理CRUD API
# ========================================


@app.get("/api/episodes", response_model=EpisodeList)
async def list_episodes(
    page: int = Query(1, ge=1, description="ページ番号"),
    page_size: int = Query(20, ge=1, le=100, description="ページサイズ"),
    person_type: Optional[str] = Query(None, description="人物タイプフィルター（REAL/FICTIONAL）"),
):
    """エピソード一覧取得

    ページングとフィルタリング機能を提供
    """
    csv_path = get_default_csv_path()
    episode_manager = EpisodeManager(str(csv_path))

    episodes, total = episode_manager.list_episodes(page=page, page_size=page_size, filter_person_type=person_type)

    return EpisodeList(total=total, page=page, page_size=page_size, episodes=episodes)


@app.get("/api/episodes/search", response_model=EpisodeList)
async def search_episodes(
    q: str = Query(..., min_length=1, description="検索クエリ"),
    page: int = Query(1, ge=1, description="ページ番号"),
    page_size: int = Query(20, ge=1, le=100, description="ページサイズ"),
):
    """エピソード検索

    人物名またはエピソードテキストで検索
    """
    csv_path = get_default_csv_path()
    episode_manager = EpisodeManager(str(csv_path))

    episodes, total = episode_manager.search_episodes(query=q, page=page, page_size=page_size)

    return EpisodeList(total=total, page=page, page_size=page_size, episodes=episodes)


@app.get("/api/episodes/{person_id}", response_model=Episode)
async def get_episode(person_id: str):
    """エピソード詳細取得

    person_idでエピソードを取得
    """
    csv_path = get_default_csv_path()
    episode_manager = EpisodeManager(str(csv_path))

    episode = episode_manager.get_episode_by_id(person_id)
    if not episode:
        raise HTTPException(status_code=404, detail=f"エピソードが見つかりません: {person_id}")

    return episode


@app.post("/api/episodes", response_model=Episode, status_code=201)
async def create_episode(episode_data: EpisodeCreate, current_user: dict = Depends(require_role(["admin", "editor"]))):
    """エピソード作成

    新しいエピソードを追加

    **権限**: admin, editor
    """
    csv_path = get_default_csv_path()
    episode_manager = EpisodeManager(str(csv_path))

    try:
        episode = episode_manager.create_episode(episode_data)
        return episode
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"エピソード作成に失敗しました: {str(e)}")


@app.put("/api/episodes/{person_id}", response_model=Episode)
async def update_episode(
    person_id: str, episode_data: EpisodeUpdate, current_user: dict = Depends(require_role(["admin", "editor"]))
):
    """エピソード更新

    既存のエピソードを更新

    **権限**: admin, editor
    """
    csv_path = get_default_csv_path()
    episode_manager = EpisodeManager(str(csv_path))

    episode = episode_manager.update_episode(person_id, episode_data)
    if not episode:
        raise HTTPException(status_code=404, detail=f"エピソードが見つかりません: {person_id}")

    return episode


@app.delete("/api/episodes/{person_id}", response_model=EpisodeDeleteResponse)
async def delete_episode(person_id: str, current_user: dict = Depends(require_role(["admin"]))):
    """エピソード削除

    エピソードをCSVから削除

    **権限**: admin のみ
    """
    csv_path = get_default_csv_path()
    episode_manager = EpisodeManager(str(csv_path))

    success = episode_manager.delete_episode(person_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"エピソードが見つかりません: {person_id}")

    return EpisodeDeleteResponse(success=True, message="エピソードが正常に削除されました", deleted_person_id=person_id)


@app.post("/api/episodes/{person_id}/evaluate-llm", response_model=LLMEvaluationResponse)
async def evaluate_episode_llm(person_id: str, current_user: dict = Depends(require_role(["admin", "editor"]))):
    """エピソードLLM評価

    LLMを使用してエピソードを7軸で評価し、ハイブリッドスコアを返却

    **権限**: admin, editor
    """
    import time

    start_time = time.time()

    csv_path = get_default_csv_path()
    episode_manager = EpisodeManager(str(csv_path))

    episode = episode_manager.get_episode_by_id(person_id)
    if not episode:
        raise HTTPException(status_code=404, detail=f"エピソードが見つかりません: {person_id}")

    episode_text = episode.episode_text
    if not episode_text or len(episode_text) < 50:
        raise HTTPException(status_code=400, detail="エピソードテキストが短すぎます（最低50文字必要）")

    # エピソードデータを辞書形式で準備
    episode_data = {
        "episode_text": episode_text,
        "person_name": episode.person_name,
        "episode_type": episode.episode_type,
    }

    # 特性検出
    characteristics = detect_episode_characteristics(episode_text)

    # ルールベーススコア
    rule_scores = calculate_hybrid_rule_scores(episode_data)

    # LLM評価
    llm_scores = evaluate_with_llm(episode_text, calibrate=True)
    if llm_scores is None:
        raise HTTPException(status_code=503, detail="LLM評価に失敗しました（API接続エラーの可能性）")

    # ハイブリッドスコア（動的重み）
    hybrid_scores = calculate_hybrid_scores_dynamic(episode_data, llm_scores, use_dynamic_weights=True)

    evaluation_time = time.time() - start_time

    return LLMEvaluationResponse(
        episode_id=person_id,
        person_name=episode.person_name,
        llm_scores=llm_scores,
        rule_scores=rule_scores,
        hybrid_scores=hybrid_scores,
        characteristics=characteristics,
        evaluation_time=round(evaluation_time, 2),
    )
