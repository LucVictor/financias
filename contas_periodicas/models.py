from django.conf import settings
from django.db import models
from django.utils import timezone


def _ultimo_dia_mes(ano, mes):
    import calendar
    return calendar.monthrange(ano, mes)[1]


class BasePeriodico(models.Model):
    RECURRENCIA_CHOICES = [
        ('mensal', 'Mensal'),
        ('quinzenal', 'Quinzenal'),
        ('semanal', 'Semanal'),
        ('anual', 'Anual'),
    ]

    descricao = models.CharField(max_length=255)
    valor_esperado = models.DecimalField(max_digits=15, decimal_places=2)
    dia_do_mes = models.PositiveSmallIntegerField(default=1)
    recorrência = models.CharField(max_length=15, choices=RECURRENCIA_CHOICES, default='mensal')
    categoria = models.CharField(max_length=100, blank=True, default='')
    ativo = models.BooleanField(default=True)
    observacoes = models.TextField(blank=True, default='')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    @staticmethod
    def _proxima_data(dia_do_mes, base=None):
        """Próxima data com o dia `dia_do_mes` a partir de `base` (hoje por padrão).

        Caso o dia não exista no mês (ex.: dia 31 em fevereiro), usa o último dia do mês.
        """
        from datetime import date
        hoje = base or timezone.localdate()

        def _candidata(ano, mes):
            dia = min(dia_do_mes, _ultimo_dia_mes(ano, mes))
            return date(ano, mes, dia)

        candidata = _candidata(hoje.year, hoje.month)
        if candidata >= hoje:
            return candidata
        if hoje.month < 12:
            return _candidata(hoje.year, hoje.month + 1)
        return _candidata(hoje.year + 1, 1)


class ContaPeriodica(BasePeriodico):
    """Conta recorrente a pagar (aluguel, internet, energia, assinaturas etc.)."""
    TIPO_CONTROLE_CHOICES = [
        ('conta', 'Conta bancária'),
        ('cartao', 'Cartão de crédito'),
    ]

    conta_pagamento_padrao = models.ForeignKey(
        'contas.Banco', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='contas_periodicas',
    )
    cartao_pagamento_padrao = models.ForeignKey(
        'cartoes.CartaoCredito', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='contas_periodicas',
    )

    class Meta(BasePeriodico.Meta):
        verbose_name = 'Conta Periódica (a pagar)'
        verbose_name_plural = 'Contas Periódicas (a pagar)'

    def __str__(self):
        return self.descricao


class OcorrenciaContaPeriodica(models.Model):
    STATUS_CHOICES = [
        ('a_pagar', 'A pagar (futura)'),
        ('vencendo_hoje', 'Vencendo hoje'),
        ('atrasada', 'Atrasada'),
        ('paga', 'Paga'),
    ]

    conta_periodica = models.ForeignKey(
        ContaPeriodica, on_delete=models.CASCADE, related_name='ocorrencias'
    )
    data_vencimento = models.DateField()
    valor = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='a_pagar')
    data_pagamento = models.DateField(null=True, blank=True)
    valor_pago = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    movimentacao = models.ForeignKey(
        'contas.Movimentacao', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ocorrencias_conta_periodica',
        help_text='Movimentação de saída na conta bancária vinculada à baixa.',
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Ocorrência de Conta Periódica'
        verbose_name_plural = 'Ocorrências de Contas Periódicas'
        ordering = ['data_vencimento']

    def __str__(self):
        return f'{self.conta_periodica.descricao} — {self.data_vencimento:%d/%m/%Y}'

    @property
    def atrasado(self):
        return self.data_vencimento < timezone.localdate() and self.status != 'paga'

    def atualizar_status(self):
        hoje = timezone.localdate()
        if self.status == 'paga':
            return
        if self.data_vencimento < hoje:
            self.status = 'atrasada'
        elif self.data_vencimento == hoje:
            self.status = 'vencendo_hoje'
        else:
            self.status = 'a_pagar'
        self.save(update_fields=['status'])


class RecebimentoPeriodico(BasePeriodico):
    """Recebimento recorrente (salário, aluguel recebido, mesada etc.)."""
    conta_destino_padrao = models.ForeignKey(
        'contas.Banco', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='recebimentos_periodicos',
    )

    class Meta(BasePeriodico.Meta):
        verbose_name = 'Recebimento Periódico'
        verbose_name_plural = 'Recebimentos Periódicos'

    def __str__(self):
        return self.descricao


class OcorrenciaRecebimento(models.Model):
    STATUS_CHOICES = [
        ('a_receber', 'A receber (futuro)'),
        ('atrasado', 'Atrasado'),
        ('recebido', 'Recebido'),
    ]

    recebimento_periodico = models.ForeignKey(
        RecebimentoPeriodico, on_delete=models.CASCADE, related_name='ocorrencias'
    )
    data_prevista = models.DateField()
    valor = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='a_receber')
    data_recebimento = models.DateField(null=True, blank=True)
    valor_recebido = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    movimentacao = models.ForeignKey(
        'contas.Movimentacao', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ocorrencias_recebimento',
        help_text='Movimentação de entrada na conta bancária vinculada à baixa.',
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Ocorrência de Recebimento'
        verbose_name_plural = 'Ocorrências de Recebimentos'
        ordering = ['data_prevista']

    def __str__(self):
        return f'{self.recebimento_periodico.descricao} — {self.data_prevista:%d/%m/%Y}'

    def atualizar_status(self):
        hoje = timezone.localdate()
        if self.status == 'recebido':
            return
        if self.data_prevista < hoje:
            self.status = 'atrasado'
        else:
            self.status = 'a_receber'
        self.save(update_fields=['status'])


class RecebimentoAvulso(models.Model):
    STATUS_CHOICES = [
        ('a_receber', 'A receber (futuro)'),
        ('atrasado', 'Atrasado'),
        ('recebido', 'Recebido'),
    ]

    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=15, decimal_places=2)
    data_prevista = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='a_receber')
    data_recebimento = models.DateField(null=True, blank=True)
    valor_recebido = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    conta_destino = models.ForeignKey(
        'contas.Banco', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='recebimentos_avulsos',
    )
    movimentacao = models.ForeignKey(
        'contas.Movimentacao', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ocorrencias_recebimento_avulso',
    )
    observacoes = models.TextField(blank=True, default='')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Recebimento Avulso'
        verbose_name_plural = 'Recebimentos Avulsos'
        ordering = ['data_prevista']

    def __str__(self):
        return self.descricao

    def atualizar_status(self):
        hoje = timezone.localdate()
        if self.status == 'recebido':
            return
        if self.data_prevista < hoje:
            self.status = 'atrasado'
        else:
            self.status = 'a_receber'
        self.save(update_fields=['status'])