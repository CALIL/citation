"""過去のダンプを集めて、最新の抽出ロジックで再処理する。

公式サイトは直近数か月のダンプしか置いていないため、過去分は Internet Archive の
wikimediadownloads コレクションと公式のヒストリカルアーカイブから取る。年によって
取得元も配布形式（multistreamの有無）も違うので、対象を :data:`TARGETS` に集めて
一元管理する。

    uv run python tools/backfill.py list
    uv run python tools/backfill.py run --wiki jawiki
    uv run python tools/backfill.py table

fetch と extract は冪等。ダンプがサイズもmd5も一致していれば取り直さず、出力が既に
あれば再処理しない。全部で200GB超・数時間かかる作業なので、途中で止めて再実行できる
ことを前提にしている。
"""

import base64
import hashlib
import json
import shutil
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import click

#: ダンプと出力を置くディレクトリ。どちらも .gitignore 済み。
ROOT = Path(__file__).resolve().parent.parent

#: 処理した件数を残すファイル。README の表は table サブコマンドでここから作る。
COUNTS_PATH = Path(__file__).with_name("backfill-counts.tsv")

IA_DOWNLOAD_URL = "https://archive.org/download/{item}/{name}"
IA_METADATA_URL = "https://archive.org/metadata/{item}/files"
OFFICIAL_URL = "https://dumps.wikimedia.org/{wiki}/{date}/{name}"
ARCHIVE_URL = "https://dumps.wikimedia.org/archive/{wiki}/{date}/{name}"
GCS_URL = "https://storage.googleapis.com/isbn-citation/{name}"

#: 素の urllib のUser-Agentは dumps.wikimedia.org から403で弾かれる。Wikimediaの
#: User-Agentポリシーに従って、連絡先の分かる名前を送る。
USER_AGENT = "citation-backfill/1.0 (https://github.com/CALIL/citation; ryuuji@calil.jp)"

#: md5を計算するときの読み取り単位。
CHUNK_SIZE = 8 * 1024 * 1024

#: ``extract --watch`` がダウンロードの完了を確認しにいく間隔（秒）。
WATCH_INTERVAL = 120


@dataclass(frozen=True, slots=True)
class Target:
    """再処理するダンプ1本。

    :param kind: 取得元。``ia`` はInternet Archive、``official`` は公式の通常ディレクトリ、
        ``archive`` は公式のヒストリカルアーカイブ、``gcs`` は過去に自分で保存した
        `gs://isbn-citation`、``local`` はどこにも無く手元のファイルしか残っていないもの
    :param mode: ``multi`` はmultistream（ストリーム単位で並列処理できる）、``single`` は
        multistreamが無かった時代のダンプで逐次処理になる
    """

    year: int
    wiki: str
    date: str
    kind: str
    mode: str
    optional: bool = False
    """年次シリーズには要らないが、既刊データを最新ロジックに揃えるために処理するもの。"""

    @property
    def dump_name(self) -> str:
        if self.mode == "multi":
            return f"{self.wiki}-{self.date}-pages-articles-multistream.xml.bz2"
        return f"{self.wiki}-{self.date}-pages-articles.xml.bz2"

    @property
    def output_name(self) -> str:
        return f"citation-{self.wiki}-{self.date}.jsonl"

    @property
    def dump_path(self) -> Path:
        return ROOT / self.dump_name

    @property
    def output_path(self) -> Path:
        return ROOT / self.output_name

    @property
    def verified_path(self) -> Path:
        """md5照合が済んだことを示す印。ダウンロード中との区別に使う。"""
        return ROOT / f"{self.dump_name}.verified"

    @property
    def item(self) -> str:
        return f"{self.wiki}-{self.date}"

    @property
    def url(self) -> str | None:
        """ダンプのURL。配布が終わっているものは None。"""
        if self.kind == "ia":
            return IA_DOWNLOAD_URL.format(item=self.item, name=self.dump_name)
        if self.kind == "official":
            return OFFICIAL_URL.format(wiki=self.wiki, date=self.date, name=self.dump_name)
        if self.kind == "archive":
            return ARCHIVE_URL.format(wiki=self.wiki, date=self.date, name=self.dump_name)
        if self.kind == "gcs":
            return GCS_URL.format(name=self.dump_name)
        return None

    @property
    def checksums_url(self) -> str | None:
        """公式が置いているmd5sums.txtのURL。"""
        name = f"{self.wiki}-{self.date}-md5sums.txt"
        if self.kind == "official":
            return OFFICIAL_URL.format(wiki=self.wiki, date=self.date, name=name)
        if self.kind == "archive":
            return ARCHIVE_URL.format(wiki=self.wiki, date=self.date, name=name)
        return None


