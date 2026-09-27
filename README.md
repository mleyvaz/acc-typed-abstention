# Abstaining for the wrong reason: discretionary clauses and the limits of automated building-code compliance checking

Code, data and results for the paper by **Maikel Leyva-Vázquez** (Universidad Bernardo O'Higgins, Chile; Universidad de Guayaquil, Ecuador) and **Angélica María Neira Toledo** (Asociación Latinoamericana de Ciencias Neutrosóficas).

The paper asks which part of a building code admits a binary automated verdict at all. It measures how many clauses are undecidable because they rest on discretion or on open-textured predicates ("adequate", "where appropriate"). It then tests whether an evidence representation that separates support, opposition and indeterminacy handles those clauses better than a scalar score. The central conceptual claim is that **normative vagueness is not evidential uncertainty**.

## Repository layout

| Path | Contents |
|---|---|
| `code/` | All scripts, numbered in execution order (see below) |
| `data/` | Controlled batteries built from CODE-ACCORD (`battery_acc*.jsonl`), routing environments (`acc_route*.jsonl`) and the two Ecuadorian NEC chapters (`data/nec/`) |
| `results/` | Every result file cited in the paper, plus `llm_cache/` (cached LLM responses; re-running with the cache costs 0 USD) |
| `docs/` | Preregistrations (`PREREG_RUTEO*.md`) with their SHA-256 hashes, the experiment plan and the result reports |

## Reproducing the results

```bash
pip install -r requirements.txt
python code/build_acc_battery.py          # controlled battery from CODE-ACCORD (downloads the dataset from Hugging Face)
python code/build_A_curated.py            # curated condition A
python code/20_framing_probe.py           # framing probe
python code/30_nec_ecuador.py             # Ecuador as third jurisdiction
python code/50_jurisdiction_rates.py      # undecidable rates by jurisdiction
python code/40_vti_stage0.py              # routing experiment, stage 0 (value of typed indeterminacy)
python code/41_build_acc_route.py && python code/42_run_agents.py && python code/43_analyze_route.py     # routing v1
python code/44_build_acc_route2.py && python code/46_run_agents2.py && python code/47_analyze_route2.py  # routing v2 (preregistered)
python code/48_dynamic_u_rival.py         # exploratory robustness: dynamic untyped rival
python code/49_second_evaluator.py        # second evaluator for the I channel
```

Scripts that call language models use OpenRouter and read the key from the `OPENROUTER_API_KEY` environment variable. With `results/llm_cache/` present, the cached responses are reused.

**Evaluator for the main battery (`results/nli_cum_acc.json`).** It was produced with the NLI pipeline of the companion repository [mleyvaz/evidence-coordinates-rag](https://github.com/mleyvaz/evidence-coordinates-rag), pinned at commit `8338a853f50533b41c16ee0d98e766945921915e`, with:

```bash
python run_experiment.py --battery data/battery_acc.jsonl --evaluator nli --agg cum --K 3 --tag acc --save_coords
```

The evaluator is `cross-encoder/nli-deberta-v3-base`, run locally at no cost.

`code/45_codex_audit.py` documents the independent audit of the gold labels of routing v2; its output is in `results/codex_audit_route2*.json`.

## Preregistration

`docs/PREREG_RUTEO.md` and `docs/PREREG_RUTEO2.md` were frozen before running the confirmatory analyses. Their hashes are in the `.sha256` files: `sha256sum docs/PREREG_RUTEO*.md` must match. Analyses not listed there (for example `48_dynamic_u_rival.py`) are exploratory, and the paper reports them as such.

## Data sources and licences

- **CODE-ACCORD**: Hettiarachchi et al., *Scientific Data* (2025), CC BY 4.0. It is downloaded from Hugging Face (`ACCORD-NLP/CODE-ACCORD-*`); the batteries in `data/` are derived from it and keep that licence.
- **Norma Ecuatoriana de la Construcción (NEC)**, chapters NEC-HS-AU (universal accessibility) and NEC-HS-CI, official regulatory documents of the Government of Ecuador, redistributed unchanged for reproducibility.
- **Code** in this repository: MIT licence (see `LICENSE`).

## Citation

If you use this material, please cite the paper (reference to be added on publication) and this repository.
