# Tareas 006 — Sprint 6: Inventario predictivo + calidad de planos

> **Spec:** `specs/006-inventario-calidad/spec.md` (aprobada)
> **Plan:** `specs/006-inventario-calidad/plan.md` (aprobado)
> **Regla SDD:** una tarea a la vez; tests primero, luego código; se marca y
> se para para validación humana.

## Fase A — Módulos de cálculo

- [x] **T1. Configuración del sprint**
  - RF: RNF configuración.
  - Añadir a `config.py` las 8 constantes `INVENTARIO_*` y `CALIDAD_DPI_MINIMO`
    con defaults del plan.
  - Hecho: `python -c "from config import Config; print(Config.INVENTARIO_VENTANA_DIAS, Config.CALIDAD_DPI_MINIMO)"` responde `90 150`.

- [x] **T2. Predicción de inventario (`inventario_predictivo.py`)**
  - RF: CA1–CA4, CA7, CA8.
  - `calcular_predicciones(...)` con velocidad, divisor por histórico real,
    ajuste por activos con tope, reorden, días restantes, compra sugerida,
    estados y avisos; `Decimal`/redondeos coherentes.
  - Hecho: 3 facturas/30 días → velocidad exacta; sin facturas →
    `sin_historial`; 1 proyecto activo aplica el 10 %; casos límite
    (velocidad 0, stock 0) sin excepción.

- [x] **T3. Silencios persistentes**
  - RF: CA5.
  - `leer_silencios`/`guardar_silencios` con JSON atómico, purga de vencidos y
    tolerancia a archivo corrupto.
  - Hecho: guardar → leer devuelve la fecha; archivo corrupto → `{}` sin
    excepción; escritura no deja `.tmp` colgando.

- [x] **T4. Calidad de planos (`calidad_planos.py`)**
  - RF: CA2–CA5 de PB-13.
  - Verificaciones de archivo, formato, DPI (JFIF/pHYs), página PDF y
    legibilidad; nunca lanza excepción.
  - Hecho: PNG 300/72 dpi, PNG sin pHYs, JPG 300 dpi, JPG renombrado a PDF,
    PDF A4, PDF corrupto y archivo vacío devuelven el estado esperado.

## Fase B — Integración web

- [x] **T5. Panel de predicción en `/inventario`**
  - RF: CA1–CA4, CA7.
  - Consulta agregada de consumo, llamado a `calcular_predicciones`, paso de
    `predicciones`/`silencios` a la plantilla; tabla con estado y avisos.
  - Hecho: con facturas de prueba el panel muestra velocidad, días, reorden y
    compra; sin facturas muestra `sin_historial`.

- [x] **T6. Acciones silenciar/reactivar**
  - RF: CA5, CA8.
  - Rutas POST con RBAC, escritura del JSON y flashes; botones en el panel.
  - Hecho: silenciar oculta la alerta activa y persiste tras recargar;
    reactivar la devuelve; cliente recibe redirección con aviso.

- [x] **T7. Checklist en detalle del plano y aviso al subir**
  - RF: PB-13 CA1–CA5.
  - `detalle_plano` pasa `calidad`; tarjeta en la plantilla; `subir_plano`
    añade flashes de advertencia sin bloquear.
  - Hecho: subir un PNG de 72 dpi guarda el plano y muestra la advertencia;
    el detalle lista los ítems con su estado.

## Fase C — Verificación y entrega

- [x] **T8. Suite `test_sprint6.py` y regresión**
  - RF: todos los CA + RNF.
  - Hecho: 12 grupos del plan en verde; `test_sprint4.py` y
    `test_sprint5.py` sin regresiones.

- [x] **T9. Documentación**
  - RF: RNF documentación.
  - `docs/SPRINT_6.md`, fila en `GUIA_REVISION.md`, criterios marcados en
    `BACKLOG_IA.md`.
  - Hecho: documentos coherentes con la spec y las pruebas.

- [ ] **T10. Despliegue en el G60 y verificación**
  - RF: RNF portabilidad.
  - Push a `origin`/`review`, copiar archivos al G60, reiniciar `asplot` y
    probar el panel y el checklist con datos reales.
  - Hecho: `/inventario` y `/planos/detalle/<id>` responden 200 en LAN y
    túnel; suite completa en verde en el teléfono.
