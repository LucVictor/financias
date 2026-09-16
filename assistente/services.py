"""
Assistente de IA: monta um contexto detalhado das finanças do usuário (a partir
do banco de dados) e conversa com um modelo OpenAI-compatível (API Maritaca).

Configuração via variáveis de ambiente:
- MARITACA_API_KEY      chave da API (obrigatória para conversar)
- MARITACA_BASE_URL     padrão: https://chat.maritaca.ai/api
- MARITACA_MODEL        padrão: sabia-4
- MARITACA_MAX_TOKENS   máximo de tokens na resposta (padrão: 2048)
"""
import json
import os
import urllib.error
import urllib.request
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from cartoes.models import CartaoCredito
from cartoes.services import faturas_recentes, previsao_faturas_fluxo
from contas.models import Banco, Movimentacao
from contas_periodicas.models import (
    OcorrenciaContaPeriodica,
    OcorrenciaRecebimento,
    PagamentoAvulso,
    RecebimentoAvulso,
)
from cripto.models import Criptomoeda
from dividas.models import Divida, ParcelaDivida
from poupanca.models import ContaPoupanca
from renda_fixa.models import AplicacaoCDB
from renda_fixa.services import calcular_valor_bruto
from renda_variavel.models import Ativo, ProventoRecebido


def _br(numero) -> str:
    """Formata decimal como R$ 1.234,56 (sem sufixo R$)."""
    valor = Decimal(numero or 0).quantize(Decimal('0.01'))
    negativo = valor < 0
    inteiro = str(int(abs(valor)))
    inteiro = f'{int(inteiro):,}'.replace(',', '.')
    partes = f'{abs(valor):.2f}'.split('.')
    return ('-' if negativo else '') + f'{inteiro},{partes[1]}'


def _duracao(data):
    hoje = timezone.localdate()
    dias = (data - hoje).days
    if dias < 0:
        return f'{abs(dias)} dias atrás'
    if dias == 0:
        return 'hoje'
    if dias == 1:
        return 'amanhã'
    return f'em {dias} dias'


def _contexto_patrimonio():
    linhas = []
    total_ativo = Decimal('0')
    for banco in Banco.objects.filter(ativo=True).order_by('nome'):
        total_ativo += banco.saldo_atual
        linhas.append(f'- {banco.nome} ({banco.get_tipo_conta_display()}): R$ {_br(banco.saldo_atual)}')
    for poupanca in ContaPoupanca.objects.filter(ativo=True).order_by('nome'):
        total_ativo += poupanca.saldo_atual
        linhas.append(f'- Poupança {poupanca.nome} ({poupanca.instituicao or "instituição não informada"}): '
                      f'R$ {_br(poupanca.saldo_atual)}')
    for aplicacao in AplicacaoCDB.objects.filter(ativo=True).order_by('data_vencimento'):
        bruto = calcular_valor_bruto(aplicacao)['valor_bruto']
        total_ativo += bruto
        cdi = aplicacao.percentual_cdi
        linhas.append(
            f'- CDB {aplicacao.instituicao}: aplicado R$ {_br(aplicacao.valor_aplicado)}, '
            f'bruto hoje R$ {_br(bruto)}, vence {aplicacao.data_vencimento:%d/%m/%Y}, {cdi}% do CDI'
        )
    for ativo in Ativo.objects.filter(ativo=True).order_by('ticker'):
        valor = ativo.valor_mercado
        total_ativo += valor
        proventos = ativo.proventos_mensais_estimados()
        linhas.append(
            f'- {ativo.ticker} ({ativo.get_tipo_display()}): {ativo.quantidade} cotas '
            f'a R$ {_br(ativo.preco_atual)} = R$ {_br(valor)} '
            f'(preço médio R$ {_br(ativo.preco_medio)})'
            f"{f', proventos mensais est. R$ {_br(proventos)}' if proventos else ''}"
        )
    for moeda in Criptomoeda.objects.filter(ativo=True).order_by('simbolo'):
        total_ativo += moeda.valor_brl
        linhas.append(
            f'- Cripto {moeda.nome} ({moeda.simbolo}): {moeda.quantidade} unidades '
            f'a R$ {_br(moeda.cotacao_brl)} = R$ {_br(moeda.valor_brl)}'
        )

    total_passivo = Decimal('0')
    passivos = []
    for divida in Divida.objects.filter(ativa=True).order_by('data_vencimento'):
        total_passivo += divida.valor_restante
        passivos.append(
            f'- Dívida {divida.descricao} (credor: {divida.credor or "não informado"}): '
            f'R$ {_br(divida.valor_restante)} restantes em {divida.parcelas_restantes} parcela(s), '
            f'status {divida.get_status_display()}'
        )
    faturas = 0
    for cartao in CartaoCredito.objects.filter(ativo=True).order_by('nome'):
        faturas += cartao.saldo_devedor_fatura_atual()
    if faturas:
        total_passivo += faturas
        passivos.append(f'- Faturas de cartão em aberto: R$ {_br(faturas)}')

    contexto = [
        '== PATRIMÔNIO ==',
        f'Total de ativos: R$ {_br(total_ativo)}',
        f'Total de passivos (dívidas + faturas): R$ {_br(total_passivo)}',
        f'Patrimônio líquido: R$ {_br(total_ativo - total_passivo)}',
    ]
    contexto.append('Ativos em detalhe:')
    contexto.extend(linhas)
    contexto.append('Passivos em detalhe:')
    contexto.extend(passivos)
    return '\n'.join(contexto)


