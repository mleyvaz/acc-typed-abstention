# Resultados — experimento de enrutamiento (15-sep-2026)

Preregistro y enmiendas: `PREREG_RUTEO.md` (+ `.sha256`). Código: `code/41-43`, `code/llm.py`.
Batería: `data/acc_route.jsonl` (334 ítems, 46 semillas + 58 discrecionales reales, sin anotadores).
Trayectorias: `results/route_traj_*.jsonl`. Análisis: `results/route_analysis_*.json|md`,
`results/route_exploratory_confident_verdicts.json`. **Coste total ≈ 1,23 USD.**

## 1. Veredicto en una línea

**Tipar la abstención no pagó en este entorno. Lo que sí pagó fue tener una opción de abstenerse
como categoría de salida, en vez de un umbral sobre una confianza escalar.**

## 2. Confirmatorio (riesgo selectivo ≤ 5 %): degenerado en ambos modelos

| modelo | H1 | H2 | por qué |
|---|---|---|---|
| gpt-4o-mini | no | no | todas las políticas derivan el 100 %; precisión del veredicto en D 0,85 con errores a confianza ≈ 1 |
| gpt-4.1-mini (réplica) | no | no | igual; precisión en D 0,96 (escalar) / 0,94 (tipada), no alcanza para riesgo ≤ 5 % |

H3 y C1 «pasan» solo porque todas las políticas son idénticas: pasos triviales, no evidencia.
**La hipótesis no pudo someterse a prueba en el régimen preregistrado**: la fiabilidad del
veredicto, no el tipado, es la restricción que manda.

## 3. Lo que replica en los dos modelos: la confianza escalar no sabe abstenerse

Veredictos emitidos con confianza ≥ 0,99 (ronda 0):

| condición | n | gpt-4o-mini escalar / tipada / abstención sin tipo | gpt-4.1-mini escalar / tipada / sin tipo |
|---|---|---|---|
| D (decidible) | 46 | 46 / 44 / 43 | 44 / 39 / 37 |
| IND_del (delegada) | 46 | **28** / 7 / 14 | **36** / 7 / 5 |
| IND_sil (silencio) | 46 | **27** / 9 / 10 | **32** / 6 / 8 |
| IND_real (real) | 58 | **40** / 11 / 14 | **35** / 6 / 5 |

La cabeza escalar se compromete con confianza ≥ 0,99 en el 59-78 % de los casos que **no tienen
respuesta**, casi tanto como en los decidibles. Cualquier categoría de abstención lo reduce a
10-30 %. Es la versión operativa de §7.1 del borrador («SCALAR {A,N} = 0,000»), ahora con un
modelo distinto al NLI y sobre casos cuya indecidibilidad está garantizada por construcción.

## 4. Lo que NO se sostiene: que el tipo añada algo sobre abstenerse

Exploratorio, declarado en las Enmiendas 1 y 2 antes de ver los datos respectivos.

**Techo del enrutamiento por tipo en este entorno (oráculos, conjunto primario):**
ORACLE_S frente a ORACLE_T = 1,71 → 1,36 (ρ = 3), 4,14 → 3,75 (ρ = 10), 11,10 → 10,57 (ρ = 30);
ahorro máximo 20 %, 9 % y 5 %. Es pequeño porque la cláusula que decide aparece en la primera
ronda de búsqueda en 44 de 46 semillas: buscar una vez en un caso indeterminado cuesta muy poco.

**T1 (tipada) frente a U1 (abstención sin tipo), conjunto primario, ρ = 10:**

| modelo | riesgo ≤ 0,20 | sin límite |
|---|---|---|
| gpt-4.1-mini | U1 − T1 = +0,14 (IC95 −0,33; +0,55) | +0,46 (+0,10; +0,83) |
| gpt-4o-mini | U1 degenerado (deriva todo) | −0,38 (−0,90; +0,09) |

- El signo cambia entre modelos.
- Donde T1 gana (gpt-4.1-mini sin límite), **gana igual en el control de silencio** (+0,32) y en
  el brazo real (+0,36), donde el tipo no se ve en el texto. No es leer la delegación.
- Enrutar por tipo frente a la misma cabeza sin enrutar (T1_notype − T1) aporta 0-2 %.

Con la tabla de lectura acordada de antemano: **H1 falla y el techo del oráculo es pequeño en
este entorno.** La taxonomía no queda refutada; queda sin demostrar que pague.

**Confusión que no se puede separar (añadido 15-sep, relectura):** la cabeza tipada tipa mal.
Argmax en la ronda 0 sobre IND_del: INDETERMINATE 22 de 46 (gpt-4o-mini) y 12 de 46 (gpt-4.1-mini);
el resto sale INSUFFICIENT (12 y 16) o veredicto (12 y 18). Sobre IND_real: 13 y 8 de 58. El error
INS/IND (0,26-0,35) supera el de empate de la Etapa 0 (~0,21). Aplica también la fila «H1 falla y la
cabeza tipada confunde INS con IND → la taxonomía vale, el instrumento no». **Este experimento no
distingue entre «el tipo no vale» y «estos modelos no saben tipar».**

## 5. Límites

- 46 semillas (los filtros automáticos descartaron ~40 %); corpus de 862 cláusulas donde la búsqueda
  resuelve casi todo en una ronda: el entorno es desfavorable al tipado por diseño del corpus, no
  por elección. La Etapa 0 predice más techo con colas de búsqueda largas; **no está medido**.
- Gemelas delegadas y hechos de diseño generados por deepseek con validación automática.
- Dos modelos de la misma familia (OpenAI), respuesta de un dígito con logprobs; gpt-4.1-mini dejó
  109 de 3.340 salidas con masa de dígitos válidos < 0,5.
- Búsqueda BM25 fija, no consultas generadas por el agente.

## 6. Qué significa para la línea y para ACC

1. **Para ACC:** el hallazgo publicable es §3 (el escalar se compromete con confianza máxima donde no
   hay respuesta; una categoría de abstención lo corrige), con coste y dos modelos. No §4.
   §7.2 («wrong reason») sigue sin sostenerse con la condición A actual.
2. **Para la línea «tipar la abstención»:** en este entorno el tipo no añade valor medible sobre
   abstenerse sin tipo. Queda **una sola prueba** que podría cambiarlo: un corpus donde conseguir
   evidencia sea caro o largo (Approved Documents completos, o RFI con coste real), que es donde la
   Etapa 0 ubica el techo. Si ahí tampoco paga, la línea queda como taxonomía.
3. **Cuidado con la novedad:** «la abstención debe ser una salida y no un umbral de confianza» ya
   tiene literatura (predicción selectiva, abstención en LLM). Lo propio aquí es la construcción de
   indecidibilidad garantizada sin anotadores y la medición en cumplimiento normativo.
