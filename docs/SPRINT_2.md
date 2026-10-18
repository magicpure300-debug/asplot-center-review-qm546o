# ASPLOT CENTER — Sprint 2: Optimización de consultas e índices

> **PB-04 (8 pts) + PB-05 (5 pts)** — Duración: 2 semanas · Equipo: 2 desarrolladores
> Objetivo: reducir los tiempos de respuesta eliminando búsquedas completas
> (full table scan) y el patrón N+1, dejando evidencia medible.

---

## PB-05 — Índices en las tablas más consultadas

**24 índices** añadidos en `models.py` (`__table_args__`) y aplicables a BDs
existentes con `aplicar_indices.py` (idempotente, compatible SQLite y MySQL):

| Grupo | Índices | Justificación |
|---|---|---|
| `usuarios` | `rol`, `activo` | Filtrado por rol en menús y permisos |
| `clientes` | `id_usuario`, `(nombre, apellido)` | JOINs y búsquedas de clientes |
| `proyectos` | `id_cliente`, `estado`, `fecha_solicitud`, `tipo_servicio`, `presupuesto`, `(estado, tipo_servicio)` | Tablero por estado, listados ordenados y filtros del portafolio (Sprint 3) |
| `planos` | `id_proyecto`, `id_tipo_plano`, `id_usuario`, `fecha_subida` | JOINs de listados y búsqueda por fechas |
| `materiales` | `categoria`, `activo` | Filtros del inventario |
| `inventario` | `id_material` | JOIN con materiales |
| `facturas` | `id_proyecto`, `id_cliente`, `fecha_factura`, `estado_pago` | Reportes financieros |
| `detalle_facturas` | `id_factura`, `id_plano`, `id_material` | Agregaciones de facturación |

```powershell
python aplicar_indices.py                # SQLite local
python aplicar_indices.py --motor mysql  # MySQL (variables MYSQL_*)
python aplicar_indices.py --listar       # inspeccionar índices existentes
```

Verificado: 24 creados desde cero, y en cada reejecución todos omitidos (idempotente).

## PB-04 — Optimización de consultas

| Optimización | Antes | Después |
|---|---|---|
| Dashboard: conteos de clientes/proyectos/planos | 3 consultas `count()` | 1 consulta con `UNION ALL` |
| Tablero de proyectos: conteos por estado | 4 consultas `count()` | 1 consulta `GROUP BY` |
| N+1 en listados (dashboard, proyectos admin, planos, inventario, facturas, búsqueda) | 1 + N consultas (una por fila) | `selectinload` (2-3 consultas fijas) |
| Búsqueda de planos | cargaba el histórico completo (`query.all()`) | paginación `limit/offset` (20/página) con controles en la plantilla |

### Evidencia (`perf_test.py`, promedio de 3 iteraciones, SQLite local)

| Ruta | ms | Queries SQL | BD ms |
|---|---|---|---|
| `/dashboard` | 31.6 | 6 | 1.93 |
| `/clientes` | 7.9 | 5 | 0.77 |
| `/proyectos?estado=todas` | 16.9 | 4 | 0.79 |
| `/planos` | 12.8 | 6 | 1.04 |
| `/inventario` | 8.5 | 3 | 0.49 |
| `/facturas` | 10.1 | 2 | 0.37 |
| `/planos/buscar?nombre=a` | 17.7 | 7 | 1.22 |
| `/reportes` | 3.5 | 1 | 0.15 |

Con solo 22 registros las diferencias de tiempo son marginales; el impacto real
de los índices y del `selectinload` se observa con datos de producción
(el patrón N+1 dispara `7 + 7×N` consultas en inventario con N filas).

## Archivos del sprint

| Archivo | Cambio |
|---|---|
| `models.py` | 24 índices en `__table_args__` de las 8 tablas |
| `aplicar_indices.py` | Script idempotente de aplicación (SQLite/MySQL) |
| `app.py` | Conteos consolidados, `selectinload` en 6 listados, paginación |
| `templates/buscar_planos.html` | Controles de paginación con conservación de filtros |
| `static/css/style.css` | Estilos de paginación |
| `perf_test.py` | Herramienta de medición de tiempos y consultas |

## Criterios de aceptación

- [x] Índices creados en las tablas más consultadas, aplicables a SQLite y MySQL
- [x] Script idempotente verificado (2ª ejecución: 24 omitidos)
- [x] Cero consultas N+1 en los listados principales (medido con `perf_test.py`)
- [x] Conteos del tablero en una sola consulta por vista
- [x] Búsqueda de planos paginada (20 por página, filtros conservados)
- [x] Todas las rutas responden HTTP 200 tras los cambios
