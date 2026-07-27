"""リファクタ前の実装と出力が一致することを確認する。

単一スクリプトを分割する前に記録したゴールデンと突き合わせ、構造変更で挙動が
変わっていないことを保証する。
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from citation.cli import extract_citation
from conftest import GOLDEN_DIR, digest, normalized_bytes


def run_cli(dump: Path, output: Path) -> None:
    result = CliRunner().invoke(extract_citation, [str(dump), str(output)])
    assert result.exit_code == 0, result.output


def test_syntheticの出力がゴールデンと一致する(synthetic_dump: Path, tmp_path: Path) -> None:
    output = tmp_path / "synthetic.jsonl"
    run_cli(synthetic_dump, output)
    assert normalized_bytes(output) == normalized_bytes(GOLDEN_DIR / "synthetic.jsonl")


@pytest.mark.slow
def test_miniダンプの出力がゴールデンと一致する(mini_dump: Path, tmp_path: Path) -> None:
    output = tmp_path / "mini-jawiki.jsonl"
    run_cli(mini_dump, output)
    expected = (GOLDEN_DIR / "mini-jawiki.sha256").read_text(encoding="utf-8").split()[0]
    assert digest(output) == expected
