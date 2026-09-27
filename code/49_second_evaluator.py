# -*- coding: utf-8 -*-
"""
49_second_evaluator.py -- segundo evaluador del canal I (27-sep-2026, autorizado por Maikel; tope duro 2,00 USD).

Por que: sec. 9 del manuscrito ("A single evaluator"): toda la bateria de 1.020 items se puntuo con un solo
cross-encoder NLI (DeBERTa-v3, Microsoft). Sin un segundo instrumento de otra familia, la planitud del canal
I se atribuye a ESE modelo y no a la clase de detectores evidenciales.

Instrumento: meta-llama/llama-3.3-70b-instruct via OpenRouter (familia Meta; distinta del NLI DeBERTa y de
los modelos OpenAI usados en el ruteo). Mismas preguntas y los dos encuadres de paper2 (coordinates.FRAMINGS),
P(Yes) desde top_logprobs, una llamada por canal (T, F, I), temperatura 0. Mismo pipeline de agregacion
(cum, K = 3), ajuste de umbrales en dev y decision en test que el NLI (policy.py / evaluate.py de paper2,
importados sin modificar).

Modos:
  --pilot N    N llamadas reales para medir tokens por llamada -> results/second_evaluator_cost_estimate.json
  --run        corrida completa; aborta si el gasto acumulado (usage.cost de OpenRouter) supera --budget.
Salidas: results/second_evaluator_llama33_f{1,2}.json, results/second_evaluator_cost.json, cache en results/llm_cache/.
"""
import os, sys, json, math, time, argparse, threading, random
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
P2 = os.path.join(ROOT, "..", "Neutrosophic_Annotated_Logic_2026", "paper2_ConflictAware_RAG", "code")
sys.path.insert(0, P2)
from coordinates import FRAMINGS, aggregate            # noqa: E402
from policy import decide, fit_thresholds, BEHAV       # noqa: E402
from evaluate import summarize, nonredundancy_test, collapse_test  # noqa: E402
from openai import OpenAI                             # noqa: E402

MODEL = "meta-llama/llama-3.3-70b-instruct"
SYSTEM = "You judge a single passage. Reply with exactly one word: Yes or No."   # identico a coordinates.py
RES = os.path.join(ROOT, "results")
CACHE = os.path.join(RES, "llm_cache", "second_evaluator_" + MODEL.replace("/", "_") + ".jsonl")
REPS = ["IND", "TF", "NORM", "RENORM3", "SCALAR"]
lock = threading.Lock(); SPENT = [0.0, 0, 0, 0]   # usd, calls, in_tok, out_tok
FAILED = []
cache = {}
if os.path.exists(CACHE):
    for l in open(CACHE, encoding="utf-8"):
        r = json.loads(l); cache[r["k"]] = r
cli = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"], timeout=60)


def ask(passage, question, budget):
    k = json.dumps([MODEL, passage, question])
    with lock:
        if k in cache:
            return cache[k]["p"]
        if SPENT[0] >= budget:
            raise RuntimeError("BUDGET")
    last = None
    for att in range(10):
        try:
            r = cli.chat.completions.create(
                model=MODEL, temperature=0, max_tokens=1, logprobs=True, top_logprobs=10,
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": f"Passage:\n{passage}\n\nQuestion: {question} Answer Yes or No."}],
                extra_body={"provider": {"require_parameters": True}, "usage": {"include": True}})
            lp = r.choices[0].logprobs
            if lp is None or not lp.content:
                raise RuntimeError("no logprobs")
            tops = lp.content[0].top_logprobs
            py = sum(math.exp(t.logprob) for t in tops if t.token.strip().lower().startswith("yes"))
            pn = sum(math.exp(t.logprob) for t in tops if t.token.strip().lower().startswith("no"))
            p = py / (py + pn) if py + pn > 0 else 0.5
            u = r.usage; cost = getattr(u, "cost", None)
            if cost is None:
                cost = (u.prompt_tokens * 0.10 + u.completion_tokens * 0.32) / 1e6
            rec = dict(k=k, p=p, mass=py + pn, tin=u.prompt_tokens, tout=u.completion_tokens, cost=cost)
            with lock:
                cache[k] = rec
                SPENT[0] += cost; SPENT[1] += 1; SPENT[2] += u.prompt_tokens; SPENT[3] += u.completion_tokens
                with open(CACHE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec) + "\n")
            return p
        except Exception as e:
            last = e; time.sleep(1.5 * (att + 1))
    FAILED.append(str(last)[:80])
    return None   # sin logprobs tras 10 intentos: el documento se excluye y se reporta


