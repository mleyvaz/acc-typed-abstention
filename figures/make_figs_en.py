# -*- coding: utf-8 -*-
"""English figures for the AJCE manuscript (ACC, typed abstention). Adapted from the Spanish script
(ACC_TypedAbstention_2026/paper/figs_es/make_figs_es.py, not modified).

RULE: no number typed by hand. Every plotted value and every n printed in a figure is read from a file in
ACC_TypedAbstention_2026/results/. Figure 6 is a conceptual diagram without data.

Usage: python make_figs_en.py   (writes Fig1..Fig6 *.png at 300 dpi in this folder)
"""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

HERE = Path(__file__).resolve().parent
RES = HERE.parent / "results"
DPI = 300
plt.rcParams.update({"font.family": "Arial", "font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#555555",
                     "axes.linewidth": 0.7, "legend.frameon": False})
INK, MUTED = "#222222", "#8a8a8a"
BLUE, ORANGE, GREEN, RED, PURPLE, GREY = "#2f6db3", "#d9822b", "#3a8f5c", "#b84a4a", "#7a5aa6", "#bdbdbd"


def load(name):
    with open(RES / name, encoding="utf-8") as f:
        return json.load(f)


def save(fig, name):
    fig.savefig(HERE / name, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig); print("written", name)


def box(ax, x, y, w, h, title, body, fc, ec):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.018", fc=fc, ec=ec, lw=1.0))
    ax.text(x + w / 2, y + h - 0.03, title, ha="center", va="top", fontsize=8.6, fontweight="bold", color=INK)
    ax.text(x + w / 2, y + h - 0.085, body, ha="center", va="top", fontsize=7.1, color="#333333", linespacing=1.3)


def arrow(ax, p0, p1):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=10, lw=1.0, color="#555555"))


# ------------------------------------------------------------------ Fig 1 methodology
def fig1():
    ca, nli, fp = load("condicion_A.json"), load("nli_cum_acc.json"), load("framing_probe.json")
    nec = load("nec_ecuador.json")["NEC-HS-AU"]
    r2 = load("route2_analysis_primary.json"); b2 = load("acc_route2_build.json"); b1 = load("acc_route_build.json")
    se = load("second_evaluator_cost.json")
    fig, ax = plt.subplots(figsize=(7.4, 6.2)); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    W, H = 0.30, 0.215; xs = [0.02, 0.35, 0.68]; y1, y2, y3 = 0.75, 0.47, 0.19
    box(ax, xs[0], y1, W, H, "1. Corpus", f"CODE-ACCORD: {ca['N']} self-contained\nclauses (England, Finland)\n+ NEC-HS-AU (Ecuador, accessibility):\n{nec['n_sentences_total']} segmented sentences", "#eaf1fa", BLUE)
    box(ax, xs[1], y1, W, H, "2. Decidability classification", f"explicit pattern lists (§3.2)\nnumeric threshold vs\nexplicit discretion or unquantified\nqualitative predicate (n = {ca['A_union']})", "#eaf1fa", BLUE)
    box(ax, xs[2], y1, W, H, "3. Controlled battery", f"{nli['n_items']} items; claim fixed,\nonly documents vary\nS, R, A, N, N_hard\ndev {nli['n_dev']} / test {nli['n_test']}", "#fdf0e3", ORANGE)
    box(ax, xs[2], y2, W, H, "4. Evaluators", f"NLI cross-encoder (DeBERTa-v3)\nand Llama-3.3-70B ({se['total_calls_cached']} calls)\nthree separate questions:\nsupport, opposition, indeterminacy", "#fdf0e3", ORANGE)
    box(ax, xs[1], y2, W, H, "5. Scalar vs typed output", f"SCALAR: one confidence\nIND: (T, I, F) unnormalised\nTF, NORM, RENORM3\nsame decision-rule family (K = {nli['K']})", "#eaf5ee", GREEN)
    box(ax, xs[0], y2, W, H, "6. Metrics (test split)", "macro-F1, accuracy by condition,\nbehaviour emitted on A,\nmean T, F, I by condition;\nbootstrap, McNemar, Holm, TOST", "#eaf5ee", GREEN)
    box(ax, xs[0], y3, 0.47, H, "7. Framing probe (§7.4; uses step 2)", f"{fp['n_discretionary']} non-decidable vs {fp['n_decidable']} decidable clauses\nEVID, APPL, JUDG, CTRL questions\nAUROC vs trivial baseline (no digit)\nNLI and Llama-3.3-70B", "#f3eef9", PURPLE)
    box(ax, 0.51, y3, 0.47, H, "8. Routing experiments (§5.2, §7.2; seeds from step 1)", f"v1: {b1['seeds_final']} seeds, {b1['items']} items (two OpenAI models)\nv2: {b2['seeds_final']} seeds, {r2['n_excluded_seeds']} excluded by audit, {r2['n_items']} items\nD, INS_reg, INS_design, IND_del, IND_sil, IND_real\ntyped vs untyped (fixed plan, dynamic) agents", "#f3eef9", PURPLE)
    ax.text(0.5, 0.06, "Steps 1–6: what a checker emits.  Steps 7–8: whether the emitted type is visible to the model and what routing by type costs.",
            ha="center", fontsize=7.3, color=MUTED, style="italic")
    yc = y1 + H / 2
    arrow(ax, (xs[0] + W, yc), (xs[1], yc)); arrow(ax, (xs[1] + W, yc), (xs[2], yc))
    arrow(ax, (xs[2] + W / 2, y1), (xs[2] + W / 2, y2 + H))
    yc2 = y2 + H / 2
    arrow(ax, (xs[2], yc2), (xs[1] + W, yc2)); arrow(ax, (xs[1], yc2), (xs[0] + W, yc2))
    save(fig, "Fig1_methodology.png")


