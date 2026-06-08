# Diseño — Modelo de Perfiles/Marcas (Subsistema A)

Fecha: 2026-06-08
Rama: room-ui-2
Tipo: spec de subsistema. Es la **columna vertebral** de un proyecto mayor (5
subsistemas). Este doc cubre SOLO el modelo de perfiles; B/C/D/E van después, cada
uno con su propio spec→plan→deploy.

## Visión

Hoy el observatorio tiene **una sola lente editorial** (Tess evalúa todo por
"relevancia para un docente / EdTech") y **una sola voz** (Carla) que publica a
**una sola cuenta** (Bluesky). El usuario quiere **segmentar** su producción de
contenido en varios "modos/sombreros" — sin marcas formales todavía — para que
quede claro **qué contenido va a qué cuenta y con qué voz**.

Introducimos una **capa de Perfil** encima del pipeline existente. Un Perfil es un
modo de contenido (no una marca, no un usuario aparte): declara qué fuentes pesan,
con qué voz escribe Carla, qué formatos produce y a qué cuenta apunta. El pipeline
(Tess→Carla→Edu→Pablo) se conserva; solo gana una capa de configuración encima.

## Estado actual (verificado en código)

- **Agentes = personas markdown + 1 llamada Ollama.** `agents/tess.md`, `carla.md`,
  `edu.md` tienen frontmatter con un campo `tools:` que `observatory/agents/persona.py`
  carga (`Persona.tools`) pero **nadie ejecuta**: config muerta. No hay loop de
  tool-calling ni framework de agentes. Las llamadas reales son single-shot
  `ChatOllama` + `HumanMessage` (`evaluator.py`, `ai_evaluator.py`, `drafter.py`,
  `agents/edu.py`). LangChain se usa solo como cliente LLM delgado.
- **Tess (artículos)** vive en `observatory/intelligence/ai_evaluator.py`: puntúa
  relevancia y emite `angles`. Salida hoy parseada a mano desde texto JSON.
- **Carla / drafter** (`observatory/intelligence/drafter.py`):
  `draft_for_platforms(hook, summary, angles, platforms, lang, ..., tone="")` **ya
  acepta `tone=` y `platforms=`**. `PLATFORM_PROMPTS` define x/linkedin/bluesky/blog.
  Persiste cada borrador vía `upsert_draft()`.
- **Modelo de draft** (`observatory/storage/drafts_store.py` + `models.py`): un
  borrador tiene `item_url, platform, lang, content, item_title, item_source` y un
  `DraftStatus`. **No** tiene noción de perfil ni de cuenta.
- **Pablo** (`observatory/agents/pablo.py`): relé a Postiz; hoy solo la integración
  de Bluesky está cableada (`postiz_bluesky_integration_id` en settings).
- **Fuentes** (`config/sources/rss_feeds.yaml`): YA existen feeds de IA (Anthropic,
  OpenAI, Google AI, HF, Meta, MS). El usuario "no postea de Claude" no porque
  falten fuentes, sino porque la única lente (educador) las descarta.
- **Perfil de usuario** (`config/profiles/hesus.yaml`, `user_profile.txt`): un solo
  individuo (Hesus). No hay perfiles de marca/modo.

## Decisiones (confirmadas con el usuario)

1. **No CrewAI / ningún framework de agentes.** Workload corre en Raspberry Pi +
   Ollama (gemma3); los modelos chicos locales son flaky para tool-calling. El
   "ruteo a perfil" es **una clasificación de una sola llamada**, no un enjambre.
2. **Robustecer con structured output** (Pydantic vía `with_structured_output`) en
   vez de parsear JSON a mano. Es el upgrade que da fiabilidad sin framework.
3. **Ruteo: router inteligente, 1 perfil por ítem.** Tess elige el MEJOR perfil.
   Fan-out (1 ítem → varios perfiles) queda como flag futuro; el modelo lo soporta
   pero arrancamos 1:1.
4. **Cuatro perfiles**: `tech-reviewer`, `tech-educator`, `linkedin-influencer`,
   `promo`. "office/pinelens" eran solo ilustrativos: NO se modelan como marcas.
