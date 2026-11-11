# ASPLOT CENTER — Guion de defensa

> Documento de apoyo para la presentación del proyecto. Ordena qué decir,
> qué mostrar y qué responder. No sustituye a la demo: la demo manda.
>
> Credenciales de la demo: se entregan por separado (no van en el repo).
> Admin: `admin@asplot.com`. Clave en `~/asplot.env` del G60.

---

## 1. Resumen de 30 segundos

ASPLOT CENTER es un sistema web para una empresa de impresión de planos que
digitaliza el ciclo completo: el cliente solicita en línea, el taller cotiza
(con cálculo automático desde el PDF/DXF), produce, factura y controla
insumos. Sobre esa base se añadieron **cuatro agentes de IA deterministas**
—cotización, calidad de planos, inventario predictivo y copilot NL→SQL— que
funcionan **sin depender de una API externa**, con el humano siempre decidiendo.

**Frase para abrir:** «No hicimos una demo de IA: hicimos un sistema de
gestión real, y la IA entra como una capa opcional que se puede apagar sin
romper nada.»

---

## 2. Cifras y evidencias (para citar sin dudar)

| Dato | Valor |
|---|---|
| Sprints entregados | 1 a 7 (+ rediseño visual «blueprint») |
| Historias de IA | PB-10, PB-11, PB-12, PB-13 |
| Pruebas automatizadas | 26 (Sprint 5) + 31 (Sprint 6) + 63 (Sprint 7) + smoke de diseño |
| Dependencias nativas añadidas | Ninguna (Python puro + `pypdf` para PDF) |
| Cambios de esquema en Fase 2 | Ninguno |
| Despliegue | Servidor casero G60 (Termux/Android) con nginx + gunicorn |
| Repositorio | `develop` público en espejo; `main` reservado a producción |
| Documentación | `docs/SPRINT_N.md`, `docs/ANEXO_IA.md`, `specs/00N-…` (SDD) |

---

## 3. Antes de empezar (checklist de 3 minutos)

1. Abrir la URL del túnel o la LAN y comprobar que carga `/asplot/login`.
2. Confirmar que hay datos: dashboard con facturas del mes (646,00) y
   clientes; si todo está a cero, ejecutar `scripts/demo_datos.py` en el G60.
3. Tener a mano dos pestañas: la app y este guion.
4. Probar una vez el copilot (chip «Facturación del mes») para precalentar.
5. Plan B listo: capturas en el móvil y suites locales.

> Si el túnel cambió de URL, se lee del bot (`/links`) o de
> `~/links.estado.json` en el G60. La LAN (`http://192.168.0.101:8000/asplot/`)
> no depende de internet.

---

## 4. Recorrido de demo (10–12 minutos)

### 4.1. Entrada pública (1 min)
- **`/`**: landing con la identidad «blueprint».
- **`/solicitud`**: el cliente pide un servicio **sin cuenta**, adjunta el
  plano y recibe seguimiento. Esto es PB-14 (Sprint 4).
- Mensaje: «El cliente entra por aquí; no hace falta crear usuario».

### 4.2. Panel del administrador (2 min)
- Login → **dashboard**: alertas accionables (solicitudes nuevas, inventario en
  riesgo), accesos rápidos.
- **`/solicitudes`**: bandeja con la solicitud recién creada; aprobar/cotizar.
- **Ficha 360 del cliente**: proyectos, facturas y historial en una vista.

### 4.3. Cotización automática — PB-10 (2 min)
- Abrir un proyecto → **«Calcular automáticamente»**.
- Mostrar el panel de desglose: área detectada del PDF/DXF, insumos, tarifa,
  margen y **precio sugerido**.
- Frase clave: «El sistema **sugiere**; el humano aprueba o corrige. No
  escribe nada en la base por su cuenta».

### 4.4. Inventario predictivo — PB-11 (2 min)
- **`/inventario`**: velocidad de consumo (90 días), punto de reorden, días
  restantes, compra sugerida y estado (`riesgo`, `sin_historial`, `ok`).
- Mostrar el material bajo mínimo y el botón de **silenciar alerta**.
- Mensaje: «No inventamos números: si no hay historial, lo dice».

### 4.5. Calidad de planos — PB-13 (1 min)
- Subir un plano (o abrir el detalle): checklist de **formato real vs.
  declarado**, DPI, tamaño de página y archivo corrupto.
- Mensaje: «Avisa, no bloquea: el operador decide si el plano sirve».

### 4.6. Copilot NL→SQL — PB-12 (2–3 min)
- **`/copilot`** (solo admin). Mostrar el aviso «Modo plantillas».
- Pulsar **Facturación del mes** → explicar: interpretación, SQL ejecutado
  (desplegable) y tabla.
- Probar una pregunta libre: «¿Qué materiales están por debajo del mínimo?».
- Probar una que no entiende: «hola mundo» → mensaje con sugerencias, sin SQL.
- Mensaje: «Sin API funciona; con API key traduce preguntas libres, y **todo**
  pasa por un validador de solo lectura antes de ejecutarse».

