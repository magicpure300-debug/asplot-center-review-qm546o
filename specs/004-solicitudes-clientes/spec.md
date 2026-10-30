# Spec 004 — Sprint 4: Solicitudes online y gestión de clientes

> **Estado:** pendiente de aprobación
> **Sprint:** 4 · **Puntos:** 13 (PB-14: 8 · PB-15: 5)
> **Depende de:** Sprints 1–3 (auth/RBAC, cotizador, inventario, caché, portafolio)
> **Habilita:** PB-10 (cotizador automático, Fase 2)

---

## 1. Problema

Hoy una persona interesada en los servicios de ASPLOT CENTER no puede solicitar
nada sin crear una cuenta: la landing solo ofrece «Iniciar sesión / Registrarse»
y el formulario `solicitar_servicio` exige un usuario con rol `cliente` ya
autenticado. Esto frena la captación: el visitante abandona, y quien llega por
teléfono o WhatsApp termina siendo cargado a mano por un administrador.

Además, la gestión de clientes es incompleta: existe la lista y el CRUD básico,
pero **no hay ficha de cliente** que muestre su historial (proyectos, facturas,
montos pendientes). El administrador no puede responder «¿qué le hemos hecho a
este cliente y cuánto debe?» sin navegar por tres módulos distintos.

## 2. Objetivos

1. Permitir que cualquier visitante envíe una solicitud de servicio **sin
   crear cuenta**, con los mismos datos que hoy pide el formulario interno.
2. Convertir esa solicitud en un `Cliente` (o reutilizar uno existente por
   email) y un `Proyecto` en estado `solicitado`, sin duplicados.
3. Dar al administrador una bandeja clara de solicitudes nuevas y una ficha
   de cliente 360° con historial y saldos.

## 3. Alcance

### Dentro del alcance

- Formulario público de solicitud en la landing (`/solicitud`), sin login.
- Reutilización de cliente existente por email (sin duplicar registros).
- Adjunto opcional (PDF/DWG/JPG/PNG) con las validaciones ya existentes.
- Confirmación al solicitante con número de solicitud y aviso al admin
  (contador en dashboard + listado filtrado).
- Bandeja de solicitudes pendientes para admin/gestor (estado `solicitado`).
- Ficha de cliente `/clientes/<id>`: datos, proyectos con estado, facturas,
  totales (facturado, pagado, pendiente) y accesos a acciones.
- Búsqueda de clientes ampliada (nombre, apellido, email, teléfono) y
  paginación simple si supera 50 registros.
- Vinculación consistente `Usuario` ↔ `Cliente` (el registro ya la crea; la
  solicitud pública debe respetarla y no romperla).

### Fuera del alcance (para no inflar el sprint)

- Portal de autogestión del cliente (seguimiento en vivo de su solicitud):
  queda para un sprint posterior; el cliente ya ve sus proyectos en el
  dashboard existente.
- Cotización automática de la solicitud (PB-10, Fase 2).
- Notificaciones por email/SMS reales: se deja el punto de extensión y
  mensaje en pantalla; el envío queda documentado como pendiente.
- Rediseño visual de la landing más allá del bloque de solicitud.

## 4. Historias de usuario y criterios de aceptación

### PB-14 — Solicitud de servicio online sin cuenta (8 pts)

**Como** visitante sin cuenta, **quiero** enviar una solicitud de servicio
desde la landing **para** recibir una cotización sin registrarme.

Criterios de aceptación:

1. `GET /solicitud` muestra el formulario público con: nombre, apellido,
   email, teléfono, dirección, tipo de servicio, nombre del proyecto,
   descripción y adjunto opcional.
2. `POST /solicitud` válido crea un `Proyecto` con estado `solicitado`:
   - si no existe `Cliente` con ese email → crea el cliente;
   - si existe → reutiliza el cliente y **no** duplica;
   - si existe un `Usuario` con ese email → el proyecto queda asociado a su
     cliente vinculado (id_usuario coherente).
3. Respuesta exitosa: página de confirmación con el número de proyecto y el
   mensaje «Un asesor se contactará al teléfono/email indicado».
4. Errores de validación (campos vacíos, email inválido, archivo con
   extensión no permitida) se muestran en el mismo formulario sin perder lo
   escrito.
5. El formulario público **no** permite fijar presupuesto, estado, fechas ni
   cliente: esos campos se ignoran si llegan en el POST.
