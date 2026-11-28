# 攻略関係の語彙候補

13関係を適用・条件・戦略・順序・根拠・効果・評価・更新に分類する。定義は [relation-candidates.json](../examples/social-strategy/relation-candidates.json) を参照。

既存の case.json の appliesTo は再利用し、assessedBy は evaluatedBy の別名候補とする。既存データは変更しない。TaxOntOy の [otl-relations.json](https://github.com/myon-bioinformatics/TaxOntOy/blob/b4f49d265bb944eb28e50c7fd189abd9a0f4dd0b/otl-relations.json) の現行分類に同名の13関係はない。requires と dependsOn、prevents と blocks は意味・端点が異なり得るので自動同一視しない。横断語彙への昇格は別途照合する。

エッジの conditions、confidence、evidence、counterexamples、status を保持する。未実測の効果は hypothesis、確信度は null とする。支持・反証の端点は Claim と Evidence とし、戦略の効果そのものと証跡を区別する。相互関係・推移性は未確定であり、自動推論しない。

例は独立した合成データのみ。部分グラフ取得は次段階。今回の検査は候補語彙と仮説属性の整合性に限定する。

検証: `python -S -m unittest discover -s tests -p 'test_guide_relations.py'`
