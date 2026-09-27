# -*- coding: utf-8 -*-
"""
43_analyze_route.py -- DECISION del experimento de enrutamiento (preregistrado en PREREG_RUTEO.md).

Simula politicas sobre las trayectorias de 42_run_agents.py. Costes: c_r = 1 por ronda de busqueda,
c_h = rho por derivacion a humano, c_e = rho por veredicto comprometido erroneo.
Un compromiso sobre un item INDETERMINATE es siempre erroneo (no existe umbral que lo decida).

Politicas
  E0(tau,B)          escalar: compromete si max P >= tau; si no, busca hasta B y deriva
  E1(tau,B,delta)    E0 + deriva si la confianza no sube al menos delta tras una ronda   [RIVAL PRIMARIO]
  R0(tau,B)          E0 + deriva si la clausula mas cercana al hecho es discrecional por regex
  T1(tau,B,tau_i)    tipada: compromete si max(P_C,P_V) >= tau; deriva si P_IND >= tau_i; si no busca  [METODO]
  T1_notype(tau,B)   T1 con tau_i = nunca (misma cabeza, sin enrutar por tipo)             [ABLACION]
  ORACLE_T           tipo y veredicto de oro;  ORACLE_S  veredicto de oro sin tipo, B ajustado

Ajuste cruzado en 2 pliegues por semilla: parametros elegidos en un pliegue (min coste medio con riesgo
selectivo <= 5 %) y evaluados en el otro. IC95 por bootstrap de conglomerados (semilla), 2000 remuestreos.

Salida: results/route_analysis_<modelo>.json y .md
"""
import os, re, json, math, random, argparse, itertools, collections, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
os.environ.setdefault("HF_DATASETS_OFFLINE", "1"); os.environ.setdefault("HF_HUB_OFFLINE", "1")


def _imp(name, file):
    s = importlib.util.spec_from_file_location(name, os.path.join(HERE, file))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


bab = _imp("bab", "build_acc_battery.py")
vti = _imp("vti", "40_vti_stage0.py")

RHOS = [2, 3, 5, 10, 30, 50, 100]
RHO_PRIMARY = 10
RISK_MAX = 0.05
TAUS = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 0.999, 1.01]
BS = [0, 1, 2, 3, 4]
DELTAS = [None, -0.05, 0.0, 0.05, 0.1]
TAU_IS = [0.3, 0.5, 0.7, 0.9]
SETS = {
    "primary": ["D", "INS", "IND_del"],
    "antishortcut": ["D_words", "INS", "IND_delnum"],
    "control_silence": ["D", "INS", "IND_sil"],
    "external_real": ["D", "INS", "IND_real"],
}


def verdict_of(p):
    return ("COMPLIES", p["COMPLIES"]) if p["COMPLIES"] >= p["VIOLATES"] else ("VIOLATES", p["VIOLATES"])


def outcome(it, kind, t, verdict=None, rho=10):
    """kind: commit | escalate. Devuelve (coste, commit, error, escalado, rondas)."""
    if kind == "escalate":
        return (t + rho, 0, 0, 1, t)
    wrong = it["gold_type"] == "INDETERMINATE" or verdict != it["gold_verdict"]
    return (t + (rho if wrong else 0), 1, int(wrong), 0, t)


