"""抽出結果のレコードと、その出力形式。"""

import json
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Record:
    """抽出された出典ISBN1件分。"""

    isbn: str
    """正規化されたISBN（ISBN-10）。変換できなかった場合は空文字。"""

    raw: str
    """本文に書かれていた元の表記。"""

    title: str
    """Wikipediaのページ名。"""

    score: float
    """ISBN表記としての確からしさに、出典らしさの補正を加えた値。

    採用するかどうかの判定は補正前の値で済んでいるため、著作一覧の見出しによる
    減点を受けたレコードは採用の閾値（1.0）を下回ることがある。
    """

    h1: str | None
    """ISBNが現れた位置の見出し1。"""

    h2: str | None
    """ISBNが現れた位置の見出し2。"""

    is_ref: bool
    """出典であることが明記されているか。"""

    def to_json(self) -> str:
        """Line-delimited JSONの1行分に変換する。"""
        return json.dumps(
            {
                "isbn": self.isbn,
                "raw": self.raw,
                "title": self.title,
                "score": self.score,
                "h1": self.h1,
                "h2": self.h2,
                "is_ref": self.is_ref,
            },
            ensure_ascii=False,
        )


@dataclass(frozen=True, slots=True)
class Exclusion:
    """スコアが閾値に届かず採用されなかった候補。--show-exclusion で表示する。"""

    pattern: str
    prefix: str
    isbn: str
    title: str
    score: float

    def format(self) -> str:
        """1行のテキストに整形する。"""
        return " ".join([self.pattern, self.prefix, self.isbn, self.title, str(self.score)])
