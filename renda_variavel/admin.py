from django.contrib import admin

from .models import Ativo, HistoricoAtivo, ProventoRecebido


@admin.register(Ativo)
class AtivoAdmin(admin.ModelAdmin):
    list_display = [
        'ticker', 'tipo', 'quantidade', 'preco_medio', 'preco_atual',
        'valor_mercado', 'dividend_yield_mensal', 'fonte_preco', 'ativo',
    ]
    list_filter = ['tipo', 'ativo', 'fonte_preco']
    search_fields = ['ticker']


@admin.register(ProventoRecebido)
class ProventoRecebidoAdmin(admin.ModelAdmin):
    list_display = ['ativo', 'data', 'valor', 'tipo']
    list_filter = ['ativo']


@admin.register(HistoricoAtivo)
class HistoricoAtivoAdmin(admin.ModelAdmin):
    list_display = ['ativo', 'preco', 'valor_mercado', 'criado_em']
    list_filter = ['ativo']