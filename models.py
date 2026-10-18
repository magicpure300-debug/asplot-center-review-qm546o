from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Usuario(UserMixin, db.Model):
    """Modelo para la tabla Usuarios"""
    __tablename__ = 'usuarios'
    
    id_usuario = db.Column(db.Integer, primary_key=True)
    nombre_usuario = db.Column(db.String(50), unique=True, nullable=False)
    contraseña = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    # Roles: 'admin', 'cliente', 'trabajador'
    rol = db.Column(db.String(20), default='trabajador', nullable=False)
    nombre_completo = db.Column(db.String(100))
    telefono = db.Column(db.String(20))
    direccion = db.Column(db.Text)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Índices (Sprint 2 - PB-05): búsquedas por email y filtrado por rol en login/menu
    __table_args__ = (
        db.Index('ix_usuarios_rol', 'rol'),
        db.Index('ix_usuarios_activo', 'activo'),
    )
    
    # Relaciones
    planos = db.relationship('Plano', backref='usuario', lazy=True)
    facturas = db.relationship('Factura', backref='usuario', lazy=True)
    
    # Método requerido por Flask-Login para obtener el ID
    def get_id(self):
        return str(self.id_usuario)
    
    def set_password(self, password):
        """Encriptar contraseña"""
        self.contraseña = generate_password_hash(password)
    
    def check_password(self, password):
        """Verificar contraseña"""
        return check_password_hash(self.contraseña, password)
    
    @property
    def es_admin(self):
        return self.rol == 'admin'
    
    @property
    def es_trabajador(self):
        return self.rol == 'trabajador'
    
    @property
    def es_cliente(self):
        return self.rol == 'cliente'
    
    def __repr__(self):
        return f'<Usuario {self.nombre_usuario}>'

class Cliente(db.Model):
    """Modelo para la tabla Clientes"""
    __tablename__ = 'clientes'
    
    id_cliente = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    apellido = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    telefono = db.Column(db.String(20), nullable=False)
    direccion = db.Column(db.Text, nullable=False)
    
    # Vinculación opcional con usuario (para clientes que tienen cuenta)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=True)
    
    # Índices (Sprint 2 - PB-05): FK usada en JOINs y búsquedas por nombre/apellido
    __table_args__ = (
        db.Index('ix_clientes_id_usuario', 'id_usuario'),
        db.Index('ix_clientes_nombre_apellido', 'nombre', 'apellido'),
    )
    
    # Relaciones
    proyectos = db.relationship('Proyecto', backref='cliente', lazy=True)
    facturas = db.relationship('Factura', backref='cliente', lazy=True)
    
    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"
    
    def __repr__(self):
        return f'<Cliente {self.nombre_completo}>'

class Proyecto(db.Model):
    """Modelo para la tabla Proyectos - Solicitudes de servicio de clientes"""
    __tablename__ = 'proyectos'
    
    id_proyecto = db.Column(db.Integer, primary_key=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('clientes.id_cliente'), nullable=False)
    nombre_proyecto = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    
    # Tipo de servicio solicitado
    # Opciones: 'render', 'topografia', 'plano', 'correccion'
    tipo_servicio = db.Column(db.String(20), nullable=False)
    
    # Archivo que el cliente suba al solicitar el servicio
    archivo_solicitud = db.Column(db.String(255), nullable=True)
    
    # Fechas del proyecto
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_inicio = db.Column(db.Date, nullable=True)
    fecha_fin = db.Column(db.Date, nullable=True)  # Fecha límite establecida por admin
    
    # Presupuesto establecido por el administrador
    presupuesto = db.Column(db.Numeric(10, 2), nullable=True)
    
    # Estado del proyecto
    # Opciones: 'solicitado', 'cotizado', 'aprobado', 'en_progreso', 'ejecutado', 'rechazado'
    estado = db.Column(db.String(20), default='solicitado', nullable=False)
    
    # Notas adicionales del admin o cliente
    notas = db.Column(db.Text, nullable=True)
    
    # Índices (Sprint 2 - PB-05): tablero por estado, orden por fecha,
    # listado por cliente y filtros del portafolio (tipo_servicio, presupuesto)
    __table_args__ = (
        db.Index('ix_proyectos_id_cliente', 'id_cliente'),
        db.Index('ix_proyectos_estado', 'estado'),
        db.Index('ix_proyectos_fecha_solicitud', 'fecha_solicitud'),
        db.Index('ix_proyectos_tipo_servicio', 'tipo_servicio'),
        db.Index('ix_proyectos_presupuesto', 'presupuesto'),
        db.Index('ix_proyectos_estado_tipo', 'estado', 'tipo_servicio'),
    )
    
    # Relaciones
    planos = db.relationship('Plano', backref='proyecto', lazy=True)
    facturas = db.relationship('Factura', backref='proyecto', lazy=True)
    
    def __repr__(self):
        return f'<Proyecto {self.nombre_proyecto} - {self.tipo_servicio}>'

