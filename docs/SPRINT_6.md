# ASPLOT CENTER — Sprint 6: Inventario predictivo y calidad de planos

> **PB-11 (5) + PB-13 (3) = 8 puntos — Fase 2 del backlog de IA**
> Ambas historias son deterministas: sin LLM, sin servicios externos y sin
> cambios de esquema.

---

## PB-11 — Predicción de reabastecimiento (5 pts)

**Módulo `inventario_predictivo.py`** (Python puro):

- Velocidad de consumo = líneas de `DetalleFactura` de la ventana
  configurable (90 días por defecto) ÷ días reales de histórico
  (`min(ventana, días desde la primera factura)`), para no subestimar en
  instalaciones nuevas.
- Ajuste por proyectos `en_progreso`: `1 + min(0.50, 0.10 × activos)`.
- Punto de reorden = velocidad ajustada × (7 días de reposición + 7 de
  seguridad).
- Días restantes = stock ÷ velocidad ajustada.
- Compra sugerida = lo necesario para cubrir 30 días de demanda menos el
  stock actual (mínimo 0, redondeo hacia arriba).
- Estados: `riesgo` (bajo reorden o bajo mínimo), `sin_historial` (sin
  facturas en la ventana: no se inventan números), `ok`, `silenciada`.
- Histórico menor a 14 días → aviso «estimación preliminar».

**Panel** en `/inventario` («Predicción de reabastecimiento») con stock,
velocidad, días restantes, reorden, compra sugerida, estado y acción. El
consumo se obtiene con **una sola consulta agregada** (`SUM`/`GROUP BY`).

**Silencio de alertas:** JSON `instance/inventario_alertas.json`
(`{"<id_material>": "AAAA-MM-DD"}`), escritura atómica con `os.replace`,
purga de vencidos y tolerancia a archivos corruptos. Botones «Silenciar»
(7 días, configurable) y «Reactivar»; solo admin/trabajador.

## PB-13 — Checklist de calidad del plano (3 pts)

**Módulo `calidad_planos.py`** (Python puro + `pypdf`):

| Verificación | Implementación |
|---|---|
| Formato declarado vs. real | firma de bytes: `%PDF`, `\x89PNG`, `\xFF\xD8\xFF`, `AC10` (DWG), DXF texto con `SECTION/HEADER` |
| DPI en JPG | segmento APP0/JFIF (unidades ppi o ppcm) |
| DPI en PNG | chunk `pHYs` (píxeles por metro → DPI) |
| Tamaño de página PDF | `mediabox` de todas las páginas + detector A0–A4 del Sprint 5 |
| Legibilidad | PDF corrupto/cifrado, cabecera DXF/DWG |

- **Sin Pillow**: solo cabeceras, por lo que funciona en el G60.
- Estados por ítem: `ok`, `aviso`, `no_verificable` (nunca 500).
- Al subir un plano se guarda igual que antes y se añaden avisos por flash;
  el detalle del plano muestra la tarjeta «Calidad del archivo» con el
  checklist completo (se recalcula al abrir, no en los listados).

## Configuración

| Variable | Default |
|---|---|
| `INVENTARIO_VENTANA_DIAS` | 90 |
| `INVENTARIO_DIAS_REPOSICION` | 7 |
| `INVENTARIO_DIAS_SEGURIDAD` | 7 |
| `INVENTARIO_DIAS_COMPRA` | 30 |
| `INVENTARIO_FACTOR_ACTIVO` | 0.10 |
| `INVENTARIO_TOPE_ACTIVO` | 0.50 |
| `INVENTARIO_SILENCIO_DIAS` | 7 |
| `CALIDAD_DPI_MINIMO` | 150 |

## Pruebas

Suite `test_sprint6.py` (copia limpia con SQLite propio): **31 comprobaciones
en verde**.

- Calidad: PNG 300/72 dpi, PNG sin `pHYs`, JPG 300 dpi, JPG renombrado a PDF,
  PDF corrupto, archivo vacío, PDF A4.
- Subida real con PNG de 72 dpi: se guarda (no bloquea) y muestra la
  advertencia; el detalle pinta el checklist.
- Inventario: 30 unidades en 30 días → 1.0 u/día, 12 días restantes, reorden
  14, compra 18, estado `riesgo`; material sin facturas → `sin_historial`;
  proyecto en progreso → ajuste ×1.10.
- Silencio persistido en JSON, reactivación, y cliente sin permiso.
- Regresión: landing, solicitud pública, dashboard, planos, facturas y
  clientes; suites de Sprints 4 y 5 completas en verde.

## Decisiones técnicas

| Decisión | Motivo |
|---|---|
| Consumo desde facturas | Es la única fuente existente; el backlog prohíbe tablas nuevas |
| Divisor por histórico real | Evita subestimar la velocidad en una instalación recién sembrada |
| JSON para silencios | Persistente y sin migración; se pierde solo si se borra `instance/` |
| DPI sin Pillow | Pillow no existe en el G60 (Android arm64) |
| Verificación bajo demanda | No penaliza listados ni subidas |

## Limitaciones documentadas

- **Consumo ≠ venta:** se asume que lo facturado se consumió; no hay
  movimientos de inventario en el esquema.
- **Demo sin facturas:** el panel muestra `sin_historial` y la alerta por
  `stock_minimo` hasta que se facture (las pruebas crean facturas temporales).
- **Silencios en `instance/`:** se pierden si se borra esa carpeta.
- **Visión por computador** (líneas superpuestas, tramado, escalas): v2
  explícita del backlog, requiere dataset anotado.
- **DWG:** solo se valida la cabecera, no el contenido.
