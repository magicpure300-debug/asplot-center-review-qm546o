# Spec 006 — Sprint 6: Inventario predictivo (PB-11) + calidad de planos (PB-13)

> **Estado:** pendiente de aprobación
> **Sprint:** 6 · **Puntos:** 8 (PB-11: 5 · PB-13: 3)
> **Depende de:** Sprints 1–5 (inventario, facturas con detalle, módulo de planos)
> **Fase:** 2 (backlog de IA) — ambas historias son **deterministas**, sin LLM

---

## 1. Problema

**Inventario (PB-11).** El panel actual solo compara stock contra un
`stock_minimo` fijo. No dice *cuándo* se va a agotar un material ni *cuánto*
comprar: el administrador descubre la falta cuando ya está por debajo del
mínimo, y la reposición se decide a ojo. Tampoco existe forma de silenciar una
alerta ya atendida (el material sigue apareciendo en rojo hasta que llega la
compra).

**Calidad de planos (PB-13).** El sistema acepta cualquier archivo con la
extensión permitida sin verificar su contenido. Se han subido PDFs corruptos,
imágenes de baja resolución y archivos renombrados (un JPG llamado `.pdf`), y
el problema se descubre al plotear: se desperdicia material y tiempo de taller.
Hoy no hay ningún aviso previo.

## 2. Objetivos

1. Estimar, con datos reales de facturación, la **velocidad de consumo** de
   cada material, los **días hasta agotarse**, el **punto de reorden** y una
   **cantidad de compra sugerida**.
2. Permitir **silenciar** una alerta ya atendida y **reactivarla**, sin tocar
   el esquema de base de datos.
3. Verificar automáticamente la **calidad del archivo del plano** (formato
   real, DPI y tamaño de página) y mostrar el resultado como checklist,
   **sin bloquear** la subida ni el flujo actual.

## 3. Alcance

### Dentro del alcance

- Panel «Predicción de reabastecimiento» en `/inventario` con una fila por
  material: stock, velocidad (unidades/día), días restantes, punto de reorden,
  compra sugerida y estado.
- Velocidad calculada con las líneas de `DetalleFactura` de los **últimos 90
  días** (ventana configurable) y ajustada al alza por proyectos
  `en_progreso`.
- Silencio persistente por material en un JSON dentro de `instance/`
  (7 días por defecto, reactivable).
- Checklist de calidad en el **detalle del plano** y resumen de advertencias
  al subir un archivo:
  - formato declarado vs. contenido real (magic bytes);
  - DPI en JPG/PNG (lectura de metadatos sin Pillow);
  - tamaño de página en PDF (A0–A4 vs. personalizado, páginas mezcladas);
  - archivo vacío o ilegible.
- La verificación **nunca bloquea**: el archivo se guarda igual que hoy.

### Fuera del alcance

- Modelos de series temporales o ML (v2 del backlog, cuando haya histórico).
- Nuevas tablas o columnas (regla transversal del backlog de IA).
- Edición de la imagen o del PDF para «corregirlo»: solo se informa.
- Visión por computador (líneas superpuestas, tramado, escalas): v2 explícita
  del backlog, requiere dataset anotado.
- Envío de la alerta por Telegram/email: la alerta vive en el panel.

## 4. Historias de usuario y criterios de aceptación

### PB-11 — Predicción de reabastecimiento (5 pts)

**Como** administrador, **quiero** saber qué material se agotará y cuánto
comprar **para** evitar paradas por falta de papel o tinta.

Criterios de aceptación:

1. `/inventario` muestra el panel con todos los materiales activos y, por
   cada uno: stock actual, velocidad (u/día), días estimados hasta agotarse,
   punto de reorden, cantidad sugerida y estado (`riesgo` / `ok` /
   `sin_historial` / `silenciada`).
2. La velocidad usa solo líneas de factura de la ventana configurable
   (90 días por defecto) y se expresa en unidades/día; si no hay facturas en
   la ventana → `sin_historial` (no se inventan números) y se mantiene la
   alerta por `stock_minimo` ya existente.
3. El punto de reorden = `velocidad_ajustada × (días_reposición +
   días_seguridad)`; la compra sugerida cubre `días_compra` de demanda menos
   el stock actual (mínimo 0, redondeo hacia arriba).
4. La velocidad se ajusta por proyectos `en_progreso` (factor configurable,
   con tope) y el panel indica el ajuste aplicado.
5. Una alerta se puede **silenciar 7 días** (configurable) y **reactivar**
   desde el panel; el silencio persiste entre reinicios y no altera la base.
