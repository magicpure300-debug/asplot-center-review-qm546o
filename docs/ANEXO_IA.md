# Anexo — Observaciones del ERS y estado de la IA en ASPLOT CENTER

> Documento de evidencias para la defensa. Responde **punto por punto** a
> las observaciones de revisión del ERS y al uso de agentes de IA, con la
> implementación real (rutas, módulos, pruebas y documentación).

---

## Parte A — Correcciones de concepto en el ERS

### A.1. DBMS vs ORM

| Observación | Respuesta | Evidencia |
|---|---|---|
| «La base de datos… será SQLALCHEMY» debe redactarse como MySQL 8.0 (DBMS) + SQLAlchemy (ORM) | **Corregido.** MySQL 8.0 es el Sistema Gestor de Base de Datos; SQLAlchemy es el ORM de la capa de persistencia en Python/Flask; PyMySQL es el driver. | `config.py` (`mysql+pymysql://…`), `docs/MIGRACION_MYSQL.md`, `requirements.txt` (`SQLAlchemy`, `PyMySQL`) |

**Redacción recomendada para el ERS:** «La persistencia se implementa sobre
el Sistema Gestor de Base de Datos MySQL 8.0; el acceso a datos desde
Flask se realiza mediante el ORM SQLAlchemy (driver PyMySQL), con SQLite
como motor de respaldo para desarrollo y demostración.»

### A.2. Almacenamiento de planos (.DWG / .PDF)

| Observación | Respuesta | Evidencia |
|---|---|---|
| En MySQL solo metadatos y rutas; los binarios en el sistema de archivos (o S3/blob) | **Implementado así.** La tabla `planos` guarda el nombre relativo del archivo (`archivo`); los PDF/DXF/DWG viven en `static/uploads/planos/` y los adjuntos de solicitudes en `static/uploads/planos/solicitudes/`. Ningún binario se almacena en la base. | `models.py` (`Plano.archivo`), `app.py` (subida y `UPLOAD_FOLDER`), `config.py` (`UPLOAD_FOLDER`) |

**Redacción recomendada para el ERS:** «En MySQL se almacenan únicamente
los metadatos del plano y la ruta relativa del archivo; los archivos
binarios residen en el sistema de archivos del servidor (con posibilidad
de migrar a un bucket S3/blob sin cambiar el esquema), evitando degradar
el rendimiento del motor SQL.»

> **Nota de alcance:** el demo del G60 usa disco local. La abstracción por
> ruta relativa permite mover el almacenamiento a S3/blob sin cambios de
> base de datos.

---

## Parte B — Los cuatro agentes de IA

La plataforma se diseñó con una arquitectura **aditiva**: cada agente se
implementa como servicio/módulo nuevo sobre las tablas existentes, **sin
migraciones ni reingeniería**, y con el humano siempre decidiendo. Donde
el ERS propone LLM/visión/ML, se entregó primero una **v1 determinista y
operativa** (funciona sin API, sin GPU y sin internet) y la v2 avanzada
queda explícitamente diferida en el backlog.

### B.1. Agente de cubicación y cotización automática (CU10, CU14)

| | |
|---|---|
| **Observación del ERS** | LLM + RAG que analice PDF/DXF/DWG, extraiga dimensiones, calcule área, consumo e insumos y cotice sin intervención humana. |
| **Hecho (v1 — Sprint 5)** | Análisis de PDF (`pypdf`) y DXF (lector propio de `$EXTMIN`/`$EXTMAX`), cálculo de área en m², insumos proporcionales, tarifa + margen y **propuesta de precio** en el formulario de cotización. El humano confirma. |
| **Pendiente (v2)** | LLM/RAG para planos no normalizados y soporte de DWG (formato propietario). |
| **Evidencia** | `cotizador_auto.py`, `POST /proyectos/<id>/cotizacion-automatica`, botón «Calcular automáticamente» en `aprobar_proyecto.html`, `docs/SPRINT_5.md`, `specs/005-cotizacion-automatica/`, suite `test_sprint5.py` |

### B.2. Agente de control de calidad visual (CU13, CU20)

