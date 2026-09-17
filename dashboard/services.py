"""Serviços de consolidação patrimonial para o dashboard."""
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import F, Sum
from django.utils import timezone

from contas.models import Banco, HistoricoContaBancaria
from cartoes.models import CartaoCredito, HistoricoCartao
from cartoes.services import previsao_faturas_fluxo
from contas_periodicas.models import (
    OcorrenciaContaPeriodica,
    OcorrenciaRecebimento,
    PagamentoAvulso,
    RecebimentoAvulso,
)
from cripto.models import Criptomoeda, HistoricoCripto
from dividas.models import Divida, HistoricoDivida, ParcelaDivida
from planejamento.models import AporteMensal
from poupanca.models import ContaPoupanca, HistoricoPoupanca
from renda_fixa.models import AplicacaoCDB, HistoricoCDB
from renda_fixa.services import calcular_valor_bruto
from renda_variavel.models import Ativo, HistoricoAtivo


def total_contas() -> Decimal:
    return Banco.objects.filter(ativo=True).aggregate(t=Sum('saldo_atual'))['t'] or Decimal('0')


def total_poupanca() -> Decimal:
    return ContaPoupanca.objects.filter(ativo=True).aggregate(t=Sum('saldo_atual'))['t'] or Decimal('0')


def total_cdbs_bruto() -> Decimal:
    total = Decimal('0')
    for cdbs in AplicacaoCDB.objects.filter(ativo=True):
        total += calcular_valor_bruto(cdbs, data=date.today())['valor_bruto']
    return total


def total_renda_variavel() -> Decimal:
    return Ativo.objects.filter(ativo=True).aggregate(
        t=Sum(F('preco_atual') * F('quantidade'))
    )['t'] or Decimal('0')


def total_cripto() -> Decimal:
    total = Decimal('0')
    for moeda in Criptomoeda.objects.filter(ativo=True):
        total += moeda.valor_brl
    return total


def total_dividas() -> Decimal:
    return Divida.objects.filter(ativa=True).aggregate(
        t=Sum(F('valor_total') - F('valor_pago'))
    )['t'] or Decimal('0')


def total_faturas_em_aberto() -> Decimal:
    total = Decimal('0')
    for cartao in CartaoCredito.objects.filter(ativo=True):
        total += cartao.saldo_devedor_fatura_atual()
    return total


def total_ativos() -> Decimal:
    return total_contas() + total_poupanca() + total_cdbs_bruto() + total_renda_variavel() + total_cripto()


def total_passivos() -> Decimal:
    return total_dividas() + total_faturas_em_aberto()


def saldo_liquido() -> Decimal:
    return total_ativos() - total_passivos()


