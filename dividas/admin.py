from django.contrib import admin

from .models import Divida, HistoricoDivida


@admin.register(Divida)
class DividaAdmin(admin.ModelAdmin):
    list_display = [
        'descricao', 'credor', 'valor_total', 'valor_pago', 'valor_restante',
        'data_vencimento', 'status', 'ativa',
    ]
    list_filter = ['status', 'ativa']
    search_fields = ['descricao', 'credor']


@admin.register(HistoricoDivida)
class HistoricoDividaAdmin(admin.ModelAdmin):
    list_display = ['divida', 'valor_restante', 'criado_em', 'usuario']
    list_filter = ['divida']