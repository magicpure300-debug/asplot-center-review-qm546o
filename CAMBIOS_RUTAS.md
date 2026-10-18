# Guía de Cambios de Rutas en app.py

## Resumen de Cambios Necesarios

### 1. Renombrar Rutas y Funciones

#### Cambio: Ventas → Facturas
```python
# ANTES:
@app.route('/ventas')
def ventas():
    ...

@app.route('/ventas/crear', methods=['GET', 'POST'])
def crear_venta():
    ...

@app.route('/ventas/<int:id>')
def ver_venta(id):
    ...

@app.route('/ventas/<int:id>/eliminar', methods=['POST'])
def eliminar_venta(id):
    ...

@app.route('/ventas/<int:id>/imprimir')
def imprimir_venta(id):
    ...

# DESPUÉS:
@app.route('/facturas')
def facturas():
    ...

@app.route('/facturas/crear', methods=['GET', 'POST'])
def crear_factura():
    ...

@app.route('/facturas/<int:id>')
def ver_factura(id):
    ...

@app.route('/facturas/<int:id>/eliminar', methods=['POST'])
def eliminar_factura(id):
    ...

@app.route('/facturas/<int:id>/imprimir')
def imprimir_factura(id):
    ...
```

### 2. Actualizar Importaciones en app.py

```python
# ANTES:
from models import db, Usuario, Cliente, Proyecto, TipoPlano, Plano, Material, Inventario, Venta, DetalleVenta

# DESPUÉS:
from models import db, Usuario, Cliente, Proyecto, TipoPlano, Plano, Material, Inventario, Factura, DetalleFactura
```

### 3. Actualizar Referencias en Queries

Dentro de las funciones, cambiar todas las referencias:

```python
# ANTES:
ventas = Venta.query.all()
venta = Venta.query.get_or_404(id)
nueva_venta = Venta(...)
detalle = DetalleVenta(...)

# DESPUÉS:
facturas = Factura.query.all()
factura = Factura.query.get_or_404(id)
nueva_factura = Factura(...)
detalle = DetalleFactura(...)
```

### 4. Actualizar función dashboard()

La función dashboard necesita proporcionar nuevas variables:

```python
@app.route('/dashboard')
@login_required
def dashboard():
    # Estadísticas básicas
    total_clientes = Cliente.query.count()
    total_proyectos = Proyecto.query.count()  # NUEVA
    total_planos = Plano.query.count()
    total_insumos = Inventario.query.count()  # NUEVA (suma de cantidades)
    
    # Calcular total de facturas (valor monetario)
    facturas = Factura.query.all()
    total_facturas = sum(f.total for f in facturas)  # NUEVA
    
    # Proyectos recientes
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

### 5. Actualizar Lógica de Facturas

Las facturas ahora requieren un proyecto obligatorio:

```python
@app.route('/facturas/crear', methods=['GET', 'POST'])
@login_required
def crear_factura():
    if request.method == 'POST':
        # Obtener el proyecto (OBLIGATORIO)
        id_proyecto = request.form.get('id_proyecto')
        if not id_proyecto:
            flash('El proyecto es obligatorio para crear una factura', 'error')
            return redirect(url_for('crear_factura'))
        
        proyecto = Proyecto.query.get_or_404(id_proyecto)
        
        # Crear factura vinculada al proyecto
        nueva_factura = Factura(
            id_proyecto=proyecto.id_proyecto,
            id_cliente=proyecto.id_cliente,
            id_usuario=current_user.id_usuario,
            total=proyecto.presupuesto or 0,
            estado_pago='pendiente',
            metodo_pago=request.form.get('metodo_pago'),
            referencia_pago=request.form.get('referencia_pago')
        )
        
        db.session.add(nueva_factura)
        db.session.commit()
        
        flash('Factura creada exitosamente', 'success')
        return redirect(url_for('facturas'))
    
    # GET: Mostrar solo proyectos aprobados sin factura
    proyectos_disponibles = Proyecto.query.filter_by(
        estado='aprobado'
    ).filter(
        ~Proyecto.facturas.any()
    ).all()
    
    return render_template('crear_factura.html', 
                         proyectos=proyectos_disponibles)
```

### 6. Actualizar Templates Referenciados

Cambiar nombres de templates:
- `ventas.html` → `facturas.html`
- `crear_venta.html` → `crear_factura.html`
- `ver_venta.html` → `ver_factura.html`

### 7. Control de Acceso por Roles

Agregar decoradores para proteger rutas según roles:

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

# Aplicar a rutas:
@app.route('/clientes')
@login_required
@admin_or_trabajador_required  # NUEVA PROTECCIÓN
def clientes():
    ...

@app.route('/reportes')
@login_required
@admin_required  # NUEVA PROTECCIÓN
def reportes():
    ...
```

## Checklist de Cambios

- [ ] Actualizar importaciones (Venta → Factura, DetalleVenta → DetalleFactura)
- [ ] Renombrar función `ventas()` → `facturas()`
- [ ] Renombrar función `crear_venta()` → `crear_factura()`
- [ ] Renombrar función `ver_venta()` → `ver_factura()`
- [ ] Renombrar función `eliminar_venta()` → `eliminar_factura()`
- [ ] Renombrar función `imprimir_venta()` → `imprimir_factura()`
- [ ] Actualizar función `dashboard()` con nuevas variables
- [ ] Actualizar todas las queries de Venta → Factura
- [ ] Actualizar todas las queries de DetalleVenta → DetalleFactura
- [ ] Agregar `id_proyecto` obligatorio en creación de facturas
- [ ] Crear decoradores de control de acceso
- [ ] Aplicar decoradores a rutas protegidas
- [ ] Actualizar referencias en flash messages
- [ ] Actualizar todos los `url_for('ventas')` → `url_for('facturas')`
- [ ] Renombrar templates de ventas → facturas

## Notas Importantes

1. **Migración de Base de Datos**: Después de estos cambios, será necesario ejecutar migraciones para actualizar la estructura de la BD.

2. **Datos Existentes**: Si hay datos de `ventas` en la BD actual, necesitarás un script de migración para convertirlos a `facturas`.

3. **Testing**: Probar cada ruta después de los cambios para asegurar que funcionen correctamente.

4. **Roles**: Verificar que las propiedades `es_admin`, `es_trabajador`, `es_cliente` funcionen correctamente después de actualizar los roles en el modelo Usuario.
