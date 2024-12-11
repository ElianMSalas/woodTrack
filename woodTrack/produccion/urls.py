from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

app_name = 'produccion'

urlpatterns = [
    path('pedidos/', views.ListaPedidosView.as_view(), name='lista_pedidos'),
    path('crear_pedido/', views.CrearPedidoView.as_view(), name='crear_pedido'),
    path('pedido/editar/<int:pedido_id>/', views.EditarPedidoView.as_view(), name='editar_pedido'),
    path('pedido/detalle/<int:pk>', views.DetallePedidoView.as_view(), name='detalle_pedido'),
    path('produccion/<int:pk>/', views.GestionProduccionView.as_view(), name='gestion_produccion'),
    path('logistica/<int:pk>/', views.GestionLogisticaView.as_view(), name='gestion_logistica'),
    path('calidad/<int:pk>/', views.GestionCalidadView.as_view(), name='gestion_calidad'),
    path('gestion_usuarios/', views.GestionUsuariosView.as_view(), name='gestion_usuarios'),
    path('inventario/', views.GestionInventarioView.as_view(), name='gestionar_inventario'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('dashboard_ventas/', views.DashboardVentasView.as_view(), name='dashboard_ventas'),
    path('dashboard_produccion/', views.DashboardProduccionView.as_view(), name='dashboard_produccion'),
    path('dashboard_calidad/', views.DashboardCalidadView.as_view(), name='dashboard_calidad'),
    path('dashboard_logistica', views.DashboardLogisticaView.as_view(), name='dashboard_logistica'),
    path('notifications/read/', views.mark_notifications_read, name='mark_notifications_read'),
]


# Agregar soporte para archivos multimedia en modo DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
