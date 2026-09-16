from django.urls import path

from . import views

app_name = 'contas'

urlpatterns = [
    path('', views.lista, name='lista'),
    path('novo/', views.novo_banco, name='novo'),
    path('<int:pk>/', views.detalhe, name='detalhe'),
    path('<int:pk>/editar/', views.editar_banco, name='editar'),
    path('<int:pk>/excluir/', views.excluir_banco, name='excluir'),
    path('<int:pk>/movimentacoes/nova/', views.nova_movimentacao, name='nova_movimentacao'),
    path('movimentacoes/nova/', views.nova_movimentacao, name='nova_movimentacao_sem_conta'),
    path('movimentacoes/<int:pk>/editar/', views.editar_movimentacao, name='editar_movimentacao'),
    path('movimentacoes/<int:pk>/excluir/', views.excluir_movimentacao, name='excluir_movimentacao'),
]