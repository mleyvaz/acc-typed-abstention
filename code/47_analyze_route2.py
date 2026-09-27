# -*- coding: utf-8 -*-
"""
47_analyze_route2.py -- DECISION de ACC-Route v2 (preregistrado en PREREG_RUTEO2.md).

Acciones y costes (USD):
  SEARCH    una ronda mas de recuperacion             c_s   (primario 10; sensibilidad 1, 100)
  RFI       peticion de informacion al proyectista    c_rfi = 1.080 (Navigant Construction Forum 2013)
  ESCALATE  interpretacion formal por la autoridad    c_h   = 5.510 (Seattle SDCI 2026: 10 h x 551 USD)
  COMMIT    veredicto; si es erroneo                  c_e   = c_h (primario; sensibilidad 3 c_h)
Un compromiso sobre un item INDETERMINATE, o sobre INS_design antes de la RFI, cuenta como erroneo
salvo que acierte el veredicto de oro (INS_design) -- en IND no existe veredicto correcto.

Politicas (confianza = fraccion de k muestras):
  U(tau, plan)        cabeza sin tipo; si no compromete, ejecuta un PLAN fijo de remedios ajustado
                      (E | S^b E | R E | S^b R E | R S^b E), b = 1..R                [RIVAL]
  T(tau,B,tau_i,tau_d) cabeza tipada; si no compromete, remedio segun el tipo modal:
                      MISSING_RULE -> buscar (hasta B) ; MISSING_DATA (frac >= tau_d) -> RFI (una vez) ;
                      INDETERMINATE (frac >= tau_i) -> derivar ; agotado -> derivar  [METODO]
  T_plan(tau, plan)   cabeza tipada usada como U (sin enrutar por tipo)             [ABLACION]
  ORACLE_T, ORACLE_U  tipo+veredicto de oro / veredicto de oro con plan fijo ajustado

Ajuste cruzado en 2 pliegues por CLAUSULA; min coste con riesgo selectivo <= RISK_MAX.
IC95 bootstrap por conglomerado (clausula), 2000 remuestreos.
"""
import os, json, random, argparse, itertools, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
R = 3
C_RFI, C_H = 1080.0, 5510.0
TAUS = [0.6, 0.8, 1.0, 1.01]
TAU_IS = [0.2, 0.6, 1.0]
TAU_DS = [0.2, 0.6, 1.0, 1.01]
PLANS = [("E",)] + [tuple(["S"] * b + ["E"]) for b in range(1, R + 1)] + [("R", "E")] + \
        [tuple(["S"] * b + ["R", "E"]) for b in range(1, R + 1)] + [tuple(["R"] + ["S"] * b + ["E"]) for b in range(1, R + 1)]
SETS = {"primary": ["D", "INS_reg", "INS_design", "IND_del"],
        "control_silence": ["D", "INS_reg", "INS_design", "IND_sil"],
        "external_real": ["D", "INS_reg", "INS_design", "IND_real"]}


def probs(counts, k):
    return {lab: n / k for lab, n in counts.items() if lab != "None"}


class Env:
    def __init__(self, it, samples, k, costs):
        self.it, self.s, self.k = it, samples, k
        self.c_s, self.c_e = costs["c_s"], costs["c_e"]

    def p(self, head, t, rfi):
        key = f"{t}|{rfi if self.it['missing_value'] else 0}"
        return probs(self.s[head][key], self.k)

    def commit(self, v, cost, t, rfi):
        it = self.it
        wrong = it["gold_type"] == "INDETERMINATE" or v != it["gold_verdict"]
        return dict(cost=cost + (self.c_e if wrong else 0), commit=1, error=int(wrong), esc=0, rfi=rfi, rounds=t)

    def escalate(self, cost, t, rfi):
        return dict(cost=cost + C_H, commit=0, error=0, esc=1, rfi=rfi, rounds=t)


