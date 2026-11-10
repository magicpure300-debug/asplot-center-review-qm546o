# ASPLOT CENTER — Sprint 7: Copilot administrativo NL→SQL

> **PB-12 (8 puntos) — última historia de la Fase 2 del backlog de IA**
> El LLM es una capa **opcional**: sin API key el copilot funciona con
> 8 plantillas deterministas, sin internet y sin dependencias nuevas.

---

## Qué se construyó

**Página `/copilot`** (solo administrador): caja de pregunta libre, chips
de preguntas frecuentes, tarjeta de interpretación, SQL ejecutado en un
`<details>` y tabla de resultados. Enlace en el sidebar (Administración) y
acción rápida «Preguntar al copilot» en el dashboard.

**Módulo `copilot.py`** (Python puro, sin dependencias nuevas):

| Componente | Función |
|---|---|
| `PLANTILLAS` (8) | preguntas frecuentes → SQL + interpretación, con fechas calculadas en Python (compatible SQLite/MySQL) |
| `resolver_plantilla` | coincidencia exacta con el ejemplo + puntuación por palabras clave (sin acentos) |
| `validar_sql` | solo `SELECT`/`WITH`; rechaza escritura, comentarios y sentencias múltiples; catálogo cerrado de tablas; fuerza `LIMIT` |
| `llamar_llm` | `urllib` a `{COPILOT_BASE_URL}/chat/completions`, `temperature 0`, timeout configurable |
| `responder` | IA → validar → ejecutar; ante cualquier fallo cae a plantilla con aviso (nunca 500) |

### Las 8 plantillas

| id | Pregunta | Consulta |
|---|---|---|
| `facturacion_mes` | Facturación del mes | `COUNT` + `SUM(total)` de facturas no canceladas desde el día 1 |
| `top_clientes` | Top clientes | facturado por cliente, `ORDER BY SUM(total) DESC` |
| `proyectos_estado` | Proyectos por estado | `GROUP BY estado` |
| `margen_proyecto` | Margen por proyecto | facturado − costo de insumos (precio de compra) |
| `consumo_insumos` | Consumo de insumos del mes | `SUM(cantidad)` por material |
| `solicitudes_pendientes` | Solicitudes pendientes | proyectos `solicitado` con cliente y fecha |
| `inventario_riesgo` | Inventario en riesgo | stock ≤ mínimo, con faltante |
| `planos_tipo` | Planos por tipo | `GROUP BY nombre_tipo` |

## Seguridad

1. **Validador en dos capas:** parser propio (SELECT/WITH, sin verbos de
   escritura, sin comentarios, una sola sentencia) + catálogo cerrado de
   tablas. La tabla **`usuarios` está fuera** del catálogo.
2. **`LIMIT` forzado** al envolver la consulta:
   `SELECT * FROM (<sql>) AS copilot_resultado LIMIT 200`.
3. **Timeout** de 15 s en la llamada al LLM y `fetchmany` acotado.
4. **`COPILOT_DATABASE_URL` opcional** para usar un usuario MySQL de solo
   lectura; sin ella se usa la conexión principal con las salvaguardas
   anteriores.
5. **Privacidad:** al LLM solo se envían la pregunta y el esquema, nunca
   datos de clientes. La API key vive únicamente en el entorno.
6. **Auditoría:** cada ejecución registra en el log usuario, pregunta, SQL,
   cantidad de filas y fuente (`ia`/`plantilla`).

## Configuración

| Variable | Default |
|---|---|
| `COPILOT_BASE_URL` | `https://api.openai.com/v1` |
| `COPILOT_MODEL` | `gpt-4o-mini` |
| `COPILOT_API_KEY` | *(vacío → modo plantillas)* |
| `COPILOT_TIMEOUT` | 15 s |
| `COPILOT_MAX_FILAS` | 200 |
| `COPILOT_DATABASE_URL` | *(vacío → conexión principal)* |

Cualquier proveedor compatible con OpenAI sirve (OpenAI, DeepSeek, Groq,
Together, Ollama local). Documentado en `.env.example`.

## Pruebas

Suite `test_sprint7.py` (copia limpia con SQLite propio):
**63 comprobaciones en verde**.

- **Validador:** acepta SELECT/WITH (incluye CTE), rechaza `DROP`, `DELETE`,
  `UPDATE`, tabla `usuarios`, sentencias múltiples, comentarios, `OUTFILE` y
  consultas vacías; agrega `LIMIT`; las 8 plantillas se pre-validan.
- **Resolución:** texto libre → plantilla correcta; sin coincidencia →
  sugerencias sin ejecutar SQL.
- **RBAC:** anónimo → login; cliente → dashboard; admin → 200.
- **Sin API:** los 8 chips devuelven interpretación, SQL y tabla con datos
  reales sembrados (facturas del mes, cliente top, margen, consumo,
  pendientes, riesgo de inventario y planos por tipo).
- **LLM simulado:** respuesta válida → fuente «IA»; SQL prohibido, tabla
  fuera de catálogo, error de red y JSON inválido → fallback a plantilla
  con aviso, siempre 200.
- **Auditoría:** la línea `COPILOT usuario=… fuente=… filas=… pregunta=…
  sql=…` queda en el log.
- **Regresión:** suites de Sprints 5 y 6 y smoke de diseño en verde.

## Despliegue

- Copiado al G60: `copilot.py`, `app.py`, `config.py`, `style.css`,
  `templates/copilot.html`, `layout.html`, `dashboard.html`.
- Reinicio del servicio y prueba del modo plantillas por LAN y túnel.
- `docs/ANEXO_IA.md` recoge las evidencias para el ERS.

## Decisiones técnicas

| Decisión | Motivo |
|---|---|
| Proveedor OpenAI-compatible | Un solo cliente HTTP cubre OpenAI, DeepSeek, Groq y Ollama sin cambiar código |
| Plantillas deterministas | El backlog exige funcionar sin API; además permite demostrar sin internet |
| Validador propio (no solo el LLM) | El modelo puede alucinar SQL; la seguridad no se delega al prompt |
| `urllib` de la stdlib | Sin dependencias nuevas; funciona en Windows, Render y el G60 |
| Sin tabla de historial | El backlog prohíbe cambios de esquema; el log cubre la auditoría |

## Limitaciones documentadas

- **Sin API en la demo:** el jurado ve el modo plantillas; el modo IA se
  demuestra con una clave temporal.
- **SQL semánticamente incorrecto del LLM:** posible; la interpretación
  visible permite detectarlo y el validador bloquea lo peligroso.
- **Consultas costosas:** el `LIMIT` no evita un `CROSS JOIN` grande; el
  catálogo de tablas pequeñas y el timeout lo mitigan (mejora futura:
  `EXPLAIN` previo).
- **Historial de conversaciones:** no persistente (sin migración).