def run_policy(name, prm, it, tr, rho, regex_flags=None):
    R = len(tr["scalar"]) - 1
    if name == "ORACLE_T":
        if it["gold_type"] == "DECIDABLE":
            return outcome(it, "commit", 0, it["gold_verdict"], rho)
        if it["gold_type"] == "INDETERMINATE":
            return outcome(it, "escalate", 0, rho=rho)
        g = it["governing_round"]
        if g is not None and g < rho:
            return outcome(it, "commit", g, it["gold_verdict"], rho)
        return outcome(it, "escalate", 0, rho=rho)
    if name == "ORACLE_S":
        (B,) = prm
        if it["gold_type"] == "DECIDABLE":
            return outcome(it, "commit", 0, it["gold_verdict"], rho)
        g = it["governing_round"] if it["gold_type"] == "INSUFFICIENT" else None
        if g is not None and g <= B:
            return outcome(it, "commit", g, it["gold_verdict"], rho)
        return outcome(it, "escalate", B, rho=rho)
    prev = None
    for t in range(R + 1):
        if name in ("E0", "E1", "R0"):
            p, _ = tr["scalar"][t]
            v, c = verdict_of(p)
            tau, B = prm[0], prm[1]
            if name == "R0" and regex_flags[t]:
                return outcome(it, "escalate", t, rho=rho)
            if c >= tau:
                return outcome(it, "commit", t, v, rho)
            if name == "E1" and prm[2] is not None and prev is not None and c - prev < prm[2]:
                return outcome(it, "escalate", t, rho=rho)
            prev = c
            if t >= B:
                return outcome(it, "escalate", t, rho=rho)
        elif name == "U1":  # abstencion SIN tipo (3 clases): compromete o busca/deriva
            p, _ = tr["abstain3"][t]
            tau, B = prm[0], prm[1]
            v, c = verdict_of(p)
            if c >= tau:
                return outcome(it, "commit", t, v, rho)
            if t >= B:
                return outcome(it, "escalate", t, rho=rho)
        else:  # T1, T1_notype
            p, _ = tr["typed"][t]
            tau, B = prm[0], prm[1]
            tau_i = prm[2] if name == "T1" else 9.0
            v, c = verdict_of(p)
            if c >= tau:
                return outcome(it, "commit", t, v, rho)
            if p["INDETERMINATE"] >= tau_i:
                return outcome(it, "escalate", t, rho=rho)
            if t >= B:
                return outcome(it, "escalate", t, rho=rho)
    return outcome(it, "escalate", R, rho=rho)


def grid(name):
    if name == "E1":
        return list(itertools.product(TAUS, BS, DELTAS))
    if name == "T1":
        return list(itertools.product(TAUS, BS, TAU_IS))
    if name == "ORACLE_S":
        return [(b,) for b in BS]
    if name == "ORACLE_T":
        return [()]
    return list(itertools.product(TAUS, BS))


def summarize(outs):
    n = len(outs) or 1
    commits = sum(o[1] for o in outs); errors = sum(o[2] for o in outs)
    return dict(cost=sum(o[0] for o in outs) / n, risk=(errors / commits if commits else 0.0),
                commit_rate=commits / n, escalation_rate=sum(o[3] for o in outs) / n,
                mean_rounds=sum(o[4] for o in outs) / n, wrong_commits=errors)


def crossfit(name, items, trajs, rho, regex):
    per_item = {}
    chosen = {}
    for f in (0, 1):
        tune = [it for it in items if it["fold"] != f]
        test = [it for it in items if it["fold"] == f]
        if not tune or not test:
            continue
        best = None
        for prm in grid(name):
            s = summarize([run_policy(name, prm, it, trajs[it["id"]], rho, regex.get(it["id"])) for it in tune])
            key = (s["risk"] > RISK_MAX, s["cost"], s["risk"])
            if best is None or key < best[0]:
                best = (key, prm)
        chosen[f] = best[1]
        for it in test:
            per_item[it["id"]] = run_policy(name, best[1], it, trajs[it["id"]], rho, regex.get(it["id"]))
    return per_item, chosen


