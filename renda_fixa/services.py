from datetime import date
from decimal import Decimal

from workalendar.america import Brazil

from .models import AplicacaoCDB, TaxaCDI

_calendario = Brazil()


def aliquota_ir_por_dias(dias_corridos):
    """Alíquota regressiva do IR para renda fixa (em %)."""
    if dias_corridos <= 180:
        return Decimal('22.5')
    if dias_corridos <= 360:
        return Decimal('20.0')
    if dias_corridos <= 720:
        return Decimal('17.5')
    return Decimal('15.0')


def taxa_cdi_vigente():
    return TaxaCDI.taxa_vigente()


def taxa_diaria(cdi_anual, percentual_cdi):
    """Taxa diária (dias úteis) composta: (1 + (CDI_anual × %_contratado))^(1/252) − 1."""
    if cdi_anual <= 0:
        return Decimal('0')
    cdi_anual_dec = Decimal(str(cdi_anual)) / Decimal('100')
    pct = Decimal(str(percentual_cdi)) / Decimal('100')
    return (Decimal('1') + cdi_anual_dec * pct) ** (Decimal('1') / Decimal('252')) - Decimal('1')


def contar_dias_uteis(inicio: date, fim: date) -> int:
    """Conta dias úteis entre `inicio` e `fim` (inclusive), ignorando feriados nacionais."""
    if fim < inicio:
        return 0
    total = 0
    dia = inicio
    while dia <= fim:
        if _calendario.is_working_day(dia):
            total += 1
        dia = _proximo_dia(dia)
    return total


def _proximo_dia(d):
    from datetime import timedelta
    return d + timedelta(days=1)


def calcular_valor_bruto(aplicacao: AplicacaoCDB, data: date | None = None) -> dict:
    """Calcula o rendimento de um CDB na data informada (hoje, se omitida).

    Retorna dict com valor_bruto, valor_liquido, rendimento, IR, dias_uteis e dias_corridos.
    """
    data = data or date.today()
    cdi = Decimal(str(taxa_cdi_vigente()))
    pct = Decimal(str(aplicacao.percentual_cdi))
    taxa = taxa_diaria(cdi, pct)

    fim = min(data, aplicacao.data_vencimento)
    dias_uteis = contar_dias_uteis(aplicacao.data_aplicacao, fim)
    dias_corridos = (fim - aplicacao.data_aplicacao).days

    fator = (Decimal('1') + taxa) ** Decimal(dias_uteis) if dias_uteis > 0 else Decimal('1')
    valor_bruto = Decimal(str(aplicacao.valor_aplicado)) * fator
    rendimento = valor_bruto - Decimal(str(aplicacao.valor_aplicado))
    ir = Decimal('0')
    if rendimento > 0 and dias_corridos > 0:
        aliquota = aliquota_ir_por_dias(dias_corridos)
        ir = rendimento * aliquota / Decimal('100')
    valor_liquido = valor_bruto - ir

    return {
        'valor_bruto': valor_bruto.quantize(Decimal('0.01')),
        'rendimento': rendimento.quantize(Decimal('0.01')),
        'ir': ir.quantize(Decimal('0.01')),
        'valor_liquido': valor_liquido.quantize(Decimal('0.01')),
        'dias_uteis': dias_uteis,
        'dias_corridos': dias_corridos,
        'taxa_diaria': taxa,
    }


def calcular_projecao_vencimento(aplicacao: AplicacaoCDB) -> dict:
    """Projeção (bruta e líquida) na data de vencimento do CDB."""
    return calcular_valor_bruto(aplicacao, data=aplicacao.data_vencimento)


def total_renda_fixa(data: date | None = None) -> Decimal:
    """Soma dos valores brutos atuais de todos os CDBs ativos."""
    data = data or date.today()
    total = Decimal('0')
    for aplicacao in AplicacaoCDB.objects.filter(ativo=True):
        total += calcular_valor_bruto(aplicacao, data=data)['valor_bruto']
    return total