# ------------------------------------------------------------------ Fig 2 decidability
def fig2():
    ca, jr, comp, fp = load("condicion_A.json"), load("jurisdiction_rates.json"), load("nec_comparacion.json"), load("framing_probe.json")
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(7.4, 2.9), gridspec_kw={"width_ratios": [1.15, 0.8, 1.4], "wspace": 0.55})
    N = ca["N"]
    labels = ["quantified\n('decidable')", "non-decidable", "· explicit discretion", "· qualitative,\n  no number"]
    vals = [jr["decidable"], ca["A_union"], ca["A_strict"], ca["A_qual"]]
    y = list(range(len(vals)))[::-1]
    a1.barh(y, [100 * v / N for v in vals], color=[BLUE, RED, "#d98c8c", "#d98c8c"], height=0.6)
    for yi, v in zip(y, vals):
        a1.text(100 * v / N + 0.8, yi, f"{v} ({100 * v / N:.1f}%)", va="center", fontsize=7)
    a1.set_yticks(y); a1.set_yticklabels(labels, fontsize=7.2); a1.set_xlim(0, 45)
    a1.set_xlabel(f"% of {N} clauses"); a1.set_title("(a) CODE-ACCORD", loc="left")
    J = jr["by_jurisdiction"]; names = {"UK": "England", "FI": "Finland"}
    ks = ["UK", "FI"]
    a2.bar(range(2), [100 * J[k]["rate"] for k in ks], color=[BLUE, GREEN], width=0.6)
    for i, k in enumerate(ks):
        a2.text(i, 100 * J[k]["rate"] + 0.4, f"{100 * J[k]['rate']:.1f}%\n({J[k]['nondecidable']}/{J[k]['total']})", ha="center", fontsize=7)
    a2.set_xticks(range(2)); a2.set_xticklabels([names[k] for k in ks]); a2.set_ylim(0, 17)
    a2.set_ylabel("% non-decidable"); a2.set_title("(b) By jurisdiction", loc="left")
    keys = ["UK_DocM (accesibilidad, V1+V2)", "NEC-HS-AU [todas]", "NEC-HS-AU [long 60-400]", "NEC-HS-AU [deontico]", "NEC-HS-AU [deontico+long]"]
    lab = ["England\nDocM", "Ecuador\nall", "Ecuador\nlength", "Ecuador\ndeontic", "Ecuador\nboth"]
    x = range(len(keys)); w = 0.38
    num = [comp[k]["numeric_pct"] for k in keys]; nd = [comp[k]["nondec_pct"] for k in keys]
    a3.bar([i - w / 2 for i in x], num, w, color=[BLUE] + [GREEN] * 4, label="with numeric threshold")
    a3.bar([i + w / 2 for i in x], nd, w, color=GREY, label="non-decidable (unstable for Ecuador)")
    for i in x:
        a3.text(i - w / 2, num[i] + 1, f"{num[i]:.1f}", ha="center", fontsize=6.3)
    a3.set_xticks(list(x)); a3.set_xticklabels([f"{l}\nn={comp[k]['n']}" for l, k in zip(lab, keys)], fontsize=6.4)
    a3.set_ylim(0, 90); a3.set_ylabel("% of sentences"); a3.legend(fontsize=6.3, loc="upper left")
    a3.set_title("(c) Accessibility: England vs Ecuador", loc="left")
    save(fig, "Fig2_decidability.png")


