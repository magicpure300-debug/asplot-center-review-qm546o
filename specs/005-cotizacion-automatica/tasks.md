# Tareas 005 — Sprint 5: Cubicación y cotización automática

> **Spec:** `specs/005-cotizacion-automatica/spec.md` (aprobada)
> **Plan:** `specs/005-cotizacion-automatica/plan.md` (aprobado)
> **Regla SDD:** una tarea a la vez; tests primero, luego código; se marca y
> se para para validación humana.

## Fase A — Base

- [x] **T1. Configuración y dependencia**
  - RF: RNF configuración/portabilidad.
  - Añadir a `config.py` las 4 constantes `COTIZACION_*` con `os.environ.get`
    y defaults (8.0 / 30 / 10 / 20); agregar `pypdf==6.4.0` a
    `requirements.txt`; instalarlo en el Python local.
  - Hecho: `python -c "import pypdf; print(pypdf.__version__)"` responde y
    `Config.COTIZACION_TARIFA_M2 == 8.0`.

- [x] **T2. Análisis de PDF (`cotizador_auto.py`)**
  - RF: CA1, CA7, RNF determinismo.
  - `analizar_pdf(ruta)`: suma de páginas con `mediabox`, conversión a m²,
    detección A0–A4 (±2 %), PDF cifrado/corrupto → `ok:false` con mensaje.
  - Hecho: pruebas rápidas con PDF A4 (≈0.0624 m²) y A0×2 (≈2.0 m²) en
    verde; PDF corrupto devuelve mensaje sin excepción.

- [x] **T3. Análisis de DXF (`cotizador_auto.py`)**
  - RF: CA2, CA7.
  - Lector de cabecera: `$INSUNITS`, `$EXTMIN`, `$EXTMAX`; conversión de
    unidades; binario → `ok:false`; sin extensiones → `ok:false`.
  - Hecho: DXF 2000×1000 mm → 2.0 m²; DXF en metros → 2.0 m²; sin unidades
    → 2.0 m² + advertencia; los 4 casos límite devuelven mensajes claros.

- [x] **T4. Cálculo de precio y texto del desglose**
  - RF: CA4, CA10.
  - `calcular_precio(...)` con la fórmula del plan (redondeos con `Decimal`
    o `round` a 2 decimales), insumos papel/tinta con stock, advertencias
    por precio 0 o sin materiales; `texto_desglose(...)`.
  - Hecho: con área 1.0, tarifa 8, margen 30, papel 18/rend. 10 y tinta
    45/rend. 20 → base 8.00, insumos 4.05 (1.80 + 2.25), margen 3.62,
    total 15.67 (verificado a mano); texto incluye área, líneas y total.

## Fase B — Integración web

- [x] **T5. Endpoint `/proyectos/<id>/cotizacion-automatica`**
  - RF: CA3, CA6, CA7, CA9.
  - Ruta POST JSON con RBAC admin/trabajador; selección de archivo
    (planos recientes → adjunto, saltando no analizables); consulta de
    materiales/inventario; respuesta `ok:true/false`; sin escrituras en base.
  - Hecho: con un proyecto de prueba responde 200 + JSON correcto; cliente
    → 403; sin sesión → 302; DWG reciente + PDF anterior → analiza el PDF;
    `presupuesto`/`estado` intactos tras la llamada.

- [x] **T6. Botón y panel en `aprobar_proyecto.html`**
  - RF: CA3, CA4, CA10, RNF usabilidad.
  - Botón «Calcular automáticamente», panel de desglose oculto, JS fetch,
    relleno de `#presupuesto` (con confirmación si ya hay valor), botón
    «Añadir desglose a notas» (concatena con fecha) y disparo con `?auto=1`.
  - Hecho: en navegador local, el botón pinta el desglose y rellena el
    campo; un archivo DWG muestra el aviso y no toca el formulario.

- [x] **T7. Acceso desde la bandeja de solicitudes**
  - RF: CA8.
  - `solicitudes.html`: el enlace «Cotizar» pasa a `aprobar_proyecto` con
    `auto=1`.
  - Hecho: desde `/solicitudes`, «Cotizar» abre el formulario con el
    cálculo ya ejecutado.

## Fase C — Verificación y entrega

- [x] **T8. Suite `test_sprint5.py` completa y regresión**
  - RF: todos los CA (17 checks del plan §6) + RNF.
  - Hecho: `test_sprint5.py` en verde (incluye PDF/DXF generados,
    endpoint, RBAC, no-escritura, stock) y `test_sprint4.py` sin
    regresiones.

- [x] **T9. Documentación del sprint**
  - RF: RNF documentación.
  - `docs/SPRINT_5.md` (detalle técnico, fórmula, pruebas, limitaciones),
    fila en `docs/GUIA_REVISION.md`, marcar PB-10 v1 en
    `docs/BACKLOG_IA.md`.
  - Hecho: los tres documentos actualizados y coherentes con la spec.

- [ ] **T10. Despliegue y verificación end-to-end**
  - RF: RNF portabilidad (G60, Render).
  - Push de `develop` a `origin` y `review`; copiar archivos al G60,
    instalar `pypdf` en su venv, reiniciar `asplot` y probar una cotización
    real; confirmar redeploy de Render.
  - Hecho: `/asplot/` responde 200 en LAN y túnel; una cotización de prueba
    devuelve desglose correcto; suite completa en verde tras el despliegue.
