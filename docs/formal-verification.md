# RDF statement と JSON グラフの情報保持

[`formal/GraphProjection.lean`](../formal/GraphProjection.lean) は、
[`ontology.py::graph_json`](../ontology.py) が N3 表記の statement を JSON の
ノード・有向関係へ投影する部分をモデル化する。元の subject・predicate・object を
区別したまま保持すること、関係の両端が必ずノードとして存在すること、生成した
グラフの構造比較と元の statement 集合の比較が対応することを証明する。

## 実装とモデルの対応

現行実装の `statements(graph)` は RDF 項を `.n3()` で文字列にし、行を整列する。
`graph_json(graph)` はその行から一意な subject/object ノードと関係を作る。
モデルの入力は、この N3 文字列化が終わった行のリストである。

| Python の表現 | Lean の表現 | 扱い |
|---|---|---|
| `subject`, `predicate`, `object` の N3 文字列 | `Statement` の 3 つの `String` | IRI・literal・言語タグ・datatype を含む token をそのまま区別する |
| `nodes[*].id` と `properties.term` | `PropertyGraph.nodes` | 両方は同じ token。固定 label `OtlTerm` は省略 |
| `rels[*].start.id`, `properties.predicate`, `end.id` | `Relationship.start`, `predicate`, `finish` | 方向と predicate を別々のフィールドに保持 |
| 一意化・整列したノード | endpoint のリストを `eraseDups` | ノードの存在を比較し、表示上の順序を比較しない |
| JSON グラフの比較 | `sameGraph` | ノード集合と有向関係集合の一致。配列順や重複回数は比較しない |
| 元の RDF statement の比較 | `sameStatements` | N3 token の三つ組の集合として比較する |

同じ subject/object に異なる predicate がつく場合は、別の関係になる。
IRI と同じ文字を含む literal、言語タグの異なる literal も別 token のままである。
この性質を、JSON のノード ID や「始点と終点だけ」の組へまとめて失わないことが対象になる。

## 証明する性質

| 定理 | 保証 |
|---|---|
| `Onto.relationship_injective` | 異なる statement は異なる有向関係になる |
| `Onto.relationship_membership` | 元の statement が存在することと、対応する関係が存在することが同値 |
| `Onto.node_membership` | ノードが存在することと、いずれかの元 statement の端点であることが同値 |
| `Onto.endpoints_present` | 出力された関係の始点・終点は両方ともノードに含まれる |
| `Onto.graph_equivalence_iff` | 投影後のグラフの集合比較と、投影前の statement の集合比較が同値 |
| `Onto.parallel_predicates_preserved` | 同じ始点・終点でも predicate が異なれば関係は異なる |

`graph_equivalence_iff` によって、単なる往復の恒等式に加え、表現を変えた後の
構造比較で何を区別できるかを明示する。名前空間 prefix の綴り、JSON のキー順、
配列の並び順など、表示形式の一致を主張するものではない。

## 実装への接続テスト

[`tests/test_formal_graph_projection.py`](../tests/test_formal_graph_projection.py)
は Python 標準ライブラリだけで実行できる部分と、既存の optional `exchange`
依存がある環境で実行する部分に分かれる。

```sh
python -S -m unittest discover -s tests -p test_formal_graph_projection.py -v
```

標準ライブラリのテストは `statements()` の返り値だけを差し替え、実際の
`graph_json()` を呼ぶ。並行する predicate、逆向きの関係、自己ループ、IRI と literal、
言語タグ、型付き literal を含む 8 statement のすべての部分集合を、2 つの入力順で
調べる（`2^8 × 2 = 512` ケース）。生成 JSON を serialize/parse し直して、関係の全項、
端点ノード、固定 label と `properties.term`、入力を変更しないことを確認する。
この層だけでは `.n3()` 変換や RDF パーサーを検証したことにはならない。

既存 CI の `exchange` 導入後のテストでは、実際の rdflib による Turtle 保存・
`read_graph()` 読み込み、`statements()`、`graph_json()`、`transfer()` の行エンコードと
デコードを通す。言語・datatype・改行や引用符、並行する関係を保持する標準的な
literal を使う。名前のない資源の拒否と DB 関係の重複拒否も確認する。
DB 通信だけはローカル stub に置き換え、実サービスには接続しない。

```sh
uv run --no-project --with rdflib python -m unittest discover -s tests -v
```

rdflib がない環境では、この RDF I/O 部分は明示的に skip する。標準ライブラリの
投影テストは引き続き実行し、skip を RDF 往復の成功とは扱わない。

## Lean の実行

Lean 4.36.0 を [`formal/lean-toolchain`](../formal/lean-toolchain) で固定し、
Lean の標準ライブラリだけを使う。Python の通常実行に Lean は不要。
親リポジトリの共通
[`lean_verify.py`](https://github.com/myon-bioinformatics/myon-bioinformatics/blob/6c2558c4251698c50bc07bad86fb49f902b2738f/lean_verify.py)
を、ONTO のルートから次のように呼ぶ。

```sh
python -S /path/to/myon-bioinformatics/lean_verify.py \
  --cwd formal --required \
  --theorem Onto.relationship_injective \
  --theorem Onto.relationship_membership \
  --theorem Onto.node_membership \
  --theorem Onto.endpoints_present \
  --theorem Onto.graph_equivalence_iff \
  --theorem Onto.parallel_predicates_preserved \
  --json-output build/onto-lean-verification.json \
  GraphProjection.lean
```

すべての定理名を渡してコンパイルと公理依存を監査する。Lean 専用 CI では
`--required` により Lean 不在も失敗となる。任意のローカル実行でこの指定を省いても、
Lean 不在は `unverified` という別の結果になり、証明成功とは区別する。

## 保証の境界と残る往復課題

Lean は上のモデルについて証明し、Python 実装との接続は回帰テストで調べる。
RDF/N3 パーサー自体、DB の保存・分離・並行動作、RDF の意味論的同値性、任意の
JSON から RDF へ戻す汎用インポーターは今回の証明対象に含まない。
現行 ONTO の JSON 出力に対応する汎用 JSON→TTL API はまだない。

また、字句上同じ RDF term を保持する保証と、値の同一性は区別が必要になる。
たとえば現行の `transfer()` の `from_n3()` 復元では、明示的に正規化を止めて作った
`"01"^^xsd:integer` が `"1"^^xsd:integer` になる。このため DB 行→RDF 往復について、
すべての非正規 literal まで字句を保持するとは主張しない。N3 token→JSON の投影は
与えられた文字列をそのまま保持し、この境界の外で発生する正規化をモデルに隠さない。
