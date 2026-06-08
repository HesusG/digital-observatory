# Guía práctica de video: tu equipo para YouTube y Shorts

> Guía para creador principiante, escrita para **tu equipo concreto**.
> Fecha de elaboración: **2026-06-08**. Specs verificados con búsqueda web (ver sección **Fuentes** al final).
> Objetivo: que sepas exactamente **qué dispositivo y qué lente usar en cada toma**, con ajustes que funcionen sin que tengas que pelearte con menús.

---

## 0. Tu equipo de un vistazo

| Equipo | Qué es | Nota importante |
|---|---|---|
| **Fujifilm X-T30 II** | Cámara APS-C, recorte **1.5x** | Tu cámara principal de video |
| Lente **35mm f1.7** | Prime económico (de tercero, p. ej. Viltrox/TTArtisan/7Artisans) | Equivale a **~52mm** |
| Lente **24mm f2** | Prime gran angular ligero | Equivale a **~36mm** |
| **Zoom de kit** | *Probablemente* Fujinon **XC 15-45mm f3.5-5.6 OIS PZ** | Ver nota de incertidumbre abajo |
| **50mm f1.4 Nikon** | Lente manual Nikon con **adaptador** | **Solo enfoque manual, sin autofoco**. Equivale a **~75mm** |
| **Tablets Huawei** (varias) | Pantallas grandes | Teleprompter / monitor / guion / edición |
| **2× Huawei Pura 70** | Teléfonos con cámara muy buena | B-roll, segundo ángulo, verticales |
| **1× iPhone 16** | Teléfono cámara | Verticales, B-roll, color consistente |

> **Sobre el lente de kit (incertidumbre honesta):** el kit estándar del X-T30 II es el **Fujinon XC 15-45mm f3.5-5.6 OIS PZ** (rango equivalente **~23–69mm**, con estabilización óptica OIS y zoom motorizado "power zoom"). **Es muy probable que sea el tuyo, pero no está 100% confirmado.** Algunos kits llevaron el **XF 18-55mm f2.8-4 OIS** (mejor lente, más luminoso). **Cómo confirmarlo en 5 segundos:** mira el texto impreso en el anillo frontal del lente: dirá literalmente `XC15-45mmF3.5-5.6 OIS PZ` o `XF18-55mmF2.8-4 R LM OIS`. Toda esta guía asume el **15-45**, pero si resulta ser el 18-55, ese lente es **mejor** para casi todo (más luminoso) y puedes usarlo en lugar del 24mm en varios casos.

---

## 1. La Fujifilm X-T30 II para video

### 1.1 Resoluciones y framerates reales (verificados)

| Modo | Resoluciones | Framerates | Bitrate | Notas |
|---|---|---|---|---|
| **4K** | DCI 4K (4096×2160) y UHD 4K (3840×2160) | **30p / 25p / 24p / 23.98p** (NO hay 4K 60p) | 200 o 100 Mbps | Tu mejor calidad para YouTube |
| **Full HD 1080p** | 17:9 y 16:9 | **60p / 50p / 30p / 25p / 24p** | 200 / 100 / 50 Mbps | Usa 60p para movimiento suave o slow-mo ligero |
| **Cámara lenta (high-speed)** | Full HD | **240p / 200p / 120p / 100p** | — | **Sin audio** y con **recorte adicional**; 240/200p limitado a ~3 min |

**Traducción práctica:**
- **No existe 4K a 60fps** en esta cámara. Si quieres movimiento fluido o slow-mo suave, graba **1080p 60p**.
- Para slow-mo dramático (10x), usa **1080p 240p**, pero recuerda: **no graba sonido** y recorta más la imagen (acércate o usa gran angular).
- Para video normal de YouTube, **4K 24p o 25p** se ve cinematográfico; **30p** es más "estándar/limpio".

### 1.2 Límites de grabación y sobrecalentamiento

- **Límite por clip: ~30 minutos** tanto en 4K como en 1080p (verificado en specs oficiales). Para un video largo de "talking head", esto significa **cortar y reanudar** cada media hora (o partir en tomas, que es lo normal).
- **Sobrecalentamiento:** es un cuerpo compacto sin ventilación grande. En **4K continuo y ambiente caluroso** puede calentarse en grabaciones largas. Mitiga así:
  - Abre la pantalla abatible (ayuda a disipar calor).
  - Para sesiones muy largas, considera grabar en **1080p** (calienta menos).
  - Ajusta **AUTO POWER OFF TEMP.** a **HIGH** en el menú si quieres maximizar tiempo antes de que se apague por calor.
