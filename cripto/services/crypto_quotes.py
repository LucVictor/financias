"""
Precificação automática de criptomoedas.

Fonte padrão: CoinGecko (simple/price). Alternativas: Binance (ticker/price) e
CryptoCompare (data/price). Quando o par da moeda não existe direto em real
(ex.: TURBOBRL), buscamos em USD/USDT e convertemos automaticamente para BRL
usando a taxa de câmbio (Frankfurter, com fallback para AwesomeAPI).
"""
import json
import time
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation

from django.utils import timezone

from cripto.models import Criptomoeda, HistoricoCripto

TIMEOUT = 15

_COINGECKO_URL = 'https://api.coingecko.com/api/v3/simple/price'
_BINANCE_URL = 'https://api.binance.com/api/v3/ticker/price'
_CRYPTOCOMPARE_URL = 'https://min-api.cryptocompare.com/data/price'
_FRANKFURTER_URL = 'https://api.frankfurter.dev/v2/rate/USD/BRL'
_AWESOMEAPI_URL = 'https://economia.awesomeapi.com.br/json/last/USD-BRL'

_cambio_cache = {'taxa': None, 'timestamp': 0}
_cambio_ttl = 60 * 20  # 20 minutos


def _get_json(url: str, params: dict | None = None) -> dict:
    """GET e decodifica JSON. Lança ValueError com mensagem amigável em erro de HTTP."""
    if params:
        from urllib.parse import urlencode
        url = f'{url}?{urlencode(params)}'
    requisicao = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (financas-pessoais; contato lucascoding.site)'},
    )
    try:
        with urllib.request.urlopen(requisicao, timeout=TIMEOUT) as resposta:
            return json.loads(resposta.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        corpo = ''
        try:
            corpo = e.read().decode('utf-8')[:300]
        except Exception:
            pass
        raise ValueError(f'API respondeu com erro {e.code}: {corpo[:200]}') from e
    except urllib.error.URLError as e:
        raise ValueError(f'Falha de conexão: {e.reason}') from e


def _decimal(valor) -> Decimal:
    try:
        d = Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f'Valor numérico inválido recebido: {valor!r}') from None
    if not d.is_finite():
        raise ValueError(f'Valor numérico inválido recebido: {valor!r}')
    return d


def _busca_identificador(moeda) -> str:
    return (moeda.id_api or moeda.simbolo).strip()


# ===== Barras de conversão por fonte =====

def _preco_coingecko(moeda) -> tuple[Decimal, Decimal]:
    """Retorna (BRL, USD) direto da CoinGecko (oferece os dois simultaneamente)."""
    id_moeda = _busca_identificador(moeda).lower()
    dados = _get_json(_COINGECKO_URL, {
        'ids': id_moeda,
        'vs_currencies': 'brl,usd',
    })
    item = dados.get(id_moeda)
    if not item:
        raise ValueError(f'Moeda "{id_moeda}" não encontrada na CoinGecko. Confira o campo '
                         '"Identificador na fonte" (ex.: turbo, bitcoin).')
    return _decimal(item.get('brl')), _decimal(item.get('usd'))


def _preco_binance(moeda) -> tuple[Decimal, Decimal]:
    """Retorna (BRL, USD). Binance oferece um único par por chamada: se o par em BRL
    informado não existir, buscamos o par USDT e convertemos via taxa de câmbio."""
    simbolo = _busca_identificador(moeda).upper()
    par = moeda.par_cotacao
    suffixo = 'BRL' if par == 'BRL' else 'USDT'
    simb_par = f'{simbolo}{suffixo}'

    try:
        dados = _get_json(_BINANCE_URL, {'symbol': simb_par})
        preco = _decimal(dados.get('price'))
    except ValueError as e:
        raise ValueError(f'Par {simb_par} indisponível na Binance. {e}') from e

    if par == 'BRL':
        taxa = taxa_cambio_usd_brl()
        brl = preco
        usd = preco / taxa if taxa else None
    else:
        usd = preco
        taxa = taxa_cambio_usd_brl()
        if not taxa:
            raise ValueError('Não foi possível obter o câmbio USD/BRL para converter.')
        brl = usd * taxa
    return brl, usd


