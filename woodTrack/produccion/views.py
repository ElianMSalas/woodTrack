from django import forms
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView, ListView, DetailView
from django.forms import ModelForm, inlineformset_factory, modelformset_factory
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.utils import timezone
from .models import User, Cliente, Pedido, Inventario, Producto, PedidoProducto, Produccion, Calidad, Logistica, ImagenCalidad, Notification
from .mixins import VentasRequiredMixin, AdminRequiredMixin, ProduccionRequiredMixin, CalidadRequiredMixin, LogisticaRequiredMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import ClienteForm, PedidoProductoForm, PedidoForm, InventarioForm, CalidadForm, GestionLogisticaForm, ImagenCalidadForm
from django.http import HttpResponse
from django.db.models import Count, Sum, F
from django.utils.dateparse import parse_date
from django.core.paginator import Paginator
from django.http import JsonResponse


class GestionInventarioView(TemplateView):
    template_name = 'produccion/gestionar_inventario.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['inventarios'] = Inventario.objects.all()

        # Eliminar las notificaciones anteriores para evitar duplicados
        Notification.objects.filter(role="gestor de ventas").delete()

        # Generar notificaciones según el estado del stock
        for item in context['inventarios']:
            if item.cantidad_stock < item.punto_reorden:
                # Notificación crítica para "Gestor de Ventas"
                Notification.objects.create(
                    role="gestor de ventas",
                    message=f'El material "{item.nombre_material}" necesita reabastecimiento inmediato (Stock: {item.cantidad_stock}).',
                )

        return context


    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        material_id = request.POST.get('material_id')
        item = get_object_or_404(Inventario, pk=material_id)

        # Acción: Editar material
        if action == 'edit':
            form = InventarioForm(request.POST, instance=item)
            if form.is_valid():
                form.save()
                # Notificación de éxito
                Notification.objects.create(
                    role="gestor de ventas",
                    message=f'El material "{item.nombre_material}" se actualizó correctamente.'
                )
            else:
                Notification.objects.create(
                    role="gestor de ventas",
                    message=f'Error al actualizar el material "{item.nombre_material}".'
                )

        # Acción: Reabastecer material
        elif action == 'reabastecer':
            try:
                cantidad = int(request.POST.get('cantidad', 0))
                if cantidad > 0:
                    item.cantidad_stock += cantidad
                    item.save()
                    Notification.objects.create(
                        role="gestor de ventas",
                        message=f'Se añadieron {cantidad} unidades al material "{item.nombre_material}".'
                    )
                else:
                    Notification.objects.create(
                        role="gestor de ventas",
                        message="La cantidad de reabastecimiento debe ser mayor a 0."
                    )
            except ValueError:
                Notification.objects.create(
                    role="gestor de ventas",
                    message="Por favor, ingresa una cantidad válida."
                )

        # Acción: Eliminar material
        elif action == 'delete':
            item.delete()
            Notification.objects.create(
                role="gestor de ventas",
                message=f'El material "{item.nombre_material}" fue eliminado correctamente.'
            )

        return redirect('produccion:gestionar_inventario')


class GestionUsuariosView(AdminRequiredMixin, TemplateView):
    template_name = 'produccion/gestion_usuarios.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['users'] = User.objects.all()
        return context

    def post(self, request, *args, **kwargs):
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        user = get_object_or_404(User, id=user_id)

        if action == 'delete':  # Eliminar usuario
            user.delete()
            # Crear notificación para el administrador
            Notification.objects.create(
                role="ADMIN",
                message=f"El usuario {user.username} ha sido eliminado correctamente.",
            )
            messages.success(request, "Usuario eliminado correctamente.")

        elif action == 'update_role':  # Actualizar rol del usuario
            role = request.POST.get('role')
            if role in [choice[0] for choice in User.ROLE_CHOICES]:
                user.role = role
                user.save()
                # Crear notificación para el administrador
                Notification.objects.create(
                    role="ADMIN",
                    message=f"El rol del usuario {user.username} ha sido actualizado a {role}.",
                )
                messages.success(request, f"Rol del usuario {user.username} actualizado a {role}.")
            else:
                messages.error(request, "Rol inválido.")
                # Crear notificación de error
                Notification.objects.create(
                    role="ADMIN",
                    message=f"Intento fallido de actualizar el rol del usuario {user.username}. Rol inválido.",
                )

        return redirect('produccion:gestion_usuarios')


class UserProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'produccion/profile.html'

    def post(self, request, *args, **kwargs):
        user = request.user

        # Actualizar datos básicos
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)

        # Permitir actualización de rol solo para administradores
        if user.is_superuser or user.role == User.ADMINISTRADOR:
            role = request.POST.get('role')
            if role in [choice[0] for choice in User.ROLE_CHOICES]:
                user.role = role
            else:
                messages.error(request, "Rol inválido.")

        user.save()
        messages.success(request, "Perfil actualizado correctamente.")
        return redirect('produccion:profile')

class CrearPedidoView(VentasRequiredMixin, View):
    template_name = 'produccion/crear_pedido.html'

    def get(self, request):
        cliente_form = ClienteForm()
        pedido_producto_formset = inlineformset_factory(
            Pedido, PedidoProducto, form=PedidoProductoForm, extra=1, can_delete=False
        )
        formset = pedido_producto_formset()
        return render(request, self.template_name, {'cliente_form': cliente_form, 'formset': formset})

    def post(self, request):
        cliente_form = ClienteForm(request.POST)
        pedido_producto_formset = inlineformset_factory(
            Pedido, PedidoProducto, form=PedidoProductoForm
        )
        formset = pedido_producto_formset(request.POST)

        if cliente_form.is_valid() and formset.is_valid():
            # Crear cliente y pedido
            cliente = cliente_form.save()
            pedido = Pedido.objects.create(cliente=cliente, realizado_por=request.user)
            inventario_insuficiente = []

            # Procesar cada producto en el formset
            for form in formset:
                if form.cleaned_data:
                    producto = form.cleaned_data['producto']
                    cantidad = form.cleaned_data['cantidad']

                    # Registrar en PedidoProducto
                    PedidoProducto.objects.create(
                        pedido=pedido,
                        producto=producto,
                        cantidad=cantidad
                    )

                    # Verificar inventario y actualizar stock si es posible
                    total_material_necesario = producto.cantidad_material * cantidad
                    if producto.tipo_material.cantidad_stock >= total_material_necesario:
                        producto.tipo_material.cantidad_stock -= total_material_necesario
                        producto.tipo_material.save()
                    else:
                        inventario_insuficiente.append(producto.nombre_producto)

            # Actualizar estado del pedido
            pedido.estado_pedido = "Pendiente" if inventario_insuficiente else "En proceso"
            pedido.save()

            # Crear registros en Producción, Calidad y Logística
            self.crear_registros_asociados(pedido, inventario_insuficiente)

            # Crear notificaciones
            self.crear_notificaciones(pedido, inventario_insuficiente)

            # Mensajes al usuario
            if inventario_insuficiente:
                mensaje_error = (
                    "Algunos productos tienen inventario insuficiente:\n" +
                    "\n".join(inventario_insuficiente)
                )
                messages.warning(request, mensaje_error)
            else:
                messages.success(request, "Pedido procesado exitosamente.")

            return redirect('produccion:lista_pedidos')

        # Si hay errores en los formularios
        return render(request, self.template_name, {'cliente_form': cliente_form, 'formset': formset})

    def crear_registros_asociados(self, pedido, inventario_insuficiente):
        estado_inicial = "Pendiente" if inventario_insuficiente else "En proceso"
        resultado = "Sin revisión" if inventario_insuficiente else "Sin revisión"
        estado_entrega = "Pendiente"

        # Crear instancia de Producción
        produccion_instancia = Produccion.objects.create(
            pedido=pedido,
            estado_produccion=estado_inicial
        )

        # Crear instancia de Calidad y asociarla con Producción
        Calidad.objects.create(
            produccion=produccion_instancia,
            resultado=resultado
        )

        # Crear instancia de Logística y asociarla con el pedido
        Logistica.objects.create(
            produccion=produccion_instancia,
            estado_entrega=estado_entrega
        )

    def crear_notificaciones(self, pedido, inventario_insuficiente):
        """Crea notificaciones específicas para el gestor de ventas."""
        if inventario_insuficiente:
            # Notificación de inventario insuficiente
            Notification.objects.create(
                role="gestor de ventas",
                message=(
                    f"El pedido #{pedido.id} contiene productos con inventario insuficiente: "
                    f"{', '.join(inventario_insuficiente)}."
                ),
            )
        else:
            # Notificación de éxito
            Notification.objects.create(
                role="gestor de ventas",
                message=f"El pedido #{pedido.id} fue procesado exitosamente.",
            )

class PedidoEstadoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ['estado_pedido']
        widgets = {
            'estado_pedido': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'estado_pedido': 'Estado del Pedido',
        }

class EditarPedidoView(View):
    template_name = 'produccion/editar_pedido.html'
    formset_class = None

    def dispatch(self, request, *args, **kwargs):
        self.pedido = get_object_or_404(Pedido, id=kwargs['pedido_id'])
        self.formset_class = modelformset_factory(
            PedidoProducto,
            form=PedidoProductoForm,
            extra=0,
            can_delete=True
        )
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        formset = self.formset_class(queryset=self.pedido.pedido_productos.all())
        estado_form = PedidoEstadoForm(instance=self.pedido)
        return self.render_to_response({
            'pedido': self.pedido,
            'formset': formset,
            'estado_form': estado_form,
        })

    def post(self, request, *args, **kwargs):
        estado_form = PedidoEstadoForm(request.POST, instance=self.pedido)
        formset = self.formset_class(
            request.POST,
            queryset=self.pedido.pedido_productos.all()
        )
        restar_material = 'restar_material' in request.POST  # Checkbox para decidir si ajustar inventario

        if formset.is_valid() and estado_form.is_valid():
            try:
                # Procesar el formset y asignar el pedido
                self.procesar_formset(formset, restar_material)
                estado_form.save()  # Guardar el nuevo estado del pedido

                # Crear notificación de éxito
                self.crear_notificacion(
                    f"El pedido #{self.pedido.id} fue actualizado correctamente.",
                    "success"
                )

                messages.success(request, "Pedido actualizado correctamente.")
                return redirect('produccion:detalle_pedido', pk=self.pedido.id)
            except ValidationError as e:
                messages.error(request, f"Error al actualizar el pedido: {str(e)}")
                self.crear_notificacion(
                    f"Error al actualizar el pedido #{self.pedido.id}: {str(e)}.",
                    "error"
                )
        else:
            messages.error(request, "Corrige los errores del formulario.")
            self.crear_notificacion(
                f"El pedido #{self.pedido.id} no pudo ser actualizado debido a errores en el formulario.",
                "warning"
            )

        return self.render_to_response({
            'pedido': self.pedido,
            'formset': formset,
            'estado_form': estado_form,
        })

    def procesar_formset(self, formset, restar_material):
        productos_procesados = set()  # Para evitar procesar el mismo producto más de una vez
        cambios_realizados = []

        for form in formset:
            if form.cleaned_data.get('DELETE'):
                # Restaurar inventario si se elimina un producto y restar_material está activo
                if restar_material:
                    producto = form.instance.producto
                    cantidad_a_reponer = form.instance.cantidad * producto.cantidad_material
                    producto.actualizar_inventario(cantidad_a_reponer, agregar=True)
                cambios_realizados.append(f"Producto eliminado: {form.instance.producto.nombre_producto}")
                form.instance.delete()
            else:
                # Asignar el pedido al formulario antes de guardarlo
                instancia = form.save(commit=False)
                instancia.pedido = self.pedido  # Asegurar que el pedido está asignado
                producto = instancia.producto
                cantidad_nueva = form.cleaned_data['cantidad']

                # Evitar procesar el mismo producto más de una vez
                if producto.id in productos_procesados:
                    continue

                if restar_material:
                    # Validar disponibilidad de material SOLO si `restar_material` está marcado
                    total_material_requerido = cantidad_nueva * producto.cantidad_material

                    if not producto.verificar_disponibilidad_material(cantidad_nueva):
                        # Mostrar advertencia si no hay suficiente material
                        messages.warning(
                            self.request,
                            f"No hay suficiente material para {producto.nombre_producto}. "
                            f"Disponible: {producto.tipo_material.cantidad_stock}, "
                            f"Requerido: {total_material_requerido}. El cambio se aplicará sin ajustar inventario."
                        )
                        cambios_realizados.append(f"Inventario insuficiente para: {producto.nombre_producto}")
                    else:
                        # Ajustar inventario si hay suficiente material
                        producto.actualizar_inventario(total_material_requerido, agregar=False)

                # Guardar la instancia del pedido actualizada
                instancia.save()
                cambios_realizados.append(f"Producto actualizado: {producto.nombre_producto}, cantidad: {cantidad_nueva}")

                # Marcar el producto como procesado
                productos_procesados.add(producto.id)


    def crear_notificacion(self, mensaje, tipo):
        Notification.objects.create(
            role="gestor de ventas",
            message=mensaje,
        )

    def render_to_response(self, context):
        return render(self.request, self.template_name, context)

