# Formato de brief de sesión

Se carga en `/brief` **antes** de cada focus group. El texto se inyecta en tres
lugares del pipeline: el prompt de análisis (como referencia canónica de
objetivos y participantes), el mapeo de hablantes (`map_speaker_names`, usa los
primeros 3.000 caracteres) y la traducción al inglés. Dura 60 días en Redis.

## Reglas

- **Un brief por grupo.** La clave es el título de la reunión de Zoom
  normalizado (`_normalize_title`: minúsculas y puntuación → `_`; los acentos
  se conservan y cuentan). Copiá y pegá el título exacto desde Zoom.
- **Cada reunión, un título distinto.** Si dos grupos se llaman igual, el
  segundo pisa la sesión del primero.
- **Los nombres, como aparecen en Zoom.** Es lo que usa para pegar voz ↔ nombre.
- **Solo los participantes de esta sala.** Cargar los de todos los grupos
  empeora el mapeo de hablantes: son nombres de más para elegir mal.
- El glosario de nombres propios va aparte, en la variable `QUALBOT_GLOSSARY`
  de Railway (una sola vez por proyecto). Repetirlos acá no molesta.

## Plantilla

```
CLIENTE Y OBJETIVOS                          [bloque fijo, igual en todos los grupos]
Cliente: <nombre exacto, como se escribe>
Estudio: <tema en una línea>
Decisión que se toma con esto: <para qué se usa el informe, quién lo lee>
Diseño muestral: <N> grupos segmentados por <criterio>. Este es el Grupo <n>.
Objetivo de ESTE grupo: <qué tiene que aportar este en particular>

PARTICIPANTES DE ESTE GRUPO                  [bloque variable — solo los de esta sala]
1. <Nombre como aparece en Zoom> — <edad> — <ocupación> — <dato de perfil que importe>
2. ...
Modera: <nombre>
Presentes que no participan (observadores/cliente): <nombres>

GUÍA DE PAUTAS / TEMAS                        [fijo, salvo que cambie la guía]
1. <bloque> (<minutos>): ...
2. ...
Estímulos: <qué se muestra y en qué momento>

HIPÓTESIS O FOCOS DE ATENCIÓN                 [mitad fijo, mitad de este grupo]
- Hipótesis del estudio: ...
- En este grupo prestar atención a: ...
- Contrastar con: <lo que apareció en el grupo anterior>
- Qué NO nos interesa: <para que no gaste análisis ahí>

NOMBRES PROPIOS Y JERGA DEL PROYECTO
<marcas, personas, productos, siglas — tal cual se escriben>

CORRECCIONES DE NOMBRE                        [opcional — solo si Zoom miente]
<nombre como sale en Zoom> -> <nombre que va en el documento>
```

## Qué rinde y qué no

- El dato de perfil de cada participante es lo que permite leer "las dos
  participantes de zona norte coincidieron en X" en vez de una lista de nombres.
- "Qué NO nos interesa" evita media página de análisis sobre un tema lateral
  que se comió veinte minutos de charla.
- Un brief de tres líneas no hace daño, pero tampoco arregla las atribuciones
  de citas: para eso hace falta la lista de participantes.

## Lo que el pipeline hace solo (no hace falta pedirlo)

- **La transcripción arranca en la apertura de la moderadora.** Todo lo previo
  —chequeos de audio, la anfitriona haciendo entrar gente, saludos, problemas
  técnicos— se descarta antes del análisis y de los dos PDF. El corte se
  detecta por el encuadre que la moderadora dice siempre ("no hay respuestas
  correctas o incorrectas", "voy a ser la moderadora"); si no aparece, no
  recorta nada y el aviso de Slack lo dice.
- **Los `[MM:SS]` siguen siendo del reloj de la reunión**, aunque se haya
  recortado el principio: un `[21:48]` se busca en ese minuto del video de Zoom.
- **Los títulos son `Transcripción — <grupo>` y `Transcript — <grupo>`**, con el
  idioma en el subtítulo. Los archivos de Drive salen como
  `Transcripcion_<grupo>_<session_id>_ES.pdf` / `Transcript_..._EN.pdf`.

## CORRECCIONES DE NOMBRE

El mapeo de hablantes trata la lista de asistentes de Zoom como verdad: es lo
que resuelve quién es quién. Cuando Zoom miente —dos tiles cruzados, la
moderadora entrando desde la cuenta de otra persona— el mapeo se equivoca con
toda confianza y sale un documento con la moderadora llamándose como la
anfitriona (pasó en el G2 de NOA). Esta sección lo corrige a mano, después del
mapeo y antes de cualquier PDF:

```
CORRECCIONES DE NOMBRE
Claudia -> Josefina
```

Una línea por nombre, `->` o `=`. Vale también para limpiar un nombre que
aparece mal escrito. El aviso de Slack lista las correcciones aplicadas.
