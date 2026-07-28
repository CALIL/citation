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


def test_見出しに等号が含まれても途中で切れない() -> None:
    """HTMLの属性など "=" を含む見出しがそのまま取れること。"""
    line = '== Schools of thought <span class="anchor" id="x"></span> =='
    assert parse_heading(line) == (2, 'Schools of thought <span class="anchor" id="x"></span>')


def test_本文中の等号は見出しとみなさない() -> None:
    """行全体が "=" で囲まれていなければ見出しではない。"""
    assert parse_heading("本文中に == が出てくる場合") is None
    assert parse_heading("数式 a == b について") is None


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("==== 深い見出し ====", (4, "深い見出し")),
        ("===== 5段階 =====", (5, "5段階")),
    ],
)
def test_4段階以上の見出しもレベルを返す(line: str, expected: tuple[int, str]) -> None:
    """呼び出し側で3段階以上をまとめて見出し2として扱う。"""
    assert parse_heading(line) == expected


def test_閉じる等号の数が違えば見出しの一部とみなす() -> None:
    assert parse_heading("== 参考文献 ===") == (2, "参考文献 =")


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
        "Collected editions",
        "Published works",
        "Volume list",
        "Volumes",
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
