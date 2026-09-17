from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from sistema_financas.helpers import erro_message, success_message

from .forms import ObjetivoForm
from .models import AporteMensal, ObjetivoFinanceiro
from .services import (
    calcular_aporte_constante,
    criar_agenda,
    dados_grafico_temporal,
    recalcular_agenda,
    saldo_projetado_hoje,
    sincronizar_agenda,
    tabela_simulacao,
)


@login_required
def lista(request):
    objetivos = ObjetivoFinanceiro.objects.all()
    dados = []
    for obj in objetivos:
        projetado = saldo_projetado_hoje(obj)
        pct = min(100, int(projetado / obj.valor_final * 100)) if obj.valor_final else 0
        dados.append({
            'obj': obj,
            'projetado': projetado,
            'pct': pct,
        })
    return render(request, 'planejamento/lista.html', {'dados': dados})


@login_required
def novo(request):
    form = ObjetivoForm(request.POST or None, initial={
        'data_inicio': timezone.localdate(),
        'taxa_rendimento_pct': 0,
    })
    if request.method == 'POST' and form.is_valid():
        objetivo = form.save()
        criar_agenda(objetivo)
        success_message(request, f'Objetivo "{objetivo.nome}" criado com {objetivo.numero_meses} aportes.')
        return redirect(reverse('planejamento:detalhe', args=[objetivo.pk]))
    return render(request, 'generic_form.html', {
        'titulo': 'Novo Objetivo Financeiro',
        'form': form,
        'back_url': reverse('planejamento:lista'),
        'icone': 'bi-bullseye',
    })


@login_required
def editar(request, pk):
    objetivo = get_object_or_404(ObjetivoFinanceiro, pk=pk)
    form = ObjetivoForm(request.POST or None, instance=objetivo)
    if request.method == 'POST' and form.is_valid():
        objetivo = form.save()
        sincronizar_agenda(objetivo)
        recalcular_agenda(objetivo)
        success_message(request, f'Objetivo "{objetivo.nome}" atualizado.')
        return redirect(reverse('planejamento:detalhe', args=[objetivo.pk]))
    return render(request, 'generic_form.html', {
        'titulo': f'Editar {objetivo.nome}',
        'form': form,
        'back_url': reverse('planejamento:detalhe', args=[objetivo.pk]),
        'icone': 'bi-bullseye',
    })


@login_required
def detalhe(request, pk):
    objetivo = get_object_or_404(ObjetivoFinanceiro, pk=pk)
    tabela = tabela_simulacao(objetivo)
    projetado = saldo_projetado_hoje(objetivo)
    pmt = calcular_aporte_constante(
        objetivo.valor_final, objetivo.valor_inicial,
        objetivo.taxa_mensal, objetivo.numero_meses,
    )
    hoje = date.today()
    total_realizado = sum(
        a.valor_efetivo for a in objetivo.aportes_mensais.filter(realizado=True)
    )
    return render(request, 'planejamento/detalhe.html', {
        'objetivo': objetivo,
        'tabela': tabela,
        'projetado': projetado,
        'pmt': pmt,
        'hoje': hoje,
        'total_realizado': total_realizado,
        'grafico': dados_grafico_temporal(objetivo),
    })


@login_required
def editar_aporte(request, pk, aporte_pk):
    objetivo = get_object_or_404(ObjetivoFinanceiro, pk=pk)
    aporte = get_object_or_404(AporteMensal, pk=aporte_pk, objetivo=objetivo)
    if request.method == 'POST':
        try:
            valor = float(request.POST.get('valor', 0))
            aporte.valor = valor
            aporte.manual = True
            aporte.descricao = request.POST.get('descricao', '')
            aporte.save(update_fields=['valor', 'manual', 'descricao'])
            recalcular_agenda(objetivo)
            success_message(request, f'Aporte {aporte.mes:02d}/{aporte.ano} atualizado.')
        except (ValueError, TypeError):
            erro_message(request, 'Valor inválido.')
    return redirect(reverse('planejamento:detalhe', args=[objetivo.pk]))


@login_required
def realizar_aporte(request, pk):
    objetivo = get_object_or_404(ObjetivoFinanceiro, pk=pk)
    if request.method == 'POST':
        try:
            valor = Decimal(request.POST.get('valor', 0))
            mes = int(request.POST.get('mes'))
            ano = int(request.POST.get('ano'))
            descricao = request.POST.get('descricao', '')

            aporte, created = AporteMensal.objects.get_or_create(
                objetivo=objetivo, ano=ano, mes=mes,
                defaults={'valor': 0},
            )
            aporte.valor_realizado = valor
            aporte.data_realizado = timezone.localdate()
            aporte.realizado = True
            aporte.descricao = descricao
            aporte.save(update_fields=[
                'valor_realizado', 'data_realizado', 'realizado', 'descricao',
            ])
            recalcular_agenda(objetivo)
            success_message(request, f'Aporte realizado: R$ {valor} em {mes:02d}/{ano}.')
        except (ValueError, TypeError) as e:
            erro_message(request, f'Erro ao registrar aporte: {e}')
    return redirect(reverse('planejamento:detalhe', args=[objetivo.pk]))


@login_required
def alternar_fluxo(request, pk):
    objetivo = get_object_or_404(ObjetivoFinanceiro, pk=pk)
    if request.method == 'POST':
        objetivo.refletir_fluxo = not objetivo.refletir_fluxo
        if objetivo.refletir_fluxo and objetivo.status == 'planejamento':
            objetivo.status = 'ativo'
        elif not objetivo.refletir_fluxo and objetivo.status == 'ativo':
            objetivo.status = 'planejamento'
        objetivo.save(update_fields=['refletir_fluxo', 'status'])
        msg = 'Objetivo refletido no fluxo de caixa.' if objetivo.refletir_fluxo else 'Objetivo removido do fluxo.'
        success_message(request, msg)
    return redirect(reverse('planejamento:detalhe', args=[objetivo.pk]))


@login_required
def concluir(request, pk):
    objetivo = get_object_or_404(ObjetivoFinanceiro, pk=pk)
    if request.method == 'POST':
        objetivo.status = 'concluido'
        objetivo.refletir_fluxo = False
        objetivo.save(update_fields=['status', 'refletir_fluxo'])
        success_message(request, f'Objetivo "{objetivo.nome}" concluído!')
    return redirect(reverse('planejamento:detalhe', args=[objetivo.pk]))


@login_required
def excluir(request, pk):
    objetivo = get_object_or_404(ObjetivoFinanceiro, pk=pk)
    if request.method == 'POST':
        nome = objetivo.nome
        objetivo.delete()
        success_message(request, f'Objetivo "{nome}" excluído.')
        return redirect(reverse('planejamento:lista'))
    return render(request, 'generic_confirm_delete.html', {
        'objeto': objetivo,
        'back_url': reverse('planejamento:detalhe', args=[objetivo.pk]),
    })
