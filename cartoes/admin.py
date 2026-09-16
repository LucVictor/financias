from django.contrib import admin

from .models import CartaoCredito, CompraCartao, FaturaCartao, HistoricoCartao, ParcelaCompra


class ParcelaCompraInline(admin.TabularInline):
    model = ParcelaCompra
    extra = 0
    readonly_fields = ['numero_parcela', 'valor', 'ano', 'mes', 'status']


@admin.register(CartaoCredito)
class CartaoCreditoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'banco_emissor', 'limite_total', 'limite_disponivel', 'ativo']
    search_fields = ['nome', 'banco_emissor']


@admin.register(CompraCartao)
class CompraCartaoAdmin(admin.ModelAdmin):
    list_display = [
        'data_compra', 'descricao', 'estabelecimento', 'categoria', 'valor_total',
        'forma_pagamento', 'num_parcelas', 'cancelada',
    ]
    list_filter = ['forma_pagamento', 'data_compra', 'cartao', 'cancelada']
    search_fields = ['descricao', 'estabelecimento', 'categoria']
    inlines = [ParcelaCompraInline]


@admin.register(ParcelaCompra)
class ParcelaCompraAdmin(admin.ModelAdmin):
    list_display = ['compra', 'numero_parcela', 'valor', 'mes', 'ano', 'status']
    list_filter = ['status', 'mes', 'ano']


@admin.register(FaturaCartao)
class FaturaCartaoAdmin(admin.ModelAdmin):
    list_display = ['cartao', 'mes', 'ano', 'valor_total', 'estado', 'data_pagamento']
    list_filter = ['estado', 'cartao']


@admin.register(HistoricoCartao)
class HistoricoCartaoAdmin(admin.ModelAdmin):
    list_display = ['cartao', 'limite_disponivel', 'saldo_devedor', 'criado_em']
    list_filter = ['cartao']