"""
Geração e atualização das ocorrências de contas periódicas (a pagar) e
recebimentos periódicos, além de atualização de status das pendências.
"""
from datetime import date, timedelta

from django.utils import timezone

from .models import (
    ContaPeriodica,
    OcorrenciaContaPeriodica,
    RecebimentoPeriodico,
    OcorrenciaRecebimento,
    RecebimentoAvulso,
)


def _fim_horizonte(data_base):
    """Final do mês corrente + 2 meses à frente."""
    if data_base.month == 12:
        return date(data_base.year + 1, 2, _ultimo_dia(data_base.year + 1, 2))
    if data_base.month == 11:
        return date(data_base.year, 12, _ultimo_dia(data_base.year, 12))
    return date(data_base.year, data_base.month + 2, _ultimo_dia(data_base.year, data_base.month + 2))


def _ultimo_dia(ano, mes):
    import calendar
    return calendar.monthrange(ano, mes)[1]


def gerar_ocorrencias_conta_periodica(conta: ContaPeriodica, ate: date | None = None):
    """Gera/garante ocorrências de uma conta periódica desde o início do mês corrente
    até o horizonte de 2 meses à frente."""
    hoje = timezone.localdate()
    inicio = hoje.replace(day=1)
    origem = conta._proxima_data(conta.dia_do_mes, base=inicio)
    limite = _fim_horizonte(hoje)
    while origem <= limite:
        OcorrenciaContaPeriodica.objects.get_or_create(
            conta_periodica=conta,
            data_vencimento=origem,
            defaults={'valor': conta.valor_esperado},
        )
        origem = _avancar_recorrencia(conta.recorrência, origem)


def gerar_todas_ocorrencias_contas():
    for conta in ContaPeriodica.objects.filter(ativo=True):
        gerar_ocorrencias_conta_periodica(conta)


def gerar_ocorrencias_recebimento_periodico(recebimento: RecebimentoPeriodico):
    hoje = timezone.localdate()
    inicio = hoje.replace(day=1)
    origem = recebimento._proxima_data(recebimento.dia_do_mes, base=inicio)
    limite = _fim_horizonte(hoje)
    while origem <= limite:
        OcorrenciaRecebimento.objects.get_or_create(
            recebimento_periodico=recebimento,
            data_prevista=origem,
            defaults={'valor': recebimento.valor_esperado},
        )
        origem = _avancar_recorrencia(recebimento.recorrência, origem)


def gerar_todas_ocorrencias_recebimentos():
    for recebimento in RecebimentoPeriodico.objects.filter(ativo=True):
        gerar_ocorrencias_recebimento_periodico(recebimento)


def _avancar_recorrencia(recorrencia, data):
    if recorrencia == 'mensal':
        if data.month == 12:
            return date(data.year + 1, 1, min(data.day, _ultimo_dia(data.year + 1, 1)))
        return date(data.year, data.month + 1, min(data.day, _ultimo_dia(data.year, data.month + 1)))
    if recorrencia == 'quinzenal':
        return data + timedelta(days=15)
    if recorrencia == 'semanal':
        return data + timedelta(days=7)
    # anual
    return date(data.year + 1, data.month, min(data.day, _ultimo_dia(data.year + 1, data.month)))


def atualizar_status_das_pendencias():
    hoje = timezone.localdate()
    for ocorrencia in OcorrenciaContaPeriodica.objects.exclude(status='paga'):
        ocorrencia.atualizar_status()
    for ocorrencia in OcorrenciaRecebimento.objects.exclude(status='recebido'):
        ocorrencia.atualizar_status()
    for avulso in RecebimentoAvulso.objects.exclude(status='recebido'):
        avulso.atualizar_status()


def processar_ciclos():
    """Rotina diária: cria ocorrências dos próximos ciclos e atualiza status."""
    gerar_todas_ocorrencias_contas()
    gerar_todas_ocorrencias_recebimentos()
    atualizar_status_das_pendencias()