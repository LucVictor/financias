from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from sistema_financas.helpers import erro_message, success_message
from .forms import CriptomoedaForm
from .models import Criptomoeda
from .services.crypto_quotes import precificar_auto, precificar_moeda


@login_required
def lista(request):
    moedas = Criptomoeda.objects.filter(ativo=True)
    total_brl = sum(m.valor_brl for m in moedas)
    total_usd = sum(m.valor_usd for m in moedas)
    return render(request, 'cripto/lista.html', {
        'moedas': moedas,
        'total_brl': total_brl,
        'total_usd': total_usd,
        'possui_auto': moedas.filter(auto_cotacao=True).exists(),
    })


@login_required
@require_POST
def atualizar(request, pk):
    moeda = get_object_or_404(Criptomoeda, pk=pk)
    resultado = precificar_moeda(moeda)
    if resultado['ok']:
        success_message(request, resultado['mensagem'])
    else:
        erro_message(request, resultado['mensagem'])
    return redirect(reverse('cripto:lista'))


@login_required
@require_POST
def atualizar_todas(request):
    resultado = precificar_auto()
    if resultado['ok']:
        success_message(request, resultado['mensagem'])
    else:
        erro_message(request, resultado['mensagem'])
    return redirect(reverse('cripto:lista'))


@login_required
def nova(request):
    form = CriptomoedaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.atualizado_em = timezone.now()
        obj.save()
        success_message(request, 'Criptomoeda cadastrada.')
        return redirect(reverse('cripto:lista'))
    return render(request, 'generic_form.html', {
        'titulo': 'Nova Criptomoeda',
        'form': form,
        'back_url': reverse('cripto:lista'),
        'icone': 'bi-currency-bitcoin',
        'submit_label': 'Cadastrar',
    })


@login_required
def editar(request, pk):
    moeda = get_object_or_404(Criptomoeda, pk=pk)
    form = CriptomoedaForm(request.POST or None, instance=moeda)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.atualizado_em = timezone.now()
        obj.save()
        success_message(request, 'Cotação atualizada (fonte: manual).')
        return redirect(reverse('cripto:lista'))
    return render(request, 'generic_form.html', {
        'titulo': f'Editar {moeda.simbolo} — Atualizar cotação',
        'form': form,
        'back_url': reverse('cripto:lista'),
        'icone': 'bi-currency-bitcoin',
        'submit_label': 'Salvar cotação',
    })


@login_required
def excluir(request, pk):
    moeda = get_object_or_404(Criptomoeda, pk=pk)
    if request.method == 'POST':
        moeda.delete()
        success_message(request, 'Criptomoeda excluída.')
        return redirect(reverse('cripto:lista'))
    return render(request, 'generic_confirm_delete.html', {
        'objeto': moeda,
        'back_url': reverse('cripto:lista'),
    })