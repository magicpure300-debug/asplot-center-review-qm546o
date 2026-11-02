# Plan técnico 005 — Sprint 5: Cubicación y cotización automática

> **Spec aprobada:** `specs/005-cotizacion-automatica/spec.md`
> **Estrategia:** módulo nuevo `cotizador_auto.py` (Python puro, sin Flask) +
> una ruta JSON en `app.py` + botón/panel en el formulario de cotización. Sin
> cambios de esquema, sin servicios externos.

---

## 1. Arquitectura de la solución

### 1.1 Componentes nuevos

| Componente | Tipo | Responsabilidad |
|---|---|---|
| `cotizador_auto.py` | módulo Python puro | Leer PDF/DXF y calcular el desglose de precio. Sin imports de Flask: testeable aislado. |
| `POST /proyectos/<int:id>/cotizacion-automatica` | ruta Flask (JSON) | RBAC, selección del archivo del proyecto, consulta de materiales/inventario, arma la respuesta. |
| Panel «Cubicación automática» | JS + HTML en `aprobar_proyecto.html` | Dispara el fetch, muestra desglose, rellena `#presupuesto`, permite copiar el desglose a `#notas`. |
| Constantes `COTIZACION_*` | `config.py` | Tarifa/m², margen %, rendimientos de papel y tinta (env vars con default). |

### 1.2 API del módulo (`cotizador_auto.py`)

```
analizar_archivo(ruta) -> dict
    {
      'ok': bool, 'mensaje': str,
      'formato': 'pdf'|'dxf',
      'paginas': int, 'detalle_area': str,
      'ancho_m': float, 'alto_m': float, 'area_m2': float,
      'advertencias': [str, ...]
    }

calcular_precio(area_m2, papel, tinta, tarifa_m2, margen_pct,
                rendimiento_rollo_m2, rendimiento_cartucho_m2) -> dict
    papel/tinta: {'nombre', 'precio_compra', 'unidad', 'stock'|None}
    {
      'base', 'insumos': [{nombre, cantidad, unidad, precio, subtotal,
                           stock, alcanza}], 'subtotal_insumos',
      'margen_pct', 'margen', 'total', 'advertencias'
    }

texto_desglose(analisis, desglose) -> str   # para las notas del proyecto
```

### 1.3 Rutas

| Ruta | Método | Acceso | Propósito |
|---|---|---|---|
| `/proyectos/<int:id>/cotizacion-automatica` | POST | Admin/trabajador | Devuelve el desglose en JSON (no escribe en base) |
| `/proyectos/<int:id>/aprobar` | GET | Admin/trabajador (ya existe) | Acepta `?auto=1`: la página dispara el cálculo al cargar |

Códigos de respuesta del endpoint: `200` con `ok:true/false` para resultados
de análisis (el formulario siempre sigue operativo), `403` si el rol no
permite cotizar, `404` si el proyecto no existe, `302` a login si no hay
sesión (comportamiento estándar de `login_required`).

## 2. Algoritmos

### 2.1 PDF (`pypdf`, puro Python)

1. `PdfReader(path)`; si `is_encrypted` → intentar `decrypt('')`; si sigue
   cifrado → `ok:false` («PDF protegido con contraseña»).
2. Recorrer todas las páginas y sumar `page.mediabox.width * height`
   (pypdf resuelve la herencia de `/MediaBox` del árbol de páginas).
3. Convertir puntos → metros: `1 pt = 0.0254/72 m`; área × factor².
4. Detectar formato estándar comparando el lado mayor/menor con A0–A4
   (tolerancia ±2 %); si no coincide → «personalizado».
5. Redondear a 4 decimales. Cualquier excepción se captura y se devuelve
   `ok:false` con mensaje controlado (nunca 500).

### 2.2 DXF (lector propio de cabecera)

1. Leer los primeros bytes: si empieza con `AutoCAD Binary DXF` →
   `ok:false` («DXF binario no soportado»).
