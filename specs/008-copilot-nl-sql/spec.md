# Spec 008 — Sprint 7: Copilot administrativo NL→SQL (PB-12)

> **Estado:** pendiente de aprobación
> **Sprint:** 7 · **Puntos:** 8 (PB-12, última historia de la Fase 2)
> **Depende de:** Sprints 1–6 (datos de clientes, proyectos, facturas,
> inventario y planos)
> **Fase:** 2 (backlog de IA) — el LLM es **opcional**; sin API funciona con
> plantillas

---

## 1. Problema

La directiva depende de reportes fijos: para responder «¿cuál fue el proyecto
de arquitectura con mayor consumo de insumos el mes pasado y su margen?» hay
que pedirle a alguien que consulte la base o exporte a Excel. El dashboard y
`/reportes` muestran métricas predefinidas, no preguntas libres.

El ERS y el backlog piden un **copilot administrativo** que traduzca lenguaje
natural a SQL sobre las tablas existentes, sin abrir la puerta a consultas
peligrosas ni exigir un proveedor de IA para funcionar.

## 2. Objetivos

1. Permitir preguntas en lenguaje natural sobre los datos del negocio y
   devolver **interpretación + tabla de resultados**.
2. Funcionar **sin API key** con 8 preguntas frecuentes predefinidas
   (plantillas), y con **cualquier API compatible con OpenAI** cuando se
   configure.
3. Garantizar **solo lectura**: SELECT, tablas permitidas, `LIMIT` y registro
   de cada consulta.
4. No tocar el esquema ni los flujos existentes.

## 3. Alcance

### Dentro del alcance

- Página `/copilot` (solo admin) con:
  - caja de pregunta libre y 8 chips de preguntas frecuentes;
  - tarjeta de interpretación, SQL ejecutado (desplegable) y tabla de
    resultados;
  - indicador de la fuente (`IA` o `plantilla`), avisos y estado vacío.
- Servicio `copilot.py` (Python puro, sin dependencias nuevas):
  - catálogo de 8 plantillas con SQL e interpretación;
  - cliente HTTP para APIs OpenAI-compatible (`/chat/completions`);
  - validador de SQL y ejecución de solo lectura.
- Configuración por entorno (mismo patrón que `FLASK_CONFIG`):
  `COPILOT_BASE_URL`, `COPILOT_MODEL`, `COPILOT_API_KEY`,
  `COPILOT_TIMEOUT`, `COPILOT_MAX_FILAS`.
- Enlace en el sidebar (Administración) y acción rápida en el dashboard.
- Registro de cada consulta (usuario, pregunta, SQL, filas, fuente) en el log
  de la aplicación.

### Fuera del alcance

- Escribir datos desde el copilot (solo SELECT).
- Historial persistente de conversaciones (sin tabla nueva).
- Gráficos interactivos o generación de PDF desde el copilot (queda para una
  mejora posterior; los reportes PDF existentes siguen igual).
- Modelos locales pesados o fine-tuning.
- Acceso para clientes o trabajadores: métricas sensibles solo admin.

## 4. Historias de usuario y criterios de aceptación

### PB-12 — Copilot administrativo (8 pts)

**Como** directivo, **quiero** preguntar métricas en lenguaje natural **para**
obtener respuestas sin depender de reportes fijos.

Criterios de aceptación:

1. `GET /copilot` (admin) muestra la caja de pregunta y los 8 chips; un
   usuario no admin recibe redirección con aviso.
2. **Sin API configurada**, cada chip devuelve interpretación, SQL y tabla
   con datos reales de la base (plantilla predefinida). El texto libre se
   resuelve por coincidencia de palabras clave; si no coincide, se indica
   qué preguntas sí están disponibles.
3. **Con API configurada**, el servicio envía la pregunta + catálogo de
   tablas al modelo, recibe `{interpretacion, sql}`, valida el SQL y lo
   ejecuta; la respuesta indica fuente «IA».
4. Si el LLM falla (red, timeout, JSON inválido o SQL rechazado), se cae a la
   plantilla más cercana y se informa el motivo, sin error 500.
5. Toda consulta ejecutada:
   - es un único `SELECT` (se rechazan `INSERT/UPDATE/DELETE/DROP/ALTER/
     PRAGMA/ATTACH`, comentarios y múltiples sentencias);
   - usa solo tablas permitidas (sin `usuarios` ni columnas sensibles);
   - lleva `LIMIT` (máximo 200 filas) y se corta si el motor tarda demasiado.
6. La respuesta incluye la **interpretación** («qué entendió») y el **dato
   analítico** (tabla), como pide el backlog.
7. Cada ejecución queda registrada en el log con usuario, pregunta, SQL,
   cantidad de filas y fuente.
8. Las 8 plantillas cubren: facturación del mes, top clientes por facturación,
   proyectos por estado, margen por proyecto, consumo de insumos, solicitudes
   pendientes, inventario en riesgo y planos por tipo.
9. Sin cambios de esquema y sin dependencias Python nuevas.

## 5. Requisitos no funcionales

- **Seguridad:** validación en dos capas (parser propio + catálogo de tablas);
  si `COPILOT_DATABASE_URL` está definida se usa esa conexión (pensada para un
  usuario MySQL de solo lectura); si no, se ejecuta sobre la conexión normal
  con las salvaguardas anteriores. El prompt incluye instrucciones explícitas
  de solo lectura y el esquema permitido. Nunca se envían datos de clientes al
  LLM: solo la pregunta y el esquema.
- **Privacidad:** la API key vive en el entorno, nunca en el repositorio ni en
  la respuesta HTML.
- **Rendimiento:** timeout de 15 s para el LLM y límite de filas; la página no
  consulta nada hasta que el admin pregunta.
- **Portabilidad:** `urllib` de la stdlib para el HTTP; funciona en Windows,
  Render y el G60. Sin internet, el modo plantillas sigue operativo.
- **Documentación:** `docs/SPRINT_7.md`, `docs/ANEXO_IA.md` (evidencias para el
  ERS), fila en `GUIA_REVISION.md` y criterios de PB-12 marcados en
  `BACKLOG_IA.md`.

## 6. Modelo de datos

Sin cambios. El copilot lee de `clientes`, `proyectos`, `facturas`,
`detalle_facturas`, `materiales`, `inventario`, `planos` y `tipos_plano`.
`usuarios` queda fuera del catálogo para no exponer credenciales.

## 7. Criterios de éxito

- Sin API: los 8 chips responden con datos correctos y verificables a mano.
- Con una API compatible: una pregunta libre («facturación de este mes»)
  devuelve interpretación y tabla, con fuente «IA».
- Un intento de `DROP TABLE` o de consultar `usuarios` es rechazado y se
  informa sin ejecutar nada.
- Suites 4, 5, 6 y 7 en verde.

## 8. Riesgos y preguntas abiertas

1. **Sin API en la demo:** el jurado verá el modo plantillas; basta para
   cumplir el criterio del backlog, y el modo IA se demuestra con una clave
   temporal si hay internet.
2. **SQL generado por el modelo:** puede ser válido pero semánticamente
   incorrecto; la interpretación visible permite detectarlo. Se mitiga con
   temperatura 0 y un catálogo de esquema explícito.
3. **SQLite vs MySQL:** las plantillas usan SQL compatible con ambos
   (`strftime` se evita; se usan rangos de fechas calculados en Python).
4. **Consultas costosas:** el límite de filas y el timeout no evitan un
   `CROSS JOIN` grande; el catálogo permite solo tablas pequeñas y el
   validador exige `LIMIT`. Se documenta como mejora el `EXPLAIN` previo.
