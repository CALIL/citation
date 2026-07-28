"""コマンドラインインターフェース。"""

import bz2
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, TextIO

import click

from citation.dump import stream_ranges
from citation.extract import ExclusionHandler, Extractor
from citation.parallel import MIN_STREAMS_FOR_PARALLEL, extract_streams
from citation.record import Exclusion

#: 逐次処理で進捗表示を更新するレコード数の間隔。
PROGRESS_INTERVAL = 1000


class ProgressReporter(Protocol):
    """click.progressbar のうち、進捗の更新に使う部分だけを表す。"""

    def update(self, n_steps: int) -> None: ...


@dataclass
class Totals:
    """処理件数の集計。"""

    pages: int = 0
    isbn_count: int = 0
    error_count: int = 0
    duplicate_count: int = 0


def _run_sequential(
    input_filename: str,
    export_file: TextIO,
    on_exclusion: ExclusionHandler | None,
    unique: bool,
    bar: ProgressReporter,
) -> Totals:
    """ダンプを先頭から順に読んで処理する。

    進捗は圧縮ファイル側の読み取り位置で測る。展開後のサイズは読み終わるまで
    分からないが、圧縮ファイルのサイズなら最初から分かるため。
    """
    extractor = Extractor(on_exclusion=on_exclusion, unique=unique)
    with open(input_filename, "rb") as raw, bz2.open(raw, "rt", encoding="utf-8") as dump:
        reported = 0
        for count, record in enumerate(extractor.extract(dump), start=1):
            export_file.write(record.to_json() + "\n")
            if count % PROGRESS_INTERVAL == 0:
                position = raw.tell()
                bar.update(position - reported)
                reported = position
    return Totals(
        extractor.pages, extractor.isbn_count, extractor.error_count, extractor.duplicate_count
    )


def _run_parallel(
    input_filename: str,
    export_file: TextIO,
    ranges: list[tuple[int, int]],
    jobs: int,
    unique: bool,
    bar: ProgressReporter,
) -> Totals:
    """ストリーム単位で並列に処理する。"""
    totals = Totals()
    for result in extract_streams(input_filename, ranges, jobs, unique):
        export_file.write(result.payload)
        totals.pages += result.pages
        totals.isbn_count += result.isbn_count
        totals.error_count += result.error_count
        totals.duplicate_count += result.duplicate_count
        bar.update(result.nbytes)
    return totals


@click.command()
@click.argument("input_filename", type=click.Path(exists=True, dir_okay=False))
@click.argument("export_filename", type=click.Path(exists=False, dir_okay=False))
@click.option("--show-exclusion/--no-show-exclusion", default=False, help="除外した項目を表示する")
@click.option(
    "--unique/--no-unique",
    default=False,
    help="同じページに同じISBNが複数あれば1件にまとめる",
)
@click.option(
    "-j",
    "--jobs",
    type=int,
    default=None,
    help="並列数。既定はCPU数。1を指定すると逐次処理する",
)
def extract_citation(
    input_filename: str,
    export_filename: str,
    show_exclusion: bool,
    unique: bool,
    jobs: int | None,
) -> None:
    """Wikipediaのダンプファイルから出典ISBNを抽出する"""
    click.echo("| extract_citation")
    click.echo("| 処理するファイル:" + click.format_filename(input_filename))
    click.echo("| 出力するファイル:" + click.format_filename(export_filename))

    if jobs is None:
        jobs = os.process_cpu_count() or 1

    # 除外項目はワーカープロセスからは通知できないため、表示する場合は逐次処理する。
    ranges: list[tuple[int, int]] = []
    if jobs > 1 and not show_exclusion:
        ranges = stream_ranges(input_filename)
    parallel = len(ranges) >= MIN_STREAMS_FOR_PARALLEL

    if parallel:
        click.echo(f"| 並列数:{jobs}（ストリーム数:{len(ranges)}）")
    else:
        click.echo("| 逐次処理")

    def show(exclusion: Exclusion) -> None:
        click.echo("\n" + exclusion.format())

    with (
        # newlineを指定しないとWindowsでは "\n" がCRLFに変換され、出力の
        # バイト列が実行環境によって変わってしまう。
        open(export_filename, "w", encoding="utf-8", newline="\n") as export_file,
        click.progressbar(length=Path(input_filename).stat().st_size, label="| 抽出") as bar,
    ):
        if parallel:
            totals = _run_parallel(input_filename, export_file, ranges, jobs, unique, bar)
        else:
            totals = _run_sequential(
                input_filename, export_file, show if show_exclusion else None, unique, bar
            )

    click.echo("count_pages:" + str(totals.pages))
    click.echo("count_isbn:" + str(totals.isbn_count))
    click.echo("count_error:" + str(totals.error_count))
    if unique:
        click.echo("count_duplicate:" + str(totals.duplicate_count))
    click.secho("処理が完了しました", fg="green")


main = extract_citation


if __name__ == "__main__":
    main()
