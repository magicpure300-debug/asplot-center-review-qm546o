# =============================================================================
# NUEVAS RUTAS DE PROYECTOS - Reemplazar en app.py
# =============================================================================

from werkzeug.utils import secure_filename
import os
from datetime import datetime, date

# Configuración de archivos permitidos
ALLOWED_EXTENSIONS = {'pdf', 'dwg', 'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# =============================================================================
# RUTA PRINCIPAL DE PROYECTOS (Vista según rol)
# =============================================================================

@app.route('/proyectos')
@login_required
def proyectos():
    """
    Vista de proyectos que cambia según el rol del usuario:
    - Cliente: Ve solo sus propias solicitudes
    - Admin/Trabajador: Ve todas las solicitudes pendientes y puede gestionarlas
    """
    
    # Si es cliente, mostrar solo sus proyectos
    if current_user.es_cliente:
        # Buscar el cliente asociado al usuario
        # NOTA: Necesitas tener una forma de vincular usuario con cliente
        # Opción 1: Agregar campo 'id_usuario' a Cliente
        # Opción 2: Relacionar por email
        cliente = Cliente.query.filter_by(email=current_user.email).first()
        
        if cliente:
            mis_proyectos = Proyecto.query.filter_by(
                id_cliente=cliente.id_cliente
            ).order_by(Proyecto.fecha_solicitud.desc()).all()
        else:
            mis_proyectos = []
        
        return render_template('proyectos_cliente.html', 
                             proyectos=mis_proyectos)
    
    # Si es admin o trabajador, mostrar solicitudes pendientes y todas
    else:
        # Filtros opcionales
        estado_filter = request.args.get('estado', 'solicitado')
        search = request.args.get('search', '')
        
        query = Proyecto.query
        
        # Filtrar por estado (por defecto 'solicitado')
        if estado_filter and estado_filter != 'todas':
            query = query.filter_by(estado=estado_filter)
        
        # Búsqueda por nombre
        if search:
            query = query.filter(Proyecto.nombre_proyecto.contains(search))
        
        proyectos = query.order_by(Proyecto.fecha_solicitud.desc()).all()
        
        # Contar solicitudes por estado
        pendientes_count = Proyecto.query.filter_by(estado='solicitado').count()
        cotizados_count = Proyecto.query.filter_by(estado='cotizado').count()
        aprobados_count = Proyecto.query.filter_by(estado='aprobado').count()
        en_progreso_count = Proyecto.query.filter_by(estado='en_progreso').count()
        
        return render_template('proyectos_admin.html',
                             proyectos=proyectos,
                             estado_filter=estado_filter,
                             search=search,
                             pendientes_count=pendientes_count,
                             cotizados_count=cotizados_count,
                             aprobados_count=aprobados_count,
                             en_progreso_count=en_progreso_count)


# =============================================================================
# CREAR SOLICITUD DE SERVICIO (Solo Cliente)
# =============================================================================

@app.route('/proyectos/solicitar', methods=['GET', 'POST'])
@login_required
def solicitar_servicio():
    """
    Formulario para que el cliente solicite un nuevo servicio
    """
    
    # Solo clientes pueden solicitar servicios
    if not current_user.es_cliente:
        flash('Solo los clientes pueden solicitar servicios', 'error')
        return redirect(url_for('proyectos'))
    
    if request.method == 'POST':
        # Buscar el cliente asociado al usuario
        cliente = Cliente.query.filter_by(email=current_user.email).first()
        
        if not cliente:
            flash('No se encontró un perfil de cliente asociado. Contacte al administrador.', 'error')
            return redirect(url_for('dashboard'))
        
        # Obtener datos del formulario
        tipo_servicio = request.form.get('tipo_servicio')
        nombre_proyecto = request.form.get('nombre_proyecto')
        descripcion = request.form.get('descripcion')
        
        # Validaciones
        if not all([tipo_servicio, nombre_proyecto, descripcion]):
            flash('Por favor complete todos los campos obligatorios', 'error')
            return redirect(url_for('solicitar_servicio'))
        
        # Manejar archivo adjunto
        archivo_path = None
        if 'archivo_solicitud' in request.files:
            file = request.files['archivo_solicitud']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Agregar timestamp para evitar duplicados
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{timestamp}_{filename}"
                
                # Crear directorio si no existe
                upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'solicitudes')
                os.makedirs(upload_folder, exist_ok=True)
                
                filepath = os.path.join(upload_folder, filename)
                file.save(filepath)
                archivo_path = filename
        
        # Crear nuevo proyecto (solicitud)
        nuevo_proyecto = Proyecto(
            id_cliente=cliente.id_cliente,
            nombre_proyecto=nombre_proyecto,
            descripcion=descripcion,
            tipo_servicio=tipo_servicio,
            archivo_solicitud=archivo_path,
            estado='solicitado',
            fecha_solicitud=datetime.utcnow()
        )
        
        db.session.add(nuevo_proyecto)
        db.session.commit()
        
        flash(f'Solicitud de {tipo_servicio} enviada exitosamente. En breve recibirás una cotización.', 'success')
        return redirect(url_for('proyectos'))
    
    # GET: Mostrar formulario
    return render_template('solicitar_servicio.html')


