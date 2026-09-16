from django.contrib import admin

from .models import (
    ContaPeriodica,
    OcorrenciaContaPeriodica,
    OcorrenciaRecebimento,
    RecebimentoAvulso,
    RecebimentoPeriodico,
)


class OcorrenciaContaPeriodicaInline(admin.TabularInline):
    model = OcorrenciaContaPeriodica
    extra = 0
    readonly_fields = ['data_vencimento', 'valor', 'status', 'data_pagamento']


@admin.register(ContaPeriodica)
class ContaPeriodicaAdmin(admin.ModelAdmin):
    list_display = [
        'descricao', 'valor_esperado', 'dia_do_mes', 'recorrência',
        'categoria', 'conta_pagamento_padrao', 'cartao_pagamento_padrao', 'ativo',
    ]
    list_filter = ['ativo', 'recorrência']
    search_fields = ['descricao']
    inlines = [OcorrenciaContaPeriodicaInline]


@admin.register(OcorrenciaContaPeriodica)
class OcorrenciaContaPeriodicaAdmin(admin.ModelAdmin):
    list_display = ['conta_periodica', 'data_vencimento', 'valor', 'status', 'data_pagamento']
    list_filter = ['status']


@admin.register(RecebimentoPeriodico)
class RecebimentoPeriodicoAdmin(admin.ModelAdmin):
    list_display = ['descricao', 'valor_esperado', 'dia_do_mes', 'recorrência', 'ativo']
    list_filter = ['ativo', 'recorrência']


@admin.register(OcorrenciaRecebimento)
class OcorrenciaRecebimentoAdmin(admin.ModelAdmin):
    list_display = ['recebimento_periodico', 'data_prevista', 'valor', 'status', 'data_recebimento']
    list_filter = ['status']


@admin.register(RecebimentoAvulso)
class RecebimentoAvulsoAdmin(admin.ModelAdmin):
    list_display = ['descricao', 'valor', 'data_prevista', 'status', 'data_recebimento']
    list_filter = ['status']