# Preregistro — experimento de enrutamiento (¿paga tipar la abstención?)

**Congelado:** 2026-09-15T05:57:43Z, **antes** de correr los agentes sobre la batería completa.
Preregistro local con hashes. No se subió a OSF; subirlo es decisión de Maikel.
Plan de referencia: `PLAN_EXPERIMENTO_RUTEO.md`.

## Artefactos congelados (sha256)

| archivo | sha256 |
|---|---|
| code/llm.py | ab1b6f829a73c87ffdaf5eef5be409a3884a76db47051c28287ce22cc956bd6c |
| code/41_build_acc_route.py | 0aa09116cb495ca7ff4632859c23f40461aed42f3907925b91555418789ded3b |
| code/42_run_agents.py | d81576988a0f26eb379dfe0c0fa073011f54490e2be38b15b06003431f638409 |
| code/43_analyze_route.py | 9d69d3bc2af7ad65369e862c237eb18e89c869ae14f9adf00643648c232bb1b9 |
| data/acc_route.jsonl | b073b87fb466fb29d7252711ac477f49bbe0e55d88e304c4227a319085e6e760 |
| results/acc_route_build.json | 6c2f4ab33a65f386efa9f6e1343bdf29f5257107ff14cf3acfd06e2937122b96 |

## Batería (construida, sin anotadores)

46 semillas con umbral anotado en CODE-ACCORD-Relations × 6 condiciones (D, D_words, INS, IND_del,
IND_delnum, IND_sil) + 58 cláusulas discrecionales reales (IND_real). 334 ítems. Generación con
`deepseek/deepseek-chat-v3.1` y validación automática (rol requisito/alcance, aritmética de
cumplimiento, deriva léxica de la gemela). Coste 0,021 USD. INS: la cláusula que decide reaparece
en la ronda 1 en 44 de 46 semillas, en la 4 en 1 y fuera de presupuesto en 1.

## Agente

`openai/gpt-4o-mini`, temperatura 0, respuesta de un dígito, probabilidades por logprobs.
Dos cabezas por ítem y ronda (0-4): tipada (4 clases) y escalar (2 clases). Recuperador BM25 fijo.

## Hipótesis y reglas de decisión

Costes: c_r = 1 por ronda; c_h = ρ por derivación; c_e = ρ por veredicto erróneo. ρ primario = 10.
Parámetros por ajuste cruzado en 2 pliegues por semilla (mínimo coste con riesgo selectivo ≤ 5 %).
IC95 por bootstrap de conglomerados (semilla), 2000 remuestreos, semilla 0.

| id | enunciado | pasa si |
|---|---|---|
| **H1** | conjunto primario (D, INS, IND_del), ρ = 10: T1 cuesta menos que E1 | ahorro ≥ 10 % y límite inferior del IC95 de (E1 − T1) > 0 |
| **H2** | T1 captura el hueco del oráculo | (E1 − T1)/(E1 − ORACLE_T) ≥ 0,5 |
| **H3** | frontera: con ρ = 2 el tipado no paga | ahorro de T1 frente a E1 < 5 % |
| **C1** | control negativo (D, INS, IND_sil), ρ = 10: sin ganancia | límite inferior del IC95 de (E1 − T1) ≤ 0 |
| S1 | secundaria: enrutar por tipo frente a la misma cabeza sin enrutar | se reporta (T1_notype − T1), sin umbral |
| S2 | anti-atajo (D_words, INS, IND_delnum) y validez externa (D, INS, IND_real) | se reportan los mismos contrastes, sin umbral |
| S3 | R0 (tipado por regex) frente a E1 | se reporta |

**Lectura acordada de antemano:**
- H1 y H2 pasan, y C1 también → el tipado paga como método; va a §8 de ACC.
- H1 pasa pero C1 falla → hay fuga de etiqueta en el diseño; no se afirma nada.
- H1 falla y la cabeza tipada confunde INS con IND → la taxonomía vale, el instrumento no.
- H1 falla y ORACLE_T no mejora a E1 → no hay techo en este entorno.

## Desviaciones respecto de PLAN_EXPERIMENTO_RUTEO.md (todas antes de ver resultados)

1. **Confianza por logprobs, no verbalizada.** En la prueba de humo (7 ítems) la confianza verbalizada
   salió constante (80-90) y habría hecho del escalar un rival de paja.
2. **Ajuste cruzado en 2 pliegues** en vez de partición dev/test: con 46 semillas, un dev del 30 % sería
   demasiado pequeño para ajustar umbrales.
3. **c_e = ρ** además de la restricción de riesgo ≤ 5 %.
4. **E2 (desacuerdo entre muestras) no se corre** en esta ronda.
5. **La compuerta del instrumento no bloquea:** la corrida completa cuesta céntimos; el error de tipado
   se reporta (tabla de argmax en la ronda 0) en lugar de decidir si se gasta.
6. **Se añade T1_notype** como ablación, para separar el efecto del enrutamiento por tipo del efecto
   de la redacción de la cabeza.
7. **Tamaño:** 46 semillas, menos que las ~100-130 previstas; los filtros automáticos de validez
   descartaron el resto. Sin simulación de potencia previa; el IC95 dirá si alcanza.

## Exposición previa a datos

- Prueba de humo de 42 sobre 7 ítems (semillas s0022 y s0063) con ambas versiones de las cabezas.
- 43 se probó con trayectorias **aleatorias** sintéticas, no con salidas del modelo.
- Ninguna métrica de coste se calculó con salidas reales antes de este congelado.

---

## RESULTADO 1 (gpt-4o-mini) y ENMIENDA 1 — 2026-09-15T06:04:32Z