def projecao_fluxo_caixa(mes: int | None = None, ano: int | None = None) -> dict:
    """Projeção simples de fluxo de caixa do mês: a pagar vs a receber."""
    hoje = timezone.localdate()
    mes = mes or hoje.month
    ano = ano or hoje.year

    # A pagar: contas periódicas + faturas em aberto no mês
    a_pagar = OcorrenciaContaPeriodica.objects.filter(
        data_vencimento__year=ano, data_vencimento__month=mes
    ).exclude(status='paga').aggregate(t=Sum('valor'))['t'] or Decimal('0')

    infos_pagar_texto = list(
        OcorrenciaContaPeriodica.objects.filter(
            data_vencimento__year=ano, data_vencimento__month=mes
        ).exclude(status='paga').values_list('conta_periodica__descricao', 'valor')
    )

    # Faturas de cartão que impactam o mês (inclui faturas em processamento)
    faturas = previsao_faturas_fluxo(ano, mes)
    a_pagar += sum((f['valor'] for f in faturas), Decimal('0'))
    infos_pagar_texto += [(f'Fatura {f["cartao"].nome}', f['valor']) for f in faturas]

    # Pagamentos avulsos (pontuais) do mês
    a_pagar += PagamentoAvulso.objects.filter(
        data_pagamento__year=ano, data_pagamento__month=mes
    ).exclude(status='pago').aggregate(t=Sum('valor'))['t'] or Decimal('0')
    infos_pagar_texto += list(
        PagamentoAvulso.objects.filter(
            data_pagamento__year=ano, data_pagamento__month=mes
        ).exclude(status='pago').values_list('descricao', 'valor')
    )

    # Parcelas de dívidas marcadas "para pagamento"
    parcelas_dividas = ParcelaDivida.objects.filter(
        divida__para_pagamento=True,
        divida__ativa=True,
        status='a_pagar',
        data_vencimento__year=ano,
        data_vencimento__month=mes,
    )
    a_pagar += parcelas_dividas.aggregate(t=Sum('valor'))['t'] or Decimal('0')
    infos_pagar_texto += list(
        parcelas_dividas.values_list('divida__descricao', 'valor')
    )

    # A receber: recebimentos periódicos + avulsos
    a_receber = OcorrenciaRecebimento.objects.filter(
        data_prevista__year=ano, data_prevista__month=mes
    ).exclude(status='recebido').aggregate(t=Sum('valor'))['t'] or Decimal('0')

    a_receber += RecebimentoAvulso.objects.filter(
        data_prevista__year=ano, data_prevista__month=mes
    ).exclude(status='recebido').aggregate(t=Sum('valor'))['t'] or Decimal('0')

    # Aportes planejados para objetivos refletidos no fluxo
    aportes_fluxo = AporteMensal.objects.filter(
        objetivo__refletir_fluxo=True,
        objetivo__status__in=['planejamento', 'ativo'],
        ano=ano, mes=mes,
    )
    valor_aportes = sum(a.valor_efetivo for a in aportes_fluxo)
    a_pagar += valor_aportes
    infos_pagar_texto += [(f'Objetivo: {a.objetivo.nome}', a.valor_efetivo) for a in aportes_fluxo]

    return {
        'mes': mes,
        'ano': ano,
        'a_pagar': a_pagar,
        'a_receber': a_receber,
        'saldo_projetado': a_receber - a_pagar,
        'itens_a_pagar': infos_pagar_texto,
    }


def evolucao_patrimonial(dias: int = 365) -> dict:
    """Séries temporais do patrimônio líquido e bruto dos últimos N dias."""
    inicio = timezone.now() - timedelta(days=dias)
    dados = {'datas': [], 'patrimonio_liquido': [], 'ativos_totais': [], 'passivos': []}

    # Agrupa por dia usando valores acumulados: usa o snapshot mais recente de cada dia
    def serie(modelo, valores):
        out = {}
        for obj in modelo.objects.filter(criado_em__gte=inicio).order_by('-criado_em'):
            dia = obj.criado_em.date()
            if dia not in out:
                out[dia] = valores(obj)
        return out

    contas_dia = serie(HistoricoContaBancaria, lambda o: o.valor)
    poupanca_dia = serie(HistoricoPoupanca, lambda o: o.valor)
    cdbs_dia = serie(HistoricoCDB, lambda o: o.valor_bruto)
    ativos_dia = serie(HistoricoAtivo, lambda o: o.valor_mercado)
    cripto_dia = serie(HistoricoCripto, lambda o: o.valor_brl)
    dividas_dia = serie(HistoricoDivida, lambda o: o.valor_restante)
    cartoes_dia = serie(HistoricoCartao, lambda o: o.saldo_devedor)

    dias_todos = sorted(set(contas_dia) | set(poupanca_dia) | set(cdbs_dia) | set(ativos_dia) | set(cripto_dia))
    for dia in dias_todos:
        ativos = (
            contas_dia.get(dia, Decimal('0'))
            + poupanca_dia.get(dia, Decimal('0'))
            + cdbs_dia.get(dia, Decimal('0'))
            + ativos_dia.get(dia, Decimal('0'))
            + cripto_dia.get(dia, Decimal('0'))
        )
        passivos = dividas_dia.get(dia, Decimal('0')) + cartoes_dia.get(dia, Decimal('0'))
        dados['datas'].append(dia.strftime('%d/%m'))
        dados['ativos_totais'].append(float(ativos))
        dados['passivos'].append(float(passivos))
        dados['patrimonio_liquido'].append(float(ativos - passivos))
    return dados


def composicao_ativos() -> dict:
    """Composição atual do patrimônio por classe, para gráfico de pizza."""
    return {
        'Contas bancárias': float(total_contas()),
        'Poupança': float(total_poupanca()),
        'Renda fixa (CDB)': float(total_cdbs_bruto()),
        'Renda variável': float(total_renda_variavel()),
        'Cripto': float(total_cripto()),
    }