### 4.7. Cierre (1 min)
- **`/reportes`**: PDF de clientes/facturación como entregable formal.
- Recordar: 4 de 4 agentes con v1 desplegada; v2 (LLM/RAG, OpenCV, series
  temporales) está en el backlog **con criterios de aceptación**.

---

## 5. Las cuatro historias de IA: qué mostrar y qué decir

| Historia | Qué se muestra | Qué se dice | Evidencia |
|---|---|---|---|
| **PB-10** Cotización | Panel de desglose al calcular | Extrae área real del archivo; PDF con `pypdf`, DXF con lector propio; sin librerías nativas | `cotizador_auto.py`, `docs/SPRINT_5.md`, 26 checks |
| **PB-11** Inventario | Panel de reabastecimiento | Velocidad desde facturas reales, ajuste por proyectos activos, reorden y compra sugerida | `inventario_predictivo.py`, `docs/SPRINT_6.md`, 31 checks |
| **PB-12** Copilot | `/copilot` + SQL + tabla | 8 plantillas sin API; proveedor OpenAI-compatible opcional; validador y auditoría | `copilot.py`, `docs/SPRINT_7.md`, `docs/ANEXO_IA.md`, 63 checks |
| **PB-13** Calidad | Checklist del plano | Verifica formato/DPI/página; avisa sin bloquear | `calidad_planos.py`, `docs/SPRINT_6.md` |

**Idea que debe quedar:** los cuatro comparten tres reglas —sin cambios de
esquema, sin dependencias pesadas y con el humano en el bucle—. Están en
`docs/ANEXO_IA.md` (Parte D).

---

## 6. Preguntas probables y respuestas cortas

**«¿Por qué no usaron un LLM para todo?»**
Porque el jurado y el cliente tienen que poder usarlo sin internet ni
presupuesto. El LLM es opcional (PB-12); el resto es determinista y
reproducible. Donde hace falta IA generativa, se enchufa por variable de
entorno sin tocar código.

**«¿Cómo evitan que el copilot borre datos o filtre contraseñas?»**
Tres capas: el prompt, un **validador propio** (solo `SELECT`/`WITH`, sin
verbos de escritura ni comentarios, una sola sentencia) y un **catálogo
cerrado de tablas** donde `usuarios` no existe. Además se fuerza `LIMIT` y
todo se ejecuta con un usuario de solo lectura si se configura
`COPILOT_DATABASE_URL`.

**«¿Qué pasa si el modelo alucina SQL?»**
Se rechaza, se avisa en pantalla y se responde con la plantilla más cercana.
Nunca hay error 500. Cada consulta queda en el log con usuario, pregunta y SQL.

**«¿Por qué no migraron la base de datos?»**
Regla del backlog: la fase de IA es **aditiva**. Los agentes leen y sugieren
sobre el esquema existente. Cero migraciones = cero riesgo para producción.

**«¿Cómo sé que el cálculo de área es correcto?»**
El PDF se lee con `pypdf` y el DXF con un lector propio contrastado con
`$EXTMIN`/`$EXTMAX`; los casos están en `test_sprint5.py`. Si el archivo no es
legible, el sistema **no inventa**: pide los datos a mano.

**«¿Esto aguanta varios usuarios?»**
El despliegue real usa MySQL 8 + SQLAlchemy con índices y caché por ruta
(Sprint 2/3). La demo del G60 usa SQLite por portabilidad. La arquitectura es
la misma; cambia el motor.

**«¿Dónde está la IA predictiva de verdad?»**
En el backlog v2 con criterios escritos: LLM/RAG + DWG (PB-10), OpenCV/YOLO
(PB-13) y series temporales/EOQ (PB-11). La v1 entrega el valor operativo hoy;
la v2 necesita datos y cómputo que el servidor actual no tiene.

**«¿Qué pasa si se cae el G60?»**
El sistema es portable: mismo código en cualquier Linux/Windows con el venv.
Las suites se corren en local y las capturas quedan de respaldo.

**«¿Cómo se revisa sin cuenta de GitHub?»**
Hay un espejo público del repositorio; `GUIA_REVISION.md` indica rama, commits
por sprint y qué documento leer para cada historia.

---

## 7. Plan de contingencia

| Falla | Qué hacer |
|---|---|
| Túnel caído | Usar LAN `http://192.168.0.101:8000/asplot/` |
| G60 apagado | Demo local: `python app.py` con SQLite + `scripts/demo_datos.py` |
| Sin internet | Todo funciona: no hay llamadas externas en modo plantillas |
| Datos vacíos | `scripts/demo_datos.py` (idempotente) y recargar |
| Pregunta del copilot no reconocida | Mostrar el mensaje con sugerencias: es el comportamiento esperado |

---

## 8. Cierre honesto

- **Entregado:** sistema completo, 7 sprints, 4 agentes v1, 120+ comprobaciones,
  despliegue real y documentación SDD.
- **Limitaciones conocidas:** el análisis de planos cubre PDF/DXF (DWG es v2);
  el copilot sin API solo responde las 8 preguntas frecuentes; la visión por
  computador es v2; la demo corre en un servidor doméstico.
- **Mensaje final:** «Preferimos un sistema que funciona sin excusas: sin API,
  sin GPU y sin internet, y con el humano decidiendo siempre».
