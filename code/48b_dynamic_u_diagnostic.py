# -*- coding: utf-8 -*-
"""48b -- diagnostico del rival U_dyn (exploratorio, 27-sep-2026). Sin ajuste cruzado: coste medio por
condicion (conjunto primario, sin limite de riesgo, c_s=10, c_e=c_h) de variantes fijas de U_dyn, para
ver por que la busqueda en rejilla elige la variante que nunca se estanca. Salida:
results/route2_dynamic_u_diagnostic.json"""
import os, sys, json, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
spec = importlib.util.spec_from_file_location("m48", os.path.join(HERE, "48_dynamic_u_rival.py"))
m48 = importlib.util.module_from_spec(spec); spec.loader.exec_module(m48); a47 = m48.a47
out = os.path.join(ROOT, "results", "route2_dynamic_u_diagnostic.json")
if os.path.exists(out): sys.exit("ya existe")
samples = {json.loads(l)["id"]: json.loads(l) for l in open(os.path.join(ROOT, "results", "route2_samples_openai_gpt-oss-120b_low.jsonl"), encoding="utf-8")}
exc = set(json.load(open(os.path.join(ROOT, "results", "codex_audit_route2_excluded.json"))))
items = [it for it in (json.loads(l) for l in open(os.path.join(ROOT, "data", "acc_route2.jsonl"), encoding="utf-8"))
         if it["id"] in samples and it["seed"] not in exc and it["condition"] in a47.SETS["primary"]]
envs = {it["id"]: a47.Env(it, samples[it["id"]], 5, dict(c_s=10.0, c_e=a47.C_H)) for it in items}
# confianza de la cabeza sin tipo en el estado inicial, por condicion
conf0 = {}
for c in a47.SETS["primary"]:
    xs = [a47.verdict(envs[it["id"]].p("untyped3", 0, 0))[1] for it in items if it["condition"] == c]
    conf0[c] = dict(mean=sum(xs) / len(xs), share_zero=sum(x == 0 for x in xs) / len(xs), n=len(xs))
variants = {"never_stall_B3_rfi (=plan S S S R E)": (0.6, -1.0, 3, True, "S"),
            "stall_if_no_rise_B3_rfi": (0.6, 0.19, 3, True, "S"),
            "stall_if_no_rise_B3_no_rfi": (0.6, 0.19, 3, False, "S"),
            "never_stall_B3_no_rfi": (0.6, -1.0, 3, False, "S")}
res = {}
for name, prm in variants.items():
    row = {}
    for c in a47.SETS["primary"] + ["ALL"]:
        o = [m48.run_untyped_dynamic(envs[it["id"]], *prm) for it in items if c == "ALL" or it["condition"] == c]
        row[c] = round(a47.summ(o)["cost"], 1)
    res[name] = row
T = {}
for c in a47.SETS["primary"] + ["ALL"]:
    o = [a47.run_typed(envs[it["id"]], 0.6, 1, 0.2, 1.0) for it in items if c == "ALL" or it["condition"] == c]
    T[c] = round(a47.summ(o)["cost"], 1)
res["T(0.6,1,0.2,1.0) reference"] = T
json.dump(dict(untyped_conf_state0=conf0, mean_cost_by_condition=res), open(out, "w"), indent=1)
print(json.dumps(conf0, indent=1)); [print(k, v) for k, v in res.items()]
