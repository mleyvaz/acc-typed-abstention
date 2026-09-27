# -*- coding: utf-8 -*-
"""
46_run_agents2.py -- PERCEPCION de ACC-Route v2 con modelo de RAZONAMIENTO y confianza por FRECUENCIA.

Modelo: openai/gpt-oss-120b (OpenRouter), temperatura 1, k muestras por estado; la confianza de una
respuesta es la fraccion de muestras que la eligen (los modelos de razonamiento no entregan logprobs utiles).

Cabezas:
  typed5    1 COMPLIES, 2 VIOLATES, 3 MISSING_RULE (buscar), 4 MISSING_DATA (RFI), 5 INDETERMINATE (derivar)
  untyped3  1 COMPLIES, 2 VIOLATES, 3 CANNOT_DETERMINE

Estados: ronda de busqueda t = 0..R y, solo en INS_design, si ya se hizo la RFI (el valor aparece).
En los demas items la RFI no cambia la memoria de diseno: su estado post-RFI es identico y reutiliza muestras.

Salida: results/route2_samples_<modelo>_<effort>.jsonl  (una fila por item con conteos por estado y cabeza)
"""
import os, re, json, argparse, importlib.util, collections
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
s = importlib.util.spec_from_file_location("llm", os.path.join(HERE, "llm.py"))
llm = importlib.util.module_from_spec(s); s.loader.exec_module(llm)

INTRO = ("You are an automated building-code compliance checker. You receive a statement from a building design "
         "submission and regulation clauses retrieved from the building code. Retrieval may be incomplete.\n")

SYS = {
    "typed5": INTRO + """Classify the case as exactly one of:
1 = COMPLIES: a retrieved clause sets a verifiable requirement for this property, the design statement gives the value, and the design meets the requirement.
2 = VIOLATES: a retrieved clause sets a verifiable requirement for this property, the design statement gives the value, and the design fails the requirement.
3 = MISSING_RULE: none of the retrieved clauses governs this property; searching the code further might find the governing clause.
4 = MISSING_DATA: a retrieved clause sets a verifiable requirement for this property, but the design statement does not give the value needed; a request for information to the designer is required.
5 = INDETERMINATE: a retrieved clause governs this property but does not fix a verifiable threshold (it leaves the matter to judgement), so neither searching nor asking the designer would settle compliance; a formal interpretation by the authority is required.
Answer with the single digit only.""",
    "untyped3": INTRO + """Classify the case as exactly one of:
1 = COMPLIES: a retrieved clause sets a verifiable requirement for this property, the design statement gives the value, and the design meets the requirement.
2 = VIOLATES: a retrieved clause sets a verifiable requirement for this property, the design statement gives the value, and the design fails the requirement.
3 = CANNOT_DETERMINE: compliance cannot be determined from this information.
Answer with the single digit only.""",
}
LAB = {"typed5": {"1": "COMPLIES", "2": "VIOLATES", "3": "MISSING_RULE", "4": "MISSING_DATA", "5": "INDETERMINATE"},
       "untyped3": {"1": "COMPLIES", "2": "VIOLATES", "3": "CANNOT_DETERMINE"}}


def statement(it, rfi):
    if it["missing_value"] and not rfi:
        return it["fact_missing"]
    if it["missing_value"] and rfi:
        return it["fact"] + " (Value provided by the designer in response to a request for information.)"
    return it["fact"]


def user_msg(stmt, ctx):
    return "Design statement: " + stmt + "\n\nRetrieved clauses:\n" + "\n".join(f"[{i+1}] {c}" for i, c in enumerate(ctx))


def parse(text, labels):
    m = re.search(r"[1-5]", (text or "").strip())
    return labels.get(m.group(0)) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="openai/gpt-oss-120b")
    ap.add_argument("--effort", default="low")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--heads", default="typed5,untyped3")
    ap.add_argument("--conditions", default="")
    ap.add_argument("--exclude_seeds", default="")
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    items = [json.loads(l) for l in open(os.path.join(ROOT, "data", "acc_route2.jsonl"), encoding="utf-8")]
    if a.conditions:
        items = [it for it in items if it["condition"] in a.conditions.split(",")]
    if a.exclude_seeds:
        exc = set(json.load(open(a.exclude_seeds)))
        items = [it for it in items if it["seed"] not in exc]
    heads = a.heads.split(",")

    jobs = []
    for it in items:
        for t in range(len(it["contexts"])):
            for rfi in ([0, 1] if it["missing_value"] else [0]):
                for h in heads:
                    for j in range(a.k):
                        jobs.append((it["id"], t, rfi, h, j, SYS[h], user_msg(statement(it, rfi), it["contexts"][t])))

    def run(job):
        iid, t, rfi, h, j, sys_, user = job
        return iid, t, rfi, h, parse(llm.call_sample(a.model, sys_, user, j, effort=a.effort), LAB[h])

    counts = collections.defaultdict(collections.Counter)
    n = 0
    with ThreadPoolExecutor(a.workers) as ex:
        for iid, t, rfi, h, lab in ex.map(run, jobs):
            counts[(iid, t, rfi, h)][str(lab)] += 1
            n += 1
            if n % 2000 == 0:
                print(f"{n}/{len(jobs)}", flush=True)
    out = os.path.join(ROOT, "results", f"route2_samples_{a.model.replace('/', '_')}_{a.effort}{a.tag}.jsonl")
    with open(out, "w", encoding="utf-8") as f:
        for it in items:
            rec = {"id": it["id"]}
            for h in heads:
                rec[h] = {f"{t}|{rfi}": dict(counts[(it["id"], t, rfi, h)])
                          for t in range(len(it["contexts"])) for rfi in ([0, 1] if it["missing_value"] else [0])}
            f.write(json.dumps(rec) + "\n")
    print(f"items {len(items)}; llamadas {len(jobs)}; nulas {sum(c.get('None', 0) for c in counts.values())}")
    print(llm.cost_report())


if __name__ == "__main__":
    main()
