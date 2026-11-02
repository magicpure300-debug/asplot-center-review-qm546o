# ASPLOT CENTER — Sprint 5: Cubicación y cotización automática

> **PB-10 (8 puntos) — Fase 2 del backlog de IA (`docs/BACKLOG_IA.md`)**
> Versión v1 determinista: sin LLM ni servicios externos.
> Objetivo: calcular el área de impresión de un plano (PDF/DXF) y proponer
> un precio con desglose, manteniendo la decisión final en el humano.

---

## Qué se construyó

### Módulo `cotizador_auto.py` (Python puro, sin Flask)

| Función | Responsabilidad |
|---|---|
| `analizar_archivo(ruta)` | Despacha por extensión real a PDF o DXF y devuelve un dict uniforme (`ok`, `mensaje`, `area_m2`, `detalle_area`, `advertencias`, …). |
| `analizar_pdf(ruta)` | Suma el área de **todas las páginas** con `pypdf` (1 pt = 0,0254/72 m) y detecta A0–A4 con tolerancia ±2 %. |
| `analizar_dxf(ruta)` | Lector propio de la cabecera DXF: `$INSUNITS`, `$EXTMIN`, `$EXTMAX`; convierte pulgadas/pies/mm/cm/m a metros. |
| `calcular_precio(...)` | Aplica la fórmula con `Decimal` y redondeo comercial a 2 decimales. |
| `texto_desglose(...)` | Texto legible para las notas del proyecto. |

Nunca lanza excepciones hacia la vista: PDF corrupto o cifrado, DXF binario,
sin extensiones o con unidades ambiguas devuelven `ok:false` con un mensaje
claro (un DXF sin unidades se asume en mm **con advertencia**).

### Fórmula y configuración

```
base    = área_m2 × COTIZACION_TARIFA_M2
insumos = (área / rendimiento_rollo) × precio_compra(papel)
        + (área / rendimiento_cartucho) × precio_compra(tinta)
margen  = (base + insumos) × COTIZACION_MARGEN_PCT / 100
total   = base + insumos + margen
```

Los insumos se consumen de forma **proporcional al área** (no se cobra un
rollo completo por una hoja A4). El papel se elige por el formato detectado
(A0–A4) y la tinta negra por defecto; ambos salen de `materiales`, con el
stock de `inventario` como dato informativo (`alcanza`).

| Variable de entorno | Default demo |
|---|---|
| `COTIZACION_TARIFA_M2` | `8.0` |
| `COTIZACION_MARGEN_PCT` | `30` |
| `COTIZACION_RENDIMIENTO_ROLLO_M2` | `10` |
| `COTIZACION_RENDIMIENTO_CARTUCHO_M2` | `20` |

### Ruta y selección de archivo

`POST /proyectos/<id>/cotizacion-automatica` (admin/trabajador, JSON):

1. Planos subidos del proyecto, del más reciente al más antiguo.
2. Adjunto de la solicitud pública (`archivo_solicitud`).
3. Se analiza el **primer candidato PDF/DXF**; DWG/JPG/PNG se saltan.
4. Sin candidatos analizables → mensaje («Sube un plano PDF/DXF…» o el motivo
   concreto) y el formulario sigue manual.

El endpoint **no escribe** en la base: ni presupuesto ni estado. El admin
revisa el desglose, ajusta el monto y guarda con el formulario existente
(`estado = cotizado`).

### Interfaz

- `aprobar_proyecto.html`: botón «Calcular automáticamente», panel con área,
  tarifa, insumos, margen y total; rellena el presupuesto (pide confirmación
  si ya había otro valor escrito) y botón «Añadir desglose a notas» que
  **concatena** al texto existente con fecha y hora.
- `solicitudes.html`: «Atender» abre el formulario con `?auto=1`, que dispara
  el cálculo al cargar.
- Corrección incluida: el enlace de descarga del adjunto apuntaba a
  `uploads/solicitudes/` y el archivo se guarda en
  `uploads/planos/solicitudes/`; ahora coincide.

## Decisiones técnicas

| Decisión | Motivo |
|---|---|
| Solo librerías puras Python (`pypdf` + lector DXF propio) | PyMuPDF y Pillow no tienen wheel para Android arm64; el demo corre en el G60 (Termux). Así funciona igual en Windows, Render y el teléfono. |
| Sin cambios de esquema | Regla transversal del backlog de IA: capa aditiva sobre las tablas existentes. |
| El cálculo solo sugiere | Regla «los agentes solo sugieren; el precio final es humano». |
| Insumos proporcionales | Evita que un A4 cotice un rollo completo; el desglose queda verificable a mano. |
| Sin LLM en v1 | Determinismo primero; el RAG/LLM es la v2 sobre estos datos estructurados. |

## Pruebas

Suite `test_sprint5.py` (copia limpia del proyecto con SQLite propio):
**26 comprobaciones en verde**.

- PDF A4 (0,0624 m²), PDF A0 de 2 páginas (2,0 m²), PDF corrupto.
- DXF en mm, en metros, sin unidades (advertencia) y binario; DXF sin
  `$EXTMIN/$EXTMAX`.
- Endpoint: aritmética exacta contra la configuración, elección del material
  A4, proyecto sin archivos, DWG reciente con PDF de respaldo, stock
  insuficiente marcado, `texto_notas`.
- RBAC (cliente 403, anónimo 302) y **no escritura** de presupuesto/estado.
- Formulario con `?auto=1` y smoke de regresión (landing, solicitud pública,
  dashboard, solicitudes, inventario).
- Regresión completa: `test_sprint4.py` (29 checks) sigue en verde.

## Despliegue y hallazgo en el G60

- Verificado en el servidor propio (Termux): `pypdf` instala sin compilar y
  la suite completa corre en el teléfono (26 comprobaciones en verde).
- Prueba viva con login real y un PDF A0: HTTP 200, área 0,9999 m², total
  $15,67; los datos de prueba se eliminaron al terminar.
- **Corrección de siembra:** la demo solo se siembra en bases nuevas
  (`if not Usuario.query.first()`). En el G60 existía una base previa con otro
  email de admin y el guard anterior (por email) intentaba sembrar de nuevo,
  chocando con los emails únicos y dejando el servicio sin arrancar. Ahora una
  instalación existente arranca sin tocar sus datos.

## Limitaciones documentadas

- **.DWG** queda fuera (formato propietario; requiere conversor ODA).- **JPG/PNG** no se analizan: sin DPI fiable en el G60 se tratan como no
  analizables y la cotización sigue manual.
- **DXF sin `$EXTMIN`/`$EXTMAX`** no se analiza (no se recorren entidades en
  v1); se informa y queda manual.
- **Unidades DXF ausentes:** se asumen milímetros y se advierte en pantalla.
- **Precios de compra de la demo** pueden hacer que los insumos pesen mucho
  en planos pequeños; el desglose es transparente y el admin puede editar el
  total. En producción se cargan los precios reales en `materiales`.
- **Render:** el análisis funciona (disco efímero solo afecta a los archivos
  adjuntos, como en el Sprint 4).
- **v2 (LLM+RAG)** para planos no normalizados queda en el backlog.
