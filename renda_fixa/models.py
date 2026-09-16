from django.conf import settings
from django.db import models
from django.utils import timezone
from decimal import Decimal


class TaxaCDI(models.Model):
    """Registros históricos da taxa CDI anual (%). O mais recente é a taxa vigente."""
    valor_anual = models.DecimalField(max_digits=6, decimal_places=3)
    data_inicio = models.DateField(default=timezone.localdate)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Taxa CDI'
        verbose_name_plural = 'Taxas CDI'
        ordering = ['-data_inicio']

    def __str__(self):
        return f'CDI {self.valor_anual}% a.a. (desde {self.data_inicio:%d/%m/%Y})'

    @staticmethod
    def taxa_vigente():
        ultima = TaxaCDI.objects.order_by('-data_inicio', '-id').first()
        if ultima:
            return ultima.valor_anual
        return Decimal('0')


class AplicacaoCDB(models.Model):
    instituicao = models.CharField(max_length=200)
    valor_aplicado = models.DecimalField(max_digits=15, decimal_places=2)
    data_aplicacao = models.DateField()
    data_vencimento = models.DateField()
    percentual_cdi = models.DecimalField(
        max_digits=8, decimal_places=3, default=Decimal('100.000'),
        help_text='Percentual do CDI contratado (ex.: 100 = 100% do CDI, 110 = 110%).',
    )
    observacoes = models.TextField(blank=True, default='')
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Aplicação de CDB'
        verbose_name_plural = 'Aplicações de CDB'
        ordering = ['data_aplicacao']

    def __str__(self):
        return f'{self.instituicao} — R$ {self.valor_aplicado} ({self.percentual_cdi}% CDI)'


class HistoricoCDB(models.Model):
    aplicacao = models.ForeignKey(AplicacaoCDB, on_delete=models.CASCADE, related_name='historicos')
    valor_bruto = models.DecimalField(max_digits=15, decimal_places=2)
    valor_liquido = models.DecimalField(max_digits=15, decimal_places=2)
    dias_uteis = models.PositiveIntegerField(default=0)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Histórico do CDB'
        verbose_name_plural = 'Históricos dos CDBs'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.aplicacao} — bruto R$ {self.valor_bruto}'