def boot_diff(items, a, b, reps=2000, seed=0):
    """IC95 de mean(cost_a - cost_b) remuestreando semillas."""
    by = collections.defaultdict(list)
    for it in items:
        by[it["seed"]].append(a[it["id"]][0] - b[it["id"]][0])
    seeds = sorted(by)
    rng = random.Random(seed)
    point = sum(sum(v) for v in by.values()) / sum(len(v) for v in by.values())
    stats = []
    for _ in range(reps):
        smp = [rng.choice(seeds) for _ in seeds]
        tot = sum(sum(by[s]) for s in smp); n = sum(len(by[s]) for s in smp)
        stats.append(tot / n)
    stats.sort()
    return point, stats[int(0.025 * reps)], stats[int(0.975 * reps) - 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="openai/gpt-4o-mini")
    ap.add_argument("--battery", default=os.path.join(ROOT, "data", "acc_route.jsonl"))
    ap.add_argument("--traj", default=None)
    ap.add_argument("--risk_max", type=float, default=0.05)
    a = ap.parse_args()
    global RISK_MAX
    RISK_MAX = a.risk_max
    rtag = "" if abs(a.risk_max - 0.05) < 1e-12 else f"_risk{a.risk_max:g}"
    tag = a.model.replace("/", "_")
    trpath = a.traj or os.path.join(ROOT, "results", f"route_traj_{tag}.jsonl")
    trajs = {}
    for l in open(trpath, encoding="utf-8"):
        r = json.loads(l); trajs[r["id"]] = r
    ab3 = os.path.join(ROOT, "results", f"route_traj_{tag}_abstain3.jsonl")
    has_u1 = os.path.exists(ab3)
    if has_u1:
        for l in open(ab3, encoding="utf-8"):
            r = json.loads(l)
            if r["id"] in trajs:
                trajs[r["id"]]["abstain3"] = r["abstain3"]
    items = [it for it in (json.loads(l) for l in open(a.battery, encoding="utf-8")) if it["id"] in trajs]

    # regex R0: clausula del contexto con mayor BM25 frente al hecho, regla de discrecionalidad del paper
    rows = bab.load_rows()
    bm = vti.BM25([r["text"] for r in rows])

    def bm_score(q, text):
        tf = collections.Counter(vti.toks(text)); L = sum(tf.values()) or 1; s = 0.0
        for w in set(q):
            if w in tf:
                df = bm.df.get(w, 0)
                idf = math.log(1 + (bm.N - df + 0.5) / (df + 0.5))
                s += idf * tf[w] * (bm.k1 + 1) / (tf[w] + bm.k1 * (1 - bm.b + bm.b * L / bm.avg))
        return s

    def discretionary(text):
        return bool(bab.DISCRETION.search(text)) or (bool(bab.QUALITATIVE.search(text)) and not bab.HAS_NUM.search(text))

    regex = {}
    for it in items:
        q = vti.toks(it["fact"])
        regex[it["id"]] = [discretionary(max(ctx, key=lambda c: bm_score(q, c))) for ctx in it["contexts"]]

    POL = ["E0", "E1", "R0", "T1", "T1_notype"] + (["U1"] if has_u1 else []) + ["ORACLE_S", "ORACLE_T"]
    report = dict(model=a.model, n_items=len(items), sets={})
    md = [f"# Experimento de enrutamiento — {a.model}", "", f"Ítems con trayectoria: {len(items)}", ""]

    # confusion de tipo en la ronda 0 (argmax de la cabeza tipada)
    conf = collections.defaultdict(collections.Counter)
    for it in items:
        p, _ = trajs[it["id"]]["typed"][0]
        conf[it["condition"]][max(p, key=p.get)] += 1
    report["typed_argmax_round0"] = {k: dict(v) for k, v in conf.items()}
    md += ["## Argmax de la cabeza tipada en la ronda 0", "", "| condición | COMPLIES | VIOLATES | INSUFFICIENT | INDETERMINATE |", "|---|---|---|---|---|"]
    for k in ["D", "D_words", "INS", "IND_del", "IND_delnum", "IND_sil", "IND_real"]:
        c = conf.get(k, {})
        md.append(f"| {k} | " + " | ".join(str(c.get(x, 0)) for x in ["COMPLIES", "VIOLATES", "INSUFFICIENT", "INDETERMINATE"]) + " |")
    md.append("")

    for sname, conds in SETS.items():
        sit = [it for it in items if it["condition"] in conds]
        if not sit:
            continue
        srep = dict(conditions=conds, n=len(sit), n_seeds=len({it["seed"] for it in sit}), by_rho={})
        md += [f"## Conjunto `{sname}` ({', '.join(conds)}; n = {len(sit)}, conglomerados = {srep['n_seeds']})", ""]
        for rho in RHOS:
            res, per = {}, {}
            for pol in POL:
                pi, ch = crossfit(pol, sit, trajs, rho, regex)
                per[pol] = pi
                res[pol] = dict(summarize(list(pi.values())), params={str(k): v for k, v in ch.items()})
                bycond = {}
                for cnd in conds:
                    o = [pi[it["id"]] for it in sit if it["condition"] == cnd]
                    bycond[cnd] = summarize(o)
                res[pol]["by_condition"] = bycond
            contr = {}
            for x, y in [("E1", "T1"), ("T1_notype", "T1"), ("E1", "R0"), ("E0", "T1"), ("E1", "ORACLE_T")] + ([("U1", "T1"), ("E1", "U1")] if has_u1 else []):
                pt, lo, hi = boot_diff(sit, per[x], per[y])
                contr[f"{x}-{y}"] = dict(diff=pt, ci95=[lo, hi], saving_pct=100 * pt / res[x]["cost"] if res[x]["cost"] else None)
            gap = res["E1"]["cost"] - res["ORACLE_T"]["cost"]
            contr["capture_T1_of_oracle_gap"] = (res["E1"]["cost"] - res["T1"]["cost"]) / gap if gap > 1e-9 else None
            srep["by_rho"][str(rho)] = dict(policies=res, contrasts=contr)
            if rho in (2, RHO_PRIMARY, 50):
                md += [f"### ρ = c_h/c_r = {rho}", "", "| política | coste/ítem | riesgo selectivo | compromete | deriva | rondas |", "|---|---|---|---|---|---|"]
                for pol in POL:
                    r = res[pol]
                    md.append(f"| {pol} | {r['cost']:.3f} | {r['risk']:.3f} | {r['commit_rate']:.2f} | {r['escalation_rate']:.2f} | {r['mean_rounds']:.2f} |")
                md += ["", "| contraste | diferencia (IC95) | ahorro % |", "|---|---|---|"]
                for k, v in contr.items():
                    if isinstance(v, dict):
                        md.append(f"| {k} | {v['diff']:+.3f} ({v['ci95'][0]:+.3f}, {v['ci95'][1]:+.3f}) | {v['saving_pct']:.1f} |" if v["saving_pct"] is not None else f"| {k} | {v['diff']:+.3f} | — |")
                md += [f"| captura del hueco del oráculo por T1 | {contr['capture_T1_of_oracle_gap']} | |", ""]
        report["sets"][sname] = srep

    # ---- hipotesis preregistradas
    P = report["sets"].get("primary", {}).get("by_rho", {})
    h = {}
    if P:
        c10 = P[str(RHO_PRIMARY)]["contrasts"]["E1-T1"]
        h["H1_primary"] = dict(saving_pct=c10["saving_pct"], ci95=c10["ci95"],
                               pass_=bool(c10["saving_pct"] is not None and c10["saving_pct"] >= 10 and c10["ci95"][0] > 0))
        cap = P[str(RHO_PRIMARY)]["contrasts"]["capture_T1_of_oracle_gap"]
        h["H2_capture"] = dict(capture=cap, pass_=bool(cap is not None and cap >= 0.5))
        c2 = P["2"]["contrasts"]["E1-T1"]
        h["H3_boundary_rho2"] = dict(saving_pct=c2["saving_pct"], pass_=bool(c2["saving_pct"] is not None and c2["saving_pct"] < 5))
        nt = P[str(RHO_PRIMARY)]["contrasts"]["T1_notype-T1"]
        h["S1_type_routing_vs_same_head"] = dict(saving_pct=nt["saving_pct"], ci95=nt["ci95"])
    C = report["sets"].get("control_silence", {}).get("by_rho", {})
    if C:
        cc = C[str(RHO_PRIMARY)]["contrasts"]["E1-T1"]
        h["C1_control_no_gain"] = dict(saving_pct=cc["saving_pct"], ci95=cc["ci95"], pass_=bool(cc["ci95"][0] <= 0))
    report["hypotheses"] = h
    md += ["## Hipótesis preregistradas", "", "```", json.dumps(h, ensure_ascii=False, indent=1), "```"]

    json.dump(report, open(os.path.join(ROOT, "results", f"route_analysis_{tag}{rtag}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(ROOT, "results", f"route_analysis_{tag}{rtag}.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("\n".join(md[-40:]))


if __name__ == "__main__":
    main()
