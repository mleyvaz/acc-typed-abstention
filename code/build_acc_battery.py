# -*- coding: utf-8 -*-
"""
build_acc_battery.py -- bateria controlada de verificacion de cumplimiento normativo
sobre CODE-ACCORD (Hettiarachchi et al., Scientific Data 2025; 862 clausulas
auto-contenidas de la reglamentacion de edificacion de Inglaterra y Finlandia).

Emite el MISMO esquema que battery.py del paper 2, para poder reutilizar
run_experiment.py / coordinates.py / policy.py / evaluate.py sin tocarlos:
  {"id","split","claim","condition","gold","docs":[{"text","label","weak","subtype"}],"pair_id"}

CONDICIONES (4 conductas; NO hay CONFLICT_AWARE, ver DECISIONES abajo)
  S       la clausula decidible que fija el requisito            -> ANSWER
  R       la misma clausula frente a la afirmacion NEGADA        -> REFUTE
  A       clausulas DISCRECIONALES sobre el mismo objeto: la
          norma habla del asunto y se niega a cuantificarlo      -> ABSTAIN_INDETERMINATE
  N       clausulas de OTRO documento (otro tema)                -> ABSTAIN_INSUFFICIENT
  N_hard  clausulas del MISMO documento, otro objeto             -> ABSTAIN_INSUFFICIENT

DECISIONES DE DISENO (para el preregistro y DEVIATIONS)
 1. NO se construye la condicion de conflicto. Medido el 6-sep-2026: los pares
    UK-Finlandia comparten sustantivos genericos pero regulan PROPIEDADES
    DISTINTAS (galibo vs anchura), no requisitos contradictorios; solo 15 pares
    tienen valor numerico en ambos lados y ninguno es una contradiccion. Los
    pares de version V1-V2 dan 7 casi-coincidencias y son cambios EDITORIALES
    ("home"->"building", anadir "NOTE:"). Un conflicto fabricado seria un
    artefacto. Ademas la validacion externa del paper 2 en ConfRAG ya mostro
    que la ventaja de la tripleta esta en insuficiencia e indeterminacion, no
    en conflicto (IND ~ TF en conflicto puro).
 2. La AFIRMACION se construye igual en TODAS las condiciones (misma plantilla
    de normalizacion). Asi la forma de la afirmacion no queda confundida con la
    condicion: lo unico que varia entre condiciones son los DOCUMENTOS. Esto
    responde a la critica de "estimulos de plantilla" del paper 2, donde A_tpl
    quedo fuera de los resultados primarios.
 3. Los documentos son SIEMPRE texto normativo real, nunca generado.
"""
import os, re, json, random, argparse, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")

BEHAV = ["ANSWER", "REFUTE", "CONFLICT_AWARE", "ABSTAIN_INSUFFICIENT", "ABSTAIN_INDETERMINATE"]
GOLD = {"S": "ANSWER", "R": "REFUTE", "A": "ABSTAIN_INDETERMINATE",
        "N": "ABSTAIN_INSUFFICIENT", "N_hard": "ABSTAIN_INSUFFICIENT"}

# --- discrecionalidad: la norma delega el juicio o no fija umbral verificable
DISCRETION = re.compile("|".join([
    r"where\s+(appropriate|necessary|practicable|possible|required)",
    r"if\s+(appropriate|practicable|necessary|possible)",
    r"as far as is reasonably practicable", r"so far as is reasonably practicable",
    r"where this is not (possible|practicable)", r"should be considered",
    r"may be (necessary|appropriate|required)", r"at the discretion",
]), re.I)
QUALITATIVE = re.compile(
    r"\b(adequate|suitable|reasonable|appropriate|sufficient|satisfactory|acceptable)\b", re.I)
HAS_NUM = re.compile(r"\d")

STOP = {"the", "a", "an", "of", "and", "or", "in", "to", "be", "is", "are", "that", "this",
        "it", "for", "with", "should", "shall", "must", "may", "not", "any", "all", "as",
        "at", "by", "on", "from", "where", "when", "which", "building", "buildings"}


def _mid(m):
    mm = re.search(r"'ID':\s*'([^']+)'", str(m))
    return mm.group(1) if mm else str(m)


def _spans(toks, labs, kind):
    out, cur = [], []
    for t, l in zip(toks, labs):
        if l == f"B-{kind}":
            if cur: out.append(" ".join(cur))
            cur = [t]
        elif l == f"I-{kind}" and cur:
            cur.append(t)
        else:
            if cur: out.append(" ".join(cur)); cur = []
    if cur: out.append(" ".join(cur))
    return out


def _keys(strs):
    ks = set()
    for s in strs:
        for w in s.split():
            w = w.lower().strip(".,;:()[]")
            if len(w) > 3 and w not in STOP:
                ks.add(w)
    return ks


def normalise_claim(text):
    """Normalizacion deterministica clausula -> proposicion de cumplimiento.
    Identica en todas las condiciones (decision 2)."""
    t = " ".join(text.split())
    t = re.sub(r"^(NOTE:|Note:)\s*", "", t)
    t = re.sub(r"^(In|Where|If|When|For|Under)\b[^,]{0,80},\s*", "", t)  # quitar preambulo
    t = re.sub(r"\bshould\b", "must", t)
    t = re.sub(r"\bshall\b", "must", t)
    t = t.rstrip(". ").strip()
    if t and t[0].islower():
        t = t[0].upper() + t[1:]
    return t + "."