- **Batería:** la NP-W126S dura poco en video (~40-50 min reales). **Compra 1-2 baterías extra** o usa alimentación USB-C / dummy battery para sesiones de escritorio.

### 1.3 Perfiles: Eterna vs F-Log (¿cuál usar?)

| Perfil | Qué hace | Cuándo usarlo |
|---|---|---|
| **Eterna** (Film Simulation) | Look cinematográfico, contraste suave, colores agradables **listos para subir** | **Recomendado para ti como principiante.** Grabas y subes casi sin editar color |
| **Provia / Standard** | Look neutro fiel | Si quieres algo limpio y versátil |
| **F-Log** | Imagen **plana** (desaturada, baja en contraste) para **corregir color (grading) en edición** | Solo si vas a editar color. **Importante:** el X-T30 II **sí graba F-Log internamente, pero solo en 8-bit 4:2:0**. El **10-bit 4:2:2 es únicamente por HDMI** a una grabadora externa (que no tienes) |

> **Recomendación honesta para empezar:** usa **Eterna** y olvídate de F-Log por ahora. F-Log en 8-bit interno se "rompe" (banding, ruido) si lo fuerzas en edición, y como principiante el grading te quitará tiempo sin gran beneficio. Pasa a F-Log cuando domines la edición de color.

### 1.4 Ajustes recomendados

**A) Talking-head para YouTube (tú hablando a cámara):**

| Ajuste | Valor | Por qué |
|---|---|---|
| Resolución/FPS | **4K 25p o 30p** | Calidad alta, archivo manejable |
| Bitrate | 200 Mbps (o 100 si te falta espacio) | Más detalle |
| Film Simulation | **Eterna** | Look bonito sin editar |
| Obturador (shutter) | **1/50** (con 25p) o **1/60** (con 30p) | Regla "doble del framerate" = movimiento natural |
| ISO | **Auto, tope 3200** | Limita el ruido |
| Balance de blancos | **Manual** (mide con tu luz) o fijo a tu ambiente | Evita cambios de color en cámara |
| Autofoco | **AF-C + Face/Eye Detection ON** | Mantiene tu cara enfocada |
| F-Log | **OFF** | (ver arriba) |
| Estabilización | El X-T30 II **no tiene IBIS** (estabilización en cuerpo); depende del OIS del lente | Por eso para talking-head fijo: **usa trípode** |

**B) B-roll (tomas de apoyo: productos, detalles, ambiente):**

| Ajuste | Valor | Por qué |
|---|---|---|
| Resolución/FPS | **4K 24p** (look cine) o **1080p 60p** si quieres ralentizar | 60p te deja hacer slow-mo a 24/30p en edición |
| Shutter | Doble del FPS (24p→1/48≈1/50; 60p→1/120 ó 1/125) | Movimiento natural |
| Apertura | **Abierta** (f1.7 / f2 / f1.4) para fondo desenfocado | B-roll bonito = poca profundidad de campo |
| ISO | Auto tope 3200 | — |
| Film Simulation | Eterna (consistente con el A) | Que combine con tu talking-head |

### 1.5 Micrófono: ¿entrada disponible?

- **Sí hay entrada de micrófono, PERO es un conector de 2.5mm** (no el estándar 3.5mm), compartido para mic y disparador remoto. Verificado en specs oficiales.
- **No hay salida de auriculares** (no puedes monitorear audio por cable desde la cámara).
- **Recomendación práctica:**
  1. Para conectar un mic estándar de 3.5mm necesitas un **adaptador 3.5mm hembra → 2.5mm macho** (cuesta ~3-8 USD; JJC lo fabrica específicamente para Fuji).
  2. **Mejor aún para un creador solo:** evita el problema usando un **micrófono de solapa inalámbrico que graba en su propia unidad** (tipo DJI Mic Mini / Hollyland Lark M2). Grabas audio limpio aparte y lo sincronizas en edición, **sin depender de la entrada de 2.5mm ni de la falta de monitoreo**. Esto es lo que recomiendo (ver sección 5).

---

## 2. Qué lente para qué toma (con el recorte 1.5x)

