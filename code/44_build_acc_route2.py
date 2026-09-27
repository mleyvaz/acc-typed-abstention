# -*- coding: utf-8 -*-
"""
44_build_acc_route2.py -- bateria ACC-Route v2 (experimento decisivo, ver PLAN_RUTEO2 en PREREG_RUTEO2.md).

Cambios frente a 41 (v1):
  * MAS SEMILLAS: una semilla por RELACION de comparacion (no solo clausulas con una); las clausulas
    que fijan umbral sobre la misma propiedad ya no descartan la semilla: se BORRAN del corpus en los
    mundos indeterminados, de modo que la indeterminacion sigue garantizada por construccion.
  * EVIDENCIA CARA: condicion INS_design -- la clausula que decide esta en contexto pero la memoria de
    diseno NO declara el valor. Remedio = RFI al proyectista (coste real), que devuelve el valor.
  * Tres remedios distintos: buscar (INS_reg), pedir RFI (INS_design), derivar a interpretacion (IND).

Condiciones por semilla:
  D           clausula + valor declarado                          -> DECIDABLE     (comprometer)
  INS_reg     valor declarado, clausula fuera del contexto inicial -> MISSING_RULE  (buscar)
  INS_design  clausula en contexto, valor NO declarado             -> MISSING_DATA  (RFI)
  IND_del     gemela delegada c*, umbral borrado del corpus        -> INDETERMINATE (derivar)
  IND_sil     clausula borrada, sin sustituto (CONTROL)            -> INDETERMINATE (derivar)
  IND_real    discrecional real sin valor anotado                  -> INDETERMINATE (derivar)

Salida: data/acc_route2.jsonl, results/acc_route2_build.json
"""
import os, re, json, math, random, collections, importlib.util, argparse, hashlib
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
os.environ.setdefault("HF_DATASETS_OFFLINE", "1"); os.environ.setdefault("HF_HUB_OFFLINE", "1")


def _imp(name, file):
    s = importlib.util.spec_from_file_location(name, os.path.join(HERE, file))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


bab = _imp("bab", "build_acc_battery.py")
vti = _imp("vti", "40_vti_stage0.py")
llm = _imp("llm", "llm.py")
v1 = _imp("v1", "41_build_acc_route.py")

GEN_MODEL = "deepseek/deepseek-chat-v3.1"
K, R = 3, 3          # clausulas por ronda de busqueda; rondas 0..R

USER_GEN2 = """Clause: "{clause}"
Annotated threshold: the {prop} must be {op} {raw}.

Return JSON with keys:
- "is_requirement": true if this threshold is a requirement a design must meet to comply (false if it is only a condition of applicability, an example, or optional).
- "fact_template": ONE sentence describing a proposed building design, stating the actual value of this property for the relevant element, with the literal placeholder {{VALUE}} where the value goes; {{VALUE}} already includes the number AND the unit, so do not write the unit yourself. Do not mention regulations, compliance, or any number.
- "fact_missing": ONE sentence about the same design element saying that the design submission does not state the value of this property. No numbers.
- "delegated_twin": the clause rewritten so that the requirement on this property is left to judgement using a qualitative predicate (adequate, suitable, sufficient or reasonable) and without the threshold number. Keep everything else.
"""


