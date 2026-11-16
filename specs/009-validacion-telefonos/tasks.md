# Tareas — Validación de teléfonos (Sprint 8)

- [x] **T1. Módulo de validación**
  - RF: CA1-CA4.
  - `validacion_telefono.py` con catálogos y cuatro funciones públicas.
  - Hecho: casos móvil/fijo/internacional válidos e inválidos verificados a mano.

- [x] **T2. Integración en las rutas**
  - RF: CA1-CA3, CA6.
  - `/registro`, `/clientes/crear`, `/clientes/editar/<id>`, `/solicitud`,
    `/usuarios/crear`, `/usuarios/editar/<id>`, `/configuracion/actualizar`.
  - Hecho: ningún formulario guarda un valor inválido; el valor guardado es
    el canónico.

- [x] **T3. Interfaz**
  - RF: CA4, CA5.
  - Atributos en los 7 inputs, texto de ayuda, `telefono.js` y estilos.
  - Hecho: el hint muestra operadora/estado y el envío inválido se bloquea.

- [x] **T4. Suite y regresión**
  - RF: CA7.
  - `test_sprint8.py` + suites 5, 6, 7 y smoke de diseño.
  - Hecho: todo en verde en PC y en el G60.

- [x] **T5. Documentación y despliegue**
  - RF: RNF documentación/portabilidad.
  - `docs/SPRINT_8.md`, `GUIA_REVISION.md`, `scripts/demo_datos.py` si aplica,
    copia al G60 y verificación en vivo.
  - Hecho: demo actualizada y commit en `develop` + mirror.