Recuerda: en APS-C todo se "alarga" 1.5x. Un 35mm **se comporta como ~52mm**.

| Lente (real) | Equivalente (1.5x) | Tipo de toma ideal | Por qué |
|---|---|---|---|
| **24mm f2** | ~36mm | **Talking-head a brazo / espacio pequeño**, vlog, mostrar entorno | Suficientemente amplio para grabarte cerca sin deformar mucho la cara; cabes tú + algo de fondo |
| **35mm f1.7** | ~52mm | **Talking-head clásico sentado**, entrevistas, B-roll general | El "ojo humano". Cara natural, fondo agradablemente desenfocado a f1.7. **Tu lente más versátil** |
| **Zoom kit 15-45mm** | ~23-69mm | **Flexibilidad / B-roll variado**, cuando no quieres cambiar de lente, planos abiertos | Tiene **OIS (estabilización)**, útil para tomas a mano. Menos luminoso (f3.5-5.6) → fondo menos desenfocado |
| **50mm f1.4 Nikon (manual)** | ~75mm | **Retrato, detalle, B-roll de producto con mucho desenfoque** | Comprime y aísla el sujeto; el f1.4 da un fondo cremoso precioso. **Solo enfoque manual** |

### 2.1 El 50mm Nikon manual: cómo usarlo y cuándo conviene

Es un lente sin chip: **no hay autofoco ni control de apertura desde la cámara** (cambias la apertura con el anillo físico del lente). Pese a eso, es una joya para ciertas tomas.

**Cómo enfocar bien sin autofoco:**
1. Activa **FOCUS PEAKING** (resaltado de bordes) en el menú de la Fuji: marca con color los bordes que están en foco.
2. Usa **MF Assist → Focus Peak Highlight** (rojo o blanco, intenso).
3. Para precisión extra, presiona el dial para hacer **zoom de enfoque** y ajusta el anillo hasta que el detalle esté nítido.
4. Pon la cámara en modo de enfoque **MF** (la palanca lateral).

**Cuándo conviene pese a ser manual:**
- **B-roll de producto / detalle:** el sujeto no se mueve, tú no te mueves → enfocas una vez y listo. Aquí el manual **no es problema** y ganas un desenfoque y nitidez superiores.
- **Retrato estático tuyo o de alguien** sentado quieto.
- **Tomas "cinematográficas" planeadas** donde controlas todo.

**Cuándo EVITARLO:**
- Talking-head donde te mueves o te acercas/alejas (perderás foco).
- Cualquier cosa rápida o espontánea (vlog, acción). Para eso usa 35mm o 24mm con autofoco.

---

## 3. Aprovechar tablets y teléfonos

### 3.1 Tablets Huawei (varias)

| Uso | Cómo | Nota |
|---|---|---|
| **Teleprompter** | App de teleprompter (ej. "Teleprompter for Video", "BIGVU", "PromptSmart"). Pones la tablet **debajo o al lado del lente** y lees tu guion mientras te grabas | Lo más útil: elimina los "ehh" y los olvidos. Para mirar a cámara, ideal un soporte que ponga la tablet justo frente al lente (espejo/beam-splitter) o simplemente debajo del lente |
| **Segunda pantalla para guion / notas** | Tablet al lado con bullets de lo que vas a decir | Más barato y simple que un teleprompter real |
| **Monitor externo** | El X-T30 II saca señal por **micro-HDMI**; con una **capturadora HDMI→USB** podrías llevar imagen a la tablet, pero es complicado en Android | **Más práctico:** usa la app **FUJIFILM XApp** vía Wi-Fi/Bluetooth para ver una vista en vivo en la tablet (con algo de retardo). Útil para encuadrarte solo |
| **Editar Shorts sobre la marcha** | Apps como **CapCut** en la tablet para cortar verticales rápido | La pantalla grande ayuda; exporta y sube |

### 3.2 Pura 70 / iPhone 16 como cámaras

Verificado: el **Huawei Pura 70 graba hasta 4K 60fps** (16:9; en 21:9 baja a Full HD). El **iPhone 16 graba 4K hasta 60fps en Dolby Vision**. Ambos son excelentes cámaras secundarias.

