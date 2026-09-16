from django import forms

from sistema_financas.helpers import BootstrapFormMixin
from .models import Criptomoeda


class CriptomoedaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Criptomoeda
        fields = [
            'nome', 'simbolo', 'quantidade', 'cotacao_brl', 'cotacao_usd',
            'cotacao_btc', 'fonte_cotacao', 'ativo',
        ]
        widgets = {
            'cotacao_btc': forms.TextInput(attrs={'placeholder': 'Somente sem par direto com BTC'}),
        }