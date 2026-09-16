from celery import shared_task

from contas_periodicas.services import processar_ciclos
from .services import gerar_todos_os_snapshots


@shared_task
def snapshot_historico_8h():
    """Roda a cada 8 horas: snapshot de todos os módulos + ciclos de contas periódicas."""
    processar_ciclos()
    gerar_todos_os_snapshots()
    return {'status': 'ok'}