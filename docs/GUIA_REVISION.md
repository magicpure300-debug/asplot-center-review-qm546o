# ASPLOT CENTER — Guía de revisión académica

> Repositorio de solo lectura (temporal). Aquí puedes ver el avance real del
> proyecto a través de los commits, la documentación de cada sprint y ejecutar
> la aplicación en local si lo deseas.

---

## 1. Línea de tiempo del proyecto

Cada sprint corresponde a **un commit** con su mensaje descriptivo.
Historial completo: [commits de `develop`](https://github.com/magicpure300-debug/asplot-center-review-qm546o/commits/develop)

| Sprint | Backlog | Commit | Contenido |
|---|---|---|---|
| Sprint 1 | PB-01, PB-02, PB-03 | `0aba7fe` | Migración SQLite → MySQL: detección de motor por variables de entorno (`config.py`), scripts `migrate_sqlite_to_mysql.py`, `importar_a_mysql.py`, `validar_migracion.py`, documentación `docs/MIGRACION_MYSQL.md`, `.env.example`. Se conserva SQLite como respaldo (patrón Strangler Fig). |
| Sprint 2 | PB-04, PB-05 | `7b9f56a` | 24 índices de rendimiento en `models.py` (aplicables con `aplicar_indices.py`, idempotente y compatible SQLite/MySQL). Eliminación del patrón N+1 con `selectinload` en 6 listados. Conteos consolidados (UNION ALL / GROUP BY). Paginación en la búsqueda de planos. Herramienta de medición `perf_test.py`. |
| Sprint 3 | PB-06, PB-07, PB-08, PB-09 | `9a39941` | Caché en memoria con TTL y clave por usuario (`cachear.py`) con invalidación automática tras cada escritura. Compresión gzip y cabeceras `Cache-Control`. Optimización de imágenes con Pillow + WebP. Portafolio público con filtros por tipo de servicio y presupuesto. Visor de imágenes HD con zoom y arrastre (`zoom.js`). |
| Sprint 4 | PB-14, PB-15 | `ed61abe` | Solicitud de servicio online **sin cuenta** (`/solicitud`) con reutilización de cliente por email, honeypot y límite por IP; bandeja `/solicitudes` y contador en dashboard. Ficha de cliente 360° (`/clientes/<id>`) con historial, totales facturado/pagado/pendiente, búsqueda por teléfono, paginación e integridad al eliminar. Planificación SDD en `specs/004-solicitudes-clientes/` y detalle en `docs/SPRINT_4.md`. |
| Sprint 5 | PB-10 | `2c21702` | Cotización automática (Fase 2, v1 determinista): botón «Calcular automáticamente» en el formulario de cotización; área de impresión de PDF (`pypdf`) y DXF (lector de `$EXTMIN/$EXTMAX`), precio con desglose (área × tarifa + insumos + margen), archivo del proyecto con respaldo al adjunto de la solicitud. Sin cambios de esquema ni servicios externos. Detalle en `docs/SPRINT_5.md` y `specs/005-cotizacion-automatica/`. |
| Sprint 6 | PB-11, PB-13 | `f2d13c4` | Inventario predictivo y calidad de planos (Fase 2): panel de reabastecimiento con velocidad de consumo real, punto de reorden, días restantes, compra sugerida y silencio persistente; checklist de calidad del plano (formato real, DPI sin Pillow, tamaño de página) que informa sin bloquear. Detalle en `docs/SPRINT_6.md` y `specs/006-inventario-calidad/`. |
| Rediseño | — | `244be29` | Identidad visual «blueprint»: design tokens, sidebar agrupado por flujos con badges, breadcrumb, dashboard admin accionable, línea de estado del cliente, landing/login renovados, tablas y formularios consistentes y menú móvil. Solo presentación, sin cambios de lógica. Detalle en `docs/DISENO.md` y `specs/007-rediseno-blueprint/`. |
| Higiene | — | `1dd63e5`, `eebb640`, `15e8049`, `12ed757` | Corrección de credenciales en la documentación y sincronización de ramas (`main` = producción, `develop` = desarrollo). |

## 2. Documentos de evidencia

- [`docs/SPRINT_2.md`](../docs/SPRINT_2.md) — métricas antes/después por ruta y criterios de aceptación.
- [`docs/SPRINT_3.md`](../docs/SPRINT_3.md) — resultados de compresión, diseño de la caché y verificación (26 aserciones).
- [`docs/SPRINT_4.md`](../docs/SPRINT_4.md) — solicitudes online, ficha de cliente, decisiones y verificación (29 comprobaciones).
- [`docs/SPRINT_5.md`](../docs/SPRINT_5.md) — cotización automática (PB-10), fórmula, decisiones y verificación (26 comprobaciones).
- [`docs/SPRINT_6.md`](../docs/SPRINT_6.md) — inventario predictivo y calidad de planos (PB-11/PB-13), verificación (31 comprobaciones).
- [`docs/DISENO.md`](../docs/DISENO.md) — sistema de diseño «blueprint», componentes y navegación.
- [`specs/004-solicitudes-clientes/`](../specs/004-solicitudes-clientes/) — especificación, plan técnico y tareas del Sprint 4 (SDD).
- [`specs/005-cotizacion-automatica/`](../specs/005-cotizacion-automatica/) — especificación, plan técnico y tareas del Sprint 5 (SDD).
- [`specs/006-inventario-calidad/`](../specs/006-inventario-calidad/) — especificación, plan técnico y tareas del Sprint 6 (SDD).
- [`specs/007-rediseno-blueprint/`](../specs/007-rediseno-blueprint/) — especificación, plan técnico y tareas del rediseño (SDD).
- [`docs/MIGRACION_MYSQL.md`](../docs/MIGRACION_MYSQL.md) — arquitectura y pasos de la migración a MySQL.

## 3. Ejecutar la aplicación en local

Requisitos: Python 3.8+ y `pip`.

```bash
git clone https://github.com/magicpure300-debug/asplot-center-review-qm546o.git
cd asplot-center-review-qm546o
pip install -r requirements.txt
python app.py
```

- La aplicación arranca sobre **SQLite** automáticamente (sin configuración extra).
- Navegar a `http://localhost:5000`
- Credenciales iniciales creadas en el primer arranque: `admin@asplot.com` / `admin123`
- **Portafolio público** (sin login): `http://localhost:5000/portafolio` — filtros por tipo de servicio y rango de presupuesto; al hacer clic en una miniatura se abre el visor de zoom.

> Nota: para ejecutarla sobre MySQL se usan las variables `MYSQL_HOST`,
> `MYSQL_USER`, `MYSQL_PASSWORD` y `FLASK_CONFIG=mysql` (ver `docs/MIGRACION_MYSQL.md`).

## 4. Mapa de funcionalidades principales

| Ruta | Qué muestra |
|---|---|
| `/` | Landing page pública (con WebP optimizado y gzip) |
| `/portafolio` | Portafolio interactivo público con filtros y zoom |
| `/dashboard` | KPIs (cliente admin) con caché de 60 s |
| `/clientes`, `/proyectos`, `/planos`, `/inventario`, `/facturas` | Módulos de gestión (requieren login) |
| `/reportes` | Generación de reportes PDF |
| `/planos/buscar` | Búsqueda avanzada paginada |

---

**Repositorio principal (privado):** `magicpure300-debug/asplot-center` — rama de trabajo `develop`; `main` se reserva para la versión desplegada en campo.
