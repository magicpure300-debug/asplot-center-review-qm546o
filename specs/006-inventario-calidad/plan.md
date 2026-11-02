# Plan técnico 006 — Sprint 6: Inventario predictivo + calidad de planos

> **Spec aprobada:** `specs/006-inventario-calidad/spec.md`
> **Estrategia:** dos módulos Python puros (`inventario_predictivo.py`,
> `calidad_planos.py`) + rutas de lectura/acciones en `app.py` + panel en
> `inventario.html` y checklist en `detalle_plano.html`. Sin cambios de
> esquema ni librerías nativas.

---

## 1. Arquitectura

### 1.1 Componentes nuevos

| Componente | Responsabilidad |
|---|---|
| `inventario_predictivo.py` | Calcular velocidad, días restantes, punto de reorden y compra sugerida; leer/escribir silencios JSON. Python puro. |
| `calidad_planos.py` | Verificar firma real, DPI (JPG/PNG), tamaño de página (PDF) y archivo vacío. Python puro + `pypdf`. |
| Panel en `/inventario` | Tabla de predicciones, estado y acciones silenciar/reactivar. |
| Checklist en `/planos/detalle/<id>` | Tarjeta con el resultado de las verificaciones. |
| Constantes `INVENTARIO_*` / `CALIDAD_*` | `config.py`, con defaults de demo y override por entorno. |

### 1.2 API de los módulos

```
# inventario_predictivo.py
calcular_predicciones(materiales, consumos, proyectos_activos, params, hoy) -> [dict]
    materiales: [{id, nombre, stock, stock_minimo, unidad, precio_compra}]
    consumos:   {id_material: {'total': float, 'primera': date, 'ultima': date}}
    params:     ventana_dias, dias_reposicion, dias_seguridad,
                dias_compra, factor_activo, tope_activo, silencio_dias
    -> [{id, nombre, stock, velocidad, velocidad_ajustada, dias_restantes,
         punto_reorden, compra_sugerida, estado, avisos}]

leer_silencios(ruta, hoy) -> {id_material: fecha_hasta}
guardar_silencios(ruta, datos) -> bool     # escritura atómica
```

```
# calidad_planos.py
verificar_archivo(ruta) -> [dict]
    [{'clave': 'formato', 'etiqueta': 'Formato declarado vs. real',
      'estado': 'ok'|'aviso'|'no_verificable', 'detalle': '...'}]
```

## 2. Inventario predictivo (PB-11)

### 2.1 Cálculo

```
dias_base   = min(ventana, max(1, (hoy - primera_factura_historial).days + 1))
velocidad   = total_consumido_en_ventana / dias_base         # u/día
ajuste      = 1 + min(tope, factor × n_proyectos_en_progreso)
vel_ajust   = velocidad × ajuste
reorden     = vel_ajust × (dias_reposicion + dias_seguridad)
dias_restan = stock / vel_ajust  (None si velocidad 0)
compra      = max(0, ceil(vel_ajust × dias_compra - stock))
```

- El consumo se obtiene con **una sola consulta agregada**:
  `SUM(DetalleFactura.cantidad) GROUP BY id_material` con
  `Factura.fecha_factura >= hoy - ventana` y `id_material NOT NULL`.
- `primera_factura_historial` = `MIN(Factura.fecha_factura)` global (para el
  divisor cuando el sistema es nuevo).
- Estados: `silenciada` (silencio vigente) > `sin_historial` (sin líneas en la
  ventana) > `riesgo` (`stock <= reorden` **o** `stock <= stock_minimo`) >
  `ok`.
- Si el histórico es menor a 14 días → aviso «estimación preliminar».
- Materiales sin registro en `Inventario` se muestran con stock 0 y aviso.

### 2.2 Silencios

- Archivo `instance/inventario_alertas.json`:
  `{"<id_material>": "AAAA-MM-DD"}` (fecha hasta la que está silenciada).
- `leer_silencios` descarta fechas vencidas y entradas corruptas.
- `guardar_silencios`: escribe a `.tmp` y `os.replace` (atómico).
- Rutas:
  - `POST /inventario/alertas/silenciar/<int:id>` → +7 días (config).
  - `POST /inventario/alertas/reactivar/<int:id>` → elimina la entrada.
  - RBAC admin/trabajador; redirección a `/inventario` con flash.
- `app.instance_path` se usa para localizar el JSON (funciona en G60 y
  Render).

## 3. Calidad de planos (PB-13)

### 3.1 Verificaciones

| Clave | Regla | Estados |
|---|---|---|
| `archivo` | existe y pesa > 0 | aviso si falta/vacío |
| `formato` | firma real vs extensión: PDF `%PDF`, PNG `\x89PNG`, JPG `\xFF\xD8\xFF`, DWG `AC10`, DXF texto con `SECTION`/`HEADER` (o binario) | ok / aviso (no coincide) |
| `dpi` | JPG: APP0 JFIF (unidades 1=dpi, 2=dpcm); PNG: chunk `pHYs` (ppm × 0,0254) | ok (≥150), aviso (<150), no_verificable (sin metadato) |
| `pagina` | PDF: A0–A4 con ±2 % (reutiliza `cotizador_auto.detectar_formato`); páginas mezcladas | ok / aviso (personalizado o mixto) / no_verificable (no PDF) |
| `legible` | PDF corrupto/cifrado; DXF/DWG sin cabecera esperada | aviso |

