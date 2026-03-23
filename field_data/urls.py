from django.urls import path
from django.shortcuts import redirect
from . import views

app_name = 'field_data'

urlpatterns = [
    # Prevent direct access to /field-data/ (redirect to dashboard instead)
    path('', lambda request: redirect('dashboard:index'), name='overview'),

    # List views
    path('distribution/', views.distribution_list, name='distribution_list'),
    path('harvest/', views.harvest_list, name='harvest_list'),
    path('nursery/', views.nursery_list, name='nursery_list'),
    path('terminal/', views.terminal_list, name='terminal_list'),
    path('pollen/', views.pollen_list, name='pollen_list'),

    # Create (manual data entry)
    path('distribution/add/', views.distribution_create, name='distribution_create'),
    path('harvest/add/', views.harvest_create, name='harvest_create'),
    path('nursery/add/', views.nursery_create, name='nursery_create'),
    path('terminal/add/', views.terminal_create, name='terminal_create'),
    path('pollen/add/', views.pollen_create, name='pollen_create'),

    # Edit (update) views — must be before generic delete path
    path('distribution/<int:pk>/edit/', views.distribution_update, name='distribution_edit'),
    path('harvest/<int:pk>/edit/', views.harvest_update, name='harvest_edit'),
    path('nursery/<int:pk>/edit/', views.nursery_update, name='nursery_edit'),
    path('terminal/<int:pk>/edit/', views.terminal_update, name='terminal_edit'),
    path('pollen/<int:pk>/edit/', views.pollen_update, name='pollen_edit'),

    # Record Deletion and Status Change
    path('<str:data_type>/<int:pk>/delete/', views.record_delete, name='record_delete'),
    path('<str:data_type>/<int:pk>/status/<str:new_status>/', views.change_status, name='change_status'),

    # Excel export / download
    path('export/<str:data_type>/', views.export_excel, name='export'),

    # AJAX: carry-forward previous data
    path('harvest/carry-forward/', views.harvest_carry_forward, name='harvest_carry_forward'),
    path('pollen/carry-forward/', views.pollen_carry_forward, name='pollen_carry_forward'),
    path('nursery/carry-forward/', views.nursery_carry_forward, name='nursery_carry_forward'),
    path('terminal/carry-forward/', views.terminal_carry_forward, name='terminal_carry_forward'),
]

