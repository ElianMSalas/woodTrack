from django import forms
from .models import Cliente, PedidoProducto, Pedido, Inventario, Logistica, Calidad, ImagenCalidad
from django.forms import ModelForm, inlineformset_factory, modelformset_factory
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, EmailValidator

class ClienteForm(ModelForm):
    # Campos con validaciones específicas
    nombre_cliente = forms.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$',
                message="El nombre solo puede contener letras y espacios."
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese el nombre del cliente'
        })
    )
    direccion = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese la dirección del cliente'
        })
    )
    telefono = forms.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="El número de teléfono debe contener entre 9 y 15 dígitos."
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese el teléfono del cliente'
        })
    )
    email = forms.EmailField(
        validators=[
            EmailValidator(message="Ingrese una dirección de correo electrónico válida.")
        ],
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese el correo electrónico del cliente'
        })
    )

    class Meta:
        model = Cliente
        fields = ['nombre_cliente', 'direccion', 'telefono', 'email']
class PedidoProductoForm(forms.ModelForm):
    class Meta:
        model = PedidoProducto
        fields = ['producto', 'cantidad']
        exclude = ('pedido',)  # Excluye el campo pedido

    def save(self, commit=True, pedido=None):
        instance = super().save(commit=False)
        if pedido:
            instance.pedido = pedido
        if commit:
            instance.save()
        return instance
    



class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ['cliente', 'estado_pedido']

class InventarioForm(forms.ModelForm):
    class Meta:
        model = Inventario
        fields = ['nombre_material', 'cantidad_stock', 'punto_reorden']

class GestionLogisticaForm(forms.ModelForm):
    class Meta:
        model = Logistica
        fields = ['estado_entrega', 'fecha_entrega']
        widgets = {
            'estado_entrega': forms.Select(choices=[
                ('Pendiente', 'Pendiente'),
                ('Enviado', 'Enviado'),
                ('Entregado', 'Entregado')
            ]),
            'fecha_entrega': forms.DateInput(attrs={'type': 'date'}),
        }

class CalidadForm(forms.ModelForm):
    class Meta:
        model = Calidad
        fields = ['resultado', 'comentarios']
        widgets = {
            'resultado': forms.Select(choices=[
                ('Aprobado', 'Aprobado'),
                ('Rechazado', 'Rechazado'),
                ('Sin revisión', 'Sin revisión')
            ]),
            'comentarios': forms.Textarea(attrs={'rows': 4, 'cols': 50}),
        }

class ImagenCalidadForm(forms.ModelForm):
    class Meta:
        model = ImagenCalidad
        fields = ['imagen', 'descripcion']

