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
  --unique / --no-unique          同じページに同じISBNが複数あれば1件にまとめる
  -j, --jobs INTEGER              並列数。既定はCPU数。1を指定すると逐次処理する
  --help                          Show this message and exit.
```

1つのページで同じ出典を何度も参照していると、そのぶんレコードが増えます
（jawiki-20260401で約9%が重複）。ISBNから記事を引く用途なら `--unique` を付けると
（ページ, ISBN）単位にまとまります。どのセクションで参照されたかを分析したい場合は、
`h1` / `h2` が失われるため既定のままにしてください。

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
| isbn   | String      | 正規化されたISBN（原則ISBN-10。979で始まるものはISBN-13）                                |
| raw    | String      | 解析される元のISBN表記                                                                   |
| title  | String      | Wikipediaのページ名                                                                      |
| score  | Number      | 独自指標により算出されたISBNの正確さ<br>（スコアが低い場合は、誤って検出した場合がある） |
| h1     | String/null | 見出し1                                                                                  |
| h2     | String/null | 見出し2                                                                                  |
| is_ref | Boolean     | 出典であることが明記されているか（作品リストなどではfalse）                              |

`isbn` は原則としてISBN-10に揃えていますが、979で始まるISBN-13だけは13桁のまま出力します。
979は2007年に追加されたプレフィックスで、ISBN-10の番号空間に対応する番号が存在しないためです
（jawiki-20260401で約660件）。

### スコアについて

スコアは2段階で算出しています。

1. **ISBN表記としての確からしさ** — 接頭辞（`ISBN` など）の有無、チェックデジットの検証、
   桁数パターンから算出します。**この値が1.0以上のものを抽出対象として採用します**
2. **出典らしさの補正** — 採用したあとに、`<ref>` タグやciteテンプレートの有無、
   直近の見出しに応じて加減点します

出力される `score` は補正後の値です。採用の判定は補正前の値で済んでいるため、
「作品リスト」のような著作一覧の見出しで減点されたレコードは、`score` が1.0を
下回ることがあります（jawiki-20260401で12,614件、全体の1.0%）。ISBN自体は有効なので、
出典かどうかで絞り込みたい場合は `score` ではなく `is_ref` を使ってください。

処理済みデータのダウンロード
----

| ダンプ | 処理データ | 件数 | 最新ロジック |
|---|---|---:|:-:|
| [jawiki-20110921](https://dumps.wikimedia.org/jawiki/20110921/jawiki-20110921-pages-articles.xml.bz2) | [citation-jawiki-20110921.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20110921.jsonl) |   261,170 | ○ |
| [jawiki-20141211](https://dumps.wikimedia.org/jawiki/20141211/jawiki-20141211-pages-articles-multistream.xml.bz2) | [citation-jawiki-20141211.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20141211.jsonl) |   416,078 | ○ |
| [jawiki-20150602](https://dumps.wikimedia.org/jawiki/20150602/jawiki-20150602-pages-articles-multistream.xml.bz2) | [citation-jawiki-20150602.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20150602.jsonl) |   441,064 | ○ |
| [jawiki-20160601](https://dumps.wikimedia.org/jawiki/20160601/jawiki-20160601-pages-articles-multistream.xml.bz2) | [citation-jawiki-20160601.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20160601.jsonl) |   495,273 | ○ |
| [jawiki-20170601](https://dumps.wikimedia.org/jawiki/20170601/jawiki-20170601-pages-articles-multistream.xml.bz2) | [citation-jawiki-20170601.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20170601.jsonl) |   547,018 | ○ |
| [jawiki-20180901](https://dumps.wikimedia.org/jawiki/20180901/jawiki-20180901-pages-articles-multistream.xml.bz2) | [citation-jawiki-20180901.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20180901.jsonl) |   616,968 | ○ |
| [jawiki-20190420](https://dumps.wikimedia.org/jawiki/20190420/jawiki-20190420-pages-articles-multistream.xml.bz2) | [citation-jawiki-20190420.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20190420.jsonl) |   672,155 |   |
| [jawiki-20190601](https://dumps.wikimedia.org/jawiki/20190601/jawiki-20190601-pages-articles-multistream.xml.bz2) | [citation-jawiki-20190601.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20190601.jsonl) |   679,440 |   |
| [jawiki-20190801](https://dumps.wikimedia.org/jawiki/20190801/jawiki-20190801-pages-articles-multistream.xml.bz2) | [citation-jawiki-20190801.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20190801.jsonl) |   688,393 |   |
| [jawiki-20191220](https://dumps.wikimedia.org/jawiki/20191220/jawiki-20191220-pages-articles-multistream.xml.bz2) | [citation-jawiki-20191220.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20191220.jsonl) |   714,273 |   |
| [jawiki-20200301](https://dumps.wikimedia.org/jawiki/20200301/jawiki-20200301-pages-articles-multistream.xml.bz2) | [citation-jawiki-20200301.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20200301.jsonl) |   728,278 |   |
| [jawiki-20200801](https://dumps.wikimedia.org/jawiki/20200801/jawiki-20200801-pages-articles-multistream.xml.bz2) | [citation-jawiki-20200801.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20200801.jsonl) |   763,007 |   |
| [jawiki-20201201](https://dumps.wikimedia.org/jawiki/20201201/jawiki-20201201-pages-articles-multistream.xml.bz2) | [citation-jawiki-20201201.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20201201.jsonl) |   788,068 |   |
| [jawiki-20210620](https://dumps.wikimedia.org/jawiki/20210620/jawiki-20210620-pages-articles-multistream.xml.bz2) | [citation-jawiki-20210620.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20210620.jsonl) |   839,059 |   |
| [jawiki-20210920](https://dumps.wikimedia.org/jawiki/20210920/jawiki-20210920-pages-articles-multistream.xml.bz2) | [citation-jawiki-20210920.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20210920.jsonl) |   864,341 |   |
| [jawiki-20211120](https://dumps.wikimedia.org/jawiki/20211120/jawiki-20211120-pages-articles-multistream.xml.bz2) | [citation-jawiki-20211120.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20211120.jsonl) |   880,591 |   |
| [enwiki-20211120](https://dumps.wikimedia.org/enwiki/20211120/enwiki-20211120-pages-articles-multistream.xml.bz2) | [citation-enwiki-20211120.jsonl](https://storage.googleapis.com/isbn-citation/citation-enwiki-20211120.jsonl) | 5,116,149 |   |
| [jawiki-20221220](https://dumps.wikimedia.org/jawiki/20221220/jawiki-20221220-pages-articles-multistream.xml.bz2) | [citation-jawiki-20221220.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20221220.jsonl) |   970,869 |   |
| [enwiki-20221220](https://dumps.wikimedia.org/enwiki/20221220/enwiki-20221220-pages-articles-multistream.xml.bz2) | [citation-enwiki-20221220.jsonl](https://storage.googleapis.com/isbn-citation/citation-enwiki-20221220.jsonl) | 6,064,901 |   |
| [jawiki-20240401](https://dumps.wikimedia.org/jawiki/20240401/jawiki-20240401-pages-articles-multistream.xml.bz2) | [citation-jawiki-20240401.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20240401.jsonl) | 1,042,239 | ○ |
| [enwiki-20240401](https://dumps.wikimedia.org/enwiki/20240401/enwiki-20240401-pages-articles-multistream.xml.bz2) | [citation-enwiki-20240401.jsonl](https://storage.googleapis.com/isbn-citation/citation-enwiki-20240401.jsonl) | 5,295,568 | ○ |
| [jawiki-20241201](https://dumps.wikimedia.org/jawiki/20241201/jawiki-20241201-pages-articles-multistream.xml.bz2) | [citation-jawiki-20241201.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20241201.jsonl) | 1,097,343 | ○ |
| [enwiki-20241201](https://dumps.wikimedia.org/enwiki/20241201/enwiki-20241201-pages-articles-multistream.xml.bz2) | [citation-enwiki-20241201.jsonl](https://storage.googleapis.com/isbn-citation/citation-enwiki-20241201.jsonl) | 5,545,002 | ○ |
| [jawiki-20250601](https://dumps.wikimedia.org/jawiki/20250601/jawiki-20250601-pages-articles-multistream.xml.bz2) | [citation-jawiki-20250601.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20250601.jsonl) | 1,140,156 | ○ |
| [enwiki-20250601](https://dumps.wikimedia.org/enwiki/20250601/enwiki-20250601-pages-articles-multistream.xml.bz2) | [citation-enwiki-20250601.jsonl](https://storage.googleapis.com/isbn-citation/citation-enwiki-20250601.jsonl) | 5,722,443 | ○ |
| [jawiki-20260401](https://dumps.wikimedia.org/jawiki/20260401/jawiki-20260401-pages-articles-multistream.xml.bz2) | [citation-jawiki-20260401.jsonl](https://storage.googleapis.com/isbn-citation/citation-jawiki-20260401.jsonl) | 1,212,087 | ○ |

「最新ロジック」の列は、現在の抽出ロジックで処理し直したものに○を付けている。空欄のものは以前のロジックで抽出したままで、記事以外の名前空間が混ざっていたり、日付や電話番号を誤ってISBNとして拾っていたりする。順次処理し直す。

- [日本語版Wikipediaのダンプ](https://dumps.wikimedia.org/jawiki/)
- [英語版Wikipediaのダンプ](https://dumps.wikimedia.org/enwiki/)
- [保存場所の管理](https://console.cloud.google.com/storage/browser/isbn-citation) （管理者用）

過去ダンプの入手と再処理
----

公式サイトは直近数か月分のダンプしか置いていないため、過去のダンプは別の場所から取る。
年次シリーズの対象と取得元は `tools/backfill.py` にまとめてある。

```bash
# 対象と手元の状態を一覧する
uv run python tools/backfill.py list

