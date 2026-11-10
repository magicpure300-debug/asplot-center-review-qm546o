# Plan técnico 008 — Sprint 7: Copilot NL→SQL (PB-12)

> **Spec:** `specs/008-copilot-nl-sql/spec.md` (pendiente de aprobación)
> **Estrategia:** módulo `copilot.py` (Python puro, sin dependencias nuevas) +
> una ruta `/copilot` + plantilla. El LLM es opcional; las 8 plantillas
> funcionan siempre.

---

## 1. Arquitectura

| Componente | Responsabilidad |
|---|---|
| `copilot.py` | Catálogo de plantillas, resolución por palabras clave, prompt y cliente HTTP OpenAI-compatible, validador de SQL, orquestador con fallback. |
| `POST /copilot` | RBAC admin, ejecuta la consulta con la conexión de la app (o la de solo lectura si está configurada), registra en log y renderiza. |
| `templates/copilot.html` | Pregunta libre, chips, interpretación, SQL desplegable y tabla dinámica. |
| Constantes `COPILOT_*` | `config.py` con defaults y override por entorno. |

### 1.1 API del módulo

```
PLANTILLAS: [{id, etiqueta, ejemplo, palabras, interpretacion, consulta(hoy) -> (sql, params)}]

resolver_plantilla(texto) -> plantilla | None
validar_sql(sql, max_filas) -> (ok, sql_envuelto, error)
llamar_llm(pregunta, config) -> {'interpretacion', 'sql'}   # urllib, timeout
responder(pregunta, ejecutar, config) -> {
    ok, fuente ('ia'|'plantilla'), interpretacion, sql, columnas, filas,
    aviso, mensaje, sugerencias
}
```

`ejecutar(sql, params) -> (columnas, filas)` lo inyecta `app.py`; así el
módulo no depende de Flask y se testea aislado.

## 2. Plantillas (8)

| id | Pregunta | Consulta |
|---|---|---|
| `facturacion_mes` | Facturación del mes | `COUNT` + `SUM(total)` de facturas no canceladas desde el día 1 |
| `top_clientes` | Top clientes por facturación | `JOIN clientes` + `GROUP BY` + `ORDER BY SUM(total) DESC` |
| `proyectos_estado` | Proyectos por estado | `GROUP BY estado` con conteo |
| `margen_proyecto` | Margen por proyecto | facturado − costo de insumos (`detalle_factura × precio_compra`) |
| `consumo_insumos` | Consumo de insumos del mes | `SUM(cantidad)` por material desde el día 1 |
| `solicitudes_pendientes` | Solicitudes pendientes | proyectos `solicitado` con cliente y fecha |
| `inventario_riesgo` | Inventario en riesgo | materiales con `cantidad <= stock_minimo` |
| `planos_tipo` | Planos por tipo | `JOIN tipos_plano` + `GROUP BY` |

Las fechas se calculan en Python y se pasan como parámetros (compatible
SQLite/MySQL). La coincidencia usa texto normalizado (sin acentos, minúsculas)
y puntúa palabras clave; sin coincidencia devuelve la lista de chips.

## 3. Seguridad del SQL

1. Limpieza: sin `;` interno, sin comentarios (`--`, `/*`, `#`).
2. Debe empezar por `SELECT` o `WITH`.
3. Rechaza verbos de escritura/DDL (`INSERT`, `UPDATE`, `DELETE`, `DROP`,
   `ALTER`, `CREATE`, `ATTACH`, `PRAGMA`, …).
4. Tablas extraídas de `FROM`/`JOIN` y comparadas contra catálogo:
   `clientes, proyectos, facturas, detalle_facturas, materiales, inventario,
   planos, tipos_plano`. **`usuarios` queda fuera.** Los CTE (`WITH x AS …`)
   se tratan como alias locales permitidos.
5. Se envuelve como `SELECT * FROM (<sql>) AS copilot_resultado LIMIT 200`
   (tope configurable) para garantizar el límite incluso si el modelo no lo
   puso.
6. Ejecución con `text()` y parámetros; `fetchmany(max_filas)`; errores de
   motor → mensaje controlado.
