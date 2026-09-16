from django import forms

from sistema_financas.helpers import BootstrapFormMixin
from .models import Criptomoeda


class CriptomoedaForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Criptomoeda
        fields = [
            'nome', 'simbolo', 'quantidade', 'cotacao_brl', 'cotacao_usd',
            'cotacao_btc', 'fonte_cotacao', 'ativo',
            'auto_cotacao', 'fonte_api', 'id_api', 'par_cotacao',
        ]
        widgets = {
            'cotacao_btc': forms.TextInput(attrs={'placeholder': 'Somente sem par direto com BTC'}),
        }

    def clean(self):
        dados = super().clean()
        if dados.get('auto_cotacao') and dados.get('fonte_cotacao') == 'manual':
            # Precificação automática implicará em fonte = API após primeira atualização
            dados['fonte_cotacao'] = 'api'
        return dados