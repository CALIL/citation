"""ダンプ走査の状態機械を検証する。"""

import pytest

from citation.extract import Extractor
from citation.record import Exclusion, Record


def dump_page(title: str, body: list[str], ns: str = "0") -> list[str]:
    """ダンプ1ページ分の行を組み立てる。"""
    lines = [
        "  <page>\n",
        f"    <title>{title}</title>\n",
        f"    <ns>{ns}</ns>\n",
        "    <revision>\n",
        "      <text>\n",
    ]
    lines.extend(f"{line}\n" for line in body)
    lines.extend(["      </text>\n", "    </revision>\n", "  </page>\n"])
    return lines


def extract(lines: list[str]) -> list[Record]:
    return list(Extractor().extract(lines))


def test_タイトルと見出しがレコードに入る() -> None:
    (record,) = extract(dump_page("地理学", ["== 参考文献 ==", "* ISBN 4-7722-1227-2"]))
    assert record.title == "地理学"
    assert record.h1 == "参考文献"
    assert record.h2 is None
    assert record.isbn == "4772212272"
    assert record.raw == "4-7722-1227-2"
    assert record.is_ref


def test_ページ境界で状態がリセットされる() -> None:
    lines = dump_page("前のページ", ["== 参考文献 ==", "* ISBN 4-7722-1227-2"])
    lines += dump_page("次のページ", ["* ISBN 4-7722-1227-2"])
    records = extract(lines)
    assert [r.title for r in records] == ["前のページ", "次のページ"]
    assert records[1].h1 is None  # 前のページの見出しを引きずらない


def test_見出し1が変わると見出し2はクリアされる() -> None:
    body = [
        "== 第一章 ==",
        "=== 第一節 ===",
        "* ISBN 4-7722-1227-2",
        "== 第二章 ==",
        "* ISBN 4-7722-1227-2",
    ]
    records = extract(dump_page("見出しの継承", body))
    assert (records[0].h1, records[0].h2) == ("第一章", "第一節")
    assert (records[1].h1, records[1].h2) == ("第二章", None)


def test_refタグがあれば出典とみなす() -> None:
    (record,) = extract(dump_page("出典", ["記述&lt;ref&gt;ISBN 4-7722-1227-2&lt;/ref&gt;"]))
    assert record.is_ref
    assert record.score == pytest.approx(2.9)


def test_小文字のciteテンプレートは出典と判定されない() -> None:
    """`{Cite book` としか比較していないため取りこぼす（KNOWN_ISSUES.md 参照）。"""
    (upper,) = extract(dump_page("A", ["* {{Cite book|isbn=4-7722-1227-2}}"]))
    (lower,) = extract(dump_page("A", ["* {{cite book|isbn=4-7722-1227-2}}"]))
    assert upper.is_ref
    assert not lower.is_ref


def test_著作一覧の見出しでは出典とみなさない() -> None:
    (record,) = extract(dump_page("作品", ["== 作品リスト ==", "* ISBN 4-7722-1227-2"]))
    assert not record.is_ref
    assert record.score == pytest.approx(1.9)


def test_978で始まるISBN10は変換に失敗して空になる() -> None:
    """to_isbn10() が接頭辞だけでISBN-13と判定するため（KNOWN_ISSUES.md 参照）。"""
    (record,) = extract(dump_page("空ISBN", ["* ISBN 9780000003"]))
    assert record.isbn == ""
    assert record.raw == "9780000003"


def test_記事以外の名前空間も抽出対象になる() -> None:
    """<ns> を見ていないため Wikipedia: なども対象になる（KNOWN_ISSUES.md 参照）。"""
    records = extract(dump_page("Wikipedia:井戸端", ["* ISBN 4-7722-1227-2"], ns="4"))
    assert len(records) == 1


def test_ページ数と採否の件数を数える() -> None:
    lines = dump_page("A", ["* ISBN 4-7722-1227-2", "* ISBN 4-7722-1227-3"])
    extractor = Extractor()
    records = list(extractor.extract(lines))
    assert extractor.pages == 1
    assert extractor.isbn_count == 1
    assert extractor.error_count == 1
    assert len(records) == 1


def test_除外された候補が通知される() -> None:
    seen: list[Exclusion] = []
    extractor = Extractor(on_exclusion=seen.append)
    list(extractor.extract(dump_page("雑誌", ["* ISBN 4910123456789"])))
    assert len(seen) == 1
    assert seen[0].pattern == "雑誌コード"
    assert seen[0].title == "雑誌"