def questions(claim, fr):
    c = claim.rstrip(".")
    return {ch: FRAMINGS[fr][ch].format(c=c) for ch in ("T", "F", "I")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", type=int, default=0)
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--budget", type=float, default=1.80)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--framings", default="1,2")
    a = ap.parse_args()
    items = [json.loads(l) for l in open(os.path.join(ROOT, "data", "battery_acc.jsonl"), encoding="utf-8")]
    frs = [int(x) for x in a.framings.split(",")]
    pairs = sorted({(d["text"], it["claim"]) for it in items for d in it["docs"]})
    n_calls = len(pairs) * 3 * len(frs)

    if a.pilot:
        rng = random.Random(7); sample = rng.sample(pairs, a.pilot)
        for (txt, cl) in sample:
            ask(txt, questions(cl, 1)["I"], budget=0.05)
        recs = [cache[json.dumps([MODEL, t, questions(c, 1)["I"]])] for t, c in sample]
        tin = sum(r["tin"] for r in recs) / len(recs); tout = sum(r["tout"] for r in recs) / len(recs)
        cpc = sum(r["cost"] for r in recs) / len(recs)
        est = dict(model=MODEL, distinct_pairs=len(pairs), framings=frs, planned_calls=n_calls,
                   pilot_calls=len(recs), mean_prompt_tokens=tin, mean_completion_tokens=tout,
                   mean_cost_per_call_usd=cpc, pilot_cost_usd=sum(r["cost"] for r in recs),
                   estimated_total_usd=cpc * n_calls, hard_cap_usd=2.00,
                   decision="RUN" if cpc * n_calls * 1.15 < 2.00 else "REDUCE",
                   note="tokens medidos en llamadas reales (usage de OpenRouter); margen de seguridad 15 %")
        json.dump(est, open(os.path.join(RES, "second_evaluator_cost_estimate.json"), "w"), indent=1)
        print(json.dumps(est, indent=1)); return

    if not a.run:
        return
    for fr in frs:
        out_p = os.path.join(RES, f"second_evaluator_llama33_f{fr}.json")
        if os.path.exists(out_p):
            print("existe", out_p); continue
        def score_pair(pc):
            q = questions(pc[1], fr)
            return pc, {ch: ask(pc[0], q[ch], a.budget) for ch in ("T", "F", "I")}
        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            sc = dict(ex.map(score_pair, pairs))
        for it in items:
            it["scores"] = []; kept = []
            for d in it["docs"]:
                s = sc[(d["text"], it["claim"])]
                if any(v is None for v in s.values()):
                    continue
                kept.append(d); tot = s["T"] + s["F"] + s["I"]
                it["scores"].append({"T": s["T"], "I": s["I"], "F": s["F"], "p": s["T"],
                                     "soft3": [s["T"] / tot, s["I"] / tot, s["F"] / tot] if tot > 0 else [1 / 3] * 3})
            it["docs_used"] = kept
            it["reps"] = aggregate(it["scores"], agg="cum", K=3)
        dev = [it for it in items if it["split"] == "dev"]; test = [it for it in items if it["split"] == "test"]
        dev_rows = list({(d["text"], it["claim"]): (s["T"], s["I"], s["F"]) for it in dev for d, s in zip(it["docs_used"], it["scores"])}.values())
        nr = nonredundancy_test(dev_rows, seed=0); r2 = collapse_test(dev_rows, degree=2)
        ths = {rep: fit_thresholds(rep, [it["reps"][rep] for it in dev], [it["gold"] for it in dev])[0] for rep in REPS}
        preds = {rep: [decide(rep, it["reps"][rep], ths[rep]) for it in test] for rep in REPS}
        summary = summarize(test, preds)
        conds = sorted({it["condition"] for it in test}); means, emit, doc_I = {}, {}, {}
        for c in conds:
            rows = [it["reps"]["IND"] for it in test if it["condition"] == c]
            means[c] = dict(D=sum(r["T"] - r["F"] for r in rows) / len(rows), E=sum(r["T"] + r["F"] for r in rows) / len(rows),
                            I=sum(r["I"] for r in rows) / len(rows), n=len(rows))
            idx = [i for i, it in enumerate(test) if it["condition"] == c]
            emit[c] = {rep: {b: sum(1 for i in idx if preds[rep][i] == b) for b in BEHAV} for rep in ("IND", "TF")}
            dI = [s["I"] for it in test if it["condition"] == c for s in it["scores"]]
            doc_I[c] = dict(mean=sum(dI) / len(dI), share_gt_0_5=sum(x > 0.5 for x in dI) / len(dI),
                            max=max(dI), p90=sorted(dI)[int(0.9 * len(dI))], n_docs=len(dI))
        n_fail = sum(1 for it in items for d in it["docs"] if d not in it["docs_used"])
        out = dict(docs_excluded_no_logprobs=n_fail, model=MODEL, framing=fr, framing_text=FRAMINGS[fr], n_items=len(items), n_dev=len(dev), n_test=len(test),
                   gate_H4=dict(collapse_R2_insample=r2, nonredundancy=nr), thresholds=ths, summary=summary,
                   condition_means_IND=means, doc_level_I=doc_I, emitted_behaviours_test=emit,
                   status="secondary instrument; same battery, pipeline and thresholds procedure as NLI run nli_cum_acc")
        json.dump(out, open(out_p, "w", encoding="utf-8"), indent=1, default=str)
        print(f"\n== framing {fr}  spent so far {SPENT[0]:.4f} USD, {SPENT[1]} new calls")
        for c in conds:
            print(f"  {c:7s} I_mean(agg) {means[c]['I']:.3f}  docI_mean {doc_I[c]['mean']:.3f}  docI>0.5 {doc_I[c]['share_gt_0_5']:.3f}  IND emits IND-abst {emit[c]['IND']['ABSTAIN_INDETERMINATE']}/{means[c]['n']}")
        for rep in REPS:
            s = summary[rep]
            print(f"  {rep:8s} macroF1 {s['macro_f1']:.3f} acc {s['accuracy']:.3f} AN {s.get('AN_macro_f1')} per-cond {s['per_condition_acc']}")
        print("  IND vs TF", summary.get("delta_IND_vs", {}).get("TF"))
    prev = {}
    cp = os.path.join(RES, "second_evaluator_cost.json")
    if os.path.exists(cp):
        prev = json.load(open(cp))
    tot_cached = sum(r["cost"] for r in cache.values())
    json.dump(dict(model=MODEL, new_calls_this_run=SPENT[1], new_cost_this_run_usd=SPENT[0], in_tokens=SPENT[2], out_tokens=SPENT[3],
                   total_cost_all_cached_calls_usd=tot_cached, total_calls_cached=len(cache), hard_cap_usd=2.00,
                   source="usage.cost reported by OpenRouter per call (sum over cache file)", previous=prev or None),
              open(cp, "w"), indent=1)
    print(f"TOTAL gasto (todas las llamadas en cache): {tot_cached:.4f} USD en {len(cache)} llamadas")


if __name__ == "__main__":
    main()
