# Especificación — Validación de teléfonos (Sprint 8)

> **Historia:** PB-16 (mejora de calidad de datos)
> **Origen:** observación del usuario (nov-2026): el sistema acepta
> teléfonos con cualquier longitud o prefijo, sin verificar que
> correspondan a una línea real de Venezuela.

## Problema

Todos los formularios con teléfono (`/registro`, `/clientes/crear`,
`/clientes/editar/<id>`, `/solicitud`, `/usuarios/crear`,
`/usuarios/editar/<id>`, `/configuracion/actualizar`) guardan el texto tal
como se escribe. Se puede registrar `123`, `0414`, `04141917498x` o un
prefijo inexistente como `0417`, y la base queda con datos inutilizables.

## Objetivo

Validar el teléfono en el servidor (obligatorio) y en el navegador
(experiencia), aceptando únicamente números venezolanos válidos y
guardándolos siempre en la forma canónica de 11 dígitos.

## Reglas de negocio

1. **Longitud exacta:** 11 dígitos locales (`04141917498`).
2. **Móvil:** prefijo de 4 dígitos dentro del plan vigente:
   - `0412`, `0422` → Digitel
   - `0414`, `0424` → Movistar
   - `0415` → Tesan
   - `0416`, `0426` → Movilnet
   - `0417` y `0418` **no**: fueron eliminados en 2006.
3. **Fijo:** `02XX` + 7 dígitos, con código de área existente
   (`0212`, `0241`, `0291`, …). Un `02XX` inventado se rechaza.
4. **Formatos de entrada aceptados:** espacios, guiones, puntos,
   paréntesis y prefijo internacional `+58`, `0058` o `58`.
5. **Se rechaza:** letras, longitud distinta de 11, prefijo desconocido,
   código de área inexistente y números con todos los dígitos iguales.
6. **Canónico:** en la base se guarda siempre `04141917498` (sin
   separadores). La interfaz muestra `0414-1917498`.
7. **Opcionalidad:** en usuarios y configuración el campo sigue siendo
   opcional; si se envía, debe ser válido. En cliente, registro y
   solicitud es obligatorio.

## Criterios de aceptación

- [ ] CA1. Un teléfono inválido no se guarda en ninguna de las 7 rutas.
- [ ] CA2. El error indica el motivo (longitud, prefijo, área, caracteres).
- [ ] CA3. `+58 414 1917498`, `0414-1917498` y `04141917498` producen el
      mismo valor almacenado.
- [ ] CA4. Un móvil válido muestra su operadora; un fijo, su estado.
- [ ] CA5. El formulario avisa en vivo antes de enviar y bloquea el envío
      inválido.
- [ ] CA6. Los datos existentes no se migran ni se reescriben.
- [ ] CA7. Suites de Sprints 5, 6, 7 y smoke de diseño siguen en verde.

## Fuera de alcance

- Verificación por SMS/código de la línea (requiere proveedor externo y
  costo por mensaje).
- Validación de teléfonos de otros países (el sistema es de Venezuela).
- Cambios de esquema o migraciones.
