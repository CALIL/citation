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


def test_タイトルの実体参照を戻す() -> None:
    """ダンプはXMLなのでタイトルもエスケープされている。"""
    (record,) = extract(dump_page("ゲーム&amp;ウォッチ", ["* ISBN 4-7722-1227-2"]))
    assert record.title == "ゲーム&ウォッチ"


def test_見出しの実体参照を戻す() -> None:
    body = ["== 息子、または&quot;通称&quot; ==", "* ISBN 4-7722-1227-2"]
    (record,) = extract(dump_page("A", body))
    assert record.h1 == '息子、または"通称"'


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


@pytest.mark.parametrize(
    "markup",
    [
        "{{cite journal",
        "{{cite encyclopedia",
        "{{cite report",
        "{{cite magazine",
        "{{cite thesis",
        "{{cite web",
    ],
)
def test_書籍以外のciteテンプレートも出典とみなす(markup: str) -> None:
    """種類を問わず、citeテンプレートは出典を示すマークアップとして扱う。"""
    (record,) = extract(dump_page("A", ["* " + markup + "|isbn=4-7722-1227-2}}"]))
    assert record.is_ref


@pytest.mark.parametrize(
    "markup",
    [
        "{{Cite book",
        "{{cite book",
        "{{Cite Book",
        "{{ cite book",
        "{{cite  book",
        "{{cite_book",
        "{Cite book",
    ],
)
def test_citeテンプレートの表記ゆれを吸収する(markup: str) -> None:
    (record,) = extract(dump_page("A", ["* " + markup + "|isbn=4-7722-1227-2}}"]))
    assert record.is_ref
    assert record.score == pytest.approx(2.9)


@pytest.mark.parametrize(
    "markup",
    [
        "{{Citation|title=地理学|isbn=4-7722-1227-2}}",
        "{{citation|title=地理学|isbn=4-7722-1227-2}}",
        "{{ Citation |title=地理学|isbn=4-7722-1227-2}}",
        "{{Citation}} ISBN 4-7722-1227-2",
    ],
)
def test_citationテンプレートも出典とみなす(markup: str) -> None:
    (record,) = extract(dump_page("A", ["* " + markup]))
    assert record.is_ref


def test_要出典テンプレートは出典とみなさない() -> None:
    """{{Citation needed}} は出典が無いことを示すマーカーなので区別する。"""
    (record,) = extract(dump_page("A", ["* {{Citation needed}} ISBN 4-7722-1227-2"]))
    assert not record.is_ref


def test_ISBNの表記ゆれを3つとも含む行も処理する() -> None:
    """かつて論理が反転した読み飛ばし条件があり、この種の行を取りこぼしていた。"""
    line = "isbn と ISBN と Isbn の表記ゆれについて ISBN 4-7722-1227-2"
    (record,) = extract(dump_page("表記ゆれの解説", [line]))
    assert record.isbn == "4772212272"


def test_接頭辞のない裸の数字列も拾う() -> None:
    """接頭辞なしの検出はREADMEに明記された仕様（KNOWN_ISSUES.md 課題1参照）。"""
    (record,) = extract(dump_page("裸の表記", ["参考 4-7722-1227-2 を参照"]))
    assert record.isbn == "4772212272"
    assert record.score == pytest.approx(1.5)


def test_採用後の減点でスコアが閾値を下回ることがある() -> None:
    """採用の判定は補正前のスコアで行うため、出力は1.0を下回りうる。

    接頭辞なしのISBN-13（補正前1.0）が著作一覧の見出しの下にあるケース。
    """
    (record,) = extract(dump_page("作品", ["== 作品リスト ==", "* 9784396380656"]))
    assert record.score == 0.5


def test_スコアに浮動小数点の誤差が残らない() -> None:
    """0.9 + 0.5 - 0.5 が 0.8999999999999999 にならないこと。"""
    (record,) = extract(dump_page("作品", ["== 作品リスト ==", "* ISBN 0-230-22620-5"]))
    assert record.score == 0.9  # 誤差を許容せず厳密に比較する


