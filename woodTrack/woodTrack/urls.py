from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('produccion/', include('produccion.urls', namespace='produccion')),
    path('accounts/', include('allauth.urls')),  # Rutas de Allauth
    path('', lambda request: redirect('account_login')), 
]
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

