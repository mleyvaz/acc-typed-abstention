# -*- coding: utf-8 -*-
"""Figuras en español para paper_v01_ES (ACC, abstención tipada).

REGLA: ningún número sin código. Todo valor graficado se lee de un archivo de
../../results/. Las figuras 1 y 5 son diagramas sin datos numéricos, salvo los
n de la Figura 1, que también se leen de results/.

Uso:  python make_figs_es.py      (escribe fig1..fig5 *.png a 300 dpi en esta carpeta)
"""
import collections
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

HERE = Path(__file__).resolve().parent
RES = HERE.parent / "results"
DPI = 300

plt.rcParams.update({
    "font.family": "Calibri",
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": "#555555",
    "axes.linewidth": 0.7,
    "xtick.color": "#333333",
    "ytick.color": "#333333",
    "legend.frameon": False,
})

# paleta sobria, accesible
INK = "#222222"
MUTED = "#8a8a8a"
BLUE = "#2f6db3"
ORANGE = "#d9822b"
GREEN = "#3a8f5c"
RED = "#b84a4a"
PURPLE = "#7a5aa6"
GREY = "#bdbdbd"
LIGHT = "#f2f2f2"


def load(name):
    with open(RES / name, encoding="utf-8") as f:
        return json.load(f)


def es(x, nd=1):
    """Formato decimal con coma."""
    return f"{x:.{nd}f}".replace(".", ",")


from matplotlib.ticker import FuncFormatter
COMMA = FuncFormatter(lambda v, _: f"{v:g}".replace(".", ",").replace("-", "−"))


def save(fig, name):
    fig.savefig(HERE / name, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("escrito", name)


# ---------------------------------------------------------------- Figura 1
def box(ax, x, y, w, h, title, body, fc, ec):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.018",
                                fc=fc, ec=ec, lw=1.0))
    ax.text(x + w / 2, y + h - 0.035, title, ha="center", va="top", fontsize=9.2,
            fontweight="bold", color=INK)
    ax.text(x + w / 2, y + h - 0.095, body, ha="center", va="top", fontsize=7.6,
            color="#333333", linespacing=1.3)


def arrow(ax, p0, p1):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=11,
                                 lw=1.1, color="#555555", shrinkA=0, shrinkB=0))


