# ============================================================================
# RESUMEN COMPLETO DE CAMBIOS - AS PLOT CENTER
# Refactor: Panel Administrativo → Portal Cliente-Admin
# ============================================================================

## ✅ ARCHIVOS COMPLETADOS Y LISTOS

### 1. MODELOS (models.py) - ✓ ACTUALIZADO
**Ubicación:** d:\genshin\PRUEBAS\Programa Asplot\models.py

**Cambios aplicados:**
- ✓ Roles actualizados: 'admin', 'cliente', 'trabajador'
- ✓ Usuario: Propiedades es_admin, es_trabajador, es_cliente
- ✓ Cliente: Campo id_usuario agregado (vinculación opcional con Usuario)
- ✓ Proyecto: Campos nuevos (tipo_servicio, archivo_solicitud, presupuesto, estados nuevos)
- ✓ Factura: Reemplazo completo de Venta (con id_proyecto obligatorio)
- ✓ DetalleFactura: Reemplazo de DetalleVenta
- ✓ Material e Inventario: Actualizados para conceptualizar como "Insumos"

### 2. TEMPLATES CREADOS - ✓ COMPLETOS

**Templates nuevos de Proyectos:**
- ✓ templates/solicitar_servicio.html - Formulario para clientes
- ✓ templates/proyectos_cliente.html - Vista "Mis Solicitudes"
- ✓ templates/proyectos_admin.html - Vista de gestión para admin
- ✓ templates/aprobar_proyecto.html - Form de cotización
- ✓ templates/detalle_proyecto.html - Vista detallada con timeline

**Templates actualizados:**
- ✓ templates/dashboard.html - Dashboard simplificado (5 KPIs)
- ✓ templates/layout.html - Menú reorganizado con permisos

### 3. ESTILOS (style.css) - ✓ ACTUALIZADO
**Ubicación:** d:\genshin\PRUEBAS\Programa Asplot\static\css\style.css

**Cambios aplicados:**
- ✓ Tema verde unificado (.kpi-unified)
- ✓ Tipografía aumentada (h3: 1.1rem bold, números: 2.5rem bold)
- ✓ Estados de proyectos actualizados (6 nuevos estados)
- ✓ Estilos para badges de servicios
- ✓ Timeline de progreso

### 4. RUTAS DE PROYECTOS - ✓ CÓDIGO PREPARADO
**Ubicación:** d:\genshin\PRUEBAS\Programa Asplot\NUEVAS_RUTAS_PROYECTOS.py

**9 Rutas implementadas:**
1. `/proyectos` - Vista diferenciada por rol
2. `/proyectos/solicitar` - Formulario de solicitud (cliente)
3. `/proyectos/<id>` - Detalle del proyecto
4. `/proyectos/<id>/aprobar` - Cotizar proyecto (admin/trabajador)
5. `/proyectos/<id>/rechazar` - Rechazar solicitud (admin/trabajador)
6. `/proyectos/<id>/aceptar-cotizacion` - Cliente acepta cotización
7. `/proyectos/<id>/iniciar` - Iniciar trabajo (admin/trabajador)
8. `/proyectos/<id>/finalizar` - Completar proyecto (admin/trabajador)

### 5. GUÍAS DE IMPLEMENTACIÓN - ✓ CREADAS

**Documentos de referencia:**
- ✓ CAMBIOS_RUTAS.md - Guía de cambios Ventas → Facturas
- ✓ GUIA_CAMBIOS_APP.txt - Instrucciones paso a paso para app.py

## ⚠️ PASOS FINALES REQUERIDOS PARA FUNCIONAMIENTO 100%

### PASO 1: Actualizar app.py (CRÍTICO)

**1.1 Cambiar importación (línea 4):**
```python
# ANTES:
from models import db, Usuario, Cliente, Proyecto, TipoPlano, Plano, Material, Inventario, Venta, DetalleVenta

# DESPUÉS:
from models import db, Usuario, Cliente, Proyecto, TipoPlano, Plano, Material, Inventario, Factura, DetalleFactura
```

