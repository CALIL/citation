"""multistreamダンプのストリーム境界を扱う。

Wikipediaのmultistreamダンプは、100ページごとに独立したbz2ストリームを連結した
ファイルになっている。ストリームの先頭はバイト境界に揃っているため、シグネチャを
探すだけで分割位置が分かり、それぞれを単体でデコードできる。
"""

import re
from collections.abc import Iterator
from pathlib import Path

#: bz2ストリームの先頭。"BZh" + ブロックサイズ + ブロックマジック "1AY&SY"。
#: ストリーム内部のブロックマジックはビット境界に置かれるため、バイト境界でこの
#: シグネチャが現れる位置はストリームの開始とみなせる。
STREAM_SIGNATURE = re.compile(rb"BZh[1-9]\x31\x41\x59\x26\x53\x59")

#: シグネチャのバイト数。チャンクをまたぐ検出のために重ね幅として使う。
SIGNATURE_LENGTH = 10

SCAN_CHUNK_SIZE = 8 * 1024 * 1024


def iter_stream_offsets(path: str | Path) -> Iterator[int]:
    """ファイル内のbz2ストリームの開始位置を先頭から順に返す。

    チャンクをまたいで現れるシグネチャを取りこぼさないよう、チャンクの末尾を
    次のスキャンに持ち越す。持ち越し部分で重複して検出しないように、直前に
    返した位置より後ろのものだけを返す。
    """
    overlap = SIGNATURE_LENGTH - 1
    with open(path, "rb") as f:
        carried = b""
        base = 0  # carried の先頭がファイル内で何バイト目か
        last = -1
        while chunk := f.read(SCAN_CHUNK_SIZE):
            data = carried + chunk
            for match in STREAM_SIGNATURE.finditer(data):
                offset = base + match.start()
                if offset > last:
                    last = offset
                    yield offset
            base += len(data) - overlap
            carried = data[-overlap:]


def stream_ranges(path: str | Path) -> list[tuple[int, int]]:
    """各ストリームの (開始位置, 終了位置) を返す。

    終了位置は次のストリームの開始位置、最後のストリームはファイル末尾。
    """
    offsets = list(iter_stream_offsets(path))
    if not offsets:
        return []
    bounds = [*offsets, Path(path).stat().st_size]
    return [(bounds[i], bounds[i + 1]) for i in range(len(offsets))]