def verdict(p):
    c, v = p.get("COMPLIES", 0), p.get("VIOLATES", 0)
    return ("COMPLIES", c) if c >= v else ("VIOLATES", v)


def run_plan(env, head, tau, plan):
    t, rfi, cost = 0, 0, 0.0
    steps = list(plan)
    while True:
        v, c = verdict(env.p(head, t, rfi))
        if c >= tau:
            return env.commit(v, cost, t, rfi)
        a = steps.pop(0)
        if a == "E":
            return env.escalate(cost, t, rfi)
        if a == "S":
            if t < R:
                t += 1; cost += env.c_s
        elif a == "R":
            if not rfi:
                rfi = 1; cost += C_RFI


def run_typed(env, tau, B, tau_i, tau_d):
    t, rfi, cost = 0, 0, 0.0
    for _ in range(2 * R + 4):
        p = env.p("typed5", t, rfi)
        v, c = verdict(p)
        if c >= tau:
            return env.commit(v, cost, t, rfi)
        types = sorted(["MISSING_RULE", "MISSING_DATA", "INDETERMINATE"], key=lambda x: -p.get(x, 0))
        acted = False
        for ty in types:
            if ty == "INDETERMINATE" and p.get(ty, 0) >= tau_i and p.get(ty, 0) > 0:
                return env.escalate(cost, t, rfi)
            if ty == "MISSING_DATA" and not rfi and p.get(ty, 0) >= tau_d and p.get(ty, 0) > 0:
                rfi = 1; cost += C_RFI; acted = True; break
            if ty == "MISSING_RULE" and t < B and p.get(ty, 0) > 0:
                t += 1; cost += env.c_s; acted = True; break
        if not acted:
            return env.escalate(cost, t, rfi)
    return env.escalate(cost, t, rfi)


def run_oracle_t(env):
    it = env.it
    if it["gold_type"] == "DECIDABLE":
        return env.commit(it["gold_verdict"], 0.0, 0, 0)
    if it["gold_type"] == "MISSING_RULE":
        g = it["governing_round"]
        if g is not None and g * env.c_s < C_H:
            return env.commit(it["gold_verdict"], g * env.c_s, g, 0)
        return env.escalate(0.0, 0, 0)
    if it["gold_type"] == "MISSING_DATA":
        return env.commit(it["gold_verdict"], C_RFI, 0, 1) if C_RFI < C_H else env.escalate(0.0, 0, 0)
    return env.escalate(0.0, 0, 0)


def run_oracle_u(env, plan):
    it = env.it
    t, rfi, cost = 0, 0, 0.0
    steps = list(plan)
    while True:
        ok = it["gold_type"] == "DECIDABLE" or (it["gold_type"] == "MISSING_RULE" and it["governing_round"] is not None and t >= it["governing_round"]) \
             or (it["gold_type"] == "MISSING_DATA" and rfi)
        if ok:
            return env.commit(it["gold_verdict"], cost, t, rfi)
        a = steps.pop(0)
        if a == "E":
            return env.escalate(cost, t, rfi)
        if a == "S" and t < R:
            t += 1; cost += env.c_s
        elif a == "R" and not rfi:
            rfi = 1; cost += C_RFI


POLICIES = {
    "U": (lambda env, prm: run_plan(env, "untyped3", *prm), list(itertools.product(TAUS, PLANS))),
    "T": (lambda env, prm: run_typed(env, *prm), list(itertools.product(TAUS, range(R + 1), TAU_IS, TAU_DS))),
    "T_plan": (lambda env, prm: run_plan(env, "typed5", *prm), list(itertools.product(TAUS, PLANS))),
    "ORACLE_U": (lambda env, prm: run_oracle_u(env, *prm), [(p,) for p in PLANS]),
    "ORACLE_T": (lambda env, prm: run_oracle_t(env), [()]),
}


