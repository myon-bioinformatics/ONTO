# ONTO

オントロジーに絡むリポジトリを紐付ける、索引と、横断して使う Python API。

## 役割

- 語彙・データ・評価結果の一次情報は各リポジトリ側に置く。語彙検査とグラフ操作の正本はリポジトリ直下の [ontology.py](ontology.py) と [knowledgegraph.py](knowledgegraph.py) に置く。
- 更新は末端（孫）のリポジトリから。ONTO はそれを集めてリンクする

## 紐付け先

- [TopOntOlogy](https://github.com/myon-bioinformatics/TopOntolOgy) — Topology × Ontology の造語プロジェクト
- [OnTautoLogy](https://github.com/myon-bioinformatics/OnTautoLogy) — 規則・同値性・反例・事例と判断の照合
- [TaxOntOy](https://github.com/myon-bioinformatics/TaxOntOy) — Taxonomy × Ontology

[Aoi の共有ツール配布](https://github.com/myon-bioinformatics/Aoi) に合わせ、共通処理はここでテストし、利用側は採用したコミットとファイルを固定します。
語彙やグラフ構造の変更は ONTO、論理的に成立する条件や反例の変更は OTL で扱います。

## 共通 Python API

checkout を `uv pip install .` で導入すると、どのプロジェクトからも次の入口を使えます。

```python
import ontology
import knowledgegraph
```

[分類例](examples/shared_taxonomy.py) は同じグラフで語彙検査・循環検出・Mermaid 表示を行います。
共通処理を直すときは ONTO を更新し、利用側で採用する版を選びます。

## RDF・プロパティグラフの入出力

[onto_exchange.py](onto_exchange.py) は RDF の読み込み、SPARQL 照会、Neo4j・ArcadeDB への入出力を担当します。
`uv pip install '.[exchange]'` で追加できます。保存済み RDF の照会は DB を起動せずに実行できます。

```sh
python -m onto_exchange query graph.ttl 'SELECT ?s ?p ?o WHERE { ?s ?p ?o }' > answer.json
python -m onto_exchange export neo4j demo > graph.ttl
python -m onto_exchange export neo4j demo --format json > graph.json
```

OTL はこの実装に事例・判断を渡し、論理検証で使ったデータが DB 往復後も同じかを調べます。
