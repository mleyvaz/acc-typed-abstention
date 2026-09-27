# -*- coding: utf-8 -*-
"""
41_build_acc_route.py -- bateria ACC-Route SIN ANOTADORES (PLAN_EXPERIMENTO_RUTEO.md §4).

El tipo de oro se FABRICA editando el corpus: por semilla (clausula con umbral anotado por los
expertos de CODE-ACCORD-Relations) se construyen mundos que solo difieren en que hay en el corpus.

  D          c en el contexto inicial                          -> DECIDABLE (veredicto de oro)
  D_words    c con el umbral escrito en letras                 -> DECIDABLE   (estrato anti-atajo)
  INS        c en el corpus, fuera del contexto inicial        -> INSUFFICIENT
  IND_del    c sustituida por gemela delegada c*               -> INDETERMINATE
  IND_delnum c* conservando un numero ajeno al umbral          -> INDETERMINATE (estrato anti-atajo)
  IND_sil    c borrada, sin sustituto (CONTROL NEGATIVO)       -> INDETERMINATE
  IND_real   clausula discrecional real sin valor anotado      -> INDETERMINATE (validez externa)

Generacion (hecho de diseno, gemelas) con deepseek/deepseek-chat-v3.1 -- familia distinta de los
agentes -- y validacion automatica de cada salida. Sin personas en el bucle.

Salida: data/acc_route.jsonl, results/acc_route_build.json
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

GEN_MODEL = "deepseek/deepseek-chat-v3.1"
K, R = 3, 4                      # clausulas por ronda; rondas de busqueda 1..R
COMP = {"greater-equal": ">=", "greater": ">", "less-equal": "<=", "less": "<"}
QUAL = re.compile(r"\b(adequate|suitable|sufficient|reasonable|appropriate|satisfactory)\b", re.I)
NUMV = re.compile(r"^\s*(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*([A-Za-z°%][^<>]*)$")
TAG = re.compile(r"<e1>(.*?)</e1>|<e2>(.*?)</e2>")


def norm(t):
    return " ".join(t.split())


def load_relations():
    from datasets import load_dataset
    rel = load_dataset("ACCORD-NLP/CODE-ACCORD-Relations")
    by = collections.defaultdict(list)
    for s in rel:
        for r in rel[s]:
            by[norm(r["content"])].append(r)
    return by


def parse_comp(rs):
    """Relaciones de comparacion con valor numerico + unidad. Devuelve lista (prop, num, unit, raw, op)."""
    out = []
    for r in rs:
        if r["relation_type"] not in COMP:
            continue
        e1 = re.search(r"<e1>(.*?)</e1>", r["tagged_sentence"]); e2 = re.search(r"<e2>(.*?)</e2>", r["tagged_sentence"])
        if not (e1 and e2):
            continue
        a, b = e1.group(1), e2.group(1)
        for prop, val in ((a, b), (b, a)):
            m = NUMV.match(val)
            if m:
                out.append((prop, float(m.group(1).replace(",", "")), m.group(2).strip(), val, COMP[r["relation_type"]]))
                break
    return out


def fmt(x, like):
    if "." not in like.replace(",", "") and abs(x - round(x)) < 1e-9:
        return f"{int(round(x)):,}" if "," in like else str(int(round(x)))
    if "." not in like.replace(",", ""):
        return str(int(round(x)))
    return f"{x:.2f}".rstrip("0").rstrip(".")


def design_values(num, unit, raw, op):
    numtxt = raw.split()[0] if raw.split() else raw
    numtxt = re.match(r"[\d.,]+", raw).group(0)
    up, down = num * 1.25, num * 0.75
    if op in (">=", ">"):
        comply, violate = up, down
    else:
        comply, violate = down, up
    sep = "" if raw[len(numtxt):len(numtxt) + 1] != " " else " "
    return fmt(comply, numtxt) + sep + unit, fmt(violate, numtxt) + sep + unit


SYS_GEN = ("You transform building-regulation clauses for a controlled experiment. "
           "Return ONLY a JSON object with the requested keys. Keep the regulatory register.")

USER_GEN = """Clause: "{clause}"
Annotated threshold: the {prop} must be {op} {raw}.

Return JSON with keys:
- "is_requirement": true if this threshold is a requirement a design must meet to comply (false if it is only a condition of applicability, an example, or optional).
- "fact_template": ONE sentence describing a proposed building design, stating the actual value of this property for the relevant element, with the literal placeholder {{VALUE}} where the value goes; {{VALUE}} already includes the number AND the unit, so do not write the unit yourself. Do not mention regulations, compliance, or any number.
- "delegated_twin": the clause rewritten so that the requirement on this property is left to judgement using a qualitative predicate (adequate, suitable, sufficient or reasonable) and NO number at all. Keep everything else.
- "clause_words": the original clause with the threshold number written out in words (e.g. "four hundred millimetres"). Nothing else changes.
"""

SYS_REAL = SYS_GEN
USER_REAL = """Clause: "{clause}"

