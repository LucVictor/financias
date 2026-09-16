from django.contrib import admin

from .models import Banco, HistoricoContaBancaria, Movimentacao


@admin.register(Banco)
class BancoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo_conta', 'saldo_atual', 'ativo']
    list_filter = ['tipo_conta', 'ativo']
    search_fields = ['nome']


@admin.register(Movimentacao)
class MovimentacaoAdmin(admin.ModelAdmin):
    list_display = ['data', 'descricao', 'categoria', 'tipo', 'valor', 'conta']
    list_filter = ['tipo', 'data', 'conta']
    search_fields = ['descricao', 'categoria']


@admin.register(HistoricoContaBancaria)
class HistoricoContaBancariaAdmin(admin.ModelAdmin):
    list_display = ['banco', 'valor', 'criado_em', 'usuario']
    list_filter = ['banco', 'criado_em']
    search_fields = ['banco__nome']