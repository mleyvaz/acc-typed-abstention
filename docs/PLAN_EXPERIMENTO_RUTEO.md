# Experimento de enrutamiento: ¿paga tipar la abstención?

**Creado:** 2026-09-15. **Estado:** Etapa 0 corrida; Etapas 1-5 diseñadas, sin ejecutar.
**Destino:** sección decisiva del paper ACC (*Abstaining for the wrong reason*), no un paper nuevo.

## 1. La pregunta y qué decide

Un agente de verificación que no puede dar veredicto tiene dos salidas caras: **buscar más
evidencia** o **derivar a un humano**. El agente escalar solo sabe «no estoy seguro». El tipado
sabe además *por qué*:

| tipo | remedio correcto | remedio equivocado |
|---|---|---|
| INSUFICIENTE (la cláusula que decide existe, no está en contexto) | buscar | derivar (humano resuelve algo que la máquina resolvía) |
| INDETERMINADA (la cláusula que gobierna delega el juicio) | derivar | buscar (rondas perdidas; riesgo de agarrar una cláusula parecida) |

**Pregunta:** a igual riesgo de veredicto erróneo, ¿el agente tipado cuesta menos que el mejor
agente escalar?

| resultado | lectura para la línea |
|---|---|
| Sí, y captura ≥ 50 % del techo | método con impacto; §8 de ACC y base de la línea de agentes |
| El techo existe pero el clasificador de tipos supera el error de empate | la taxonomía vale, el instrumento no; paper de medición |
| Sin techo | la línea queda como taxonomía (descartado ya por la Etapa 0, ver §2) |

## 2. Etapa 0 — techo con percepción perfecta (HECHA, 0 USD)

`code/40_vti_stage0.py` → `results/vti_stage0.json`, `results/vti_stage0.md`.
Corpus real CODE-ACCORD (862 cláusulas), BM25 con la consulta que haría un verificador (los
objetos anotados), k = 3 cláusulas por ronda.

**Valor de conocer el tipo (VTI).** El escalar óptimo elige un presupuesto fijo de rondas B y
luego deriva; con la única observación «aún no encontrado», ninguna regla de parada determinista
lo supera. La tipada deriva la indeterminada de inmediato. Coste por ítem incierto:

| P(indet. \| incierto) | c_h/c_r | ahorro del tipado | error simétrico de empate |
|---|---|---|---|
| 0,285 (94/330 del corpus) | 3 | 10,0 % | 0,40 |
| 0,285 | 5 | 18,4 % | 0,28 |
| 0,285 | **10** | **23,8 %** | **0,21** |
| 0,285 | 30 | 21,4 % | 0,12 |
| 0,285 | 50 | 18,3 % | 0,10 |
| cualquiera | 1-2 | 0-4 % | — |

Lecturas:

1. **El techo existe y es moderado: ~18-24 % para c_h/c_r entre 5 y 50.** Pasa la compuerta de
   techo (≥ 10 %). No es un efecto enorme; el paper no puede prometer más.
2. **El tipado casi no paga si buscar es tan caro como derivar** (c_h/c_r ≤ 2), y el ahorro
   relativo **decae cuando buscar es casi gratis**. Predicción falsable: la ganancia vive donde
   conseguir evidencia cuesta de verdad (en ACC, pedir información al proyectista), no en la
   recuperación automática barata.
3. **Tolerancia del clasificador de tipos: error ≤ ~0,21 en el punto primario.** Por encima, el
   tipado cuesta más que el escalar. El evaluador NLI actual emite INDETERMINADA 6 veces en 740
   ítems; si esa conducta se mantiene sobre indeterminación genuina, con ese instrumento el
   tipado **perdería**.
4. Recuperación en un corpus pequeño: 197 de 234 decidibles aparecen ya en la ronda 0; solo 37
   son insuficientes (mediana 1 ronda, cola hasta 16). Con una cola más larga el escalar necesita
   más rondas antes de derivar, así que el techo **probablemente** crece en un corpus completo;
   no está medido.

**Canal no modelado que favorece al tipado:** 20 de 94 cláusulas discrecionales tienen una
decidible parecida (≥ 2 claves de objeto) en el top-15. Un escalar que sigue buscando puede
comprometer un veredicto sobre esa cláusula. La Etapa 0 no lo cuenta; la corrida real sí.

## 3. ALERTA: la condición A no sirve para este experimento (y toca §7.2 del borrador)

Medido en la Etapa 0:

- **v1 (la del paper): 114 de 114 afirmaciones de A son una cláusula decidible del corpus.**
  v2 (A_cur): 150 de 150.
- **Buscando con la propia afirmación, la cláusula que decide sale en el rango 1 en 148 de 150.**

Por el criterio operativo del propio paper («¿se resuelve con más evidencia? Sí → insuficiencia»),
los ítems de A son **insuficientes**, no indeterminados. Decir ABSTAIN_INSUFFICIENT en el 98,8 %
de A es, bajo ese criterio, la respuesta correcta.