**1.2 Agregar decoradores de control de acceso (ANTES de create_app()):**
```python
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.es_admin:
            flash('Acceso denegado. Se requiere rol de Administrador.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def admin_or_trabajador_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not (current_user.es_admin or current_user.es_trabajador):
            flash('Acceso denegado.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function
```

**1.3 Configurar UPLOAD_FOLDER (después de línea 16):**
```python
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Crear directorio
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'solicitudes'), exist_ok=True)
```

**1.4 Actualizar usuario admin por defecto (línea 39):**
```python
# Cambiar:
rol='administrador',
# Por:
rol='admin',
```

**1.5 Actualizar proyecto de ejemplo (línea 71-78):**
```python
proyecto_ejemplo = Proyecto(
    id_cliente=cliente_ejemplo.id_cliente,
    nombre_proyecto='Proyecto de Prueba',
    descripcion='Proyecto de ejemplo para subir planos de prueba',
    tipo_servicio='plano',
    estado='aprobado'
)
```

**1.6 Reemplazar función dashboard() (líneas 109-136):**
```python
@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    total_clientes = Cliente.query.count()
    total_proyectos = Proyecto.query.count()
    total_planos = Plano.query.count()
    total_insumos = db.session.query(db.func.sum(Inventario.cantidad)).scalar() or 0
    total_facturas = db.session.query(db.func.sum(Factura.total)).filter(
        Factura.estado_pago != 'cancelada'
    ).scalar() or 0
    
    proyectos_recientes = Proyecto.query.order_by(
        Proyecto.fecha_solicitud.desc()
    ).limit(5).all()
    
    return render_template('dashboard.html',
                         total_clientes=total_clientes,
                         total_proyectos=total_proyectos,
                         total_planos=total_planos,
                         total_insumos=total_insumos,
                         total_facturas=total_facturas,
                         proyectos_recientes=proyectos_recientes)
```

**1.7 ELIMINAR funciones antiguas de proyectos (líneas 200-265):**
- proyectos()
- crear_proyecto()
- editar_proyecto()
- eliminar_proyecto()

**1.8 INSERTAR rutas nuevas de proyectos:**
Copiar todo el contenido de `NUEVAS_RUTAS_PROYECTOS.py` después de eliminar_cliente() (línea 198)

**1.9 RENOMBRAR todas las rutas de Ventas → Facturas:**

Buscar y reemplazar en todo el archivo:
```
/ventas → /facturas
ventas() → facturas()
crear_venta() → crear_factura()
ver_venta() → ver_factura()
eliminar_venta() → eliminar_factura()
imprimir_venta() → imprimir_factura()
Venta.query → Factura.query
DetalleVenta( → DetalleFactura(
venta = Venta( → factura = Factura(
venta. → factura.
detalle_ventas → detalles
'ventas.html' → 'facturas.html'
'crear_venta.html' → 'crear_factura.html'
'ver_venta.html' → 'ver_factura.html'
url_for('ventas') → url_for('facturas')
```

**1.10 Aplicar decoradores a rutas protegidas:**

Agregar `@admin_or_trabajador_required` en:
- clientes()
- crear_cliente()
- editar_cliente()
- eliminar_cliente()
- inventario()
- materiales()
- crear_material()
- editar_material()
- ajustar_inventario()

Agregar `@admin_required` en:
- reportes()
- generar_reporte()
- usuarios()
- crear_usuario()
- editar_usuario()
- eliminar_usuario()

**1.11 Actualizar allowed_file (línea 1079):**
```python
ALLOWED_EXTENSIONS = {'pdf', 'dwg', 'dxf', 'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
```

### PASO 2: Renombrar Templates (si existen)

```bash
# Renombrar templates de ventas a facturas:
mv templates/ventas.html templates/facturas.html
mv templates/crear_venta.html templates/crear_factura.html
mv templates/ver_venta.html templates/ver_factura.html
```

### PASO 3: Migración de Base de Datos

**OPCIÓN 1 - Desarrollo (reiniciar BD):**
```bash
# Eliminar base de datos existente
rm instance/asplot.db

# Iniciar aplicación (creará tablas nuevas)
python run_dev.py
```

