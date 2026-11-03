# Plan técnico 007 — Rediseño visual «blueprint»

> **Spec:** `specs/007-rediseno-blueprint/spec.md` (pendiente de aprobación)
> **Estrategia:** tokens y overrides en `style.css` + cambios puntuales en
> `layout.html`, `dashboard*.html`, `landing.html/css` y `login.html`.
> La lógica solo recibe conteos para badges y la tarjeta de riesgo.

---

## 1. Design system

### 1.1 Paleta (CSS variables)

| Token | Valor | Uso |
|---|---|---|
| `--primary` | `#1D4ED8` | acciones principales, enlaces, foco |
| `--primary-dark` | `#16357A` | sidebar, hero |
| `--accent` | `#10B981` | éxito, plotter, indicadores |
| `--warning` | `#F59E0B` | alertas de stock, avisos |
| `--danger` | `#DC2626` | errores, eliminar |
| `--ink` | `#0F172A` | texto principal |
| `--muted` | `#64748B` | texto secundario |
| `--surface` | `#FFFFFF` | tarjetas |
| `--bg` | `#F4F7FB` | fondo |
| `--border` | `#DCE5F0` | bordes |
| `--radius` | `12px` | tarjetas/botones |
| `--shadow-sm/md` | sombras suaves | elevación |

Tipografía: `--font-display: 'Space Grotesk', 'Segoe UI', sans-serif` para
títulos (cargada opcionalmente con `<link>` y fallback local); cuerpo con la
pila actual. Las clases viejas (`btn-green`, `btn-blue`, `status-warning`)
se mantienen como alias de los tokens para no tocar todas las plantillas.

### 1.2 Fondo blueprint

Cuadrícula sutil con `linear-gradient` (dos ejes, 24 px) sobre `--bg`, solo en
la landing, el hero del login y la cabecera de página; nunca detrás de tablas
largas para no cansar la vista.

## 2. Layout (`layout.html`)

- Sidebar oscuro (`--primary-dark`) con grupos:
  - **Comercial:** Solicitudes (badge), Clientes, Proyectos
  - **Producción:** Planos, Insumos (badge de riesgo)
  - **Facturación:** Facturas, Reportes
  - **Administración:** Usuarios
  - **Cliente:** Dashboard, Proyectos, Mis Planos, Mis Facturas (según rol)
- Header: logo + breadcrumb (`Sección / Página` vía `request.endpoint`),
  usuario, salir. Botón hamburguesa visible < 900 px.
- Badges: `_contadores_nav()` en `app.py` como *context processor*:
  `solicitudes_pendientes` (`COUNT estado='solicitado'`) y
  `materiales_riesgo` (reutiliza `_prediccion_inventario` sin silencios).
  Se calculan solo para admin/trabajador.
- JS en `main.js`: alternar clase `sidebar-abierta` en `<body>`; cerrar al
  navegar; `aria-expanded` en el botón.

## 3. Dashboards

### 3.1 Admin (`dashboard.html`)

- Fila de **acciones rápidas**: Nueva cotización (solicitudes), Subir plano,
  Nueva factura, Ver inventario.
- Tarjetas de alerta: «Solicitudes por atender» (enlace a `/solicitudes`) y
  «Materiales en riesgo» (enlace a `/inventario#prediccion`), con color
  semántico.
- KPIs existentes reordenados y con iconos coherentes.
- Proyectos recientes con pills de estado y enlace al detalle.

### 3.2 Cliente (`dashboard_cliente.html`)

- Por cada proyecto: nombre, tipo, presupuesto y **línea de progreso** con
  los estados (`solicitado → cotizado → aprobado → en_progreso → ejecutado`),
  resaltando el actual.
- Acciones: «Ver planos» y «Ver detalle»; estado vacío con CTA a
  `/solicitud`.

## 4. Landing y login

- `landing.html` + `landing.css`: hero con cuadrícula blueprint, titular
  claro, CTA «Solicitar cotización» y tarjetas de servicios con borde fino.
- `login.html`: tarjeta centrada sobre fondo blueprint, misma paleta; el
  formulario y sus validaciones no cambian.
- `solicitud_publica.html`: se alinea tipografía/colores, sin tocar campos.

## 5. Tablas, formularios y estados

- `data-table`: cabecera con fondo suave, filas con hover, celdas numéricas
  alineadas, botones de acción compactos.
- `page-header`: título + subtítulo + acciones alineadas; breadcrumb.
- `status-badge`: variantes `success`, `warning`, `danger`, `muted`.
- Formularios: `.form-group` con label fuerte, ayuda en `--muted`, foco con
  anillo `--primary`; botones primario/secundario/peligro unificados.
- Flash messages: icono, color semántico y cierre (ya existe) con los tokens.

## 6. Integración Sprint 5/6

- Tarjeta «Materiales en riesgo» en dashboard admin (conteo de la predicción).
- Enlace directo a `#prediccion` desde la tarjeta y desde el badge del menú.
- En el detalle del plano, el checklist ya existe: se le aplican los tokens.
- En el formulario de cotización, el panel de desglose hereda los tokens.

## 7. Pruebas

- `test_sprint4.py`, `test_sprint5.py`, `test_sprint6.py` en verde (no cambia
  comportamiento).
- Smoke visual por HTTP: landing, login, dashboard admin, dashboard cliente,
  inventario, planos, detalle de plano, solicitud pública → 200 y presencia de
  las clases nuevas (`sidebar-grupo`, `breadcrumb`, `acciones-rapidas`).
- Revisión manual de contraste y del menú móvil en el navegador.

## 8. Despliegue

- Push a `origin` y `review`; copiar `style.css`, `main.js`, `layout.html`,
  dashboards, landing/login y `app.py` al G60; reiniciar `asplot`.
- `docs/DISENO.md` + fila en `GUIA_REVISION.md`.
