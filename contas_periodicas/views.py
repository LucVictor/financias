from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from contas.models import Movimentacao
from cartoes.services import previsao_faturas_fluxo
from dashboard.services import projecao_fluxo_caixa
from dividas.models import ParcelaDivida
from sistema_financas.helpers import erro_message, success_message
from .forms import (
    BaixaContaForm,
    BaixaRecebimentoForm,
    ContaPeriodicaForm,
    PagamentoAvulsoForm,
    RecebimentoAvulsoForm,
    RecebimentoPeriodicoForm,
)
from .models import (
    ContaPeriodica,
    OcorrenciaContaPeriodica,
    OcorrenciaRecebimento,
    PagamentoAvulso,
    RecebimentoAvulso,
    RecebimentoPeriodico,
)
from .services import (
    gerar_ocorrencias_conta_periodica,
    gerar_ocorrencias_recebimento_periodico,
    processar_ciclos,
)


def _contexto_fluxo(ano=None, mes=None):
    hoje = timezone.localdate()
    ano = int(ano or hoje.year)
    mes = int(mes or hoje.month)
    projecao = projecao_fluxo_caixa(mes, ano)

    ocorrencias_pagar = (
        OcorrenciaContaPeriodica.objects
        .filter(data_vencimento__year=ano, data_vencimento__month=mes)
        .order_by('data_vencimento')
    )
    ocorrencias_receber = (
        OcorrenciaRecebimento.objects
        .filter(data_prevista__year=ano, data_prevista__month=mes)
        .order_by('data_prevista')
    )
    avulsos = (
        RecebimentoAvulso.objects
        .filter(data_prevista__year=ano, data_prevista__month=mes)
        .order_by('data_prevista')
    )
    pagamentos_avulsos = (
        PagamentoAvulso.objects
        .filter(data_pagamento__year=ano, data_pagamento__month=mes)
        .order_by('data_pagamento')
    )
    faturas_projecao = previsao_faturas_fluxo(ano, mes)
    parcelas_dividas = (
        ParcelaDivida.objects
        .filter(
            divida__para_pagamento=True,
            divida__ativa=True,
            status='a_pagar',
            data_vencimento__year=ano,
            data_vencimento__month=mes,
        )
        .select_related('divida')
        .order_by('data_vencimento')
    )
    periodos_mes = [{'value': str(m), 'label': f'{m:02d}/{ano}'} for m in range(1, 13)]
    anos_disponiveis = list(range(ano, ano - 3, -1))
    return {
        'ano': ano,
        'mes': mes,
        'periodos_mes': periodos_mes,
        'anos_disponiveis': anos_disponiveis,
        'projecao': projecao,
        'ocorrencias_pagar': ocorrencias_pagar,
        'pagamentos_avulsos': pagamentos_avulsos,
        'ocorrencias_receber': ocorrencias_receber,
        'avulsos': avulsos,
        'faturas_projecao': faturas_projecao,
        'parcelas_dividas': parcelas_dividas,
        'contas_periodicas': ContaPeriodica.objects.filter(ativo=True),
        'recebimentos_periodicos': RecebimentoPeriodico.objects.filter(ativo=True),
    }


@login_required
def home(request):
    processar_ciclos()
    contexto = _contexto_fluxo(request.GET.get('ano'), request.GET.get('mes'))
    return render(request, 'contas_periodicas/fluxo.html', contexto)


# ===== Contas periódicas (a pagar) =====

@login_required
def nova_conta(request):
    form = ContaPeriodicaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        conta = form.save()
        gerar_ocorrencias_conta_periodica(conta)
        success_message(request, 'Conta periódica cadastrada e ocorrências geradas.')
        return redirect(reverse('contas_periodicas:home'))
    return render(request, 'generic_form.html', {
        'titulo': 'Nova Conta Periódica',
        'form': form,
        'back_url': reverse('contas_periodicas:home'),
        'icone': 'bi-calendar-event',
    })


