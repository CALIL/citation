"""コマンドラインの引数処理を検証する。"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from citation import cli
from citation.cli import cgroup_cpu_limit, default_jobs, extract_citation


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("400000 100000\n", 4),  # CPU 4個分のquota
        ("50000 100000\n", 1),  # 0.5個分でも最低1は返す
        ("max 100000\n", None),  # 制限なし
        ("こわれている", None),
        ("400000 0\n", None),  # periodが0
    ],
)
def test_cgroupのCPU制限を読む(
    content: str, expected: int | None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "cpu.max"
    path.write_text(content, encoding="utf-8")
    monkeypatch.setattr(cli, "CGROUP_CPU_MAX", path)
    assert cgroup_cpu_limit() == expected


def test_cgroupが無ければ制限なしとみなす(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """WindowsやmacOS、cgroup v1の環境ではファイルが存在しない。"""
    monkeypatch.setattr(cli, "CGROUP_CPU_MAX", tmp_path / "存在しない")
    assert cgroup_cpu_limit() is None


def test_並列数はCPU制限を超えない(monkeypatch: pytest.MonkeyPatch) -> None:
    """コンテナのquotaがホストの論理CPU数より小さいときはquotaに従う。"""
    monkeypatch.setattr(cli.os, "process_cpu_count", lambda: 64)
    monkeypatch.setattr(cli, "cgroup_cpu_limit", lambda: 8)
    assert default_jobs() == 8


def test_制限が無ければ論理CPU数を使う(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli.os, "process_cpu_count", lambda: 28)
    monkeypatch.setattr(cli, "cgroup_cpu_limit", lambda: None)
    assert default_jobs() == 28


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
