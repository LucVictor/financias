from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from sistema_financas.helpers import success_message
from .forms import CartaoForm, CompraForm, FaturaPagamentoForm
from .models import CartaoCredito, CompraCartao, FaturaCartao
from .services import faturas_recentes


@login_required
def lista(request):
    cartoes = CartaoCredito.objects.filter(ativo=True)
    total_limites = sum(c.limite_total for c in cartoes)
    total_devedor = sum(c.saldo_devedor_fatura_atual() for c in cartoes)
    return render(request, 'cartoes/lista.html', {
        'cartoes': cartoes,
        'total_limites': total_limites,
        'total_devedor': total_devedor,
    })


@login_required
def novo(request):
    form = CartaoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        success_message(request, 'Cartão cadastrado.')
        return redirect(reverse('cartoes:lista'))
    return render(request, 'generic_form.html', {
        'titulo': 'Novo Cartão de Crédito',
        'form': form,
        'back_url': reverse('cartoes:lista'),
        'icone': 'bi-credit-card',
    })


@login_required
def editar(request, pk):
    cartao = get_object_or_404(CartaoCredito, pk=pk)
    form = CartaoForm(request.POST or None, instance=cartao)
    if request.method == 'POST' and form.is_valid():
        form.save()
        success_message(request, 'Cartão atualizado.')
        return redirect(reverse('cartoes:lista'))
    return render(request, 'generic_form.html', {
        'titulo': f'Editar {cartao.nome}',
        'form': form,
        'back_url': reverse('cartoes:lista'),
        'icone': 'bi-credit-card',
    })


@login_required
def excluir(request, pk):
    cartao = get_object_or_404(CartaoCredito, pk=pk)
    if request.method == 'POST':
        cartao.delete()
        success_message(request, 'Cartão excluído.')
        return redirect(reverse('cartoes:lista'))
    return render(request, 'generic_confirm_delete.html', {
        'objeto': cartao,
        'back_url': reverse('cartoes:lista'),
    })


@login_required
def detalhe(request, pk):
    cartao = get_object_or_404(CartaoCredito, pk=pk)
    faturas = faturas_recentes(cartao, meses=6)
    fatura_selecionada = request.GET.get('fatura')
    compras_mes = None
    total_categoria = None
    if fatura_selecionada:
        ano_s, mes_s = fatura_selecionada.split('-')
        fatura_obj = get_object_or_404(FaturaCartao, cartao=cartao, ano=int(ano_s), mes=int(mes_s))
        compras_mes = fatura_obj.parcelas.select_related('compra').order_by('numero_parcela')
        total_categoria = {}
        for p in compras_mes:
            cat = p.compra.categoria or 'Sem categoria'
            total_categoria[cat] = total_categoria.get(cat, 0) + p.valor

    return render(request, 'cartoes/detalhe.html', {
        'cartao': cartao,
        'faturas': faturas,
        'fatura_selecionada': fatura_selecionada,
        'compras_mes': compras_mes,
        'total_categoria': total_categoria,
    })


@login_required
def nova_compra(request, cartao_pk=None):
    form = CompraForm(request.POST or None)
    if cartao_pk:
        form.fields['cartao'].initial = CartaoCredito.objects.get(pk=cartao_pk)
    if request.method == 'POST' and form.is_valid():
        form.save()
        success_message(request, 'Compra registrada e parcelas geradas.')
        return redirect(reverse('cartoes:detalhe', args=[form.cleaned_data['cartao'].pk]))
    return render(request, 'generic_form.html', {
        'titulo': 'Nova Compra no Cartão',
        'form': form,
        'back_url': reverse('cartoes:lista'),
        'icone': 'bi-bag',
    })


@login_required
def pagar_fatura(request, pk):
    fatura = get_object_or_404(FaturaCartao, pk=pk)
    form = FaturaPagamentoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        fatura.estado = 'paga'
        fatura.data_pagamento = form.cleaned_data['data_pagamento']
        fatura.valor_pago = form.cleaned_data['valor_pago']
        fatura.save()
        # Marca as parcelas da fatura como pagas
        for parcela in fatura.parcelas.all():
            parcela.status = 'paga'
            parcela.save(update_fields=['status'])
        success_message(request, 'Fatura marcada como paga.')
        return redirect(reverse('cartoes:detalhe', args=[fatura.cartao.pk]))
    return render(request, 'generic_form.html', {
        'titulo': f'Pagar fatura {fatura.mes:02d}/{fatura.ano} ({fatura.cartao.nome})',
        'form': form,
        'back_url': reverse('cartoes:detalhe', args=[fatura.cartao.pk]),
        'icone': 'bi-check2-circle',
        'submit_label': 'Quitar fatura',
    })