5. **`account` es un alias** resuelto en un único lugar (`accounts.yaml`). Hoy solo
   Bluesky cableado; el resto queda declarado, listo para cablear.
6. **`promo` activo con catálogo manual** (`books.yaml`), sembrado con `ser-tutor` e
   `ia-para-docentes`. Leer el contenido real de los libros queda para subsistema D.
7. Campo `tools:` muerto de las personas → se quita/reconvierte a metadata simple.

## Modelo de datos

### Perfil — `config/profiles/brands/<id>.yaml`

```yaml
id: tech-reviewer
display_name: "Tech Reviewer"
emoji: "🗞️"
# Lente: multiplicadores por source_group; sesgan el score que da Tess.
source_weights:
  ai_news: 1.5
  ai_research: 1.0
  llm_tools: 1.0
  edtech: 0.3
  opportunities: 0.0
# Voz que adopta Carla para este perfil (se pasa como tone= al drafter).
voice: >
  Punchy, con opinión. "Esto salió hoy, esto importa, esto pienso."
  Directo, sin hype vacío. Primera persona.
# Qué formatos genera y a qué cuenta (alias) van.
outputs:
  - format: thread
    account: x
  - format: bluesky
    account: bluesky
  - format: youtube_short   # formato del subsistema C; aquí solo se DECLARA
    account: youtube
min_score: 6                # umbral para generar borrador con este perfil
active: true                # promo arranca con su fuente; todos active salvo aviso
```

Los 4 perfiles:

| id | source_weights (alto) | formatos (declarados) | cuentas | activo |
|----|----------------------|----------------------|---------|--------|
| `tech-reviewer` | ai_news, ai_research | thread, bluesky, youtube_short | x, bluesky, youtube | sí |
| `tech-educator` | edtech, ai_research, llm_tools | linkedin, blog, youtube_long | linkedin, youtube, (blog→Obsidian) | sí |
| `linkedin-influencer` | opportunities + carrera | linkedin | linkedin | sí |
| `promo` | (fuente: books.yaml, no RSS) | bluesky, thread, linkedin | x, bluesky, linkedin | sí |

> Nota: `youtube_short`, `youtube_long`, `blog` real son del **subsistema C**. Aquí
> los perfiles los DECLARAN, pero el pipeline solo genera los formatos que ya
> existen en `PLATFORM_PROMPTS` (x→thread se mapea a x; linkedin; bluesky; blog).
> Un `format` aún no soportado se ignora con un warning (no rompe).

### Cuentas — `config/profiles/accounts.yaml`

```yaml
# alias -> cómo se resuelve realmente en el publicador.
x:        { platform: x,        postiz_integration_id: "" }        # por cablear
linkedin: { platform: linkedin, postiz_integration_id: "" }        # por cablear
bluesky:  { platform: bluesky,  postiz_integration_id: "${BLUESKY}" } # cableado
youtube:  { platform: youtube,  destination: obsidian_draft }      # sin publicar auto
```

Un alias sin integración cableada → el borrador igual se genera y se etiqueta, pero
Pablo lo deja en estado `awaiting-user` sin intentar publicar (lo registra y avisa).

### Catálogo de libros — `config/profiles/books.yaml`

```yaml
- id: ser-tutor
  title: "Ser Tutor"
  audience: "educadores"
  status: "en preparación"
  themes: ["tutoría", "acompañamiento docente"]
  cta_url: ""              # se llena cuando exista landing/venta
  note: "contenido real en repos; ingestarlo es subsistema D"
- id: ia-para-docentes
  title: "IA para Docentes (nivel medio y superior)"
  audience: "docentes media superior y superior"
  status: "idea"
  themes: ["IA en el aula", "alfabetización en IA"]
  cta_url: ""
```

### Loader — `observatory/profiles/loader.py`

Análogo a `persona.py`. Modelos Pydantic `Profile`, `Account`, `Book`. Funciones:
`load_profiles() -> dict[str, Profile]`, `load_accounts() -> dict[str, Account]`,
`load_books() -> list[Book]`, `resolve_account(alias) -> Account`. Valida al cargar
(falla ruidoso si un perfil referencia un alias inexistente).

