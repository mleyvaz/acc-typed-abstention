# Resultados v2 — ¿paga tipar la abstención cuando la evidencia es cara? (15-sep-2026)

Preregistro: `PREREG_RUTEO2.md` (+ `.sha256`), congelado 06:53:59Z antes de correr ítems no decidibles.
Muestras: `results/route2_samples_openai_gpt-oss-120b_low.jsonl` (sha256 b17578da…05a4).
Análisis: `results/route2_analysis_{primary,norisk,ce3,cs1,cs100,norisk_ce3}.json`.
**Coste v2 ≈ 0,70 USD** (gpt-oss-120b 0,68; deepseek 0,025); auditoría Codex con el plan de ChatGPT.

## 1. Veredicto en una línea

**Sí paga, pero con condiciones.** Con un modelo que tipa bien, la abstención tipada envía cada caso
al remedio correcto y ahorra por canal (≈ 860 USD por caso indeterminado). El ahorro **neto** depende
de cuánto cuesta un veredicto erróneo: nulo si cuesta lo mismo que una interpretación formal, 12 %
si cuesta el triple, 28 % con límite de riesgo del 5 % (este último frágil).

## 2. Mejoras de v2 que sí funcionaron

| | v1 | v2 |
|---|---|---|
| exactitud del veredicto en D | 0,85-0,96 | **0,970** (G0 aprobada, en el límite) |
| semillas | 46 sin auditar | 89 → **74 tras auditoría Codex** (15 excluidas: 6 veredicto de oro erróneo, 4 umbral no requisito, 10 otra cláusula con umbral) |
| evidencia cara | no | RFI 1.080 USD; interpretación formal 5.510 USD |

**El modelo de razonamiento tipa bien** (tipo modal, estado inicial, cabeza tipada):

| condición | tipo correcto | acierto |
|---|---|---|
| INS_design (falta el valor) | MISSING_DATA | **73/74** |
| INS_reg (falta la cláusula) | MISSING_RULE | 52/74 |
| IND_del (norma delegada) | INDETERMINATE | **57/74** |
| IND_sil (control: cláusula borrada) | INDETERMINATE | **1/74** (63 dicen MISSING_RULE) |
| IND_real (discrecional real) | INDETERMINATE | 21/58 |

La diferencia IND_del frente a IND_sil (77 % frente a 1 %) muestra que el modelo **lee la delegación**
y no una fuga de etiqueta. En v1 (gpt-4o-mini / gpt-4.1-mini) IND_del se tipaba 12-22 de 46.

## 3. Confirmatorio (riesgo ≤ 5 %, c_s = 10, c_e = 5.510)

| hipótesis | resultado | pasa |
|---|---|---|
| H1 ahorro de T frente a U | **28,5 %** (IC95 1.140-2.022 USD por caso) | sí |
| H2 captura del hueco del oráculo | 0,41 | no |
| H3 canal IND (U − T en IND_del) | −15 USD (−46; 0) | no |
| H4 canal RFI (U − T en INS_design) | +1.842 USD (1.337; 2.383) | sí |
| C1 lee la delegación | −0,11 | no |

**Por qué H1 no significa lo que parece:**
- U (sin tipo) no logra riesgo ≤ 5 % en ningún pliegue y deriva el 100 %.
- T lo logra en un solo pliegue, y en el pliegue de prueba su riesgo sale **6,1 %**, por encima del límite.
- El ahorro viene de que T puede comprometer en D, INS_reg e INS_design, no de enrutar indeterminados.
- Es la misma estructura en c_s = 1, c_s = 100 y c_e = 3× (ahorro 24-29 %). **Resultado frágil.**

**C1 estaba mal especificado** (error mío en el preregistro): mide la derivación inmediata con los
parámetros ajustados por separado en cada conjunto. En el conjunto control, T se ajustó a derivarlo
todo, lo que infla la tasa en IND_sil. Queda reportado como fallido tal como estaba escrito.

Lectura acordada, aplicada literalmente: **fila 2, «paga el tipo falta dato (RFI), no la indeterminación».**

## 4. Sensibilidades preregistradas: aquí se ve el mecanismo

**Sin límite de riesgo** (U y T operan ambos; parámetros comparables entre conjuntos):

| canal | U − T (USD por caso, IC95) |
|---|---|
| IND_del | **+856 (749; 958)** — deriva directo en vez de buscar y pedir RFI |
| IND_sil (control) | +737 (613; 855) — no pide RFI porque tipa «falta regla», no «falta dato» |
| INS_reg | **−460 (−873; −132)** — el tipado deja de buscar antes o se equivoca de remedio |
| INS_design | −31 (−339; 274) |
| D | −117 (−355; 48) |
| **total** | **+62 (−93; 198), 2,6 %: sin diferencia** |

- C1 con parámetros comparables: T deriva de inmediato en IND_del un **76 % más** que en IND_sil (IC95 0,60-0,90). **Pasa.**
- H3 pasa (+856).

**Sin límite de riesgo y c_e = 3 × 5.510:**
- **H1 pasa: 12,0 %** (IC95 91-682 USD por caso). H3 pasa (+1.776). C1 pasa (0,76).
- Control 9,8 % y brazo real 8,6 %, este último con el IC95 rozando cero (0,7-599).

## 5. Qué se puede afirmar

1. **La indeterminación tipada tiene valor operativo real cuando la evidencia es cara.** Un caso delegado
   bien tipado se deriva directo y ahorra ≈ 860 USD frente a un agente sin tipo que primero busca y pide
   RFI. Con veredictos erróneos caros, eso da un ahorro neto del 12 % con IC95 que excluye cero.
2. **No es gratis.** El mismo tipado pierde ≈ 460 USD por caso donde falta la cláusula (se rinde antes de
   buscar o elige mal el remedio). Con errores baratos, las pérdidas compensan las ganancias.
3. **El confirmatorio primario pasa H1 por una razón distinta de la hipótesis:** la cabeza tipada comete
   menos veredictos erróneos confiados y roza el límite de riesgo. No se vende como prueba del enrutamiento.
4. Frente a v1: el «no paga» de v1 era, en buena parte, **«estos modelos no tipan»**. Con un modelo que
   tipa, el efecto por canal aparece claro.

## 6. Límites

- G0 aprobada en el límite exacto (0,970). Un solo modelo, k = 5 (confianza gruesa).
- **El rival U no tiene regla dinámica** (v1 tenía E1: derivar si la confianza no sube). Un agente sin tipo
  que aprenda de la trayectoria podría recortar parte del ahorro en IND. No probado en v2.
- Auditoría de oro por un solo juez automático (Codex), no por personas.
- Costes: RFI de un estudio de 2013 citado por fuentes secundarias; la interpretación formal de Seattle es
  el caso caro (las consultas informales cuestan menos); c_e supuesto. Sin coste de demora (9,7 días, 6 semanas).
- Gemelas delegadas y hechos de diseño generados por LLM. Corpus pequeño, sin Approved Documents completos.

## 7. Qué hacer ahora

- **Para ACC:** el hallazgo publicable pasa a ser **§4**: el tipado ahorra por canal y en neto cuando los
  errores son caros, con el control de silencio que prueba que el modelo lee la delegación.
- **Antes de enviar**, cerrar el límite más serio: añadir a U una regla dinámica (volver a correr 47 con E1-like;
  cuesta 0 USD, las muestras ya están). Si el ahorro en IND sobrevive a ese rival, el resultado es sólido.