def fig1():
    ca = load("condicion_A.json")
    nli = load("nli_cum_acc.json")
    fp = load("framing_probe.json")
    nec = load("nec_ecuador.json")["NEC-HS-AU"]
    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    ax.set_xlim(0, 1); ax.set_ylim(-0.01, 1); ax.axis("off")

    W, H = 0.29, 0.27
    xs = [0.02, 0.355, 0.69]
    ytop, ybot = 0.66, 0.24
    # fila superior: corpus -> clasificación -> batería
    box(ax, xs[0], ytop, W, H, "1. Corpus",
        f"CODE-ACCORD: {ca['N']} cláusulas\nautocontenidas (Inglaterra, Finlandia)\n"
        f"+ NEC-HS-AU (Ecuador, accesibilidad):\n{nec['n_sentences_total']} oraciones segmentadas",
        "#eaf1fa", BLUE)
    box(ax, xs[1], ytop, W, H, "2. Clasificación de decidibilidad",
        "listas de patrones explícitas (§3.2)\n• decidible: umbral numérico\n"
        f"• no decidible: discreción explícita\n  o predicado cualitativo sin número\n"
        f"  (n = {ca['A_union']} en CODE-ACCORD)",
        "#eaf1fa", BLUE)
    box(ax, xs[2], ytop, W, H, "3. Batería controlada",
        f"{nli['n_items']} ítems; afirmación fija,\nsolo cambian los documentos\n"
        "condiciones S, R, A, N, N_hard\n"
        f"desarrollo {nli['n_dev']} / prueba {nli['n_test']}",
        "#fdf0e3", ORANGE)
    # fila inferior: evaluador -> representaciones -> métricas
    box(ax, xs[2], ybot, W, H, "4. Evaluador NLI",
        "cross-encoder/nli-deberta-v3-base\ntres hipótesis separadas:\n"
        "afirmación · negación · indeterminación\n→ canales T, F, I (sin softmax)",
        "#fdf0e3", ORANGE)
    box(ax, xs[1], ybot, W, H, "5. Salida escalar vs tipada",
        "SCALAR: una sola confianza\nIND: (T, I, F) sin normalizar\n"
        "TF, NORM, RENORM3: variantes\nmisma familia de reglas de decisión\n"
        f"(umbrales en desarrollo, K = {nli['K']})",
        "#eaf5ee", GREEN)
    box(ax, xs[0], ybot, W, H, "6. Métricas (prueba)",
        "macro-F1 y exactitud por condición\ncomportamiento predicho en A\n"
        "medias de T, F, I por condición\nbootstrap, McNemar, Holm, TOST",
        "#eaf5ee", GREEN)
    # sonda de formulación (rama aparte)
    box(ax, xs[0], 0.005, 0.965, 0.17, "",
        "", "#f3eef9", PURPLE)
    ax.text(0.5, 0.155, "7. Sonda de formulación (usa la clasificación del paso 2; independiente de la batería, §7.4)",
            ha="center", va="top", fontsize=9.2, fontweight="bold", color=INK)
    ax.text(0.5, 0.098,
            f"{fp['n_discretionary']} cláusulas no decidibles frente a {fp['n_decidable']} decidibles · "
            "4 hipótesis (EVID, APPL, JUDG, CTRL)\n"
            "probabilidad de implicación → AUROC, comparado con una línea base trivial "
            "(ausencia de dígito)",
            ha="center", va="top", fontsize=7.6, color="#333333", linespacing=1.3)

    yc = ytop + H / 2
    arrow(ax, (xs[0] + W + 0.005, yc), (xs[1] - 0.005, yc))
    arrow(ax, (xs[1] + W + 0.005, yc), (xs[2] - 0.005, yc))
    arrow(ax, (xs[2] + W / 2, ytop - 0.01), (xs[2] + W / 2, ybot + H + 0.01))
    yc2 = ybot + H / 2
    arrow(ax, (xs[2] - 0.005, yc2), (xs[1] + W + 0.005, yc2))
    arrow(ax, (xs[1] - 0.005, yc2), (xs[0] + W + 0.005, yc2))
    save(fig, "fig1_metodologia.png")


# ---------------------------------------------------------------- Figura 2
def fig2():
    ca = load("condicion_A.json")
    fp = load("framing_probe.json")
    comp = load("nec_comparacion.json")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.2, 3.1),
                                 gridspec_kw={"width_ratios": [1, 1.35], "wspace": 0.45})

    # (a) composición de CODE-ACCORD
    N = ca["N"]
    labels = ["Con umbral numérico\n(decidibles)", "No decidibles\n(unión)",
              "· discreción explícita", "· predicado cualitativo\n  sin número"]
    vals = [fp["n_decidable"], ca["A_union"], ca["A_strict"], ca["A_qual"]]
    cols = [BLUE, RED, "#d98c8c", "#d98c8c"]
    y = range(len(vals))[::-1]
    a1.barh(list(y), [100 * v / N for v in vals], color=cols, height=0.62)
    for yi, v in zip(y, vals):
        a1.text(100 * v / N + 0.8, yi, f"{v} ({es(100 * v / N)} %)", va="center", fontsize=8)
    a1.set_yticks(list(y)); a1.set_yticklabels(labels, fontsize=8)
    a1.set_xlabel(f"% de las {N} cláusulas")
    a1.set_xlim(0, 40)
    a1.xaxis.set_major_formatter(COMMA)
    a1.set_title("(a) CODE-ACCORD (Inglaterra + Finlandia)", loc="left")

    # (b) accesibilidad: Inglaterra vs Ecuador bajo 4 segmentaciones
    keys = ["UK_DocM (accesibilidad, V1+V2)", "NEC-HS-AU [todas]", "NEC-HS-AU [long 60-400]",
            "NEC-HS-AU [deontico]", "NEC-HS-AU [deontico+long]"]
    names = ["Inglaterra\nDocM V1+V2", "Ecuador\ntodas", "Ecuador\nlongitud",
             "Ecuador\ndeóntico", "Ecuador\ndeónt.+long."]
    num = [comp[k]["numeric_pct"] for k in keys]
    nd = [comp[k]["nondec_pct"] for k in keys]
    ns = [comp[k]["n"] for k in keys]
    x = range(len(keys))
    w = 0.38
    a2.bar([i - w / 2 for i in x], num, w, color=[BLUE] + [GREEN] * 4, label="con umbral numérico")
    a2.bar([i + w / 2 for i in x], nd, w, color=GREY, label="no decidibles")
    for i in x:
        a2.text(i - w / 2, num[i] + 1.2, es(num[i]), ha="center", fontsize=7.2)
        a2.text(i + w / 2, nd[i] + 1.2, es(nd[i]), ha="center", fontsize=7.2, color="#555555")
    a2.set_xticks(list(x))
    a2.set_xticklabels([f"{n}\n(n = {k})" for n, k in zip(names, ns)], fontsize=7.2)
    a2.set_ylabel("% de oraciones")
    a2.set_ylim(0, 85)
    a2.legend(fontsize=7.5, loc="upper left")
    a2.set_title("(b) Accesibilidad: Inglaterra frente a Ecuador", loc="left")
    save(fig, "fig2_decidibilidad.png")


