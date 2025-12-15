# Archive: Root Scripts

このディレクトリには、プロジェクトのルート直下に存在していた682個のPythonスクリプトが保管されています。

## 移動日時
- **日付**: 2025-12-15
- **理由**: プロジェクト構造のクリーンアップ
- **方針**: 使用頻度に基づいてアーカイブに移動

## 背景

プロジェクトのルート直下に685個のPythonファイルが散在しており、以下の問題がありました：

1. **構造的混乱**: プロジェクトのエントリーポイントが不明瞭
2. **保守性低下**: ファイル検索が困難
3. **LSP/IDE負荷**: 大量のファイルによるインデクサ過負荷

## 移動対象

以下の基準で移動しました：

- **実行可能スクリプト**: `if __name__ == "__main__"` を含むファイル
- **一時的スクリプト**: 開発・メンテナンス用の単発スクリプト
- **除外ファイル**: `test_*.py`, `app.py`（プロジェクトコアファイルのため保持）

## カテゴリ分類

移動されたファイルの主なカテゴリ：

| カテゴリ | 推定数 | 例 |
|---------|-------|-----|
| **advanced** | ~85 | `ultra_think_*.py`, `advanced_*.py` |
| **validation** | ~30 | `check_*.py`, `validate_*.py` |
| **maintenance** | ~25 | `fix_*.py`, `cleanup_*.py` |
| **generation** | ~15 | `generate_*.py`, `add_*.py`, `create_*.py` |
| **migration** | ~10 | `import_*.py`, `export_*.py` |
| **other** | ~450 | 様々な機能スクリプト |

## 使用方法

アーカイブされたスクリプトを使用する場合：

```bash
# 直接実行
python archive/root_scripts/script_name.py

# または、必要に応じてscripts/に移動
mv archive/root_scripts/script_name.py scripts/
```

## 注意事項

- **削除なし**: すべてのファイルが保持されています
- **Git履歴**: 完全なコミット履歴が保存されています
- **復元可能**: 必要に応じて簡単に復元できます

## 関連ドキュメント

- [クリーンアップレポート](../../CLEANUP_REPORT_20251215.md)
- [プロジェクトガイド](../../CLAUDE.md)

---

**Status**: Archived
**Reason**: Project structure cleanup
**Safety**: All files preserved, no data loss
