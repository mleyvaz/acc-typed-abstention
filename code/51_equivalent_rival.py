# -*- coding: utf-8 -*-
"""
51_equivalent_rival.py -- RIVAL EQUIVALENTE (exploratorio, no preregistrado; 27-sep-2026, aprobado por Maikel;
tope duro 1,00 USD).

Pregunta (hallazgo R2-2): cuanto de la ventaja de T sobre U se debe al TIPADO de la salida y cuanto a las
INSTRUCCIONES? En 46_run_agents2.py la cabeza typed5 recibe en el prompt las cinco situaciones con sus causas y
remedios (buscar / RFI / interpretacion formal); untyped3 solo recibe COMPLIES / VIOLATES / CANNOT_DETERMINE.

Cabeza nueva 'untyped_eq': MISMO prompt de sistema que typed5 (las mismas causas y los mismos remedios descritos
palabra por palabra), pero la salida NO lleva la causa: 1 COMPLIES, 2 VIOLATES, 3 CANNOT_DETERMINE (cualquiera de
los otros tres casos). Mismo modelo (openai/gpt-oss-120b, effort low, temperatura 1, k = 5), mismos estados y
mismos entornos (data/acc_route2.jsonl, semillas auditadas).
Politicas sobre esa cabeza, con la MISMA libertad de remedios que tiene cualquier agente sin tipo en 47/48:
  U_eq      plan fijo de remedios ajustado por rejilla (run_plan de 47)
  U_eq_dyn  regla dinamica de 48 (estancamiento de la confianza -> RFI -> derivar)
Nota: un agente que eligiera el remedio en su salida (BUSCAR / RFI / DERIVAR) seria isomorfo a la cabeza tipada
(remedio = tipo), por eso el rival equivalente no elige remedio en la salida.

Analisis: el de 47 (costes, riesgo selectivo, ajuste cruzado por clausula, bootstrap por clausula), importado sin
modificarlo, en las seis configuraciones de 48.

Modos: --pilot N (llamadas reales para medir tokens -> results/route2_equivalent_rival_cost_estimate.json)
       --run      (muestras -> results/route2_samples_equivalent_rival.jsonl; aborta al superar --budget)
       --analyze  (-> results/route2_equivalent_rival.json)
"""
import os, sys, json, argparse, importlib.util, itertools, random, threading, collections
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")


def load(name, fn):
    s = importlib.util.spec_from_file_location(name, os.path.join(HERE, fn))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


r46 = load("r46", "46_run_agents2.py")
m48 = load("m48", "48_dynamic_u_rival.py"); a47 = m48.a47
llm = r46.llm
MODEL, EFFORT, K = "openai/gpt-oss-120b", "low", 5
HEAD = "untyped_eq"
SYS_EQ = r46.SYS["typed5"].replace(
    "Classify the case as exactly one of:",
    "The case falls under exactly one of the following five situations:").replace(
    "Answer with the single digit only.",
    "Now answer only whether compliance can be determined. Reply 1 if the case is situation 1 (COMPLIES), "
    "2 if it is situation 2 (VIOLATES), and 3 if it is any of situations 3, 4 or 5 (CANNOT_DETERMINE). "
    "Do not say which of 3, 4 or 5 applies. Answer with the single digit only.")
LAB_EQ = {"1": "COMPLIES", "2": "VIOLATES", "3": "CANNOT_DETERMINE"}
RES = os.path.join(ROOT, "results")
SAMPLES = os.path.join(RES, "route2_samples_equivalent_rival.jsonl")
lock = threading.Lock()


def items_audited():
    exc = set(json.load(open(os.path.join(RES, "codex_audit_route2_excluded.json"))))
    return [it for it in (json.loads(l) for l in open(os.path.join(ROOT, "data", "acc_route2.jsonl"), encoding="utf-8"))
            if it["seed"] not in exc]


