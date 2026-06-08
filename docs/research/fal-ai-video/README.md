# Generar video con IA usando fal.ai — Guía práctica para principiantes

> **Para quién es esto:** un creador en solitario, con solo una laptop + nube (sin GPU
> propia), que quiere generar clips de video con IA (B-roll, shorts, clips ilustrativos)
> para un flujo de YouTube / redes sociales.
>
> **Contexto:** esta guía alimenta el proyecto `digital-observatory`, que ya descubre
> noticias de IA y redacta posts. El objetivo es decidir **si y cómo** enchufar fal.ai
> al pipeline.
>
> **Fecha de verificación:** 2026-06-08. Los precios y el catálogo de modelos de fal.ai
> **cambian rápido**; cada cifra está atada a su fuente en la sección [Fuentes](#fuentes).
> Donde hay incertidumbre, lo digo explícitamente.

---

## 1. ¿Qué es fal.ai?

fal.ai es una **plataforma de inferencia** (un "servidor de modelos como servicio"). En
lugar de instalar modelos o alquilar GPUs, llamas a **una sola API** y fal ejecuta el
modelo en su infraestructura, optimizada para baja latencia. Pagas solo por el resultado.

Lo importante para nosotros:

- **Hospeda muchos modelos detrás de una API unificada.** fal anuncia un catálogo de
  **600–1000+ modelos** de imagen, **video**, audio y 3D. Cambias de Kling a Veo a
  Seedance cambiando un único string (el "endpoint id"), sin reescribir tu código.
- **No necesitas GPU.** Todo corre en la nube de fal. Tu laptp solo manda el prompt y
  descarga el `.mp4` resultante por URL.
- **Pensado para desarrolladores.** Hay cliente oficial de **Python** (`fal-client`) y
  de JavaScript, además de REST y un sistema de **cola (queue)** para trabajos largos
  como el video.
- **Modelo de pago prepago (créditos).** Compras créditos por adelantado y se descuentan
  conforme generas. **No te cobran por errores del servidor ni por tiempo en cola** —
  solo por inferencias exitosas.

En una frase: fal.ai es el "router multi-modelo" más práctico para video con IA en 2026,
ideal cuando quieres probar y comparar varios modelos sin atarte a un solo proveedor.

---

## 2. ¿Qué modelos de video hay hoy en fal?

fal aloja casi todos los modelos de video relevantes del momento. Esto es lo que se
puede usar **a junio de 2026** (verificado contra páginas de modelos de fal.ai):

| Modelo | Tipo | Uso típico | Notas de duración / resolución |
|---|---|---|---|
| **Kling 2.5 Turbo Pro** (`fal-ai/kling-video/v2.5-turbo/pro/...`) | text→video, image→video | El mejor balance calidad/precio para principiantes. Movimiento fluido, look cinematográfico | Base de 5 s, extensible segundo a segundo |
| **Kling 3.0 / 3.0 Pro** | text→video, image→video | Top de gama de Kling, audio nativo, soporte de "elementos" personalizados | El más nuevo de la familia Kling |
| **Veo 3 / 3.1** (Google) | text→video, image→video | Calidad "broadcast", **audio nativo**, color profesional. Para entregables finales | Premium; resolución alta hasta 4K en variantes |
| **Seedance 1.0 / 1.5 / 2.0 Pro** (ByteDance) | text→video, image→video | Muy buena relación calidad/precio, soporta 1080p y audio (1.5+) | Ej. 1080p a 5 s |
| **MiniMax / Hailuo 02** (Standard y Pro) | text→video, image→video | Económico, buena física de movimiento. Standard 768p, Pro 1080p | Hasta ~10 s, 24–30 FPS |
| **Wan 2.2 / 2.5 / 2.6** (Alibaba) | text→video, image→video | Open-source, **el más barato por segundo**. Buena calidad/diversidad de movimiento | Wan 2.5 ~$0.05/s |
| **LTX Video / LTX 2** | text→video, image→video | Muy rápido y barato, ideal para iterar borradores | Variantes "fast" y "pro" |
| **Sora 2 / Sora 2 Pro** (OpenAI) | text→video, image→video | Clips detallados y dinámicos con audio | Premium |
| **Hunyuan Video, Mochi 1** | text→video | Modelos abiertos de alta calidad | Alternativas open |
| **Ovi** | text→video | Cobrado **por video** (precio plano), no por segundo | ~$0.20 por video |

**Cómo leer la tabla para empezar:**

- **text-to-video (t2v):** das solo un prompt de texto → te devuelve un clip. Útil para
  B-roll genérico ("calle de ciudad neón de noche, cámara en travelling").
- **image-to-video (i2v):** das una **imagen de partida** (p. ej. un still generado con
  Flux/SDXL, o un fotograma de marca) + prompt → la anima. Da **mucho más control** sobre
  composición y consistencia. Para un workflow de marca, i2v suele ser superior.
- **Duración:** la mayoría genera clips cortos (típicamente **5–10 s**). Para un short de
  30–60 s, generas varios clips y los unes en edición.

---

## 3. Costo aproximado

fal cobra **por unidad de salida**: la mayoría de los modelos de video son **por segundo
de video generado**, algunos son **por video** (precio plano) y otros (Seedance) por
**millón de tokens de video**, donde tokens = `(alto × ancho × FPS × duración) / 1024`.

> ⚠️ **Los precios cambian rápido.** Las cifras siguientes fueron verificadas el
> **2026-06-08** en las páginas oficiales de modelos / pricing de fal.ai. Confirma
> siempre en la página del modelo antes de presupuestar a escala.

### Tabla de precios (verificada 2026-06-08)

| Modelo | Precio | Costo de un clip de 5 s | Fuente |
|---|---|---|---|
| **Wan 2.5** | $0.05 / segundo | **~$0.25** | fal.ai/pricing |
| **Kling 2.5 Turbo Pro** | $0.07 / segundo ($0.35 los primeros 5 s, luego $0.07/s) | **~$0.35** | página del modelo |
| **MiniMax Hailuo 02 Standard (768p)** | ~$0.045 / segundo | **~$0.23** | búsqueda fal.ai |
| **MiniMax Hailuo 02 Pro (1080p)** | ~$0.08 / segundo | **~$0.40** | búsqueda fal.ai |
| **Seedance 1.0 Pro (1080p)** | ~$0.62 por video de 5 s a 1080p (o $2.5 / 1M tokens) | **~$0.62** | página del modelo |
| **Ovi** | $0.20 por **video** (precio plano) | **~$0.20** | fal.ai/pricing |
| **Veo 3 / 3.1** | $0.40 / segundo | **~$2.00** | fal.ai/pricing |

**Lecturas clave:**

- **Lo más barato para empezar:** **Wan 2.5** (~$0.25 / clip de 5 s) y **Hailuo 02
  Standard** (~$0.23). Excelentes para iterar B-roll sin quemar presupuesto.
- **Mejor calidad/precio "todoterreno":** **Kling 2.5 Turbo Pro** (~$0.35). Es el que yo
  recomendaría como default para un creador en solitario.
- **Premium (solo para el clip "hero"):** **Veo 3.1** (~$2 por 5 s). Reserva esto para el
  plano final de máxima calidad con audio nativo, no para B-roll de relleno.
- **Cobro justo:** solo pagas por generaciones exitosas; los errores del servidor y la
  espera en cola **no se cobran**.

> Nota de honestidad: las cifras de Hailuo 02 y algunos detalles de resolución provienen
> de resúmenes de búsqueda, no de una lectura directa de cada subpágina. Trátalas como
> **aproximadas (±)** y verifica en la página del endpoint exacto que vayas a usar.

---

## 4. Requisitos

Para empezar necesitas muy poco:

1. **Cuenta fal.ai** — registro en [fal.ai](https://fal.ai). Reportan **~$20 de créditos
   gratis** al registrarte (con email de empresa); confírmalo al crear la cuenta.
2. **API key** — se genera en el dashboard. Es lo único que necesita tu script.
3. **Billing (créditos prepago)** — compras créditos por adelantado; se descuentan por uso.
4. **Laptop con Python** — nada de GPU. Solo `pip install fal-client`.

**Límites:**

- **Concurrencia:** el número de trabajos simultáneos **escala con tu historial de
  compra** (cuanto más has gastado, más concurrencia). Para un creador en solitario esto
  rara vez es un problema.
- **Rate limits exactos:** fal no publica números duros fáciles de citar; en la práctica
  el límite efectivo es tu **concurrencia** + tu **saldo de créditos**. Si vas a hacer
  lotes grandes, usa la **cola (queue)** en vez de llamadas síncronas.

**¿Se puede llamar desde un script Python simple?** Sí. Ese es justamente el caso de uso
principal. Ver el ejemplo mínimo abajo.

---

## 5. Flujo para empezar (paso a paso)

### Paso 0 — Instalar el cliente

```bash
pip install fal-client
export FAL_KEY="tu-api-key-aqui"   # consíguela en el dashboard de fal.ai
```

### Paso 1 — Primer clip text-to-video

```python
import fal_client

def on_update(update):
    # imprime los logs de progreso mientras se genera
    if isinstance(update, fal_client.InProgress):
        for log in update.logs:
            print(log["message"])

result = fal_client.subscribe(
    "fal-ai/kling-video/v2.5-turbo/pro/text-to-video",
    arguments={
        "prompt": "B-roll cinematográfico: calle de ciudad con luces de neón "
                  "de noche, cámara en travelling lento, look filmico",
        "duration": "5",
        "aspect_ratio": "16:9",
    },
    with_logs=True,
    on_queue_update=on_update,
)

video_url = result["video"]["url"]
print("Video listo:", video_url)
```

`subscribe()` envía el trabajo a la cola de fal y **espera** hasta que termina,
devolviéndote un dict con la URL del `.mp4`.

### Paso 2 — Image-to-video (más control)

Sube una imagen de partida (un still de tu marca o uno generado con Flux) y anímala:

```python
import fal_client

# 1) sube la imagen local -> fal te devuelve una URL
image_url = fal_client.upload_file("./still_inicial.png")

# 2) anima esa imagen
result = fal_client.subscribe(
    "fal-ai/kling-video/v2.5-turbo/pro/image-to-video",
    arguments={
        "prompt": "la cámara hace un push-in suave, hojas que se mueven con el viento",
        "image_url": image_url,
        "duration": "5",
    },
)
print(result["video"]["url"])
```

### Paso 3 — Descargar el resultado

```python
import requests

url = result["video"]["url"]
with open("broll_001.mp4", "wb") as f:
    f.write(requests.get(url).content)
```

Eso es todo: signup → API key → t2v → i2v → descarga del `.mp4`.

> Para lotes grandes, en vez de `subscribe()` usa `fal_client.submit()` (encola y te da
> un `request_id` para hacer polling o recibir un webhook), así no bloqueas el proceso.

---

## 6. Cómo integrarlo al pipeline (digital-observatory)

`digital-observatory` ya **descubre noticias de IA** y **redacta posts** (incluidos
guiones de shorts). fal.ai encaja como **un paso opcional de "generación de B-roll"** al
final de la cadena de un short:

```
descubrir noticia → redactar guion (youtube_short) → [NUEVO] generar B-roll con fal
                                                    → revisión humana → editar/publicar
```

**Dónde encaja una llamada a fal, en concreto:**

- Cuando un guion de `youtube_short` ya está aprobado, extraer 4–8 "beats" visuales
  (frases descriptivas) y, por cada uno, llamar a fal para un clip de 5 s.
- Usar **image-to-video** cuando quieras consistencia de marca: parte de un still fijo
  (logo/escenario) y anímalo, en vez de t2v puro que varía mucho entre tomas.
- Guardar las URLs/`.mp4` junto al borrador del post para que el editor los ensamble.

**Costo aproximado por video producido:**

- Un short de ~45 s ≈ **8 clips de 5 s**.
- Con **Kling 2.5 Turbo Pro** (~$0.35/clip): **~$2.80 por short** (sin contar reintentos).
- Con **Wan 2.5** (~$0.25/clip): **~$2.00 por short**.
- Si reservas **Veo 3.1** solo para el plano "hero" (1 clip) y Wan para el resto:
  ~$2 + $0.20×7 ≈ **~$3.40 por short**. Presupuesta un **margen del 1.5–2×** por iteraciones.

**Human-in-the-loop (importante):**

- **No publiques automáticamente** clips generados. La IA de video aún produce artefactos
  (manos, texto, física rara) y riesgos de marca/legales (parecidos no deseados, logos).
- Inserta un **gate de revisión humana** entre "generación" y "publicación": el pipeline
  deja los `.mp4` como *propuesta* en el borrador (igual que ya hace con el inbox de
  posts), y una persona aprueba/regenera antes de montar.
- Loggea **prompt, modelo, costo y request_id** por clip para trazabilidad y control de
  gasto.

---

## 7. Alternativas / cuándo NO usar fal

- **Ir directo al proveedor del modelo.** Veo (Google Gemini API / Vertex), Kling
  (API oficial de Kuaishou), Hailuo (MiniMax), Runway, Luma/Dream Machine tienen sus
  propias APIs. Úsalas si: necesitas **features exclusivas** que fal no expone, quieres
  un **SLA/contrato** directo, o el proveedor te da **mejor precio a tu volumen**. La
  contra: pierdes el "una sola API para todos" y tienes que integrar cada uno por separado.
- **Local / open-source (Wan, LTX, Hunyuan, Mochi).** Si más adelante consigues una GPU
  potente (o alquilas una), correr estos modelos localmente puede salir más barato a
  **volumen muy alto** y te da privacidad total. Pero contradice la premisa actual
  (**solo laptop, sin GPU**) y exige mantenimiento. Para un creador en solitario, **no
  vale la pena al principio**.
- **Herramientas "no-code" (Runway, Pika, Kling web, CapCut).** Si **no** quieres
  automatizar y solo generas clips a mano de vez en cuando, una UE web es más simple que
  un script. fal brilla cuando quieres **automatización dentro de un pipeline**, que es
  exactamente el caso de digital-observatory.

**Resumen de la decisión:** para este proyecto (laptop + nube, automatización, varios
modelos, gasto controlado) **fal.ai es la opción correcta** para empezar. Cambia de
estrategia solo si el volumen crece mucho o necesitas algo que fal no ofrece.

---

## Fuentes

Todas verificadas el **2026-06-08**:

- fal.ai — Pricing (modelos de video, por segundo / por video): <https://fal.ai/pricing>
- fal.ai — Docs / Pricing (modelo de créditos prepago, no se cobran errores ni cola, concurrencia): <https://fal.ai/docs/documentation/model-apis/pricing>
- fal.ai — Quickstart (instalar `fal-client`, `FAL_KEY`, `subscribe`): <https://fal.ai/docs/model-apis/quickstart>
- fal.ai — Referencia del cliente Python `fal_client` (subscribe, submit, upload_file, async): <https://fal.ai/docs/reference/client-libraries/python/fal_client>
- fal.ai — Kling 2.5 Turbo Pro (image-to-video), precio $0.35 por 5 s + $0.07/s: <https://fal.ai/models/fal-ai/kling-video/v2.5-turbo/pro/image-to-video>
- fal.ai — Seedance 1.0 Pro (text-to-video), ~$0.62 a 1080p 5 s / $2.5 por 1M tokens: <https://fal.ai/models/fal-ai/bytedance/seedance/v1/pro/text-to-video>
- fal.ai — MiniMax Hailuo 02 Pro (text-to-video): <https://fal.ai/models/fal-ai/minimax/hailuo-02/pro/text-to-video>
- fal.ai — MiniMax Hailuo 02 Standard (image-to-video): <https://fal.ai/models/fal-ai/minimax/hailuo-02/standard/image-to-video>
- fal.ai — Explorar modelos (text-to-video / image-to-video): <https://fal.ai/explore?categories=image-to-video&categories=text-to-video>
- fal.ai — APIs de video para desarrolladores: <https://fal.ai/video>
- fal.ai — 10 mejores generadores de video IA (2026): <https://fal.ai/learn/tools/ai-video-generators>
- PyPI — `fal-client` (cliente oficial Python): <https://pypi.org/project/fal-client/>
- DevTk.AI — AI Video API Pricing 2026 (Seedance vs Sora vs Kling vs Veo, contexto de precios): <https://devtk.ai/en/blog/ai-video-generation-pricing-2026/>

> **Aviso de incertidumbre:** los precios de Hailuo 02 y algunos detalles de resolución
> provienen de resúmenes de búsqueda, no de lectura directa de cada subpágina. Antes de
> presupuestar a escala, abre la página del **endpoint exacto** que vayas a usar en
> fal.ai y confirma el precio vigente, ya que el catálogo cambia con frecuencia.