class TipoPlano(db.Model):
    """Modelo para la tabla Tipos_Plano"""
    __tablename__ = 'tipos_plano'
    
    id_tipo_plano = db.Column(db.Integer, primary_key=True)
    nombre_tipo = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text)
    
    # Relaciones
    planos = db.relationship('Plano', backref='tipo_plano', lazy=True)
    
    def __repr__(self):
        return f'<TipoPlano {self.nombre_tipo}>'

class Plano(db.Model):
    """Modelo para la tabla Planos"""
    __tablename__ = 'planos'
    
    id_plano = db.Column(db.Integer, primary_key=True)
    id_proyecto = db.Column(db.Integer, db.ForeignKey('proyectos.id_proyecto'), nullable=False)
    id_tipo_plano = db.Column(db.Integer, db.ForeignKey('tipos_plano.id_tipo_plano'), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    nombre_plano = db.Column(db.String(100), nullable=False)
    archivo = db.Column(db.String(255), nullable=False)
    fecha_subida = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Índices (Sprint 2 - PB-05): JOINs de listados y búsqueda por fechas/tipo
    __table_args__ = (
        db.Index('ix_planos_id_proyecto', 'id_proyecto'),
        db.Index('ix_planos_id_tipo_plano', 'id_tipo_plano'),
        db.Index('ix_planos_id_usuario', 'id_usuario'),
        db.Index('ix_planos_fecha_subida', 'fecha_subida'),
    )
    
    # Relaciones
    detalle_facturas = db.relationship('DetalleFactura', backref='plano', lazy=True)
    
    def __repr__(self):
        return f'<Plano {self.nombre_plano}>'

class Material(db.Model):
    """Modelo para la tabla Materiales (Insumos del negocio)"""
    __tablename__ = 'materiales'
    
    id_material = db.Column(db.Integer, primary_key=True)
    nombre_material = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    # Categorías: 'papel', 'tinta', 'herramienta', 'otro'
    categoria = db.Column(db.String(50), default='otro')
    # Subcategoría para papeles: 'A0', 'A1', 'A2', 'A3', 'A4'
    # Subcategoría para tintas: 'negro', 'color', 'cyan', 'magenta', 'amarillo'
    subcategoria = db.Column(db.String(50))
    
    # Índices (Sprint 2 - PB-05): filtros de categorías del inventario
    __table_args__ = (
        db.Index('ix_materiales_categoria', 'categoria'),
        db.Index('ix_materiales_activo', 'activo'),
    )
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    precio_compra = db.Column(db.Numeric(10, 2), default=0.0)
    unidad_medida = db.Column(db.String(20), default='unidad')
    stock_minimo = db.Column(db.Integer, default=10)
    activo = db.Column(db.Boolean, default=True)
    
    # Relaciones
    inventarios = db.relationship('Inventario', backref='material', lazy=True)
    detalle_facturas = db.relationship('DetalleFactura', backref='material', lazy=True)
    
    def __repr__(self):
        return f'<Material {self.nombre_material}>'

class Inventario(db.Model):
    """Modelo para la tabla Inventario (Gestión de Insumos)"""
    __tablename__ = 'inventario'
    
    id_inventario = db.Column(db.Integer, primary_key=True)
    id_material = db.Column(db.Integer, db.ForeignKey('materiales.id_material'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=0)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ubicacion = db.Column(db.String(100))
    
    # Índices (Sprint 2 - PB-05): JOIN con materiales en el listado de inventario
    __table_args__ = (
        db.Index('ix_inventario_id_material', 'id_material'),
    )
    
    @property
    def necesita_reposicion(self):
        """Verifica si el inventario está por debajo del stock mínimo"""
        return self.cantidad <= self.material.stock_minimo
    
    @property
    def valor_total(self):
        """Calcula el valor total del inventario"""
        return float(self.cantidad * self.material.precio_unitario)
    
    def __repr__(self):
        return f'<Inventario {self.material.nombre_material}: {self.cantidad}>'

class Factura(db.Model):
    """Modelo para la tabla Facturas - Resultado final de un proyecto aprobado"""
    __tablename__ = 'facturas'
    
    id_factura = db.Column(db.Integer, primary_key=True)
    
    # Vinculación OBLIGATORIA con un proyecto
    id_proyecto = db.Column(db.Integer, db.ForeignKey('proyectos.id_proyecto'), nullable=False)
    
    id_cliente = db.Column(db.Integer, db.ForeignKey('clientes.id_cliente'), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)  # Usuario que genera la factura
    
    fecha_factura = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_vencimiento = db.Column(db.Date, nullable=True)
    
    # Montos
    subtotal = db.Column(db.Numeric(10, 2), default=0.0)
    impuesto = db.Column(db.Numeric(10, 2), default=0.0)
    descuento = db.Column(db.Numeric(10, 2), default=0.0)
    total = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Información de pago
    estado_pago = db.Column(db.String(20), default='pendiente')  # pendiente, pagada, vencida, cancelada
    metodo_pago = db.Column(db.String(50))  # efectivo, tarjeta, transferencia, deposito
    referencia_pago = db.Column(db.String(100))  # Número de referencia/transacción
    fecha_pago = db.Column(db.DateTime, nullable=True)  # Fecha en que se realizó el pago
    
    notas = db.Column(db.Text)
    
    # Índices (Sprint 2 - PB-05): reportes financieros por fecha y estado de pago
    __table_args__ = (
        db.Index('ix_facturas_id_proyecto', 'id_proyecto'),
        db.Index('ix_facturas_id_cliente', 'id_cliente'),
        db.Index('ix_facturas_fecha_factura', 'fecha_factura'),
        db.Index('ix_facturas_estado_pago', 'estado_pago'),
    )
    
    # Relaciones
    detalles = db.relationship('DetalleFactura', backref='factura', lazy=True, cascade='all, delete-orphan')
    
    def calcular_total(self):
        """Calcula el total de la factura basado en los detalles"""
        self.subtotal = sum(detalle.subtotal for detalle in self.detalles)
        self.total = float(self.subtotal + self.impuesto - self.descuento)
        return self.total
    
    def __repr__(self):
        return f'<Factura {self.id_factura} - Proyecto {self.id_proyecto}>'

class DetalleFactura(db.Model):
    """Modelo para la tabla Detalle de Facturas"""
    __tablename__ = 'detalle_facturas'
    
    id_detalle_factura = db.Column(db.Integer, primary_key=True)
    id_factura = db.Column(db.Integer, db.ForeignKey('facturas.id_factura'), nullable=False)
    id_plano = db.Column(db.Integer, db.ForeignKey('planos.id_plano'), nullable=True)
    id_material = db.Column(db.Integer, db.ForeignKey('materiales.id_material'), nullable=True)
    descripcion = db.Column(db.String(200))
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)
    descuento = db.Column(db.Numeric(10, 2), default=0.0)
    
    # Índices (Sprint 2 - PB-05): agregaciones de factura, planos y materiales vendidos
    __table_args__ = (
        db.Index('ix_detalle_facturas_id_factura', 'id_factura'),
        db.Index('ix_detalle_facturas_id_plano', 'id_plano'),
        db.Index('ix_detalle_facturas_id_material', 'id_material'),
    )
    
    @property
    def subtotal(self):
        """Calcula el subtotal del detalle"""
        return float(self.cantidad * self.precio_unitario - self.descuento)
    
    def __repr__(self):
        return f'<DetalleFactura {self.id_detalle_factura}>'