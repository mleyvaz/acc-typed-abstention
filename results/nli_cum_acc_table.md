# Run `nli_cum_acc` (nli, aggregation=cum, K=3); items=1020 dev=280 test=740

Gate H4 -- pre-specified in-sample poly-2 R2 = 0.082; empirical non-redundancy (5-fold CV R2 of I from (T,F)): poly2_ridge=-3.828, poly4_ridge=-3.673, random_forest=-3.427, grad_boosting=-0.901, knn10=-7.509, mlp=-6.024, max_cv_r2=-0.901; neighbour check: 39026 near-identical (T,F) pairs, mean |dI| = 0.009574239203788436 vs random 0.013562057708384449 (ratio 0.7059577100803346) -> PASS (I not a function of (T,F) for the tested classes)

| Rep | macro-F1 (95% cluster CI) | acc | over-answer under conflict | {A,N} macro-F1 | collision pairs discriminated | dF1 vs IND (95% CI) | p perm (Holm) | McNemar p | TOST acc. equiv. (+-0.02) |
|---|---|---|---|---|---|---|---|---|---|
| IND | 0.488 (0.471-0.504) | 0.757 | None | 0.429 | None | - | - | - | - |
| TF | 0.490 (0.473-0.507) | 0.764 | None | 0.431 | None | -0.003 (-0.006, +0.000) | 0.1434 (0.2869) | 0.0625 | yes [-0.012, -0.003] |
| NORM | 0.554 (0.525-0.586) | 0.636 | None | 0.429 | None | -0.067 (-0.093, -0.042) | 0.0100 (0.0400) | 3.1629462798282884e-17 | no [+0.097, +0.144] |
| RENORM3 | 0.435 (0.419-0.564) | 0.519 | None | 0.256 | None | +0.052 (-0.078, +0.074) | 0.0105 (0.0400) | 1.1511421913152447e-15 | no [+0.200, +0.275] |
| SCALAR | 0.345 (0.331-0.359) | 0.427 | None | 0.000 | None | +0.143 (+0.122, +0.163) | 0.0005 (0.0025) | 3.170856214913216e-38 | no [+0.295, +0.361] |
| INDX | 0.487 (0.470-0.503) | 0.755 | None | 0.429 | None | +0.001 (+0.000, +0.002) | 1.0000 (1.0000) | 1.0 | yes [+0.000, +0.004] |

Per-condition accuracy:

| Rep | A | N | N_hard | R | S |
|---|---|---|---|---|---|
| IND | 0.00 | 0.97 | 0.93 | 0.56 | 0.97 |
| TF | 0.00 | 0.98 | 0.93 | 0.57 | 0.98 |
| NORM | 0.08 | 0.77 | 0.72 | 0.49 | 0.86 |
| RENORM3 | 0.93 | 0.04 | 0.09 | 0.97 | 0.75 |
| SCALAR | 0.00 | 0.00 | 0.00 | 0.95 | 0.98 |
| INDX | 0.00 | 0.97 | 0.93 | 0.56 | 0.96 |

Indeterminacy conditions (A = real hedged sentences; A_mixed = annotator disagreement; A_tpl = templated manipulation check):

| condition | n | IND | TF | NORM | RENORM3 | SCALAR | INDX |
|---|---|---|---|---|---|---|---|
| A | 86 | 0.00 | 0.00 | 0.08 | 0.93 | 0.00 | 0.00 |
| A_mixed | 0 | - | - | - | - | - | - |
| A_tpl | 0 | - | - | - | - | - | - |

Source naming of IND renderings vs gold document labels (no human, no judge): sup_precision=0.977, sup_recall=0.977, opp_precision=0.872, opp_recall=0.873

Condition means (IND) in (D,E,I):

| cond | n | D | E | I |
|---|---|---|---|---|
| A | 86 | 0.00 | 0.01 | 0.00 |
| N | 164 | -0.01 | 0.01 | 0.00 |
| N_hard | 162 | -0.00 | 0.02 | 0.01 |
| R | 164 | -0.16 | 0.20 | 0.01 |
| S | 164 | 0.31 | 0.34 | 0.02 |