Consecuencia para el borrador (**no lo toqué**): la frase de §7.2 «every abstention carries the
wrong reason» no se sostiene con A tal como está construida. La reformulación 6/740 de la ronda
adversarial (conteo de salida, independiente del oro) sí se sostiene. Hay que decidir si §7.2 se
reescribe sobre 6/740 o sobre la batería nueva de §4.

## 4. Etapa 1 — batería ACC-Route SIN ANOTADORES (versión adoptada 15-sep)

**Idea:** no etiquetar el tipo; **fabricarlo editando el entorno**. Se parte de una cláusula con
umbral y se construyen cuatro mundos que solo difieren en qué hay en el corpus. El tipo de oro es
un hecho de construcción («¿existe en este corpus la cláusula que decide?»), no un juicio. Resuelve
de paso el límite declarado en §6.2 del borrador: el par «mismo requisito, una vez cuantificado y
otra delegado» no existe en un corpus único, así que se construye.

**Semillas: umbrales anotados por los expertos de CODE-ACCORD, no por nuestra regex.** El conjunto
`CODE-ACCORD-Relations` marca relaciones de comparación (`greater-equal` 107, `equal` 74,
`less-equal` 70, `greater` 55, `less` 9) entre propiedad y valor. Medido hoy: 233 cláusulas con
relación de comparación, 170 con valor numérico parseable, **131 con exactamente una**. Filtro
automático adicional: la relación debe estar en la parte obligatoria de la cláusula, no en el
antecedente («If the area exceeds 25 %…» se descarta). Rendimiento final a medir en el paso 1.

**Cuatro condiciones por semilla** (mismo hecho de diseño «propiedad = valor′» en las cuatro):

| condición | corpus visible al agente | contexto inicial | oro | remedio correcto |
|---|---|---|---|---|
| D | original | incluye la cláusula c | CUMPLE / INCUMPLE (valor′ = valor ± 15 %, relación anotada) | comprometer |
| INS | original | top-k BM25 **sin** c | insuficiente; rondas necesarias medidas | buscar |
| IND-del | c **sustituida** por su gemela delegada c* | incluye c* | indeterminada: el umbral no existe en ningún sitio | derivar |
| IND-sil | c **borrada**, sin sustituto | top-k BM25 | indeterminada: la fuente calla | derivar |

**Gemela delegada c\*:** se reemplaza el tramo «comparador + valor» por un predicado cualitativo
del propio vocabulario del corpus (adequate, suitable, sufficient, reasonable). Validación
automática, sin personas: c* no contiene el valor, contiene el predicado, conserva los tokens de
objeto y propiedad; si una reescritura con LLM hace falta para la gramática, se aceptan solo las
que pasan esas tres comprobaciones. Se excluyen semillas cuyo top-15 contenga **otra** cláusula con
relación de comparación sobre la misma propiedad (si no, IND-del sería en realidad INS).

**IND-sil es el control negativo.** Ahí el tipo no se ve en el texto: nada distingue «aún no lo
encontré» de «no existe». Predicción preregistrada: **el tipado no mejora al escalar en IND-sil.**
Si mejora, hay fuga de etiqueta en el diseño. Si no mejora en IND-sil y sí en IND-del, la ganancia
viene de leer la delegación, que es exactamente la tesis.

**Estratos anti-atajo** (la sonda de encuadre mostró que una regex de dígitos daba AUROC 0,995):

| estrato | construcción | qué rompe |
|---|---|---|
| IND-del + número | c* conserva un número ajeno al umbral (alcance, «in buildings over 3 storeys») | «sin dígitos ⇒ indeterminada» |
| D en palabras | valor escrito en letras («four hundred millimetres») | «con dígitos ⇒ decidible» |

R0 (tipado por regex) debe fallar en estos estratos; se reporta el coste por estrato.

**Brazo de validez externa (secundario, también sin anotadores):** las cláusulas discrecionales
reales sin tramo `value` en la anotación experta (83 de 94), excluidas automáticamente las 20 con
decidible parecida en el top-15. Oro = anotación publicada de CODE-ACCORD. Pregunta: ¿el ahorro
medido en IND-del se transfiere a delegación real?

**Tamaño:** ~100-130 semillas × 4 condiciones + estratos. Diseño pareado; conglomerado = semilla;
partición dev/test por semilla. El n exacto sale de la simulación de potencia (paso 2).

**Qué se pierde frente a la versión con anotadores:** las gemelas c* son texto editado, no norma
real; lo compensa el brazo externo. La anotación humana queda como robustez opcional, no como
bloqueo.

## 5. Etapa 2 — agentes

Mismo modelo base, mismo recuperador, mismas rondas; solo cambia la cabeza de salida y la regla de
enrutamiento. Todos los umbrales se ajustan en dev.