2. Parsear pares (código, valor) del formato de texto y localizar en la
   sección `HEADER`: `$INSUNITS` (código 70), `$EXTMIN`/`$EXTMAX`
   (códigos 10 y 20 para X/Y).
3. `$INSUNITS`: 1=in, 2=ft, 4=mm, 5=cm, 6=m; ausente o 0 → **mm con
   advertencia** (CA2 de la spec).
4. Área = `|xmax-xmin| * |ymax-ymin|` convertida a m²; si falta alguna
   extensión o el área es 0 → `ok:false` con mensaje.

### 2.3 Fórmula de precio

```
papel:    fraccion_rollo    = area_m2 / RENDIMIENTO_ROLLO_M2
tinta:    fraccion_cartucho = area_m2 / RENDIMIENTO_CARTUCHO_M2
base      = area_m2 * TARIFA_M2
insumos   = fraccion_rollo * precio_compra(papel)
          + fraccion_cartucho * precio_compra(tinta)
margen    = (base + insumos) * MARGEN_PCT / 100
total     = base + insumos + margen
```

- Redondeo monetario con `Decimal` + `ROUND_HALF_UP` a 2 decimales; el área
  se redondea a 4 decimales.
- Para el stock se compara la **fracción** con la cantidad disponible
  (`alcanza = stock >= fraccion`); sin registro de inventario → `null`.

- Selección de material: papel por `subcategoria` = formato detectado
  (A0–A4); si no existe, el primer `papel` (A0 en la siembra). Tinta
  `negro` (planos), si no la primera `tinta`.
- `precio_compra = 0` → insumo computa 0 y añade advertencia «sin precio de
  compra cargado».
- Stock desde `Inventario` por `id_material`; `alcanza = stock >= cantidad`.
  Si no hay registro → `stock: null` («sin registro de inventario»).
- Sin materiales cargados → insumos vacíos + advertencia; el precio sigue
  calculándose con base + margen.

### 2.4 Selección del archivo a analizar

1. `proyecto.planos` ordenados por `fecha_subida` descendente.
2. Adjunto `archivo_solicitud` (vive en `static/uploads/solicitudes/`).
3. Se resuelve la ruta absoluta **solo** desde esos campos de base, se
   comprueba que exista dentro de su carpeta de subida y se prueba en orden
   el primer candidato con extensión PDF/DXF; los DWG/JPG/PNG se saltan
   (CA6/CA7). Si ninguno sirve → `ok:false` con el motivo del primer
   candidato encontrado («el plano es DWG; sube un PDF o DXF»).

## 3. Interfaz

### 3.1 `aprobar_proyecto.html`

- Botón `#btn-calcular` «Calcular automáticamente» (tipo `button`, no
  envía el formulario) junto al campo de presupuesto.
- Panel `#desglose` oculto por defecto: área + formato + advertencias,
  tabla de líneas (tarifa, insumos, margen), total sugerido y botón
  «Añadir desglose a notas».
- JS: `fetch(POST)` con `credentials: 'same-origin'`; si `ok:true`, rellena
  `#presupuesto` (si el admin ya escribió un valor, pide confirmación antes
  de reemplazarlo) y muestra el panel. Si `ok:false`, muestra el mensaje y
  **no toca** el formulario.
- «Añadir a notas» concatena `texto_desglose` al final del textarea
  `#notas` con salto de línea y fecha, sin borrar lo existente.
- Con `?auto=1` en la URL, el fetch se ejecuta al cargar la página.

### 3.2 `solicitudes.html`

- El enlace «Cotizar» de la bandeja apunta a
  `url_for('aprobar_proyecto', id=..., auto=1)`; el resto igual.

## 4. Configuración

`config.py` (clase `Config`), con defaults válidos para la demo:

| Constante | Env var | Default |
|---|---|---|
| `COTIZACION_TARIFA_M2` | `COTIZACION_TARIFA_M2` | `8.0` |
| `COTIZACION_MARGEN_PCT` | `COTIZACION_MARGEN_PCT` | `30` |
| `COTIZACION_RENDIMIENTO_ROLLO_M2` | `COTIZACION_RENDIMIENTO_ROLLO_M2` | `10` |
| `COTIZACION_RENDIMIENTO_CARTUCHO_M2` | `COTIZACION_RENDIMIENTO_CARTUCHO_M2` | `20` |

