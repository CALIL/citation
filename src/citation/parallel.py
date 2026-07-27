"""multistreamダンプをストリーム単位で並列処理する。

抽出の状態機械はページ境界で状態が閉じるため、ストリームごとに独立して処理しても
逐次処理と同じ結果になる。``ProcessPoolExecutor.map()`` は入力順に結果を返すので、
出力の並び順も変わらない。
"""

import bz2
import io
from collections.abc import Iterator, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from citation.extract import Extractor

#: 一度にワーカーへ渡すストリーム数の係数。並列数のこの倍数ずつ投入する。
#: 全ストリームを一括で投入すると、順序を保つために完了済みの結果がメモリに
#: 積み上がってしまうため、小分けにして上限を設ける。
BATCH_FACTOR = 8

#: これ未満のストリーム数なら並列化する意味がないため逐次処理に任せる。
MIN_STREAMS_FOR_PARALLEL = 2


@dataclass(frozen=True, slots=True)
class StreamResult:
    """ストリーム1本分の抽出結果。"""

    payload: str
    """そのまま出力ファイルに書けるJSONL。"""

    pages: int
    isbn_count: int
    error_count: int

    nbytes: int
    """このストリームが占める圧縮後のバイト数（進捗表示用）。"""


def _extract_stream(task: tuple[str, int, int]) -> StreamResult:
    """ワーカープロセスでストリーム1本を処理する。"""
    path, start, end = task
    with open(path, "rb") as f:
        f.seek(start)
        compressed = f.read(end - start)

    # bz2.open(..., "rt") と同じ行分割にするため TextIOWrapper を通す。
    # str.splitlines() はU+2028などでも行を分けてしまい、逐次処理と結果がずれる。
    stream = io.TextIOWrapper(io.BytesIO(bz2.decompress(compressed)), encoding="utf-8")

    extractor = Extractor()
    payload = "".join(record.to_json() + "\n" for record in extractor.extract(stream))
    return StreamResult(
        payload=payload,
        pages=extractor.pages,
        isbn_count=extractor.isbn_count,
        error_count=extractor.error_count,
        nbytes=end - start,
    )


def extract_streams(
    path: str | Path, ranges: Sequence[tuple[int, int]], jobs: int
) -> Iterator[StreamResult]:
    """ストリームを並列に処理し、ダンプ内の順序どおりに結果を返す。

    :param path: ダンプファイル
    :param ranges: :func:`citation.dump.stream_ranges` が返すストリームの範囲
    :param jobs: ワーカープロセス数
    """
    tasks = [(str(path), start, end) for start, end in ranges]
    batch_size = jobs * BATCH_FACTOR

    with ProcessPoolExecutor(max_workers=jobs) as pool:
        for i in range(0, len(tasks), batch_size):
            yield from pool.map(_extract_stream, tasks[i : i + batch_size])