# ------------------------------------------------------------------ Fig 3 scalar vs typed
REPS = ["IND", "TF", "NORM", "RENORM3", "SCALAR"]; CONDS = ["S", "R", "A", "N", "N_hard"]
BEH = ["ANSWER", "REFUTE", "CONFLICT_AWARE", "ABSTAIN_INSUFFICIENT", "ABSTAIN_INDETERMINATE"]
BCOL = {"ANSWER": BLUE, "REFUTE": RED, "CONFLICT_AWARE": PURPLE, "ABSTAIN_INSUFFICIENT": ORANGE, "ABSTAIN_INDETERMINATE": GREEN}


def fig3():
    d = load("nli_cum_acc.json"); s = d["summary"]
    fig = plt.figure(figsize=(7.4, 6.2)); gs = fig.add_gridspec(2, 2, height_ratios=[1, 1], hspace=0.6, wspace=0.45)
    a1, a2, a3 = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, :])
    y = list(range(len(REPS)))[::-1]; h = 0.36
    mf = [s[r]["macro_f1"] for r in REPS]; an = [s[r]["AN_macro_f1"] for r in REPS]
    lo = [s[r]["macro_f1"] - s[r]["macro_f1_ci"][0] for r in REPS]; hi = [s[r]["macro_f1_ci"][1] - s[r]["macro_f1"] for r in REPS]
    a1.barh([v + h / 2 for v in y], mf, h, xerr=[lo, hi], color=BLUE, error_kw={"lw": 0.8, "capsize": 2}, label="macro-F1, all behaviours (95% CI)")
    a1.barh([v - h / 2 for v in y], an, h, color=ORANGE, label="macro-F1 on abstention {A, N}")
    for v, a in zip(y, an):
        a1.text(a + 0.01, v - h / 2, f"{a:.3f}", va="center", fontsize=6.8)
    a1.set_yticks(y); a1.set_yticklabels(REPS); a1.set_xlim(0, 0.75); a1.set_xlabel("macro-F1 (test)")
    a1.legend(fontsize=6.6, loc="upper center", bbox_to_anchor=(0.45, -0.22)); a1.set_title("(a) Scalar vs typed (NLI)", loc="left")
    M = [[s[r]["per_condition_acc"][c] for c in CONDS] for r in REPS]
    im = a2.imshow(M, cmap="Blues", vmin=0, vmax=1, aspect="auto")
    for i, row in enumerate(M):
        for j, v in enumerate(row):
            a2.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7, color="white" if v > 0.6 else INK)
    a2.set_xticks(range(5)); a2.set_xticklabels(CONDS); a2.set_yticks(range(5)); a2.set_yticklabels(REPS)
    for sp in a2.spines.values(): sp.set_visible(False)
    a2.tick_params(length=0); a2.set_title("(b) Accuracy by condition", loc="left")
    fig.colorbar(im, ax=a2, fraction=0.046, pad=0.03).outline.set_visible(False)
    preds = [p for p in d["test_predictions"] if p["condition"] == "A"]; nA = len(preds)
    left = [0.0] * 5; yy = list(range(5))[::-1]
    for b in BEH:
        cnt = [sum(1 for p in preds if p[r] == b) for r in REPS]; pct = [100 * c / nA for c in cnt]
        a3.barh(yy, pct, left=left, color=BCOL[b], height=0.6, label=b)
        for yi, l, p, c in zip(yy, left, pct, cnt):
            if p >= 6: a3.text(l + p / 2, yi, f"{c}/{nA}", ha="center", va="center", fontsize=7, color="white")
        left = [l + p for l, p in zip(left, pct)]
    a3.set_yticks(yy); a3.set_yticklabels(REPS); a3.set_xlim(0, 100)
    a3.set_xlabel(f"% of condition-A test items (n = {nA}); only 20–27% of A is genuine indeterminacy (§6.2)")
    a3.legend(ncol=3, fontsize=6.8, loc="upper center", bbox_to_anchor=(0.5, -0.28))
    a3.set_title("(c) Behaviour emitted on discretionary-document items (condition A)", loc="left")
    save(fig, "Fig3_scalar_vs_typed.png")


