# Spec 007 — Rediseño visual «blueprint» y navegación por flujos

> **Estado:** pendiente de aprobación
> **Tipo:** cambio de presentación (UI/UX), sin nuevas historias de negocio
> **Alcance técnico:** CSS + plantillas + pequeños datos de contexto en
> `app.py`. Sin cambios de esquema, rutas ni lógica de negocio.

---

## 1. Problema

La aplicación funciona, pero visualmente se percibe como una plantilla
genérica de administración:

- 4–5 verdes distintos (`#20c997`, `#2e7d32`, `#198754`, `#28a745`) y grises
  sueltos, sin tokens ni jerarquía.
- Sidebar plano de 8 enlaces que mezcla áreas y roles; sin agrupación ni
  indicadores de pendientes.
- El dashboard admin muestra KPIs pero no lleva a la acción; el cliente ve
  una lista, no el estado de su solicitud.
- Cada pantalla resuelve tablas/formularios/estados a su manera.
- Las funciones nuevas (cotización automática, inventario predictivo, calidad
  de planos) viven en pantallas aparte y no se ven desde el flujo principal.

Para la defensa, la primera impresión (landing, login, dashboard) es lo que
más pesa y hoy no refleja un producto de plotter/planos.

## 2. Objetivos

1. Dar identidad propia (**blueprint / plotter**) con un design system mínimo
   y consistente.
2. Ordenar la navegación por flujos de trabajo y hacerla usable en móvil.
3. Convertir el dashboard en un panel accionable (admin) y en un seguimiento
   claro (cliente).
4. Unificar tablas, formularios, estados y mensajes.
5. Integrar las funciones de los Sprints 5–6 en el flujo visible.

## 3. Alcance

### Dentro del alcance

- **Design tokens** en `style.css`: colores, tipografía, radios, sombras,
  espaciado; sustitución de los verdes dispersos por variables.
- **Identidad blueprint**: fondo de cuadrícula sutil en landing/hero y
  cabeceras, azul cianotipo como primario, verde plotter como acento, ámbar
  para advertencias. Tipografía de títulos con fallback local.
- **Layout**: sidebar agrupado (Comercial, Producción, Facturación,
  Administración), estado activo claro, badges de pendientes (solicitudes) y
  de riesgo de inventario; header con breadcrumb y menú hamburguesa en móvil.
- **Dashboard admin**: accesos rápidos («Nueva cotización», «Solicitudes»,
  «Subir plano»), tarjetas de alerta reales (solicitudes pendientes,
  materiales en riesgo) y proyectos recientes con mejor jerarquía.
- **Dashboard cliente**: línea de estado de cada proyecto (solicitado →
  cotizado → aprobado → en progreso → ejecutado) y accesos a sus planos.
- **Tablas y formularios**: barra de herramientas única, pills de estado
  semánticas, estados vacíos útiles, foco visible y botones con texto.
- **Landing y login**: hero tipo plano técnico, tarjetas de servicios y
  formulario de acceso coherentes con la nueva identidad.
- **Integración**: tarjeta «Inventario en riesgo» en dashboard admin
  (reutiliza la predicción del Sprint 6) y enlaces directos a las funciones
  nuevas.

### Fuera del alcance

- Cambiar rutas, reglas de negocio, permisos o esquema de datos.
- Reescribir todas las plantillas desde cero: se intervienen las clave y el
  resto hereda los tokens.
- Modo oscuro (se documenta como mejora futura).
- Sustituir Font Awesome o añadir frameworks CSS/JS nuevos.
- Capturas o assets gráficos pesados: la identidad se logra con CSS.

## 4. Criterios de aceptación

1. `style.css` define tokens (`--primary`, `--accent`, `--warning`,
   `--surface`, `--border`, `--radius`, `--shadow-*`, `--font-display`) y las
   pantallas principales dejan de usar verdes hardcodeados.
2. El sidebar muestra 4 grupos con solo los enlaces permitidos por rol,
   estado activo visible, badge de solicitudes pendientes y de materiales en
   riesgo; en móvil se colapsa con un botón y vuelve a abrirse.
3. El dashboard admin incluye accesos rápidos y alertas con datos reales
   (conteo de solicitudes `solicitado` y de materiales en riesgo del Sprint 6).
4. El dashboard cliente muestra el estado de cada proyecto como línea de
   progreso y enlaces a «Mis planos».
5. Landing y login usan la identidad blueprint (cuadrícula, paleta,
   tipografía) sin romper el formulario público de solicitud.
6. Tablas, formularios y mensajes flash comparten estilos (sin cambios de
   comportamiento).
7. Todas las rutas siguen respondiendo 200/302 igual que antes y **las suites
   de Sprints 4, 5 y 6 quedan en verde**.
8. Sin dependencias nuevas obligatorias; si la fuente web no carga, hay
   fallback local legible.

## 5. Requisitos no funcionales

- **Sin lógica nueva de negocio:** los únicos datos extra son conteos para
  badges y la tarjeta de riesgo (reutiliza `_prediccion_inventario`).
- **Rendimiento:** los badges usan consultas `COUNT` simples; el dashboard ya
  está cacheado 60 s.
- **Accesibilidad:** contraste AA en texto, `:focus-visible`, `aria-label` en
  botones de icono, navegación por teclado en el menú móvil.
- **Portabilidad:** todo CSS/JS propio; funciona igual en LAN, túnel y el G60.
- **Documentación:** `docs/DISENO.md` con la paleta, componentes y capturas
  textuales; fila en `GUIA_REVISION.md`.

## 6. Riesgos

1. **`style.css` es compartido por todas las plantillas:** se cambia por
   capas (tokens + overrides) y se verifica cada módulo con las suites.
2. **Plantillas con estilos inline** (aprobar_proyecto, detalle_plano):
   se conservan sus estilos específicos y solo se alinean colores base.
3. **Fuente web no disponible sin internet:** fallback a la pila del sistema.
4. **Sidebar en pantallas pequeñas:** el menú colapsable debe recordar el
   estado solo durante la sesión de navegación (sin persistencia).
