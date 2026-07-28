"""見出しの解析と出典セクション判定を検証する。"""

import pytest

from citation.headings import is_non_reference_heading, is_reference_heading, parse_heading


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("== 参考文献 ==", (2, "参考文献")),
        ("=== 詳細 ===", (3, "詳細")),
        ("==参考文献==", (2, "参考文献")),
        ("本文には見出しがない", None),
        ("", None),
    ],
)
def test_見出しの解析(line: str, expected: tuple[int, str] | None) -> None:
    assert parse_heading(line) == expected


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("== ゲーム&amp;ウォッチ版 ==", (2, "ゲーム&ウォッチ版")),
        ("== &quot;通称&quot; ==", (2, '"通称"')),
        ("=== A&amp;B ===", (3, "A&B")),
    ],
)
def test_見出しの実体参照を戻す(line: str, expected: tuple[int, str]) -> None:
    assert parse_heading(line) == expected


def test_1行に複数の見出しがあれば先頭のものを採用する() -> None:
    assert parse_heading("== 第一章 == と == 第二章 ==") == (2, "第一章")


def test_イコール4つ以上は見出し2として扱われる() -> None:
    """先頭の "=" を読み飛ばした位置から "===" としてマッチするため。"""
    assert parse_heading("==== 深い見出し ====") == (3, "深い見出し")


@pytest.mark.parametrize(
    "heading",
    ["参考文献", "出典", "脚注", "文献", "典拠・資料", "脚注および参考文献"],
)
def test_出典セクションの見出し(heading: str) -> None:
    assert is_reference_heading(heading)


def test_関連文献で始まる見出しも出典扱い() -> None:
    assert is_reference_heading("関連文献")
    assert is_reference_heading("関連文献リスト")


@pytest.mark.parametrize(
    "heading",
    ["References", "Bibliography", "Further reading", "Sources", "Notes", "Works cited"],
)
def test_英語版の出典セクションの見出し(heading: str) -> None:
    assert is_reference_heading(heading)


@pytest.mark.parametrize("heading", ["references", "REFERENCES", "Further Reading"])
def test_英語の見出しは大文字小文字を問わない(heading: str) -> None:
    assert is_reference_heading(heading)


@pytest.mark.parametrize("heading", ["概要", "歴史", "History", "External links", "See also"])
def test_出典セクションではない見出し(heading: str) -> None:
    assert not is_reference_heading(heading)


@pytest.mark.parametrize(
    "heading",
    [
        "作品リスト",
        "作品",
        "著書",
        "著作",
        "既刊一覧",
        "単行本",
        "出版物",
        "主な著書",
        "著作一覧",
        "写真集",
        "Works",
        "Publications",
    ],
)
def test_著作一覧の見出し(heading: str) -> None:
    assert is_non_reference_heading(heading)


@pytest.mark.parametrize(
    "heading",
    ["General and cited references", "Notes, references and sources", "General and cited sources"],
)
def test_英語の出典見出しのバリエーション(heading: str) -> None:
    assert is_reference_heading(heading)


def test_参考文献は著作一覧ではない() -> None:
    assert not is_non_reference_heading("参考文献")
