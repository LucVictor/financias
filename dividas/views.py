from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from sistema_financas.helpers import success_message
from .forms import DividaForm
from .models import Divida, ParcelaDivida


def _atualizar_status_das_dividas(queryset):
    for divida in queryset:
        divida.atualizar_status()


@login_required
def lista(request):
    dividas = Divida.objects.filter(ativa=True)
    _atualizar_status_das_dividas(dividas)
    total_bruto = dividas.aggregate(t=Sum('valor_total'))['t'] or 0
    total_pago = dividas.aggregate(t=Sum('valor_pago'))['t'] or 0
    total_em_aberto = total_bruto - total_pago

    hoje = timezone.localdate()
    limite = hoje + timedelta(days=7)
    parcelas_proximas = (
        ParcelaDivida.objects
        .filter(
            divida__para_pagamento=True,
            divida__ativa=True,
            status='a_pagar',
            data_vencimento__lte=limite,
        )
        .select_related('divida')
        .order_by('data_vencimento')
    )

    return render(request, 'dividas/lista.html', {
        'dividas': dividas,
        'total_em_aberto': total_em_aberto,
        'parcelas_proximas': parcelas_proximas,
    })


@login_required
def detalhe(request, pk):
    divida = get_object_or_404(Divida, pk=pk)
    divida.atualizar_status()
    parcelas = divida.parcelas.all()
    return render(request, 'dividas/detalhe.html', {
        'divida': divida,
        'parcelas': parcelas,
    })


@login_required
def nova(request):
    form = DividaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        divida = form.save()
        divida.atualizar_status()
        success_message(request, 'Dívida cadastrada.')
        return redirect(reverse('dividas:lista'))
    return render(request, 'generic_form.html', {
        'titulo': 'Nova Dívida',
        'form': form,
        'back_url': reverse('dividas:lista'),
        'icone': 'bi-exclamation-triangle',
    })


@login_required
def editar(request, pk):
    divida = get_object_or_404(Divida, pk=pk)
    form = DividaForm(request.POST or None, instance=divida)
    if request.method == 'POST' and form.is_valid():
        divida = form.save()
        divida.atualizar_status()
        success_message(request, 'Dívida atualizada.')
        return redirect(reverse('dividas:detalhe', args=[divida.pk]))
    return render(request, 'generic_form.html', {
        'titulo': f'Editar: {divida.descricao}',
        'form': form,
        'back_url': reverse('dividas:detalhe', args=[divida.pk]),
        'icone': 'bi-exclamation-triangle',
    })


@login_required
def excluir(request, pk):
    divida = get_object_or_404(Divida, pk=pk)
    if request.method == 'POST':
        divida.delete()
        success_message(request, 'Dívida excluída.')
        return redirect(reverse('dividas:lista'))
    return render(request, 'generic_confirm_delete.html', {
        'objeto': divida,
        'back_url': reverse('dividas:detalhe', args=[divida.pk]),
    })


@login_required
def pagar_parcela(request, pk):
    parcela = get_object_or_404(ParcelaDivida, pk=pk, status='a_pagar')
    if request.method == 'POST':
        parcela.status = 'paga'
        parcela.data_pagamento = timezone.localdate()
        parcela.save(update_fields=['status', 'data_pagamento'])
        divida = parcela.divida
        divida._sync_valores()
        divida.atualizar_status()
        success_message(
            request,
            f'Parcela {parcela.numero} de "{divida.descricao}" paga.',
        )
        destino = request.POST.get('next')
        if not destino or not destino.startswith('/') or destino.startswith('//'):
            destino = reverse('dividas:lista')
        return redirect(destino)
    return redirect(reverse('dividas:lista'))