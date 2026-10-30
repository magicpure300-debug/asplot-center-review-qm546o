# Plan técnico 004 — Sprint 4: Solicitudes online y gestión de clientes

> **Spec aprobada:** `specs/004-solicitudes-clientes/spec.md`
> **Estrategia:** incremento sobre el monolito `app.py` (rutas dentro de
> `create_app()`), sin cambios de esquema y reutilizando caché, RBAC inline y
> validación de adjuntos ya existentes.

---

## 1. Arquitectura de la solución

### 1.1 Rutas nuevas

| Ruta | Método | Acceso | Propósito |
|---|---|---|---|
| `/solicitud` | GET, POST | Público | Formulario de solicitud sin cuenta |
| `/solicitud/enviada/<int:id>` | GET | Público (por id de proyecto) | Confirmación con número de solicitud |
| `/solicitudes` | GET | Admin/gestor | Bandeja de solicitudes en estado `solicitado` |
| `/clientes/<int:id>` | GET | Admin/gestor | Ficha de cliente 360° |

### 1.2 Rutas existentes que se tocan

- `landing()`: nuevo CTA «Solicitar cotización» → `url_for('solicitud_publica')`
  (se conserva el CTA de login/registro).
- `dashboard()`: cuarto `UNION ALL` para contar solicitudes pendientes
  (`Proyecto.estado == 'solicitado'`) y una tarjeta nueva en `dashboard.html`.
- `clientes()`: búsqueda ampliada a `telefono`, paginación de 25 con `?page=`,
  nombre enlazado a la ficha.
- `layout.html`: enlace «Solicitudes» visible para admin/gestor.

### 1.3 Componentes auxiliares

- **`_reutilizar_cliente(email, datos)`** (helper dentro de `create_app`):
  busca `Cliente` por email (`func.lower`), si no existe crea uno con los
  datos del formulario, si existe actualiza teléfono/dirección solo si llegan
  valores nuevos. Devuelve el cliente. Evita duplicados por email que exige
  el criterio PB-14.2.
- **`_limitar_solicitudes(ip)`**: diccionario en memoria
  `{ip: [timestamps]}` protegido con `threading.Lock`, ventana deslizante de
  10 minutos, máximo 3 envíos. Devuelve `(permitido, segundos_restantes)`.
  Elegido sobre Redis/caché por simplicidad y porque el formulario es de bajo
  tráfico; documentado como limitación multi-proceso (igual que PB-06).
- **Honeypot**: campo `sitio_web` oculto por CSS (`display:none`,
  `tabindex="-1"`, `autocomplete="off"`). Si llega con valor, se responde la
  misma confirmación genérica sin crear registros.
- **Validación**: nombre/apellido/email/teléfono/dirección/tipo/nombre
  proyecto/descripción obligatorios; email con expresión regular simple;
  `tipo_servicio` restringido a la lista permitida; adjunto opcional validado
  con `allowed_file` + límite de 10 MB (config `MAX_CONTENT_LENGTH`).
- **Normalización**: `strip()` en todos los campos de texto; email en
  minúsculas para comparar y guardar.

### 1.4 Flujo de la solicitud pública

```
GET /solicitud → formulario (tipo_servicio desde lista fija)
POST /solicitud
  ├─ honeypot con valor → confirmación genérica (sin persistir)
  ├─ rate limit excedido → 429 amable con reintento en N minutos
  ├─ validación fallida → formulario con errores y valores previos
  ├─ archivo válido → guardar en UPLOAD_FOLDER/solicitudes con timestamp
  ├─ cliente por email → crear o reutilizar (id_usuario si el email
  │  coincide con un Usuario registrado)
  └─ Proyecto(estado='solicitado', archivo_solicitud=...) → commit
       → redirect /solicitud/enviada/<id>
```

La invalidación de caché es automática: el `after_commit` de SQLAlchemy ya
invalida dashboard/reportes/portafolio en cualquier INSERT.

## 2. Interfaz (plantillas)