@login_required
def editar_conta(request, pk):
    conta = get_object_or_404(ContaPeriodica, pk=pk)
    form = ContaPeriodicaForm(request.POST or None, instance=conta)
    if request.method == 'POST' and form.is_valid():
        form.save()
        gerar_ocorrencias_conta_periodica(conta)
        success_message(request, 'Conta periódica atualizada.')
        return redirect(reverse('contas_periodicas:home'))
    return render(request, 'generic_form.html', {
        'titulo': f'Editar {conta.descricao}',
        'form': form,
        'back_url': reverse('contas_periodicas:home'),
        'icone': 'bi-calendar-event',
    })


@login_required
def excluir_conta(request, pk):
    conta = get_object_or_404(ContaPeriodica, pk=pk)
    if request.method == 'POST':
        conta.delete()
        success_message(request, 'Conta periódica excluída.')
        return redirect(reverse('contas_periodicas:home'))
    return render(request, 'generic_confirm_delete.html', {
        'objeto': conta,
        'back_url': reverse('contas_periodicas:home'),
    })


@login_required
def dar_baixa_conta(request, pk):
    ocorrencia = get_object_or_404(OcorrenciaContaPeriodica, pk=pk)
    form = BaixaContaForm(request.POST or None, initial={
        'data_efetiva': timezone.localdate(),
        'valor': ocorrencia.valor,
        'conta': ocorrencia.conta_periodica.conta_pagamento_padrao,
        'meio': 'conta' if ocorrencia.conta_periodica.conta_pagamento_padrao else 'dinheiro',
    })
    if request.method == 'POST' and form.is_valid():
        dados = form.cleaned_data
        mov = None
        if dados['meio'] == 'conta' and dados['conta']:
            mov = Movimentacao.objects.create(
                conta=dados['conta'],
                descricao=f'{ocorrencia.conta_periodica.descricao} (venc. {ocorrencia.data_vencimento:%d/%m/%Y})',
                categoria=ocorrencia.conta_periodica.categoria,
                valor=dados['valor'],
                data=dados['data_efetiva'],
                tipo='saida',
            )
        elif dados['meio'] == 'cartao' and ocorrencia.conta_periodica.cartao_pagamento_padrao:
            pass  # pago no cartão: não impacta conta bancária
        ocorrencia.status = 'paga'
        ocorrencia.data_pagamento = dados['data_efetiva']
        ocorrencia.valor_pago = dados['valor']
        ocorrencia.movimentacao = mov
        ocorrencia.save()
        success_message(request, 'Baixa registrada. Saldo da conta atualizado.')
        return redirect(reverse('contas_periodicas:home'))
    return render(request, 'generic_form.html', {
        'titulo': f'Dar baixa: {ocorrencia.conta_periodica.descricao} ({ocorrencia.data_vencimento:%d/%m/%Y})',
        'form': form,
        'back_url': reverse('contas_periodicas:home'),
        'icone': 'bi-check2-circle',
        'submit_label': 'Confirmar baixa',
    })


# ===== Pagamentos avulsos (a pagar) =====

@login_required
def novo_pagamento_avulso(request):
    form = PagamentoAvulsoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        success_message(request, 'Pagamento avulso cadastrado.')
        return redirect(reverse('contas_periodicas:home'))
    return render(request, 'generic_form.html', {
        'titulo': 'Novo Pagamento Avulso',
        'form': form,
        'back_url': reverse('contas_periodicas:home'),
        'icone': 'bi-arrow-up-circle',
    })


@login_required
def editar_pagamento_avulso(request, pk):
    avulso = get_object_or_404(PagamentoAvulso, pk=pk)
    form = PagamentoAvulsoForm(request.POST or None, instance=avulso)
    if request.method == 'POST' and form.is_valid():
        form.save()
        success_message(request, 'Pagamento avulso atualizado.')
        return redirect(reverse('contas_periodicas:home'))
    return render(request, 'generic_form.html', {
        'titulo': f'Editar {avulso.descricao}',
        'form': form,
        'back_url': reverse('contas_periodicas:home'),
        'icone': 'bi-arrow-up-circle',
    })


