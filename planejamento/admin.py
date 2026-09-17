from django.contrib import admin

from .models import AporteMensal, ObjetivoFinanceiro


class AporteMensalInline(admin.TabularInline):
    model = AporteMensal
    extra = 0
    readonly_fields = ['ano', 'mes', 'valor', 'realizado', 'valor_realizado', 'data_realizado']
    can_delete = False


@admin.register(ObjetivoFinanceiro)
class ObjetivoFinanceiroAdmin(admin.ModelAdmin):
    list_display = [
        'nome', 'valor_final', 'valor_inicial', 'taxa_rendimento_pct',
        'data_inicio', 'data_conclusao', 'status', 'refletir_fluxo', 'criado_em',
    ]
    list_filter = ['status', 'refletir_fluxo']
    search_fields = ['nome', 'descricao']
    inlines = [AporteMensalInline]
