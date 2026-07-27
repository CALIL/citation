"""ISBN正規化の各分岐を検証する。

桁数パターンごとの判定はこのツールの中核だが、長らく一度も検証されないまま
本番の出力に反映されていた。ここで全パターンを固定する。
"""

import pytest

from citation.isbn import UNKNOWN, find_isbn_candidates, normalize_isbn, to_isbn10

#: (本文の表記, 期待するパターン名, 期待するISBN, 期待するスコア)
#: スコアは接頭辞 "ISBN " があることによる +0.9 を含む。
PATTERNS = [
    ("4-7722-1227-2", "I10", "4772212272", 2.4),
    ("4-00-000008-X", "I10", "400000008X", 2.9),
    ("978-4-7722-1227-4", "I13", "9784772212274", 1.9),
    ("4772212274", "I13(978+)", "9784772212274", 1.9),
    ("1234772212272", "I10(978-)", "4772212272", 1.4),
    ("84772212274", "I13(97+)", "9784772212274", 1.4),
    ("97847722122740", "I13(Cut13)", "9784772212274", 1.4),
    ("978477221227200", "I10(Cut13_978-)", "4772212272", 1.4),
    ("477221227200", "I10(Cut10)", "4772212272", 1.4),
    ("477221227400", "I13(Cut10_978+)", "9784772212274", 1.4),
    ("772-212272", "I10(4+)", "4772212272", 1.4),
    ("9789784772212274", "I13(978978Cut)", "9784772212274", 1.4),
    ("4910123456789", "雑誌コード", "4910123456789", -1),
]


@pytest.mark.parametrize(("raw", "pattern", "isbn", "score"), PATTERNS)
def test_各パターンが判定される(raw: str, pattern: str, isbn: str, score: float) -> None:
    result = normalize_isbn("ISBN ", raw)
    assert result.pattern == pattern
    assert result.isbn == isbn
    assert result.score == pytest.approx(score)


def test_全パターンを網羅している() -> None:
    """PATTERNSが取りこぼしなく分岐を覆っていること。"""
    covered = {pattern for _, pattern, _, _ in PATTERNS}
    assert covered == {
        "I10",
        "I13",
        "I13(978+)",
        "I13(978978Cut)",
        "I10(978-)",
        "I13(97+)",
        "I13(Cut13)",
        "I10(Cut13_978-)",
        "I10(Cut10)",
        "I13(Cut10_978+)",
        "I10(4+)",
        "雑誌コード",
    }


def test_接頭辞がないとスコアが0_9低い() -> None:
    with_prefix = normalize_isbn("ISBN ", "4-7722-1227-2")
    without_prefix = normalize_isbn("", "4-7722-1227-2")
    assert without_prefix.pattern == with_prefix.pattern
    assert without_prefix.score == pytest.approx(with_prefix.score - 0.9)


def test_区切りなしのISBN_10表記を救済する() -> None:
    """ "ISBN-104772212272" のように接頭辞と本体が地続きのケース。"""
    result = normalize_isbn("ISBN-", "104772212272")
    assert result.pattern == "I10"
    assert result.isbn == "4772212272"


def test_チェックデジットが不正なら採用しない() -> None:
    result = normalize_isbn("ISBN ", "4-7722-1227-3")
    assert result.pattern == UNKNOWN
    assert not result.adopted


def test_雑誌コードは採用しない() -> None:
    assert not normalize_isbn("ISBN ", "4910123456789").adopted


def test_978で始まるISBN10はそのまま返す() -> None:
    """isbnlibのto_isbn10()は先頭3文字だけでISBN-13と誤認する（KNOWN_ISSUES.md 参照）。"""
    assert to_isbn10("9784062577") == "9784062577"


@pytest.mark.parametrize(
    ("isbn", "expected"),
    [
        ("9784772212274", "4772212272"),  # ISBN-13から変換
        ("4772212272", "4772212272"),  # すでにISBN-10
        ("400000008X", "400000008X"),  # チェックデジットがX
        ("9771234567003", ""),  # ISBNではない（雑誌のバーコード）
    ],
)
def test_isbn10への正規化(isbn: str, expected: str) -> None:
    assert to_isbn10(isbn) == expected


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("* ISBN 4-7722-1227-2", [("ISBN ", "4-7722-1227-2")]),
        ("* isbn=4-7722-1227-2", [("isbn=", "4-7722-1227-2")]),
        ("* ISBN：4-7722-1227-2", [("ISBN：", "4-7722-1227-2")]),
        ("* ISBN　4-7722-1227-2", [("ISBN　", "4-7722-1227-2")]),
        ("裸の表記 4772212272 を含む", [("", "4772212272")]),
        ("短い数字 1234567 は拾わない", []),
    ],
)
def test_候補の切り出し(line: str, expected: list[tuple[str, str]]) -> None:
    assert find_isbn_candidates(line) == expected
