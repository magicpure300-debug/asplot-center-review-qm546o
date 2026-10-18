from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from models import db, Usuario, Cliente, Proyecto, TipoPlano, Plano, Material, Inventario, Factura, DetalleFactura
from sqlalchemy.orm import selectinload, joinedload  # Sprint 2 - PB-04 (evitar N+1)
from config import config
import os
from datetime import datetime, date
from fpdf import FPDF
from cachear import cache, cachear_ruta  # Sprint 3 - PB-06
import io
import gzip
from io import BytesIO


# =============================================================================
# Sprint 3 (PB-07) - Compresión gzip para respuestas de texto
# Middleware WSGI ligero: comprime HTML/CSS/JS/JSON/XML cuando el navegador
# lo acepta (Accept-Encoding: gzip) y el cuerpo supera el umbral mínimo.
# Reduce drásticamente el peso de plantillas y estáticos sin dependencias.
# =============================================================================
UMBRAL_GZIP = 512  # bytes mínimos para compensar la CPU de comprimir
TIPOS_TEXTO = ('text/html', 'text/css', 'application/javascript',
               'text/javascript', 'application/json', 'text/xml',
               'image/svg+xml', 'text/plain')


class CompresionGzip:
    """Middleware WSGI de compresión gzip (solo si el cliente lo soporta)."""

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        if 'gzip' not in environ.get('HTTP_ACCEPT_ENCODING', ''):
            return self.app(environ, start_response)

        fragmentos = []
        codigo = [200]
        cabeceras = []

        def inicio(status, headers, exc_info=None):
            codigo[0] = int(status.split(' ', 1)[0])
            cabeceras[:] = headers
            return fragmentos.append

        cuerpo = b''.join(self.app(environ, inicio))

        tipo = dict((k.lower(), v) for k, v in cabeceras).get('content-type', '')
        ya_comprimido = any(t in tipo for t in ('gzip', 'zip', 'pdf', 'png', 'jpeg'))
        if (codigo[0] == 200 and len(cuerpo) >= UMBRAL_GZIP
                and tipo.startswith(TIPOS_TEXTO) and not ya_comprimido):
            cuerpo = gzip.compress(cuerpo, compresslevel=6)
            cabeceras = [(k, v) for k, v in cabeceras if k.lower() != 'content-length']
            cabeceras.append(('Content-Encoding', 'gzip'))
            cabeceras.append(('Vary', 'Accept-Encoding'))

        start_response(f'{codigo[0]} OK', cabeceras)
        return [cuerpo]


