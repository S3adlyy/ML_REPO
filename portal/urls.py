from django.urls import path
from . import views

app_name = 'portal'
urlpatterns = [
    path('', views.home, name='home'),
    path('modules/<slug:slug>/', views.module_detail, name='module'),
    path('api/modules/<slug:slug>/predict/', views.predict_api, name='predict_api'),
    path('health/', views.health, name='health'),
]