def _contexto_cartoes():
    linhas = []
    for cartao in CartaoCredito.objects.filter(ativo=True).order_by('nome'):
        comprometido = cartao.valor_comprometido()
        linhas.append(
            f'- {cartao.nome} ({cartao.banco_emissor or "emissor não informado"}): '
            f'limite total R$ {_br(cartao.limite_total)}, comprometido R$ {_br(comprometido)}, '
            f'disponível R$ {_br(cartao.limite_disponivel())}, '
            f'fatura atual/vencida R$ {_br(cartao.saldo_devedor_fatura_atual())}'
        )
    return '== CARTÕES DE CRÉDITO ==\n' + ('\n'.join(linhas) if linhas else 'Nenhum cartão cadastrado.')


def _contexto_faturas_proximas():
    hoje = timezone.localdate()
    linhas = []
    for cartao in CartaoCredito.objects.filter(ativo=True).order_by('nome'):
        for fatura in faturas_recentes(cartao, meses=3):
            venc = fatura.data_vencimento
            linhas.append(
                f'- Fatura {fatura.mes:02d}/{fatura.ano} {cartao.nome}: R$ {_br(fatura.valor_total)} '
                f'({fatura.get_estado_display().lower()}), vence {venc:%d/%m/%Y} ({_duracao(venc)})'
            )
    return '== FATURAS DE CARTÃO (3 últimos/correntes) ==\n' + (
        '\n'.join(linhas) if linhas else 'Nenhuma fatura.')


def _contexto_dividas():
    hoje = timezone.localdate()
    linhas = []
    for divida in Divida.objects.filter(ativa=True).order_by('data_vencimento'):
        proxima = divida.proxima_parcela
        venc = proxima.data_vencimento if proxima else None
        atraso = divida.dias_em_atraso
        tracejado = ''
        if divida.para_pagamento:
            tracejado = ' (marcada para pagamento no fluxo)'
        if venc <= hoje:
            linhas.append(
                f'- {divida.descricao}: R$ {_br(divida.valor_restante)} em aberto, '
                f'{atraso} dia(s) de atraso, próxima parcela venceu em {venc:%d/%m/%Y}{tracejado}'
            )
        else:
            linhas.append(
                f'- {divida.descricao}: R$ {_br(divida.valor_restante)} em aberto, '
                f'próxima parcela {venc:%d/%m/%Y} ({_duracao(venc)}){tracejado}'
            )
    proximas = ParcelaDivida.objects.filter(
        status='a_pagar', data_vencimento__gte=hoje,
        divida__ativa=True,
    ).order_by('data_vencimento')[:10]
    contexto = '== DÍVIDAS ==\n' + ('\n'.join(linhas) if linhas else 'Nenhuma dívida ativa.')
    if proximas.exists():
        contexto += '\nPróximas parcelas de dívidas a vencer:\n'
        contexto += '\n'.join(
            f'- {p.divida.descricao} parcela {p.numero}: R$ {_br(p.valor)} '
            f'em {p.data_vencimento:%d/%m/%Y}'
            for p in proximas
        )
    return contexto


