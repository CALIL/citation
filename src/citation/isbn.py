"""ISBN表記の抽出と正規化。

Wikipediaの本文には様々な表記でISBNが書かれているため、正規表現で候補を拾った上で
チェックデジットの検証と桁数の調整を行い、どのくらい確からしいかをスコアで表す。
ここで算出するのは「ISBN表記としての確からしさ」だけで、これが ADOPTION_THRESHOLD
以上の候補を抽出結果として採用する。

採用したあとに「出典らしさ」の補正（出典マークアップや見出しによる加減点）が
citation.extract で加わる。出力されるスコアは補正後の値なので、採用の閾値を
下回ることがある。
"""

import re
from dataclasses import dataclass

import isbnlib

#: ISBNを示す接頭辞。並び順がそのまま優先順位になる。長いものを先に置かないと
#: "ISBN-10 " が "ISBN-" として解釈されてしまうため、並べ替えないこと。
ISBN_PREFIXES = [
    # 書店や書誌サイトのURLに現れる形。版元ドットコムやWorldCatは /isbn/ を、
    # 紀伊國屋書店は W-ISBN= を使う。
    #
    # CALILの /book/ はドメインごと指定している。単に "/book/" とすると、URLに
    # ISBNをゼロ埋めして並べているサイトまで拾ってしまい、"97845752362860000000"
    # のような不格好な元表記のレコードが2,400件ほど増えるため。
    r"/isbn/",
    r"/ISBN/",
    r"ISBN=",
    r"calil\.jp/book/",
    # 商品URLのパス。Amazonの書籍のASINはISBN-10と同じ番号なので、ここに続く
    # 数字列はISBNとみなせる。書籍以外のASINは "B0" で始まるため数字列にならない。
    r"/dp/",
    r"/ASIN/",
    r"/asin/",
    r"/gp/product/",
    # テンプレート記法。日本語版では {{ISBN2|...}} が最も多く使われる
    r"ISBN2\|",
    r"isbn2\|",
    r"Isbn2\|",
    r"ISBNT\|",
    r"isbnt\|",
    r"ISBN\|",
    r"isbn\|",
    r"Isbn\|",
    # 本文中の表記
    "ISBN10 ",
    "ISBN13 ",
    "ISBN　",
    "isbn=",
    "ISBN  ",
    "isbn = ",
    "ISBN-10 ",
    "ISBN-13 ",
    "ISBN：",
    "ISBN-",
    "ISBN ",
    "ISBN",
]

#: ISBN候補を拾う正規表現。前半がISBNを示す接頭辞、後半が数字列。
ISBN_RE = re.compile("((?:" + "|".join(ISBN_PREFIXES) + ")?)" + r"([0-9][0-9\- ]{8,20}[0-9Xx])")

#: 桁数からも接頭辞からも正体を判定できなかった候補につけるパターン名。
UNKNOWN = "?"

#: 採用の閾値。補正前のスコアがこれ未満の候補は抽出結果に含めない。
#: 出力されるスコアは採用後に補正を受けるため、この値を下回ることがある。
ADOPTION_THRESHOLD = 1.0


@dataclass(frozen=True)
class NormalizedIsbn:
    """正規化されたISBNと、その判定根拠。"""

    isbn: str
    """正規化後のISBN。判定できなかった場合は入力のまま。"""

    pattern: str
    """どの桁数パターンとして解釈したか。判定できなかった場合は ``UNKNOWN``。"""

    score: float
    """ISBN表記としての確からしさ。出典らしさの補正は含まない。"""

    @property
    def adopted(self) -> bool:
        """抽出結果として採用する水準に達しているか。"""
        return self.score >= ADOPTION_THRESHOLD


def _hyphenated_as_isbn(raw: str, isbn: str) -> bool:
    """元の表記が、そのISBNの正しい区切り位置でハイフン分割されているか。

    "0-520-20743-2" のように、グループ・出版社・書名・チェックデジットの境目で
    ハイフンが入っていれば、書き手がISBNとして整形したとみなせる。日付や連番が
    たまたまこの位置で区切られることは考えにくい。
    """
    try:
        return raw == isbnlib.mask(isbn)
    except isbnlib.NotValidISBNError:
        return False


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

    # ISBNの記述もISBN-13のプレフィックスも無いのに、区切りとしてスペースが混じって
    # いる数字列は、日付やページ範囲や郵便番号を拾っている。jawiki-20260401 で該当した
    # 1,871件を調べたところ "2008-12-10 00"（日付と時刻）、"197-207 1991"（ページと年）、
    # "10115 - 14199"（郵便番号の範囲）のようなものばかりだった。
    # 逆に "ISBN 0 521 31827 0" のように接頭辞があるものや "978 1 84603 502 9" のように
    # ISBN-13のプレフィックスで始まるものは、スペース区切りのISBNとして妥当なので残す。
    if not prefix and " " in raw and not isbn.startswith(("978", "979")):
        return NormalizedIsbn(isbn=isbn, pattern=UNKNOWN, score=score)

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
            # ISBN-13の "978" が欠けた表記。ただしISBN-13のチェックデジットは10通り
            # しかないため、任意の10桁数字列の約1割が偶然この条件を満たす。実際に
            # jawiki-20260401 で該当した49,120件のうちISBNの記述があるものは40件だけで、
            # 残りは日付や電話番号やフォーメーションの数字だった。ISBNの記述が無ければ
            # 採用しない重みにしておく。
            pattern = "I13(978+)"
            isbn = "978" + isbn
            score += 0.5
    elif length == 13:
        if isbn.startswith("491"):
            pattern = "雑誌コード"
            score = -1
        elif "X" not in isbn and isbnlib.is_isbn13(isbn):
            # is_isbn13() が 978/979 のプレフィックスとチェックデジットの両方を検証する。
            # 977（雑誌のバーコード）はこの関数が弾くため、ここには入らない。
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

    # ISBNの記述が無くても、正しい区切り位置でハイフンが入っていれば書き手が
    # ISBNとして整形したとみなせる。実測では、これに該当して採用されていなかった
    # 6,463件がいずれも "0-520-20743-2" のような英語圏の実在ISBNだった。
    if not prefix and "-" in raw and pattern != UNKNOWN and _hyphenated_as_isbn(raw.strip(), isbn):
        score += 0.5

    return NormalizedIsbn(isbn=isbn, pattern=pattern, score=score)


def find_isbn_candidates(line: str) -> list[tuple[str, str]]:
    """行からISBN候補を (接頭辞, 数字列) の組で拾い出す。"""
    return ISBN_RE.findall(line)


def canonical_isbn(isbn: str) -> str:
    """出力用のISBNに正規化する。正規化できない場合は空文字。

    原則としてISBN-10に揃えるが、979で始まるISBN-13はISBN-13のまま返す。979は2007年に
    追加されたプレフィックスで、ISBN-10の番号空間に対応する番号が存在しないため。

    isbnlibの ``to_isbn10()`` は先頭3文字が "978" かどうかだけでISBN-13と判断する。
    そのため "9784062577" のような978で始まる正当なISBN-10を渡すと、ISBN-13として
    検証に失敗して空文字を返してしまう。先にISBN-10かどうかを確かめる。
    """
    if isbnlib.is_isbn10(isbn):
        return isbn
    converted = isbnlib.to_isbn10(isbn)
    if converted:
        return converted
    if isbn.startswith("979") and isbnlib.is_isbn13(isbn):
        return isbn
    return ""