6. El cálculo es de solo lectura: no modifica stock, materiales ni facturas.
7. Datos insuficientes (menos de 14 días de histórico) se marcan como
   «estimación preliminar» con aviso visible.
8. Solo admin/trabajador acceden al panel y a las acciones de silencio.

### PB-13 — Checklist de calidad del plano (3 pts)

**Como** trabajador de taller, **quiero** una verificación automática antes de
plotear **para** reducir el desperdicio por archivos deficientes.

Criterios de aceptación:

1. Al subir un plano, tras guardarlo, se muestran las advertencias detectadas
   (si las hay) sin impedir la subida; si todo está bien, un mensaje de
   conformidad.
2. El detalle del plano (`/planos/detalle/<id>`) muestra un **checklist**:
   - formato declarado vs. real (PDF/JPG/PNG/DXF/DWG por firma de bytes);
   - DPI mínimo (150 por defecto) en JPG/PNG; sin metadato → «no
     verificable», no fallo;
   - tamaño de página en PDF (A0–A4 o personalizado; aviso si hay páginas de
     tamaños distintos);
   - archivo vacío o ilegible.
3. Un JPG renombrado a `.pdf` genera advertencia de formato; un PDF corrupto
   también; un PNG de 72 DPI genera advertencia de resolución.
4. La verificación se ejecuta bajo demanda al abrir el detalle (no en cada
   listado) y **nunca** devuelve un error 500: archivo ausente o ilegible se
   informa como advertencia.
5. Las advertencias no cambian el estado del plano ni el flujo de facturación.

## 5. Requisitos no funcionales

- **Portabilidad:** sin librerías nativas nuevas. DPI de JPG/PNG se lee de la
  cabecera (JFIF/PNG pHYs) con Python puro; PDF usa `pypdf` (ya instalado).
  Debe funcionar en Windows, Render (opcional) y el G60.
- **Rendimiento:** el panel de inventario agrega el consumo con **una sola
  consulta** (`SUM`/`GROUP BY` por material) y el checklist se calcula solo al
  abrir el detalle; los listados no cambian.
- **Persistencia del silencio:** JSON pequeño en `instance/` con escritura
  atómica (temporal + `os.replace`); si el archivo está corrupto se ignora y
  se regenera sin romper la página.
- **Seguridad:** RBAC en las rutas de silencio; el JSON no se sirve por HTTP;
  los IDs se validan contra la base; nada de rutas desde el usuario.
- **Sin migración:** no se agregan tablas ni columnas.
- **Documentación:** `docs/SPRINT_6.md`, fila en `docs/GUIA_REVISION.md`,
  criterios marcados en `docs/BACKLOG_IA.md`.

## 6. Modelo de datos (sin cambios)

| Entidad | Uso | Cambios |
|---|---|---|
| `DetalleFactura` | líneas de consumo histórico (cantidad por material) | ninguno |
| `Factura` | fecha para la ventana de 90 días | ninguno |
| `Material` / `Inventario` | stock actual, mínimo y precios | ninguno |
| `Proyecto` | ajuste por proyectos `en_progreso` | ninguno |
| `Plano` | archivo a verificar | ninguno |

## 7. Criterios de éxito

- Con 3 facturas de prueba en 30 días, el panel muestra velocidad, días
  restantes y compra sugerida verificables a mano.
- Silenciar un material lo saca de las alertas activas, sobrevive a un
  reinicio y se puede reactivar.
- Un PDF válido pasa el checklist; un JPG renombrado y un PNG de 72 DPI
  muestran advertencias claras, y la subida sigue funcionando.
- Suite `test_sprint6.py` en verde + regresión de Sprints 4 y 5 en verde.

## 8. Riesgos y preguntas abiertas

1. **Pocas facturas en la demo:** los datos sembrados no incluyen facturas;
   el panel mostrará `sin_historial` y la alerta por mínimo. Las pruebas
   crean facturas temporales para verificar el cálculo.
2. **Consumo ≠ venta:** `DetalleFactura` registra lo facturado; se asume que
   el material facturado se consumió. Es la única fuente existente y el
   backlog prohíbe tablas nuevas.
3. **DPI ausente en muchos JPG:** se reporta «no verificable» en lugar de
   asumir 72 u 96 DPI (evita falsos positivos).
4. **Ventana de 90 días con histórico corto:** el divisor se limita a los
   días reales desde la primera factura para no subestimar la velocidad.
5. **Silencio en JSON:** si se borra `instance/`, se pierden los silencios
   (aceptable en demo; documentado).
