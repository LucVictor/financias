from datetime import date

from django.db import models
from django.utils import timezone


class ObjetivoFinanceiro(models.Model):
    STATUS_CHOICES = [
        ('planejamento', 'Em planejamento'),
        ('ativo', 'Ativo (refletido no fluxo)'),
        ('concluido', 'Concluído'),
        ('cancelado', 'Cancelado'),
    ]

    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, default='')
    valor_final = models.DecimalField(max_digits=15, decimal_places=2)
    valor_inicial = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text='Valor já destinado para este objetivo (fictício, sem movimentação bancária).',
    )
    taxa_rendimento_pct = models.DecimalField(
        max_digits=6, decimal_places=3, default=0,
        help_text='Taxa de rendimento mensal (%) considerada nos cotaes.',
    )
    data_inicio = models.DateField()
    data_conclusao = models.DateField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='planejamento')
    refletir_fluxo = models.BooleanField(
        default=False,
        help_text='Se ativo, os aportes planejados aparecem no fluxo de caixa como saídas.',
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    alterado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Objetivo Financeiro'
        verbose_name_plural = 'Objetivos Financeiros'
        ordering = ['data_conclusao']

    def __str__(self):
        return self.nome

    @property
    def taxa_mensal(self):
        return self.taxa_rendimento_pct / 100

    @property
    def numero_meses(self):
        return (
            (self.data_conclusao.year - self.data_inicio.year) * 12
            + (self.data_conclusao.month - self.data_inicio.month)
            + 1
        )


class AporteMensal(models.Model):
    objetivo = models.ForeignKey(
        ObjetivoFinanceiro, on_delete=models.CASCADE, related_name='aportes_mensais'
    )
    ano = models.PositiveSmallIntegerField()
    mes = models.PositiveSmallIntegerField()
    valor = models.DecimalField(max_digits=15, decimal_places=2)
    descricao = models.CharField(max_length=255, blank=True, default='')
    manual = models.BooleanField(
        default=False,
        help_text='Aporte editado manualmente — não é recalculado automaticamente.',
    )
    realizado = models.BooleanField(default=False)
    valor_realizado = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        help_text='Valor efetivamente aportado (sobrepõe valor planejado no cálculo).',
    )
    data_realizado = models.DateField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Aporte Mensal'
        verbose_name_plural = 'Aportes Mensais'
        ordering = ['ano', 'mes']
        unique_together = ['objetivo', 'ano', 'mes']

    def __str__(self):
        return f'{self.objetivo.nome} — {self.mes:02d}/{self.ano}: R$ {self.valor}'

    @property
    def valor_efetivo(self):
        """Valor usado nos cálculos: realizado > planejado."""
        if self.valor_realizado is not None:
            return self.valor_realizado
        return self.valor

    @property
    def meses_restantes(self):
        """Meses até o fim do objetivo a partir deste mês (para juros compostos)."""
        hoje = timezone.localdate()
        data_ref = date(self.ano, self.mes, 1)
        fim = date(self.objetivo.data_conclusao.year, self.objetivo.data_conclusao.month, 1)
        return (
            (fim.year - data_ref.year) * 12
            + (fim.month - data_ref.month)
        )