# 取得（md5照合まで）→ 抽出 → 件数の記録
uv run python tools/backfill.py run --wiki jawiki

# ダウンロードと抽出を並走させる場合（抽出は取得できたものから順に処理する）
uv run python tools/backfill.py fetch --wiki enwiki -j 3
uv run python tools/backfill.py extract --watch
```

| 取得元 | 残っている範囲 |
|---|---|
| [dumps.wikimedia.org](https://dumps.wikimedia.org/) | 直近5〜7か月分 |
| [Internet Archive](https://archive.org/details/wikimediadownloads) | jawiki・enwikiとも2014年11月〜2022年5月がほぼ毎月。ほかにjawikiの2011年、enwikiの2008〜2010年 |
| [公式のヒストリカルアーカイブ](https://dumps.wikimedia.org/archive/) | enwikiの20080103と20100312（`pages-articles`） |
| `gs://isbn-citation` | 上のどこにも残っていないダンプの控え（jawikiの2019年〜、enwikiの2024年〜） |

Internet Archive のミラーは2022年5月で止まっているため、**2012年・2013年・2023年の
ダンプはどこにも残っておらず再処理できない**。2011年以前のダンプは multistream が無いため
逐次処理になり、`<ns>` を持たないため記事以外の名前空間も混ざる
（[KNOWN_ISSUES.md](KNOWN_ISSUES.md) の25番）。

