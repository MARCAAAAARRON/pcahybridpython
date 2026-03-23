from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('hybridization/', include('hybridization.urls')),
    path('reports/', include('reports.urls')),
    path('audit/', include('audit.urls')),
    path('field-data/', include('field_data.urls')),
    # Temporary route to test the 403 page layout
    path('test403/', TemplateView.as_view(template_name='403.html')),
    # Root redirect to dashboard
    path('', lambda request: redirect('dashboard:index')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
