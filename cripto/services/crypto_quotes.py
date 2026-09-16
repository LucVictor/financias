"""
Serviço de cotações de criptomoedas.

Hoje apenas lê a cotação inserida manualmente no banco, mas já está desacoplado
das views. No futuro, a função `get_cotacao_brl` pode consultar uma API real
(CoinGecko, Binance etc.) sem quebrar a estrutura existente.
"""
from decimal import Decimal

from cripto.models import Criptomoeda


def get_cotacao_brl(simbolo: str) -> Decimal:
    """Retorna a cotação em BRL de uma moeda (leitura manual, por enquanto)."""
    moeda = Criptomoeda.objects.get(simbolo__iexact=simbolo)
    return moeda.cotacao_brl


def get_cotacao_usd(simbolo: str) -> Decimal:
    """Retorna a cotação em USD de uma moeda (leitura manual, por enquanto)."""
    moeda = Criptomoeda.objects.get(simbolo__iexact=simbolo)
    return moeda.cotacao_usd


def get_cotacao_btc(simbolo: str) -> Decimal | None:
    """Retorna a cotação em BTC (válida apenas para moedas sem par direto contra BTC)."""
    moeda = Criptomoeda.objects.get(simbolo__iexact=simbolo)
    return moeda.cotacao_btc


def valor_carteira_brl() -> Decimal:
    """Soma do valor (BRL) de todas as moedas ativas."""
    total = Decimal('0')
    for moeda in Criptomoeda.objects.filter(ativo=True):
        total += moeda.valor_brl
    return total