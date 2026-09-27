# -*- coding: utf-8 -*-
"""
49b_second_evaluator_probe.py -- sonda de encuadre (20_framing_probe.py) repetida con el segundo evaluador
(meta-llama/llama-3.3-70b-instruct), 27-sep-2026. Dentro del mismo tope duro de 2,00 USD del punto B.

Por que: en la bateria (49), la condicion A solo es genuina al 20-27 %, asi que A ~ N no distingue
"el canal no ve la delegacion" de "A es casi toda insuficiencia". La sonda interroga la CLAUSULA directamente
(94 discrecionales frente a 236 decidibles), sin pares afirmacion-documento, como 20_framing_probe.py.

Preguntas si/no (P(Yes) desde top_logprobs, temperatura 0), una por encuadre:
  EVID  "Is it uncertain whether this requirement is met?"                       (evidencial)
  APPL  "Does this provision leave its requirement without a measurable threshold?" (aplicativo)
  JUDG  "Does this provision leave the requirement to professional judgement?"      (delegacion)
  CTRL  "Does this provision concern a building?"                                   (sanidad)
Metricas: AUROC (discrecional vs decidible) con IC95 bootstrap; medias de P(Yes); y, para controlar el
confundido con los digitos, AUROC restringido a clausulas que CONTIENEN algun digito en ambos lados.
Salida: results/second_evaluator_probe_llama33.json (no sobrescribe).
"""
import os, sys, json, re, importlib.util
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import build_acc_battery as B  # noqa: E402

spec = importlib.util.spec_from_file_location("se49", os.path.join(HERE, "49_second_evaluator.py"))
se = importlib.util.module_from_spec(spec); spec.loader.exec_module(se)
spec2 = importlib.util.spec_from_file_location("fp20", os.path.join(HERE, "20_framing_probe.py"))
fp = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(fp)

Q = {"EVID": "Is it uncertain whether this requirement is met?",
     "APPL": "Does this provision leave its requirement without a measurable threshold?",
     "JUDG": "Does this provision leave the requirement to professional judgement?",
     "CTRL": "Does this provision concern a building?"}


def main():
    out = os.path.join(ROOT, "results", "second_evaluator_probe_llama33.json")
    if os.path.exists(out):
        sys.exit("ya existe")
    rows = B.load_rows()
    disc = [r["text"] for r in rows if r["discretionary"]]
    deci = [r["text"] for r in rows if r["decidable"]]
    n_calls = (len(disc) + len(deci)) * len(Q)
    prev = sum(r["cost"] for r in se.cache.values())
    est = n_calls * 3.1e-5
    print(f"llamadas {n_calls}; estimacion {est:.3f} USD (3,1e-5 USD/llamada medido en 49); gastado antes {prev:.3f}")
    if prev + est * 1.5 > 2.0:
        sys.exit("superaria el tope de 2 USD")
    from concurrent.futures import ThreadPoolExecutor
    res = {}
    has_d = lambda s: bool(re.search(r"\d", s))
    for name, q in Q.items():
        with ThreadPoolExecutor(12) as ex:
            p = list(ex.map(lambda t: se.ask(t, q, 1.0), disc))
            n = list(ex.map(lambda t: se.ask(t, q, 1.0), deci))
        ok = lambda xs: [x for x in xs if x is not None]
        pp, nn = ok(p), ok(n)
        a = fp.auroc(pp, nn); lo, hi = fp.boot_ci(pp, nn)
        pd = [x for x, t in zip(p, disc) if x is not None and has_d(t)]
        nd = [x for x, t in zip(n, deci) if x is not None and has_d(t)]
        ad = fp.auroc(pd, nd) if pd and nd else None
        adci = fp.boot_ci(pd, nd) if pd and nd else None
        res[name] = dict(question=q, auroc=a, ci95=[lo, hi], mean_p_discretionary=float(np.mean(pp)),
                         mean_p_decidable=float(np.mean(nn)), share_gt_0_5_discretionary=float(np.mean([x > 0.5 for x in pp])),
                         share_gt_0_5_decidable=float(np.mean([x > 0.5 for x in nn])), n_failed=len(p) + len(n) - len(pp) - len(nn),
                         digit_controlled=dict(n_discretionary_with_digit=len(pd), n_decidable=len(nd), auroc=ad, ci95=adci))
        print(name, json.dumps(res[name]))
    spent = sum(r["cost"] for r in se.cache.values())
    json.dump(dict(model=se.MODEL, n_discretionary=len(disc), n_decidable=len(deci), framings=res,
                   cost_this_probe_usd=spent - prev, total_second_evaluator_usd=spent, hard_cap_usd=2.0,
                   status="secondary instrument; direct clause probe, same classes as 20_framing_probe.py"),
              open(out, "w", encoding="utf-8"), indent=1)
    print(f"gasto sonda {spent - prev:.4f} USD; total segundo evaluador {spent:.4f} USD")


if __name__ == "__main__":
    main()
