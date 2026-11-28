# 判定モデル・ローカルLLMとの接続

既存実装の参照:
- [Aoiの命題判定](https://github.com/myon-bioinformatics/Aoi/blob/f680d3c114e8463bbcbbbca516d78ce9dc73a75c/pythdragoras/core/propositions.py): judge は命題の各形式、反例、未確定、標本数等の結果を受け取る。文章の好みを直接採点するAPIではない。効果測定の命題と実測データが揃ってから接続する。
- [PortfolioのローカルLLM](https://github.com/myon-bioinformatics/myon-bioinformatics.github.io/blob/a25533922e1e140e8c1564e650b0dad29d860ed2/scripts/chat.py): wllamaによるブラウザ内推論。既存の実行機構を利用候補とし、別のモデル配布機構は作らない。

hybrid_editing.py は特徴抽出・候補順位付けのコールバック境界を提供する。モデル出力は語彙IDに制限し、未知IDは拒否する。制約違反は順位付けより優先する。モデルによる特徴抽出の漏れは検出できないため、公開は常に別途レビューする。順位は仮説であり効果の証明ではない。

比較計画: LLM単独、規則のみ、規則+判定モデル、規則+判定モデル+LLM。独立した合成教材で特徴抽出精度、未知拒否、制約遵守、順位の一致、時間、トークン数を比較する。実測前は unverified。個人情報や原文との対応は保存しない。

今回の実装は注入可能な接続境界と模擬コールバックのテストまで。Aoiの実モデル・wllamaの実呼び出し、実測、Portfolioへの組み込みは未実施。

検証: `python -S -m unittest discover -s tests -p 'test_hybrid_editing.py'`
