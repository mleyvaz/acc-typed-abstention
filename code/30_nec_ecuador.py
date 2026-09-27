# -*- coding: utf-8 -*-
"""
30_nec_ecuador.py -- Ecuador como TERCERA jurisdicción, comparada tema a tema.

MOTIVO. La asimetría Inglaterra 13,0 % / Finlandia 5,9 % se apoya en solo 253 cláusulas
finlandesas: es el número más débil del paper. Añadir una tercera jurisdicción EN OTRA LENGUA
Y OTRA TRADICIÓN JURÍDICA contrasta la afirmación «la automatizabilidad depende de la
redacción, no de la tecnología» contra la alternativa «es un artefacto del inglés y el finés».

COMPARACIÓN TEMA A TEMA, no código contra código:
  accesibilidad  ->  NEC-HS-AU (Ecuador) · UK_DocM V1+V2 (Inglaterra) · Finnish_Accessibility
  incendios      ->  NEC-HS-CI (Ecuador) · Finnish_FireSafety        (Inglaterra no está en el corpus)

AMENAZA A LA COMPARABILIDAD, declarada. Las oraciones de CODE-ACCORD fueron seleccionadas a
mano por 12 anotadores con el criterio de ser AUTO-CONTENIDAS. Aquí la segmentación es
automática. Para aproximar el mismo criterio se exige que la oración (a) contenga un marcador
deóntico y (b) tenga entre 60 y 400 caracteres. No es el mismo procedimiento y se reporta
como limitación; la dirección del sesgo se discute en el manuscrito.

LOS MARCADORES SE RECONSTRUYEN, NO SE TRADUCEN. El español normativo delega de otra forma
y con más variedad que el inglés.
"""
import os, re, json, unicodedata, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")

# --- marcador deóntico: la oración enuncia una obligación, no describe
DEONTIC = re.compile(r"\b(debe|deben|deberá|deberán|debiendo|es obligatori|será obligatori|"
                     r"se prohíbe|no se permitirá|se permitirá|requiere|requerirá|"
                     r"tendrá que|habrá de|se exigirá|deberán ser|debe ser|debe estar)\b", re.I)

# --- DISCRECIÓN EXPLÍCITA: el redactor delega el juicio en quien aplica
DISCRECION = re.compile("|".join([
    r"cuando\s+(sea|resulte|fuere)\s+(aplicable|necesari\w+|pertinente|posible|factible|procedente)",
    r"en\s+(lo\s+que|los\s+casos\s+en\s+que)\s+correspond\w+",
    r"de\s+ser\s+(posible|necesari\w+|aplicable)",
    r"a\s+criterio\s+d(el|e\s+la|e\s+los)",
    r"seg[uú]n\s+(el\s+criterio|las\s+buenas\s+pr[aá]cticas|correspond\w+|sea\s+necesari\w+)",
    r"siempre\s+que\s+sea\s+posible",
    r"en\s+la\s+medida\s+de\s+lo\s+posible",
    r"cuando\s+las\s+condiciones\s+lo\s+permitan",
    r"de\s+considerar\w*\s+necesari\w+",
    r"se\s+recomienda",
    r"preferentemente",
]), re.I)

# --- PREDICADO CUALITATIVO sin umbral verificable
CUALITATIVO = re.compile(r"\b(adecuad\w+|apropiad\w+|id[oó]ne\w+|suficiente\w*|razonable\w*|"
                         r"satisfactori\w+|aceptable\w*|debidamente|correctamente|"
                         r"convenient\w+|[oó]ptim\w+)\b", re.I)

HAS_NUM = re.compile(r"\d")


def reflow(txt):
    """Une líneas partidas por el maquetado a dos columnas."""
    txt = txt.replace("­", "")
    lines = [l.strip() for l in txt.split("\n")]
    out, buf = [], ""
    for l in lines:
        if not l:
            if buf: out.append(buf); buf = ""
            continue
        if re.fullmatch(r"[\d\s.,;:()\-–—]+", l):      # numeración suelta / cabeceras de página
            continue
        buf = (buf + " " + l).strip() if buf else l
        if re.search(r"[.;:]\s*$", buf):
            out.append(buf); buf = ""
    if buf: out.append(buf)
    return " ".join(out)


