#!/usr/bin/env python3
"""
Wikidata同名曖昧性解決モジュール。

limit=1の誤採用問題を解決するため、複数候補を取得して
P31（instance of）やoccupation等で正しいエンティティを選択する。

主な機能:
- 候補を複数取得（limit=10）
- P31でhuman/fictional characterをフィルタ
- 確信度スコアで最適な候補を選択
"""

import time
from dataclasses import dataclass
from typing import Optional

import requests

# レート制限用
_last_request_time = 0.0
REQUEST_INTERVAL = 0.2  # 5 req/sec


def _rate_limit() -> None:
    """レート制限を適用"""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < REQUEST_INTERVAL:
        time.sleep(REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


# Wikidata定数
Q_HUMAN = "Q5"  # instance of: human
Q_FICTIONAL_CHARACTER = "Q95074"  # instance of: fictional character
Q_FICTIONAL_HUMAN = "Q15632617"  # instance of: fictional human

# 架空キャラクターとして扱うべきタイプ（Q95074のサブタイプ含む）
FICTIONAL_TYPES = {
    "Q95074",  # fictional character
    "Q15632617",  # fictional human
    "Q15773317",  # television character
    "Q3658341",  # literary character
    "Q1114461",  # comics character
    "Q19180675",  # film character
    "Q89050913",  # animated character
    "Q15711870",  # video game character
    "Q20086263",  # television series regular cast member (fictional)
    "Q20086260",  # literary character from a series
    "Q76388782",  # fictional creature
    "Q80447738",  # animated film character
    "Q118247723",  # anime/manga character
    "Q123126876",  # Disney character
}

# 除外すべきエンティティタイプ
EXCLUDE_TYPES = {
    "Q11424",  # film（映画）
    "Q5398426",  # television series（テレビシリーズ）
    "Q7725634",  # literary work（文学作品）
    "Q482994",  # album（アルバム）
    "Q134556",  # single（シングル）
    "Q7889",  # video game（ビデオゲーム）
    "Q6881511",  # enterprise（企業）
    "Q4830453",  # business（ビジネス）
    "Q43229",  # organization（組織）
    "Q6256",  # country（国）
    "Q515",  # city（都市）
    "Q16521",  # taxon（分類群 - 生物学的分類）
    # 追加: 基本概念・動物・地理関連
    "Q729",  # animal（動物）
    "Q12136",  # disease（病気）
    "Q82794",  # geographic region（地理的地域）
    "Q7275",  # state（州）
    "Q3624078",  # sovereign state（主権国家）
    "Q5119",  # capital city（首都）
    "Q18786",  # continent（大陸）
    "Q8502",  # mountain（山）
    "Q4022",  # river（川）
    "Q23397",  # lake（湖）
    "Q523",  # star（恒星）
    "Q634",  # planet（惑星）
    "Q1457376",  # musical ensemble（音楽グループ）
    "Q215380",  # band（バンド）
    "Q483501",  # musical artist（ミュージシャン名義）
    "Q488111",  # chemical element（化学元素）
    "Q11862829",  # academic discipline（学問分野）
    "Q9174",  # religion（宗教）
}

# Q番号が小さい場合は基本概念の可能性が高い
# 例: Q1=宇宙、Q5=人間、Q114=ケニア、Q140=ライオン、Q199=1
BASIC_CONCEPT_QID_THRESHOLD = 1000


@dataclass
class WikidataCandidate:
    """Wikidata候補エンティティ"""

    qid: str
    label: str
    description: str
    sitelinks: int
    instance_of: list[str]  # P31の値リスト
    occupation: list[str]  # P106の値リスト（あれば）
    confidence: float = 0.0
    rejection_reason: Optional[str] = None


@dataclass
class DisambiguationResult:
    """曖昧性解決結果"""

    success: bool
    selected_qid: Optional[str]
    selected_label: Optional[str]
    sitelinks: int
    confidence: float
    candidates_count: int
    rejection_reason: Optional[str] = None
    all_candidates: list[WikidataCandidate] = None


def search_wikidata_candidates(
    name: str,
    lang: str = "ja",
    limit: int = 10,
    timeout: float = 10.0,
) -> list[dict]:
    """
    人物名からWikidata候補を複数取得。

    Args:
        name: 検索名
        lang: 検索言語
        limit: 取得件数上限
        timeout: タイムアウト秒数

    Returns:
        候補リスト: [{"id": "Q...", "label": "...", "description": "..."}, ...]
    """
    _rate_limit()

    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbsearchentities",
        "search": name,
        "language": lang,
        "format": "json",
        "limit": limit,
        "type": "item",
    }
    headers = {"User-Agent": "FameScoreBot/3.0 (disambiguation)"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        if response.status_code != 200:
            return []

        data = response.json()
        return data.get("search", [])
    except (requests.RequestException, ValueError):
        return []


def get_entity_details(
    qid: str,
    timeout: float = 10.0,
) -> Optional[dict]:
    """
    Wikidata IDからエンティティ詳細を取得。

    Args:
        qid: Wikidata ID（例: "Q312"）
        timeout: タイムアウト秒数

    Returns:
        エンティティ情報（P31, P106, sitelinks等）
    """
    _rate_limit()

    url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
    headers = {"User-Agent": "FameScoreBot/3.0 (disambiguation)"}

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code != 200:
            return None

        data = response.json()
        entity = data.get("entities", {}).get(qid, {})

        # P31 (instance of) を取得
        claims = entity.get("claims", {})
        p31_claims = claims.get("P31", [])
        instance_of = []
        for claim in p31_claims:
            mainsnak = claim.get("mainsnak", {})
            datavalue = mainsnak.get("datavalue", {})
            if datavalue.get("type") == "wikibase-entityid":
                instance_of.append(datavalue.get("value", {}).get("id", ""))

        # P106 (occupation) を取得
        p106_claims = claims.get("P106", [])
        occupation = []
        for claim in p106_claims:
            mainsnak = claim.get("mainsnak", {})
            datavalue = mainsnak.get("datavalue", {})
            if datavalue.get("type") == "wikibase-entityid":
                occupation.append(datavalue.get("value", {}).get("id", ""))

        # sitelinks数
        sitelinks = entity.get("sitelinks", {})

        # ラベル・説明
        labels = entity.get("labels", {})
        descriptions = entity.get("descriptions", {})

        return {
            "qid": qid,
            "instance_of": instance_of,
            "occupation": occupation,
            "sitelinks": len(sitelinks),
            "label_ja": labels.get("ja", {}).get("value", ""),
            "label_en": labels.get("en", {}).get("value", ""),
            "description_ja": descriptions.get("ja", {}).get("value", ""),
            "description_en": descriptions.get("en", {}).get("value", ""),
        }
    except (requests.RequestException, ValueError):
        return None


def is_basic_concept_qid(qid: str) -> bool:
    """
    Q番号が小さい（基本概念の可能性が高い）かチェック。

    例: Q114=ケニア、Q140=ライオン、Q199=1
    """
    try:
        qnum = int(qid[1:])  # "Q140" -> 140
        return qnum < BASIC_CONCEPT_QID_THRESHOLD
    except (ValueError, IndexError):
        return False


def is_valid_person_type(
    instance_of: list[str],
    expected_type: str = "REAL",
    qid: str = None,
) -> tuple[bool, str]:
    """
    P31の値から有効な人物タイプか判定。

    Args:
        instance_of: P31の値リスト
        expected_type: "REAL" または "FICTIONAL"
        qid: WikidataのQ番号（基本概念チェック用）

    Returns:
        (有効か, 拒否理由)
    """
    # Q番号が非常に小さい場合は基本概念の可能性（Q1=宇宙、Q5=人間を除く）
    if qid and qid not in ("Q5", Q_HUMAN):
        if is_basic_concept_qid(qid):
            # 基本概念の可能性があるが、P31がhumanなら許可
            if Q_HUMAN not in instance_of:
                return False, f"basic_concept:{qid}"

    # 除外タイプに該当する場合
    for inst_qid in instance_of:
        if inst_qid in EXCLUDE_TYPES:
            return False, f"excluded_type:{inst_qid}"

    # humanかどうか
    is_human = Q_HUMAN in instance_of

    # fictional characterかどうか（拡張タイプセットで判定）
    is_fictional = bool(set(instance_of) & FICTIONAL_TYPES)

    if expected_type == "REAL":
        if is_human and not is_fictional:
            return True, ""
        elif is_fictional:
            return False, "is_fictional"
        elif not is_human:
            return False, "not_human"
    elif expected_type == "FICTIONAL":
        if is_fictional:
            return True, ""
        elif is_human:
            # 実在人物だが、架空キャラクターとして登録されている可能性
            return False, "is_real_human"
        else:
            # human/fictionalどちらでもない
            return False, "not_character"

    return False, "unknown_type"


def calculate_confidence(
    candidate: WikidataCandidate,
    search_name: str,
    expected_type: str = "REAL",
) -> float:
    """
    候補の確信度を計算。

    スコア構成:
    - タイプ一致（human/fictional）: +50点
    - 名前完全一致: +30点
    - sitelinks高い（>50）: +10点
    - 説明文あり: +10点

    Args:
        candidate: 候補エンティティ
        search_name: 検索名
        expected_type: "REAL" または "FICTIONAL"

    Returns:
        確信度スコア（0-100）
    """
    score = 0.0

    # タイプ一致判定
    is_valid, _ = is_valid_person_type(candidate.instance_of, expected_type)
    if is_valid:
        score += 50.0

    # 名前一致判定
    label_lower = candidate.label.lower().replace(" ", "").replace("　", "")
    name_lower = search_name.lower().replace(" ", "").replace("　", "")
    if label_lower == name_lower:
        score += 30.0
    elif name_lower in label_lower or label_lower in name_lower:
        score += 15.0

    # sitelinkスコア
    if candidate.sitelinks >= 50:
        score += 10.0
    elif candidate.sitelinks >= 20:
        score += 5.0

    # 説明文あり
    if candidate.description:
        score += 10.0

    return min(score, 100.0)


def get_min_confidence_for_name(name: str, person_type: str) -> float:
    """
    名前の長さとタイプに基づいて最低確信度を決定。

    短い名前（≤3文字）は誤マッチのリスクが高いため、閾値を引き上げる。
    """
    # Unicode文字数でカウント（日本語対応）
    name_len = len(name.strip())

    if name_len <= 2:
        # 非常に短い名前（例: "ONE", "ジジ"）は最も厳格
        return 85.0
    elif name_len <= 3:
        # 短い名前（例: "ken"）は厳格
        return 75.0
    elif person_type == "FICTIONAL":
        # 架空キャラクターは中程度
        return 60.0
    else:
        # デフォルト
        return 50.0


def disambiguate_person(
    name: str,
    person_type: str = "REAL",
    lang: str = "ja",
    min_confidence: float = None,
    work_title: str = None,
) -> DisambiguationResult:
    """
    人物名からWikidataエンティティを曖昧性解決して選択。

    Args:
        name: 人物名
        person_type: "REAL" または "FICTIONAL"
        lang: 検索言語
        min_confidence: 最低確信度（Noneの場合は名前長から自動決定）
        work_title: 作品名（架空キャラの場合、検索クエリに追加）

    Returns:
        DisambiguationResult
    """
    # 最低確信度を決定
    if min_confidence is None:
        min_confidence = get_min_confidence_for_name(name, person_type)

    # 架空キャラクターで作品名がある場合、検索クエリに追加
    search_query = name
    if person_type == "FICTIONAL" and work_title and work_title not in ("未登録", ""):
        search_query = f"{name} {work_title}"

    # 候補を取得
    raw_candidates = search_wikidata_candidates(search_query, lang=lang, limit=10)

    if not raw_candidates:
        return DisambiguationResult(
            success=False,
            selected_qid=None,
            selected_label=None,
            sitelinks=0,
            confidence=0,
            candidates_count=0,
            rejection_reason="no_candidates",
        )

    # 各候補の詳細を取得
    candidates: list[WikidataCandidate] = []
    for raw in raw_candidates:
        qid = raw.get("id", "")
        if not qid:
            continue

        details = get_entity_details(qid)
        if not details:
            continue

        candidate = WikidataCandidate(
            qid=qid,
            label=raw.get("label", ""),
            description=raw.get("description", ""),
            sitelinks=details["sitelinks"],
            instance_of=details["instance_of"],
            occupation=details["occupation"],
        )

        # タイプチェック（Q番号も渡す）
        is_valid, reason = is_valid_person_type(candidate.instance_of, person_type, qid=qid)
        if not is_valid:
            candidate.rejection_reason = reason
            candidate.confidence = 0
        else:
            candidate.confidence = calculate_confidence(candidate, name, person_type)

        candidates.append(candidate)

    if not candidates:
        return DisambiguationResult(
            success=False,
            selected_qid=None,
            selected_label=None,
            sitelinks=0,
            confidence=0,
            candidates_count=0,
            rejection_reason="no_valid_candidates",
        )

    # 確信度でソート
    candidates.sort(key=lambda c: c.confidence, reverse=True)
    best = candidates[0]

    # 最低確信度チェック
    if best.confidence < min_confidence:
        return DisambiguationResult(
            success=False,
            selected_qid=None,
            selected_label=None,
            sitelinks=0,
            confidence=best.confidence,
            candidates_count=len(candidates),
            rejection_reason=f"low_confidence:{best.confidence:.1f}",
            all_candidates=candidates,
        )

    return DisambiguationResult(
        success=True,
        selected_qid=best.qid,
        selected_label=best.label,
        sitelinks=best.sitelinks,
        confidence=best.confidence,
        candidates_count=len(candidates),
        all_candidates=candidates,
    )


def main():
    """テスト実行"""
    test_cases = [
        # (name, expected_type, expected_qid_or_fail)
        ("ken", "REAL", "L'Arc~en~Cielのギタリストを期待"),
        ("ONE", "REAL", "漫画家を期待"),
        ("バンビ", "FICTIONAL", "キャラクターを期待"),
        ("ジジ", "FICTIONAL", "魔女の宅急便の猫を期待"),
        ("大谷翔平", "REAL", "野球選手を期待"),
        ("ドナルド・トランプ", "REAL", "政治家を期待"),
    ]

    print("=== Wikidata同名曖昧性解決テスト ===\n")

    for name, person_type, expected in test_cases:
        print(f"検索: {name} (type={person_type})")
        print(f"期待: {expected}")

        result = disambiguate_person(name, person_type=person_type)

        if result.success:
            print(f"  ✓ 成功: {result.selected_qid} ({result.selected_label})")
            print(f"    sitelinks: {result.sitelinks}, 確信度: {result.confidence:.1f}")
        else:
            print(f"  ✗ 失敗: {result.rejection_reason}")
            if result.all_candidates:
                print(f"    候補数: {len(result.all_candidates)}")
                for c in result.all_candidates[:3]:
                    status = c.rejection_reason or f"conf={c.confidence:.1f}"
                    print(f"      - {c.qid}: {c.label} ({status})")

        print()


if __name__ == "__main__":
    main()
