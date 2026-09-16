from django.contrib import admin

from .models import Criptomoeda, HistoricoCripto


@admin.register(Criptomoeda)
class CriptomoedaAdmin(admin.ModelAdmin):
    list_display = [
        'simbolo', 'nome', 'quantidade', 'cotacao_brl', 'cotacao_usd',
        'cotacao_btc', 'fonte_cotacao', 'ativo',
    ]
    list_filter = ['ativo', 'fonte_cotacao']
    search_fields = ['simbolo', 'nome']


@admin.register(HistoricoCripto)
class HistoricoCriptoAdmin(admin.ModelAdmin):
    list_display = ['moeda', 'cotacao_brl', 'valor_brl', 'criado_em']
    list_filter = ['moeda']