# -*- coding: utf-8 -*-
"""48c -- sensibilidad EXPLORATORIA al coste de la interpretacion formal c_h (27-sep-2026, tras la revision R1).
El plan congelado usa c_h = 5.510 USD (tarifa de interpretacion del codigo de USO DEL SUELO de Seattle, 10 x 551).
En el mismo tarifario (City of Seattle SDCI 2026 Fee Subtitle, Tabla D-2, item 26) una 'Code Alternate Request'
de construccion se cobra a la tarifa horaria SDCI (292 USD) con minimo de 2 h -> >= 584 USD; las horas reales no
constan. Se repite el analisis de 47/48 con c_h en {584, 1168, 2920, 5510} (2, 4, 10 h a 292; y el original),
c_e = c_h y c_e = 3 c_h, sin limite de riesgo y con riesgo <= 5 %. Mismas muestras, 0 USD.
Salida: results/route2_ch_sensitivity.json (no sobrescribe)."""
import os, sys, json, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
spec = importlib.util.spec_from_file_location("m48", os.path.join(HERE, "48_dynamic_u_rival.py"))
m48 = importlib.util.module_from_spec(spec); spec.loader.exec_module(m48); a47 = m48.a47
out = os.path.join(ROOT, "results", "route2_ch_sensitivity.json")
if os.path.exists(out): sys.exit("ya existe")
samples = {json.loads(l)["id"]: json.loads(l) for l in open(os.path.join(ROOT, "results", "route2_samples_openai_gpt-oss-120b_low.jsonl"), encoding="utf-8")}
exc = set(json.load(open(os.path.join(ROOT, "results", "codex_audit_route2_excluded.json"))))
items = [it for it in (json.loads(l) for l in open(os.path.join(ROOT, "data", "acc_route2.jsonl"), encoding="utf-8"))
         if it["id"] in samples and it["seed"] not in exc and it["condition"] in a47.SETS["primary"]]
rep = {}
for ch in (584.0, 1168.0, 2920.0, 5510.0):
    a47.C_H = ch
    for mult in (1.0, 3.0):
        for risk in (1.0, 0.05):
            envs = {it["id"]: a47.Env(it, samples[it["id"]], 5, dict(c_s=10.0, c_e=mult * ch)) for it in items}
            per, res = {}, {}
            for pol in ("U", "U_dyn", "T"):
                pi, chosen = a47.crossfit(pol, items, envs, risk)
                per[pol] = pi; res[pol] = dict(a47.summ(list(pi.values())), params={str(k): str(v) for k, v in chosen.items()})
            con = {}
            for x in ("U", "U_dyn"):
                d, lo, hi = a47.boot(items, per[x], per["T"])
                con[f"{x}-T"] = dict(diff=d, ci95=[lo, hi], saving_pct=100 * d / res[x]["cost"] if res[x]["cost"] else None)
                for c in a47.SETS["primary"]:
                    d, lo, hi = a47.boot(items, per[x], per["T"], subset={c})
                    con[f"{x}-T@{c}"] = dict(diff=d, ci95=[lo, hi])
            key = f"ch{int(ch)}_ce{int(mult)}x_risk{risk}"
            rep[key] = dict(policies=res, contrasts=con)
            c = con["U_dyn-T"]; ci = con["U_dyn-T@IND_del"]; cr = con["U_dyn-T@INS_reg"]
            print(f"{key:26s} total {c['diff']:+8.1f} [{c['ci95'][0]:+.0f},{c['ci95'][1]:+.0f}] {c['saving_pct'] or 0:5.1f}% | IND_del {ci['diff']:+7.1f} [{ci['ci95'][0]:+.0f},{ci['ci95'][1]:+.0f}] | INS_reg {cr['diff']:+7.1f}")
json.dump(dict(status="EXPLORATORY, post hoc (after adversarial review R1)", c_h_values=[584, 1168, 2920, 5510],
               source="City of Seattle SDCI 2026 Fee Subtitle: SDCI hourly 292 USD; Code Alternate Request 2 h minimum; land use interpretation 10 x 551",
               results=rep), open(out, "w"), indent=1)
