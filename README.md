citation [![](https://img.shields.io/badge/python-3.14+-blue.svg)](https://docs.python.org/3.14/) 
=========================================================================================================================================================================================
Wikipediaのダンプファイルから出典ISBNを抽出するツール

概要
-----

- 日本語版・英語版Wikipediaのダンプから出典ISBNを抽出
- 抽出したデータはLine-delimited JSON形式で保存
- ある程度の表記ゆれを吸収
- multistreamダンプをストリーム単位で並列処理（28コア環境で約16倍）

依存パッケージのインストール
----

```bash
uv sync
```

コマンドライン
----

```bash
Usage: citation [OPTIONS] INPUT_FILENAME EXPORT_FILENAME

Options:
  --show-exclusion / --no-show-exclusion
                                  除外した項目を表示する
  -j, --jobs INTEGER              並列数。既定はCPU数。1を指定すると逐次処理する
  --help                          Show this message and exit.
```

```bash
wget https://dumps.wikimedia.org/jawiki/20190420/jawiki-20190420-pages-articles-multistream.xml.bz
uv run citation jawiki-20190420-pages-articles-multistream.xml.bz2 citation-jawiki-20190420.jsonl
```

multistreamダンプは100ページごとに独立したbz2ストリームが連結されているため、
ストリーム単位で分割して並列に処理する。抽出の状態はページ境界で閉じるので、
出力は逐次処理と1バイトも変わらない。

抽出結果の集計と比較
----

```bash
# 件数、空のISBN、スコア分布、見出しの内訳
uv run citation-audit stats citation-jawiki-20260401.jsonl

# 2つの出力を比較して、増減した件数と内容が変わった件数を表示
uv run citation-audit diff before.jsonl after.jsonl
```

抽出ロジックに手を入れたときの影響を測るために使う。未対応の問題は
[KNOWN_ISSUES.md](KNOWN_ISSUES.md) を参照。

抽出されるデータ
----

```json
{
  "isbn": "4772212272",
  "raw": "4-7722-1227-2",
  "title": "地理学",
  "score": 2.9,
  "h1": "参考文献",
  "h2": null,
  "is_ref": true
}
```

| 項目   | 型          | 概要                                                                                     |
|--------|-------------|------------------------------------------------------------------------------------------| 
| isbn   | String      | 正規化されたISBN（ISBN-10）                                                              |
| raw    | String      | 解析される元のISBN表記                                                                   |
| title  | String      | Wikipediaのページ名                                                                      |
| score  | Number      | 独自指標により算出されたISBNの正確さ<br>（スコアが低い場合は、誤って検出した場合がある） |
| h1     | String/null | 見出し1                                                                                  |
| h2     | String/null | 見出し2                                                                                  |
| is_ref | Boolean     | 出典であることが明記されているか（作品リストなどではfalse）                              |

処理済みデータのダウンロード
----

| ダンプ                                                                                                                                               | 処理データ                                                                                                    |      件数 |
|------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|----------:|
| [jawiki-20190420-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20190420/jawiki-20190420-pages-articles-multistream.xml.bz2) | [citation-jawiki-20190420.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20190420.jsonl) |   672,155 |
| [jawiki-20190601-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20190601/jawiki-20190601-pages-articles-multistream.xml.bz2) | [citation-jawiki-20190601.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20190601.jsonl) |   679,440 |
| [jawiki-20190801-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20190801/jawiki-20190801-pages-articles-multistream.xml.bz2) | [citation-jawiki-20190801.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20190801.jsonl) |   688,393 |
| [jawiki-20191220-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20191220/jawiki-20191220-pages-articles-multistream.xml.bz2) | [citation-jawiki-20191220.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20191220.jsonl) |   714,273 |
| [jawiki-20200301-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20200301/jawiki-20200301-pages-articles-multistream.xml.bz2) | [citation-jawiki-20200301.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20200301.jsonl) |   728,278 |
| [jawiki-20200801-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20200801/jawiki-20200801-pages-articles-multistream.xml.bz2) | [citation-jawiki-20200801.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20200801.jsonl) |   763,007 |
| [jawiki-20201201-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20201201/jawiki-20201201-pages-articles-multistream.xml.bz2) | [citation-jawiki-20201201.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20201201.jsonl) |   788,068 |
| [jawiki-20210620-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20210620/jawiki-20210620-pages-articles-multistream.xml.bz2) | [citation-jawiki-20210620.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20210620.jsonl) |   839,059 |
| [jawiki-20210920-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20210920/jawiki-20210920-pages-articles-multistream.xml.bz2) | [citation-jawiki-20210920.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20210920.jsonl) |   864,341 |
| [jawiki-20211120-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20211120/jawiki-20211120-pages-articles-multistream.xml.bz2) | [citation-jawiki-20211120.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20211120.jsonl) |   880,591 |
| [enwiki-20211120-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/enwiki/20211120/enwiki-20211120-pages-articles-multistream.xml.bz2) | [citation-enwiki-20211120.jsonl](https://storage.googleapis.com/isbn-citation/citation-enwiki-20211120.jsonl) | 5,116,149 |
| [jawiki-20221220-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20221220/jawiki-20221220-pages-articles-multistream.xml.bz2) | [citation-jawiki-20221220.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20221220.jsonl) |   970,869 |
| [enwiki-20221220-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/enwiki/20221220/enwiki-20221220-pages-articles-multistream.xml.bz2) | [citation-enwiki-20221220.jsonl](https://storage.googleapis.com/isbn-citation/citation-enwiki-20221220.jsonl) | 6,064,901 |
| [jawiki-20240401-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20240401/jawiki-20240401-pages-articles-multistream.xml.bz2) | [citation-jawiki-20240401.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20240401.jsonl) | 1,073,563 |
| [enwiki-20240401-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/enwiki/20240401/enwiki-20240401-pages-articles-multistream.xml.bz2) | [citation-enwiki-20240401.jsonl](https://storage.googleapis.com/isbn-citation/citation-enwiki-20240401.jsonl) | 7,023,140 |
| [jawiki-20241201-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20241201/jawiki-20241201-pages-articles-multistream.xml.bz2) | [citation-jawiki-20241201.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20241201.jsonl) | 1,130,854 |
| [enwiki-20241201-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/enwiki/20241201/enwiki-20241201-pages-articles-multistream.xml.bz2) | [citation-enwiki-20241201.jsonl](https://storage.googleapis.com/isbn-citation/citation-enwiki-20241201.jsonl) | 8,669,996 |
| [jawiki-20250601-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20250601/jawiki-20250601-pages-articles-multistream.xml.bz2) | [citation-jawiki-20250601.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20250601.jsonl) | 1,175,404 |
| [enwiki-20250601-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/enwiki/20250601/enwiki-20250601-pages-articles-multistream.xml.bz2) | [citation-enwiki-20250601.jsonl](https://storage.googleapis.com/isbn-citation/citation-enwiki-20250601.jsonl) | 9,212,634 |

- [日本語版Wikipediaのダンプ](https://dumps.wikimedia.org/jawiki/)
- [英語版Wikipediaのダンプ](https://dumps.wikimedia.org/enwiki/)
- [保存場所の管理](https://console.cloud.google.com/storage/browser/isbn-citation) （管理者用）

注意事項
----

- チェックデジットの一致により、ISBN以外を誤判定する場合があります。ただし、ISBNから参照記事を検索する目的では問題とならないため許容しています
- チェックデジット間違いのISBNは抽出されません
- 抽出精度に関する未対応の問題は [KNOWN_ISSUES.md](KNOWN_ISSUES.md) にまとめてあります

開発
----

```bash
uv sync
uv run pytest
uv run ruff check && uv run ruff format --check
```

`tests/golden/` には現行実装の出力を固定したファイルを置いてある。抽出ロジックを変更すると
ここに差分が出るので、意図した変更かどうかを確認すること。

`slow` マーカーのテストは実ダンプから切り出したフィクスチャ（3,000ページ）を使う。
手元で動かす場合は先に生成する。

```bash
uv run python tests/fixtures/make_fixture.py jawiki-20260401-pages-articles-multistream.xml.bz2
uv run pytest -m slow
```