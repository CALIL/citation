"""コマンドラインの引数処理を検証する。"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from citation.cli import extract_citation


@pytest.mark.parametrize("jobs", ["0", "-5"])
def test_並列数に1未満を指定するとエラーになる(
    jobs: str, synthetic_dump: Path, tmp_path: Path
) -> None:
    result = CliRunner().invoke(
        extract_citation, [str(synthetic_dump), str(tmp_path / "out.jsonl"), "--jobs", jobs]
    )
    assert result.exit_code != 0
    assert "1" in result.output  # 範囲を示すメッセージが出る


def test_並列数に1を指定すると逐次処理になる(synthetic_dump: Path, tmp_path: Path) -> None:
    result = CliRunner().invoke(
        extract_citation, [str(synthetic_dump), str(tmp_path / "out.jsonl"), "--jobs", "1"]
    )
    assert result.exit_code == 0, result.output
    assert "逐次処理" in result.output


def test_uniqueを指定すると重複件数を表示する(synthetic_dump: Path, tmp_path: Path) -> None:
    result = CliRunner().invoke(
        extract_citation, [str(synthetic_dump), str(tmp_path / "out.jsonl"), "--unique"]
    )
    assert result.exit_code == 0, result.output
    assert "count_duplicate:" in result.output


def test_uniqueを指定しなければ重複件数は表示しない(synthetic_dump: Path, tmp_path: Path) -> None:
    result = CliRunner().invoke(extract_citation, [str(synthetic_dump), str(tmp_path / "o.jsonl")])
    assert result.exit_code == 0, result.output
    assert "count_duplicate:" not in result.output