| Uso | Mejor teléfono | Cómo |
|---|---|---|
| **Shorts verticales** | iPhone 16 o Pura 70 | Graba en **9:16, 4K 30 o 60fps**. El teléfono es **más cómodo que la Fuji para vertical** |
| **B-roll** | Pura 70 (cámara potente) | Modo Pro, fija ISO/shutter, 4K |
| **Segundo ángulo (multicámara)** | El segundo Pura 70 o el iPhone | Coloca un teléfono en otro encuadre mientras la Fuji hace el principal |
| **Producto / detalle** | Pura 70 (tiene macro/teleobjetivo) | Buena para close-ups si no quieres cambiar lente en la Fuji |
| **Time-lapse / hyperlapse** | Cualquiera | Modo nativo de time-lapse de ambos teléfonos |

**Consistencia de color entre teléfono y la Fuji (importante):**
- En el iPhone, **desactiva el HDR/Dolby Vision** si tu edición no es HDR: Ajustes → Cámara → Grabar vídeo → desactiva **"HDR Video"** (graba en SDR). Si no, los clips se ven raros junto a los de la Fuji.
- Bloquea **balance de blancos y exposición** en el teléfono (mantén presionado el AE/AF lock) para que no cambien de toma a toma.
- Usa el **mismo balance de blancos numérico** en ambos cuando puedas (ej. 5200K).
- En edición (CapCut/DaVinci/Premiere), iguala los clips: ajusta temperatura, contraste y saturación del teléfono para que **coincidan con el look Eterna** de la Fuji. Un LUT suave o un ajuste manual de 30 segundos basta.
- Graba todos los dispositivos al **mismo framerate** (ej. todo a 25p o todo a 30p) para evitar problemas al mezclar.

### 3.3 Setup multi-dispositivo sensato para una persona sola

```
        [Tablet Huawei = TELEPROMPTER / guion]
                     |  (debajo del lente)
   Luz  →   [Fujifilm X-T30 II + 35mm]  ← cámara principal (trípode)
                     |
   [Pura 70 #1] = segundo ángulo lateral (trípode/mini-soporte)
   [iPhone 16]  = vertical para Shorts (grabando en paralelo)
   [DJI/Lark Mic] = audio limpio en su propia grabadora
```

**Filosofía:** una sola persona no puede vigilar 4 pantallas. Mantén **un dispositivo principal** (la Fuji) y deja los demás grabando "set and forget". Sincroniza todo en edición con una **palmada inicial** (claqueta casera) para alinear audio/video.

---

## 4. Flujo de grabación mínimo

### (a) Video largo "talking head" para YouTube

1. **Cámara:** Fujifilm X-T30 II en **trípode**.
2. **Lente:** **35mm f1.7** (look natural, fondo desenfocado) — o **24mm f2** si el espacio es chico.
3. **Ajustes:** 4K 25p, Eterna, shutter 1/50, ISO auto (tope 3200), AF-C + detección de cara, f2-2.8.
4. **Audio:** micrófono inalámbrico de solapa grabando aparte (o lavalier a la entrada de 2.5mm con adaptador).
5. **Teleprompter:** tablet Huawei debajo del lente con tu guion.
6. **Luz:** una luz suave frente a ti (ventana o panel LED).
7. **Recuerda:** corta cada ~30 min (límite de clip). Sincroniza audio en edición con una palmada al empezar.

### (b) Short vertical

1. **Cámara:** **iPhone 16** o **Pura 70** (más práctico vertical que la Fuji).
2. **Orientación:** **9:16**, 4K 30fps, HDR desactivado (para que combine si lo mezclas con clips de la Fuji).
3. **Audio:** el mismo mic inalámbrico, o el micrófono del teléfono si el entorno es silencioso.
4. **Edición:** CapCut en la tablet o el teléfono → subtítulos automáticos → exportar.
5. *(Opcional avanzado):* graba el Short con la **Fuji + 35mm** recortando a 9:16 en edición, si quieres el desenfoque de fondo de la cámara grande. Pero para velocidad, el teléfono gana.

---

## 5. Qué te falta y próximas compras de bajo costo (por impacto/costo)

Tienes **mucho cuerpo y lentes** ya; lo que más te limita es **audio, estabilidad y luz**. Prioridad de mayor a menor retorno:

