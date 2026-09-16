from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from sistema_financas.helpers import erro_message, success_message
from .forms import BancoForm, MovimentacaoForm
from .models import Banco, Movimentacao


@login_required
def lista(request):
    bancos = Banco.objects.filter(ativo=True)
    total_geral = sum(b.saldo_atual for b in bancos)
    return render(request, 'contas/lista.html', {
        'bancos': bancos,
        'total_geral': total_geral,
    })


@login_required
def detalhe(request, pk):
    banco = get_object_or_404(Banco, pk=pk)

    # Filtros por período
    ano = request.GET.get('ano', str(date.today().year))
    mes = request.GET.get('mes', '')
    movs = Movimentacao.objects.filter(conta=banco)
    if mes:
        movs = movs.filter(data__year=int(ano), data__month=int(mes))
    else:
        movs = movs.filter(data__year=int(ano))
    movs = movs.order_by('-data')

    totais_entrada = movs.filter(tipo='entrada').aggregate(t=Sum('valor'))['t'] or 0
    totais_saida = movs.filter(tipo='saida').aggregate(t=Sum('valor'))['t'] or 0
    saldo_periodo = totais_entrada - totais_saida

    periodos = []
    for m in range(1, 13):
        periodos.append({'value': str(m), 'label': f'{m:02d}/{ano}'})
    anos = list(range(date.today().year, date.today().year - 5, -1))

    return render(request, 'contas/detalhe.html', {
        'banco': banco,
        'movimentacoes': movs,
        'totais_entrada': totais_entrada,
        'totais_saida': totais_saida,
        'saldo_periodo': saldo_periodo,
        'ano': ano,
        'mes': mes,
        'periodos': periodos,
        'anos': anos,
    })


@login_required
def novo_banco(request):
    form = BancoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        success_message(request, 'Conta cadastrada com sucesso.')
        return redirect(reverse('contas:lista'))
    return render(request, 'generic_form.html', {
        'titulo': 'Novo Banco / Conta',
        'form': form,
        'back_url': reverse('contas:lista'),
        'icone': 'bi-bank',
    })


@login_required
def editar_banco(request, pk):
    banco = get_object_or_404(Banco, pk=pk)
    form = BancoForm(request.POST or None, instance=banco)
    if request.method == 'POST' and form.is_valid():
        form.save()
        success_message(request, 'Conta atualizada.')
        return redirect(reverse('contas:lista'))
    return render(request, 'generic_form.html', {
        'titulo': f'Editar {banco.nome}',
        'form': form,
        'back_url': reverse('contas:lista'),
        'icone': 'bi-bank',
    })


@login_required
def excluir_banco(request, pk):
    banco = get_object_or_404(Banco, pk=pk)
    if request.method == 'POST':
        banco.delete()
        success_message(request, 'Conta excluída.')
        return redirect(reverse('contas:lista'))
    return render(request, 'generic_confirm_delete.html', {
        'objeto': banco,
        'back_url': reverse('contas:lista'),
    })


@login_required
def nova_movimentacao(request, pk=None):
    form = MovimentacaoForm(request.POST or None)
    if pk:
        form.fields['conta'].initial = Banco.objects.get(pk=pk)
        form.fields['conta'].disabled = True
    if request.method == 'POST' and form.is_valid():
        mov = form.save(commit=False)
        if pk:
            mov.conta = Banco.objects.get(pk=pk)
        mov.save()
        success_message(request, 'Movimentação registrada e saldo atualizado.')
        return redirect(reverse('contas:detalhe', args=[mov.conta.pk]))
    return render(request, 'generic_form.html', {
        'titulo': 'Nova Movimentação',
        'form': form,
        'back_url': reverse('contas:lista'),
        'icone': 'bi-arrow-left-right',
    })


@login_required
def editar_movimentacao(request, pk):
    mov = get_object_or_404(Movimentacao, pk=pk)
    form = MovimentacaoForm(request.POST or None, instance=mov)
    if request.method == 'POST' and form.is_valid():
        form.save()
        success_message(request, 'Movimentação atualizada.')
        return redirect(reverse('contas:detalhe', args=[mov.conta.pk]))
    return render(request, 'generic_form.html', {
        'titulo': 'Editar Movimentação',
        'form': form,
        'back_url': reverse('contas:detalhe', args=[mov.conta.pk]),
        'icone': 'bi-arrow-left-right',
    })


@login_required
def excluir_movimentacao(request, pk):
    mov = get_object_or_404(Movimentacao, pk=pk)
    conta_pk = mov.conta.pk
    if request.method == 'POST':
        # Reverte o efeito no saldo
        if mov.tipo == 'entrada':
            mov.conta.saldo_atual -= mov.valor
        else:
            mov.conta.saldo_atual += mov.valor
        mov.conta.save(update_fields=['saldo_atual'])
        mov.delete()
        success_message(request, 'Movimentação excluída e saldo ajustado.')
        return redirect(reverse('contas:detalhe', args=[conta_pk]))
    return render(request, 'generic_confirm_delete.html', {
        'objeto': mov,
        'back_url': reverse('contas:detalhe', args=[conta_pk]),
    })