`requirements.txt`: `pypdf==6.19.0` (puro Python; instala igual en Windows,
Render y Termux). No se agrega `ezdxf` ni `PyMuPDF`.

## 5. Seguridad

- `login_required` + `es_admin or es_trabajador` (mismo patrón del resto).
- El endpoint **no lee** rutas ni precios del POST: solo el `id` de la URL;
  tarifa/margen/rendimientos salen de `config`.
- Las rutas de archivo se construyen con `os.path.abspath` y se verifica
  que queden dentro de `static/uploads/planos` o
  `static/uploads/solicitudes` (defensa contra path traversal en datos
  viejos).
- Todo error de análisis → mensaje controlado; nunca se propaga una
  excepción del parser a la respuesta.

## 6. Pruebas (gate por tarea)

Script nuevo `C:\Users\L\AppData\Local\Temp\opencode\test_sprint5.py`
(app de prueba SQLite temporal, patrón de `test_sprint4.py`):

1. PDF A4 generado con pypdf → área ≈ 0.0624 m², formato «A4».
2. PDF A0 de 2 páginas → área ≈ 2.0 m² (suma de páginas).
3. PDF corrupto → `ok:false`, mensaje claro, sin excepción.
4. DXF en mm de 2000×1000 → 2.0 m².
5. DXF con `$INSUNITS=6` (metros) 2×1 → 2.0 m².
6. DXF sin `$INSUNITS` → asume mm + advertencia.
7. DXF sin `$EXTMIN/$EXTMAX` → `ok:false`.
8. DXF binario → `ok:false`.
9. Endpoint con PDF del proyecto → JSON con área, base, insumos, margen y
   total exactos (verificación aritmética a mano).
10. Proyecto sin planos pero con adjunto PDF → analiza el adjunto.
11. Proyecto sin archivos → `ok:false` y mensaje «sube un plano…».
12. Plano DWG reciente + PDF anterior → usa el PDF (salto de no analizable).
13. El cálculo **no** modifica `presupuesto` ni `estado` en base.
14. Cliente autenticado → 403; sin sesión → 302 a login.
15. Stock insuficiente se marca `alcanza:false`.
16. `texto_desglose` incluye área, fórmula y total.
17. Regresión: `test_sprint4.py` (y suites previas disponibles) en verde.

## 7. Despliegue

1. `pip install pypdf` en el Python local para la suite.
2. Commit en `develop` → push a `origin` y al mirror `review`.
3. G60: copiar `cotizador_auto.py`, `app.py`, `config.py`,
   `templates/aprobar_proyecto.html`, `templates/solicitudes.html`,
   `requirements.txt`; `.venv/bin/pip install pypdf`; reiniciar con
   `sh ~/reiniciar-servicio.sh asplot`; verificar `/asplot/` y una
   cotización real.
4. Render: redeploy automático desde `develop`; `pypdf` se instala del
   `requirements.txt` y funciona en Linux sin dependencias nativas.
5. `docs/SPRINT_5.md` + fila en `docs/GUIA_REVISION.md` + marcar PB-10 v1
   en `docs/BACKLOG_IA.md`.

## 8. Riesgos

| Riesgo | Mitigación |
|---|---|
| DXF sin extensiones (editores que no las guardan) | Mensaje claro y cotización manual; documentado |
| `$INSUNITS` ambiguo | Suposición mm + advertencia visible |
| Precios de compra de la demo irreales | Desglose transparente; el admin puede editar el presupuesto |
| PDFs escaneados (imagen dentro del PDF) | Igual se calcula el área de la página (el contenido no importa para m²) |
| `pypdf` con PDFs raros | Todo envuelto en try/except con mensaje controlado y tests de corrupción |
| Divergencia G60/PC por versiones | Misma librería pura Python en los tres entornos |
