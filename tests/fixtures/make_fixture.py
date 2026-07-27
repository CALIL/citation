"""実ダンプの先頭ストリームを切り出して、テスト用の小さなダンプを生成する。

Wikipediaのmultistreamダンプは100ページ単位の独立したbz2ストリームを連結した
ファイルなので、ストリーム境界でそのままバイトコピーすれば有効なダンプになる。

生成物 (mini-jawiki.xml.bz2) はgitignoreしているため、ゴールデンテストを
ローカルで動かす前にこのスクリプトを実行すること。

    uv run python tests/fixtures/make_fixture.py \
        jawiki-20260401-pages-articles-multistream.xml.bz2
"""

import bz2
from itertools import islice, pairwise
from pathlib import Path

import click

from citation.dump import iter_stream_offsets

DEFAULT_OUTPUT = Path(__file__).parent / "mini-jawiki.xml.bz2"


@click.command()
@click.argument("dump_filename", type=click.Path(exists=True, dir_okay=False))
@click.option("--streams", default=30, help="切り出すストリーム数（1ストリーム=100ページ）")
@click.option("--output", default=str(DEFAULT_OUTPUT), type=click.Path(dir_okay=False))
def make_fixture(dump_filename: str, streams: int, output: str) -> None:
    """ダンプの先頭からSTREAMS個のストリームを切り出してOUTPUTに書き出す。"""
    # 先頭ストリームはsiteinfoヘッダで、以降が100ページずつのページストリーム。
    # 切り出す範囲を決めるには、末尾の境界も含めて streams + 2 個の位置が必要。
    offsets = list(islice(iter_stream_offsets(dump_filename), streams + 2))
    if len(offsets) < streams + 2:
        raise click.ClickException(
            f"ストリームが{len(offsets)}個しか見つかりません（{streams + 2}個必要）"
        )

    cut = offsets[streams + 1]
    with open(dump_filename, "rb") as f:
        data = f.read(cut)

    # 切り出した各ストリームが単体でデコードできることを確認する。
    total_pages = sum(
        bz2.decompress(data[start:end]).count(b"<page>") for start, end in pairwise(offsets)
    )

    # 元ダンプの末尾ストリームには</mediawiki>だけが入っている。切り出した分では
    # 閉じタグが欠けるので、同じ構造になるよう独立したストリームとして追加する。
    payload = data + bz2.compress(b"</mediawiki>\n")
    Path(output).write_bytes(payload)

    click.echo(f"| ストリーム数: {streams + 1}（ヘッダ含む）")
    click.echo(f"| ページ数: {total_pages}")
    click.echo(f"| 出力: {output} ({len(payload):,} bytes)")


if __name__ == "__main__":
    make_fixture()