#: 再処理する対象。年1本を基本に、入手できる最古まで遡る。
#:
#: 2012・2013・2023はミラーが存在せず入手できない。Internet Archive は2022年5月で
#: ダンプ本体のミラーを止めており、2023年以降の過去分はどこにも残っていない。
#: 英語版の2011年（enwiki-20111007）はアイテムが空で中身が無い。
#:
#: 2011年以前は export-0.3/0.5 で ``<ns>`` を持たないため、記事以外の名前空間も
#: 抽出対象に入る（KNOWN_ISSUES.md に注記）。
TARGETS: list[Target] = [
    Target(2008, "enwiki", "20080103", "archive", "single"),
    Target(2009, "enwiki", "20090618", "ia", "single"),
    Target(2010, "enwiki", "20100312", "archive", "single"),
    Target(2011, "jawiki", "20110921", "ia", "single"),
    # 2014年だけは日付が揃わない（ja 20141211 / en 20141208）。
    Target(2014, "jawiki", "20141211", "ia", "multi"),
    Target(2014, "enwiki", "20141208", "ia", "multi"),
    Target(2015, "jawiki", "20150602", "ia", "multi"),
    Target(2015, "enwiki", "20150602", "ia", "multi"),
    Target(2016, "jawiki", "20160601", "ia", "multi"),
    Target(2016, "enwiki", "20160601", "ia", "multi"),
    Target(2017, "jawiki", "20170601", "ia", "multi"),
    Target(2017, "enwiki", "20170601", "ia", "multi"),
    Target(2018, "jawiki", "20180901", "ia", "multi"),
    Target(2018, "enwiki", "20180901", "ia", "multi"),
    Target(2019, "jawiki", "20190201", "ia", "multi"),
    Target(2019, "enwiki", "20190201", "ia", "multi"),
    Target(2020, "jawiki", "20200920", "ia", "multi"),
    Target(2020, "enwiki", "20200920", "ia", "multi"),
    Target(2021, "jawiki", "20210620", "ia", "multi"),
    Target(2021, "enwiki", "20210620", "ia", "multi"),
    Target(2022, "jawiki", "20220501", "ia", "multi"),
    Target(2022, "enwiki", "20220501", "ia", "multi"),
    # 2024・2025のダンプは公式からもIAからも消えており、手元のファイルしか残っていない。
    Target(2024, "jawiki", "20240401", "local", "multi"),
    Target(2024, "enwiki", "20240401", "local", "multi"),
    Target(2024, "jawiki", "20241201", "local", "multi", optional=True),
    Target(2024, "enwiki", "20241201", "local", "multi", optional=True),
    Target(2025, "jawiki", "20250601", "local", "multi"),
    Target(2025, "enwiki", "20250601", "local", "multi"),
    Target(2026, "jawiki", "20260401", "official", "multi"),
    Target(2026, "enwiki", "20260401", "official", "multi"),
    # 既刊の非年次日付。IAに残っているものはIAから取る（下り課金がかからない）。
    Target(2020, "jawiki", "20201201", "ia", "multi", optional=True),
    Target(2021, "jawiki", "20210920", "ia", "multi", optional=True),
    Target(2021, "jawiki", "20211120", "ia", "multi", optional=True),
    Target(2021, "enwiki", "20211120", "ia", "multi", optional=True),
    # 公式もIAも消えているが、2019年から自分でGCSに保存していたぶんが残っている。
    # gs://isbn-citation にあるのはjawikiのダンプだけで、enwikiは1本も無い。
    Target(2019, "jawiki", "20190420", "gcs", "multi", optional=True),
    Target(2019, "jawiki", "20190601", "gcs", "multi", optional=True),
    Target(2019, "jawiki", "20190801", "gcs", "multi", optional=True),
    Target(2019, "jawiki", "20191220", "gcs", "multi", optional=True),
    Target(2020, "jawiki", "20200301", "gcs", "multi", optional=True),
    Target(2020, "jawiki", "20200801", "gcs", "multi", optional=True),
    Target(2022, "jawiki", "20221220", "gcs", "multi", optional=True),
]