@login_required
def excluir_pagamento_avulso(request, pk):
    avulso = get_object_or_404(PagamentoAvulso, pk=pk)
    if request.method == 'POST':
        avulso.delete()
        success_message(request, 'Pagamento avulso excluído.')
        return redirect(reverse('contas_periodicas:home'))
    return render(request, 'generic_confirm_delete.html', {
        'objeto': avulso,
        'back_url': reverse('contas_periodicas:home'),
    })


@login_required
def dar_baixa_pagamento_avulso(request, pk):
    avulso = get_object_or_404(PagamentoAvulso, pk=pk)
    form = BaixaContaForm(request.POST or None, initial={
        'data_efetiva': timezone.localdate(),
        'valor': avulso.valor,
        'conta': avulso.conta_pagamento,
        'meio': 'conta' if avulso.conta_pagamento else 'dinheiro',
    })
    if request.method == 'POST' and form.is_valid():
        dados = form.cleaned_data
        mov = None
        if dados['meio'] == 'conta' and dados['conta']:
            mov = Movimentacao.objects.create(
                conta=dados['conta'],
                descricao=f'{avulso.descricao} (avulso)',
                valor=dados['valor'],
                data=dados['data_efetiva'],
                tipo='saida',
            )
        avulso.status = 'pago'
        avulso.data_efetiva_pagamento = dados['data_efetiva']
        avulso.valor_pago = dados['valor']
        avulso.movimentacao = mov
        avulso.save()
        success_message(request, 'Baixa registrada. Saldo da conta atualizado.')
        return redirect(reverse('contas_periodicas:home'))
    return render(request, 'generic_form.html', {
        'titulo': f'Dar baixa: {avulso.descricao}',
        'form': form,
        'back_url': reverse('contas_periodicas:home'),
        'icone': 'bi-check2-circle',
        'submit_label': 'Confirmar baixa',
    })


# ===== Recebimentos periódicos =====

@login_required
def novo_recebimento(request):
    form = RecebimentoPeriodicoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        receb = form.save()
        gerar_ocorrencias_recebimento_periodico(receb)
        success_message(request, 'Recebimento periódico cadastrado.')
        return redirect(reverse('contas_periodicas:home'))
    return render(request, 'generic_form.html', {
        'titulo': 'Novo Recebimento Periódico',
        'form': form,
        'back_url': reverse('contas_periodicas:home'),
        'icone': 'bi-cash-stack',
    })


@login_required
def editar_recebimento(request, pk):
    receb = get_object_or_404(RecebimentoPeriodico, pk=pk)
    form = RecebimentoPeriodicoForm(request.POST or None, instance=receb)
    if request.method == 'POST' and form.is_valid():
        form.save()
        gerar_ocorrencias_recebimento_periodico(receb)
        success_message(request, 'Recebimento periódico atualizado.')
        return redirect(reverse('contas_periodicas:home'))
    return render(request, 'generic_form.html', {
        'titulo': f'Editar {receb.descricao}',
        'form': form,
        'back_url': reverse('contas_periodicas:home'),
        'icone': 'bi-cash-stack',
    })


@login_required
def excluir_recebimento(request, pk):
    receb = get_object_or_404(RecebimentoPeriodico, pk=pk)
    if request.method == 'POST':
        receb.delete()
        success_message(request, 'Recebimento excluído.')
        return redirect(reverse('contas_periodicas:home'))
    return render(request, 'generic_confirm_delete.html', {
        'objeto': receb,
        'back_url': reverse('contas_periodicas:home'),
    })


