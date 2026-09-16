from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from sistema_financas.helpers import success_message
from .forms import AplicacaoCDBForm, TaxaCDIForm
from .models import AplicacaoCDB, TaxaCDI
from .services import calcular_projecao_vencimento, calcular_valor_bruto, taxa_cdi_vigente


@login_required
def lista(request):
    aplicacoes = AplicacaoCDB.objects.filter(ativo=True).order_by('data_vencimento')
    cdi = taxa_cdi_vigente()

    com_valores = []
    total_bruto = 0
    total_liquido = 0
    total_investido = 0
    for a in aplicacoes:
        atual = calcular_valor_bruto(a)
        projecao = calcular_projecao_vencimento(a)
        total_investido += a.valor_aplicado
        total_bruto += atual['valor_bruto']
        total_liquido += atual['valor_liquido']
        com_valores.append({
            'aplicacao': a,
            'atual': atual,
            'projecao': projecao,
        })

    taxas = TaxaCDI.objects.all().order_by('-data_inicio')[:5]
    return render(request, 'renda_fixa/lista.html', {
        'aplicacoes': com_valores,
        'cdi': cdi,
        'taxas': taxas,
        'total_investido': total_investido,
        'total_bruto': total_bruto,
        'total_liquido': total_liquido,
    })


@login_required
def nova_aplicacao(request):
    form = AplicacaoCDBForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        success_message(request, 'CDB cadastrado.')
        return redirect(reverse('renda_fixa:lista'))
    return render(request, 'generic_form.html', {
        'titulo': 'Nova Aplicação de CDB',
        'form': form,
        'back_url': reverse('renda_fixa:lista'),
        'icone': 'bi-building',
    })


@login_required
def editar_aplicacao(request, pk):
    aplicacao = get_object_or_404(AplicacaoCDB, pk=pk)
    form = AplicacaoCDBForm(request.POST or None, instance=aplicacao)
    if request.method == 'POST' and form.is_valid():
        form.save()
        success_message(request, 'CDB atualizado.')
        return redirect(reverse('renda_fixa:lista'))
    return render(request, 'generic_form.html', {
        'titulo': f'Editar {aplicacao.instituicao}',
        'form': form,
        'back_url': reverse('renda_fixa:lista'),
        'icone': 'bi-building',
    })


@login_required
def excluir_aplicacao(request, pk):
    aplicacao = get_object_or_404(AplicacaoCDB, pk=pk)
    if request.method == 'POST':
        aplicacao.delete()
        success_message(request, 'CDB excluído.')
        return redirect(reverse('renda_fixa:lista'))
    return render(request, 'generic_confirm_delete.html', {
        'objeto': aplicacao,
        'back_url': reverse('renda_fixa:lista'),
    })


@login_required
def nova_taxa(request):
    form = TaxaCDIForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        success_message(request, 'Taxa CDI registrada como vigente.')
        return redirect(reverse('renda_fixa:lista'))
    return render(request, 'generic_form.html', {
        'titulo': 'Registrar Taxa CDI',
        'form': form,
        'back_url': reverse('renda_fixa:lista'),
        'icone': 'bi-percent',
    })