# =============================================================================
# VER DETALLE DE PROYECTO (Admin/Trabajador y Cliente dueño)
# =============================================================================

@app.route('/proyectos/<int:id>')
@login_required
def detalle_proyecto(id):
    """
    Muestra el detalle de un proyecto
    """
    proyecto = Proyecto.query.get_or_404(id)
    
    # Si es cliente, verificar que sea su proyecto
    if current_user.es_cliente:
        cliente = Cliente.query.filter_by(email=current_user.email).first()
        if not cliente or proyecto.id_cliente != cliente.id_cliente:
            flash('No tienes permiso para ver este proyecto', 'error')
            return redirect(url_for('proyectos'))
    
    return render_template('detalle_proyecto.html', proyecto=proyecto)


# =============================================================================
# APROBAR/COTIZAR PROYECTO (Solo Admin/Trabajador)
# =============================================================================

@app.route('/proyectos/<int:id>/aprobar', methods=['GET', 'POST'])
@login_required
def aprobar_proyecto(id):
    """
    Permite al admin/trabajador cotizar un proyecto
    """
    
    # Solo admin y trabajador pueden aprobar
    if not (current_user.es_admin or current_user.es_trabajador):
        flash('No tienes permiso para realizar esta acción', 'error')
        return redirect(url_for('proyectos'))
    
    proyecto = Proyecto.query.get_or_404(id)
    
    if request.method == 'POST':
        presupuesto = request.form.get('presupuesto')
        fecha_estimada = request.form.get('fecha_fin')
        notas = request.form.get('notas')
        
        # Validaciones
        if not presupuesto:
            flash('El presupuesto es obligatorio', 'error')
            return redirect(url_for('aprobar_proyecto', id=id))
        
        try:
            presupuesto = float(presupuesto)
        except ValueError:
            flash('El presupuesto debe ser un número válido', 'error')
            return redirect(url_for('aprobar_proyecto', id=id))
        
        # Actualizar proyecto
        proyecto.presupuesto = presupuesto
        proyecto.estado = 'cotizado'
        proyecto.notas = notas
        
        if fecha_estimada:
            proyecto.fecha_fin = datetime.strptime(fecha_estimada, '%Y-%m-%d').date()
        
        db.session.commit()
        
        flash(f'Proyecto cotizado exitosamente. Presupuesto: ${presupuesto:.2f}', 'success')
        return redirect(url_for('proyectos'))
    
    # GET: Mostrar formulario de cotización
    # Calcular precio base según tipo de servicio
    precio_base = 0
    if proyecto.tipo_servicio in ['plano', 'correccion']:
        precio_base = 15.00
    
    return render_template('aprobar_proyecto.html', 
                         proyecto=proyecto,
                         precio_base=precio_base)


# =============================================================================
# RECHAZAR PROYECTO (Solo Admin/Trabajador)
# =============================================================================

