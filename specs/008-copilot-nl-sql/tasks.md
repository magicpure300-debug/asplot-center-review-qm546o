# Tareas 008 — Sprint 7: Copilot NL→SQL (PB-12)

> **Spec:** `specs/008-copilot-nl-sql/spec.md`
> **Plan:** `specs/008-copilot-nl-sql/plan.md`
> **Regla SDD:** una tarea a la vez; tests primero, código después; parada
> para validación humana.

- [x] **T1. Configuración y catálogo de plantillas**
  - RF: CA2, CA8.
  - Constantes `COPILOT_*` en `config.py`; `PLANTILLAS` (8) con SQL
    compatible SQLite/MySQL, interpretación y palabras clave;
    `resolver_plantilla` con normalización de acentos.
  - Hecho: cada plantilla devuelve SQL y parámetros; el texto «facturación del
    mes» resuelve la plantilla correcta.

- [x] **T2. Validador de SQL y ejecución segura**
  - RF: CA5.
  - `validar_sql` (SELECT/WITH, sin escritura, sin comentarios, tablas
    permitidas, `LIMIT` forzado) y `ejecutar` inyectado con `fetchmany`.
  - Hecho: rechaza `DROP`, `DELETE`, `usuarios`, múltiples sentencias y
    comentarios; acepta los 8 SQL de plantilla; agrega el límite.

- [x] **T3. Cliente LLM y orquestador con fallback**
  - RF: CA3, CA4, CA6.
  - `llamar_llm` (urllib, JSON estricto, timeout) y `responder` (IA → validar
    → ejecutar; error → plantilla → mensaje).
  - Hecho: con un stub válido devuelve fuente `ia`; con SQL inválido o error
    de red cae a plantilla con aviso, sin excepción.

- [x] **T4. Ruta `/copilot`, RBAC y logging**
  - RF: CA1, CA4, CA7, CA9.
  - Ruta GET/POST solo admin; ejecutor con `COPILOT_DATABASE_URL` opcional;
    log de usuario, pregunta, SQL, filas y fuente.
  - Hecho: admin recibe 200; cliente/anónimo redirigen; la línea de log
    aparece al preguntar.

- [x] **T5. Interfaz y navegación**
  - RF: CA1, CA2, CA3.
  - `copilot.html` con chips, interpretación, SQL desplegable y tabla;
    enlace en Administración y acción rápida en dashboard.
  - Hecho: los chips y el formulario funcionan en navegador; el modo
    plantillas se indica cuando no hay API.

- [x] **T6. Suite `test_sprint7.py` y regresión**
  - RF: todos los CA.
  - Hecho: 10 grupos del plan en verde; suites 4/5/6 y smoke de diseño sin
    regresiones.

- [x] **T7. Documentación y anexo de evidencias**
  - RF: RNF documentación.
  - `docs/SPRINT_7.md`, `docs/ANEXO_IA.md` (observaciones del ERS → qué se
    hizo → evidencia), `GUIA_REVISION.md`, `BACKLOG_IA.md` (PB-12 marcado).
  - Hecho: anexo con tabla completa y enlaces a specs, rutas y pruebas.

- [ ] **T8. Despliegue y verificación en el G60**
  - RF: RNF portabilidad.
  - Push a `origin`/`review`, copia al G60, reinicio y prueba real del modo
    plantillas (y del modo IA si hay clave temporal).
  - Hecho: `/asplot/copilot` responde 200 con sesión admin; un chip devuelve
    tabla; suites en verde en el teléfono.
