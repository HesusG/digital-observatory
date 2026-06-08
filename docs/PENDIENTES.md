# Observatorio Digital — Lo que falta

Estado al 2026-06-08. Ver también el doc maestro
`docs/superpowers/specs/2026-06-08-room-management-hub-master-design.md`.

## ✅ Hecho y desplegado en nano-spud
- **A — Perfiles/Marcas**: router por fuente (tech-reviewer, tech-educator, linkedin-influencer, promo), voz/cuenta por perfil.
- **E0 — Shell**: barra lateral; Oficina encapsulada (su game loop se pausa al salir).
- **E1 — Bandeja legible**: tarjetas con tira perfil→cuenta y cuerpo en fuente legible.
- **C — Guiones YouTube**: formatos `youtube_long`/`youtube_short` + sección 🎬 Videos & Guiones.
- **Research** (git + Obsidian): guiones, producción tipo "Janus", fal.ai, equipo de video.

Room en vivo: http://100.84.156.15:8400/room/ · PRs #26–#29 mergeados · 130 tests verdes.

## ⚠️ Bloqueador operativo #1 — el Ryzen apagado
Casi todo borrador (posts, guiones) **solo se genera cuando corre el pipeline, y el pipeline necesita Ollama en el Ryzen (d3r-ser), que está apagado/offline.** Hasta que el Ryzen despierte y haya una corrida, la Bandeja y Videos están vacías. Por eso lo primero útil es el botón "Prender Ryzen".

## ⏳ Pendientes por fase

### RAG — "Preguntar" + ⚡ Prender Ryzen  (siguiente sugerido)
- [ ] `POST /api/ryzen/wake` (wake-on-LAN, apoyado en `deploy/wol-service`) + `GET /api/ryzen/status` (ya existe `check_ollama`).
- [ ] Botón "⚡ Prender Ryzen" en el Room con indicador dormido/despierto.
- [ ] Sección 💬 Preguntar: chat RAG sobre mis notas/contenido (ChromaDB ya existe).
- [ ] Decidir: ¿el RAG indexa Obsidian, los artículos del observatorio, o ambos?

### B — Fuentes de descubrimiento
- [ ] Agregar **The Batch / DeepLearning.AI (Andrew Ng)** a `config/sources/rss_feeds.yaml`.
- [ ] Afinar `source_weights` por perfil (p. ej. ¿`llm_tools` → reviewer o educator?).
- [ ] Verificar que noticias de Claude/OpenAI sí generen borradores (con el Ryzen encendido).

### D — Obsidian como hub de salida
- [ ] Escribir **cada post/guion generado a Obsidian** (archivar + publicar manual fuera de casa).
- [ ] Flujo "subir grabación → transcribir → proponer cortes" como endpoint manual.
- [ ] Ingestar contenido real de los libros (*Ser Tutor* ya está en repos) para el perfil promo.

### E — Room (resto del hub)
- [ ] Sección 📚 **Guías & Mentoring** (ligada a libros/cursos).
- [ ] Sección 🗓️ **Plan semanal** (rutina tipo "Fama" sobre Google Calendar + tareas).
- [ ] Limpiar chrome heredado de "Pixel Agents" que aún habla de "Claude sessions/hooks".

### Publicación real (infra, aparte)
- [ ] **Cablear cuentas en Postiz**: hoy solo **Bluesky** publica; X/LinkedIn/YouTube son alias sin `integration_id` → esos borradores quedan en `awaiting-user`.

## 🤔 Decisiones que dependen de mí (Hesus)
- [ ] **Blog**: ¿WordPress o blog propio en el dominio de GoDaddy? (hoy "blog" cae a borrador en Obsidian).
- [ ] Llenar `config/profiles/books.yaml` con CTA/links reales de los libros.
- [ ] Revisar voces/umbrales (`min_score`) en `config/profiles/brands/*.yaml`.
- [ ] ¿Fan-out (un ítem → varios perfiles) en el futuro? (hoy 1 perfil por ítem).

## 🔧 Deuda técnica menor
- [ ] `test_pipeline_full_flow` falla por gspread/Sheets (ambiental, ruta de oportunidades) — pre-existente, no bloquea.

## Próximo paso
Implementar **"⚡ Prender Ryzen"** (wake-on-LAN) — el interruptor que enciende toda la fábrica de contenido y el primer trozo de la fase RAG.
