# ASPLOT CENTER — Sprint 3: Caché y Portafolio Interactivo

> **PB-06 (8) + PB-07 (3) + PB-08 (8) + PB-09 (5) = 24 puntos**
> Duración: 2 semanas · Equipo: 2 desarrolladores
> Objetivo: reducir la carga del servidor con caché y compresión, y abrir
> el sistema al público con un portafolio filtrable y galería HD con zoom.

---

## PB-06 — Sistema de caché (8 pts)

**`cachear.py`** — módulo propio, sin dependencias externas:

- Caché en memoria con TTL, thread-safe (`threading.RLock`).
- Decorador `@cachear_ruta(ttl=…)` para vistas Flask.
- **Clave por usuario** (`ruta:{usuario_id}:…`): imprescindible porque el
  dashboard sirve vistas distintas según rol; sin esto se filtrarían datos
  entre sesiones. Solo cachea respuestas HTTP 200 (no redirecciones).
- **Invalidación automática**: enganche al evento `after_commit` de
  SQLAlchemy → cualquier INSERT/UPDATE/DELETE invalida las vistas de
  dashboard, reportes y portafolio. No depende de recordarlo en cada ruta.

Aplicado a: `/dashboard` (60 s), `/reportes` (120 s), `/portafolio` (300 s).

**Limitación documentada:** cada proceso gunicorn mantiene su propia caché;
para despliegues multi-instancia se migraría a Redis cambiando el backend
del módulo.

## PB-07 — Compresión y optimización de recursos (3 pts)

| Acción | Resultado |
|---|---|
| Middleware gzip WSGI (`CompresionGzip`), umbral 512 B, solo texto y si el cliente lo pide | Landing `/`: **13.017 → 3.153 bytes (−76%)** |
| Cabecera `Cache-Control: public, max-age=604800` en `/static` (imágenes subidas: `no-cache`) | Estáticos cacheados 7 días en el navegador |
| `optimizar_estaticos.py` (Pillow) + versión WebP | `mapa_ubicacion.webp`: **529 KB → 101 KB (−81%)** |
| `<picture>` con fallback a PNG en la landing + `loading="lazy"` | Los navegadores modernos sirven el WebP |

## PB-08 — Portafolio interactivo público (8 pts)

- Nueva ruta **`GET /portafolio`** (sin login), enlazada en navbar y footer
  de la landing.
- Muestra solo estados comerciales: `aprobado`, `en_progreso`, `ejecutado`
  (oculta el embudo interno: solicitado/cotizado/rechazado).
- **Filtros**: tipo de servicio + rango de presupuesto (min/max), con
  tolerancia a valores no numéricos.
- Aprovecha los índices del Sprint 2: `ix_proyectos_estado_tipo`,
  `ix_proyectos_tipo_servicio` e `ix_proyectos_presupuesto`.
- `selectinload` de cliente y planos (sin N+1).

## PB-09 — Galería HD con zoom (5 pts)

- **`static/js/zoom.js`** — visor vanilla JS, sin librerías externas:
  zoom 100–500% (rueda/botones/teclado), arrastre con ratón y táctil
  (pinch-zoom en móvil), pantalla completa, atajos `+ − 0 ←→ Esc`.
- **`static/css/zoom.css`** — overlay compartido.
- Integrado en:
  - `portafolio.html` — miniaturas de planos de cada proyecto.
  - `detalle_plano.html` — vista previa ampliable (solo imágenes
    PNG/JPG/JPEG/WEBP; los PDF siguen con "Ver Plano").

## Evidencia de rendimiento (`perf_test.py`, 5 iteraciones)

| Ruta | Antes (Sprint 2) | Después (Sprint 3) | Queries |
|---|---|---|---|
| `/dashboard` | 31.6 ms · 6 SQL | **12.6 ms · 2 SQL** | caché + consolidación |
| `/reportes` | 3.5 ms · 1 SQL | 2.5 ms · 1 SQL | caché 120 s |
| resto de rutas | — | 6.6–14.0 ms | sin regresiones |

## Verificación

Prueba integral (26 aserciones) ejecutada antes del commit:
portafolio público, filtros, ocultación de estados internos, assets de
zoom, detalle de plano con visor, cabeceras de caché, gzip y regresión de
las 8 rutas principales. **Todas OK.**

## Criterios de aceptación

- [x] Caché con TTL y invalidación automática en escrituras
- [x] Identidad de usuario en la clave de caché (sin fugas entre sesiones)
- [x] gzip activo en respuestas de texto (payload −76% en landing)
- [x] Estáticos con `Cache-Control` de 7 días
- [x] Imágenes optimizadas + WebP (−81% en el mapa)
- [x] Portafolio público filtrable por tipo de servicio y presupuesto
- [x] Zoom + arrastre + fullscreen funcionando en portafolio y detalle de plano
- [x] Sin regresiones en rutas existentes
