from django.urls import path

from . import views

app_name = 'dividas'

urlpatterns = [
    path('', views.lista, name='lista'),
    path('novo/', views.nova, name='nova'),
    path('<int:pk>/editar/', views.editar, name='editar'),
    path('<int:pk>/excluir/', views.excluir, name='excluir'),
]