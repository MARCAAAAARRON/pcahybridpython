from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.index, name='index'),
    path('generate/', views.generate_report, name='generate'),
    path('<int:pk>/download/', views.download_report, name='download'),
]
