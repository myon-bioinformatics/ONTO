# ONTO

オントロジーに絡むリポジトリを紐付ける、索引と、横断して使う Python API。

## 役割

- 語彙・データ・評価結果の一次情報は各リポジトリ側に置く。語彙検査とグラフ操作の正本はリポジトリ直下の [ontology.py](ontology.py) と [knowledgegraph.py](knowledgegraph.py) に置く。
- 更新は末端（孫）のリポジトリから。ONTO はそれを集めてリンクする

## 紐付け先

- [TopOntOlogy](https://github.com/myon-bioinformatics/TopOntolOgy) — Topology × Ontology の造語プロジェクト
- [OnTautoLogy](https://github.com/myon-bioinformatics/OnTautoLogy)

- [TaxOntOy](https://github.com/myon-bioinformatics/TaxOntOy) — Taxonomy × Ontology

対象が増えたらここに追加していきます。

## 共通 Python API

checkout を `uv pip install .` で導入すると、どのプロジェクトからも次の入口を使えます。

```python
import ontology
import knowledgegraph
```

[分類例](examples/shared_taxonomy.py) は同じグラフで語彙検査・循環検出・Mermaid 表示を行います。
共通処理を直すときは ONTO を更新し、利用側で採用する版を選びます。
