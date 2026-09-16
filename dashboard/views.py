from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from . import services


@login_required
def home(request):
    composicao = services.composicao_ativos()
    contexto = {
        'total_contas': services.total_contas(),
        'total_poupanca': services.total_poupanca(),
        'total_cdbs': services.total_cdbs_bruto(),
        'total_renda_variavel': services.total_renda_variavel(),
        'total_cripto': services.total_cripto(),
        'total_ativos': services.total_ativos(),
        'total_dividas': services.total_dividas(),
        'total_faturas': services.total_faturas_em_aberto(),
        'total_passivos': services.total_passivos(),
        'saldo_liquido': services.saldo_liquido(),
        'fluxo_caixa': services.projecao_fluxo_caixa(),
        'evolucao': services.evolucao_patrimonial(dias=180),
        'composicao': composicao,
        'composicao_labels': list(composicao.keys()),
        'composicao_valores': list(composicao.values()),
    }
    return render(request, 'dashboard/home.html', contexto)