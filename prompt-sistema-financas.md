# Prompt: Sistema de Controle Financeiro Pessoal (Django + MySQL + Bootstrap)

## Contexto e Objetivo

Crie um sistema web monolítico de controle financeiro pessoal usando **Python/Django**, banco de dados **MySQL** e front-end com **Bootstrap** (server-side rendering via templates Django, sem SPA separado). O sistema deve consolidar em um único painel a visão completa da minha vida financeira: contas bancárias, cartões de crédito, dívidas, poupança, CDBs/renda fixa, ativos de renda variável (FIIs/ações) e criptomoedas — com histórico automático de todos os valores.

---

## 1. Stack técnica

- **Backend:** Python 3.x + Django (última versão estável)
- **Banco de dados:** MySQL
- **Front-end:** Django Templates + Bootstrap 5 (monolítico, sem API REST separada por enquanto — pode usar Django Forms/Views tradicionais)
- **Agendamento de tarefas:** Django + Celery + Celery Beat (ou `django-crontab`/`django-q` como alternativa mais simples) para rotinas automáticas (snapshot de histórico a cada 8h, cálculo de rendimento diário do CDB em dias úteis)
- **Autenticação:** sistema de login simples baseado no Django Auth padrão (ver seção 2.0 abaixo)
- **Admin:** usar o Django Admin customizado para cadastro/manutenção rápida dos dados

---

## 2. Módulos do sistema

### 2.1 Dashboard geral
- Visão consolidada: patrimônio total, total em contas, total em dívidas/cartões, total investido (renda fixa + variável + cripto), saldo líquido (ativos − passivos).
- Gráficos de evolução patrimonial ao longo do tempo (usando os snapshots históricos).

### 2.2 Contas bancárias
- Cadastro de bancos/contas (nome do banco, tipo de conta, saldo atual).
- Atualização manual do saldo, com registro de histórico a cada alteração.
- **Registro de movimentações (compras e pagamentos) na conta:**
  - Cadastro de cada movimentação: descrição, categoria (opcional), valor, data, tipo (**saída** — compra/pagamento/débito, ou **entrada** — depósito/transferência recebida), conta vinculada.
  - Cada movimentação lançada deve atualizar automaticamente o saldo atual da conta (e gerar o respectivo histórico).
  - Listagem de movimentações por período (dia/mês), com totais de entradas e saídas e extrato consolidado por conta.
  - Permitir vincular uma movimentação de saída ao pagamento de uma conta periódica ou dívida (ver seção 2.9), e uma movimentação de entrada a um recebimento periódico ou avulso (ver seção 2.10), para dar baixa automática nesses itens.

### 2.3 Cartões de crédito
- Cadastro de cartões (nome, banco emissor, limite total, **limite atual disponível** — calculado automaticamente com base no limite total menos o somatório das compras/parcelas em aberto).
- Saldo devedor atual (fatura em aberto).
- Data de fechamento e vencimento da fatura.
- Indicar se a fatura está paga, em aberto ou atrasada.
- **Registro de compras realizadas no cartão:**
  - Cadastro de cada compra: descrição, estabelecimento, categoria (opcional, ex: alimentação, transporte, lazer), valor total, data da compra, cartão vinculado.
  - Indicar se a compra é **à vista** ou **parcelada**.
  - **Parcelamentos:** ao cadastrar uma compra parcelada, informar número total de parcelas e valor da parcela (pode ser calculado automaticamente: valor total ÷ nº de parcelas). O sistema deve gerar automaticamente os registros das parcelas futuras, vinculando cada parcela a uma fatura/mês específico, e abatendo o valor da parcela do limite disponível até a quitação.
  - Cada parcela deve ter status: **a vencer**, **na fatura atual**, **paga**.
  - O limite disponível do cartão deve considerar o somatório de todas as parcelas futuras em aberto (não só a fatura do mês atual), já que o limite fica comprometido até o fim do parcelamento.
  - Listagem de compras por fatura/mês, com total gasto por categoria (para relatórios simples).

