"""Snapshot do histórico de todos os módulos (valor atual de cada item ativo)."""
from datetime import date
from decimal import Decimal
from django.utils import timezone

from contas.models import Banco, HistoricoContaBancaria
from cartoes.models import CartaoCredito, HistoricoCartao
from dividas.models import Divida, HistoricoDivida
from poupanca.models import ContaPoupanca, HistoricoPoupanca
from renda_fixa.models import AplicacaoCDB, HistoricoCDB
from renda_fixa.services import calcular_valor_bruto
from renda_variavel.models import Ativo, HistoricoAtivo
from cripto.models import Criptomoeda, HistoricoCripto
from cripto.services.crypto_quotes import valor_carteira_brl


def snapshot_contas():
    for banco in Banco.objects.filter(ativo=True):
        HistoricoContaBancaria.objects.create(banco=banco, valor=banco.saldo_atual, descricao='Snapshot automático')


def snapshot_cartoes():
    for cartao in CartaoCredito.objects.filter(ativo=True):
        HistoricoCartao.objects.create(
            cartao=cartao,
            limite_disponivel=cartao.limite_disponivel(),
            saldo_devedor=cartao.saldo_devedor_fatura_atual(),
        )


def snapshot_dividas():
    for divida in Divida.objects.filter(ativa=True):
        divida.atualizar_status()
        HistoricoDivida.objects.create(divida=divida, valor_restante=divida.valor_restante, descricao='Snapshot automático')


def snapshot_poupanca():
    for conta in ContaPoupanca.objects.filter(ativo=True):
        HistoricoPoupanca.objects.create(conta=conta, valor=conta.saldo_atual, descricao='Snapshot automático')


def snapshot_cdbs():
    for cdbs in AplicacaoCDB.objects.filter(ativo=True):
        dados = calcular_valor_bruto(cdbs, data=date.today())
        HistoricoCDB.objects.create(
            aplicacao=cdbs,
            valor_bruto=dados['valor_bruto'],
            valor_liquido=dados['valor_liquido'],
            dias_uteis=dados['dias_uteis'],
        )


def snapshot_ativos():
    for ativo in Ativo.objects.filter(ativo=True):
        HistoricoAtivo.objects.create(ativo=ativo, valor_mercado=ativo.valor_mercado, preco=ativo.preco_atual)


def snapshot_cripto():
    for moeda in Criptomoeda.objects.filter(ativo=True):
        HistoricoCripto.objects.create(moeda=moeda, valor_brl=moeda.valor_brl, cotacao_brl=moeda.cotacao_brl)


def gerar_todos_os_snapshots():
    """Gera um snapshot de todos os módulos ativos."""
    snapshot_contas()
    snapshot_cartoes()
    snapshot_dividas()
    snapshot_poupanca()
    snapshot_cdbs()
    snapshot_ativos()
    snapshot_cripto()
    return True