def _preco_cryptocompare(moeda) -> tuple[Decimal, Decimal]:
    """Retorna (BRL, USD) direto da CryptoCompare (suporta os dois ao mesmo tempo)."""
    simbolo = _busca_identificador(moeda).upper()
    dados = _get_json(_CRYPTOCOMPARE_URL, {'fsym': simbolo, 'tsyms': 'BRL,USD'})
    if 'BRL' not in dados or 'USD' not in dados:
        raise ValueError(f'Moeda "{simbolo}" não encontrada na CryptoCompare. Confira o '
                         '"Identificador na fonte" (ex.: BTC, TURBO).')
    return _decimal(dados['BRL']), _decimal(dados['USD'])


# ===== Câmbio USD/BRL =====

def taxa_cambio_usd_brl(usar_cache: bool = True) -> Decimal | None:
    """Taxa atual USD→BRL (Frankfurter; fallback AwesomeAPI), com cache de 20 min."""
    agora = time.time()
    if usar_cache and _cambio_cache['taxa'] is not None and agora - _cambio_cache['timestamp'] < _cambio_ttl:
        return _cambio_cache['taxa']

    taxa = None
    try:
        dados = _get_json(_FRANKFURTER_URL)
        taxa = _decimal(dados.get('rate'))
    except ValueError:
        taxa = None
    if taxa is None:
        try:
            dados = _get_json(_AWESOMEAPI_URL)
            taxa = _decimal(dados.get('USDBRL', {}).get('bid'))
        except ValueError:
            taxa = None
    if taxa is None:
        _cambio_cache.update({'taxa': None, 'timestamp': agora})
        return None
    _cambio_cache.update({'taxa': taxa, 'timestamp': agora})
    return taxa


# ===== Precificação =====

def _preco_da_fonte(moeda) -> tuple[Decimal, Decimal]:
    if moeda.fonte_api == 'binance':
        return _preco_binance(moeda)
    if moeda.fonte_api == 'cryptocompare':
        return _preco_cryptocompare(moeda)
    return _preco_coingecko(moeda)


def precificar_moeda(moeda: Criptomoeda) -> dict:
    """Atualiza a cotação de uma moeda via API.

    Retorna dict com 'ok' (bool), 'mensagem' e, em sucesso, 'cotacao_brl'/'cotacao_usd'.
    """
    if not moeda.auto_cotacao:
        return {
            'ok': False,
            'mensagem': f'{moeda.simbolo}: precificação automática está desativada '
                        '(marque "Precificação automática via API").',
        }

    try:
        brl, usd = _preco_da_fonte(moeda)
    except ValueError as e:
        return {'ok': False, 'mensagem': f'{moeda.simbolo}: {e}'}

    if brl is None or usd is None:
        return {'ok': False, 'mensagem': f'{moeda.simbolo}: resposta sem preço válido.'}

    cotacao_btc = moeda.cotacao_btc  # mantém valor atual (cruzamento não é auto-gerado)

    moeda.cotacao_brl = brl
    moeda.cotacao_usd = usd
    moeda.cotacao_btc = cotacao_btc
    moeda.fonte_cotacao = 'api'
    moeda.atualizado_em = timezone.now()
    moeda.save(update_fields=[
        'cotacao_brl', 'cotacao_usd', 'cotacao_btc', 'fonte_cotacao', 'atualizado_em',
    ])
    HistoricoCripto.objects.create(
        moeda=moeda,
        valor_brl=moeda.valor_brl,
        cotacao_brl=moeda.cotacao_brl,
    )
    return {
        'ok': True,
        'mensagem': f'{moeda.simbolo}: cotação atualizada (fonte {moeda.get_fonte_api_display()}).',
        'cotacao_brl': brl,
        'cotacao_usd': usd,
    }


def precificar_auto() -> dict:
    """Atualiza todas as moedas ativas com precificação automática habilitada."""
    moedas = Criptomoeda.objects.filter(ativo=True, auto_cotacao=True)
    if not moedas.exists():
        return {'ok': True, 'mensagem': 'Nenhuma moeda com precificação automática habilitada.'}

    ok = 0
    erros = []
    for moeda in moedas:
        resultado = precificar_moeda(moeda)
        if resultado['ok']:
            ok += 1
        else:
            erros.append(resultado['mensagem'])
    mensagem = f'{ok} moeda(s) atualizada(s).'
    if erros:
        mensagem += ' Erros: ' + ' | '.join(erros)
    return {'ok': ok > 0 or not erros, 'mensagem': mensagem, 'erros': erros}