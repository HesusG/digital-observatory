# Investigación: guiones y producción de video con IA

Fecha: 2026-06-08
Para: digital-observatory — alimenta los subsistemas **C** (formatos: guiones YouTube/shorts) y **D** (research en Obsidian + flujo de producción).

## Qué es esto

Recopilación de **cómo escribir guiones de YouTube** y **cómo generar/gestionar videos con IA**, destilada de 6 videos y **adaptada para alguien que empieza** (solo laptop + servicios cloud; sin NAS, sin Mac, sin servidor con GPU).

## Documentos

- **[`flow-guiones.md`](./flow-guiones.md)** — Método unificado para escribir guiones (video largo + shorts), con fórmulas de hook, retención y el flujo de scripting asistido por IA. Incluye plantillas listas para pegar en un LLM.
- **[`flow-produccion-gestion.md`](./flow-produccion-gestion.md)** — El pipeline "graba → publica" que Nate Gentile automatiza con su IA "Janus", **traducido a una versión mínima viable sin hardware propio**, y mapeado a qué podría hacer el observatorio.

## Fuentes (transcripts en `./` y `./raw/`)

| Video | Autor | Enfoque | Transcript |
|-------|-------|---------|-----------|
| [Creé una IA que hace TODO lo que odio](https://youtu.be/OcvvmdwpPMA) | Nate Gentile | Gestión/automatización de canal | `nate-gentile-transcript.txt` |
| [How to Write a Script for a YouTube Video](https://youtu.be/8s0i1LutAc4) | Think Media | Estructura básica (hook/contenido/CTA) | `src-think-media-write-script.txt` |
| [How to Write Scripts for YouTube Videos](https://youtu.be/thhIUq_fevU) | Nate Curtiss | Intro, outline, longitud | `src-nate-curtiss-scripts.txt` |
| [Killer Script That Keeps Viewers Hooked](https://youtu.be/7I50PECz7SU) | Kallaway | Hooks + retención (el más profundo) | `src-kallaway-killer-hook.txt` |
| [Killer YouTube Shorts Script](https://youtu.be/vgq14_IqdYM) | Daniel Bitton | **Shorts** específicamente | `src-daniel-bitton-shorts.txt` |
| [Write INSANELY Good Scripts with AI](https://youtu.be/jaOIw-NiEPM) | Youri van Hofwegen | Scripting con IA (patrón de 3 grupos) | `src-youri-scripts-with-ai.txt` |

## Herramientas usadas para recopilar

- `yt-dlp` para bajar subtítulos (`json3`).
- `json3_to_text.py` (en esta carpeta) convierte los subtítulos a texto legible.

Reproducir un transcript:
```bash
yt-dlp --skip-download --write-auto-subs --sub-langs "es-orig,en-orig" --sub-format json3 -o "raw/%(id)s.%(ext)s" <URL>
python json3_to_text.py raw/<id>.<lang>.json3 > transcript.txt
```