def _select(
    wiki: str | None,
    year: int | None,
    date: str | None,
    optional: bool,
    only_optional: bool = False,
) -> list[Target]:
    """絞り込み条件に合う対象を、日付順（同じ日付なら日本語版が先）に返す。

    ``only_optional`` は年次シリーズ以外だけを選ぶ。年次シリーズを処理している
    プロセスと同時に走らせても、同じ出力を二重に書かないようにするために使う。
    """
    # 日付を明示したときと --only-optional のときは、年次シリーズ以外も対象に入れる。
    include_optional = optional or only_optional or date is not None
    targets = [
        target
        for target in TARGETS
        if (wiki is None or target.wiki == wiki)
        and (year is None or target.year == year)
        and (date is None or target.date == date)
        and (include_optional or not target.optional)
        and (not only_optional or target.optional)
    ]
    return sorted(targets, key=lambda target: (target.date, target.wiki != "jawiki"))


def _open(url: str, method: str = "GET"):
    """User-Agentを付けてHTTPリクエストを投げる。"""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method=method)
    return urllib.request.urlopen(request, timeout=120)


def _remote_info(target: Target) -> tuple[int | None, str | None]:
    """取得元が公開しているサイズとmd5を返す。分からないものは None。"""
    if target.kind == "ia":
        with _open(IA_METADATA_URL.format(item=target.item)) as response:
            files = json.load(response).get("result") or []
        for entry in files:
            if entry.get("name") == target.dump_name:
                size = entry.get("size")
                return (int(size) if size else None), entry.get("md5")
        return None, None

    if target.kind == "gcs":
        # GCSはmd5をbase64で x-goog-hash に載せる。crc32cと2行に分かれて来る。
        with _open(target.url, method="HEAD") as response:
            size = int(response.headers["Content-Length"])
            hashes = response.headers.get_all("x-goog-hash") or []
        for line in hashes:
            for part in line.split(","):
                name, _, value = part.strip().partition("=")
                if name == "md5":
                    return size, base64.b64decode(value).hex()
        return size, None

    size = None
    with _open(target.url, method="HEAD") as response:
        length = response.headers.get("Content-Length")
        if length:
            size = int(length)

    with _open(target.checksums_url) as response:
        text = response.read().decode()
    for line in text.splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[1] == target.dump_name:
            return size, fields[0]
    return size, None


def _local_md5(path: Path) -> str:
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "md5").hexdigest()


def _curl(url: str, path: Path, quiet: bool) -> None:
    """途中から再開できるダウンロード。

    IAのノードは時折503を返すため、リトライを厚めにしておく。
    """
    curl = shutil.which("curl")
    if curl is None:
        raise click.ClickException("curlが見つかりません")
    command = [
        curl,
        "--location",
        "--continue-at",
        "-",
        "--retry",
        "8",
        "--retry-delay",
        "5",
        "--retry-all-errors",
        "--fail",
        "--user-agent",
        USER_AGENT,
        "--output",
        str(path),
        "--progress-bar" if not quiet else "--no-progress-meter",
        url,
    ]
    subprocess.run(command, check=True)


def _fetch(target: Target, quiet: bool = False) -> None:
    """ダンプを手元に用意する。既に完全なものがあれば何もしない。

    照合が済んだら :attr:`Target.verified_path` に印を置く。ダウンロード中の
    ファイルを処理してしまわないよう、抽出側はこの印を見る。
    """
    if target.kind == "local":
        if not target.dump_path.exists():
            raise click.ClickException(
                f"{target.dump_name} が見つかりません。"
                "このダンプは配布が終わっているため再取得できません"
            )
        return

    if target.verified_path.exists():
        click.echo(f"| 照合済みのためスキップ: {target.dump_name}")
        return

    size, expected = _remote_info(target)
    for attempt in (1, 2):
        complete = (
            target.dump_path.exists()
            and size is not None
            and target.dump_path.stat().st_size == size
        )
        if not complete:
            click.echo(f"| 取得: {target.dump_name}")
            _curl(target.url, target.dump_path, quiet)

        if expected is None:
            click.echo(f"| md5が公開されていないため照合を省略: {target.dump_name}")
            target.verified_path.write_text("md5なし\n", encoding="utf-8", newline="\n")
            return
        digest = _local_md5(target.dump_path)
        if digest == expected:
            click.echo(f"| md5一致: {target.dump_name}")
            target.verified_path.write_text(digest + "\n", encoding="utf-8", newline="\n")
            return

        click.echo(f"| md5不一致（{attempt}回目）: {target.dump_name} を破棄して取り直す")
        target.dump_path.unlink()

    raise click.ClickException(f"{target.dump_name} のmd5が2回とも一致しませんでした")


