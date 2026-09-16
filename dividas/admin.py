from django.contrib import admin

from .models import Divida, HistoricoDivida, ParcelaDivida


@admin.register(Divida)
class DividaAdmin(admin.ModelAdmin):
    list_display = [
        'descricao', 'credor', 'valor_total', 'valor_pago', 'valor_restante',
        'data_vencimento', 'status', 'para_pagamento', 'ativa',
    ]
    list_filter = ['status', 'ativa', 'para_pagamento']
    search_fields = ['descricao', 'credor']


@admin.register(ParcelaDivida)
class ParcelaDividaAdmin(admin.ModelAdmin):
    list_display = ['divida', 'numero', 'valor', 'data_vencimento', 'status', 'data_pagamento']
    list_filter = ['status']
    search_fields = ['divida__descricao']


@admin.register(HistoricoDivida)
class HistoricoDividaAdmin(admin.ModelAdmin):
    list_display = ['divida', 'valor_restante', 'criado_em', 'usuario']
    list_filter = ['divida']