import random
from faker import Faker
from django.core.management.base import BaseCommand
from produccion.models import Cliente, Inventario, Producto, Pedido, PedidoProducto, Produccion, Calidad, Logistica, ImagenCalidad

fake = Faker('es_ES')  # Para datos en español

class Command(BaseCommand):
    help = "Genera datos de prueba masivos siguiendo la lógica: pedido > producción > calidad > logística."

    def handle(self, *args, **kwargs):
        self.stdout.write("Generando datos iniciales...")

        # Diccionarios de datos
        nombres_materiales = ['Madera', 'Metal', 'Vidrio', 'Plástico', 'Aluminio', 'Cobre']
        tipos_productos = ['Mueble', 'Componente', 'Accesorio']
        nombres_productos = ['Mesa', 'Silla', 'Lámpara', 'Estante', 'Escritorio', 'Sofá', 'Cama']

        # Crear inventarios (6 materiales)
        materiales = []
        for i in range(6):
            inventario = Inventario.objects.create(
                nombre_material=nombres_materiales[i],
                cantidad_stock=random.randint(100, 1000),
                punto_reorden=random.randint(50, 200),
            )
            materiales.append(inventario)

        self.stdout.write(f"Se generaron {len(materiales)} materiales en inventario.")

        # Crear clientes (50 datos)
        clientes = []
        for _ in range(50):
            cliente = Cliente.objects.create(
                nombre_cliente=fake.name(),
                direccion=fake.address(),
                telefono=fake.phone_number(),
                email=fake.email(),
            )
            clientes.append(cliente)

        self.stdout.write(f"Se generaron {len(clientes)} clientes.")

        # Crear productos (50 datos)
        productos = []
        for _ in range(50):
            nombre_producto = f"{random.choice(nombres_productos)} {fake.word().capitalize()}"
            tipo_producto = random.choice(tipos_productos)
            precio_unitario = random.randint(5000, 500000)  # Precios en CLP
            tipo_material = random.choice(materiales)
            cantidad_material = random.randint(1, 10)
            producto = Producto.objects.create(
                nombre_producto=nombre_producto,
                tipo_producto=tipo_producto,
                precio_unitario=precio_unitario,
                tipo_material=tipo_material,
                cantidad_material=cantidad_material,
            )
            productos.append(producto)

        self.stdout.write(f"Se generaron {len(productos)} productos.")

        # Crear pedidos (50 datos)
        pedidos = []
        for _ in range(50):
            cliente = random.choice(clientes)
            estado_pedido = random.choice(["Pendiente", "En proceso", "Completado"])
            pedido = Pedido.objects.create(
                cliente=cliente,
                estado_pedido=estado_pedido,
                realizado_por=None
            )
            pedidos.append(pedido)

            # Asociar productos a cada pedido
            num_productos = random.randint(1, 5)
            for _ in range(num_productos):
                producto = random.choice(productos)
                cantidad = random.randint(1, 10)
                total_material_necesario = producto.cantidad_material * cantidad

                # Verificar inventario antes de asociar el producto
                if producto.tipo_material.cantidad_stock >= total_material_necesario:
                    producto.tipo_material.cantidad_stock -= total_material_necesario
                    producto.tipo_material.save()

                    PedidoProducto.objects.create(
                        pedido=pedido,
                        producto=producto,
                        cantidad=cantidad,
                    )

        self.stdout.write(f"Se generaron {len(pedidos)} pedidos.")

        # Crear órdenes de producción, calidad y logística
        for pedido in pedidos:
            if pedido.estado_pedido == "Completado":
                # Producción
                estado_produccion = random.choice(["En proceso", "Completado"])
                produccion = Produccion.objects.create(
                    pedido=pedido,
                    estado_produccion=estado_produccion,
                    fecha_inicio=fake.date_this_year(),
                    fecha_fin=fake.date_this_year() if estado_produccion == "Completado" else None,
                )

                # Calidad
                if produccion.estado_produccion == "Completado":
                    resultado_calidad = random.choice(["Aprobado", "Rechazado"])
                else:
                    resultado_calidad = "Sin revisión"

                comentarios = (
                    fake.text(max_nb_chars=100) if resultado_calidad == "Rechazado" else None
                )

                calidad = Calidad.objects.create(
                    produccion=produccion,
                    resultado=resultado_calidad,
                    comentarios=comentarios
                )

                # Si la calidad está aprobada, avanza a logística
                if calidad.resultado == "Aprobado":
                    estado_logistica = random.choice(["Pendiente", "Enviado", "Entregado"])
                elif calidad.resultado == "Rechazado":
                    produccion.estado_produccion = "En proceso"
                    produccion.save()
                    estado_logistica = "Pendiente"
                else:
                    estado_logistica = "Pendiente"

                Logistica.objects.create(
                    produccion=produccion,
                    estado_entrega=estado_logistica,
                    fecha_entrega=fake.date_this_year() if estado_logistica == "Entregado" else None,
                )
            else:
                # Generar las fases con estados básicos si el pedido no está completado
                produccion = Produccion.objects.create(
                    pedido=pedido,
                    estado_produccion="Pendiente",
                )

                Calidad.objects.create(
                    produccion=produccion,
                    resultado="Sin revisión",
                )

                Logistica.objects.create(
                    produccion=produccion,
                    estado_entrega="Pendiente",
                )

        self.stdout.write(f"Se generaron órdenes de producción, calidad y logística asociadas.")

        # Crear imágenes para controles de calidad rechazados
        for calidad in Calidad.objects.filter(resultado="Rechazado"):
            for _ in range(random.randint(1, 3)):
                ImagenCalidad.objects.create(
                    calidad=calidad,
                    imagen=fake.image_url(width=800, height=600),
                    descripcion=fake.text(max_nb_chars=50)
                )

        self.stdout.write(f"Se generaron imágenes solo para controles de calidad rechazados.")

        self.stdout.write(self.style.SUCCESS("Datos generados exitosamente."))
