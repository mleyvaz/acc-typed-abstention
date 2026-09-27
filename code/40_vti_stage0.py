# -*- coding: utf-8 -*-
"""
40_vti_stage0.py -- ETAPA 0 del experimento de enrutamiento (sin LLM, coste 0 USD).

Pregunta: con percepcion PERFECTA, cuanto vale conocer el TIPO de una abstencion
(insuficiente vs indeterminada) frente a un agente escalar que solo sabe "no estoy seguro"?
Es el techo (Value of Type Information, VTI). Si el techo es pequeno, ningun clasificador
de tipos real puede rescatar la linea y no hace falta gastar en LLM.

Entorno real: las 862 clausulas de CODE-ACCORD, recuperacion BM25 con la consulta que haria
un verificador (los OBJETOS anotados de la clausula, no su texto literal), k clausulas por ronda.

  insuficiente  = la clausula que decide existe en el corpus pero no esta en el contexto
                  inicial; rondas necesarias = ceil(rango/k) - 1  (medido, no supuesto)
  indeterminada = la clausula que gobierna es discrecional; ninguna ronda la resuelve

Politicas (costes: c_r por ronda de recuperacion, c_h por derivacion a humano):
  ESCALAR(B)  no distingue tipos: recupera hasta B rondas y luego deriva. Optimiza B.
              (Con la unica observacion "aun no encontrado", un umbral fijo es la politica
              optima: la posterior de "insuficiente" solo baja con cada ronda fallida.)
  TIPADA(B')  insuficiente -> recupera hasta B' rondas y luego deriva; indeterminada -> deriva ya.
  TIPADA con errores e1 = P(pred indet | insuf), e2 = P(pred insuf | indet).

Salida: results/vti_stage0.json y results/vti_stage0.md
"""
import os, re, json, math, collections, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")

spec = importlib.util.spec_from_file_location("bab", os.path.join(HERE, "build_acc_battery.py"))
bab = importlib.util.module_from_spec(spec); spec.loader.exec_module(bab)

TOK = re.compile(r"[a-z0-9]+")
K = 3            # clausulas por ronda (igual que la bateria)
B_MAX = 30       # rondas maximas consideradas
RHOS = [1, 2, 3, 5, 10, 20, 30, 50]          # c_h / c_r
PIS = [0.10, 0.20, 0.285, 0.40, 0.50]        # P(indeterminada | incierta); 0.285 = 94/(236+94)


def toks(s):
    return [w for w in TOK.findall(s.lower()) if w not in bab.STOP and len(w) > 2]


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.docs = [toks(d) for d in docs]
        self.N = len(self.docs)
        self.avg = sum(map(len, self.docs)) / self.N
        self.df = collections.Counter(w for d in self.docs for w in set(d))
        self.tf = [collections.Counter(d) for d in self.docs]
        self.k1, self.b = k1, b

    def scores(self, q):
        out = []
        for i, tf in enumerate(self.tf):
            L, s = len(self.docs[i]), 0.0
            for w in set(q):
                if w in tf:
                    idf = math.log(1 + (self.N - self.df[w] + 0.5) / (self.df[w] + 0.5))
                    s += idf * tf[w] * (self.k1 + 1) / (tf[w] + self.k1 * (1 - self.b + self.b * L / self.avg))
            out.append(s)
        return out

    def rank_of(self, q, target):
        sc = self.scores(q)
        order = sorted(range(self.N), key=lambda i: (-sc[i], i))
        return order.index(target) + 1, order


def query_of(r):
    return toks(" ".join(r["objects"])) if r["objects"] else toks(" ".join(sorted(r["keys"])))


def scalar_cost(rounds_ins, pi, rho, B):
    """Coste esperado por item incierto, en unidades de c_r."""
    n = len(rounds_ins)
    ins = sum((t if t <= B else B + rho) for t in rounds_ins) / n
    ind = B + rho
    return (1 - pi) * ins + pi * ind


def typed_cost(rounds_ins, pi, rho, B, e1=0.0, e2=0.0):
    n = len(rounds_ins)
    ins_ok = sum((t if t <= B else B + rho) for t in rounds_ins) / n
    ins = (1 - e1) * ins_ok + e1 * rho          # insuficiente tomada por indeterminada: deriva ya
    ind = (1 - e2) * rho + e2 * (B + rho)       # indeterminada tomada por insuficiente: gasta B rondas
    return (1 - pi) * ins + pi * ind


def best(f, *a):
    vals = [(f(*a, B), B) for B in range(B_MAX + 1)]
    return min(vals)