def _extracted(target: Target) -> bool:
    return target.output_path.exists() and target.output_path.stat().st_size > 0


def _fetched(target: Target) -> bool:
    """ダンプが揃っているか。ダウンロード途中のファイルを処理しないための判定。"""
    return target.kind == "local" or target.verified_path.exists()


def _extract(target: Target) -> None:
    """ダンプを最新ロジックで処理する。

    multistreamでないダンプは並列化できない。ストリーム境界の全走査も無駄なので
    逐次処理を明示する。
    """
    command = [sys.executable, "-m", "citation.cli", str(target.dump_path), str(target.output_path)]
    if target.mode == "single":
        command += ["-j", "1"]
    subprocess.run(command, check=True, cwd=ROOT)


def _count_records(path: Path) -> int:
    total = 0
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            total += chunk.count(b"\n")
    return total


def _load_counts() -> dict[tuple[str, str], int]:
    if not COUNTS_PATH.exists():
        return {}
    counts = {}
    for line in COUNTS_PATH.read_text(encoding="utf-8").splitlines()[1:]:
        wiki, date, records = line.split("\t")
        counts[(wiki, date)] = int(records)
    return counts


def _save_counts(counts: dict[tuple[str, str], int]) -> None:
    lines = ["wiki\tdate\trecords"]
    lines += [f"{wiki}\t{date}\t{records}" for (wiki, date), records in sorted(counts.items())]
    COUNTS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _record_count(target: Target) -> int:
    counts = _load_counts()
    records = _count_records(target.output_path)
    counts[(target.wiki, target.date)] = records
    _save_counts(counts)
    return records


def _gigabytes(size: int) -> str:
    return f"{size / 1e9:.2f}GB"


wiki_option = click.option("--wiki", type=click.Choice(["jawiki", "enwiki"]), help="言語版で絞る")
year_option = click.option("--year", type=int, help="年で絞る")
date_option = click.option("--date", help="ダンプの日付で絞る（指定すると任意対象も含む）")
optional_option = click.option(
    "--include-optional/--no-include-optional",
    "optional",
    default=False,
    help="年次シリーズ以外（既刊データを揃えるための日付）も対象にする",
)
only_optional_option = click.option(
    "--only-optional",
    is_flag=True,
    help="年次シリーズ以外だけを対象にする（年次シリーズの処理と並走させるとき）",
)


@click.group()
def backfill() -> None:
    """過去ダンプの取得と再処理。"""


@backfill.command("list")
@wiki_option
@year_option
@date_option
@optional_option
@only_optional_option
def list_targets(
    wiki: str | None, year: int | None, date: str | None, optional: bool, only_optional: bool
) -> None:
    """対象と手元の状態を一覧表示する。"""
    counts = _load_counts()
    click.echo(f"{'年':<6}{'wiki':<8}{'日付':<10}{'形式':<8}{'ダンプ':<12}{'出力':<12}件数")
    for target in _select(wiki, year, date, optional, only_optional):
        dump = _gigabytes(target.dump_path.stat().st_size) if target.dump_path.exists() else "-"
        output = (
            _gigabytes(target.output_path.stat().st_size) if target.output_path.exists() else "-"
        )
        records = counts.get((target.wiki, target.date))
        click.echo(
            f"{target.year:<6}{target.wiki:<8}{target.date:<10}{target.mode:<8}"
            f"{dump:<12}{output:<12}{f'{records:,}' if records is not None else '-'}"
        )


@backfill.command()
@wiki_option
@year_option
@date_option
@optional_option
@only_optional_option
@click.option("-j", "--jobs", type=click.IntRange(min=1), default=2, help="同時ダウンロード数")
def fetch(
    wiki: str | None,
    year: int | None,
    date: str | None,
    optional: bool,
    only_optional: bool,
    jobs: int,
) -> None:
    """ダンプをダウンロードしてmd5を照合する。"""
    targets = _select(wiki, year, date, optional, only_optional)
    if jobs == 1:
        for target in targets:
            _fetch(target)
        return
    # 進捗バーが混ざって読めなくなるので、並列時は消して完了ログだけ出す。
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        for _ in pool.map(lambda target: _fetch(target, quiet=True), targets):
            pass


