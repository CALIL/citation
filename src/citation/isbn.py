"""ISBN表記の抽出と正規化。

Wikipediaの本文には様々な表記でISBNが書かれているため、正規表現で候補を拾った上で
チェックデジットの検証と桁数の調整を行い、どのくらい確からしいかをスコアで表す。
スコアが1.0以上のものだけを抽出結果として採用する。
"""

import re
from dataclasses import dataclass

import isbnlib

#: ISBN候補を拾う正規表現。前半がISBNを示す接頭辞、後半が数字列。
#:
#: 接頭辞の並び順はそのまま優先順位になる。長いものを先に置かないと
#: "ISBN-10 " が "ISBN-" として解釈されてしまうため、並べ替えないこと。
ISBN_RE = re.compile(
    r"((?:ISBN10 |ISBN13 |ISBN　|isbn=|ISBN  |isbn = |ISBN-10 |ISBN-13 |ISBN：|ISBN-|ISBN |ISBN)?)"
    r"([0-9][0-9\- ]{8,20}[0-9Xx])"
)

#: 桁数からも接頭辞からも正体を判定できなかった候補につけるパターン名。
UNKNOWN = "?"

#: 採用の閾値。これ未満のスコアは抽出結果に含めない。
ADOPTION_THRESHOLD = 1.0


@dataclass(frozen=True)
class NormalizedIsbn:
    """正規化されたISBNと、その判定根拠。"""

    isbn: str
    """正規化後のISBN。判定できなかった場合は入力のまま。"""

    pattern: str
    """どの桁数パターンとして解釈したか。判定できなかった場合は ``UNKNOWN``。"""

    score: float
    """ISBNらしさ。``ADOPTION_THRESHOLD`` 以上なら採用する。"""

    @property
    def adopted(self) -> bool:
        """抽出結果として採用する水準に達しているか。"""
        return self.score >= ADOPTION_THRESHOLD


def normalize_isbn(prefix: str, raw: str) -> NormalizedIsbn:
    """ISBN候補を正規化し、確からしさのスコアをつける。

    :param prefix: 数字列の直前にあったISBNの接頭辞（無い場合は空文字）
    :param raw: 本文から拾った数字列（ハイフンやスペースを含みうる）
    """
    score = 0.0
    isbn = raw.replace("-", "")
    isbn = isbn.replace(" ", "")
    isbn = isbn.replace("x", "X")

    # "ISBN-104772212272" のように、"ISBN-10" と本体が区切られずに書かれたケース。
    # 接頭辞として "ISBN-" までしか切り出せないので、残った "10" を捨てる。
    if prefix == "ISBN-" and len(isbn) == 12 and isbn[0:2] == "10" and isbn[2] == "4":
        isbn = isbn[2:12]

    pattern = UNKNOWN
    length = len(isbn)

    if prefix:  # ISBNの記述があった場合は信頼
        score += 0.9

    # "978" を重ねて書いてしまった16桁。先頭の3桁を捨てるとISBN-13になる。
    # NOTE: 実データでこの表記は見つかっていない（jawiki 3,000ページと
    # enwiki 49,965ページの16桁候補2,596件を調べて0件）。
    if length == 16 and isbn.startswith("978978") and isbnlib.is_isbn13(isbn[3:16]):
        pattern = "I13(978978Cut)"
        score += 0.5
        isbn = isbn[3:16]
    elif length == 10:
        if isbnlib.is_isbn10(isbn):
            pattern = "I10"
            score += 0.5
            if isbn.startswith("4"):  # 日本の出版物
                score += 1.0
            if isbn.endswith("X"):  # チェックデジットがXなら偶然の一致ではない
                score += 0.5
        elif "X" not in isbn and isbnlib.is_isbn13("978" + isbn):
            # ISBN-13の "978" が欠けた表記
            pattern = "I13(978+)"
            isbn = "978" + isbn
            score += 1.0
    elif length == 13:
        if isbn.startswith("491"):
            pattern = "雑誌コード"
            score = -1
        elif (
            (isbn.startswith("978") or isbn.startswith("977"))
            and "X" not in isbn
            and isbnlib.is_isbn13(isbn)
        ):
            pattern = "I13"
            score += 1.0
        elif isbnlib.is_isbn10(isbn[3:]):
            # 先頭3桁が余分に付いたISBN-10
            isbn = isbn[3:]
            pattern = "I10(978-)"
            score += 0.5
    elif length == 11 and isbn[0] == "8" and isbnlib.is_isbn13("97" + isbn):
        # ISBN-13の "97" が欠けた表記
        isbn = "97" + isbn
        pattern = "I13(97+)"
        score += 0.5
    elif (
        length > 13 and isbn.startswith("978") and "X" not in isbn and isbnlib.is_isbn13(isbn[0:13])
    ):
        # 末尾に余分な数字が続くISBN-13
        pattern = "I13(Cut13)"
        isbn = isbn[0:13]
        score += 0.5
    elif length > 13 and isbn.startswith("978") and isbnlib.is_isbn10(isbn[3:13]):
        # "978" が付いた上に末尾も余分なISBN-10
        isbn = isbn[3:13]
        pattern = "I10(Cut13_978-)"
        score += 0.5
    elif length > 10 and isbnlib.is_isbn10(isbn[0:10]):
        # 末尾に余分な数字が続くISBN-10
        isbn = isbn[0:10]
        pattern = "I10(Cut10)"
        score += 0.5
    elif length > 10 and isbnlib.is_isbn13("978" + isbn[0:10]):
        isbn = "978" + isbn[0:10]
        pattern = "I13(Cut10_978+)"
        score += 0.5
    elif length == 9 and isbnlib.is_isbn10("4" + isbn):
        # 先頭の "4" が落ちた日本の出版物
        isbn = "4" + isbn
        pattern = "I10(4+)"
        score += 0.5

    return NormalizedIsbn(isbn=isbn, pattern=pattern, score=score)


def find_isbn_candidates(line: str) -> list[tuple[str, str]]:
    """行からISBN候補を (接頭辞, 数字列) の組で拾い出す。"""
    return ISBN_RE.findall(line)


def to_isbn10(isbn: str) -> str:
    """ISBN-10に正規化する。変換できない場合は空文字。

    isbnlibの ``to_isbn10()`` は先頭3文字が "978" かどうかだけでISBN-13と判断する。
    そのため "9784062577" のような978で始まる正当なISBN-10を渡すと、ISBN-13として
    検証に失敗して空文字を返してしまう。先にISBN-10かどうかを確かめる。
    """
    if isbnlib.is_isbn10(isbn):
        return isbn
    return isbnlib.to_isbn10(isbn)
