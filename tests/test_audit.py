"""集計・比較ツールを検証する。"""

import json
from pathlib import Path

from click.testing import CliRunner

from citation.audit import audit


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
        encoding="utf-8",
        newline="\n",
    )


def record(**overrides: object) -> dict:
    """テスト用のレコードを作る。"""
    base = {
        "isbn": "4772212272",
        "raw": "4-7722-1227-2",
        "title": "地理学",
        "score": 2.4,
        "h1": "参考文献",
        "h2": None,
        "is_ref": True,
    }
    return base | overrides


def run(*args: str) -> str:
    result = CliRunner().invoke(audit, list(args))
    assert result.exit_code == 0, result.output
    return result.output


def test_件数と空ISBNを集計する(tmp_path: Path) -> None:
    path = tmp_path / "a.jsonl"
    write_jsonl(path, [record(), record(isbn="", score=0.5), record(title="別の記事")])
    output = run("stats", str(path))
    assert "レコード数     : 3" in output
    assert "空のISBN       : 1" in output
    assert "スコア1.0未満  : 1" in output
    assert "ユニークISBN   : 2" in output  # "4772212272" と ""


def test_差分がなければその旨を伝える(tmp_path: Path) -> None:
    old, new = tmp_path / "old.jsonl", tmp_path / "new.jsonl"
    write_jsonl(old, [record()])
    write_jsonl(new, [record()])
    assert "差分はありません" in run("diff", str(old), str(new))


def test_同じ出典の内容が変わったことを検出する(tmp_path: Path) -> None:
    """ページ名と元表記が同じなら、増減ではなく変更として数える。"""
    old, new = tmp_path / "old.jsonl", tmp_path / "new.jsonl"
    write_jsonl(old, [record(is_ref=False, score=2.4)])
    write_jsonl(new, [record(is_ref=True, score=2.9)])
    output = run("diff", str(old), str(new))
    assert "内容が変わった: 1" in output
    assert "新たに増えた  : 0" in output
    assert "なくなった    : 0" in output


def test_同じページに同じ表記が複数あっても取りこぼさない(tmp_path: Path) -> None:
    """キーが重なる行を畳み込むとき、件数を足し合わせずに上書きしないこと。"""
    old, new = tmp_path / "old.jsonl", tmp_path / "new.jsonl"
    write_jsonl(old, [record(is_ref=False, score=2.4), record(is_ref=False, score=1.5)])
    write_jsonl(new, [record(is_ref=True, score=2.9), record(is_ref=True, score=2.0)])
    output = run("diff", str(old), str(new))
    assert "一致しない行: 追加 2 / 消失 2" in output
    assert "内容が変わった: 2" in output


def test_レコードの増減を検出する(tmp_path: Path) -> None:
    old, new = tmp_path / "old.jsonl", tmp_path / "new.jsonl"
    write_jsonl(old, [record(), record(title="消える記事")])
    write_jsonl(new, [record(), record(title="増える記事")])
    output = run("diff", str(old), str(new))
    assert "レコード数: 2 -> 2 (+0)" in output
    assert "新たに増えた  : 1" in output
    assert "なくなった    : 1" in output
