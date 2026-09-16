from django.urls import path

from . import views

app_name = 'cartoes'

urlpatterns = [
    path('', views.lista, name='lista'),
    path('novo/', views.novo, name='novo'),
    path('<int:pk>/', views.detalhe, name='detalhe'),
    path('<int:pk>/editar/', views.editar, name='editar'),
    path('<int:pk>/excluir/', views.excluir, name='excluir'),
    path('<int:cartao_pk>/compras/nova/', views.nova_compra, name='nova_compra'),
    path('compras/nova/', views.nova_compra, name='nova_compra_sem_cartao'),
    path('faturas/<int:pk>/pagar/', views.pagar_fatura, name='pagar_fatura'),
]