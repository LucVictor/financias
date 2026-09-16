from django.contrib import admin

from .models import Criptomoeda, HistoricoCripto


@admin.register(Criptomoeda)
class CriptomoedaAdmin(admin.ModelAdmin):
    list_display = [
        'simbolo', 'nome', 'quantidade', 'cotacao_brl', 'cotacao_usd',
        'cotacao_btc', 'fonte_cotacao', 'auto_cotacao', 'fonte_api',
        'par_cotacao', 'atualizado_em', 'ativo',
    ]
    list_filter = ['ativo', 'fonte_cotacao', 'auto_cotacao', 'fonte_api']
    search_fields = ['simbolo', 'nome']
    actions = ['precificar_selecionadas']

    @admin.action(description='Atualizar cotações selecionadas via API')
    def precificar_selecionadas(self, request, queryset):
        from .services.crypto_quotes import precificar_moeda
        atualizadas = 0
        erros = []
        for moeda in queryset:
            resultado = precificar_moeda(moeda)
            if resultado['ok']:
                atualizadas += 1
            else:
                erros.append(resultado['mensagem'])
        mensagem = f'{atualizadas} moeda(s) atualizada(s).'
        if erros:
            mensagem += ' Erros: ' + ' | '.join(erros)
        self.message_user(request, mensagem)


@admin.register(HistoricoCripto)
class HistoricoCriptoAdmin(admin.ModelAdmin):
    list_display = ['moeda', 'cotacao_brl', 'valor_brl', 'criado_em']
    list_filter = ['moeda']