# ASPLOT CENTER — Sistema de diseño «blueprint»

> **Origen:** rediseño visual completo (spec `specs/007-rediseno-blueprint/`).
> Sin cambios de lógica, rutas, permisos ni esquema: es una capa de
> presentación sobre los módulos existentes.

---

## 1. Identidad

El negocio es **plotter y planos**, así que la interfaz adopta un lenguaje
técnico: azul cianotipo, cuadrícula de plano y verde de plotter como acento.

| Token | Valor | Uso |
|---|---|---|
| `--primary` | `#1d4ed8` | acciones principales, enlaces, foco |
| `--primary-dark` | `#16357a` | sidebar, hero, login |
| `--primary-soft` | `#e8efff` | fondos de iconos y estados informativos |
| `--accent` | `#10b981` | éxito, etapa completada, plotter |
| `--accent-soft` | `#e6f7f1` | fondos de éxito |
| `--warning` | `#f59e0b` | stock bajo, avisos |
| `--danger` | `#dc2626` | errores, eliminar |
| `--ink` | `#0f172a` | texto principal |
| `--muted` | `#64748b` | texto secundario |
| `--surface` | `#ffffff` | tarjetas |
| `--bg` | `#f4f7fb` | fondo de la app |
| `--border` | `#dce5f0` | bordes |
| `--radius` | `12px` | tarjetas y botones |
| `--shadow-sm/md` | sombras suaves | elevación |

Tipografía: **Space Grotesk** para títulos (Google Fonts con fallback a
`Segoe UI`), cuerpo con la pila del sistema. Si no hay internet, la interfaz
sigue siendo legible.

## 2. Navegación

Sidebar oscuro agrupado por flujo de trabajo, con badges de pendientes:

- **General:** Dashboard.
- **Comercial:** Solicitudes (badge de `solicitado`), Clientes, Proyectos.
- **Producción:** Planos, Insumos (badge de materiales bajo mínimo).
- **Facturación:** Facturas, Reportes (solo admin).
- **Administración:** Usuarios (solo admin).
- **Mi cuenta** (cliente): Mis Proyectos, Mis Planos.

Cada pantalla muestra un **breadcrumb** (General / Sección / Página) y el
menú se colapsa en móvil con botón hamburguesa (cierre con Escape o al
navegar). Los badges se calculan con dos `COUNT` simples en un *context
processor*; el cliente no ejecuta consultas de admin.

## 3. Componentes

- **Botones:** primario (azul), secundario (blanco con borde), éxito (verde),
  peligro (rojo); radio 10 px y foco visible.
- **KPIs:** tarjetas blancas con icono en `--primary-soft`, etiqueta en
  `--muted` y número en Space Grotesk.
- **Tablas:** cabecera `#eef3fb`, filas con hover, bordes suaves, pills de
  estado semánticas (`solicitado`, `cotizado`, `en_progreso`, `ejecutado`,
  `rechazado`).
- **Formularios:** etiquetas fuertes, inputs con borde `--border` y anillo de
  foco azul.
- **Mensajes flash:** color semántico con icono y cierre.
- **Fondo blueprint:** clases `.fondo-blueprint` y hero con cuadrícula.
- **Dashboard admin:** acciones rápidas + tarjetas de alerta (solicitudes por
  atender, inventario bajo mínimo) + KPIs + proyectos recientes.
- **Dashboard cliente:** KPIs + tarjetas de proyecto con **línea de estado**
  (`Solicitado → Cotizado → Aprobado → En progreso → Entregado`).

## 4. Integración con los sprints de IA

- La tarjeta «Inventario bajo mínimo» enlaza a `/inventario#prediccion`.
- El panel de predicción y el checklist de calidad del plano usan los mismos
  tokens (sin estilos propios duplicados).
- El desglose de cotización automática conserva su panel y hereda la paleta.

## 5. Responsive y accesibilidad

- Breakpoint principal en **900 px**: sidebar fuera de pantalla y botón
  hamburguesa; contenido a una columna.
- En **560 px**: KPIs, acciones y alertas a una columna; se oculta el detalle
  del usuario en el header para evitar desbordes.
- Foco visible (`:focus-visible`), etiquetas `aria` en botones de icono y
  navegación por teclado (Escape cierra el menú).

## 6. Verificación

- Suites de Sprints 4, 5 y 6 en verde (sin cambios de comportamiento).
- Smoke de diseño (`test_diseno_smoke.py`): clases nuevas, badges, breadcrumb,
  grupos por rol y línea de estado del cliente.
- Capturas reales con Edge headless: landing, login, dashboard admin,
  dashboard cliente, inventario y vista móvil (430 px).

## 7. Limitaciones y mejoras futuras

- **Modo oscuro:** no incluido; los tokens ya están preparados para añadirlo.
- **Tipografía web:** Space Grotesk se carga desde Google Fonts; sin internet
  se usa el fallback local.
- **Iconos:** Font Awesome sigue viniendo por CDN (comportamiento previo).
- **Plantillas con estilos inline** (cotizador, detalle de plano): conservan
  sus reglas específicas y solo comparten tokens.