6. Anti-abuso mínimo: campo honeypot invisible (si viene completo, se
   descarta silenciosamente con mensaje genérico) y límite de 3 envíos por
   IP cada 10 minutos (en memoria, mismo patrón que `cachear.py`).
7. El admin ve las nuevas solicitudes en el dashboard (contador «Solicitudes
   pendientes») y en `/solicitudes`, con enlace a aprobar/rechazar ya
   existentes.
8. La landing incluye un CTA «Solicitar cotización» que apunta a
   `/solicitud` (además del CTA actual a login).

### PB-15 — Ficha de cliente 360° (5 pts)

**Como** administrador, **quiero** abrir la ficha de un cliente **para** ver
de un vistazo su historial y sus saldos.

Criterios de aceptación:

1. `GET /clientes/<id>` (solo admin/gestor) muestra:
   - datos de contacto y estado de vinculación con usuario;
   - tabla de proyectos con estado y fechas;
   - tabla de facturas con estado de pago y montos;
   - resumen: total facturado, total pagado, total pendiente.
2. Desde la ficha se accede a editar cliente, ver cada proyecto y cada
   factura, y crear una factura para ese cliente (precargando el cliente).
3. La lista de clientes enlaza al nombre con su ficha y conserva la búsqueda
   actual, ampliada a teléfono; si hay más de 50 resultados se pagina de a 25.
4. Eliminar cliente sigue bloqueado si tiene proyectos/facturas (regla actual
   de integridad); el mensaje explica por qué.
5. La ficha no expone datos de otros clientes ni permite acceso a usuarios
   con rol `cliente` (redirección con aviso, igual patrón RBAC existente).

## 5. Requisitos no funcionales

- **Seguridad:** RBAC en todas las rutas nuevas; el POST público valida
  tamaño máximo de adjunto (10 MB) y extensión; los campos del formulario se
  escapan en plantilla (Jinja autoescape); el honeypot y el rate limit no
  revelan su funcionamiento al usuario.
- **Rendimiento:** la ficha de cliente usa las relaciones ya definidas con
  `lazy=True` y agrega totales con una sola consulta agregada (evitar N+1);
  se registra la ruta en la caché existente solo si el perfil es de lectura.
- **Compatibilidad:** SQLite (demo/Render) y MySQL (producción); sin cambios
  de esquema obligatorios (se reutilizan `clientes` y `proyectos`). Si se
  agrega un campo (p. ej. `origen`), la migración debe ser opcional e
  idempotente como en Sprints 1–3.
- **Documentación:** `docs/SPRINT_4.md` con el detalle técnico y las pruebas,
  alineado al formato de `SPRINT_2.md`/`SPRINT_3.md`.

## 6. Modelo de datos (sin migración obligatoria)

| Entidad | Uso en Sprint 4 | Cambios |
|---|---|---|
| `Cliente` | alta/reutilización por email, ficha 360° | ninguno |
| `Proyecto` | estado `solicitado`, adjunto, origen público | opcional: `origen` (`interno`/`web`) |
| `Factura` | totales en ficha | ninguno |
| `Usuario` | vinculación por email | ninguno |

## 7. Criterios de éxito

- Un visitante completo la solicitud en < 2 minutos y recibe confirmación con
  número.
- El admin ve la solicitud en el dashboard en la siguiente carga y puede
  aprobarla/rechazarla desde la bandeja.
- La ficha de cliente responde historial y saldos con una sola pantalla.
- Suite de pruebas: casos nuevos en `smoke_test.py`/`test_sprint4.py` +
  regresión de Sprints 1–3 en verde.

## 8. Riesgos y preguntas abiertas

1. **ERS no disponible localmente:** el documento `PST ASPLOT CENTER` ya no
   está en Descargas. Esta spec se basa en el estado del código y en el
   alcance acordado («solicitudes online y gestión de clientes»). Si el ERS
   define otras historias o numeración, se ajusta antes de implementar.
2. **Numeración:** PB-14/PB-15 quedan libres; PB-10…13 ya están usadas por las
   propuestas de IA (`docs/BACKLOG_IA.md`).
3. **Sin CSRF global:** la app no usa Flask-WTF; el formulario público es el
   primer POST anónimo. Se mitiga con honeypot + rate limit y validación
   estricta; evaluar CSRF simple por token de sesión como mejora opcional.
