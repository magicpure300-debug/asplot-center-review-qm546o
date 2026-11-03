# Tareas 007 — Rediseño visual «blueprint»

> **Spec:** `specs/007-rediseno-blueprint/spec.md`
> **Plan:** `specs/007-rediseno-blueprint/plan.md`
> **Regla:** una tarea a la vez; al terminar, suites en verde y parada para
> validación humana.

- [x] **T1. Design tokens y base**
  - RF: CA1, RNF accesibilidad.
  - Variables en `style.css`, alias de clases viejas, tipografía de títulos,
    fondo blueprint reutilizable, botones/estados/flash con tokens.
  - Hecho: `grep` no encuentra los verdes hardcodeados en las clases base;
    landing y dashboard siguen 200.

- [x] **T2. Layout: sidebar agrupado, header y móvil**
  - RF: CA2.
  - `layout.html` con 4 grupos por rol, breadcrumb, badges, botón hamburguesa;
    `main.js` para abrir/cerrar; estilos en `style.css`.
  - Hecho: admin ve los 4 grupos y badges; cliente ve solo lo suyo; en ancho
    < 900 px el menú se colapsa y se abre con el botón.

- [x] **T3. Dashboard admin accionable**
  - RF: CA3, CA6.
  - Acciones rápidas, tarjetas de alerta con datos reales, KPIs y proyectos
    recientes reestilizados.
  - Hecho: la tarjeta de solicitudes enlaza a `/solicitudes` y la de riesgo a
    `/inventario`; los conteos coinciden con la base.

- [x] **T4. Dashboard cliente con línea de estado**
  - RF: CA4.
  - `dashboard_cliente.html` con progreso por proyecto, presupuesto y accesos;
    estado vacío con CTA.
  - Hecho: un proyecto en `cotizado` muestra la etapa resaltada y el enlace a
    sus planos.

- [x] **T5. Landing y login blueprint**
  - RF: CA5.
  - Hero con cuadrícula, tarjetas de servicios, login centrado; sin tocar
    campos ni validaciones.
  - Hecho: landing y login 200; el formulario público `/solicitud` sigue
    funcionando.

- [x] **T6. Consistencia de tablas, formularios y estados**
  - RF: CA6.
  - Overrides de `data-table`, `page-header`, `form-group`, `status-badge`,
    `action-buttons`; revisión de inventario, planos, facturas, clientes y
    solicitudes.
  - Hecho: las cinco pantallas comparten barra de herramientas, pills y
    botones; sin cambios de comportamiento.

- [x] **T7. Integración Sprint 5/6 y contadores**
  - RF: CA3, CA7.
  - Context processor con conteos; tarjeta de riesgo; enlaces a las funciones
    nuevas; tokens en el checklist y el desglose.
  - Hecho: badges correctos para admin; el cliente no ejecuta consultas de
    admin.

- [x] **T8. Verificación**
  - RF: CA7, CA8, RNF.
  - Suites 4/5/6 en verde + smoke HTTP de las rutas tocadas.
  - Hecho: todo en verde y sin 500 en las pantallas revisadas.

- [x] **T9. Documentación y despliegue en el G60**
  - RF: RNF documentación/portabilidad.
  - `docs/DISENO.md`, fila en `GUIA_REVISION.md`, push a `origin`/`review`,
    copia al G60, reinicio y verificación LAN/túnel.
  - Hecho: G60 con el rediseño y 200 en landing, login, dashboard e
    inventario.