### Cambios al modelo de draft — `models.py` + `drafts_store.py`

El borrador gana dos campos:
- `profile_id: str` — qué perfil lo generó.
- `account: str` — alias de cuenta destino.

`upsert_draft()` los recibe y persiste (metadata de la colección de drafts en Chroma).

## Flujo (extremo a extremo)

1. **Colecta** (sin cambios): ítems entran con `source_group` (ai_news, edtech, …).
2. **Tess rutea** (`ai_evaluator.py`): por cada ítem produce, vía structured output:
   `{ profile_id, score, angles, summary, reasoning }`. Elige el perfil cuyo
   `source_weights[item.source_group] × relevancia` sea máximo. Si el `score` no
   supera el `min_score` del perfil elegido → se archiva sin borrador (menos ruido).
3. **Pipeline carga el perfil** y llama `draft_for_platforms(..., tone=profile.voice,
   platforms=[mapear(o.format) for o in profile.outputs if soportado])`. Cada draft
   resultante se persiste con `profile_id` y el `account` de ese output.
   - Caso `promo`: el pipeline NO usa Tess sobre RSS; en su lugar genera borradores
     desde `books.yaml` (hook = título+audiencia+themes, tone = voz de promo). Esto
     es una rama aparte, disparada manualmente (botón/endpoint), no por colecta.
4. **Edu** revisa igual (sin cambios).
5. **Pablo** (`pablo.py`): al publicar lee `draft.account` → `resolve_account()`.
   Si hay `postiz_integration_id` → publica; si no, deja `awaiting-user` y registra.

**Carla y los collectors no se tocan.** Carla solo recibe otro `tone`/`platforms`.

## Aislamiento y contratos

- **`profiles/loader.py`**: única fuente de verdad de perfiles/cuentas/libros.
  Entrada: archivos YAML. Salida: objetos Pydantic validados. Sin dependencias del
  pipeline → testeable solo.
- **Tess router**: entrada = `CollectedItem` + perfiles cargados; salida = struct
  `{profile_id, score, angles, ...}`. Determinista dado el modelo (temperature 0).
- **drafter**: contrato intacto; solo se le pasan `tone`/`platforms` distintos.
- **Pablo**: entrada = draft con `account`; resuelve vía loader. No conoce perfiles.

## Manejo de errores

- Perfil con alias inexistente → loader falla al arrancar (fail-fast, no en runtime).
- `format` no soportado en `PLATFORM_PROMPTS` → warning + se omite ese output.
- Cuenta sin integración → draft queda `awaiting-user`, Pablo no intenta publicar.
- Ningún perfil supera `min_score` → ítem archivado sin draft (comportamiento normal,
  no error).
- Structured output inválido del LLM → reintento de la llamada; si persiste, score=0
  y se archiva (igual que el fallback actual de `parse_llm_response`).

## Pruebas

- `loader`: carga de los 4 perfiles + accounts + books; validación de alias roto;
  resolución de cuenta cableada vs sin cablear.
- Router (Tess): dado un ítem `source_group=ai_news`, elige `tech-reviewer`; dado
  `edtech`, elige `tech-educator`. Mock del proveedor LLM con structured output.
- drafter: se invoca con `tone` y `platforms` derivados del perfil (assert sobre los
  argumentos pasados, no sobre el texto generado).
- drafts_store: round-trip de `profile_id`/`account`.
- Pablo: cuenta sin integración → no publica, deja `awaiting-user`.
- Rama `promo`: genera borradores desde `books.yaml` sin tocar RSS.

## Fuera de alcance (otros subsistemas)

- Formatos nuevos reales: guion YouTube, blog largo, shorts → **C**.
- The Batch + re-pesado de fuentes de descubrimiento → **B**.
- Salida a Obsidian (archivo + publicar manual + research fal.ai) + ingesta del
  contenido de los libros → **D**.
- Bandeja/Room: legibilidad + mostrar etiqueta de cuenta/perfil → **E**.
- Cablear cuentas reales de X/LinkedIn/YouTube en Postiz → infra aparte.
- Fan-out (1 ítem → varios perfiles) → flag futuro.
- Multi-usuario.
