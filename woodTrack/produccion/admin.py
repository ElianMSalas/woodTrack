from django.contrib import admin
from .models import User, Inventario, Producto, Cliente, Pedido, PedidoProducto, Produccion, Calidad, Logistica, Notification

from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    search_fields = ('username', 'email')
    ordering = ('username',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Información Personal', {'fields': ('first_name', 'last_name', 'email')}),
        ('Roles y Permisos', {'fields': ('role', 'is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
        ('Fechas Importantes', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'role', 'is_staff', 'is_active')}
        ),
    )

    def has_role(self, request, obj=None):
        return request.user.has_role('ADMIN')  # Ejemplo: permitir sólo a administradores ver esta interfaz

# Configuración para el modelo Inventario
@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = ('nombre_material', 'cantidad_stock', 'punto_reorden')
    search_fields = ('nombre_material',)
    ordering = ('nombre_material',)

# Configuración para el modelo Producto
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre_producto', 'tipo_producto', 'precio_unitario', 'tipo_material', 'cantidad_material')
    list_filter = ('tipo_producto',)
    search_fields = ('nombre_producto',)
    ordering = ('nombre_producto',)

# Configuración para el modelo Cliente
@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre_cliente', 'direccion', 'telefono', 'email')
    search_fields = ('nombre_cliente', 'email')
    ordering = ('nombre_cliente',)

# Configuración para el modelo Pedido
@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'fecha_pedido', 'estado_pedido')
    list_filter = ('estado_pedido', 'fecha_pedido')
    search_fields = ('cliente__nombre_cliente',)
    ordering = ('-fecha_pedido',)

# Configuración para el modelo PedidoProducto
@admin.register(PedidoProducto)
class PedidoProductoAdmin(admin.ModelAdmin):
    list_display = ('pedido', 'producto', 'cantidad')
    list_filter = ('producto',)
    search_fields = ('pedido__cliente__nombre_cliente', 'producto__nombre_producto')

# Configuración para el modelo Produccion
@admin.register(Produccion)
class ProduccionAdmin(admin.ModelAdmin):
    list_display = ('id', 'pedido', 'estado_produccion', 'fecha_inicio', 'fecha_fin', 'modified_by')
    list_filter = ('estado_produccion', 'fecha_inicio', 'fecha_fin')
    search_fields = ('pedido__cliente__nombre_cliente',)
    ordering = ('-fecha_inicio',)

# Configuración para el modelo Calidad
@admin.register(Calidad)
class CalidadAdmin(admin.ModelAdmin):
    list_display = ('id', 'produccion', 'resultado', 'modified_by')
    list_filter = ('resultado',)
    search_fields = ('produccion__pedido__cliente__nombre_cliente',)

# Configuración para el modelo Logistica
@admin.register(Logistica)
class LogisticaAdmin(admin.ModelAdmin):
    list_display = ('id', 'produccion', 'estado_entrega', 'fecha_entrega', 'modified_by')
    list_filter = ('estado_entrega', 'fecha_entrega')
    search_fields = ('produccion__pedido__cliente__nombre_cliente',)
    ordering = ('-fecha_entrega',)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'role', 'message', 'is_read', 'created_at')
    list_filter = ('is_read', 'role', 'created_at')
    search_fields = ('user__username', 'role', 'message')
    ordering = ('-created_at',)
    list_editable = ('is_read',)

    def get_queryset(self, request):
        """Optimización del queryset para evitar consultas adicionales."""
        queryset = super().get_queryset(request)
        return queryset.select_related('user')
