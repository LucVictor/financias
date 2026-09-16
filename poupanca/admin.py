from django.contrib import admin

from .models import ContaPoupanca, HistoricoPoupanca, MovimentacaoPoupanca


@admin.register(ContaPoupanca)
class ContaPoupancaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'instituicao', 'saldo_atual', 'usar_regra_selic', 'taxa_selic_anual', 'ativo']
    list_filter = ['ativo']


@admin.register(MovimentacaoPoupanca)
class MovimentacaoPoupancaAdmin(admin.ModelAdmin):
    list_display = ['data', 'conta', 'tipo', 'valor', 'descricao']
    list_filter = ['tipo', 'conta']


@admin.register(HistoricoPoupanca)
class HistoricoPoupancaAdmin(admin.ModelAdmin):
    list_display = ['conta', 'valor', 'criado_em']
    list_filter = ['conta']