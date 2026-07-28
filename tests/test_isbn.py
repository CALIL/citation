"""ISBN正規化の各分岐を検証する。

桁数パターンごとの判定はこのツールの中核だが、長らく一度も検証されないまま
本番の出力に反映されていた。ここで全パターンを固定する。
"""

import pytest

from citation.isbn import UNKNOWN, canonical_isbn, find_isbn_candidates, normalize_isbn

#: (本文の表記, 期待するパターン名, 期待するISBN, 期待するスコア)
#: スコアは接頭辞 "ISBN " があることによる +0.9 を含む。
PATTERNS = [
    ("4-7722-1227-2", "I10", "4772212272", 2.4),
    ("4-00-000008-X", "I10", "400000008X", 2.9),
    ("978-4-7722-1227-4", "I13", "9784772212274", 1.9),
    ("979-8-9878-9940-3", "I13", "9798987899403", 1.9),
    ("4772212274", "I13(978+)", "9784772212274", 1.4),
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
    """区切りの一致による加点が混ざらないよう、ハイフンなしの表記で比べる。"""
    with_prefix = normalize_isbn("ISBN ", "4772212272")
    without_prefix = normalize_isbn("", "4772212272")
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


@pytest.mark.parametrize(
    "raw",
    [
        "2008-12-10 00",  # 日付と時刻
        "197-207 1991",  # ページ範囲と年
        "10115 - 14199",  # 郵便番号の範囲
        "3000 780103",
    ],
)
def test_接頭辞なしでスペースを含む数字列は採用しない(raw: str) -> None:
    """日付やページ範囲を拾っているため（KNOWN_ISSUES.md 参照）。"""
    result = normalize_isbn("", raw)
    assert result.pattern == UNKNOWN
    assert not result.adopted


@pytest.mark.parametrize(
    ("prefix", "raw", "isbn"),
    [
        ("ISBN ", "0 521 31827 0", "0521318270"),  # 接頭辞があればスペース区切りを認める
        ("", "978 1 84603 502 9", "9781846035029"),  # 978で始まればISBNと分かる
    ],
)
def test_スペース区切りのISBNは採用する(prefix: str, raw: str, isbn: str) -> None:
    result = normalize_isbn(prefix, raw)
    assert result.adopted
    assert result.isbn == isbn


@pytest.mark.parametrize(
    "raw",
    ["0-520-20743-2", "0-299-02470-9", "0-340-76167-9"],
)
def test_正しい区切りのハイフンがあれば接頭辞なしでも採用する(raw: str) -> None:
    """英語圏のISBNは先頭が4でないため、従来はスコアが足りず採用できなかった。"""
    result = normalize_isbn("", raw)
    assert result.pattern == "I10"
    assert result.adopted
    assert result.score == pytest.approx(1.0)  # I10の0.5 + 区切り一致の0.5


def test_区切り位置が違えば加点しない() -> None:
    """ISBNとしての正しい区切りでなければ、日付や連番の可能性がある。"""
    result = normalize_isbn("", "2026-21614-2")  # 正しくは 2-02-621614-2
    assert not result.adopted


def test_ハイフンがなければ加点しない() -> None:
    result = normalize_isbn("", "1000342530")
    assert not result.adopted


def test_接頭辞があるときは区切りで二重に加点しない() -> None:
    """接頭辞の+0.9で十分に信頼できるため、区切りの一致は見ない。"""
    result = normalize_isbn("ISBN ", "4-7722-1227-2")
    assert result.score == pytest.approx(2.4)


def test_雑誌コードは採用しない() -> None:
    assert not normalize_isbn("ISBN ", "4910123456789").adopted


def test_978で始まるISBN10はそのまま返す() -> None:
    """isbnlibの to_isbn10() は先頭3文字だけでISBN-13と誤認する（KNOWN_ISSUES.md 参照）。"""
    assert canonical_isbn("9784062577") == "9784062577"


@pytest.mark.parametrize(
    ("isbn", "expected"),
    [
        ("9784772212274", "4772212272"),  # ISBN-13から変換
        ("4772212272", "4772212272"),  # すでにISBN-10
        ("400000008X", "400000008X"),  # チェックデジットがX
        ("9798987899403", "9798987899403"),  # 979は対応するISBN-10が無いので13桁のまま
        ("9790014006723", "9790014006723"),  # 楽譜のISMN（979-0）も同様
        ("9771234567003", ""),  # ISBNではない（雑誌のバーコード）
    ],
)
def test_出力用ISBNへの正規化(isbn: str, expected: str) -> None:
    assert canonical_isbn(isbn) == expected


@pytest.mark.parametrize(
    ("line", "prefix"),
    [
        ("https://www.hanmoto.com/bd/isbn/4772212272", "/isbn/"),
        ("https://calil.jp/book/4772212272", "calil.jp/book/"),
        ("https://www.worldcat.org/isbn/4772212272", "/isbn/"),
        ("http://bookweb.kinokuniya.co.jp/wshosea.cgi?W-ISBN=4772212272", "ISBN="),
        ("url=https://www.amazon.com/Rough-Guide/dp/4772212272", "/dp/"),
        ("[https://www.amazon.co.jp/exec/obidos/ASIN/4772212272 書名]", "/ASIN/"),
        ("https://www.amazon.com/gp/product/4772212272", "/gp/product/"),
    ],
)
def test_商品URLのパスを接頭辞として認識する(line: str, prefix: str) -> None:
    """AmazonのASINは書籍ならISBN-10と同じ番号なので出典として拾える。"""
    candidates = find_isbn_candidates(line)
    assert candidates[0][0] == prefix
    assert normalize_isbn(*candidates[0]).adopted


def test_書籍以外のASINは拾わない() -> None:
    """書籍以外のASINは "B0" で始まるため、数字列としてマッチしない。"""
    assert find_isbn_candidates("https://www.amazon.co.jp/dp/B08XYZABCD") == []


@pytest.mark.parametrize(
    ("line", "prefix"),
    [
        ("*# 初版発行、{{ISBN2|4-7722-1227-2}}", "ISBN2|"),
        ("{{isbn2|4-7722-1227-2}}", "isbn2|"),
        ("{{ISBNT|4-7722-1227-2}}", "ISBNT|"),
        ("{{ISBN|4772212272}}", "ISBN|"),
        ("{{isbn|4772212272}}", "isbn|"),
    ],
)
def test_テンプレート記法を接頭辞として認識する(line: str, prefix: str) -> None:
    """日本語版では {{ISBN2|...}} が22万件以上使われている。"""
    candidates = find_isbn_candidates(line)
    assert candidates[0][0] == prefix
    assert normalize_isbn(*candidates[0]).score == pytest.approx(2.4)


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
