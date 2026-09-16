from django.urls import path

from . import views

app_name = 'renda_variavel'

urlpatterns = [
    path('', views.lista, name='lista'),
    path('novo/', views.novo, name='novo'),
    path('<int:pk>/editar/', views.editar, name='editar'),
    path('<int:pk>/excluir/', views.excluir, name='excluir'),
    path('<int:ativo_pk>/proventos/novo/', views.novo_provento, name='novo_provento'),
    path('proventos/novo/', views.novo_provento, name='novo_provento_sem_ativo'),
]