### 2.4 Dívidas
- Cadastro de dívidas (descrição, credor, valor total, valor pago, valor restante).
- Status: **em dia**, **a pagar (futura)**, **atrasada**.
- Data de vencimento e, se atrasada, cálculo de dias em atraso.
- Parcelamento (opcional): número de parcelas, valor da parcela, parcelas restantes.

### 2.5 Poupança
- Saldo atual por conta poupança.
- Histórico de aportes/retiradas.
- Projeção simples de rendimento (taxa da poupança, aplicada conforme regra vigente: 0,5%/mês + TR quando Selic > 8,5% a.a., ou 70% da Selic + TR quando ≤ 8,5% a.a. — deixar configurável).

### 2.6 CDB / Renda Fixa
Este módulo precisa ser o mais robusto:
- Cadastro de cada aplicação de CDB: banco/financeira, valor aplicado, data de aplicação, data de vencimento, **percentual do CDI contratado** (ex: 100%, 110%, 120% — editável a qualquer momento, pois pode variar por instituição).
- Campo para taxa do CDI vigente (atualizável manualmente por enquanto, mas estruturado para futura integração com API — ex: Banco Central/CDI diário).
- **Cálculo de rendimento com projeção:**
  - Rendimento deve ser calculado **exclusivamente em dias úteis** (não incidir em sábados, domingos e feriados nacionais).
  - Necessário um calendário de dias úteis/feriados (pode usar a biblioteca `workalendar` ou `python-holidays` para feriados nacionais brasileiros).
  - Fórmula: rendimento diário = ((1 + (CDI_anual × %_contratado)) ^ (1/252)) − 1, aplicado apenas nos dias úteis decorridos.
  - Exibir: valor investido, valor bruto atual (rendimento acumulado), projeção para data de vencimento, e projeção líquida (com IR regressivo conforme tabela: 22,5% até 180 dias, 20% até 360 dias, 17,5% até 720 dias, 15% acima de 720 dias).
- Permitir múltiplos CDBs simultâneos com taxas diferentes por instituição.

### 2.7 Ativos de renda variável (ex: MXRF11, ações, outros FIIs)
- Cadastro de ativos: ticker, tipo (FII, ação, ETF), quantidade de cotas/ações, preço médio de compra.
- Preço atual (atualização manual por enquanto, campo preparado para futura integração com API de cotações, ex: brapi.dev ou similar).
- Projeção: com base em preço atual × quantidade = valor de mercado atual; campo para projeção de dividendos/proventos mensais (dividend yield estimado, editável).
- Histórico de proventos recebidos (opcional, mas recomendado).

### 2.8 Criptomoedas (módulo preparado para API futura)
- Cadastro de moedas: nome, símbolo (ex: BTC, ETH), quantidade possuída.
- Campos de cotação **inseridos manualmente por enquanto**:
  - Valor em BRL
  - Valor em USD
  - Valor em BTC (**apenas quando não houver par direto** com BTC — ou seja, se a moeda já for o próprio BTC, esse campo não se aplica; para demais moedas sem par negociado contra BTC, usar essa cotação de referência)
- Estruturar o model com um campo `fonte_cotacao` (ex: "manual" / "api") e um campo `atualizado_em`, para que no futuro um serviço/integração (ex: CoinGecko, Binance API) possa substituir a atualização manual sem quebrar a estrutura existente.
- Isolar a lógica de "buscar cotação atual" em uma função/service (`services/crypto_quotes.py`) que hoje apenas lê o valor manual do banco, mas que já está desacoplada da view — facilitando a troca futura por uma chamada de API real.

