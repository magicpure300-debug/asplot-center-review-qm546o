# As Plot Center - Sistema de Gestión de Planos

## Descripción del Proyecto

**As Plot Center** es una aplicación web interna desarrollada para la gestión y administración de una empresa de ploteo e impresión de planos. La plataforma digitaliza y centraliza las operaciones, reemplazando los métodos manuales tradicionales.

### Características Principales

- **Gestión de Clientes**: Administración completa de información de clientes
- **Gestión de Proyectos**: Seguimiento y administración de proyectos de construcción
- **Gestión de Planos**: Subida, visualización y descarga de planos digitales (PDF, DWG, DXF)
- **Dashboard**: Resumen general con KPIs y métricas del negocio
- **Reportes**: Generación de reportes en PDF para diferentes módulos
- **Configuración**: Gestión de perfil de usuario y configuraciones del sistema

## Tecnologías Utilizadas

### Backend
- **Python 3.8+**
- **Flask 2.3.3** - Framework web
- **Flask-SQLAlchemy 3.0.5** - ORM para base de datos
- **Flask-Login 0.6.3** - Manejo de autenticación
- **SQLite** - Base de datos (respaldo local)
- **MySQL 8.0** - Base de datos objetivo (Sprint 1, vía variables de entorno `MYSQL_*`)
- **FPDF2 2.7.6** - Generación de reportes PDF

### Frontend
- **HTML5** - Estructura de páginas
- **CSS3** - Estilos y diseño responsivo
- **JavaScript (Vanilla)** - Interactividad del cliente
- **Font Awesome 6.0.0** - Iconografía

## Estructura del Proyecto

```
Programa Asplot/
├── static/
│   ├── css/
│   │   └── style.css          # Estilos principales
│   ├── js/
│   │   └── main.js           # JavaScript principal
│   ├── images/               # Imágenes y logos
│   └── uploads/
│       └── planos/           # Archivos de planos subidos
├── templates/
│   ├── layout.html          # Plantilla base
│   ├── login.html           # Página de inicio de sesión
│   ├── dashboard.html       # Dashboard principal
│   ├── clientes.html        # Lista de clientes
│   ├── crear_cliente.html    # Formulario crear cliente
│   ├── editar_cliente.html   # Formulario editar cliente
│   ├── proyectos.html        # Lista de proyectos
│   ├── crear_proyecto.html   # Formulario crear proyecto
│   ├── editar_proyecto.html  # Formulario editar proyecto
│   ├── planos.html          # Lista de planos
│   ├── subir_plano.html     # Formulario subir plano
│   ├── reportes.html        # Generación de reportes
│   └── configuracion.html   # Configuración de usuario
├── app.py                   # Aplicación Flask principal
├── models.py                # Modelos SQLAlchemy
├── config.py               # Configuración de la aplicación
├── requirements.txt         # Dependencias Python
└── asplot_database.db      # Base de datos SQLite
```

## Instalación y Configuración

### Prerrequisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### Pasos de Instalación

1. **Clonar o descargar el proyecto**
   ```bash
   # Si tienes el proyecto en un repositorio
   git clone <url-del-repositorio>
   
   # O simplemente navegar al directorio del proyecto
   cd "Programa Asplot"
   ```

2. **Crear entorno virtual (recomendado)**
   ```bash
   # Crear entorno virtual
   python -m venv venv
   
   # Activar entorno virtual
   # En Windows:
   venv\Scripts\activate
   
   # En Linux/Mac:
   source venv/bin/activate
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecutar la aplicación**
   ```bash
   python app.py
   ```

5. **Acceder a la aplicación**
   - Abrir navegador web
   - Ir a: `http://localhost:5000`
   - Usar las credenciales por defecto:
     - **Email**: admin@asplot.com
     - **Contraseña**: admin123

## Uso del Sistema

### Autenticación

El sistema está protegido por un sistema de login. Las credenciales por defecto son:
- **Email**: admin@asplot.com
- **Contraseña**: admin123

### Módulos Principales

#### 1. Dashboard
- Vista general de las operaciones
- KPIs en tiempo real
- Métricas de clientes, proyectos, planos y ventas
- Información de inventario y finanzas

#### 2. Gestión de Clientes
- **Crear**: Agregar nuevos clientes con información completa
- **Leer**: Visualizar lista de clientes con búsqueda
- **Actualizar**: Modificar información de clientes existentes
- **Eliminar**: Remover clientes del sistema

#### 3. Gestión de Proyectos
- **Crear**: Registrar nuevos proyectos de construcción
- **Leer**: Visualizar proyectos en formato de tarjetas
- **Actualizar**: Modificar detalles de proyectos
- **Eliminar**: Remover proyectos del sistema
- **Filtrar**: Por estado (Planificación, En Progreso, Completado, Cancelado)

#### 4. Gestión de Planos
- **Subir**: Cargar archivos de planos (PDF, DWG, DXF, JPG, PNG)
- **Ver**: Visualizar planos directamente en el navegador
- **Descargar**: Descargar archivos de planos
- **Eliminar**: Remover planos del sistema
- **Filtrar**: Por tipo de plano y proyecto