def summ(outs):
    n = len(outs) or 1
    com = sum(o["commit"] for o in outs); err = sum(o["error"] for o in outs)
    return dict(cost=sum(o["cost"] for o in outs) / n, risk=err / com if com else 0.0, commit=com / n,
                escalate=sum(o["esc"] for o in outs) / n, rfi=sum(o["rfi"] for o in outs) / n,
                rounds=sum(o["rounds"] for o in outs) / n)


def crossfit(pol, items, envs, risk_max):
    fn, grid = POLICIES[pol]
    per, chosen = {}, {}
    for f in (0, 1):
        tune = [it for it in items if it["fold"] != f]; test = [it for it in items if it["fold"] == f]
        best = None
        for prm in grid:
            s = summ([fn(envs[it["id"]], prm) for it in tune])
            key = (s["risk"] > risk_max, s["cost"], s["risk"])
            if best is None or key < best[0]:
                best = (key, prm)
        chosen[f] = best[1]
        for it in test:
            per[it["id"]] = fn(envs[it["id"]], best[1])
    return per, chosen


def boot(items, a, b, subset=None, reps=2000, seed=0):
    by = collections.defaultdict(list)
    for it in items:
        if subset is None or it["condition"] in subset:
            by[it["clause_idx"]].append(a[it["id"]]["cost"] - b[it["id"]]["cost"])
    keys = sorted(by); rng = random.Random(seed)
    tot = lambda ks: sum(sum(by[k]) for k in ks) / max(1, sum(len(by[k]) for k in ks))
    st = sorted(tot([rng.choice(keys) for _ in keys]) for _ in range(reps))
    return tot(keys), st[int(0.025 * reps)], st[int(0.975 * reps) - 1]


