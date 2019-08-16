citation
=========================================================================================================================================================================================
Wikipediaのダンプファイルから出典ISBNを抽出するツール

概要
-----
- [Wikipediaのダンプ](https://dumps.wikimedia.org/jawiki/)から出典ISBNを抽出します
- 抽出したデータはLine-delimited JSON形式で保存します

コマンドライン
----
```json
wget https://dumps.wikimedia.org/jawiki/20190420/jawiki-20190420-pages-articles-multistream.xml.bz
pipenv run python citation.py jawiki-20190420-pages-articles-multistream.xml.bz2 citation-jawiki-20190420.json
```

抽出されるデータ例
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

- raw ... 解析される元のISBN表記
- score (float) ... 独自指標により算出されたISBNの正確さ（スコアが低い場合は、誤って検出した場合がある）
- authority (boolean) ... 出典であることが明記されているか（作品リストなどではfalse）

