# -*- coding: utf-8 -*-
"""Cliente OpenRouter con cache en disco y contabilidad de tokens (compartido por 41-43)."""
import os, json, hashlib, threading, time
from openai import OpenAI

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(HERE, "..", "results", "llm_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

PRICES = {  # USD por millon de tokens (OpenRouter, 15-sep-2026)
    "openai/gpt-4o-mini": (0.15, 0.60),
    "openai/gpt-4.1-mini": (0.40, 1.60),
    "openai/gpt-oss-120b": (0.037, 0.17),
    "deepseek/deepseek-chat-v3.1": (0.25, 0.95),
    "qwen/qwen3-235b-a22b-2507": (0.087, 0.35),
}

_lock = threading.Lock()
_client = None
USAGE = {}


def client():
    global _client
    if _client is None:
        _client = OpenAI(base_url="https://openrouter.ai/api/v1",
                         api_key=os.environ["OPENROUTER_API_KEY"], timeout=120)
    return _client


def _path(model):
    return os.path.join(CACHE_DIR, model.replace("/", "_") + ".jsonl")


_mem = {}


def _load(model):
    if model in _mem:
        return _mem[model]
    d = {}
    p = _path(model)
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            try:
                r = json.loads(line); d[r["k"]] = r
            except Exception:
                pass
    _mem[model] = d
    return d


def call_json(model, system, user, max_tokens=300, temperature=0.0, retries=4):
    """Devuelve (dict_parseado_o_None, texto). Cachea por (modelo, system, user, temperatura)."""
    k = hashlib.sha256(json.dumps([model, system, user, temperature, max_tokens]).encode()).hexdigest()
    with _lock:
        cache = _load(model)
        if k in cache:
            r = cache[k]
            return r["parsed"], r["text"]
    last = None
    for a in range(retries):
        try:
            resp = client().chat.completions.create(
                model=model, temperature=temperature, max_tokens=max_tokens,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
            text = resp.choices[0].message.content or ""
            u = resp.usage
            try:
                s = text.strip()
                if s.startswith("```"):
                    s = s.strip("`").split("\n", 1)[1] if "\n" in s else s
                parsed = json.loads(s[s.find("{"): s.rfind("}") + 1])
            except Exception:
                parsed = None
            rec = {"k": k, "parsed": parsed, "text": text,
                   "in": getattr(u, "prompt_tokens", 0), "out": getattr(u, "completion_tokens", 0)}
            with _lock:
                cache[k] = rec
                with open(_path(model), "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                ui = USAGE.setdefault(model, [0, 0, 0])
                ui[0] += rec["in"]; ui[1] += rec["out"]; ui[2] += 1
            return parsed, text
        except Exception as e:
            last = e
            time.sleep(2 * (a + 1))
    raise RuntimeError(f"LLM falla tras {retries} intentos: {last}")


def call_digit_probs(model, system, user, digits, retries=4):
    """Respuesta de un solo digito; devuelve {digito: prob normalizada sobre `digits`} desde top_logprobs."""
    import math
    k = hashlib.sha256(json.dumps([model, system, user, "digitprobs", digits]).encode()).hexdigest()
    with _lock:
        cache = _load(model)
        if k in cache:
            return cache[k]["parsed"]
    last = None
    for a in range(retries):
        try:
            resp = client().chat.completions.create(
                model=model, temperature=0, max_tokens=1, logprobs=True, top_logprobs=10,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
            lp = resp.choices[0].logprobs
            if lp is None or not lp.content:
                raise RuntimeError("sin logprobs")
            mass = {d: 0.0 for d in digits}
            for t in lp.content[0].top_logprobs:
                tok = t.token.strip()
                if tok in mass:
                    mass[tok] += math.exp(t.logprob)
            z = sum(mass.values())
            parsed = {d: (m / z if z > 0 else 1.0 / len(digits)) for d, m in mass.items()}
            parsed["_raw_mass"] = z
            u = resp.usage
            rec = {"k": k, "parsed": parsed, "text": resp.choices[0].message.content,
                   "in": getattr(u, "prompt_tokens", 0), "out": getattr(u, "completion_tokens", 0)}
            with _lock:
                cache[k] = rec
                with open(_path(model), "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                ui = USAGE.setdefault(model, [0, 0, 0])
                ui[0] += rec["in"]; ui[1] += rec["out"]; ui[2] += 1
            return parsed
        except Exception as e:
            last = e
            time.sleep(2 * (a + 1))
    raise RuntimeError(f"LLM falla tras {retries} intentos: {last}")


def call_sample(model, system, user, sample_idx, effort="low", temperature=1.0, max_tokens=4000, retries=5):
    """Una muestra (temperatura > 0) de un modelo de razonamiento; devuelve el texto final. Cache por indice de muestra."""
    k = hashlib.sha256(json.dumps([model, system, user, "sample", sample_idx, effort, temperature]).encode()).hexdigest()
    with _lock:
        cache = _load(model)
        if k in cache:
            return cache[k]["text"]
    last = None
    for a in range(retries):
        try:
            resp = client().chat.completions.create(
                model=model, temperature=temperature, max_tokens=max_tokens,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                extra_body={"reasoning": {"effort": effort}})
            text = resp.choices[0].message.content or ""
            u = resp.usage
            rec = {"k": k, "parsed": None, "text": text,
                   "in": getattr(u, "prompt_tokens", 0), "out": getattr(u, "completion_tokens", 0)}
            with _lock:
                cache[k] = rec
                with open(_path(model), "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                ui = USAGE.setdefault(model, [0, 0, 0])
                ui[0] += rec["in"]; ui[1] += rec["out"]; ui[2] += 1
            return text
        except Exception as e:
            last = e
            time.sleep(3 * (a + 1))
    raise RuntimeError(f"LLM falla tras {retries} intentos: {last}")


def cost_report():
    tot = 0.0
    lines = []
    for m, (i, o, n) in USAGE.items():
        pi, po = PRICES.get(m, (0, 0))
        c = i / 1e6 * pi + o / 1e6 * po
        tot += c
        lines.append(f"{m}: {n} llamadas nuevas, {i} in, {o} out, {c:.3f} USD")
    lines.append(f"TOTAL nuevo: {tot:.3f} USD")
    return "\n".join(lines)
