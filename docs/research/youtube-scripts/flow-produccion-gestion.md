# Flujo de producción y gestión de video con IA — versión para empezar

Basado en "Janus", la IA que **gestiona el canal** de Nate Gentile (transcript: `nate-gentile-transcript.txt`).
**Traducido a una versión mínima viable sin NAS, sin Mac y sin servidor con GPU** — solo laptop + servicios cloud.

---

## La filosofía (cópiala tal cual)

> **"Human First, AI Powered"** — no "AI First". El humano hace lo creativo; la IA hace **todo lo procedimental**.

Regla de oro de Nate para decidir qué delegar:

> *"Lo que se puede hacer con un procedimiento, con una serie de pasos, lo delego a la IA. La parte de pensar, inventar, el arte — esa es la parte humana."*

**Línea roja creativa**: él **NO** automatiza el **guion** ni la parte artística. Probó y la IA daba resultados "predecibles, iguales". El valor diferencial son las "idas de olla" humanas (ideas que la IA califica de terribles y luego hacen millones de vistas). → Para ti: usa la IA para el **borrador 0** y la logística; el pase creativo es tuyo.

Puntos donde siempre mantiene control humano: el **primer corte** de la IA no es definitivo (segunda pasada del editor), la **newsletter** se revisa antes de enviar, el **guion** lo aprueba el humano.

---

## El pipeline de Janus (lo que automatiza, en orden)

**Fase creativa (humana, asistida):** idea → requisitos → investigación → **guion** (en su app de mapas mentales, con un botón IA para verificar datos).

**Fase producción → publicación (IA orquesta):**
1. Avisas "ya estoy grabando" → la IA **notifica al equipo de edición** y marca la tarea "grabar" como *en curso*.
2. Grabas (cámara/micro → PC que graba directo al servidor).
3. Al terminar, **se sube y recompone** el video solo, y la tarea pasa a *finalizada*.
4. La IA **avisa a los editores con la ruta exacta** del archivo.
5. **Transcribe** el video entero (marca cada palabra).
6. **Propone un primer corte** (detecta repeticiones y lo que sobra).
7. **Genera el proyecto de edición** (DaVinci) ya con el corte cargado.
8. **Localiza e importa B-roll**: identifica los productos mencionados y mete planos de recurso desde una librería **indexada** (un proceso de fondo escanea, analiza con IA, comprime ~10x e indexa todo el material).
9. **Seguimiento (agente "Fama")**: pregunta avances al equipo, recibe audios, transcribe y **actualiza las tarjetas** de cada proyecto.
10. **Rutina semanal (lunes)**: reporta qué debía salir, evalúa si es realista el plan, y **re-planifica** el calendario considerando agenda personal (viajes, ferias).

Todo conectado porque **cada app tiene "puerta trasera" = una API**, y el agente central (Janus) habla con todas.

---

## Mapa: qué necesita hardware vs. qué replicas con laptop + cloud

| Pieza de Nate | ¿Imprescindible? | Sustituto para empezar |
|---|---|---|
| **NAS** (almacenamiento central) | No | **Cloud storage**: Google Drive / Dropbox / S3 / Backblaze B2 (barato). |
| **Servidor IA Threadripper + RTX 6000** | No | **Inferencia y embeddings por API** (Claude/OpenAI/Gemini) o tu Ollama actual en el Ryzen para tareas chicas. |
| **PC de grabación Linux + capturadora** | No | Graba normal (OBS en tu laptop / el móvil) y **sube manual** a la nube. |
| **Base de datos semántica de todos los videos** | No (pero muy útil) | **Vector store ligero** (ya tienes ChromaDB en el observatorio) con las transcripciones. |
| **DaVinci Resolve** (proyecto auto-generado) | No para empezar | DaVinci **gratis**; la auto-generación del proyecto se deja para después. |
| **Orion** (web app a medida = "SO del canal") | No | Empieza con **un gestor de tareas + Google Calendar** y crece. |
| **Element/Outline/Mindmap** (open-source self-hosted) | No | SaaS gratis o se autohospedan en un **VPS barato** más adelante. |
| **Mensajería a editores (WhatsApp/audios)** | — | Si trabajas solo, **se omite**; si tienes editor, un bot de Telegram basta. |

**Conclusión:** todo el **patrón** (agente orquestador + APIs + transcripción + corte + vector store + seguimiento + rutina semanal) es replicable en cloud. El hardware de Nate es **optimización de coste/control a su escala**, no un requisito.

---

## Tu versión mínima viable (sin hardware propio)

Lo que de verdad mueve la aguja para alguien que empieza, en orden de valor:

1. **Transcribir + proponer cortes.** Graba → sube a Drive → un script transcribe (Whisper API o local) → un LLM marca repeticiones y propone un primer corte en texto. *(Reemplaza pasos 5-6 de Janus, sin NAS.)*
2. **Borrador 0 del guion desde una noticia.** El patrón de "3 grupos" de `flow-guiones.md` → el observatorio ya descubre noticias (subsistema A); que genere el guion borrador. *(Esto es el subsistema C.)*
3. **Librería de B-roll indexada (ligera).** Cuando tengas clips, mételos en ChromaDB con una descripción; busca por texto. Sin compresión 10x ni GPU.
4. **Seguimiento + rutina semanal.** Un agente que cada lunes lea tu Google Calendar + lista de tareas y te diga: qué tocaba publicar, qué falta, y re-planifique. *(El "Fama"/rutina de Janus.)*
5. **Orquestador.** Más adelante, un único punto de contacto (tipo Janus) que dispare todo lo anterior. Hoy: tu observatorio + n8n ya son el embrión.

---

## Cómo aterriza en digital-observatory (subsistemas C y D)

- **Subsistema C (formatos)**: añade `youtube_long` y `youtube_short` como formatos que generan **guiones** (no posts) usando el framework de `flow-guiones.md`. Los borradores caen en la Bandeja como cualquier otro.
- **Subsistema D (Obsidian + producción)**: 
  - Esta carpeta de investigación es exactamente la "sección de research" que pediste — se puede sincronizar al vault de Obsidian.
  - El flujo "transcribir → proponer cortes" puede vivir como un endpoint manual (subes un archivo / pegas un link) que escribe el resultado a Obsidian.
  - La rutina semanal tipo "Fama" encaja con el scheduler que ya disparas por n8n.

> Próximo research pedido (subsistema D): **fal.ai** para generar video con IA — costo aproximado, requisitos, flujo. Pendiente; va en su propio documento cuando lo abordemos.