def _contexto_fluxo():
    hoje = timezone.localdate()
    fim = hoje + timedelta(days=60)
    linhas = []

    pagar = OcorrenciaContaPeriodica.objects.filter(
        data_vencimento__gte=hoje, data_vencimento__lte=fim,
    ).exclude(status='paga').select_related('conta_periodica').order_by('data_vencimento')
    if pagar.exists():
        linhas.append('Contas periódicas a pagar:')
        linhas.extend(
            f'- {o.conta_periodica.descricao}: R$ {_br(o.valor)} em {o.data_vencimento:%d/%m/%Y}'
            for o in pagar
        )

    avulsos = PagamentoAvulso.objects.filter(
        data_pagamento__gte=hoje, data_pagamento__lte=fim,
    ).exclude(status='pago').order_by('data_pagamento')
    if avulsos.exists():
        linhas.append('Pagamentos avulsos a pagar:')
        linhas.extend(
            f'- {p.descricao}: R$ {_br(p.valor)} em {p.data_pagamento:%d/%m/%Y}'
            for p in avulsos
        )

    parcelas_dividas = ParcelaDivida.objects.filter(
        status='a_pagar', data_vencimento__gte=hoje, data_vencimento__lte=fim,
        divida__ativa=True, divida__para_pagamento=True,
    ).select_related('divida').order_by('data_vencimento')
    if parcelas_dividas.exists():
        linhas.append('Parcelas de dívidas a pagar (nos próximos 60 dias):')
        linhas.extend(
            f'- {p.divida.descricao} parcela {p.numero}: R$ {_br(p.valor)} em {p.data_vencimento:%d/%m/%Y}'
            for p in parcelas_dividas
        )

    faturas = previsao_faturas_fluxo(hoje.year, hoje.month)
    for f in faturas:
        if f['data_vencimento'] <= fim:
            linhas.append(
                f'- Fatura {f["cartao"].nome}: R$ {_br(f["valor"])} em '
                f'{f["data_vencimento"]:%d/%m/%Y} (situação: {f["situacao"].replace("_", " ")})'
            )

    receber = OcorrenciaRecebimento.objects.filter(
        data_prevista__gte=hoje, data_prevista__lte=fim,
    ).exclude(status='recebido').select_related('recebimento_periodico').order_by('data_prevista')
    if receber.exists():
        linhas.append('Recebimentos periódicos a receber:')
        linhas.extend(
            f'- {r.recebimento_periodico.descricao}: R$ {_br(r.valor)} em {r.data_prevista:%d/%m/%Y}'
            for r in receber
        )

    avulsos_receber = RecebimentoAvulso.objects.filter(
        data_prevista__gte=hoje, data_prevista__lte=fim,
    ).exclude(status='recebido').order_by('data_prevista')
    if avulsos_receber.exists():
        linhas.append('Recebimentos avulsos a receber:')
        linhas.extend(
            f'- {r.descricao}: R$ {_br(r.valor)} em {r.data_prevista:%d/%m/%Y}'
            for r in avulsos_receber
        )

    if not linhas:
        linhas.append('Nenhum movimento previsto para os próximos 60 dias.')
    return '== FLUXO DE CAIXA (próximos 60 dias) ==\n' + '\n'.join(linhas)


def _contexto_movimentacoes():
    hoje = timezone.localdate()
    inicio = hoje - timedelta(days=30)
    recentes = Movimentacao.objects.filter(data__gte=inicio).select_related('conta').order_by('-data')
    entradas = recentes.filter(tipo='entrada').aggregate(t=Sum('valor'))['t'] or Decimal('0')
    saidas = recentes.filter(tipo='saida').aggregate(t=Sum('valor'))['t'] or Decimal('0')
    linhas = [
        '== MOVIMENTAÇÕES (últimos 30 dias) ==',
        f'Entradas: R$ {_br(entradas)} | Saídas: R$ {_br(saidas)} | '
        f'Saldo do período: R$ {_br(entradas - saidas)}',
    ]
    for mov in recentes[:15]:
        direcao = 'Entrada' if mov.tipo == 'entrada' else 'Saída'
        linhas.append(
            f'- [{direcao}] {mov.descricao} (cat.: {mov.categoria or "sem categoria"}) '
            f'R$ {_br(mov.valor)} em {mov.data:%d/%m/%Y} na {mov.conta.nome}'
        )
    if not recentes.exists():
        linhas.append('Nenhuma movimentação nos últimos 30 dias.')
    proventos = ProventoRecebido.objects.filter(data__gte=inicio).order_by('-data')
    if proventos.exists():
        linhas.append('Proventos recebidos no período:')
        linhas.extend(
            f'- {p.ativo.ticker} ({p.tipo or "provento"}): R$ {_br(p.valor)} em {p.data:%d/%m/%Y}'
            for p in proventos[:10]
        )
    return '\n'.join(linhas)


