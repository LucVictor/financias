from django.conf import settings
from django.db import models
from django.utils import timezone


class Banco(models.Model):
    TIPO_CONTA_CHOICES = [
        ('corrente', 'Conta Corrente'),
        ('poupanca', 'Poupança'),
        ('salario', 'Conta Salário'),
        ('investimento', 'Conta Investimento'),
        ('outro', 'Outro'),
    ]

    nome = models.CharField(max_length=200)
    tipo_conta = models.CharField(max_length=20, choices=TIPO_CONTA_CHOICES, default='corrente')
    saldo_atual = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    observacoes = models.TextField(blank=True, default='')
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Banco / Conta'
        verbose_name_plural = 'Bancos / Contas'
        ordering = ['nome']

    def __str__(self):
        return f'{self.nome} ({self.get_tipo_conta_display()})'


class Movimentacao(models.Model):
    TIPO_CHOICES = [
        ('entrada', 'Entrada'),
        ('saida', 'Saída'),
    ]

    descricao = models.CharField(max_length=255)
    categoria = models.CharField(max_length=100, blank=True, default='')
    valor = models.DecimalField(max_digits=15, decimal_places=2)
    data = models.DateField(default=timezone.localdate)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    conta = models.ForeignKey(Banco, on_delete=models.PROTECT, related_name='movimentacoes')
    observacoes = models.TextField(blank=True, default='')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Movimentação'
        verbose_name_plural = 'Movimentações'
        ordering = ['-data', '-criado_em']

    def __str__(self):
        return f'{self.descricao} ({self.get_tipo_display()}) R$ {self.valor}'

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self._atualizar_saldo()

    def _atualizar_saldo(self):
        if self.tipo == 'entrada':
            self.conta.saldo_atual += self.valor
        else:
            self.conta.saldo_atual -= self.valor
        self.conta.save(update_fields=['saldo_atual'])
        HistoricoContaBancaria.objects.create(
            banco=self.conta,
            valor=self.conta.saldo_atual,
            descricao=f'Movimentação: {self.descricao}',
            usuario=None,
        )


class HistoricoContaBancaria(models.Model):
    banco = models.ForeignKey(Banco, on_delete=models.CASCADE, related_name='historicos')
    valor = models.DecimalField(max_digits=15, decimal_places=2)
    descricao = models.CharField(max_length=255, blank=True, default='')
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Histórico da Conta'
        verbose_name_plural = 'Históricos das Contas'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.banco.nome} — R$ {self.valor} em {self.criado_em:%d/%m/%Y %H:%M}'
