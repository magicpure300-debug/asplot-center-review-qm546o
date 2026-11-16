# ASPLOT CENTER — Sprint 8: Validación de teléfonos

> **Mejora de calidad de datos (PB-16)** a partir de una observación real:
> el sistema aceptaba cualquier texto en el teléfono, sin longitud ni
> prefijo válido. Ahora se valida en el servidor y en el navegador, y se
> guarda siempre la forma canónica de 11 dígitos.

---

## Reglas implementadas

| Tipo | Formato | Prefijos / códigos aceptados |
|---|---|---|
| Móvil | `04XX-XXXXXXX` | 0412 y 0422 (Digitel), 0414 y 0424 (Movistar), 0415 (Tesan), 0416 y 0426 (Movilnet) |
| Fijo | `02XX-XXXXXXX` | códigos de área reales (0212, 0241, 0291, …); un `02XX` inventado se rechaza |

- **0417 y 0418 se rechazan:** fueron eliminados en 2006.
- Se aceptan espacios, guiones, puntos, paréntesis y prefijo `+58`, `0058`
  o `58`; también el número sin el cero inicial (`4141917498`).
- Se rechazan letras, longitudes distintas de 11, prefijos desconocidos,
  áreas inexistentes y números con todos los dígitos iguales.
- **Canónico en base:** `04141917498`. **En pantalla:** `0414-1917498`.

## Dónde se aplica

| Ruta | Campo | Obligatorio |
|---|---|---|
| `/registro` | alta de cliente | sí |
| `/clientes/crear` y `/clientes/editar/<id>` | ficha de cliente | sí |
| `/solicitud` | solicitud pública | sí |
| `/usuarios/crear` y `/usuarios/editar/<id>` | usuario interno | opcional |
| `/configuracion/actualizar` | perfil propio | opcional |

En `/solicitud` el error se muestra junto al campo y no se pierden los datos
escritos; en el resto se avisa con un mensaje y se vuelve al formulario.

## Experiencia de usuario

- El campo declara `maxlength`, `inputmode="tel"`, `autocomplete="tel"` y
  un texto de ayuda con el formato.
- `static/js/telefono.js` replica las reglas y, mientras se escribe, indica
  la línea detectada: **«Móvil Movilnet (0416)»**, **«Fijo — Monagas (0291)»**
  o el motivo del error. Un valor inválido bloquea el envío.
- El servidor vuelve a validar: el JavaScript es comodidad, no seguridad.

## Pruebas

Suite `test_sprint8.py`: **61 comprobaciones en verde**.

- **Módulo (23):** los 7 prefijos móviles, `+58`, `0058`, número sin cero,
  fijos 0212/0291, formateo, descripción y 9 casos inválidos.
- **Catálogo (2):** los prefijos y áreas del JavaScript coinciden
  exactamente con los de Python.
- **Rutas (19):** rechazo y aceptación en las 7 rutas, verificación de que
  no se guarda nada inválido y de que el valor guardado es el canónico,
  incluido el caso opcional vacío.
- **Interfaz (17):** las 7 páginas cargan `telefono.js` y muestran la ayuda;
  los estilos existen.
- **Regresión:** suites de Sprints 5, 6, 7 y smoke de diseño en verde.

## Decisiones

| Decisión | Motivo |
|---|---|
| Catálogo cerrado de prefijos y áreas | Permite decir «esta línea no existe», no solo contar dígitos |
| Guardar sin separadores | Búsquedas y reportes consistentes; el formato es presentación |
| Sin constraint en la base | Regla del proyecto: mejoras sin migraciones |
| Validar también en el navegador | Evita el viaje al servidor y guía al usuario |
| 0415 aceptado | Operador vigente; rechazarlo bloquearía líneas reales |

## Limitaciones documentadas

- **No se verifica la titularidad por SMS:** requiere un proveedor externo y
  costo por mensaje; queda fuera del alcance académico.
- **Solo Venezuela:** un teléfono extranjero se rechaza a propósito.
- **Datos históricos:** no se migran; al editar un registro antiguo se exige
  corregir el teléfono.
- **Fijos:** se valida el código de área, no la existencia física de la línea.

## Despliegue

- Archivos nuevos: `validacion_telefono.py`, `static/js/telefono.js`,
  `specs/009-validacion-telefonos/`, `tests/`.
- Modificados: `app.py`, `style.css`, 7 plantillas, `scripts/demo_datos.py`.
- Verificado en el G60 con la suite y con el formulario en vivo.
