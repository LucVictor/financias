from django.conf import settings
from django.db import models
from django.utils import timezone


class Ativo(models.Model):
    TIPO_CHOICES = [
        ('fii', 'FII'),
        ('acao', 'Ação'),
        ('etf', 'ETF'),
        ('outro', 'Outro'),
    ]
    FONTE_CHOICES = [
        ('manual', 'Manual'),
        ('api', 'API'),
    ]

    ticker = models.CharField(max_length=20)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    quantidade = models.DecimalField(max_digits=15, decimal_places=6)
    preco_medio = models.DecimalField(max_digits=15, decimal_places=2)
    preco_atual = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    dividend_yield_mensal = models.DecimalField(
        max_digits=6, decimal_places=3, default=0,
        help_text='Rendimento de proventos mensal estimado (% do valor de mercado/mês).',
    )
    fonte_preco = models.CharField(max_length=10, choices=FONTE_CHOICES, default='manual')
    atualizado_em = models.DateTimeField(null=True, blank=True)
    ativo = models.BooleanField(default=True)
    observacoes = models.TextField(blank=True, default='')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Ativo (renda variável)'
        verbose_name_plural = 'Ativos (renda variável)'
        ordering = ['ticker']

    def __str__(self):
        return f'{self.ticker} ({self.get_tipo_display()})'

    @property
    def valor_mercado(self):
        return self.preco_atual * self.quantidade

    def proventos_mensais_estimados(self):
        return self.valor_mercado * self.dividend_yield_mensal / 100


class ProventoRecebido(models.Model):
    ativo = models.ForeignKey(Ativo, on_delete=models.CASCADE, related_name='proventos')
    valor = models.DecimalField(max_digits=15, decimal_places=2)
    data = models.DateField(default=timezone.localdate)
    tipo = models.CharField(max_length=50, blank=True, default='', help_text='ex.: dividendo, JCP')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Provento Recebido'
        verbose_name_plural = 'Proventos Recebidos'
        ordering = ['-data']

    def __str__(self):
        return f'{self.ativo.ticker} — R$ {self.valor} em {self.data:%d/%m/%Y}'


class HistoricoAtivo(models.Model):
    ativo = models.ForeignKey(Ativo, on_delete=models.CASCADE, related_name='historicos')
    valor_mercado = models.DecimalField(max_digits=15, decimal_places=2)
    preco = models.DecimalField(max_digits=15, decimal_places=2)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Histórico do Ativo'
        verbose_name_plural = 'Históricos dos Ativos'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.ativo.ticker} — R$ {self.valor_mercado}'