@backfill.command()
@wiki_option
@year_option
@date_option
@optional_option
@only_optional_option
def verify(
    wiki: str | None, year: int | None, date: str | None, optional: bool, only_optional: bool
) -> None:
    """手元にあるダンプのmd5を照合して、処理してよい印を付ける。

    別のプロセスがダウンロードしている場合や、印を付ける前のコードで取得した場合に使う。
    サイズが取得元と一致しないものはまだ途中とみなして触らない。
    """
    for target in _select(wiki, year, date, optional, only_optional):
        if target.kind == "local" or target.verified_path.exists():
            continue
        if not target.dump_path.exists():
            continue
        size, expected = _remote_info(target)
        actual = target.dump_path.stat().st_size
        if size is not None and actual != size:
            click.echo(f"| ダウンロード中: {target.dump_name}（{actual:,}/{size:,}）")
            continue
        digest = _local_md5(target.dump_path)
        if expected is None or digest == expected:
            target.verified_path.write_text(digest + "\n", encoding="utf-8", newline="\n")
            click.echo(f"| 照合できた: {target.dump_name}")
        else:
            click.echo(f"| md5不一致: {target.dump_name}（取り直しが必要）")


@backfill.command()
@wiki_option
@year_option
@date_option
@optional_option
@only_optional_option
@click.option("--watch", is_flag=True, help="ダウンロードが終わるのを待ちながら処理し続ける")
def extract(
    wiki: str | None,
    year: int | None,
    date: str | None,
    optional: bool,
    only_optional: bool,
    watch: bool,
) -> None:
    """手元のダンプを処理して件数を記録する。

    ``--watch`` を付けると、ダウンロードが済んだものから順に処理して、残りが無くなるまで
    待ち続ける。抽出はCPUを使い切るので、この1プロセスに直列で処理させる。
    """
    targets = _select(wiki, year, date, optional, only_optional)
    counts = _load_counts()
    # 手動で処理した出力など、件数が記録されていないものを先に数えておく。
    for target in targets:
        if _extracted(target) and (target.wiki, target.date) not in counts:
            click.echo(f"| {target.output_name}: {_record_count(target):,}件")

    while True:
        for target in targets:
            if _extracted(target) or not _fetched(target):
                continue
            _extract(target)
            click.echo(f"| {target.output_name}: {_record_count(target):,}件")

        pending = [target for target in targets if not _extracted(target)]
        if not watch or not pending:
            break
        click.echo(f"| 取得待ち{len(pending)}本: {', '.join(t.dump_name for t in pending[:3])} …")
        time.sleep(WATCH_INTERVAL)


@backfill.command()
@wiki_option
@year_option
@date_option
@optional_option
@click.option("--delete-dump", is_flag=True, help="処理に成功したらダンプを削除する")
def run(
    wiki: str | None, year: int | None, date: str | None, optional: bool, delete_dump: bool
) -> None:
    """取得から処理まで通す。"""
    for target in _select(wiki, year, date, optional):
        _fetch(target)
        if not _extracted(target):
            _extract(target)
        click.echo(f"| {target.output_name}: {_record_count(target):,}件")
        if delete_dump and target.kind != "local":
            target.dump_path.unlink(missing_ok=True)
            click.echo(f"| ダンプを削除: {target.dump_name}")


@backfill.command()
@optional_option
def table(optional: bool) -> None:
    """READMEの表の行をMarkdownで出力する。"""
    counts = _load_counts()
    for target in _select(None, None, None, optional):
        records = counts.get((target.wiki, target.date))
        if records is None:
            continue
        # ダンプのリンクは実際に取得できる場所へ張る。公式に残っていない日付は
        # Internet Archive か gs://isbn-citation のコピーを指す。
        url = target.url
        dump = f"[{target.item}]({url})" if url else target.item
        output = f"[{target.output_name}]({GCS_URL.format(name=target.output_name)})"
        click.echo(f"| {dump} | {output} | {records:,} |")


if __name__ == "__main__":
    backfill()