# ---------------------------------------------------------------- Figura 3
REPS = ["IND", "TF", "NORM", "RENORM3", "SCALAR"]
CONDS = ["S", "R", "A", "N", "N_hard"]
BEH = ["ANSWER", "REFUTE", "CONFLICT_AWARE", "ABSTAIN_INSUFFICIENT", "ABSTAIN_INDETERMINATE"]
BEH_ES = {"ANSWER": "ANSWER (cumple)", "REFUTE": "REFUTE (no cumple)",
          "CONFLICT_AWARE": "CONFLICT_AWARE",
          "ABSTAIN_INSUFFICIENT": "ABSTAIN_INSUFFICIENT",
          "ABSTAIN_INDETERMINATE": "ABSTAIN_INDETERMINATE"}
BEH_COL = {"ANSWER": BLUE, "REFUTE": RED, "CONFLICT_AWARE": PURPLE,
           "ABSTAIN_INSUFFICIENT": ORANGE, "ABSTAIN_INDETERMINATE": GREEN}


def fig3():
    d = load("nli_cum_acc.json")
    s = d["summary"]
    fig = plt.figure(figsize=(7.2, 6.4))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.05], hspace=0.55, wspace=0.42)
    a1 = fig.add_subplot(gs[0, 0]); a2 = fig.add_subplot(gs[0, 1]); a3 = fig.add_subplot(gs[1, :])

    # (a) macro-F1 global y en {A,N}
    y = list(range(len(REPS)))[::-1]
    mf = [s[r]["macro_f1"] for r in REPS]
    lo = [s[r]["macro_f1"] - s[r]["macro_f1_ci"][0] for r in REPS]
    hi = [s[r]["macro_f1_ci"][1] - s[r]["macro_f1"] for r in REPS]
    an = [s[r]["AN_macro_f1"] for r in REPS]
    h = 0.36
    a1.barh([v + h / 2 for v in y], mf, h, xerr=[lo, hi], color=BLUE,
            error_kw={"lw": 0.8, "capsize": 2}, label="macro-F1 global (IC 95 %)")
    a1.barh([v - h / 2 for v in y], an, h, color=ORANGE, label="macro-F1 en abstención {A, N}")
    for v, m, a in zip(y, mf, an):
        a1.text(a + 0.01, v - h / 2, es(a, 3), va="center", fontsize=7)
    a1.set_yticks(y); a1.set_yticklabels(REPS)
    a1.set_xlim(0, 0.75); a1.set_xlabel("macro-F1 (conjunto de prueba)")
    a1.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.45, -0.2), ncol=1)
    a1.xaxis.set_major_formatter(COMMA)
    a1.set_title("(a) Escalar frente a representaciones tipadas", loc="left")

    # (b) exactitud por condición (mapa de calor)
    M = [[s[r]["per_condition_acc"][c] for c in CONDS] for r in REPS]
    im = a2.imshow(M, cmap="Blues", vmin=0, vmax=1, aspect="auto")
    for i, row in enumerate(M):
        for j, v in enumerate(row):
            a2.text(j, i, es(v, 2), ha="center", va="center", fontsize=7.5,
                    color="white" if v > 0.6 else INK)
    a2.set_xticks(range(len(CONDS))); a2.set_xticklabels(CONDS)
    a2.set_yticks(range(len(REPS))); a2.set_yticklabels(REPS)
    for sp in a2.spines.values():
        sp.set_visible(False)
    a2.tick_params(length=0)
    a2.set_xlabel("condición de la batería")
    cb_fmt = True
    a2.set_title("(b) Exactitud por condición", loc="left")
    cb = fig.colorbar(im, ax=a2, fraction=0.046, pad=0.03)
    cb.ax.yaxis.set_major_formatter(COMMA); cb.ax.tick_params(labelsize=7); cb.outline.set_visible(False)

    # (c) comportamiento predicho en la condición A, por representación
    preds = [p for p in d["test_predictions"] if p["condition"] == "A"]
    nA = len(preds)
    left = [0.0] * len(REPS)
    yy = list(range(len(REPS)))[::-1]
    for b in BEH:
        cnt = [sum(1 for p in preds if p[r] == b) for r in REPS]
        pct = [100 * c / nA for c in cnt]
        a3.barh(yy, pct, left=left, color=BEH_COL[b], height=0.6, label=BEH_ES[b])
        for yi, l, p, c in zip(yy, left, pct, cnt):
            if p >= 6:
                a3.text(l + p / 2, yi, f"{c}/{nA}", ha="center", va="center",
                        fontsize=7.5, color="white")
        left = [l + p for l, p in zip(left, pct)]
    a3.set_yticks(yy); a3.set_yticklabels(REPS)
    a3.set_xlim(0, 100); a3.set_xlabel(f"% de los ítems de la condición A en prueba (n = {nA})")
    a3.legend(ncol=3, fontsize=7.3, loc="upper center", bbox_to_anchor=(0.5, -0.2))
    a3.xaxis.set_major_formatter(COMMA)
    a3.set_title("(c) Qué emite cada representación ante cláusulas discrecionales (condición A; "
                 "referencia: ABSTAIN_INDETERMINATE)", loc="left")
    save(fig, "fig3_escalar_vs_tipado.png")