def jobs_for(items):
    J = []
    for it in items:
        for t in range(len(it["contexts"])):
            for rfi in ([0, 1] if it["missing_value"] else [0]):
                for j in range(K):
                    J.append((it["id"], t, rfi, j, r46.user_msg(r46.statement(it, rfi), it["contexts"][t])))
    return J


def spent():
    i, o, n = llm.USAGE.get(MODEL, [0, 0, 0]); pi, po = llm.PRICES[MODEL]
    return i / 1e6 * pi + o / 1e6 * po


def call(job, budget):
    iid, t, rfi, j, user = job
    with lock:
        if spent() > budget:
            raise RuntimeError("BUDGET")
    txt = llm.call_sample(MODEL, SYS_EQ, user, j, effort=EFFORT)
    return iid, t, rfi, r46.parse(txt, LAB_EQ)


def run_untyped_dynamic_head(env, head, tau, delta, B, try_rfi, first):
    t, rfi, cost, prev = 0, 0, 0.0, None
    for step in range(2 * a47.R + 4):
        v, c = a47.verdict(env.p(head, t, rfi))
        if c >= tau:
            return env.commit(v, cost, t, rfi)
        if step == 0 and first == "R" and try_rfi and not rfi:
            rfi = 1; cost += a47.C_RFI; prev = c; continue
        stalled = prev is not None and (c - prev) < delta
        if stalled or t >= B or t >= a47.R:
            if try_rfi and not rfi:
                rfi = 1; cost += a47.C_RFI; prev = c; continue
            return env.escalate(cost, t, rfi)
        t += 1; cost += env.c_s; prev = c
    return env.escalate(cost, t, rfi)