@login_required
def dar_baixa_recebimento(request, pk):
    ocorrencia = get_object_or_404(OcorrenciaRecebimento, pk=pk)
    form = BaixaRecebimentoForm(request.POST or None, initial={
        'data_efetiva': timezone.localdate(),
        'valor': ocorrencia.valor,
        'conta': ocorrencia.recebimento_periodico.conta_destino_padrao,
    })
    if request.method == 'POST' and form.is_valid():
        dados = form.cleaned_data
        mov = None
        if dados['conta']:
            mov = Movimentacao.objects.create(
                conta=dados['conta'],
                descricao=f'{ocorrencia.recebimento_periodico.descricao} (prev. {ocorrencia.data_prevista:%d/%m/%Y})',
                categoria=ocorrencia.recebimento_periodico.categoria,
                valor=dados['valor'],
                data=dados['data_efetiva'],
                tipo='entrada',
            )
        ocorrencia.status = 'recebido'
        ocorrencia.data_recebimento = dados['data_efetiva']
        ocorrencia.valor_recebido = dados['valor']
        ocorrencia.movimentacao = mov
        ocorrencia.save()
        success_message(request, 'Recebimento dado como recebido.')
        return redirect(reverse('contas_periodicas:home'))
    return render(request, 'generic_form.html', {
        'titulo': f'Baixa de recebimento: {ocorrencia.recebimento_periodico.descricao}',
        'form': form,
        'back_url': reverse('contas_periodicas:home'),
        'icone': 'bi-cash-coin',
        'submit_label': 'Confirmar recebimento',
    })


# ===== Recebimentos avulsos =====

@login_required
def novo_avulso(request):
    form = RecebimentoAvulsoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        success_message(request, 'Recebimento avulso cadastrado.')
        return redirect(reverse('contas_periodicas:home'))
    return render(request, 'generic_form.html', {
        'titulo': 'Novo Recebimento Avulso',
        'form': form,
        'back_url': reverse('contas_periodicas:home'),
        'icone': 'bi-arrow-down-circle',
    })


@login_required
def editar_avulso(request, pk):
    avulso = get_object_or_404(RecebimentoAvulso, pk=pk)
    form = RecebimentoAvulsoForm(request.POST or None, instance=avulso)
    if request.method == 'POST' and form.is_valid():
        form.save()
        success_message(request, 'Recebimento avulso atualizado.')
        return redirect(reverse('contas_periodicas:home'))
    return render(request, 'generic_form.html', {
        'titulo': f'Editar {avulso.descricao}',
        'form': form,
        'back_url': reverse('contas_periodicas:home'),
        'icone': 'bi-arrow-down-circle',
    })


@login_required
def excluir_avulso(request, pk):
    avulso = get_object_or_404(RecebimentoAvulso, pk=pk)
    if request.method == 'POST':
        avulso.delete()
        success_message(request, 'Recebimento avulso excluído.')
        return redirect(reverse('contas_periodicas:home'))
    return render(request, 'generic_confirm_delete.html', {
        'objeto': avulso,
        'back_url': reverse('contas_periodicas:home'),
    })


@login_required
def dar_baixa_avulso(request, pk):
    avulso = get_object_or_404(RecebimentoAvulso, pk=pk)
    form = BaixaRecebimentoForm(request.POST or None, initial={
        'data_efetiva': timezone.localdate(),
        'valor': avulso.valor,
        'conta': avulso.conta_destino,
    })
    if request.method == 'POST' and form.is_valid():
        dados = form.cleaned_data
        mov = None
        if dados['conta']:
            mov = Movimentacao.objects.create(
                conta=dados['conta'],
                descricao=f'{avulso.descricao} (avulso)',
                valor=dados['valor'],
                data=dados['data_efetiva'],
                tipo='entrada',
            )
        avulso.status = 'recebido'
        avulso.data_recebimento = dados['data_efetiva']
        avulso.valor_recebido = dados['valor']
        avulso.movimentacao = mov
        avulso.save()
        success_message(request, 'Recebimento avulso dado como recebido.')
        return redirect(reverse('contas_periodicas:home'))
    return render(request, 'generic_form.html', {
        'titulo': f'Baixa de recebimento: {avulso.descricao}',
        'form': form,
        'back_url': reverse('contas_periodicas:home'),
        'icone': 'bi-cash-coin',
        'submit_label': 'Confirmar recebimento',
    })