# ------------------------------------------------------------------ Fig 4 I channel, two evaluators, probe
def fig4():
    cm = load("nli_cum_acc.json")["condition_means_IND"]
    f1, f2 = load("second_evaluator_llama33_f1.json")["condition_means_IND"], load("second_evaluator_llama33_f2.json")["condition_means_IND"]
    fp, lp, tb = load("framing_probe.json")["framings"], load("second_evaluator_probe_llama33.json")["framings"], load("framing_trivial_baseline.json")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.4, 3.1), gridspec_kw={"width_ratios": [1.15, 1], "wspace": 0.42})
    x = list(range(5)); w = 0.26
    for k, (src, lab, col) in enumerate([(cm, "NLI", GREEN), (f1, "Llama, framing 1", BLUE), (f2, "Llama, framing 2", ORANGE)]):
        a1.bar([i + (k - 1) * w for i in x], [src[c]["I"] for c in CONDS], w, color=col, label=lab)
    a1.set_xticks(x); a1.set_xticklabels([f"{c}\nn={cm[c]['n']}" for c in CONDS], fontsize=7)
    a1.set_ylim(0, 0.62); a1.set_ylabel("mean aggregated I (test)"); a1.legend(fontsize=6.8, loc="upper left")
    a1.set_title("(a) Indeterminacy channel by condition", loc="left")
    order = ["CTRL", "EVID", "JUDG", "APPL"]; yv = list(range(4))
    for yi, k in zip(yv, order):
        for off, src, col, lab in [(-0.14, fp, GREEN, "NLI"), (0.14, lp, ORANGE, "Llama-3.3-70B")]:
            f = src[k]
            a2.errorbar(f["auroc"], yi + off, xerr=[[f["auroc"] - f["ci95"][0]], [f["ci95"][1] - f["auroc"]]], fmt="o", color=col, ms=4, capsize=2, lw=1, label=lab if yi == 0 else None)
    a2.axvline(0.5, color=MUTED, lw=0.7, ls=":"); a2.axvline(tb["auroc"], color=RED, lw=1, ls="--")
    a2.text(tb["auroc"] - 0.01, 3.55, f"regex 'no digit'\nAUROC {tb['auroc']:.3f}", ha="right", va="top", fontsize=6.6, color=RED)
    a2.set_yticks(yv); a2.set_yticklabels(order); a2.set_xlim(0.4, 1.02); a2.set_ylim(-0.5, 3.7)
    a2.set_xlabel("AUROC, non-decidable vs decidable clauses"); a2.legend(fontsize=6.8, loc="lower right")
    a2.set_title("(b) Framing probe, two evaluators", loc="left")
    save(fig, "Fig4_indeterminacy_channel_probe.png")


