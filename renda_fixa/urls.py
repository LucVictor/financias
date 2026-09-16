from django.urls import path

from . import views

app_name = 'renda_fixa'

urlpatterns = [
    path('', views.lista, name='lista'),
    path('novo/', views.nova_aplicacao, name='nova'),
    path('<int:pk>/editar/', views.editar_aplicacao, name='editar'),
    path('<int:pk>/excluir/', views.excluir_aplicacao, name='excluir'),
    path('taxa/nova/', views.nova_taxa, name='nova_taxa'),
]