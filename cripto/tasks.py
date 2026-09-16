from celery import shared_task

from cripto.services.crypto_quotes import precificar_auto


@shared_task
def atualizar_cotacoes_cripto():
    """Atualiza via API todas as criptomoedas com precificação automática habilitada."""
    resultado = precificar_auto()
    return resultado