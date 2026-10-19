from django.urls import path
from . import views
from .occupation_full import occupation_dashboard, occupation_profil

app_name = 'portal'
urlpatterns = [
    path('', views.home, name='home'),
    path('modules/occupation/', occupation_dashboard, name='occupation_dashboard'),
    path('modules/occupation/profil/', occupation_profil, name='occupation_profil'),
    path('modules/<slug:slug>/', views.module_detail, name='module'),
    path('api/modules/<slug:slug>/predict/', views.predict_api, name='predict_api'),
    path('health/', views.health, name='health'),
]
