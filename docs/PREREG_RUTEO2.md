# Preregistro v2 — experimento decisivo: ¿paga tipar la abstención cuando la evidencia es cara?

**Estado:** CONGELADO tras G0 y antes de correr las condiciones no decidibles (hashes al final). v1: `PREREG_RUTEO.md`, `RESULTADOS_RUTEO.md`.

## Por qué v2

v1 no pudo decidir por cuatro razones, cada una atacada aquí:

| límite de v1 | respuesta en v2 |
|---|---|
| veredicto poco fiable (85-96 % en D) | modelo de razonamiento `openai/gpt-oss-120b`, confianza por frecuencia en k = 5 muestras; **compuerta G0** |
| búsqueda barata y corta (techo 5-20 %) | **evidencia cara con costes reales**: RFI al proyectista 1.080 USD (Navigant Construction Forum 2013, citado por fuentes secundarias; mediana 9,7 días); interpretación formal 5.510 USD (Seattle SDCI, Fee Subtitle 2026: 10 h × 551 USD; ~6 semanas; verificado en el PDF oficial) |
| etiquetas de oro sin verificación independiente | **auditoría con Codex CLI** (familia distinta del generador): 15 de 89 semillas con algún fallo, **excluidas antes de correr agentes** |
| 46 semillas | **89 semillas** (una por relación de comparación, choques borrados del corpus en mundos IND) → 74 tras la auditoría, en 77 cláusulas |

**No incluido:** los Approved Documents completos (búsqueda larga). Requiere descargar ~19 PDF de
gov.uk y el permiso explícito de Maikel; queda como v3 si v2 no decide.

## Batería (`data/acc_route2.jsonl`, `code/44_build_acc_route2.py`)

Por semilla: **D** (comprometer), **INS_reg** (falta la cláusula → buscar), **INS_design** (falta el
valor en la memoria de diseño → RFI), **IND_del** (gemela delegada, umbral borrado del corpus →
derivar), **IND_sil** (cláusula borrada → derivar; control). Más **IND_real** (58 discrecionales
reales). 503 ítems antes de exclusiones.

## Agentes (`code/46_run_agents2.py`)

`openai/gpt-oss-120b`, esfuerzo de razonamiento fijado por G0, temperatura 1, k = 5 muestras por estado.
Cabezas: **typed5** (COMPLIES, VIOLATES, MISSING_RULE, MISSING_DATA, INDETERMINATE) y **untyped3**
(COMPLIES, VIOLATES, CANNOT_DETERMINE). Estados: ronda 0-3 y, en INS_design, antes/después de la RFI.

## Compuerta G0 (solo ítems D, sin información sobre tipado)

Sobre las semillas auditadas, en el estado inicial y para **ambas** cabezas: exactitud del veredicto
modal entre los ítems donde el modal es COMPLIES/VIOLATES **≥ 0,97**, y abstención modal en D ≤ 0,15.
Si `low` no pasa, se prueba `medium`; si ninguno pasa, se reporta y no se corre el resto.

## Análisis (`code/47_analyze_route2.py`)

Costes: búsqueda c_s = 10 USD (sensibilidad 1 y 100), RFI 1.080, derivación 5.510, error c_e = 5.510
(sensibilidad 3×). Riesgo selectivo ≤ 5 % (sensibilidad sin límite). Ajuste cruzado 2 pliegues por
cláusula. IC95 bootstrap por cláusula, 2000 remuestreos.

Políticas: **U** (sin tipo + plan fijo de remedios ajustado: E, S^b E, R E, S^b R E, R S^b E),
**T** (tipada, remedio por tipo modal), **T_plan** (cabeza tipada con plan fijo; ablación),
**ORACLE_U**, **ORACLE_T**.

| id | enunciado | pasa si |
|---|---|---|
| **H1** | conjunto primario (D, INS_reg, INS_design, IND_del): T cuesta menos que U | ahorro ≥ 10 % y límite inferior IC95 de (U − T) > 0 |
| **H2** | T captura el hueco U − ORACLE_T | ≥ 0,5 |
| **H3** | canal IND: (U − T) sobre ítems IND_del | límite inferior IC95 > 0 |
| **H4** | canal RFI: (U − T) sobre ítems INS_design | límite inferior IC95 > 0 |
| **C1** | lee la delegación: P(T deriva en el estado inicial \| IND_del) − P(\| IND_sil) | límite inferior IC95 > 0 |
| S | T_plan − T; conjuntos control y externo; sensibilidades de coste y riesgo | se reportan |

**Lectura acordada:**
- H1 + H2 + C1 → el tipado paga cuando la evidencia es cara y se debe a leer el tipo.
- H1 por H4 pero no H3/C1 → paga el tipo «falta dato» (RFI), no la indeterminación.
- H1 falla con G0 aprobada y ORACLE_T ≪ ORACLE_U → el instrumento no tipa bien (medir tipo modal).
- H1 falla y ORACLE_T ≈ ORACLE_U → no hay techo ni con evidencia cara.

## Resultado de G0 (visto antes de congelar; solo ítems D)

`effort = low`, 74 semillas auditadas, estado inicial. untyped3: 64/66 = **0,970**, abstención modal
0,108. typed5: 64/66 = **0,970**, abstención 0,108. **Pasa, en el límite exacto**; no se prueba
`medium`. Coste 0,121 USD (3.560 llamadas). Muestras: `results/route2_samples_openai_gpt-oss-120b_low_gateD.jsonl`.

## Exposición previa
- Muestras de ítems D (G0). Ningún ítem INS_reg, INS_design, IND_* corrido con gpt-oss-120b.
- 47 probado solo con muestras aleatorias sintéticas.
- Una llamada de prueba de latencia sobre un ítem D.

## Artefactos congelados (sha256)
    0f3e333720ab7ead549857874887becb951439df591b1cb5ec6ccc42fa8593a7 *code/44_build_acc_route2.py
    3494d379e96baac4268d97797597800687dfe323d26b754c3b53b04b1107a1b2 *code/45_codex_audit.py
    220202652a1b2cb6a547db077d5fa246730331faa041da5b5a9a8f0453c4e6e6 *code/46_run_agents2.py
    c0f61ee23d1799b3f377f81441a63356275d058f32f96d7dfc225f15c6bd0aa4 *code/47_analyze_route2.py
    d47b502d69f0489d4aa4f7c05bcf0b835de03a9e96fd6c1de9fd9ea25f0a86b0 *code/llm.py
    6f2fc849739878a65071b027bbc1ef12aee12ff01400ac3e47e2a0f8a9ef991a *data/acc_route2.jsonl
    c018afb604c76adc469ddfdd85de631754f8043aecdf33a66073a545b0cbec46 *results/codex_audit_route2.json
    1be026e843af889b9e443abaaf6fcce6f91ca97108f9dc5a5c2c643a3e59b395 *results/codex_audit_route2_excluded.json
    congelado 2026-09-15T06:53:59Z

---

## RESULTADO (tras congelado) — ver `RESULTADOS_RUTEO2.md`

Muestras sha256 b17578daf877d83a30bcde45df32619d74c1238faaf66e97129f206cd1a105a4 (20.080 llamadas, 12 nulas).
Primario: H1 pasa (28,5 %), H2 no (0,41), H3 no (−15), H4 pasa (+1.842), C1 no (−0,11). T en el pliegue de
prueba con riesgo 6,1 %. **C1 mal especificado** (parámetros ajustados por conjunto). Sensibilidad sin
límite: H1 no (2,6 %), H3 sí (+856), C1 sí (0,76). Sin límite y c_e 3×: H1 sí (12,0 %), H3 sí, C1 sí.
