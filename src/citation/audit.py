"""抽出結果のJSONLを集計・比較するツール。

KNOWN_ISSUES.md に挙げた不具合に手を入れたとき、出力がどう変わるかを数値で
確かめるために使う。修正前後の2本を ``citation-audit diff`` にかければ、
何件増えて何件減り、どのレコードの内容が変わったかが分かる。
"""

import json
from collections import Counter
from collections.abc import Iterator

import click

#: 差分表示に出すサンプルの件数。
SAMPLE_SIZE = 5

#: 見出しの集計で表示する上位件数。
TOP_HEADINGS = 15


def _iter_records(path: str) -> Iterator[dict]:
    with open(path, encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)


def _iter_lines(path: str) -> Iterator[str]:
    """改行を除いた各行を返す。"""
    with open(path, encoding="utf-8") as f:
        for line in f:
            yield line.rstrip("\n")


def _record_key(line: str) -> tuple[str, str]:
    """同じ出典を指すレコードかどうかを見分けるキー。"""
    record = json.loads(line)
    return record["title"], record["raw"]


def _count_by_key(lines: Counter[str]) -> Counter[tuple[str, str]]:
    """行ごとの集計を (ページ名, 元表記) 単位に畳み込む。

    1つのページに同じ表記が複数回現れることがあるため、キーが重なったら
    足し合わせる必要がある。
    """
    keys: Counter[tuple[str, str]] = Counter()
    for line, count in lines.items():
        keys[_record_key(line)] += count
    return keys


@click.group()
def audit() -> None:
    """抽出結果のJSONLを集計・比較する"""


@audit.command()
@click.argument("filename", type=click.Path(exists=True, dir_okay=False))
def stats(filename: str) -> None:
    """JSONLの内容を集計する"""
    total = 0
    empty_isbn = 0
    unique_isbn: set[str] = set()
    scores: Counter[float] = Counter()
    ref_flags: Counter[bool] = Counter()
    headings: Counter[str | None] = Counter()
    digit_lengths: Counter[int] = Counter()

    for record in _iter_records(filename):
        total += 1
        if not record["isbn"]:
            empty_isbn += 1
        unique_isbn.add(record["isbn"])
        scores[record["score"]] += 1
        ref_flags[record["is_ref"]] += 1
        headings[record["h1"]] += 1
        digits = record["raw"].replace("-", "").replace(" ", "")
        digit_lengths[len(digits)] += 1

    click.echo(f"レコード数     : {total:,}")
    click.echo(f"ユニークISBN   : {len(unique_isbn):,}")
    click.echo(f"空のISBN       : {empty_isbn:,}")
    click.echo(f"出典と判定     : {ref_flags[True]:,} / 出典ではない: {ref_flags[False]:,}")

    below = sum(count for score, count in scores.items() if score < 1.0)
    click.echo(f"スコア1.0未満  : {below:,}")

    click.echo("\nスコアの分布:")
    for score, count in sorted(scores.items()):
        click.echo(f"  {score:>5} : {count:>10,}")

    click.echo("\n元表記の桁数:")
    for length, count in sorted(digit_lengths.items()):
        click.echo(f"  {length:>3}桁 : {count:>10,}")

    click.echo(f"\n見出し1の上位{TOP_HEADINGS}件:")
    for heading, count in headings.most_common(TOP_HEADINGS):
        click.echo(f"  {count:>10,}  {heading}")


@audit.command()
@click.argument("old_filename", type=click.Path(exists=True, dir_okay=False))
@click.argument("new_filename", type=click.Path(exists=True, dir_okay=False))
def diff(old_filename: str, new_filename: str) -> None:
    """2つのJSONLを比較して差分の内訳を表示する

    両方のファイルを丸ごとメモリに載せるため、数百万件を比較する場合は
    それなりのメモリを使う。
    """
    old_lines = Counter(_iter_lines(old_filename))
    new_lines = Counter(_iter_lines(new_filename))

    old_total = sum(old_lines.values())
    new_total = sum(new_lines.values())
    click.echo(f"レコード数: {old_total:,} -> {new_total:,} ({new_total - old_total:+,})")

    added = new_lines - old_lines
    removed = old_lines - new_lines
    if not added and not removed:
        click.secho("差分はありません", fg="green")
        return

    click.echo(f"一致しない行: 追加 {sum(added.values()):,} / 消失 {sum(removed.values()):,}")

    # 同じ (ページ名, 元表記) が両方に現れるなら、レコードが増減したのではなく
    # スコアや出典判定といった中身が変わったということ。
    added_keys = _count_by_key(added)
    removed_keys = _count_by_key(removed)
    modified = added_keys & removed_keys
    gained = added_keys - removed_keys
    lost = removed_keys - added_keys

    click.echo(f"  内容が変わった: {sum(modified.values()):,}")
    click.echo(f"  新たに増えた  : {sum(gained.values()):,}")
    click.echo(f"  なくなった    : {sum(lost.values()):,}")

    _show_samples("内容が変わった例", modified, added, removed)
    _show_samples("新たに増えた例", gained, added, None)
    _show_samples("なくなった例", lost, None, removed)


def _show_samples(
    label: str,
    keys: Counter[tuple[str, str]],
    added: Counter[str] | None,
    removed: Counter[str] | None,
) -> None:
    """差分のサンプルを数件表示する。"""
    if not keys:
        return
    click.echo(f"\n{label}:")
    targets = {key for key, _ in keys.most_common(SAMPLE_SIZE)}
    shown = 0
    for source, mark in ((removed, "-"), (added, "+")):
        if source is None:
            continue
        for line in source:
            if _record_key(line) in targets:
                click.echo(f"  {mark} {line}")
                shown += 1
                if shown >= SAMPLE_SIZE * 2:
                    return


main = audit


if __name__ == "__main__":
    main()
