# Tareas 004 — Sprint 4

> **Regla SDD:** una tarea a la vez. No se avanza a la siguiente sin que la
> validación de la anterior esté en verde. Cambios solo en `develop`.

---

## T0 — Línea base (sin cambios de código)

- [ ] Ejecutar `smoke_test.py`, `test_sprint3.py` y `test_sprint3_full.py`
      sobre el estado actual de `develop`.
- [ ] Registrar resultados y `git status` limpio.

**Gate:** las tres suites en verde antes de tocar `app.py`.

---

## T1 — Solicitud pública + confirmación (PB-14, núcleo)

**Archivos:** `app.py`, `templates/solicitud_publica.html`,
`templates/solicitud_confirmacion.html`.

- [ ] Helpers: `_reutilizar_cliente`, `_limitar_solicitudes`, validación de
      campos y honeypot.
- [ ] `GET/POST /solicitud` con lista fija de tipos de servicio y adjunto
      opcional (usa `allowed_file` y `MAX_CONTENT_LENGTH` = 10 MB).
- [ ] `GET /solicitud/enviada/<id>` con número de solicitud y resumen.
- [ ] Ignorar campos de control en el POST público.
- [ ] Estilos coherentes con `solicitar_servicio.html` (sin tocar `style.css`).

**Gate:** pruebas 1–8 de `test_sprint4.py` en verde + regresión smoke.

---

## T2 — Bandeja de solicitudes y aviso en dashboard (PB-14, gestión)

**Archivos:** `app.py`, `templates/solicitudes.html`, `templates/dashboard.html`,
`templates/layout.html`, `templates/landing.html`.

- [ ] `GET /solicitudes` (admin/gestor) con proyectos `solicitado`, orden por
      fecha desc, enlaces a aprobar/rechazar existentes.
- [ ] Cuarto `UNION ALL` en `dashboard()` para solicitudes pendientes +
      tarjeta en `dashboard.html` con enlace.
- [ ] Enlace «Solicitudes» en `layout.html` solo para admin/gestor.
- [ ] CTA «Solicitar cotización» en la landing → `/solicitud`.

**Gate:** prueba 9 + smoke; captura/verificación visual de dashboard y nav.

---

## T3 — Ficha de cliente 360° (PB-15)

**Archivos:** `app.py`, `templates/detalle_cliente.html`,
`templates/clientes.html`.

- [ ] `GET /clientes/<id>` (admin/gestor): datos, proyectos, facturas,
      totales facturado/pagado/pendiente con una consulta agregada.
- [ ] Botones: editar cliente, ver proyecto, ver factura, crear factura
      precargada.
- [ ] Búsqueda por teléfono + paginación 25 (`page`), nombre enlazado a ficha.
- [ ] Regla de integridad al eliminar con mensaje explicativo.

**Gate:** pruebas 10–11 + regresión completa.

---

## T4 — Documentación, regresión final y entrega

**Archivos:** `docs/SPRINT_4.md`, `specs/004-solicitudes-clientes/*`.

- [ ] `docs/SPRINT_4.md` con alcance, decisiones, pruebas y limitaciones
      (adjuntos efímeros en Render, rate limit por proceso, sin CSRF).
- [ ] Suite completa: `test_sprint4.py`, `smoke_test.py`,
      `test_sprint3.py`, `test_sprint3_full.py`, `freshboot_render.py`.
- [ ] Commit en `develop` + push a `origin` y al mirror de revisión.
- [ ] Resumen al usuario con evidencia (salida de pruebas).

**Gate:** todas las suites en verde y remotos sincronizados.
