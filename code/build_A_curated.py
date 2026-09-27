# -*- coding: utf-8 -*-
"""
build_A_curated.py -- reconstruye la condicion A con emparejamiento TEMATICO explicito.

MOTIVO (auditoria del 6-sep-2026, results/A_audit_muestra.txt):
la version automatica por solapamiento lexico de objetos dio ~20-27% de items
genuinamente indeterminados sobre una muestra de 30; el resto era INSUFICIENCIA
disfrazada (compartian un sustantivo y nada mas). El emparejamiento por
`property` anotada tampoco sirve: de las 94 clausulas discrecionales solo 24
llevan esa anotacion.

DISENO NUEVO. Una clausula discrecional solo se empareja con una afirmacion si
ambas pertenecen al MISMO TEMA REGULATORIO, definido por listas de terminos
explicitas y auditables (no por solapamiento de tokens). La afirmacion procede
de una clausula DECIDIBLE del mismo tema: la norma fija un umbral en un sitio y
delega el juicio en otro, sobre la misma materia. Eso es indeterminacion de la
extension del predicado (textura abierta), no falta de evidencia.

Se exige ademas que la clausula discrecional contenga el predicado cualitativo
o el marcador de discrecion DENTRO del tema, no en una subordinada suelta.

Salida: data/battery_acc_v2.jsonl (S/R/N/N_hard heredados + A_cur) y
        results/A_curated_audit.txt (las parejas completas, para auditar).
"""
import os, re, json, random, collections, argparse
import build_acc_battery as B

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")

# --- taxonomia tematica explicita (auditable; cada tema son terminos, no tokens sueltos)
TOPICS = {
    "ventilation":  r"ventilat|air flow|airflow|extract fan|duct|indoor air|outdoor air|infiltration|purge",
    "access_circ":  r"\blift\b|lifting platform|stair|landing|corridor|door|ramp|handrail|wheelchair|access route|circulation|threshold",
    "sanitary":     r"toilet|washbasin|washroom|sanitary|urinal|shower|bathroom|drain|sewer|water supply|household water|hot water|cold water",
    "energy_therm": r"u-value|thermal|insulat|heat loss|energy (efficiency|performance|rating)|primary energy|boiler|heating (system|circuit|appliance)|heat pump|district heat",
    "electrical_ev": r"electric vehicle|charge point|cable route|electrical installation|onsite electricity|photovoltaic|meter reading|submeter",
    "fire_escape":  r"\bfire\b|escape|evacuat|exit route|smoke|combustib|means of escape",
    "structure":    r"structural|load|parapet|barrier|balustrade|crawl space|foundation|beam|column|stability",
    "acoustics":    r"acoustic|sound|noise|reverberation|decibel|\bdB\b",
    "safety_fall":  r"falling|fall from|collision|slip|guarding|level difference|precipice|impact",
    "security":     r"security|unauthorised access|resist .{0,20}entry|burglar",
}
TOPIC_RE = {k: re.compile(v, re.I) for k, v in TOPICS.items()}


def topics_of(text):
    return {k for k, rx in TOPIC_RE.items() if rx.search(text)}


def norm_key(t):
    return re.sub(r"[^a-z0-9]", "", t.lower())[:110]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    rng = random.Random(a.seed)

    rows = B.load_rows()
    for r in rows:
        r["topics"] = topics_of(r["text"])
    dec = [r for r in rows if r["decidable"] and r["topics"]]
    dis = [r for r in rows if r["discretionary"] and r["topics"]]
    print(f"decidibles con tema: {len(dec)}   discrecionales con tema: {len(dis)}")
    print("\nclausulas discrecionales por tema:")
    cnt = collections.Counter(t for r in dis for t in r["topics"])
    for t, n in cnt.most_common():
        print(f"   {t:16s} {n:3d}   (decidibles del mismo tema: "
              f"{sum(1 for r in dec if t in r['topics'])})")

    items, audit = [], []
    n = 0
    for src in dec:
        claim = B.normalise_claim(src["text"])
        if len(claim) < 40 or len(claim) > 400:
            continue
        # documentos: discrecionales que comparten TEMA, deduplicados
        cand, seen = [], {norm_key(src["text"])}
        for d in dis:
            if d["topics"] & src["topics"] and norm_key(d["text"]) not in seen:
                seen.add(norm_key(d["text"]))
                cand.append(d)
        if len(cand) < 2:
            continue
        # preferir los que comparten MAS temas con la afirmacion
        cand.sort(key=lambda d: -len(d["topics"] & src["topics"]))
        docs = cand[:a.k]
        n += 1
        split = "dev" if rng.random() < 0.25 else "test"
        items.append({"id": f"A_cur{n:04d}", "split": split, "claim": claim,
                      "condition": "A_cur", "gold": "ABSTAIN_INDETERMINATE",
                      "docs": [B.D(d["text"], "UNDETERMINED", subtype="discretionary")
                               for d in docs],
                      "pair_id": None})
        audit.append((f"A_cur{n:04d}", sorted(src["topics"]), claim,
                      [(sorted(d["topics"]), d["text"]) for d in docs]))

    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    with open(os.path.join(ROOT, "results", "A_curated_audit.txt"), "w", encoding="utf-8") as fh:
        fh.write(f"CONDICION A CURADA — {len(items)} items, emparejamiento por tema explicito\n\n")
        for i, tp, cl, ds in audit:
            fh.write("=" * 100 + f"\n[{i}] temas de la afirmacion: {tp}\nCLAIM: {cl}\n")
            for dt, dx in ds:
                fh.write(f"  DOC {dt}: {dx}\n")

    # batería v2: S/R/N/N_hard originales + A_cur (se descarta la A automatica)
    old = [json.loads(l) for l in open(os.path.join(ROOT, "data", "battery_acc.jsonl"),
                                       encoding="utf-8") if '"condition": "A"' not in l]
    allit = old + items
    out = os.path.join(ROOT, "data", "battery_acc_v2.jsonl")
    with open(out, "w", encoding="utf-8") as fh:
        for it in allit:
            fh.write(json.dumps(it, ensure_ascii=False) + "\n")

    print(f"\nA_cur: {len(items)} items")
    c = collections.Counter(i["condition"] for i in allit)
    print(f"bateria v2: {len(allit)} items -> {out}")
    for k in ["S", "R", "A_cur", "N", "N_hard"]:
        print(f"   {k:7s} {c[k]}")
    print("\nAuditoria completa en results/A_curated_audit.txt")


if __name__ == "__main__":
    main()
