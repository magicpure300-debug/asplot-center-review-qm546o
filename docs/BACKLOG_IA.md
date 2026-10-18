# ASPLOT CENTER — Backlog de Inteligencia Artificial (Fase 2)

> **Origen:** observaciones del docente en la revisión del ERS (18/10/2026) sobre
> integración de agentes de IA (RAG, visión por computador y LLM).
> **Principio rector:** los agentes se implementan como una **capa aditiva** sobre los
> datos y rutas existentes —sin modificar el esquema ni los flujos comprometidos— y en
> una **fase 2 posterior a los nueve sprints** del proyecto, de modo que no se compromete
> el objetivo de entrega. Primero componentes **deterministas** que producen datos
> estructurados; el componente LLM/RAG o de aprendizaje automático se enchufa después
> sin reingeniería.

---

## Resumen

| HU | Agente | CUs | Esfuerzo | Dependencias | Fase |
|---|---|---|---|---|---|
| PB-10 | Cubicación y cotización automática | CU10, CU14 | 8 pts | Sprint 4 (solicitudes online) | 2 |
| PB-11 | Predictivo de inventario | CU19, CU21 | 5 pts | Módulo de inventario (existe) | 2 |
| PB-12 | Copilot administrativo NL→SQL | CU29, CU37, CU38 | 8 pts | Reportes/dashboard (existente) + API LLM | 2 |
| PB-13 | Control de calidad de planos | CU13, CU20 | 3 pts | Módulo de planos (existe) | 2 |

Total estimado fase 2: **~24 puntos**.

---

## PB-10 — Agente de cubicación y cotización automática (8 pts)

**Como** cliente que sube un plano,
**quiero** que el sistema estime automáticamente el área de impresión y genere una
cotización,
**para** agilizar la respuesta comercial sin intervención manual inmediata.

- **Versión v1 (determinista, sin LLM):**
  - Extracción de dimensiones de página/contenido en **PDF** con PyMuPDF.
  - Lectura de extensiones y geometría en **DXF** con `ezdxf` (biblioteca abierta).
  - Cálculo de área de impresión (m²) según rollo/papel estándar (A0–A4).
  - Estimación de consumo de insumos con la tabla `materiales` + `inventario` existente.
  - Cotización automática (área × precio + insumos + margen) ligada a la solicitud.
- **Versión v2 (fase posterior):** componente LLM+RAG sobre los datos estructurados de
  la v1 para interpretar planos no normalizados.
- **Fuera de alcance v1:** formato **.DWG** (propietario; requiere conversor ODA) — se
  cubre PDF/DXF, que es el flujo de subida del sistema.

### Criterios de aceptación
- [ ] Con un PDF estándar (A0–A4), el sistema extrae el tamaño correcto sin intervención.
- [ ] Con un DXF, calcula la extensión del dibujo y la convierte a m² de impresión.
- [ ] La cotización resultante se registra como propuesta de precio en la solicitud.
- [ ] Si el formato no es analizable, el sistema lo indica y deja la cotización manual.

---

## PB-11 — Agente predictivo de inventario (5 pts)

**Como** administrador,
**quiero** alertas de reabastecimiento basadas en la velocidad de consumo real,
**para** evitar paradas por falta de papel o tinta.

- **Versión v1 (reglas, sin ML):**
  - Velocidad de consumo por material: unidades/día = consumo histórico ÷ días.
  - Punto de reorden y stock de seguridad por material.
  - Ajuste por proyectos activos (estado `en_progreso` → mayor demanda esperada).
  - Alerta tipo: *"Papel A0: stock se agota en ~12 días según velocidad actual"*.
  - Sugerencia de orden de compra con cantidad económica (EOQ simplificado).
- **Versión v2 (fase posterior):** modelos de series temporales cuando exista histórico
  suficiente de consumo (alimentados por las mismas métricas de la v1).

### Criterios de aceptación
- [ ] Panel de inventario muestra materiales en zona de riesgo con días estimados.
- [ ] El cálculo usa solo datos de facturas/movimientos existentes (sin nuevas tablas).
- [ ] Las alertas se pueden silenciar/marcar como atendidas.

---

## PB-12 — Copilot administrativo: métricas en lenguaje natural (8 pts)

**Como** directivo,
**quiero** preguntar métricas en lenguaje natural (ej. *"proyecto de arquitectura con
mayor consumo de insumos el mes pasado y su margen"*),
**para** obtener respuestas analíticas sin depender de reportes fijos.

- **Versión v1:**
  - Servicio NL→SQL con proveedor LLM **configurable por variable de entorno** (mismo
    patrón que `FLASK_CONFIG=mysql`), de modo que sin API el módulo queda desactivado.
  - Conexión con usuario de base de datos **solo lectura**, sentencia acotada con
    `LIMIT`, catálogo de tablas permitidas (protección contra prompt injection/SQL libre).
  - **Plantillas de respaldo sin LLM:** preguntas frecuentes mapeadas a consultas
    predefinidas (funciona sin internet ni presupuesto).
- **Fuera de alcance:** modelos locales de gran tamaño (requieren GPU/operación pesada
  para este despliegue).

### Criterios de aceptación
- [ ] Sin API configurada, el módulo responde con las plantillas de respaldo.
- [ ] Con API configurada, traduce consultas de lenguaje natural a SQL válido y limitado.
- [ ] Toda consulta ejecutada es de solo lectura y queda registrada en log.
- [ ] La respuesta incluye la interpretación (qué entendió) y el dato analítico.

---

## PB-13 — Control de calidad de planos (3 pts)

**Como** trabajador de taller,
**quiero** una validación automática antes de plotear,
**para** reducir desperdicio de material por archivos deficientes.

- **Versión v1 (determinista, sin IA):**
  - Resolución/DPI mínima en mapas de bits (Pillow).
  - Formato declarado vs. real (extensión vs. contenido).
  - Tamaño de página vs. estándares de papel (A0–A4) y detección de páginas atípicas.
  - Resultado visible en el detalle del plano como checklist ("advertencias").
- **Versión v2 (diferida expresamente):** agente de visión por computador (OpenCV/YOLO)
  para detectar líneas superpuestas, tramado deficiente, texto fuera de margen y escalas
  no estandarizadas. **Requiere** dataset de defectos anotado + ciclo de
  entrenamiento/validación (equiparable a un proyecto de investigación); se difiere por
  comprometer el objetivo del proyecto.

### Criterios de aceptación
- [ ] Subir una imagen de baja resolución genera una advertencia automática.
- [ ] Un PDF cuyo contenido no coincide con la extensión declarada genera advertencia.
- [ ] La verificación no bloquea la subida, solo informa (no degrada el flujo).

---

## Reglas transversales de implementación

1. **Sin reingeniería:** ninguna HU de IA modifica el esquema existente; se agregan como
   rutas/servicios nuevos sobre las tablas actuales.
2. **Determinismo primero:** toda funcionalidad funciona sin servicios externos; el LLM
   es una capa opcional detrás de una variable de entorno.
3. **Seguridad:** cualquier generación SQL usa usuario solo lectura, `LIMIT` y catálogo
   de tablas permitidas; las claves de API nunca se versionan (solo `.env.example`).
4. **Trazabilidad:** los agentes solo sugieren; las decisiones comerciales (precio final,
   orden de compra) siguen siendo humanas.

---

*Relacionado:* `docs/GUIA_REVISION.md`, `docs/SPRINT_2.md`, `docs/SPRINT_3.md`.
Anexo A del ERS (§A.3) resume estas historias para la entrega académica.
