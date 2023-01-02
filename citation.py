__title__ = 'Wikipedia Citation Extractor'
__copyright__ = "Copyright (C) 2023 CALIL Inc."
__author__ = "Ryuuji Yoshimoto <ryuuji@calil.jp>"

import re
import bz2
import json
import isbnlib
import click
from halo import Halo


@click.command()
@click.argument('input_filename', type=click.Path(exists=True))
@click.argument('export_filename', type=click.Path(exists=False))
@click.option('--show-exclusion/--no-show-exclusion', default=False, help='除外した項目を表示する')
def extract_citation(input_filename, export_filename, show_exclusion):
    """
    Wikipediaのダンプファイルから出典ISBNを抽出する
    :param input_filename: ダンプファイル
    :param export_filename: 出力するJSON
    :param show_exclusion: 除外した項目を表示する
    :return:
    """
    click.echo('| extract_citation')
    click.echo('| 処理するファイル:' + click.format_filename(input_filename))
    click.echo('| 出力するファイル:' + click.format_filename(export_filename))

    title = None
    topic1 = None
    topic2 = None
    isbn_regex = re.compile(r"((?:ISBN10 |ISBN13 |ISBN　|isbn=|ISBN  |isbn = |ISBN-10 |ISBN-13 |ISBN：|ISBN-|ISBN |ISBN)?)([0-9][0-9\- ]{8,20}[0-9Xx])")
    topic_regex = re.compile("([=]{2,3})([^=]+)(.*)")
    pages = 0
    count_isbn = 0
    count_error = 0
    with Halo(text='Loading', spinner='dots') as spinner:
        with open(export_filename, 'w', encoding='utf-8') as f:
            for line in bz2.open(input_filename, 'rt', encoding='utf-8'):
                if line == "\n":  # Optimize
                    continue
                if line == "  <page>\n":
                    title = None
                    topic1 = None
                    topic2 = None
                    pages += 1
                    if pages % 300 == 0:
                        spinner.text = str(pages)
                elif not title:
                    for title_ in re.findall(u"<title>([^<]*)</title>", line):
                        title = title_
                else:
                    # 見出しの検索
                    if line.find("==") != -1:
                        ret = topic_regex.findall(line)
                        if len(ret) == 1:
                            if len(ret[0][0]) == 2:
                                topic1 = ret[0][1].strip()
                                topic2 = None
                            if len(ret[0][0]) == 3:
                                topic2 = ret[0][1].strip()

                    if line.find("ISBN") != -1 and line.find("isbn") != -1 and line.find("Isbn") != -1:
                        continue

                    for ret in isbn_regex.findall(line):
                        score = 0.0
                        _isbn = ret[1].replace('-', '')
                        _isbn = _isbn.replace(' ', '')
                        _isbn = _isbn.replace('x', 'X')

                        if ret[0] == 'ISBN-' and len(_isbn) == 12 and _isbn[0:2] == '10' and _isbn[2] == '4':
                            _isbn = _isbn[2:12]
                        _isbn_pattern = "?"
                        _isbn_length = len(_isbn)

                        if len(ret[0]) > 0:  # ISBNの記述があった場合は信頼
                            score += 0.9

                        if _isbn_length == 16:
                            if _isbn.find('978978') == 0 and isbnlib.is_isbn13(_isbn[6:16]):
                                _isbn_pattern = "I13(978978Cut)"
                                score += 0.5
                                _isbn = _isbn[6:16]
                        if _isbn_length == 10:
                            if isbnlib.is_isbn10(_isbn):
                                _isbn_pattern = "I10"
                                score += 0.5
                                if re.search("^4", _isbn):
                                    score += 1.0
                                if re.search("[X]$", _isbn):
                                    score += 0.5
                            elif _isbn.find("X") == -1 and isbnlib.is_isbn13("978" + _isbn):
                                _isbn_pattern = "I13(978+)"
                                _isbn = "978" + _isbn
                                score += 1.0
                        elif _isbn_length == 13:
                            if _isbn.find('491') == 0:
                                _isbn_pattern = u"雑誌コード"
                                score = -1
                            elif (_isbn.find('978') == 0 or _isbn.find('977') == 0) and _isbn.find(
                                    "X") == -1 and isbnlib.is_isbn13(_isbn):
                                _isbn_pattern = "I13"
                                if _isbn.find('978') == 0:
                                    _isbn = _isbn
                                score += 1.0
                            elif isbnlib.is_isbn10(_isbn[3:]):  # 10桁を無理矢理13桁化
                                _isbn = _isbn[3:]
                                _isbn_pattern = "I10(978-)"
                                score += 0.5
                        elif _isbn_length == 11 and _isbn[0] == '8' and isbnlib.is_isbn13("97" + _isbn):  # 10桁を13桁化
                            _isbn = "97" + _isbn
                            _isbn_pattern = "I13(97+)"
                            score += 0.5
                        elif _isbn_length > 13 and _isbn.find("978") == 0 and _isbn.find("X") == -1 and isbnlib.is_isbn13(
                                _isbn[0:13]):
                            _isbn_pattern = "I13(Cut13)"
                            _isbn = _isbn[0:13]
                            score += 0.5
                        elif _isbn_length > 13 and _isbn.find("978") == 0 and isbnlib.is_isbn10(_isbn[3:13]):
                            _isbn = _isbn[3:13]
                            _isbn_pattern = "I10(Cut13_978-)"
                            score += 0.5
                        elif _isbn_length > 10 and isbnlib.is_isbn10(_isbn[0:10]):
                            _isbn = _isbn[0:10]
                            _isbn_pattern = "I10(Cut10)"
                            score += 0.5
                        elif _isbn_length > 10 and isbnlib.is_isbn13("978" + _isbn[0:10]):
                            _isbn = "978" + _isbn[0:10]
                            _isbn_pattern = "I13(Cut10_978+)"
                            score += 0.5
                        elif _isbn_length == 9 and isbnlib.is_isbn10("4" + _isbn):
                            _isbn = '4' + _isbn
                            _isbn_pattern = "I10(4+)"
                            score += 0.5
                        if score >= 1.0:
                            count_isbn += 1
                            if line.find("&lt;ref") != -1 or line.find("{Cite book") != -1:
                                is_ref = True
                                score += 0.5
                            else:
                                is_ref = False
                            if topic1:
                                if topic1 in ["作品リスト", "作品"]:
                                    is_ref = False
                                    score -= 0.5
                                if (topic1 in ["典拠・資料", "脚注", "脚注および参考文献", "参考図書", "主な文献", "参照資料",
                                               "関連図書", "参考書籍", "参考文献", "参考資料",
                                               "関連書籍", "文献", "出典", "参照文献"]) or topic1.find("関連文献") == 0:
                                    is_ref = True
                                    score += 0.5
                            item = {'isbn': isbnlib.to_isbn10(_isbn),
                                    'raw': ret[1].strip(),
                                    'title': title,
                                    'score': score,
                                    'h1': topic1,
                                    'h2': topic2,
                                    'is_ref': is_ref}
                            f.write(json.dumps(item, ensure_ascii=False) + '\n')
                        else:
                            count_error += 1
                            if show_exclusion and len(ret[0]) > 0:
                                click.echo("\n" + " ".join([_isbn_pattern, ret[0], _isbn, title, str(score)]))

    click.echo("count_pages:" + str(pages))
    click.echo("count_isbn:" + str(count_isbn))
    click.echo("count_error:" + str(count_error))
    click.secho('処理が完了しました', fg='green')


if __name__ == '__main__':
    extract_citation()
