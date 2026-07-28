"""Wikipediaのダンプファイルから出典ISBNを抽出するツール。"""

__title__ = "Wikipedia Citation Extractor"
__copyright__ = "Copyright (C) 2023 CALIL Inc."
__author__ = "Ryuuji Yoshimoto <ryuuji@calil.jp>"
__version__ = "2.0.0"

from citation.extract import Extractor
from citation.isbn import NormalizedIsbn, normalize_isbn
from citation.record import Exclusion, Record

__all__ = [
    "Exclusion",
    "Extractor",
    "NormalizedIsbn",
    "Record",
    "__version__",
    "normalize_isbn",
]