### 2.9 Contas periódicas a pagar
- Cadastro de contas recorrentes (ex: aluguel, internet, energia, assinaturas): descrição, valor esperado (pode variar mês a mês, ex: conta de luz), dia de vencimento no mês, categoria, conta/cartão de pagamento padrão (opcional).
- Recorrência configurável: mensal, quinzenal, anual, etc.
- A cada novo ciclo, o sistema deve gerar automaticamente uma nova ocorrência/lançamento "a pagar" com base na recorrência cadastrada (pode ser feito via a mesma tarefa agendada do histórico, ou uma tarefa própria rodando diariamente).
- Status de cada ocorrência: **a pagar (futura)**, **vencendo hoje**, **atrasada**, **paga**.
- Ao dar baixa (marcar como paga), permitir vincular à movimentação de saída correspondente em uma conta bancária/cartão, e registrar a data efetiva do pagamento (para comparar com a data de vencimento e identificar atrasos).

### 2.10 Recebimentos periódicos e avulsos
- **Recebimentos periódicos** (ex: salário, aluguel recebido, mesada): descrição, valor esperado, dia de recebimento no mês, recorrência (mensal, quinzenal, etc.), conta bancária de destino padrão (opcional).
- **Recebimentos avulsos** (ex: venda de algo, reembolso, freelance pontual): descrição, valor, data prevista de recebimento, sem recorrência.
- Status de cada ocorrência: **a receber (futuro)**, **atrasado** (passou da data prevista e não foi recebido), **recebido**.
- Ao dar baixa (marcar como recebido), permitir vincular à movimentação de entrada correspondente em uma conta bancária, e registrar a data efetiva do recebimento.
- Exibir no dashboard uma projeção simples de fluxo de caixa do mês: total a pagar (contas periódicas + dívidas + faturas) vs. total a receber (recebimentos periódicos + avulsos), para visualizar o saldo projetado do mês.

---

## 3. Histórico automático (snapshot a cada 8 horas)

- Criar uma tabela genérica de histórico (`HistoricoSnapshot` ou uma tabela por módulo, ex: `HistoricoContaBancaria`, `HistoricoCartao`, `HistoricoCDB`, `HistoricoAtivo`, `HistoricoCripto`) que registre o valor de **todos** os itens do sistema.
- Tarefa agendada (Celery Beat) rodando **a cada 8 horas** (00:00, 08:00, 16:00 ou o intervalo que preferir) que:
  1. Percorre todos os registros ativos de cada módulo.
  2. Calcula o valor atual (incluindo rendimento projetado do dia, no caso do CDB).
  3. Grava um snapshot com timestamp em cada tabela de histórico.
- Essa base histórica alimenta os gráficos de evolução patrimonial do dashboard.

---

## 4. Requisitos não funcionais

- Percentuais e taxas (CDI, % do CDB, taxa da poupança, dividend yield) devem ser **campos editáveis**, nunca hardcoded, pois variam por instituição/produto e ao longo do tempo.
- Toda alteração manual de saldo/valor deve gerar um registro de auditoria (quem alterou, valor anterior, valor novo, data/hora) — pode reaproveitar as tabelas de histórico para isso.
- Interface responsiva com Bootstrap 5, painéis/cards por módulo, tabelas com totais.
- Preparar variáveis de ambiente (`.env`) para configurações sensíveis (DB, secret key, futuras chaves de API).
- Estrutura de apps Django separada por domínio, sugestão:
  - `contas` (bancos/contas correntes)
  - `cartoes`
  - `dividas`
  - `poupanca`
  - `renda_fixa` (CDB)
  - `renda_variavel` (ativos/FIIs)
  - `cripto`
  - `contas_periodicas` (contas a pagar e recebimentos periódicos/avulsos)
  - `historico`
  - `dashboard`

---

## 5. Entregáveis esperados

1. Modelagem de dados (models.py) de todos os módulos acima.
2. Migrations.
3. Views + templates Bootstrap para CRUD de cada módulo.
4. Dashboard consolidado com gráficos (pode usar Chart.js via CDN).
5. Serviço de cálculo de rendimento de CDB considerando dias úteis.
6. Tarefa agendada (Celery Beat) para snapshot de histórico a cada 8h.
7. Estrutura pronta (mas não implementada) para plugar APIs externas de cotação de criptos e ativos no futuro.
