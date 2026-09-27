# -*- coding: utf-8 -*-
"""
45_codex_audit.py -- auditoria INDEPENDIENTE de las etiquetas de oro de ACC-Route v2 con Codex CLI
(familia OpenAI, distinta del generador deepseek). Se corre ANTES de cualquier agente.

Por semilla, cinco comprobaciones:
  q1  el umbral es un requisito de cumplimiento (no una condicion de alcance)
  q2  el veredicto de oro (CUMPLE / INCUMPLE) es correcto para el valor de diseno
  q3  el hecho "sin valor" no declara ni implica el valor
  q4  la gemela delegada no fija umbral verificable para la propiedad
  q5  ninguna otra clausula del contexto del mundo IND_del fija umbral para esa propiedad

Semillas con alguna comprobacion en falso quedan EXCLUIDAS del analisis confirmatorio.
Salida: results/codex_audit_route2.json
"""
import os, json, subprocess, argparse, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")

SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["results"],
    "properties": {"results": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["seed", "q1_requirement", "q2_verdict_correct", "q3_missing_ok", "q4_twin_no_threshold", "q5_no_other_threshold", "note"],
        "properties": {"seed": {"type": "string"}, "q1_requirement": {"type": "boolean"}, "q2_verdict_correct": {"type": "boolean"},
                       "q3_missing_ok": {"type": "boolean"}, "q4_twin_no_threshold": {"type": "boolean"},
                       "q5_no_other_threshold": {"type": "boolean"}, "note": {"type": "string"}}}}}}

PROMPT = """You are auditing gold labels of a building-code compliance benchmark. Do not run commands; reason only from the text below.
For EACH seed answer five yes/no checks, strictly:
q1_requirement: in CLAUSE, the THRESHOLD is a requirement a design must satisfy to comply (false if it is only a scope/applicability condition, an example, or optional).
q2_verdict_correct: given CLAUSE and THRESHOLD, a design described by FACT correctly has the verdict GOLD_VERDICT.
q3_missing_ok: FACT_MISSING does not state or imply the value of the property.
q4_twin_no_threshold: TWIN does not fix any verifiable numeric threshold for this property (the requirement is left to judgement).
q5_no_other_threshold: none of the OTHER_CLAUSES fixes a verifiable numeric threshold for this same property of this same element.
Use "note" only to explain any false answer (empty string otherwise). Return one result per seed, same seed ids.

SEEDS:
{packet}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk", type=int, default=15)
    a = ap.parse_args()
    items = [json.loads(l) for l in open(os.path.join(ROOT, "data", "acc_route2.jsonl"), encoding="utf-8")]
    by = {}
    for it in items:
        if it["seed"].startswith("s"):
            by.setdefault(it["seed"], {})[it["condition"]] = it
    seeds = sorted(by)
    out_path = os.path.join(ROOT, "results", "codex_audit_route2.json")
    done = json.load(open(out_path, encoding="utf-8")) if os.path.exists(out_path) else {}
    todo = [s for s in seeds if s not in done]
    schema_file = os.path.join(tempfile.gettempdir(), "codex_audit_schema.json")
    json.dump(SCHEMA, open(schema_file, "w"))
    for k in range(0, len(todo), a.chunk):
        chunk = todo[k:k + a.chunk]
        blocks = []
        for sd in chunk:
            d = by[sd]
            others = [c for c in d["IND_del"]["contexts"][-1] if c != d["IND_del"]["twin"]]
            blocks.append(json.dumps(dict(seed=sd, CLAUSE=d["D"]["clause"], THRESHOLD=f"{d['D']['prop']} {d['D']['threshold']}",
                                          FACT=d["D"]["fact"], GOLD_VERDICT=d["D"]["gold_verdict"], FACT_MISSING=d["D"]["fact_missing"],
                                          TWIN=d["IND_del"]["twin"], OTHER_CLAUSES=others), ensure_ascii=False))
        prompt = PROMPT.replace("{packet}", "\n".join(blocks))
        last = os.path.join(tempfile.gettempdir(), f"codex_audit_{k}.json")
        cmd = ["codex", "exec", "--skip-git-repo-check", "-s", "read-only", "--output-schema", schema_file, "-o", last, "-"]
        p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8", timeout=1800, shell=(os.name == "nt"))
        try:
            res = json.load(open(last, encoding="utf-8"))["results"]
        except Exception as e:
            print("fallo en bloque", k, e, p.stderr[-500:]); continue
        for r in res:
            if r["seed"] in chunk:
                done[r["seed"]] = r
        json.dump(done, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"bloque {k}: {len(res)} resultados; acumulado {len(done)}/{len(seeds)}", flush=True)
    bad = {s: r for s, r in done.items() if not all(r[q] for q in ["q1_requirement", "q2_verdict_correct", "q3_missing_ok", "q4_twin_no_threshold", "q5_no_other_threshold"])}
    summary = {q: sum(1 for r in done.values() if not r[q]) for q in ["q1_requirement", "q2_verdict_correct", "q3_missing_ok", "q4_twin_no_threshold", "q5_no_other_threshold"]}
    print("auditadas", len(done), "de", len(seeds), "; con algun fallo:", len(bad), "; fallos por comprobacion:", summary)


if __name__ == "__main__":
    main()
