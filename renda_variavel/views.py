from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from sistema_financas.helpers import success_message
from .forms import AtivoForm, ProventoForm
from .models import Ativo, ProventoRecebido


@login_required
def lista(request):
    ativos = Ativo.objects.filter(ativo=True)
    total_mercado = sum(a.valor_mercado for a in ativos)
    total_proventos_mensais = sum(a.proventos_mensais_estimados() for a in ativos)
    proventos_recebidos = ProventoRecebido.objects.filter(data__year=date.today().year).order_by('-data')
    return render(request, 'renda_variavel/lista.html', {
        'ativos': ativos,
        'total_mercado': total_mercado,
        'total_proventos_mensais': total_proventos_mensais,
        'proventos_recebidos': proventos_recebidos,
    })


@login_required
def novo(request):
    form = AtivoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        success_message(request, 'Ativo cadastrado.')
        return redirect(reverse('renda_variavel:lista'))
    return render(request, 'generic_form.html', {
        'titulo': 'Novo Ativo',
        'form': form,
        'back_url': reverse('renda_variavel:lista'),
        'icone': 'bi-graph-up',
    })


@login_required
def editar(request, pk):
    ativo = get_object_or_404(Ativo, pk=pk)
    form = AtivoForm(request.POST or None, instance=ativo)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.atualizado_em = timezone.now()
        obj.save()
        success_message(request, 'Ativo atualizado.')
        return redirect(reverse('renda_variavel:lista'))
    return render(request, 'generic_form.html', {
        'titulo': f'Editar {ativo.ticker}',
        'form': form,
        'back_url': reverse('renda_variavel:lista'),
        'icone': 'bi-graph-up',
    })


@login_required
def excluir(request, pk):
    ativo = get_object_or_404(Ativo, pk=pk)
    if request.method == 'POST':
        ativo.delete()
        success_message(request, 'Ativo excluído.')
        return redirect(reverse('renda_variavel:lista'))
    return render(request, 'generic_confirm_delete.html', {
        'objeto': ativo,
        'back_url': reverse('renda_variavel:lista'),
    })


@login_required
def novo_provento(request, ativo_pk=None):
    form = ProventoForm(request.POST or None)
    if ativo_pk:
        form.fields['ativo'].initial = Ativo.objects.get(pk=ativo_pk)
    if request.method == 'POST' and form.is_valid():
        form.save()
        success_message(request, 'Provento registrado.')
        return redirect(reverse('renda_variavel:lista'))
    return render(request, 'generic_form.html', {
        'titulo': 'Registrar Provento Recebido',
        'form': form,
        'back_url': reverse('renda_variavel:lista'),
        'icone': 'bi-coin',
    })