citation [![](https://img.shields.io/badge/python-3.12+-blue.svg)](https://docs.python.org/3.12/) [![Maintainability](https://api.codeclimate.com/v1/badges/d2ff9760abb138cd70bc/maintainability)](https://codeclimate.com/github/CALIL/citation/maintainability)
=========================================================================================================================================================================================
Wikipediaのダンプファイルから出典ISBNを抽出するツール

概要
-----

- 日本語版Wikipediaのダンプから出典ISBNを抽出
- 抽出したデータはLine-delimited JSON形式で保存
- ある程度の表記ゆれを吸収

依存パッケージのインストール
----

```bash
poetry install
```

コマンドライン
----

```bash
Usage: citation.py [OPTIONS] INPUT_FILENAME EXPORT_FILENAME

Options:
  --show-exclusion / --no-show-exclusion
                                  除外した項目を表示する
  --help                          Show this message and exit.
```

```bash
wget https://dumps.wikimedia.org/jawiki/20190420/jawiki-20190420-pages-articles-multistream.xml.bz
poetry run python citation.py jawiki-20190420-pages-articles-multistream.xml.bz2 citation-jawiki-20190420.jsonl
```

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

| 項目     | 型           | 概要                                               |
|--------|-------------|--------------------------------------------------| 
| isbn   | String      | 正規化されたISBN（ISBN-10）                              |
| raw    | String      | 解析される元のISBN表記                                    |
| title  | String      | Wikipediaのページ名                                   |
| score  | Number      | 独自指標により算出されたISBNの正確さ<br>（スコアが低い場合は、誤って検出した場合がある） |
| h1     | String/null | 見出し1                                             |
| h2     | String/null | 見出し2                                             |
| is_ref | Boolean     | 出典であることが明記されているか（作品リストなどではfalse）                 |

処理済みデータのダウンロード
----

| ダンプ                                                                                                                                                  | 処理データ                                                                                                         |        件数 |
|------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|----------:|
| [jawiki-20190420-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20190420/jawiki-20190420-pages-articles-multistream.xml.bz2) | [citation-jawiki-20190420.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20190420.jsonl) |   672,155 |
| [jawiki-20190601-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20190601/jawiki-20190601-pages-articles-multistream.xml.bz2) | [citation-jawiki-20190601.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20190601.jsonl) |   679,440 |
| [jawiki-20190801-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20190801/jawiki-20190801-pages-articles-multistream.xml.bz2) | [citation-jawiki-20190801.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20190801.jsonl) |   688,393 |
| [jawiki-20191220-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20191220/jawiki-20191220-pages-articles-multistream.xml.bz2) | [citation-jawiki-20191220.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20191220.jsonl) |   714,273 |
| [jawiki-20200301-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20200301/jawiki-20200301-pages-articles-multistream.xml.bz2) | [citation-jawiki-20200301.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20200301.jsonl) |   728,278 |
| [jawiki-20200801-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20200801/jawiki-20200801-pages-articles-multistream.xml.bz2) | [citation-jawiki-20200801.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20200801.jsonl) |   763,007 |
| [jawiki-20201201-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20201201/jawiki-20201201-pages-articles-multistream.xml.bz2) | [citation-jawiki-20201201.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20201201.jsonl) |   788,068 |
| [jawiki-20210620-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20201201/jawiki-20210620-pages-articles-multistream.xml.bz2) | [citation-jawiki-20210620.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20210620.jsonl) |   839,059 |
| [jawiki-20210920-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20210920/jawiki-20210920-pages-articles-multistream.xml.bz2) | [citation-jawiki-20210920.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20210920.jsonl) |   864,341 |
| [jawiki-20211120-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20211120/jawiki-20211120-pages-articles-multistream.xml.bz2) | [citation-jawiki-20211120.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20211120.jsonl) |   880,591 |
| [enwiki-20211120-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/enwiki/20211120/enwiki-20211120-pages-articles-multistream.xml.bz2) | [citation-enwiki-20211120.jsonl](https://storage.googleapis.com/isbn-citation/citation-enwiki-20211120.jsonl) | 5,116,149 |
| [jawiki-20221220-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20221220/jawiki-20221220-pages-articles-multistream.xml.bz2) | [citation-jawiki-20221220.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20221220.jsonl) |   970,869 |
| [enwiki-20221220-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/enwiki/20221220/enwiki-20221220-pages-articles-multistream.xml.bz2) | [citation-enwiki-20221220.jsonl](https://storage.googleapis.com/isbn-citation/citation-enwiki-20221220.jsonl) | 6,064,901 |
| [jawiki-20240401-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20240401/jawiki-20240401-pages-articles-multistream.xml.bz2) | [citation-jawiki-20240401.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20240401.jsonl) | 1,073,563 |
| [enwiki-20240401-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/enwiki/20240401/jawiki-20240401-pages-articles-multistream.xml.bz2) | [citation-enwiki-20240401.jsonl](https://storage.googleapis.com/isbn-citation/citation-enwiki-20240401.jsonl) | 7,023,140 |
| [jawiki-20241201-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20240401/jawiki-20240401-pages-articles-multistream.xml.bz2) | [citation-jawiki-20241201.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20240401.jsonl) | 1,130,854 |
| [enwiki-20241201-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/enwiki/20240401/jawiki-20240401-pages-articles-multistream.xml.bz2) | [citation-enwiki-20241201.jsonl](https://storage.googleapis.com/isbn-citation/citation-enwiki-20240401.jsonl) | 8,669,996 |

- [日本語版Wikipediaのダンプ](https://dumps.wikimedia.org/jawiki/)
- [英語版Wikipediaのダンプ](https://dumps.wikimedia.org/enwiki/)
- [保存場所の管理](https://console.cloud.google.com/storage/browser/isbn-citation) （管理者用）

注意事項
----

- チェックデジットの一致により、ISBN以外を誤判定する場合があります。ただし、ISBNから参照記事を検索する目的では問題とならないため許容しています
- チェックデジット間違いのISBNは抽出されません