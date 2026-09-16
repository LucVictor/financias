from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from sistema_financas.helpers import success_message
from .forms import DividaForm
from .models import Divida


@login_required
def lista(request):
    dividas = Divida.objects.filter(ativa=True)
    total_bruto = dividas.aggregate(t=Sum('valor_total'))['t'] or 0
    total_pago = dividas.aggregate(t=Sum('valor_pago'))['t'] or 0
    total_em_aberto = total_bruto - total_pago
    return render(request, 'dividas/lista.html', {
        'dividas': dividas,
        'total_em_aberto': total_em_aberto,
    })


@login_required
def nova(request):
    form = DividaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
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
        form.save()
        success_message(request, 'Dívida atualizada.')
        return redirect(reverse('dividas:lista'))
    return render(request, 'generic_form.html', {
        'titulo': f'Editar: {divida.descricao}',
        'form': form,
        'back_url': reverse('dividas:lista'),
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
        'back_url': reverse('dividas:lista'),
    })