| agente | salida | enrutamiento | por qué está |
|---|---|---|---|
| E0 escalar | veredicto + confianza | compromete si conf ≥ τ; si no, busca hasta B y deriva | línea base ingenua |
| **E1 escalar dinámico** | ídem, por ronda | deriva si la confianza no sube ≥ δ tras una ronda | **rival fuerte**: puede inferir «buscar no ayuda» sin tipos |
| E2 escalar + desacuerdo | veredicto en m muestras | busca si el desacuerdo baja con evidencia, deriva si no | ataque «esto es epistémica vs aleatoria» |
| R0 tipado regex | tipo por regex sobre la cláusula recuperada | por tipo | si la regex captura el techo, tipar paga y es barato |
| T1 tipado LLM | {CUMPLE, INCUMPLE, INSUFICIENTE, INDETERMINADA} + conf | por tipo | el método |
| T2 tipado, dos encuadres | T1 + pregunta aplicativa («¿aborda el requisito y no fija umbral?») | por tipo | APPL superó a EVID en la sonda (+0,090) |
| Oráculos | tipo de oro / escalar perfecto | por tipo / B óptimo | techo y suelo |

Nota de encuadre: la pregunta es si **la representación tipada** paga, no si un LLM sabe tipar.
Si R0 gana, el resultado sigue siendo positivo para la línea.

## 6. Métrica y análisis (a preregistrar antes de abrir test)

**Primaria.** Coste esperado por verificación, C = c_r·rondas + c_h·derivaciones + c_e·veredictos
erróneos, **a riesgo selectivo igualado** r* = 5 % (fracción de veredictos comprometidos que son
erróneos), con τ, B y δ ajustados en dev para cumplir r*.

**Razones de coste.** Punto primario c_h/c_r = 10; curva completa {2, 3, 5, 10, 30, 50, 100}.
Justificación externa de c_r y c_h (tiempo de una RFI al proyectista frente a una interpretación
del inspector): buscar fuente citable antes de preregistrar.

**Hipótesis.**
- **H1 (primaria):** en r* = 5 % y c_h/c_r = 10, coste(mejor tipado) < coste(E1) con ahorro ≥ 10 %;
  IC95 por bootstrap de conglomerados (conglomerado = cláusula que gobierna) con límite inferior > 0.
- **H2:** el mejor tipado captura ≥ 50 % del ahorro del oráculo tipado frente a E1.
- **H3 (frontera, confirmatoria):** con c_h/c_r ≤ 2 el ahorro es < 5 %.
- **Compuerta del instrumento:** error simétrico de tipado en dev ≤ el de empate de la Etapa 0
  recalculado con las rondas reales. Si no pasa, se reporta como resultado (fila 2 de §1) y no se
  gasta en test.

**Secundarias.** Veredictos erróneos sobre IND por agarrar una decidible parecida (E0/E1 frente a
tipados); derivaciones mal asignadas (a ingeniería frente a autoridad interpretativa).

**Robustez.** Recuperador denso además de BM25; k ∈ {3, 5}; prevalencia de IND reponderada a
0,10 y 0,50.

## 7. Plan de ejecución

| paso | qué | coste | bloqueo |
|---|---|---|---|
| 0 | techo VTI | 0 USD | **hecho** |
| 1 | construir ACC-Route sin anotadores (semillas, gemelas c*, 4 condiciones, estratos) | 0 USD (o céntimos si c* se reescribe con LLM) | ninguno |
| 1-opc | anotación humana de una muestra de c* | opcional | no bloquea |
| 2 | simulación de potencia con costes por ítem de la Etapa 0 → n mínimo | 0 USD | 1a |
| 3 | piloto 30 ítems con E1 y T1 → tokens reales y coste de la corrida | pocos USD | saldo de API (OpenRouter estaba en negativo el 6-sep) |
| 4 | preregistro (OSF) con umbrales, razones de coste y compuertas | 0 USD | 2, 3 |
| 5 | corrida completa dev → compuerta → test | según piloto | 4 |

Ninguna cifra de n ni de coste en USD se fija antes de los pasos 2 y 3.

## 8. Amenazas declaradas

- **Corpus pequeño:** 84 % de las decidibles se recuperan en la ronda 0; la cola de insuficiencia
  es corta. Probablemente subestima el techo; generalizar exige los Approved Documents completos.
- **Circularidad de la regex** en IND: se corta con semillas de la anotación experta publicada,
  estratos anti-atajo y R0 como línea base.
- **Gemelas editadas:** texto no normativo real; lo mitigan el brazo externo y el control IND-sil.
- **Razones de coste:** la conclusión depende de c_h/c_r; por eso se reporta la curva y H3 fija
  dónde se espera que el tipado no pague.
- **Un solo dominio.** Two-Sided NLI queda como segundo dominio, fuera de este paso (regla de 4 papers).
