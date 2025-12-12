#!/usr/bin/env python3
"""
アーティスト名を公式表記に復元するスクリプト

カタカナ等に誤変換されたアーティスト名を、公式の英字表記に戻す。
監査用に元の表記はname_rawに保存。

使用方法:
    python scripts/restore_official_artist_names.py --dry-run
    python scripts/restore_official_artist_names.py --execute
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"

# 公式名マッピング
# 根拠: Wikipedia日本語版・英語版、公式サイト、音楽配信サービス
OFFICIAL_NAME_MAP = {
    # === 既知の要修正（タスク指定）===
    "ガクト": {
        "official": "GACKT",
        "source": "https://ja.wikipedia.org/wiki/GACKT",
        "confidence": "高",
        "note": "公式表記は大文字のGACKT",
    },
    "ミーシャ": {
        "official": "MISIA",
        "source": "https://ja.wikipedia.org/wiki/MISIA",
        "confidence": "高",
        "note": "公式表記は大文字のMISIA",
    },
    "バウンディ": {
        "official": "Vaundy",
        "source": "https://ja.wikipedia.org/wiki/Vaundy",
        "confidence": "高",
        "note": "公式表記はVaundy",
    },
    "エメ": {
        "official": "Aimer",
        "source": "https://ja.wikipedia.org/wiki/Aimer",
        "confidence": "高",
        "note": "公式表記はAimer",
    },
    "ハー": {
        "official": "H.E.R.",
        "source": "https://en.wikipedia.org/wiki/H.E.R.",
        "confidence": "高",
        "note": "アメリカのR&Bシンガー、公式表記はH.E.R.（ドット含む）",
    },
    "アイコ": {
        "official": "aiko",
        "source": "https://ja.wikipedia.org/wiki/Aiko",
        "confidence": "高",
        "note": "公式表記は小文字のaiko",
    },
    # === 追加検出（公式名が英字）===
    "トーフビーツ": {
        "official": "tofubeats",
        "source": "https://ja.wikipedia.org/wiki/Tofubeats",
        "confidence": "高",
        "note": "公式表記は小文字のtofubeats",
    },
    "ハイド": {
        "official": "hyde",
        "source": "https://ja.wikipedia.org/wiki/Hyde",
        "confidence": "高",
        "note": "L'Arc〜en〜Cielのボーカル、公式表記は小文字のhyde",
    },
    "ヨシキ": {
        "official": "YOSHIKI",
        "source": "https://ja.wikipedia.org/wiki/YOSHIKI",
        "confidence": "高",
        "note": "X JAPANのドラマー、公式表記は大文字のYOSHIKI",
    },
    "クレバ": {
        "official": "KREVA",
        "source": "https://ja.wikipedia.org/wiki/KREVA",
        "confidence": "高",
        "note": "公式表記は大文字のKREVA",
    },
    "アド": {
        "official": "Ado",
        "source": "https://ja.wikipedia.org/wiki/Ado",
        "confidence": "高",
        "note": "公式表記はAdo",
    },
    "リサ": {
        "official": "LiSA",
        "source": "https://ja.wikipedia.org/wiki/LiSA",
        "confidence": "高",
        "note": "公式表記はLiSA（iは小文字）",
    },
    "アヤセ": {
        "official": "Ayase",
        "source": "https://ja.wikipedia.org/wiki/Ayase_(音楽家)",
        "confidence": "高",
        "note": "YOASOBIのコンポーザー、公式表記はAyase",
    },
    "エイウィッチ": {
        "official": "Awich",
        "source": "https://ja.wikipedia.org/wiki/Awich",
        "confidence": "高",
        "note": "沖縄出身のラッパー、公式表記はAwich",
    },
    "バッドホップ": {
        "official": "BAD HOP",
        "source": "https://ja.wikipedia.org/wiki/BAD_HOP",
        "confidence": "高",
        "note": "川崎のヒップホップグループ、公式表記はBAD HOP",
    },
    "ダパンプ": {
        "official": "DA PUMP",
        "source": "https://ja.wikipedia.org/wiki/DA_PUMP",
        "confidence": "高",
        "note": "公式表記はDA PUMP",
    },
    "アールエム": {
        "official": "RM",
        "source": "https://ja.wikipedia.org/wiki/RM_(ラッパー)",
        "confidence": "高",
        "note": "BTSのリーダー、公式表記はRM",
    },
    "ジス": {
        "official": "JISOO",
        "source": "https://ja.wikipedia.org/wiki/ジス_(歌手)",
        "confidence": "高",
        "note": "BLACKPINKのメンバー、公式表記はJISOO",
    },
    "ナヨン": {
        "official": "NAYEON",
        "source": "https://ja.wikipedia.org/wiki/ナヨン",
        "confidence": "高",
        "note": "TWICEのメンバー、公式表記はNAYEON",
    },
    "タカヒロ": {
        "official": "TAKAHIRO",
        "source": "https://ja.wikipedia.org/wiki/TAKAHIRO_(歌手)",
        "confidence": "高",
        "note": "EXILEのボーカル、公式表記はTAKAHIRO",
    },
    "DJクラッシュ": {
        "official": "DJ Krush",
        "source": "https://ja.wikipedia.org/wiki/DJ_Krush",
        "confidence": "高",
        "note": "公式表記はDJ Krush",
    },
    "ケンゾー": {
        "official": "KENZO",
        "source": "https://ja.wikipedia.org/wiki/KENZO_(ダンサー)",
        "confidence": "高",
        "note": "DA PUMPのメンバー、公式表記はKENZO",
    },
    "ミキコ": {
        "official": "MIKIKO",
        "source": "https://ja.wikipedia.org/wiki/MIKIKO_(振付師)",
        "confidence": "高",
        "note": "振付師・演出家、公式表記はMIKIKO",
    },
    # === 要確認（複数候補あり）===
    "ヒカル": {
        "official": "Hikaru",
        "source": "https://ja.wikipedia.org/wiki/ヒカル_(YouTuber)",
        "confidence": "中",
        "note": "YouTuber。宇多田ヒカルとは別人。要確認",
    },
    "コー": {
        "official": "KO",
        "source": "",
        "confidence": "低",
        "note": "特定困難。要確認",
    },
    "サム": {
        "official": "SAM",
        "source": "https://ja.wikipedia.org/wiki/SAM_(ダンサー)",
        "confidence": "高",
        "note": "TRFのダンサー、公式表記はSAM",
    },
}


def main():
    parser = argparse.ArgumentParser(description="アーティスト名を公式表記に復元")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン（変更なし）")
    parser.add_argument("--execute", action="store_true", help="実行")
    parser.add_argument("--high-confidence-only", action="store_true", help="高信頼度のみ")
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        args.dry_run = True

    print("=" * 70)
    print(f"🎵 アーティスト名公式表記復元 ({'dry-run' if args.dry_run else '実行'})")
    print("=" * 70)

    # データ読み込み
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"📂 CSV読み込み: {CSV_PATH}")
    print(f"  レコード数: {len(df)}件")

    # 修正対象を検出
    changes = []
    for katakana, info in OFFICIAL_NAME_MAP.items():
        if args.high_confidence_only and info["confidence"] != "高":
            continue

        mask = df["person_name"] == katakana
        count = mask.sum()

        if count > 0:
            # 既に公式名が存在するか確認
            official_exists = (df["person_name"] == info["official"]).sum()

            changes.append(
                {
                    "katakana": katakana,
                    "official": info["official"],
                    "count": count,
                    "confidence": info["confidence"],
                    "source": info["source"],
                    "note": info["note"],
                    "official_exists": official_exists,
                    "indices": df[mask].index.tolist(),
                }
            )

    # 集計表示
    print(f"\n🔍 修正対象: {len(changes)}人")
    print()

    total_episodes = 0
    duplicates = 0

    print("=" * 70)
    print(f"{'カタカナ':<15} {'→':<3} {'公式名':<15} {'件数':<6} {'信頼度':<6} {'重複':<6}")
    print("-" * 70)
    for c in changes:
        dup_flag = f"⚠️{c['official_exists']}件" if c["official_exists"] > 0 else ""
        print(f"{c['katakana']:<15} → {c['official']:<15} {c['count']:<6} {c['confidence']:<6} {dup_flag}")
        total_episodes += c["count"]
        if c["official_exists"] > 0:
            duplicates += 1

    print("-" * 70)
    print(f"合計: {total_episodes}件のエピソード、{duplicates}件の重複")
    print("=" * 70)

    if args.dry_run:
        print("\n⚠️ ドライラン: 変更は保存されません")
        print("\n【根拠URL一覧】")
        for c in changes:
            if c["source"]:
                print(f"  {c['katakana']} → {c['official']}: {c['source']}")

        # レポート出力
        report = {
            "timestamp": datetime.now().isoformat(),
            "mode": "dry-run",
            "total_changes": len(changes),
            "total_episodes": total_episodes,
            "duplicates": duplicates,
            "changes": changes,
        }
        report_path = REPORTS_DIR / f"artist_name_restore_dryrun_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n📄 レポート: {report_path}")
        return

    # 実行モード
    print("\n🔄 公式名に復元中...")

    results = []
    for c in changes:
        for idx in c["indices"]:
            old_name = df.loc[idx, "person_name"]

            # name_rawに元の表記を保存（まだ設定されていない場合）
            if pd.isna(df.loc[idx, "name_raw"]) or df.loc[idx, "name_raw"] == "":
                df.loc[idx, "name_raw"] = old_name

            # 公式名に更新
            df.loc[idx, "person_name"] = c["official"]

            results.append(
                {
                    "episode_id": df.loc[idx, "episode_id"],
                    "old_name": old_name,
                    "new_name": c["official"],
                    "confidence": c["confidence"],
                    "source": c["source"],
                }
            )

        print(f"  ✅ {c['katakana']} → {c['official']}: {c['count']}件")

    # 保存
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"\n💾 CSV更新完了: {CSV_PATH}")

    # レポート
    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": "execute",
        "total_changes": len(changes),
        "total_episodes": len(results),
        "results": results,
    }

    report_path = REPORTS_DIR / f"artist_name_restore_executed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"📄 レポート: {report_path}")

    print(f"\n✅ 完了: {len(results)}件を公式名に復元")


if __name__ == "__main__":
    main()
