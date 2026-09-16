from django.conf import settings
from django.db import models
from django.utils import timezone
from decimal import Decimal


class ContaPoupanca(models.Model):
    nome = models.CharField(max_length=200)
    instituicao = models.CharField(max_length=200, blank=True, default='')
    saldo_atual = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    usar_regra_selic = models.BooleanField(
        default=True,
        help_text='Aplica a regra oficial da poupança (0,5% + TR quando Selic > 8,5% a.a., '
                  'ou 70% da Selic + TR quando ≤ 8,5% a.a.).',
    )
    taxa_fixa_mensal = models.DecimalField(
        max_digits=6, decimal_places=3, default=Decimal('0.50'),
        help_text='Taxa mensal (%) usada quando "usar_regra_selic" está desativado.',
    )
    taxa_selic_anual = models.DecimalField(
        max_digits=6, decimal_places=3, default=Decimal('10.500'),
        help_text='Taxa Selic vigente (% a.a.), usada para aplicar a regra da poupança.',
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Conta Poupança'
        verbose_name_plural = 'Contas Poupança'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    def taxa_mensal_efetiva(self):
        if self.usar_regra_selic:
            if self.taxa_selic_anual > Decimal('8.5'):
                return Decimal('0.50')
            return (self.taxa_selic_anual * Decimal('0.7')) / Decimal('12')
        return self.taxa_fixa_mensal


class MovimentacaoPoupanca(models.Model):
    TIPO_CHOICES = [
        ('aporte', 'Aporte'),
        ('retirada', 'Retirada'),
    ]

    conta = models.ForeignKey(ContaPoupanca, on_delete=models.PROTECT, related_name='movimentacoes')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    valor = models.DecimalField(max_digits=15, decimal_places=2)
    data = models.DateField(default=timezone.localdate)
    descricao = models.CharField(max_length=255, blank=True, default='')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Movimentação de Poupança'
        verbose_name_plural = 'Movimentações de Poupança'
        ordering = ['-data']

    def __str__(self):
        return f'{self.get_tipo_display()} R$ {self.valor} em {self.conta.nome}'

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            if self.tipo == 'aporte':
                self.conta.saldo_atual += self.valor
            else:
                self.conta.saldo_atual -= self.valor
            self.conta.save(update_fields=['saldo_atual'])


class HistoricoPoupanca(models.Model):
    conta = models.ForeignKey(ContaPoupanca, on_delete=models.CASCADE, related_name='historicos')
    valor = models.DecimalField(max_digits=15, decimal_places=2)
    descricao = models.CharField(max_length=255, blank=True, default='')
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Histórico da Poupança'
        verbose_name_plural = 'Históricos da Poupança'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.conta.nome} — R$ {self.valor} em {self.criado_em:%d/%m/%Y %H:%M}'