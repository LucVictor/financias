"""Garantia de faturas e vinculação de parcelas a elas."""
from datetime import date
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from .models import CartaoCredito, FaturaCartao, ParcelaCompra


def mes_para_data(ano, mes):
    try:
        return date(ano, mes, 1)
    except ValueError:
        return timezone.localdate()


def proximo_mes(ano, mes, delta):
    m = mes + delta
    while m > 12:
        m -= 12
        ano += 1
    while m < 1:
        m += 12
        ano -= 1
    return ano, m


def get_or_create_fatura(cartao, ano, mes):
    fatura, _ = FaturaCartao.objects.get_or_create(cartao=cartao, ano=ano, mes=mes)
    fatura.parcelas.set(ParcelaCompra.objects.filter(ano=ano, mes=mes, compra__cartao=cartao))
    fatura.parcelas.filter(compra__cancelada=True).update(status='paga')
    fatura.atualizar_total()
    return fatura


def faturas_recentes(cartao, meses=6):
    """Retorna lista de faturas para os últimos `meses` meses + o atual.

    Faturas passadas sem valores (total zero, ex.: cartão recém-criado) são
    consideradas pagas, para não aparecerem como atrasadas. Se depois uma
    fatura passada ganhar parcelas não pagas, volta a ser atrasada.
    """
    hoje = timezone.localdate()
    resultado = []
    for i in range(meses - 1, -1, -1):
        ano, mes = proximo_mes(hoje.year, hoje.month, -i)
        fatura = get_or_create_fatura(cartao, ano, mes)
        if fatura.data_vencimento < hoje:
            if fatura.parcelas.exclude(status='paga').exists():
                fatura.estado = 'atrasada'
            else:
                fatura.estado = 'paga'
            fatura.save(update_fields=['estado'])
        resultado.append(fatura)
    return resultado


def previsao_faturas_fluxo(ano, mes):
    """Faturas de cartão que impactam o fluxo de caixa do mês (a pagar).

    Para cada cartão ativo soma o valor das parcelas ainda não pagas do mês
    (ano/mes) e devolve uma lista ordenada por vencimento, com a situação:
    'em_processamento' (ainda não fechou), 'fechada', 'atrasada' ou 'futura'.
    """
    hoje = timezone.localdate()
    resultado = []
    for cartao in CartaoCredito.objects.filter(ativo=True):
        total = (
            ParcelaCompra.objects.filter(
                Q(compra__cartao=cartao)
                & Q(compra__cancelada=False)
                & ~Q(status='paga'),
                ano=ano,
                mes=mes,
            ).aggregate(t=Sum('valor'))['t'] or Decimal('0')
        )
        if total == 0:
            continue

        data_vencimento = date(ano, mes, cartao.dia_vencimento)

        if ano < hoje.year or (ano == hoje.year and mes < hoje.month):
            situacao = 'atrasada'
        elif ano == hoje.year and mes == hoje.month and hoje.day >= cartao.dia_fechamento:
            situacao = 'fechada'
        elif ano == hoje.year and mes == hoje.month:
            situacao = 'em_processamento'
        else:
            situacao = 'futura'

        resultado.append({
            'cartao': cartao,
            'valor': total,
            'data_vencimento': data_vencimento,
            'situacao': situacao,
        })

    resultado.sort(key=lambda x: x['data_vencimento'])
    return resultado