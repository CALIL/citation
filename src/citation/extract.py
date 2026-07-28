"""ダンプの行ストリームから出典ISBNを抽出する状態機械。"""

import re
from collections.abc import Callable, Iterable, Iterator

from citation.headings import (
    is_non_reference_heading,
    is_reference_heading,
    parse_heading,
)
from citation.isbn import NormalizedIsbn, canonical_isbn, find_isbn_candidates, normalize_isbn
from citation.record import Exclusion, Record

#: ページの開始行。ダンプのインデントは固定なので完全一致で判定できる。
PAGE_START = "  <page>\n"

TITLE_RE = re.compile(r"<title>([^<]*)</title>")

NS_RE = re.compile(r"<ns>(\d+)</ns>")

#: 記事の名前空間。Wikipedia: や Help: などはこれ以外の値を持つ。
ARTICLE_NAMESPACE = "0"

#: 出典であることを示すrefタグ。ダンプ内ではXMLエスケープされている。
REF_TAG = "&lt;ref"

#: 出典を表すciteテンプレート。"{{cite book" "{{Cite Book" "{{ cite book" のように
#: 大文字小文字と空白が揺れるため正規表現で吸収する。波括弧を1つ以上としているのは、
#: 表記ゆれを吸収する前の "{Cite book" という部分一致の挙動を包含するため。
#:
#: 種類は問わない。ISBNが書かれた行にciteテンプレートがあるなら、それが journal でも
#: encyclopedia でも出典を示していることに変わりはないため。
#:
#: {{Citation}} も出典テンプレートだが、出典が無いことを示す {{Citation needed}} と
#: 紛らわしい。引数の区切りか閉じ括弧が直後に来る場合だけを拾って区別する。
CITE_TEMPLATE_RE = re.compile(r"\{\s*(?:cite[\s_]+[a-z]|citation\s*[|}])", re.IGNORECASE)

#: 除外された候補を受け取るコールバック。
ExclusionHandler = Callable[[Exclusion], None]


class Extractor:
    """ダンプの行を順に読み、出典ISBNのレコードを生成する。

    ページの開始行でタイトルと見出しの状態をリセットするため、状態はページ内で
    完結する。ダンプをページ境界で分割して別々に処理しても結果は変わらない。
    """

    def __init__(self, on_exclusion: ExclusionHandler | None = None) -> None:
        """:param on_exclusion: 除外された候補を通知するコールバック"""
        self.pages = 0
        self.isbn_count = 0
        self.error_count = 0
        self._on_exclusion = on_exclusion
        self._title: str | None = None
        self._h1: str | None = None
        self._h2: str | None = None
        self._skip_page = False

    def extract(self, lines: Iterable[str]) -> Iterator[Record]:
        """行を順に読み、採用されたISBNをレコードとして返す。"""
        for line in lines:
            if line == "\n":  # 本文の空行。数が多いので先に弾く
                continue
            if line == PAGE_START:
                self._title = None
                self._h1 = None
                self._h2 = None
                self._skip_page = False
                self.pages += 1
            elif not self._title:
                for title in TITLE_RE.findall(line):
                    self._title = title
            elif not self._skip_page:
                yield from self._scan(line)

    def _scan(self, line: str) -> Iterator[Record]:
        """本文1行からISBNを拾う。"""
        # 名前空間はタイトルの直後に現れる。記事以外（Wikipedia:、Help:、Template:
        # など）はこのページごと読み飛ばす。<ns> を持たない古い形式のダンプでは
        # この行が現れないため、従来どおり全ページが対象になる。
        if "<ns>" in line:
            namespace = NS_RE.search(line)
            if namespace is not None:
                self._skip_page = namespace.group(1) != ARTICLE_NAMESPACE
                return

        self._track_heading(line)

        for prefix, raw in find_isbn_candidates(line):
            normalized = normalize_isbn(prefix, raw)
            if normalized.adopted:
                self.isbn_count += 1
                yield self._build_record(line, raw, normalized)
            else:
                self.error_count += 1
                if self._on_exclusion is not None and prefix:
                    self._on_exclusion(
                        Exclusion(
                            pattern=normalized.pattern,
                            prefix=prefix,
                            isbn=normalized.isbn,
                            title=self._title or "",
                            score=normalized.score,
                        )
                    )

    def _track_heading(self, line: str) -> None:
        """見出し行なら現在の見出し状態を更新する。"""
        heading = parse_heading(line)
        if heading is None:
            return
        level, text = heading
        if level == 2:
            self._h1 = text
            self._h2 = None
        else:
            self._h2 = text

    def _build_record(self, line: str, raw: str, normalized: NormalizedIsbn) -> Record:
        """出典らしさの補正を加えてレコードを組み立てる。

        採用するかどうかの判定は補正前のスコアで済んでいるため、ここでの減点によって
        出力されるスコアが採用の閾値を下回ることがある。
        """
        score = normalized.score

        is_ref = REF_TAG in line or CITE_TEMPLATE_RE.search(line) is not None
        if is_ref:
            score += 0.5

        if self._h1:
            if is_non_reference_heading(self._h1):
                is_ref = False
                score -= 0.5
            if is_reference_heading(self._h1):
                is_ref = True
                score += 0.5

        # 0.9 や 0.5 を足し引きすると二進小数で表せない端数が残る（0.9 + 0.5 - 0.5 が
        # 0.8999999999999999 になる）ため、記録する前に丸める。
        return Record(
            isbn=canonical_isbn(normalized.isbn),
            raw=raw.strip(),
            title=self._title or "",
            score=round(score, 1),
            h1=self._h1,
            h2=self._h2,
            is_ref=is_ref,
        )
