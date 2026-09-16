from django.conf import settings
from django.db import models
from django.utils import timezone


class Divida(models.Model):
    STATUS_CHOICES = [
        ('em_dia', 'Em dia'),
        ('a_pagar', 'A pagar (futura)'),
        ('atrasada', 'Atrasada'),
    ]

    descricao = models.CharField(max_length=255)
    credor = models.CharField(max_length=200, blank=True, default='')
    valor_total = models.DecimalField(max_digits=15, decimal_places=2)
    valor_pago = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    data_vencimento = models.DateField(default=timezone.localdate)
    num_parcelas = models.PositiveSmallIntegerField(default=1)
    valor_parcela = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    parcelas_restantes = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='a_pagar')
    ativa = models.BooleanField(default=True)
    observacoes = models.TextField(blank=True, default='')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Dívida'
        verbose_name_plural = 'Dívidas'
        ordering = ['data_vencimento']

    def __str__(self):
        return self.descricao

    @property
    def valor_restante(self):
        return self.valor_total - self.valor_pago

    @property
    def dias_em_atraso(self):
        hoje = timezone.localdate()
        if hoje > self.data_vencimento:
            return (hoje - self.data_vencimento).days
        return 0

    def atualizar_status(self):
        hoje = timezone.localdate()
        if self.valor_restante <= 0:
            self.status = 'em_dia'
        elif hoje < self.data_vencimento:
            self.status = 'a_pagar'
        else:
            self.status = 'atrasada'
        self.save(update_fields=['status'])


class HistoricoDivida(models.Model):
    divida = models.ForeignKey(Divida, on_delete=models.CASCADE, related_name='historicos')
    valor_restante = models.DecimalField(max_digits=15, decimal_places=2)
    descricao = models.CharField(max_length=255, blank=True, default='')
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Histórico da Dívida'
        verbose_name_plural = 'Históricos das Dívidas'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.divida.descricao} — restante R$ {self.valor_restante}'