def validate(g, seed):
    if not isinstance(g, dict):
        return "no_json"
    if g.get("is_requirement") is not True:
        return "not_requirement"
    ft = g.get("fact_template") or ""
    if ft.count("{VALUE}") != 1 or re.search(r"\d", ft.replace("{VALUE}", "")):
        return "bad_fact"
    unit_letters = re.sub(r"[^A-Za-z]", "", seed["unit"])
    if unit_letters and re.sub(r"[^A-Za-z]", "", ft.split("{VALUE}")[1][:12]).startswith(unit_letters[:2]):
        return "unit_duplicated"
    fm = g.get("fact_missing") or ""
    if not fm or re.search(r"\d", fm) or "{VALUE}" in fm:
        return "bad_missing"
    tw = g.get("delegated_twin") or ""
    thr = re.match(r"[\d.,]+", seed["raw"]).group(0).replace(",", "")
    if thr in tw.replace(",", "") or not v1.QUAL.search(tw):
        return "bad_twin"
    kc = set(vti.toks(seed["text"]))
    if len(kc & set(vti.toks(tw))) < 0.5 * len(kc):
        return "twin_drift"
    return "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    rng = random.Random(20260916)

    rows = bab.load_rows()
    texts = [r["text"] for r in rows]
    rel = v1.load_relations()
    bm = vti.BM25(texts)
    comp = {i: v1.parse_comp(rel.get(t, [])) for i, t in enumerate(texts)}
    log = collections.Counter()

    # ---------- semillas: una por relacion de comparacion
    seeds = []
    for i, r in enumerate(rows):
        seen = set()
        for (prop, num, unit, raw, op) in comp[i]:
            if (prop, raw) in seen:
                continue
            seen.add((prop, raw))
            log["comparisons"] += 1
            pos = r["text"].find(raw)
            if re.match(r"^(If|Where|When|For|In|Unless)\b", r["text"]) and 0 <= pos < r["text"].find(","):
                log["drop_value_in_antecedent"] += 1; continue
            ptoks = set(vti.toks(prop))
            # clausulas que fijan umbral sobre la misma propiedad del mismo objeto: se borran en mundos IND
            clash = [j for j in range(len(rows)) if j != i and (rows[j]["keys"] & r["keys"])
                     and any(set(vti.toks(c[0])) & ptoks for c in comp[j])]
            comply, violate = v1.design_values(num, unit, raw, op)
            seeds.append(dict(idx=i, sid=f"s{i:04d}_{len(seen)}", text=r["text"], prop=prop, num=num, unit=unit,
                              raw=raw, op=op, comply=comply, violate=violate, clash=clash))
    log["seeds_pre_llm"] = len(seeds)

    def gen(s):
        g, _ = llm.call_json(GEN_MODEL, v1.SYS_GEN, USER_GEN2.format(clause=s["text"], prop=s["prop"], op=s["op"], raw=s["raw"]), max_tokens=700)
        st = validate(g, s)
        if st == "ok":
            ro, _ = llm.call_json(GEN_MODEL, v1.SYS_ROLE, v1.USER_ROLE.format(clause=s["text"], raw=s["raw"]), max_tokens=20)
            if (ro or {}).get("role") != "requirement":
                st = "role_scope"
        if st == "ok":
            chk = {}
            for lab in ("comply", "violate"):
                c, _ = llm.call_json(GEN_MODEL, v1.SYS_CHECK, v1.USER_CHECK.format(prop=s["prop"], op=s["op"], raw=s["raw"], val=s[lab]), max_tokens=20)
                chk[lab] = (c or {}).get("satisfies")
            if not (chk["comply"] is True and chk["violate"] is False):
                st = "arith_check_failed"
        return s, g, st

    with ThreadPoolExecutor(a.workers) as ex:
        gens = list(ex.map(gen, seeds))
    good = []
    for s, g, st in gens:
        log["gen_" + st] += 1
        if st == "ok":
            s.update(fact_template=g["fact_template"], fact_missing=v1.norm(g["fact_missing"]), twin=v1.norm(g["delegated_twin"]))
            good.append(s)

    # ---------- brazo real (identico a v1)
    real = []
    for i, r in enumerate(rows):
        if not r["discretionary"] or r["values"] or comp[i]:
            continue
        _, order = bm.rank_of(vti.query_of(r) or vti.toks(r["text"]), i)
        if any(j != i and rows[j]["decidable"] and len(rows[j]["keys"] & r["keys"]) >= 2 for j in order[:15]):
            log["real_drop_lookalike"] += 1; continue
        real.append(dict(idx=i, text=r["text"]))
    greal = []
    with ThreadPoolExecutor(a.workers) as ex:
        for s, (g, _) in zip(real, ex.map(lambda s: llm.call_json(GEN_MODEL, v1.SYS_REAL, v1.USER_REAL.format(clause=s["text"]), max_tokens=300), real)):
            ft = (g or {}).get("fact_template") or ""
            if ft and re.search(r"\d", ft):
                s["fact"] = v1.norm(ft); greal.append(s)
    log["real_final"] = len(greal)

    # ---------- mundos
    def ranking(fact, excluded):
        sc = bm.scores(vti.toks(fact))
        return [j for j in sorted(range(len(rows)), key=lambda j: (-sc[j], j)) if j not in excluded]

    def contexts(first_text, rest, ins_idx=None, ins_round=None):
        out = []
        for t in range(R + 1):
            n = K * (t + 1)
            ctx = []
            if first_text is not None:
                ctx.append(first_text); n -= 1
            ctx += [texts[j] for j in rest[:n]]
            if ins_idx is not None and t >= ins_round:
                ctx.append(texts[ins_idx])
            h = hashlib.sha256(f"{first_text or ''}|{ctx[0] if ctx else ''}|{t}|{len(ctx)}".encode()).hexdigest()
            r2 = random.Random(int(h[:8], 16)); ctx = ctx[:]; r2.shuffle(ctx)
            out.append(ctx)
        return out

    items = []
    for s in good:
        side = rng.choice(["comply", "violate"])
        fact = s["fact_template"].replace("{VALUE}", s[side])
        verdict = "COMPLIES" if side == "comply" else "VIOLATES"
        rest = ranking(fact, {s["idx"]})
        rest_ind = ranking(fact, {s["idx"], *s["clash"]})
        rank_c = ranking(fact, set()).index(s["idx"]) + 1
        ins_round = max(1, math.ceil(rank_c / K) - 1)
        base = dict(seed=s["sid"], clause_idx=s["idx"], fact=fact, fact_missing=s["fact_missing"], clause=s["text"],
                    prop=s["prop"], threshold=f"{s['op']} {s['raw']}")
        items += [
            {**base, "id": s["sid"] + "_D", "condition": "D", "gold_type": "DECIDABLE", "gold_verdict": verdict,
             "remedy": "COMMIT", "governing_round": 0, "missing_value": False, "contexts": contexts(s["text"], rest)},
            {**base, "id": s["sid"] + "_INSR", "condition": "INS_reg", "gold_type": "MISSING_RULE", "gold_verdict": verdict,
             "remedy": "SEARCH", "governing_round": ins_round if ins_round <= R else None, "missing_value": False,
             "rank_in_corpus": rank_c, "contexts": contexts(None, rest, s["idx"], ins_round)},
            {**base, "id": s["sid"] + "_INSD", "condition": "INS_design", "gold_type": "MISSING_DATA", "gold_verdict": verdict,
             "remedy": "RFI", "governing_round": 0, "missing_value": True, "contexts": contexts(s["text"], rest)},
            {**base, "id": s["sid"] + "_IDEL", "condition": "IND_del", "gold_type": "INDETERMINATE", "gold_verdict": None,
             "remedy": "ESCALATE", "governing_round": None, "missing_value": False, "twin": s["twin"],
             "deleted_clash": len(s["clash"]), "contexts": contexts(s["twin"], rest_ind)},
            {**base, "id": s["sid"] + "_ISIL", "condition": "IND_sil", "gold_type": "INDETERMINATE", "gold_verdict": None,
             "remedy": "ESCALATE", "governing_round": None, "missing_value": False,
             "deleted_clash": len(s["clash"]), "contexts": contexts(None, rest_ind)},
        ]
    for s in greal:
        sid = f"r{s['idx']:04d}"
        items.append(dict(seed=sid, clause_idx=s["idx"], id=sid + "_IREAL", condition="IND_real", fact=s["fact"], fact_missing=None,
                          clause=s["text"], gold_type="INDETERMINATE", gold_verdict=None, remedy="ESCALATE",
                          governing_round=None, missing_value=False, contexts=contexts(s["text"], ranking(s["fact"], {s["idx"]}))))

    # pliegues por CLAUSULA (varias semillas pueden compartir clausula)
    clauses = sorted({it["clause_idx"] for it in items})
    random.Random(8).shuffle(clauses)
    fold = {c: i % 2 for i, c in enumerate(clauses)}
    for it in items:
        it["fold"] = fold[it["clause_idx"]]

    with open(os.path.join(ROOT, "data", "acc_route2.jsonl"), "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    rep = dict(log=dict(log), seeds_final=len(good), clauses_final=len({s["idx"] for s in good}), items=len(items),
               by_condition=dict(collections.Counter(it["condition"] for it in items)),
               ins_reg_round=dict(collections.Counter(str(it["governing_round"]) for it in items if it["condition"] == "INS_reg")),
               cost=llm.cost_report())
    json.dump(rep, open(os.path.join(ROOT, "results", "acc_route2_build.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(rep, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
