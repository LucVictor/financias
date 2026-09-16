from django.urls import path

from . import views

app_name = 'assistente'

urlpatterns = [
    path('chat/', views.chat, name='chat'),
]