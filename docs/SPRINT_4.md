# ASPLOT CENTER — Sprint 4: Solicitudes online y gestión de clientes

> **PB-14 (8) + PB-15 (5) = 13 puntos**
> Duración: 2 semanas · Equipo: 2 desarrolladores
> Objetivo: abrir la captación al público (solicitud sin cuenta) y dar al
> administrador una ficha de cliente con historial y saldos en una sola pantalla.
> Habilita PB-10 (cotizador automático, Fase 2 de IA).

---

## PB-14 — Solicitud de servicio online sin cuenta (8 pts)

**Rutas nuevas** (`app.py`):

- `GET/POST /solicitud` — formulario público, sin `login_required`.
- `GET /solicitud/enviada/<id>` — confirmación con número de solicitud.
- `GET /solicitudes` — bandeja de pendientes para admin/gestor.

**Flujo:**

1. El visitante completa nombre, apellido, email, teléfono, dirección, tipo de
   servicio, nombre del proyecto, descripción y adjunto opcional.
2. El servidor valida (campos obligatorios, email con expresión regular, tipo
   de servicio dentro de la lista permitida, adjunto ≤ 10 MB y extensión
   permitida) y re-renderiza el formulario con los errores y lo ya escrito.
3. `_obtener_o_crear_cliente()` busca al cliente por email
   (`func.lower`), lo reutiliza si existe (completando teléfono/dirección si
   faltaban) o lo crea. Si el email coincide con un `Usuario` registrado, el
   cliente nace vinculado (`id_usuario`).
4. Se crea el `Proyecto` con estado `solicitado` (los campos de control del
   POST — `presupuesto`, `estado`, `id_cliente`, fechas — se ignoran).
5. Redirección a la confirmación con el número de solicitud.

**Anti-abuso:**

- *Honeypot* invisible (`sitio_web`, fuera de pantalla, `tabindex="-1"`): si
  llega completo se responde la confirmación genérica sin persistir nada.
- Límite en memoria de **3 solicitudes por IP cada 10 minutos** (ventana
  deslizante con `threading.Lock`); el cuarto POST devuelve HTTP 429 con un
  mensaje que indica cuántos segundos faltan.

**Bandeja y visibilidad:**

- `/solicitudes` lista los proyectos `solicitado` con cliente, contacto,
  servicio, adjunto y acciones (atender/rechazar, reutilizando las rutas
  existentes de aprobación).
- El dashboard admin suma una tarjeta «Solicitudes» (cuarto `UNION ALL` en la
  consulta consolidada de PB-04, sin consultas extra) y el menú lateral un
  enlace «Solicitudes» visible solo para admin/gestor.
- La landing tiene ahora el CTA «Solicitar cotización» en el hero y en la
  sección final.

**Plantillas:** `solicitud_publica.html` y `solicitud_confirmacion.html`
(autónomas, sin layout privado, con su propio encabezado público),
`solicitudes.html` (extiende `layout.html`).

## PB-15 — Ficha de cliente 360° (5 pts)

**Ruta:** `GET /clientes/<id>` (admin/gestor; un cliente recibe redirección
con aviso, mismo patrón RBAC del proyecto).

Muestra:

- Datos de contacto y si el cliente tiene usuario vinculado.
- Totales **facturado / pagado / pendiente** calculados con **una sola
  consulta agregada** (`SUM` + `CASE`), excluyendo facturas canceladas.
- Tabla de proyectos con estado, tipo, presupuesto y enlace al detalle.
- Tabla de facturas con vencimiento, total, estado de pago y enlace.
- Acciones: volver, editar cliente y **crear factura precargada**
  (`/facturas/crear?cliente=<id>`, el `<select>` queda seleccionado).

**Listado de clientes (`/clientes`):**

- Búsqueda ampliada a **teléfono** además de nombre, apellido y email
  (`ilike`, compatible SQLite/MySQL).
- **Paginación de 25** por página con controles que conservan el término de
  búsqueda.
- El nombre enlaza directamente a la ficha.

**Integridad:** eliminar un cliente con proyectos o facturas ya no se intenta:
se bloquea con un mensaje explicativo y enlace a su ficha (antes el borrado
dependía de la base de datos).

## Decisiones técnicas

| Decisión | Motivo |
|---|---|
| Sin migración de esquema | Se reutilizan `clientes` y `proyectos`; evita tocar MySQL y el demo de Render. Campo `origen` queda como mejora futura. |
| Rate limit en memoria | Mismo criterio que la caché de PB-06; el demo corre un solo worker. |
| Invalidación de caché automática | El hook `after_commit` de SQLAlchemy ya invalida dashboard/reportes/portafolio en cada INSERT. |
| Honeypot + validación estricta | La app no usa CSRF global; se mitiga el primer POST anónimo sin añadir dependencias. |

## Pruebas

Suite `test_sprint4.py` (copia limpia del proyecto con SQLite propio, mismo
escenario que el arranque en frío de Render): **29 comprobaciones en verde**.

- Formulario público (GET), creación de proyecto `solicitado`, confirmación
  con número.
- Reutilización de cliente por email y vinculación con usuario registrado.
- Honeypot, rate limit (3 permitidos / 4.º 429), validaciones, extensión no
  permitida y PDF válido guardado.
- Campos de control ignorados en el POST público.
- Bandeja `/solicitudes` (admin sí, cliente no) y tarjeta en dashboard.
- Ficha de cliente con historial y totales (150 / 100 / 50), RBAC, búsqueda
  por teléfono, paginación de 25, bloqueo de borrado con historial y factura
  precargada.
- Regresión: landing, portafolio, login, dashboard anónimo, inventario,
  facturas, reportes y proyectos.

## Limitaciones documentadas

- **Adjuntos en Render:** el disco es efímero; los archivos subidos se pierden
  en cada redeploy (el registro de la solicitud se conserva).
- **Rate limit por proceso:** con varios workers gunicorn cada uno tendría su
  propio contador; para producción multi-instancia se movería a Redis.
- **Sin CSRF global:** se compensa con honeypot, límite por IP y validación;
  un token CSRF simple por sesión queda como mejora.
- **Notificaciones:** no se envía email/SMS real. En el servidor propio (G60)
  sí hay aviso opcional por **Telegram** al recibir una solicitud: se activa
  con `ASPLOT_TELEGRAM_TOKEN` y `ASPLOT_TELEGRAM_CHAT` en el entorno; si no
  están definidas, la solicitud funciona igual (el aviso falla en silencio).