def sentences(txt):
    txt = " ".join(txt.split())
    parts = re.split(r"(?<=[.;])\s+(?=[A-ZÁÉÍÓÚÑ¿¡])", txt)
    return [p.strip() for p in parts if p.strip()]


def classify(s):
    disc = bool(DISCRECION.search(s))
    qual = bool(CUALITATIVO.search(s)) and not HAS_NUM.search(s)
    return dict(text=s,
                discretion=disc, qualitative=qual,
                non_decidable=disc or qual,
                decidable=bool(HAS_NUM.search(s)) and not (disc or qual))


def load_nec(name):
    p = os.path.join(ROOT, "data", "nec", f"{name}.txt")
    raw = open(p, encoding="utf-8").read()
    sents = sentences(reflow(raw))
    keep = [s for s in sents if DEONTIC.search(s) and 60 <= len(s) <= 400]
    return [classify(s) for s in keep], len(sents)


def load_codeaccord_topic(docs):
    """Subconjunto temático del corpus inglés/finés, con la MISMA operacionalización
    que usa build_acc_battery (patrones en inglés)."""
    import build_acc_battery as B
    rows = B.load_rows()
    sel = [r for r in rows if r["doc"] in docs]
    return sel


if __name__ == "__main__":
    import sys
    sys.path.insert(0, HERE)

    res = {}
    print("=" * 78)
    for name in ["NEC-HS-AU", "NEC-HS-CI"]:
        cls, n_all = load_nec(name)
        nd = sum(c["non_decidable"] for c in cls)
        dc = sum(c["decidable"] for c in cls)
        disc = sum(c["discretion"] for c in cls)
        qual = sum(c["qualitative"] for c in cls)
        res[name] = dict(n_sentences_total=n_all, n_normative=len(cls),
                         non_decidable=nd, decidable=dc,
                         discretion=disc, qualitative=qual,
                         rate=100 * nd / len(cls) if cls else 0)
        print(f"{name}: {n_all} oraciones -> {len(cls)} normativas")
        print(f"   NO DECIDIBLES {nd} = {100*nd/max(len(cls),1):5.1f} %   "
              f"(discreción {disc}, cualitativo {qual})")
        print(f"   decidibles con umbral numérico: {dc} = {100*dc/max(len(cls),1):5.1f} %")
        print("   ejemplos no decidibles:")
        for c in [c for c in cls if c["non_decidable"]][:3]:
            print(f"      · {c['text'][:150]}")
        print()

    print("=" * 78)
    print("COMPARACIÓN TEMA A TEMA — ACCESIBILIDAD")
    topic_docs = {
        "Inglaterra (UK_DocM V1+V2)": ["UK_DocM_V1_AccessAndUseOfBuildings",
                                       "UK_DocM_V2_AccessAndUseOfBuildings"],
        "Finlandia (Finnish_Accessibility)": ["Finnish_Accessibility"],
    }
    for label, docs in topic_docs.items():
        sel = load_codeaccord_topic(docs)
        nd = sum(r["discretionary"] for r in sel)
        print(f"   {label:38s} {nd:3d}/{len(sel):3d} = {100*nd/max(len(sel),1):5.1f} %")
        res[label] = dict(n=len(sel), non_decidable=nd,
                          rate=100 * nd / max(len(sel), 1))
    ec = res["NEC-HS-AU"]
    print(f"   {'Ecuador (NEC-HS-AU)':38s} {ec['non_decidable']:3d}/{ec['n_normative']:3d} "
          f"= {ec['rate']:5.1f} %")

    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    json.dump(res, open(os.path.join(ROOT, "results", "nec_ecuador.json"), "w",
                        encoding="utf-8"), indent=2, ensure_ascii=False)
    print("\n-> results/nec_ecuador.json")
