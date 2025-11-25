"""同期データの型定義とバリデーション。

ChatGPT Projects 由来のエクスポート JSON を受け取り、内部統一スキーマへ
マッピングする。Pydantic v2 を使用し、厳格な型検証を行う。
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, HttpUrl, ValidationError


class ProjectResource(BaseModel):
    """プロジェクトに添付された外部/内部リソース情報。"""

    id: str = Field(..., description="リソースID（エクスポート由来のユニークキー）")
    title: Optional[str] = Field(None, description="人間可読のタイトル")
    url: Optional[HttpUrl] = Field(None, description="外部参照 URL（存在する場合）")
    kind: Optional[str] = Field(None, description="リソース種別（document|dataset|link など）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="任意メタデータ")


class ProjectItem(BaseModel):
    """プロジェクト内の個別アイテム（ノート/タスク/ファイル等）。"""

    id: str
    type: str = Field(..., description="アイテム種別（note|task|file|prompt など）")
    title: Optional[str] = None
    content: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProjectModel(BaseModel):
    """内部統一プロジェクトモデル。"""

    id: str = Field(..., description="プロジェクトID（エクスポート由来）")
    name: str = Field(..., description="プロジェクト名")
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    items: List[ProjectItem] = Field(default_factory=list)
    resources: List[ProjectResource] = Field(default_factory=list)
    raw: Dict[str, Any] = Field(default_factory=dict, description="元 JSON の生データ（トレーサビリティ用）")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="補助的なメタデータ（対象, 収益化, 開発情報など）"
    )


class ParseResult(BaseModel):
    """パース結果（成功/警告/エラー情報）。"""

    success: bool
    project: Optional[ProjectModel] = None
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


def _slugify_name(name: str) -> str:
    """名前からファイル名安全なスラッグを生成。

    日本語など CJK 文字はそのまま許容し、空白や記号はハイフンに変換する。
    """
    if not name:
        return ""

    # 空白類をハイフンに
    s = re.sub(r"\s+", "-", name.strip())
    # 許可する文字: 英数/アンダースコア/ハイフン/CJK
    allowed_pattern = re.compile(r"[^\w\-\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+", re.UNICODE)
    s = allowed_pattern.sub("", s)
    # 連続ハイフンの正規化
    s = re.sub(r"-+", "-", s)
    return s.lower()


def _extract_name(d: Dict[str, Any]) -> str:
    return d.get("name") or d.get("title") or d.get("project_name") or "Untitled Project"


def _extract_id(d: Dict[str, Any], derived_name: str) -> str:
    return d.get("id") or d.get("project_id") or d.get("uuid") or _slugify_name(str(derived_name)) or "unknown-project"


def _extract_description(d: Dict[str, Any]) -> Optional[str]:
    return d.get("description") or d.get("summary")


def _parse_raw_items(raw: List[Dict[str, Any]]) -> Tuple[List[ProjectItem], List[str], List[str]]:
    out: List[ProjectItem] = []
    warns: List[str] = []
    errs: List[str] = []
    for idx, item in enumerate(raw):
        try:
            out.append(
                ProjectItem(
                    id=str(item.get("id") or item.get("uuid") or f"item-{idx}"),
                    type=str(item.get("type") or item.get("kind") or "note"),
                    title=item.get("title") or item.get("name"),
                    content=item.get("content") or item.get("body"),
                    created_at=item.get("created_at") or item.get("createdAt"),
                    updated_at=item.get("updated_at") or item.get("updatedAt"),
                    tags=item.get("tags") or [],
                    metadata=item.get("metadata") or {},
                )
            )
        except ValidationError as ve:
            errs.append(f"item[{idx}] validation error: {ve}")
    return out, warns, errs


def _parse_features(d: Dict[str, Any]) -> Tuple[List[ProjectItem], List[str]]:
    out: List[ProjectItem] = []
    warns: List[str] = []
    for idx, feat in enumerate(d.get("features") or []):
        try:
            out.append(ProjectItem(id=f"feature-{idx}", type="feature", title=str(feat)))
        except ValidationError as ve:
            warns.append(f"feature[{idx}] validation warning: {ve}")
    return out, warns


def _parse_goals(d: Dict[str, Any]) -> Tuple[List[ProjectItem], List[str]]:
    out: List[ProjectItem] = []
    warns: List[str] = []
    for idx, goal in enumerate(d.get("goals") or []):
        try:
            out.append(ProjectItem(id=f"goal-{idx}", type="goal", title=str(goal)))
        except ValidationError as ve:
            warns.append(f"goal[{idx}] validation warning: {ve}")
    return out, warns


def _parse_development(d: Dict[str, Any]) -> Tuple[List[ProjectItem], Dict[str, Any], List[str]]:
    out: List[ProjectItem] = []
    warns: List[str] = []
    meta: Dict[str, Any] = {}
    development = d.get("development") or {}
    languages = development.get("languages") or []
    tools = development.get("tools") or []
    if development.get("platform"):
        meta["platform"] = development.get("platform")
    if development.get("status"):
        meta["status"] = development.get("status")
    if languages:
        meta["languages"] = languages
    if tools:
        meta["tools"] = tools
    for idx, lang in enumerate(languages):
        try:
            out.append(ProjectItem(id=f"lang-{idx}", type="tech", title=f"language: {lang}"))
        except ValidationError as ve:
            warns.append(f"language[{idx}] validation warning: {ve}")
    for idx, tool in enumerate(tools):
        try:
            out.append(ProjectItem(id=f"tool-{idx}", type="tech", title=f"tool: {tool}"))
        except ValidationError as ve:
            warns.append(f"tool[{idx}] validation warning: {ve}")
    return out, meta, warns


def _parse_resources(d: Dict[str, Any]) -> Tuple[List[ProjectResource], List[str]]:
    out: List[ProjectResource] = []
    warns: List[str] = []
    for idx, res in enumerate(d.get("resources") or d.get("links") or []):
        try:
            out.append(
                ProjectResource(
                    id=str(res.get("id") or res.get("uuid") or f"res-{idx}"),
                    title=res.get("title") or res.get("name"),
                    url=res.get("url"),
                    kind=res.get("kind") or res.get("type"),
                    metadata=res.get("metadata") or {},
                )
            )
        except ValidationError as ve:
            warns.append(f"resource[{idx}] validation warning: {ve}")
    return out, warns


def _build_project_metadata(d: Dict[str, Any], dev_meta: Dict[str, Any]) -> Dict[str, Any]:
    meta: Dict[str, Any] = {}
    if d.get("target_audience"):
        meta["target_audience"] = d["target_audience"]
    if d.get("monetization"):
        meta["monetization"] = d["monetization"]
    meta.update(dev_meta)
    return meta


def coerce_to_project(data: Dict[str, Any]) -> ParseResult:
    """エクスポート JSON を内部 `ProjectModel` に変換する。"""

    # 1) 基本情報抽出
    warnings: List[str] = []
    errors: List[str] = []
    name = _extract_name(data)
    project_id = _extract_id(data, name)
    description = _extract_description(data)

    # 2) アイテム群の構築
    base_items, w1, e1 = _parse_raw_items(data.get("items") or data.get("notes") or [])
    feature_items, w2 = _parse_features(data)
    goal_items, w3 = _parse_goals(data)
    dev_items, dev_meta, w4 = _parse_development(data)
    items: List[ProjectItem] = [*base_items, *feature_items, *goal_items, *dev_items]
    warnings.extend([*w1, *w2, *w3, *w4])
    errors.extend(e1)

    # 3) リソース
    resources, w5 = _parse_resources(data)
    warnings.extend(w5)

    # 4) メタデータ
    metadata = _build_project_metadata(data, dev_meta)

    # 5) 最終モデル
    try:
        project = ProjectModel(
            id=str(project_id),
            name=str(name),
            description=description,
            created_at=data.get("created_at") or data.get("createdAt"),
            updated_at=data.get("updated_at") or data.get("updatedAt"),
            items=items,
            resources=resources,
            raw=data,
            metadata=metadata,
        )
        return ParseResult(success=True, project=project, warnings=warnings, errors=errors)
    except ValidationError as ve:
        errors.append(f"project validation error: {ve}")
        return ParseResult(success=False, project=None, warnings=warnings, errors=errors)