| Plantilla | Contenido |
|---|---|
| `solicitud_publica.html` | Formulario standalone (hereda `layout.html`), mismo estilo que `solicitar_servicio.html`, con honeypot y campos de contacto públicos |
| `solicitud_confirmacion.html` | Número de solicitud, resumen y mensaje de contacto; sin datos sensibles |
| `solicitudes.html` | Tabla de pendientes (fecha, cliente, tipo, proyecto, adjunto) con acciones aprobar/rechazar existentes |
| `detalle_cliente.html` | Datos, tarjetas de totales, tablas de proyectos y facturas, botones de acción |
| `dashboard.html` | Tarjeta «Solicitudes pendientes» con enlace a `/solicitudes` |
| `clientes.html` | Nombre → ficha, búsqueda con teléfono, paginación |
| `layout.html` | Enlace «Solicitudes» (solo admin/gestor) |

Accesibilidad: etiquetas `label for`, mensajes de error junto al campo,
botones con texto (no solo icono), contraste heredado del CSS actual.

## 3. Reglas de negocio y seguridad

- El POST público **ignora** cualquier campo de control (`presupuesto`,
  `estado`, `fechas`, `id_cliente`, `id_usuario`): solo se leen los campos
  permitidos.
- No se revela si un email ya existe (misma respuesta de confirmación).
- `id_usuario` del cliente se asigna únicamente si existe un `Usuario` con
  ese email y el cliente aún no estaba vinculado.
- Eliminar cliente mantiene la regla actual de integridad; la ficha explica
  el bloqueo con enlaces a sus proyectos/facturas.
- RBAC: `/solicitudes` y `/clientes/<id>` redirigen con aviso si el rol no
  es admin/gestor, replicando el patrón `if not (es_admin or es_trabajador)`.

## 4. Datos y rendimiento

- Sin migración: se usan las columnas existentes. No se agrega `origen`
  (evita migración en MySQL y Render); se documenta como mejora futura.
- Ficha de cliente: una consulta de proyectos, una de facturas y una
  agregada de totales (`func.sum` con `case`), evitando N+1.
- Bandeja: filtro por estado + `joinedload(Proyecto.cliente)`.
- Búsqueda: `or_` sobre nombre/apellido/email/teléfono + `paginate`.

## 5. Pruebas (gate por tarea)

Script nuevo `test_sprint4.py` en `C:\Users\L\AppData\Local\Temp\opencode`
(app de prueba con SQLite temporal, patrón de `smoke_test.py`):

1. `GET /solicitud` 200 y contiene los campos esperados.
2. `POST` válido crea cliente + proyecto `solicitado`; confirmación muestra
   el número.
3. `POST` con email existente reutiliza cliente (no duplica).
4. `POST` con un usuario registrado vincula `id_usuario`.
5. Honeypot completo → no crea registros y devuelve confirmación.
6. Cuarto POST en <10 min desde la misma IP → bloqueado (429/mensaje).
7. Campos faltantes → 400/200 con errores y sin registros.
8. Extensión no permitida → error; PDF válido → archivo guardado.
9. `/solicitudes` solo admin/gestor; cliente recibe redirección con aviso.
10. `/clientes/<id>` muestra proyectos, facturas y totales correctos;
    cliente no accede.
11. Búsqueda por teléfono encuentra al cliente; paginación respeta `page`.
12. Regresión: `smoke_test.py`, `test_sprint3_full.py` y `test_sprint3.py`
    en verde; arranque en frío tipo Render (`freshboot_render.py`).

## 6. Despliegue

- `develop` → push a `origin` y al mirror de revisión.
- Render: el formulario funciona con SQLite demo; los adjuntos viven en el
  disco efímero y se pierden en cada redeploy (documentar en `SPRINT_4.md` y
  `GUIA_REVISION.md` si aplica).
- `render.yaml` no cambia.

## 7. Riesgos

| Riesgo | Mitigación |
|---|---|
| Sin CSRF global (primer POST anónimo) | Honeypot + rate limit + validación estricta; se documenta y se evalúa token CSRF simple como mejora |
| Rate limit por proceso (gunicorn multi-worker) | Documentado; el demo corre 1 worker |
| Adjuntos efímeros en Render | Aviso en confirmación y doc |
| ERS no disponible | Spec validada por el usuario; numeración PB-14/PB-15 revisable |
| Duplicado de clientes por email con mayúsculas | Comparación `func.lower` + normalización previa |
