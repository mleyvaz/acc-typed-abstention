# -*- coding: utf-8 -*-
"""
42_run_agents.py -- PERCEPCION del experimento de enrutamiento.

Para cada item y cada ronda t = 0..R se consulta el modelo UNA vez por cabeza de salida, con
respuesta de un digito y probabilidades leidas de los logprobs (no confianza verbalizada, que en el
humo salio constante en 90 y habria hecho del escalar un rival de paja):
  typed   P(COMPLIES), P(VIOLATES), P(INSUFFICIENT), P(INDETERMINATE)
  scalar  P(COMPLIES), P(VIOLATES)
Las politicas (E0, E1, R0, T1, oraculos) se simulan despues en 43_analyze.py sobre estas
trayectorias: todas ven exactamente las mismas salidas del modelo y el mismo recuperador.

Salida: results/route_traj_<modelo>.jsonl
"""
import os, json, argparse, importlib.util
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
s = importlib.util.spec_from_file_location("llm", os.path.join(HERE, "llm.py"))
llm = importlib.util.module_from_spec(s); s.loader.exec_module(llm)

SYS_TYPED = """You are an automated building-code compliance checker. You receive a statement about a proposed building design and regulation clauses retrieved from the building code. Retrieval may be incomplete.
Classify the case as exactly one of:
1 = COMPLIES: a retrieved clause sets a verifiable requirement for this property and the design meets it.
2 = VIOLATES: a retrieved clause sets a verifiable requirement for this property and the design fails it.
3 = INSUFFICIENT: none of the retrieved clauses governs this property; searching the code further might find the governing clause.
4 = INDETERMINATE: a retrieved clause governs this property but does not fix a verifiable threshold (it leaves the matter to judgement), so further searching would not settle compliance and a human must interpret.
Answer with the single digit only."""

SYS_SCALAR = """You are an automated building-code compliance checker. You receive a statement about a proposed building design and regulation clauses retrieved from the building code. Retrieval may be incomplete.
Decide whether the design complies with the applicable requirement:
1 = COMPLIES
2 = VIOLATES
Answer with the single digit only."""

SYS_ABSTAIN3 = """You are an automated building-code compliance checker. You receive a statement about a proposed building design and regulation clauses retrieved from the building code. Retrieval may be incomplete.
Classify the case as exactly one of:
1 = COMPLIES: a retrieved clause sets a verifiable requirement for this property and the design meets it.
2 = VIOLATES: a retrieved clause sets a verifiable requirement for this property and the design fails it.
3 = CANNOT DETERMINE: compliance cannot be determined from the retrieved clauses.
Answer with the single digit only."""

LAB = {"1": "COMPLIES", "2": "VIOLATES", "3": "INSUFFICIENT", "4": "INDETERMINATE"}
LAB3 = {"1": "COMPLIES", "2": "VIOLATES", "3": "ABSTAIN"}


def user_msg(fact, ctx):
    return "Design statement: " + fact + "\n\nRetrieved clauses:\n" + "\n".join(f"[{i+1}] {c}" for i, c in enumerate(ctx))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="openai/gpt-4o-mini")
    ap.add_argument("--battery", default=os.path.join(ROOT, "data", "acc_route.jsonl"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--heads", default="typed,scalar")
    a = ap.parse_args()
    items = [json.loads(l) for l in open(a.battery, encoding="utf-8")]
    if a.limit:
        items = items[: a.limit]

    jobs = [(it, t, head) for it in items for t in range(len(it["contexts"])) for head in a.heads.split(",")]

    def run(job):
        it, t, head = job
        if head == "abstain3":
            p = llm.call_digit_probs(a.model, SYS_ABSTAIN3, user_msg(it["fact"], it["contexts"][t]), ["1", "2", "3"])
            return it["id"], t, head, ({LAB3[d]: round(v, 5) for d, v in p.items() if d in LAB3}, round(p["_raw_mass"], 4))
        if head == "typed":
            p = llm.call_digit_probs(a.model, SYS_TYPED, user_msg(it["fact"], it["contexts"][t]), ["1", "2", "3", "4"])
        else:
            p = llm.call_digit_probs(a.model, SYS_SCALAR, user_msg(it["fact"], it["contexts"][t]), ["1", "2"])
        probs = {LAB[d]: round(v, 5) for d, v in p.items() if d in LAB}
        return it["id"], t, head, (probs, round(p["_raw_mass"], 4))

    with ThreadPoolExecutor(a.workers) as ex:
        res = list(ex.map(run, jobs))
    traj = {}
    for iid, t, head, (v, c) in res:
        traj.setdefault(iid, {}).setdefault(head, {})[t] = (v, c)
    heads = a.heads.split(",")
    htag = "" if heads == ["typed", "scalar"] else "_" + "_".join(heads)
    out = os.path.join(ROOT, "results", f"route_traj_{a.model.replace('/', '_')}{htag}{'_smoke' if a.limit else ''}.jsonl")
    lowmass = 0
    with open(out, "w", encoding="utf-8") as f:
        for it in items:
            tr = traj[it["id"]]
            rec = dict(id=it["id"], **{h: [tr[h][t] for t in range(len(it["contexts"]))] for h in heads})
            lowmass += sum(m < 0.5 for h in heads for _, m in rec[h])
            f.write(json.dumps(rec) + "\n")
    bad = lowmass
    print(f"items {len(items)}; llamadas {len(jobs)}; salidas con masa de digitos validos < 0,5: {bad}")
    print(llm.cost_report())


if __name__ == "__main__":
    main()
