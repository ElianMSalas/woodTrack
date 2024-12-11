from django.core.management.base import BaseCommand
from produccion.models import Pedido, PedidoProducto, Producto, Cliente, Inventario

class Command(BaseCommand):
    help = "Elimina los datos generados por populate_db."

    def handle(self, *args, **kwargs):
        self.stdout.write("Eliminando datos generados...")

        # Borrar los modelos en orden de dependencias
        PedidoProducto.objects.all().delete()
        Pedido.objects.all().delete()
        Producto.objects.all().delete()
        Cliente.objects.all().delete()
        Inventario.objects.all().delete()

        self.stdout.write(self.style.SUCCESS("Datos eliminados correctamente."))
