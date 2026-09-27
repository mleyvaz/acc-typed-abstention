# Run `nli_cum_acc_smoke` (nli, aggregation=cum, K=3); items=60 dev=15 test=45

Gate H4 -- pre-specified in-sample poly-2 R2 = 0.008; empirical non-redundancy (5-fold CV R2 of I from (T,F)): poly2_ridge=-5.357, poly4_ridge=-4.228, random_forest=-8.049, grad_boosting=-1.050, knn10=-7.347, mlp=-426572.340, max_cv_r2=-1.050; neighbour check: 781 near-identical (T,F) pairs, mean |dI| = 0.0054476514948073925 vs random 0.0047511287808080244 (ratio 1.1466015227398048) -> PASS (I not a function of (T,F) for the tested classes)

| Rep | macro-F1 (95% cluster CI) | acc | over-answer under conflict | {A,N} macro-F1 | collision pairs discriminated | dF1 vs IND (95% CI) | p perm (Holm) | McNemar p | TOST acc. equiv. (+-0.02) |
|---|---|---|---|---|---|---|---|---|---|
| IND | 0.483 (0.392-0.683) | 0.689 | None | 0.386 | None | - | - | - | - |
| TF | 0.483 (0.392-0.683) | 0.689 | None | 0.386 | None | +0.000 (+0.000, +0.000) | 1.0000 (1.0000) | 1.0 | yes [+0.000, +0.000] |
| NORM | 0.323 (0.223-0.481) | 0.422 | None | 0.196 | None | +0.160 (+0.068, +0.356) | 0.0170 (0.0850) | 0.004180908203125 | no [+0.154, +0.379] |
| RENORM3 | 0.481 (0.437-0.646) | 0.578 | None | 0.257 | None | +0.002 (-0.195, +0.210) | 0.9790 (1.0000) | 0.47312965989112854 | no [-0.054, +0.260] |
| SCALAR | 0.350 (0.295-0.401) | 0.400 | None | 0.000 | None | +0.133 (+0.033, +0.348) | 0.3618 (1.0000) | 0.007197380065917969 | no [+0.129, +0.420] |
| INDX | 0.483 (0.392-0.683) | 0.689 | None | 0.386 | None | +0.000 (+0.000, +0.000) | 1.0000 (1.0000) | 1.0 | yes [+0.000, +0.000] |

Per-condition accuracy:

| Rep | A | N | N_hard | R | S |
|---|---|---|---|---|---|
| IND | 0.00 | 1.00 | 0.89 | 0.67 | 0.89 |
| TF | 0.00 | 1.00 | 0.89 | 0.67 | 0.89 |
| NORM | 0.11 | 0.11 | 0.22 | 0.78 | 0.89 |
| RENORM3 | 1.00 | 0.00 | 0.00 | 1.00 | 0.89 |
| SCALAR | 0.00 | 0.00 | 0.00 | 1.00 | 1.00 |
| INDX | 0.00 | 1.00 | 0.89 | 0.67 | 0.89 |

Indeterminacy conditions (A = real hedged sentences; A_mixed = annotator disagreement; A_tpl = templated manipulation check):

| condition | n | IND | TF | NORM | RENORM3 | SCALAR | INDX |
|---|---|---|---|---|---|---|---|
| A | 9 | 0.00 | 0.00 | 0.11 | 1.00 | 0.00 | 0.00 |
| A_mixed | 0 | - | - | - | - | - | - |
| A_tpl | 0 | - | - | - | - | - | - |

Source naming of IND renderings vs gold document labels (no human, no judge): sup_precision=1.000, sup_recall=1.000, opp_precision=0.889, opp_recall=0.889

Condition means (IND) in (D,E,I):

| cond | n | D | E | I |
|---|---|---|---|---|
| A | 9 | -0.00 | 0.00 | 0.00 |
| N | 9 | -0.00 | 0.00 | 0.00 |
| N_hard | 9 | -0.04 | 0.04 | 0.00 |
| R | 9 | -0.19 | 0.21 | 0.00 |
| S | 9 | 0.31 | 0.35 | 0.03 |