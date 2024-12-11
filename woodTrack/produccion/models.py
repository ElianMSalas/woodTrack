from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser
from django.conf import settings
import os

# Modelo Usuario
class User(AbstractUser):
    ADMINISTRADOR = 'ADMIN'
    OPERARIO_PRODUCCION = 'PRODUCCION'
    ENCARGADO_CALIDAD = 'CALIDAD'
    OPERARIO_LOGISTICA = 'LOGISTICA'
    ENCARGADO_VENTAS = 'VENTAS' 
    SIN_ASIGNAR = 'SASIGNAR' 

    ROLE_CHOICES = [
        (ADMINISTRADOR, 'Administrador'),
        (OPERARIO_PRODUCCION, 'Operario de Producción'),
        (ENCARGADO_CALIDAD, 'Encargado de Calidad'),
        (OPERARIO_LOGISTICA, 'Operario de Logística'),
        (ENCARGADO_VENTAS, 'Encargado de Ventas'),
        (SIN_ASIGNAR, 'Sin Asignar')
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=SIN_ASIGNAR)

    def has_role(self, role):
        return self.role == role

# Modelo Inventario
class Inventario(models.Model):
    nombre_material = models.CharField(max_length=255)
    cantidad_stock = models.PositiveIntegerField()
    punto_reorden = models.PositiveIntegerField()

    def __str__(self):
        return self.nombre_material

    def clean(self):
        if self.cantidad_stock < 0:
            raise ValidationError("La cantidad en stock no puede ser negativa")
        if self.punto_reorden < 0:
            raise ValidationError("El punto de reorden no puede ser negativo")

    def restar_material(self, cantidad):
        if cantidad > self.cantidad_stock:
            raise ValidationError(
                f"No hay suficiente stock de {self.nombre_material}. "
                f"Requerido: {cantidad}, Disponible: {self.cantidad_stock}"
            )
        self.cantidad_stock -= cantidad
        self.save()

    def agregar_material(self, cantidad):
        self.cantidad_stock += cantidad
        self.save()

# Modelo Producto
class Producto(models.Model):
    nombre_producto = models.CharField(max_length=255)
    tipo_producto = models.CharField(
        max_length=50,
        choices=[('Mueble', 'Mueble'), ('Componente', 'Componente'), ('Accesorio', 'Accesorio')],
    )
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    tipo_material = models.ForeignKey(Inventario, on_delete=models.CASCADE)
    cantidad_material = models.PositiveIntegerField()
    descripcion = models.TextField(blank=True, null=True)  # Nuevo campo

    def __str__(self):
        return self.nombre_producto

    def clean(self):
        if self.precio_unitario <= 0:
            raise ValidationError("El precio unitario debe ser mayor a 0")

    def __str__(self):
        return self.nombre_producto

    def clean(self):
        if self.precio_unitario <= 0:
            raise ValidationError("El precio unitario debe ser mayor a 0")

    def verificar_disponibilidad_material(self, cantidad_deseada):
        total_material_requerido = self.cantidad_material * cantidad_deseada
        print(f"[DEBUG] Verificando disponibilidad para {self.nombre_producto}: Requerido {total_material_requerido}, Disponible {self.tipo_material.cantidad_stock}")
        return self.tipo_material.cantidad_stock >= total_material_requerido

    def actualizar_inventario(self, cantidad, agregar=False):
        if agregar:
            print(f"[DEBUG] Restaurando {cantidad} unidades de {self.tipo_material.nombre_material}. Stock inicial: {self.tipo_material.cantidad_stock}")
            self.tipo_material.agregar_material(cantidad)
        else:
            print(f"[DEBUG] Restando {cantidad} unidades de {self.tipo_material.nombre_material}. Stock inicial: {self.tipo_material.cantidad_stock}")
            self.tipo_material.restar_material(cantidad)
        print(f"[DEBUG] Stock final de {self.tipo_material.nombre_material}: {self.tipo_material.cantidad_stock}")

# Modelo Cliente
class Cliente(models.Model):
    nombre_cliente = models.CharField(max_length=255)
    direccion = models.CharField(max_length=255)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.nombre_cliente


# Modelo Pedido
class Pedido(models.Model):
    fecha_pedido = models.DateField(auto_now_add=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    estado_pedido = models.CharField(
        max_length=20,
        choices=[('Pendiente', 'Pendiente'), ('En proceso', 'En proceso'), ('Completado', 'Completado')],
        default='Pendiente',
    )
    realizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Pedido {self.id}"


class PedidoProducto(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='pedido_productos')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.pedido} - {self.producto} (Cantidad: {self.cantidad})"



# Modelo Producción
class Produccion(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    estado_produccion = models.CharField(
        max_length=20,
        choices=[('Asignado', 'Asignado'), ('En proceso', 'En proceso'), ('Completado', 'Completado')],
        default='Asignado',
    )
    fecha_inicio = models.DateField(blank=True, null=True)
    fecha_fin = models.DateField(blank=True, null=True)
    modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Producción {self.id}"

    @classmethod
    def crear_orden_produccion(cls, pedido):
        # Crear Producción
        produccion = cls.objects.create(
            pedido=pedido,
            estado_produccion='Asignado',  # Cambiado de 'estado' a 'estado_produccion'
            fecha_inicio=timezone.now()
        )

        # Crear control de calidad para cada producto en el pedido
        for pedido_producto in pedido.pedido_productos.all():
            Calidad.objects.create(
                produccion=produccion,
                resultado='Sin revisión',  # Estado inicial
            )

        # Crear registro logístico para la producción
        Logistica.objects.create(
            produccion=produccion,
            estado_entrega='Pendiente'  # Estado inicial
        )

        return produccion

# Modelo Calidad
class Calidad(models.Model):
    produccion = models.ForeignKey(Produccion, on_delete=models.CASCADE)
    resultado = models.CharField(
        max_length=20,
        choices=[('Aprobado', 'Aprobado'), ('Rechazado', 'Rechazado'), ('Sin revisión', 'Sin revisión')],
    )
    comentarios = models.TextField(blank=True, null=True)
    modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Control de Calidad {self.id}"

    def save(self, *args, **kwargs):
        # Verificar si el resultado ha cambiado a "Rechazado"
        if self.pk:  # Si ya existe, es una actualización
            old_resultado = Calidad.objects.get(pk=self.pk).resultado
            if old_resultado != 'Rechazado' and self.resultado == 'Rechazado':
                # Cambiar el estado de la producción a "En proceso"
                self.produccion.estado_produccion = 'En proceso'
                self.produccion.save()

        super().save(*args, **kwargs)


def upload_to_calidad(instance, filename):
    calidad_id = instance.calidad.id
    return f'calidad_imagenes/calidad_{calidad_id}/{filename}'

class ImagenCalidad(models.Model):
    calidad = models.ForeignKey('Calidad', related_name='imagenes', on_delete=models.CASCADE)
    imagen = models.ImageField(upload_to=upload_to_calidad)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Imagen para Calidad {self.calidad.id}"


# Modelo Logística
class Logistica(models.Model):
    produccion = models.ForeignKey(Produccion, on_delete=models.CASCADE)
    estado_entrega = models.CharField(
        max_length=20,
        choices=[('Pendiente', 'Pendiente'), ('Enviado', 'Enviado'), ('Entregado', 'Entregado')],
        default='Pendiente',
    )
    fecha_entrega = models.DateField(blank=True, null=True)
    modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Logística {self.id}"
    
    
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications", null=True, blank=True)
    role = models.CharField(max_length=50, null=True, blank=True)  # Campo para asociar roles
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message