def negate_claim(claim):
    return "It is not the case that " + claim[0].lower() + claim[1:]


def D(text, label, weak=False, subtype=None):
    return {"text": text, "label": label, "weak": weak, "subtype": subtype}


def load_rows():
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    from datasets import load_dataset
    ds = load_dataset("ACCORD-NLP/CODE-ACCORD-Entities")
    rows = []
    for sp in ds:
        for r in ds[sp]:
            doc = re.sub(r"^\d+_", "", _mid(r["metadata"]))
            toks = r["processed_content"].split()
            labs = r["label"].split()
            objs = _spans(toks, labs, "object")
            vals = _spans(toks, labs, "value")
            text = " ".join(r["content"].split())
            discretionary = bool(DISCRETION.search(text)) or (
                bool(QUALITATIVE.search(text)) and not HAS_NUM.search(text))
            rows.append(dict(text=text, doc=doc,
                             juris="UK" if doc.startswith("UK") else "FI",
                             objects=objs, values=vals,
                             keys=_keys(objs) or _keys([text]),
                             decidable=bool(HAS_NUM.search(text)) and not discretionary,
                             discretionary=discretionary))
    return rows


def build(rows, k=3, per_cond=250, seed=0):
    rng = random.Random(seed)
    items, counts = [], collections.Counter()
    decidable = [r for r in rows if r["decidable"] and r["keys"]]
    discret = [r for r in rows if r["discretionary"] and r["keys"]]
    by_doc = collections.defaultdict(list)
    for r in rows:
        by_doc[r["doc"]].append(r)
    docs = sorted(by_doc)

    def add(cond, claim, ds_, split):
        if counts[cond] >= per_cond: return
        counts[cond] += 1
        items.append({"id": f"{cond}{counts[cond]:04d}", "split": split, "claim": claim,
                      "condition": cond, "gold": GOLD[cond], "docs": ds_, "pair_id": None})

    rng.shuffle(decidable)
    for src in decidable:
        split = "dev" if rng.random() < 0.25 else "test"
        claim = normalise_claim(src["text"])
        if len(claim) < 40 or len(claim) > 400:
            continue

        # --- S: la clausula que fija el requisito, mas relleno del mismo documento
        same_doc = [r for r in by_doc[src["doc"]] if r["text"] != src["text"]]
        pad = rng.sample(same_doc, min(k - 1, len(same_doc))) if same_doc else []
        add("S", claim, [D(src["text"], "SUPPORTS")] + [D(p["text"], "IRRELEVANT") for p in pad], split)

        # --- R: misma evidencia, afirmacion negada
        add("R", negate_claim(claim),
            [D(src["text"], "REFUTES")] + [D(p["text"], "IRRELEVANT") for p in pad], split)

        # --- A: clausulas discrecionales sobre el MISMO objeto (la norma habla y no cuantifica)
        cand = [d for d in discret if len(d["keys"] & src["keys"]) >= 1 and d["text"] != src["text"]]
        cand.sort(key=lambda d: -len(d["keys"] & src["keys"]))
        if len(cand) >= 2:
            add("A", claim, [D(d["text"], "UNDETERMINED", subtype="discretionary")
                             for d in cand[:k]], split)

        # --- N: clausulas de OTRO documento
        other = [d for d in docs if d != src["doc"]]
        pool = []
        while len(pool) < k and other:
            dd = rng.choice(other)
            c = rng.choice(by_doc[dd])
            if not (c["keys"] & src["keys"]):
                pool.append(c)
        if len(pool) == k:
            add("N", claim, [D(p["text"], "IRRELEVANT") for p in pool], split)

        # --- N_hard: MISMO documento, objeto distinto (negativos duros)
        hard = [r for r in same_doc if not (r["keys"] & src["keys"])]
        if len(hard) >= k:
            add("N_hard", claim, [D(h["text"], "IRRELEVANT", subtype="hard_negative")
                                  for h in rng.sample(hard, k)], split)
    return items, counts


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--per_cond", type=int, default=250)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=os.path.join(ROOT, "data", "battery_acc.jsonl"))
    a = ap.parse_args()

    rows = load_rows()
    print(f"clausulas: {len(rows)}  decidibles: {sum(r['decidable'] for r in rows)}  "
          f"discrecionales: {sum(r['discretionary'] for r in rows)}")
    items, counts = build(rows, k=a.k, per_cond=a.per_cond, seed=a.seed)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        for it in items:
            fh.write(json.dumps(it, ensure_ascii=False) + "\n")
    print(f"\nitems: {len(items)} -> {a.out}")
    for c in ["S", "R", "A", "N", "N_hard"]:
        n = counts[c]
        dev = sum(1 for i in items if i["condition"] == c and i["split"] == "dev")
        print(f"  {c:7s} {n:4d}   (dev {dev}, test {n-dev})   gold={GOLD[c]}")
