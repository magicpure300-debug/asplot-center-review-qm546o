# ASPLOT CENTER — Migración de Base de Datos: SQLite → MySQL

> **Sprint 1 (PB-01, PB-02, PB-03)** — Patrón *Strangler Fig*: migración
> incremental que mantiene el sistema operativo, con SQLite como opción de
> respaldo mientras MySQL no esté disponible en producción.

---

## 1. Artefactos del Sprint 1

| Archivo | Historia | Descripción |
|---|---|---|
| `migrate_sqlite_to_mysql.py` | PB-01 | Script principal: exporta esquema y datos desde SQLite, genera `create_mysql_schema.sql` y `datos_exportados.json`, y (opcionalmente) ejecuta la importación en MySQL |
| `importar_a_mysql.py` | PB-02 | Importación alternativa vía SQLAlchemy, para entornos donde no se pueda ejecutar el archivo SQL directamente |
| `validar_migracion.py` | PB-03 | Valida la integridad de los datos: conteos, huella de datos y claves foráneas huérfanas |
| `config.py` | PB-01 | Incorpora `MySQLConfig` y detección automática de variables de entorno `MYSQL_*`; SQLite se mantiene como respaldo |
| `migracion/` | — | Carpeta de salida con los archivos generados (se excluye del repositorio por contener datos sensibles) |

---

## 2. Requisitos previos

- Python 3.8+
- `pip install -r requirements.txt` (incluye `PyMySQL`)
- Un servidor **MySQL 8.0+** accesible (local o remoto)

---

## 3. Variables de entorno MySQL

| Variable | Por defecto | Ejemplo |
|---|---|---|
| `MYSQL_HOST` | *(sin definir)* | `localhost` |
| `MYSQL_PORT` | `3306` | `3306` |
| `MYSQL_USER` | `root` | `root` |
| `MYSQL_PASSWORD` | *(vacía)* | `secret` |
| `MYSQL_DATABASE` | `asplot_center` | `asplot_center` |

La aplicación **solo** usará MySQL si `MYSQL_HOST`, `MYSQL_USER` y
`MYSQL_PASSWORD` están definidas; en caso contrario sigue operando sobre
SQLite (`instance/asplot_database.db`).

Puede copiar `.env.example` como referencia (cargar las variables con su
método preferido: PowerShell, terminal, systemd, etc.).

---

## 4. Proceso de migración (3 fases)

### Fase 1 — Exportación y transformación (PB-01)

```powershell
python migrate_sqlite_to_mysql.py
```

Genera en `migracion/`:
- `datos_exportados.json`: todos los registros en formato portable.
- `create_mysql_schema.sql`: `CREATE DATABASE` (utf8mb4), `CREATE TABLE` e
  `INSERT` en el orden de dependencias de claves foráneas.

Conversiones aplicadas: `INTEGER→INT`, `NUMERIC(p,s)→DECIMAL(p,s)`,
`BOOLEAN→TINYINT(1)`, `DATETIME→DATETIME(6)`, `VARCHAR(n)→VARCHAR(n)`.

### Fase 2 — Carga en MySQL (dos opciones)

**Opción A — archivo SQL (recomendada):**
```powershell
$env:MYSQL_HOST="localhost"; $env:MYSQL_USER="root"; $env:MYSQL_PASSWORD="secret"
python migrate_sqlite_to_mysql.py --importar
# ... o ejecutar migracion/create_mysql_schema.sql en MySQL Workbench
```

**Opción B — importación vía SQLAlchemy:**
```powershell
python importar_a_mysql.py            # usa migracion/datos_exportados.json
python importar_a_mysql.py --vaciar   # limpia las tablas antes de importar
```

### Fase 3 — Validación de integridad (PB-03)

```powershell
python validar_migracion.py
```

Verifica por cada tabla: existencia, conteo de registros, **huella de datos**
(normaliza DECIMAL/float, TINYINT/bool y precisión de fechas entre motores) y
registros huérfanos en claves foráneas. Código de salida `0` = migración
exitosa; `1` = diferencias; `2` = sin conexión a MySQL.

---

## 5. Ejecutar la aplicación sobre MySQL

```powershell
$env:MYSQL_HOST="localhost"; $env:MYSQL_USER="root"; $env:MYSQL_PASSWORD="secret"
$env:FLASK_CONFIG="mysql"
python run_dev.py
```

Sin esas variables, la aplicación arranca normalmente sobre SQLite
(compatibilidad hacia atrás garantizada).

---

## 6. Criterios de aceptación (Sprint Review)

- [x] Las 9 tablas del sistema existen en MySQL con sus estructuras y
      relaciones foráneas intactas (`usuarios`, `clientes`, `proyectos`,
      `tipos_plano`, `planos`, `materiales`, `inventario`, `facturas`,
      `detalle_facturas`).
- [x] Los 22 registros de SQLite se migran sin pérdida ni corrupción
      (verificado con `validar_migracion.py`).
- [x] La aplicación Flask puede conectarse a MySQL configurando variables de
      entorno (`FLASK_CONFIG=mysql` + `MYSQL_*`).
- [x] Esquema compatible con MySQL 8.0, codificación UTF-8 / `utf8mb4_unicode_ci`
      (soporte de caracteres especiales del español).
- [x] SQLite se mantiene como opción de respaldo mientras MySQL no esté en
      producción.