| # | Compra | Costo aprox. | Impacto | Por qué es prioridad |
|---|---|---|---|---|
| **1** | **Micrófono inalámbrico de solapa** (DJI Mic Mini / Hollyland Lark M2) | ~$80-150 USD | **ALTÍSIMO** | El audio es lo que más diferencia "amateur" de "pro". Grabar aparte esquiva la entrada rara de 2.5mm y la falta de monitoreo del X-T30 II. **Cómprala primero.** |
| **2** | **Trípode decente** (o trípode + cabezal fluido) | ~$30-70 USD | Alto | El X-T30 II **no tiene IBIS**; un trípode da tomas estables de talking-head y B-roll. Imprescindible para grabarte solo |
| **3** | **Una luz LED suave** (panel + softbox/difusor, o un aro) | ~$40-80 USD | Alto | Buena luz mejora cualquier cámara. Una luz frontal suave + algo de ambiente |
| **4** | **Baterías NP-W126S extra (2×) + cargador** | ~$25-40 USD | Medio | La batería rinde poco en video; sin esto, te quedas a media sesión |
| **5** | **Adaptador de mic 3.5mm→2.5mm** (JJC) | ~$5-8 USD | Bajo-medio | Solo si quieres usar un mic cableado en la entrada de la Fuji |
| **6** | **Tarjeta SD rápida U3/V30, 128GB+** | ~$20-30 USD | Medio | El 4K a 200 Mbps necesita tarjeta rápida; evita cortes de grabación |
| **7** | **Mini-soportes / clamps para teléfonos** | ~$15-25 USD | Bajo | Para fijar los Pura 70 / iPhone como segundos ángulos |

**Si solo compras UNA cosa: el micrófono inalámbrico (#1).** Es el mayor salto de calidad por dólar para video hablado.

---

## Fuentes

Consultadas el **2026-06-08**:

- Fujifilm — Especificaciones oficiales X-T30 II (4K/1080p/high-speed, límite ~30 min, conector mic 2.5mm): https://www.fujifilm-x.com/global/products/cameras/x-t30-ii/specifications/
- Fujifilm DSC — Manual técnico / especificaciones X-T30 II: https://fujifilm-dsc.com/en/manual/x-t30-2/technical_notes/spec/
- Photography Blog — Reseña X-T30 II (4K 30p, 240fps slow-mo, límite 4K): https://www.photographyblog.com/reviews/fujifilm_x_t30_ii_review
- Videomaker — X-T30 video (8-bit 4:2:0 interno, 10-bit 4:2:2 solo por HDMI; F-Log): https://www.videomaker.com/reviews/cameras/fujifilm-x-t30-review-great-for-video-not-perfect/
- Slashcam — F-Log y 10-bit 4:2:2 vía HDMI en X-T30: https://www.slashcam.com/news/single/FUJI-X-T30-offers-F-log-and-10-bit-4-2-2-via-HDMI-14899.html
- Fujifilm — Guía F-Log / Eterna (Movie Setting): https://fujifilm-dsc.com/en/manual/x-t30-2/menu_shooting/movie_setting/
- Fujifilm — Using an External Microphone: https://www.fujifilm-x.com/en-gb/learning-centre/using-an-external-microphone/
- JJC — Adaptador mic 3.5mm→2.5mm para Fujifilm X-T30 II (Amazon): https://www.amazon.com/JJC-Microphone-Adapter-Fujifilm-HS50EXR/dp/B071XHT9F7
- B&H Photo — Kit X-T30 II con XC 15-45mm f3.5-5.6 (lente de kit, equiv. 23-69mm): https://www.bhphotovideo.com/c/product/1662379-REG/fujifilm_16759768_x_t30_ii_mirrorless_digital.html
- GSMArena — Reseña Huawei Pura 70 Ultra (video hasta 4K 60fps): https://www.gsmarena.com/huawei_pura_70_ultra-review-2700.php
- Apple Support — iPhone 16 specs (4K hasta 60fps Dolby Vision): https://support.apple.com/en-bw/121031

> **Notas de incertidumbre:** (1) El lente de kit se asume **XC 15-45mm** pero no está confirmado; verifica el texto impreso en el lente. (2) Las cifras de sobrecalentamiento exactas del X-T30 II no están publicadas oficialmente; lo descrito son recomendaciones de mitigación. (3) Specs del Pura 70 base pueden variar ligeramente respecto al Pura 70 Ultra reseñado; el tope de 4K 60fps aplica a la gama.
