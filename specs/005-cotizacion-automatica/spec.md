# Spec 005 — Sprint 5: Cubicación y cotización automática (PB-10)

> **Estado:** pendiente de aprobación
> **Sprint:** 5 · **Puntos:** 8 (PB-10)
> **Depende de:** Sprint 4 (solicitudes online con adjunto) + módulo de planos y
> tabla de materiales/inventario (Sprints 1–3)
> **Fase:** 2 (backlog de IA `docs/BACKLOG_IA.md`) — versión v1 determinista,
> sin LLM

---

## 1. Problema

Hoy toda cotización es manual: el administrador abre
`/proyectos/<id>/aprobar`, estima «de memoria» el precio (el único apoyo es un
`precio_base` fijo de $15 para plano/corrección) e introduce el presupuesto a
mano. No se considera el tamaño real del plano que el cliente adjuntó ni el
consumo de papel/tinta que la impresión implicará.

Consecuencias: respuestas comerciales lentas (el visitante que envió una
solicitud pública espera), precios inconsistentes entre personas, y riesgo de
cotizar por debajo del costo cuando el plano es grande. El docente señaló esta
brecha en la revisión del ERS y el backlog de IA la ubica como la primera
historia de la Fase 2.

## 2. Objetivos

1. Calcular automáticamente el **área de impresión (m²)** de un plano adjunto
   (PDF o DXF) sin intervención humana.
2. Convertir esa área en una **propuesta de precio** con desglose visible
   (área × tarifa + insumos + margen), usando la tabla `materiales` para el
   costo de insumos.
3. Preservar la regla de negocio: **el sistema solo sugiere; el precio final lo
   fija el humano** con el flujo de cotización existente.

## 3. Alcance

### Dentro del alcance

- Botón «Calcular automáticamente» en el formulario de cotización
  (`/proyectos/<id>/aprobar`) y acceso equivalente desde la bandeja de
  solicitudes (`/solicitudes` → mismo formulario con el cálculo precargado).
- Extracción de tamaño de página en **PDF** (todas las páginas, suma de áreas).
- Lectura de extensiones de dibujo (`$EXTMIN`/`$EXTMAX`) en **DXF** y
  conversión a m².
- Selección automática del archivo a analizar: **planos subidos del proyecto
  (del más reciente al más antiguo) y después el adjunto de la solicitud
  pública**; se usa el primer candidato con formato analizable.
- Fórmula de precio: `(área × tarifa/m²) + insumos + margen`, con tarifa y
  margen **configurables por entorno** y desglose mostrado en pantalla.
- Estimación de consumo de insumos (papel y tinta) desde `materiales` +
  `inventario`, incluida la disponibilidad informativa de stock.
- Respuesta clara cuando el archivo no es analizable, dejando la cotización
  manual intacta.

### Fuera del alcance (para no inflar el sprint)

- Formato **.DWG** (propietario; requiere conversor ODA) — cubierto por
  PDF/DXF, que es el flujo de subida del sistema.
- Imágenes (JPG/PNG): no tienen tamaño de página fiable (la app no puede
  leer DPI en el G60, donde no hay Pillow) → se tratan como «no analizable».
- Componente **LLM+RAG** (v2): interpretación de planos no normalizados;
  queda documentado en `BACKLOG_IA.md` para fase posterior.
- Envío automático de la cotización al cliente por email/SMS (sigue pendiente
  desde el Sprint 4).
- Modificación automática del estado del proyecto o del presupuesto **sin**
  pasar por el formulario del admin.
- Persistencia del desglose en columnas nuevas (no se agrega esquema; ver §6).

## 4. Historias de usuario y criterios de aceptación

### PB-10 — Cubicación y cotización automática (8 pts)

**Como** administrador, **quiero** un botón que calcule área y precio de un
plano **para** responder la cotización sin estimar a mano.

Criterios de aceptación:

1. Con un **PDF estándar (A0–A4)**, el sistema extrae el tamaño de página
   correcto sin intervención y muestra el área total en m² (suma de todas las
   páginas).
2. Con un **DXF**, calcula la extensión del dibujo y la convierte a m² de
   impresión; si el DXF no declara unidades, se asumen milímetros **y se
   muestra la advertencia** en el desglose.
3. El cálculo se dispara con un botón «Calcular automáticamente» en el
   formulario de cotización; el resultado **rellena el campo de presupuesto**
   y muestra el desglose (área, tarifa, insumos, margen, total). El admin
   puede editar el monto antes de guardar.
4. La fórmula es: `total = (área × tarifa_m2) + insumos + margen`, donde
   - **tarifa_m2**: constante configurable por variable de entorno;
   - **insumos**: consumo estimado de papel y tinta **proporcional al área**
     (fracción de rollo A0 / cartucho según rendimiento configurable),
     tomados de `materiales` a **precio de compra** y redondeados a centavos,
     más disponibilidad informativa desde `inventario`;
   - **margen**: porcentaje configurable, aplicado sobre (área × tarifa +
     insumos).
5. Al guardar el formulario con ese valor, rige el flujo existente: el
   proyecto pasa a estado `cotizado` con el presupuesto indicado **por acción
   explícita del admin** (el cálculo por sí solo no modifica la base).
