from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from sistema_financas.helpers import erro_message, success_message
from .forms import CartaoForm, CompraForm, FaturaPagamentoForm
from .models import CartaoCredito, CompraCartao, FaturaCartao
from .services import faturas_recentes, get_or_create_fatura


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
    compras_da_fatura = None
    total_categoria = None
    if fatura_selecionada:
        ano_s, mes_s = fatura_selecionada.split('-')
        fatura_obj = get_or_create_fatura(cartao, int(ano_s), int(mes_s))
        compras_mes = fatura_obj.parcelas.select_related('compra').order_by('numero_parcela')
        total_categoria = {}
        for p in compras_mes:
            cat = p.compra.categoria or 'Sem categoria'
            total_categoria[cat] = total_categoria.get(cat, 0) + p.valor
        compras_da_fatura = []
        for c in (
            CompraCartao.objects
            .filter(parcelas__fatura=fatura_obj)
            .distinct()
            .prefetch_related('parcelas')
            .order_by('data_compra', 'id')
        ):
            parcelas = list(c.parcelas.all())
            compras_da_fatura.append({
                'compra': c,
                'paga': bool(parcelas) and all(p.status == 'paga' for p in parcelas),
            })

    return render(request, 'cartoes/detalhe.html', {
        'cartao': cartao,
        'faturas': faturas,
        'fatura_selecionada': fatura_selecionada,
        'compras_mes': compras_mes,
        'compras_da_fatura': compras_da_fatura,
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
def editar_compra(request, pk):
    compra = get_object_or_404(CompraCartao, pk=pk)
    origem = {
        'forma_pagamento': compra.forma_pagamento,
        'num_parcelas': compra.num_parcelas,
        'valor_total': compra.valor_total,
        'data_compra': compra.data_compra,
        'valor_parcela': compra.valor_parcela,
    }
    form = CompraForm(request.POST or None, instance=compra)
    form.fields['cartao'].disabled = True
    if request.method == 'POST' and form.is_valid():
        nova = form.save(commit=False)
        pagas = nova.parcelas.filter(status='paga').count()
        if pagas > nova.num_parcelas:
            erro_message(
                request,
                f'Esta compra já tem {pagas} parcela(s) paga(s); '
                'o número de parcelas não pode ser reduzido abaixo disso.',
            )
        else:
            estrutura_mudou = any([
                nova.forma_pagamento != origem['forma_pagamento'],
                nova.num_parcelas != origem['num_parcelas'],
                nova.valor_total != origem['valor_total'],
                nova.data_compra != origem['data_compra'],
                nova.valor_parcela != origem['valor_parcela'],
            ])
            if estrutura_mudou:
                if nova.forma_pagamento == 'avista':
                    nova.valor_parcela = nova.valor_total
                elif nova.valor_parcela is None or nova.valor_parcela == origem['valor_parcela']:
                    nova.valor_parcela = nova.valor_total / max(nova.num_parcelas, 1)
            nova.save()
            if estrutura_mudou:
                meses_impactados = nova.regerar_parcelas()
                for ano, mes in meses_impactados:
                    get_or_create_fatura(nova.cartao, ano, mes)
            success_message(request, 'Compra atualizada e parcelas recalculadas.')
            return redirect(reverse('cartoes:detalhe', args=[nova.cartao.pk]))
    return render(request, 'generic_form.html', {
        'titulo': f'Editar compra: {compra.descricao}',
        'form': form,
        'back_url': reverse('cartoes:detalhe', args=[compra.cartao.pk]),
        'icone': 'bi-bag',
        'submit_label': 'Salvar alterações',
    })


@login_required
def excluir_compra(request, pk):
    compra = get_object_or_404(CompraCartao, pk=pk)
    cartao = compra.cartao
    meses_impactados = {(p.ano, p.mes) for p in compra.parcelas.all()}
    if request.method == 'POST':
        compra.delete()
        for ano, mes in meses_impactados:
            get_or_create_fatura(cartao, ano, mes)
        success_message(request, 'Compra excluída e faturas atualizadas.')
        return redirect(reverse('cartoes:detalhe', args=[cartao.pk]))
    return render(request, 'generic_confirm_delete.html', {
        'objeto': compra,
        'back_url': reverse('cartoes:detalhe', args=[cartao.pk]),
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
        'confirm_submit': 'Confirmar quitação da fatura? As parcelas serão marcadas como pagas.',
    })