# ---------------------------------------------------------------- Figura 4
def fig4():
    d = load("nli_cum_acc.json")
    cm = d["condition_means_IND"]
    fp = load("framing_probe.json")
    pr = load("framing_paired.json")
    tb = load("framing_trivial_baseline.json")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.2, 3.2),
                                 gridspec_kw={"width_ratios": [1.1, 1], "wspace": 0.4})

    # (a) medias de D, E, I por condición
    x = list(range(len(CONDS)))
    w = 0.26
    series = [("D", "D = T − F", BLUE), ("E", "E = T + F", GREY),
              ("I", "I (indeterminación)", GREEN)]
    for k, (key, lab, col) in enumerate(series):
        vals = [cm[c][key] for c in CONDS]
        a1.bar([i + (k - 1) * w for i in x], vals, w, color=col, label=lab)
    for i, c in enumerate(CONDS):
        a1.text(i + w, max(cm[c]["I"], 0) + 0.012, es(cm[c]["I"], 2), ha="center",
                fontsize=7, color=GREEN, fontweight="bold")
    a1.axhline(0, color="#555555", lw=0.7)
    a1.set_xticks(x); a1.set_xticklabels([f"{c}\n(n = {cm[c]['n']})" for c in CONDS], fontsize=7.5)
    a1.set_ylabel("media en prueba")
    a1.legend(fontsize=7, loc="upper right")
    a1.yaxis.set_major_formatter(COMMA)
    a1.set_title("(a) El canal I es plano en todas las condiciones", loc="left")

    # (b) sonda de formulación: AUROC con IC 95 % y línea base trivial
    order = ["CTRL", "EVID", "JUDG", "APPL"]
    names = {"CTRL": "CTRL (control)", "EVID": "EVID (evidencial)",
             "JUDG": "JUDG (juicio)", "APPL": "APPL (aplicativa)"}
    yv = list(range(len(order)))
    for yi, k in zip(yv, order):
        f = fp["framings"][k]
        col = PURPLE if k == "APPL" else (MUTED if k == "CTRL" else BLUE)
        a2.errorbar(f["auroc"], yi, xerr=[[f["auroc"] - f["ci95"][0]], [f["ci95"][1] - f["auroc"]]],
                    fmt="o", color=col, ms=5, capsize=3, lw=1.1)
        a2.text(f["ci95"][1] + 0.012, yi, es(f["auroc"], 3), va="center", fontsize=7.5)
    a2.axvline(0.5, color=MUTED, lw=0.7, ls=":")
    a2.axvline(tb["auroc"], color=RED, lw=1.1, ls="--")
    a2.text(tb["auroc"] - 0.01, len(order) - 0.45,
            f"regex «sin dígito»\nAUROC = {es(tb['auroc'], 3)}",
            ha="right", va="top", fontsize=7, color=RED)
    a2.set_yticks(yv); a2.set_yticklabels([names[k] for k in order], fontsize=7.8)
    a2.set_ylim(-0.6, len(order) - 0.3)
    a2.set_xlim(0.4, 1.02)
    a2.set_xlabel(f"AUROC ({fp['n_discretionary']} no decidibles vs {fp['n_decidable']} decidibles)")
    a2.xaxis.set_major_formatter(COMMA)
    a2.set_title("(b) Sonda de formulación", loc="left")
    a2.text(0.41, -0.52,
            f"APPL − EVID = +{es(pr['delta_mean'], 3)}  "
            f"[IC 95 %: +{es(pr['delta_ci95'][0], 3)}, +{es(pr['delta_ci95'][1], 3)}]",
            fontsize=7, color=PURPLE)
    save(fig, "fig4_canal_I_y_sonda.png")


