import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .services import enviar_mensagem, montar_contexto


@login_required
@require_POST
def chat(request):
    """Endpoint do chat popup. Espera JSON: {"mensagem": "...", "historico": [...]}."""
    try:
        corpo = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'erro': 'Requisição inválida.'}, status=400)

    mensagem = (corpo.get('mensagem') or '').strip()
    historico = corpo.get('historico') or []
    if not mensagem:
        return JsonResponse({'erro': 'Mensagem vazia.'}, status=400)

    if not isinstance(historico, list):
        historico = []

    # Garante que cada item de histórico é (role, content) válido
    limpo = []
    for item in historico:
        if isinstance(item, dict) and item.get('role') in ('user', 'assistant'):
            conteudo = (item.get('content') or '').strip()
            if conteudo:
                limpo.append({'role': item['role'], 'content': conteudo})
    limpo.append({'role': 'user', 'content': mensagem})

    contexto = montar_contexto()
    sucesso, texto = enviar_mensagem(limpo, contexto=contexto)
    if not sucesso:
        return JsonResponse({'erro': texto}, status=502)
    return JsonResponse({'resposta': texto})