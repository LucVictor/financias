"""Simulação e cálculos para planejamento de objetivos financeiros."""
from datetime import date
from decimal import Decimal

from .models import AporteMensal, ObjetivoFinanceiro


def meses_entre(data_inicio: date, data_fim: date) -> int:
    """Número de meses (inclusivo) entre duas datas."""
    return (data_fim.year - data_inicio.year) * 12 + (data_fim.month - data_inicio.month) + 1


def calcular_aporte_constante(
    valor_final: Decimal,
    valor_inicial: Decimal,
    taxa_mensal: Decimal,
    n_meses: int,
) -> Decimal:
    """Calcula aporte mensal constante (postnumerando) para atingir valor_final.

    FV = PV*(1+i)^N + PMT * [((1+i)^N - 1) / i]
    PMT = (FV - PV*(1+i)^N) * i / ((1+i)^N - 1)
    """
    if n_meses <= 0:
        return Decimal('0')

    if taxa_mensal == 0:
        necessario = valor_final - valor_inicial
        if necessario <= 0:
            return Decimal('0')
        return necessario / Decimal(n_meses)

    i = taxa_mensal
    fator = (1 + i) ** n_meses
    pv_futuro = valor_inicial * fator
    necessario = valor_final - pv_futuro

    if necessario <= 0:
        return Decimal('0')

    denominador = (fator - 1) / i
    pmt = necessario / denominador
    return pmt.quantize(Decimal('0.01'))


def criar_agenda(objetivo: ObjetivoFinanceiro) -> None:
    """Cria agenda de aportes mensais com valor constante."""
    pmt = calcular_aporte_constante(
        objetivo.valor_final,
        objetivo.valor_inicial,
        objetivo.taxa_mensal,
        objetivo.numero_meses,
    )
    data = objetivo.data_inicio
    fim = objetivo.data_conclusao
    aportes = []
    while data <= fim:
        aportes.append(AporteMensal(
            objetivo=objetivo,
            ano=data.year,
            mes=data.month,
            valor=pmt,
        ))
        if data.month == 12:
            data = date(data.year + 1, 1, 1)
        else:
            data = date(data.year, data.month + 1, 1)
    AporteMensal.objects.filter(objetivo=objetivo).exclude(
        realizado=True, valor_realizado__isnull=False
    ).delete()
    AporteMensal.objects.bulk_create(aportes, ignore_conflicts=True)


def sincronizar_agenda(objetivo: ObjetivoFinanceiro) -> None:
    """Garante que todos os meses do período tenham linha de aporte (cria faltantes)."""
    existentes = {
        (a.ano, a.mes)
        for a in objetivo.aportes_mensais.all()
    }
    data = objetivo.data_inicio
    fim = objetivo.data_conclusao
    novos = []
    while data <= fim:
        if (data.year, data.month) not in existentes:
            novos.append(AporteMensal(
                objetivo=objetivo,
                ano=data.year,
                mes=data.month,
                valor=Decimal('0'),
            ))
        if data.month == 12:
            data = date(data.year + 1, 1, 1)
        else:
            data = date(data.year, data.month + 1, 1)
    if novos:
        AporteMensal.objects.bulk_create(novos)


def recalcular_agenda(objetivo: ObjetivoFinanceiro) -> None:
    """Recalcula aportes futuros não-manualizados, congelando passados/realizados.

    Trata meses congelados intercalados entre meses futuros: o aporte de cada
    mês futuro capitaliza (1+i)^(N-j) independentemente da posição.
    """
    hoje = date.today()
    aportes = list(objetivo.aportes_mensais.order_by('ano', 'mes'))
    i = objetivo.taxa_mensal
    n = objetivo.numero_meses

    fixos = Decimal('0')
    soma_fatores_futuros = Decimal('0')

    for a in aportes:
        data_aporte = date(a.ano, a.mes, 1)
        is_congelado = (
            data_aporte < date(hoje.year, hoje.month, 1)
            or a.realizado
            or a.manual
        )
        exponente = max(0, meses_entre(data_aporte, objetivo.data_conclusao) - 1)
        if is_congelado:
            fixos += a.valor_efetivo * (1 + i) ** exponente
        else:
            soma_fatores_futuros += (1 + i) ** exponente

    pv_futuro = objetivo.valor_inicial * (1 + i) ** n
    necessario = objetivo.valor_final - pv_futuro - fixos

    pmt = (necessario / soma_fatores_futuros) if (
        soma_fatores_futuros > 0 and necessario > 0
    ) else Decimal('0')
    pmt = pmt.quantize(Decimal('0.01'))

    for a in aportes:
        data_aporte = date(a.ano, a.mes, 1)
        is_congelado = (
            data_aporte < date(hoje.year, hoje.month, 1)
            or a.realizado
            or a.manual
        )
        if not is_congelado:
            a.valor = pmt
            a.save(update_fields=['valor'])