@app.route('/proyectos/<int:id>/rechazar', methods=['POST'])
@login_required
def rechazar_proyecto(id):
    """
    Permite al admin/trabajador rechazar un proyecto
    """
    
    # Solo admin y trabajador pueden rechazar
    if not (current_user.es_admin or current_user.es_trabajador):
        flash('No tienes permiso para realizar esta acción', 'error')
        return redirect(url_for('proyectos'))
    
    proyecto = Proyecto.query.get_or_404(id)
    
    motivo = request.form.get('motivo_rechazo', '')
    
    proyecto.estado = 'rechazado'
    proyecto.notas = f"Rechazado. Motivo: {motivo}" if motivo else "Rechazado"
    
    db.session.commit()
    
    flash(f'Proyecto "{proyecto.nombre_proyecto}" rechazado', 'success')
    return redirect(url_for('proyectos'))


# =============================================================================
# MARCAR PROYECTO COMO APROBADO (Cliente acepta cotización)
# =============================================================================

@app.route('/proyectos/<int:id>/aceptar-cotizacion', methods=['POST'])
@login_required
def aceptar_cotizacion(id):
    """
    Permite al cliente aceptar la cotización y mover el proyecto a 'aprobado'
    """
    
    if not current_user.es_cliente:
        flash('Solo el cliente puede aceptar cotizaciones', 'error')
        return redirect(url_for('proyectos'))
    
    proyecto = Proyecto.query.get_or_404(id)
    
    # Verificar que es el cliente dueño
    cliente = Cliente.query.filter_by(email=current_user.email).first()
    if not cliente or proyecto.id_cliente != cliente.id_cliente:
        flash('No tienes permiso para realizar esta acción', 'error')
        return redirect(url_for('proyectos'))
    
    # Verificar que el proyecto está cotizado
    if proyecto.estado != 'cotizado':
        flash('Este proyecto no tiene una cotización pendiente', 'error')
        return redirect(url_for('proyectos'))
    
    # Cambiar estado a aprobado
    proyecto.estado = 'aprobado'
    proyecto.fecha_inicio = date.today()
    
    db.session.commit()
    
    flash(f'Cotización aceptada. El proyecto comenzará pronto.', 'success')
    return redirect(url_for('proyectos'))


# =============================================================================
# MARCAR PROYECTO EN PROGRESO (Admin/Trabajador inicia trabajo)
# =============================================================================

@app.route('/proyectos/<int:id>/iniciar', methods=['POST'])
@login_required
def iniciar_proyecto(id):
    """
    Cambia el estado del proyecto a 'en_progreso'
    """
    
    if not (current_user.es_admin or current_user.es_trabajador):
        flash('No tienes permiso para realizar esta acción', 'error')
        return redirect(url_for('proyectos'))
    
    proyecto = Proyecto.query.get_or_404(id)
    
    if proyecto.estado != 'aprobado':
        flash('Solo se pueden iniciar proyectos aprobados', 'error')
        return redirect(url_for('proyectos'))
    
    proyecto.estado = 'en_progreso'
    if not proyecto.fecha_inicio:
        proyecto.fecha_inicio = date.today()
    
    db.session.commit()
    
    flash(f'Proyecto "{proyecto.nombre_proyecto}" iniciado', 'success')
    return redirect(url_for('proyectos'))


# =============================================================================
# MARCAR PROYECTO COMO EJECUTADO (Admin/Trabajador finaliza)
# =============================================================================

@app.route('/proyectos/<int:id>/finalizar', methods=['POST'])
@login_required
def finalizar_proyecto(id):
    """
    Cambia el estado del proyecto a 'ejecutado'
    """
    
    if not (current_user.es_admin or current_user.es_trabajador):
        flash('No tienes permiso para realizar esta acción', 'error')
        return redirect(url_for('proyectos'))
    
    proyecto = Proyecto.query.get_or_404(id)
    
    if proyecto.estado != 'en_progreso':
        flash('Solo se pueden finalizar proyectos en progreso', 'error')
        return redirect(url_for('proyectos'))
    
    proyecto.estado = 'ejecutado'
    
    db.session.commit()
    
    flash(f'Proyecto "{proyecto.nombre_proyecto}" finalizado exitosamente', 'success')
    return redirect(url_for('proyectos'))
