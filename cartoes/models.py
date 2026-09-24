from django.conf import settings
from django.db import models
from django.db.models import Sum, Q
from django.utils import timezone


class CartaoCredito(models.Model):
    STATUS_CHOICES = [
        ('paga', 'Fatura paga'),
        ('aberta', 'Fatura em aberto'),
        ('atrasada', 'Fatura atrasada'),
    ]

    nome = models.CharField(max_length=200)
    banco_emissor = models.CharField(max_length=200, blank=True, default='')
    limite_total = models.DecimalField(max_digits=15, decimal_places=2)
    dia_fechamento = models.PositiveSmallIntegerField(
        default=1,
        help_text='Dia do mês em que a fatura fecha (1-28).',
    )
    dia_vencimento = models.PositiveSmallIntegerField(
        default=10,
        help_text='Dia do mês em que a fatura vence (1-28).',
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Cartão de Crédito'
        verbose_name_plural = 'Cartões de Crédito'
        ordering = ['nome']

    def __str__(self):
        return f'{self.nome} ({self.banco_emissor})'

    def valor_comprometido(self):
        total = ParcelaCompra.objects.filter(
            Q(status='a_vencer') | Q(status='fatura_atual')
        ).filter(compra__cartao=self, compra__cancelada=False).aggregate(total=Sum('valor'))['total'] or 0
        return total

    def limite_disponivel(self):
        return self.limite_total - self.valor_comprometido()

    def saldo_devedor_fatura_atual(self):
        """Soma das parcelas já vencidas/na fatura atual (não pagas), sem depender
        da existência de registros de FaturaCartao."""
        hoje = timezone.localdate()
        q = (
            Q(compra__cartao=self)
            & Q(compra__cancelada=False)
            & ~Q(status='paga')
            & (
                Q(ano__lt=hoje.year)
                | Q(ano=hoje.year, mes__lte=hoje.month)
                | Q(status='fatura_atual')
            )
        )
        return ParcelaCompra.objects.filter(q).aggregate(total=Sum('valor'))['total'] or 0

    def fatura_do_mes(self, ano, mes):
        try:
            return FaturaCartao.objects.get(cartao=self, ano=ano, mes=mes)
        except FaturaCartao.DoesNotExist:
            return None


class CompraCartao(models.Model):
    FORMA_CHOICES = [
        ('avista', 'À vista'),
        ('parcelada', 'Parcelada'),
    ]

    cartao = models.ForeignKey(CartaoCredito, on_delete=models.PROTECT, related_name='compras')
    descricao = models.CharField(max_length=255)
    estabelecimento = models.CharField(max_length=255, blank=True, default='')
    categoria = models.CharField(max_length=100, blank=True, default='')
    valor_total = models.DecimalField(max_digits=15, decimal_places=2)
    data_compra = models.DateField(default=timezone.localdate)
    forma_pagamento = models.CharField(max_length=10, choices=FORMA_CHOICES, default='avista')
    num_parcelas = models.PositiveSmallIntegerField(default=1)
    valor_parcela = models.DecimalField(
        max_digits=15, decimal_places=2, blank=True, null=True,
        help_text='Deixe em branco para calcular automaticamente (valor_total ÷ nº parcelas).',
    )
    cancelada = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Compra no Cartão'
        verbose_name_plural = 'Compras no Cartão'
        ordering = ['-data_compra']

    def __str__(self):
        return self.descricao

    def save(self, *args, **kwargs):
        if self.forma_pagamento == 'avista':
            self.num_parcelas = 1
            self.valor_parcela = self.valor_total
        if self.valor_parcela is None or self.valor_parcela == 0:
            self.valor_parcela = self.valor_total / max(self.num_parcelas, 1)
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self._gerar_parcelas()

    def _mes_fatura(self, data):
        """Determina o ano/mês da fatura a partir da data e do fechamento do cartão."""
        ano, mes = data.year, data.month
        if data.day > self.cartao.dia_fechamento:
            # Entra na fatura do mês seguinte
            mes += 1
            if mes > 12:
                mes = 1
                ano += 1
        return ano, mes

    def _gerar_parcelas(self):
        ano, mes = self._mes_fatura(self.data_compra)
        for i in range(self.num_parcelas):
            status = 'fatura_atual' if i == 0 else 'a_vencer'
            ParcelaCompra.objects.create(
                compra=self,
                numero_parcela=i + 1,
                valor=self.valor_parcela,
                ano=ano,
                mes=mes,
                status=status,
            )
            mes += 1
            if mes > 12:
                mes = 1
                ano += 1
        # Recalcula limites/histórico do cartão
        self.cartao.save()

    def regerar_parcelas(self):
        """Regenera as parcelas após uma edição da compra, preservando o
        status 'paga' das parcelas antigas que mantêm o mesmo número.

        Retorna os meses (ano, mes) impactados para ressincronizar as faturas.
        """
        antigas = list(self.parcelas.all())
        pagas = {p.numero_parcela for p in antigas if p.status == 'paga'}
        meses_impactados = {(p.ano, p.mes) for p in antigas}
        self.parcelas.all().delete()
        ano, mes = self._mes_fatura(self.data_compra)
        for i in range(self.num_parcelas):
            numero = i + 1
            if numero in pagas:
                status = 'paga'
            else:
                status = 'fatura_atual' if i == 0 else 'a_vencer'
            ParcelaCompra.objects.create(
                compra=self,
                numero_parcela=numero,
                valor=self.valor_parcela,
                ano=ano,
                mes=mes,
                status=status,
            )
            meses_impactados.add((ano, mes))
            mes += 1
            if mes > 12:
                mes = 1
                ano += 1
        return meses_impactados


class ParcelaCompra(models.Model):
    STATUS_CHOICES = [
        ('a_vencer', 'A vencer'),
        ('fatura_atual', 'Na fatura atual'),
        ('paga', 'Paga'),
    ]

    compra = models.ForeignKey(CompraCartao, on_delete=models.CASCADE, related_name='parcelas')
    numero_parcela = models.PositiveSmallIntegerField()
    valor = models.DecimalField(max_digits=15, decimal_places=2)
    ano = models.PositiveSmallIntegerField()
    mes = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='a_vencer')
    fatura = models.ForeignKey(
        'FaturaCartao', on_delete=models.SET_NULL, null=True, blank=True, related_name='parcelas'
    )

    class Meta:
        verbose_name = 'Parcela da Compra'
        verbose_name_plural = 'Parcelas das Compras'
        ordering = ['ano', 'mes', 'numero_parcela']

    def __str__(self):
        return f'{self.compra.descricao} — parcela {self.numero_parcela}/{self.compra.num_parcelas}'


