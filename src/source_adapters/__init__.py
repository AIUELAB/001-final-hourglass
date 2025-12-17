"""
Source Adapters - 人物候補収集システム

このパッケージは様々なソースから人物候補を収集するためのアダプタを提供します。

利用可能なアダプタ:
- ManualSourceAdapter: 手動作成CSVファイル
- NHKAsadoraAdapter: NHK朝ドラモデル人物
"""

from src.source_adapters.base import PersonCandidate, SourceAdapter
from src.source_adapters.manual_adapter import ManualSourceAdapter
from src.source_adapters.nhk_asadora_adapter import NHKAsadoraAdapter

__all__ = [
    "PersonCandidate",
    "SourceAdapter",
    "ManualSourceAdapter",
    "NHKAsadoraAdapter",
]