**Resultado preregistrado con gpt-4o-mini:** H1 no se sostiene (H1 = false, H2 = false). La causa no
es el tipado: con riesgo selectivo ≤ 5 % **ninguna política con el modelo puede comprometer
veredictos**, y todas derivan el 100 % en los cuatro conjuntos y en todo ρ. El modelo acierta el
veredicto en el 85 % de D, con errores a confianza ≈ 1,000 (6 de 7 con el oro aritméticamente
correcto, p. ej. 1000 mm ≥ 800 mm leído como incumplimiento). H3 y C1 «pasan» solo porque todo es
idéntico: son pasos triviales, no evidencia.
`results/route_traj_openai_gpt-4o-mini.jsonl` sha256 44cd1ade…5aac;
`results/route_analysis_openai_gpt-4o-mini.json` sha256 67d17caa…e301.

**Enmienda 1 (antes de ver cualquier dato del modelo nuevo):**
1. **Réplica confirmatoria con `openai/gpt-4.1-mini`**, mismo 42 (sha256 d8157698…8409) y mismo 43,
   mismas hipótesis y riesgo ≤ 5 %. Exposición previa: una sola llamada de prueba de logprobs sin
   ítems de la batería («Is 1000 mm at least 800 mm?»).
2. **43 gana el argumento `--risk_max`** (por defecto 0,05, idéntico al congelado); sha256 nuevo
   1d35881a…0043. llm.py solo añade el precio de gpt-4.1-mini (sha256 c864bcd1…2e6d).
3. **Exploratorio, NO confirmatorio, declarado aquí:** sensibilidad con riesgo ≤ 0,10, 0,20 y sin
   límite (1,0) para ambos modelos; y conteo de veredictos confiados (≥ 0,99) sobre ítems
   INDETERMINATE por cabeza. Visto ya para gpt-4o-mini: escalar 28/46 IND_del, 27/46 IND_sil,
   40/58 IND_real; tipada 7/46, 9/46, 11/58.

---

## RESULTADO 2 y ENMIENDA 2 — 2026-09-15T06:13:14Z

**Réplica confirmatoria gpt-4.1-mini (riesgo ≤ 5 %):** igual que gpt-4o-mini, degenerada. H1 = false,
H2 = false; todas las políticas derivan el 100 %. Precisión del veredicto en D: 0,957 (escalar),
0,935 (tipada).

**Exploratorio visto (Enmienda 1.3):**
- Veredictos con confianza ≥ 0,99 sobre ítems INDETERMINATE, escalar frente a tipada.
  gpt-4.1-mini: IND_del 36 frente a 7 de 46; IND_sil 32 frente a 6; IND_real 35 frente a 6 de 58.
  gpt-4o-mini: 28 frente a 7; 27 frente a 9; 40 frente a 11.
- Con riesgo ≤ 0,10-0,20, T1 ahorra 25-52 % frente a E1, pero **T1_notype ahorra casi lo mismo**
  (T1_notype − T1 ≈ 0-1 %) y **el control de silencio gana igual** (C1 falla con riesgo ≤ 0,20 en
  gpt-4.1-mini). Sin límite de riesgo, E1 ≈ T1 en coste (IC95 incluye 0), con la mitad de riesgo
  selectivo para T1 (0,23 frente a 0,42 con ρ = 10, gpt-4.1-mini).
- Lectura provisional: la ganancia viene de **tener categorías de abstención**, no de **enrutar por tipo**.

**Enmienda 2 (antes de ver datos de la cabeza nueva):** ablación decisiva **U1 = abstención SIN
tipo** (3 clases: COMPLIES, VIOLATES, CANNOT DETERMINE), misma batería, mismos contextos, ambos
modelos. 42 sha256 1a4a036d…a336 (añade `--heads abstain3`); 43 sha256 157277ed…23d0 (añade U1 y
contrastes U1 − T1, E1 − U1).

| id | enunciado | lectura |
|---|---|---|
| **A1** | veredictos ≥ 0,99 sobre IND_del: U1 frente a T1 | si U1 ≈ T1, el efecto es la abstención, no el tipo |
| **A2** | conjunto primario, ρ = 10, riesgo ≤ 0,20 y sin límite: coste U1 − T1 | IC95 > 0 → el tipo añade algo sobre abstener; IC95 ∋ 0 → no |
| **A3** | lo mismo en `control_silence` | si T1 no supera a U1 en primario ni en control, el tipado no aporta en este entorno |

Riesgo ≤ 0,20 y sin límite se eligen porque son los regímenes no degenerados ya vistos; se declara.

---

## RESULTADO 3 (Enmienda 2) — cierre

Ver `RESULTADOS_RUTEO.md`. A1: la abstención sin tipo reduce los veredictos confiados sobre
IND_del igual que la tipada en gpt-4.1-mini (5 frente a 7 de 46) y a la mitad en gpt-4o-mini (14
frente a 7). A2: U1 − T1 con ρ = 10 no tiene signo estable entre modelos (gpt-4.1-mini, riesgo ≤ 0,20:
+0,14 [−0,33; +0,55]; sin límite: +0,46 [+0,10; +0,83]; gpt-4o-mini sin límite: −0,38 [−0,90; +0,09]).
A3: donde T1 supera a U1 lo hace también en el control de silencio. **Conclusión según la lectura
acordada: el tipado no aporta en este entorno; el techo del oráculo es 5-20 %.**

Nota de trazabilidad: `results/route_analysis_openai_gpt-4o-mini.json` se regeneró con el 43 de la
Enmienda 2 (añade U1); su sha256 ya no es 67d17caa…e301. Las trayectorias originales
(`route_traj_openai_gpt-4o-mini.jsonl`, sha256 44cd1ade…5aac) no cambiaron y las hipótesis H1-C1
salen idénticas al reejecutar.