def montar_contexto(limite_caracteres: int | None = None) -> str:
    """Monta o contexto financeiro completo do usuário.

    O contexto é truncado para caber no orçamento de tokens (aprox.
    4 caracteres por token).
    """
    hoje = timezone.localdate()
    partes = [
        f'Hoje é {hoje:%d/%m/%Y}. Você é o assistente financeiro pessoal do usuário, '
        'integrado ao sistema "Controle Financeiro". Responda sempre em português do '
        'Brasil, de forma clara, direta e útil. Use APENAS os dados fornecidos abaixo — '
        'nunca invente números. Se a informação pedida não estiver no contexto, diga '
        'que não está disponível no sistema.',
        '',
        _contexto_patrimonio(),
        '',
        _contexto_cartoes(),
        '',
        _contexto_faturas_proximas(),
        '',
        _contexto_dividas(),
        '',
        _contexto_fluxo(),
        '',
        _contexto_movimentacoes(),
    ]
    contexto = '\n'.join(partes)

    if not limite_caracteres:
        limite_caracteres = int(getattr(settings, 'MARITACA_MAX_TOKENS', 2048)) * 4
    if len(contexto) > limite_caracteres:
        contexto = contexto[: limite_caracteres - len('\n[contexto truncado por limite de tokens]')]
        contexto += '\n[contexto truncado por limite de tokens]'
    return contexto


def _config():
    base_url = getattr(settings, 'MARITACA_BASE_URL', 'https://chat.maritaca.ai/api').rstrip('/')
    return {
        'api_key': getattr(settings, 'MARITACA_API_KEY', ''),
        'base_url': base_url,
        'model': getattr(settings, 'MARITACA_MODEL', 'sabia-4'),
        'max_tokens': int(getattr(settings, 'MARITACA_MAX_TOKENS', 2048)),
        'timeout': int(getattr(settings, 'MARITACA_TIMEOUT', 60)),
    }


def enviar_mensagem(historico, contexto=None) -> tuple[bool, str]:
    """Envia a conversa (system com contexto + mensagens) ao modelo.

    Retorna (sucesso, texto). Em caso de erro, texto traz a mensagem amigável.
    """
    cfg = _config()
    if not cfg['api_key']:
        return False, (
            'Assistente não configurado: defina MARITACA_API_KEY nas variáveis de '
            'ambiente para habilitar a IA.'
        )

    contexto = contexto or montar_contexto()
    messages = [{'role': 'system', 'content': contexto}]
    messages.extend(historico[-20:])

    payload = {
        'model': cfg['model'],
        'messages': messages,
        'max_tokens': cfg['max_tokens'],
        'temperature': 0.3,
    }
    dados = json.dumps(payload).encode('utf-8')
    requisicao = urllib.request.Request(
        f"{cfg['base_url']}/chat/completions",
        data=dados,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {cfg["api_key"]}',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(requisicao, timeout=cfg['timeout']) as resposta:
            corpo = json.loads(resposta.read().decode('utf-8'))
        escolha = corpo.get('choices', [{}])[0]
        texto = escolha.get('message', {}).get('content', '') or ''
        return True, texto.strip()
    except urllib.error.HTTPError as e:
        detalhe = ''
        try:
            detalhe = e.read().decode('utf-8')[:300]
        except Exception:
            pass
        return False, f'Erro da API ({e.code}): {detalhe or "resposta vazia da API".strip()}'
    except urllib.error.URLError as e:
        return False, f'Falha de conexão com a API: {e.reason}'
    except Exception as e:  # noqa: BLE001
        return False, f'Erro inesperado: {e}'


def assistente_habilitado() -> bool:
    return bool(getattr(settings, 'MARITACA_API_KEY', ''))