| | |
|---|---|
| **Observación del ERS** | Visión por computador (OpenCV/YOLO) para detectar líneas superpuestas, tramado deficiente, texto fuera de margen y escalas no estándar. |
| **Hecho (v1 — Sprint 6)** | Checklist de calidad: formato declarado vs. real (firmas de bytes), DPI en JPG/PNG sin Pillow, tamaño de página A0–A4 en PDF y detección de archivos corruptos. Avisa sin bloquear la subida. |
| **Pendiente (v2)** | Visión por computador real (OpenCV/YOLO): requiere un dataset de defectos anotado y ciclo de entrenamiento/validación. |
| **Evidencia** | `calidad_planos.py`, checklist en `detalle_plano.html`, avisos al subir, `docs/SPRINT_6.md`, `specs/006-inventario-calidad/`, suite `test_sprint6.py` |

### B.3. Agente predictivo de inventario y cadena de suministro (CU19, CU21)

| | |
|---|---|
| **Observación del ERS** | Análisis de series temporales del consumo de papel, bobinas y tintas; alertas predictivas y órdenes de compra óptimas. |
| **Hecho (v1 — Sprint 6)** | Velocidad de consumo desde facturas (ventana de 90 días), ajuste por proyectos activos, punto de reorden, días restantes, compra sugerida y silencio persistente de alertas. Panel en `/inventario`. |
| **Pendiente (v2)** | Modelo de series temporales, EOQ completo e integración con proveedores. |
| **Evidencia** | `inventario_predictivo.py`, panel en `/inventario`, `instance/inventario_alertas.json`, `docs/SPRINT_6.md`, `specs/006-inventario-calidad/`, suite `test_sprint6.py` |

### B.4. Copilot administrativo y reportes en lenguaje natural (CU29, CU37, CU38)

| | |
|---|---|
| **Observación del ERS** | Agente conversacional que traduzca preguntas de la directiva a SQL optimizado sobre MySQL y devuelva el análisis al instante. |
| **Hecho (v1 — Sprint 7)** | Página `/copilot` (solo admin): 8 plantillas deterministas sin API + proveedor OpenAI-compatible opcional; validador de SQL de solo lectura con catálogo cerrado de tablas; interpretación, SQL y tabla; auditoría en el log. |
| **Pendiente (v2)** | Historial de conversaciones persistente, gráficos y generación de PDF desde el copilot. |
| **Evidencia** | `copilot.py`, `GET/POST /copilot`, `templates/copilot.html`, `docs/SPRINT_7.md`, `specs/008-copilot-nl-sql/`, suite `test_sprint7.py` |

---

## Parte C — Tabla resumen de cobertura

| Agente | Historia | v1 determinista | Desplegado en G60 | v2 avanzada |
|---|---|---|---|---|
| Cubicación y cotización | PB-10 | ✅ Sprint 5 | ✅ | ⏳ LLM/RAG + DWG |
| Calidad visual | PB-13 | ✅ Sprint 6 | ✅ | ⏳ OpenCV/YOLO |
| Inventario predictivo | PB-11 | ✅ Sprint 6 | ✅ | ⏳ Series temporales/EOQ |
| Copilot NL→SQL | PB-12 | ✅ Sprint 7 | ✅ | ⏳ Historial/gráficos |

**Cobertura:** 4 de 4 agentes con v1 funcional; **0 de 4** requieren un
proveedor de IA para operar (el LLM es opcional en PB-12 y la visión/ML
queda como v2 explícita). Sin cambios de esquema en ninguna historia.

---

## Parte D — Reglas de diseño de la capa de IA

1. **Sin reingeniería:** los agentes son módulos/rutas nuevas sobre las
   tablas existentes; no se modifica el esquema.
2. **Determinismo primero:** todo funciona sin servicios externos; el LLM
   es una capa opcional detrás de variables de entorno.
3. **Seguridad:** SQL de solo lectura, catálogo cerrado de tablas, `LIMIT`
   y auditoría; claves solo en el entorno (`.env.example` sin valores).
4. **Humano en el bucle:** el sistema sugiere (precio, compra, alertas);
   la persona decide. Ningún agente escribe datos por sí solo.
5. **Portabilidad:** Python puro + `urllib`; funciona en Windows, Render y
   el servidor casero (Termux/Android) sin dependencias nativas pesadas.
