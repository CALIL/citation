"""テスト共通のフィクスチャとヘルパ。"""

import bz2
import hashlib
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
GOLDEN_DIR = Path(__file__).parent / "golden"


def normalized_bytes(path: Path) -> bytes:
    """改行コードをLFに揃えて読む。

    出力ファイルの改行はプラットフォームによって変わるため、ゴールデン比較では
    その差を無視する。
    """
    return path.read_bytes().replace(b"\r\n", b"\n")


def digest(path: Path) -> str:
    """改行を正規化した上でのSHA-256。"""
    return hashlib.sha256(normalized_bytes(path)).hexdigest()


@pytest.fixture(scope="session")
def synthetic_dump(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """手書きフィクスチャを、実ダンプと同じbz2形式にしたもの。"""
    dump = tmp_path_factory.mktemp("dump") / "synthetic.xml.bz2"
    dump.write_bytes(bz2.compress((FIXTURES_DIR / "synthetic.xml").read_bytes()))
    return dump


@pytest.fixture(scope="session")
def mini_dump() -> Path:
    """実ダンプから切り出したフィクスチャ。未生成ならテストをスキップする。"""
    path = FIXTURES_DIR / "mini-jawiki.xml.bz2"
    if not path.exists():
        pytest.skip("tests/fixtures/make_fixture.py で生成してください")
    return path