a47.POLICIES["U_eq"] = (lambda env, prm: a47.run_plan(env, HEAD, *prm), list(itertools.product(a47.TAUS, a47.PLANS)))
a47.POLICIES["U_eq_dyn"] = (lambda env, prm: run_untyped_dynamic_head(env, HEAD, *prm), m48.GRID)
POLS = ["U", "U_dyn", "U_eq", "U_eq_dyn", "T", "ORACLE_T"]
PAIRS = [("U", "T"), ("U_eq", "T"), ("U_eq_dyn", "T"), ("U", "U_eq")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", type=int, default=0)
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--analyze", action="store_true")
    ap.add_argument("--budget", type=float, default=0.95)
    ap.add_argument("--workers", type=int, default=24)
    a = ap.parse_args()
    items = items_audited()
    J = jobs_for(items)

    if a.pilot:
        rng = random.Random(3); sample = rng.sample(J, a.pilot)
        for jb in sample:
            call(jb, 0.05)
        i, o, n = llm.USAGE.get(MODEL, [0, 0, 0])
        per = spent() / max(n, 1)
        est = dict(model=MODEL, effort=EFFORT, k=K, planned_calls=len(J), pilot_calls=n,
                   mean_prompt_tokens=i / max(n, 1), mean_completion_tokens=o / max(n, 1),
                   pilot_cost_usd=spent(), est_cost_per_call_usd=per, estimated_total_usd=per * len(J),
                   prices_per_M=llm.PRICES[MODEL], hard_cap_usd=1.00,
                   decision="RUN" if per * len(J) * 1.3 < 1.00 else "REDUCE",
                   note="tokens medidos en llamadas reales (usage de OpenRouter, precios de llm.PRICES); margen 30 %")
        json.dump(est, open(os.path.join(RES, "route2_equivalent_rival_cost_estimate.json"), "w"), indent=1)
        print(json.dumps(est, indent=1)); return

    if a.run:
        counts = collections.defaultdict(collections.Counter)
        with ThreadPoolExecutor(a.workers) as ex:
            for iid, t, rfi, lab in ex.map(lambda jb: call(jb, a.budget), J):
                counts[(iid, t, rfi)][str(lab)] += 1
        with open(SAMPLES, "w", encoding="utf-8") as f:
            for it in items:
                f.write(json.dumps({"id": it["id"], HEAD: {f"{t}|{rfi}": dict(counts[(it["id"], t, rfi)])
                        for t in range(len(it["contexts"])) for rfi in ([0, 1] if it["missing_value"] else [0])}}) + "\n")
        i, o, n = llm.USAGE.get(MODEL, [0, 0, 0])
        nulls = sum(c.get("None", 0) for c in counts.values())
        json.dump(dict(model=MODEL, new_calls=n, in_tokens=i, out_tokens=o, cost_usd=spent(), null_answers=nulls,
                       total_calls=len(J), hard_cap_usd=1.00, prices_per_M=llm.PRICES[MODEL],
                       source="usage tokens de OpenRouter x precios de llm.PRICES (15-sep-2026)"),
                  open(os.path.join(RES, "route2_equivalent_rival_cost.json"), "w"), indent=1)
        print(llm.cost_report(), "nulas", nulls)

    if a.analyze:
        out = os.path.join(RES, "route2_equivalent_rival.json")
        base = {json.loads(l)["id"]: json.loads(l) for l in open(os.path.join(RES, "route2_samples_openai_gpt-oss-120b_low.jsonl"), encoding="utf-8")}
        for l in open(SAMPLES, encoding="utf-8"):
            r = json.loads(l); base[r["id"]][HEAD] = r[HEAD]
        items2 = [it for it in items if it["id"] in base]
        # tipo/veredicto modal de la cabeza equivalente en el estado inicial
        modal = collections.defaultdict(collections.Counter)
        conf0 = {}
        for it in items2:
            c = base[it["id"]][HEAD]["0|0"]; modal[it["condition"]][max(c, key=c.get) if c else "None"] += 1
        rep = dict(status="EXPLORATORY, not preregistered (after adversarial review R2)", n_items=len(items2),
                   modal_state0_untyped_eq={k: dict(v) for k, v in modal.items()}, configs={})
        for cname, cfg in m48.CONFIGS.items():
            costs = dict(c_s=cfg["c_s"], c_e=cfg["c_e_mult"] * a47.C_H)
            envs = {it["id"]: a47.Env(it, base[it["id"]], K, costs) for it in items2}
            outc = {}
            for sname, conds in a47.SETS.items():
                sit = [it for it in items2 if it["condition"] in conds]
                per, res = {}, {}
                for pol in POLS:
                    pi, ch = a47.crossfit(pol, sit, envs, cfg["risk_max"])
                    per[pol] = pi
                    res[pol] = dict(a47.summ(list(pi.values())), params={str(k): str(v) for k, v in ch.items()},
                                    by_condition={c: a47.summ([pi[it["id"]] for it in sit if it["condition"] == c]) for c in conds})
                con = {}
                for x, y in PAIRS:
                    d, lo, hi = a47.boot(sit, per[x], per[y])
                    con[f"{x}-{y}"] = dict(diff=d, ci95=[lo, hi], saving_pct=100 * d / res[x]["cost"] if res[x]["cost"] else None)
                    for c in conds:
                        d, lo, hi = a47.boot(sit, per[x], per[y], subset={c})
                        con[f"{x}-{y}@{c}"] = dict(diff=d, ci95=[lo, hi])
                outc[sname] = dict(policies=res, contrasts=con)
            rep["configs"][cname] = dict(cfg=cfg, sets=outc)
            P = outc["primary"]
            print(f"\n== {cname} {cfg}")
            for pol in POLS:
                r = P["policies"][pol]
                print(f"  {pol:9s} cost {r['cost']:8.1f} risk {r['risk']:.3f} commit {r['commit']:.2f} esc {r['escalate']:.2f} rfi {r['rfi']:.2f}")
            for x, y in PAIRS:
                for suf in ["", "@IND_del", "@INS_reg", "@INS_design", "@D"]:
                    v = P["contrasts"][f"{x}-{y}{suf}"]
                    print(f"  {x+'-'+y+suf:22s} {v['diff']:+9.1f} [{v['ci95'][0]:+.1f}, {v['ci95'][1]:+.1f}] {('%.1f%%' % v['saving_pct']) if v.get('saving_pct') is not None else ''}")
        json.dump(rep, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
