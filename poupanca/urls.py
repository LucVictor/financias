from django.urls import path

from . import views

app_name = 'poupanca'

urlpatterns = [
    path('', views.lista, name='lista'),
    path('novo/', views.nova, name='nova'),
    path('<int:pk>/', views.detalhe, name='detalhe'),
    path('<int:pk>/editar/', views.editar, name='editar'),
    path('<int:pk>/excluir/', views.excluir, name='excluir'),
    path('<int:pk>/movimentacoes/nova/', views.nova_movimentacao, name='nova_movimentacao'),
]