- JPG/PNG se leen solo los primeros KB y los chunks iniciales; nunca se
  decodifica la imagen (sin Pillow).
- DXF/DWG solo verifican cabecera; el área DXF ya la calcula el Sprint 5.

### 3.2 Integración

- `subir_plano()`: tras `commit`, ejecuta `verificar_archivo` y añade un
  `flash` por cada advertencia (o uno de conformidad). La subida **no** se
  bloquea.
- `detalle_plano()`: pasa `calidad` a la plantilla; se recalcula al abrir.
- `detalle_plano.html`: tarjeta «Calidad del archivo» con iconos por estado
  (verde ok, ámbar aviso, gris no verificable) y el detalle textual.

## 4. Configuración (`config.py`)

| Constante | Env var | Default |
|---|---|---|
| `INVENTARIO_VENTANA_DIAS` | `INVENTARIO_VENTANA_DIAS` | `90` |
| `INVENTARIO_DIAS_REPOSICION` | `INVENTARIO_DIAS_REPOSICION` | `7` |
| `INVENTARIO_DIAS_SEGURIDAD` | `INVENTARIO_DIAS_SEGURIDAD` | `7` |
| `INVENTARIO_DIAS_COMPRA` | `INVENTARIO_DIAS_COMPRA` | `30` |
| `INVENTARIO_FACTOR_ACTIVO` | `INVENTARIO_FACTOR_ACTIVO` | `0.10` |
| `INVENTARIO_TOPE_ACTIVO` | `INVENTARIO_TOPE_ACTIVO` | `0.50` |
| `INVENTARIO_SILENCIO_DIAS` | `INVENTARIO_SILENCIO_DIAS` | `7` |
| `CALIDAD_DPI_MINIMO` | `CALIDAD_DPI_MINIMO` | `150` |

## 5. Seguridad

- Silencio: `login_required` + `es_admin or es_trabajador`; el `id` se busca
  con `get_or_404` (no se aceptan rutas ni nombres de archivo).
- El JSON de silencios vive en `instance/`, fuera de `static/` (no se sirve).
- Las verificaciones usan rutas derivadas de la base y confinadas a
  `UPLOAD_FOLDER` (mismo patrón del Sprint 5).
- Cualquier error de parseo se convierte en un ítem de checklist, nunca en
  500.

## 6. Pruebas (gate por tarea)

`test_sprint6.py` (copia limpia, SQLite propio):

1. PNG 300 DPI → checklist OK; PNG 72 DPI → aviso; PNG sin `pHYs` →
   no verificable.
2. JPG con JFIF 300 DPI → OK; JPG renombrado a `.pdf` → aviso de formato.
3. PDF A4 → página OK; PDF corrupto → aviso de legibilidad.
4. Archivo vacío → aviso.
5. `subir_plano` con PNG de baja resolución: guarda igual (302) y el mensaje
   incluye la advertencia.
6. Detalle del plano muestra la tarjeta con los ítems.
7. Inventario: 3 facturas en 30 días → velocidad y días restantes exactos;
   material bajo reorden marcado `riesgo`.
8. Sin facturas → `sin_historial` (no inventa velocidad).
9. Ajuste por 1 proyecto `en_progreso` aplica el factor configurado.
10. Silenciar: POST deja el material `silenciada`, el JSON existe y persiste
    tras una nueva petición; reactivar lo devuelve a `riesgo`.
11. Cliente autenticado no puede silenciar (redirección con aviso).
12. Regresión: suites de Sprints 4 y 5 en verde + smoke de inventario,
    planos y facturas.

## 7. Despliegue

- Push a `origin` y `review`; el G60 se actualiza copiando los módulos,
  `app.py`, `config.py` y las dos plantillas, y reiniciando `asplot`.
- En el G60 no hace falta instalar nada nuevo (Python puro + `pypdf` ya está).
- `docs/SPRINT_6.md` + fila en `GUIA_REVISION.md` + criterios de PB-11/PB-13
  marcados en `BACKLOG_IA.md`.

## 8. Riesgos

| Riesgo | Mitigación |
|---|---|
| Sin facturas en la demo | Estado `sin_historial` + alerta por mínimo; pruebas crean facturas temporales |
| DPI ausente en JPG | `no_verificable`, no se asume un valor |
| JSON de silencios corrupto | Se ignora y se regenera; nunca rompe la página |
| Consumo real ≠ facturado | Documentado; es la única fuente sin esquema nuevo |
| Falsos positivos de formato | Se compara por firma de bytes, no por nombre |
