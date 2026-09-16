# Sistema de Controle Financeiro Pessoal

Sistema web monolítico de finanças pessoais em **Python/Django + MySQL + Bootstrap 5**:
contas bancárias, cartões de crédito (com parcelamento), dívidas, poupança,
CDB/renda fixa (com projeção em dias úteis + IR regressivo), renda variável,
criptomoedas, contas/recebimentos periódicos e dashboard consolidado com
gráficos (Chart.js). Histórico automático de patrimônio via snapshot agendado
(Celery Beat) a cada 8 horas.

## Stack

- Python 3.13+, Django 6.0
- MySQL 8+ (ou SQLite em dev, configurável via variáveis de ambiente)
- Celery + Celery Beat (snapshot a cada 8h, ciclos de contas periódicas)
- `workalendar` (dias úteis/feriados BR para cálculo do CDB)
- Bootstrap 5 + Chart.js via CDN
- Deploy containerizado via Dockerfile (gunicorn + Celery)

## Configuração por variáveis de ambiente

> **Importante:** este projeto **não** usa `python-dotenv`. Todas as
> configurações (chave secreta, banco, broker do Celery) vêm **direto do
> ambiente do processo** (`os.environ`). Não há `.env` lido pela aplicação —
> exporte as variáveis abaixo no shell, compose, systemd, k8s etc.

### Referência de variáveis

| Variável | Obrigatória (prod) | Padrão | Descrição |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | **sim** | `django-insecure-fallback` | Chave secreta do Django. Gere com `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DJANGO_DEBUG` | sim (usar `False`) | `True` | `True`/`False`. Nunca `True` em produção |
| `DJANGO_ALLOWED_HOSTS` | **sim** | `127.0.0.1,localhost` | Hosts/domínios permitidos, separados por vírgula |
| `DB_ENGINE` | sim (usar `mysql`) | `sqlite` | `mysql` (produção) ou `sqlite` (local) |
| `DB_NAME` | se `mysql` | `financas` | Nome do banco (deve existir com `utf8mb4`) |
| `DB_USER` | se `mysql` | `` | Usuário do MySQL |
| `DB_PASSWORD` | se `mysql` | `` | Senha do usuário do MySQL |
| `DB_HOST` | se `mysql` | `127.0.0.1` | Host do servidor MySQL |
| `DB_PORT` | se `mysql` | `3306` | Porta do servidor MySQL |
| `CELERY_BROKER_URL` | **sim** (broker real) | `memory://` | Ex.: `redis://redis:6379/0` |
| `CELERY_RESULT_BACKEND` | não | `django-db` | Backend de resultados (tabelas do Django) |
| `PORT` | não | `8000` | Porta do gunicorn (lida pelo entrypoint) |
| `WEB_CONCURRENCY` | não | `3` | Workers do gunicorn (entrypoint) |

## Instalação local (desenvolvimento)

```bash
# 1. Crie e ative um virtualenv
python -m venv .venv
.venv\Scripts\activate        # Windows

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Exporte as variáveis (o fallback = SQLite já funciona sem nada)
#    Windows (PowerShell):    $env:DJANGO_SECRET_KEY="..."
#    Linux/macOS:            export DJANGO_SECRET_KEY="..."

# 4. Rode as migrations (cria o BD, superuser opcional)
python manage.py migrate
python manage.py createsuperuser

# 5. Suba o servidor
python manage.py runserver
```

Acesse http://127.0.0.1:8000/ (login `admin`).

### Usando MySQL local

1. Instale o servidor MySQL e crie o banco:
   `CREATE DATABASE financas CHARACTER SET utf8mb4;`
2. Exporte as variáveis:
   ```
   DB_ENGINE=mysql
   DB_NAME=financas
   DB_USER=seu_usuario
   DB_PASSWORD=sua_senha
   DB_HOST=127.0.0.1
   DB_PORT=3306
   ```
3. Rode `python manage.py migrate`.

Se `DB_ENGINE` for deixado vazio/`sqlite`, o sistema usa SQLite (ideal para dev).

## Tarefas agendadas (Celery Beat)

O snapshot de histórico (a cada 8h: 00h, 08h e 16h) e os ciclos de contas
periódicas são executados pelo Celery. O agendamento já é criado
automaticamente pelas migrations (tabela `PeriodicTask`).

```bash
# Terminal 1 - worker (no Windows use --pool=solo)
celery -A sistema_financas worker -l info --pool=solo

# Terminal 2 - beat scheduler
celery -A sistema_financas beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

Para um snapshot manual imediato:

```bash
python manage.py shell -c "from historico.tasks import snapshot_historico_8h; snapshot_historico_8h.apply()"
```

## Deploy com Docker

### Infraestrutura necessária

- [Docker Engine](https://docs.docker.com/engine/install/) (ou Docker Desktop).
- **MySQL 8+** rodando em container ou externamente — banco de dados.
- **Redis 7+** rodando em container ou externamente — broker/fila do Celery
  (`CELERY_BROKER_URL=redis://...`). Sem Redis o `memory://` só funciona em dev.
- **3 processos da mesma imagem**, um por serviço:
  - `SERVICE=web` → gunicorn (aplicação HTTP, porta 8000)
  - `SERVICE=worker` → Celery worker (consome a fila de tarefas)
  - `SERVICE=beat` → Celery beat (agenda os snapshots)