This clause leaves a requirement to judgement (no measurable threshold). Return JSON with keys:
- "property": the property the clause governs, in a few words.
- "fact_template": ONE sentence describing a proposed building design, stating a plausible concrete value (with unit) for that property for the relevant element. Do not mention regulations or compliance.
"""

SYS_ROLE = "You analyse building-regulation clauses. Return ONLY JSON."
USER_ROLE = """Clause: "{clause}"
Numeric value in the clause: {raw}.
Is this value (a) a REQUIREMENT that a design must meet in order to comply, or (b) a SCOPE CONDITION that only says when or to what the clause applies?
Return {{"role": "requirement"}} or {{"role": "scope"}}."""

SYS_CHECK = "You check compliance arithmetic. Return ONLY JSON."
USER_CHECK = """Requirement: the {prop} must be {op} {raw}.
Design value: {val}.
Does the design value satisfy the requirement? Return {{"satisfies": true}} or {{"satisfies": false}}."""


def validate_gen(g, seed):
    if not isinstance(g, dict):
        return "no_json"
    if g.get("is_requirement") is not True:
        return "not_requirement"
    ft = g.get("fact_template") or ""
    if ft.count("{VALUE}") != 1 or re.search(r"\d", ft.replace("{VALUE}", "")):
        return "bad_fact"
    unit_letters = re.sub(r"[^A-Za-z]", "", seed["unit"])
    after = ft.split("{VALUE}")[1][:12]
    if unit_letters and re.sub(r"[^A-Za-z]", "", after).startswith(unit_letters[:2]):
        return "unit_duplicated"
    tw = g.get("delegated_twin") or ""
    thr = re.match(r"[\d.,]+", seed["raw"]).group(0).replace(",", "")
    if thr in tw.replace(",", "") or not QUAL.search(tw):
        return "bad_twin"
    keys_c = set(vti.toks(seed["text"])); keys_t = set(vti.toks(tw))
    if len(keys_c & keys_t) < 0.5 * len(keys_c):
        return "twin_drift"
    cw = g.get("clause_words") or ""
    if thr in cw.replace(",", "") or len(set(vti.toks(cw)) & keys_c) < 0.5 * len(keys_c):
        return "bad_words"
    return "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max_seeds", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    rng = random.Random(20260915)

    rows = bab.load_rows()
    texts = [r["text"] for r in rows]
    rel = load_relations()
    bm = vti.BM25(texts)
    comp_by_idx = {i: parse_comp(rel.get(t, [])) for i, t in enumerate(texts)}
    log = collections.Counter()

    # ---------- semillas
    seeds = []
    for i, r in enumerate(rows):
        cs = comp_by_idx[i]
        if not cs:
            continue
        log["with_numeric_comparison"] += 1
        if len(cs) != 1:
            log["multiple_comparisons_first_used"] += 1
        prop, num, unit, raw, op = cs[0]
        pos = r["text"].find(raw)
        if re.match(r"^(If|Where|When|For|In|Unless)\b", r["text"]) and 0 <= pos < r["text"].find(",") :
            log["drop_value_in_antecedent"] += 1; continue
        q = vti.query_of(r) + vti.toks(prop)
        _, order = bm.rank_of(q, i)
        ptoks = set(vti.toks(prop))
        clash = any(j != i and (rows[j]["keys"] & r["keys"]) and any(set(vti.toks(c[0])) & ptoks for c in comp_by_idx[j])
                    for j in order[:15])
        if clash:
            log["drop_same_property_elsewhere"] += 1; continue
        comply, violate = design_values(num, unit, raw, op)
        seeds.append(dict(idx=i, text=r["text"], doc=r["doc"], prop=prop, num=num, unit=unit, raw=raw, op=op,
                          comply=comply, violate=violate))
    log["seeds_pre_llm"] = len(seeds)
    if a.max_seeds:
        seeds = seeds[: a.max_seeds]

    # ---------- generacion y verificacion aritmetica (familia distinta de los agentes)
    def gen(s):
        g, _ = llm.call_json(GEN_MODEL, SYS_GEN, USER_GEN.format(clause=s["text"], prop=s["prop"], op=s["op"], raw=s["raw"]), max_tokens=700)
        st = validate_gen(g, s)
        chk = {}
        if st == "ok":
            ro, _ = llm.call_json(GEN_MODEL, SYS_ROLE, USER_ROLE.format(clause=s["text"], raw=s["raw"]), max_tokens=20)
            if (ro or {}).get("role") != "requirement":
                st = "role_scope"
        if st == "ok":
            for lab in ("comply", "violate"):
                c, _ = llm.call_json(GEN_MODEL, SYS_CHECK, USER_CHECK.format(prop=s["prop"], op=s["op"], raw=s["raw"], val=s[lab]), max_tokens=20)
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
            s.update(fact_template=g["fact_template"], twin=norm(g["delegated_twin"]),
                     twin_num=norm(g["delegated_twin"]).rstrip(". ") + f", as described in paragraph {2 + s['idx'] % 7}.{10 + s['idx'] % 37}.", words=norm(g["clause_words"]))
            good.append(s)

    # ---------- brazo real: discrecionales sin valor anotado ni comparacion, sin decidible parecida
    real = []
    for i, r in enumerate(rows):
        if not r["discretionary"] or r["values"] or comp_by_idx[i]:
            continue
        _, order = bm.rank_of(vti.query_of(r) or vti.toks(r["text"]), i)
        if any(j != i and rows[j]["decidable"] and len(rows[j]["keys"] & r["keys"]) >= 2 for j in order[:15]):
            log["real_drop_lookalike"] += 1; continue
        real.append(dict(idx=i, text=r["text"], doc=r["doc"]))
    if a.max_seeds:
        real = real[: max(2, a.max_seeds // 3)]

    def gen_real(s):
        g, _ = llm.call_json(GEN_MODEL, SYS_REAL, USER_REAL.format(clause=s["text"]), max_tokens=300)
        ft = (g or {}).get("fact_template") or ""
        ok = bool(ft) and bool(re.search(r"\d", ft))
        return s, ft, ok

    with ThreadPoolExecutor(a.workers) as ex:
        greal = list(ex.map(gen_real, real))
    real_ok = []
    for s, ft, ok in greal:
        log["real_gen_ok" if ok else "real_gen_bad"] += 1
        if ok:
            s["fact"] = norm(ft); real_ok.append(s)

    # ---------- mundos y trayectorias de contexto
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
            r2 = random.Random(int(h[:8], 16))
            ctx = ctx[:]; r2.shuffle(ctx)
            out.append(ctx)
        return out

    items = []
    seed_ids = sorted({s["idx"] for s in good})
    for s in good:
        sid = f"s{s['idx']:04d}"
        side = rng.choice(["comply", "violate"])
        fact = s["fact_template"].replace("{VALUE}", s[side])
        verdict = "COMPLIES" if side == "comply" else "VIOLATES"
        rest = ranking(fact, {s["idx"]})
        full = ranking(fact, set())
        rank_c = full.index(s["idx"]) + 1
        ins_round = max(1, math.ceil(rank_c / K) - 1)
        base = dict(seed=sid, fact=fact, clause=s["text"], prop=s["prop"], threshold=f"{s['op']} {s['raw']}")
        items.append({**base, "id": sid + "_D", "condition": "D", "gold_type": "DECIDABLE", "gold_verdict": verdict,
                      "governing_round": 0, "contexts": contexts(s["text"], rest)})
        items.append({**base, "id": sid + "_Dw", "condition": "D_words", "gold_type": "DECIDABLE", "gold_verdict": verdict,
                      "governing_round": 0, "contexts": contexts(s["words"], rest)})
        items.append({**base, "id": sid + "_INS", "condition": "INS", "gold_type": "INSUFFICIENT", "gold_verdict": verdict,
                      "governing_round": ins_round if ins_round <= R else None, "rank_in_corpus": rank_c,
                      "contexts": contexts(None, rest, s["idx"], ins_round)})
        items.append({**base, "id": sid + "_IDEL", "condition": "IND_del", "gold_type": "INDETERMINATE", "gold_verdict": None,
                      "governing_round": None, "twin": s["twin"], "contexts": contexts(s["twin"], rest)})
        items.append({**base, "id": sid + "_IDN", "condition": "IND_delnum", "gold_type": "INDETERMINATE", "gold_verdict": None,
                      "governing_round": None, "twin": s["twin_num"], "contexts": contexts(s["twin_num"], rest)})
        items.append({**base, "id": sid + "_ISIL", "condition": "IND_sil", "gold_type": "INDETERMINATE", "gold_verdict": None,
                      "governing_round": None, "contexts": contexts(None, rest)})
    for s in real_ok:
        sid = f"r{s['idx']:04d}"
        rest = ranking(s["fact"], {s["idx"]})
        items.append(dict(seed=sid, id=sid + "_IREAL", condition="IND_real", fact=s["fact"], clause=s["text"],
                          gold_type="INDETERMINATE", gold_verdict=None, governing_round=None,
                          contexts=contexts(s["text"], rest)))

    # particion en dos pliegues por semilla (ajuste cruzado)
    allseeds = sorted({it["seed"] for it in items})
    random.Random(7).shuffle(allseeds)
    fold = {sd: i % 2 for i, sd in enumerate(allseeds)}
    for it in items:
        it["fold"] = fold[it["seed"]]

    out = os.path.join(ROOT, "data", "acc_route.jsonl" if not a.max_seeds else "acc_route_pilot.jsonl")
    with open(out, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    rep = dict(log=dict(log), seeds_final=len(good), real_final=len(real_ok), items=len(items),
               by_condition=dict(collections.Counter(it["condition"] for it in items)),
               ins_governing_round=dict(collections.Counter(str(it["governing_round"]) for it in items if it["condition"] == "INS")),
               cost=llm.cost_report())
    json.dump(rep, open(os.path.join(ROOT, "results", "acc_route_build" + ("_pilot" if a.max_seeds else "") + ".json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(rep, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