def main():
    rows = bab.load_rows()
    texts = [r["text"] for r in rows]
    bm = BM25(texts)

    # --- 1. dinamica de recuperacion sobre clausulas decidibles (insuficiencia real)
    ranks = []
    for i, r in enumerate(rows):
        if r["decidable"]:
            q = query_of(r)
            if q:
                ranks.append(bm.rank_of(q, i)[0])
    at0 = sum(rk <= K for rk in ranks)
    rounds_ins = [math.ceil(rk / K) - 1 for rk in ranks if rk > K]
    dist = collections.Counter(min(t, B_MAX + 1) for t in rounds_ins)

    # --- 2. contaminacion de A_cur: su afirmacion ES una clausula decidible del corpus
    bat = [json.loads(l) for l in open(os.path.join(ROOT, "data", "battery_acc_v2.jsonl"), encoding="utf-8")]
    text_idx = {bab.normalise_claim(t): i for i, t in enumerate(texts)}
    A = [x for x in bat if x["condition"] == "A_cur"]
    A_src = [text_idx.get(x["claim"]) for x in A]
    A_found = [s for s in A_src if s is not None]
    A_rank_claim = [bm.rank_of(toks(x["claim"]), s)[0] for x, s in zip(A, A_src) if s is not None]
    A_rank_obj = [bm.rank_of(query_of(rows[s]), s)[0] for s in A_found]

    # --- 3. clausulas discrecionales: aparece una decidible con >=2 claves de objeto en la ventana?
    disc = [(i, r) for i, r in enumerate(rows) if r["discretionary"]]
    lookalike = collections.Counter()
    for i, r in disc:
        _, order = bm.rank_of(query_of(r) or toks(r["text"]), i)
        window = [j for j in order[:K * 5] if j != i]
        hit = any(rows[j]["decidable"] and len(rows[j]["keys"] & r["keys"]) >= 2 for j in window)
        lookalike[hit] += 1

    # --- 4. VTI con percepcion perfecta, y tolerancia a errores del clasificador de tipos
    grid = []
    for pi in PIS:
        for rho in RHOS:
            cs, Bs = best(scalar_cost, rounds_ins, pi, rho)
            ct, Bt = best(typed_cost, rounds_ins, pi, rho)
            # errores simetricos maximos antes de perder contra el escalar optimo
            e_break = None
            for e in [x / 100 for x in range(0, 51)]:
                c, _ = min((typed_cost(rounds_ins, pi, rho, B, e, e), B) for B in range(B_MAX + 1))
                if c >= cs:
                    e_break = e; break
            grid.append(dict(pi=pi, rho=rho, scalar=round(cs, 3), B_scalar=Bs, typed=round(ct, 3),
                             B_typed=Bt, saving_abs=round(cs - ct, 3),
                             saving_pct=round(100 * (cs - ct) / cs, 1) if cs else 0.0,
                             symmetric_error_breakeven=e_break))

    out = dict(
        corpus_clauses=len(rows), decidable=sum(r["decidable"] for r in rows),
        discretionary=sum(r["discretionary"] for r in rows), K=K, query="objetos anotados (BM25)",
        retrieval=dict(n=len(ranks), found_in_initial_context=at0,
                       insufficient=len(rounds_ins),
                       rounds_needed_distribution={str(k): v for k, v in sorted(dist.items())},
                       median_rounds=sorted(rounds_ins)[len(rounds_ins) // 2] if rounds_ins else None),
        A_cur_contamination=dict(n=len(A), claim_is_corpus_clause=len(A_found),
                                 source_rank1_with_claim_query=sum(x == 1 for x in A_rank_claim),
                                 source_within_5_rounds_with_object_query=sum(x <= K * 6 for x in A_rank_obj)),
        discretionary_lookalike_decidable_in_top15=dict(yes=lookalike[True], no=lookalike[False]),
        vti=grid)
    json.dump(out, open(os.path.join(ROOT, "results", "vti_stage0.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    md = ["# Etapa 0 -- techo del valor de conocer el tipo (VTI)", "",
          f"Corpus {len(rows)} clausulas; decidibles {out['decidable']}; discrecionales {out['discretionary']}; k={K}.", "",
          "## Recuperacion (consulta = objetos anotados)", "",
          f"- decidibles con consulta: {len(ranks)}; en contexto inicial: {at0}; insuficientes: {len(rounds_ins)}",
          f"- rondas necesarias (distribucion): {out['retrieval']['rounds_needed_distribution']}",
          f"- mediana de rondas: {out['retrieval']['median_rounds']}", "",
          "## Contaminacion de A_cur", "", json.dumps(out["A_cur_contamination"], ensure_ascii=False), "",
          "## Discrecionales con decidible parecida en top-15", "",
          json.dumps(out["discretionary_lookalike_decidable_in_top15"]), "",
          "## VTI (coste por item incierto en unidades de c_r)", "",
          "| pi | c_h/c_r | escalar (B) | tipada (B') | ahorro | ahorro % | error simetrico de empate |",
          "|---|---|---|---|---|---|---|"]
    for g in grid:
        md.append(f"| {g['pi']} | {g['rho']} | {g['scalar']} ({g['B_scalar']}) | {g['typed']} ({g['B_typed']}) | "
                  f"{g['saving_abs']} | {g['saving_pct']} | {g['symmetric_error_breakeven']} |")
    open(os.path.join(ROOT, "results", "vti_stage0.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
