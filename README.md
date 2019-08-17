citation (https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/download/releases/3.6.0/) ![t]
=========================================================================================================================================================================================
Wikipediaのダンプファイルから出典ISBNを抽出するツール

概要
-----
- 日本語版Wikipediaのダンプから出典ISBNを抽出します
- 抽出したデータはLine-delimited JSON形式で保存します

依存パッケージのインストール
----
```json
pipenv install
```

コマンドライン
----
```json
wget https://dumps.wikimedia.org/jawiki/20190420/jawiki-20190420-pages-articles-multistream.xml.bz
pipenv run python citation.py jawiki-20190420-pages-articles-multistream.xml.bz2 citation-jawiki-20190420.jsonl
```

抽出されるデータ
----

```json
{  
   "isbn":"4772212272",
   "raw":"4-7722-1227-2",
   "title":"地理学",
   "score":2.9,
   "h1":"参考文献",
   "h2":null,
   "authority":true
}
```

| 項目 | 型 | 概要 |
| ---- | ---- | ---- | 
| isbn | String | 正規化されたISBN（ISBN-10） |
| raw | String | 解析される元のISBN表記 |
| title | String | Wikipediaのページ名 |
| score | Number | 独自指標により算出されたISBNの正確さ<br>（スコアが低い場合は、誤って検出した場合がある） |
| h1 | String/null | 見出し1 |
| h2 | String/null | 見出し2 |
| authority | Boolean | 出典であることが明記されているか（作品リストなどではfalse） |

処理済みのデータ
----

| ダンプ | 処理データ | 件数 |
| ---- | ---- | ----: |
| [jawiki-20190420-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20190420/jawiki-20190420-pages-articles-multistream.xml.bz2)  | [citation-jawiki-20190420.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20190420.jsonl) | 672,155 |
| [jawiki-20190801-pages-articles-multistream.xml.bz2](https://dumps.wikimedia.org/jawiki/20190801/jawiki-20190801-pages-articles-multistream.xml.bz2)  | [citation-jawiki-20190801.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20190801.jsonl) | 688,393 |

- [日本語版Wikipediaのダンプ](https://dumps.wikimedia.org/jawiki/)
- [保存場所の管理](https://console.cloud.google.com/storage/browser/isbn-citation)