#### 5. Reportes
- **Generar PDF**: Crear reportes en formato PDF
- **Tipos disponibles**:
  - Reporte de Clientes
  - Reporte de Proyectos
  - Reporte de Ventas
  - Reporte de Inventario
- **Períodos**: Este mes, mes pasado, últimos 3/6 meses, este año, todos

#### 6. Configuración
- **Perfil de Usuario**: Actualizar información personal
- **Cambiar Contraseña**: Modificar contraseña de acceso
- **Configuraciones**: Preferencias del sistema

## Base de Datos

### Estructura de Tablas

El sistema utiliza las siguientes tablas principales:

- **usuarios**: Información de usuarios del sistema
- **clientes**: Datos de clientes
- **proyectos**: Proyectos de construcción
- **tipos_plano**: Categorías de planos
- **planos**: Archivos de planos digitales
- **materiales**: Materiales e insumos
- **inventario**: Control de stock
- **ventas**: Transacciones de venta
- **detalle_ventas**: Detalles de cada venta

### Datos Iniciales

Al ejecutar la aplicación por primera vez, se crean automáticamente:
- Usuario administrador por defecto
- Tipos de planos básicos (Arquitectónico, Estructural, Eléctrico, etc.)
- Materiales de ejemplo (Papel, Tinta, etc.)
- Inventario inicial

## Configuración Avanzada

### Variables de Entorno

Puedes configurar las siguientes variables de entorno:

```bash
# Configuración de la base de datos
export DATABASE_URL="sqlite:///asplot_database.db"

# Clave secreta para sesiones
export SECRET_KEY="tu-clave-secreta-aqui"

# Directorio de subida de archivos
export UPLOAD_FOLDER="static/uploads/planos"

# Tamaño máximo de archivo (en bytes)
export MAX_CONTENT_LENGTH=16777216  # 16MB
```

### Personalización

#### Cambiar Colores del Tema
Editar `static/css/style.css` y modificar las variables CSS:

```css
:root {
    --primary-color: #20c997;
    --secondary-color: #6c757d;
    --success-color: #28a745;
    --danger-color: #dc3545;
    --warning-color: #ffc107;
    --info-color: #17a2b8;
}
```

#### Agregar Nuevos Tipos de Archivo
Modificar `config.py`:

```python
ALLOWED_EXTENSIONS = {'pdf', 'dwg', 'dxf', 'jpg', 'jpeg', 'png', 'tiff', 'bmp'}
```

## Solución de Problemas

### Problemas Comunes

1. **Error de permisos en Windows**
   ```bash
   # Ejecutar como administrador o cambiar permisos de la carpeta
   ```

2. **Puerto 5000 ocupado**
   ```bash
   # Cambiar puerto en app.py
   app.run(debug=True, port=5001)
   ```

3. **Error de base de datos**
   ```bash
   # Eliminar archivo de base de datos para recrear
   rm asplot_database.db
   python app.py
   ```

4. **Problemas con archivos grandes**
   - Verificar configuración de `MAX_CONTENT_LENGTH`
   - Asegurar espacio suficiente en disco

### Logs y Debugging

Para habilitar logs detallados:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contribución

### Desarrollo

1. Fork del proyecto
2. Crear rama de feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit de cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crear Pull Request

### Estándares de Código

- Seguir PEP 8 para Python
- Comentarios en español
- Nombres de variables descriptivos
- Documentación de funciones complejas

## Migración de Base de Datos (Sprint 1)

El sistema soporta **MySQL 8.0** manteniendo **SQLite como respaldo**
(Patrón Strangler Fig). Scripts disponibles:

| Script | Función |
|---|---|
| `python migrate_sqlite_to_mysql.py` | Exporta esquema y datos SQLite, genera `create_mysql_schema.sql` y `datos_exportados.json` |
| `python migrate_sqlite_to_mysql.py --importar` | Lo anterior + importación directa a MySQL |
| `python importar_a_mysql.py` | Importación alternativa vía SQLAlchemy (`--vaciar` para reiniciar tablas) |
| `python validar_migracion.py` | Valida integridad: conteos, huella de datos y claves foráneas |

Para ejecutar la aplicación sobre MySQL:

```powershell
$env:MYSQL_HOST="localhost"; $env:MYSQL_USER="root"; $env:MYSQL_PASSWORD="secret"
$env:FLASK_CONFIG="mysql"
python run_dev.py
```

Sin esas variables, la aplicación arranca sobre SQLite automáticamente.
Documentación completa: [`docs/MIGRACION_MYSQL.md`](docs/MIGRACION_MYSQL.md).

## Licencia

Este proyecto está desarrollado para uso interno de la empresa de ploteo e impresión de planos.

## Soporte

Para soporte técnico o consultas sobre el sistema, contactar al equipo de desarrollo.

---

**Versión**: 1.0.0  
**Última actualización**: Octubre 2025  
**Desarrollado con**: Python Flask + SQLAlchemy + HTML5/CSS3/JavaScript