# ---------------------------------------------------------------- Figura 5 (conceptual)
def fig5():
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    cols = [(0.02, "Incertidumbre evidencial", "#fdf0e3", ORANGE,
             "«No se recuperó la cláusula aplicable\no falta el dato del proyecto»",
             "La norma fija el requisito; falta\ninformación sobre el caso.",
             "¿Más evidencia lo resuelve?  SÍ",
             "ABSTAIN_INSUFFICIENT\n→ ingeniería: recuperar, indexar,\n   completar el corpus"),
            (0.51, "Vaguedad normativa (textura abierta)", "#eaf5ee", GREEN,
             "«Mechanical ventilation systems must be\ncommissioned to provide adequate ventilation»",
             "La norma delega: no fija la extensión\ndel predicado «adequate».",
             "¿Más evidencia lo resuelve?  NO",
             "ABSTAIN_INDETERMINATE\n→ autoridad interpretativa humana\n   (revisor, profesional responsable)")]
    for x, title, fc, ec, ex, what, test, route in cols:
        w = 0.47
        ax.add_patch(FancyBboxPatch((x, 0.03), w, 0.94, boxstyle="round,pad=0.01,rounding_size=0.02",
                                    fc=fc, ec=ec, lw=1.1))
        ax.text(x + w / 2, 0.93, title, ha="center", va="top", fontsize=10.5,
                fontweight="bold", color=INK)
        ax.text(x + w / 2, 0.82, ex, ha="center", va="top", fontsize=8, style="italic",
                color="#333333", linespacing=1.3)
        ax.text(x + w / 2, 0.64, what, ha="center", va="top", fontsize=8.3, color="#333333",
                linespacing=1.3)
        ax.text(x + w / 2, 0.45, test, ha="center", va="top", fontsize=9, fontweight="bold",
                color=ec)
        ax.add_patch(FancyBboxPatch((x + 0.04, 0.07), w - 0.08, 0.26,
                                    boxstyle="round,pad=0.008,rounding_size=0.015",
                                    fc="white", ec=ec, lw=0.9))
        ax.text(x + w / 2, 0.30, route, ha="center", va="top", fontsize=8.2, color=INK,
                linespacing=1.35)
    ax.text(0.5, 0.52, "≠", ha="center", va="center", fontsize=26, color=INK)
    save(fig, "fig5_vaguedad_vs_incertidumbre.png")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4(); fig5()
