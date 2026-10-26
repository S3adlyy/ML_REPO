from django.urls import path
from . import views, accounts
from .occupation_full import occupation_dashboard, occupation_profil

app_name = 'portal'
urlpatterns = [
    path('signin/', accounts.auth_page, name='signin'),
    path('signup/', accounts.auth_page, {'mode': 'signup'}, name='signup'),
    path('auth/session/', accounts.firebase_session, name='firebase_session'),
    path('signout/', accounts.signout, name='signout'),
    path('onboarding/', accounts.onboarding, name='onboarding'),
    path('workspace/', accounts.dashboard, name='dashboard'),
    path('workspace/history/clear/', accounts.clear_history, name='clear_history'),
    path('', views.home, name='home'),
    path('modules/occupation/', occupation_dashboard, name='occupation_dashboard'),
    path('modules/occupation/profil/', occupation_profil, name='occupation_profil'),
    path('modules/<slug:slug>/', views.module_detail, name='module'),
    path('api/modules/<slug:slug>/predict/', views.predict_api, name='predict_api'),
    path('health/', views.health, name='health'),
]
