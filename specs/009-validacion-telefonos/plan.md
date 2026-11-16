# Plan técnico — Validación de teléfonos (Sprint 8)

## Componentes

| Componente | Responsabilidad |
|---|---|
| `validacion_telefono.py` | Catálogos (prefijos móviles, códigos de área) y funciones `normalizar_telefono`, `validar_telefono`, `formatear_telefono`, `describir_telefono`. Sin dependencias. |
| `app.py` | Valida y normaliza en las 7 rutas de escritura; mensajes de error por campo. |
| `static/js/telefono.js` | Misma regla en el navegador: hint en vivo (operadora/estado), `setCustomValidity` y bloqueo del envío. |
| `templates/*.html` | Atributos `maxlength`, `inputmode`, `autocomplete`, texto de ayuda y carga del script. |
| `static/css/style.css` | Estilos de la ayuda (neutra, válida, error). |

## Flujo servidor

```
POST formulario
  └─ validar_telefono(texto, obligatorio)
       ├─ ok  → se guarda el valor canónico
       └─ error → flash(mensaje) + redirect al formulario (o errores[campo]
                  en /solicitud, que re-renderiza con el detalle)
```

En `/solicitud` el error se integra al diccionario `errores` existente para
mostrarse junto al campo, sin perder los datos ya escritos.

## Normalización

1. Quitar espacios, guiones, puntos, paréntesis y `/`.
2. Quitar `+`, `0058` o `58` inicial.
3. Si quedan 10 dígitos y empieza por `2` o `4`, anteponer `0`.
4. Exigir 11 dígitos; validar prefijo (móvil) o código de área (fijo).

## Decisiones

| Decisión | Motivo |
|---|---|
| Validar en servidor y navegador | El navegador da feedback; el servidor es la garantía real (se puede saltar el HTML). |
| Guardar sin separadores | Búsquedas y comparaciones consistentes; el formato es solo presentación. |
| Catálogo cerrado de prefijos y áreas | Es lo que permite decir «esta línea no existe» en vez de solo contar dígitos. |
| Sin constraint en la base | Regla del proyecto: sin migraciones en mejoras; la validación vive en la capa de aplicación. |
| 0415 (Tesan) aceptado | Operador vigente en el plan; rechazarlo bloquearía líneas reales. |
| 0417/0418 rechazados | Eliminados en 2006 y reasignados a 0412. |

## Riesgos

- **Datos históricos inválidos:** no se tocan; al editarlos se exige corregir.
- **Números extranjeros:** se rechazan a propósito (fuera de alcance).
- **Duplicados de código:** el catálogo del servidor y el de JS deben
  mantenerse iguales; hay una prueba que compara las listas.

## Verificación

Suite `test_sprint8.py`: unidad del módulo, las 7 rutas (rechazo y
aceptación), normalización, plantillas y regresión de las suites 5/6/7.