class ListaPedidosView(LoginRequiredMixin, ListView):
    template_name = 'produccion/lista_pedidos.html'
    context_object_name = 'items'
    paginate_by = 10  # Número de elementos por página

    def get_queryset(self):
        user_role = self.request.user.role

        if user_role in [User.ENCARGADO_VENTAS, User.ADMINISTRADOR]:
            # Ventas y Administradores ven todos los pedidos
            return Pedido.objects.all().order_by('-fecha_pedido')
        else:
            # Otros roles no tienen acceso
            return Pedido.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Paginación
        paginator = Paginator(self.get_queryset(), self.paginate_by)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # Contexto adicional
        context['page_obj'] = page_obj
        context['is_paginated'] = page_obj.has_other_pages()
        return context

class GestionProduccionView(View):
    template_name = 'produccion/gestion_produccion.html'

    def get(self, request, pk):
        # Obtener la producción relacionada
        produccion = get_object_or_404(Produccion, pk=pk)
        
        # Obtener las imágenes asociadas al control de calidad, si existe
        calidad = Calidad.objects.filter(produccion=produccion).first()
        imagenes_calidad = calidad.imagenes.all() if calidad else []

        # Obtener productos relacionados al pedido
        productos = produccion.pedido.pedido_productos.select_related('producto')

        context = {
            'produccion': produccion,
            'imagenes_calidad': imagenes_calidad,
            'productos': productos,  # Agregamos los productos al contexto
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        # Obtener la producción relacionada
        produccion = get_object_or_404(Produccion, pk=pk)

        # Obtener los datos del formulario
        estado_produccion = request.POST.get('estado_produccion')
        fecha_inicio = request.POST.get('fecha_inicio')
        fecha_fin = request.POST.get('fecha_fin')

        try:
            # Actualizar los datos de producción
            produccion.estado_produccion = estado_produccion
            produccion.fecha_inicio = fecha_inicio if fecha_inicio else produccion.fecha_inicio
            produccion.fecha_fin = fecha_fin if fecha_fin else produccion.fecha_fin
            produccion.modified_by = request.user  # Registrar el usuario que realizó el cambio
            produccion.save()

            # Verificar si el estado de calidad es "Rechazado" y cambiar a "En revisión"
            calidad = Calidad.objects.filter(produccion=produccion).first()
            if calidad and calidad.resultado == "Rechazado":
                calidad.resultado = "Sin revisión"
                calidad.save()

            # Crear notificación de éxito
            self.crear_notificacion(
                f"La producción del pedido #{produccion.pedido.id} fue actualizada correctamente.",
                "success"
            )

            messages.success(request, "Producción y estado de calidad actualizados correctamente.")
        except Exception as e:
            messages.error(request, f"Hubo un error al actualizar la producción: {str(e)}")
            # Crear notificación de error
            self.crear_notificacion(
                f"Error al actualizar la producción del pedido #{produccion.pedido.id}: {str(e)}.",
                "error"
            )

        return redirect('produccion:gestion_produccion', pk=produccion.id)

    def crear_notificacion(self, mensaje, tipo):
        Notification.objects.create(
            role="gestor de produccion",
            message=mensaje,
        )


class GestionLogisticaView(LogisticaRequiredMixin, View):
    template_name = 'produccion/gestion_logistica.html'
    success_url = reverse_lazy('produccion:lista_pedidos')

    def get(self, request, pk):
        produccion = get_object_or_404(Produccion, pk=pk)
        logistica, created = Logistica.objects.get_or_create(produccion=produccion)
        form = GestionLogisticaForm(instance=logistica)
        return render(request, self.template_name, {'produccion': produccion, 'form': form})

    def post(self, request, pk):
        produccion = get_object_or_404(Produccion, pk=pk)
        logistica = get_object_or_404(Logistica, produccion=produccion)

        form = GestionLogisticaForm(request.POST, instance=logistica)

        if form.is_valid():
            logistica = form.save(commit=False)
            logistica.modified_by = request.user

            # Actualizar fecha de entrega si el estado es "Entregado"
            if logistica.estado_entrega == 'Entregado' and not logistica.fecha_entrega:
                logistica.fecha_entrega = timezone.now()

            logistica.save()

            # Crear notificación de éxito
            self.crear_notificacion(
                f"El estado logístico del pedido #{produccion.pedido.id} ha sido actualizado a '{logistica.estado_entrega}'.",
                "success"
            )

            messages.success(request, 'Estado de logística actualizado correctamente.')
            return redirect('produccion:dashboard_logistica')
        else:
            # Crear notificación de error
            self.crear_notificacion(
                f"Error al actualizar el estado logístico del pedido #{produccion.pedido.id}.",
                "error"
            )

        return render(request, self.template_name, {'produccion': produccion, 'form': form})

    def crear_notificacion(self, mensaje, tipo):
        Notification.objects.create(
            role="gestor de logistica",
            message=mensaje,
        )
    
class GestionCalidadView(CalidadRequiredMixin, View):
    template_name = 'produccion/gestion_calidad.html'

    def get(self, request, pk):
        calidad = get_object_or_404(Calidad, pk=pk)
        calidad_form = CalidadForm(instance=calidad)
        imagen_formset = modelformset_factory(ImagenCalidad, form=ImagenCalidadForm, extra=1, can_delete=True)
        formset = imagen_formset(queryset=calidad.imagenes.all())

        return render(request, self.template_name, {
            'calidad': calidad,
            'calidad_form': calidad_form,
            'formset': formset,
        })

    def post(self, request, pk):
        calidad = get_object_or_404(Calidad, pk=pk)
        calidad_form = CalidadForm(request.POST, instance=calidad)
        imagen_formset = modelformset_factory(ImagenCalidad, form=ImagenCalidadForm, extra=1, can_delete=True)
        formset = imagen_formset(request.POST, request.FILES, queryset=calidad.imagenes.all())

        if calidad_form.is_valid() and formset.is_valid():
            try:
                # Actualizar el registro de calidad
                calidad = calidad_form.save(commit=False)
                calidad.modified_by = request.user  # Asigna el usuario actual al campo modified_by
                calidad.save()

                # Guardar las imágenes relacionadas
                instances = formset.save(commit=False)
                for instance in instances:
                    instance.calidad = calidad
                    instance.save()
                for obj in formset.deleted_objects:
                    obj.delete()

                # Crear notificación de éxito
                self.crear_notificacion(
                    f"La revisión de calidad del pedido #{calidad.produccion.pedido.id} fue actualizada correctamente.",
                    "success"
                )

                messages.success(request, "Revisión de calidad y las imágenes se han actualizado correctamente.")
                return redirect('produccion:gestion_calidad', pk=calidad.id)
            except Exception as e:
                # Crear notificación de error
                self.crear_notificacion(
                    f"Error al actualizar la revisión de calidad del pedido #{calidad.produccion.pedido.id}: {str(e)}.",
                    "error"
                )
                messages.error(request, f"Hubo un error al actualizar la revisión de calidad: {str(e)}")
        else:
            # Crear notificación de formulario inválido
            self.crear_notificacion(
                f"No se pudo actualizar la revisión de calidad del pedido #{calidad.produccion.pedido.id}. Hay errores en el formulario.",
                "warning"
            )
            messages.error(request, "Hubo un error al actualizar la revisión de calidad.")

        return render(request, self.template_name, {
            'calidad': calidad,
            'calidad_form': calidad_form,
            'formset': formset,
        })

    def crear_notificacion(self, mensaje, tipo):
        Notification.objects.create(
            role="gestor de calidad",
            message=mensaje,
        )


class DetallePedidoView(VentasRequiredMixin, View):
    template_name = 'produccion/detalle_pedido.html'

    def test_func(self):
        """Verifica que el usuario sea administrador."""
        return self.request.user.role == 'ADMIN' or "VENTAS"

    def get(self, request, pk):
        pedido = get_object_or_404(Pedido, pk=pk)
        produccion = Produccion.objects.filter(pedido=pedido).first()
        calidad = Calidad.objects.filter(produccion=produccion).first() 
        logistica = Logistica.objects.filter(produccion=produccion).first() 

        context = {
            'pedido': pedido,
            'produccion': produccion,
            'calidad': calidad,
            'logistica': logistica,
        }
        return render(request, self.template_name, context)


class DashboardVentasView(VentasRequiredMixin, TemplateView):
    template_name = "produccion/dashboard_ventas.html"
    paginate_by = 10  # Número de pedidos por página

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Obtener los parámetros de filtro de la solicitud
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')

        # Convertir las fechas en objetos datetime
        start_date_obj = parse_date(start_date) if start_date else None
        end_date_obj = parse_date(end_date) if end_date else None

        # Filtrar pedidos por rango de fechas
        pedidos = Pedido.objects.all()
        if start_date_obj:
            pedidos = pedidos.filter(fecha_pedido__gte=start_date_obj)
        if end_date_obj:
            pedidos = pedidos.filter(fecha_pedido__lte=end_date_obj)

        # Resumen de pedidos
        context["total_pedidos"] = pedidos.count()
        context["pedidos_completados"] = pedidos.filter(estado_pedido="Completado").count()
        context["pedidos_pendientes"] = pedidos.filter(estado_pedido="Pendiente").count()
        context["pedidos_en_proceso"] = pedidos.filter(estado_pedido="En proceso").count()

        # Inventario crítico (opcional)
        inventarios = Inventario.objects.all()
        context["inventarios"] = [
            {
                "nombre_material": item.nombre_material,
                "cantidad_stock": item.cantidad_stock,
                "punto_reorden": item.punto_reorden,
                "status": "Crítico" if item.cantidad_stock <= item.punto_reorden * 0.5
                else "Reabastecer" if item.cantidad_stock <= item.punto_reorden
                else "Suficiente",
            }
            for item in inventarios
        ]
        context["stock_critico"] = len(
            [item for item in context["inventarios"] if item["status"] == "Crítico"]
        )

        # Top productos más vendidos filtrados por rango de fechas
        top_productos = PedidoProducto.objects.select_related("producto")

        # Filtrar por rango de fechas, si están especificadas
        if start_date_obj:
            top_productos = top_productos.filter(pedido__fecha_pedido__gte=start_date_obj)
        if end_date_obj:
            top_productos = top_productos.filter(pedido__fecha_pedido__lte=end_date_obj)

        # Agrupar y ordenar por cantidad vendida
        top_productos = (
            top_productos
            .values("producto__nombre_producto")
            .annotate(cantidad_vendida=Sum("cantidad"))
            .order_by("-cantidad_vendida")[:5]
        )

        context["top_productos"] = top_productos


        # Paginación de los pedidos filtrados
        paginator = Paginator(pedidos.order_by("-fecha_pedido"), self.paginate_by)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context["page_obj"] = page_obj
        context["is_paginated"] = page_obj.has_other_pages()
        context["start_date"] = start_date
        context["end_date"] = end_date

        return context

class DashboardProduccionView(ProduccionRequiredMixin, TemplateView):
    template_name = "produccion/dashboard_produccion.html"
    paginate_by = 10  # Número de elementos por página

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Contar las órdenes de producción por estado
        context['ordenes_en_proceso'] = Produccion.objects.filter(estado_produccion='En proceso').count()
        context['ordenes_completadas'] = Produccion.objects.filter(estado_produccion='Completado').count()
        context['ordenes_pendientes'] = Produccion.objects.filter(estado_produccion='Asignado').count()

        # Obtener las producciones actuales filtradas por estado "En proceso"
        producciones = Produccion.objects.filter(
            pedido__estado_pedido="Completado"
        ).exclude(
            estado_produccion="Completado"
        )


        # Paginación de las producciones
        paginator = Paginator(producciones, self.paginate_by)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context['page_obj'] = page_obj
        context['is_paginated'] = page_obj.has_other_pages()

        # Inventarios críticos
        inventarios = Inventario.objects.all()
        context['inventarios'] = [
            {
                "nombre_material": item.nombre_material,
                "cantidad_stock": item.cantidad_stock,
                "punto_reorden": item.punto_reorden,
                "status": "Crítico" if item.cantidad_stock <= item.punto_reorden * 0.5
                else "Reabastecer" if item.cantidad_stock <= item.punto_reorden
                else "Suficiente",
            }
            for item in inventarios
        ]

        return context

class DashboardCalidadView(CalidadRequiredMixin, TemplateView):
    template_name = "produccion/dashboard_calidad.html"
    paginate_by = 10  # Número de revisiones por página

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Filtrar revisiones por estado "Sin revisión" y producción en estado "Completado"
        revisiones = Calidad.objects.filter(
            resultado="Sin revisión",
            produccion__estado_produccion="Completado"
        ).order_by("-id")


        # Resumen de revisiones
        context["total_revisiones"] = revisiones.count()
        context["revisiones_pendientes"] = revisiones.filter(resultado="Sin revisión").count()
        context["revisiones_aprobadas"] = Calidad.objects.filter(resultado="Aprobado").count()
        context["revisiones_rechazadas"] = Calidad.objects.filter(resultado="Rechazado").count()

        # Paginación de las revisiones
        paginator = Paginator(revisiones, self.paginate_by)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context["page_obj"] = page_obj
        context["is_paginated"] = page_obj.has_other_pages()

        return context

class DashboardLogisticaView(LogisticaRequiredMixin, TemplateView):
    template_name = "produccion/dashboard_logistica.html"
    paginate_by = 10  # Número de órdenes por página

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Filtrar órdenes en estado 'Pendiente' o 'Enviado'
        ordenes = Logistica.objects.filter(
            produccion__estado_produccion="Completado",
            estado_entrega__in=['Pendiente', 'Enviado']
        ).order_by('-id')

        # Resumen de estados de órdenes
        context["ordenes_pendientes"] = Logistica.objects.filter(estado_entrega="Pendiente").count()
        context["ordenes_enviadas"] = Logistica.objects.filter(estado_entrega="Enviado").count()
        context["ordenes_entregadas"] = Logistica.objects.filter(estado_entrega="Entregado").count()

        # Paginación de las órdenes
        paginator = Paginator(ordenes, self.paginate_by)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context["page_obj"] = page_obj
        context["is_paginated"] = page_obj.has_other_pages()

        return context

def mark_notifications_read(request):
    if request.user.is_authenticated:
        user_role = request.user.role

        # Diccionario para mapear roles a gestores
        role_mapping = {
            "VENTAS": "gestor de ventas",
            "PRODUCCION": "gestor de produccion",
            "CALIDAD": "gestor de calidad",
            "LOGISTICA": "gestor de logistica",
            "ADMIN": "ADMIN",
        }

        if user_role in role_mapping:
            # Actualizar notificaciones no leídas como leídas
            Notification.objects.filter(role=role_mapping[user_role], is_read=False).update(is_read=True)

            # Eliminar notificaciones leídas del rol del usuario
            deleted_count, _ = Notification.objects.filter(role=user_role, is_read=True).delete()

            return JsonResponse({'status': 'success', 'deleted_count': deleted_count})

    return JsonResponse({'status': 'error'}, status=403)
