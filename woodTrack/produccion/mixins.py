from django.core.exceptions import PermissionDenied
from .models import User

class AdminRequiredMixin:
    """Mixin para permitir acceso solo a administradores o superusuarios."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not (request.user.role == User.ADMINISTRADOR or request.user.is_superuser):
            raise PermissionDenied("Acceso denegado.")
        return super().dispatch(request, *args, **kwargs)

class VentasRequiredMixin:
    """Mixin para permitir acceso solo a encargados de ventas y administradores."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not (request.user.role == User.ENCARGADO_VENTAS or request.user.role == User.ADMINISTRADOR):
            raise PermissionDenied("Acceso denegado.")
        return super().dispatch(request, *args, **kwargs)

class ProduccionRequiredMixin:
    """Mixin para permitir acceso solo a operarios de producción."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role not in [User.ADMINISTRADOR, User.OPERARIO_PRODUCCION]:
            raise PermissionDenied("Acceso denegado.")
        return super().dispatch(request, *args, **kwargs)

class CalidadRequiredMixin:
    """Mixin para permitir acceso solo a encargados de calidad."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role not in [User.ADMINISTRADOR, User.ENCARGADO_CALIDAD]:
            raise PermissionDenied("Acceso denegado.")
        return super().dispatch(request, *args, **kwargs)

class LogisticaRequiredMixin:
    """Mixin para permitir acceso solo a operarios de logística."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role not in [User.ADMINISTRADOR, User.OPERARIO_LOGISTICA]:
            raise PermissionDenied("Acceso denegado.")
        return super().dispatch(request, *args, **kwargs)