# ------------------------------------------------------------------ Fig 5 routing: channels, dynamic rival, c_h
def fig5():
    dyn = load("route2_dynamic_u_rival.json")["configs"]; chs = load("route2_ch_sensitivity.json")["results"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.4, 3.2), gridspec_kw={"width_ratios": [1.25, 1], "wspace": 0.4})
    chan = ["IND_del", "INS_reg", "INS_design", "D"]; y = list(range(len(chan)))[::-1]
    for off, cfg, col, lab in [(0.18, "norisk", BLUE, "c_e = c_h"), (-0.18, "norisk_ce3", ORANGE, "c_e = 3 c_h")]:
        P = dyn[cfg]["sets"]["primary"]["contrasts"]
        for yi, c in zip(y, chan):
            v = P[f"U-T@{c}"]; vd = P[f"U_dyn-T@{c}"]
            a1.errorbar(v["diff"], yi + off, xerr=[[v["diff"] - v["ci95"][0]], [v["ci95"][1] - v["diff"]]], fmt="o", color=col, ms=4, capsize=2, lw=1, label=lab if c == chan[0] else None)
            a1.plot(vd["diff"], yi + off, marker="x", color=INK, ms=6, lw=0, label="dynamic rival U_dyn" if (c == chan[0] and cfg == "norisk") else None)
    a1.axvline(0, color=MUTED, lw=0.8)
    a1.set_yticks(y); a1.set_yticklabels(chan); a1.set_xlabel("untyped − typed cost, USD per case (95% CI)")
    a1.legend(fontsize=6.6, loc="lower right"); a1.set_title("(a) Saving by channel (no risk limit)", loc="left")
    vals = [584, 1168, 2920, 5510]
    for mult, col in [(1, BLUE), (3, ORANGE)]:
        ys = [chs[f"ch{v}_ce{mult}x_risk1.0"]["contrasts"]["U_dyn-T@IND_del"] for v in vals]
        a2.errorbar(vals, [q["diff"] for q in ys], yerr=[[q["diff"] - q["ci95"][0] for q in ys], [q["ci95"][1] - q["diff"] for q in ys]], fmt="-o", color=col, ms=4, capsize=2, lw=1, label=f"c_e = {mult} c_h" if mult == 3 else "c_e = c_h")
    a2.axvline(1080, color=RED, lw=0.9, ls="--"); a2.text(1130, 1200, "RFI cost\n(USD 1,080)", color=RED, fontsize=6.6)
    a2.set_xscale("log"); a2.set_xticks(vals); a2.set_xticklabels([str(v) for v in vals], fontsize=7)
    a2.set_xlabel("cost of a formal interpretation c_h (USD)"); a2.set_ylabel("saving on IND_del, USD per case")
    a2.axhline(0, color=MUTED, lw=0.8); a2.legend(fontsize=6.8, loc="center right", bbox_to_anchor=(1.0, 0.62))
    a2.set_title("(b) Delegated-case saving vs c_h", loc="left")
    save(fig, "Fig5_routing_costs.png")


# ------------------------------------------------------------------ Fig 6 conceptual
def fig6():
    fig, ax = plt.subplots(figsize=(7.4, 3.2)); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    cols = [(0.02, "Evidential uncertainty", "#fdf0e3", ORANGE, "'The governing clause was not retrieved,\nor the design omits the value'",
             "The norm fixes the requirement;\ninformation about the case is missing.", "Does more evidence resolve it?  YES",
             "ABSTAIN_INSUFFICIENT\n-> engineering (retrieve, index)\n-> designer (RFI)"),
            (0.51, "Normative vagueness (open texture)", "#eaf5ee", GREEN, "'Mechanical ventilation systems must be\ncommissioned to provide adequate ventilation'",
             "The norm delegates: it does not fix the\nextension of the predicate 'adequate'.", "Does more evidence resolve it?  NO",
             "ABSTAIN_INDETERMINATE\n-> interpreting authority\n   (reviewer, responsible professional)")]
    for x, title, fc, ec, ex, what, test, route in cols:
        w = 0.47
        ax.add_patch(FancyBboxPatch((x, 0.03), w, 0.94, boxstyle="round,pad=0.01,rounding_size=0.02", fc=fc, ec=ec, lw=1.1))
        ax.text(x + w / 2, 0.93, title, ha="center", va="top", fontsize=10, fontweight="bold", color=INK)
        ax.text(x + w / 2, 0.82, ex, ha="center", va="top", fontsize=7.6, style="italic", color="#333333", linespacing=1.3)
        ax.text(x + w / 2, 0.64, what, ha="center", va="top", fontsize=8, color="#333333", linespacing=1.3)
        ax.text(x + w / 2, 0.45, test, ha="center", va="top", fontsize=8.6, fontweight="bold", color=ec)
        ax.add_patch(FancyBboxPatch((x + 0.04, 0.07), w - 0.08, 0.26, boxstyle="round,pad=0.008,rounding_size=0.015", fc="white", ec=ec, lw=0.9))
        ax.text(x + w / 2, 0.30, route, ha="center", va="top", fontsize=7.8, color=INK, linespacing=1.35)
    ax.text(0.5, 0.52, "≠", ha="center", va="center", fontsize=24, color=INK)
    save(fig, "Fig6_vagueness_vs_uncertainty.png")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4(); fig5(); fig6()
