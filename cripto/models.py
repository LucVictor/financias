from django.conf import settings
from django.db import models
from django.utils import timezone


class Criptomoeda(models.Model):
    FONTE_CHOICES = [
        ('manual', 'Manual'),
        ('api', 'API'),
    ]
    FONTE_API_CHOICES = [
        ('coingecko', 'CoinGecko'),
        ('binance', 'Binance'),
        ('cryptocompare', 'CryptoCompare'),
    ]
    PAR_COTACAO_CHOICES = [
        ('USD', 'USD/USDT (converter para BRL)'),
        ('BRL', 'BRL (par direto em real)'),
    ]

    nome = models.CharField(max_length=200)
    simbolo = models.CharField(max_length=20, unique=True)
    quantidade = models.DecimalField(max_digits=20, decimal_places=10)
    cotacao_brl = models.DecimalField(
        max_digits=20, decimal_places=8, default=0,
        help_text='Cotação em BRL (R$ por unidade).',
    )
    cotacao_usd = models.DecimalField(
        max_digits=20, decimal_places=8, default=0,
        help_text='Cotação em USD por unidade.',
    )
    cotacao_btc = models.DecimalField(
        max_digits=30, decimal_places=15, null=True, blank=True,
        help_text='Cotação em BTC por unidade. Só se aplica quando não houver par direto '
                  'negociado contra BTC (não preencher para o próprio BTC).',
    )
    fonte_cotacao = models.CharField(max_length=10, choices=FONTE_CHOICES, default='manual')
    auto_cotacao = models.BooleanField(
        default=False,
        verbose_name='Precificação automática via API',
        help_text='Se marcado, a cotação será atualizada automaticamente pela API selecionada.',
    )
    fonte_api = models.CharField(
        max_length=15, choices=FONTE_API_CHOICES, default='coingecko',
        verbose_name='Fonte da API',
    )
    id_api = models.CharField(
        max_length=64, blank=True, default='',
        verbose_name='Identificador na fonte',
        help_text='ID usado pela fonte. Ex.: CoinGecko "bitcoin"/"turbo"; Binance/CryptoCompare '
                  'símbolo "BTC". Em branco, usa o símbolo da moeda.',
    )
    par_cotacao = models.CharField(
        max_length=3, choices=PAR_COTACAO_CHOICES, default='USD',
        verbose_name='Par de cotação',
        help_text='Se a moeda não tiver par direto em real (ex.: TURBOBRL), use USD/USDT — '
                  'o sistema converte automaticamente para BRL pela taxa de câmbio.',
    )
    atualizado_em = models.DateTimeField(null=True, blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Criptomoeda'
        verbose_name_plural = 'Criptomoedas'
        ordering = ['simbolo']

    def __str__(self):
        return f'{self.simbolo} ({self.nome})'

    @property
    def valor_brl(self):
        return self.cotacao_brl * self.quantidade

    @property
    def valor_usd(self):
        return self.cotacao_usd * self.quantidade


class HistoricoCripto(models.Model):
    moeda = models.ForeignKey(Criptomoeda, on_delete=models.CASCADE, related_name='historicos')
    valor_brl = models.DecimalField(max_digits=20, decimal_places=2)
    cotacao_brl = models.DecimalField(max_digits=20, decimal_places=8)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Histórico da Criptomoeda'
        verbose_name_plural = 'Históricos das Criptomoedas'
        ordering = ['-criado_em']

    def __str__(self):
        return f'{self.moeda.simbolo} — R$ {self.valor_brl}'