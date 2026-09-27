# -*- coding: utf-8 -*-
"""
20_framing_probe.py -- ¿es la indeterminación normativa detectable, y depende del encuadre?

MOTIVO. La corrida completa dio I ~ 0 en las cinco condiciones. Dos lecturas posibles
(planteadas por Maikel el 6-sep):
  (a) la vaguedad normativa NO es indeterminación evidencial -> ningún canal evidencial
      puede verla, e I~0 es la conducta CORRECTA del instrumento;
  (b) preguntamos mal -> el encuadre de la tercera pregunta está mal apuntado.
Este experimento las separa, y es independiente del defecto de emparejamiento de la
condición A (auditado: solo 20-27 % genuinamente indeterminados), porque NO usa pares
afirmación-documento: interroga la cláusula directamente.

DISEÑO. 94 cláusulas discrecionales (positivas) vs 94 decidibles (control negativo),
del mismo corpus CODE-ACCORD. Para cada cláusula se toma la probabilidad de vinculación
(entailment) del cross-encoder NLI bajo varias hipótesis:
  - EVID  : encuadre evidencial, el que usa hoy coordinates.py
  - APPL  : encuadre aplicativo, pregunta por umbral no cuantificado
  - JUDG  : encuadre de delegación, pregunta por juicio profesional
Métrica: AUROC discriminando discrecional vs decidible. Sin umbral, sin ajuste.

LECTURA. Si EVID ~ 0,5 y APPL/JUDG >> 0,5 -> (b) es cierta y el canal se puede reapuntar.
Si todos ~ 0,5 -> (a) es cierta: el objeto es otro y ningún encuadre de este instrumento
lo alcanza. Los dos resultados son publicables.
"""
import os, sys, json, re
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_acc_battery as B

MODEL = "cross-encoder/nli-deberta-v3-base"

FRAMINGS = {
    "EVID": "It is uncertain whether this requirement is met.",
    "APPL": "This provision does not state a measurable threshold.",
    "JUDG": "This provision leaves the requirement to professional judgement.",
    # control de sanidad: una hipótesis que NO debería separar
    "CTRL": "This provision concerns a building.",
}


def auroc(pos, neg):
    """AUROC por el estadístico U de Mann-Whitney, sin dependencias."""
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    allv = np.concatenate([pos, neg])
    order = allv.argsort()
    ranks = np.empty(len(allv), float)
    ranks[order] = np.arange(1, len(allv) + 1)
    # promediar rangos de empates
    for v in np.unique(allv):
        m = allv == v
        if m.sum() > 1:
            ranks[m] = ranks[m].mean()
    n1, n2 = len(pos), len(neg)
    r1 = ranks[:n1].sum()
    return (r1 - n1 * (n1 + 1) / 2) / (n1 * n2)


def boot_ci(pos, neg, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    pos, neg = np.asarray(pos), np.asarray(neg)
    vals = [auroc(rng.choice(pos, len(pos), True), rng.choice(neg, len(neg), True))
            for _ in range(n)]
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def main():
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch

    rows = B.load_rows()
    disc = [r["text"] for r in rows if r["discretionary"]]
    deci = [r["text"] for r in rows if r["decidable"]]
    print(f"discrecionales (positivas): {len(disc)}   decidibles (control): {len(deci)}")

    tok = AutoTokenizer.from_pretrained(MODEL)
    mdl = AutoModelForSequenceClassification.from_pretrained(MODEL).eval()
    labels = [mdl.config.id2label[i].lower() for i in range(mdl.config.num_labels)]
    ent_ix = [i for i, l in enumerate(labels) if "entail" in l][0]
    print(f"etiquetas del modelo: {labels}  -> indice de entailment = {ent_ix}")

    def pent(premises, hypothesis, bs=16):
        out = []
        for i in range(0, len(premises), bs):
            chunk = premises[i:i + bs]
            enc = tok(chunk, [hypothesis] * len(chunk), return_tensors="pt",
                      truncation=True, padding=True, max_length=256)
            with torch.no_grad():
                p = torch.softmax(mdl(**enc).logits, -1)[:, ent_ix]
            out.extend(p.tolist())
        return out

    res = {}
    for name, hyp in FRAMINGS.items():
        p = pent(disc, hyp)
        n = pent(deci, hyp)
        a = auroc(p, n)
        lo, hi = boot_ci(p, n)
        res[name] = dict(hypothesis=hyp, auroc=a, ci95=[lo, hi],
                         mean_discretionary=float(np.mean(p)),
                         mean_decidable=float(np.mean(n)))
        print(f"\n[{name}] «{hyp}»")
        print(f"   AUROC = {a:.3f}   IC95 bootstrap [{lo:.3f}, {hi:.3f}]")
        print(f"   P(entail) media -> discrecionales {np.mean(p):.3f} | decidibles {np.mean(n):.3f}")

    os.makedirs(os.path.join(HERE, "..", "results"), exist_ok=True)
    out = os.path.join(HERE, "..", "results", "framing_probe.json")
    json.dump(dict(model=MODEL, n_discretionary=len(disc), n_decidable=len(deci),
                   framings=res), open(out, "w", encoding="utf-8"), indent=2,
              ensure_ascii=False)
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# LINEA BASE TRIVIAL (anadida 2026-09-07 tras revision adversarial).
# Las clases estan separadas POR CONSTRUCCION segun lleven digitos: "decidible"
# exige HAS_NUM y "no decidible cualitativa" exige NO HAS_NUM. Cualquier lectura
# de los AUROC de arriba tiene que compararse contra esto o esta confundida.
# ---------------------------------------------------------------------------
def trivial_digit_baseline():
    import re, json
    rows = B.load_rows()
    disc = [r["text"] for r in rows if r["discretionary"]]
    deci = [r["text"] for r in rows if r["decidable"]]
    score = lambda s: 0.0 if re.search(r"\d", s) else 1.0   # alto = parece delegada
    a = auroc([score(s) for s in disc], [score(s) for s in deci])
    out = dict(baseline="ausencia de digito en la clausula", auroc=float(a),
               n_discretionary=len(disc), n_decidable=len(deci),
               nota="las clases estan separadas por construccion; comparar todo AUROC contra esto")
    p = os.path.join(HERE, "..", "results", "framing_trivial_baseline.json")
    json.dump(out, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"linea base trivial (ausencia de digito): AUROC = {a:.3f}  -> {p}")
    return a