def boot_prop_diff(items, pol_out, cond_a, cond_b, reps=2000, seed=0):
    """P(escala en el estado inicial | cond_a) - P(... | cond_b), bootstrap por clausula."""
    by = collections.defaultdict(lambda: {"a": [], "b": []})
    for it in items:
        o = pol_out[it["id"]]
        early = int(o["esc"] == 1 and o["rounds"] == 0 and o["rfi"] == 0)
        if it["condition"] == cond_a: by[it["clause_idx"]]["a"].append(early)
        if it["condition"] == cond_b: by[it["clause_idx"]]["b"].append(early)
    keys = sorted(by); rng = random.Random(seed)

    def stat(ks):
        A = [x for k in ks for x in by[k]["a"]]; B = [x for k in ks for x in by[k]["b"]]
        return (sum(A) / len(A) if A else 0) - (sum(B) / len(B) if B else 0)
    st = sorted(stat([rng.choice(keys) for _ in keys]) for _ in range(reps))
    return stat(keys), st[int(0.025 * reps)], st[int(0.975 * reps) - 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", required=True)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--risk_max", type=float, default=0.05)
    ap.add_argument("--c_s", type=float, default=10.0)
    ap.add_argument("--c_e_mult", type=float, default=1.0)
    ap.add_argument("--exclude", default=os.path.join(ROOT, "results", "codex_audit_route2_excluded.json"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    costs = dict(c_s=a.c_s, c_e=a.c_e_mult * C_H)
    excluded = set(json.load(open(a.exclude))) if os.path.exists(a.exclude) else set()
    samples = {json.loads(l)["id"]: json.loads(l) for l in open(a.samples, encoding="utf-8")}
    items = [it for it in (json.loads(l) for l in open(os.path.join(ROOT, "data", "acc_route2.jsonl"), encoding="utf-8"))
             if it["id"] in samples and it["seed"] not in excluded]
    envs = {it["id"]: Env(it, samples[it["id"]], a.k, costs) for it in items}
    rep = dict(args=vars(a), n_items=len(items), n_excluded_seeds=len(excluded), sets={})

    # tipo modal en el estado inicial
    modal = collections.defaultdict(collections.Counter)
    for it in items:
        p = envs[it["id"]].p("typed5", 0, 0)
        modal[it["condition"]][max(p, key=p.get) if p else "None"] += 1
    rep["typed5_modal_state0"] = {k: dict(v) for k, v in modal.items()}

    for sname, conds in SETS.items():
        sit = [it for it in items if it["condition"] in conds]
        res, per = {}, {}
        for pol in POLICIES:
            pi, ch = crossfit(pol, sit, envs, a.risk_max)
            per[pol] = pi
            res[pol] = dict(summ(list(pi.values())), params={str(k): str(v) for k, v in ch.items()},
                            by_condition={c: summ([pi[it["id"]] for it in sit if it["condition"] == c]) for c in conds})
        con = {}
        for x, y in [("U", "T"), ("T_plan", "T"), ("U", "ORACLE_T"), ("ORACLE_U", "ORACLE_T")]:
            d, lo, hi = boot(sit, per[x], per[y])
            con[f"{x}-{y}"] = dict(diff=d, ci95=[lo, hi], saving_pct=100 * d / res[x]["cost"] if res[x]["cost"] else None)
            for c in conds:
                d, lo, hi = boot(sit, per[x], per[y], subset={c})
                con[f"{x}-{y}@{c}"] = dict(diff=d, ci95=[lo, hi])
        gap = res["U"]["cost"] - res["ORACLE_T"]["cost"]
        con["capture"] = (res["U"]["cost"] - res["T"]["cost"]) / gap if gap > 1e-9 else None
        rep["sets"][sname] = dict(policies=res, contrasts=con, per_item_T={k: v for k, v in per["T"].items()})

    P, C = rep["sets"]["primary"], rep["sets"]["control_silence"]
    h = {}
    c = P["contrasts"]["U-T"]
    h["H1"] = dict(saving_pct=c["saving_pct"], ci95=c["ci95"], pass_=bool(c["saving_pct"] is not None and c["saving_pct"] >= 10 and c["ci95"][0] > 0))
    h["H2"] = dict(capture=P["contrasts"]["capture"], pass_=bool(P["contrasts"]["capture"] is not None and P["contrasts"]["capture"] >= 0.5))
    ci = P["contrasts"]["U-T@IND_del"]
    h["H3_IND_channel"] = dict(diff=ci["diff"], ci95=ci["ci95"], pass_=bool(ci["ci95"][0] > 0))
    cd = P["contrasts"]["U-T@INS_design"]
    h["H4_RFI_channel"] = dict(diff=cd["diff"], ci95=cd["ci95"], pass_=bool(cd["ci95"][0] > 0))
    both = {**P["per_item_T"], **C["per_item_T"]}
    allit = [it for it in items if it["condition"] in ("IND_del", "IND_sil")]
    d, lo, hi = boot_prop_diff(allit, both, "IND_del", "IND_sil")
    h["C1_reads_delegation"] = dict(early_escalation_diff=d, ci95=[lo, hi], pass_=bool(lo > 0))
    rep["hypotheses"] = h
    for s in rep["sets"].values():
        s.pop("per_item_T")
    json.dump(rep, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(dict(n=len(items), modal=rep["typed5_modal_state0"], hyp=h), ensure_ascii=False, indent=1))
    for sname, s in rep["sets"].items():
        print(f"\n[{sname}]")
        for pol, r in s["policies"].items():
            print(f"  {pol:9s} cost {r['cost']:8.1f}  risk {r['risk']:.3f}  commit {r['commit']:.2f}  esc {r['escalate']:.2f}  rfi {r['rfi']:.2f}  params {r['params']}")
        for k, v in s["contrasts"].items():
            if isinstance(v, dict) and "@" not in k:
                print(f"  {k:18s} {v['diff']:+8.1f} [{v['ci95'][0]:+.1f}, {v['ci95'][1]:+.1f}]  {v.get('saving_pct') or 0:.1f}%")
        print("  capture", s["contrasts"]["capture"])


if __name__ == "__main__":
    main()