**OPCIÓN 2 - Producción (migrar datos):**
```bash
# Instalar Flask-Migrate si no está instalado
pip install Flask-Migrate

# Inicializar migraciones
flask db init
flask db migrate -m "Refactor: Admin panel to client portal"
flask db upgrade
```

### PASO 4: Crear Usuarios de Prueba

**Admin:**
- Usuario: admin
- Email: admin@asplot.com
- Contraseña: admin123
- Rol: admin

**Cliente de Prueba (crear después de iniciar):**
```python
# En consola de Flask o crear ruta temporal:
cliente = Cliente(
    nombre='Cliente',
    apellido='Demo',
    email='cliente@asplot.com',
    telefono='555-1234',
    direccion='Dirección de prueba'
)

usuario_cliente = Usuario(
    nombre_usuario='cliente',
    email='cliente@asplot.com',
    rol='cliente',
    nombre_completo='Cliente Demo',
    activo=True
)
usuario_cliente.set_password('cliente123')

db.session.add(cliente)
db.session.add(usuario_cliente)
db.session.commit()

# Vincular cliente con usuario
cliente.id_usuario = usuario_cliente.id_usuario
db.session.commit()
```

## 📊 RESUMEN DE CAMBIOS POR COMPONENTE

### Modelos:
- Usuario: 3 cambios
- Cliente: +1 campo
- Proyecto: +7 campos, +6 nuevos estados
- Venta → Factura: Reemplazo completo
- DetalleVenta → DetalleFactura: Reemplazo completo

### Rutas:
- Proyectos: 9 rutas nuevas
- Ventas → Facturas: 5 rutas renombradas
- Dashboard: 1 ruta actualizada
- Total decoradores nuevos: 15 rutas protegidas

### Templates:
- Nuevos: 5 archivos
- Actualizados: 2 archivos
- Por renombrar: 3 archivos

### Estilos CSS:
- KPIs: Tema unificado verde
- Estados: 6 nuevos + 4 compatibilidad
- Tipografía: 2 aumentos de tamaño

## 🎯 FUNCIONALIDAD AL 100%

Cuando completes los pasos anteriores, tendrás:

✓ Sistema completo de roles (admin, trabajador, cliente)
✓ Clientes pueden solicitar servicios
✓ Admin cotiza y gestiona proyectos
✓ Flujo completo: Solicitado → Cotizado → Aprobado → En Progreso → Ejecutado
✓ Facturas vinculadas a proyectos
✓ Dashboard con métricas relevantes
✓ UI verde unificada y profesional
✓ Control de acceso por roles
✓ Upload de archivos para solicitudes
✓ Precio base automático para planos ($15)

## 📝 NOTAS IMPORTANTES

1. **Vinculación Usuario-Cliente**: El código busca clientes por email. Para producción, considera agregar campo id_usuario a Cliente.

2. **Archivos**: Asegúrate de que `static/uploads/solicitudes/` existe y tiene permisos de escritura.

3. **Testing**: Después de los cambios, prueba:
   - Login con diferentes roles
   - Solicitud de servicio (cliente)
   - Cotización (admin)
   - Aceptación (cliente)
   - Flujo completo del proyecto

4. **Backup**: Haz backup de tu BD actual antes de migrar.

## 🚀 COMANDO PARA INICIAR

```bash
# Aseg

urarte de que el entorno virtual está activado
.\venv\Scripts\activate

# Instalar dependencias si es necesario
pip install -r requirements.txt

# Iniciar aplicación
python run_dev.py
```

## ✅ VERIFICACIÓN FINAL

Revisa que todos estos archivos existan:
- [x] models.py (actualizado)
- [x] layout.html (menú actualizado)
- [x] dashboard.html (5 KPIs)
- [x] style.css (tema verde)
- [x] solicitar_servicio.html
- [x] proyectos_cliente.html
- [x] proyectos_admin.html
- [x] aprobar_proyecto.html
- [x] detalle_proyecto.html
- [x] NUEVAS_RUTAS_PROYECTOS.py
- [x] GUIA_CAMBIOS_APP.txt
- [x] CAMBIOS_RUTAS.md

# ============================================================================
# FIN DEL RESUMEN
# ============================================================================