6. Selección de archivo: se analizan, en orden, los planos subidos (del más
   reciente al más antiguo) y después el adjunto de la solicitud
   (`archivo_solicitud`); se usa el **primer candidato con formato
   analizable** (PDF/DXF). Si no hay ninguno, el botón muestra «sube un plano
   o adjunta el PDF para calcular» y no rellena nada.
7. Si el formato no es analizable (DWG, JPG, PNG), el archivo está **ausente
   del disco** o es ilegible (PDF corrupto o protegido con contraseña, DXF
   ilegible o con extensiones ausentes), el sistema **lo indica con mensaje
   claro** y deja la cotización manual (el formulario funciona igual que hoy).
8. Desde la bandeja `/solicitudes`, el enlace de cotizar lleva al mismo
   formulario con el cálculo ya ejecutado (parámetro en la URL), sin escribir
   en la base.
9. Solo roles con permiso de cotizar (admin/trabajador, misma regla RBAC
   actual) pueden usar el cálculo; un cliente autenticado recibe
   redirección con aviso.
10. El desglose puede incorporarse a las **notas** del proyecto con un clic:
    se **concatena** al final de las notas existentes (nunca las sobrescribe),
    con fecha y hora del cálculo, sin crear tablas nuevas.

## 5. Requisitos no funcionales

- **Portabilidad (decisión validada):** sin librerías nativas. PDF se lee con
  `pypdf` (puro Python) y DXF con un lector propio de la cabecera de
  extensiones. Debe funcionar igual en Windows (dev), Render (Linux) y el
  **G60 (Termux/Android)**, donde las wheels nativas como Pillow/PyMuPDF
  fallan.
- **Determinismo:** la misma entrada produce siempre el mismo cálculo; sin
  servicios externos ni API keys. La v2 (LLM) se conectará después sobre estos
  datos estructurados.
- **Seguridad:** RBAC en el endpoint de cálculo; las rutas de archivo se
  derivan solo de registros de base (nunca de entrada del usuario) y se
  resuelven dentro de las carpetas de subida; el lector tolera archivos
  corruptos (nunca un 500: siempre mensaje controlado y la tarifa/margen no
  son manipulables vía POST, solo por configuración).
- **Rendimiento:** el análisis es bajo demanda (botón), no en cada carga de
  página; PDF se lee solo en cabecera/páginas (sin renderizar); DXF solo la
  cabecera `$EXTMIN/$EXTMAX`.
- **Sin migración:** ninguna columna ni tabla nueva (regla transversal del
  backlog: «ninguna HU de IA modifica el esquema existente»).
- **Configuración:** constantes con `os.environ.get(..., default)` en
  `config.py`, mismo patrón que `SECRET_KEY`/`FLASK_CONFIG`; valores por
  defecto válidos para la demo sembrada. `.env.example` documentado, sin
  secretos versionados.
- **Documentación:** `docs/SPRINT_5.md` con detalle técnico y pruebas, alineado
  al formato de `SPRINT_2.md`/`SPRINT_3.md`/`SPRINT_4.md`; fila en
  `docs/GUIA_REVISION.md`.

## 6. Modelo de datos (sin cambios de esquema)

| Entidad | Uso en Sprint 5 | Cambios |
|---|---|---|
| `Proyecto` | `archivo_solicitud`, `presupuesto`, `notas` (desglose opcional) | ninguno |
| `Plano` | archivo a analizar (más reciente por proyecto) | ninguno |
| `Material` | precios de compra de papel/tinta para insumos | ninguno |
| `Inventario` | disponibilidad informativa de stock | ninguno |

La propuesta «se registra en la solicitud» = el presupuesto calculado se
propone en el formulario y se persiste con el guardado existente
(`presupuesto` + estado `cotizado`), sin pasos extra ni tablas nuevas.

## 7. Criterios de éxito

- Un PDF A4 de prueba devuelve ≈ 0,0625 m² y un DXF de 2×1 m devuelve 2 m²
  sin tocar nada más.
- El desglose completo (área, tarifa, insumos, margen, total) es verificable a
  mano con los mismos datos de entrada.
- Archivo no analizable → mensaje claro y formulario manual operativo.
- Suite `test_sprint5.py` en verde + regresión de Sprints 1–4 en verde.
- La app sigue arrancando y cotizando en el G60 tras el despliegue (mismas
  rutas, mismos datos).

## 8. Riesgos y preguntas abiertas

1. **DXF sin `$EXTMIN`/`$EXTMAX`:** algunos editores no los guardan. Plan de
   respaldo (v1): se declara «no analizable» en lugar de parsear todas las
   entidades; documentado como limitación.
2. **Unidades DXF ambiguas:** se lee `$INSUNITS` si existe; si no, se asumen
   mm con advertencia visible (CA2).
3. **Insumos con datos sembrados:** el costo de papel/tinta a precio de
   compra puede superar el área × tarifa en planos pequeños (decisión
   validada: se suma al total igual, porque en producción los precios reales
   sí incluyen margen; la demo muestra el desglose completo para que el admin
   ajuste).
4. **Precios de compra en 0:** si un material tiene `precio_compra = 0`, el
   insumo computa 0 y el desglose lo marca «sin precio cargado».
5. **Numeración:** PB-10 corresponde al backlog de IA; este sprint es el
   primero de la Fase 2 pero se entrega con el mismo flujo SDD y numeración de
   specs (005).
