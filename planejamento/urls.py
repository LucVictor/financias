from django.urls import path

from . import views

app_name = 'planejamento'

urlpatterns = [
    path('', views.lista, name='lista'),
    path('novo/', views.novo, name='novo'),
    path('<int:pk>/', views.detalhe, name='detalhe'),
    path('<int:pk>/editar/', views.editar, name='editar'),
    path('<int:pk>/excluir/', views.excluir, name='excluir'),
    path('<int:pk>/alternar-fluxo/', views.alternar_fluxo, name='alternar_fluxo'),
    path('<int:pk>/concluir/', views.concluir, name='concluir'),
    path('<int:pk>/realizar-aporte/', views.realizar_aporte, name='realizar_aporte'),
    path('<int:pk>/aportes/<int:aporte_pk>/editar/', views.editar_aporte, name='editar_aporte'),
]