def test_著作一覧の見出しでは出典とみなさない() -> None:
    (record,) = extract(dump_page("作品", ["== 作品リスト ==", "* ISBN 4-7722-1227-2"]))
    assert not record.is_ref
    assert record.score == pytest.approx(1.9)


def test_978で始まるISBN10も変換できる() -> None:
    (record,) = extract(dump_page("978始まり", ["* ISBN 9780000003"]))
    assert record.isbn == "9780000003"
    assert record.raw == "9780000003"


@pytest.mark.parametrize("ns", ["4", "10", "12", "100"])
def test_記事以外の名前空間は読み飛ばす(ns: str) -> None:
    assert extract(dump_page("Wikipedia:井戸端", ["* ISBN 4-7722-1227-2"], ns=ns)) == []


def test_記事の名前空間は抽出する() -> None:
    assert len(extract(dump_page("地理学", ["* ISBN 4-7722-1227-2"], ns="0"))) == 1


def test_名前空間を読み飛ばしても次のページは処理する() -> None:
    lines = dump_page("Wikipedia:井戸端", ["* ISBN 4-7722-1227-2"], ns="4")
    lines += dump_page("地理学", ["* ISBN 4-7722-1227-2"], ns="0")
    records = extract(lines)
    assert [r.title for r in records] == ["地理学"]


def test_名前空間の行がなくても抽出する() -> None:
    """<ns> を持たない古い形式のダンプでも従来どおり動く。"""
    lines = [
        "  <page>\n",
        "    <title>地理学</title>\n",
        "    <revision>\n",
        "      <text>\n",
        "* ISBN 4-7722-1227-2\n",
        "      </text>\n",
        "    </revision>\n",
        "  </page>\n",
    ]
    assert len(extract(lines)) == 1


def test_ページ数と採否の件数を数える() -> None:
    lines = dump_page("A", ["* ISBN 4-7722-1227-2", "* ISBN 4-7722-1227-3"])
    extractor = Extractor()
    records = list(extractor.extract(lines))
    assert extractor.pages == 1
    assert extractor.isbn_count == 1
    assert extractor.error_count == 1
    assert len(records) == 1


def test_uniqueで同じページの同じISBNをまとめる() -> None:
    """表記が違っても正規化後のISBNが同じなら1件にする。"""
    body = ["* ISBN 4-7722-1227-2", "* ISBN 978-4-7722-1227-4", "* ISBN 4-7722-1227-2"]
    extractor = Extractor(unique=True)
    records = list(extractor.extract(dump_page("重複のあるページ", body)))
    assert len(records) == 1
    assert extractor.duplicate_count == 2
    assert extractor.isbn_count == 3  # 採用した数は重複を含めて数える


def test_uniqueの重複判定はページをまたがない() -> None:
    lines = dump_page("A", ["* ISBN 4-7722-1227-2"])
    lines += dump_page("B", ["* ISBN 4-7722-1227-2"])
    records = list(Extractor(unique=True).extract(lines))
    assert [r.title for r in records] == ["A", "B"]


def test_uniteを指定しなければ重複はそのまま出力する() -> None:
    body = ["* ISBN 4-7722-1227-2", "* ISBN 4-7722-1227-2"]
    extractor = Extractor()
    assert len(list(extractor.extract(dump_page("重複", body)))) == 2
    assert extractor.duplicate_count == 0


def test_除外された候補が通知される() -> None:
    seen: list[Exclusion] = []
    extractor = Extractor(on_exclusion=seen.append)
    list(extractor.extract(dump_page("雑誌", ["* ISBN 4910123456789"])))
    assert len(seen) == 1
    assert seen[0].pattern == "雑誌コード"
    assert seen[0].title == "雑誌"
