# -*- coding: utf-8 -*-
"""
48_dynamic_u_rival.py -- CHEQUEO DE ROBUSTEZ EXPLORATORIO (no preregistrado; 27-sep-2026).

Motivo: RESULTADOS_RUTEO2.md, sec. 6-7. El rival U de 47_analyze_route2.py solo sigue un PLAN fijo
de remedios. v1 tenia E1 ("escalar dinamico: deriva si la confianza no sube >= delta tras una ronda",
PLAN_EXPERIMENTO_RUTEO.md). Un agente sin tipo que aprende de su trayectoria podria recortar parte del
ahorro de T en IND_del. Este script anade ese rival SIN tocar 47 (atado al preregistro por sha256):
importa 47 como modulo, reutiliza Env, verdict, run_typed, crossfit, boot y los costes, y registra
una politica nueva en el diccionario POLICIES en memoria.

U_dyn(tau, delta, B, try_rfi, first)  -- cabeza sin tipo (untyped3):
  en cada estado: si conf >= tau -> comprometer.
  'estancado' si (hubo un paso previo) y conf - conf_prev < delta.
  si estancado o t >= B:  RFI una vez si try_rfi y no usada; si no, derivar.
  si no: buscar una ronda (t += 1).
  first = "R": el primer remedio es la RFI (si try_rfi), luego sigue la regla.
  delta = -1 -> nunca se estanca (busca hasta B); 0 -> estancado si baja;
  0.19 -> estancado si no sube al menos una muestra de k = 5; 0.39 -> si no sube dos.

Criterio (fijado por Maikel, 27-sep): si el ahorro de T en IND_del sobrevive a U_dyn, el hallazgo por
canal queda solido; si no, el paper lo dice.

Uso: python code/48_dynamic_u_rival.py --samples results/route2_samples_openai_gpt-oss-120b_low.jsonl
Salida: results/route2_dynamic_u_rival.json (todas las configuraciones de 47 en una corrida).
"""
import os, sys, json, itertools, importlib.util, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
spec = importlib.util.spec_from_file_location("a47", os.path.join(HERE, "47_analyze_route2.py"))
a47 = importlib.util.module_from_spec(spec); spec.loader.exec_module(a47)

DELTAS = [-1.0, 0.0, 0.19, 0.39]
BS = list(range(a47.R + 1))


def run_untyped_dynamic(env, tau, delta, B, try_rfi, first):
    t, rfi, cost, prev = 0, 0, 0.0, None
    for step in range(2 * a47.R + 4):
        v, c = a47.verdict(env.p("untyped3", t, rfi))
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


GRID = [g for g in itertools.product(a47.TAUS, DELTAS, BS, (False, True), ("S", "R"))
        if not (g[4] == "R" and not g[3])]
a47.POLICIES["U_dyn"] = (lambda env, prm: run_untyped_dynamic(env, *prm), GRID)

CONFIGS = {  # mismas configuraciones que route2_analysis_*.json
    "primary": dict(risk_max=0.05, c_s=10.0, c_e_mult=1.0),
    "norisk": dict(risk_max=1.0, c_s=10.0, c_e_mult=1.0),
    "ce3": dict(risk_max=0.05, c_s=10.0, c_e_mult=3.0),
    "norisk_ce3": dict(risk_max=1.0, c_s=10.0, c_e_mult=3.0),
    "cs1": dict(risk_max=0.05, c_s=1.0, c_e_mult=1.0),
    "cs100": dict(risk_max=0.05, c_s=100.0, c_e_mult=1.0),
}
POLS = ["U", "U_dyn", "T", "ORACLE_T"]


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", required=True)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "route2_dynamic_u_rival.json"))
    a = ap.parse_args()
    if os.path.exists(a.out):
        sys.exit(f"{a.out} ya existe; no se sobrescribe.")
    excluded = set(json.load(open(os.path.join(ROOT, "results", "codex_audit_route2_excluded.json"))))
    samples = {json.loads(l)["id"]: json.loads(l) for l in open(a.samples, encoding="utf-8")}
    items = [it for it in (json.loads(l) for l in open(os.path.join(ROOT, "data", "acc_route2.jsonl"), encoding="utf-8"))
             if it["id"] in samples and it["seed"] not in excluded]
    rep = dict(status="EXPLORATORY robustness check, not preregistered",
               sha256=dict(samples=sha(a.samples), a47=sha(os.path.join(HERE, "47_analyze_route2.py"))),
               n_items=len(items), grid_size_U_dyn=len(GRID), configs={})
    for cname, cfg in CONFIGS.items():
        costs = dict(c_s=cfg["c_s"], c_e=cfg["c_e_mult"] * a47.C_H)
        envs = {it["id"]: a47.Env(it, samples[it["id"]], a.k, costs) for it in items}
        out = {}
        for sname, conds in a47.SETS.items():
            sit = [it for it in items if it["condition"] in conds]
            per, res = {}, {}
            for pol in POLS:
                pi, ch = a47.crossfit(pol, sit, envs, cfg["risk_max"])
                per[pol] = pi
                res[pol] = dict(a47.summ(list(pi.values())), params={str(k): str(v) for k, v in ch.items()},
                                by_condition={c: a47.summ([pi[it["id"]] for it in sit if it["condition"] == c]) for c in conds})
            con = {}
            for x, y in [("U", "T"), ("U_dyn", "T"), ("U", "U_dyn")]:
                d, lo, hi = a47.boot(sit, per[x], per[y])
                con[f"{x}-{y}"] = dict(diff=d, ci95=[lo, hi], saving_pct=100 * d / res[x]["cost"] if res[x]["cost"] else None)
                for c in conds:
                    d, lo, hi = a47.boot(sit, per[x], per[y], subset={c})
                    con[f"{x}-{y}@{c}"] = dict(diff=d, ci95=[lo, hi])
            out[sname] = dict(policies=res, contrasts=con)
        rep["configs"][cname] = dict(cfg=cfg, sets=out)
        P = out["primary"]["contrasts"]
        print(f"\n== {cname} {cfg}")
        for pol in POLS:
            r = out["primary"]["policies"][pol]
            print(f"  {pol:8s} cost {r['cost']:8.1f} risk {r['risk']:.3f} commit {r['commit']:.2f} esc {r['escalate']:.2f} rfi {r['rfi']:.2f} {r['params']}")
        for key in ["U-T", "U_dyn-T", "U-U_dyn", "U-T@IND_del", "U_dyn-T@IND_del", "U_dyn-T@INS_reg",
                    "U_dyn-T@INS_design", "U_dyn-T@D"]:
            v = P[key]
            print(f"  {key:20s} {v['diff']:+9.1f} [{v['ci95'][0]:+.1f}, {v['ci95'][1]:+.1f}] {('%.1f%%' % v['saving_pct']) if v.get('saving_pct') is not None else ''}")
        for s2 in ("control_silence", "external_real"):
            v = out[s2]["contrasts"]["U_dyn-T"]
            print(f"  [{s2}] U_dyn-T {v['diff']:+.1f} [{v['ci95'][0]:+.1f}, {v['ci95'][1]:+.1f}] {v['saving_pct'] or 0:.1f}%")
    json.dump(rep, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
