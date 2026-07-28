"""見出し行の解析と、出典セクションかどうかの判定。

ISBNが本文のどのセクションに現れたかは、それが出典なのか単なる作品紹介なのかを
見分ける手がかりになるため、直近の見出しを追跡してスコアの補正に使う。
"""

import html
import re

#: 見出し行にマッチする正規表現。行全体が同じ数の "=" で囲まれていることを求める。
#: 1つ目のグループが "=" の数（見出しレベル）。
HEADING_RE = re.compile(r"^(={2,6})\s*(.+?)\s*\1\s*$")

#: 出典が列挙されているとみなす見出し。
#:
#: 英語の見出しは "Further reading" と "Further Reading" のように大文字小文字が
#: 揺れるため、すべて小文字で持ち、比較するときに見出し側を小文字化する。
#: 日本語には大文字小文字の区別がないので同じ扱いで問題ない。
REF_HEADINGS = frozenset(
    {
        # 日本語版
        "典拠・資料",
        "脚注",
        "脚注および参考文献",
        "参考図書",
        "主な文献",
        "参照資料",
        "関連図書",
        "参考書籍",
        "参考文献",
        "参考資料",
        "関連書籍",
        "文献",
        "出典",
        "参照文献",
        # 英語版
        "references",
        "reference",
        "bibliography",
        "further reading",
        "sources",
        "notes",
        "footnotes",
        "citations",
        "works cited",
        "notes and references",
        "references and notes",
        "references and further reading",
        "general and cited references",
        "general and cited sources",
        "notes, references and sources",
    }
)

#: この文字列で始まる見出しも出典とみなす（「関連文献リスト」など）。
REF_HEADING_PREFIXES = ("関連文献",)

#: 出典ではなく、その人物・団体の著作を並べているとみなす見出し。
#: REF_HEADINGS と同じく英語は小文字で持つ。
NON_REF_HEADINGS = frozenset(
    {
        # 日本語版。記事の主題そのものが生み出した本を並べる見出し
        "作品",
        "作品リスト",
        "作品一覧",
        "主な作品",
        "著書",
        "著作",
        "著作一覧",
        "著作リスト",
        "著作物",
        "主な著書",
        "主な著作",
        "主要著作",
        "単行本",
        "単行本リスト",
        "既刊一覧",
        "刊行一覧",
        "掲載刊行物一覧",
        "出版物",
        "写真集",
        "ビブリオグラフィ",
        # 英語版。日本語版の「既刊一覧」「著作」に相当する見出し
        "works",
        "publications",
        "selected works",
        "selected publications",
        "published works",
        "collected editions",
        "volume list",
        "volumes",
    }
)


def parse_heading(line: str) -> tuple[int, str] | None:
    """見出し行なら (レベル, 見出し文字列) を返す。見出しでなければ None。

    行の全体が同じ数の "=" で囲まれている場合だけを見出しとみなす。そのため見出しに
    "=" が含まれていても途中で切れず（`== A <span id="x"></span> ==` のようなケース）、
    本文中にたまたま "==" が現れただけの行を見出しと誤認することもない。

    ダンプはXMLなので本文がエスケープされている。"Q&amp;A" のような見出しをそのまま
    返さないよう、実体参照を戻してから空白を落とす。
    """
    match = HEADING_RE.match(line.strip())
    if match is None:
        return None
    return len(match.group(1)), html.unescape(match.group(2)).strip()


def is_reference_heading(heading: str) -> bool:
    """出典が列挙されているセクションの見出しか。"""
    return heading.lower() in REF_HEADINGS or heading.startswith(REF_HEADING_PREFIXES)


def is_non_reference_heading(heading: str) -> bool:
    """出典ではなく著作の一覧とみなすセクションの見出しか。"""
    return heading.lower() in NON_REF_HEADINGS
