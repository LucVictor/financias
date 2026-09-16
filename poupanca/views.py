from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from sistema_financas.helpers import success_message
from .forms import ContaPoupancaForm, MovimentacaoPoupancaForm
from .models import ContaPoupanca, MovimentacaoPoupanca


@login_required
def lista(request):
    contas = ContaPoupanca.objects.filter(ativo=True)
    total = sum(c.saldo_atual for c in contas)
    return render(request, 'poupanca/lista.html', {
        'contas': contas,
        'total': total,
    })


@login_required
def nova(request):
    form = ContaPoupancaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        success_message(request, 'Conta poupança cadastrada.')
        return redirect(reverse('poupanca:lista'))
    return render(request, 'generic_form.html', {
        'titulo': 'Nova Conta Poupança',
        'form': form,
        'back_url': reverse('poupanca:lista'),
        'icone': 'bi-piggy-bank',
    })


@login_required
def editar(request, pk):
    conta = get_object_or_404(ContaPoupanca, pk=pk)
    form = ContaPoupancaForm(request.POST or None, instance=conta)
    if request.method == 'POST' and form.is_valid():
        form.save()
        success_message(request, 'Conta poupança atualizada.')
        return redirect(reverse('poupanca:lista'))
    return render(request, 'generic_form.html', {
        'titulo': f'Editar {conta.nome}',
        'form': form,
        'back_url': reverse('poupanca:lista'),
        'icone': 'bi-piggy-bank',
    })


@login_required
def excluir(request, pk):
    conta = get_object_or_404(ContaPoupanca, pk=pk)
    if request.method == 'POST':
        conta.delete()
        success_message(request, 'Conta poupança excluída.')
        return redirect(reverse('poupanca:lista'))
    return render(request, 'generic_confirm_delete.html', {
        'objeto': conta,
        'back_url': reverse('poupanca:lista'),
    })


@login_required
def detalhe(request, pk):
    conta = get_object_or_404(ContaPoupanca, pk=pk)
    movs = MovimentacaoPoupanca.objects.filter(conta=conta).order_by('-data')
    return render(request, 'poupanca/detalhe.html', {
        'conta': conta,
        'movimentacoes': movs,
    })


@login_required
def nova_movimentacao(request, pk):
    conta = get_object_or_404(ContaPoupanca, pk=pk)
    form = MovimentacaoPoupancaForm(request.POST or None)
    form.fields['conta'].initial = conta
    form.fields['conta'].disabled = True
    if request.method == 'POST' and form.is_valid():
        mov = form.save(commit=False)
        mov.conta = conta
        mov.save()
        success_message(request, 'Movimentação registrada.')
        return redirect(reverse('poupanca:detalhe', args=[conta.pk]))
    return render(request, 'generic_form.html', {
        'titulo': f'Movimentar {conta.nome}',
        'form': form,
        'back_url': reverse('poupanca:detalhe', args=[conta.pk]),
        'icone': 'bi-arrow-left-right',
    })