# -*- coding: utf-8 -*-
"""50 -- tasas de no decidibles por jurisdiccion y documento, y reconciliacion 236/237 (27-sep-2026).
Lee las mismas filas que build_acc_battery.load_rows() (CODE-ACCORD, 862 clausulas). Solo cuenta; no cambia
ninguna definicion. Salida: results/jurisdiction_rates.json (no sobrescribe)."""
import os, sys, json, re, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import build_acc_battery as B
out = os.path.join(HERE, "..", "results", "jurisdiction_rates.json")
if os.path.exists(out): sys.exit("ya existe")
rows = B.load_rows()
J = collections.defaultdict(lambda: [0, 0]); D = collections.defaultdict(lambda: [0, 0, None])
for r in rows:
    J[r["juris"]][0] += int(r["discretionary"]); J[r["juris"]][1] += 1
    D[r["doc"]][0] += int(r["discretionary"]); D[r["doc"]][1] += 1; D[r["doc"]][2] = r["juris"]
has_digit = sum(bool(re.search(r"\d", r["text"])) for r in rows)
res = dict(n=len(rows),
           by_jurisdiction={k: dict(nondecidable=v[0], total=v[1], rate=v[0] / v[1]) for k, v in J.items()},
           by_document={k: dict(juris=v[2], nondecidable=v[0], total=v[1], rate=v[0] / v[1]) for k, v in D.items()},
           decidable=sum(r["decidable"] for r in rows), discretionary=sum(r["discretionary"] for r in rows),
           contains_any_digit=has_digit,
           decidable_and_discretionary=sum(r["decidable"] and r["discretionary"] for r in rows))
json.dump(res, open(out, "w", encoding="utf-8"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "by_document"}, indent=1))