def create_app():
    """Factory function para crear la aplicación Flask"""
    app = Flask(__name__)
    
    # Configuración (FLASK_CONFIG=development|production|mysql; por defecto development)
    # Con FLASK_CONFIG=mysql la app usa MySQL si MYSQL_HOST/MYSQL_USER/MYSQL_PASSWORD
    # están definidas; sin ellas sigue en SQLite (respaldo).
    app.config.from_object(config[os.environ.get('FLASK_CONFIG', 'development')])
    
    # Inicializar extensiones
    db.init_app(app)
    
    # =========================================================================
    # Sprint 3 (PB-06) - Invalidación automática de caché tras cada escritura
    # Se engancha al evento after_commit de SQLAlchemy: cualquier INSERT /
    # UPDATE / DELETE invalida las vistas cacheadas que dependen de esos
    # datos (dashboard y reportes), garantizando consistencia sin tener que
    # recordar la invalidación en cada ruta que escribe.
    # =========================================================================
    from sqlalchemy import event
    from sqlalchemy.orm import Session
    
    @event.listens_for(Session, 'after_commit')
    def _invalidar_caché_escrituras(trx):
        cache.invalidar_contiene('dashboard')
        cache.invalidar_contiene('reportes')
        cache.invalidar_contiene('portafolio')
    
    # Configurar Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
    
    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))
    
    # Crear tablas de la base de datos
    with app.app_context():
        db.create_all()
        # Crear usuario administrador por defecto
        if not Usuario.query.filter_by(email='admin@asplot.com').first():
            admin = Usuario(
                nombre_usuario='admin',
                email='admin@asplot.com',
                rol='admin',  # Rol actualizado: 'admin', 'cliente', 'trabajador'
                nombre_completo='Administrador del Sistema',
                activo=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            
            # Crear tipos de plano por defecto
            tipos_plano = [
                TipoPlano(nombre_tipo='Arquitectónico', descripcion='Planos arquitectónicos'),
                TipoPlano(nombre_tipo='Estructural', descripcion='Planos estructurales'),
                TipoPlano(nombre_tipo='Eléctrico', descripcion='Planos eléctricos'),
                TipoPlano(nombre_tipo='Plomería', descripcion='Planos de plomería'),
                TipoPlano(nombre_tipo='Mecánico', descripcion='Planos mecánicos'),
                TipoPlano(nombre_tipo='HVAC', descripcion='Planos de climatización'),
                TipoPlano(nombre_tipo='Topográfico', descripcion='Planos topográficos')
            ]
            
            for tipo in tipos_plano:
                db.session.add(tipo)
            
            # Crear cliente y proyecto de ejemplo para poder subir planos
            cliente_ejemplo = Cliente(
                nombre='Cliente',
                apellido='Ejemplo',
                email='ejemplo.sistema@asplot.com',
                telefono='555-0000',
                direccion='Dirección de ejemplo'
            )
            db.session.add(cliente_ejemplo)
            db.session.flush()
            
            proyecto_ejemplo = Proyecto(
                id_cliente=cliente_ejemplo.id_cliente,
                nombre_proyecto='Proyecto de Prueba',
                descripcion='Proyecto de ejemplo para subir planos de prueba',
                tipo_servicio='plano',  # CAMPO OBLIGATORIO
                estado='aprobado'  # Estados válidos: solicitado, cotizado, aprobado, en_progreso, ejecutado, rechazado
            )
            db.session.add(proyecto_ejemplo)
            
            db.session.commit()
    
    # Landing Page (Página de inicio pública)
    @app.route('/')
    def landing():
        return render_template('landing.html')
    
    # =========================================================================
    # Sprint 3 (PB-08) - PORTAFOLIO INTERACTIVO PÚBLICO
    # Muestra los proyectos entregados/en curso (oculta el embudo interno:
    # solicitado, cotizado, rechazado) con filtros por tipo de servicio y
    # rango de presupuesto. Usa los índices del Sprint 2:
    #   ix_proyectos_estado_tipo y ix_proyectos_tipo_servicio.
    # Ruta pública (sin login): material comercial para atraer clientes.
    # =========================================================================
    @app.route('/portafolio')
    @cachear_ruta(ttl=300)  # PB-06: 5 min; se invalida al escribir datos
    def portafolio():
        # Filtros de búsqueda
        tipo_servicio = request.args.get('tipo', '')
        presupuesto_min = request.args.get('presupuesto_min', type=float)
        presupuesto_max = request.args.get('presupuesto_max', type=float)
        
        # Estados visibles al público (el resto es flujo interno de gestión)
        estados_visibles = ('aprobado', 'en_progreso', 'ejecutado')
        
        query = Proyecto.query.options(
            selectinload(Proyecto.cliente),
            selectinload(Proyecto.planos).selectinload(Plano.tipo_plano),
        ).filter(Proyecto.estado.in_(estados_visibles))
        
        if tipo_servicio:
            query = query.filter(Proyecto.tipo_servicio == tipo_servicio)
        if presupuesto_min is not None:
            query = query.filter(Proyecto.presupuesto >= presupuesto_min)
        if presupuesto_max is not None:
            query = query.filter(Proyecto.presupuesto <= presupuesto_max)
        
        proyectos = query.order_by(Proyecto.fecha_solicitud.desc()).all()
        
        # Catálogo de tipos de servicio disponibles (para el filtro)
        tipos_disponibles = [
            valor for (valor,) in db.session.query(Proyecto.tipo_servicio)
            .filter(Proyecto.estado.in_(estados_visibles))
            .distinct().all()
        ]
        
        return render_template('portafolio.html',
                             proyectos=proyectos,
                             tipos_disponibles=tipos_disponibles,
                             tipo_servicio=tipo_servicio,
                             presupuesto_min=presupuesto_min or '',
                             presupuesto_max=presupuesto_max or '')
    
    # Rutas de autenticación
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            user = Usuario.query.filter_by(email=email).first()
            
            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for('dashboard'))
            else:
                flash('Credenciales inválidas', 'error')
        
        return render_template('login.html')
    
    @app.route('/registro', methods=['GET', 'POST'])
    def registro():
        if request.method == 'POST':
            nombre = request.form['nombre']
            apellido = request.form['apellido']
            email = request.form['email']
            telefono = request.form['telefono']
            direccion = request.form.get('direccion', '')
            password = request.form['password']
            password_confirm = request.form['password_confirm']
            
            # Validaciones
            if password != password_confirm:
                flash('Las contraseñas no coinciden', 'error')
                return redirect(url_for('registro'))
            
            if Usuario.query.filter_by(email=email).first():
                flash('Este correo ya está registrado', 'error')
                return redirect(url_for('registro'))
            
            # Crear usuario con rol cliente
            nombre_usuario = email.split('@')[0]  # Generar nombre de usuario del email
            if Usuario.query.filter_by(nombre_usuario=nombre_usuario).first():
                nombre_usuario = f"{nombre_usuario}_{Usuario.query.count()}"
            
            nuevo_usuario = Usuario(
                nombre_usuario=nombre_usuario,
                email=email,
                rol='cliente',
                nombre_completo=f"{nombre} {apellido}",
                telefono=telefono,
                direccion=direccion,
                activo=True
            )
            nuevo_usuario.set_password(password)
            db.session.add(nuevo_usuario)
            db.session.flush()
            
            # Crear registro de cliente vinculado al usuario
            nuevo_cliente = Cliente(
                nombre=nombre,
                apellido=apellido,
                email=email,
                telefono=telefono,
                direccion=direccion,
                id_usuario=nuevo_usuario.id_usuario
            )
            db.session.add(nuevo_cliente)
            db.session.commit()
            
            flash('¡Cuenta creada exitosamente! Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))
        
        return render_template('registro.html')
    
    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))
    
    # Dashboard
    @app.route('/dashboard')
    @login_required
    @cachear_ruta(ttl=60)  # Sprint 3 - PB-06: caché 60 s por usuario
    def dashboard():
        # Si es cliente, mostrar dashboard de cliente
        if current_user.es_cliente:
            # Obtener cliente vinculado al usuario
            cliente = Cliente.query.filter_by(id_usuario=current_user.id_usuario).first()
            if cliente:
                mis_proyectos = Proyecto.query.filter_by(id_cliente=cliente.id_cliente).order_by(
                    Proyecto.fecha_solicitud.desc()
                ).all()
            else:
                mis_proyectos = []
            
            return render_template('dashboard_cliente.html', mis_proyectos=mis_proyectos)
        
        # Dashboard de administrador/trabajador
        # (Sprint 2 - PB-04) Conteos consolidados en UNA sola consulta
        # (UNION ALL), en lugar de 3 consultas independientes a la BD.
        filas_conteo = db.session.query(
            db.func.count(Cliente.id_cliente)
        ).union_all(
            db.session.query(db.func.count(Proyecto.id_proyecto))
        ).union_all(
            db.session.query(db.func.count(Plano.id_plano))
        ).all()
        total_clientes, total_proyectos, total_planos = (f[0] for f in filas_conteo)
        
        # Calcular total de insumos (suma de cantidades)
        total_insumos = db.session.query(db.func.sum(Inventario.cantidad)).scalar() or 0
        
        # Calcular total de facturas (valor monetario)
        total_facturas = db.session.query(db.func.sum(Factura.total)).filter(
            Factura.estado_pago != 'cancelada'
        ).scalar() or 0
        
        # Obtener proyectos recientes (ordenados por fecha_solicitud)
        # (Sprint 2 - PB-04) selectinload evita el patrón N+1 al acceder
        # a proyecto.cliente en la plantilla (1 consulta extra en vez de 5).
        proyectos_recientes = Proyecto.query.options(
            selectinload(Proyecto.cliente)
        ).order_by(
            Proyecto.fecha_solicitud.desc()
        ).limit(5).all()
        
        return render_template('dashboard.html',
                             total_clientes=total_clientes,
                             total_proyectos=total_proyectos,
                             total_planos=total_planos,
                             total_insumos=total_insumos,
                             total_facturas=total_facturas,
                             proyectos_recientes=proyectos_recientes)
    
    # Gestión de Clientes
    @app.route('/clientes')
    @login_required
    def clientes():
        search = request.args.get('search', '')
        if search:
            clientes = Cliente.query.filter(
                db.or_(
                    Cliente.nombre.contains(search),
                    Cliente.apellido.contains(search),
                    Cliente.email.contains(search)
                )
            ).all()
        else:
            clientes = Cliente.query.all()
        
        return render_template('clientes.html', clientes=clientes, search=search)
    
    @app.route('/clientes/crear', methods=['GET', 'POST'])
    @login_required
    def crear_cliente():
        if request.method == 'POST':
            cliente = Cliente(
                nombre=request.form['nombre'],
                apellido=request.form['apellido'],
                email=request.form['email'],
                telefono=request.form['telefono'],
                direccion=request.form['direccion']
            )
            db.session.add(cliente)
            db.session.commit()
            flash('Cliente creado exitosamente', 'success')
            return redirect(url_for('clientes'))
        
        return render_template('crear_cliente.html')
    
    @app.route('/clientes/editar/<int:id>', methods=['GET', 'POST'])
    @login_required
    def editar_cliente(id):
        cliente = Cliente.query.get_or_404(id)
        
        if request.method == 'POST':
            cliente.nombre = request.form['nombre']
            cliente.apellido = request.form['apellido']
            cliente.email = request.form['email']
            cliente.telefono = request.form['telefono']
            cliente.direccion = request.form['direccion']
            db.session.commit()
            flash('Cliente actualizado exitosamente', 'success')
            return redirect(url_for('clientes'))
        
        return render_template('editar_cliente.html', cliente=cliente)
    
    @app.route('/clientes/eliminar/<int:id>')
    @login_required
    def eliminar_cliente(id):
        cliente = Cliente.query.get_or_404(id)
        db.session.delete(cliente)
        db.session.commit()
        flash('Cliente eliminado exitosamente', 'success')
        return redirect(url_for('clientes'))
    
    # Gestión de Proyectos
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
        
            # (Sprint 2 - PB-04) selectinload precarga el cliente de cada
            # proyecto: la plantilla accede a proyecto.cliente.nombre_completo
            # y sin esto se disparaba una consulta por fila (N+1).
            proyectos = query.options(
                selectinload(Proyecto.cliente)
            ).order_by(Proyecto.fecha_solicitud.desc()).all()
        
            # (Sprint 2 - PB-04) Conteos por estado en UNA sola consulta
            # con GROUP BY, en lugar de 4 consultas count() separadas.
            conteos_filas = db.session.query(
                Proyecto.estado, db.func.count(Proyecto.id_proyecto)
            ).group_by(Proyecto.estado).all()
            conteos_por_estado = dict(conteos_filas)
            pendientes_count = conteos_por_estado.get('solicitado', 0)
            cotizados_count = conteos_por_estado.get('cotizado', 0)
            aprobados_count = conteos_por_estado.get('aprobado', 0)
            en_progreso_count = conteos_por_estado.get('en_progreso', 0)
        
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
    
    # Gestión de Planos
    @app.route('/planos')
    @login_required
    def planos():
        search = request.args.get('search', '')
        tipo = request.args.get('tipo', '')
        
        query = Plano.query.join(Proyecto).join(Cliente)
        
        if search:
            query = query.filter(
                db.or_(
                    Plano.nombre_plano.contains(search),
                    Proyecto.nombre_proyecto.contains(search),
                    Cliente.nombre.contains(search)
                )
            )
        
        if tipo:
            query = query.join(TipoPlano).filter(TipoPlano.id_tipo_plano == tipo)
        
        # (Sprint 2 - PB-04) Precarga de relaciones: la plantilla accede a
        # plano.proyecto y plano.tipo_plano por fila (N+1 sin esto).
        planos = query.options(
            selectinload(Plano.proyecto),
            selectinload(Plano.tipo_plano),
        ).all()
        tipos_plano = TipoPlano.query.all()
        
        return render_template('planos.html', planos=planos, tipos_plano=tipos_plano, search=search, tipo=tipo)
    
    @app.route('/planos/subir', methods=['GET', 'POST'])
    @login_required
    def subir_plano():
        if request.method == 'POST':
            try:
                # Validar que se haya enviado un archivo
                if 'archivo' not in request.files:
                    flash('No se seleccionó ningún archivo', 'error')
                    proyectos = Proyecto.query.all()
                    tipos_plano = TipoPlano.query.all()
                    return render_template('subir_plano.html', proyectos=proyectos, tipos_plano=tipos_plano)
                
                archivo = request.files['archivo']
                if archivo.filename == '':
                    flash('No se seleccionó ningún archivo', 'error')
                    proyectos = Proyecto.query.all()
                    tipos_plano = TipoPlano.query.all()
                    return render_template('subir_plano.html', proyectos=proyectos, tipos_plano=tipos_plano)
                
                # Validar tipo de archivo
                if archivo and allowed_file(archivo.filename):
                    filename = secure_filename(archivo.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                    filename = timestamp + filename
                    
                    # Crear directorio si no existe (usar ruta absoluta)
                    upload_path = os.path.abspath(app.config['UPLOAD_FOLDER'])
                    os.makedirs(upload_path, exist_ok=True)
                    
                    # Guardar archivo
                    file_path = os.path.join(upload_path, filename)
                    archivo.save(file_path)
                    
                    # Crear registro en base de datos
                    plano = Plano(
                        id_proyecto=int(request.form['id_proyecto']),
                        id_tipo_plano=int(request.form['id_tipo_plano']),
                        id_usuario=current_user.id_usuario,
                        nombre_plano=request.form['nombre_plano'],
                        archivo=filename
                    )
                    db.session.add(plano)
                    db.session.commit()
                    
                    flash('Plano subido exitosamente', 'success')
                    return redirect(url_for('planos'))
                else:
                    flash('Tipo de archivo no permitido. Formatos válidos: PDF, DWG, DXF, JPG, PNG', 'error')
                    proyectos = Proyecto.query.all()
                    tipos_plano = TipoPlano.query.all()
                    return render_template('subir_plano.html', proyectos=proyectos, tipos_plano=tipos_plano)
                    
            except Exception as e:
                db.session.rollback()
                flash(f'Error al subir el plano: {str(e)}', 'error')
                proyectos = Proyecto.query.all()
                tipos_plano = TipoPlano.query.all()
                return render_template('subir_plano.html', proyectos=proyectos, tipos_plano=tipos_plano)
        
        proyectos = Proyecto.query.all()
        tipos_plano = TipoPlano.query.all()
        return render_template('subir_plano.html', proyectos=proyectos, tipos_plano=tipos_plano)
    
    @app.route('/planos/ver/<int:id>')
    @login_required
    def ver_plano(id):
        plano = Plano.query.get_or_404(id)
        archivo_path = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], plano.archivo))
        
        if os.path.exists(archivo_path):
            return send_file(archivo_path, as_attachment=False)
        else:
            flash('Archivo no encontrado', 'error')
            return redirect(url_for('planos'))
    
    @app.route('/planos/descargar/<int:id>')
    @login_required
    def descargar_plano(id):
        plano = Plano.query.get_or_404(id)
        archivo_path = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], plano.archivo))
        
        if os.path.exists(archivo_path):
            return send_file(archivo_path, as_attachment=True, download_name=plano.nombre_plano)
        else:
            flash('Archivo no encontrado', 'error')
            return redirect(url_for('planos'))
    
    @app.route('/planos/eliminar/<int:id>')
    @login_required
    def eliminar_plano(id):
        plano = Plano.query.get_or_404(id)
        archivo_path = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], plano.archivo))
        
        # Eliminar archivo físico
        if os.path.exists(archivo_path):
            os.remove(archivo_path)
        
        # Eliminar registro de la base de datos
        db.session.delete(plano)
        db.session.commit()
        flash('Plano eliminado exitosamente', 'success')
        return redirect(url_for('planos'))
    
    @app.route('/planos/detalle/<int:id>')
    @login_required
    def detalle_plano(id):
        plano = Plano.query.get_or_404(id)
        return render_template('detalle_plano.html', plano=plano)
    
    @app.route('/mis-planos')
    @login_required
    def mis_planos():
        # Solo para clientes - muestra planos de sus proyectos
        if not current_user.es_cliente:
            flash('Esta sección es solo para clientes', 'error')
            return redirect(url_for('dashboard'))
        
        # Obtener cliente vinculado al usuario
        cliente = Cliente.query.filter_by(id_usuario=current_user.id_usuario).first()
        if not cliente:
            planos = []
        else:
            # Obtener planos de los proyectos del cliente
            planos = Plano.query.join(Proyecto).filter(
                Proyecto.id_cliente == cliente.id_cliente
            ).order_by(Plano.fecha_subida.desc()).all()
        
        return render_template('mis_planos.html', planos=planos)
    
    @app.route('/planos/buscar')
    @login_required
    def buscar_planos():
        # Búsqueda avanzada
        nombre = request.args.get('nombre', '')
        proyecto = request.args.get('proyecto', '')
        tipo = request.args.get('tipo', '')
        fecha_desde = request.args.get('fecha_desde', '')
        fecha_hasta = request.args.get('fecha_hasta', '')
        
        query = Plano.query.join(Proyecto).join(Cliente)
        
        if nombre:
            query = query.filter(Plano.nombre_plano.contains(nombre))
        
        if proyecto:
            query = query.filter(Proyecto.nombre_proyecto.contains(proyecto))
        
        if tipo:
            query = query.join(TipoPlano).filter(TipoPlano.id_tipo_plano == tipo)
        
        if fecha_desde:
            fecha_desde_obj = datetime.strptime(fecha_desde, '%Y-%m-%d')
            query = query.filter(Plano.fecha_subida >= fecha_desde_obj)
        
        if fecha_hasta:
            fecha_hasta_obj = datetime.strptime(fecha_hasta, '%Y-%m-%d')
            query = query.filter(Plano.fecha_subida <= fecha_hasta_obj)
        
        # (Sprint 2 - PB-04) Paginación: antes se cargaba el histórico
        # completo de planos en memoria; ahora se pagina con limit/offset
        # sobre el motor de BD (aprovecha los índices ix_planos_*).
        por_pagina = 20
        total_planos = query.count()
        total_paginas = max(1, -(-total_planos // por_pagina))  # techo
        pagina = request.args.get('pagina', 1, type=int)
        pagina = max(1, min(pagina, total_paginas))
        
        planos = query.options(
            selectinload(Plano.proyecto).selectinload(Proyecto.cliente),
            selectinload(Plano.tipo_plano),
        ).limit(por_pagina).offset((pagina - 1) * por_pagina).all()
        tipos_plano = TipoPlano.query.all()
        
        return render_template('buscar_planos.html', 
                             planos=planos, 
                             tipos_plano=tipos_plano,
                             nombre=nombre,
                             proyecto=proyecto,
                             tipo=tipo,
                             fecha_desde=fecha_desde,
                             fecha_hasta=fecha_hasta,
                             pagina=pagina,
                             total_paginas=total_paginas,
                             total_planos=total_planos)
    
    # Gestión de Inventario
    @app.route('/inventario')
    @login_required
    def inventario():
        search = request.args.get('search', '')
        categoria = request.args.get('categoria', '')
        
        query = Inventario.query.join(Material)
        
        if search:
            query = query.filter(
                db.or_(
                    Material.nombre_material.contains(search),
                    Material.descripcion.contains(search)
                )
            )
        
        if categoria:
            query = query.filter(Material.categoria == categoria)
        
        # (Sprint 2 - PB-04) selectinload precarga material por fila:
        # inventario.html accede a inventario.material.* 7 veces por registro.
        inventarios = query.options(
            selectinload(Inventario.material)
        ).all()# Obtener materiales con stock bajo
        materiales_bajo_stock = Inventario.query.join(Material).filter(
            Inventario.cantidad <= Material.stock_minimo
        ).all()
        
        return render_template('inventario.html', 
                             inventarios=inventarios, 
                             materiales_bajo_stock=materiales_bajo_stock,
                             search=search,
                             categoria=categoria)
    
    @app.route('/inventario/materiales')
    @login_required
    def materiales():
        search = request.args.get('search', '')
        categoria = request.args.get('categoria', '')
        
        query = Material.query
        
        if search:
            query = query.filter(
                db.or_(
                    Material.nombre_material.contains(search),
                    Material.descripcion.contains(search)
                )
            )
        
        if categoria:
            query = query.filter(Material.categoria == categoria)
        
        materiales = query.filter(Material.activo == True).all()
        
        return render_template('materiales.html', materiales=materiales, search=search, categoria=categoria)
    
    @app.route('/inventario/materiales/crear', methods=['GET', 'POST'])
    @login_required
    def crear_material():
        if request.method == 'POST':
            material = Material(
                nombre_material=request.form['nombre_material'],
                descripcion=request.form['descripcion'],
                categoria=request.form['categoria'],
                subcategoria=request.form.get('subcategoria', ''),

                precio_unitario=0.0,
                precio_compra=0.0,
                unidad_medida=request.form['unidad_medida'],
                stock_minimo=int(request.form['stock_minimo'])
            )
            db.session.add(material)
            db.session.flush()
            
            # Crear registro de inventario inicial
            inventario = Inventario(
                id_material=material.id_material,
                cantidad=int(request.form.get('cantidad_inicial', 0)),
                ubicacion=request.form.get('ubicacion', '')
            )
            db.session.add(inventario)
            db.session.commit()
            
            flash('Material creado exitosamente', 'success')
            return redirect(url_for('materiales'))
        
        return render_template('crear_material.html')
    
    @app.route('/inventario/materiales/editar/<int:id>', methods=['GET', 'POST'])
    @login_required
    def editar_material(id):
        material = Material.query.get_or_404(id)
        
        if request.method == 'POST':
            material.nombre_material = request.form['nombre_material']
            material.descripcion = request.form['descripcion']
            material.categoria = request.form['categoria']
            material.subcategoria = request.form.get('subcategoria', '')
            material.precio_unitario = float(request.form['precio_unitario'])
            material.precio_compra = float(request.form.get('precio_compra', 0))
            material.unidad_medida = request.form['unidad_medida']
            material.stock_minimo = int(request.form['stock_minimo'])
            db.session.commit()
            
            flash('Material actualizado exitosamente', 'success')
            return redirect(url_for('materiales'))
        
        return render_template('editar_material.html', material=material)
    
    @app.route('/inventario/materiales/eliminar/<int:id>')
    @login_required
    def eliminar_material(id):
        material = Material.query.get_or_404(id)
        material.activo = False
        db.session.commit()
        flash('Material desactivado exitosamente', 'success')
        return redirect(url_for('materiales'))
    
    @app.route('/inventario/ajustar/<int:id>', methods=['GET', 'POST'])
    @login_required
    def ajustar_inventario(id):
        inventario = Inventario.query.get_or_404(id)
        
        if request.method == 'POST':
            tipo_ajuste = request.form['tipo_ajuste']
            cantidad = int(request.form['cantidad'])
            
            if tipo_ajuste == 'entrada':
                inventario.cantidad += cantidad
            elif tipo_ajuste == 'salida':
                if inventario.cantidad >= cantidad:
                    inventario.cantidad -= cantidad
                else:
                    flash('No hay suficiente stock para realizar la salida', 'error')
                    return redirect(url_for('inventario'))
            elif tipo_ajuste == 'ajuste':
                inventario.cantidad = cantidad
            
            inventario.ubicacion = request.form.get('ubicacion', inventario.ubicacion)
            inventario.fecha_actualizacion = datetime.utcnow()
            db.session.commit()
            
            flash('Inventario ajustado exitosamente', 'success')
            return redirect(url_for('inventario'))
        
        return render_template('ajustar_inventario.html', inventario=inventario)
    
    # Gestión de Facturas
    @app.route('/facturas')
    @login_required
    def facturas():
        search = request.args.get('search', '')
        estado = request.args.get('estado', '')
        
        query = Factura.query.join(Cliente)
        
        if search:
            query = query.filter(
                db.or_(
                    Cliente.nombre.contains(search),
                    Cliente.apellido.contains(search)
                )
            )
        
        if estado:
            query = query.filter(Factura.estado_pago == estado)
        
        # (Sprint 2 - PB-04) Precarga de cliente y proyecto para la plantilla
        # (facturas.html y ver_factura.html acceden a factura.cliente/proyecto).
        facturas = query.options(
            selectinload(Factura.cliente),
            selectinload(Factura.proyecto),
            selectinload(Factura.usuario),
            selectinload(Factura.detalles),
        ).order_by(Factura.fecha_factura.desc()).all()
        
        return render_template('facturas.html', facturas=facturas, search=search, estado=estado)
    
    @app.route('/facturas/crear', methods=['GET', 'POST'])
    @login_required
    def crear_factura():
        if request.method == 'POST':
            # Crear factura
            # NOTA: Se requiere id_proyecto. Por ahora, si no se envía, esto fallará.
            # Idealmente, se debe seleccionar un proyecto aprobado para facturar.
            id_proyecto = request.form.get('id_proyecto')
            
            factura = Factura(
                id_cliente=request.form['id_cliente'],
                id_proyecto=id_proyecto, # Asegurarse de enviar esto desde el formulario
                id_usuario=current_user.id_usuario,
                metodo_pago=request.form.get('metodo_pago', 'efectivo'),
                notas=request.form.get('notas', ''),
                impuesto=float(request.form.get('impuesto', 0)),
                descuento=float(request.form.get('descuento', 0)),
                total=0
            )
            db.session.add(factura)
            db.session.flush()
            
            # Procesar detalles de factura
            descripciones = request.form.getlist('descripcion[]')
            cantidades = request.form.getlist('cantidad[]')
            precios = request.form.getlist('precio[]')
            
            for i in range(len(descripciones)):
                if descripciones[i] and cantidades[i] and precios[i]:
                    cantidad = int(cantidades[i])
                    precio = float(precios[i])
                    
                    detalle = DetalleFactura(
                        id_factura=factura.id_factura,
                        id_material=None,
                        descripcion=descripciones[i],
                        cantidad=cantidad,
                        precio_unitario=precio
                    )
                    db.session.add(detalle)
            
            # Calcular total
            factura.calcular_total()
            db.session.commit()
            
            flash('Factura registrada exitosamente', 'success')
            return redirect(url_for('facturas'))
        
        clientes = Cliente.query.all()
        # Pasar proyectos aprobados para seleccionar
        proyectos = Proyecto.query.filter_by(estado='aprobado').all()
        return render_template('crear_factura.html', clientes=clientes, proyectos=proyectos)
    
    @app.route('/facturas/ver/<int:id>')
    @login_required
    def ver_factura(id):
        factura = Factura.query.get_or_404(id)
        return render_template('ver_factura.html', factura=factura)
    
    @app.route('/facturas/eliminar/<int:id>')
    @login_required
    def eliminar_factura(id):
        factura = Factura.query.get_or_404(id)
        
        # Cancelar factura
        factura.estado_pago = 'cancelada'
        db.session.commit()
        flash('Factura cancelada exitosamente', 'success')
        return redirect(url_for('facturas'))
    
    @app.route('/facturas/imprimir/<int:id>')
    @login_required
    def imprimir_factura(id):
        factura = Factura.query.get_or_404(id)
        
        # Crear PDF de factura
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        
        # Encabezado
        pdf.cell(0, 10, 'ASPLOT CENTER', 0, 1, 'C')
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 5, 'Factura de Venta', 0, 1, 'C')
        pdf.ln(5)
        
        # Información de la factura
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(40, 6, 'Factura No:', 0, 0)
        pdf.set_font('Arial', '', 10)
        pdf.cell(60, 6, f'{factura.id_factura:06d}', 0, 0)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(30, 6, 'Fecha:', 0, 0)
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 6, factura.fecha_factura.strftime('%Y-%m-%d %H:%M'), 0, 1)
        
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(40, 6, 'Cliente:', 0, 0)
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 6, factura.cliente.nombre_completo, 0, 1)
        
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(40, 6, 'Atendido por:', 0, 0)
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 6, factura.usuario.nombre_usuario, 0, 1)
        pdf.ln(5)
        
        # Tabla de detalles
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(80, 8, 'Descripcion', 1, 0, 'C')
        pdf.cell(30, 8, 'Cantidad', 1, 0, 'C')
        pdf.cell(30, 8, 'Precio Unit.', 1, 0, 'C')
        pdf.cell(30, 8, 'Subtotal', 1, 1, 'C')
        
        pdf.set_font('Arial', '', 9)
        for detalle in factura.detalles:
            pdf.cell(80, 6, detalle.descripcion[:40], 1, 0)
            pdf.cell(30, 6, str(detalle.cantidad), 1, 0, 'C')
            pdf.cell(30, 6, f'${detalle.precio_unitario:.2f}', 1, 0, 'R')
            pdf.cell(30, 6, f'${detalle.subtotal:.2f}', 1, 1, 'R')
        
        # Totales
        pdf.ln(3)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(140, 6, 'Subtotal:', 0, 0, 'R')
        pdf.cell(30, 6, f'${factura.subtotal:.2f}', 0, 1, 'R')
        
        if factura.impuesto > 0:
            pdf.cell(140, 6, 'Impuesto:', 0, 0, 'R')
            pdf.cell(30, 6, f'${factura.impuesto:.2f}', 0, 1, 'R')
        
        if factura.descuento > 0:
            pdf.cell(140, 6, 'Descuento:', 0, 0, 'R')
            pdf.cell(30, 6, f'-${factura.descuento:.2f}', 0, 1, 'R')
        
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(140, 8, 'TOTAL:', 0, 0, 'R')
        pdf.cell(30, 8, f'${factura.total:.2f}', 0, 1, 'R')
        
        # Generar respuesta
        output = io.BytesIO()
        pdf.output(output)
        output.seek(0)
        
        return send_file(
            output,
            as_attachment=True,
            download_name=f'factura_{factura.id_factura:06d}.pdf',
            mimetype='application/pdf'
        )
    
    # Gestión de Reportes
    @app.route('/reportes')
    @login_required
    @cachear_ruta(ttl=120)  # Sprint 3 - PB-06: caché 120 s por usuario
    def reportes():
        return render_template('reportes.html')
    
    @app.route('/reportes/generar', methods=['POST'])
    @login_required
    def generar_reporte():
        tipo_reporte = request.form['tipo_reporte']
        periodo = request.form['periodo']
        
        # Crear PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        
        if tipo_reporte == 'clientes':
            pdf.cell(0, 10, 'Reporte de Clientes', 0, 1, 'C')
            pdf.ln(10)
            
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(40, 10, 'Nombre', 1, 0, 'C')
            pdf.cell(60, 10, 'Email', 1, 0, 'C')
            pdf.cell(40, 10, 'Teléfono', 1, 0, 'C')
            pdf.cell(50, 10, 'Dirección', 1, 1, 'C')
            
            pdf.set_font('Arial', '', 10)
            clientes = Cliente.query.all()
            for cliente in clientes:
                pdf.cell(40, 10, cliente.nombre_completo, 1, 0)
                pdf.cell(60, 10, cliente.email, 1, 0)
                pdf.cell(40, 10, cliente.telefono, 1, 0)
                pdf.cell(50, 10, cliente.direccion[:45], 1, 1)
        
        elif tipo_reporte == 'proyectos':
            pdf.cell(0, 10, 'Reporte de Proyectos', 0, 1, 'C')
            pdf.ln(10)
            
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(50, 10, 'Proyecto', 1, 0, 'C')
            pdf.cell(40, 10, 'Cliente', 1, 0, 'C')
            pdf.cell(30, 10, 'Estado', 1, 0, 'C')
            pdf.cell(30, 10, 'Inicio', 1, 0, 'C')
            pdf.cell(30, 10, 'Fin', 1, 1, 'C')
            
            pdf.set_font('Arial', '', 10)
            proyectos = Proyecto.query.join(Cliente).all()
            for proyecto in proyectos:
                pdf.cell(50, 10, proyecto.nombre_proyecto[:25], 1, 0)
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(60, 10, 'Material', 1, 0, 'C')
            pdf.cell(40, 10, 'Categoría', 1, 0, 'C')
            pdf.cell(30, 10, 'Cantidad', 1, 0, 'C')
            pdf.cell(30, 10, 'Precio Unit.', 1, 1, 'C')
            
            pdf.set_font('Arial', '', 10)
            inventarios = Inventario.query.join(Material).filter(Material.activo == True).all()
            for inventario in inventarios:
                pdf.cell(60, 10, inventario.material.nombre_material[:30], 1, 0)
                pdf.cell(40, 10, inventario.material.categoria[:20], 1, 0)
                pdf.cell(30, 10, str(inventario.cantidad), 1, 0, 'C')
                pdf.cell(30, 10, f"${inventario.material.precio_unitario:.2f}", 1, 1, 'R')
        
        elif tipo_reporte == 'planos':
            pdf.cell(0, 10, 'Reporte de Planos', 0, 1, 'C')
            pdf.ln(10)
            
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(50, 8, 'Nombre Plano', 1, 0, 'C')
            pdf.cell(40, 8, 'Proyecto', 1, 0, 'C')
            pdf.cell(30, 8, 'Tipo', 1, 0, 'C')
            pdf.cell(35, 8, 'Cliente', 1, 0, 'C')
            pdf.cell(35, 8, 'Fecha', 1, 1, 'C')
            
            pdf.set_font('Arial', '', 8)
            planos = Plano.query.join(Proyecto).join(Cliente).join(TipoPlano).all()
            for plano in planos:
                pdf.cell(50, 6, plano.nombre_plano[:25], 1, 0)
                pdf.cell(40, 6, plano.proyecto.nombre_proyecto[:20], 1, 0)
                pdf.cell(30, 6, plano.tipo_plano.nombre_tipo[:15], 1, 0)
                pdf.cell(35, 6, plano.proyecto.cliente.nombre_completo[:18], 1, 0)
                pdf.cell(35, 6, plano.fecha_subida.strftime('%Y-%m-%d'), 1, 1, 'C')
        
        elif tipo_reporte == 'planos_proyecto':
            id_proyecto = request.form.get('id_proyecto')
            proyecto = Proyecto.query.get(id_proyecto)
            
            pdf.cell(0, 10, f'Reporte de Planos - {proyecto.nombre_proyecto}', 0, 1, 'C')
            pdf.ln(5)
            
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(40, 6, 'Cliente:', 0, 0)
            pdf.set_font('Arial', '', 10)
            pdf.cell(0, 6, proyecto.cliente.nombre_completo, 0, 1)
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(40, 6, 'Estado:', 0, 0)
            pdf.set_font('Arial', '', 10)
            pdf.cell(0, 6, proyecto.estado.title(), 0, 1)
            pdf.ln(5)
            
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(70, 8, 'Nombre Plano', 1, 0, 'C')
            pdf.cell(40, 8, 'Tipo', 1, 0, 'C')
            pdf.cell(40, 8, 'Usuario', 1, 0, 'C')
            pdf.cell(40, 8, 'Fecha Subida', 1, 1, 'C')
            
            pdf.set_font('Arial', '', 9)
            planos = Plano.query.filter_by(id_proyecto=id_proyecto).all()
            for plano in planos:
                pdf.cell(70, 6, plano.nombre_plano[:35], 1, 0)
                pdf.cell(40, 6, plano.tipo_plano.nombre_tipo, 1, 0)
                pdf.cell(40, 6, plano.usuario.nombre_usuario, 1, 0)
                pdf.cell(40, 6, plano.fecha_subida.strftime('%Y-%m-%d'), 1, 1, 'C')
            
            pdf.ln(5)
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(0, 6, f'Total de planos: {len(planos)}', 0, 1)
        
        elif tipo_reporte == 'stock_bajo':
            pdf.cell(0, 10, 'Reporte de Stock Bajo', 0, 1, 'C')
            pdf.ln(10)
            
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(60, 8, 'Material', 1, 0, 'C')
            pdf.cell(30, 8, 'Cantidad', 1, 0, 'C')
            pdf.cell(30, 8, 'Stock Min.', 1, 0, 'C')
            pdf.cell(40, 8, 'Ubicación', 1, 1, 'C')
            
            pdf.set_font('Arial', '', 9)
            inventarios = Inventario.query.join(Material).filter(
                Material.activo == True,
                Inventario.cantidad <= Material.stock_minimo
            ).all()
            
            for inventario in inventarios:
                pdf.cell(60, 6, inventario.material.nombre_material[:30], 1, 0)
                pdf.cell(30, 6, str(inventario.cantidad), 1, 0, 'C')
                pdf.cell(30, 6, str(inventario.material.stock_minimo), 1, 0, 'C')
                pdf.cell(40, 6, (inventario.ubicacion or 'N/A')[:20], 1, 1)
        
        # Generar respuesta
        output = io.BytesIO()
        pdf.output(output)
        output.seek(0)
        
        return send_file(
            output,
            as_attachment=True,
            download_name=f'reporte_{tipo_reporte}_{datetime.now().strftime("%Y%m%d")}.pdf',
            mimetype='application/pdf'
        )
    
    # Gestión de Usuarios
    @app.route('/usuarios')
    @login_required
    def usuarios():
        if not current_user.es_admin:
            flash('No tienes permisos para acceder a esta sección', 'error')
            return redirect(url_for('dashboard'))
        
        search = request.args.get('search', '')
        rol = request.args.get('rol', '')
        
        query = Usuario.query.filter(Usuario.activo == True)
        
        if search:
            query = query.filter(
                db.or_(
                    Usuario.nombre_usuario.contains(search),
                    Usuario.email.contains(search),
                    Usuario.nombre_completo.contains(search)
                )
            )
        
        if rol:
            query = query.filter(Usuario.rol == rol)
        
        usuarios = query.all()
        
        return render_template('usuarios.html', usuarios=usuarios, search=search, rol=rol)
    
    @app.route('/usuarios/crear', methods=['GET', 'POST'])
    @login_required
    def crear_usuario():
        if not current_user.es_admin:
            flash('No tienes permisos para acceder a esta sección', 'error')
            return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            # Verificar si el usuario ya existe
            if Usuario.query.filter_by(email=request.form['email']).first():
                flash('El email ya está registrado', 'error')
                return redirect(url_for('crear_usuario'))
            
            if Usuario.query.filter_by(nombre_usuario=request.form['nombre_usuario']).first():
                flash('El nombre de usuario ya está en uso', 'error')
                return redirect(url_for('crear_usuario'))
            
            usuario = Usuario(
                nombre_usuario=request.form['nombre_usuario'],
                email=request.form['email'],
                rol=request.form['rol'],
                nombre_completo=request.form.get('nombre_completo', ''),
                telefono=request.form.get('telefono', ''),
                direccion=request.form.get('direccion', ''),
                activo=True
            )
            usuario.set_password(request.form['password'])
            db.session.add(usuario)
            db.session.commit()
            
            flash('Usuario creado exitosamente', 'success')
            return redirect(url_for('usuarios'))
        
        return render_template('crear_usuario.html')
    
    @app.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
    @login_required
    def editar_usuario(id):
        if not current_user.es_admin:
            flash('No tienes permisos para acceder a esta sección', 'error')
            return redirect(url_for('dashboard'))
        
        usuario = Usuario.query.get_or_404(id)
        
        if request.method == 'POST':
            # Verificar email único
            email_existente = Usuario.query.filter(
                Usuario.email == request.form['email'],
                Usuario.id_usuario != id
            ).first()
            if email_existente:
                flash('El email ya está registrado', 'error')
                return redirect(url_for('editar_usuario', id=id))
            
            usuario.nombre_usuario = request.form['nombre_usuario']
            usuario.email = request.form['email']
            usuario.rol = request.form['rol']
            usuario.nombre_completo = request.form.get('nombre_completo', '')
            usuario.telefono = request.form.get('telefono', '')
            usuario.direccion = request.form.get('direccion', '')
            
            if request.form.get('password'):
                usuario.set_password(request.form['password'])
            
            db.session.commit()
            flash('Usuario actualizado exitosamente', 'success')
            return redirect(url_for('usuarios'))
        
        return render_template('editar_usuario.html', usuario=usuario)
    
    @app.route('/usuarios/eliminar/<int:id>')
    @login_required
    def eliminar_usuario(id):
        if not current_user.es_administrador:
            flash('No tienes permisos para acceder a esta sección', 'error')
            return redirect(url_for('dashboard'))
        
        if id == current_user.id_usuario:
            flash('No puedes eliminar tu propio usuario', 'error')
            return redirect(url_for('usuarios'))
        
        usuario = Usuario.query.get_or_404(id)
        usuario.activo = False
        db.session.commit()
        flash('Usuario desactivado exitosamente', 'success')
        return redirect(url_for('usuarios'))
    
    # Configuración
    @app.route('/configuracion')
    @login_required
    def configuracion():
        return render_template('configuracion.html', usuario=current_user)
    
    @app.route('/configuracion/actualizar', methods=['POST'])
    @login_required
    def actualizar_configuracion():
        usuario = current_user
        usuario.nombre_usuario = request.form['nombre_usuario']
        usuario.email = request.form['email']
        usuario.nombre_completo = request.form.get('nombre_completo', '')
        usuario.telefono = request.form.get('telefono', '')
        usuario.direccion = request.form.get('direccion', '')
        
        if request.form.get('password'):
            usuario.set_password(request.form['password'])
        
        db.session.commit()
        flash('Configuración actualizada exitosamente', 'success')
        return redirect(url_for('configuracion'))
    
    # Funciones auxiliares
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    
    # =========================================================================
    # Sprint 3 (PB-07) - Cabeceras HTTP de caché para archivos estáticos
    # Los CSS/JS/imágenes tienen nombre estable: se cachean 7 días en el
    # navegador. Los HTML siempre se revalidan (son dinámicos).
    # =========================================================================
    @app.after_request
    def cabeceras_caché(respuesta):
        if request.path.startswith('/static/'):
            # 7 días = 604800 s; los planos subidos NO se cachean (son datos vivos)
            if '/uploads/' not in request.path:
                respuesta.headers['Cache-Control'] = 'public, max-age=604800'
            else:
                respuesta.headers['Cache-Control'] = 'no-cache'
        elif request.path.endswith(('.html', '/')) or request.path == '':
            respuesta.headers['Cache-Control'] = 'no-cache'
        return respuesta
    
    # Compresión gzip de respuestas de texto (PB-07)
    # Se envuelve la capa WSGI interna (no el objeto Flask) para conservar
    # la API de Flask: app.run(), app.test_client(), etc.
    app.wsgi_app = CompresionGzip(app.wsgi_app)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)

