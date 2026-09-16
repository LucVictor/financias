from django.urls import path

from . import views

app_name = 'contas_periodicas'

urlpatterns = [
    path('', views.home, name='home'),
    path('cadastros/', views.cadastros, name='cadastros'),
    path('contas/nova/', views.nova_conta, name='nova_conta'),
    path('contas/<int:pk>/editar/', views.editar_conta, name='editar_conta'),
    path('contas/<int:pk>/excluir/', views.excluir_conta, name='excluir_conta'),
    path('ocorrencias/<int:pk>/baixa/', views.dar_baixa_conta, name='baixa_conta'),
    path('recebimentos/novo/', views.novo_recebimento, name='novo_recebimento'),
    path('recebimentos/<int:pk>/editar/', views.editar_recebimento, name='editar_recebimento'),
    path('recebimentos/<int:pk>/excluir/', views.excluir_recebimento, name='excluir_recebimento'),
    path('ocorrencias-recebimento/<int:pk>/baixa/', views.dar_baixa_recebimento, name='baixa_recebimento'),
    path('avulsos/novo/', views.novo_avulso, name='novo_avulso'),
    path('avulsos/<int:pk>/editar/', views.editar_avulso, name='editar_avulso'),
    path('avulsos/<int:pk>/excluir/', views.excluir_avulso, name='excluir_avulso'),
    path('avulsos/<int:pk>/baixa/', views.dar_baixa_avulso, name='baixa_avulso'),
    path('pagamentos-avulsos/novo/', views.novo_pagamento_avulso, name='novo_pagamento_avulso'),
    path('pagamentos-avulsos/<int:pk>/editar/', views.editar_pagamento_avulso, name='editar_pagamento_avulso'),
    path('pagamentos-avulsos/<int:pk>/excluir/', views.excluir_pagamento_avulso, name='excluir_pagamento_avulso'),
    path('pagamentos-avulsos/<int:pk>/baixa/', views.dar_baixa_pagamento_avulso, name='baixa_pagamento_avulso'),
]