- O entrypoint (`docker-entrypoint.sh`) roda `migrate` + `collectstatic`
  automaticamente a cada start — conecte os containers ao mesmo MySQL primeiro.

### Build da imagem

```bash
docker build -t sistema-financas .
```

> A imagem do processo de build compila o `mysqlclient`, por isso instala
> `gcc`, `default-libmysqlclient-dev` e `pkg-config` automaticamente — não é
> preciso configurar nada.

### Variáveis obrigatórias em produção

Ao menos estas devem ser definidas no ambiente dos containers:

```
DJANGO_SECRET_KEY=<chave-forte>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,seus-dominios
DB_ENGINE=mysql
DB_NAME=financas
DB_USER=<usuario>
DB_PASSWORD=<senha>
DB_HOST=<host-do-mysql>
DB_PORT=3306
CELERY_BROKER_URL=redis://<host-do-redis>:6379/0
```

### Rodando os serviços

```bash
# App web (porta 8000)
docker run -d -p 8000:8000 --name financas-web \
  -e DJANGO_SECRET_KEY=... -e DJANGO_DEBUG=False \
  -e DJANGO_ALLOWED_HOSTS=127.0.0.1,seus-dominios \
  -e DB_ENGINE=mysql -e DB_NAME=financas -e DB_USER=... -e DB_PASSWORD=... \
  -e DB_HOST=mysql -e CELERY_BROKER_URL=redis://redis:6379/0 \
  sistema-financas

# Celery worker
docker run -d --name financas-worker \
  -e SERVICE=worker \
  -e DB_ENGINE=mysql -e DB_NAME=financas -e DB_USER=... -e DB_PASSWORD=... \
  -e DB_HOST=mysql -e CELERY_BROKER_URL=redis://redis:6379/0 \
  sistema-financas

# Celery beat
docker run -d --name financas-beat \
  -e SERVICE=beat \
  -e DB_ENGINE=mysql -e DB_NAME=financas -e DB_USER=... -e DB_PASSWORD=... \
  -e DB_HOST=mysql -e CELERY_BROKER_URL=redis://redis:6379/0 \
  sistema-financas
```

> **Sugestão:** para orquestrar MySQL, Redis e os 3 serviços de uma vez, use
> `docker compose` (substitua os `docker run` por services `web`, `worker` e
> `beat` na mesma imagem, com as variáveis acima).

### Passos após o primeiro deploy

1. Aguarde o container `web` subir — o entrypoint aplica as migrations e
   coleta os static files automaticamente.
2. Crie o superusuário (executando dentro do container `web`):
   ```bash
   docker exec -it financas-web python manage.py createsuperuser
   ```
3. No admin (`/admin/`), a tarefa periódica **"Snapshot histórico a cada 8h"**
   já é criada automaticamente pelas migrations (Celery Beat).

## Módulos

| Módulo | URL | Descrição |
|---|---|---|
| Dashboard | `/` | Patrimônio total, saldo líquido, fluxo de caixa do mês, evolução patrimonial (Chart.js) |
| Contas | `/contas/` | Bancos, saldo, movimentações com atualização automática + extrato por período |
| Cartões | `/cartoes/` | Limite, faturas, compras à vista/parceladas (parcelas geradas automaticamente) |
| Dívidas | `/dividas/` | Valor restante, parcelamento, dias em atraso |
| Poupança | `/poupanca/` | Aportes/retiradas, regra Selic configurável |
| CDB | `/renda-fixa/` | Rendimento só em dias úteis, IR regressivo, projeção no vencimento |
| Ativos | `/ativos/` | FIIs/ações/ETFs, valor de mercado, dividend yield, proventos |
| Cripto | `/cripto/` | Cotações manuais (estrutura pronta para API via `cripto/services/crypto_quotes.py`) |
| Fluxo de Caixa | `/fluxo/` | Contas periódicas, recebimentos (periódicos/avulsos), baixas vinculadas a movimentações |
| Admin | `/admin/` | Cadastro rápido de tudo |

## Estrutura

```
Dockerfile            # imagem de deploy (gunicorn + Celery)
docker-entrypoint.sh  # migrate + collectstatic + SERVICE=web|worker|beat
sistema_financas/     # projeto (settings, urls, celery, helpers)
contas/               # bancos + movimentações
cartoes/              # cartões, compras, parcelas, faturas
dividas/
poupanca/
renda_fixa/           # CDB + TaxaCDI + services (rendimento)
renda_variavel/       # ativos + proventos
cripto/               # cripto + services/crypto_quotes.py
contas_periodicas/    # contas a pagar, recebimentos, baixas
historico/            # services + tasks (snapshot 8h)
dashboard/            # resumo patrimonial + gráficos
templates/            # base.html, generic_form.html, login
```

## Notas

- Taxas/pedras (CDI, % do CDB, Selic, dividend yield) são **campos editáveis** — nunca hardcoded.
- Toda alteração registra histórico/auditoria nas tabelas `Historico*`.
- Cotações de cripto e preços de ativos são manuais por enquanto; a estrutura
  (`fonte_cotacao`, `atualizado_em`, serviços isolados) está pronta para plugar APIs.
- Em produção coloque o serviço `web` atrás de um reverse proxy (nginx/Caddy)
  com HTTPS — o gunicorn serve HTTP na porta 8000.