def tabela_simulacao(objetivo: ObjetivoFinanceiro) -> list[dict]:
    """Retorna lista de dicts com simulação mês a mês."""
    hoje = date.today()
    saldo = objetivo.valor_inicial
    i = objetivo.taxa_mensal
    tabela = []

    aportes_por_mes = {
        (a.ano, a.mes): a
        for a in objetivo.aportes_mensais.order_by('ano', 'mes')
    }

    data = objetivo.data_inicio
    fim = objetivo.data_conclusao

    while data <= fim:
        saldo_inicio = saldo
        rendimento = saldo_inicio * i
        saldo += rendimento

        chave = (data.year, data.month)
        aporte_obj = aportes_por_mes.get(chave)

        if aporte_obj:
            aporte_valor = aporte_obj.valor_efetivo
            is_realizado = aporte_obj.realizado
            is_manual = aporte_obj.manual
            descricao = aporte_obj.descricao
        else:
            aporte_valor = Decimal('0')
            is_realizado = False
            is_manual = False
            descricao = ''

        saldo += aporte_valor

        is_passado = data < date(hoje.year, hoje.month, 1)

        tabela.append({
            'ano': data.year,
            'mes': data.month,
            'saldo_inicio': saldo_inicio.quantize(Decimal('0.01')),
            'rendimento': rendimento.quantize(Decimal('0.01')),
            'aporte': aporte_valor.quantize(Decimal('0.01')),
            'saldo_final': saldo.quantize(Decimal('0.01')),
            'realizado': is_realizado,
            'manual': is_manual,
            'passado': is_passado,
            'descricao': descricao,
            'aporte_obj': aporte_obj,
        })

        if data.month == 12:
            data = date(data.year + 1, 1, 1)
        else:
            data = date(data.year, data.month + 1, 1)

    return tabela


def saldo_projetado_hoje(objetivo: ObjetivoFinanceiro) -> Decimal:
    """Saldo projetado do objetivo na data atual (para cards)."""
    tabela = tabela_simulacao(objetivo)
    hoje = date.today()
    for linha in reversed(tabela):
        if date(linha['ano'], linha['mes'], 1) <= date(hoje.year, hoje.month, 1):
            return linha['saldo_final']
    return objetivo.valor_inicial


def dados_grafico_temporal(objetivo: ObjetivoFinanceiro) -> dict:
    """Séries para o gráfico de linha do tempo: realizados, restantes,
    rendimentos e saldo acumulado, mês a mês (mesmo mês atual e futuros)."""
    tabela = tabela_simulacao(objetivo)
    rotulos = []
    realizados = []
    restantes = []
    rendimentos = []
    saldos = []
    for linha in tabela:
        rotulos.append(f"{linha['mes']:02d}/{linha['ano']}")
        if linha['realizado']:
            realizados.append(float(linha['aporte']))
            restantes.append(0.0)
        else:
            realizados.append(0.0)
            restantes.append(float(linha['aporte']))
        rendimentos.append(float(linha['rendimento']))
        saldos.append(float(linha['saldo_final']))
    return {
        'rotulos': rotulos,
        'realizados': realizados,
        'restantes': restantes,
        'rendimentos': rendimentos,
        'saldos': saldos,
    }