7. Si `COPILOT_DATABASE_URL` existe se usa un motor aparte (usuario MySQL de
   solo lectura); si no, el motor normal con las validaciones anteriores.

## 4. Cliente LLM (OpenAI-compatible)

- `POST {COPILOT_BASE_URL}/chat/completions` con `urllib.request`, timeout
  `COPILOT_TIMEOUT` (15 s), `temperature: 0`, `model: COPILOT_MODEL`.
- Mensajes: sistema (rol de analista, esquema permitido, reglas de solo
  lectura, respuesta JSON estricta) + usuario (la pregunta).
- Respuesta esperada: `{"interpretacion": "...", "sql": "SELECT ..."}`.
  Se toleran bloques ```json```; si el JSON es inválido → excepción → fallback.
- Sin `COPILOT_API_KEY` no se hace ninguna llamada de red.

## 5. Interfaz

- `GET /copilot`: encabezado, aviso de modo («IA configurada» o «modo
  plantillas»), caja de texto, botón «Preguntar» y chips.
- Resultado:
  - badge de fuente (`IA` / `Plantilla`);
  - interpretación;
  - aviso si hubo fallback;
  - `<details>` con el SQL ejecutado;
  - tabla dinámica (columnas del cursor, valores formateados);
  - estado vacío y mensaje con sugerencias si no hay coincidencia.
- Sidebar: enlace «Copilot» en Administración (solo admin).
- Dashboard: acción rápida «Preguntar al copilot» (solo admin).

## 6. Configuración

| Constante | Env var | Default |
|---|---|---|
| `COPILOT_BASE_URL` | `COPILOT_BASE_URL` | `https://api.openai.com/v1` |
| `COPILOT_MODEL` | `COPILOT_MODEL` | `gpt-4o-mini` |
| `COPILOT_API_KEY` | `COPILOT_API_KEY` | `None` |
| `COPILOT_TIMEOUT` | `COPILOT_TIMEOUT` | `15` |
| `COPILOT_MAX_FILAS` | `COPILOT_MAX_FILAS` | `200` |
| `COPILOT_DATABASE_URL` | `COPILOT_DATABASE_URL` | `None` (usa la principal) |

`.env.example` documentado; la clave nunca se versiona.

## 7. Pruebas (gate por tarea)

`test_sprint7.py`:

1. Validador: acepta SELECT/WITH; rechaza `DROP`, `DELETE`, `usuarios`,
   múltiples sentencias y comentarios; agrega `LIMIT`.
2. Sin API: los 8 chips responden con interpretación, SQL y tabla.
3. Texto libre «facturación del mes» → plantilla correcta.
4. Texto sin coincidencia → mensaje con sugerencias, sin ejecutar SQL.
5. LLM simulado (monkeypatch) válido → fuente `ia` y SQL ejecutado.
6. LLM simulado con SQL prohibido → fallback a plantilla + aviso.
7. LLM con error de red → fallback sin 500.
8. RBAC: cliente y anónimo no acceden.
9. Log: la consulta queda registrada (captura de `app.logger`).
10. Regresión suites 4/5/6 y smoke de diseño.

## 8. Despliegue

- Push a `origin`/`review`; copiar `copilot.py`, `app.py`, `config.py`,
  `templates/copilot.html`, `templates/layout.html`,
  `templates/dashboard.html` al G60; reiniciar `asplot`.
- Probar en el G60 el modo plantillas (no requiere clave) y, si el usuario
  facilita una clave temporal, el modo IA.
- `docs/SPRINT_7.md` + `docs/ANEXO_IA.md` (evidencias ERS) + filas en
  `GUIA_REVISION.md`.

## 9. Riesgos

| Riesgo | Mitigación |
|---|---|
| SQL semánticamente incorrecto del LLM | Interpretación visible + temperatura 0 + fallback |
| Prompt injection | Catálogo cerrado de tablas + validador + solo lectura |
| Sin internet en la demo | 8 plantillas deterministas |
| Consulta costosa | LIMIT 200 + timeout + tablas pequeñas |
| Clave API en el repo | Solo entorno; `.env.example` sin valor |