class FaturaCartao(models.Model):
    STATUS_CHOICES = [
        ('aberta', 'Em aberto'),
        ('paga', 'Paga'),
        ('atrasada', 'Atrasada'),
    ]

    cartao = models.ForeignKey(CartaoCredito, on_delete=models.CASCADE, related_name='faturas')
    ano = models.PositiveSmallIntegerField()
    mes = models.PositiveSmallIntegerField()
    valor_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    estado = models.CharField(max_length=10, choices=STATUS_CHOICES, default='aberta')
    data_pagamento = models.DateField(null=True, blank=True)
    valor_pago = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Fatura do Cartão'
        verbose_name_plural = 'Faturas dos Cartões'
        ordering = ['-ano', '-mes']
        unique_together = [('cartao', 'ano', 'mes')]

    def __str__(self):
        return f'Fatura {self.mes:02d}/{self.ano} — {self.cartao.nome}'

    @property
    def data_vencimento(self):
        return timezone.localdate().replace(day=self.cartao.dia_vencimento, month=self.mes, year=self.ano)

    def atualizar_total(self):
        total = self.parcelas.aggregate(total=Sum('valor'))['total'] or 0
        self.valor_total = total
        self.save(update_fields=['valor_total'])


class HistoricoCartao(models.Model):
    cartao = models.ForeignKey(CartaoCredito, on_delete=models.CASCADE, related_name='historicos')
    limite_disponivel = models.DecimalField(max_digits=15, decimal_places=2)
    saldo_devedor = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Histórico do Cartão'
        verbose_name_plural = 'Históricos dos Cartões'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.cartao.nome} — limite disp. R$ {self.limite_disponivel}'