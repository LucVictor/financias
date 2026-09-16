from django.urls import path

from . import views

app_name = 'dividas'

urlpatterns = [
    path('', views.lista, name='lista'),
    path('novo/', views.nova, name='nova'),
    path('<int:pk>/', views.detalhe, name='detalhe'),
    path('<int:pk>/editar/', views.editar, name='editar'),
    path('<int:pk>/excluir/', views.excluir, name='excluir'),
    path('parcelas/<int:pk>/pagar/', views.pagar_parcela, name='pagar_parcela'),
]