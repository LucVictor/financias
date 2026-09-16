import calendar
from datetime import date

from django.conf import settings
from django.db import models
from django.utils import timezone


def _add_meses(data, n):
    """Soma `n` meses a uma data ajustando o dia ao fim do mês quando preciso."""
    mes = data.month - 1 + n
    ano = data.year + mes // 12
    mes = mes % 12 + 1
    dia = min(data.day, calendar.monthrange(ano, mes)[1])
    return date(ano, mes, dia)


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
    data_vencimento = models.DateField(default=timezone.localdate,
                                       help_text='Data da primeira/renda parcela a pagar.')
    num_parcelas = models.PositiveSmallIntegerField(default=1)
    valor_parcela = models.DecimalField(
        max_digits=15, decimal_places=2, blank=True, null=True,
        help_text='Deixe em branco para calcular automaticamente (valor_total ÷ nº parcelas).',
    )
    parcelas_restantes = models.PositiveSmallIntegerField(default=1)
    para_pagamento = models.BooleanField(
        default=False,
        verbose_name='Considerar para pagamento',
        help_text='Se marcado, as parcelas desta dívida aparecem no fluxo de caixa como pagamento.',
    )
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

    def save(self, *args, **kwargs):
        if not self.valor_parcela:
            self.valor_parcela = self.valor_total / max(self.num_parcelas, 1)
        super().save(*args, **kwargs)
        if not self.parcelas.exists():
            self._gerar_parcelas()
        self._sync_valores()

    def _gerar_parcelas(self):
        base = self.data_vencimento or timezone.localdate()
        for i in range(self.num_parcelas):
            ParcelaDivida.objects.create(
                divida=self,
                numero=i + 1,
                valor=self.valor_parcela,
                data_vencimento=_add_meses(base, i),
            )
        # Marca como pagas as primeiras parcelas equivalentes ao valor já pago
        n_pagas = min(
            int(round(self.valor_pago / self.valor_parcela)),
            self.num_parcelas,
        )
        if n_pagas > 0:
            for parcela in self.parcelas.order_by('numero')[:n_pagas]:
                parcela.status = 'paga'
                parcela.data_pagamento = parcela.data_vencimento
                parcela.save(update_fields=['status', 'data_pagamento'])

    def _sync_valores(self):
        pagas = self.parcelas.filter(status='paga').order_by('numero')
        valor_pago = pagas.aggregate(t=models.Sum('valor'))['t'] or 0
        restantes = self.num_parcelas - pagas.count()
        Divida.objects.filter(pk=self.pk).update(
            valor_pago=valor_pago, parcelas_restantes=restantes,
        )
        self.valor_pago = valor_pago
        self.parcelas_restantes = restantes

    @property
    def valor_restante(self):
        parcelas_abertas = self.parcelas.exclude(status='paga')
        if parcelas_abertas.exists():
            return parcelas_abertas.aggregate(t=models.Sum('valor'))['t'] or 0
        return self.valor_total - self.valor_pago

    @property
    def proxima_parcela(self):
        return self.parcelas.exclude(status='paga').order_by('data_vencimento').first()

    @property
    def parcelas_abertas(self):
        return self.parcelas.exclude(status='paga')

    @property
    def parcelas_pagas(self):
        return self.parcelas.filter(status='paga').count()

    @property
    def dias_em_atraso(self):
        proxima = self.proxima_parcela
        if proxima and timezone.localdate() > proxima.data_vencimento:
            return (timezone.localdate() - proxima.data_vencimento).days
        return 0

    def atualizar_status(self):
        hoje = timezone.localdate()
        proxima = self.proxima_parcela
        if not proxima:
            self.status = 'em_dia'
        elif hoje < proxima.data_vencimento:
            self.status = 'a_pagar'
        else:
            self.status = 'atrasada'
        self.save(update_fields=['status'])


class ParcelaDivida(models.Model):
    STATUS_CHOICES = [
        ('a_pagar', 'A pagar'),
        ('paga', 'Paga'),
    ]

    divida = models.ForeignKey(Divida, on_delete=models.CASCADE, related_name='parcelas')
    numero = models.PositiveSmallIntegerField()
    valor = models.DecimalField(max_digits=15, decimal_places=2)
    data_vencimento = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='a_pagar')
    data_pagamento = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = 'Parcela da Dívida'
        verbose_name_plural = 'Parcelas das Dívidas'
        ordering = ['data_vencimento']

    @property
    def vencida(self):
        return self.data_vencimento < timezone.localdate()

    def __str__(self):
        return f'{self.divida.descricao} — parcela {self.numero}/{self.divida.num_parcelas}'


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