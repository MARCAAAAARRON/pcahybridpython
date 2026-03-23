from django.urls import path
from . import views

app_name = 'hybridization'

urlpatterns = [
    path('', views.record_list, name='record_list'),
    path('create/', views.record_create, name='record_create'),
    path('<int:pk>/', views.record_detail, name='record_detail'),
    path('<int:pk>/edit/', views.record_update, name='record_update'),
    path('<int:pk>/delete/', views.record_delete, name='record_delete'),
    path('<int:pk>/submit/', views.record_submit, name='record_submit'),
    path('<int:pk>/validate/', views.record_validate, name='record_validate'),
]
