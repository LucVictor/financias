from django.contrib import admin

from .models import AplicacaoCDB, HistoricoCDB, TaxaCDI


@admin.register(TaxaCDI)
class TaxaCDIAdmin(admin.ModelAdmin):
    list_display = ['valor_anual', 'data_inicio', 'criado_em']
    ordering = ['-data_inicio']


@admin.register(AplicacaoCDB)
class AplicacaoCDBAdmin(admin.ModelAdmin):
    list_display = [
        'instituicao', 'valor_aplicado', 'data_aplicacao', 'data_vencimento',
        'percentual_cdi', 'ativo',
    ]
    list_filter = ['ativo', 'instituicao']


@admin.register(HistoricoCDB)
class HistoricoCDBAdmin(admin.ModelAdmin):
    list_display = ['aplicacao', 'valor_bruto', 'valor_liquido', 'dias_uteis', 'criado_em']
    list_filter = ['aplicacao']