### ダンプの控えを残す方針

公式は数か月でダンプを消し、Internet Archive のミラーも止まっているため、**新しく処理した
ダンプはどこにも残らない**。実際に jawiki-20190420 から 20200801 までは公式もIAも消えており、
このバケットに置いた控えだけが残っている。そのため次の基準で控えを置く。

- **置く**: 他に現存するコピーが無いもの（jawikiの2019年以降、enwikiの2024年以降）。
  処理した直後に上げる。上げ忘れるとその日付は二度と再処理できなくなる
- **置かない**: Internet Archive にあるもの（2008〜2022年）。`tools/backfill.py` が
  md5照合付きで取り直せるので、同じものを二重に持たない

バケットのライフサイクルで30日後にNearline、100日後にArchiveへ落ちる。
旧ロジックで生成した出力は `archive/` に退避してある（`archive/NOTE.txt` に違いを記載）。

注意事項
----

- チェックデジットの一致により、ISBN以外を誤判定する場合があります。ただし、ISBNから参照記事を検索する目的では問題とならないため許容しています
- チェックデジット間違いのISBNは抽出されません
- 抽出精度に関する未対応の問題は [KNOWN_ISSUES.md](KNOWN_ISSUES.md) にまとめてあります
- 抽出結果が変わる変更は [CHANGELOG.md](CHANGELOG.md) に記録しています。過去のデータと比較する場合はバージョンを揃えてください

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
