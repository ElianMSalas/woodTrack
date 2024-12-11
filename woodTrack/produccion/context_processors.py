from .models import Notification

def role_notifications(request):
    if request.user.is_authenticated and request.user.role == "VENTAS":
        return {
            'notifications': Notification.objects.filter(role="gestor de ventas", is_read=False)
        }
    elif request.user.is_authenticated and request.user.role == "PRODUCCION":
        return {
            'notifications': Notification.objects.filter(role="gestor de produccion", is_read=False)
        }
    elif request.user.is_authenticated and request.user.role == "CALIDAD":
        return {
            'notifications': Notification.objects.filter(role="gestor de calidad", is_read=False)
        }
    elif request.user.is_authenticated and request.user.role == "LOGISTICA":
        return {
            'notifications': Notification.objects.filter(role="gestor de logistica", is_read=False)
        }
    elif request.user.is_authenticated and request.user.role == "ADMIN":
        return {
            'notifications': Notification.objects.filter(role="ADMIN", is_read=False)
        }

    return {'notifications': []}
